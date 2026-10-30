"""Direct synchronous Anthropic estimates with disjoint cache categories."""
from decimal import Decimal
from .costs import money, value
from .anthropic_usage import API_VERSION

RATES = ('input', 'cached_input', 'cache_write_5m', 'cache_write_1h', 'output')


def validate_card(card, config):
    fields = {'version', 'provider', 'model', 'currency', 'source', 'as_of',
              'context_threshold', 'long_input_multiplier', 'long_output_multiplier',
              'service_tier', 'api_version', 'processing_mode', 'inference_geo', *RATES}
    if set(card) != fields: raise ValueError('Invalid Anthropic rate card')
    if (card['provider'] != 'anthropic' or card['model'] != config.get('model')
            or config.get('backend') != 'anthropic' or config.get('endpoint') != 'https://api.anthropic.com'
            or type(config.get('usage_version')) is not int or config['usage_version'] != 2
            or card['currency'] != 'USD' or card['service_tier'] != 'standard'
            or card['api_version'] != API_VERSION or card['processing_mode'] != 'synchronous'
            or card['inference_geo'] != 'global'):
        raise ValueError('Anthropic pricing requires matching direct standard global execution')
    if type(card['context_threshold']) is not int or card['context_threshold'] <= 0:
        raise ValueError('A positive context threshold is required')
    for key in RATES: money(card[key])
    for key in ('long_input_multiplier', 'long_output_multiplier'):
        if money(card[key]) < 1: raise ValueError('Context multipliers must be at least one')


def reservation(policy, output_limit):
    card = policy['rate_card']
    rate = max(money(card[key]) for key in RATES if key != 'output')
    return (Decimal(policy['input_token_reservation']) * rate * money(card['long_input_multiplier'])
            / Decimal(1000000) + value(output_limit, card['output']) * money(card['long_output_multiplier']))


def summary(state):
    policy = state['config']['cost_policy']; card = policy['rate_card']
    minimum = Decimal(0); exposure = Decimal(0); uncertain = 0
    entries = state.get('cost_ledger', [])
    for entry in entries:
        record = state['usage_ledger'][entry['call'] - 1]
        reserved = money(entry['reservation_usd'])
        if (record['model'] != card['model'] or record['service_tier'] != card['service_tier']
                or record['api_version'] != card['api_version']):
            exposure += reserved; uncertain += 1
            continue
        total = record['input_tokens']
        known_input = sum(record[key] or 0 for key in
                          ('uncached_input_tokens', 'cached_input_tokens', 'cache_creation_input_tokens'))
        long = known_input > card['context_threshold']
        low_multiplier = money(card['long_input_multiplier']) if long else Decimal(1)
        high_multiplier = money(card['long_input_multiplier']) if long or total is None else Decimal(1)
        low = Decimal(0); high = Decimal(0)
        for field, rate in (('uncached_input_tokens', 'input'), ('cached_input_tokens', 'cached_input')):
            if record[field] is not None:
                charge = value(record[field], card[rate]); low += charge; high += charge
        creation = record['cache_creation_input_tokens']
        split = record['cache_creation_5m_tokens'] is not None
        if split:
            charge = (value(record['cache_creation_5m_tokens'], card['cache_write_5m'])
                      + value(record['cache_creation_1h_tokens'], card['cache_write_1h']))
            low += charge; high += charge
        elif creation is not None:
            rates = [money(card[k]) for k in ('cache_write_5m', 'cache_write_1h')]
            low += Decimal(creation) * min(rates) / Decimal(1000000)
            high += Decimal(creation) * max(rates) / Decimal(1000000)
        low *= low_multiplier; high *= high_multiplier
        outputs = record['output_tokens']
        if outputs is not None:
            charge = value(outputs, card['output'])
            low += charge * (money(card['long_output_multiplier']) if long else Decimal(1))
            high += charge * (money(card['long_output_multiplier']) if long or total is None else Decimal(1))
        complete = total is not None and outputs is not None
        exact = complete and low == high
        minimum += low
        exposure += high if complete else max(reserved, high)
        uncertain += not exact
    return dict(currency='USD', billing_context=policy['billing_context'],
        calculated_usage_value_usd=str(minimum) if not uncertain else None,
        known_minimum_usd=str(minimum), estimated_exposure_usd=str(exposure),
        cash_charge_usd=None, provider_reconciled=False, budget_is_estimate=True,
        unknown_usage_calls=sum(e['input_tokens'] is None or e['output_tokens'] is None for e in entries),
        uncertain_valuation_calls=uncertain,
        model_identity_verified=bool(entries) and all(e['served_model'] == card['model'] for e in entries),
        model_mismatch_calls=sum(e['served_model'] not in (None, card['model']) for e in entries))
