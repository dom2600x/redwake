"""Check retained experiment files and reclassify saved evidence offline."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from redwake.verifier import assess, score


def verify_comparison_controls(batch, states):
    """Recheck v2 treatment equality without rewriting historical batch rules."""
    if batch.get("comparison_version") != 2:
        return
    from redwake.comparison import json_sha256
    from redwake.providers import validate_diagnostic
    shared = ("comparison_version", "experiment_profile", "prompt_variant",
              "initial_messages", "initial_messages_sha256", "tools_sha256",
              "controls", "limits", "endpoint", "scenario")
    if (batch["initial_messages_sha256"] != json_sha256(batch["initial_messages"])
            or type(batch["repeat"]) is not int or batch["repeat"] <= 0):
        raise ValueError("Invalid comparison prompt or repetition count")
    expected = Counter((repeat, mode, model) for repeat in range(1, batch["repeat"] + 1)
                       for mode in batch["modes"] for model in ["baseline"] + batch["models"])
    actual = Counter((row["repeat"], row["mode"], row["model"]) for row in batch["rows"])
    if actual != expected or len(batch["rows"]) != len(states):
        raise ValueError("Comparison plan differs from retained runs")
    for row in batch["rows"]:
        state = states[row["run_id"]]
        if any(state["config"].get(key) != batch[key] for key in shared):
            raise ValueError("Run controls differ from comparison")
        if state["messages"]:
            if state["messages"][:len(batch["initial_messages"])] != batch["initial_messages"]:
                raise ValueError("Executed prompt differs from comparison")
        elif state["model_calls"] or state["requests"] or state["status"] != "stopped":
            raise ValueError("Executed run lacks its initial prompt")
        for diagnostic in state.get("diagnostics", []):
            validate_diagnostic(diagnostic)
            if diagnostic.get("model_call", 0) > state["model_calls"]:
                raise ValueError("Diagnostic call exceeds reserved calls")


def verify_bundle(directory):
    directory = Path(directory)
    manifest = json.loads((directory / "manifest.json").read_text())
    if manifest.get('schema_version') == 2 and manifest.get('kind') == 'transcript_reduction':
        from redwake.transcript_experiment import verify_bundle as verify_transcript
        return verify_transcript(directory)
    if manifest.get('schema_version') == 2 and manifest.get('kind') == 'provider_compatibility':
        from redwake.compatibility import verify_bundle as verify_compatibility
        return verify_compatibility(directory)
    if manifest.get("schema_version") != 1:
        raise ValueError("Unsupported manifest schema")
    expected_files = set()
    for entry in manifest["files"]:
        relative = PurePosixPath(entry["path"])
        if relative.is_absolute() or ".." in relative.parts or entry["path"] in expected_files:
            raise ValueError("Invalid or duplicate artifact path")
        expected_files.add(entry["path"])
        path = directory.joinpath(*relative.parts)
        if path.is_symlink() or not path.is_file():
            raise ValueError("Missing or unsupported artifact: " + entry["path"])
        path.resolve().relative_to(directory.resolve())
        raw = path.read_bytes()
        if len(raw) != entry["bytes"] or hashlib.sha256(raw).hexdigest() != entry["sha256"]:
            raise ValueError("Artifact hash mismatch: " + entry["path"])
    actual_files = {p.relative_to(directory).as_posix() for p in directory.rglob("*")
                    if p.is_file() and p.name != "manifest.json"}
    if actual_files != expected_files:
        raise ValueError("Artifact inventory differs from manifest")
    rows = json.loads((directory / "results.json").read_text())["rows"]
    ids = [row["run_id"] for row in rows]
    if len(set(ids)) != len(ids) or ids != manifest["run_ids"] or len(ids) != manifest["run_count"]:
        raise ValueError("Run inventory differs from manifest")
    by_id = {}
    for row in rows:
        run_id = row["run_id"]
        if len(run_id) != 12 or any(c not in "0123456789abcdef" for c in run_id):
            raise ValueError("Invalid run ID")
        folder = directory / "runs" / run_id
        state = json.loads((folder / "state.json").read_text())
        evidence = json.loads((folder / "evidence.json").read_text())
        saved_result = json.loads((folder / "result.json").read_text())
        scenario = state["config"].get("scenario", "classic")
        results = assess(evidence, scenario)
        if (state["id"] != run_id or state["evidence"] != evidence
                or saved_result["run_id"] != run_id or saved_result["results"] != results
                or saved_result["status"] != state["status"] or row["results"] != results
                or row["status"] != state["status"] or row["reason"] != state.get("reason")
                or row["limits"] != state["config"]["limits"]):
            raise ValueError("State, evidence or verdict mismatch: " + run_id)
        for key, value in score(evidence, state["config"]["mode"], scenario).items():
            if row[key] != value:
                raise ValueError("Score mismatch: " + run_id)
        for key in ("requests", "model_calls", "input_tokens", "output_tokens",
                    "reserved_output_tokens", "usage_complete"):
            if row[key] != state[key]:
                raise ValueError("Accounting mismatch: " + run_id)
        if row["seconds"] != state["elapsed"]:
            raise ValueError("Elapsed-time mismatch: " + run_id)
        if (row["backend"] != state["config"]["backend"]
                or row["model"] != state["config"].get("model")
                or row["mode"] != state["config"]["mode"] or row["scenario"] != scenario):
            raise ValueError("Configuration mismatch: " + run_id)
        if (row.get("diagnostics", []) != state.get("diagnostics", [])
                or saved_result.get("diagnostics", []) != state.get("diagnostics", [])):
            raise ValueError("Diagnostic mismatch: " + run_id)
        by_id[run_id] = state
    evaluation = directory / "baseline-evaluation.json"
    if evaluation.exists():
        for evaluated in json.loads(evaluation.read_text()):
            state = by_id[evaluated["run_id"]]
            verdicts = [r["verdict"] for r in assess(state["evidence"])]
            if evaluated["verdicts"] != verdicts or evaluated["mode"] != state["config"]["mode"]:
                raise ValueError("Baseline evaluation mismatch")
    comparison = directory / "comparison.json"
    if comparison.exists():
        batch = json.loads(comparison.read_text())
        if 'suite_version' in batch and batch['suite_version'] not in (1, 2):
            raise ValueError('Unsupported discovery suite version')
        if [r['run_id'] for r in batch['rows']] != ids:
            raise ValueError('Comparison run inventory mismatch')
        if batch.get('suite_version') in (1, 2):
            from redwake.discovery_suite import verify_comparison
            verify_comparison(batch, by_id)
        else:
            from redwake.comparison import aggregate, result_row
            if batch["summary"] != aggregate(batch["rows"]):
                raise ValueError("Comparison summary mismatch")
            for row in batch["rows"]:
                if row != result_row(by_id[row["run_id"]], row["repeat"]):
                    raise ValueError("Comparison row mismatch")
            verify_comparison_controls(batch, by_id)
    return {"bundle": directory.name, "runs": len(ids), "files": len(expected_files)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundles", nargs="*", type=Path)
    args = parser.parse_args(argv)
    bundles = args.bundles or sorted(p.parent for p in (ROOT / "docs" / "experiments").glob("*/manifest.json"))
    if not bundles:
        parser.error("No retained experiment bundles found")
    try:
        totals = [verify_bundle(p) for p in bundles]
    except (KeyError, OSError, TypeError, ValueError) as exc:
        print("Verification failed: " + str(exc), file=sys.stderr)
        return 1
    for row in totals:
        print("%(bundle)s: %(runs)d runs, %(files)d files verified offline." % row)
    print("%d saved runs/trials verified; no network or model calls." % sum(r["runs"] for r in totals))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
