import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from redwake.comparison import aggregate, main, result_row
from redwake.providers import Ollama
from redwake.runner import DISCOVERY_LIMITS
from redwake.store import Store
from redwake.transport import request_json


class ComparisonTests(unittest.TestCase):
    def test_partial_runs_retain_misses_and_usage(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'runs.db')
            try:
                state = store.create({'scenario': 'discovery', 'mode': 'vulnerable',
                                      'backend': 'ollama', 'model': 'gpt-oss:120b',
                                      'limits': dict(DISCOVERY_LIMITS)})
                state.update(status='stopped', reason='Time budget exhausted',
                             model_calls=2, reserved_output_tokens=2048, usage_complete=False)
                row = result_row(state, 1)
            finally:
                store.close()
        self.assertFalse(row['correct_run'])
        self.assertEqual(row['missed_flaws'], 2)
        self.assertEqual(row['record_pairs'], 0)
        self.assertEqual(row['reserved_output_tokens'], 2048)
        self.assertFalse(row['usage_complete'])
        self.assertEqual(row['reason'], 'Time budget exhausted')

    def test_aggregate_keeps_failed_runs_in_denominator(self):
        first = dict(model='gpt-oss:120b', correct_findings=2, missed_flaws=0,
                     false_positives=0, requests=18, model_calls=8, input_tokens=100,
                     output_tokens=50, seconds=10, correct_run=True, usage_complete=True)
        second = dict(first, correct_findings=0, missed_flaws=2, requests=4,
                      seconds=30, correct_run=False, usage_complete=False)
        result = aggregate([first, second])[0]
        self.assertEqual(result['runs'], 2)
        self.assertEqual(result['correct_runs'], 1)
        self.assertEqual(result['correct_findings'], 2)
        self.assertEqual(result['missed_flaws'], 2)
        self.assertEqual(result['requests'], 22)
        self.assertEqual(result['mean_seconds'], 20)
        self.assertFalse(result['usage_complete'])

    def test_existing_comparison_cannot_be_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / 'runs.sqlite3'
            db.write_text('retain')
            with patch('sys.stderr'), self.assertRaises(SystemExit) as error:
                main(['--directory', directory])
            self.assertEqual(error.exception.code, 2)
            self.assertEqual(db.read_text(), 'retain')

    def test_cloud_preserves_proxy_and_local_does_not(self):
        response = (200, {'message': {'role': 'assistant', 'content': ''}})
        with patch.dict('os.environ', {'OLLAMA_API_KEY': 'synthetic'}), patch(
                'redwake.providers.request_json', return_value=response) as request:
            Ollama('test').chat([], 100, 10)
            self.assertTrue(request.call_args.kwargs['use_env_proxy'])
            Ollama('test', 'http://127.0.0.1:11434').chat([], 100, 10)
            self.assertFalse(request.call_args.kwargs['use_env_proxy'])

    def test_transport_default_explicitly_disables_environment_proxy(self):
        with patch('redwake.transport.urllib.request.ProxyHandler') as proxy, patch(
                'redwake.transport.urllib.request.build_opener') as opener:
            opener.return_value.open.side_effect = TimeoutError()
            with self.assertRaises(TimeoutError):
                request_json('http://127.0.0.1:1234')
            proxy.assert_called_once_with({})
            proxy.reset_mock()
            with self.assertRaises(TimeoutError):
                request_json('https://ollama.com/api/chat', use_env_proxy=True)
            proxy.assert_called_once_with()


if __name__ == '__main__':
    unittest.main()
