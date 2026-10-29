"""Decimal rate-card valuation; provider billing and unknown usage stay distinct."""
from decimal import Decimal, InvalidOperation
from datetime import datetime, timezone
import re


def money(value):
    if not isinstance(value, str): raise ValueError('Money must be a decimal string')
    try: result = Decimal(value)
    except InvalidOperation: raise ValueError('Invalid money') from None
    if not result.is_finite() or result < 0: raise ValueError('Invalid money')
    return result


def validate_policy(policy, config):
    if not isinstance(policy, dict): raise ValueError('Invalid cost policy')
    if set(policy) != {'rate_card', 'billing_context', 'max_cost_usd', 'input_token_reservation'}:
        raise ValueError('Invalid cost policy')
    card = policy['rate_card']
    if not isinstance(card, dict): raise ValueError('Invalid rate card')
    openai = card.get('version') == 2
    extra = {'cache_write_30m', 'cache_write_12h', 'context_threshold',
             'long_input_multiplier', 'long_output_multiplier', 'service_tier',
             'cache_write_pricing'} if openai else set()
    if set(card) != {'version', 'provider', 'model', 'currency', 'source', 'as_of', 'input', 'cached_input', 'output'} | extra:
        raise ValueError('Invalid rate card')
    provider = 'openai' if openai else 'ollama'
    endpoint = 'https://api.openai.com' if openai else 'https://ollama.com'
    if (card['version'] not in (1, 2) or type(card['version']) is not int or card['provider'] != provider
            or card['model'] != config.get('model') or card['currency'] != 'USD'
            or config.get('backend') != provider or config.get('endpoint') != endpoint):
        raise ValueError('Rate card must match the cloud provider and model')
    if openai:
        from .openai_costs import validate_card
        validate_card(card, config)
    if not all(isinstance(card[k], str) and card[k] for k in ('source', 'as_of')):
        raise ValueError('Pricing provenance required')
    for key in ('input', 'output'): money(card[key])
    if card['cached_input'] is not None: money(card['cached_input'])
    if policy['billing_context'] not in ('free', 'included', 'purchased', 'unknown'):
        raise ValueError('Invalid billing context')
    if policy['max_cost_usd'] is not None: money(policy['max_cost_usd'])
    if type(policy['input_token_reservation']) is not int or policy['input_token_reservation'] <= 0:
        raise ValueError('Input reservation must be positive')


def value(tokens, rate):
    return Decimal(tokens) * money(rate) / Decimal(1000000)


def reservation(policy, output_limit):
    card = policy['rate_card']
    if card['version'] == 2:
        from .openai_costs import reservation as openai_reservation
        return openai_reservation(policy, output_limit)
    # Unknown cache split: reserve at the highest declared input rate.
    input_rate = max(money(card['input']), money(card['cached_input'] or card['input']))
    return Decimal(policy['input_token_reservation']) * input_rate / Decimal(1000000) + value(output_limit, card['output'])


def summary(state):
    policy = state['config']['cost_policy']; validate_policy(policy, state['config'])
    if policy['rate_card']['version'] == 2:
        from .openai_costs import summary as openai_summary
        return openai_summary(state)
    card = policy['rate_card']; minimum = Decimal(0); exposure = Decimal(0); exact = True
    for entry in state.get('cost_ledger', []):
        if entry.get('served_model') not in (None, card['model']):
            exposure += money(entry['reservation_usd']); exact = False
            continue
        known = Decimal(0); upper = Decimal(0); complete = True
        inputs, outputs = entry['input_tokens'], entry['output_tokens']
        if inputs is None: complete = False
        else:
            rates = [money(card['input'])]
            if card['cached_input'] is not None: rates.append(money(card['cached_input']))
            else: rates.append(Decimal(0))
            known += Decimal(inputs) * min(rates) / Decimal(1000000)
            upper += Decimal(inputs) * max(rates) / Decimal(1000000)
        if outputs is None: complete = False
        else:
            known += value(outputs, card['output']); upper += value(outputs, card['output'])
        minimum += known
        exposure += max(upper, money(entry['reservation_usd'])) if not complete else upper
        exact = exact and complete and known == upper
    return dict(currency='USD', billing_context=policy['billing_context'],
                calculated_usage_value_usd=str(minimum) if exact else None,
                known_minimum_usd=str(minimum), estimated_exposure_usd=str(exposure),
                unknown_usage_calls=sum(e['input_tokens'] is None or e['output_tokens'] is None for e in state.get('cost_ledger', [])),
                cash_charge_usd=None, provider_reconciled=False,
                model_identity_verified=bool(state.get('cost_ledger')) and all(e.get('served_model') == card['model'] for e in state.get('cost_ledger', [])),
                model_mismatch_calls=sum(e.get('served_model') not in (None, card['model']) for e in state.get('cost_ledger', [])),
                budget_is_estimate=True)


def reserve(state, output_limit):
    policy = state['config']['cost_policy']; amount = reservation(policy, output_limit)
    limit = policy['max_cost_usd']
    if limit is not None and money(summary(state)['estimated_exposure_usd']) + amount > money(limit):
        return False
    state.setdefault('cost_ledger', []).append(dict(call=state['model_calls'] + 1,
        started_utc=datetime.now(timezone.utc).isoformat(), served_model=None, status='reserved', output_limit=output_limit, reservation_usd=str(amount), input_tokens=None, output_tokens=None))
    return True


def received(state, response):
    entry = state['cost_ledger'][-1]
    entry['status'] = 'reported'
    model = response.get('model')
    entry['served_model'] = model if isinstance(model, str) and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9:._/-]{0,127}', model) else None
    for source, key in (('prompt_eval_count', 'input_tokens'), ('eval_count', 'output_tokens')):
        n = response.get(source)
        entry[key] = n if type(n) is int and n >= 0 else None


def interrupted(state):
    entries = state.get('cost_ledger', [])
    if entries and entries[-1]['status'] == 'reserved': entries[-1]['status'] = 'unknown'


def recheck(state):
    if 'cost_policy' not in state['config']:
        if 'cost_ledger' in state: raise ValueError('Ledger without pricing policy')
        return None
    policy = state['config']['cost_policy']; validate_policy(policy, state['config'])
    if policy['rate_card']['version'] == 2:
        from .usage import recheck as recheck_usage
        recheck_usage(state)
    entries = state.get('cost_ledger', [])
    if not isinstance(entries, list) or len(entries) != state['model_calls']:
        raise ValueError('Cost ledger differs from model calls')
    for i, entry in enumerate(entries, 1):
        if set(entry) != {'call', 'started_utc', 'served_model', 'status', 'output_limit', 'reservation_usd', 'input_tokens', 'output_tokens'}:
            raise ValueError('Invalid cost ledger fields')
        if (type(entry['call']) is not int or entry['call'] != i or entry['status'] not in ('reported', 'unknown')
                or type(entry['output_limit']) is not int or not 1 <= entry['output_limit'] <= 1024
                or money(entry['reservation_usd']) != reservation(policy, entry['output_limit'])):
            raise ValueError('Invalid call reservation')
        if entry['served_model'] is not None and (not isinstance(entry['served_model'], str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9:._/-]{0,127}', entry['served_model'])):
            raise ValueError('Invalid served model identifier')
        timestamp = datetime.fromisoformat(entry['started_utc'])
        if timestamp.utcoffset() != timezone.utc.utcoffset(timestamp): raise ValueError('Call timestamp must use UTC')
        for key in ('input_tokens', 'output_tokens'):
            if entry[key] is not None and (type(entry[key]) is not int or entry[key] < 0):
                raise ValueError('Invalid reported token count')
        if entry['status'] == 'unknown' and any(entry[k] is not None for k in ('input_tokens','output_tokens')):
            raise ValueError('Unknown call contains reported usage')
    if sum(e['output_limit'] for e in entries) != state['reserved_output_tokens']:
        raise ValueError('Output reservations differ from ledger')
    for key in ('input_tokens', 'output_tokens'):
        if sum(e[key] or 0 for e in entries) != state[key]: raise ValueError('Usage totals differ from ledger')
    if any(e[k] is None for e in entries for k in ('input_tokens','output_tokens')) and state['usage_complete']:
        raise ValueError('Incomplete usage marked complete')
    return summary(state)
