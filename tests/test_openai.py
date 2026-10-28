import copy
import io
import json
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from redwake.artifacts import export_run, verify_bundle, validate_run
from redwake.cli import main
from redwake.lab import lab
from redwake.openai import OpenAI
from redwake.providers import Ollama
from redwake.runner import DEFAULT_LIMITS, investigate
from redwake.store import Store
from redwake.submission import SUBMISSION_TOOLS, recheck as recheck_findings
from redwake.usage import normalize, recheck


SECRET = 'private-credential-or-provider-error'


def call(name, args, number):
    return dict(type='function_call', id='fc_' + str(number), call_id='call_' + str(number),
                name=name, arguments=json.dumps(args))


def response(output=None, **changes):
    result = dict(model='test-model', status='completed', service_tier='default', output=output or [],
                  usage=dict(input_tokens=100, output_tokens=20,
                             input_tokens_details=dict(cached_tokens=30),
                             output_tokens_details=dict(reasoning_tokens=15)))
    result.update(changes)
    return result


class OpenAITests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.store = Store(self.root / 'db'); self.addCleanup(self.store.close)
        self.env = patch.dict('os.environ', {'OPENAI_API_KEY': SECRET}); self.env.start(); self.addCleanup(self.env.stop)
        self.model = OpenAI('test-model', tools=SUBMISSION_TOOLS)
        self.contract = json.loads(Path('examples/findings/contract.json').read_text())

    def state(self, **limits):
        return self.store.create(dict(backend='openai', model='test-model', endpoint='https://api.openai.com',
            mode='vulnerable', usage_version=1, access_contract=self.contract, limits=dict(DEFAULT_LIMITS, **limits)))

    def test_submission_replay_and_usage_export_offline(self):
        finding = json.loads(Path('examples/findings/finding.json').read_text())
        reasoning = dict(type='reasoning', id='rs_1', summary=[], encrypted_content='opaque-reasoning')
        turns = [response([reasoning] + [call('probe', dict(actor=a, path='/api/documents/101'), i)
                                        for i, a in enumerate(('alice', 'bob'), 1)]),
                 response([call('submit_finding', finding, 3), call('finish_investigation', {}, 4)])]
        state = self.state(requests=2)
        def respond(url, headers, payload, **options):
            saved = self.store.load(state['id'])
            self.assertTrue(saved['inflight_model'])
            self.assertEqual(saved['usage_ledger'][-1]['status'], 'reserved')
            self.assertEqual(url, 'https://api.openai.com/v1/responses')
            self.assertFalse(payload['store']); self.assertFalse(payload['stream'])
            self.assertEqual(payload['service_tier'], 'default')
            self.assertEqual(payload['include'], ['reasoning.encrypted_content'])
            self.assertEqual(payload['max_output_tokens'], 1024)
            self.assertTrue(options['strict_json']); self.assertTrue(options['use_env_proxy'])
            self.assertEqual(headers['Authorization'], 'Bearer ' + SECRET)
            self.assertEqual([t['name'] for t in payload['tools']], ['probe', 'submit_finding', 'finish_investigation'])
            if saved['model_calls'] == 2:
                self.assertIn(reasoning, payload['input'])
                results = [i for i in payload['input'] if i.get('type') == 'function_call_output']
                self.assertEqual([i['call_id'] for i in results], ['call_1', 'call_2'])
                self.assertEqual([json.loads(i['output'])['actor'] for i in results], ['alice', 'bob'])
            return 200, turns.pop(0)
        with patch('redwake.openai.request_json', side_effect=respond), lab('vulnerable') as origin:
            investigate(self.store, state, origin, self.model)
        self.assertEqual(state['status'], 'completed')
        self.assertTrue(recheck_findings(state)[0]['current_validation']['accepted'])
        self.assertEqual((state['input_tokens'], state['output_tokens']), (200, 40))
        self.assertEqual([e['cached_input_tokens'] for e in recheck(state)], [30, 30])
        self.assertEqual([e['reasoning_tokens'] for e in recheck(state)], [15, 15])
        with patch('urllib.request.OpenerDirector.open', side_effect=AssertionError('offline')):
            export_run(state, self.root / 'proof'); verify_bundle(self.root / 'proof')
        result = json.loads((self.root / 'proof' / 'runs' / state['id'] / 'result.json').read_text())
        self.assertEqual(result['provider_usage'], state['usage_ledger'])
        self.assertNotIn('cost', result)
        self.assertNotIn(SECRET, json.dumps(state))

    def test_resume_pending_batch_preserves_call_ids_without_refunding(self):
        state = self.state()
        first = response([call('probe', dict(actor=a, path='/api/documents/101'), i)
                          for i, a in enumerate(('alice', 'bob'), 1)])
        from redwake.transport import probe
        attempts = []
        def interrupted_probe(*args, **kwargs):
            attempts.append(1)
            if len(attempts) == 2: raise KeyboardInterrupt()
            return probe(*args, **kwargs)
        with patch('redwake.openai.request_json', return_value=(200, first)), patch('redwake.runner.probe', side_effect=interrupted_probe), lab('vulnerable') as origin:
            investigate(self.store, state, origin, self.model)
        self.assertEqual(state['requests'], 2); self.assertEqual(len(state['pending']), 1)
        state = self.store.load(state['id'])
        def finish(url, headers, payload, **kwargs):
            results = [i for i in payload['input'] if i.get('type') == 'function_call_output']
            self.assertEqual([i['call_id'] for i in results], ['call_1', 'call_2'])
            return 200, response([call('finish_investigation', {}, 3)])
        with patch('redwake.openai.request_json', side_effect=finish), lab('vulnerable') as origin:
            investigate(self.store, state, origin, self.model)
        self.assertEqual(state['status'], 'completed'); self.assertEqual(state['requests'], 3)
        self.assertEqual(len(recheck(state)), 2)

    def test_failed_malformed_and_incomplete_responses_keep_usage_without_execution(self):
        for native, category in ((response(status='failed', error={'message': SECRET}), 'inference_error'),
                                 (response(output=[dict(type='unsupported', error=SECRET)]), 'response_protocol'),
                                 (response([call('probe', dict(actor='alice', path='/api/documents/101'), 1)],
                                           status='incomplete', incomplete_details={'reason': SECRET}), 'inference_incomplete')):
            with self.subTest(category=category):
                state = self.state()
                with patch('redwake.openai.request_json', return_value=(200, native)):
                    investigate(self.store, state, 'unused', self.model)
                self.assertEqual(state['diagnostics'][-1]['category'], category)
                self.assertEqual(state['requests'], 0); self.assertEqual(state['pending'], [])
                self.assertEqual(state['output_tokens'], 20); self.assertTrue(state['usage_complete'])
                self.assertEqual(recheck(state)[0]['status'], 'reported')
                self.assertNotIn(SECRET, json.dumps(state)); validate_run(state)
                if category == 'inference_incomplete':
                    def finish(url, headers, payload, **kwargs):
                        self.assertFalse(any(i.get('type') == 'function_call' for i in payload['input']))
                        return 200, response([call('finish_investigation', {}, 2)])
                    with patch('redwake.openai.request_json', side_effect=finish):
                        investigate(self.store, state, 'unused', self.model)
                    self.assertEqual(state['status'], 'completed')

    def test_missing_and_invalid_counts_remain_unknown_and_subsets_are_not_added(self):
        for native in (response(usage=None), response(usage=dict(input_tokens=True, output_tokens=-1)),
                       response(usage=dict(input_tokens=100, output_tokens=20,
                           input_tokens_details=dict(cached_tokens=101), output_tokens_details=dict(reasoning_tokens=21)))):
            with self.subTest(usage=native['usage']):
                state = self.state(model_calls=1)
                with patch('redwake.openai.request_json', return_value=(200, native)):
                    investigate(self.store, state, 'unused', self.model)
                entry = recheck(state)[0]
                self.assertIsNone(entry['cached_input_tokens']); self.assertIsNone(entry['reasoning_tokens'])
                self.assertEqual(state['input_tokens'], 100 if native['usage'] and native['usage'].get('input_tokens') == 100 else 0)
                self.assertEqual(state['usage_complete'], entry['input_tokens'] is not None and entry['output_tokens'] is not None)

    def test_transport_failures_and_crashes_retain_unknown_usage(self):
        for failure in (TimeoutError(SECRET), KeyboardInterrupt()):
            state = self.state(model_calls=1)
            with patch('redwake.openai.request_json', side_effect=failure):
                investigate(self.store, state, 'unused', self.model)
            with patch('redwake.openai.request_json', side_effect=AssertionError('no retry')):
                investigate(self.store, state, 'unused', self.model)
            self.assertEqual(recheck(state)[0]['status'], 'unknown')
            self.assertFalse(state['usage_complete']); self.assertNotIn(SECRET, json.dumps(state))
        from redwake.usage import begin
        state = self.state(model_calls=1); begin(state, 1024)
        state.update(model_calls=1, reserved_output_tokens=1024, inflight_model=True)
        self.store.save(state)
        investigate(self.store, state, 'unused', self.model)
        self.assertEqual(recheck(state)[0]['status'], 'unknown')

    def test_http_errors_are_sanitized_and_model_choices_stay_distinct(self):
        for status, category in ((401, 'http_auth'), (429, 'http_rate_limit'), (503, 'http_server')):
            state = self.state(model_calls=1)
            with patch('redwake.openai.request_json', return_value=(status, {'error': SECRET})):
                investigate(self.store, state, 'unused', self.model)
            self.assertEqual(state['diagnostics'][-1]['category'], category)
            self.assertIsNone(recheck(state)[0]['input_tokens']); self.assertNotIn(SECRET, json.dumps(state))
        for arguments in ('{bad json', json.dumps({'actor': 'admin', 'path': '/outside'})):
            state = self.state()
            proposal = dict(call('probe', {}, 1), arguments=arguments)
            with patch('redwake.openai.request_json', return_value=(200, response([proposal]))):
                investigate(self.store, state, 'unused', self.model)
            self.assertEqual(state['diagnostics'][-1]['source'], 'model')
            self.assertEqual(state['requests'], 0); self.assertTrue(state['usage_complete']); recheck(state)

    def test_usage_forgery_is_rejected(self):
        state = self.state(model_calls=1)
        with patch('redwake.openai.request_json', return_value=(200, response())):
            investigate(self.store, state, 'unused', self.model)
        for change in (dict(input_tokens=99), dict(cached_input_tokens=101), dict(output_limit=1),
                       dict(reasoning_tokens=True), dict(model=SECRET + ' '), dict(service_tier=SECRET),
                       dict(status='unknown'), dict(started_utc='2026-10-28T00:00:00')):
            changed = copy.deepcopy(state); changed['usage_ledger'][0].update(change)
            with self.assertRaises(ValueError): validate_run(changed)
        changed = copy.deepcopy(state); del changed['config']['usage_version']
        with self.assertRaises(ValueError): validate_run(changed)

    def test_cli_model_endpoint_and_pricing_guards(self):
        base = ['--db', str(self.root / 'cli-db'), '--reports', str(self.root / 'reports')]
        with redirect_stderr(io.StringIO()), redirect_stdout(io.StringIO()):
            for args in (['--backend', 'openai'], ['--backend', 'openai', '--model', 'test-model', '--endpoint', 'https://ollama.com'],
                         ['--backend', 'ollama', '--endpoint', 'https://api.openai.com'],
                         ['--backend', 'openai', '--model', 'test-model', '--pricing', 'examples/pricing/ollama-ultra.json']):
                with patch('redwake.openai.request_json', side_effect=AssertionError('no inference')):
                    self.assertEqual(main(base + ['demo'] + args), 2)
            with patch('redwake.openai.request_json', return_value=(200, response([call('finish_investigation', {}, 1)]))):
                self.assertEqual(main(base + ['demo', '--backend', 'openai', '--model', 'test-model',
                                             '--contract', 'examples/findings/contract.json']), 0)

    def test_new_ollama_runs_use_normalized_usage_and_keep_cost_ledger_consistent(self):
        from redwake import costs
        state = self.state(model_calls=1)
        card = json.loads(Path('examples/pricing/ollama-ultra.json').read_text())
        state['config'].update(backend='ollama', endpoint='https://ollama.com', model=card['model'],
            cost_policy=dict(rate_card=card, billing_context='free', max_cost_usd=None, input_token_reservation=1000))
        native = dict(model=card['model'], message=dict(role='assistant'), done=True, prompt_eval_count=100, eval_count=20)
        with patch('redwake.providers.request_json', return_value=(200, native)), patch.dict('os.environ', {'OLLAMA_API_KEY': SECRET}):
            investigate(self.store, state, 'unused', Ollama(card['model']))
        self.assertIsNone(recheck(state)[0]['cached_input_tokens']); costs.recheck(state)
        export_run(state, self.root / 'ollama'); verify_bundle(self.root / 'ollama')
        changed = copy.deepcopy(state); changed['usage_ledger'][0]['model'] = 'other-model'
        with self.assertRaises(ValueError): validate_run(changed)
        self.assertEqual(normalize('ollama', native)['response_status'], 'completed')
