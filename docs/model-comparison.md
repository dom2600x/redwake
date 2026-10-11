# First live Ollama comparison

2026-10-10. Direct Ollama Cloud inference against the synthetic loopback lab. Each model ran twice against vulnerable behaviour and twice against fixed behaviour with the same default budgets. Results were read from SQLite and checked using the independent evidence verifier.

| Model | Correct runs | Total model calls | Total input tokens | Total output tokens | Mean active time per run |
|---|---:|---:|---:|---:|---:|
| gpt-oss:120b | 4/4 | 24 | 16,951 | 1,733 | 7.92s |
| nemotron-3-super | 4/4 | 24 | 24,110 | 2,180 | 13.28s |
| nemotron-3-ultra | 4/4 | 14 | 11,869 | 1,536 | 29.65s |

Every run executed exactly six probes, completed with conclusive coverage, and reported complete provider token usage. Vulnerable cases produced two vulnerable verdicts and one public_allowed verdict. Fixed cases produced two protected verdicts and one public_allowed verdict. No run required a missing-check recovery prompt.

GPT-OSS used approximately 29% fewer combined recorded tokens and took approximately 40% less active time than Super in this sample. Ultra used approximately 28% fewer combined recorded tokens than GPT-OSS, but took approximately 3.7 times as long. Token totals are not monetary costs; model tokenisation, caching and account billing may differ.

Ultra issued all six probes in a single model response in both fixed runs; it issued one probe per response in both vulnerable runs. GPT-OSS and Super issued one probe per response in all their runs. This explains much of Ultra's lower aggregate prompt usage. The sample does not establish that the lab mode caused the batching difference: models receive the same initial contract in both modes and choose their initial tool calls before seeing any lab responses.

Keep GPT-OSS as the default baseline for the next experiment, with Ultra as a challenger on harder cases and Super as the other comparison model. All three tie on correctness here. The sample establishes successful tool execution and correct harness verdicts for these fixtures. The model was given the endpoints, actors and expected access rules, while the verifier made the final classifications; this does not establish broader security-testing ability. The next useful experiment requires resource discovery and less explicit investigation guidance. Four runs per model and cloud runs taken at different times are insufficient for a general latency or capability ranking.

| Run | Model | Lab | Model calls | Input tokens | Output tokens | Active time |
|---|---|---|---:|---:|---:|---:|
| 433800a5e27b | gpt-oss:120b | vulnerable | 6 | 4,317 | 448 | 7.84s |
| a098f1ef794f | gpt-oss:120b | fixed | 6 | 4,127 | 406 | 8.75s |
| 538011a2646e | gpt-oss:120b | vulnerable | 6 | 4,330 | 463 | 7.95s |
| 4d25a02019ea | gpt-oss:120b | fixed | 6 | 4,177 | 416 | 7.12s |
| 899affb8c81b | nemotron-3-super | vulnerable | 6 | 6,346 | 640 | 14.51s |
| 7cefd3613f48 | nemotron-3-super | fixed | 6 | 5,595 | 442 | 9.13s |
| e402ba23cc76 | nemotron-3-super | vulnerable | 6 | 6,140 | 577 | 18.41s |
| 322a9e1c7b35 | nemotron-3-super | fixed | 6 | 6,029 | 521 | 11.08s |
| 97ffdf75dc71 | nemotron-3-ultra | vulnerable | 6 | 5,246 | 372 | 39.18s |
| 614dd2265662 | nemotron-3-ultra | fixed | 1 | 535 | 379 | 10.74s |
| d492eb307711 | nemotron-3-ultra | vulnerable | 6 | 5,553 | 423 | 46.01s |
| 59f9fc5c3a6c | nemotron-3-ultra | fixed | 1 | 535 | 362 | 22.66s |

Raw reports and evidence are retained under `.redwake/reports/<run-id>/`; conversations and cumulative accounting are retained in `.redwake/runs.sqlite3`.
