import copy
import fcntl
import hashlib
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from redwake.comparison import PROFILES, aggregate, experiment_controls, result_row
from redwake.report import write_report
from redwake.store import Store
from scripts.export_experiment import export_bundle, main
from scripts.verify_experiments import verify_bundle


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "docs/experiments/2026-10-11-discovery"
SECRET = "private-provider-error-and-credential-sentinel"


class ExportExperimentTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / "source"
        self.source.mkdir()
        self.destination = self.root / "retained"
        self.report = self.root / "reviewed.md"
        self.report.write_text("# Reviewed synthetic comparison\n\nAll planned runs, including failures.\n")

    def make_source(self, profile=None):
        original = json.loads((FIXTURE / "comparison.json").read_text())
        self.batch = {key: copy.deepcopy(value) for key, value in original.items()
                      if key not in ("rows", "summary")}
        self.batch["repeat"] = 1
        if profile:
            self.batch.update(experiment_controls(PROFILES[profile]), limits=PROFILES[profile].limits)
        self.states = {}
        store = Store(self.source / "runs.sqlite3")
        try:
            for row in original["rows"]:
                if row["repeat"] != 1:
                    continue
                run_id = row["run_id"]
                state = json.loads((FIXTURE / "runs" / run_id / "state.json").read_text())
                if profile:
                    state["config"].update(experiment_controls(PROFILES[profile]), limits=PROFILES[profile].limits)
                    if state["messages"]:
                        state["messages"][:2] = copy.deepcopy(state["config"]["initial_messages"])
                    write_report(state, self.source / "reports")
                else:
                    folder = self.source / "reports" / run_id
                    folder.mkdir(parents=True)
                    for name in ("report.md", "evidence.json", "result.json"):
                        shutil.copyfile(FIXTURE / "runs" / run_id / name, folder / name)
                self.states[run_id] = state
                store.save(state)
        finally:
            store.close()
        Path(str(self.source / "runs.sqlite3") + ".lock").touch()
        self.save_batch()

    def save_batch(self):
        self.batch["rows"] = [result_row(state, 1) for state in self.states.values()]
        self.batch["summary"] = aggregate(self.batch["rows"])
        self.write_batch()

    def write_batch(self):
        (self.source / "comparison.json").write_text(json.dumps(self.batch) + "\n")

    def save_state(self, state, regenerate=True):
        store = Store(self.source / "runs.sqlite3")
        try:
            store.save(state)
        finally:
            store.close()
        if regenerate:
            write_report(state, self.source / "reports")
        self.save_batch()

    def export(self):
        return export_bundle(self.source, self.destination, self.report)

    def test_original_bytes_every_run_and_unknown_usage_survive_offline_export(self):
        self.make_source()
        before = hashlib.sha256((self.source / "runs.sqlite3").read_bytes()).hexdigest()
        with patch("urllib.request.OpenerDirector.open", side_effect=AssertionError("Unexpected network")):
            result = self.export()
            self.assertEqual(verify_bundle(self.destination)["runs"], 8)
        self.assertEqual(result["runs"], 8)
        self.assertEqual(hashlib.sha256((self.source / "runs.sqlite3").read_bytes()).hexdigest(), before)
        for run_id, state in self.states.items():
            folder = self.destination / "runs" / run_id
            self.assertEqual(json.loads((folder / "state.json").read_text()), state)
            for name in ("report.md", "evidence.json", "result.json"):
                self.assertEqual((folder / name).read_bytes(), (self.source / "reports" / run_id / name).read_bytes())
        self.assertEqual((self.destination / "comparison.json").read_bytes(), (self.source / "comparison.json").read_bytes())
        self.assertEqual((self.destination / "report.md").read_bytes(), self.report.read_bytes())
        self.assertTrue(any(not state["usage_complete"] for state in self.states.values()))
        manifest = json.loads((self.destination / "manifest.json").read_text())
        self.assertEqual(manifest["source_database_sha256"], before)

    def test_all_profiles_retain_failed_rows_and_safe_diagnostics(self):
        for profile in PROFILES:
            with self.subTest(profile=profile):
                if (self.source / "runs.sqlite3").exists():
                    shutil.rmtree(self.source)
                    self.source.mkdir()
                self.destination = self.root / profile
                self.make_source(profile)
                state = next(s for s in self.states.values() if s["config"]["backend"] == "ollama")
                state.update(status="stopped", reason="Provider failure (http_server); reservations retained",
                             usage_complete=False, diagnostics=[{"source": "provider", "category": "http_server",
                                                               "model_call": state["model_calls"], "http_status": 503}])
                self.save_state(state)
                self.export()
                saved = json.loads((self.destination / "runs" / state["id"] / "state.json").read_text())
                self.assertEqual(saved, state)
                self.assertEqual(verify_bundle(self.destination)["runs"], 8)

    def test_existing_destination_is_never_overwritten(self):
        self.make_source()
        self.destination.mkdir()
        sentinel = self.destination / "keep"
        sentinel.write_text("unchanged")
        with self.assertRaises(ValueError):
            self.export()
        self.assertEqual(sentinel.read_text(), "unchanged")

    def test_active_lock_and_uncheckpointed_journal_are_rejected(self):
        self.make_source()
        with open(str(self.source / "runs.sqlite3") + ".lock", "rb") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            with self.assertRaises(BlockingIOError):
                self.export()
        (self.source / "runs.sqlite3-journal").write_bytes(b"active")
        with self.assertRaisesRegex(ValueError, "journal"):
            self.export()
        self.assertFalse(self.destination.exists())

    def test_missing_row_and_unplanned_database_run_are_rejected(self):
        self.make_source()
        self.batch["rows"].pop()
        self.write_batch()
        with self.assertRaises(ValueError):
            self.export()
        self.save_batch()
        extra = copy.deepcopy(next(iter(self.states.values())))
        extra["id"] = "123456abcdef"
        store = Store(self.source / "runs.sqlite3")
        try:
            store.save(extra)
        finally:
            store.close()
        with self.assertRaises(ValueError):
            self.export()

    def test_duplicate_plan_slot_rejected_with_same_run_inventory(self):
        self.make_source()
        self.batch["rows"][1]["model"] = self.batch["rows"][0]["model"]
        self.write_batch()
        with self.assertRaisesRegex(ValueError, "unplanned"):
            self.export()

    def test_active_state_and_accounting_changes_are_rejected(self):
        self.make_source()
        state = next(iter(self.states.values()))
        state["status"] = "running"
        self.save_state(state)
        with self.assertRaisesRegex(ValueError, "active"):
            self.export()
        state["status"] = "stopped"
        state["reason"] = "Request budget exhausted"
        state["requests"] = state["config"]["limits"]["requests"] + 1
        self.save_state(state)
        with self.assertRaisesRegex(ValueError, "reservations"):
            self.export()

    def test_original_result_metrics_must_match_state(self):
        self.make_source()
        state = next(iter(self.states.values()))
        path = self.source / "reports" / state["id"] / "result.json"
        result = json.loads(path.read_text())
        result["metrics"]["requests"] += 1
        path.write_text(json.dumps(result))
        with self.assertRaisesRegex(ValueError, "Original result"):
            self.export()

    def test_rejected_model_tool_call_is_preserved(self):
        self.make_source()
        state = next(s for s in self.states.values() if "Rejected" in s.get("reason", ""))
        state["pending"] = [{"function": {"name": "unknown", "arguments": {"unexpected": "retained"}}}]
        self.save_state(state)
        self.export()
        saved = json.loads((self.destination / "runs" / state["id"] / "state.json").read_text())
        self.assertEqual(saved["pending"], state["pending"])

    def test_unknown_credentials_and_unstructured_error_are_not_published(self):
        self.make_source()
        state = next(iter(self.states.values()))
        for mutation in ("configuration", "reason"):
            with self.subTest(mutation=mutation):
                if mutation == "configuration":
                    state["config"]["api_key"] = SECRET
                else:
                    state["config"].pop("api_key")
                    state.update(status="stopped", reason=SECRET)
                self.save_state(state)
                error = io.StringIO()
                with patch("sys.stderr", error):
                    self.assertEqual(main([str(self.source), str(self.destination), "--report", str(self.report)]), 1)
                self.assertNotIn(SECRET, error.getvalue())
                self.assertFalse(self.destination.exists())

    def test_unsafe_nested_controls_are_rejected(self):
        self.make_source("current")
        self.batch["controls"]["api_key"] = SECRET
        self.write_batch()
        with self.assertRaisesRegex(ValueError, "profile controls"):
            self.export()

    def test_unversioned_metadata_and_state_cannot_smuggle_profile_controls(self):
        self.make_source()
        self.batch["controls"] = {"Authorization": SECRET}
        self.write_batch()
        with self.assertRaisesRegex(ValueError, "Unversioned"):
            self.export()
        self.batch.pop("controls")
        state = next(iter(self.states.values()))
        state["config"]["controls"] = {"Authorization": SECRET}
        self.save_state(state)
        with self.assertRaisesRegex(ValueError, "Unversioned"):
            self.export()
        self.assertFalse(self.destination.exists())
