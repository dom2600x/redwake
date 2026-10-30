# Production readiness

Status checked: 2026-10-30. This plan distinguishes the bounded synthetic lab from
future external-target functionality. Redwake remains a research prototype;
passing deterministic checks does not establish model capability or readiness for
customer targets.

## Current evidence

| Gate | Evidence | Remaining work |
|---|---|---|
| Bounded synthetic execution | Scoped loopback probes, durable call/request allowances, resume and offline export | Keep historical artifact compatibility in CI |
| Provider usage estimates | OpenAI and Anthropic rate cards, unknown usage, durable reservations and resume checks | Provider billing reconciliation and hard cash caps are unavailable |
| Finding correctness | Executed owner/cross-account evidence, explicit policy, stale evidence and identity checks | Limited to two-account record reads |
| Acceptance controls | PR #19 adds two positive cases and seven negative controls, with scripted correct/silent/indiscriminate controls | Review the PR; scripted controls establish harness behavior, not model capability |
| Supported platforms | PR #19 head `be7abeb12083eee313d925cded62f336eef2b26a` passed Checks on Ubuntu 22.04/Python 3.9 and macOS/Python 3.12 | Decide maintained Python/platform support before release |
| Model selection | No retained live acceptance result on the new cases | Select accessible candidates, freeze assessment controls and run a bounded assessment |
| Installed distribution | Source-tree execution is documented; a console entry point is declared | Build/install from a clean checkout and verify the installed CLI outside the source directory |
| Operations | Local SQLite state, sanitized diagnostics and portable proofs | Define evidence retention/deletion, backup/recovery and operator procedures for the intended deployment |
| External targets | Explicitly outside the current executor's scope | Product requirements, target authorization, credentials, network boundary, sensitive evidence handling and access model design |

PR #19 was open, mergeable and had no submitted reviews when checked. Its two CI
jobs passed. Review and merge state must be checked again before treating it as a
released dependency. This plan records observations, not a standing assertion
about future branch state.

## Next delivery sequence

1. Review the acceptance foundation and resolve concrete findings. Preserve the
   strict separation between captured evidence, model claims and fixture truth.
2. Freeze a model acceptance protocol before spending. Record exact provider/model
   IDs, verified rate cards and dates, prompt/tool/fixture hashes, repetitions,
   per-run allowances, an overall assessment ceiling and stopping conditions.
   Keep every planned slot, including failures and exhausted runs. Never reset a
   budget through resume or automatically retry failed slots. If multiple runs are
   orchestrated, implement and test the aggregate durable spending reservation
   before promising a whole-assessment cap. Per-run estimated budgets alone do
   not enforce a total assessment allowance.
3. Assess only account-accessible candidates against supported findings, misses,
   unsupported attempts, negative-control claims, reliability and complete-run
   cost. Preserve the evidence; select a backend only if it meets declared criteria.
   Restricted models remain excluded. No default live study or benchmark matrix
   is authorized by this plan.
4. Add clean installed-package smoke checks to CI, then rehearse the documented
   investigate/resume/export/verify workflow from the built artifact. Record the
   source revision, artifact hashes and supported platforms. No publishing is
   required to validate a local build.
5. Agree the production boundary and operator requirements. For a lab release,
   retain loopback-only execution and state its limits. For real APIs, design
   target authorization, credential isolation, request scope and evidence handling
   as explicit features before allowing external execution.

## Decisions needed

The next paid acceptance milestone needs exact accessible model candidates and a
USD assessment ceiling. The broader production milestone needs a concrete target:
a dependable local synthetic-lab tool, a user-operated real-API CLI, or a hosted
service. The latter two introduce requirements not covered by current fixture tests.
Until those decisions are supplied, continue reversible offline engineering and
review; do not infer permission to spend, publish a release, change external-target
scope, or claim production capability.
