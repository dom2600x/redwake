import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from redwake import costs
from redwake.artifacts import export_run, verify_bundle, validate_run
from redwake.openai import OpenAI
from redwake.runner import investigate, DEFAULT_LIMITS
from redwake.store import Store


class OpenAICostTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.store = Store(self.root / 'db'); self.addCleanup(self.store.close)
        self.card = dict(version=2, provider='openai', model='test-model', currency='USD',
            source='Synthetic test rates', as_of='2026-10-29', input='2', cached_input='0.1',
            output='10', cache_write_30m='2.5', cache_write_12h='5',
            context_threshold=100, long_input_multiplier='2', long_output_multiplier='1.5',
            service_tier='default', cache_write_pricing='replacement')
        with patch.dict('os.environ', OPENAI_API_KEY='test-key'):
            self.model = OpenAI('test-model')

    def state(self, budget=None, calls=1):
        return self.store.create(dict(backend='openai', model='test-model',
            endpoint='https://api.openai.com', usage_version=1, mode='vulnerable',
            limits=dict(DEFAULT_LIMITS, model_calls=calls), cost_policy=dict(rate_card=copy.deepcopy(self.card),
                billing_context='purchased', max_cost_usd=budget, input_token_reservation=100)))

    def run_response(self, state, inputs=100, cached=30, outputs=20, **fields):
        native = dict(model='test-model', status='completed', service_tier='default', output=[],
            usage=dict(input_tokens=inputs, output_tokens=outputs,
                       input_tokens_details=dict(cached_tokens=cached),
                       output_tokens_details=dict(reasoning_tokens=15)))
        native.update(fields)
        with patch('redwake.openai.request_json', return_value=(200, native)) as request:
            investigate(self.store, state, 'unused', self.model)
        return request

    def test_cached_reads_and_reasoning_are_not_double_counted_and_export(self):
        state = self.state(); self.run_response(state)
        result = costs.recheck(state)
        self.assertEqual(costs.money(result['known_minimum_usd']), costs.money('0.000343'))
        self.assertEqual(costs.money(result['estimated_exposure_usd']), costs.money('0.000553'))
        self.assertIsNone(result['calculated_usage_value_usd'])
        self.assertIsNone(result['cash_charge_usd'])
        export_run(state, self.root / 'proof'); verify_bundle(self.root / 'proof')
        saved = json.loads((self.root / 'proof' / 'runs' / state['id'] / 'result.json').read_text())
        self.assertEqual(saved['cost'], result)

    def test_context_threshold_is_strict_and_scales_whole_request(self):
        state = self.state(); self.run_response(state, inputs=101)
        result = costs.recheck(state)
        self.assertEqual(costs.money(result['known_minimum_usd']), costs.money('0.000590'))
        self.assertEqual(costs.money(result['estimated_exposure_usd']), costs.money('0.001016'))

    def test_missing_cache_split_and_partial_usage_remain_conservative(self):
        state = self.state(); self.run_response(state, inputs=100, cached=None)
        result = costs.recheck(state)
        self.assertEqual(costs.money(result['known_minimum_usd']), costs.money('0.000210'))
        self.assertEqual(costs.money(result['estimated_exposure_usd']), costs.money('0.000700'))
        state = self.state(); self.run_response(state, inputs=None, cached=None)
        result = costs.recheck(state)
        self.assertEqual(result['unknown_usage_calls'], 1)
        self.assertGreaterEqual(costs.money(result['estimated_exposure_usd']), costs.reservation(state['config']['cost_policy'], 1024))

    def test_failed_usage_and_unknown_models_or_tiers_do_not_become_exact(self):
        for fields in (dict(status='failed'), dict(status='incomplete'),
                       dict(model='another-model'), dict(model=None),
                       dict(service_tier='priority'), dict(service_tier=None)):
            state = self.state(); self.run_response(state, **fields)
            result = costs.recheck(state)
            self.assertIsNone(result['calculated_usage_value_usd'])
            self.assertEqual(len(state['cost_ledger']), 1)
            if 'model' in fields or 'service_tier' in fields:
                self.assertEqual(costs.money(result['known_minimum_usd']), 0)
                self.assertEqual(costs.money(result['estimated_exposure_usd']),
                                 costs.reservation(state['config']['cost_policy'], 1024))
            validate_run(state)

    def test_budget_blocks_before_network_and_survives_resume(self):
        state = self.state('0.001', calls=2)
        with patch('redwake.openai.request_json', side_effect=AssertionError('no inference')):
            investigate(self.store, state, 'unused', self.model)
            restored = self.store.load(state['id'])
            investigate(self.store, restored, 'unused', self.model)
        self.assertEqual(restored['model_calls'], 0)
        self.assertEqual(restored['reason'], 'Estimated cost budget exhausted')
        costs.recheck(restored)

    def test_unpriceable_routes_stop_tools_and_resume_without_new_spend(self):
        proposal = dict(type='function_call', call_id='probe', name='probe',
                        arguments=json.dumps(dict(actor='alice', path='/api/documents/101')))
        for fields in (dict(model='different-model'), dict(model=None),
                       dict(service_tier='priority'), dict(service_tier='flex'),
                       dict(service_tier=None), dict(service_tier='unrecognized-tier')):
            with self.subTest(fields=fields):
                state = self.state(calls=3)
                with patch('redwake.runner.probe', side_effect=AssertionError('must not execute')):
                    request = self.run_response(state, output=[proposal], **fields)
                self.assertEqual(request.call_count, 1)
                self.assertEqual(state['reason'], 'Provider billing metadata does not match pricing policy')
                self.assertEqual(state['requests'], 0)
                self.assertEqual(state['pending'], [])
                self.assertEqual(state['usage_ledger'][0]['status'], 'reported')
                self.assertEqual(state['input_tokens'], 100)
                self.assertEqual(state['reserved_output_tokens'], 1024)
                restored = self.store.load(state['id'])
                with patch('redwake.openai.request_json', side_effect=AssertionError('must not call')):
                    investigate(self.store, restored, 'unused', self.model)
                self.assertEqual(restored['model_calls'], 1)
                self.assertFalse(costs.reserve(restored, 1024))
                export_run(restored, self.root / ('route-' + restored['id']))
                verify_bundle(self.root / ('route-' + restored['id']))

    def test_resume_blocks_previously_saved_pending_calls_from_unpriceable_route(self):
        state = self.state(calls=3)
        self.run_response(state, service_tier='priority')
        # Simulate a checkpoint written by the earlier runner, before this guard.
        state['pending'] = [dict(function=dict(name='probe', arguments=dict(actor='alice', path='/api/documents/101')))]
        self.store.save(state)
        restored = self.store.load(state['id'])
        with patch('redwake.runner.probe', side_effect=AssertionError('must not execute')), \
             patch('redwake.openai.request_json', side_effect=AssertionError('must not call')):
            investigate(self.store, restored, 'unused', self.model)
        self.assertEqual(restored['requests'], 0)
        self.assertEqual(restored['model_calls'], 1)
        self.assertEqual(len(restored['pending']), 1)

    def test_unpriced_runs_are_not_restricted_by_billing_metadata(self):
        state = self.state(calls=2)
        del state['config']['cost_policy']
        request = self.run_response(state, model='served-alias', service_tier='priority')
        self.assertEqual(request.call_count, 2)
        self.assertEqual(state['reason'], 'Model-call budget exhausted')
        self.assertNotIn('cost_ledger', state)
        validate_run(state)

    def test_timeout_reservation_and_ledger_forgery(self):
        state = self.state()
        with patch('redwake.openai.request_json', side_effect=TimeoutError()):
            investigate(self.store, state, 'unused', self.model)
        self.assertEqual(costs.recheck(state)['unknown_usage_calls'], 1)
        for field, value in (('reservation_usd', '0'), ('input_tokens', 1), ('served_model', 'forged')):
            changed = copy.deepcopy(state); changed['cost_ledger'][0][field] = value
            with self.assertRaises(ValueError): costs.recheck(changed)

    def test_partial_usage_blocks_next_call_using_upper_value(self):
        state = self.state('0.02', calls=2)
        request = self.run_response(state, inputs=1800, cached=0, outputs=None)
        self.assertEqual(request.call_count, 1)
        result = costs.recheck(state)
        self.assertEqual(costs.money(result['estimated_exposure_usd']), costs.money('0.018'))
        self.assertEqual(state['reason'], 'Estimated cost budget exhausted')

    def test_reported_overrun_stops_before_proposed_tool_executes(self):
        state = self.state('0.02', calls=2)
        proposal = dict(type='function_call', call_id='call_1', name='probe',
                        arguments=json.dumps(dict(actor='alice', path='/api/documents/101')))
        self.run_response(state, inputs=100000, cached=0, output=[proposal])
        self.assertEqual(state['reason'], 'Estimated cost budget exhausted')
        self.assertEqual(state['requests'], 0)
        self.assertGreater(costs.money(costs.recheck(state)['estimated_exposure_usd']), costs.money('0.02'))
        restored = self.store.load(state['id'])
        with patch('redwake.openai.request_json', side_effect=AssertionError('no further calls')):
            investigate(self.store, restored, 'unused', self.model)
        export_run(restored, self.root / 'overrun'); verify_bundle(self.root / 'overrun')

    def test_example_card_and_cli_pricing_work_without_live_inference(self):
        from contextlib import redirect_stdout
        import io
        from redwake.cli import main
        card = json.loads(Path('examples/pricing/openai-sol.json').read_text())
        state = self.state()
        state['config']['model'] = card['model']
        state['config']['cost_policy']['rate_card'] = card
        costs.validate_policy(state['config']['cost_policy'], state['config'])
        finish = dict(type='function_call', call_id='finish', name='finish_investigation', arguments='{}')
        native = dict(model=card['model'], status='completed', service_tier='default', output=[finish],
                      usage=dict(input_tokens=10, output_tokens=10, input_tokens_details=dict(cached_tokens=0)))
        with patch.dict('os.environ', OPENAI_API_KEY='test-key'), redirect_stdout(io.StringIO()):
            # Mock only the lab context; the real adapter/runner/CLI perform all accounting.
            with patch('redwake.cli.lab') as lab, patch('redwake.openai.request_json', return_value=(200, native)):
                lab.return_value.__enter__.return_value = 'unused'
                self.assertEqual(main(['--db', str(self.root / 'cli-db'), '--reports', str(self.root / 'reports'),
                    'demo', '--backend', 'openai', '--model', card['model'],
                    '--pricing', 'examples/pricing/openai-sol.json', '--max-cost-usd', '1',
                    '--contract', 'examples/findings/contract.json']), 0)

    def test_invalid_cards_rejected(self):
        for field, value in (('service_tier', 'priority'), ('context_threshold', True),
                             ('long_input_multiplier', '0.5'), ('cache_write_12h', None),
                             ('provider', 'ollama'), ('version', True), ('cache_write_pricing', 'surcharge')):
            state = self.state(); state['config']['cost_policy']['rate_card'][field] = value
            with self.assertRaises(ValueError):
                costs.validate_policy(state['config']['cost_policy'], state['config'])
