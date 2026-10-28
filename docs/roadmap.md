# Roadmap

Redwake develops the lab harness and its evidence model before adding external
targets. This is the canonical sequence of planned work. Dated experiment reports
record observations and limitations; the [documentation index](README.md) links
to those reports and their retained evidence.

## Completed foundations

- A bounded loopback executor, durable accounting, evidence replay and a scripted
  baseline. See [initial Mac validation](experiments/2026-10-10-mac/validation.md).
- A [discovery lab](discovery-lab.md) with account-specific project listings,
  nested records and detail links, covering vulnerable, protected, public and
  outage cases.
- Model-facing API guidance separated from private ownership rules and verifier
  expectations.
- A repeatable comparison of the scripted baseline, GPT-OSS, Super and Ultra,
  recording findings, misses, false positives, requests, tokens and active time.
  See the [live discovery comparison](experiments/2026-10-11-discovery/report.md).
- Fixed current, sequential-capacity and batching-guidance profiles, safe provider
  diagnostics, and complete comparison export. The [controlled follow-up](experiments/2026-10-27-discovery-followup.md)
  retains all 72 new runs, including baselines, scope rejections and inference failures.
- An [inference-only compatibility study](experiments/2026-10-27-provider-compatibility/report.md)
  pairs fresh prompts and saved failure contexts at two response capacities,
  retaining all 36 live calls and 36 scripted controls.
- A [declared transcript-reduction study](experiments/2026-10-28-transcript-reduction/report.md)
  retains 48 calls and 48 controls across adapter/native request construction.
  The original control no longer reproduced HTTP 500 in that sample; no field
  removal or correlation workaround is credited with fixing it.
- A [varied-discovery pilot](experiments/2026-10-28-varied-discovery/report.md)
  retains 72 runs with rotating profile order, renamed IDs and opaque collection
  URLs. Access semantics and scripted traversal length stay fixed.

- A [counterbalanced topology study](experiments/2026-10-28-topology-study/report.md)
  retains all 216 investigations across opaque-reference, deeper and branching
  graphs, with three repetitions and balanced profile/model positions within
  each condition. All fixtures share explicit graph guidance; the reference
  costs 18 scripted probes and the deeper/branching variants cost 20. These
  remain related deterministic cases, rather than independent vulnerability classes.

## Next experiments

1. Re-establish a failing original provider control before further minimisation.
   Prefer a stable provider version or safe trace identifier when available;
   preserve both the historical failures and later non-reproduction.
2. Test any change to scope-rejection behaviour as a separate treatment. Inferred
   valid paths can shorten traversal; rejected paths currently stop a run.

Continue separating resource discovery, evidence collection, budget management
and operational failures. Keep prompts and allowances fixed within each batch,
with baselines and failed runs in every comparison. Detailed observations and
limitations remain in the dated comparison reports.

## External targets

General target support should follow only after the access contract, scope
enforcement and evidence model can represent it accurately. Extend those
foundations before adding external targets; the current synthetic lab does not
establish readiness for them.
