import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from redwake import costs
from redwake.artifacts import export_run, verify_bundle
from redwake.runner import investigate, DEFAULT_LIMITS
from redwake.store import Store


class Model:
    def chat(self,*args):
        return dict(model='nemotron-3-ultra',message=dict(role='assistant',tool_calls=[]),prompt_eval_count=1000,eval_count=100)


class CostTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.store=Store(self.root/'db');self.addCleanup(self.store.close)
        self.card=json.loads(Path('examples/pricing/ollama-ultra.json').read_text())

    def state(self,budget=None,calls=1):
        return self.store.create(dict(backend='ollama',model='nemotron-3-ultra',endpoint='https://ollama.com',mode='vulnerable',
            limits=dict(DEFAULT_LIMITS,model_calls=calls),cost_policy=dict(rate_card=copy.deepcopy(self.card),
                billing_context='free',max_cost_usd=budget,input_token_reservation=1000)))

    def test_exact_decimal_value_is_not_a_cash_charge_and_exports(self):
        state=self.state(); model=Model(); original=model.chat
        def inspect(*args):
            saved=self.store.load(state['id'])
            self.assertTrue(saved['inflight_model'])
            self.assertEqual(saved['cost_ledger'][0]['status'],'reserved')
            return original(*args)
        with patch.object(model,'chat',side_effect=inspect): investigate(self.store,state,'unused',model)
        result=costs.recheck(state)
        self.assertEqual(costs.money(result['calculated_usage_value_usd']),costs.money('0.0004'))
        self.assertIsNone(result['cash_charge_usd']);self.assertEqual(result['billing_context'],'free')
        with patch('urllib.request.OpenerDirector.open',side_effect=AssertionError('network')):
            export_run(state,self.root/'proof');verify_bundle(self.root/'proof')
        self.assertIn('cost',json.loads((self.root/'proof'/'runs'/state['id']/'result.json').read_text()))

    def test_missing_cache_split_produces_range_not_false_precision(self):
        state=self.state();state['config']['cost_policy']['rate_card']['cached_input']='0.01'
        investigate(self.store,state,'unused',Model());result=costs.recheck(state)
        self.assertIsNone(result['calculated_usage_value_usd'])
        self.assertEqual(costs.money(result['known_minimum_usd']),costs.money('0.00031'))
        self.assertEqual(costs.money(result['estimated_exposure_usd']),costs.money('0.0004'))

    def test_budget_refuses_before_inference_and_persists_on_resume(self):
        state=self.state('0.001');model=Model()
        with patch.object(model,'chat',side_effect=AssertionError('must not call')):
            investigate(self.store,state,'unused',model)
            restored=self.store.load(state['id']);investigate(self.store,restored,'unused',model)
        self.assertEqual(restored['model_calls'],0)
        self.assertEqual(restored['reason'],'Estimated cost budget exhausted')

    def test_failed_and_interrupted_calls_keep_unknown_reservations(self):
        for error in (TimeoutError(),KeyboardInterrupt()):
            with self.subTest(error=type(error).__name__):
                state=self.state();model=Model()
                with patch.object(model,'chat',side_effect=error): investigate(self.store,state,'unused',model)
                result=costs.recheck(state)
                self.assertEqual(result['unknown_usage_calls'],1);self.assertIsNone(result['calculated_usage_value_usd'])
                self.assertEqual(state['cost_ledger'][0]['status'],'unknown')
                self.assertGreater(costs.money(result['estimated_exposure_usd']),0)
                restored=self.store.load(state['id']);investigate(self.store,restored,'unused',Model())
                self.assertEqual(len(restored['cost_ledger']),1)

    def test_inflight_crash_recovery_and_partial_usage(self):
        state=self.state();costs.reserve(state,1024)
        state.update(model_calls=1,reserved_output_tokens=1024,inflight_model=True)
        self.store.save(state);investigate(self.store,state,'unused',Model())
        self.assertEqual(costs.recheck(state)['unknown_usage_calls'],1)
        state=self.state();model=Model()
        response=dict(message=dict(role='assistant',tool_calls=[]),eval_count=100)
        with patch.object(model,'chat',return_value=response):investigate(self.store,state,'unused',model)
        self.assertEqual(costs.recheck(state)['unknown_usage_calls'],1)
        self.assertEqual(state['cost_ledger'][0]['output_tokens'],100)

    def test_offline_ledger_forgery_and_invalid_rate_cards_are_rejected(self):
        state=self.state();investigate(self.store,state,'unused',Model())
        for mutate in (lambda s:s['cost_ledger'][0].update(reservation_usd='0'),
                       lambda s:s['cost_ledger'][0].update(input_tokens=999),
                       lambda s:s['config']['cost_policy']['rate_card'].update(model='other')):
            changed=copy.deepcopy(state);mutate(changed)
            with self.assertRaises(ValueError):costs.recheck(changed)
        for amount in ('NaN','Infinity','-1'):
            with self.assertRaises(ValueError):costs.money(amount)

    def test_reported_usage_exceeding_estimate_stops_before_tools(self):
        state=self.state('0.004');model=Model()
        response=dict(model='nemotron-3-ultra',message=dict(role='assistant',tool_calls=[]),prompt_eval_count=100000,eval_count=100)
        with patch.object(model,'chat',return_value=response):investigate(self.store,state,'unused',model)
        self.assertEqual(state['reason'],'Estimated cost budget exhausted')
        self.assertEqual(state['cost_ledger'][0]['status'],'reported')
        self.assertGreater(costs.money(costs.recheck(state)['estimated_exposure_usd']),costs.money('0.004'))

    def test_different_served_model_does_not_receive_requested_model_price(self):
        state=self.state(); model=Model()
        response=dict(model='different-model',message=dict(role='assistant',tool_calls=[]),prompt_eval_count=1000,eval_count=100)
        with patch.object(model,'chat',return_value=response): investigate(self.store,state,'unused',model)
        result=costs.recheck(state)
        self.assertIsNone(result['calculated_usage_value_usd'])
        self.assertEqual(result['model_mismatch_calls'],1)

    def test_missing_or_mismatched_ollama_model_stops_before_tools_and_resume(self):
        for model_name in (None, 'different-model'):
            state = self.state(calls=3)
            response = dict(model=model_name, prompt_eval_count=1000, eval_count=100,
                message=dict(role='assistant', tool_calls=[dict(function=dict(name='probe',
                    arguments=dict(actor='alice', path='/api/documents/101')))]))
            model = Model()
            with patch.object(model, 'chat', return_value=response) as chat, \
                 patch('redwake.runner.probe', side_effect=AssertionError('must not execute')):
                investigate(self.store, state, 'unused', model)
            self.assertEqual(chat.call_count, 1)
            self.assertEqual(state['reason'], 'Provider billing metadata does not match pricing policy')
            self.assertEqual(state['requests'], 0)
            result = costs.recheck(state)
            self.assertFalse(result['model_identity_verified'])
            if model_name is None:
                # Keep historical v1 report/proof valuation stable. The guard
                # blocks execution independently of its unverified estimate.
                self.assertEqual(costs.money(result['calculated_usage_value_usd']), costs.money('0.0004'))
            restored = self.store.load(state['id'])
            with patch.object(model, 'chat', side_effect=AssertionError('must not call')):
                investigate(self.store, restored, 'unused', model)
            self.assertEqual(restored['model_calls'], 1)
            self.assertFalse(costs.reserve(restored, 1024))
            export_run(restored, self.root / ('route-' + restored['id']))
            verify_bundle(self.root / ('route-' + restored['id']))

    def test_unknown_usage_with_matching_model_still_uses_estimated_reservations(self):
        state = self.state(calls=2)
        response = dict(model='nemotron-3-ultra', message=dict(role='assistant', tool_calls=[]))
        model = Model()
        with patch.object(model, 'chat', return_value=response) as chat:
            investigate(self.store, state, 'unused', model)
        self.assertEqual(chat.call_count, 2)
        self.assertEqual(costs.recheck(state)['unknown_usage_calls'], 2)

    def test_partial_usage_keeps_upper_input_value_and_blocks_next_call(self):
        state = self.state('0.015', calls=2)
        state['config']['cost_policy']['rate_card']['cached_input'] = '0.01'
        model = Model()
        # The first call fits its reservation, but reports a larger context and
        # no output usage. The unknown cache split must use the upper input rate
        # for exposure while retaining the lower rate as the known minimum.
        response = dict(model='nemotron-3-ultra',message=dict(role='assistant', tool_calls=[]),
                        prompt_eval_count=120000)
        with patch.object(model, 'chat', return_value=response) as chat:
            investigate(self.store, state, 'unused', model)
        result = costs.recheck(state)
        self.assertEqual(chat.call_count, 1)
        self.assertEqual(state['reason'], 'Estimated cost budget exhausted')
        self.assertEqual(costs.money(result['known_minimum_usd']), costs.money('0.0012'))
        self.assertEqual(costs.money(result['estimated_exposure_usd']), costs.money('0.012'))
        self.assertIsNone(result['calculated_usage_value_usd'])
        restored = self.store.load(state['id'])
        with patch.object(model, 'chat', side_effect=AssertionError('budget exhausted')):
            investigate(self.store, restored, 'unused', model)
        self.assertEqual(restored['model_calls'], 1)
        export_run(restored, self.root / 'partial-proof')
        verify_bundle(self.root / 'partial-proof')
