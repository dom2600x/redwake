"""Paired inference-only tool compatibility trials; no lab probes are executed."""

import argparse
import copy
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import time

from .cli import positive
from .comparison import json_sha256, source_provenance
from .guidance import ACTOR_NAMES
from .lab import allowed_paths
from .providers import Ollama, TOOLS, provider_failure, validate_diagnostic
from .runner import discovery_checks

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {'gpt-oss:120b': '65224d9d368f', 'nemotron-3-super': '3130bcd41596'}
CAPACITIES = (1024, 2048)
CASES = ('single', 'batch_two', 'replay')


def write_json(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')
    temporary.replace(path)


def inputs():
    result = {}
    for model, run_id in SOURCES.items():
        source = ROOT / 'docs/experiments/2026-10-27-discovery-batching/runs' / run_id / 'state.json'
        raw = source.read_bytes()
        state = json.loads(raw)
        assert state['config']['model'] == model and state['diagnostics'][-1]['http_status'] == 500
        cases = {}
        for name, actors in (('single', ['alice']), ('batch_two', ['alice', 'bob'])):
            expected = [{'actor': actor, 'path': '/api/projects'} for actor in actors]
            messages = [
                {'role': 'system', 'content': 'Use actual probe tool_calls in this synthetic API lab. '
                 'Return the requested calls in a single assistant response. Do not simulate tool results.'},
                {'role': 'user', 'content': 'Issue exactly these independent probes: ' + json.dumps(expected)}]
            cases[name] = {'messages': messages, 'baseline': expected}
        cases['replay'] = {'messages': state['messages'],
                           'baseline': discovery_checks(state['evidence'])[:2],
                           'source_run': run_id, 'source_sha256': hashlib.sha256(raw).hexdigest()}
        result[model] = cases
    return result


def classify(message, case, expected):
    calls = message.get('tool_calls') or []
    if not isinstance(calls, list) or len(calls) > 12:
        return 'invalid_tools'
    if not calls:
        return 'no_tools'
    pairs = []
    for call in calls:
        function = call.get('function', {}) if isinstance(call, dict) else {}
        if not isinstance(function, dict):
            return 'invalid_tools'
        args = function.get('arguments')
        if (function.get('name') != 'probe' or not isinstance(args, dict)
                or set(args) != {'actor', 'path'} or not isinstance(args['actor'], str)
                or not isinstance(args['path'], str) or args['actor'] not in ACTOR_NAMES
                or args['path'] not in allowed_paths('discovery')):
            return 'invalid_tools'
        pairs.append((args['actor'], args['path']))
    if case == 'replay':
        return 'in_scope'
    target = [(p['actor'], p['path']) for p in expected]
    return 'matched' if sorted(pairs) == sorted(target) else 'mismatch'


def plan(repeat):
    rows = []
    for repetition in range(1, repeat + 1):
        # Rotate capacity order within every paired model/case block.
        for index, model in enumerate(SOURCES):
            for case_index, case in enumerate(CASES):
                order = CAPACITIES if (repetition + index + case_index) % 2 else CAPACITIES[::-1]
                for capacity in order:
                    for backend in ('baseline', 'ollama'):
                        rows.append(dict(repeat=repetition, model=model, case=case,
                                         capacity=capacity, backend=backend))
    return rows


def trial(slot, case, provider=None):
    started = time.monotonic()
    row = dict(slot, status='reserved', calls_reserved=0 if slot['backend'] == 'baseline' else 1,
               output_reserved=0 if slot['backend'] == 'baseline' else slot['capacity'],
               input_tokens=0, output_tokens=0, usage_complete=True, seconds=0)
    try:
        if slot['backend'] == 'baseline':
            response = {'message': {'role': 'assistant', 'content': '', 'tool_calls': [
                {'function': {'name': 'probe', 'arguments': args}} for args in case['baseline']]},
                'prompt_eval_count': 0, 'eval_count': 0, 'done_reason': 'stop'}
        else:
            if provider is None:
                provider = Ollama(slot['model'])
            response = provider.chat(copy.deepcopy(case['messages']), slot['capacity'], 60)
        message = response.get('message')
        if (not isinstance(message, dict) or message.get('role') != 'assistant'
                or 'error' in response or 'error' in message):
            from .providers import ProviderError
            raise ProviderError('response_protocol')
        # Only the model message and allowlisted accounting are retained.
        row['message'] = {k: message[k] for k in ('role', 'content', 'thinking', 'tool_calls') if k in message}
        row['result'] = classify(row['message'], slot['case'], case['baseline'])
        for source, target in (('prompt_eval_count', 'input_tokens'), ('eval_count', 'output_tokens')):
            value = response.get(source)
            if type(value) is int and value >= 0:
                row[target] = value
            else:
                row['usage_complete'] = False
        reason = response.get('done_reason')
        row['done_reason'] = reason if reason in ('stop', 'length', 'load', 'unload') else 'unknown'
        row['status'] = 'returned'
    except Exception as exc:
        row.update(status='failed', result='provider_failure', usage_complete=False,
                   diagnostic=dict(provider_failure(exc).diagnostic, model_call=1))
    row['seconds'] = time.monotonic() - started
    return row


def verify_data(data):
    if data['schema_version'] != 1 or data['kind'] != 'provider_compatibility':
        raise ValueError('Unsupported compatibility data')
    if type(data['repeat']) is not int or data['repeat'] < 1:
        raise ValueError('Invalid repetition count')
    if data['controls'] != {'temperature': 0, 'timeout': 60, 'retries': 0,
                             'probes_executed': 0, 'capacities': list(CAPACITIES)}:
        raise ValueError('Compatibility controls differ')
    if data['tools_sha256'] != json_sha256(TOOLS) or data['inputs'] != inputs():
        raise ValueError('Recorded compatibility inputs differ')
    expected = plan(data['repeat'])
    if len(data['rows']) != len(expected):
        raise ValueError('Incomplete compatibility plan')
    for row, slot in zip(data['rows'], expected):
        allowed = set(slot) | {'status', 'calls_reserved', 'output_reserved', 'input_tokens',
                              'output_tokens', 'usage_complete', 'seconds', 'message',
                              'result', 'done_reason', 'diagnostic'}
        if set(row) - allowed or type(row['usage_complete']) is not bool:
            raise ValueError('Invalid trial schema')
        if (type(row['seconds']) not in (int, float) or not math.isfinite(row['seconds'])
                or row['seconds'] < 0):
            raise ValueError('Invalid elapsed time')
        if any(row[k] != v for k, v in slot.items()):
            raise ValueError('Compatibility trial differs from plan')
        baseline = slot['backend'] == 'baseline'
        if (row['calls_reserved'] != (0 if baseline else 1)
                or row['output_reserved'] != (0 if baseline else slot['capacity'])):
            raise ValueError('Reservation mismatch')
        if row['status'] == 'failed':
            validate_diagnostic(row['diagnostic'])
            if (baseline or row['usage_complete'] or row['result'] != 'provider_failure'
                    or 'message' in row or row['diagnostic']['source'] != 'provider'
                    or row['diagnostic'].get('model_call') != 1):
                raise ValueError('Invalid failure accounting')
        elif row['status'] == 'returned':
            message = row['message']
            if (not isinstance(message, dict) or message.get('role') != 'assistant'
                    or set(message) - {'role', 'content', 'thinking', 'tool_calls'}
                    or 'diagnostic' in row
                    or row['done_reason'] not in ('stop', 'length', 'load', 'unload', 'unknown')):
                raise ValueError('Invalid returned message')
            case = data['inputs'][slot['model']][slot['case']]
            if row['result'] != classify(row['message'], slot['case'], case['baseline']):
                raise ValueError('Compatibility classification mismatch')
            if baseline and (not row['usage_complete'] or row['input_tokens'] or row['output_tokens']
                             or row['result'] != ('in_scope' if slot['case'] == 'replay' else 'matched')):
                raise ValueError('Scripted control did not match')
        else:
            raise ValueError('Unfinished compatibility trial')
        for key in ('input_tokens', 'output_tokens'):
            if type(row[key]) is not int or row[key] < 0:
                raise ValueError('Invalid returned accounting')
    return len(expected)


def verify_bundle(directory):
    directory = Path(directory)
    manifest = json.loads((directory / 'manifest.json').read_text())
    if manifest.get('schema_version') != 2 or manifest.get('kind') != 'provider_compatibility':
        raise ValueError('Unsupported compatibility manifest')
    if set(manifest['sha256']) != {'compatibility.json', 'report.md'}:
        raise ValueError('Invalid compatibility inventory')
    if {p.name for p in directory.iterdir()} != {'manifest.json', 'compatibility.json', 'report.md'}:
        raise ValueError('Compatibility inventory differs')
    for name, digest in manifest['sha256'].items():
        p = directory / name
        if p.is_symlink() or hashlib.sha256(p.read_bytes()).hexdigest() != digest:
            raise ValueError('Compatibility artifact hash mismatch')
    count = verify_data(json.loads((directory / 'compatibility.json').read_text()))
    return {'bundle': directory.name, 'runs': count, 'files': 2}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--repeat', type=positive, default=3)
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args(argv)
    if args.verify:
        print(verify_bundle(args.directory))
        return 0
    args.directory.mkdir(parents=True, exist_ok=False)
    data = dict(schema_version=1, kind='provider_compatibility', repeat=args.repeat,
                started_utc=datetime.now(timezone.utc).isoformat(), inputs=inputs(),
                controls=dict(temperature=0, timeout=60, retries=0, probes_executed=0,
                              capacities=list(CAPACITIES)), tools_sha256=json_sha256(TOOLS),
                provenance=source_provenance(), rows=[])
    path = args.directory / 'compatibility.json'
    write_json(path, data)
    for slot in plan(args.repeat):
        # Persist the reservation before any network call. A crash leaves this
        # slot visibly unfinished; fresh runs never overwrite or retry it.
        reserved = dict(slot, status='reserved',
                        calls_reserved=0 if slot['backend'] == 'baseline' else 1,
                        output_reserved=0 if slot['backend'] == 'baseline' else slot['capacity'],
                        usage_complete=False)
        data['rows'].append(reserved)
        write_json(path, data)
        row = trial(slot, data['inputs'][slot['model']][slot['case']])
        data['rows'][-1] = row
        write_json(path, data)
        print(json.dumps({k: row[k] for k in ('repeat', 'model', 'case', 'capacity', 'backend', 'result')}), flush=True)
    verify_data(data)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
