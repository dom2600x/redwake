# Documentation

Start with the current guides, then read the design and roadmap. Dated experiments
preserve what was observed at a particular source revision; their test counts and
conclusions describe that snapshot.

## Current guides

1. [Project README](../README.md): setup, commands, execution controls and current limitations.
2. [Discovery lab](discovery-lab.md): navigation, access cases, private verifier rules and metrics.
3. [Experiment artifacts](artifacts.md): publishing and importing retained evidence, provenance and offline checks.

Generated runtime state stays in the ignored `.redwake/` directory. Published
experiment bundles under `docs/experiments/` contain the evidence retained with
the repository, so reading them does not require the original local database.

## Design and roadmap

- [Roadmap](roadmap.md): the canonical next steps and their dependencies.
- [Initial engineering decisions](decisions.md): the dated 2026-10-10 classic-lab design; the discovery guide describes the current model guidance.

## Dated experiments

| Experiment | Read first | Retained evidence |
|---|---|---|
| 2026-10-10 Mac classic experiments | [Model comparison](experiments/2026-10-10-mac/report.md), [initial validation](experiments/2026-10-10-mac/validation.md), [example report](experiments/2026-10-10-mac/example-report.md) | 39 saved runs with state, captured responses, results and reports; [manifest](experiments/2026-10-10-mac/manifest.json) and [results](experiments/2026-10-10-mac/results.json) |
| 2026-10-11 cloud proxy validation | [Validation summary](experiments/2026-10-11-cloud-proxy/report.md) | Summary only; the original raw run is unavailable in the uploaded Mac archive and current workspace |
| 2026-10-11 discovery comparison | [Comparison report](experiments/2026-10-11-discovery/report.md) | All 24 comparison runs; [manifest](experiments/2026-10-11-discovery/manifest.json) and [comparison data](experiments/2026-10-11-discovery/comparison.json) |

These are historical reports, not instructions to rerun an experiment. A new run
produces a new result and should retain its own provenance. Use the roadmap for
the next planned experiments.
