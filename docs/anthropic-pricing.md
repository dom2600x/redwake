# Anthropic pricing and access reference

Checked: 2026-10-28 against the [official pricing documentation](https://platform.claude.com/docs/en/about-claude/pricing).
This snapshot is not an executable rate card or confirmation of account entitlement.

## Project access

The owner confirms that this project currently has **no access to restricted Mythos
models**. Exclude them from default configurations, acceptance checks and release
requirements. Do not probe restricted models. Published prices do not establish account
access to other models either; confirm that access before using them.

## Relevant text rates

USD per million tokens, base synchronous Claude API pricing. Separate cache categories
must retain their model-specific rates.

| Model | Input | Output | 5-minute cache write | 1-hour cache write | Cache read |
|---|---:|---:|---:|---:|---:|
| Claude Fable 5.1 | 10.00 | 50.00 | 12.50 | 20.00 | 0.25 |
| Claude Opus 5.5 | 4.00 | 20.00 | 5.00 | 8.00 | 0.20 |
| Claude Sonnet 5.5 | 2.00 | 10.00 | 2.50 | 4.00 | 0.10 |
| Claude Haiku 5.5, prompt up to 100,000 tokens | 0.10 | 0.50 | 0.125 | 0.20 | 0.01 |
| Claude Haiku 5.5, prompt above 100,000 tokens | 0.50 | 2.50 | 0.625 | 1.00 | 0.05 |

Haiku's threshold includes cache reads and writes; the higher tier applies per request.
Batch halves base input/output rates. Opus 5.5 Fast has input/output rates of 8.00/40.00,
stacks cache/residency modifiers and cannot use Batch. Applicable US-only inference adds
10% across token categories. Partner-operated cloud routes need their own pricing.
Client tools incur token overhead; hosted tools can carry additional charges.

## Usage normalization

The [prompt caching guide](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)
reports ordinary input, cache creation and cache reads in separate usage fields:

```text
total_input_tokens = input_tokens
                   + cache_creation_input_tokens
                   + cache_read_input_tokens
```

Here `input_tokens` excludes both cached categories. Do not subtract cache reads from it,
or apply an OpenAI-style inclusive-input assumption. Cache creation must be split by
5-minute/1-hour retention when both are used. If the supplied usage cannot resolve that
split, preserve the unknown rather than inventing an exact charge.

## Implementation consequences

The [Anthropic adapter](anthropic-provider.md) preserves allowlisted reported usage
categories alongside normalized totals, requested API version, stop reason and service tier.
Future monetary valuation must keep provider/model identifiers, cache retention,
processing mode, inference geography and pricing provenance with cost calculations.
Use reported token usage rather than assuming the same prompt has the same token count
across models or providers. Confirm exact API model IDs before making the snapshot executable.

Opt-in monetary estimates now use version 3 rate cards. Credentials, model
availability and billing have not been checked through API calls.
Recheck current rates before paid acceptance work and reconcile against provider billing
where supported. Published price or model descriptions do not establish security capability;
selection remains governed by the project's security acceptance criteria.

## Executable estimates

`--pricing examples/pricing/anthropic-template.json` illustrates the version 3
schema with **synthetic rates and a placeholder model**. Copy it and replace the
model, every rate, context threshold, multipliers, source and date with verified
account-applicable values before paid use. No default model or executable price
snapshot is inferred from the reference table above.

Only direct, synchronous, standard-tier global execution with API version
`2023-06-01` is supported. Processing mode and geography are explicit pricing
assumptions matching the adapter's default request; geography is not independently
reported or verified by the usage response. Batch, Fast, priority, US residency,
partner clouds and hosted-tool charges need separate contracts and are rejected
as card settings. Served model and reported service tier must match; missing or
mismatched metadata retains the reservation and blocks further execution.

All rates are decimal USD strings per million tokens. `input` prices ordinary
input, `cached_input` prices reads, and `cache_write_5m`/`cache_write_1h` price
replacement creation tokens. These categories are disjoint. The sum of all input
categories selects the context tier: strictly above `context_threshold`, multiply
all input categories by `long_input_multiplier` and output by
`long_output_multiplier`. Use multipliers of one when no premium applies.

Unknown creation retention yields a range between the declared write rates;
zero creation needs no split. Missing counters remain unknown, with known
categories valued separately. If known categories already exceed the threshold,
the long tier is certain; otherwise a missing total retains both tier possibilities.
Exact rate-card values require resolved categories and rates. They remain estimates,
never reconciled provider cash charges.

Before transport the SQLite checkpoint retains a reservation using
`input_token_reservation` times the highest input/cache rate and long multiplier,
plus the output allowance at the long output rate. Transport failures and crash
recovery retain that exposure. Partial usage keeps the greater of the reservation
and the known upper valuation; complete usage replaces the reservation with its
valuation range. Resume rechecks ledger arithmetic, metadata and accumulated
exposure before tools or new inference. An overrun stops execution immediately.
Exports retain the policy and ledgers; `verify` recomputes estimates offline.

Deterministic tests use synthetic rates and mocked transport; they establish
accounting behavior, not account entitlement or actual billing.
