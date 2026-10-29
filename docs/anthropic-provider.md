# Direct Anthropic provider

Redwake supports the synchronous [Messages API](https://platform.claude.com/docs/en/api/messages)
at the fixed `https://api.anthropic.com/v1/messages` endpoint. Choose an explicit
account-accessible model and set `ANTHROPIC_API_KEY` in the environment. There is
no default model, automatic fallback, model download or entitlement check. The
project has no restricted Mythos access and does not depend on those models.

```sh
# Optional live command: incurs provider usage and requires account/network setup.
python3 -m redwake demo --backend anthropic --model YOUR_MODEL \
  --contract examples/findings/contract.json --max-model-calls 8
```

The implementation is validated with mocked provider responses and the synthetic
loopback lab. No live account validation or model-capability certification is implied.
Managed environments must separately permit `api.anthropic.com` and configure the
credential. The adapter never changes network policy or attempts another provider.

## Requests and execution

Requests use `anthropic-version: 2023-06-01`, verified TLS, inherited cloud proxy
settings and the existing bounded JSON transport. Redirects and streaming are
disabled; no automatic retries occur. The API key is sent only in the `x-api-key`
header and is not saved to run state. HTTP failures retain fixed diagnostics rather
than arbitrary provider error bodies or headers.

System guidance is sent separately from conversation turns. Only Redwake's client
tools are exposed: bounded `probe` calls, plus `submit_finding` and explicit
`finish_investigation` when a contract is supplied. Tool results are grouped into
the subsequent user turn and correlated with the original tool-use IDs. An
interrupted batch resumes its remaining calls without losing that correlation or
refunding consumed reservations. Provider-hosted tools, extended thinking, cache
controls, custom gateways, partner clouds and additional request modes are unsupported.

`max_tokens` uses the same per-call output reservation as other providers. A
`max_tokens` or `pause_turn` response stops before any proposed tool executes.
The allowlisted partial content is retained for inspection; resume omits it and
sends a fixed continuation notice. Refusals, unsupported stop reasons, unknown
content blocks and malformed response envelopes stop with sanitized diagnostics.
Malformed tool arguments and out-of-scope model choices remain tool-contract
rejections. Completion is an explicit reporting action for submitted-finding runs,
not a claim that the application is secure.

## Usage contract version 2

Anthropic runs use `usage_version: 2`. Existing Ollama/OpenAI runs retain version 1
and its original record shape. Each Anthropic call records the requested API
version, allowlisted stop reason and service tier, served model, reservation and
nullable token categories:

| Ledger field | Meaning |
|---|---|
| `uncached_input_tokens` | Reported ordinary `input_tokens`, excluding cache reads/writes |
| `cache_creation_input_tokens` | Reported total cache creation |
| `cached_input_tokens` | Reported `cache_read_input_tokens` |
| `input_tokens` | Ordinary input + cache creation + cache reads, when all three are known |
| `cache_creation_5m_tokens` | Reported `cache_creation.ephemeral_5m_input_tokens` |
| `cache_creation_1h_tokens` | Reported `cache_creation.ephemeral_1h_input_tokens` |
| `output_tokens` | Reported output total |
| `reasoning_tokens` | Unknown; no separate reasoning breakdown is assumed |

Missing or invalid counts stay unknown, including omitted cache counters. A
missing category makes the normalized input total unknown while preserving known
categories. No absent value is treated as zero. Cache retention splits are kept
only when both counts are valid and sum to the reported creation total; otherwise
both remain unknown. Ordinary input is never reduced by cached reads, and the
cache categories are never added twice. API version records the requested header,
not an assertion that the provider authenticated the retained evidence.

Reported totals survive malformed, incomplete and failed HTTP 200 responses.
Timeouts, interruptions and HTTP failures retain unknown usage and output
reservations. Aggregate token completeness does not establish cache-split or
billing completeness. Resume, replay, reports, single-run export and offline
verification preserve these categories and recompute their arithmetic. Exports
contain model text and captured synthetic responses; review them before sharing.

## Pricing boundary

Anthropic monetary valuation and `--pricing`/`--max-cost-usd` are unsupported in
this milestone. Ollama/OpenAI cards cannot be applied to this route. Cache-write
retention, context thresholds, processing mode and geography need a separate
rate-card contract; the [pricing reference](anthropic-pricing.md) records those
requirements without claiming exact API model IDs or account access. Token,
call and time allowances are not a monetary spending cap. Use provider-side
controls for paid runs. No cash charge or security-model ranking is inferred.
