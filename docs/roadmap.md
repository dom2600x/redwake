# Roadmap

Redwake develops the lab harness and its evidence model before adding external
targets. This is the delivery roadmap. Dated experiment reports
record observations and limitations; the [documentation index](README.md) links
to those reports and their retained evidence.

## Implemented foundations

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

## Delivery priorities

The current release delivers the README's bounded, evidence-backed lab prototype.
Completion means a user can run an investigation, inspect an evidence-backed result,
resume interrupted work without resetting allowances, export its proof and verify that
proof independently of the original database. Public reads and outages must never be
reported as proven private-data leaks. External-target support is a separate future
scope, not an implied part of this release.

1. Complete the ordinary investigation workflow: portable single-run export and offline
   verification for completed and stopped runs. This is implemented through `export`
   and `verify`; the experimental batch exporter remains available separately.
2. Enforce release checks with deterministic tests on supported Python/platform targets,
   including evidence integrity, scope, accounting and historical artifact compatibility.
   These checks require no provider credentials or live inference.
3. Review and merge the delivery changes, then run the documented workflow from a clean
   checkout. Do not call the release complete while a required check is failing.

## Next implementation work

The [current decision record](project-decisions.md) captures the owner discussion and
distinguishes supplied provider information from unresolved questions. Prioritize
model-submitted security findings and evidence validation, a provider usage/cost contract,
then additional adapters and configurable access contracts. Model security capability
remains unproven; select a backend through a bounded security acceptance check once that
workflow is implemented. Pricing and free quota are separate accounting concerns.

## Research policy

Live model comparisons are optional development tools, not the roadmap's default next
step. A new study needs a concrete unresolved engineering question, an implementation
or release decision it could change, a bounded call allowance and a stopping condition.
Use unit/integration tests and retained evidence first. Preserve existing experiments;
do not rerun them just to generate a larger sample or report progress.

Provider transcript minimisation is deferred until a reproducible failure blocks a
supported workflow. Scope-rejection policy remains unchanged; assess a proposed recovery
feature against a concrete user need before commissioning another live comparison.
The completed studies establish neither general model capability nor external-target
readiness.

## Future scope

External APIs would require user-supplied access contracts, explicit target and credential
handling, suitable evidence matching and scope enforcement. Those are product requirements
for a later release and must be designed and implemented directly. More synthetic model
comparisons do not implement them or substitute for their acceptance tests.

The submitted-finding foundation now provides offline policy/claim validation and portable
proofs; see [the guide](submitted-findings.md). Opt-in model-loop submission now retains validation feedback and explicit completion.
Opt-in Ollama usage ledgers and flat-rate valuations are implemented; see
[cost accounting](cost-accounting.md). Additional provider adapters and their billing
normalization remain the next integration task. The historical fixture scores remain separate from submitted claims.
