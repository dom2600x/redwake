"""Standard direct OpenAI rate-card estimates; no provider billing reconciliation."""
from decimal import Decimal

from .costs import money, value


def validate_card(card, config):
    if type(config.get('usage_version')) is not int or config['usage_version'] != 1 or card['service_tier'] != 'default':
        raise ValueError('OpenAI pricing requires versioned usage and default service')
    if card['cache_write_pricing'] != 'replacement':
        raise ValueError('Only replacement cache-write rates are supported')
    if type(card['context_threshold']) is not int or card['context_threshold'] <= 0:
        raise ValueError('A positive context threshold is required')
    for key in ('cached_input', 'cache_write_30m', 'cache_write_12h'):
        money(card[key])
    for key in ('long_input_multiplier', 'long_output_multiplier'):
        if money(card[key]) < 1: raise ValueError('Context multipliers must be at least one')


def input_rates(card):
    return [money(card[key]) for key in ('input', 'cache_write_30m', 'cache_write_12h')]


def reservation(policy, output_limit):
    card = policy['rate_card']
    # Input is an estimate rather than an enforced limit. Reserve the long tier
    # even for small estimated contexts, including the highest cache-write rate.
    rate = max(input_rates(card) + [money(card['cached_input'])])
    return (Decimal(policy['input_token_reservation']) * rate * money(card['long_input_multiplier'])
            / Decimal(1000000) + value(output_limit, card['output']) * money(card['long_output_multiplier']))


def summary(state):
    policy = state['config']['cost_policy']; card = policy['rate_card']
    minimum = Decimal(0); exposure = Decimal(0); uncertain = 0
    entries = state.get('cost_ledger', [])
    usage = state.get('usage_ledger', [])
    for entry in entries:
        record = usage[entry['call'] - 1]
        reserved = money(entry['reservation_usd'])
        if record['model'] != card['model'] or record['service_tier'] != 'default':
            exposure += reserved; uncertain += 1
            continue
        inputs, outputs = record['input_tokens'], record['output_tokens']
        cached = record['cached_input_tokens']
        long = inputs is not None and inputs > card['context_threshold']
        input_low = money(card['long_input_multiplier']) if long else Decimal(1)
        output_low = money(card['long_output_multiplier']) if long else Decimal(1)
        input_high = money(card['long_input_multiplier']) if inputs is None or long else Decimal(1)
        output_high = money(card['long_output_multiplier']) if inputs is None or long else Decimal(1)
        low = Decimal(0); high = Decimal(0)
        if inputs is not None:
            rates = input_rates(card)
            if cached is None:
                rates.append(money(card['cached_input']))
                low += Decimal(inputs) * min(rates) * input_low / Decimal(1000000)
                high += Decimal(inputs) * max(rates) * input_high / Decimal(1000000)
            else:
                reads = value(cached, card['cached_input'])
                low += (reads + Decimal(inputs - cached) * min(rates) / Decimal(1000000)) * input_low
                high += (reads + Decimal(inputs - cached) * max(rates) / Decimal(1000000)) * input_high
        if outputs is not None:
            # Reasoning is a subset of output_tokens, never an extra charge here.
            low += value(outputs, card['output']) * output_low
            high += value(outputs, card['output']) * output_high
        minimum += low
        exposure += max(reserved, high) if inputs is None or outputs is None else high
        # Cache writes are not separately reported by the adapter; never present
        # the rate-card calculation as an exact bill, even with complete totals.
        uncertain += 1
    return dict(currency='USD', billing_context=policy['billing_context'],
        calculated_usage_value_usd=None, known_minimum_usd=str(minimum),
        estimated_exposure_usd=str(exposure), cash_charge_usd=None,
        provider_reconciled=False, budget_is_estimate=True,
        unknown_usage_calls=sum(e['input_tokens'] is None or e['output_tokens'] is None for e in entries),
        uncertain_valuation_calls=uncertain,
        model_identity_verified=bool(entries) and all(e['served_model'] == card['model'] for e in entries),
        model_mismatch_calls=sum(e['served_model'] not in (None, card['model']) for e in entries))
