"""Investigation loop and deterministic evidence validation."""

import json
import time
from .lab import ACTORS, allowed_paths
from .contracts import RESOURCES
from .verifier import assess, missing_checks, score, discovery_coverage
from .guidance import response_links, discovery_scenario
from .providers import ProviderError, initial_messages, provider_failure, validate_diagnostic
from .transport import probe
from . import usage


DEFAULT_LIMITS = {"requests": 12, "model_calls": 8, "output_tokens": 8192, "seconds": 120}


DISCOVERY_LIMITS = dict(DEFAULT_LIMITS, requests=32, model_calls=16, output_tokens=16384)


def discovery_checks(evidence):
    """Scripted baseline: use only documented entry points and observed links."""
    observed = {(e["actor"], e["path"]) for e in evidence}
    candidates = [(actor, "/api/projects") for actor in ACTORS]
    for e in evidence:
        if e["status"] != 200 or not isinstance(e["body"], dict):
            continue
        candidates.extend((e["actor"], path) for path in response_links(e["body"]))
        if "data" in e["body"] and "owner" in e["body"]:
            candidates.extend((actor, e["path"]) for actor in ACTORS)
        # An export can be unavailable to its owner. A discovered detail link
        # still needs both account controls, even when neither succeeds.
        if isinstance(e["body"].get("records"), list):
            candidates.extend((actor, path) for path in response_links(e["body"])
                              for actor in ACTORS)
    return [{"actor": actor, "path": path} for actor, path in
            dict.fromkeys(candidates) if (actor, path) not in observed]


def investigate(store, state, origin, provider=None):
    if state["status"] == "completed":
        return state
    limits = state["config"]["limits"]
    scenario = state["config"].get("scenario", "classic")
    priced = 'cost_policy' in state['config']
    metered = 'usage_version' in state['config']
    if metered: usage.empty_record(state['config'])
    if state['config']['backend'] in ('openai', 'anthropic') and not metered:
        raise ValueError('Direct providers require versioned usage accounting')
    if priced:
        from . import costs
        costs.validate_policy(state['config']['cost_policy'], state['config'])
    contract = state['config'].get('access_contract')
    if contract is not None:
        from .submission import check_contract
        check_contract(contract, scenario)
        if state['config']['backend'] not in ('ollama', 'openai', 'anthropic'):
            raise ValueError('Finding submission requires a model backend')
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

    def diagnose(source, category, **details):
        record = dict(source=source, category=category, **details)
        if source in ("provider", "model") and state["model_calls"] > 0:
            record["model_call"] = state["model_calls"]
        state.setdefault("diagnostics", []).append(validate_diagnostic(record))

    state["status"] = "running"
    state.pop("reason", None)
    if state.pop("inflight_model", False):
        state["usage_complete"] = False
        if priced: costs.interrupted(state)
        if metered: usage.interrupted(state)
        diagnose("provider", "interrupted")
        state["events"].append("Interrupted model call: reservation retained; actual usage unknown.")
    if not state["messages"]:
        state["messages"] = initial_messages(scenario, state["config"].get("prompt_variant", "original"),
                                             state["config"].get("guidance_variant", "standard"))
        if contract is not None:
            from .submission import guidance
            state['messages'].append(guidance(contract))
    if priced:
        costs.recheck(state)
    save()
    try:
        while True:
            if priced and costs.execution_blocked(state):
                return stop('Provider billing metadata does not match pricing policy')
            if priced:
                budget = state['config']['cost_policy']['max_cost_usd']
                if budget is not None and costs.money(costs.summary(state)['estimated_exposure_usd']) > costs.money(budget):
                    return stop('Estimated cost budget exhausted')
            if contract is None and state["config"]["backend"] != "baseline" and (discovery_coverage(state["evidence"], scenario) if discovery_scenario(scenario)
                    else not missing_checks(state["evidence"])):
                state["status"] = "completed"
                state["pending"] = []
                save()
                return state
            if remaining() <= 0:
                return stop("Time budget exhausted")
            if not state["pending"]:
                if state["config"]["backend"] == "baseline":
                    if discovery_scenario(scenario):
                        checks = discovery_checks(state["evidence"])
                    else:
                        observed = {(e["actor"], e["path"]) for e in state["evidence"]}
                        checks = [{"actor": actor, "path": path} for path in RESOURCES for actor in ACTORS
                                  if (actor, path) not in observed]
                    state["pending"] = [{"function": {"name": "probe", "arguments": check}}
                                        for check in checks]
                    if not state["pending"]:
                        state["status"] = "completed"
                        save()
                        return state
                else:
                    if contract is None and state["requests"] >= limits["requests"]:
                        return stop("Request budget exhausted")
                    if state["model_calls"] >= limits["model_calls"]:
                        return stop("Model-call budget exhausted")
                    output_limit = min(1024, limits["output_tokens"] - state["reserved_output_tokens"])
                    if output_limit <= 0 or state["output_tokens"] >= limits["output_tokens"]:
                        return stop("Output-token budget exhausted")
                    if provider is None:
                        raise ValueError("Model provider required")
                    if priced and not costs.reserve(state, output_limit):
                        return stop("Estimated cost budget exhausted")
                    if metered: usage.begin(state, output_limit)
                    state["model_calls"] += 1
                    state["reserved_output_tokens"] += output_limit
                    state["inflight_model"] = True
                    save()
                    response = provider.chat(state["messages"], output_limit, min(60, remaining()))
                    if isinstance(response, dict) and ("error" in response or
                            (isinstance(response.get("message"), dict) and "error" in response["message"])):
                        raise ProviderError("inference_error")
                    if not isinstance(response, dict) or not isinstance(response.get("message"), dict):
                        raise ProviderError("response_protocol")
                    state["inflight_model"] = False
                    for key, field in (("prompt_eval_count", "input_tokens"), ("eval_count", "output_tokens")):
                        count = response.get(key)
                        if type(count) is int and count >= 0:
                            state[field] += count
                        else:
                            state["usage_complete"] = False
                    if metered:
                        usage.received(state, response)
                    if priced:
                        costs.received(state, response)
                    if state['config']['backend'] in ('openai', 'anthropic') and response.get('provider_failure_category'):
                        category = response['provider_failure_category']
                        if category not in ('inference_error', 'response_protocol', 'inference_incomplete'):
                            category = 'response_protocol'
                        if category == 'inference_incomplete' and ('openai_output' in response['message'] or 'anthropic_content' in response['message']):
                            state['messages'].append(response['message'])
                        raise ProviderError(category)
                    if priced:
                        if costs.execution_blocked(state):
                            return stop('Provider billing metadata does not match pricing policy')
                        budget = state["config"]["cost_policy"]["max_cost_usd"]
                        if budget is not None and costs.money(costs.summary(state)["estimated_exposure_usd"]) > costs.money(budget):
                            return stop("Estimated cost budget exhausted")
                    message = response["message"]
                    if message.get("role") != "assistant":
                        raise ProviderError("response_protocol")
                    state["messages"].append(message)
                    calls = message.get("tool_calls") or []
                    if not isinstance(calls, list) or len(calls) > 12:
                        diagnose("model", "tool_batch")
                        return stop("Rejected invalid or excessive tool-call batch")
                    # The execution queue must not alias the transcript: popping a
                    # completed call must preserve the assistant's tool_calls.
                    state["pending"] = list(calls)
                    save()
                    if state["output_tokens"] > limits["output_tokens"]:
                        diagnose("provider", "output_budget")
                        return stop("Provider exceeded the requested output-token budget")
                    if not calls:
                        if contract is not None:
                            content = 'Continue using executed evidence and submit_finding, or explicitly call finish_investigation. No finding is implied by captured coverage.'
                        elif discovery_scenario(scenario):
                            content = (
                                "Continue discovery through both accounts' project listings and response links. "
                                "Use actual probe tool_calls to compare discovered records with both accounts. "
                                "Assistant claims are not executed evidence. Remaining request allowance: "
                                + str(limits["requests"] - state["requests"]))
                        else:
                            content = (
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
                                    "seconds": max(0, round(remaining(), 2))}))
                        state["messages"].append({"role": "user", "content": content})
                        save()
                        continue
            if remaining() <= 0:
                return stop("Time budget exhausted")
            if contract is None and state["requests"] >= limits["requests"]:
                return stop("Request budget exhausted")
            call = state["pending"][0]
            function = call.get("function", {}) if isinstance(call, dict) else {}
            if not isinstance(function, dict):
                diagnose("model", "tool_contract")
                return stop("Rejected tool call outside the lab contract")
            args = function.get("arguments", {})
            if contract is not None and function.get('name') in ('submit_finding', 'finish_investigation'):
                from .findings import evaluate
                try:
                    if function['name'] == 'finish_investigation':
                        if args != {}: raise ValueError('Invalid finish arguments')
                        validation = {'finished': True}
                    else:
                        validation = evaluate(contract, args, state['evidence'])
                except (ValueError, KeyError, TypeError, AttributeError):
                    diagnose('model', 'tool_contract')
                    return stop('Rejected tool call outside the lab contract')
                if function['name'] == 'submit_finding':
                    state.setdefault('submissions', []).append(dict(finding=args,
                        evidence_count=len(state['evidence']), validation=validation))
                state['pending'].pop(0)
                reply = dict(role='tool', tool_name=function['name'], content=json.dumps(validation))
                state['messages'].append(reply)
                if function['name'] == 'finish_investigation':
                    state.update(finding_finished=True, status='completed', pending=[])
                    save()
                    return state
                save()
                continue
            if (function.get("name") != "probe" or not isinstance(args, dict)
                    or set(args) != {"actor", "path"}
                    or not isinstance(args["actor"], str) or not isinstance(args["path"], str)
                    or args["actor"] not in ACTORS or args["path"] not in allowed_paths(scenario)):
                diagnose("model", "tool_contract")
                return stop("Rejected tool call outside the lab contract")
            if state["requests"] >= limits["requests"]:
                return stop("Request budget exhausted")
            # Reserve first; a crash can consume allowance but cannot create free retries.
            state["requests"] += 1
            save()
            probe_options = {"scenario": scenario} if scenario != "classic" else {}
            evidence = probe(origin, **args, timeout=min(10, remaining()), **probe_options)
            evidence["id"] = len(state["evidence"]) + 1
            state["evidence"].append(evidence)
            state["pending"].pop(0)
            if state["config"]["backend"] != "baseline":
                state["messages"].append({"role": "tool", "tool_name": "probe", "content": json.dumps(evidence)})
            save()
    except KeyboardInterrupt:
        if priced: costs.interrupted(state)
        if metered: usage.interrupted(state)
        if state.pop("inflight_model", False):
            state["usage_complete"] = False
            diagnose("provider", "interrupted")
        return stop("Interrupted; saved progress can be resumed")
    except Exception as exc:
        if priced: costs.interrupted(state)
        if metered: usage.interrupted(state)
        inflight = state.pop("inflight_model", False)
        if inflight:
            state["usage_complete"] = False
        if inflight or isinstance(exc, ProviderError):
            failure = provider_failure(exc).diagnostic
            diagnose(**failure)
            return stop("Provider failure (%s); reservations retained" % failure["category"])
        diagnose("harness", "unknown")
        return stop("Operation failed; reservations retained")
