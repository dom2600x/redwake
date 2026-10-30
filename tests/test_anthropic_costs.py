import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from redwake import costs
from redwake.anthropic import Anthropic
from redwake.anthropic_usage import API_VERSION
from redwake.artifacts import export_run, verify_bundle, validate_run
from redwake.runner import DEFAULT_LIMITS, investigate
from redwake.store import Store
from test_anthropic import response, call


class AnthropicCostTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.store = Store(self.root / 'db'); self.addCleanup(self.store.close)
        self.card = dict(version=3, provider='anthropic', model='test-model', currency='USD',
            source='Synthetic rates, not published prices', as_of='2026-10-29', input='2',
            cached_input='0.1', output='10', cache_write_5m='2.5', cache_write_1h='4',
            context_threshold=170, long_input_multiplier='2', long_output_multiplier='3',
            service_tier='standard', api_version=API_VERSION, processing_mode='synchronous', inference_geo='global')
        with patch.dict('os.environ', ANTHROPIC_API_KEY='test-key'):
            self.model = Anthropic('test-model')

    def state(self, budget=None, calls=1):
        return self.store.create(dict(backend='anthropic', model='test-model', endpoint='https://api.anthropic.com',
            usage_version=2, mode='vulnerable', limits=dict(DEFAULT_LIMITS, model_calls=calls),
            cost_policy=dict(rate_card=copy.deepcopy(self.card), billing_context='purchased',
                             max_cost_usd=budget, input_token_reservation=100)))

    def run_response(self, state, native=None):
        with patch('redwake.anthropic.request_json', return_value=(200, native or response())) as request:
            investigate(self.store, state, 'unused', self.model)
        return request

    def test_disjoint_categories_exact_value_and_offline_export(self):
        state = self.state(); self.run_response(state)
        result = costs.recheck(state)
        # 100*2 + 30*.1 + 10*2.5 + 30*4 + 20*10, per million.
        self.assertEqual(costs.money(result['calculated_usage_value_usd']), costs.money('0.000548'))
        self.assertEqual(result['uncertain_valuation_calls'], 0)
        with patch('urllib.request.OpenerDirector.open', side_effect=AssertionError('offline')):
            export_run(state, self.root / 'proof'); verify_bundle(self.root / 'proof')
        saved = json.loads((self.root / 'proof' / 'runs' / state['id'] / 'result.json').read_text())
        self.assertEqual(saved['cost'], result)

    def test_context_threshold_includes_all_cache_categories(self):
        for field in ('input_tokens', 'cache_read_input_tokens', 'cache_creation_input_tokens'):
            native = response(); native['usage'][field] += 1
            if field == 'cache_creation_input_tokens':
                native['usage']['cache_creation']['ephemeral_1h_input_tokens'] += 1
            state = self.state(); self.run_response(state, native)
            extra = {'input_tokens': '2', 'cache_read_input_tokens': '.1', 'cache_creation_input_tokens': '4'}[field]
            expected = (costs.money('348') + costs.money(extra)) * 2 / 1000000 + costs.money('.0006')
            self.assertEqual(costs.money(costs.recheck(state)['calculated_usage_value_usd']), expected)

    def test_unknown_retention_uses_range_and_zero_creation_is_exact(self):
        native = response(); del native['usage']['cache_creation']
        state = self.state(); self.run_response(state, native); result = costs.recheck(state)
        self.assertIsNone(result['calculated_usage_value_usd'])
        self.assertEqual(costs.money(result['known_minimum_usd']), costs.money('.000503'))
        self.assertEqual(costs.money(result['estimated_exposure_usd']), costs.money('.000563'))
        native['usage']['cache_creation_input_tokens'] = 0
        state = self.state(); self.run_response(state, native)
        self.assertEqual(costs.money(costs.recheck(state)['calculated_usage_value_usd']), costs.money('.000403'))

    def test_partial_usage_retains_known_categories_and_reservation(self):
        native = response(); del native['usage']['input_tokens']
        state = self.state(); self.run_response(state, native); result = costs.recheck(state)
        self.assertIsNone(result['calculated_usage_value_usd'])
        self.assertEqual(costs.money(result['known_minimum_usd']), costs.money('.000348'))
        self.assertGreaterEqual(costs.money(result['estimated_exposure_usd']), costs.reservation(state['config']['cost_policy'], 1024))
        native['usage']['cache_read_input_tokens'] = 200
        state = self.state(); self.run_response(state, native)
        # Known categories alone prove the long tier, despite the missing ordinary input.
        self.assertEqual(costs.money(costs.recheck(state)['known_minimum_usd']), costs.money('.000930'))

    def test_reservation_is_durable_before_transport_and_timeout_survives_resume(self):
        state = self.state(calls=2)
        def timeout(*args, **kwargs):
            saved = self.store.load(state['id'])
            self.assertTrue(saved['inflight_model'])
            self.assertEqual(saved['cost_ledger'][0]['status'], 'reserved')
            self.assertEqual(costs.money(saved['cost_ledger'][0]['reservation_usd']), costs.money('.03152'))
            raise TimeoutError()
        with patch('redwake.anthropic.request_json', side_effect=timeout):
            investigate(self.store, state, 'unused', self.model)
        restored = self.store.load(state['id']); restored['config']['cost_policy']['max_cost_usd'] = '.04'
        with patch('redwake.anthropic.request_json', side_effect=AssertionError('no spend')):
            investigate(self.store, restored, 'unused', self.model)
        self.assertEqual(restored['model_calls'], 1)
        self.assertEqual(costs.recheck(restored)['unknown_usage_calls'], 1)
        export_run(restored, self.root / 'timeout'); verify_bundle(self.root / 'timeout')

    def test_crash_recovery_retains_reservation(self):
        from redwake import usage
        state = self.state(calls=1); costs.reserve(state, 1024); usage.begin(state, 1024)
        state.update(model_calls=1, reserved_output_tokens=1024, inflight_model=True)
        self.store.save(state)
        restored = self.store.load(state['id'])
        with patch('redwake.anthropic.request_json', side_effect=AssertionError('no retry')):
            investigate(self.store, restored, 'unused', self.model)
        self.assertEqual(restored['cost_ledger'][0]['status'], 'unknown')
        self.assertEqual(costs.money(costs.recheck(restored)['estimated_exposure_usd']), costs.money('.03152'))

    def test_budget_and_metadata_block_tools_and_new_spend_on_resume(self):
        proposal = response([call('probe', dict(actor='alice', path='/api/documents/101'), 1)])
        for changed in ('budget', 'model', 'tier'):
            state = self.state('.04', calls=3); native = copy.deepcopy(proposal)
            if changed == 'budget': native['usage']['input_tokens'] = 100000
            if changed == 'model': native['model'] = 'different'
            if changed == 'tier': native['usage']['service_tier'] = 'priority'
            with patch('redwake.runner.probe', side_effect=AssertionError('no tools')):
                self.assertEqual(self.run_response(state, native).call_count, 1)
                restored = self.store.load(state['id'])
                # Also guard checkpoints containing pending work.
                restored['pending'] = [dict(function=dict(name='probe', arguments=dict(actor='alice', path='/api/documents/101')))]
                with patch('redwake.anthropic.request_json', side_effect=AssertionError('no spend')):
                    investigate(self.store, restored, 'unused', self.model)
            self.assertEqual(restored['requests'], 0)
            costs.recheck(restored)
        state = self.state('.001')
        with patch('redwake.anthropic.request_json', side_effect=AssertionError('no spend')):
            investigate(self.store, state, 'unused', self.model)
        self.assertEqual(state['model_calls'], 0)

    def test_tampered_ledgers_and_unsupported_policy_rejected(self):
        state = self.state(); self.run_response(state)
        for field, val in (('reservation_usd', '0'), ('input_tokens', 1), ('status', 'unknown')):
            changed = copy.deepcopy(state); changed['cost_ledger'][0][field] = val
            with self.assertRaises(ValueError): validate_run(changed)
        changed = copy.deepcopy(state); changed['usage_ledger'][0]['cache_creation_1h_tokens'] = 0
        with self.assertRaises(ValueError): validate_run(changed)
        for field, val in (('version', True), ('service_tier', 'priority'), ('api_version', 'other'),
                           ('processing_mode', 'batch'), ('inference_geo', 'us'), ('context_threshold', True),
                           ('cache_write_1h', None), ('long_input_multiplier', '.5')):
            changed = copy.deepcopy(state); changed['config']['cost_policy']['rate_card'][field] = val
            with self.assertRaises(ValueError): costs.validate_policy(changed['config']['cost_policy'], changed['config'])

    def test_cli_template_and_estimated_budget_without_live_inference(self):
        from contextlib import redirect_stdout
        import io
        from redwake.cli import main
        template = json.loads(Path('examples/pricing/anthropic-template.json').read_text())
        template['model'] = 'test-model'
        card_path = self.root / 'pricing.json'; card_path.write_text(json.dumps(template))
        native = response([call('finish_investigation', {}, 1)])
        with patch.dict('os.environ', ANTHROPIC_API_KEY='test-key'), redirect_stdout(io.StringIO()):
            with patch('redwake.cli.lab') as local_lab, patch('redwake.anthropic.request_json', return_value=(200, native)):
                local_lab.return_value.__enter__.return_value = 'unused'
                self.assertEqual(main(['--db', str(self.root / 'cli-db'), '--reports', str(self.root / 'reports'),
                    'demo', '--backend', 'anthropic', '--model', 'test-model', '--pricing', str(card_path),
                    '--max-cost-usd', '1', '--contract', 'examples/findings/contract.json']), 0)

    def test_missing_metadata_and_failed_usage_remain_accounted(self):
        for field in ('service_tier', 'model'):
            native = response()
            if field == 'model': native['model'] = None
            else: del native['usage']['service_tier']
            state = self.state(calls=2); self.run_response(state, native)
            self.assertEqual(state['model_calls'], 1)
            self.assertEqual(costs.money(costs.recheck(state)['known_minimum_usd']), 0)
            self.assertTrue(costs.execution_blocked(state))
        state = self.state(); self.run_response(state, response(stop_reason='max_tokens'))
        self.assertEqual(costs.money(costs.recheck(state)['calculated_usage_value_usd']), costs.money('.000548'))
        self.assertEqual(state['diagnostics'][-1]['category'], 'inference_incomplete')
