# Documentation

Start with the current guides, then read the design and roadmap. Dated experiments
preserve what was observed at a particular source revision; their test counts and
conclusions describe that snapshot.

## Current guides

1. [Project README](../README.md): setup, commands, execution controls and current limitations.
2. [Discovery lab](discovery-lab.md): navigation, access cases, private verifier rules and metrics.
3. [Evidence artifacts](artifacts.md): exporting individual investigations, retained evidence, provenance and offline checks.

Generated runtime state stays in the ignored `.redwake/` directory. Published
experiment bundles under `docs/experiments/` contain the evidence retained with
the repository, so reading them does not require the original local database.

See also the [comparison method](comparison-method.md) for fixed profiles and diagnostics.

The [provider compatibility experiment](provider-compatibility.md) isolates fresh
tool-call prompts and saved failure contexts from live investigation.
The [transcript experiment](transcript-experiment.md) tests declared reductions
and tool-result correlation with a direct native API cross-check.
The [varied discovery suite](varied-discovery.md) rotates profiles across ID and
navigation variants while retaining the same access cases and allowances.
The [counterbalanced topology suite](topology-suite.md) adds deeper and branching
graphs with graph-aware guidance and repeated within-condition order balance.

## Design and roadmap

- [Current project decisions](project-decisions.md): delivery direction, security acceptance, model usage, cost accounting and user-supplied Ollama pricing/quota information.
- [OpenAI pricing and access](openai-pricing.md): dated official pricing reference, billing conditions and the project's Daybreak access restriction.
- [Anthropic pricing and access](anthropic-pricing.md): dated official pricing reference, cache accounting and the project's Mythos access restriction.
- [Roadmap](roadmap.md): the canonical next steps and their dependencies.
- [Initial engineering decisions](decisions.md): the dated 2026-10-10 classic-lab design; the discovery guide describes the current model guidance.

## Dated experiments

| Experiment | Read first | Retained evidence |
|---|---|---|
| 2026-10-10 Mac classic experiments | [Model comparison](experiments/2026-10-10-mac/report.md), [initial validation](experiments/2026-10-10-mac/validation.md), [example report](experiments/2026-10-10-mac/example-report.md) | 39 saved runs with state, captured responses, results and reports; [manifest](experiments/2026-10-10-mac/manifest.json) and [results](experiments/2026-10-10-mac/results.json) |
| 2026-10-11 cloud proxy validation | [Validation summary](experiments/2026-10-11-cloud-proxy/report.md) | Summary only; the original raw run is unavailable in the uploaded Mac archive and current workspace |
| 2026-10-11 discovery comparison | [Comparison report](experiments/2026-10-11-discovery/report.md) | All 24 comparison runs; [manifest](experiments/2026-10-11-discovery/manifest.json) and [comparison data](experiments/2026-10-11-discovery/comparison.json) |
| 2026-10-27 controlled discovery follow-up | [Combined comparison](experiments/2026-10-27-discovery-followup.md) | All 72 runs across separate [current](experiments/2026-10-27-discovery-current/report.md), [sequential](experiments/2026-10-27-discovery-sequential/report.md) and [batching](experiments/2026-10-27-discovery-batching/report.md) bundles |
| 2026-10-27 provider compatibility | [Compatibility report](experiments/2026-10-27-provider-compatibility/report.md) | All 36 live calls and 36 scripted controls; [inputs and results](experiments/2026-10-27-provider-compatibility/compatibility.json) and [manifest](experiments/2026-10-27-provider-compatibility/manifest.json) |
| 2026-10-28 transcript reduction | [Reduction report](experiments/2026-10-28-transcript-reduction/report.md) | All 48 calls and 48 scripted controls; [inputs and results](experiments/2026-10-28-transcript-reduction/transcript.json) and [manifest](experiments/2026-10-28-transcript-reduction/manifest.json) |
| 2026-10-28 varied discovery pilot | [Pilot report](experiments/2026-10-28-varied-discovery/report.md) | All 72 runs across original, renamed-ID and opaque-collection fixtures; [comparison plan](experiments/2026-10-28-varied-discovery/comparison.json) and [manifest](experiments/2026-10-28-varied-discovery/manifest.json) |
| 2026-10-28 counterbalanced topology study | [Study report](experiments/2026-10-28-topology-study/report.md) | All 216 investigations with three repetitions across opaque-reference, deeper and branching graphs; [comparison plan](experiments/2026-10-28-topology-study/comparison.json) and [manifest](experiments/2026-10-28-topology-study/manifest.json) |

These are historical reports, not instructions to rerun an experiment. A new run
produces a new result and should retain its own provenance. Use the roadmap for
the next planned experiments.
