# Roadmap

Redwake develops the lab harness and its evidence model before adding external
targets. Experiment results live in their own reports; this document records the
sequence of planned work.

## Completed foundations

- A bounded loopback executor, durable accounting, evidence replay and a scripted
  baseline. See [initial validation](validation.md).
- A [discovery lab](discovery-lab.md) with account-specific project listings,
  nested records and detail links, covering vulnerable, protected, public and
  outage cases.
- Model-facing API guidance separated from private ownership rules and verifier
  expectations.
- A repeatable comparison of the scripted baseline, GPT-OSS, Super and Ultra,
  recording findings, misses, false positives, requests, tokens and active time.
  See the [live discovery comparison](discovery-model-comparison.md).

## Next experiments

1. Repeat the comparison with enough model calls for sequential discovery. Keep
   the current-budget batch as a separate result so changes remain comparable.
2. Test explicit batching guidance in a separate experiment, keeping prompts and
   allowances fixed within each batch. Retain the scripted baseline and failed
   runs in every comparison.
3. Improve sanitized provider-error diagnostics to distinguish inference failures
   from model choices without persisting credentials or arbitrary provider errors.

These experiments should separate resource discovery, evidence collection and
budget management before drawing broader conclusions about model capability.
Detailed observations and experiment limitations remain in the comparison report.

## External targets

General target support should follow only after the access contract, scope
enforcement and evidence model can represent it accurately. Extend those
foundations before adding external targets; the current synthetic lab does not
establish readiness for them.
