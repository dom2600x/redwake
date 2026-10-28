# Project direction and model policy

Recorded: 2026-10-28. Source: discussion with the project owner. This is a living
decision record. Dated experiment reports and initial engineering decisions remain
historical evidence. Planned capabilities below are not implemented support claims.

## Delivery direction

The owner has delegated project and development leadership to Codex. Move Redwake
toward its README purpose: evidence-backed API authorization testing that finds
weaknesses and proves impact. Implement concrete requirements and acceptance criteria;
experiments are development tools, not deliverables by default.

Use deterministic tests, mocked providers and retained evidence first. Live assessments
need an unresolved engineering or release decision, a bounded allowance and a stopping
condition. Preserve failures. Do not rerun studies merely to enlarge samples, discover
an undocumented quota ceiling or demonstrate activity.

Portable investigation export, offline verification and credential-free CI were delivered
in PR #9. These are prototype foundations, not proof of security-analysis capability.

## Security capability and model selection

The completed comparisons primarily measured navigation and evidence collection. The
private fixture verifier generated security classifications. They did not establish
independent model ability to identify unfamiliar authorization flaws, explain violated
policies, distinguish legitimate access or assess impact.

Ultra's stronger operational completion record does not establish that it is the best
security model. Model selection remains provisional. Require model-submitted findings
with a violated access rule, executed evidence references, reproduction steps and a
bounded impact statement. Verification must check the submission; models must not be
credited with findings generated solely by fixture truth.

Security acceptance needs unfamiliar cases and negative controls: legitimate sharing,
public content, missing owner controls and outages. Assess supported findings, missed
flaws, false positives and unsupported impact claims. Successful traversal is insufficient.
A small, bounded assessment is justified when it can select a backend or determine
release readiness; another broad operational benchmark is not the next step.

## Provider and model usage policy

- Build and test using the scripted baseline and mocked inference; no paid inference is
  needed to implement accounting, provider interfaces or finding validation.
- Make small provider-integration checks only where deterministic tests cannot establish
  the remote behavior required by a supported workflow.
- Support frontier models alongside open-weight models. Free-tier availability was a
  development economy, not a sufficient basis for production model selection.
- Ollama is the existing gateway. A common provider interface with direct OpenAI and
  Anthropic adapters is the proposed initial extension; those adapters are not built yet.
- Select the least expensive backend meeting security acceptance criteria, considering
  reliability and complete-investigation cost, rather than token price alone.
- Keep scope, execution permissions, evidence requirements and budgets independent of
  provider/model choice. Establish a working single-model investigator before adding
  multi-model orchestration. Sending target data to additional providers must be explicit.

The owner can add Ollama credits if needed. This does not require purchasing credits now
or establish an unlimited spending allowance. Paid acceptance checks need bounded budgets.

## Cost accounting requirements

Record usage per call and aggregate by investigation/provider. Use decimal arithmetic
and versioned rate snapshots for the exact model and applicable service tier. Capture
ordinary input, cached input, output and other separately billed categories when reported.
Confirm whether input totals include cached tokens; do not double-count them.

Distinguish token usage, rate-card value, provider-reported credit consumption and cash
charges. Free usage, included plan credits and purchased credits are different billing
contexts. The owner confirms the historical model runs used free-tier usage: do not
assign retrospective cash charges. Any valuation at subsequently supplied rates must
be labeled separately from historical billing.

Complete usage and known rates support calculated cost. Missing cache splits or billing
details require labeled estimates. Failed, timed-out or interrupted calls may be billed
without returning usage: preserve unknown amounts and reconcile through supported
provider usage/billing interfaces where available.

Before a call, check accumulated cost, outstanding reservations and a conservative
allowance for the next call. Include input/context and output usage; an output-token cap
alone is insufficient. If a defensible bound is unavailable, do not claim a strict dollar
guarantee. Account-wide caps require provider enforcement or accounting for all clients.

## Ollama free usage: supplied facts and unknowns

The owner's dashboard says cloud models and capabilities such as web search share free
usage. A definitive quota, reset rule and conversion into dollars or remaining requests
have not been established. Treat free capacity as an opaque quota, separate from pricing.

User-supplied eligible models:

- `beam`
- `gemma4:31b`
- `gpt-oss:120b`
- `gpt-oss:20b`
- `nemotron-3-nano:30b`
- `nemotron-3-super`
- `nemotron-3-ultra`

User-supplied account observation during this discussion: 37.3% free usage consumed;
Ultra 727 requests, Super 1,331 and GPT-OSS 1,281, totaling 3,339 requests. These are not
token counts or the inventory of Redwake's retained investigations. Exact dashboard
observation time and reset boundary were not supplied. Do not extrapolate remaining
requests or a dollar ceiling from this snapshot.

Capture quota observations with their time/source through a supported interface when
available; otherwise report remaining capacity as unknown. Stop on exhaustion and preserve
progress instead of repeatedly retrying. Confirm whether Ollama exposes controls preventing
automatic purchased-credit consumption before promising an enforceable free-only mode.

## Ollama pricing reference

The owner supplied this snapshot and accompanying FAQ; it has not been independently
checked against a live endpoint. Reference: [Ollama pricing](https://ollama.com/pricing#model-pricing).
Rates are USD per million tokens. A dash means no rate was supplied, not zero cost.

| Model | Input | Cached input | Output |
|---|---:|---:|---:|
| clef | 0.24 | — | — |
| deepseek-v4.1-flash | 0.30 | 0.006 | 1.20 |
| deepseek-v4.1-flash, off-peak | 0.15 | 0.003 | 0.60 |
| deepseek-v4-pro | 1.32 | 0.044 | 3.96 |
| deepseek-v4-pro, off-peak | 0.66 | 0.022 | 1.98 |
| gemma4 | 0.14 | 0.05 | 0.40 |
| glm-5.3 | 1.40 | 0.26 | 4.40 |
| glm-5.3-flash | 0.15 | 0.03 | 0.50 |
| glm-5.2 | 1.40 | 0.26 | 4.40 |
| gpt-oss:120b | 0.15 | 0.014 | 0.60 |
| gpt-oss:20b | 0.07 | 0.035 | 0.30 |
| kimi-k3 | 3.00 | 0.30 | 15.00 |
| kimi-k2.7-code | 0.95 | 0.19 | 4.00 |
| kimi-k2.6 | 0.95 | 0.16 | 4.00 |
| minimax-m3.1-flash | 0.15 | 0.015 | 0.60 |
| minimax-m3 | 0.60 | 0.12 | 2.40 |
| minimax-m2.7 | 0.30 | 0.06 | 1.20 |
| mistral-large-4 | 0.68 | 0.07 | 2.09 |
| mistral-large-3 | 0.50 | — | 1.50 |
| muse-spark-open | 1.25 | 0.15 | 4.25 |
| nemotron-3-nano | 0.06 | — | 0.24 |
| nemotron-3-super | 0.015 | 0.015 | 0.60 |
| nemotron-3-ultra | 0.10 | 0.10 | 3.00 |

The supplied rule says off-peak pricing applies outside 12:00–18:00 UTC on weekdays
and all day on weekends. Confirm boundary and billing-event semantics before claiming
exact reconciliation. Do not discount models without a supplied off-peak rate. Confirm
model aliases and API usage fields before turning this snapshot into executable pricing.

The supplied FAQ says included credits are consumed before purchased credits, purchased
credits allow all cloud models, and Pay as you go/Pro permit three concurrent requests
while Max/Team permit ten. Eligibility, account balance and concurrency are separate
controls; do not infer account entitlement from a model name or pricing row.

The provider describes no prompt/response logging or training, and hosting primarily in
the US with possible European routing. These are provider statements, not independently
verified Redwake guarantees or promises applicable to every future backend.

## Implementation follow-through

1. Define model-submitted findings and deterministic evidence validation, including
   negative cases. Preserve the historical fixture verifier and experiment artifacts.
2. Define a common provider response/usage contract and implement per-call cost accounting
   with pricing provenance, unknown usage and budget reservations.
3. Add provider adapters and user-configured access contracts with explicit target and
   credential boundaries, verified through deterministic integration tests.
4. Once the finding workflow works, use a small, bounded security acceptance assessment
   to select a model. Do not resume the old benchmark matrix as the default next action.

Open questions: provider cache-usage fields, authoritative credit reconciliation,
free-tier reset/limits and enforceable free-only controls. Resolve these through supported
documentation/interfaces when needed, rather than spending calls to infer quotas.
