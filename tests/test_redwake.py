import copy
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from redwake.lab import ACTORS, RESOURCES, lab
from redwake.providers import Ollama
from redwake.report import write_report
from redwake.runner import DEFAULT_LIMITS, assess, investigate, missing_checks
from redwake.store import Store
from redwake.transport import probe, request_json


class FakeModel:
    def __init__(self, calls=None, responses=None):
        self.calls = calls
        self.responses = responses
        self.histories = []
        self.count = 0

    def chat(self, messages, output_limit, timeout):
        self.count += 1
        self.histories.append(copy.deepcopy(messages))
        calls = self.calls if self.calls is not None else [
            {"function": {"name": "probe", "arguments": {"actor": a, "path": p}}}
            for p in RESOURCES for a in ACTORS]
        selected = (self.responses[self.count - 1] if self.responses is not None
                    else calls if self.count == 1 else [])
        return {"message": {"role": "assistant", "content": "", "tool_calls": selected},
                "prompt_eval_count": 50, "eval_count": 20}


class RedwakeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name) / "runs.db")

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def state(self, mode="vulnerable", backend="baseline", **limits):
        return self.store.create({"mode": mode, "backend": backend,
                                  "limits": dict(DEFAULT_LIMITS, **limits)})

    def test_lab_matrix(self):
        for mode, expected in [("vulnerable", ["vulnerable"] * 2 + ["public_allowed"]),
                               ("fixed", ["protected"] * 2 + ["public_allowed"]),
                               ("concealed", ["protected"] * 2 + ["public_allowed"]),
                               ("broken", ["inconclusive"] * 3)]:
            with self.subTest(mode=mode), lab(mode) as origin:
                state = investigate(self.store, self.state(mode), origin)
                self.assertEqual(state["status"], "completed")
                self.assertEqual([r["verdict"] for r in assess(state["evidence"])], expected)

    def test_scope_rejects_paths_and_actors(self):
        for path in ["https://example.com", "//example.com", "/api/documents/101?x=1", "/api/../admin"]:
            with self.assertRaises(ValueError):
                probe("http://127.0.0.1:1234", "alice", path)
        with self.assertRaises(ValueError):
            probe("http://127.0.0.1:1234", "admin", "/api/documents/101")

    def test_scope_rejects_origin(self):
        for origin in ["http://localhost:1234", "http://127.0.0.1:1234/path", "https://example.com", "http://evil@127.0.0.1:1234"]:
            with self.assertRaises(ValueError):
                probe(origin, "alice", "/api/documents/101")

    def test_request_budget_persists_on_resume(self):
        state = self.state(requests=1)
        with lab() as origin:
            investigate(self.store, state, origin)
            restored = self.store.load(state["id"])
            investigate(self.store, restored, origin)
        self.assertEqual(restored["requests"], 1)
        self.assertEqual(len(restored["evidence"]), 1)
        self.assertEqual(restored["status"], "stopped")

    def test_resume_after_interruption(self):
        state = self.state()
        with lab("vulnerable") as origin:
            real_probe = probe
            count = [0]

            def interrupt_second(*args, **kwargs):
                count[0] += 1
                if count[0] == 2:
                    raise KeyboardInterrupt()
                return real_probe(*args, **kwargs)

            with patch("redwake.runner.probe", side_effect=interrupt_second):
                investigate(self.store, state, origin)
            self.assertEqual(len(state["evidence"]), 1)
            state = self.store.load(state["id"])
            investigate(self.store, state, origin)
        self.assertEqual(state["status"], "completed")
        self.assertEqual(len(state["evidence"]), 6)
        self.assertEqual(state["requests"], 7)

    def test_no_finding_without_owner_control(self):
        with lab("vulnerable") as origin:
            evidence = probe(origin, "bob", "/api/documents/101")
        evidence["id"] = 1
        self.assertEqual(assess([evidence])[0]["verdict"], "inconclusive")

    def test_success_status_alone_does_not_prove_leak(self):
        with lab("vulnerable") as origin:
            state = investigate(self.store, self.state(), origin)
        evidence = copy.deepcopy(state["evidence"])
        evidence[1]["body"] = {"message": "ok"}
        self.assertEqual(assess(evidence)[0]["verdict"], "inconclusive")

    def test_model_loop_and_usage(self):
        with lab("fixed") as origin:
            state = investigate(self.store, self.state("fixed", "ollama"), origin, FakeModel())
        self.assertEqual(state["status"], "completed")
        self.assertEqual(state["model_calls"], 1)
        self.assertEqual(state["output_tokens"], 20)
        self.assertEqual(state["input_tokens"], 50)

    def test_model_cannot_expand_tool_scope(self):
        model = FakeModel([{"function": {"name": "shell", "arguments": {"command": "pwd"}}}])
        state = investigate(self.store, self.state(backend="ollama"), "unused", model)
        self.assertEqual(state["requests"], 0)
        self.assertIn("Rejected", state["reason"])

    def test_model_repeated_early_finish_exhausts_budget(self):
        model = FakeModel([])
        state = investigate(self.store, self.state(backend="ollama"), "unused", model)
        self.assertEqual(state["status"], "stopped")
        self.assertEqual(state["model_calls"], DEFAULT_LIMITS["model_calls"])
        self.assertEqual(state["requests"], 0)
        self.assertIn("Model-call budget", state["reason"])
        self.assertIn("Missing checks:", model.histories[1][-1]["content"])

    def test_early_finish_prompts_only_missing_checks_then_completes(self):
        calls = FakeModel().chat([], 1024, 1)["message"]["tool_calls"]
        model = FakeModel(responses=[calls[:2], [], calls[2:]])
        with lab("fixed") as origin:
            state = investigate(self.store, self.state("fixed", "ollama"), origin, model)
        self.assertEqual(state["status"], "completed")
        self.assertEqual(state["requests"], 6)
        self.assertEqual(model.count, 3)
        prompt = model.histories[2][-1]
        self.assertEqual(prompt["role"], "user")
        self.assertNotIn("/api/documents/101", prompt["content"])
        self.assertIn("/api/invoices/inv_b7", prompt["content"])
        self.assertIn('"requests": 10', prompt["content"])
        self.assertIn('"model_calls": 6', prompt["content"])
        self.assertIn('"output_tokens": 6144', prompt["content"])
        self.assertEqual(self.store.load(state["id"])["status"], "completed")

    def test_tool_calls_remain_in_transcript_after_queue_execution(self):
        calls = FakeModel().chat([], 1024, 1)["message"]["tool_calls"]
        model = FakeModel(responses=[calls[:2], calls[2:]])
        with lab("fixed") as origin:
            state = investigate(self.store, self.state("fixed", "ollama"), origin, model)
        self.assertEqual(state["status"], "completed")
        # The next provider request must include the calls producing its tool results.
        self.assertEqual(model.histories[1][2]["tool_calls"], calls[:2])
        saved = self.store.load(state["id"])
        self.assertEqual(saved["messages"][2]["tool_calls"], calls[:2])
        self.assertEqual(saved["messages"][5]["tool_calls"], calls[2:])
        self.assertEqual(saved["pending"], [])

    def test_ollama_adapter_recovers_from_unexecuted_result_claims(self):
        calls = FakeModel().chat([], 1024, 1)["message"]["tool_calls"]
        histories = []

        def cloud_response(url, headers, payload, **kwargs):
            histories.append(copy.deepcopy(payload["messages"]))
            turn = len(histories)
            if turn == 2:
                self.assertEqual(payload["messages"][2]["tool_calls"], calls[:1])
            if turn == 3:
                self.assertEqual(payload["messages"][4]["tool_calls"], calls[1:2])
            if turn == 4:
                prompt = payload["messages"][-1]["content"]
                self.assertIn("unexecuted claims", prompt)
                self.assertIn("Issue actual probe", prompt)
                self.assertNotIn("/api/documents/101", prompt)
            selected = {1: calls[:1], 2: calls[1:2], 3: [], 4: calls[2:]}[turn]
            return 200, {"message": {"role": "assistant", "tool_calls": selected,
                                     "content": "All checks completed: simulated results" if turn == 3 else ""},
                         "prompt_eval_count": 50, "eval_count": 20}

        with patch.dict("os.environ", {"OLLAMA_API_KEY": "test-key"}), patch(
                "redwake.providers.request_json", side_effect=cloud_response), lab("vulnerable") as origin:
            state = investigate(self.store, self.state(backend="ollama"), origin, Ollama("gpt-oss:120b"))
        self.assertEqual(state["status"], "completed")
        self.assertEqual(state["model_calls"], 4)
        self.assertEqual(state["requests"], 6)
        self.assertEqual(len(state["evidence"]), 6)
        self.assertEqual([r["verdict"] for r in assess(state["evidence"])],
                         ["vulnerable", "vulnerable", "public_allowed"])

    def test_early_finish_retries_inconclusive_owner_control(self):
        calls = FakeModel().chat([], 1024, 1)["message"]["tool_calls"]
        model = FakeModel(responses=[calls, [], calls[:1]])
        attempts = [0]

        def flaky_probe(*args, **kwargs):
            attempts[0] += 1
            if attempts[0] == 1:
                return {"actor": "alice", "path": "/api/documents/101",
                        "status": 503, "body": {"error": "unavailable"}}
            return probe(*args, **kwargs)

        with lab("fixed") as origin, patch("redwake.runner.probe", side_effect=flaky_probe):
            state = investigate(self.store, self.state("fixed", "ollama"), origin, model)
        self.assertEqual(state["status"], "completed")
        self.assertEqual(state["requests"], 7)
        prompt = model.histories[2][-1]["content"]
        self.assertIn('"actor": "alice", "path": "/api/documents/101"', prompt)
        self.assertNotIn('"actor": "bob"', prompt)
        self.assertEqual(missing_checks(state["evidence"]), [])

    def test_conclusive_coverage_completes_at_exact_budget(self):
        with lab("fixed") as origin:
            state = investigate(self.store, self.state("fixed", "ollama", requests=6,
                                model_calls=1, output_tokens=1024), origin, FakeModel())
        self.assertEqual(state["status"], "completed")
        self.assertEqual(state["pending"], [])

    def test_missing_checks_stop_at_request_budget_without_extra_model_call(self):
        with lab("broken") as origin:
            model = FakeModel()
            state = investigate(self.store, self.state("broken", "ollama", requests=6), origin, model)
        self.assertEqual(state["status"], "stopped")
        self.assertEqual(state["model_calls"], 1)
        self.assertEqual(state["reason"], "Request budget exhausted")

    def test_call_budget(self):
        calls = FakeModel().chat([], 1024, 1)["message"]["tool_calls"][:1]
        with lab() as origin:
            state = investigate(self.store, self.state(backend="ollama", model_calls=1), origin, FakeModel(calls))
        self.assertEqual(state["model_calls"], 1)
        self.assertIn("Model-call", state["reason"])

    def test_token_budget(self):
        calls = FakeModel().chat([], 1024, 1)["message"]["tool_calls"][:1]
        with lab() as origin:
            state = investigate(self.store, self.state(backend="ollama", output_tokens=100), origin, FakeModel(calls))
        self.assertEqual(state["reserved_output_tokens"], 100)
        self.assertEqual(state["model_calls"], 1)

    def test_elapsed_budget(self):
        state = self.state()
        state["elapsed"] = 121
        investigate(self.store, state, "unused")
        self.assertEqual(state["requests"], 0)
        self.assertIn("Time", state["reason"])

    def test_failed_model_call_is_charged_and_usage_unknown(self):
        model = FakeModel()
        with patch.object(model, "chat", side_effect=TimeoutError()):
            state = investigate(self.store, self.state(backend="ollama"), "unused", model)
        self.assertEqual(state["model_calls"], 1)
        self.assertEqual(state["reserved_output_tokens"], 1024)
        self.assertFalse(state["usage_complete"])

    def test_report_replay_without_network(self):
        with lab() as origin:
            state = investigate(self.store, self.state("fixed"), origin)
        with patch("urllib.request.OpenerDirector.open", side_effect=AssertionError("Unexpected network")):
            path = write_report(self.store.load(state["id"]), self.tmp.name)
        self.assertIn("protected", path.read_text())
        self.assertNotIn("lab-alice", path.read_text())

    def test_cloud_key_required_and_not_sent_to_local(self):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(ValueError):
                Ollama("test")
        with patch.dict("os.environ", {"OLLAMA_API_KEY": "secret"}):
            self.assertIsNone(Ollama("test", "http://127.0.0.1:11434").key)

    def test_provider_payload_contract(self):
        response = {"message": {"role": "assistant", "content": "done"}, "eval_count": 3}
        with patch.dict("os.environ", {"OLLAMA_API_KEY": "test-key"}), patch(
                "redwake.providers.request_json", return_value=(200, response)) as request:
            Ollama("test-model").chat([], 100, 5)
        args = request.call_args.args
        self.assertEqual(args[0], "https://ollama.com/api/chat")
        self.assertEqual(args[2]["options"]["num_predict"], 100)
        self.assertFalse(args[2]["stream"])
        self.assertTrue(request.call_args.kwargs["use_env_proxy"])

    def test_local_provider_does_not_inherit_proxy_or_cloud_key(self):
        response = {"message": {"role": "assistant", "content": "done"}}
        with patch.dict("os.environ", {"OLLAMA_API_KEY": "test-key"}), patch(
                "redwake.providers.request_json", return_value=(200, response)) as request:
            Ollama("test-model", "http://127.0.0.1:11434").chat([], 100, 5)
        self.assertFalse(request.call_args.kwargs["use_env_proxy"])
        self.assertNotIn("Authorization", request.call_args.args[1])

    def test_environment_proxy_routing_keeps_lab_direct_and_refuses_redirects(self):
        visits = []

        class Proxy(BaseHTTPRequestHandler):
            def do_POST(self):
                visits.append(self.path)
                self.rfile.read(int(self.headers.get("Content-Length", 0)))
                self.send_response(302 if self.path.endswith("/redirect") else 200)
                self.send_header("Location", "http://provider.invalid/destination")
                self.end_headers()
                self.wfile.write(b'{"message":{"role":"assistant","content":"OK"}}')

            def log_message(self, *_):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Proxy)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        proxy_url = "http://127.0.0.1:%d" % server.server_port
        try:
            with patch.dict("os.environ", {"http_proxy": proxy_url, "https_proxy": proxy_url,
                                           "no_proxy": ""}, clear=True):
                # An unresolvable destination succeeds only through this proxy.
                status, body = request_json("http://provider.invalid/api/chat", payload={},
                                            use_env_proxy=True)
                self.assertEqual(status, 200)
                self.assertEqual(body["message"]["content"], "OK")
                self.assertEqual(request_json("http://provider.invalid/redirect", payload={},
                                              use_env_proxy=True)[0], 302)
                with lab() as origin:
                    self.assertEqual(probe(origin, "alice", "/api/documents/101")["status"], 200)
                    # Local provider transport also works when NO_PROXY is empty.
                    self.assertEqual(request_json(origin + "/api/documents/101",
                                                  {"Authorization": "Bearer " + ACTORS["alice"]})[0], 200)
                self.assertEqual(visits, ["http://provider.invalid/api/chat",
                                          "http://provider.invalid/redirect"])
                with self.assertRaises(ValueError):
                    request_json("http://provider.invalid/large", payload={}, limit=5,
                                 use_env_proxy=True)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_redirects_are_not_followed_and_responses_are_bounded(self):
        visits = []

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                visits.append(self.path)
                self.send_response(302 if self.path == "/redirect" else 200)
                self.send_header("Location", "/destination")
                self.end_headers()
                self.wfile.write(b'{"data":"1234567890"}')

            def log_message(self, *_):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            origin = "http://127.0.0.1:%d" % server.server_port
            self.assertEqual(request_json(origin + "/redirect")[0], 302)
            self.assertEqual(visits, ["/redirect"])
            with self.assertRaises(ValueError):
                request_json(origin + "/large", limit=5)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_interrupted_model_reservation_survives_resume(self):
        state = self.state(backend="ollama", model_calls=1)
        state.update(inflight_model=True, model_calls=1, reserved_output_tokens=1024)
        self.store.save(state)
        restored = investigate(self.store, self.store.load(state["id"]), "unused", FakeModel())
        self.assertFalse(restored["usage_complete"])
        self.assertEqual(restored["reserved_output_tokens"], 1024)
        self.assertEqual(restored["model_calls"], 1)

    def test_provider_token_overrun_stops_before_tool_execution(self):
        model = FakeModel()
        response = model.chat([], 10, 1)
        with patch.object(model, "chat", return_value=response):
            state = investigate(self.store, self.state(backend="ollama", output_tokens=10), "unused", model)
        self.assertEqual(state["requests"], 0)
        self.assertEqual(state["status"], "stopped")


if __name__ == "__main__":
    unittest.main()
