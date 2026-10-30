import copy
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from redwake.acceptance import score, score_bundle
from redwake.acceptance_fixtures import SCENARIO, RESOURCES, contract, expected_findings
from redwake.artifacts import export_run, verify_bundle
from redwake.cli import main
from redwake.findings import evaluate
from redwake.lab import lab
from redwake.providers import initial_messages
from redwake.runner import DISCOVERY_LIMITS, investigate
from redwake.store import Store
from redwake.submission import guidance


def call(name, arguments):
    return dict(function=dict(name=name, arguments=arguments))


def claim(rule, ids, actor=None):
    actor = actor or ('bob' if rule['owner'] == 'alice' else 'alice')
    return dict(rule_id=rule['id'], actor=actor, evidence_ids=ids,
                reproduction=[dict(method='GET', actor=a, path=rule['path'], evidence_id=i)
                              for a, i in zip((rule['owner'], actor), ids)], impact='unauthorized_record_read')


class ScriptedControl:
    """Deterministic test control, never evidence of model capability."""
    def __init__(self, mode='supported'):
        self.turn = 0; self.mode = mode

    def chat(self, messages, *args):
        probes = [call('probe', dict(actor=a, path=r['path'])) for r in contract()['rules'] for a in ('alice', 'bob')]
        if self.turn < 2:
            calls = probes[self.turn * 12:(self.turn + 1) * 12]
        else:
            evidence = [json.loads(m['content']) for m in messages if m['role'] == 'tool' and m['tool_name'] == 'probe']
            calls = []
            for rule in contract()['rules']:
                actor = 'bob' if rule['owner'] == 'alice' else 'alice'
                if self.mode == 'silent' or (self.mode == 'supported' and (rule['id'], actor) not in expected_findings()):
                    continue
                ids = [next(e['id'] for e in evidence if e['actor'] == a and e['path'] == rule['path'])
                       for a in (rule['owner'], actor)]
                calls.append(call('submit_finding', claim(rule, ids)))
            calls.append(call('finish_investigation', {}))
        self.turn += 1
        return dict(message=dict(role='assistant', tool_calls=calls), prompt_eval_count=10, eval_count=10)


class AcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name); self.store = Store(self.root / 'db'); self.addCleanup(self.store.close)

    def state(self, **limits):
        return self.store.create(dict(backend='ollama', model='scripted-control', endpoint='https://ollama.com',
            scenario=SCENARIO, mode='vulnerable', access_contract=contract(), usage_version=1,
            limits=dict(DISCOVERY_LIMITS, **limits)))

    def run_control(self, mode='supported', **limits):
        state = self.state(**limits)
        with lab('vulnerable', SCENARIO) as origin:
            investigate(self.store, state, origin, ScriptedControl(mode))
        return state

    def test_supported_claims_pass_and_export_recomputes_offline(self):
        state = self.run_control(); result = score(state)
        self.assertTrue(result['passed']); self.assertEqual(result['supported_findings'], 2)
        self.assertEqual(result['negative_controls_tested'], 7)
        self.assertEqual(result['cases_tested'], 9)
        with patch('urllib.request.OpenerDirector.open', side_effect=AssertionError('offline')):
            export_run(state, self.root / 'proof'); verify_bundle(self.root / 'proof')
            self.assertEqual(score_bundle(self.root / 'proof'), result)
            output = io.StringIO()
            with redirect_stdout(output): self.assertEqual(main(['acceptance-score', str(self.root / 'proof')]), 0)
        retained = json.loads((self.root / 'proof' / 'runs' / state['id'] / 'result.json').read_text())
        self.assertEqual(retained['acceptance'], result)

    def test_traversal_and_finish_without_claims_miss_both_flaws(self):
        state = self.run_control('silent'); result = score(state)
        self.assertFalse(result['passed']); self.assertTrue(result['explicitly_finished'])
        self.assertEqual(result['cases_tested'], 9)
        self.assertEqual(result['supported_findings'], 0); self.assertEqual(result['missed_findings'], 2)

    def test_claim_everything_negative_control_cannot_pass(self):
        state = self.run_control('everything'); result = score(state)
        self.assertFalse(result['passed']); self.assertEqual(result['unsupported_claim_attempts'], 7)
        self.assertEqual(result['negative_control_claimed_cases'], 7)
        self.assertEqual(result['negative_control_false_positive_cases'], 0)
        self.assertEqual(result['supported_findings'], 2)
        reasons = {r['validation']['reason'] for r in state['submissions']}
        self.assertTrue({'proved', 'access_permitted', 'unproved_cross_account_read', 'missing_successful_control'} <= reasons)

    def test_negative_controls_preserve_actual_http_semantics(self):
        state = self.run_control('silent')
        pairs = {r['id']: [next(e for e in state['evidence'] if e['path'] == r['path'] and e['actor'] == a)
                           for a in (r['owner'], 'bob' if r['owner'] == 'alice' else 'alice')]
                 for r in contract()['rules']}
        for name, statuses in [('restricted_key', [200, 403]), ('sealed_case', [200, 404]),
                               ('delegated_handover', [200, 200]), ('published_bulletin', [200, 200]),
                               ('archive_record', [503, 503]), ('workspace_report', [200, 200]),
                               ('case_export', [503, 200])]:
            self.assertEqual([e['status'] for e in pairs[name]], statuses)
        self.assertNotEqual(pairs['workspace_report'][0]['body']['data'], pairs['workspace_report'][1]['body']['data'])

    def test_private_expectations_and_identities_are_not_guidance(self):
        text = json.dumps(initial_messages(SCENARIO) + [guidance(contract())])
        for resource in RESOURCES.values():
            self.assertNotIn(resource['marker'], text)
        for private in ('behaviour', 'expected_findings', 'archive_outage', 'failed_owner_control'):
            self.assertNotIn(private, text)
        self.assertNotIn('/api/documents/101', text)

    def test_invalid_missing_stale_and_wrong_identity_evidence_rejected(self):
        state = self.run_control(); first = state['submissions'][0]['finding']
        changed = copy.deepcopy(first); changed['evidence_ids'][1] = 999
        self.assertFalse(evaluate(contract(), changed, state['evidence'])['accepted'])
        evidence = copy.deepcopy(state['evidence'])
        cross = first['evidence_ids'][1] - 1; evidence[cross]['body']['data'] = 'different'
        self.assertFalse(evaluate(contract(), first, evidence)['accepted'])
        evidence = copy.deepcopy(state['evidence']); evidence.append(dict(evidence[cross], id=19, status=403, body={}))
        self.assertEqual(evaluate(contract(), first, evidence)['reason'], 'superseded_evidence')
        changed = copy.deepcopy(state); changed['config']['access_contract']['rules'][0]['allowed_actors'] = ['alice', 'bob']
        with self.assertRaises(ValueError): score(changed)
        changed = copy.deepcopy(state); changed['submissions'][0]['validation']['accepted'] = False
        with self.assertRaises(ValueError): score(changed)

    def test_duplicate_claims_do_not_inflate_supported_count(self):
        state = self.run_control(); state['submissions'].append(copy.deepcopy(state['submissions'][0]))
        result = score(state)
        self.assertEqual(result['supported_findings'], 2); self.assertEqual(result['duplicate_submissions'], 1)

    def test_exhausted_request_allowance_cannot_pass_or_reset_on_resume(self):
        state = self.run_control(requests=1); result = score(state)
        self.assertFalse(result['passed']); self.assertFalse(result['explicitly_finished'])
        restored = self.store.load(state['id'])
        with patch('redwake.runner.probe', side_effect=AssertionError('no allowance')):
            investigate(self.store, restored, 'unused', ScriptedControl())
        self.assertEqual(restored['requests'], 1)
        export_run(restored, self.root / 'stopped'); self.assertFalse(score_bundle(self.root / 'stopped')['passed'])

    def test_bundle_tampering_and_nonacceptance_runs_cannot_be_scored(self):
        state = self.run_control(); export_run(state, self.root / 'proof')
        path = self.root / 'proof' / 'runs' / state['id'] / 'state.json'
        altered = copy.deepcopy(state); altered['submissions'] = []; path.write_text(json.dumps(altered))
        with self.assertRaises(ValueError): score_bundle(self.root / 'proof')
        state['config']['scenario'] = 'classic'
        with self.assertRaises(ValueError): score(state)

    def test_cli_attaches_canonical_policy_and_reports_acceptance(self):
        output = io.StringIO()
        with patch('redwake.cli.Ollama', return_value=ScriptedControl()), redirect_stdout(output):
            self.assertEqual(main(['--db', str(self.root / 'cli-db'), '--reports', str(self.root / 'reports'),
                'demo', '--backend', 'ollama', '--model', 'scripted-control', '--scenario', SCENARIO]), 0)
        results = list((self.root / 'reports').glob('*/result.json'))
        self.assertEqual(len(results), 1)
        self.assertTrue(json.loads(results[0].read_text())['acceptance']['passed'])
        self.assertIn('## Security acceptance', results[0].with_name('report.md').read_text())

    def test_cli_rejects_wrong_mode_backend_and_modified_contract_before_inference(self):
        from contextlib import redirect_stderr
        bad = contract(); bad['rules'][0]['allowed_actors'] = ['alice', 'bob']
        path = self.root / 'bad-policy.json'; path.write_text(json.dumps(bad))
        base = ['--db', str(self.root / 'cli-db'), 'demo', '--scenario', SCENARIO]
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()), \
             patch('redwake.cli.Ollama', side_effect=AssertionError('no inference')):
            for options in ([], ['--backend', 'ollama', '--mode', 'fixed'],
                            ['--backend', 'ollama', '--contract', str(path)]):
                self.assertEqual(main(base + options), 2)
