"""Rotate fixed profiles across discovery fixtures; preserve every planned run."""

import argparse
from datetime import datetime, timezone
import fcntl
import json
from pathlib import Path
import re

from .cli import positive
from .comparison import (MODELS, MODES, PROFILES, aggregate as aggregate_models,
                         experiment_controls, result_row, source_provenance)
from .guidance import DISCOVERY_SCENARIOS
from .lab import lab
from .providers import Ollama, validate_diagnostic
from .report import write_report
from .runner import investigate
from .store import Store

PROFILE_NAMES = tuple(PROFILES)
FIXTURES = DISCOVERY_SCENARIOS
ENDPOINT = 'https://ollama.com'


def plan(repeat):
    slots = []
    block = 0
    for repetition in range(1, repeat + 1):
        for fixture_index, scenario in enumerate(FIXTURES):
            for mode_index, mode in enumerate(MODES):
                block += 1
                # Repetition offset matters: six blocks is a multiple of three,
                # so block number alone would repeat each condition's order.
                offset = (fixture_index * len(MODES) + mode_index + repetition - 1) % len(PROFILE_NAMES)
                profiles = PROFILE_NAMES[offset:] + PROFILE_NAMES[:offset]
                for position, profile in enumerate(profiles):
                    # Two repetition offsets avoid cancellation with the
                    # profile-position rotation for a fixed treatment.
                    model_offset = (block - 1 + position + 2 * (repetition - 1)) % len(MODELS)
                    models = MODELS[model_offset:] + MODELS[:model_offset]
                    for model_position, model in enumerate(('baseline',) + models):
                        slots.append(dict(repeat=repetition, scenario=scenario, mode=mode,
                                          experiment_profile=profile, model=model, block=block,
                                          profile_position=position + 1, model_position=model_position))
    return slots


def config_for(slot):
    profile = PROFILES[slot['experiment_profile']]
    return dict(experiment_controls(profile), backend='baseline' if slot['model'] == 'baseline' else 'ollama',
                model=slot['model'], endpoint=ENDPOINT, scenario=slot['scenario'],
                mode=slot['mode'], limits=profile.limits)


def suite_row(state, slot):
    row = result_row(state, slot['repeat'])
    row.update({key: slot[key] for key in ('scenario', 'block', 'profile_position', 'model_position')})
    return row


def aggregate(rows):
    result = []
    for scenario in FIXTURES:
        selected = [row for row in rows if row['scenario'] == scenario]
        result.extend(dict(item, scenario=scenario) for item in aggregate_models(selected))
    return result


def verify_comparison(batch, states):
    fields = {'suite_version', 'kind', 'started_utc', 'repeat', 'fixtures', 'profiles',
              'models', 'modes', 'endpoint', 'treatments', 'source_revision', 'source_dirty',
              'source_sha256', 'rows', 'summary'}
    if (set(batch) != fields or batch['suite_version'] != 1 or batch['kind'] != 'varied_discovery'
            or type(batch['repeat']) is not int or batch['repeat'] < 1
            or batch['fixtures'] != list(FIXTURES) or batch['profiles'] != list(PROFILE_NAMES)
            or batch['models'] != list(MODELS) or batch['modes'] != list(MODES)
            or batch['endpoint'] != ENDPOINT):
        raise ValueError('Invalid discovery suite plan')
    treatments = {name: dict(experiment_controls(PROFILES[name]), limits=PROFILES[name].limits)
                  for name in PROFILE_NAMES}
    if batch['treatments'] != treatments:
        raise ValueError('Suite treatments differ')
    if (not re.fullmatch(r'[0-9]{8}T[0-9]{6}Z', batch['started_utc'])
            or (batch['source_revision'] is not None and not re.fullmatch(r'[0-9a-f]{40,64}', batch['source_revision']))
            or (batch['source_dirty'] is not None and type(batch['source_dirty']) is not bool)
            or not isinstance(batch['source_sha256'], dict)
            or any(not re.fullmatch(r'[a-z_]+\.py', k) or not re.fullmatch(r'[0-9a-f]{64}', v)
                   for k, v in batch['source_sha256'].items())):
        raise ValueError('Invalid suite provenance')
    expected = plan(batch['repeat'])
    ids = [row['run_id'] for row in batch['rows']]
    if (len(expected) != len(ids) or len(set(ids)) != len(ids) or set(ids) != set(states)
            or batch['summary'] != aggregate(batch['rows'])):
        raise ValueError('Incomplete or inconsistent suite inventory')
    for row, slot in zip(batch['rows'], expected):
        state = states[row['run_id']]
        if state['config'] != config_for(slot):
            raise ValueError('Suite run configuration differs from planned treatment')
        if state['status'] not in ('completed', 'stopped') or state.get('inflight_model'):
            raise ValueError('Suite contains an active run')
        messages = state['messages']
        if messages:
            if messages[:2] != state['config']['initial_messages']:
                raise ValueError('Suite executed prompt differs')
        elif state['requests'] or state['model_calls'] or state['status'] != 'stopped':
            raise ValueError('Executed suite run lacks initial prompt')
        for diagnostic in state.get('diagnostics', []):
            validate_diagnostic(diagnostic)
            if diagnostic.get('model_call', 0) > state['model_calls']:
                raise ValueError('Diagnostic exceeds reserved suite calls')
        if row != suite_row(state, slot):
            raise ValueError('Suite row differs from saved state or execution order')
    return ids


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repeat', type=positive, default=1,
                        help='One gives a 72-run pilot; three counterbalances order within each fixture/mode')
    parser.add_argument('--directory', type=Path, required=True)
    args = parser.parse_args(argv)
    args.directory.mkdir(parents=True, exist_ok=False)
    database = args.directory / 'runs.sqlite3'
    metadata = dict(suite_version=1, kind='varied_discovery',
                    started_utc=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'),
                    repeat=args.repeat, fixtures=list(FIXTURES), profiles=list(PROFILE_NAMES),
                    models=list(MODELS), modes=list(MODES), endpoint=ENDPOINT,
                    treatments={name: dict(experiment_controls(PROFILES[name]), limits=PROFILES[name].limits)
                                for name in PROFILE_NAMES}, **source_provenance())
    rows = []
    def checkpoint():
        path = args.directory / 'comparison.json'
        temporary = path.with_suffix('.tmp')
        temporary.write_text(json.dumps(dict(metadata, rows=rows, summary=aggregate(rows)), indent=2) + '\n')
        temporary.replace(path)
    with open(str(database) + '.lock', 'x') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        store = Store(database)
        try:
            checkpoint()
            for slot in plan(args.repeat):
                state = store.create(config_for(slot))
                print(json.dumps(dict(event='started', run_id=state['id'], **slot)), flush=True)
                try:
                    provider = Ollama(slot['model']) if state['config']['backend'] == 'ollama' else None
                    with lab(slot['mode'], slot['scenario']) as origin:
                        investigate(store, state, origin, provider)
                except Exception:
                    state.update(status='stopped', reason='Comparison setup failed; run retained')
                    state.setdefault('diagnostics', []).append(dict(source='harness', category='unknown'))
                    store.save(state)
                write_report(state, args.directory / 'reports')
                row = suite_row(state, slot)
                rows.append(row)
                checkpoint()
                print(json.dumps(dict(event='finished', **row)), flush=True)
            states = {row['run_id']: store.load(row['run_id']) for row in rows}
            verify_comparison(dict(metadata, rows=rows, summary=aggregate(rows)), states)
        finally:
            store.close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
