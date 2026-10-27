# Controlled discovery comparisons

The scripted traversal takes 18 requests: six navigation requests and twelve
record probes. A model using one probe per call cannot reproduce that traversal
within the original 16-call allowance. This is not a minimum enforced by the
executor: a model can infer an accepted path and skip navigation steps. Separate
profiles test capacity and batching advice.

| Profile | Guidance | Requests | Model calls | Reserved output tokens | Active seconds |
|---|---|---:|---:|---:|---:|
| `current` (default) | Original discovery prompt | 32 | 16 | 16,384 | 120 |
| `sequential` | Original discovery prompt | 32 | 24 | 24,576 | 120 |
| `batching` | Original prompt plus batching advice | 32 | 16 | 16,384 | 120 |

The sequential allowance fits 18 individual calls plus six calls of headroom.
Output reservations rise too: each call reserves up to 1,024 tokens without
refund, so increasing calls alone would still stop at 16 full reservations.
Batching guidance groups independent probes of known paths in one response,
waiting for observations before choosing dependent paths. It gives no fixture
IDs or expected verdicts. It does not require models to batch, nor does the
sequential profile prohibit batching.

```sh
python3 -m redwake.comparison --profile current --repeat 3
python3 -m redwake.comparison --profile sequential --repeat 3
python3 -m redwake.comparison --profile batching --repeat 3
```

Each command creates a fresh live Ollama Cloud batch, with the baseline and all
three models in both vulnerable and fixed mode. Prompts and allowances are fixed
within a batch, inference is serial and model order rotates between blocks.
No run is retried, resumed, excluded or given extra allowances. Failed runs keep
their reservations, unknown usage and place in every denominator.

New batch plans record the profile, full initial prompt and hash, tool hash,
runtime fingerprints and controls. Saved conversations retain actual guidance
and observations. Metrics distinguish links exposed in captured responses,
record/account probes attempted, successful owner controls, duplicates and stop
categories. Exposing a link does not establish that a model recognised it;
attempting a control does not establish a successful response.

Diagnostics use fixed categories, model-call indices and numeric HTTP statuses.
They distinguish authentication/rate/service errors, network/timeout/response
failures and rejected model tool choices. Raw provider errors, exception text,
headers and credentials are not diagnostic artifacts. A timeout near 120 active
seconds may reflect the remaining harness allowance rather than a service outage.

Correct runs require completed coverage and all verifier verdicts matching the
fixture, including the export's expected inconclusive verdict. Findings require
owner and cross-account evidence. Assistant prose is not graded. Fixture truth
and missing-resource answers are never sent as recovery advice.

Repetitions use deterministic synthetic cases; the document and attachment are
related. The fixed time cap, strict scope enforcement, model alias changes,
caching, service behaviour and batch order remain confounds. Temperature zero
does not ensure determinism. Token counts are usage, not dollar costs. Dated
reports record observations and limitations without broader capability rankings.
