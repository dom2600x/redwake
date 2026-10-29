"""Versioned, allowlisted per-call usage, independent of pricing and cash billing."""
from datetime import datetime, timezone
import re


COUNTS = ('input_tokens', 'output_tokens', 'cached_input_tokens', 'reasoning_tokens')
STATUSES = ('completed', 'incomplete', 'failed', 'unknown')
TIERS = ('default', 'flex', 'priority', 'scale', 'auto', 'unknown')


def count(value):
    return value if type(value) is int and value >= 0 else None


def identifier(value):
    return value if isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9:._/-]{0,127}', value) else None


def normalize(backend, response):
    """Totals include subsets: never add cached input or reasoning a second time."""
    if backend == 'anthropic':
        from .anthropic_usage import normalize as normalize_anthropic
        return normalize_anthropic(response)
    result = dict(model=identifier(response.get('model')), response_status='unknown',
                  service_tier='unknown', **{key: None for key in COUNTS})
    if backend == 'ollama':
        result.update(input_tokens=count(response.get('prompt_eval_count')),
                      output_tokens=count(response.get('eval_count')))
        if response.get('done') is True:
            result['response_status'] = 'completed'
    elif backend == 'openai':
        usage = response.get('usage')
        if isinstance(usage, dict):
            for key in ('input_tokens', 'output_tokens'):
                result[key] = count(usage.get(key))
            for source, key in (('input_tokens_details', 'cached_input_tokens'),
                                ('output_tokens_details', 'reasoning_tokens')):
                detail = usage.get(source)
                field = 'cached_tokens' if key == 'cached_input_tokens' else key
                if isinstance(detail, dict): result[key] = count(detail.get(field))
            for total, subset in (('input_tokens', 'cached_input_tokens'), ('output_tokens', 'reasoning_tokens')):
                if result[total] is None or (result[subset] is not None and result[subset] > result[total]):
                    result[subset] = None
        if response.get('status') in STATUSES: result['response_status'] = response['status']
        if response.get('service_tier') in TIERS: result['service_tier'] = response['service_tier']
    else:
        raise ValueError('Unsupported usage provider')
    return result


def empty_record(config):
    version = config.get('usage_version')
    if type(version) is not int or (version, config['backend']) not in ((1, 'ollama'), (1, 'openai'), (2, 'anthropic')):
        raise ValueError('Unsupported usage contract')
    if version == 2:
        from .anthropic_usage import empty
        return empty()
    return dict(model=None, response_status='unknown', service_tier='unknown', **{key: None for key in COUNTS})


def begin(state, output_limit):
    state.setdefault('usage_ledger', []).append(dict(call=state['model_calls'] + 1,
        started_utc=datetime.now(timezone.utc).isoformat(), status='reserved',
        output_limit=output_limit, **empty_record(state['config'])))


def received(state, response):
    # Direct adapters supply already normalized, strictly allowlisted metadata.
    record = (response['provider_usage'] if state['config']['backend'] in ('openai', 'anthropic')
              else normalize('ollama', response))
    validate_record(record, state['config']['usage_version'])
    state['usage_ledger'][-1].update(record, status='reported')


def interrupted(state):
    entries = state.get('usage_ledger', [])
    if entries and entries[-1]['status'] == 'reserved': entries[-1]['status'] = 'unknown'


def validate_record(record, version=1):
    if type(version) is not int or version not in (1, 2):
        raise ValueError('Unsupported usage contract')
    if version == 2:
        from .anthropic_usage import COUNTS as counts, empty, validate
        if not isinstance(record, dict) or set(record) != set(empty()):
            raise ValueError('Invalid normalized provider usage')
    else:
        counts = COUNTS
    if version != 2 and (not isinstance(record, dict) or set(record) != {'model', 'response_status', 'service_tier', *COUNTS}):
        raise ValueError('Invalid normalized provider usage')
    if (record['model'] is not None and identifier(record['model']) != record['model']
            or record['response_status'] not in STATUSES or (version != 2 and record['service_tier'] not in TIERS)):
        raise ValueError('Invalid provider usage metadata')
    for key in counts:
        if record[key] is not None and count(record[key]) is None: raise ValueError('Invalid usage count')
    if version == 2:
        validate(record)
    for total, subset in (() if version == 2 else (('input_tokens', 'cached_input_tokens'), ('output_tokens', 'reasoning_tokens'))):
        if record[subset] is not None and (record[total] is None or record[subset] > record[total]):
            raise ValueError('Invalid usage subset')


def recheck(state):
    if 'usage_version' not in state['config']:
        if 'usage_ledger' in state or state['config']['backend'] in ('openai', 'anthropic'):
            raise ValueError('Missing usage contract version')
        return None
    empty = empty_record(state['config'])
    entries = state.get('usage_ledger', [])
    if not isinstance(entries, list) or len(entries) != state['model_calls']: raise ValueError('Usage ledger differs from model calls')
    for number, entry in enumerate(entries, 1):
        if not isinstance(entry, dict) or set(entry) != {'call', 'started_utc', 'status', 'output_limit'} | set(empty):
            raise ValueError('Invalid usage ledger')
        if (type(entry['call']) is not int or entry['call'] != number or entry['status'] not in ('reported', 'unknown')
                or type(entry['output_limit']) is not int or not 1 <= entry['output_limit'] <= 1024):
            raise ValueError('Invalid usage reservation')
        if not isinstance(entry['started_utc'], str): raise ValueError('Invalid usage timestamp')
        timestamp = datetime.fromisoformat(entry['started_utc'])
        if timestamp.utcoffset() != timezone.utc.utcoffset(timestamp): raise ValueError('Usage timestamp must use UTC')
        record = {key: entry[key] for key in empty}
        validate_record(record, state['config']['usage_version'])
        if entry['status'] == 'unknown' and record != empty:
            raise ValueError('Unknown call contains reported usage')
    if sum(entry['output_limit'] for entry in entries) != state['reserved_output_tokens']:
        raise ValueError('Usage output reservations differ')
    for key in ('input_tokens', 'output_tokens'):
        if sum(entry[key] or 0 for entry in entries) != state[key]: raise ValueError('Usage totals differ')
    if 'cost_policy' in state['config']:
        costs = state.get('cost_ledger', [])
        if len(costs) != len(entries) or any(
                any(cost.get(key) != entry[key] for key in ('input_tokens', 'output_tokens', 'output_limit', 'status'))
                or cost.get('served_model') != entry['model'] for cost, entry in zip(costs, entries)):
            raise ValueError('Cost and usage ledgers differ')
    if state['usage_complete'] and any(entry[key] is None for entry in entries for key in ('input_tokens', 'output_tokens')):
        raise ValueError('Incomplete usage marked complete')
    return entries
