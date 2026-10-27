import http.client
import io
import json
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import Mock, patch

from redwake.providers import Ollama, validate_diagnostic
from redwake.report import write_report
from redwake.runner import DEFAULT_LIMITS, investigate
from redwake.store import Store
from redwake.transport import request_json


SECRET = "credential-and-private-provider-error-sentinel"


class ProviderDiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name) / "runs.db")

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def state(self, **limits):
        return self.store.create({"mode": "fixed", "backend": "ollama",
                                  "limits": dict(DEFAULT_LIMITS, **limits)})

    def model(self):
        return Ollama("test", "http://127.0.0.1:11434")

    def assert_private(self, state):
        saved = self.store.load(state["id"])
        report = write_report(saved, self.tmp.name)
        result = json.loads((report.parent / "result.json").read_text())
        self.assertNotIn(SECRET, json.dumps(saved) + report.read_text() + json.dumps(result))
        return result

    def test_http_status_failures_keep_reservations_and_only_safe_metadata(self):
        for status, category in ((401, "http_auth"), (403, "http_auth"), (429, "http_rate_limit"),
                                 (500, "http_server"), (503, "http_server"),
                                 (400, "http_other"), (302, "http_other")):
            with self.subTest(status=status), patch("redwake.providers.request_json",
                    return_value=(status, {"error": SECRET, "headers": {"Authorization": SECRET}})):
                state = investigate(self.store, self.state(), "unused", self.model())
            self.assertEqual(state["diagnostics"], [{"source": "provider", "category": category,
                                                    "http_status": status, "model_call": 1}])
            self.assertEqual(state["model_calls"], 1)
            self.assertEqual(state["reserved_output_tokens"], 1024)
            self.assertEqual(state["requests"], 0)
            self.assertFalse(state["usage_complete"])
            self.assertEqual(self.assert_private(state)["diagnostics"], state["diagnostics"])

    def test_network_protocol_and_unknown_errors_do_not_persist_text_or_names(self):
        private_exception = type("PrivateException" + SECRET, (Exception,), {})
        errors = [(TimeoutError(SECRET), "timeout"),
                  (urllib.error.URLError(TimeoutError(SECRET)), "timeout"),
                  (urllib.error.URLError(SECRET), "network"),
                  (ConnectionError(SECRET), "network"),
                  (http.client.BadStatusLine(SECRET), "response_protocol"),
                  (http.client.IncompleteRead(SECRET.encode()), "response_protocol"),
                  (json.JSONDecodeError(SECRET, SECRET, 0), "response_parse"),
                  (UnicodeDecodeError("utf8", b"\xff", 0, 1, SECRET), "response_parse"),
                  (private_exception(SECRET), "unknown"),
                  (urllib.error.HTTPError("https://" + SECRET, 429, SECRET,
                                          {"Authorization": SECRET}, io.BytesIO(SECRET.encode())),
                   "http_rate_limit")]
        for error, category in errors:
            with self.subTest(category=category), patch("redwake.providers.request_json", side_effect=error):
                state = investigate(self.store, self.state(), "unused", self.model())
            self.assertEqual(state["diagnostics"][-1]["category"], category)
            self.assertFalse(state["usage_complete"])
            self.assert_private(state)

    def test_strict_provider_transport_separates_http_parse_and_size_failures(self):
        for status, body, category in ((200, SECRET.encode(), "response_parse"),
                                       (200, b"\xff", "response_parse"),
                                       (200, b"x" * 1048577, "response_protocol"),
                                       (503, SECRET.encode(), "http_server"),
                                       (401, b"x" * 1048577, "http_auth")):
            response = io.BytesIO(body)
            response.code = status
            with self.subTest(status=status, category=category), patch(
                    "redwake.transport.urllib.request.build_opener") as opener:
                opener.return_value.open.return_value = response
                state = investigate(self.store, self.state(), "unused", self.model())
            self.assertEqual(state["diagnostics"], [{"source": "provider", "category": category,
                                                    "http_status": status, "model_call": 1}])
            self.assert_private(state)

    def test_default_lab_transport_keeps_non_json_fallback(self):
        response = io.BytesIO(SECRET.encode())
        response.code = 200
        with patch("redwake.transport.urllib.request.build_opener") as opener:
            opener.return_value.open.return_value = response
            self.assertEqual(request_json("http://127.0.0.1:11434"),
                             (200, {"error": "non-JSON response"}))

    def test_provider_errors_and_malformed_messages_never_become_evidence(self):
        responses = [({"error": SECRET}, "inference_error"),
                     ({"error": SECRET, "message": {"role": "assistant", "content": SECRET}}, "inference_error"),
                     ({"message": {"role": "assistant", "error": SECRET, "content": SECRET},
                       "prompt_eval_count": 1, "eval_count": 1}, "inference_error"),
                     ({"message": SECRET}, "response_protocol"),
                     ({"message": {"role": "tool", "content": SECRET}}, "response_protocol")]
        for response, category in responses:
            with self.subTest(category=category), patch("redwake.providers.request_json",
                    return_value=(200, response)):
                state = investigate(self.store, self.state(), "unused", self.model())
            self.assertEqual(state["diagnostics"][-1]["category"], category)
            self.assertEqual(state["evidence"], [])
            self.assertEqual(len(state["messages"]), 2)
            self.assert_private(state)

    def test_custom_provider_nested_error_is_rejected_before_transcript_append(self):
        model = Mock()
        model.chat.return_value = {"message": {"role": "assistant", "error": SECRET},
                                   "prompt_eval_count": 1, "eval_count": 1}
        state = investigate(self.store, self.state(), "unused", model)
        self.assertEqual(state["diagnostics"][-1]["category"], "inference_error")
        self.assertEqual(len(state["messages"]), 2)
        self.assertFalse(state["usage_complete"])
        self.assert_private(state)

    def test_invalid_model_choices_remain_distinct_from_provider_failure(self):
        calls = [[{"function": {"name": "probe", "arguments": {"actor": "admin", "path": "/api/projects"}}}],
                 [{"function": []}], [None]]
        for selected in calls:
            model = Mock()
            model.chat.return_value = {"message": {"role": "assistant", "tool_calls": selected},
                                       "prompt_eval_count": 5, "eval_count": 10}
            state = investigate(self.store, self.state(), "unused", model)
            self.assertEqual(state["diagnostics"], [{"source": "model", "category": "tool_contract", "model_call": 1}])
            self.assertEqual(state["messages"][-1]["tool_calls"], selected)
            self.assertTrue(state["usage_complete"])
            self.assertEqual(state["requests"], 0)

    def test_excessive_model_batch_remains_in_transcript(self):
        calls = [{"function": {"name": "probe", "arguments": {"actor": "alice", "path": "/api/documents/101"}}}] * 13
        model = Mock()
        model.chat.return_value = {"message": {"role": "assistant", "tool_calls": calls},
                                   "prompt_eval_count": 5, "eval_count": 10}
        state = investigate(self.store, self.state(), "unused", model)
        self.assertEqual(state["diagnostics"][-1]["category"], "tool_batch")
        self.assertEqual(state["messages"][-1]["tool_calls"], calls)
        self.assertEqual(state["requests"], 0)

    def test_output_overrun_is_provider_contract_failure(self):
        model = Mock()
        model.chat.return_value = {"message": {"role": "assistant", "tool_calls": []},
                                   "prompt_eval_count": 5, "eval_count": 11}
        state = investigate(self.store, self.state(output_tokens=10), "unused", model)
        self.assertEqual(state["diagnostics"], [{"source": "provider", "category": "output_budget", "model_call": 1}])
        self.assertEqual(state["reserved_output_tokens"], 10)
        self.assertEqual(state["requests"], 0)

    def test_interruption_and_resume_retain_reservations_and_unknown_usage(self):
        model = Mock()
        model.chat.side_effect = KeyboardInterrupt()
        state = investigate(self.store, self.state(model_calls=1), "unused", model)
        self.assertEqual(state["diagnostics"][-1]["category"], "interrupted")
        self.assertFalse(state["usage_complete"])
        restored = investigate(self.store, self.store.load(state["id"]), "unused", model)
        self.assertEqual(restored["model_calls"], 1)
        self.assertEqual(restored["reserved_output_tokens"], 1024)
        self.assertFalse(restored["usage_complete"])
        self.assertEqual(model.chat.call_count, 1)

    def test_saved_inflight_call_is_safely_diagnosed_on_resume(self):
        state = self.state(model_calls=1)
        state.update(model_calls=1, reserved_output_tokens=1024, inflight_model=True)
        self.store.save(state)
        state = investigate(self.store, self.store.load(state["id"]), "unused", Mock())
        self.assertEqual(state["diagnostics"], [{"source": "provider", "category": "interrupted", "model_call": 1}])
        self.assertFalse(state["usage_complete"])
        self.assert_private(state)

    def test_diagnostic_schema_rejects_arbitrary_detail_and_invalid_numbers(self):
        valid = {"source": "provider", "category": "timeout"}
        for delta in ({"detail": SECRET}, {"category": SECRET}, {"model_call": 0},
                      {"model_call": True}, {"http_status": 600}, {"http_status": "500"},
                      {"source": "model", "category": "tool_contract", "http_status": 500}):
            with self.subTest(delta=delta), self.assertRaises(ValueError):
                validate_diagnostic(dict(valid, **delta))

    def test_reports_keep_historical_shape_without_diagnostics(self):
        state = self.state()
        state.update(status="stopped", reason="Model-call budget exhausted")
        self.store.save(state)
        self.assertNotIn("diagnostics", self.assert_private(state))
