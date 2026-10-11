import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from redwake.contracts import DISCOVERY_RESOURCES, expected_verdicts
from redwake.guidance import response_links
from redwake.lab import ACTORS, lab
from redwake.providers import TOOLS, initial_messages
from redwake.report import write_report
from redwake.runner import DISCOVERY_LIMITS, assess, discovery_checks, investigate, score
from redwake.store import Store
from redwake.transport import probe, request_json


class DiscoveryModel:
    """Uses public documentation and returned links, without importing fixture IDs."""
    def __init__(self):
        self.histories = []

    def chat(self, messages, output_limit, timeout):
        self.histories.append(copy.deepcopy(messages))
        evidence = [json.loads(m["content"]) for m in messages if m["role"] == "tool"]
        calls = [{"function": {"name": "probe", "arguments": check}}
                 for check in discovery_checks(evidence)]
        return {"message": {"role": "assistant", "tool_calls": calls, "content": ""},
                "prompt_eval_count": 50, "eval_count": 20}


class DiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name) / "runs.db")

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def state(self, mode="vulnerable", backend="baseline", **limits):
        return self.store.create({"scenario": "discovery", "mode": mode,
                                  "backend": backend, "limits": dict(DISCOVERY_LIMITS, **limits)})

    def run_lab(self, mode="vulnerable", backend="baseline", provider=None):
        with lab(mode, "discovery") as origin:
            return investigate(self.store, self.state(mode, backend), origin, provider)

    def test_discovery_matrix_and_scores(self):
        for mode in ("vulnerable", "fixed", "concealed", "broken"):
            with self.subTest(mode=mode):
                state = self.run_lab(mode)
                self.assertEqual(state["status"], "completed")
                self.assertEqual([r["verdict"] for r in assess(state["evidence"], "discovery")],
                                 expected_verdicts(mode, "discovery"))
                self.assertEqual(state["requests"], 2 if mode == "broken" else 18)
                metrics = score(state["evidence"], mode, "discovery")
                self.assertEqual(metrics["false_positives"], 0)
                self.assertEqual(metrics["missed_flaws"], 0)
                self.assertEqual(metrics["correct_findings"], 2 if mode == "vulnerable" else 0)

    def test_account_lists_and_navigation_are_protected(self):
        with lab("vulnerable", "discovery") as origin:
            alice = probe(origin, "alice", "/api/projects", scenario="discovery")
            bob = probe(origin, "bob", "/api/projects", scenario="discovery")
            self.assertNotEqual(response_links(alice["body"]), response_links(bob["body"]))
            alice_project = response_links(alice["body"])[0]
            self.assertEqual(probe(origin, "bob", alice_project, scenario="discovery")["status"], 404)
            self.assertEqual(probe(origin, "bob", alice_project + "/records", scenario="discovery")["status"], 404)
            self.assertEqual(request_json(origin + "/api/projects")[0], 401)

    def test_baseline_follows_links_before_cross_account_reads(self):
        state = self.run_lab()
        evidence = state["evidence"]
        self.assertEqual([(e["actor"], e["path"]) for e in evidence[:2]],
                         [("alice", "/api/projects"), ("bob", "/api/projects")])
        for index, e in enumerate(evidence[2:], 2):
            prior_links = [path for before in evidence[:index]
                           for path in response_links(before["body"])]
            self.assertIn(e["path"], prior_links)
        file_responses = [e for e in evidence if e["path"].startswith("/api/files/")]
        self.assertEqual(len(file_responses), 2)
        self.assertTrue(all(e["status"] == 200 for e in file_responses))

    def test_guidance_schema_and_followups_do_not_reveal_truth(self):
        text = json.dumps(initial_messages("discovery")) + json.dumps(TOOLS)
        for path, record in DISCOVERY_RESOURCES.items():
            self.assertNotIn(path, text)
            self.assertNotIn(record["marker"], text)
        self.assertNotIn("behaviour", text)
        self.assertNotIn("enum", json.dumps(TOOLS[0]["function"]["parameters"]["properties"]["path"]))
        model = DiscoveryModel()
        with patch.object(model, "chat", return_value={"message": {"role": "assistant", "content": "done"},
                         "prompt_eval_count": 1, "eval_count": 1}), lab("vulnerable", "discovery") as origin:
            state = investigate(self.store, self.state(backend="ollama", model_calls=2), origin, model)
        transcript = json.dumps(state["messages"])
        for path in DISCOVERY_RESOURCES:
            self.assertNotIn(path, transcript)
        self.assertEqual(state["requests"], 0)
        self.assertEqual(state["status"], "stopped")

    def test_model_discovers_and_finishes_with_outage_inconclusive(self):
        model = DiscoveryModel()
        state = self.run_lab(backend="ollama", provider=model)
        self.assertEqual(state["status"], "completed")
        self.assertEqual(state["requests"], 18)
        self.assertEqual(state["model_calls"], 5)
        self.assertEqual([r["verdict"] for r in assess(state["evidence"], "discovery")],
                         expected_verdicts("vulnerable", "discovery"))
        self.assertEqual(state["input_tokens"], 250)

    def test_resume_retains_discovery_frontier_and_allowances(self):
        state = self.state()
        with lab("vulnerable", "discovery") as origin:
            real_probe = probe
            calls = [0]
            def interrupt(*args, **kwargs):
                calls[0] += 1
                if calls[0] == 8:
                    raise KeyboardInterrupt()
                return real_probe(*args, **kwargs)
            with patch("redwake.runner.probe", side_effect=interrupt):
                investigate(self.store, state, origin)
        with lab("vulnerable", "discovery") as origin:
            restored = investigate(self.store, self.store.load(state["id"]), origin)
        self.assertEqual(restored["status"], "completed")
        self.assertEqual(restored["requests"], 19)
        self.assertEqual(len(restored["evidence"]), 18)
        self.assertEqual(restored["messages"][1], initial_messages("discovery")[1])

    def test_partial_run_and_report_replay_use_discovery_truth(self):
        with lab("vulnerable", "discovery") as origin:
            state = investigate(self.store, self.state(requests=6), origin)
        self.assertEqual(state["status"], "stopped")
        self.assertEqual(score(state["evidence"], "vulnerable", "discovery")["missed_flaws"], 2)
        with patch("urllib.request.OpenerDirector.open", side_effect=AssertionError("network")):
            report = write_report(self.store.load(state["id"]), self.tmp.name)
        results = json.loads(report.with_name("result.json").read_text())
        self.assertEqual(len(results["results"]), 6)
        self.assertNotIn("lab-alice", report.read_text())

    def test_scope_still_rejects_unlisted_paths(self):
        for path in ("https://example.com", "//example.com", "/api/projects?actor=bob",
                     "/api/projects/../records/doc_k4", "/api/records/unknown", "/api/files/file_x9#x"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                probe("http://127.0.0.1:1234", "alice", path, scenario="discovery")

    def test_verifier_rejects_bad_controls_and_payloads(self):
        state = self.run_lab()
        path = next(iter(DISCOVERY_RESOURCES))
        record = DISCOVERY_RESOURCES[path]
        pair = [e for e in state["evidence"] if e["path"] == path]
        owner = next(e for e in pair if e["actor"] == record["owner"])
        other = next(e for e in pair if e["actor"] != record["owner"])
        mutations = [
            [other],
            [dict(owner, status=503), other],
            [owner, dict(other, body={"owner": "bob", "data": record["marker"]})],
            [owner, dict(other, body={"owner": record["owner"], "data": "wrong"})],
            [owner, dict(other, status=503)],
            [owner, dict(other, status=403, body={"nested": [record["marker"]]})],
            [owner, dict(other, status=404, body={"data": record["marker"]})],
        ]
        for evidence in mutations:
            with self.subTest(evidence=evidence):
                self.assertEqual(assess(evidence, "discovery")[0]["verdict"], "inconclusive")
        # Later errors supersede earlier successes; stale responses cannot prove a leak.
        self.assertEqual(assess(pair + [dict(other, id=99, status=503)], "discovery")[0]["verdict"], "inconclusive")
        self.assertEqual(assess(pair, "discovery")[0]["evidence_ids"], [owner["id"], other["id"]])

    def test_verifier_does_not_trust_response_visibility(self):
        state = self.run_lab()
        evidence = copy.deepcopy(state["evidence"])
        for e in evidence:
            if e["path"] in DISCOVERY_RESOURCES and isinstance(e["body"], dict):
                e["body"]["visibility"] = "public"
        self.assertEqual(assess(evidence, "discovery")[0]["verdict"], "vulnerable")
        for e in evidence:
            e["body"]["visibility"] = "private"
        self.assertEqual(assess(evidence, "discovery")[4]["verdict"], "public_allowed")

    def test_false_positive_scoring_is_independent_of_observed_verdict(self):
        state = self.run_lab()
        metrics = score(state["evidence"], "fixed", "discovery")
        self.assertEqual(metrics["false_positives"], 2)
        self.assertEqual(metrics["correct_findings"], 0)


if __name__ == "__main__":
    unittest.main()
