# Redwake

Find weaknesses. Prove impact.

Redwake is an early research prototype for evidence-backed API authorisation testing. It runs a synthetic application on an ephemeral loopback port, investigates its access rules, and produces reproducible request/response evidence. It includes classic and discovery labs, a scripted investigator, portable evidence bundles and offline verification. Optional model backends can direct the same bounded probes.

## Run it

Python 3.9+ on macOS or Linux. No runtime dependencies or installation required. From this directory:

```sh
python3 -m redwake demo
python3 -m redwake demo --mode fixed
python3 -m redwake evaluate --repeat 3
python3 -m redwake demo --scenario discovery
python3 -m redwake evaluate --scenario discovery --repeat 3
python3 -m unittest discover -s tests -v
```

The demo starts and stops its own lab. It prints a run ID and report path. Generated evidence, Markdown reports and SQLite state live under `.redwake/`, which is ignored by Git. Selected experiment bundles are retained in `docs/experiments/` for readers of a fresh clone. The vulnerable demo should prove two cross-account reads; the fixed demo should classify both as protected. Public content is a negative control.

The discovery scenario starts with account-specific project listings, follows nested record and attachment links, and mixes vulnerable reads, 403/404 protection, public content and an export outage. See [discovery lab details](docs/discovery-lab.md).

The [documentation index](docs/README.md) gives a reading order for guides, design decisions, the roadmap and retained experiment reports.

A completed investigation can be exported and verified without its original database:

```sh
python3 -m redwake export RUN_ID --output .redwake/evidence-RUN_ID
python3 -m redwake verify .redwake/evidence-RUN_ID
```

Export also supports stopped investigations, preserving incomplete coverage and consumed
allowances. It creates a fresh directory containing the saved state, captured responses,
results, report and SHA-256 manifest. Verify re-scores those responses offline; it does
not contact the application or require a model API key. A changed or inconsistent bundle
returns a nonzero exit code. Hashes detect changes, not authorship. See the
[evidence guide](docs/artifacts.md) before sharing model conversations.

```sh
python3 -m redwake resume RUN_ID
python3 -m redwake replay RUN_ID
python3 -m redwake demo --max-requests 3
```

Resume retains the original configuration, evidence, pending tool calls and cumulative allowances. A fresh instance of the same deterministic lab is started; its port may change. Exhausted budgets remain exhausted. Start a new run to choose different budgets. Replay regenerates reports from SQLite without making network requests or calling a model. It is evidence replay, not a new verification against a running application.

Global options go before the command:

```sh
python3 -m redwake --db /tmp/redwake.sqlite3 --reports /tmp/redwake-reports demo
```

## Validate submitted findings

Declare read-access policy and validate a structured finding against saved evidence with
`validate-finding`. Accepted and rejected claims can be exported and rechecked offline.
See the [submitted finding guide](docs/submitted-findings.md) and example contracts.
Use `demo --backend ollama --contract CONTRACT.json` to enable model submission and
validation feedback. These runs require an explicit finish and retain accepted/rejected
claims separately from fixture scores.

## Optional model backends

Set `OLLAMA_API_KEY` in your environment using an Ollama API key, then run:

```sh
python3 -m redwake demo --backend ollama --model gpt-oss:120b
python3 -m redwake demo --backend ollama --model nemotron-3-super
```

Model identifiers and account access must be confirmed with Ollama. Cloud requests use `https://ollama.com/api/chat`; the adapter follows the official [cloud API](https://docs.ollama.com/cloud), [chat reference](https://docs.ollama.com/api/chat) and [tool-calling contract](https://docs.ollama.com/capabilities/tool-calling). Only synthetic lab observations and the model conversation are sent. Credentials are read from the environment and are not written to run state.

Cloud calls inherit standard environment proxy settings (`HTTP_PROXY`, `HTTPS_PROXY`, and `NO_PROXY`) and Python's configured CA trust, with TLS verification enabled. This supports managed cloud environments that require an outbound proxy. Lab probes and local Ollama calls always connect directly, without inheriting proxies.

Direct OpenAI Responses API support is also available with `OPENAI_API_KEY` and an
explicit `--model`. It supports the same bounded probes and finding submissions. See the
[OpenAI provider guide](docs/openai-provider.md) for usage accounting, resume and pricing
limitations. Adapter support does not establish model security capability.

A running local Ollama server is also supported:

```sh
python3 -m redwake demo --backend ollama --endpoint http://127.0.0.1:11434 --model YOUR_MODEL
```

The local endpoint can use a locally installed model or a cloud model configured in Ollama. Redwake does not download models or configure your Ollama account.

The classic scenario’s default allowances are 12 lab requests, 8 model calls, 8,192 reserved output tokens and 120 seconds of recorded active time. Discovery defaults to 32 lab requests, 16 model calls, 16,384 reserved output tokens and the same 120 seconds. Each model call requests at most 1,024 output tokens. Override these with `--max-requests`, `--max-model-calls`, `--max-output-tokens` and `--max-seconds`. Calls and output allowances are reserved before network execution, including calls that fail or are interrupted. Successful short responses do not refund their output reservation.

These are experiment controls, **not a dollar spending cap**. Prompt tokens also cost usage, provider output limits may differ, and timed-out calls may still be billed remotely. Reports show returned token counts and flag incomplete usage; they do not invent monetary costs. Socket timeouts and between-operation time checks limit normal calls, but are not an OS-enforced wall-clock kill switch. A hard process termination can lose elapsed time since the last checkpoint.

## What the results mean

| Verdict | Required evidence |
|---|---|
| `vulnerable` | Owner and another actor both receive the expected private record |
| `protected` | Owner receives the record; the other actor receives 403 or 404 without its marker |
| `public_allowed` | Both actors receive a record explicitly declared public |
| `inconclusive` | Missing controls, errors, unexpected payloads, or insufficient evidence |

The model selects requests through one `probe(actor, path)` tool. The executor checks exact actor and path allowlists kept on the executor and uses only the current loopback lab. There is no shell tool, arbitrary URL, write operation, redirect following, or proxy inheritance for lab probes. Final model prose is not accepted as a finding. The private verifier uses known synthetic record markers and ownership rules. Models receive API guidance and observed responses; fixture IDs, ownership answers and expected verdicts are absent from discovery prompts and tool schemas.

The baseline evaluation covers vulnerable reads, 403 protection, 404 concealment and a 503 outage, each with two private resources and a public resource. Repetitions measure stability of this fixture; they do not create independent vulnerability classes. A completed baseline run means its probes finished, even if an outage leaves all verdicts inconclusive. In the classic scenario, if a model finishes early, Redwake prompts it with the missing or inconclusive checks and remaining budget, then continues the investigation. Model runs become completed as soon as coverage is conclusive, without spending another model call on a closing summary. Unresolved runs stop when a budget is exhausted or an operation fails. Discovery follow-ups give generic API guidance without revealing undiscovered paths or verifier answers. Discovery model runs complete once both account probes have been attempted for every record; outages remain inconclusive. The discovery baseline completes when its observed link frontier is exhausted.

## Implementation

- `lab.py`: ephemeral HTTP application with classic and discovery scenarios.
- `guidance.py`: model-facing API documentation and response-link parsing.
- `contracts.py`, `verifier.py`: private fixture truth, evidence validation and scoring.
- `transport.py`: bounded JSON requests and scope enforcement.
- `runner.py`: baseline/model execution, discovery traversal and usage reservations.
- `providers.py`, `openai.py`: provider adapters and tool schemas.
- `usage.py`, `costs.py`: per-call usage records and rate-card valuation.
- `store.py`: SQLite checkpoints.
- `report.py`: Markdown and JSON artifacts.
- `artifacts.py`: portable investigation export and shared offline verification.
- `cli.py`: demo, evaluation, resume, replay, export and verification.
- `comparison.py`: repeated baseline and live model comparisons.

The CLI takes an exclusive database lock to prevent concurrent writers from reusing allowances. An interrupted read may be retried on resume, with a new reservation; probes are read-only. The library itself is intended for a single runner per database. Stored evidence is a local research artifact, not a signed audit trail.

## Usage and cost accounting

Use `--pricing RATE_CARD.json` with an Ollama Cloud demo to retain a per-call usage ledger
and decimal rate-card valuations. `--billing-context` records free/included/purchased/unknown
usage; `--max-cost-usd` gates estimated usage value, not actual provider cash charges.
See [cost accounting](docs/cost-accounting.md) for examples, unknown usage and limitations.

## Research history

The retained comparisons informed the implementation and remain available in the
[documentation index](docs/README.md). They are not prerequisites for using or validating
Redwake. The [comparison method](docs/comparison-method.md) documents optional live
research commands and their costs. New live studies require a specific engineering
question and a decision that cannot be made with deterministic tests or retained evidence.

## Current limitations

This is a lab harness, not a general penetration-testing product. It does not yet support external targets, arbitrary access contracts, container isolation, mutation testing, provider-reconciled billing or proof of model capability. The lab runs in a local Python thread with synthetic data and is not a container sandbox.

See the [roadmap](docs/roadmap.md) for planned work.
