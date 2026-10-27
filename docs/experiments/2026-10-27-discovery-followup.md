# Discovery follow-up: call capacity, batching and evidence

2026-10-27 (Australia/Perth). All 72 planned runs are retained: 54 model runs and
18 scripted baselines across three separate batches. The larger-call sample
increased correct completions for GPT-OSS from 2/6 to 3/6 and Super from 0/6 to
3/6. Explicit batching did not produce a clean GPT-OSS comparison: all six runs
received HTTP 500 during inference. These are observations of this fixture and
execution envelope, not a general model-capability ranking.

## Design and retained controls

| Profile | Prompt | Requests | Model calls | Reserved output tokens | Active seconds |
|---|---|---:|---:|---:|---:|
| current | Original discovery guidance | 32 | 16 | 16,384 | 120 |
| sequential | Same original guidance | 32 | 24 | 24,576 | 120 |
| batching | Original plus explicit batching advice | 32 | 16 | 16,384 | 120 |

Each backend ran three repetitions of vulnerable and fixed behaviour in each
batch. Inference ran serially; model order rotated between blocks. Batch order
was current, sequential, batching. No run was retried, resumed, excluded or given
extra allowances. All calls used temperature 0, at most 1,024 reserved output
tokens and a maximum 60-second provider timeout bounded by remaining active time.
The sequential reservation allowance rises with calls so a hidden token-reservation
cap does not stop it after 16 calls. Other controls stay fixed.

The three batches have identical runtime module fingerprints from committed
implementation `8da7eb8`. Metadata records exact source revisions, prompt snapshots
and hashes, tool hashes, allowances and controls. Later commits checkpoint evidence;
they do not change the runtime. All 18 retained October 11 model initial prompts
also match the new current/sequential prompt. The [October 11 comparison](2026-10-11-discovery/report.md)
remains unchanged. Its GPT-OSS 0/6 and Ultra 5/6 completion counts differ from the
new control's 2/6 and 6/6 despite matching initial guidance and allowances; time,
service behaviour, model aliases and ordinary run variance remain confounds.

## Completion and proved flaws

| Backend | Current correct / 6 | Sequential correct / 6 | Batching correct / 6 |
|---|---|---|---|
| baseline | 6 | 6 | 6 |
| gpt-oss:120b | 2 | 3 | 0 |
| nemotron-3-super | 0 | 3 | 3 |
| nemotron-3-ultra | 6 | 5 | 5 |

| Backend | Current proved / 6 | Sequential proved / 6 | Batching proved / 6 |
|---|---|---|---|
| baseline | 6 | 6 | 6 |
| gpt-oss:120b | 4 | 4 | 0 |
| nemotron-3-super | 2 | 6 | 6 |
| nemotron-3-ultra | 6 | 6 | 5 |

Correct runs require completed record/account coverage and every verifier verdict
to match the fixture. Six seeded-flaw opportunities per backend/profile come from
the document and its attachment in three vulnerable runs; fixed runs have no
expected flaws. The export outage correctly remains inconclusive. All new batches
have zero verifier-proven false positives. This does not grade unsupported claims
in model prose. Baselines complete every run, with 18 probes each.

Super's sequential runs prove all six seeded flaws, while three runs remain
incomplete. In the batching sample Super also proves all six flaws and completes
three runs. Vulnerability recall and complete investigation are different outcomes.

## Discovery exposure, evidence collection and budgets

| Profile | Model | Record links exposed | Record/account pairs attempted | Successful owner controls | Duplicate probes |
|---|---|---|---|---|---|
| current | gpt-oss:120b | 36/36 | 63/72 | 28/30 | 1 |
| current | nemotron-3-super | 36/36 | 57/72 | 26/30 | 0 |
| current | nemotron-3-ultra | 36/36 | 72/72 | 30/30 | 0 |
| sequential | gpt-oss:120b | 36/36 | 65/72 | 28/30 | 7 |
| sequential | nemotron-3-super | 36/36 | 69/72 | 30/30 | 6 |
| sequential | nemotron-3-ultra | 30/36 | 60/72 | 25/30 | 0 |
| batching | gpt-oss:120b | 10/36 | 0/72 | 0/30 | 0 |
| batching | nemotron-3-super | 36/36 | 68/72 | 30/30 | 16 |
| batching | nemotron-3-ultra | 36/36 | 66/72 | 28/30 | 0 |

Each six-run model sample can expose 36 record links, attempt 72 record/account
pairs and obtain 30 successful owner controls; the export never supplies a
successful control. Exposed links are those in captured responses, not a claim
that the model recognised or used them. Duplicate probes repeat an account/path
pair. The most recent observation for a pair is the verifier's evidence.

In the current control all 18 model runs expose all six resource links. GPT-OSS
and Super still omit required comparisons and controls. Nine call-budget stops
have 76.8–110.4 active seconds left and fewer than 1,645 returned output tokens
each, while reserving all 16,384 tokens. These stops reach the call/reservation
allowance, rather than the active-time limit or actual generated-token total.

The baseline's 18-request traversal is not an executor-enforced minimum.
GPT-OSS's two successful current runs,
[06b02473cb16](2026-10-27-discovery-current/runs/06b02473cb16/report.md) and [852978e23b80](2026-10-27-discovery-current/runs/852978e23b80/report.md), use
16 singleton calls without batching: they infer valid collection URLs after the
project listings and skip the two project-detail GETs. The executor checks an
exact path allowlist, not whether each path was first obtained from a response
link. Therefore a 16-call completion does not by itself establish batching.
The occurrence of these shortcuts in fixed runs does not establish a mode effect.

Coverage also prevents an expected outage from masking unfinished work. In
[ed5e77351899](2026-10-27-discovery-current/runs/ed5e77351899/report.md) Super matches all six expected verdicts but
omits both export probes and stops at 10/12 pairs. Missing observations leave the
export inconclusive, which matches its expected verdict; the run still fails the
coverage requirement. In [bd1d1545c8e1](2026-10-27-discovery-current/runs/bd1d1545c8e1/report.md) all five obtainable
owner controls succeed, but Bob's attachment probe is absent, so that flaw is
unproved. In sequential [906de9695487](2026-10-27-discovery-sequential/runs/906de9695487/report.md) Super proves
both flaws yet exhausts 24 calls with Alice's export probe missing, after four
extra cross-account navigation probes and three duplicate record probes.

## Model choices and inference failures

| Profile | Completed model runs / 18 | Allowance stops | Scope stops | Inference failures |
|---|---|---|---|---|
| current | 8 | 9 | 1 | 0 |
| sequential | 11 | 2 | 4 | 1 |
| batching | 8 | 2 | 0 | 8 |

A scope rejection terminates the current harness before the proposed probe runs.
For example, GPT-OSS's sequential [2695eed70845](2026-10-27-discovery-sequential/runs/2695eed70845/report.md) proposes
Bob's `/api/records/nonexistent` with nine calls and about 106 seconds remaining.
This records a model choice interacting with strict harness scope, not a resource
or time-budget stop. A broader API investigator might handle a guessed nonexistent
path differently; this experiment does not test that policy.

| Profile | Model | Run | Category | HTTP | Call | Record pairs / 12 | Active seconds |
|---|---|---|---|---|---|---|---|
| sequential | nemotron-3-ultra | [8b81a5ee724f](2026-10-27-discovery-sequential/runs/8b81a5ee724f/report.md) | timeout | — | 3 | 0 | 71.67 |
| batching | gpt-oss:120b | [65224d9d368f](2026-10-27-discovery-batching/runs/65224d9d368f/report.md) | http_server | 500 | 5 | 0 | 2.83 |
| batching | nemotron-3-super | [3130bcd41596](2026-10-27-discovery-batching/runs/3130bcd41596/report.md) | http_server | 500 | 7 | 10 | 14.40 |
| batching | gpt-oss:120b | [6de713024997](2026-10-27-discovery-batching/runs/6de713024997/report.md) | http_server | 500 | 5 | 0 | 3.31 |
| batching | nemotron-3-ultra | [18971e9a387b](2026-10-27-discovery-batching/runs/18971e9a387b/report.md) | timeout | — | 7 | 6 | 79.12 |
| batching | gpt-oss:120b | [e16ce651d54c](2026-10-27-discovery-batching/runs/e16ce651d54c/report.md) | http_server | 500 | 7 | 0 | 5.21 |
| batching | gpt-oss:120b | [4d808263c700](2026-10-27-discovery-batching/runs/4d808263c700/report.md) | http_server | 500 | 5 | 0 | 2.69 |
| batching | gpt-oss:120b | [3473a9893b4d](2026-10-27-discovery-batching/runs/3473a9893b4d/report.md) | http_server | 500 | 3 | 0 | 1.99 |
| batching | gpt-oss:120b | [9fa32359a61c](2026-10-27-discovery-batching/runs/9fa32359a61c/report.md) | http_server | 500 | 7 | 0 | 4.64 |

Seven inference failures return HTTP 500; two are call timeouts. The sequential
Ultra timeout occurs at about 72 active seconds and the batching timeout at about
79, so both stop before the 120-second run allowance. Each call is also subject
to its own maximum 60-second timeout. These are operational stops with no completed
assistant response from the failed call. A server status does not establish whether
the underlying cause is service state, request handling or generated tool output.

All six GPT-OSS batching runs fail during inference before any record pair is
captured. None of their returned assistant messages contains a multi-call batch;
what the failed inference would have returned is unknown. Thus this sample cannot
show that GPT-OSS followed or rejected batching advice. Super and Ultra each return
multi-call responses in all six batching runs, but Super still has one provider
failure, one request-budget stop and one call-budget stop; Ultra has one timeout.
Batching instructions do not ensure complete evidence or remove operational limits.

Diagnostics retain fixed categories, model-call indices and numeric HTTP status.
Credentials, request headers, raw provider error bodies and arbitrary exception
text are not diagnostic artifacts. Failed calls retain reservations and mark usage
incomplete; returned token totals are lower bounds. Provider failures remain in
all denominators. The old Super `RuntimeError` cannot be retrospectively diagnosed
from missing status/error data. Token counts are not monetary costs; stopped-run
timings are not successful-investigation latency.

## Limits and next questions

Six runs per backend/profile on deterministic fixtures do not represent independent
vulnerability classes. The document and attachment are related. The baseline knows
the generic traversal algorithm, while models choose navigation and evidence steps.
Exact scope rejection, the 1,024-token response cap, reservation policy, timeouts
and generic recovery guidance all affect outcomes. Models receive no private
ownership answers, missing-resource list or live model-call countdown.

The repeated profile order was not randomised across batches, and model aliases
were not pinned to provider build revisions. Temperature zero does not guarantee
determinism. HTTP failures prevent a clean interpretation of the GPT-OSS prompt
intervention; they must not be excluded to make a success-only comparison.

The next useful work is a separate provider/tool-batching compatibility experiment,
with response capacity varied as its own controlled factor, followed by rotated
profile order and additional navigation layouts or fixture IDs. Changes to how
the harness handles inferred or rejected paths also require a separate treatment.
The current results support improving evidence and budget management in this lab;
they do not establish readiness for external targets.

## Reproduction and retained artifacts

- [Current-budget batch](2026-10-27-discovery-current/report.md): all 24 runs and [manifest](2026-10-27-discovery-current/manifest.json).
- [Sequential-capacity batch](2026-10-27-discovery-sequential/report.md): all 24 runs and [manifest](2026-10-27-discovery-sequential/manifest.json).
- [Batching-guidance batch](2026-10-27-discovery-batching/report.md): all 24 runs and [manifest](2026-10-27-discovery-batching/manifest.json).

Each bundle includes the plan, all original conversations, state, captured responses,
reports, offline scores and file hashes. Hashes detect changes, not authorship.
The incomplete October 12 working tree and raw runs were unavailable after reset;
these October 27 experiments are new samples, not reconstructed historical results.

```sh
python3 scripts/verify_experiments.py
python3 -m unittest discover -s tests -v
```

Validation before live inference: 90 tests passed and all 63 historical runs verified.
After export, all 135 retained runs verify offline. The [comparison method](../comparison-method.md)
and [artifact guide](../artifacts.md) describe profiles, accounting and export.
