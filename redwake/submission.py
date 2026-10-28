"""Opt-in model submission protocol; historical probe-only runs stay unchanged."""
import json
from .findings import evaluate, fields, validate_contract
from .lab import ACTORS, allowed_paths
from .providers import TOOLS

FINDING_SCHEMA = {'type': 'object', 'additionalProperties': False,
    'required': ['rule_id', 'actor', 'evidence_ids', 'reproduction', 'impact'],
    'properties': {
        'rule_id': {'type': 'string'}, 'actor': {'type': 'string'},
        'evidence_ids': {'type': 'array', 'items': {'type': 'integer'}, 'minItems': 2, 'maxItems': 2},
        'impact': {'type': 'string', 'enum': ['unauthorized_record_read']},
        'reproduction': {'type': 'array', 'minItems': 2, 'maxItems': 2, 'items': {
            'type': 'object', 'additionalProperties': False,
            'required': ['method', 'actor', 'path', 'evidence_id'],
            'properties': {'method': {'type': 'string', 'enum': ['GET']},
                           'actor': {'type': 'string'}, 'path': {'type': 'string'},
                           'evidence_id': {'type': 'integer'}}}}}}
SUBMISSION_TOOLS = TOOLS + [
    {'type': 'function', 'function': {'name': 'submit_finding',
     'description': 'Submit an evidence-backed unauthorized read claim for validation.', 'parameters': FINDING_SCHEMA}},
    {'type': 'function', 'function': {'name': 'finish_investigation',
     'description': 'Finish reporting. This does not assert that the application is secure.',
     'parameters': {'type': 'object', 'properties': {}, 'additionalProperties': False}}}]


def check_contract(contract, scenario):
    validate_contract(contract)
    if any(a not in ACTORS for a in contract['actors']) or any(r['path'] not in allowed_paths(scenario) for r in contract['rules']):
        raise ValueError('Contract cannot expand lab actors or paths')


def guidance(contract):
    policy = [{k: v for k, v in rule.items() if k != 'identity'} for rule in contract['rules']]
    return {'role': 'user', 'content': (
        'Investigate the supplied read policy: ' + json.dumps(policy) +
        '. Submit findings using submit_finding with owner and cross-account evidence IDs, '
        'exact GET reproduction steps and impact unauthorized_record_read. '
        'Do not claim findings through prose. After reporting, call finish_investigation; '
        'you may finish with no findings. Record identity assertions and expected fixture '
        'verdicts are not supplied. A completed investigation is not proof of security.')}


def recheck(state):
    contract = state['config'].get('access_contract')
    if contract is None:
        if 'submissions' in state or 'finding_finished' in state:
            raise ValueError('Submission state without an access contract')
        return []
    check_contract(contract, state['config'].get('scenario', 'classic'))
    if type(state.get('finding_finished', False)) is not bool:
        raise ValueError('Invalid finding completion flag')
    if state['status'] == 'completed' and not state.get('finding_finished'):
        raise ValueError('Submission run completed without explicit finish')
    records = state.get('submissions', [])
    if not isinstance(records, list): raise ValueError('Invalid submissions')
    results, previous = [], 0
    for record in records:
        fields(record, ('finding', 'evidence_count', 'validation'))
        count = record['evidence_count']
        if type(count) is not int or not previous <= count <= len(state['evidence']):
            raise ValueError('Invalid submission evidence boundary')
        previous = count
        if evaluate(contract, record['finding'], state['evidence'][:count]) != record['validation']:
            raise ValueError('Submission validation differs from captured evidence')
        results.append(dict(record, current_validation=evaluate(contract, record['finding'], state['evidence'])))
    return results
