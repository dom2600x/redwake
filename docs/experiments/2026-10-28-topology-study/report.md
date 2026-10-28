# Counterbalanced depth and branching discovery study

2026-10-28 (Australia/Perth). All 216 planned investigations are retained: 54 scripted
baselines and 162 live model runs. Each fixture/profile/backend cell contains three
vulnerable and three fixed runs. These are repeated deterministic synthetic cases, not
independent vulnerability classes or a general model ranking.

## Controls and execution

The [suite specification](../../topology-suite.md) records the graph layouts, allowances
and position rotation. Project/resource IDs, access semantics, content markers, six
verifier cases, tool schema and scope policy are held fixed. The reference uses one
opaque collection per account; deep adds an intermediate node; branch splits records
across two collections. Deep and branch each require 20 scripted probes; the reference
requires 18. The two added navigation probes reduce sequential headroom from six calls
to four when using one probe per call.

All three fixtures use the same recorded `graph` API guidance within each profile.
Current and sequential share initial messages; batching adds the existing batching
advice. This guidance explicitly permits intermediate nodes and multiple collections. It
differs from the earlier pilot, so cross-study differences cannot be attributed solely
to topology. Current and sequential do not disclose their model-call caps in the initial
prompts. Discovery feedback after a no-tool turn states remaining request allowance; it
does not announce the model-call cap. Different early choices before either cap binds
cannot be attributed to that cap alone.

| Profile | Requests | Calls | Reserved output tokens | Active seconds |
|---|---:|---:|---:|---:|
| current | 32 | 16 | 16,384 | 120 |
| sequential | 32 | 24 | 24,576 | 120 |
| batching | 32 | 16 | 16,384 | 120 |

Each inference reserves at most 1,024 output tokens and requests temperature zero. The
per-call timeout is at most 60 seconds, bounded by remaining active time. Inference is
serial. Baselines precede models in each profile. There are no retries, resumed
investigations, exclusions or extra allowances.

With three repetitions, each profile occupies each position once inside every
fixture/mode condition; each model occupies each model position once inside every
fixture/mode/profile condition. This balances positions, not all permutations or
carryover effects. Fixture and mode order remain fixed; provider state, caching and time
remain possible confounders.

Runtime was frozen at `1c3f2e814e2ec0a35274c47d896e1065dfd5b7ee` before inference, with
a clean starting tree. Exact prompts, hashes, source fingerprints and slot positions are
retained in [comparison.json](comparison.json). Between every twelve completed runs, an
operator checkpoint was committed and pushed. Those checkpoint pauses occur between
investigations and do not consume active-run allowances. The canonical bundle supersedes
the partial checkpoints preserved in Git history.

## Execution outcomes

All 54 baselines completed correctly: 18 probes on reference and 20 on both graph
variants. Live outcomes are separated below; pooled counts combine different conditions
and are not a capability ranking.

| Outcome | Live runs |
|---|---:|
| budget | 45 |
| completed | 75 |
| model_choice | 12 |
| provider_failure | 30 |

GPT-OSS received HTTP 500 diagnostics in 16/18 batching investigations across the three
graphs. Those failed calls are inference observations, not returned tool choices, and
stay in every result denominator. HTTP 500 occurred again under these graph-guidance
contexts; this does not reproduce the earlier original compatibility control or identify
a request field as the cause.

## Results by graph and profile

### discovery_links

| Profile | Backend | Correct runs | Proved flaws | Missed flaws | False positives | Calls |
|---|---|---:|---:|---:|---:|---:|
| current | baseline | 6/6 | 6/6 | 0 | 0 | 0 |
| current | gpt-oss:120b | 0/6 | 3/6 | 3 | 0 | 96 |
| current | nemotron-3-super | 0/6 | 5/6 | 1 | 0 | 96 |
| current | nemotron-3-ultra | 6/6 | 6/6 | 0 | 0 | 45 |
| sequential | baseline | 6/6 | 6/6 | 0 | 0 | 0 |
| sequential | gpt-oss:120b | 4/6 | 5/6 | 1 | 0 | 111 |
| sequential | nemotron-3-super | 3/6 | 4/6 | 2 | 0 | 128 |
| sequential | nemotron-3-ultra | 6/6 | 6/6 | 0 | 0 | 53 |
| batching | baseline | 6/6 | 6/6 | 0 | 0 | 0 |
| batching | gpt-oss:120b | 0/6 | 1/6 | 5 | 0 | 56 |
| batching | nemotron-3-super | 4/6 | 5/6 | 1 | 0 | 36 |
| batching | nemotron-3-ultra | 6/6 | 6/6 | 0 | 0 | 46 |

### discovery_deep

| Profile | Backend | Correct runs | Proved flaws | Missed flaws | False positives | Calls |
|---|---|---:|---:|---:|---:|---:|
| current | baseline | 6/6 | 6/6 | 0 | 0 | 0 |
| current | gpt-oss:120b | 0/6 | 2/6 | 4 | 0 | 93 |
| current | nemotron-3-super | 0/6 | 2/6 | 4 | 0 | 88 |
| current | nemotron-3-ultra | 3/6 | 4/6 | 2 | 0 | 55 |
| sequential | baseline | 6/6 | 6/6 | 0 | 0 | 0 |
| sequential | gpt-oss:120b | 1/6 | 5/6 | 1 | 0 | 129 |
| sequential | nemotron-3-super | 1/6 | 2/6 | 4 | 0 | 125 |
| sequential | nemotron-3-ultra | 3/6 | 5/6 | 1 | 0 | 61 |
| batching | baseline | 6/6 | 6/6 | 0 | 0 | 0 |
| batching | gpt-oss:120b | 0/6 | 0/6 | 6 | 0 | 48 |
| batching | nemotron-3-super | 5/6 | 6/6 | 0 | 0 | 42 |
| batching | nemotron-3-ultra | 3/6 | 6/6 | 0 | 0 | 60 |

### discovery_branch

| Profile | Backend | Correct runs | Proved flaws | Missed flaws | False positives | Calls |
|---|---|---:|---:|---:|---:|---:|
| current | baseline | 6/6 | 6/6 | 0 | 0 | 0 |
| current | gpt-oss:120b | 0/6 | 3/6 | 3 | 0 | 96 |
| current | nemotron-3-super | 0/6 | 2/6 | 4 | 0 | 93 |
| current | nemotron-3-ultra | 6/6 | 6/6 | 0 | 0 | 48 |
| sequential | baseline | 6/6 | 6/6 | 0 | 0 | 0 |
| sequential | gpt-oss:120b | 2/6 | 5/6 | 1 | 0 | 131 |
| sequential | nemotron-3-super | 5/6 | 6/6 | 0 | 0 | 125 |
| sequential | nemotron-3-ultra | 6/6 | 6/6 | 0 | 0 | 50 |
| batching | baseline | 6/6 | 6/6 | 0 | 0 | 0 |
| batching | gpt-oss:120b | 0/6 | 0/6 | 6 | 0 | 24 |
| batching | nemotron-3-super | 6/6 | 6/6 | 0 | 0 | 45 |
| batching | nemotron-3-ultra | 5/6 | 6/6 | 0 | 0 | 47 |

A correct run requires completed record/account coverage and every expected verifier
verdict, including the export’s expected inconclusive outcome. Each six-run cell has six
seeded-flaw opportunities from its three vulnerable runs; fixed runs contain no expected
flaws. Findings require owner and cross-account evidence. Repeating related cases does
not create independent vulnerability classes.

## Discovery and evidence collection

| Graph | Profile | Model | Links exposed | Record pairs attempted | Successful owner controls | Duplicate probes | Stops |
|---|---|---|---:|---:|---:|---:|---|
| discovery_links | current | gpt-oss:120b | 36/36 | 57/72 | 25/30 | 0 | budget: 5, model_choice: 1 |
| discovery_links | current | nemotron-3-super | 36/36 | 59/72 | 29/30 | 0 | budget: 6 |
| discovery_links | current | nemotron-3-ultra | 36/36 | 72/72 | 30/30 | 0 | completed: 6 |
| discovery_links | sequential | gpt-oss:120b | 36/36 | 67/72 | 29/30 | 2 | completed: 4, model_choice: 2 |
| discovery_links | sequential | nemotron-3-super | 36/36 | 67/72 | 28/30 | 4 | budget: 1, completed: 3, model_choice: 2 |
| discovery_links | sequential | nemotron-3-ultra | 36/36 | 72/72 | 30/30 | 6 | completed: 6 |
| discovery_links | batching | gpt-oss:120b | 27/36 | 18/72 | 10/30 | 0 | budget: 2, provider_failure: 4 |
| discovery_links | batching | nemotron-3-super | 36/36 | 66/72 | 29/30 | 0 | completed: 4, provider_failure: 2 |
| discovery_links | batching | nemotron-3-ultra | 36/36 | 72/72 | 30/30 | 0 | completed: 6 |
| discovery_deep | current | gpt-oss:120b | 36/36 | 44/72 | 24/30 | 0 | budget: 5, model_choice: 1 |
| discovery_deep | current | nemotron-3-super | 33/36 | 39/72 | 22/30 | 0 | budget: 5, model_choice: 1 |
| discovery_deep | current | nemotron-3-ultra | 30/36 | 57/72 | 23/30 | 0 | completed: 3, provider_failure: 3 |
| discovery_deep | sequential | gpt-oss:120b | 36/36 | 64/72 | 29/30 | 11 | budget: 2, completed: 1, model_choice: 3 |
| discovery_deep | sequential | nemotron-3-super | 30/36 | 54/72 | 23/30 | 3 | budget: 4, completed: 1, provider_failure: 1 |
| discovery_deep | sequential | nemotron-3-ultra | 36/36 | 69/72 | 29/30 | 14 | budget: 1, completed: 3, provider_failure: 2 |
| discovery_deep | batching | gpt-oss:120b | 25/36 | 0/72 | 0/30 | 0 | provider_failure: 6 |
| discovery_deep | batching | nemotron-3-super | 36/36 | 66/72 | 28/30 | 2 | completed: 5, provider_failure: 1 |
| discovery_deep | batching | nemotron-3-ultra | 36/36 | 69/72 | 30/30 | 2 | completed: 3, provider_failure: 3 |
| discovery_branch | current | gpt-oss:120b | 36/36 | 48/72 | 25/30 | 0 | budget: 6 |
| discovery_branch | current | nemotron-3-super | 36/36 | 40/72 | 24/30 | 1 | budget: 5, provider_failure: 1 |
| discovery_branch | current | nemotron-3-ultra | 36/36 | 72/72 | 30/30 | 0 | completed: 6 |
| discovery_branch | sequential | gpt-oss:120b | 36/36 | 65/72 | 29/30 | 7 | budget: 2, completed: 2, model_choice: 2 |
| discovery_branch | sequential | nemotron-3-super | 36/36 | 71/72 | 30/30 | 1 | budget: 1, completed: 5 |
| discovery_branch | sequential | nemotron-3-ultra | 36/36 | 72/72 | 30/30 | 2 | completed: 6 |
| discovery_branch | batching | gpt-oss:120b | 0/36 | 0/72 | 0/30 | 0 | provider_failure: 6 |
| discovery_branch | batching | nemotron-3-super | 36/36 | 72/72 | 30/30 | 1 | completed: 6 |
| discovery_branch | batching | nemotron-3-ultra | 36/36 | 71/72 | 30/30 | 4 | completed: 5, provider_failure: 1 |

Each six-run cell can expose 36 resource links, attempt 72 distinct record/account pairs
and obtain 30 successful owner controls. The export is intentionally unavailable.
Captured link exposure does not prove the model recognised or used a link. Attempted
coverage does not imply successful controls or conclusive findings. Duplicate probes
repeat an account/path pair. Scope rejection stops a run before executing the rejected
proposal.

## Operational diagnostics and accounting

| Run | Graph | Profile | Model | Source | Category | HTTP | Call |
|---|---|---|---|---|---|---:|---:|
| [4e114c97e569](runs/4e114c97e569/state.json) | discovery_links | current | gpt-oss:120b | model | tool_contract |  | 16 |
| [422c5615d0f6](runs/422c5615d0f6/state.json) | discovery_links | sequential | nemotron-3-super | model | tool_contract |  | 24 |
| [813c6ac2f1ab](runs/813c6ac2f1ab/state.json) | discovery_links | batching | gpt-oss:120b | provider | http_server | 500 | 7 |
| [bc466b7a6c58](runs/bc466b7a6c58/state.json) | discovery_links | batching | gpt-oss:120b | provider | http_server | 500 | 7 |
| [7e28c29256ee](runs/7e28c29256ee/state.json) | discovery_deep | batching | gpt-oss:120b | provider | http_server | 500 | 9 |
| [5ce054e3402d](runs/5ce054e3402d/state.json) | discovery_deep | current | gpt-oss:120b | model | tool_contract |  | 13 |
| [b94701537d24](runs/b94701537d24/state.json) | discovery_deep | current | nemotron-3-ultra | provider | timeout |  | 10 |
| [b6826d5c68ed](runs/b6826d5c68ed/state.json) | discovery_deep | sequential | gpt-oss:120b | model | tool_contract |  | 21 |
| [48900d3cff98](runs/48900d3cff98/state.json) | discovery_deep | current | nemotron-3-ultra | provider | timeout |  | 2 |
| [4454fc7ddc2f](runs/4454fc7ddc2f/state.json) | discovery_deep | sequential | nemotron-3-ultra | provider | timeout |  | 10 |
| [d830e1f5b7fd](runs/d830e1f5b7fd/state.json) | discovery_deep | batching | gpt-oss:120b | provider | http_server | 500 | 3 |
| [4e0ca10b48c2](runs/4e0ca10b48c2/state.json) | discovery_branch | sequential | gpt-oss:120b | model | tool_contract |  | 18 |
| [f113c389a3cc](runs/f113c389a3cc/state.json) | discovery_branch | batching | gpt-oss:120b | provider | http_server | 500 | 5 |
| [de4463fe057e](runs/de4463fe057e/state.json) | discovery_branch | batching | gpt-oss:120b | provider | http_server | 500 | 3 |
| [0d499d179689](runs/0d499d179689/state.json) | discovery_links | sequential | nemotron-3-super | model | tool_contract |  | 19 |
| [84ed74597ae1](runs/84ed74597ae1/state.json) | discovery_links | batching | gpt-oss:120b | provider | http_server | 500 | 3 |
| [ffe7d87cf76a](runs/ffe7d87cf76a/state.json) | discovery_links | batching | nemotron-3-super | provider | http_server | 500 | 6 |
| [82e1662527cf](runs/82e1662527cf/state.json) | discovery_links | sequential | gpt-oss:120b | model | tool_contract |  | 19 |
| [8ea335cc8888](runs/8ea335cc8888/state.json) | discovery_deep | current | nemotron-3-super | model | tool_contract |  | 8 |
| [b83e894cbe57](runs/b83e894cbe57/state.json) | discovery_deep | current | nemotron-3-ultra | provider | timeout |  | 12 |
| [899b1bb09ded](runs/899b1bb09ded/state.json) | discovery_deep | sequential | nemotron-3-super | provider | http_server | 500 | 5 |
| [31c476337dbc](runs/31c476337dbc/state.json) | discovery_deep | batching | gpt-oss:120b | provider | http_server | 500 | 9 |
| [dabf3c68304d](runs/dabf3c68304d/state.json) | discovery_deep | batching | nemotron-3-ultra | provider | timeout |  | 13 |
| [021de11a61d3](runs/021de11a61d3/state.json) | discovery_deep | sequential | nemotron-3-ultra | provider | timeout |  | 10 |
| [cc1a9fbe8b81](runs/cc1a9fbe8b81/state.json) | discovery_deep | sequential | gpt-oss:120b | model | tool_contract |  | 19 |
| [72e52a07dac3](runs/72e52a07dac3/state.json) | discovery_deep | batching | gpt-oss:120b | provider | http_server | 500 | 9 |
| [2bc0c6c75ab0](runs/2bc0c6c75ab0/state.json) | discovery_deep | batching | nemotron-3-ultra | provider | timeout |  | 10 |
| [ef9e0dcf5eef](runs/ef9e0dcf5eef/state.json) | discovery_branch | batching | gpt-oss:120b | provider | http_server | 500 | 3 |
| [0a7883cbfe93](runs/0a7883cbfe93/state.json) | discovery_branch | batching | gpt-oss:120b | provider | http_server | 500 | 5 |
| [9b25a1e50310](runs/9b25a1e50310/state.json) | discovery_links | sequential | gpt-oss:120b | model | tool_contract |  | 15 |
| [49789f6e8172](runs/49789f6e8172/state.json) | discovery_links | batching | nemotron-3-super | provider | http_server | 500 | 7 |
| [050a4887cf9c](runs/050a4887cf9c/state.json) | discovery_links | batching | gpt-oss:120b | provider | http_server | 500 | 7 |
| [97401051f4c0](runs/97401051f4c0/state.json) | discovery_deep | sequential | gpt-oss:120b | model | tool_contract |  | 20 |
| [8471e2bcc949](runs/8471e2bcc949/state.json) | discovery_deep | batching | gpt-oss:120b | provider | http_server | 500 | 9 |
| [dac5e2527ec6](runs/dac5e2527ec6/state.json) | discovery_deep | batching | nemotron-3-super | provider | http_server | 500 | 11 |
| [83028bda9f2e](runs/83028bda9f2e/state.json) | discovery_deep | batching | nemotron-3-ultra | provider | timeout |  | 9 |
| [e234dd3e6e52](runs/e234dd3e6e52/state.json) | discovery_deep | batching | gpt-oss:120b | provider | http_server | 500 | 9 |
| [c023fcd3fad4](runs/c023fcd3fad4/state.json) | discovery_branch | batching | gpt-oss:120b | provider | http_server | 500 | 3 |
| [8e366d6e8ac7](runs/8e366d6e8ac7/state.json) | discovery_branch | sequential | gpt-oss:120b | model | tool_contract |  | 23 |
| [514c83243576](runs/514c83243576/state.json) | discovery_branch | batching | nemotron-3-ultra | provider | timeout |  | 12 |
| [d63b92b48a9d](runs/d63b92b48a9d/state.json) | discovery_branch | batching | gpt-oss:120b | provider | http_server | 500 | 5 |
| [6e436414c77f](runs/6e436414c77f/state.json) | discovery_branch | current | nemotron-3-super | provider | http_server | 500 | 13 |

30 live runs have incomplete provider usage. Reported input/output tokens are lower
bounds when usage is unknown; reserved calls and output allowance remain consumed.
Structured diagnostics use a fixed allowlist and omit credentials, response bodies and
arbitrary exception text. HTTP failures and timeouts identify operational observations,
not a model choice or a demonstrated provider root cause. A timeout may arise from the
per-call or remaining active-time bound.

| Profile | Live runs | Calls | Reserved output tokens | Observed input tokens | Observed output tokens | Unknown usage runs | Active seconds |
|---|---:|---:|---:|---:|---:|---:|---:|
| current | 54 | 710 | 727040 | 1065776 | 69212 | 4 | 1633.59 |
| sequential | 54 | 913 | 934912 | 1732321 | 132924 | 3 | 1894.55 |
| batching | 54 | 404 | 413696 | 623333 | 99589 | 23 | 1618.25 |

Stopped-run latency is not successful-investigation speed. Unknown usage is retained in
every denominator; no failed investigation is replaced.

## Repetitions and terminal causes

| Repetition | Graph | Profile | Backend | Correct runs | Terminal causes |
|---:|---|---|---|---:|---|
| 1 | discovery_links | current | gpt-oss:120b | 0/2 | Model-call budget exhausted: 1, Rejected tool call outside the lab contract: 1 |
| 1 | discovery_links | current | nemotron-3-super | 0/2 | Model-call budget exhausted: 2 |
| 1 | discovery_links | current | nemotron-3-ultra | 2/2 | completed: 2 |
| 1 | discovery_links | sequential | gpt-oss:120b | 2/2 | completed: 2 |
| 1 | discovery_links | sequential | nemotron-3-super | 1/2 | Rejected tool call outside the lab contract: 1, completed: 1 |
| 1 | discovery_links | sequential | nemotron-3-ultra | 2/2 | completed: 2 |
| 1 | discovery_links | batching | gpt-oss:120b | 0/2 | Provider failure (http_server); reservations retained: 2 |
| 1 | discovery_links | batching | nemotron-3-super | 2/2 | completed: 2 |
| 1 | discovery_links | batching | nemotron-3-ultra | 2/2 | completed: 2 |
| 1 | discovery_deep | current | gpt-oss:120b | 0/2 | Model-call budget exhausted: 1, Rejected tool call outside the lab contract: 1 |
| 1 | discovery_deep | current | nemotron-3-super | 0/2 | Model-call budget exhausted: 2 |
| 1 | discovery_deep | current | nemotron-3-ultra | 0/2 | Provider failure (timeout); reservations retained: 2 |
| 1 | discovery_deep | sequential | gpt-oss:120b | 1/2 | Rejected tool call outside the lab contract: 1, completed: 1 |
| 1 | discovery_deep | sequential | nemotron-3-super | 1/2 | Model-call budget exhausted: 1, completed: 1 |
| 1 | discovery_deep | sequential | nemotron-3-ultra | 1/2 | Provider failure (timeout); reservations retained: 1, completed: 1 |
| 1 | discovery_deep | batching | gpt-oss:120b | 0/2 | Provider failure (http_server); reservations retained: 2 |
| 1 | discovery_deep | batching | nemotron-3-super | 2/2 | completed: 2 |
| 1 | discovery_deep | batching | nemotron-3-ultra | 2/2 | completed: 2 |
| 1 | discovery_branch | current | gpt-oss:120b | 0/2 | Model-call budget exhausted: 2 |
| 1 | discovery_branch | current | nemotron-3-super | 0/2 | Model-call budget exhausted: 2 |
| 1 | discovery_branch | current | nemotron-3-ultra | 2/2 | completed: 2 |
| 1 | discovery_branch | sequential | gpt-oss:120b | 1/2 | Rejected tool call outside the lab contract: 1, completed: 1 |
| 1 | discovery_branch | sequential | nemotron-3-super | 2/2 | completed: 2 |
| 1 | discovery_branch | sequential | nemotron-3-ultra | 2/2 | completed: 2 |
| 1 | discovery_branch | batching | gpt-oss:120b | 0/2 | Provider failure (http_server); reservations retained: 2 |
| 1 | discovery_branch | batching | nemotron-3-super | 2/2 | completed: 2 |
| 1 | discovery_branch | batching | nemotron-3-ultra | 2/2 | completed: 2 |
| 2 | discovery_links | current | gpt-oss:120b | 0/2 | Model-call budget exhausted: 2 |
| 2 | discovery_links | current | nemotron-3-super | 0/2 | Model-call budget exhausted: 2 |
| 2 | discovery_links | current | nemotron-3-ultra | 2/2 | completed: 2 |
| 2 | discovery_links | sequential | gpt-oss:120b | 1/2 | Rejected tool call outside the lab contract: 1, completed: 1 |
| 2 | discovery_links | sequential | nemotron-3-super | 1/2 | Rejected tool call outside the lab contract: 1, completed: 1 |
| 2 | discovery_links | sequential | nemotron-3-ultra | 2/2 | completed: 2 |
| 2 | discovery_links | batching | gpt-oss:120b | 0/2 | Model-call budget exhausted: 1, Provider failure (http_server); reservations retained: 1 |
| 2 | discovery_links | batching | nemotron-3-super | 1/2 | Provider failure (http_server); reservations retained: 1, completed: 1 |
| 2 | discovery_links | batching | nemotron-3-ultra | 2/2 | completed: 2 |
| 2 | discovery_deep | current | gpt-oss:120b | 0/2 | Model-call budget exhausted: 2 |
| 2 | discovery_deep | current | nemotron-3-super | 0/2 | Model-call budget exhausted: 1, Rejected tool call outside the lab contract: 1 |
| 2 | discovery_deep | current | nemotron-3-ultra | 1/2 | Provider failure (timeout); reservations retained: 1, completed: 1 |
| 2 | discovery_deep | sequential | gpt-oss:120b | 0/2 | Model-call budget exhausted: 1, Rejected tool call outside the lab contract: 1 |
| 2 | discovery_deep | sequential | nemotron-3-super | 0/2 | Model-call budget exhausted: 1, Provider failure (http_server); reservations retained: 1 |
| 2 | discovery_deep | sequential | nemotron-3-ultra | 1/2 | Provider failure (timeout); reservations retained: 1, completed: 1 |
| 2 | discovery_deep | batching | gpt-oss:120b | 0/2 | Provider failure (http_server); reservations retained: 2 |
| 2 | discovery_deep | batching | nemotron-3-super | 2/2 | completed: 2 |
| 2 | discovery_deep | batching | nemotron-3-ultra | 0/2 | Provider failure (timeout); reservations retained: 2 |
| 2 | discovery_branch | current | gpt-oss:120b | 0/2 | Model-call budget exhausted: 2 |
| 2 | discovery_branch | current | nemotron-3-super | 0/2 | Model-call budget exhausted: 2 |
| 2 | discovery_branch | current | nemotron-3-ultra | 2/2 | completed: 2 |
| 2 | discovery_branch | sequential | gpt-oss:120b | 1/2 | Model-call budget exhausted: 1, completed: 1 |
| 2 | discovery_branch | sequential | nemotron-3-super | 2/2 | completed: 2 |
| 2 | discovery_branch | sequential | nemotron-3-ultra | 2/2 | completed: 2 |
| 2 | discovery_branch | batching | gpt-oss:120b | 0/2 | Provider failure (http_server); reservations retained: 2 |
| 2 | discovery_branch | batching | nemotron-3-super | 2/2 | completed: 2 |
| 2 | discovery_branch | batching | nemotron-3-ultra | 2/2 | completed: 2 |
| 3 | discovery_links | current | gpt-oss:120b | 0/2 | Model-call budget exhausted: 2 |
| 3 | discovery_links | current | nemotron-3-super | 0/2 | Model-call budget exhausted: 2 |
| 3 | discovery_links | current | nemotron-3-ultra | 2/2 | completed: 2 |
| 3 | discovery_links | sequential | gpt-oss:120b | 1/2 | Rejected tool call outside the lab contract: 1, completed: 1 |
| 3 | discovery_links | sequential | nemotron-3-super | 1/2 | Model-call budget exhausted: 1, completed: 1 |
| 3 | discovery_links | sequential | nemotron-3-ultra | 2/2 | completed: 2 |
| 3 | discovery_links | batching | gpt-oss:120b | 0/2 | Model-call budget exhausted: 1, Provider failure (http_server); reservations retained: 1 |
| 3 | discovery_links | batching | nemotron-3-super | 1/2 | Provider failure (http_server); reservations retained: 1, completed: 1 |
| 3 | discovery_links | batching | nemotron-3-ultra | 2/2 | completed: 2 |
| 3 | discovery_deep | current | gpt-oss:120b | 0/2 | Model-call budget exhausted: 2 |
| 3 | discovery_deep | current | nemotron-3-super | 0/2 | Model-call budget exhausted: 2 |
| 3 | discovery_deep | current | nemotron-3-ultra | 2/2 | completed: 2 |
| 3 | discovery_deep | sequential | gpt-oss:120b | 0/2 | Model-call budget exhausted: 1, Rejected tool call outside the lab contract: 1 |
| 3 | discovery_deep | sequential | nemotron-3-super | 0/2 | Model-call budget exhausted: 2 |
| 3 | discovery_deep | sequential | nemotron-3-ultra | 1/2 | Request budget exhausted: 1, completed: 1 |
| 3 | discovery_deep | batching | gpt-oss:120b | 0/2 | Provider failure (http_server); reservations retained: 2 |
| 3 | discovery_deep | batching | nemotron-3-super | 1/2 | Provider failure (http_server); reservations retained: 1, completed: 1 |
| 3 | discovery_deep | batching | nemotron-3-ultra | 1/2 | Provider failure (timeout); reservations retained: 1, completed: 1 |
| 3 | discovery_branch | current | gpt-oss:120b | 0/2 | Model-call budget exhausted: 2 |
| 3 | discovery_branch | current | nemotron-3-super | 0/2 | Model-call budget exhausted: 1, Provider failure (http_server); reservations retained: 1 |
| 3 | discovery_branch | current | nemotron-3-ultra | 2/2 | completed: 2 |
| 3 | discovery_branch | sequential | gpt-oss:120b | 0/2 | Model-call budget exhausted: 1, Rejected tool call outside the lab contract: 1 |
| 3 | discovery_branch | sequential | nemotron-3-super | 1/2 | Model-call budget exhausted: 1, completed: 1 |
| 3 | discovery_branch | sequential | nemotron-3-ultra | 2/2 | completed: 2 |
| 3 | discovery_branch | batching | gpt-oss:120b | 0/2 | Provider failure (http_server); reservations retained: 2 |
| 3 | discovery_branch | batching | nemotron-3-super | 2/2 | completed: 2 |
| 3 | discovery_branch | batching | nemotron-3-ultra | 1/2 | Provider failure (timeout); reservations retained: 1, completed: 1 |

Each repetition cell includes one vulnerable and one fixed run. This table retains
within-condition variation and terminal reasons rather than treating all incomplete runs
as one failure type.

### Illustrative retained traces

In [5ce054e3402d](runs/5ce054e3402d/state.json), GPT-OSS on deep/current proposed
`/api/records/export_z3` after all six resource links had been captured. The recorded
export link is `/api/exports/export_z3`. Only four record/account pairs had been
attempted. Scope rejected the proposal with three model calls, 3,072 reserved output
tokens and about 113 active seconds remaining. This is an invalid path choice during
evidence collection despite link exposure; inference had returned a tool proposal.

In [4e0ca10b48c2](runs/4e0ca10b48c2/state.json), GPT-OSS on branch/sequential proposed
`/api/records/nonexistent` after all six links were captured and nine record/account
pairs attempted. Six model calls and about 111 active seconds remained. This is a scope
stop with remaining allowance, not evidence that resource links were undiscovered.

In [8ea335cc8888](runs/8ea335cc8888/state.json), Super on deep/current had captured
three resource links and two record/account pairs. Its proposed path included a newline
and explanatory text after the project URL. Scope stopped the run with eight calls
remaining. Resource discovery was also incomplete. These examples explain recorded
mechanisms, not their prevalence; all runs remain in the tables.

In [a989018a5496](runs/a989018a5496/state.json), Ultra on deep/sequential exhausted all
32 requests after 14 model calls. All six resource links had been exposed, but only
eleven of twelve record/account pairs and four of five successful owner controls were
present. Thirteen requests repeated an account/path pair. Ten model calls and about 56
active seconds remained. This is a request-budget and repeated-probe observation after
resource exposure, distinct from discovery failure, call-cap exhaustion or a provider
diagnostic.

## Limitations and next work

The graphs remain three related deterministic fixtures over the same access cases. Deep
and branch match traversal cost, while the reference is cheaper. Within-condition order
balancing reduces one source of confounding but does not randomise fixture order,
eliminate provider variation or balance every carryover. Provider build identifiers are
not pinned. Exact scope allows valid inferred paths and terminates invalid guesses, so
this study measures both navigation and the existing scope policy. Three
temperature-zero repetitions are descriptive, not a calibrated uncertainty estimate or
evidence of external-target readiness.

Keep provider compatibility work conditional on a reproduced failing original control.
Any change to scope-rejection feedback belongs in a separate fixed treatment with its
own baseline and retained failures. Broader capability claims require more independent
cases and graphs.
