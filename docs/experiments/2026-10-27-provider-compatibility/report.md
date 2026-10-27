# Provider batching compatibility and response capacity

2026-10-27 (Australia/Perth). Thirty-six live Ollama Cloud calls and 36 scripted
controls. No lab requests were executed and no vulnerability verdicts were produced.

GPT-OSS reproduced HTTP 500 for its saved failure context at both response
capacities. Fresh single-call prompts worked. Fresh two-call prompts returned
only Alice’s call in all six trials, without an HTTP error. Increasing the
response limit from 1,024 to 2,048 did not resolve either observed outcome.
Super’s saved failure did not reproduce in these trials.

## Method

Each model received three fixed inputs: a fresh request for one account’s
`/api/projects` probe, a fresh request for both accounts in one response, and
the exact recorded message sequence immediately before one historical HTTP 500.
Each model/input pair ran three repetitions at `num_predict=1024` and `2048`.
Capacity order alternated within pairs; calls ran serially at temperature zero,
with one call per trial, a 60-second timeout and no retries or tool execution.

The native tool schema and provider adapter match the discovery experiments.
Only the response capacity changes within a paired model/input block. Each input
has a scripted control under each capacity. These controls validate proposal
classification, not provider behaviour. All 36 scripted controls matched their
expected shape/scope. Repetition slots are planned independent invocations, not
retries of failed calls. Every cloud call retains its full reservation.

Sources: [GPT-OSS pre-failure state](../2026-10-27-discovery-batching/runs/65224d9d368f/state.json)
and [Super pre-failure state](../2026-10-27-discovery-batching/runs/3130bcd41596/state.json).
The complete inputs, their original file hashes, native tool hash, source revision
and runtime fingerprints are retained in [compatibility.json](compatibility.json).

## Results

| Model | Input | Output limit | Exact matches / 3 | In-scope replay responses / 3 | Other responses | Provider failures |
|---|---|---:|---:|---:|---|---:|
| gpt-oss:120b | single | 1024 | 3 | 0 | — | 0 |
| gpt-oss:120b | single | 2048 | 3 | 0 | — | 0 |
| gpt-oss:120b | batch_two | 1024 | 0 | 0 | mismatch: 3 | 0 |
| gpt-oss:120b | batch_two | 2048 | 0 | 0 | mismatch: 3 | 0 |
| gpt-oss:120b | replay | 1024 | 0 | 0 | — | 3 |
| gpt-oss:120b | replay | 2048 | 0 | 0 | — | 3 |
| nemotron-3-super | single | 1024 | 3 | 0 | — | 0 |
| nemotron-3-super | single | 2048 | 3 | 0 | — | 0 |
| nemotron-3-super | batch_two | 1024 | 2 | 0 | mismatch: 1 | 0 |
| nemotron-3-super | batch_two | 2048 | 3 | 0 | — | 0 |
| nemotron-3-super | replay | 1024 | 0 | 3 | — | 0 |
| nemotron-3-super | replay | 2048 | 0 | 3 | — | 0 |

Minimal cases require exactly the requested actor/path pairs, including
multiplicity. A two-call response containing only Alice’s probe is a mismatch.
All six GPT-OSS two-call trials and Super’s third 1,024-token trial had that
outcome. All six GPT-OSS single-call trials matched; all six Super single-call
trials matched. Super matched two of three two-call trials at 1,024 and three
of three at 2,048. This one-trial difference does not establish a capacity effect.

Replays only check whether returned proposals have permitted tool names, actors
and paths. They do not establish that the chosen next probes are correct,
complete or useful. Super returned in-scope proposals in all six replay trials.

## Error boundary and capacity interpretation

All six GPT-OSS replays returned HTTP 500, with unknown actual token usage.
They stopped in less than one second each. A quick failure is an observation,
not proof of which provider subsystem rejected the request. The stored category
is `provider/http_server`, with numeric status 500 and model-call index 1;
raw provider errors, headers and credentials are not retained.

No returned response reported `length`. All returned token counts were below
their requested limit. That provides no evidence of visible response truncation
in successful responses. Failed inference offers no returned count or completion
reason; this experiment cannot rule out internal generation/decoding failures
or determine a server root cause. It establishes only that the larger limit
did not remove the reproducible GPT-OSS context failure in this sample.

The fresh two-call mismatch and the replay HTTP 500 are distinct observations.
The former has a returned single tool proposal; the latter has no returned
assistant message. Neither establishes whether model generation, provider tool
decoding or request handling caused the missing calls. The broader discovery
comparison’s failed runs remain unchanged and remain in its denominators.

## Accounting and limitations

36 model calls reserved 55,296 output tokens.
Returned input/output totals: 26,568/6,196.
Six failed calls leave actual usage incomplete; totals are lower bounds, not
monetary costs. Scripted controls reserve no model calls or output tokens.

Three repetitions per cell, two model aliases, one saved context per model
and one minimal pair are insufficient for a general compatibility or capability
ranking. Temperature zero is not determinism. The capacity order alternates,
but model/case order is fixed; provider state and caches remain possible confounds.
A clean prompt differs from a replay in many ways, so their contrast does not
identify a particular offending transcript field. Super’s non-reproduction does
not erase its historical failure or establish that it was transient.

Next: minimise the reproducing GPT-OSS context with separately declared variants
of tool-result correlation and transcript metadata, keeping prompts/capacity fixed
within each variant. Compare direct native API behaviour against that same input
before changing the production harness. Provider-specific workarounds require
their own evidence and should not silently rewrite historical conversations.

## Reproduce and verify

```sh
python3 -m redwake.compatibility --directory .redwake/NEW-compatibility --repeat 3
python3 -m redwake.compatibility --directory docs/experiments/2026-10-27-provider-compatibility --verify
python3 scripts/verify_experiments.py
```

A live rerun is a new experiment. Offline verification checks the complete paired
plan, original contexts, reservations, classifications and hashes without calls.
See the [experiment guide](../../provider-compatibility.md). The implementation
was committed and pushed before inference; the bundle preserves that source
revision separately from later documentation/test commits.
