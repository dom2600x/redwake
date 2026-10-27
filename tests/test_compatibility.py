import copy
import json
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from redwake.compatibility import inputs, plan, trial, verify_data, verify_bundle, main
from redwake.comparison import json_sha256
from redwake.providers import ProviderError, TOOLS


class CompatibilityTests(unittest.TestCase):
    def data(self):
        cases = inputs()
        rows = []
        for slot in plan(1):
            case = cases[slot['model']][slot['case']]
            baseline = trial(dict(slot, backend='baseline'), case)
            if slot['backend'] == 'ollama':
                baseline.update(backend='ollama', calls_reserved=1, output_reserved=slot['capacity'])
            rows.append(baseline)
        return dict(schema_version=1, kind='provider_compatibility', repeat=1,
                    inputs=cases, controls=dict(temperature=0, timeout=60, retries=0,
                                               probes_executed=0, capacities=[1024, 2048]),
                    tools_sha256=json_sha256(TOOLS), rows=rows)

    def test_replay_is_exact_saved_pre_failure_context(self):
        cases = inputs()
        for model in cases:
            replay = cases[model]['replay']
            path = Path(__file__).resolve().parents[1] / 'docs/experiments/2026-10-27-discovery-batching/runs' / replay['source_run'] / 'state.json'
            source = json.loads(path.read_text())
            self.assertEqual(replay['messages'], source['messages'])
            self.assertEqual(source['diagnostics'][-1]['http_status'], 500)
            self.assertTrue(replay['baseline'])

    def test_pairing_changes_only_capacity_and_rotates_order(self):
        slots = [s for s in plan(3) if s['backend'] == 'ollama']
        self.assertEqual(len(slots), 36)
        self.assertEqual({s['capacity'] for s in slots}, {1024, 2048})
        for first, second in zip(slots[::2], slots[1::2]):
            self.assertEqual({k: v for k, v in first.items() if k != 'capacity'},
                             {k: v for k, v in second.items() if k != 'capacity'})
            self.assertNotEqual(first['capacity'], second['capacity'])
        self.assertNotEqual(slots[0]['capacity'], slots[12]['capacity'])

    def test_baseline_matches_single_and_batch_without_network(self):
        with patch('redwake.compatibility.Ollama', side_effect=AssertionError('network')):
            for name, case in inputs()['gpt-oss:120b'].items():
                row = trial(dict(backend='baseline', capacity=1024, case=name), case)
                self.assertEqual(row['result'], 'in_scope' if name == 'replay' else 'matched')
                self.assertEqual(row['calls_reserved'], 0)

    def test_failure_is_retained_without_raw_error_or_refund(self):
        case = inputs()['gpt-oss:120b']['batch_two']
        with patch('redwake.compatibility.Ollama') as provider:
            provider.return_value.chat.side_effect = ProviderError('http_server', 500)
            row = trial(dict(model='gpt-oss:120b', backend='ollama', capacity=2048, case='batch_two'), case)
        self.assertEqual(row['diagnostic']['http_status'], 500)
        self.assertEqual(row['output_reserved'], 2048)
        self.assertFalse(row['usage_complete'])
        self.assertNotIn('message', row)

    def test_capacity_and_prompt_are_forwarded_without_mutation(self):
        case = inputs()['gpt-oss:120b']['single']
        before = copy.deepcopy(case)
        with patch('redwake.compatibility.Ollama') as provider:
            provider.return_value.chat.return_value = {'message': {'role': 'assistant', 'tool_calls': []}}
            row = trial(dict(model='gpt-oss:120b', backend='ollama', capacity=2048, case='single'), case)
            args = provider.return_value.chat.call_args.args
        self.assertEqual(args, (case['messages'], 2048, 60))
        self.assertEqual(case, before)
        self.assertEqual(row['result'], 'no_tools')
        self.assertFalse(row['usage_complete'])

    def test_offline_verifier_rejects_omissions_reservation_and_result_changes(self):
        data = self.data()
        self.assertEqual(verify_data(data), 24)
        for mutation in ('omit', 'reservation', 'result', 'prompt'):
            altered = copy.deepcopy(data)
            if mutation == 'omit': altered['rows'].pop()
            if mutation == 'reservation': altered['rows'][1]['output_reserved'] = 0
            if mutation == 'result': altered['rows'][0]['result'] = 'no_tools'
            if mutation == 'prompt': altered['inputs']['gpt-oss:120b']['single']['messages'][0]['content'] = 'changed'
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                verify_data(altered)

    def test_reservation_survives_interrupt_and_destination_cannot_be_reused(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / 'experiment'
            with patch('redwake.compatibility.Ollama', side_effect=KeyboardInterrupt()):
                with self.assertRaises(KeyboardInterrupt): main(['--directory', str(destination), '--repeat', '1'])
            saved = json.loads((destination / 'compatibility.json').read_text())
            last = saved['rows'][-1]
            self.assertEqual(last['status'], 'reserved')
            self.assertEqual(last['output_reserved'], last['capacity'])
            with self.assertRaises(FileExistsError): main(['--directory', str(destination)])

    def test_bundle_hashes_and_semantics_are_checked_independently(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data = self.data()
            (root / 'compatibility.json').write_text(json.dumps(data))
            (root / 'report.md').write_text('Compatibility trials, no probes executed.')
            def rehash():
                manifest = dict(schema_version=2, kind='provider_compatibility', sha256={
                    name: hashlib.sha256((root / name).read_bytes()).hexdigest()
                    for name in ('compatibility.json', 'report.md')})
                (root / 'manifest.json').write_text(json.dumps(manifest))
            rehash()
            self.assertEqual(verify_bundle(root)['runs'], 24)
            (root / 'report.md').write_text('Changed after publication')
            with self.assertRaisesRegex(ValueError, 'hash mismatch'): verify_bundle(root)
            data['rows'][1]['output_reserved'] = 0
            (root / 'compatibility.json').write_text(json.dumps(data))
            rehash()
            with self.assertRaisesRegex(ValueError, 'Reservation'): verify_bundle(root)
