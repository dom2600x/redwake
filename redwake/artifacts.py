"""Portable evidence export and offline semantic verification."""

from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re
import shutil
import tempfile

from .contracts import SCENARIOS
from .lab import ACTORS, MODES, allowed_paths
from .providers import DIAGNOSTIC_CATEGORIES, validate_diagnostic
from .verifier import assess, score


def verify_comparison_controls(batch, states):
    """Recheck v2 treatment equality without rewriting historical batch rules."""
    if batch.get("comparison_version") != 2:
        return
    from .comparison import json_sha256
    from .providers import validate_diagnostic
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
    if not isinstance(manifest, dict):
        raise ValueError("Invalid manifest")
    if manifest.get('kind') == 'finding_proof':
        from .findings import verify_proof
        return verify_proof(directory)
    if manifest.get('schema_version') == 2 and manifest.get('kind') == 'transcript_reduction':
        from .transcript_experiment import verify_bundle as verify_transcript
        return verify_transcript(directory)
    if manifest.get('schema_version') == 2 and manifest.get('kind') == 'provider_compatibility':
        from .compatibility import verify_bundle as verify_compatibility
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
        if manifest.get("kind") == "investigation":
            validate_run(state)
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
            from .discovery_suite import verify_comparison
            verify_comparison(batch, by_id)
        else:
            from .comparison import aggregate, result_row
            if batch["summary"] != aggregate(batch["rows"]):
                raise ValueError("Comparison summary mismatch")
            for row in batch["rows"]:
                if row != result_row(by_id[row["run_id"]], row["repeat"]):
                    raise ValueError("Comparison row mismatch")
            verify_comparison_controls(batch, by_id)
    if manifest.get("kind") == "investigation":
        if len(ids) != 1 or expected_files != {"results.json"} | {
                "runs/" + ids[0] + "/" + name for name in
                ("state.json", "evidence.json", "result.json", "report.md")}:
            raise ValueError("Invalid investigation inventory")
        state = by_id[ids[0]]
        validate_run(state)
        if rows != [run_row(state)]:
            raise ValueError("Investigation summary differs from saved state")
        result = json.loads((directory / "runs" / ids[0] / "result.json").read_text())
        if result != run_result(state):
            raise ValueError("Investigation result differs from saved state")
    return {"bundle": directory.name, "runs": len(ids), "files": len(expected_files)}



ACCOUNTING = ('requests', 'model_calls', 'input_tokens', 'output_tokens',
              'reserved_output_tokens', 'usage_complete')


def validate_run(state):
    """Reject active, out-of-contract or inconsistent local run snapshots."""
    fields = {'id', 'config', 'status', 'reason', 'requests', 'model_calls',
              'input_tokens', 'output_tokens', 'reserved_output_tokens', 'elapsed',
              'evidence', 'messages', 'pending', 'events', 'usage_complete',
              'inflight_model', 'diagnostics', 'submissions', 'finding_finished', 'cost_ledger'}
    config_fields = {'backend', 'model', 'endpoint', 'scenario', 'mode', 'limits',
                     'comparison_version', 'experiment_profile', 'prompt_variant',
                     'initial_messages', 'initial_messages_sha256', 'tools_sha256',
                     'controls', 'guidance_variant', 'access_contract', 'cost_policy'}
    if not isinstance(state, dict) or set(state) - fields:
        raise ValueError('Unsupported run fields')
    if not isinstance(state.get('id'), str) or not re.fullmatch(r'[0-9a-f]{12}', state['id']):
        raise ValueError('Invalid run ID')
    config = state['config']
    if not isinstance(config, dict) or set(config) - config_fields:
        raise ValueError('Unsupported run configuration')
    scenario = config.get('scenario', 'classic')
    if (scenario not in SCENARIOS or config.get('mode') not in MODES
            or config.get('backend') not in ('baseline', 'ollama')
            or config.get('endpoint') not in (None, 'https://ollama.com', 'http://127.0.0.1:11434')):
        raise ValueError('Unsupported lab configuration')
    if state['status'] not in ('completed', 'stopped') or state.get('inflight_model'):
        raise ValueError('Run is active; finish or interrupt it before export')
    reasons = {'Time budget exhausted', 'Request budget exhausted', 'Model-call budget exhausted',
               'Estimated cost budget exhausted', 'Output-token budget exhausted', 'Provider exceeded the requested output-token budget',
               'Rejected tool call outside the lab contract', 'Interrupted; saved progress can be resumed',
               'Operation failed; reservations retained', 'Comparison setup failed; run retained',
               'Rejected invalid or excessive tool-call batch'}
    reasons.update('Provider failure (%s); reservations retained' % c
                   for c in DIAGNOSTIC_CATEGORIES['provider'])
    if (state.get('reason') is not None and state['reason'] not in reasons
            or state['status'] == 'stopped' and not state.get('reason')):
        raise ValueError('Unsupported terminal reason')
    limits = config['limits']
    if (not isinstance(limits, dict) or set(limits) != {'requests', 'model_calls', 'output_tokens', 'seconds'}
            or any(type(v) is not int or v <= 0 for v in limits.values())):
        raise ValueError('Invalid run limits')
    if any(type(state[k]) is not int or state[k] < 0 for k in ACCOUNTING[:-1]):
        raise ValueError('Invalid run usage')
    if (type(state['usage_complete']) is not bool
            or type(state['elapsed']) not in (int, float)
            or not math.isfinite(state['elapsed']) or state['elapsed'] < 0):
        raise ValueError('Invalid usage completeness or elapsed time')
    evidence = state['evidence']
    if (not isinstance(evidence, list) or state['requests'] < len(evidence)
            or state['requests'] > limits['requests'] or state['model_calls'] > limits['model_calls']
            or state['reserved_output_tokens'] > limits['output_tokens']):
        raise ValueError('Run accounting exceeds allowances or evidence')
    for i, item in enumerate(evidence, 1):
        if (not isinstance(item, dict) or set(item) != {'id', 'actor', 'path', 'status', 'body'}
                or type(item['id']) is not int or item['id'] != i
                or item['actor'] not in ACTORS or item['path'] not in allowed_paths(scenario)
                or type(item['status']) is not int or not 100 <= item['status'] <= 599):
            raise ValueError('Evidence outside the lab contract')
    for key in ('messages', 'pending', 'events', 'diagnostics'):
        if not isinstance(state.get(key, []), list):
            raise ValueError('Invalid run sequence')
    if any(e != 'Interrupted model call: reservation retained; actual usage unknown.'
           for e in state['events']):
        raise ValueError('Unsupported event detail')
    from .costs import recheck as recheck_costs
    recheck_costs(state)
    from .submission import recheck
    recheck(state)
    for record in state.get('diagnostics', []):
        validate_diagnostic(record)
        if record.get('model_call', 0) > state['model_calls']:
            raise ValueError('Diagnostic exceeds reserved model calls')


def run_row(state):
    config = state['config']
    scenario = config.get('scenario', 'classic')
    row = dict(score(state['evidence'], config['mode'], scenario),
               run_id=state['id'], backend=config['backend'], model=config.get('model'),
               scenario=scenario, mode=config['mode'], status=state['status'],
               reason=state.get('reason'), limits=config['limits'], seconds=state['elapsed'],
               results=assess(state['evidence'], scenario))
    row.update({key: state[key] for key in ACCOUNTING})
    if state.get('diagnostics'):
        row['diagnostics'] = state['diagnostics']
    return row


def run_result(state):
    scenario = state['config'].get('scenario', 'classic')
    metrics = dict(score(state['evidence'], state['config']['mode'], scenario),
                   **{key: state[key] for key in ('requests', 'model_calls', 'input_tokens',
                                                 'output_tokens', 'usage_complete')},
                   seconds=state['elapsed'])
    result = dict(run_id=state['id'], results=assess(state['evidence'], scenario),
                  status=state['status'], scenario=scenario, metrics=metrics)
    if state.get('diagnostics'):
        result['diagnostics'] = state['diagnostics']
    if 'access_contract' in state['config']:
        from .submission import recheck
        result['submitted_findings'] = recheck(state)
    if 'cost_policy' in state['config']:
        from .costs import recheck
        result['cost'] = recheck(state)
    return result


def export_run(state, destination):
    """Export one terminal run without modifying its state or using a provider."""
    from .report import write_report

    validate_run(state)
    destination = Path(destination)
    if destination.exists() or destination.is_symlink():
        raise ValueError('Destination exists; choose a fresh directory')
    destination.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='.redwake-export-', dir=destination.parent))
    def write_json(path, value):
        path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')
    try:
        write_report(state, stage / 'runs')
        write_json(stage / 'runs' / state['id'] / 'state.json', state)
        write_json(stage / 'results.json', {'rows': [run_row(state)]})
        manifest = dict(schema_version=1, kind='investigation', run_count=1,
                        run_ids=[state['id']], exported_utc=datetime.now(timezone.utc).isoformat(),
                        verification_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                             for p in sorted(Path(__file__).parent.glob('*.py'))},
                        notes=['Hashes detect changes, not authorship; no signed audit trail.',
                               'Offline verification re-scores captured synthetic evidence; no target retest.',
                               'Verifier fingerprints describe export time; original run revision is not recorded.'])
        manifest['files'] = [dict(path=p.relative_to(stage).as_posix(), bytes=p.stat().st_size,
                                  sha256=hashlib.sha256(p.read_bytes()).hexdigest())
                             for p in sorted(stage.rglob('*')) if p.is_file()]
        write_json(stage / 'manifest.json', manifest)
        verify_bundle(stage)
        # Reserve a fresh directory without replacing an existing destination.
        destination.mkdir()
        try:
            for path in stage.iterdir():
                path.rename(destination / path.name)
        except BaseException:
            shutil.rmtree(destination)
            raise
    finally:
        shutil.rmtree(stage)
    return destination / 'runs' / state['id'] / 'report.md'
