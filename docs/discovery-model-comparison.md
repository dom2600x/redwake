# Live discovery model comparison

2026-10-11 (Australia/Perth). Eighteen live Ollama Cloud investigations and six scripted baseline runs. Three repetitions per backend of both vulnerable and fixed discovery behaviour; each includes protected 403/404 reads, public content and an export outage.

Ultra performed best under the current budgets: five of six complete, correct runs and five of six seeded flaws proved. GPT-OSS and Super each proved two of six seeded flaws but completed no runs. The scripted baseline completed every run and proved all six seeded flaws.

## Method

All runs used the same discovery guidance, executor scope and budgets: 32 lab requests, 16 model calls, 16,384 reserved output tokens and 120 seconds of recorded active time. Each call requested at most 1,024 output tokens at temperature 0. Model order rotated between blocks; inference ran serially. No run was retried, resumed, excluded or given extra allowances. Ownership truth and expected verdicts stayed private to the verifier.

A correct run requires completed coverage and every verifier verdict matching fixture expectations. There are six seeded flaw opportunities per backend: two private reads in each of three vulnerable runs. Fixed runs contain no expected flaws. Findings require matched owner and other-account evidence; model prose is not graded. Outages remain inconclusive, even in correct runs.

## Findings and execution

| Backend | Correct runs | Proven flaws | Missed flaws | False positives | Total requests | Mean active time |
|---|---:|---:|---:|---:|---:|---:|
| baseline | 6/6 | 6/6 | 0 | 0 | 108 | 0.17s |
| gpt-oss:120b | 0/6 | 2/6 | 4 | 0 | 82 | 8.55s |
| nemotron-3-super | 0/6 | 2/6 | 4 | 0 | 97 | 23.79s |
| nemotron-3-ultra | 5/6 | 5/6 | 1 | 0 | 120 | 51.21s |

Mean time includes stopped runs. GPT-OSS and Super often stopped before completing coverage, so their shorter times do not show faster successful investigation.

| Backend | Total model calls | Returned input tokens | Returned output tokens | Usage complete |
|---|---:|---:|---:|---|
| baseline | 0 | 0 | 0 | yes |
| gpt-oss:120b | 83 | 97,776 | 4,196 | yes |
| nemotron-3-super | 87 | 150,535 | 8,778 | no |
| nemotron-3-ultra | 51 | 95,735 | 10,173 | yes |

Super had one failed inference operation with unknown actual usage. Its returned token totals are a lower bound on usage, and the failed call retained its reservation. Token counts are not dollar costs, and tokenisation differs across models.

## What stopped the runs

| Backend | Call budget exhausted | Scope rejection | Inference operation failure |
|---|---:|---:|---:|
| gpt-oss:120b | 5 | 1 | 0 |
| nemotron-3-super | 5 | 0 | 1 |
| nemotron-3-ultra | 1 | 0 | 0 |

GPT-OSS guessed `/api/projects/prj_a5/collections` after listing the accounts’ projects, rather than following the returned project self link. Exact scope enforcement stopped that run before any record probes. This measures the current harness’s strict rejection behaviour as well as the model’s discovery choice.

Eleven runs exhausted their model-call allowance. The baseline needs 18 requests, so a model issuing one request per call cannot reproduce that traversal within 16 calls. The successful Ultra runs batched requests and used six to nine calls. The comparison therefore tests batching and budget management alongside discovery.

Ultra’s third vulnerable run made 30 probes in 16 calls but never fetched the attachment as Alice, its owner. Bob received the attachment twice; without an owner control the verifier correctly left that read inconclusive. Repeated navigation and record probes consumed the allowance. This is an evidence-collection failure, not a protected attachment.

One Super run stopped after a failed inference operation recorded as `RuntimeError`. The saved reason does not retain the HTTP status or establish whether the failure came from the service or request handling. That run remains in the denominator; its missed attachment is an operational miss, not standalone evidence of a model reasoning failure.

Zero false positives refers to verifier-proven results. It does not measure unsupported claims in assistant prose. The fixtures are deterministic, the document and attachment are related cases, and six runs per model do not establish general security-testing ability or a reliable latency ranking.

## Next experiment

Use this batch as the unchanged-budget result. Repeat separately with a call allowance sufficient for sequential traversal, and optionally explicit batching guidance, to separate navigation ability from the 16-call constraint. Keep the baseline, frozen prompts and failed runs in every comparison. Better sanitized provider-error diagnostics would help distinguish inference failures from model choices. Ultra is the strongest investigator in this sample; the result does not justify dropping the other comparators.

## Reproduction and artifacts

```sh
python3 -m redwake.comparison --repeat 3
python3 -m unittest discover -s tests -v
```

The comparison command creates a fresh directory and refuses to overwrite an existing comparison database. Cloud requests preserve environment proxy and CA settings; loopback probes explicitly bypass proxies. No credentials are written to saved state.

The [machine-readable batch results](discovery-comparison.json) are saved in the repository alongside this report. Raw conversations and response artifacts remain in the ignored local experiment directory.

This batch is retained in `.redwake/live-discovery-20261011/`: `comparison.json` contains the plan, source SHA-256 fingerprints, all rows and aggregate metrics; `runs.sqlite3` contains conversations and cumulative accounting; `reports/<run-id>/` contains captured evidence, verifier results and Markdown reports. The experiment ran from a working tree; its module fingerprints identify the exact experiment source rather than a commit. A trailing blank line in `verifier.py` was removed before committing; runtime logic is unchanged.

Offline validation recomputed all 24 rows from SQLite, checked individual report verdicts and scores, verified equal budgets and initial guidance, and matched all module fingerprints. All 42 tests passed, including comparison aggregation, preservation of failed runs and proxy routing.

## Individual runs

| Run | Model | Mode | Repeat | Correct | Probes | Calls | Record pairs / 12 | Active time |
|---|---|---|---:|---|---:|---:|---:|---:|
| `b3b339921ba4` | baseline | vulnerable | 1 | yes | 18 | 0 | 12 | 0.16s |
| `a9541fb4445b` | gpt-oss:120b | vulnerable | 1 | no | 2 | 3 | 0 | 1.90s |
| `2379d5e689c2` | nemotron-3-super | vulnerable | 1 | no | 17 | 7 | 9 | 15.68s |
| `d55addd35738` | nemotron-3-ultra | vulnerable | 1 | yes | 18 | 9 | 12 | 84.75s |
| `f757fe3d8d62` | baseline | fixed | 1 | yes | 18 | 0 | 12 | 0.16s |
| `a1488018e21b` | nemotron-3-super | fixed | 1 | no | 16 | 16 | 10 | 19.59s |
| `4652b409345a` | nemotron-3-ultra | fixed | 1 | yes | 18 | 6 | 12 | 39.45s |
| `f73e6845f2d3` | gpt-oss:120b | fixed | 1 | no | 16 | 16 | 10 | 9.77s |
| `4f3a72e0092d` | baseline | vulnerable | 2 | yes | 18 | 0 | 12 | 0.16s |
| `fe4ad321e0ba` | nemotron-3-super | vulnerable | 2 | no | 16 | 16 | 10 | 36.84s |
| `82050c0742ba` | nemotron-3-ultra | vulnerable | 2 | yes | 18 | 7 | 12 | 23.82s |
| `1ac413b668ca` | gpt-oss:120b | vulnerable | 2 | no | 16 | 16 | 10 | 8.93s |
| `190f683a226f` | baseline | fixed | 2 | yes | 18 | 0 | 12 | 0.16s |
| `3532f932ce37` | nemotron-3-ultra | fixed | 2 | yes | 18 | 7 | 12 | 31.83s |
| `771cd78cba4a` | gpt-oss:120b | fixed | 2 | no | 16 | 16 | 10 | 9.19s |
| `faafe7162674` | nemotron-3-super | fixed | 2 | no | 16 | 16 | 10 | 26.37s |
| `2818d0e54ee3` | baseline | vulnerable | 3 | yes | 18 | 0 | 12 | 0.20s |
| `5d61223d6e3b` | nemotron-3-ultra | vulnerable | 3 | no | 30 | 16 | 11 | 104.38s |
| `f8bf0e295de2` | gpt-oss:120b | vulnerable | 3 | no | 16 | 16 | 10 | 9.92s |
| `f88d40ad3686` | nemotron-3-super | vulnerable | 3 | no | 16 | 16 | 9 | 22.68s |
| `defcfa8d36a6` | baseline | fixed | 3 | yes | 18 | 0 | 12 | 0.17s |
| `7d0f6521332b` | gpt-oss:120b | fixed | 3 | no | 16 | 16 | 10 | 11.58s |
| `61401af1c95f` | nemotron-3-super | fixed | 3 | no | 16 | 16 | 8 | 21.59s |
| `0882bd07e8b4` | nemotron-3-ultra | fixed | 3 | yes | 18 | 6 | 12 | 23.05s |
