"""Repeatable live discovery comparison; retain every run, including failures."""

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import fcntl
import hashlib
import json
from pathlib import Path
import subprocess
from types import MappingProxyType

from .cli import positive
from .contracts import expected_verdicts, resources_for
from .guidance import response_links
from .lab import lab
from .providers import Ollama, TOOLS, initial_messages
from .report import write_report
from .runner import investigate
from .store import Store
from .verifier import assess, contains_record, score


MODELS = ("gpt-oss:120b", "nemotron-3-super", "nemotron-3-ultra")
MODES = ("vulnerable", "fixed")
COMPARISON_VERSION = 2


@dataclass(frozen=True)
class ExperimentProfile:
    name: str
    model_calls: int
    output_tokens: int
    prompt_variant: str = "original"
    requests: int = 32
    seconds: int = 120

    @property
    def limits(self):
        return {"requests": self.requests, "model_calls": self.model_calls,
                "output_tokens": self.output_tokens, "seconds": self.seconds}


PROFILES = MappingProxyType({
    "current": ExperimentProfile("current", 16, 16384),
    # Eighteen single-probe calls reproduce the scripted traversal; six more
    # provide headroom. Reservations must rise too or they still stop at 16.
    "sequential": ExperimentProfile("sequential", 24, 24576),
    "batching": ExperimentProfile("batching", 16, 16384, "batching"),
})


def json_sha256(value):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    return hashlib.sha256(raw).hexdigest()


def experiment_controls(profile):
    messages = initial_messages("discovery", profile.prompt_variant)
    return {"comparison_version": COMPARISON_VERSION, "experiment_profile": profile.name,
            "prompt_variant": profile.prompt_variant, "initial_messages": messages,
            "initial_messages_sha256": json_sha256(messages), "tools_sha256": json_sha256(TOOLS),
            "controls": {"temperature": 0, "max_output_tokens_per_call": 1024,
                         "max_tool_calls_per_message": 12, "provider_timeout_seconds": 60,
                         "execution": "serial", "model_order": "rotating",
                         "retries": 0, "resume": False}}


def source_provenance():
    """Record revision and actual module bytes, including uncommitted changes."""
    root = Path(__file__).resolve().parents[1]
    def git(*args):
        try:
            return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True,
                                  text=True).stdout.strip()
        except (OSError, subprocess.CalledProcessError):
            return None
    dirty = git("status", "--porcelain", "--untracked-files=normal")
    return {"source_revision": git("rev-parse", "HEAD"),
            "source_dirty": None if dirty is None else bool(dirty),
            "source_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in sorted(Path(__file__).parent.glob("*.py"))}}


def stop_category(state):
    if state["status"] == "completed":
        return "completed"
    # Diagnostics persist on resume; classify the current terminal reason first.
    if state.get("reason") in {"Time budget exhausted", "Request budget exhausted",
                               "Model-call budget exhausted", "Output-token budget exhausted"}:
        return "budget"
    if state.get("reason", "").startswith("Interrupted"):
        return "interrupted"
    diagnostics = state.get("diagnostics", [])
    if diagnostics:
        return {"provider": "provider_failure", "model": "model_choice",
                "harness": "harness_failure"}.get(diagnostics[-1]["source"], "harness_failure")
    return "other"


def result_row(state, repetition):
    verdicts = [r["verdict"] for r in assess(state["evidence"], "discovery")]
    pairs = {(e["actor"], e["path"]) for e in state["evidence"]}
    resources = resources_for("discovery")
    record_pairs = sum((actor, path) in pairs for path in resources
                       for actor in ("alice", "bob"))
    row = dict(score(state["evidence"], state["config"]["mode"], "discovery"),
                run_id=state["id"], repeat=repetition, model=state["config"]["model"],
                mode=state["config"]["mode"], status=state["status"], reason=state.get("reason"),
                correct_run=state["status"] == "completed" and verdicts == expected_verdicts(
                    state["config"]["mode"], "discovery"), verdicts=verdicts,
                record_pairs=record_pairs, requests=state["requests"], model_calls=state["model_calls"],
                input_tokens=state["input_tokens"], output_tokens=state["output_tokens"],
                reserved_output_tokens=state["reserved_output_tokens"],
                seconds=state["elapsed"], usage_complete=state["usage_complete"])
    # Retained historical experiments must keep their original row shape.
    if state["config"].get("comparison_version") == COMPARISON_VERSION:
        links = {path for e in state["evidence"] if e["status"] == 200
                 for path in response_links(e["body"])}
        observations = {(e["actor"], e["path"]): e for e in state["evidence"]}
        messages = [m for m in state["messages"] if m.get("role") == "assistant"]
        batches = [m.get("tool_calls") or [] for m in messages]
        sizes = [len(batch) for batch in batches if isinstance(batch, list)]
        limits = state["config"]["limits"]
        row.update(comparison_version=COMPARISON_VERSION,
                   experiment_profile=state["config"]["experiment_profile"],
                   linked_resources=len(links.intersection(resources)),
                   discovery_pairs=sum(path not in resources for _, path in pairs),
                   successful_owner_controls=sum(contains_record(observations.get((r["owner"], path)), r)
                                                 for path, r in resources.items()),
                   duplicate_probes=len(state["evidence"]) - len(pairs),
                   model_choices={"assistant_turns": len(messages),
                                  "no_tool_turns": sum(size == 0 for size in sizes),
                                  "max_batch_size": max(sizes, default=0)},
                   budget_remaining={"requests": max(0, limits["requests"] - state["requests"]),
                                     "model_calls": max(0, limits["model_calls"] - state["model_calls"]),
                                     "output_tokens": max(0, limits["output_tokens"] - state["reserved_output_tokens"]),
                                     "seconds": max(0, limits["seconds"] - state["elapsed"])},
                   stop_category=stop_category(state), diagnostics=state.get("diagnostics", []))
    return row


def aggregate(rows):
    result = []
    for profile in dict.fromkeys(r.get("experiment_profile") for r in rows):
        for model in ("baseline",) + MODELS:
            selected = [r for r in rows if r["model"] == model and r.get("experiment_profile") == profile]
            if not selected:
                continue
            totals = {key: sum(r[key] for r in selected) for key in (
                "correct_findings", "missed_flaws", "false_positives", "requests", "model_calls",
                "input_tokens", "output_tokens", "seconds")}
            item = dict(totals, model=model, runs=len(selected),
                        correct_runs=sum(r["correct_run"] for r in selected),
                        usage_complete=all(r["usage_complete"] for r in selected),
                        mean_seconds=totals["seconds"] / len(selected))
            if profile is not None:
                item.update(comparison_version=COMPARISON_VERSION, experiment_profile=profile,
                            stop_categories={category: sum(r["stop_category"] == category for r in selected)
                                             for category in ("completed", "budget", "provider_failure",
                                                              "model_choice", "harness_failure", "interrupted", "other")})
            result.append(item)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeat", type=positive, default=3)
    parser.add_argument("--directory", type=Path)
    parser.add_argument("--profile", choices=tuple(PROFILES), default="current")
    args = parser.parse_args(argv)
    profile = PROFILES[args.profile]
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    directory = args.directory or Path(".redwake") / ("discovery-comparison-" + profile.name + "-" + timestamp)
    directory.mkdir(parents=True, exist_ok=True)
    db = directory / "runs.sqlite3"
    # A comparison is a fresh batch. Individual interrupted runs can still be
    # resumed with the ordinary CLI using this database and their saved run IDs.
    if any(directory.iterdir()):
        parser.error("Comparison directory is not empty; choose a fresh directory")
    metadata = {"started_utc": timestamp, "scenario": "discovery", "repeat": args.repeat,
                "modes": MODES, "models": MODELS, "limits": profile.limits,
                "endpoint": "https://ollama.com", "temperature": 0,
                **experiment_controls(profile), **source_provenance()}
    rows = []
    def checkpoint():
        path = directory / "comparison.json"
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(dict(metadata, rows=rows, summary=aggregate(rows)), indent=2) + "\n")
        temporary.replace(path)
    # Claim a fresh directory atomically against other comparison processes.
    try:
        lock = open(str(db) + ".lock", "x")
    except FileExistsError:
        parser.error("Comparison is already claimed; choose a fresh directory")
    with lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        store = Store(db)
        try:
            checkpoint()
            for repetition in range(1, args.repeat + 1):
                for mode_index, mode in enumerate(MODES):
                    # Serial execution avoids concurrent inference distorting
                    # elapsed time. Rotate model order between blocks.
                    offset = (repetition - 1 + mode_index) % len(MODELS)
                    ordered = MODELS[offset:] + MODELS[:offset]
                    for model in ("baseline",) + ordered:
                        config = {"backend": "baseline" if model == "baseline" else "ollama",
                                  "model": model, "endpoint": metadata["endpoint"],
                                  "scenario": "discovery", "mode": mode, "limits": profile.limits,
                                  **experiment_controls(profile)}
                        state = store.create(config)
                        print(json.dumps({"event": "started", "run_id": state["id"], "model": model,
                                          "mode": mode, "repeat": repetition,
                                          "experiment_profile": profile.name}), flush=True)
                        try:
                            provider = None if model == "baseline" else Ollama(model)
                            with lab(mode, "discovery") as origin:
                                investigate(store, state, origin, provider)
                        except Exception:
                            # Setup failure is an observed batch outcome too.
                            state.update(status="stopped", reason="Comparison setup failed; run retained")
                            state.setdefault("diagnostics", []).append({"source": "harness", "category": "unknown"})
                            store.save(state)
                        write_report(state, directory / "reports")
                        row = result_row(state, repetition)
                        rows.append(row)
                        checkpoint()
                        print(json.dumps(dict(event="finished", **row)), flush=True)
            print(str((directory / "comparison.json").resolve()), flush=True)
        finally:
            store.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
