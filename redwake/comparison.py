"""Repeatable live discovery comparison; retain every run, including failures."""

import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
from pathlib import Path

from .cli import positive
from .contracts import expected_verdicts, resources_for
from .lab import lab
from .providers import Ollama
from .report import write_report
from .runner import DISCOVERY_LIMITS, investigate
from .store import Store
from .verifier import assess, score


MODELS = ("gpt-oss:120b", "nemotron-3-super", "nemotron-3-ultra")
MODES = ("vulnerable", "fixed")


def result_row(state, repetition):
    verdicts = [r["verdict"] for r in assess(state["evidence"], "discovery")]
    pairs = {(e["actor"], e["path"]) for e in state["evidence"]}
    record_pairs = sum((actor, path) in pairs for path in resources_for("discovery")
                       for actor in ("alice", "bob"))
    return dict(score(state["evidence"], state["config"]["mode"], "discovery"),
                run_id=state["id"], repeat=repetition, model=state["config"]["model"],
                mode=state["config"]["mode"], status=state["status"], reason=state.get("reason"),
                correct_run=state["status"] == "completed" and verdicts == expected_verdicts(
                    state["config"]["mode"], "discovery"), verdicts=verdicts,
                record_pairs=record_pairs, requests=state["requests"], model_calls=state["model_calls"],
                input_tokens=state["input_tokens"], output_tokens=state["output_tokens"],
                reserved_output_tokens=state["reserved_output_tokens"],
                seconds=state["elapsed"], usage_complete=state["usage_complete"])


def aggregate(rows):
    result = []
    for model in ("baseline",) + MODELS:
        selected = [r for r in rows if r["model"] == model]
        if not selected:
            continue
        totals = {key: sum(r[key] for r in selected) for key in (
            "correct_findings", "missed_flaws", "false_positives", "requests", "model_calls",
            "input_tokens", "output_tokens", "seconds")}
        result.append(dict(totals, model=model, runs=len(selected),
                           correct_runs=sum(r["correct_run"] for r in selected),
                           usage_complete=all(r["usage_complete"] for r in selected),
                           mean_seconds=totals["seconds"] / len(selected)))
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeat", type=positive, default=3)
    parser.add_argument("--directory", type=Path)
    args = parser.parse_args(argv)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    directory = args.directory or Path(".redwake") / ("discovery-comparison-" + timestamp)
    directory.mkdir(parents=True, exist_ok=True)
    db = directory / "runs.sqlite3"
    # A comparison is a fresh batch. Individual interrupted runs can still be
    # resumed with the ordinary CLI using this database and their saved run IDs.
    if db.exists():
        parser.error("Comparison directory already contains a database; choose a fresh directory")
    metadata = {"started_utc": timestamp, "scenario": "discovery", "repeat": args.repeat,
                "modes": MODES, "models": MODELS, "limits": dict(DISCOVERY_LIMITS),
                "endpoint": "https://ollama.com", "temperature": 0,
                "source_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                  for p in sorted(Path(__file__).parent.glob("*.py"))}}
    rows = []
    def checkpoint():
        path = directory / "comparison.json"
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(dict(metadata, rows=rows, summary=aggregate(rows)), indent=2) + "\n")
        temporary.replace(path)
    with open(str(db) + ".lock", "w") as lock:
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
                                  "scenario": "discovery", "mode": mode, "limits": dict(DISCOVERY_LIMITS)}
                        provider = None if model == "baseline" else Ollama(model)
                        state = store.create(config)
                        print(json.dumps({"event": "started", "run_id": state["id"], "model": model,
                                          "mode": mode, "repeat": repetition}), flush=True)
                        with lab(mode, "discovery") as origin:
                            investigate(store, state, origin, provider)
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
