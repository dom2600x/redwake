# Varied discovery fixtures and rotated profile order

2026-10-28 (Australia/Perth). This pilot retains all 72 planned investigations:
18 scripted baselines and 54 model runs. It compares the existing three
profiles inside each fixture/mode block across the original fixture, renamed
IDs and opaque collection links. Each cell has only one vulnerable and one
fixed run; the results describe this pilot rather than stability or general
security-testing capability.

## Controls and execution order

The current and sequential profiles share original discovery guidance; batching
adds the same existing batching advice. Every fixture receives the same initial
messages within each profile. The independent verifier keeps the same six access
cases, ownership, content markers and behaviour expectations across variants.

| Fixture | Deliberate change |
|---|---|
| discovery | Original IDs and nested collection paths |
| discovery_ids | Project/resource IDs changed; navigation structure preserved |
| discovery_links | Original IDs; opaque collection paths returned by project links |

The two new fixtures change different factors; IDs and link layout are not
changed together. All healthy baselines need 18 probes: six navigation
account/path pairs and twelve record pairs. Opaque collections make the original
`/api/projects/ID/records` shortcut out of scope, but the executor still enforces
an exact allowlist rather than proving how each proposed path was discovered.

| Profile | Requests | Model calls | Reserved output tokens | Active seconds |
|---|---:|---:|---:|---:|
| current | 32 | 16 | 16,384 | 120 |
| sequential | 32 | 24 | 24,576 | 120 |
| batching | 32 | 16 | 16,384 | 120 |

Each call requests at most 1,024 output tokens at temperature zero. A provider
call has a maximum 60-second timeout bounded by remaining active time. Inference
is serial. Profiles rotate inside blocks; model order rotates inside profiles.
Baseline runs precede models in every profile block. There are no retries,
resumptions, exclusions or extra allowances for failed runs.

The pilot uses `--repeat 1`: each profile is first, middle and last twice
overall, but not within every fixture/mode condition. `--repeat 3` would rotate
both profile and model positions within each condition; that larger 216-run
study was not run here. Fixture order remains original, IDs, opaque links,
with vulnerable then fixed mode. Thus fixture effects remain confounded with
time/order, provider state and caching despite balanced overall profile positions.

The committed runtime, source fingerprints, exact initial prompts/hashes, per-profile
allowances and every slot’s execution positions are retained in
[comparison.json](comparison.json). No fixture IDs or private verifier answers
are added to the model-facing prompts or tool schema.

## Observations from this pilot

All 18 baselines completed correctly with 18 probes. Among the 54 model runs,
25 completed correctly, 15 stopped on allowances, eight on scope and six during
inference. Five inference failures were GPT-OSS HTTP 500 responses; one was an
Ultra timeout. These pooled counts describe execution outcomes across different
conditions, not a model-capability ranking.

Super's sequential completions were 2/2 on the original, 1/2 on renamed IDs and
0/2 on opaque links. GPT-OSS completed only the fixed renamed-ID sequential run.
Ultra completed both modes in every fixture/profile cell except opaque/current,
where the vulnerable run timed out at about 120 seconds. Each cell has only two
runs, one per mode. Fixture order, provider state and run variance prevent a causal
claim that a fixture change explains those differences.

Two opaque-link runs show a concrete shortcut/scope interaction. In
[55056ff40f99](runs/55056ff40f99/state.json) (sequential/vulnerable), GPT-OSS
proposed Alice's `/api/projects/prj_a5/records` after the two account listings,
with 21 model calls and about 118 seconds remaining. That URL is permitted by
the original fixture but absent from the opaque fixture's allowlist. No record
links or record pairs had been captured. In
[d2c7c7e666ec](runs/d2c7c7e666ec/state.json) (current/fixed), it proposed the
same out-of-scope URL before collecting record evidence. Other current runs
reached call limits instead. Initial guidance is identical for current and
sequential, and models are not told the call limit: differing early choices
before either cap binds cannot be attributed to that limit alone.

In the renamed-ID sequential run
[e83fb226f324](runs/e83fb226f324/state.json), GPT-OSS proposed
`/api/records/export_y5` rather than the captured `/api/exports/export_y5` link.
All six resource links had been exposed, but only four record/account pairs were
attempted before the scope stop. This is a path-choice observation under the
existing allowlist, not an unobserved resource, exhausted allowance or server error.

The layout variant changes collection-URL shape, not graph depth or topology.
Scope rejections are part of the harness's current policy and can suppress
recovery from a guessed path. These observations motivate a separate policy
comparison; they do not justify silently changing scope handling within this pilot.

## Results by fixture and profile

### discovery

| Profile | Backend | Correct runs | Proved flaws | Missed flaws | False positives | Calls |
|---|---|---|---|---|---|---|
| current | baseline | 2/2 | 2/2 | 0 | 0 | 0 |
| current | gpt-oss:120b | 0/2 | 1/2 | 1 | 0 | 32 |
| current | nemotron-3-super | 0/2 | 1/2 | 1 | 0 | 32 |
| current | nemotron-3-ultra | 2/2 | 2/2 | 0 | 0 | 18 |
| sequential | baseline | 2/2 | 2/2 | 0 | 0 | 0 |
| sequential | gpt-oss:120b | 0/2 | 2/2 | 0 | 0 | 40 |
| sequential | nemotron-3-super | 2/2 | 2/2 | 0 | 0 | 36 |
| sequential | nemotron-3-ultra | 2/2 | 2/2 | 0 | 0 | 18 |
| batching | baseline | 2/2 | 2/2 | 0 | 0 | 0 |
| batching | gpt-oss:120b | 0/2 | 0/2 | 2 | 0 | 12 |
| batching | nemotron-3-super | 2/2 | 2/2 | 0 | 0 | 15 |
| batching | nemotron-3-ultra | 2/2 | 2/2 | 0 | 0 | 14 |

### discovery_ids

| Profile | Backend | Correct runs | Proved flaws | Missed flaws | False positives | Calls |
|---|---|---|---|---|---|---|
| current | baseline | 2/2 | 2/2 | 0 | 0 | 0 |
| current | gpt-oss:120b | 0/2 | 1/2 | 1 | 0 | 32 |
| current | nemotron-3-super | 0/2 | 1/2 | 1 | 0 | 32 |
| current | nemotron-3-ultra | 2/2 | 2/2 | 0 | 0 | 15 |
| sequential | baseline | 2/2 | 2/2 | 0 | 0 | 0 |
| sequential | gpt-oss:120b | 1/2 | 0/2 | 2 | 0 | 30 |
| sequential | nemotron-3-super | 1/2 | 2/2 | 0 | 0 | 41 |
| sequential | nemotron-3-ultra | 2/2 | 2/2 | 0 | 0 | 16 |
| batching | baseline | 2/2 | 2/2 | 0 | 0 | 0 |
| batching | gpt-oss:120b | 0/2 | 0/2 | 2 | 0 | 23 |
| batching | nemotron-3-super | 1/2 | 2/2 | 0 | 0 | 23 |
| batching | nemotron-3-ultra | 2/2 | 2/2 | 0 | 0 | 15 |

### discovery_links

| Profile | Backend | Correct runs | Proved flaws | Missed flaws | False positives | Calls |
|---|---|---|---|---|---|---|
| current | baseline | 2/2 | 2/2 | 0 | 0 | 0 |
| current | gpt-oss:120b | 0/2 | 1/2 | 1 | 0 | 19 |
| current | nemotron-3-super | 0/2 | 1/2 | 1 | 0 | 32 |
| current | nemotron-3-ultra | 1/2 | 1/2 | 1 | 0 | 19 |
| sequential | baseline | 2/2 | 2/2 | 0 | 0 | 0 |
| sequential | gpt-oss:120b | 0/2 | 0/2 | 2 | 0 | 24 |
| sequential | nemotron-3-super | 0/2 | 1/2 | 1 | 0 | 37 |
| sequential | nemotron-3-ultra | 2/2 | 2/2 | 0 | 0 | 17 |
| batching | baseline | 2/2 | 2/2 | 0 | 0 | 0 |
| batching | gpt-oss:120b | 0/2 | 0/2 | 2 | 0 | 14 |
| batching | nemotron-3-super | 1/2 | 1/2 | 1 | 0 | 21 |
| batching | nemotron-3-ultra | 2/2 | 2/2 | 0 | 0 | 14 |

A correct run requires completed record/account coverage and every expected
verifier verdict, including the export’s expected inconclusive outcome. There
are two seeded-flaw opportunities in each fixture/profile/backend cell, both
from its single vulnerable run. Fixed runs contain no expected flaws. Findings
require owner and cross-account evidence, not assistant prose. The six fixture
cases and repeated document/attachment are related, not independent vulnerability
classes. Mean latency of stopped runs is not successful-investigation speed.

## Discovery, evidence and stops

| Fixture | Profile | Model | Links exposed | Record pairs attempted | Successful owner controls | Duplicate probes | Stops |
|---|---|---|---|---|---|---|---|
| discovery | current | gpt-oss:120b | 12/12 | 19/24 | 8/10 | 1 | budget: 2 |
| discovery | current | nemotron-3-super | 12/12 | 20/24 | 9/10 | 0 | budget: 2 |
| discovery | current | nemotron-3-ultra | 12/12 | 24/24 | 10/10 | 0 | completed: 2 |
| discovery | sequential | gpt-oss:120b | 12/12 | 22/24 | 10/10 | 1 | model_choice: 2 |
| discovery | sequential | nemotron-3-super | 12/12 | 24/24 | 10/10 | 0 | completed: 2 |
| discovery | sequential | nemotron-3-ultra | 12/12 | 24/24 | 10/10 | 0 | completed: 2 |
| discovery | batching | gpt-oss:120b | 5/12 | 0/24 | 0/10 | 0 | provider_failure: 2 |
| discovery | batching | nemotron-3-super | 12/12 | 24/24 | 10/10 | 0 | completed: 2 |
| discovery | batching | nemotron-3-ultra | 12/12 | 24/24 | 10/10 | 0 | completed: 2 |
| discovery_ids | current | gpt-oss:120b | 12/12 | 20/24 | 8/10 | 0 | budget: 2 |
| discovery_ids | current | nemotron-3-super | 12/12 | 20/24 | 8/10 | 0 | budget: 2 |
| discovery_ids | current | nemotron-3-ultra | 12/12 | 24/24 | 10/10 | 0 | completed: 2 |
| discovery_ids | sequential | gpt-oss:120b | 12/12 | 16/24 | 9/10 | 0 | completed: 1, model_choice: 1 |
| discovery_ids | sequential | nemotron-3-super | 12/12 | 23/24 | 10/10 | 1 | completed: 1, model_choice: 1 |
| discovery_ids | sequential | nemotron-3-ultra | 12/12 | 24/24 | 10/10 | 0 | completed: 2 |
| discovery_ids | batching | gpt-oss:120b | 11/12 | 9/24 | 5/10 | 0 | budget: 1, provider_failure: 1 |
| discovery_ids | batching | nemotron-3-super | 12/12 | 23/24 | 10/10 | 0 | budget: 1, completed: 1 |
| discovery_ids | batching | nemotron-3-ultra | 12/12 | 24/24 | 10/10 | 0 | completed: 2 |
| discovery_links | current | gpt-oss:120b | 6/12 | 10/24 | 4/10 | 0 | budget: 1, model_choice: 1 |
| discovery_links | current | nemotron-3-super | 12/12 | 19/24 | 9/10 | 1 | budget: 2 |
| discovery_links | current | nemotron-3-ultra | 12/12 | 23/24 | 9/10 | 0 | completed: 1, provider_failure: 1 |
| discovery_links | sequential | gpt-oss:120b | 6/12 | 11/24 | 5/10 | 2 | model_choice: 2 |
| discovery_links | sequential | nemotron-3-super | 12/12 | 21/24 | 9/10 | 5 | budget: 1, model_choice: 1 |
| discovery_links | sequential | nemotron-3-ultra | 12/12 | 24/24 | 10/10 | 0 | completed: 2 |
| discovery_links | batching | gpt-oss:120b | 10/12 | 0/24 | 0/10 | 0 | provider_failure: 2 |
| discovery_links | batching | nemotron-3-super | 12/12 | 22/24 | 9/10 | 0 | budget: 1, completed: 1 |
| discovery_links | batching | nemotron-3-ultra | 12/12 | 24/24 | 10/10 | 0 | completed: 2 |

Each two-run cell can expose twelve record links, attempt 24 record/account
pairs and obtain ten successful owner controls; the export cannot provide a
successful control. Link exposure is measured in captured responses, not as
proof a model recognised or used a link. Attempted coverage is distinct from
a successful control or a conclusive verdict. Duplicate probes repeat an
account/path pair. Exact scope rejection stops a run before executing a rejected
guess; this policy is unchanged and is part of what the pilot measures.

## Operational accounting

| Run | Fixture | Profile | Model | Provider category | HTTP | Call |
|---|---|---|---|---|---|---|
| [9f615df2e000](runs/9f615df2e000/report.md) | discovery | batching | gpt-oss:120b | http_server | 500 | 5 |
| [7c574d7e93c9](runs/7c574d7e93c9/report.md) | discovery | batching | gpt-oss:120b | http_server | 500 | 7 |
| [2620133e24fc](runs/2620133e24fc/report.md) | discovery_ids | batching | gpt-oss:120b | http_server | 500 | 7 |
| [a4334ed726f1](runs/a4334ed726f1/report.md) | discovery_links | batching | gpt-oss:120b | http_server | 500 | 7 |
| [b7055026adfd](runs/b7055026adfd/report.md) | discovery_links | current | nemotron-3-ultra | timeout | — | 9 |
| [6e444424c773](runs/6e444424c773/report.md) | discovery_links | batching | gpt-oss:120b | http_server | 500 | 7 |

Safe diagnostics locate an observed failure boundary, not its underlying cause.
Failures remain in denominators and retain reservations; incomplete returned
usage is a lower bound. Raw provider errors, headers and credentials are not
diagnostic artifacts. Token counts are not monetary costs.

| Fixture | Profile | Model | Returned input tokens | Returned output tokens | Usage complete |
|---|---|---|---|---|---|
| discovery | current | gpt-oss:120b | 39626 | 1781 | True |
| discovery | current | nemotron-3-super | 58124 | 3230 | True |
| discovery | current | nemotron-3-ultra | 30004 | 4252 | True |
| discovery | sequential | gpt-oss:120b | 63590 | 6938 | True |
| discovery | sequential | nemotron-3-super | 64841 | 2658 | True |
| discovery | sequential | nemotron-3-ultra | 29973 | 3972 | True |
| discovery | batching | gpt-oss:120b | 6493 | 572 | False |
| discovery | batching | nemotron-3-super | 31261 | 6998 | True |
| discovery | batching | nemotron-3-ultra | 22868 | 4068 | True |
| discovery_ids | batching | gpt-oss:120b | 27831 | 2635 | False |
| discovery_ids | batching | nemotron-3-super | 56303 | 13699 | True |
| discovery_ids | batching | nemotron-3-ultra | 25476 | 4267 | True |
| discovery_ids | current | gpt-oss:120b | 40490 | 1920 | True |
| discovery_ids | current | nemotron-3-super | 53355 | 2653 | True |
| discovery_ids | current | nemotron-3-ultra | 23021 | 2399 | True |
| discovery_ids | sequential | gpt-oss:120b | 38533 | 3173 | True |
| discovery_ids | sequential | nemotron-3-super | 87059 | 6728 | True |
| discovery_ids | sequential | nemotron-3-ultra | 27296 | 4171 | True |
| discovery_links | sequential | gpt-oss:120b | 34774 | 2417 | True |
| discovery_links | sequential | nemotron-3-super | 82317 | 8812 | True |
| discovery_links | sequential | nemotron-3-ultra | 29984 | 3894 | True |
| discovery_links | batching | gpt-oss:120b | 8510 | 692 | False |
| discovery_links | batching | nemotron-3-super | 37473 | 3788 | True |
| discovery_links | batching | nemotron-3-ultra | 21751 | 3680 | True |
| discovery_links | current | gpt-oss:120b | 21164 | 1025 | True |
| discovery_links | current | nemotron-3-super | 54832 | 3144 | True |
| discovery_links | current | nemotron-3-ultra | 29409 | 3542 | False |

## Individual runs

| Run | Block | Fixture | Mode | Profile / position | Backend / position | Correct | Requests / calls |
|---|---|---|---|---|---|---|---|
| [e24ff4ddf66e](runs/e24ff4ddf66e/report.md) | 1 | discovery | vulnerable | current / 1 | baseline / 0 | True | 18 / 0 |
| [66f3effee198](runs/66f3effee198/report.md) | 1 | discovery | vulnerable | current / 1 | gpt-oss:120b / 1 | False | 16 / 16 |
| [1277012f0a92](runs/1277012f0a92/report.md) | 1 | discovery | vulnerable | current / 1 | nemotron-3-super / 2 | False | 16 / 16 |
| [2ec5d67ece3e](runs/2ec5d67ece3e/report.md) | 1 | discovery | vulnerable | current / 1 | nemotron-3-ultra / 3 | True | 18 / 8 |
| [38fa4edd158b](runs/38fa4edd158b/report.md) | 1 | discovery | vulnerable | sequential / 2 | baseline / 0 | True | 18 / 0 |
| [89908c0ea26f](runs/89908c0ea26f/report.md) | 1 | discovery | vulnerable | sequential / 2 | nemotron-3-super / 1 | True | 18 / 18 |
| [4aa1970ee7f9](runs/4aa1970ee7f9/report.md) | 1 | discovery | vulnerable | sequential / 2 | nemotron-3-ultra / 2 | True | 18 / 10 |
| [f8fa53cb53bb](runs/f8fa53cb53bb/report.md) | 1 | discovery | vulnerable | sequential / 2 | gpt-oss:120b / 3 | False | 18 / 21 |
| [d8e43df7b225](runs/d8e43df7b225/report.md) | 1 | discovery | vulnerable | batching / 3 | baseline / 0 | True | 18 / 0 |
| [ef6149484c3f](runs/ef6149484c3f/report.md) | 1 | discovery | vulnerable | batching / 3 | nemotron-3-ultra / 1 | True | 18 / 6 |
| [9f615df2e000](runs/9f615df2e000/report.md) | 1 | discovery | vulnerable | batching / 3 | gpt-oss:120b / 2 | False | 4 / 5 |
| [a4799a8643a1](runs/a4799a8643a1/report.md) | 1 | discovery | vulnerable | batching / 3 | nemotron-3-super / 3 | True | 22 / 10 |
| [a17d8a2c5c51](runs/a17d8a2c5c51/report.md) | 2 | discovery | fixed | sequential / 1 | baseline / 0 | True | 18 / 0 |
| [45ed9c74af8e](runs/45ed9c74af8e/report.md) | 2 | discovery | fixed | sequential / 1 | nemotron-3-super / 1 | True | 18 / 18 |
| [3323cb25f337](runs/3323cb25f337/report.md) | 2 | discovery | fixed | sequential / 1 | nemotron-3-ultra / 2 | True | 18 / 8 |
| [81aacb329f3b](runs/81aacb329f3b/report.md) | 2 | discovery | fixed | sequential / 1 | gpt-oss:120b / 3 | False | 17 / 19 |
| [a610d7f9e093](runs/a610d7f9e093/report.md) | 2 | discovery | fixed | batching / 2 | baseline / 0 | True | 18 / 0 |
| [23520b038039](runs/23520b038039/report.md) | 2 | discovery | fixed | batching / 2 | nemotron-3-ultra / 1 | True | 18 / 8 |
| [7c574d7e93c9](runs/7c574d7e93c9/report.md) | 2 | discovery | fixed | batching / 2 | gpt-oss:120b / 2 | False | 6 / 7 |
| [7176a6056ec5](runs/7176a6056ec5/report.md) | 2 | discovery | fixed | batching / 2 | nemotron-3-super / 3 | True | 18 / 5 |
| [792976165b61](runs/792976165b61/report.md) | 2 | discovery | fixed | current / 3 | baseline / 0 | True | 18 / 0 |
| [51f2a2524ef9](runs/51f2a2524ef9/report.md) | 2 | discovery | fixed | current / 3 | gpt-oss:120b / 1 | False | 16 / 16 |
| [6ae5dc6935d9](runs/6ae5dc6935d9/report.md) | 2 | discovery | fixed | current / 3 | nemotron-3-super / 2 | False | 16 / 16 |
| [f67cf6a5c6c4](runs/f67cf6a5c6c4/report.md) | 2 | discovery | fixed | current / 3 | nemotron-3-ultra / 3 | True | 18 / 10 |
| [4edb1243893b](runs/4edb1243893b/report.md) | 3 | discovery_ids | vulnerable | batching / 1 | baseline / 0 | True | 18 / 0 |
| [471d744c0f0d](runs/471d744c0f0d/report.md) | 3 | discovery_ids | vulnerable | batching / 1 | nemotron-3-ultra / 1 | True | 18 / 7 |
| [2620133e24fc](runs/2620133e24fc/report.md) | 3 | discovery_ids | vulnerable | batching / 1 | gpt-oss:120b / 2 | False | 6 / 7 |
| [3fb95f8085f0](runs/3fb95f8085f0/report.md) | 3 | discovery_ids | vulnerable | batching / 1 | nemotron-3-super / 3 | False | 19 / 16 |
| [1e702ef0d6e8](runs/1e702ef0d6e8/report.md) | 3 | discovery_ids | vulnerable | current / 2 | baseline / 0 | True | 18 / 0 |
| [ff34b4ad1ed0](runs/ff34b4ad1ed0/report.md) | 3 | discovery_ids | vulnerable | current / 2 | gpt-oss:120b / 1 | False | 16 / 16 |
| [f7fdeb345e4e](runs/f7fdeb345e4e/report.md) | 3 | discovery_ids | vulnerable | current / 2 | nemotron-3-super / 2 | False | 16 / 16 |
| [86b99cf2d89c](runs/86b99cf2d89c/report.md) | 3 | discovery_ids | vulnerable | current / 2 | nemotron-3-ultra / 3 | True | 18 / 9 |
| [4ac8554ae270](runs/4ac8554ae270/report.md) | 3 | discovery_ids | vulnerable | sequential / 3 | baseline / 0 | True | 18 / 0 |
| [6cdd35b6dd70](runs/6cdd35b6dd70/report.md) | 3 | discovery_ids | vulnerable | sequential / 3 | nemotron-3-super / 1 | True | 19 / 19 |
| [170a81671161](runs/170a81671161/report.md) | 3 | discovery_ids | vulnerable | sequential / 3 | nemotron-3-ultra / 2 | True | 18 / 9 |
| [e83fb226f324](runs/e83fb226f324/report.md) | 3 | discovery_ids | vulnerable | sequential / 3 | gpt-oss:120b / 3 | False | 10 / 11 |
| [60a01b3c288d](runs/60a01b3c288d/report.md) | 4 | discovery_ids | fixed | current / 1 | baseline / 0 | True | 18 / 0 |
| [eace56e3fc91](runs/eace56e3fc91/report.md) | 4 | discovery_ids | fixed | current / 1 | gpt-oss:120b / 1 | False | 16 / 16 |
| [9063c8aa8ee3](runs/9063c8aa8ee3/report.md) | 4 | discovery_ids | fixed | current / 1 | nemotron-3-super / 2 | False | 16 / 16 |
| [7cddfdaed252](runs/7cddfdaed252/report.md) | 4 | discovery_ids | fixed | current / 1 | nemotron-3-ultra / 3 | True | 18 / 6 |
| [b16d9f4c2913](runs/b16d9f4c2913/report.md) | 4 | discovery_ids | fixed | sequential / 2 | baseline / 0 | True | 18 / 0 |
| [72d12403091f](runs/72d12403091f/report.md) | 4 | discovery_ids | fixed | sequential / 2 | nemotron-3-super / 1 | False | 19 / 22 |
| [f183ffdfab13](runs/f183ffdfab13/report.md) | 4 | discovery_ids | fixed | sequential / 2 | nemotron-3-ultra / 2 | True | 18 / 7 |
| [842ae87b7b3a](runs/842ae87b7b3a/report.md) | 4 | discovery_ids | fixed | sequential / 2 | gpt-oss:120b / 3 | True | 18 / 19 |
| [074b8d41b519](runs/074b8d41b519/report.md) | 4 | discovery_ids | fixed | batching / 3 | baseline / 0 | True | 18 / 0 |
| [7ad1c0eb494a](runs/7ad1c0eb494a/report.md) | 4 | discovery_ids | fixed | batching / 3 | nemotron-3-ultra / 1 | True | 18 / 8 |
| [8c90b2d47c5c](runs/8c90b2d47c5c/report.md) | 4 | discovery_ids | fixed | batching / 3 | gpt-oss:120b / 2 | False | 15 / 16 |
| [90ec5741796e](runs/90ec5741796e/report.md) | 4 | discovery_ids | fixed | batching / 3 | nemotron-3-super / 3 | True | 18 / 7 |
| [a8af6ac8ceec](runs/a8af6ac8ceec/report.md) | 5 | discovery_links | vulnerable | sequential / 1 | baseline / 0 | True | 18 / 0 |
| [438809d05e35](runs/438809d05e35/report.md) | 5 | discovery_links | vulnerable | sequential / 1 | nemotron-3-super / 1 | False | 21 / 24 |
| [99b05b4b26c5](runs/99b05b4b26c5/report.md) | 5 | discovery_links | vulnerable | sequential / 1 | nemotron-3-ultra / 2 | True | 18 / 6 |
| [55056ff40f99](runs/55056ff40f99/report.md) | 5 | discovery_links | vulnerable | sequential / 1 | gpt-oss:120b / 3 | False | 2 / 3 |
| [0f3095db8a35](runs/0f3095db8a35/report.md) | 5 | discovery_links | vulnerable | batching / 2 | baseline / 0 | True | 18 / 0 |
| [0ae44612b9e4](runs/0ae44612b9e4/report.md) | 5 | discovery_links | vulnerable | batching / 2 | nemotron-3-ultra / 1 | True | 18 / 7 |
| [a4334ed726f1](runs/a4334ed726f1/report.md) | 5 | discovery_links | vulnerable | batching / 2 | gpt-oss:120b / 2 | False | 6 / 7 |
| [6a82b4c4b535](runs/6a82b4c4b535/report.md) | 5 | discovery_links | vulnerable | batching / 2 | nemotron-3-super / 3 | False | 16 / 16 |
| [1a11366c0d10](runs/1a11366c0d10/report.md) | 5 | discovery_links | vulnerable | current / 3 | baseline / 0 | True | 18 / 0 |
| [bd65d6b0fe70](runs/bd65d6b0fe70/report.md) | 5 | discovery_links | vulnerable | current / 3 | gpt-oss:120b / 1 | False | 16 / 16 |
| [4ed48c263287](runs/4ed48c263287/report.md) | 5 | discovery_links | vulnerable | current / 3 | nemotron-3-super / 2 | False | 16 / 16 |
| [b7055026adfd](runs/b7055026adfd/report.md) | 5 | discovery_links | vulnerable | current / 3 | nemotron-3-ultra / 3 | False | 17 / 9 |
| [bdc4ff66d3c3](runs/bdc4ff66d3c3/report.md) | 6 | discovery_links | fixed | batching / 1 | baseline / 0 | True | 18 / 0 |
| [3a70ec21c392](runs/3a70ec21c392/report.md) | 6 | discovery_links | fixed | batching / 1 | nemotron-3-ultra / 1 | True | 18 / 7 |
| [6e444424c773](runs/6e444424c773/report.md) | 6 | discovery_links | fixed | batching / 1 | gpt-oss:120b / 2 | False | 6 / 7 |
| [66551d3ca8cd](runs/66551d3ca8cd/report.md) | 6 | discovery_links | fixed | batching / 1 | nemotron-3-super / 3 | True | 18 / 5 |
| [ab0735e9ae40](runs/ab0735e9ae40/report.md) | 6 | discovery_links | fixed | current / 2 | baseline / 0 | True | 18 / 0 |
| [d2c7c7e666ec](runs/d2c7c7e666ec/report.md) | 6 | discovery_links | fixed | current / 2 | gpt-oss:120b / 1 | False | 2 / 3 |
| [45e6ff00caa2](runs/45e6ff00caa2/report.md) | 6 | discovery_links | fixed | current / 2 | nemotron-3-super / 2 | False | 16 / 16 |
| [6bb13779f570](runs/6bb13779f570/report.md) | 6 | discovery_links | fixed | current / 2 | nemotron-3-ultra / 3 | True | 18 / 10 |
| [95284f80fd54](runs/95284f80fd54/report.md) | 6 | discovery_links | fixed | sequential / 3 | baseline / 0 | True | 18 / 0 |
| [229fb2c3f5aa](runs/229fb2c3f5aa/report.md) | 6 | discovery_links | fixed | sequential / 3 | nemotron-3-super / 1 | False | 21 / 13 |
| [e06ed894be49](runs/e06ed894be49/report.md) | 6 | discovery_links | fixed | sequential / 3 | nemotron-3-ultra / 2 | True | 22 / 11 |
| [ed8f21f7adfd](runs/ed8f21f7adfd/report.md) | 6 | discovery_links | fixed | sequential / 3 | gpt-oss:120b / 3 | False | 19 / 21 |

## Limits and reproduction

One run per model/profile/fixture/mode cannot estimate within-cell reliability.
These are a few deterministic ID/path variants, not random targets or new
vulnerability classes. The provider model aliases/builds are not pinned, and
temperature zero is not determinism. The original fixture is a contemporaneous
control, not a reconstruction of previous conversations or timings. No result
establishes a causal mode effect, general model ranking or external-target readiness.

```sh
python3 -m redwake.discovery_suite --directory .redwake/NEW-varied-pilot --repeat 1
python3 scripts/verify_experiments.py docs/experiments/2026-10-28-varied-discovery
```

The first command makes a new live experiment. The second checks the retained
bundle offline. All original conversations, states, captured responses and reports
are under `runs/`; [results.json](results.json) contains offline scores and
[manifest.json](manifest.json) contains provenance and the complete hash inventory.
Every planned slot, including failed runs and baselines, must be present.
See the [suite method](../../varied-discovery.md). Historical bundles remain unchanged.
