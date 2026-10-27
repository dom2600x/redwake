# Provider tool compatibility experiment

Run inference-only compatibility trials with the existing probe schema:

```sh
python3 -m redwake.compatibility --directory .redwake/provider-compatibility --repeat 3
```

This makes 36 serial Ollama calls, plus 36 scripted controls. GPT-OSS and Super
each receive three fixed cases: a fresh single-probe prompt, a fresh two-probe
prompt, and their exact saved context immediately before one historical HTTP 500.
Within each model/case pair only `num_predict` changes, from 1,024 to 2,048.
Capacity order alternates between blocks. Temperature stays zero, calls time out
after 60 seconds, and each trial gets exactly one model call without retries.
Prompts and the native tool schema are retained with source fingerprints.

No lab probes are executed. Minimal cases check whether returned tool proposals
exactly match the requested account/path pairs, including multiplicity. Replays
check tool shape and executor scope only; they do not grade whether the proposed
next investigation step is sensible. Scripted controls exercise those checks
without inference. This experiment produces no vulnerability verdicts.

Calls and their full output allowance are checkpointed before inference. Failures
retain reservations and unknown actual usage. Responses retain only assistant
message fields, allowlisted token counts and completion reasons. Diagnostics use
the existing fixed categories and numeric HTTP status; raw provider errors,
credentials and headers are excluded. Existing experiment directories cannot be
reused. An interrupted trial remains visibly unfinished rather than being retried.

Replaying one failure context per model cannot explain every earlier failure.
Aliases and temperature zero do not ensure deterministic provider output. The
capacity comparison changes an upper limit, not necessarily actual token usage.
Returned `length` reasons and observed counts can inform interpretation but do
not expose what happened inside an HTTP 500. Model/case blocks are serial and
their order is fixed, so provider state and caching remain possible confounds.
Historical discovery comparisons stay unchanged.

Completed retained bundles contain `compatibility.json`, a reviewed `report.md`
and a schema-2 SHA-256 manifest. Verify them with the ordinary offline verifier
or `python3 -m redwake.compatibility --directory BUNDLE --verify`.
