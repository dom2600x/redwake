import copy
import io
import json
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from redwake.anthropic import Anthropic, response_input
from redwake.anthropic_usage import API_VERSION
from redwake.artifacts import export_run, verify_bundle, validate_run
from redwake.cli import main
from redwake.lab import lab
from redwake.runner import DEFAULT_LIMITS, investigate
from redwake.store import Store
from redwake.submission import SUBMISSION_TOOLS, recheck as recheck_findings
from redwake.usage import normalize, recheck

SECRET = 'private-provider-credential-or-error'


def call(name, args, number):
    return dict(type='tool_use', id='tool_' + str(number), name=name, input=args)


def response(content=None, **changes):
    blocks = content if content is not None else [dict(type='text', text='Continue investigation.')]
    result = dict(type='message', role='assistant', model='test-model', content=blocks,
        stop_reason='tool_use' if any(b.get('type') == 'tool_use' for b in blocks) else 'end_turn',
        usage=dict(input_tokens=100, output_tokens=20, cache_creation_input_tokens=40,
                   cache_read_input_tokens=30, service_tier='standard',
                   cache_creation=dict(ephemeral_5m_input_tokens=10, ephemeral_1h_input_tokens=30)))
    result.update(changes)
    return result


class AnthropicTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.store = Store(self.root / 'db'); self.addCleanup(self.store.close)
        env = patch.dict('os.environ', ANTHROPIC_API_KEY=SECRET)
        env.start(); self.addCleanup(env.stop)
        self.model = Anthropic('test-model', tools=SUBMISSION_TOOLS)
        self.contract = json.loads(Path('examples/findings/contract.json').read_text())

    def state(self, **limits):
        return self.store.create(dict(backend='anthropic', model='test-model', endpoint='https://api.anthropic.com',
            usage_version=2, mode='vulnerable', access_contract=self.contract, limits=dict(DEFAULT_LIMITS, **limits)))

    def test_submission_and_disjoint_cache_usage_export_offline(self):
        finding = json.loads(Path('examples/findings/finding.json').read_text())
        turns = [response([call('probe', dict(actor=a, path='/api/documents/101'), i)
                           for i, a in enumerate(('alice', 'bob'), 1)]),
                 response([call('submit_finding', finding, 3), call('finish_investigation', {}, 4)])]
        state = self.state(requests=2)
        def respond(url, headers, payload, **options):
            saved = self.store.load(state['id'])
            self.assertTrue(saved['inflight_model'])
            self.assertEqual(saved['usage_ledger'][-1]['status'], 'reserved')
            self.assertEqual(url, 'https://api.anthropic.com/v1/messages')
            self.assertEqual(headers['x-api-key'], SECRET)
            self.assertEqual(headers['anthropic-version'], API_VERSION)
            self.assertTrue(options['use_env_proxy']); self.assertTrue(options['strict_json'])
            self.assertEqual(options['limit'], 1048576)
            self.assertEqual(payload['max_tokens'], 1024); self.assertFalse(payload['stream'])
            self.assertNotIn('thinking', payload); self.assertNotIn('cache_control', payload)
            self.assertEqual([t['name'] for t in payload['tools']], ['probe', 'submit_finding', 'finish_investigation'])
            self.assertTrue(payload['system'])
            if saved['model_calls'] == 2:
                results = payload['messages'][-1]['content']
                self.assertEqual([r['tool_use_id'] for r in results], ['tool_1', 'tool_2'])
                self.assertEqual([json.loads(r['content'])['actor'] for r in results], ['alice', 'bob'])
            return 200, turns.pop(0)
        with patch('redwake.anthropic.request_json', side_effect=respond), lab('vulnerable') as origin:
            investigate(self.store, state, origin, self.model)
        self.assertEqual(state['status'], 'completed')
        self.assertTrue(recheck_findings(state)[0]['current_validation']['accepted'])
        self.assertEqual((state['input_tokens'], state['output_tokens']), (340, 40))
        entry = recheck(state)[0]
        self.assertEqual(entry['uncached_input_tokens'], 100)
        self.assertEqual(entry['cache_creation_input_tokens'], 40)
        self.assertEqual(entry['cached_input_tokens'], 30)
        self.assertEqual((entry['cache_creation_5m_tokens'], entry['cache_creation_1h_tokens']), (10, 30))
        self.assertIsNone(entry['reasoning_tokens'])
        self.assertEqual(entry['api_version'], API_VERSION)
        with patch('urllib.request.OpenerDirector.open', side_effect=AssertionError('offline')):
            export_run(state, self.root / 'proof'); verify_bundle(self.root / 'proof')
        result = json.loads((self.root / 'proof' / 'runs' / state['id'] / 'result.json').read_text())
        self.assertEqual(result['provider_usage'], state['usage_ledger'])
        self.assertNotIn('cost', result)
        self.assertNotIn(SECRET, json.dumps(state))

    def test_interrupted_batch_resume_preserves_tool_ids_and_reservations(self):
        from redwake.transport import probe
        state = self.state()
        first = response([call('probe', dict(actor=a, path='/api/documents/101'), i)
                          for i, a in enumerate(('alice', 'bob'), 1)])
        attempts = []
        def interrupt(*args, **kwargs):
            attempts.append(1)
            if len(attempts) == 2: raise KeyboardInterrupt()
            return probe(*args, **kwargs)
        with patch('redwake.anthropic.request_json', return_value=(200, first)), \
             patch('redwake.runner.probe', side_effect=interrupt), lab('vulnerable') as origin:
            investigate(self.store, state, origin, self.model)
        self.assertEqual(state['requests'], 2)
        restored = self.store.load(state['id'])
        def finish(url, headers, payload, **options):
            results = payload['messages'][-1]['content']
            self.assertEqual([r['tool_use_id'] for r in results], ['tool_1', 'tool_2'])
            return 200, response([call('finish_investigation', {}, 3)])
        with patch('redwake.anthropic.request_json', side_effect=finish), lab('vulnerable') as origin:
            investigate(self.store, restored, origin, self.model)
        self.assertEqual(restored['status'], 'completed')
        self.assertEqual(restored['requests'], 3)
        self.assertEqual(len(recheck(restored)), 2)

    def test_missing_invalid_and_inconsistent_cache_counts_remain_unknown(self):
        for usage in (None, dict(input_tokens=100, output_tokens=20),
                      dict(input_tokens=True, output_tokens=-1, cache_read_input_tokens=30, cache_creation_input_tokens=40),
                      dict(input_tokens=100, output_tokens=20, cache_read_input_tokens=30, cache_creation_input_tokens=40,
                           cache_creation=dict(ephemeral_5m_input_tokens=50, ephemeral_1h_input_tokens=30))):
            state = self.state(model_calls=1)
            with patch('redwake.anthropic.request_json', return_value=(200, response(usage=usage))):
                investigate(self.store, state, 'unused', self.model)
            entry = recheck(state)[0]
            self.assertIsNone(entry['cache_creation_5m_tokens'])
            self.assertIsNone(entry['cache_creation_1h_tokens'])
            self.assertEqual(entry['input_tokens'], 170 if usage and usage.get('input_tokens') == 100 and 'cache_read_input_tokens' in usage else None)
            if usage and usage.get('cache_read_input_tokens') == 30:
                self.assertEqual(entry['cached_input_tokens'], 30)
            validate_run(state)

    def test_incomplete_output_never_executes_and_resume_discards_proposals(self):
        for stop in ('max_tokens', 'pause_turn'):
            state = self.state()
            native = response([call('probe', dict(actor='alice', path='/api/documents/101'), 1)], stop_reason=stop)
            with patch('redwake.anthropic.request_json', return_value=(200, native)):
                investigate(self.store, state, 'unused', self.model)
            self.assertEqual(state['diagnostics'][-1]['category'], 'inference_incomplete')
            self.assertEqual(state['requests'], 0)
            self.assertEqual(state['output_tokens'], 20)
            self.assertEqual(recheck(state)[0]['response_status'], 'incomplete')
            def finish(url, headers, payload, **kwargs):
                self.assertFalse(any(isinstance(m['content'], list) and any(b['type'] == 'tool_use' for b in m['content']) for m in payload['messages']))
                return 200, response([call('finish_investigation', {}, 2)])
            with patch('redwake.anthropic.request_json', side_effect=finish):
                investigate(self.store, state, 'unused', self.model)
            self.assertEqual(state['status'], 'completed')

    def test_http_protocol_and_inference_failures_are_sanitized(self):
        for code, native, category in ((401, {'error': SECRET}, 'http_auth'),
                (429, {'error': SECRET}, 'http_rate_limit'), (503, {'error': SECRET}, 'http_server'),
                (200, response(error={'message': SECRET}), 'inference_error'),
                (200, response(stop_reason='refusal'), 'inference_error'),
                (200, response([dict(type='thinking', thinking=SECRET)]), 'response_protocol'),
                (200, response(stop_reason='unexpected'), 'response_protocol'),
                (200, response([], stop_reason='end_turn'), 'response_protocol'),
                (200, response([call('probe', {}, 1)], stop_reason='end_turn'), 'response_protocol'),
                (200, response(role='user'), 'response_protocol'),
                (200, response([call('probe', {}, 1), call('probe', {}, 1)]), 'response_protocol')):
            state = self.state(model_calls=1)
            with patch('redwake.anthropic.request_json', return_value=(code, native)):
                investigate(self.store, state, 'unused', self.model)
            self.assertEqual(state['diagnostics'][-1]['category'], category)
            self.assertEqual(state['requests'], 0)
            self.assertNotIn(SECRET, json.dumps(state))
            self.assertEqual(recheck(state)[0]['status'], 'reported' if code == 200 else 'unknown')
            validate_run(state)

    def test_transport_and_crash_recovery_keep_unknown_usage(self):
        from redwake.usage import begin
        for error in (TimeoutError(SECRET), KeyboardInterrupt()):
            state = self.state(model_calls=1)
            with patch('redwake.anthropic.request_json', side_effect=error):
                investigate(self.store, state, 'unused', self.model)
            self.assertEqual(recheck(state)[0]['status'], 'unknown')
            self.assertFalse(state['usage_complete'])
            self.assertNotIn(SECRET, json.dumps(state))
        state = self.state(model_calls=1); begin(state, 1024)
        state.update(model_calls=1, reserved_output_tokens=1024, inflight_model=True)
        self.store.save(state)
        with patch('redwake.anthropic.request_json', side_effect=AssertionError('no retry')):
            investigate(self.store, state, 'unused', self.model)
        self.assertEqual(recheck(state)[0]['status'], 'unknown')

    def test_model_choices_still_use_scope_contract(self):
        for args in ('malformed', dict(actor='admin', path='/outside')):
            state = self.state()
            with patch('redwake.anthropic.request_json', return_value=(200, response([call('probe', args, 1)]))):
                investigate(self.store, state, 'unused', self.model)
            self.assertEqual(state['diagnostics'][-1]['source'], 'model')
            self.assertEqual(state['requests'], 0)
            recheck(state)

    def test_usage_tampering_and_wrong_contract_versions_are_rejected(self):
        state = self.state(model_calls=1)
        with patch('redwake.anthropic.request_json', return_value=(200, response())):
            investigate(self.store, state, 'unused', self.model)
        for change in (dict(input_tokens=100), dict(cache_creation_5m_tokens=11),
                       dict(cached_input_tokens=31), dict(api_version='other'), dict(stop_reason='refusal'),
                       dict(reasoning_tokens=1), dict(status='unknown'), dict(service_tier=SECRET),
                       dict(uncached_input_tokens=True), dict(output_limit=1)):
            changed = copy.deepcopy(state); changed['usage_ledger'][0].update(change)
            with self.assertRaises(ValueError): validate_run(changed)
        for version in (None, 1, True):
            changed = copy.deepcopy(state)
            if version is None: del changed['config']['usage_version']
            else: changed['config']['usage_version'] = version
            with self.assertRaises(ValueError): validate_run(changed)

    def test_cli_and_credential_endpoint_pricing_guards(self):
        with patch.dict('os.environ', {}, clear=True):
            with self.assertRaises(ValueError): Anthropic('test-model')
        with self.assertRaises(ValueError): Anthropic('test-model', 'https://example.com')
        base = ['--db', str(self.root / 'cli-db'), '--reports', str(self.root / 'reports'), 'demo']
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            for args in (['--backend', 'anthropic'], ['--backend', 'anthropic', '--model', 'test-model', '--endpoint', 'https://ollama.com'],
                         ['--backend', 'anthropic', '--model', 'test-model', '--pricing', 'examples/pricing/openai-sol.json']):
                with patch('redwake.anthropic.request_json', side_effect=AssertionError('no inference')):
                    self.assertEqual(main(base + args), 2)
            with patch('redwake.anthropic.request_json', return_value=(200, response([call('finish_investigation', {}, 1)]))), patch('redwake.cli.lab') as local_lab:
                local_lab.return_value.__enter__.return_value = 'unused'
                self.assertEqual(main(base + ['--backend', 'anthropic', '--model', 'test-model', '--contract', 'examples/findings/contract.json']), 0)

    def test_unmatched_results_cannot_be_sent_as_executed_tool_evidence(self):
        from redwake.providers import ProviderError
        with self.assertRaises(ProviderError): response_input([dict(role='tool', tool_name='probe', content='{}')])
        self.assertEqual(normalize('anthropic', response())['input_tokens'], 170)
