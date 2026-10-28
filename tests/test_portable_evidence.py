import copy
from contextlib import redirect_stderr, redirect_stdout
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from redwake.artifacts import export_run, verify_bundle
from redwake.cli import main
from redwake.lab import lab
from redwake.runner import DEFAULT_LIMITS, DISCOVERY_LIMITS, investigate
from redwake.store import Store


class PortableEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.database = self.root / 'runs.sqlite3'
        self.store = Store(self.database)
        self.addCleanup(self.store.close)

    def run_state(self, scenario='classic', mode='vulnerable', **limits):
        config = dict(backend='baseline', mode=mode, scenario=scenario,
                      limits=dict(DISCOVERY_LIMITS if scenario != 'classic' else DEFAULT_LIMITS, **limits))
        state = self.store.create(config)
        with lab(mode, scenario) as origin:
            investigate(self.store, state, origin)
        return state

    def rehash(self, directory):
        path = directory / 'manifest.json'
        manifest = json.loads(path.read_text())
        for entry in manifest['files']:
            raw = (directory / entry['path']).read_bytes()
            entry.update(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
        path.write_text(json.dumps(manifest))

    def test_completed_and_stopped_runs_round_trip_without_source_or_network(self):
        completed = self.run_state('discovery_deep', 'fixed')
        stopped = self.run_state(requests=1)
        for state in (completed, stopped):
            bundle = self.root / state['id']
            original = copy.deepcopy(state)
            with patch('urllib.request.OpenerDirector.open', side_effect=AssertionError('Unexpected network')):
                report = export_run(state, bundle)
                self.assertTrue(report.is_file())
                self.assertEqual(verify_bundle(bundle)['runs'], 1)
            self.assertEqual(state, original)
            saved = json.loads((bundle / 'runs' / state['id'] / 'state.json').read_text())
            self.assertEqual(saved, original)
        self.store.close()
        self.database.unlink()
        with patch('urllib.request.OpenerDirector.open', side_effect=AssertionError('Unexpected network')):
            for state in (completed, stopped):
                self.assertEqual(verify_bundle(self.root / state['id'])['runs'], 1)

    def test_cli_export_is_read_only_and_verify_does_not_create_database(self):
        state = self.run_state()
        raw = self.database.read_bytes()
        output = self.root / 'bundle'
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(main(['--db', str(self.database), 'export', state['id'], '--output', str(output)]), 0)
            missing = self.root / 'absent' / 'never.sqlite3'
            self.assertEqual(main(['--db', str(missing), 'verify', str(output)]), 0)
        self.assertEqual(self.database.read_bytes(), raw)
        self.assertFalse(missing.parent.exists())

    def test_package_only_workflow_without_credentials_or_source_database(self):
        package = self.root / 'standalone'
        package.mkdir()
        shutil.copytree(Path(__file__).resolve().parents[1] / 'redwake', package / 'redwake',
                        ignore=shutil.ignore_patterns('__pycache__'))
        env = dict(os.environ, PYTHONPATH=str(package))
        env.pop('OLLAMA_API_KEY', None)
        reports = self.root / 'standalone-reports'
        database = self.root / 'standalone.sqlite3'
        def cli(*args):
            return subprocess.run([sys.executable, '-m', 'redwake', *map(str, args)],
                                  cwd=package, env=env, capture_output=True, text=True, check=True)
        output = cli('--db', database, '--reports', reports, 'demo', '--scenario', 'discovery_deep', '--mode', 'fixed')
        run_id = output.stdout.split('Run: ')[1].splitlines()[0]
        bundle = self.root / 'standalone-proof'
        cli('--db', database, 'export', run_id, '--output', bundle)
        database.unlink()
        checked = cli('--db', database, 'verify', bundle)
        self.assertIn('1 saved run(s) verified offline', checked.stdout)
        self.assertFalse(database.exists())
        self.assertFalse((package / 'scripts').exists())

    def test_stopped_provider_usage_and_reservations_are_preserved(self):
        state = self.store.create(dict(backend='ollama', mode='vulnerable', limits=DEFAULT_LIMITS))
        state.update(status='stopped', reason='Provider failure (timeout); reservations retained',
                     model_calls=1, reserved_output_tokens=1024, usage_complete=False,
                     diagnostics=[dict(source='provider', category='timeout', model_call=1)])
        bundle = self.root / 'failure'
        export_run(state, bundle)
        saved = json.loads((bundle / 'runs' / state['id'] / 'state.json').read_text())
        self.assertFalse(saved['usage_complete'])
        self.assertEqual(saved['reserved_output_tokens'], 1024)
        self.assertEqual(verify_bundle(bundle)['runs'], 1)

    def test_existing_destination_active_run_and_invalid_scope_are_rejected(self):
        state = self.run_state()
        existing = self.root / 'existing'; existing.mkdir(); (existing / 'keep').write_text('keep')
        with self.assertRaises(ValueError): export_run(state, existing)
        self.assertEqual((existing / 'keep').read_text(), 'keep')
        for mutate in (
                lambda s: s.update(status='running'),
                lambda s: s.update(inflight_model=True),
                lambda s: s['config'].update(api_key='must-not-export'),
                lambda s: s['evidence'][0].update(path='/out-of-scope')):
            altered = copy.deepcopy(state); mutate(altered)
            with self.assertRaises(ValueError): export_run(altered, self.root / 'invalid')
            self.assertFalse((self.root / 'invalid').exists())

    def test_tampering_missing_evidence_and_semantic_forgery_are_rejected(self):
        state = self.run_state()
        for variant in ('altered', 'missing', 'forged', 'accounting'):
            with self.subTest(variant=variant):
                bundle = self.root / variant; export_run(state, bundle)
                folder = bundle / 'runs' / state['id']
                if variant == 'missing': (folder / 'evidence.json').unlink()
                elif variant == 'accounting':
                    snapshot = json.loads((folder / 'state.json').read_text()); snapshot['requests'] = 0
                    (folder / 'state.json').write_text(json.dumps(snapshot)); self.rehash(bundle)
                else:
                    result = json.loads((folder / 'result.json').read_text())
                    result['metrics']['correct_findings'] = 999
                    (folder / 'result.json').write_text(json.dumps(result))
                    if variant == 'forged': self.rehash(bundle)
                with self.assertRaises(ValueError): verify_bundle(bundle)

    def test_bad_bundle_returns_failure_without_traceback_or_db_creation(self):
        invalid = self.root / 'invalid'; invalid.mkdir(); (invalid / 'manifest.json').write_text('[]')
        with redirect_stderr(io.StringIO()) as err, redirect_stdout(io.StringIO()):
            self.assertEqual(main(['verify', str(invalid)]), 2)
            self.assertIn('verification failed', err.getvalue())
