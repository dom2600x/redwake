"""Export every run of a completed comparison as a verifiable offline bundle.

The supplied report and synthetic conversations are retained verbatim. Review
that free-form content before publication; validation covers structured controls,
diagnostics, accounting, evidence and the complete experiment inventory.
"""

import argparse
from collections import Counter
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from redwake.comparison import MODELS, MODES, aggregate, result_row
from redwake.lab import ACTORS, allowed_paths
from redwake.guidance import discovery_scenario
from redwake.providers import DIAGNOSTIC_CATEGORIES, validate_diagnostic
from redwake.verifier import assess, score
from scripts.verify_experiments import verify_bundle


CONFIG_FIELDS = {"backend", "model", "endpoint", "scenario", "mode", "limits",
                 "comparison_version", "experiment_profile", "prompt_variant",
                 "initial_messages", "initial_messages_sha256", "tools_sha256", "controls", "guidance_variant"}
STATE_FIELDS = {"id", "config", "status", "reason", "requests", "model_calls",
                "input_tokens", "output_tokens", "reserved_output_tokens", "elapsed",
                "evidence", "messages", "pending", "events", "usage_complete",
                "inflight_model", "diagnostics"}
BATCH_FIELDS = CONFIG_FIELDS - {"backend", "model", "mode"} | {
    "started_utc", "repeat", "modes", "models", "temperature", "source_sha256",
    "rows", "summary", "source_revision", "source_dirty"}
REASONS = {"Time budget exhausted", "Request budget exhausted", "Model-call budget exhausted",
           "Output-token budget exhausted", "Provider exceeded the requested output-token budget",
           "Rejected tool call outside the lab contract", "Interrupted; saved progress can be resumed",
           "Operation failed; reservations retained", "Comparison setup failed; run retained",
           "Rejected invalid or excessive tool-call batch"}
ACCOUNTING = ("requests", "model_calls", "input_tokens", "output_tokens",
              "reserved_output_tokens", "usage_complete")
PROFILE_FIELDS = {"comparison_version", "experiment_profile", "prompt_variant",
                  "initial_messages", "initial_messages_sha256", "tools_sha256", "controls", "guidance_variant"}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def read_file(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError("Missing or unsupported source artifact")
    return path.read_bytes()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def known_fields(value, allowed):
    if not isinstance(value, dict) or set(value) - allowed:
        raise ValueError("Unsupported structured artifact fields")


def validate_state(state, batch):
    known_fields(state, STATE_FIELDS)
    config = state["config"]
    known_fields(config, CONFIG_FIELDS)
    model = config["model"]
    if (not discovery_scenario(config["scenario"]) or config["mode"] not in MODES
            or ('scenario' in batch and config['scenario'] != batch['scenario'])
            or model not in ("baseline",) + MODELS
            or config["backend"] != ("baseline" if model == "baseline" else "ollama")
            or config.get("endpoint") != batch["endpoint"] or config["limits"] != batch["limits"]):
        raise ValueError("Run configuration differs from comparison")
    if state["status"] not in ("completed", "stopped") or state.get("inflight_model"):
        raise ValueError("Comparison contains an active run")
    reason = state.get("reason")
    safe = REASONS | {"Provider failure (%s); reservations retained" % category
                      for category in DIAGNOSTIC_CATEGORIES["provider"]}
    if reason is not None and reason not in safe and not re.fullmatch(
            r"Operation failed \((?:RuntimeError|ValueError|TimeoutError|URLError|OSError|"
            r"ConnectionError|ProviderError)\); reservations retained", reason):
        raise ValueError("Unsupported unstructured error")
    if state["status"] == "stopped" and not reason:
        raise ValueError("Stopped run lacks reason")
    if type(state["usage_complete"]) is not bool:
        raise ValueError("Invalid usage completeness")
    for key in ACCOUNTING[:-1]:
        if type(state[key]) is not int or state[key] < 0:
            raise ValueError("Invalid usage accounting")
    if (not isinstance(state["elapsed"], (int, float)) or isinstance(state["elapsed"], bool)
            or not math.isfinite(state["elapsed"]) or state["elapsed"] < 0):
        raise ValueError("Invalid elapsed time")
    if (state["requests"] > config["limits"]["requests"]
            or state["model_calls"] > config["limits"]["model_calls"]
            or state["reserved_output_tokens"] > config["limits"]["output_tokens"]
            or state["requests"] < len(state["evidence"])):
        raise ValueError("Usage reservations differ from limits or evidence")
    for index, evidence in enumerate(state["evidence"], 1):
        if (set(evidence) != {"id", "actor", "path", "status", "body"}
                or evidence["id"] != index or evidence["actor"] not in ACTORS
                or evidence["path"] not in allowed_paths(config["scenario"])
                or type(evidence["status"]) is not int or not 100 <= evidence["status"] <= 599):
            raise ValueError("Evidence outside synthetic lab contract")
    if not isinstance(state["events"], list) or any(
            event != "Interrupted model call: reservation retained; actual usage unknown."
            for event in state["events"]):
        raise ValueError("Unsupported unstructured event")
    if not isinstance(state.get("diagnostics", []), list):
        raise ValueError("Invalid diagnostics")
    for item in state.get("diagnostics", []):
        validate_diagnostic(item)
        if item.get("model_call", 0) > state["model_calls"]:
            raise ValueError("Diagnostic call exceeds reserved calls")


def validate_batch(batch, states):
    if batch.get('suite_version') in (1, 2):
        from redwake.discovery_suite import verify_comparison
        ids = verify_comparison(batch, states)
        for state in states.values():
            validate_state(state, dict(endpoint=batch['endpoint'], limits=state['config']['limits']))
        return ids
    known_fields(batch, BATCH_FIELDS)
    if 'guidance_variant' in batch or any('guidance_variant' in state['config'] for state in states.values()):
        raise ValueError('Legacy comparisons do not support changed API guidance')
    if (batch["scenario"] != "discovery" or batch["endpoint"] not in
            ("https://ollama.com", "http://127.0.0.1:11434")
            or batch["models"] != list(MODELS) or batch["modes"] != list(MODES)
            or type(batch["repeat"]) is not int or batch["repeat"] <= 0
            or batch["temperature"] != 0):
        raise ValueError("Unsupported comparison controls")
    if not re.fullmatch(r"[0-9]{8}T[0-9]{6}Z", batch["started_utc"]):
        raise ValueError("Invalid start timestamp")
    if batch.get("source_revision") is not None and not re.fullmatch(r"[0-9a-f]{40,64}", batch["source_revision"]):
        raise ValueError("Invalid source revision")
    if batch.get("source_dirty") is not None and type(batch["source_dirty"]) is not bool:
        raise ValueError("Invalid working tree status")
    control_keys = set()
    if "comparison_version" in batch:
        from redwake.comparison import PROFILES, experiment_controls
        profile = PROFILES.get(batch.get("experiment_profile"))
        if profile is None:
            raise ValueError("Unknown comparison profile")
        controls = experiment_controls(profile)
        control_keys = set(controls)
        if any(batch.get(key) != value for key, value in controls.items()) or batch["limits"] != profile.limits:
            raise ValueError("Comparison profile controls differ")
    elif set(batch) & PROFILE_FIELDS or any(set(state["config"]) & PROFILE_FIELDS for state in states.values()):
        raise ValueError("Unversioned comparison contains unsupported profile controls")
    limits = batch["limits"]
    if set(limits) != {"requests", "model_calls", "output_tokens", "seconds"} or any(
            type(value) is not int or value <= 0 for value in limits.values()):
        raise ValueError("Invalid comparison limits")
    if not isinstance(batch["source_sha256"], dict) or any(
            not re.fullmatch(r"[a-z_]+\.py", key) or not re.fullmatch(r"[0-9a-f]{64}", value)
            for key, value in batch["source_sha256"].items()):
        raise ValueError("Invalid source fingerprints")
    rows = batch["rows"]
    ids = [row["run_id"] for row in rows]
    if len(set(ids)) != len(ids) or set(ids) != set(states):
        raise ValueError("Database and comparison inventories differ")
    expected = Counter((repeat, mode, model) for repeat in range(1, batch["repeat"] + 1)
                       for mode in MODES for model in ("baseline",) + MODELS)
    if Counter((r["repeat"], r["mode"], r["model"]) for r in rows) != expected:
        raise ValueError("Comparison is incomplete or contains unplanned runs")
    if batch["summary"] != aggregate(rows):
        raise ValueError("Comparison summary mismatch")
    for row in rows:
        state = states[row["run_id"]]
        validate_state(state, batch)
        if any(state["config"].get(key) != batch.get(key) for key in control_keys):
            raise ValueError("Run controls differ from comparison")
        if row != result_row(state, row["repeat"]):
            raise ValueError("Comparison row differs from saved state")
    return ids


def rechecked_row(state):
    config = state["config"]
    row = dict(score(state["evidence"], config["mode"], config["scenario"]),
               run_id=state["id"], backend=config["backend"], model=config["model"],
               scenario=config["scenario"], mode=config["mode"], status=state["status"],
               reason=state.get("reason"), limits=config["limits"], seconds=state["elapsed"],
               results=assess(state["evidence"], config["scenario"]))
    row.update({key: state[key] for key in ACCOUNTING})
    if state.get("diagnostics"):
        row["diagnostics"] = state["diagnostics"]
    return row


def provenance():
    def git(*args):
        try:
            return subprocess.run(["git", *args], cwd=ROOT, check=True,
                                  capture_output=True, text=True).stdout.strip()
        except (OSError, subprocess.CalledProcessError):
            return None
    dirty = git("status", "--porcelain")
    paths = sorted((ROOT / "redwake").glob("*.py")) + [Path(__file__), ROOT / "scripts/verify_experiments.py"]
    return {"repository_revision": git("rev-parse", "HEAD"),
            "working_tree_dirty": None if dirty is None else bool(dirty),
            "source_sha256": {p.relative_to(ROOT).as_posix(): digest(p.read_bytes()) for p in paths}}


def export_bundle(source, destination, report):
    source, destination, report = Path(source), Path(destination), Path(report)
    if destination.exists() or destination.is_symlink():
        raise ValueError("Destination exists; choose a fresh directory")
    database = source / "runs.sqlite3"
    read_file(database)
    with open(str(database) + ".lock", "rb") as lock:
        fcntl.flock(lock, fcntl.LOCK_SH | fcntl.LOCK_NB)
        for suffix in ("-wal", "-journal"):
            sidecar = Path(str(database) + suffix)
            if sidecar.exists() and sidecar.stat().st_size:
                raise ValueError("Active or uncheckpointed journal")
        with sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True, timeout=0) as db:
            db.execute("PRAGMA query_only=ON")
            db.execute("BEGIN")
            if db.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
                raise ValueError("Database integrity check failed")
            database_hash = digest(read_file(database))
            batch_raw = read_file(source / "comparison.json")
            batch = json.loads(batch_raw)
            states, raw_states = {}, {}
            for run_id, raw in db.execute("SELECT id, state FROM runs"):
                if not re.fullmatch(r"[0-9a-f]{12}", run_id):
                    raise ValueError("Invalid run ID")
                state = json.loads(raw)
                if state["id"] != run_id:
                    raise ValueError("State and database IDs differ")
                states[run_id], raw_states[run_id] = state, raw.encode() + b"\n"
            ids = validate_batch(batch, states)
            artifacts = {"comparison.json": batch_raw, "report.md": read_file(report)}
            rows = []
            for run_id in ids:
                state = states[run_id]
                prefix = "runs/" + run_id + "/"
                artifacts[prefix + "state.json"] = raw_states[run_id]
                for name in ("evidence.json", "result.json", "report.md"):
                    artifacts[prefix + name] = read_file(source / "reports" / run_id / name)
                row = rechecked_row(state)
                metrics = {key: row[key] for key in (
                    "correct_findings", "missed_flaws", "false_positives", "correct_verdicts", "inconclusive",
                    "requests", "model_calls", "input_tokens", "output_tokens", "seconds", "usage_complete")}
                expected_result = dict(run_id=run_id, results=row["results"], status=row["status"],
                                       scenario=state['config']['scenario'], metrics=metrics)
                if state.get("diagnostics"):
                    expected_result["diagnostics"] = state["diagnostics"]
                if (json.loads(artifacts[prefix + "result.json"]) != expected_result
                        or json.loads(artifacts[prefix + "evidence.json"]) != state["evidence"]):
                    raise ValueError("Original result or evidence differs from state")
                rows.append(row)
            if digest(read_file(database)) != database_hash or read_file(source / "comparison.json") != batch_raw:
                raise ValueError("Source changed during export")
            manifest = {"schema_version": 1, "experiment": destination.name,
                        "origin": "Offline export of a completed synthetic discovery comparison",
                        "exported_utc": datetime.now(timezone.utc).isoformat(),
                        "source_database_sha256": database_hash, "source_revision": batch.get("source_revision"),
                        "original_source_sha256": batch["source_sha256"],
                        "verification": dict(provenance(), method="Read-only SQLite and saved artifact checks; offline assess() and score()."),
                        "run_count": len(ids), "run_ids": ids,
                        "notes": ["All planned runs, including failures and unknown usage, are retained.",
                                  "Original reports, state, evidence and comparison bytes are preserved.",
                                  "Hash inventory detects changes; it does not establish authorship."]}
            destination.parent.mkdir(parents=True, exist_ok=True)
            stage = Path(tempfile.mkdtemp(prefix=".redwake-export-", dir=destination.parent))
            try:
                for relative, raw in artifacts.items():
                    path = stage / relative
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(raw)
                write_json(stage / "results.json", {"schema_version": 1, "rows": rows})
                manifest["files"] = [{"path": p.relative_to(stage).as_posix(), "bytes": p.stat().st_size,
                                      "sha256": digest(p.read_bytes())} for p in sorted(stage.rglob("*")) if p.is_file()]
                write_json(stage / "manifest.json", manifest)
                verify_bundle(stage)
                destination.mkdir()
                try:
                    for path in stage.iterdir():
                        path.rename(destination / path.name)
                except BaseException:
                    shutil.rmtree(destination)
                    raise
            finally:
                shutil.rmtree(stage)
    return {"bundle": str(destination), "runs": len(ids)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--report", type=Path, required=True, help="Reviewed Markdown report retained verbatim")
    args = parser.parse_args(argv)
    try:
        result = export_bundle(args.source, args.destination, args.report)
    except (KeyError, OSError, TypeError, ValueError, sqlite3.Error):
        print("Export failed: incomplete, active, unsafe or inconsistent source; destination must be fresh.", file=sys.stderr)
        return 1
    print("Exported %(runs)d runs to %(bundle)s; no network or model calls." % result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
