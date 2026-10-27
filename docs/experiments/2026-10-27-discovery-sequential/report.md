# Discovery comparison: sequential

2026-10-27 (Australia/Perth). Three repetitions of vulnerable and fixed discovery behaviour for the baseline and each of three Ollama Cloud models. All 24 planned runs are retained, including failures.

Read the [combined comparison and limitations](../2026-10-27-discovery-followup.md) alongside this batch.

## Controls

Profile `sequential`, prompt variant `original`. Each run allows 32 lab requests, 24 model calls, 24,576 reserved output tokens and 120 active seconds. Calls reserve up to 1,024 output tokens, use temperature 0 and a maximum 60-second provider timeout bounded by remaining active time.

Current and sequential use byte-identical initial guidance. Batching adds only advice to group independent known-path probes and wait for observations before dependent probes. Runtime module fingerprints, tool schema and fixtures are identical across the new batches. Prompts and allowances are fixed within each batch. Inference is serial; model order rotates between blocks. No run is retried, resumed, excluded or given extra allowances.

Initial prompt SHA-256: `742301a33f2497cdc57479547d5954ac1ec29da3fef61e9566c38a07b21065a2`. Tool schema SHA-256: `48705357fc66428a2b785b8fe8a2b2a49bed1f4296f5ce994d02db088139417d`. [comparison.json](comparison.json) records the complete controls, prompt and source fingerprints.

## Results

| Backend | Correct runs | Proven flaws / 6 | Missed flaws | False positives | Requests | Calls | Mean active seconds |
|---|---|---|---|---|---|---|---|
| baseline | 6/6 | 6 | 0 | 0 | 108 | 0 | 0.18 |
| gpt-oss:120b | 3/6 | 4 | 2 | 0 | 106 | 110 | 14.09 |
| nemotron-3-super | 3/6 | 6 | 0 | 0 | 119 | 119 | 23.60 |
| nemotron-3-ultra | 5/6 | 6 | 0 | 0 | 100 | 43 | 52.87 |

Correct runs require completed coverage and all verifier verdicts matching fixture expectations. The export outage correctly remains inconclusive. Findings require matched owner and cross-account responses; assistant prose is not graded. Mean time includes stopped runs, so it does not show successful-investigation latency.

## Discovery and evidence

| Backend | Record links exposed | Record/account pairs attempted | Successful owner controls | Duplicate probes | Runs proposing batches |
|---|---|---|---|---|---|
| baseline | 36/36 | 72/72 | 30/30 | 0 | 0 |
| gpt-oss:120b | 36/36 | 65/72 | 28/30 | 7 | 0 |
| nemotron-3-super | 36/36 | 69/72 | 30/30 | 6 | 1 |
| nemotron-3-ultra | 30/36 | 60/72 | 25/30 | 0 | 6 |

Each run can expose six record links, attempt twelve record/account pairs and obtain five successful owner controls; the sixth resource is an expected outage. Link exposure means the captured response contains the link, not that the model recognised or used it. Counts are summed across repeated runs. Duplicates repeat an account/path pair. Proposed batches contain multiple tool calls; some calls may remain unexecuted. The baseline produces no model responses.

## Stops and accounting

| Backend | Outcome / stop reason | Runs |
|---|---|---|
| baseline | Completed | 6 |
| gpt-oss:120b | Completed | 3 |
| gpt-oss:120b | Model-call budget exhausted | 1 |
| gpt-oss:120b | Rejected tool call outside the lab contract | 2 |
| nemotron-3-super | Completed | 3 |
| nemotron-3-super | Model-call budget exhausted | 1 |
| nemotron-3-super | Rejected tool call outside the lab contract | 2 |
| nemotron-3-ultra | Completed | 5 |
| nemotron-3-ultra | Provider failure (timeout); reservations retained | 1 |

| Backend | Returned input tokens | Returned output tokens | Usage complete |
|---|---|---|---|
| baseline | 0 | 0 | yes |
| gpt-oss:120b | 159,061 | 8,488 | yes |
| nemotron-3-super | 261,265 | 14,764 | yes |
| nemotron-3-ultra | 64,841 | 7,942 | no |

Incomplete usage leaves returned totals as lower bounds; failed calls keep their reservations. Token counts are not monetary cost. Safe provider categories locate the observed failure boundary without establishing root cause. A timeout near 120 seconds may reflect the remaining harness allowance rather than a service outage. Raw errors, headers and credentials are not diagnostic artifacts.

## Individual runs

| Run | Backend | Mode | Repeat | Correct | Requests / calls | Links / 6 | Pairs / 12 | Owner controls / 5 | Stop category |
|---|---|---|---|---|---|---|---|---|---|
| [12af0e943c98](runs/12af0e943c98/report.md) | baseline | vulnerable | 1 | yes | 18 / 0 | 6 | 12 | 5 | completed |
| [2695eed70845](runs/2695eed70845/report.md) | gpt-oss:120b | vulnerable | 1 | no | 14 / 15 | 6 | 8 | 4 | model_choice |
| [906de9695487](runs/906de9695487/report.md) | nemotron-3-super | vulnerable | 1 | no | 24 / 24 | 6 | 11 | 5 | budget |
| [731ba8a0da13](runs/731ba8a0da13/report.md) | nemotron-3-ultra | vulnerable | 1 | yes | 18 / 6 | 6 | 12 | 5 | completed |
| [fb507d01da47](runs/fb507d01da47/report.md) | baseline | fixed | 1 | yes | 18 / 0 | 6 | 12 | 5 | completed |
| [489d11e67d47](runs/489d11e67d47/report.md) | nemotron-3-super | fixed | 1 | yes | 21 / 22 | 6 | 12 | 5 | completed |
| [f8109fc57e3b](runs/f8109fc57e3b/report.md) | nemotron-3-ultra | fixed | 1 | yes | 22 / 8 | 6 | 12 | 5 | completed |
| [b9a72238a1ef](runs/b9a72238a1ef/report.md) | gpt-oss:120b | fixed | 1 | yes | 18 / 18 | 6 | 12 | 5 | completed |
| [218cc7572162](runs/218cc7572162/report.md) | baseline | vulnerable | 2 | yes | 18 / 0 | 6 | 12 | 5 | completed |
| [488eae9e1cee](runs/488eae9e1cee/report.md) | nemotron-3-super | vulnerable | 2 | yes | 18 / 15 | 6 | 12 | 5 | completed |
| [a82cfa32443f](runs/a82cfa32443f/report.md) | nemotron-3-ultra | vulnerable | 2 | yes | 18 / 6 | 6 | 12 | 5 | completed |
| [c03bf6b3f2e0](runs/c03bf6b3f2e0/report.md) | gpt-oss:120b | vulnerable | 2 | yes | 18 / 18 | 6 | 12 | 5 | completed |
| [ebe122209e4f](runs/ebe122209e4f/report.md) | baseline | fixed | 2 | yes | 18 / 0 | 6 | 12 | 5 | completed |
| [8b81a5ee724f](runs/8b81a5ee724f/report.md) | nemotron-3-ultra | fixed | 2 | no | 4 / 3 | 0 | 0 | 0 | provider_failure |
| [e473d80f2173](runs/e473d80f2173/report.md) | gpt-oss:120b | fixed | 2 | yes | 16 / 16 | 6 | 12 | 5 | completed |
| [ddc7460ba28a](runs/ddc7460ba28a/report.md) | nemotron-3-super | fixed | 2 | yes | 20 / 20 | 6 | 12 | 5 | completed |
| [5dbc52e6f2ba](runs/5dbc52e6f2ba/report.md) | baseline | vulnerable | 3 | yes | 18 / 0 | 6 | 12 | 5 | completed |
| [cfcbe7e0b26f](runs/cfcbe7e0b26f/report.md) | nemotron-3-ultra | vulnerable | 3 | yes | 20 / 11 | 6 | 12 | 5 | completed |
| [d303247e1292](runs/d303247e1292/report.md) | gpt-oss:120b | vulnerable | 3 | no | 23 / 24 | 6 | 11 | 4 | budget |
| [4d9526651cde](runs/4d9526651cde/report.md) | nemotron-3-super | vulnerable | 3 | no | 19 / 20 | 6 | 11 | 5 | model_choice |
| [ac71996b0079](runs/ac71996b0079/report.md) | baseline | fixed | 3 | yes | 18 / 0 | 6 | 12 | 5 | completed |
| [baaf186be6a8](runs/baaf186be6a8/report.md) | gpt-oss:120b | fixed | 3 | no | 17 / 19 | 6 | 10 | 5 | model_choice |
| [1abe9cf326c7](runs/1abe9cf326c7/report.md) | nemotron-3-super | fixed | 3 | no | 17 / 18 | 6 | 11 | 5 | model_choice |
| [b64ac92a0a22](runs/b64ac92a0a22/report.md) | nemotron-3-ultra | fixed | 3 | yes | 18 / 9 | 6 | 12 | 5 | completed |

## Reproduction and limitations

```sh
python3 -m redwake.comparison --profile sequential --repeat 3
python3 scripts/verify_experiments.py docs/experiments/2026-10-27-discovery-sequential
```

The live command makes a new experiment, not a reconstruction of historical conversations or timings. Offline verification checks this bundle without inference. Original states, conversations, responses and reports are under `runs/`. [results.json](results.json) contains offline rechecks; [manifest.json](manifest.json) records provenance and hashes.

Recorded source revision: `84b357746d2ab8456f28fa2a8d341c59a2849250`; dirty tree: `False`. All new batches use the same runtime module hashes from committed implementation 8da7eb8; later commits checkpoint evidence without changing runtime code. The October 11 historical batch is unchanged.

The sample is six runs per backend on deterministic synthetic cases. The document and attachment are related. Strict scope, output reservations, a fixed time cap and provider behaviour affect outcomes. Models receive generic recovery guidance, not missing-resource answers or a live call-budget countdown. Batch order was current, sequential, batching; time, caches and alias changes remain confounds. These results do not establish general security-testing capability or a reliable latency ranking.
