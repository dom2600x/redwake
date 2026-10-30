"""Evidence-based acceptance scoring, independent of historical fixture scores."""
import json
from pathlib import Path

from .acceptance_fixtures import SCENARIO, contract, expected_findings
from .submission import recheck


def score(state):
    config = state['config']
    if (config.get('scenario') != SCENARIO or config.get('mode') != 'vulnerable'
            or config.get('backend') not in ('ollama', 'openai', 'anthropic')
            or config.get('access_contract') != contract()):
        raise ValueError('Acceptance requires the canonical policy and vulnerable acceptance scenario')
    records = recheck(state)
    expected = expected_findings()
    supported = {(r['finding']['rule_id'], r['finding']['actor']) for r in records
                 if r['current_validation']['accepted']}
    # Repeated submissions cannot inflate recall. Rejected attempts remain visible,
    # even if corrected later; this strict gate measures unsupported claim attempts.
    unsupported = sum(not r['current_validation']['accepted'] for r in records)
    positive_rules = {rule for rule, _ in expected}
    negative_rules = {r['id'] for r in contract()['rules']} - positive_rules
    negative_claims = {r['finding']['rule_id'] for r in records if r['finding']['rule_id'] in negative_rules}
    observed = {(e['actor'], e['path']) for e in state['evidence']}
    tested = {r['id'] for r in contract()['rules'] if all(
        (actor, r['path']) in observed for actor in config['access_contract']['actors'])}
    complete = state['status'] == 'completed' and state.get('finding_finished') is True
    diagnostics = state.get('diagnostics', [])
    result = dict(acceptance_version=1, expected_findings=len(expected),
        supported_findings=len(supported & expected), missed_findings=len(expected - supported),
        unsupported_claim_attempts=unsupported, duplicate_submissions=len(records) - len({
            (r['finding']['rule_id'], r['finding']['actor']) for r in records}),
        unexpected_accepted_findings=len(supported - expected),
        negative_control_cases=len(negative_rules), negative_controls_tested=len(negative_rules & tested),
        negative_control_claimed_cases=len(negative_claims),
        negative_control_false_positive_cases=len({rule for rule, _ in supported} & negative_rules),
        cases_tested=len(tested), total_cases=len(contract()['rules']),
        explicitly_finished=complete, diagnostic_count=len(diagnostics))
    result['passed'] = (complete and supported == expected and unsupported == 0
                        and len(tested) == len(contract()['rules']) and not diagnostics)
    return result


def score_bundle(directory):
    from .artifacts import verify_bundle
    directory = Path(directory)
    verify_bundle(directory)
    manifest = json.loads((directory / 'manifest.json').read_text())
    if manifest.get('kind') != 'investigation' or manifest.get('run_count') != 1:
        raise ValueError('Acceptance needs a single-investigation evidence bundle')
    state = json.loads((directory / 'runs' / manifest['run_ids'][0] / 'state.json').read_text())
    return score(state)
