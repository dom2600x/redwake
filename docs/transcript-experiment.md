# Reducing a saved provider failure

```sh
python3 -m redwake.transcript_experiment --directory .redwake/transcript-study --repeat 3
```

This is a separate inference-only experiment: 48 GPT-OSS calls and 48 scripted
controls, with no lab probes or vulnerability verdicts. All cells use temperature
zero, 1,024 output tokens, one call per trial, a 60-second timeout and no retries.
Variant order rotates by repetition and route order alternates within blocks.

The fixed source is the exact conversation before historical GPT-OSS HTTP 500
run `65224d9d368f`. It contains two initial messages and four assistant/tool pairs.

| Variant | Declared change |
|---|---|
| original | Exact saved context |
| no_thinking | Remove assistant `thinking` fields |
| no_function_index | Remove `function.index` from tool-call proposals |
| no_call_ids | Remove `id` from assistant tool calls |
| correlated_results | Add each corresponding `tool_call_id` to tool results |
| tail_pair | Keep initial messages plus the last assistant/tool pair |
| combined_removals | Combine removal of thinking, function index and call IDs |
| fresh_single | Use the prior study's fresh single-probe control prompt |

Individual removals preserve every other message field. Correlation preserves
tool-result content and `tool_name`. Combined removal is an interaction treatment,
not evidence of which individual field matters. Shortening the transcript also
removes observations and context; it is not a semantically equivalent request.
Removing thinking changes model-provided text as well as request structure.

Each input is sent through both the production adapter and a direct native
request constructor. Both routes use the same endpoint, tool schema, parameters,
TLS/proxy configuration and HTTP function. Unit tests compare their full request
arguments. This checks construction consistency, not independence from shared
transport or service bugs. The production adapter itself is not changed.

Scripted controls check proposal shape/scope only, using documented entry points
and links exposed in the retained input. Replay responses are never treated as
executed observations, nor graded as complete investigations. Fresh-single
responses must match the requested actor/path exactly.

Every call allowance is persisted before inference. Failed calls retain their
reservation and unknown usage, without raw provider errors or credentials.
Interrupted trials remain unfinished and directories cannot be reused. Saved
inputs, source hashes, complete planned slots, outcomes and artifact hashes can
be verified offline. A small sample with provider aliases, caching and varying
model output cannot establish a server root cause or a universally valid fix.

Retained bundles use a schema-2 `transcript_reduction` manifest covering
`transcript.json` and a reviewed `report.md`. Verify with the ordinary experiment
verifier or `python3 -m redwake.transcript_experiment --directory BUNDLE --verify`.
