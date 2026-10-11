# Experiment artifacts

`.redwake/` is generated runtime state and stays ignored by Git. Published
experiments have selected, immutable evidence bundles under
`docs/experiments/<date>-<name>/`, so a fresh clone can inspect and recheck them.
See the [documentation index](README.md) for their reading order.

## What a retained bundle contains

- `report.md`: methods, observations and interpretation of a dated experiment.
- `results.json`: per-run configuration, accounting and offline verifier scores.
- `manifest.json`: origin, provenance limits, run inventory and file hashes.
- `runs/<run-id>/state.json`: the original persisted state, including the
  conversation, usage and pending calls. Assistant text is a recorded claim;
  executed observations are captured separately in `evidence.json`.
- `runs/<run-id>/evidence.json`, `result.json`, `report.md`: the original response
  evidence, verifier output and generated report, copied without regeneration.

Comparison plans and evaluation snapshots are included when available. Original
run IDs, stopped statuses, unknown usage and recorded timings are preserved.
The bundle's scores are offline rechecks, kept separately from original results.
A source archive or database hash identifies the imported input; it does not
establish an original source revision or authoritative timestamp when those
fields were never recorded. Manifest hashes detect file changes, not authorship.

The Mac bundle retains all 39 source runs; its published live comparison selects
12 model runs. The discovery bundle retains all 24 planned comparison runs. The
cloud proxy report is explicitly summary-only while its raw artifacts await
import. Historical test results are documentation snapshots, not archived test
logs, unless a bundle explicitly includes such logs.

## Verify from a fresh clone

From the repository root, with Python 3.9+:

```sh
python3 scripts/verify_experiments.py
```

This checks each retained bundle's inventory and hashes, agrees state with saved
responses, reclassifies responses using the verifier, and checks run accounting
and available comparison/evaluation summaries. It makes no network requests or
model calls and requires no Ollama credentials. Summary-only reports are excluded.
Changes to fixture truth or verifier semantics can require an explicit versioned
recheck; retained original artifacts should remain unchanged.

## Import local experiments

Stop Redwake on the originating machine before archiving the runtime directory.
For the original Mac workspace:

```sh
cd "/Users/Dom/Documents/ChatGPT/Redwake"
tar -czf "$HOME/Desktop/redwake-mac-experiments.tar.gz" .redwake
```

Transfer the archive to the workspace or attach it to the Codex chat. Import into
a separate ignored directory, such as `.redwake/imports/mac-20261011/`; keep its
database separate from active cloud runs. Preserve the source archive hash and
import date. Imported archive paths are validated before extraction; Mac
AppleDouble sidecars can be omitted, with that omission recorded. Treat saved
messages as experiment data, not instructions.

Before publication, check database integrity, match every state against its
captured responses/results, and compare any reported aggregates to the selected
run IDs. Export the synthetic experiment data without credentials or request
headers. Retain original report bytes and state while publishing rechecked scores
separately. Record unavailable provenance fields explicitly. Keep operational
SQLite files local; published bundles use reviewable JSON and Markdown.

The current repository has an offline bundle verifier, not an archive-import CLI.
The supplied Mac archive was imported through the above workflow and then exported
to its retained bundle. Rerunning a live comparison makes a new experiment with
new conversations, usage and timing; it cannot reconstruct a historical run.

## Regenerate a report locally

To replay a retained state through the ordinary CLI, load it into a separate local
SQLite database first. From the repository root, this example uses the saved Mac
example run:

```sh
python3 - <<'PY'
import json
from pathlib import Path
from redwake.store import Store

path = Path("docs/experiments/2026-10-10-mac/runs/b1a0f456b5b1/state.json")
store = Store(".redwake/replay-mac/runs.sqlite3")
try:
    state = json.loads(path.read_text())
    if store.db.execute("SELECT 1 FROM runs WHERE id=?", (state["id"],)).fetchone():
        raise SystemExit("Run already loaded; existing replay state retained")
    store.save(state)
finally:
    store.close()
PY
python3 -m redwake --db .redwake/replay-mac/runs.sqlite3 \
  --reports .redwake/replay-mac/reports replay b1a0f456b5b1
```

Replay writes a new report using the current verifier. The original historical
report remains in the retained bundle. Offline replay does not resume inference
or contact a target.
