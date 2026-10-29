"""Anthropic's disjoint input categories, retained by usage contract version 2."""
from .usage import count, identifier

API_VERSION = '2023-06-01'
COUNTS = ('input_tokens', 'output_tokens', 'cached_input_tokens', 'reasoning_tokens',
          'uncached_input_tokens', 'cache_creation_input_tokens',
          'cache_creation_5m_tokens', 'cache_creation_1h_tokens')
STOP_REASONS = ('end_turn', 'tool_use', 'max_tokens', 'pause_turn', 'refusal', 'unknown')


def empty():
    return dict(model=None, response_status='unknown', service_tier='unknown',
                api_version=API_VERSION, stop_reason='unknown', **{key: None for key in COUNTS})


def normalize(response):
    result = empty()
    result['model'] = identifier(response.get('model'))
    stop = response.get('stop_reason')
    if stop in STOP_REASONS: result['stop_reason'] = stop
    if stop in ('end_turn', 'tool_use'): result['response_status'] = 'completed'
    elif stop in ('max_tokens', 'pause_turn'): result['response_status'] = 'incomplete'
    elif stop == 'refusal': result['response_status'] = 'failed'
    usage = response.get('usage')
    if not isinstance(usage, dict): return result
    for source, target in (('input_tokens', 'uncached_input_tokens'), ('output_tokens', 'output_tokens'),
                           ('cache_creation_input_tokens', 'cache_creation_input_tokens'),
                           ('cache_read_input_tokens', 'cached_input_tokens')):
        result[target] = count(usage.get(source))
    if usage.get('service_tier') in ('standard', 'priority', 'batch'):
        result['service_tier'] = usage['service_tier']
    parts = [result[key] for key in ('uncached_input_tokens', 'cache_creation_input_tokens', 'cached_input_tokens')]
    if all(part is not None for part in parts): result['input_tokens'] = sum(parts)
    creation = usage.get('cache_creation')
    if isinstance(creation, dict):
        five = count(creation.get('ephemeral_5m_input_tokens'))
        hour = count(creation.get('ephemeral_1h_input_tokens'))
        if five is not None and hour is not None and five + hour == result['cache_creation_input_tokens']:
            result.update(cache_creation_5m_tokens=five, cache_creation_1h_tokens=hour)
    return result


def validate(record):
    if set(record) != set(empty()): raise ValueError('Invalid Anthropic usage fields')
    if (record['api_version'] != API_VERSION or record['stop_reason'] not in STOP_REASONS
            or record['service_tier'] not in ('standard', 'priority', 'batch', 'unknown')
            or record['reasoning_tokens'] is not None):
        raise ValueError('Invalid Anthropic usage metadata')
    expected = ('completed' if record['stop_reason'] in ('end_turn', 'tool_use') else
                'incomplete' if record['stop_reason'] in ('max_tokens', 'pause_turn') else
                'failed' if record['stop_reason'] == 'refusal' else 'unknown')
    if record['response_status'] != expected: raise ValueError('Inconsistent Anthropic stop reason')
    parts = [record[key] for key in ('uncached_input_tokens', 'cache_creation_input_tokens', 'cached_input_tokens')]
    total = sum(parts) if all(part is not None for part in parts) else None
    if record['input_tokens'] != total: raise ValueError('Anthropic input total differs from categories')
    five, hour = record['cache_creation_5m_tokens'], record['cache_creation_1h_tokens']
    if (five is None) != (hour is None) or (five is not None and five + hour != record['cache_creation_input_tokens']):
        raise ValueError('Anthropic cache retention split differs from creation total')
