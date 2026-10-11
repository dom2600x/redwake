"""Investigation loop and deterministic evidence validation."""

import json
import time
from .lab import ACTORS, RESOURCES
from .providers import initial_messages
from .transport import probe


DEFAULT_LIMITS = {"requests": 12, "model_calls": 8, "output_tokens": 8192, "seconds": 120}


def contains_record(observation, resource):
    return bool(observation and observation["status"] == 200
                and isinstance(observation["body"], dict)
                and observation["body"].get("owner") == resource["owner"]
                and observation["body"].get("data") == resource["marker"])


def denied_record(observation, resource):
    return bool(observation and observation["status"] in (403, 404)
                and resource["marker"] not in json.dumps(observation["body"]))


def missing_checks(evidence):
    """Return absent or inconclusive observations, including failed owner controls."""
    observations = {(e["actor"], e["path"]): e for e in evidence}
    checks = []
    for path, resource in RESOURCES.items():
        for actor in ACTORS:
            observation = observations.get((actor, path))
            valid = contains_record(observation, resource)
            if resource["private"] and actor != resource["owner"]:
                valid = valid or denied_record(observation, resource)
            if not valid:
                checks.append({"actor": actor, "path": path})
    return checks


def assess(evidence):
    """Only matched successful owner/cross-account responses can prove a leak."""
    observations = {(e["actor"], e["path"]): e for e in evidence}
    results = []
    for path, resource in RESOURCES.items():
        owner = observations.get((resource["owner"], path))
        other_actor = next(a for a in ACTORS if a != resource["owner"])
        other = observations.get((other_actor, path))

        verdict = "inconclusive"
        if contains_record(owner, resource) and other:
            if resource["private"]:
                if contains_record(other, resource):
                    verdict = "vulnerable"
                elif denied_record(other, resource):
                    verdict = "protected"
            elif contains_record(other, resource):
                verdict = "public_allowed"
        results.append({"path": path, "verdict": verdict,
                        "evidence_ids": [e["id"] for e in (owner, other) if e]})
    return results


def investigate(store, state, origin, provider=None):
    if state["status"] == "completed":
        return state
    limits = state["config"]["limits"]
    started = time.monotonic()
    previous_elapsed = state["elapsed"]

    def save():
        state["elapsed"] = previous_elapsed + time.monotonic() - started
        store.save(state)

    def remaining():
        return limits["seconds"] - previous_elapsed - (time.monotonic() - started)

    def stop(reason):
        state["status"] = "stopped"
        state["reason"] = reason
        save()
        return state

    state["status"] = "running"
    state.pop("reason", None)
    if state.pop("inflight_model", False):
        state["usage_complete"] = False
        state["events"].append("Interrupted model call: reservation retained; actual usage unknown.")
    if not state["messages"]:
        state["messages"] = initial_messages()
    save()
    try:
        while True:
            if state["config"]["backend"] != "baseline" and not missing_checks(state["evidence"]):
                state["status"] = "completed"
                state["pending"] = []
                save()
                return state
            if remaining() <= 0:
                return stop("Time budget exhausted")
            if not state["pending"]:
                if state["config"]["backend"] == "baseline":
                    observed = {(e["actor"], e["path"]) for e in state["evidence"]}
                    state["pending"] = [{"function": {"name": "probe", "arguments": {
                        "actor": actor, "path": path}}} for path in RESOURCES for actor in ACTORS
                        if (actor, path) not in observed]
                    if not state["pending"]:
                        state["status"] = "completed"
                        save()
                        return state
                else:
                    if state["requests"] >= limits["requests"]:
                        return stop("Request budget exhausted")
                    if state["model_calls"] >= limits["model_calls"]:
                        return stop("Model-call budget exhausted")
                    output_limit = min(1024, limits["output_tokens"] - state["reserved_output_tokens"])
                    if output_limit <= 0 or state["output_tokens"] >= limits["output_tokens"]:
                        return stop("Output-token budget exhausted")
                    if provider is None:
                        raise ValueError("Ollama provider required")
                    state["model_calls"] += 1
                    state["reserved_output_tokens"] += output_limit
                    state["inflight_model"] = True
                    save()
                    response = provider.chat(state["messages"], output_limit, min(60, remaining()))
                    state["inflight_model"] = False
                    for key, field in (("prompt_eval_count", "input_tokens"), ("eval_count", "output_tokens")):
                        count = response.get(key)
                        if type(count) is int and count >= 0:
                            state[field] += count
                        else:
                            state["usage_complete"] = False
                    message = response["message"]
                    if message.get("role") != "assistant":
                        raise ValueError("Provider returned a non-assistant message")
                    state["messages"].append(message)
                    calls = message.get("tool_calls") or []
                    if not isinstance(calls, list) or len(calls) > 12:
                        raise ValueError("Invalid or excessive tool-call batch")
                    # The execution queue must not alias the transcript: popping a
                    # completed call must preserve the assistant's tool_calls.
                    state["pending"] = list(calls)
                    save()
                    if state["output_tokens"] > limits["output_tokens"]:
                        return stop("Provider exceeded the requested output-token budget")
                    if not calls:
                        state["messages"].append({"role": "user", "content": (
                            "The executor confirms coverage is still inconclusive. "
                            "Only role=tool messages are executed observations; any results "
                            "written in assistant content or thinking are unexecuted claims. "
                            "The following checks have NO conclusive executor evidence, even "
                            "if you previously described their results. Issue actual probe "
                            "function calls for them now; do not simulate responses or repeat "
                            "a summary. Do not repeat checks outside this list. Missing checks: "
                            + json.dumps(missing_checks(state["evidence"]))
                            + ". Remaining budget: " + json.dumps({
                                "requests": limits["requests"] - state["requests"],
                                "model_calls": limits["model_calls"] - state["model_calls"],
                                "output_tokens": max(0, limits["output_tokens"] - state["reserved_output_tokens"]),
                                "seconds": max(0, round(remaining(), 2))}))})
                        save()
                        continue
            if remaining() <= 0:
                return stop("Time budget exhausted")
            if state["requests"] >= limits["requests"]:
                return stop("Request budget exhausted")
            call = state["pending"][0]
            function = call.get("function", {}) if isinstance(call, dict) else {}
            args = function.get("arguments", {})
            if (function.get("name") != "probe" or not isinstance(args, dict)
                    or set(args) != {"actor", "path"}
                    or not isinstance(args["actor"], str) or not isinstance(args["path"], str)
                    or args["actor"] not in ACTORS or args["path"] not in RESOURCES):
                return stop("Rejected tool call outside the lab contract")
            # Reserve first; a crash can consume allowance but cannot create free retries.
            state["requests"] += 1
            save()
            evidence = probe(origin, **args, timeout=min(10, remaining()))
            evidence["id"] = len(state["evidence"]) + 1
            state["evidence"].append(evidence)
            state["pending"].pop(0)
            if state["config"]["backend"] != "baseline":
                state["messages"].append({"role": "tool", "tool_name": "probe", "content": json.dumps(evidence)})
            save()
    except KeyboardInterrupt:
        return stop("Interrupted; saved progress can be resumed")
    except Exception as exc:
        if state.pop("inflight_model", False):
            state["usage_complete"] = False
        # Exception text from network libraries may contain provider data.
        return stop("Operation failed (%s); reservations retained" % type(exc).__name__)
