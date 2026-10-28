# Provider usage and cost accounting

The first implementation is opt-in for Ollama Cloud. A run snapshots a flat USD rate
card and billing context, then saves one ledger entry per model call. Historical runs
and comparison profiles keep their original format and receive no retrospective charges.
Direct OpenAI/Anthropic adapters and their cache-write/tier rules are not implemented here.

```sh
python3 -m redwake demo --backend ollama --model nemotron-3-ultra \
  --pricing examples/pricing/ollama-ultra.json --billing-context free \
  --input-token-reservation 32768 --max-cost-usd 0.25
```

This command makes live inference calls; it is not required for development or tests.
The example rate card is the owner's October 28 supplied snapshot, not a current-price
lookup. Confirm its applicability before paid use. Cards identify provider, exact requested
model, USD currency, source and observation date. Rates are decimal strings per million
tokens. This version accepts flat input/output rates and an optional cached-input rate;
it does not automatically select off-peak prices or apply context/service-tier modifiers.
Use only a card applicable to the selected workload and provider route.

## What is recorded

Each call reserves output allowance as before, plus a usage-value estimate before the
network request. The durable ledger records a UTC start time, call number, output limit,
reservation and returned input/output token counts. A bounded served-model identifier is recorded
when reported. A mismatch with the rate card leaves valuation unknown and retains the
reservation; aliases are not silently equated. Missing model identity is flagged as unverified. Failures and interrupted calls retain
unknown usage and their estimated reservation. Missing usage is never replaced by zero.
Resume keeps the original policy, ledger and cumulative limits; it cannot add a new budget.

Ollama's `prompt_eval_count` and `eval_count` are recorded as reported. No undocumented
cache-hit field is assumed. When cached/uncached input rates differ, the report gives a
minimum value and conservative estimate for the reported counts rather than claiming an
exact split. An absent cached-input rate is not a zero-price guarantee. When both input
rates coincide and counts are complete, the rate-card value of those counts is calculated
with decimal arithmetic. It is still not an independently reconciled provider bill.

`billing_context` is one of free, included, purchased or unknown. It describes the caller's
configuration; Redwake cannot verify account credit routing. Rate-card usage value remains
visible even in free mode. Cash charges remain unknown and `provider_reconciled` stays
false. This flag does not enforce free-only usage or stop Ollama consuming purchased credits.

## Estimated budget, not an account spending guarantee

Before a call, the gate checks the accumulated estimated exposure plus the next reservation.
The reservation uses the configured input-token estimate, the highest declared input rate
and the requested output allowance. Complete responses replace that estimate with the upper
rate-card value of reported counts; unknown responses retain at least their reservation.
If reported usage exceeds the configured budget, the run stops before executing its tools.

The input reservation is an operator estimate, not an enforced provider input-token limit.
Underestimated context, provider billing differences and timed-out work can exceed it.
`--max-cost-usd` therefore limits estimated usage value, not cash spending. Provider-side
controls or authoritative reconciliation are needed for a strict monetary guarantee.
Costs incurred by other clients using the account are outside this run's ledger.

## Reports and evidence

Reports and result JSON include the usage valuation, known minimum, estimated exposure,
unknown-usage call count and billing context. `export` preserves the policy and call ledger;
`verify` recomputes valuations and checks call counts, reservations and aggregate usage.
No network access or billing API is used for replay or verification. There is no claim
that a self-contained hash inventory authenticates provider billing or observations.
