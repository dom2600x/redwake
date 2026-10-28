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

The proposed Anthropic adapter must preserve raw reported usage categories alongside
normalized totals. Keep provider/model identifiers, API version, cache retention,
processing mode, inference geography and pricing provenance with cost calculations.
Use reported token usage rather than assuming the same prompt has the same token count
across models or providers. Confirm exact API model IDs before making the snapshot executable.

These are implementation requirements, not claims that the adapter or accounting already
exists. Credentials, model availability and billing have not been checked through API calls.
Recheck current rates before paid acceptance work and reconcile against provider billing
where supported. Published price or model descriptions do not establish security capability;
selection remains governed by the project's security acceptance criteria.
