# GPT-OSS transcript reduction and native request cross-check

2026-10-28 (Australia/Perth). Forty-eight live GPT-OSS calls and 48 scripted
controls. No lab probes were executed and no security verdicts were produced.

The original saved context no longer reproduces HTTP 500 in this sample. It
returns in-scope tool proposals in all six invocations, through both request
construction routes. This removes the necessary failing control for attributing
a fix to any field removal or correlation change. No production workaround is
justified by these results; the earlier failures remain unchanged.

## Design

The source is the exact context before [historical failure 65224d9d368f](../2026-10-27-discovery-batching/runs/65224d9d368f/state.json).
It contains the initial system/user guidance and four assistant/tool pairs.
The [prior compatibility study](../2026-10-27-provider-compatibility/report.md)
reproduced HTTP 500 for this context at both 1,024 and 2,048 output limits.

| Variant | Change |
|---|---|
| original | Exact source messages |
| no_thinking | Remove assistant thinking fields |
| no_function_index | Remove function.index fields |
| no_call_ids | Remove assistant tool-call IDs |
| correlated_results | Add matching tool_call_id to each result, preserve tool_name and content |
| tail_pair | Keep initial guidance plus only the final assistant/tool pair |
| combined_removals | Remove thinking, function index and call IDs together |
| fresh_single | Fresh prompt requesting Alice’s /api/projects call |

Each variant ran three times through the unchanged production adapter and three
times through direct native request construction. Capacity stayed at 1,024,
temperature at zero and per-call timeout at 60 seconds. Each trial gets one call,
with no retries or probe execution. All declared slots and scripted controls are
retained. Calls reserve allowances before inference; failures would retain unknown
usage. The runtime was committed and pushed before inference.

Variant order rotates by repetition. Route order alternates across adjacent
variant blocks, but its first position for each particular variant stays constant
across repetitions because the rotation and parity calculation cancel. Thus this
is not a fully counterbalanced route comparison; the recorded plan preserves that
limitation rather than changing order after seeing results.

Both routes use https://ollama.com/api/chat, the same tool schema, secured HTTP
function, TLS/proxy configuration and model options. Unit tests compare complete
request arguments. Native construction bypasses adapter construction/validation,
but is not an independent HTTP stack or provider backend. It cannot rule out a
shared transport or service issue.

The original messages and tool schema match the previous study exactly. The
production providers.py bytes also match that study. Source revisions, runtime
fingerprints, source-file hashes, full variant inputs and prompt hashes are in
[transcript.json](transcript.json). The experiment factors do not explain the
between-day change in the unchanged control.

## Results

| Variant | Adapter outcomes / 3 | Native outcomes / 3 |
|---|---|---|
| original | in_scope: 3 | in_scope: 3 |
| no_thinking | in_scope: 3 | in_scope: 3 |
| no_function_index | in_scope: 3 | in_scope: 3 |
| no_call_ids | in_scope: 3 | in_scope: 3 |
| correlated_results | in_scope: 3 | in_scope: 3 |
| tail_pair | invalid_tools: 3 | invalid_tools: 3 |
| combined_removals | in_scope: 3 | in_scope: 3 |
| fresh_single | matched: 3 | matched: 3 |

Every live call returned a normal assistant response. There were no provider
HTTP failures or timeouts. Every response proposed exactly one tool call. A
returned in-scope proposal is not a claim that it is the best next step, nor
evidence of actual execution, complete discovery or authorisation correctness.

The six shortened-context responses all proposed Alice’s
`/api/projects/prj_a1`, which is outside the lab allowlist. This treatment removed
the prior Alice project observation while preserving Bob’s final project detail.
It therefore changes available evidence and semantics as well as transcript size.
Its invalid proposals do not reproduce a provider error and do not establish a
general discovery limitation.

The fresh-single control matched Alice’s `/api/projects` in all six responses.
All 48 scripted controls matched their expected proposal shape/scope. These
controls exercise scoring without inference; they do not validate remote behaviour.

## Interpretation and limits

The unchanged original succeeds through both routes. Removing thinking, indices
or IDs, adding result correlation, or combining removals cannot be credited with
repairing a failure that is absent from the original control. In this sample,
adding correlation IDs does not show a benefit, and missing result IDs do not
establish an unconditional invalid-request rule.

The two constructors produce the same tested request shape. Their matching
successful outcomes do not locate a provider root cause. Model aliases, remote
deployment/version, cache state and provider state were not pinned across days.
Temperature zero does not ensure deterministic output. The experiment does not
show that the earlier HTTP 500 was transient, permanently fixed, or caused by
any particular transcript field. It only records non-reproduction in this sample.

Only one saved context and one model alias were tested, with three repetitions
per cell. The combined-removal variant is an interaction treatment, and removing
thinking changes model text. Tail-pair reduction removes observations; it is not
a semantically equivalent request. No returned batch had multiple tool calls,
so success here also does not establish reliable native batching capability.

The production adapter remains unchanged. Further minimisation needs an original
control that reproduces the failure in the same study, ideally with a stable
provider version or a safe provider-supplied trace identifier. If that is absent,
additional successful reductions cannot identify a fix. The next investigation
comparison can instead rotate profile order and vary navigation layouts/fixture
IDs while retaining these operational limits and historical failures.

## Accounting and reproduction

48 model calls reserved 49,152 output tokens.
Returned input/output totals were 35,262/2,906; usage was complete for every trial.
All returned completion reasons were `stop`, and no returned output count reached
the requested cap. Token counts are not dollar costs. Scripted controls reserve
no model usage. Original messages, returned proposals, accounting and the plan
are retained; raw provider errors and credentials are not artifacts.

```sh
python3 -m redwake.transcript_experiment --directory .redwake/NEW-transcript-study --repeat 3
python3 -m redwake.transcript_experiment --directory docs/experiments/2026-10-28-transcript-reduction --verify
python3 scripts/verify_experiments.py
```

A live rerun is a new sample. Offline checks validate the complete plan, exact
declared transformations, source hashes, response classifications, reservations
and artifact inventory without inference. See the [experiment guide](../../transcript-experiment.md).
