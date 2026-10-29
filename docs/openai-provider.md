# Direct OpenAI provider

Redwake supports the direct Responses API alongside Ollama. Choose an account-accessible
model explicitly; there is no automatic model selection or fallback. This integration
has deterministic mocked API tests, not a live account or model-capability certification.
The project has no Daybreak access and does not depend on those models.

```sh
# Set OPENAI_API_KEY in your environment first. This command incurs live API usage.
python3 -m redwake demo --backend openai --model YOUR_MODEL \
  --contract examples/findings/contract.json --max-model-calls 8
```

The endpoint is fixed to `https://api.openai.com/v1/responses`. Custom gateways, Azure
and provider-hosted tools are unsupported. Only synthetic lab observations and the
conversation are sent. Requests use the runtime's environment proxy and verified TLS;
redirects are disabled. The adapter does not retry automatically. A model or account
that rejects these request options produces a sanitized failure, rather than silently
changing model, mode or output allowance.

## Tool execution and resume

The adapter converts Redwake's existing probe/submission schemas to Responses function
tools. It requests Standard/default service, disables streaming and server-side storage
(`store: false`), and requests encrypted reasoning replay content. It leaves sampling and
reasoning-effort settings at the provider's defaults. The output allowance covers both
reasoning and visible output; 1,024 tokens can be too small for some reasoning models.
No successful model investigation or security capability is implied by adapter support.

Executed tool results are paired with their original call IDs, including after an
interruption midway through a batch. Native assistant output and encrypted reasoning
items are retained for stateless replay. Unknown output types and malformed response
structures stop with a fixed provider diagnostic. Malformed function arguments and
out-of-scope choices remain model/tool-contract rejections. Scope remains the same
loopback lab, with the same evidence validator and request allowances.

Incomplete responses stop before any proposed tool executes. Replay retains their
sanitized partial output for inspection; resume omits it from the next API input and
adds a fixed notice that no proposals from that response were executed. This starts a
fresh continuation rather than treating incomplete function arguments as executable.
Failed responses retain allowlisted usage but never arbitrary provider error objects.

## Usage, pricing and artifacts

New CLI model investigations record `usage_version: 1` and a durable `usage_ledger`,
independently of whether pricing is configured. Historical runs resume with their
original accounting format. Each entry records call number, UTC start, output reservation,
reported/unknown status, served model, response status, service tier and nullable counts.
Ollama cache/reasoning breakdowns remain unknown because its existing counters do not
supply those categories.

OpenAI `input_tokens` already includes `input_tokens_details.cached_tokens`;
`output_tokens` already includes `output_tokens_details.reasoning_tokens`. The ledger
preserves these subsets without adding them again to totals. Missing/invalid totals
remain unknown. Invalid subsets become unknown without discarding valid totals. A complete
total count does not imply every billing category is known. Failed or incomplete HTTP 200
responses can still report usage; transport failures retain unknown usage and reservations.
No response bodies from HTTP failures, arbitrary errors, headers or API credentials
are written to the ledger. Reported service tier is recorded separately from requested
mode; it is not assumed to be a billing guarantee.

Reports, JSON results, resume and single-run export preserve the ledger. Offline verification
checks its shape, subset bounds, call/output reservations and aggregate totals. For priced
Ollama runs it also checks agreement with the existing cost ledger. These checks establish
internal consistency, not provider authenticity. Like existing model conversations,
exports contain model text and now also opaque encrypted reasoning; review them before sharing.
`store: false` is an API option, not a blanket statement about provider retention policies.

`--pricing` and `--max-cost-usd` support direct OpenAI with a version 2 rate card.
See [cost accounting](cost-accounting.md) for context multipliers, cache uncertainty
and estimated budget semantics. Existing token/call/time allowances are not a cash
spending cap; use provider-side spending controls for paid runs. The dated
[pricing reference](openai-pricing.md) records the example card's source. Anthropic's
direct adapter remains future work.

Priced runs stop before executing proposed tools if returned model or service-tier
metadata is missing or does not match the card. Resume retains the stop while any
reported call has unsupported billing metadata; it does not spend another allowance.
Unpriced runs retain their existing execution behavior.
