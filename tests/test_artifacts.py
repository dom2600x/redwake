import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts.verify_experiments import verify_bundle


ROOT = Path(__file__).resolve().parents[1]
MAC_BUNDLE = ROOT / 'docs' / 'experiments' / '2026-10-10-mac'
COMPLETED_RUN = '967fe3851ee8'
STOPPED_RUN = 'b253ac173c7e'


class ArtifactTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.bundle = Path(self.temporary.name) / 'retained-experiment'
        self.bundle.mkdir()

    def make_bundle(self, run_id=COMPLETED_RUN):
        """Use an original saved run, without starting a lab or model."""
        source = MAC_BUNDLE / 'runs' / run_id
        destination = self.bundle / 'runs' / run_id
        destination.mkdir(parents=True)
        for name in ('state.json', 'evidence.json', 'result.json'):
            shutil.copyfile(source / name, destination / name)
        rows = json.loads((MAC_BUNDLE / 'results.json').read_text())['rows']
        row = next(row for row in rows if row['run_id'] == run_id)
        self.write_json('results.json', {'rows': [row]})
        self.rehash_bundle(run_id)
        return destination

    def write_json(self, relative, value):
        (self.bundle / relative).write_text(json.dumps(value) + '\n')

    def rehash_bundle(self, run_id=COMPLETED_RUN):
        """Renew hashes so semantic checks must catch internally altered data."""
        files = []
        for path in sorted(self.bundle.rglob('*')):
            if path.is_file() and path.name != 'manifest.json':
                raw = path.read_bytes()
                files.append({'path': path.relative_to(self.bundle).as_posix(),
                              'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()})
        self.write_json('manifest.json', {'schema_version': 1, 'files': files,
                                          'run_ids': [run_id], 'run_count': 1})

    def test_saved_mac_run_verifies_offline(self):
        self.make_bundle()
        self.assertEqual(verify_bundle(self.bundle),
                         {'bundle': 'retained-experiment', 'runs': 1, 'files': 4})

    def test_artifact_tampering_is_detected(self):
        folder = self.make_bundle()
        evidence = folder / 'evidence.json'
        evidence.write_bytes(evidence.read_bytes() + b' ')
        with self.assertRaisesRegex(ValueError, 'Artifact hash mismatch'):
            verify_bundle(self.bundle)

    def test_missing_saved_evidence_is_detected(self):
        folder = self.make_bundle()
        (folder / 'evidence.json').unlink()
        with self.assertRaisesRegex(ValueError, 'Missing or unsupported artifact'):
            verify_bundle(self.bundle)

    def test_evidence_must_match_saved_state_after_rehashing(self):
        folder = self.make_bundle()
        evidence = json.loads((folder / 'evidence.json').read_text())
        evidence[0]['status'] = 503
        self.write_json('runs/' + COMPLETED_RUN + '/evidence.json', evidence)
        self.rehash_bundle()
        with self.assertRaisesRegex(ValueError, 'State, evidence or verdict mismatch'):
            verify_bundle(self.bundle)

    def test_saved_leak_needs_successful_owner_control_after_rehashing(self):
        folder = self.make_bundle()
        evidence = json.loads((folder / 'evidence.json').read_text())
        # The cross-account private response alone cannot retain a proven leak.
        owner = next(item for item in evidence
                     if item['actor'] == 'alice' and item['path'] == '/api/documents/101')
        owner.update(status=503, body={'error': 'temporarily unavailable'})
        state = json.loads((folder / 'state.json').read_text())
        state['evidence'] = evidence
        self.write_json('runs/' + COMPLETED_RUN + '/evidence.json', evidence)
        self.write_json('runs/' + COMPLETED_RUN + '/state.json', state)
        self.rehash_bundle()
        with self.assertRaisesRegex(ValueError, 'State, evidence or verdict mismatch'):
            verify_bundle(self.bundle)

    def test_scores_are_recomputed_from_evidence_after_rehashing(self):
        self.make_bundle()
        results = json.loads((self.bundle / 'results.json').read_text())
        results['rows'][0]['correct_findings'] = 0
        self.write_json('results.json', results)
        self.rehash_bundle()
        with self.assertRaisesRegex(ValueError, 'Score mismatch'):
            verify_bundle(self.bundle)

    def test_stopped_run_keeps_status_and_usage_accounting(self):
        folder = self.make_bundle(STOPPED_RUN)
        original_state = json.loads((folder / 'state.json').read_text())
        row = json.loads((self.bundle / 'results.json').read_text())['rows'][0]
        self.assertEqual(row['status'], 'stopped')
        self.assertEqual(row['reason'], original_state['reason'])
        self.assertGreater(row['reserved_output_tokens'], 0)
        self.assertEqual(row['correct_findings'], 1)
        self.assertEqual(row['missed_flaws'], 1)
        self.assertEqual(verify_bundle(self.bundle)['runs'], 1)
        self.assertEqual(json.loads((folder / 'state.json').read_text()), original_state)

        for field, incorrect in (('status', 'completed'),
                                 ('reason', 'Different stop reason'),
                                 ('reserved_output_tokens', 0),
                                 ('usage_complete', not row['usage_complete']),
                                 ('seconds', row['seconds'] + 1)):
            with self.subTest(field=field):
                altered = dict(row, **{field: incorrect})
                self.write_json('results.json', {'rows': [altered]})
                self.rehash_bundle(STOPPED_RUN)
                with self.assertRaises(ValueError):
                    verify_bundle(self.bundle)

    def test_checked_in_experiment_bundles_verify_offline(self):
        bundles = sorted((ROOT / 'docs' / 'experiments').glob('*/manifest.json'))
        self.assertTrue(bundles, 'Expected retained experiment manifests')
        for manifest in bundles:
            with self.subTest(bundle=manifest.parent.name):
                result = verify_bundle(manifest.parent)
                self.assertGreater(result['runs'], 0)


if __name__ == '__main__':
    unittest.main()
