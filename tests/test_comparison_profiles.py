import copy
import io
import json
import tempfile
import unittest
from contextlib import contextmanager, redirect_stdout
from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest.mock import patch

from redwake.comparison import (MODELS, PROFILES, aggregate, experiment_controls,
                                json_sha256, main, result_row, stop_category)
from redwake.contracts import DISCOVERY_RESOURCES
from redwake.lab import lab
from redwake.providers import TOOLS, initial_messages
from redwake.runner import discovery_checks, investigate
from redwake.store import Store


class SingleProbeModel:
    """Follow only response links, using one probe per call."""
    def chat(self, messages, output_limit, timeout):
        evidence = [json.loads(m["content"]) for m in messages if m["role"] == "tool"]
        check = discovery_checks(evidence)[0]
        return {"message": {"role": "assistant", "content": "", "tool_calls": [
            {"function": {"name": "probe", "arguments": check}}]},
            "prompt_eval_count": 10, "eval_count": 20}


class ComparisonProfileTests(unittest.TestCase):
    def test_profiles_change_only_intended_controls(self):
        current, sequential, batching = (PROFILES[name] for name in ("current", "sequential", "batching"))
        self.assertEqual(current.limits, batching.limits)
        self.assertEqual(current.limits, {"requests": 32, "model_calls": 16,
                                          "output_tokens": 16384, "seconds": 120})
        self.assertEqual(sequential.limits, dict(current.limits, model_calls=24, output_tokens=24576))
        first, second = experiment_controls(current), experiment_controls(sequential)
        self.assertEqual(first["initial_messages"], second["initial_messages"])
        self.assertEqual(first["initial_messages_sha256"], second["initial_messages_sha256"])
        self.assertEqual(first["tools_sha256"], json_sha256(TOOLS))
        with self.assertRaises(FrozenInstanceError):
            current.model_calls = 99
        copy_of_limits = current.limits
        copy_of_limits["requests"] = 1
        self.assertEqual(current.limits["requests"], 32)

    def test_original_prompt_unchanged_and_added_guidance_does_not_reveal_fixture(self):
        original = initial_messages("discovery")
        self.assertEqual(json_sha256(original), "742301a33f2497cdc57479547d5954ac1ec29da3fef61e9566c38a07b21065a2")
        batching = initial_messages("discovery", "batching")
        self.assertEqual(original[0], batching[0])
        self.assertTrue(batching[1]["content"].startswith(original[1]["content"]))
        text = json.dumps(batching)
        for path, record in DISCOVERY_RESOURCES.items():
            self.assertNotIn(path, text)
            self.assertNotIn(record["marker"], text)
        self.assertIn("Batch independent probes", text)
        self.assertIn("Wait for each response", text)
        with self.assertRaises(ValueError):
            initial_messages("classic", "batching")

    def test_sequential_probe_traversal_needs_eighteen_calls(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / "runs.db")
            try:
                for profile in (PROFILES["current"], PROFILES["sequential"]):
                    config = dict(experiment_controls(profile), limits=profile.limits,
                                  scenario="discovery", mode="vulnerable", backend="ollama", model=MODELS[0])
                    with self.subTest(profile=profile.name), lab("vulnerable", "discovery") as origin:
                        state = investigate(store, store.create(config), origin, SingleProbeModel())
                    row = result_row(state, 1)
                    if profile.name == "current":
                        self.assertEqual(state["status"], "stopped")
                        self.assertEqual(state["model_calls"], 16)
                        self.assertEqual(state["reason"], "Model-call budget exhausted")
                        self.assertEqual(row["record_pairs"], 10)
                    else:
                        self.assertEqual(state["status"], "completed")
                        self.assertEqual(state["model_calls"], 18)
                        self.assertEqual(state["requests"], 18)
                        self.assertEqual(row["record_pairs"], 12)
                        self.assertEqual(row["successful_owner_controls"], 5)
                        self.assertEqual(row["duplicate_probes"], 0)
                        self.assertTrue(row["correct_run"])
                    self.assertEqual(row["linked_resources"], 6)
                    self.assertEqual(row["discovery_pairs"], 6)
                    self.assertEqual(row["model_choices"]["max_batch_size"], 1)
                    self.assertEqual(state["messages"][:2], config["initial_messages"])
            finally:
                store.close()

    def test_stop_category_uses_current_reason_before_old_diagnostics(self):
        state = {"status": "stopped", "reason": "Interrupted; saved progress can be resumed",
                 "diagnostics": [{"source": "provider", "category": "interrupted"}]}
        self.assertEqual(stop_category(state), "interrupted")
        state["reason"] = "Model-call budget exhausted"
        self.assertEqual(stop_category(state), "budget")
        state["reason"] = "Provider failure (timeout); reservations retained"
        self.assertEqual(stop_category(state), "provider_failure")
        state["diagnostics"] = [{"source": "model", "category": "tool_contract"}]
        state["reason"] = "Rejected tool call outside the lab contract"
        self.assertEqual(stop_category(state), "model_choice")
        state["status"] = "completed"
        self.assertEqual(stop_category(state), "completed")

    def test_full_plan_keeps_failed_slots_and_baselines_with_fixed_controls(self):
        secret = "private-setup-error-sentinel"
        @contextmanager
        def unused_lab(*args):
            yield "unused"
        def stop_run(store, state, origin, provider=None):
            state.update(status="stopped", reason="Model-call budget exhausted")
            state["messages"] = initial_messages("discovery", state["config"]["prompt_variant"])
            store.save(state)
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "batch"
            with patch("redwake.comparison.lab", unused_lab), patch("redwake.comparison.investigate", stop_run), patch(
                    "redwake.comparison.Ollama", side_effect=RuntimeError(secret)), redirect_stdout(io.StringIO()):
                self.assertEqual(main(["--profile", "sequential", "--repeat", "1", "--directory", str(destination)]), 0)
            batch = json.loads((destination / "comparison.json").read_text())
            self.assertEqual(len(batch["rows"]), 8)
            self.assertEqual(sum(r["model"] == "baseline" for r in batch["rows"]), 2)
            self.assertTrue(all(r["status"] == "stopped" for r in batch["rows"]))
            self.assertEqual(len(batch["summary"]), 4)
            self.assertTrue(all(r["runs"] == 2 for r in batch["summary"]))
            store = Store(destination / "runs.sqlite3")
            try:
                for row in batch["rows"]:
                    state = store.load(row["run_id"])
                    self.assertEqual(state["config"]["limits"], batch["limits"])
                    for key, value in experiment_controls(PROFILES["sequential"]).items():
                        self.assertEqual(state["config"][key], value)
                        self.assertEqual(batch[key], value)
                    self.assertEqual(row, result_row(state, row["repeat"]))
                    if row["model"] != "baseline":
                        self.assertEqual(row["stop_category"], "harness_failure")
            finally:
                store.close()
            for path in destination.rglob("*"):
                if path.is_file() and path.suffix != ".sqlite3":
                    self.assertNotIn(secret.encode(), path.read_bytes())

    def test_nonempty_destination_is_preserved_without_database(self):
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / "comparison.json"
            marker.write_text("keep")
            with patch("sys.stderr"), self.assertRaises(SystemExit):
                main(["--directory", directory])
            self.assertEqual(marker.read_text(), "keep")

    def test_aggregate_does_not_pool_profiles(self):
        row = dict(model=MODELS[0], correct_findings=0, missed_flaws=2, false_positives=0,
                   requests=16, model_calls=16, input_tokens=1, output_tokens=1, seconds=1,
                   correct_run=False, usage_complete=True, stop_category="budget")
        current = dict(row, experiment_profile="current")
        sequential = dict(row, experiment_profile="sequential")
        summaries = aggregate([current, sequential])
        self.assertEqual(len(summaries), 2)
        self.assertTrue(all(r["runs"] == 1 for r in summaries))


if __name__ == "__main__":
    unittest.main()
