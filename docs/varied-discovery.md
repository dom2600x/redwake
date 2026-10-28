# Varied discovery suite

The suite compares the existing current, sequential and batching profiles within
each fixture/mode block, instead of completing whole profiles in a fixed order.

```sh
python3 -m redwake.discovery_suite --directory .redwake/varied-pilot --repeat 1
python3 -m redwake demo --scenario discovery_links
```

The default pilot contains 72 runs: three fixtures × two modes × three profiles
× four backends. This includes 18 scripted baselines and 54 live Ollama runs.
Prompts and allowances are unchanged within each named profile. The endpoint,
temperature, request/output limits, timeout policy and strict scope rejection
match the existing comparison controls. There are no retries, exclusions,
resumptions or extra allowances for failed runs.

| Fixture | Deliberate difference |
|---|---|
| discovery | Original project/record IDs and nested collection URLs |
| discovery_ids | New project and resource IDs; same navigation structure |
| discovery_links | Original IDs; collections use opaque `/api/collections/...` links |

All fixtures retain the same ownership, visibility, content markers and six
behavioural cases. Their link-following baseline takes 18 probes in vulnerable
and fixed mode. The opaque links prevent the original `/projects/ID/records`
shortcut from being an accepted path. This tests link use together with the
existing scope policy, not a new authorisation vulnerability class.

Models receive the same public API guidance across fixtures, without record IDs
or private verifier expectations. The executor uses a fixture-specific exact
allowlist; a path permitted in one fixture can be rejected in another. No target
origin, shell, redirect or arbitrary-path capability is added. Resumption keeps
the saved scenario and uses its original fixture.

Profiles rotate between blocks, and models rotate within each profile block.
In a one-repeat pilot each profile occupies first, middle and last position twice
overall, but not within every fixture/mode condition. Use `--repeat 3` for a
216-run suite that rotates both profile and model positions within each condition.
The additional repetition offset prevents order rotations from cancelling.
Fixture and mode order stay fixed, so service changes and caching remain possible
confounds. A pilot gives only one run per model/profile/fixture/mode; its strata
cannot estimate stability or support broad capability rankings.

Results are grouped by fixture and profile rather than pooling different inputs.
Completion, proved flaws, exposed links, attempted record pairs, successful owner
controls, duplicate probes, budget stops and provider failures remain distinct.
The variants share vulnerability semantics and are not independent classes.

Completed suites use the existing reviewed export flow:

```sh
python3 scripts/export_experiment.py .redwake/varied-pilot \
  docs/experiments/DATE-varied-discovery --report /tmp/varied-report.md
python3 scripts/verify_experiments.py docs/experiments/DATE-varied-discovery
```

The suite plan records each slot's fixture, profile, mode, model and execution
position, with per-profile controls and source fingerprints. Export and offline
verification require every planned slot, including baselines and failed runs,
and check actual prompts, budgets, evidence, fixture scoring and summaries.
Old fixtures and retained comparisons keep their original semantics and row shapes.
