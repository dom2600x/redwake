# OpenAI pricing and access reference

Checked: 2026-10-28 against the [official API pricing page](https://developers.openai.com/api/docs/pricing).
This is a documentation snapshot, not an executable rate card or an account-entitlement check.

## Project access

The owner confirms that this project currently has **no access to Daybreak cyber models**.
Exclude them from default configurations, acceptance checks and release dependencies.
Do not probe restricted models or assume access from a published price. Availability of
other models must also be confirmed for the project's API account before use.

## Relevant text rates

USD per million tokens, Standard mode, short-context pricing as displayed on the source
page. Cache writes and cached reads are separate billing categories.

| Model | Input | Cached input | Output | 30-minute cache write | 12-hour cache write |
|---|---:|---:|---:|---:|---:|
| gpt-6-astra | 10.00 | 1.00 | 50.00 | 12.50 | 25.00 |
| gpt-6.1-sol | 2.00 | 0.10 | 10.00 | 2.50 | 5.00 |
| gpt-6.1-terra | 1.00 | 0.05 | 5.00 | 1.25 | 2.50 |
| gpt-6-luna | 0.10 | 0.01 | 0.50 | 0.125 | 0.25 |

The pricing page separates Standard, Flex/Batch, Fast and Ultrafast modes. Record the
actual mode, context tier and cache policy. Applicable regional/FedRAMP processing can
add a 10% premium. Built-in tools can add charges beyond token usage. Direct API prices
must not be assumed to apply to Azure or Bedrock billing.

## Model-specific conditions

The [GPT-6.1 Sol reference](https://developers.openai.com/api/docs/models/gpt-6.1-sol)
requires the Responses API for tool calling. The [implemented adapter](openai-provider.md) uses the Responses API; it does not
reuse an Ollama-style chat request. Monetary valuation remains unsupported.

For Sol, that reference states that requests above 272,000 input tokens multiply input
and cache rates by two and output rates by 1.5 for the entire request. It also documents
Flex/Batch at half Standard rates, Fast at twice Standard and Ultrafast at six times
Standard. Confirm supported modes and thresholds for each model rather than inheriting
those rules across the catalog.

The [GPT-6 Astra reference](https://developers.openai.com/api/docs/models/gpt-6-astra)
also specifies the above-272,000-token input/cache and output multipliers. Cache-write
retention needs its own rate; the general cache-write price shown on a model page does
not replace the retention-specific columns on the pricing page.

## Accounting consequences

The [reasoning guide](https://developers.openai.com/api/docs/guides/reasoning) explains
that reasoning tokens incur output charges even without visible answer text. Its example
usage object includes reasoning in `output_tokens`, with a breakdown under
`output_tokens_details.reasoning_tokens`. Preserve the breakdown but do not bill it again
on top of the reported output total. An incomplete response may still consume billable
input and reasoning tokens. Preserve status and usage even when no finding is returned.

The provider interface should preserve returned usage, served model, processing mode,
cache categories/retention and any supported context-tier information. Store source/date
with calculated costs and distinguish calculation from provider-reconciled billing.
Missing categories must remain explicit estimates or unknowns. Recheck rates before a
paid acceptance check; no live inference or account-access check was made for these notes.

Published prices and provider descriptions do not establish security-analysis capability.
Model selection remains subject to the project decision record's security acceptance criteria.
