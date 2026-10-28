"""Declared GPT-OSS transcript reductions, with a direct native API cross-check."""

import argparse
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from .cli import positive
from .comparison import json_sha256, source_provenance
from .compatibility import inputs as compatibility_inputs, trial, verify_trial, write_json
from .providers import Ollama, TOOLS, http_failure
from .runner import discovery_checks
from .transport import request_json

MODEL = 'gpt-oss:120b'
VARIANTS = ('original', 'no_thinking', 'no_function_index', 'no_call_ids',
            'correlated_results', 'tail_pair', 'combined_removals', 'fresh_single')
ROUTES = ('adapter', 'native')
CONTROLS = dict(temperature=0, timeout=60, capacity=1024, retries=0, probes_executed=0)


def inputs():
    source = compatibility_inputs()[MODEL]
    result = {}
    for variant in VARIANTS:
        case = copy.deepcopy(source['single'] if variant == 'fresh_single' else source['replay'])
        messages = case['messages']
        if variant == 'tail_pair':
            messages = messages[:2] + messages[-2:]
        for message in messages:
            if variant in ('no_thinking', 'combined_removals'):
                message.pop('thinking', None)
            for call in message.get('tool_calls', []):
                if variant in ('no_function_index', 'combined_removals'):
                    call['function'].pop('index', None)
                if variant in ('no_call_ids', 'combined_removals'):
                    call.pop('id', None)
        if variant == 'correlated_results':
            pending = []
            for message in messages:
                if message['role'] == 'assistant':
                    pending = [call['id'] for call in message.get('tool_calls', [])]
                elif message['role'] == 'tool':
                    if not pending:
                        raise ValueError('Cannot correlate saved tool response')
                    message['tool_call_id'] = pending.pop(0)
        case['messages'] = messages
        if variant != 'fresh_single':
            evidence = [json.loads(m['content']) for m in messages if m['role'] == 'tool']
            case['baseline'] = discovery_checks(evidence)[:2]
        case['messages_sha256'] = json_sha256(messages)
        result[variant] = case
    return result


class NativeOllama(Ollama):
    """Bypass chat() construction/validation; retain the same secured transport.

    This is a request-construction cross-check, not an independent HTTP client.
    The common trial scorer validates returned messages and sanitizes failures.
    """
    def chat(self, messages, output_limit, timeout):
        headers = {'Content-Type': 'application/json'}
        if self.key:
            headers['Authorization'] = 'Bearer ' + self.key
        status, response = request_json(self.endpoint + '/api/chat', headers,
            {'model': self.model, 'messages': messages, 'tools': TOOLS, 'stream': False,
             'options': {'temperature': 0, 'num_predict': output_limit}},
            timeout=timeout, limit=1048576, strict_json=True,
            use_env_proxy=self.endpoint == 'https://ollama.com')
        if status != 200:
            raise http_failure(status)
        return response


def plan(repeat):
    slots = []
    for repetition in range(1, repeat + 1):
        offset = (repetition - 1) % len(VARIANTS)
        variants = VARIANTS[offset:] + VARIANTS[:offset]
        for index, variant in enumerate(variants):
            routes = ROUTES if (repetition + index) % 2 else ROUTES[::-1]
            for route in routes:
                for backend in ('baseline', 'ollama'):
                    slots.append(dict(repeat=repetition, model=MODEL, variant=variant, route=route,
                                      case='single' if variant == 'fresh_single' else 'replay',
                                      capacity=1024, backend=backend))
    return slots


def verify_data(data):
    if (data['schema_version'] != 1 or data['kind'] != 'transcript_reduction'
            or type(data['repeat']) is not int or data['repeat'] < 1
            or data['controls'] != CONTROLS or data['tools_sha256'] != json_sha256(TOOLS)
            or data['inputs'] != inputs()):
        raise ValueError('Transcript experiment controls differ')
    expected = plan(data['repeat'])
    if len(data['rows']) != len(expected):
        raise ValueError('Incomplete transcript experiment')
    for row, slot in zip(data['rows'], expected):
        verify_trial(row, slot, data['inputs'][slot['variant']])
    return len(expected)


def verify_bundle(directory):
    directory = Path(directory)
    manifest = json.loads((directory / 'manifest.json').read_text())
    if manifest.get('schema_version') != 2 or manifest.get('kind') != 'transcript_reduction':
        raise ValueError('Invalid transcript manifest')
    names = {'transcript.json', 'report.md'}
    if set(manifest['sha256']) != names or {p.name for p in directory.iterdir()} != names | {'manifest.json'}:
        raise ValueError('Invalid transcript inventory')
    for name, digest in manifest['sha256'].items():
        path = directory / name
        if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError('Transcript artifact hash mismatch')
    count = verify_data(json.loads((directory / 'transcript.json').read_text()))
    return dict(bundle=directory.name, runs=count, files=2)


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
    data = dict(schema_version=1, kind='transcript_reduction', repeat=args.repeat,
                started_utc=datetime.now(timezone.utc).isoformat(), controls=dict(CONTROLS),
                tools_sha256=json_sha256(TOOLS), inputs=inputs(), provenance=source_provenance(), rows=[])
    path = args.directory / 'transcript.json'
    write_json(path, data)
    for slot in plan(args.repeat):
        data['rows'].append(dict(slot, status='reserved', usage_complete=False,
                                calls_reserved=int(slot['backend'] == 'ollama'),
                                output_reserved=1024 if slot['backend'] == 'ollama' else 0))
        write_json(path, data)
        # Instantiate lazily inside trial's safe exception boundary, so setup
        # failures remain planned outcomes and never expose arbitrary messages.
        class Provider:
            def chat(self, messages, output_limit, timeout):
                factory = Ollama if slot['route'] == 'adapter' else NativeOllama
                return factory(MODEL).chat(messages, output_limit, timeout)
        row = trial(slot, data['inputs'][slot['variant']], Provider())
        data['rows'][-1] = row
        write_json(path, data)
        print(json.dumps({k: row[k] for k in ('repeat', 'variant', 'route', 'backend', 'result')}), flush=True)
    verify_data(data)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
