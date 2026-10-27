# Discovery comparison: current

2026-10-27 (Australia/Perth). Three repetitions of vulnerable and fixed discovery behaviour for the baseline and each of three Ollama Cloud models. All 24 planned runs are retained, including failures.

Read the [combined comparison and limitations](../2026-10-27-discovery-followup.md) alongside this batch.

## Controls

Profile `current`, prompt variant `original`. Each run allows 32 lab requests, 16 model calls, 16,384 reserved output tokens and 120 active seconds. Calls reserve up to 1,024 output tokens, use temperature 0 and a maximum 60-second provider timeout bounded by remaining active time.

Current and sequential use byte-identical initial guidance. Batching adds only advice to group independent known-path probes and wait for observations before dependent probes. Runtime module fingerprints, tool schema and fixtures are identical across the new batches. Prompts and allowances are fixed within each batch. Inference is serial; model order rotates between blocks. No run is retried, resumed, excluded or given extra allowances.

Initial prompt SHA-256: `742301a33f2497cdc57479547d5954ac1ec29da3fef61e9566c38a07b21065a2`. Tool schema SHA-256: `48705357fc66428a2b785b8fe8a2b2a49bed1f4296f5ce994d02db088139417d`. [comparison.json](comparison.json) records the complete controls, prompt and source fingerprints.

## Results

| Backend | Correct runs | Proven flaws / 6 | Missed flaws | False positives | Requests | Calls | Mean active seconds |
|---|---|---|---|---|---|---|---|
| baseline | 6/6 | 6 | 0 | 0 | 108 | 0 | 0.22 |
| gpt-oss:120b | 2/6 | 4 | 2 | 0 | 96 | 96 | 10.98 |
| nemotron-3-super | 0/6 | 2 | 4 | 0 | 95 | 96 | 21.09 |
| nemotron-3-ultra | 6/6 | 6 | 0 | 0 | 108 | 44 | 52.95 |

Correct runs require completed coverage and all verifier verdicts matching fixture expectations. The export outage correctly remains inconclusive. Findings require matched owner and cross-account responses; assistant prose is not graded. Mean time includes stopped runs, so it does not show successful-investigation latency.

## Discovery and evidence

| Backend | Record links exposed | Record/account pairs attempted | Successful owner controls | Duplicate probes | Runs proposing batches |
|---|---|---|---|---|---|
| baseline | 36/36 | 72/72 | 30/30 | 0 | 0 |
| gpt-oss:120b | 36/36 | 63/72 | 28/30 | 1 | 0 |
| nemotron-3-super | 36/36 | 57/72 | 26/30 | 0 | 0 |
| nemotron-3-ultra | 36/36 | 72/72 | 30/30 | 0 | 6 |

Each run can expose six record links, attempt twelve record/account pairs and obtain five successful owner controls; the sixth resource is an expected outage. Link exposure means the captured response contains the link, not that the model recognised or used it. Counts are summed across repeated runs. Duplicates repeat an account/path pair. Proposed batches contain multiple tool calls; some calls may remain unexecuted. The baseline produces no model responses.

## Stops and accounting

| Backend | Outcome / stop reason | Runs |
|---|---|---|
| baseline | Completed | 6 |
| gpt-oss:120b | Completed | 2 |
| gpt-oss:120b | Model-call budget exhausted | 4 |
| nemotron-3-super | Model-call budget exhausted | 5 |
| nemotron-3-super | Rejected tool call outside the lab contract | 1 |
| nemotron-3-ultra | Completed | 6 |

| Backend | Returned input tokens | Returned output tokens | Usage complete |
|---|---|---|---|
| baseline | 0 | 0 | yes |
| gpt-oss:120b | 118,149 | 5,215 | yes |
| nemotron-3-super | 169,721 | 9,348 | yes |
| nemotron-3-ultra | 65,162 | 8,309 | yes |

Incomplete usage leaves returned totals as lower bounds; failed calls keep their reservations. Token counts are not monetary cost. Safe provider categories locate the observed failure boundary without establishing root cause. A timeout near 120 seconds may reflect the remaining harness allowance rather than a service outage. Raw errors, headers and credentials are not diagnostic artifacts.

## Individual runs

| Run | Backend | Mode | Repeat | Correct | Requests / calls | Links / 6 | Pairs / 12 | Owner controls / 5 | Stop category |
|---|---|---|---|---|---|---|---|---|---|
| [1c02cf284074](runs/1c02cf284074/report.md) | baseline | vulnerable | 1 | yes | 18 / 0 | 6 | 12 | 5 | completed |
| [b6e1d72da4f7](runs/b6e1d72da4f7/report.md) | gpt-oss:120b | vulnerable | 1 | no | 16 / 16 | 6 | 9 | 5 | budget |
| [6a0622b9fd5c](runs/6a0622b9fd5c/report.md) | nemotron-3-super | vulnerable | 1 | no | 16 / 16 | 6 | 10 | 4 | budget |
| [0ae8a362692b](runs/0ae8a362692b/report.md) | nemotron-3-ultra | vulnerable | 1 | yes | 18 / 10 | 6 | 12 | 5 | completed |
| [f9ed7446281d](runs/f9ed7446281d/report.md) | baseline | fixed | 1 | yes | 18 / 0 | 6 | 12 | 5 | completed |
| [99b42114715c](runs/99b42114715c/report.md) | nemotron-3-super | fixed | 1 | no | 16 / 16 | 6 | 10 | 4 | budget |
| [5250aaf3321e](runs/5250aaf3321e/report.md) | nemotron-3-ultra | fixed | 1 | yes | 18 / 7 | 6 | 12 | 5 | completed |
| [65657cf1663c](runs/65657cf1663c/report.md) | gpt-oss:120b | fixed | 1 | no | 16 / 16 | 6 | 10 | 5 | budget |
| [b38ab1f2b9fa](runs/b38ab1f2b9fa/report.md) | baseline | vulnerable | 2 | yes | 18 / 0 | 6 | 12 | 5 | completed |
| [5211cd022aaa](runs/5211cd022aaa/report.md) | nemotron-3-super | vulnerable | 2 | no | 16 / 16 | 6 | 8 | 4 | budget |
| [93da03f8b04e](runs/93da03f8b04e/report.md) | nemotron-3-ultra | vulnerable | 2 | yes | 18 / 8 | 6 | 12 | 5 | completed |
| [ee457c8f33e6](runs/ee457c8f33e6/report.md) | gpt-oss:120b | vulnerable | 2 | no | 16 / 16 | 6 | 10 | 4 | budget |
| [135ac71e675f](runs/135ac71e675f/report.md) | baseline | fixed | 2 | yes | 18 / 0 | 6 | 12 | 5 | completed |
| [1f7319060024](runs/1f7319060024/report.md) | nemotron-3-ultra | fixed | 2 | yes | 18 / 6 | 6 | 12 | 5 | completed |
| [06b02473cb16](runs/06b02473cb16/report.md) | gpt-oss:120b | fixed | 2 | yes | 16 / 16 | 6 | 12 | 5 | completed |
| [06a5f36b99ee](runs/06a5f36b99ee/report.md) | nemotron-3-super | fixed | 2 | no | 15 / 16 | 6 | 9 | 4 | model_choice |
| [e6e02ee92879](runs/e6e02ee92879/report.md) | baseline | vulnerable | 3 | yes | 18 / 0 | 6 | 12 | 5 | completed |
| [8e3432b6b48e](runs/8e3432b6b48e/report.md) | nemotron-3-ultra | vulnerable | 3 | yes | 18 / 6 | 6 | 12 | 5 | completed |
| [9118780d3263](runs/9118780d3263/report.md) | gpt-oss:120b | vulnerable | 3 | no | 16 / 16 | 6 | 10 | 4 | budget |
| [bd1d1545c8e1](runs/bd1d1545c8e1/report.md) | nemotron-3-super | vulnerable | 3 | no | 16 / 16 | 6 | 10 | 5 | budget |
| [a041f170f3ef](runs/a041f170f3ef/report.md) | baseline | fixed | 3 | yes | 18 / 0 | 6 | 12 | 5 | completed |
| [852978e23b80](runs/852978e23b80/report.md) | gpt-oss:120b | fixed | 3 | yes | 16 / 16 | 6 | 12 | 5 | completed |
| [ed5e77351899](runs/ed5e77351899/report.md) | nemotron-3-super | fixed | 3 | no | 16 / 16 | 6 | 10 | 5 | budget |
| [2eec107459cd](runs/2eec107459cd/report.md) | nemotron-3-ultra | fixed | 3 | yes | 18 / 7 | 6 | 12 | 5 | completed |

## Reproduction and limitations

```sh
python3 -m redwake.comparison --profile current --repeat 3
python3 scripts/verify_experiments.py docs/experiments/2026-10-27-discovery-current
```

The live command makes a new experiment, not a reconstruction of historical conversations or timings. Offline verification checks this bundle without inference. Original states, conversations, responses and reports are under `runs/`. [results.json](results.json) contains offline rechecks; [manifest.json](manifest.json) records provenance and hashes.

Recorded source revision: `8da7eb8f03c5f1af16589fd0bfb58d2fb4e7e76d`; dirty tree: `False`. All new batches use the same runtime module hashes from committed implementation 8da7eb8; later commits checkpoint evidence without changing runtime code. The October 11 historical batch is unchanged.

The sample is six runs per backend on deterministic synthetic cases. The document and attachment are related. Strict scope, output reservations, a fixed time cap and provider behaviour affect outcomes. Models receive generic recovery guidance, not missing-resource answers or a live call-budget countdown. Batch order was current, sequential, batching; time, caches and alias changes remain confounds. These results do not establish general security-testing capability or a reliable latency ranking.
