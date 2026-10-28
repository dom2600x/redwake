# Counterbalanced topology suite

```sh
python3 -m redwake.discovery_suite --topologies --repeat 3 --directory .redwake/topology-study
```

This version-two suite has 216 planned investigations: three fixtures × two modes
× three profiles × four backends × three repetitions. It retains 54 baselines and
162 live model runs. Every profile occupies first, middle and last position once
within each fixture/mode condition; every model likewise occupies each model
position once within each fixture/mode/profile condition. This is position
counterbalancing, not full permutation randomisation or balancing all carryover
effects. Fixture and mode order remain fixed.

| Fixture | Navigation graph | Scripted requests |
|---|---|---:|
| discovery_links | Project → one opaque collection per account | 18 |
| discovery_deep | Project → intermediate node → opaque collection | 20 |
| discovery_branch | Project → two opaque collections per account | 20 |

Project IDs, record IDs, ownership, markers and the six access cases are identical.
The primary opaque collection URLs are shared; new nodes add their own fixed URLs.
Deep and branching graphs have equal navigation cost (eight account/path probes)
and twelve record probes. The control has six navigation probes. These are graph
variations over related security cases, not independent vulnerability classes.

The study uses a separately recorded `graph` guidance variant for every fixture
and profile. It explicitly allows intermediate nodes and multiple collections,
without revealing node IDs or verifier answers. Current and sequential share
initial messages; batching adds the existing advice. Old suite version one keeps
its exact original fixture set and guidance, preserving all historical bundles.
Cross-study changes therefore include guidance and time, not only topology.

Allowances remain current 32 requests/16 calls/16,384 reserved output tokens,
sequential 32/24/24,576 and batching 32/16/16,384, all with 120 active seconds.
Each call reserves up to 1,024 output tokens and requests temperature zero, with
the existing 60-second timeout bounded by remaining active time. Deep/branching
traversals leave four calls of sequential headroom, compared with six in control.
Correct path inference or batching can alter actual probe counts; the scripted
counts are not executor-enforced minimums.

Scope rejection, origin, actors, GET-only execution and provider request building
stay fixed. All planned slots, failed runs, unknown usage and baselines remain in
the matrix. There are no retries, resumptions or extra allowances. Regular CLI
resume retains the saved graph fixture and guidance, including consumed allowance;
the controlled experiment itself never resumes individual runs.

Export uses the existing reviewed bundle flow. Offline verification checks the
versioned fixture set, guidance, complete plan/order, per-profile controls, actual
conversations, evidence, accounting, summaries and hashes. Results must separate
discovery exposure, owner controls, attempted coverage, proved flaws, scope stops,
allowances and inference failures. Three deterministic repetitions do not establish
general capability, service reliability or independent vulnerability prevalence.
