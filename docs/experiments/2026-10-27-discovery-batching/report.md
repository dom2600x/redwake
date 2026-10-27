# Discovery comparison: batching

2026-10-27 (Australia/Perth). Three repetitions of vulnerable and fixed discovery behaviour for the baseline and each of three Ollama Cloud models. All 24 planned runs are retained, including failures.

Read the [combined comparison and limitations](../2026-10-27-discovery-followup.md) alongside this batch.

## Controls

Profile `batching`, prompt variant `batching`. Each run allows 32 lab requests, 16 model calls, 16,384 reserved output tokens and 120 active seconds. Calls reserve up to 1,024 output tokens, use temperature 0 and a maximum 60-second provider timeout bounded by remaining active time.

Current and sequential use byte-identical initial guidance. Batching adds only advice to group independent known-path probes and wait for observations before dependent probes. Runtime module fingerprints, tool schema and fixtures are identical across the new batches. Prompts and allowances are fixed within each batch. Inference is serial; model order rotates between blocks. No run is retried, resumed, excluded or given extra allowances.

Initial prompt SHA-256: `2ab26537d4e9fbaea89307d3265b27ad0fb740d7d7eeb0b6eb3414ee344c1689`. Tool schema SHA-256: `48705357fc66428a2b785b8fe8a2b2a49bed1f4296f5ce994d02db088139417d`. [comparison.json](comparison.json) records the complete controls, prompt and source fingerprints.

## Results

| Backend | Correct runs | Proven flaws / 6 | Missed flaws | False positives | Requests | Calls | Mean active seconds |
|---|---|---|---|---|---|---|---|
| baseline | 6/6 | 6 | 0 | 0 | 108 | 0 | 0.18 |
| gpt-oss:120b | 0/6 | 0 | 6 | 0 | 26 | 32 | 3.45 |
| nemotron-3-super | 3/6 | 6 | 0 | 0 | 128 | 57 | 29.02 |
| nemotron-3-ultra | 5/6 | 5 | 1 | 0 | 102 | 41 | 56.17 |

Correct runs require completed coverage and all verifier verdicts matching fixture expectations. The export outage correctly remains inconclusive. Findings require matched owner and cross-account responses; assistant prose is not graded. Mean time includes stopped runs, so it does not show successful-investigation latency.

## Discovery and evidence

| Backend | Record links exposed | Record/account pairs attempted | Successful owner controls | Duplicate probes | Runs proposing batches |
|---|---|---|---|---|---|
| baseline | 36/36 | 72/72 | 30/30 | 0 | 0 |
| gpt-oss:120b | 10/36 | 0/72 | 0/30 | 0 | 0 |
| nemotron-3-super | 36/36 | 68/72 | 30/30 | 16 | 6 |
| nemotron-3-ultra | 36/36 | 66/72 | 28/30 | 0 | 6 |

Each run can expose six record links, attempt twelve record/account pairs and obtain five successful owner controls; the sixth resource is an expected outage. Link exposure means the captured response contains the link, not that the model recognised or used it. Counts are summed across repeated runs. Duplicates repeat an account/path pair. Proposed batches contain multiple tool calls; some calls may remain unexecuted. The baseline produces no model responses.

## Stops and accounting

| Backend | Outcome / stop reason | Runs |
|---|---|---|
| baseline | Completed | 6 |
| gpt-oss:120b | Provider failure (http_server); reservations retained | 6 |
| nemotron-3-super | Completed | 3 |
| nemotron-3-super | Model-call budget exhausted | 1 |
| nemotron-3-super | Provider failure (http_server); reservations retained | 1 |
| nemotron-3-super | Request budget exhausted | 1 |
| nemotron-3-ultra | Completed | 5 |
| nemotron-3-ultra | Provider failure (timeout); reservations retained | 1 |

| Backend | Returned input tokens | Returned output tokens | Usage complete |
|---|---|---|---|
| baseline | 0 | 0 | yes |
| gpt-oss:120b | 16,464 | 1,539 | no |
| nemotron-3-super | 126,209 | 23,433 | no |
| nemotron-3-ultra | 60,220 | 8,568 | no |

Incomplete usage leaves returned totals as lower bounds; failed calls keep their reservations. Token counts are not monetary cost. Safe provider categories locate the observed failure boundary without establishing root cause. A timeout near 120 seconds may reflect the remaining harness allowance rather than a service outage. Raw errors, headers and credentials are not diagnostic artifacts.

## Individual runs

| Run | Backend | Mode | Repeat | Correct | Requests / calls | Links / 6 | Pairs / 12 | Owner controls / 5 | Stop category |
|---|---|---|---|---|---|---|---|---|---|
| [cd36089706a7](runs/cd36089706a7/report.md) | baseline | vulnerable | 1 | yes | 18 / 0 | 6 | 12 | 5 | completed |
| [65224d9d368f](runs/65224d9d368f/report.md) | gpt-oss:120b | vulnerable | 1 | no | 4 / 5 | 0 | 0 | 0 | provider_failure |
| [15be497ecd29](runs/15be497ecd29/report.md) | nemotron-3-super | vulnerable | 1 | yes | 18 / 6 | 6 | 12 | 5 | completed |
| [22e87c8833f3](runs/22e87c8833f3/report.md) | nemotron-3-ultra | vulnerable | 1 | yes | 18 / 6 | 6 | 12 | 5 | completed |
| [0571412617f8](runs/0571412617f8/report.md) | baseline | fixed | 1 | yes | 18 / 0 | 6 | 12 | 5 | completed |
| [3130bcd41596](runs/3130bcd41596/report.md) | nemotron-3-super | fixed | 1 | no | 16 / 7 | 6 | 10 | 5 | provider_failure |
| [83f040f84308](runs/83f040f84308/report.md) | nemotron-3-ultra | fixed | 1 | yes | 18 / 8 | 6 | 12 | 5 | completed |
| [6de713024997](runs/6de713024997/report.md) | gpt-oss:120b | fixed | 1 | no | 4 / 5 | 0 | 0 | 0 | provider_failure |
| [1cf7fa88ba38](runs/1cf7fa88ba38/report.md) | baseline | vulnerable | 2 | yes | 18 / 0 | 6 | 12 | 5 | completed |
| [fa0d6b938881](runs/fa0d6b938881/report.md) | nemotron-3-super | vulnerable | 2 | no | 32 / 14 | 6 | 11 | 5 | budget |
| [18971e9a387b](runs/18971e9a387b/report.md) | nemotron-3-ultra | vulnerable | 2 | no | 12 / 7 | 6 | 6 | 3 | provider_failure |
| [e16ce651d54c](runs/e16ce651d54c/report.md) | gpt-oss:120b | vulnerable | 2 | no | 6 / 7 | 5 | 0 | 0 | provider_failure |
| [a86b140c468f](runs/a86b140c468f/report.md) | baseline | fixed | 2 | yes | 18 / 0 | 6 | 12 | 5 | completed |
| [9edd87d11320](runs/9edd87d11320/report.md) | nemotron-3-ultra | fixed | 2 | yes | 18 / 6 | 6 | 12 | 5 | completed |
| [4d808263c700](runs/4d808263c700/report.md) | gpt-oss:120b | fixed | 2 | no | 4 / 5 | 0 | 0 | 0 | provider_failure |
| [23f1dfda7607](runs/23f1dfda7607/report.md) | nemotron-3-super | fixed | 2 | no | 21 / 16 | 6 | 11 | 5 | budget |
| [32db4be8847b](runs/32db4be8847b/report.md) | baseline | vulnerable | 3 | yes | 18 / 0 | 6 | 12 | 5 | completed |
| [a42d0817a1a4](runs/a42d0817a1a4/report.md) | nemotron-3-ultra | vulnerable | 3 | yes | 18 / 8 | 6 | 12 | 5 | completed |
| [3473a9893b4d](runs/3473a9893b4d/report.md) | gpt-oss:120b | vulnerable | 3 | no | 2 / 3 | 0 | 0 | 0 | provider_failure |
| [7a0efa8ba596](runs/7a0efa8ba596/report.md) | nemotron-3-super | vulnerable | 3 | yes | 19 / 6 | 6 | 12 | 5 | completed |
| [aae0d27c548e](runs/aae0d27c548e/report.md) | baseline | fixed | 3 | yes | 18 / 0 | 6 | 12 | 5 | completed |
| [9fa32359a61c](runs/9fa32359a61c/report.md) | gpt-oss:120b | fixed | 3 | no | 6 / 7 | 5 | 0 | 0 | provider_failure |
| [d149da306419](runs/d149da306419/report.md) | nemotron-3-super | fixed | 3 | yes | 22 / 8 | 6 | 12 | 5 | completed |
| [079576f1e569](runs/079576f1e569/report.md) | nemotron-3-ultra | fixed | 3 | yes | 18 / 6 | 6 | 12 | 5 | completed |

## Reproduction and limitations

```sh
python3 -m redwake.comparison --profile batching --repeat 3
python3 scripts/verify_experiments.py docs/experiments/2026-10-27-discovery-batching
```

The live command makes a new experiment, not a reconstruction of historical conversations or timings. Offline verification checks this bundle without inference. Original states, conversations, responses and reports are under `runs/`. [results.json](results.json) contains offline rechecks; [manifest.json](manifest.json) records provenance and hashes.

Recorded source revision: `4d6aefb6b9f5634e859215f2350c8c28ba26c064`; dirty tree: `False`. All new batches use the same runtime module hashes from committed implementation 8da7eb8; later commits checkpoint evidence without changing runtime code. The October 11 historical batch is unchanged.

The sample is six runs per backend on deterministic synthetic cases. The document and attachment are related. Strict scope, output reservations, a fixed time cap and provider behaviour affect outcomes. Models receive generic recovery guidance, not missing-resource answers or a live call-budget countdown. Batch order was current, sequential, batching; time, caches and alias changes remain confounds. These results do not establish general security-testing capability or a reliable latency ranking.
