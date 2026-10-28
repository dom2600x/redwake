import copy
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from redwake.compatibility import trial
from redwake.comparison import json_sha256
from redwake.providers import Ollama, TOOLS
from redwake.transcript_experiment import (CONTROLS, MODEL, NativeOllama, VARIANTS,
                                            inputs, main, plan, verify_data)


class TranscriptTests(unittest.TestCase):
    def test_individual_reductions_change_only_declared_fields(self):
        cases = inputs()
        original = cases['original']['messages']
        for variant, key in (('no_thinking', 'thinking'), ('no_function_index', 'index'), ('no_call_ids', 'id')):
            expected = copy.deepcopy(original)
            for message in expected:
                if key == 'thinking': message.pop(key, None)
                for call in message.get('tool_calls', []):
                    (call['function'] if key == 'index' else call).pop(key, None)
            self.assertEqual(cases[variant]['messages'], expected)
        self.assertEqual(cases['tail_pair']['messages'], original[:2] + original[-2:])
        combined = copy.deepcopy(original)
        for message in combined:
            message.pop('thinking', None)
            for call in message.get('tool_calls', []):
                call.pop('id', None)
                call['function'].pop('index', None)
        self.assertEqual(cases['combined_removals']['messages'], combined)
        self.assertEqual(len(cases['fresh_single']['messages']), 2)
        self.assertEqual(inputs()['original']['messages'], original)

    def test_result_correlation_preserves_content_and_matches_each_call(self):
        cases = inputs()
        original = cases['original']['messages']
        correlated = cases['correlated_results']['messages']
        for i, message in enumerate(correlated):
            expected = copy.deepcopy(original[i])
            if message['role'] == 'tool':
                expected['tool_call_id'] = original[i - 1]['tool_calls'][0]['id']
            self.assertEqual(message, expected)
        for case in cases.values():
            self.assertEqual(case['messages_sha256'], json_sha256(case['messages']))

    def test_native_and_adapter_send_identical_requests_with_same_proxy_rules(self):
        calls = []
        def request(*args, **kwargs):
            calls.append(copy.deepcopy((args, kwargs)))
            return 200, {'message': {'role': 'assistant', 'tool_calls': []}}
        with patch.dict('os.environ', {'OLLAMA_API_KEY': 'synthetic-test-key'}), patch(
                'redwake.providers.request_json', side_effect=request), patch(
                'redwake.transcript_experiment.request_json', side_effect=request):
            for provider in (Ollama(MODEL), NativeOllama(MODEL)):
                provider.chat(inputs()['original']['messages'], 1024, 60)
        self.assertEqual(calls[0], calls[1])
        self.assertTrue(calls[0][1]['use_env_proxy'])
        self.assertTrue(calls[0][1]['strict_json'])

    def test_plan_rotates_variants_and_routes_and_keeps_all_controls(self):
        slots = plan(3)
        self.assertEqual(len(slots), 96)
        self.assertEqual(sum(s['backend'] == 'ollama' for s in slots), 48)
        for variant in VARIANTS:
            for route in ('adapter', 'native'):
                self.assertEqual(sum(s['variant'] == variant and s['route'] == route for s in slots), 6)
        self.assertNotEqual(slots[0]['variant'], slots[32]['variant'])
        self.assertEqual({s['capacity'] for s in slots}, {1024})

    def test_native_errors_never_persist_response_bodies(self):
        case = inputs()['original']
        slot = dict(model=MODEL, variant='original', route='native', case='replay',
                    backend='ollama', capacity=1024)
        for status in (200, 500):
            with patch.dict('os.environ', {'OLLAMA_API_KEY': 'synthetic-test-key'}), patch(
                    'redwake.transcript_experiment.request_json',
                    return_value=(status, {'error': 'PRIVATE-PROVIDER-BODY'})):
                row = trial(slot, case, NativeOllama(MODEL))
            self.assertEqual(row['result'], 'provider_failure')
            self.assertEqual(row['output_reserved'], 1024)
            self.assertFalse(row['usage_complete'])
            self.assertNotIn('PRIVATE-PROVIDER-BODY', json.dumps(row))
            self.assertNotIn('synthetic-test-key', json.dumps(row))

    def test_offline_rechecks_plan_input_and_results(self):
        cases = inputs()
        data = dict(schema_version=1, kind='transcript_reduction', repeat=1,
                    controls=dict(CONTROLS), tools_sha256=json_sha256(TOOLS), inputs=cases, rows=[])
        for slot in plan(1):
            row = trial(dict(slot, backend='baseline'), cases[slot['variant']])
            if slot['backend'] == 'ollama':
                row.update(backend='ollama', calls_reserved=1, output_reserved=1024)
            data['rows'].append(row)
        self.assertEqual(verify_data(data), 32)
        for variant in ('omit', 'route', 'prompt', 'reservation'):
            changed = copy.deepcopy(data)
            if variant == 'omit': changed['rows'].pop()
            if variant == 'route': changed['rows'][1]['route'] = 'other'
            if variant == 'prompt': changed['inputs']['original']['messages'][0]['content'] = 'changed'
            if variant == 'reservation': changed['rows'][1]['output_reserved'] = 0
            with self.subTest(variant=variant), self.assertRaises(ValueError): verify_data(changed)

    def test_failures_are_sanitized_and_interrupt_keeps_reservation(self):
        with tempfile.TemporaryDirectory() as directory, redirect_stdout(io.StringIO()):
            destination = Path(directory) / 'trial'
            with patch('redwake.transcript_experiment.Ollama', side_effect=RuntimeError('PRIVATE-ERROR')), patch(
                    'redwake.transcript_experiment.NativeOllama', side_effect=RuntimeError('PRIVATE-ERROR')):
                self.assertEqual(main(['--directory', str(destination), '--repeat', '1']), 0)
            text = (destination / 'transcript.json').read_text()
            self.assertNotIn('PRIVATE-ERROR', text)
            interrupted = Path(directory) / 'interrupted'
            with patch('redwake.transcript_experiment.Ollama', side_effect=KeyboardInterrupt()):
                with self.assertRaises(KeyboardInterrupt): main(['--directory', str(interrupted)])
            last = json.loads((interrupted / 'transcript.json').read_text())['rows'][-1]
            self.assertEqual((last['status'], last['calls_reserved'], last['output_reserved']), ('reserved', 1, 1024))
            with self.assertRaises(FileExistsError): main(['--directory', str(interrupted)])
