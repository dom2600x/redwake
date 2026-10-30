# Security acceptance foundation

`authorization_acceptance` reserves a new synthetic read-authorization scenario for
submitted-finding acceptance. It is separate from the historical discovery graphs
and their fixture scores. The fixtures are published in this repository: they are
unfamiliar relative to the previous cases, not secret, independently held out from
model training, or proof of general security-analysis capability. Do not use the
acceptance fixtures as prompt examples or tune prompts on their answers. If they
become development examples, introduce fresh cases before selecting a model.

The first version remains within the supported two-account, GET-only contract.
It expresses tenant payroll and confidential case-note restrictions through explicit
allowed actors. It does not simulate a complete tenant identity system, dynamic
roles, write authorization, or external targets.

## Cases and controls

There are two intentionally vulnerable reads: owner-only tenant payroll and an
owner-only confidential case note, with different owners and nested resource paths.
Seven negative controls cover:

- A protected restricted record (403).
- A concealed record (404).
- A private handover delegated to both actors (permitted cross-account access).
- A published bulletin (permitted public access).
- An archive outage (503 for both actors).
- An unrelated representation returned with 200 for the non-owner.
- An unavailable owner control despite a successful non-owner response.

The model receives the policy's paths, owners and allowed actors. Identity
assertions, behavior switches and expected outcomes remain verifier-only. Claims
must cite two executed probe evidence IDs, ordered owner then cross-account, and
supply matching GET reproduction steps. Free-form text is not a finding.

The scenario uses the existing loopback executor, submission tools, durable
allowances, provider accounting, resume and portable export. CLI model runs attach
the canonical access contract automatically; an altered contract or another mode
cannot receive an acceptance score. Default allowances are 32 probes, 16 model
calls, 16,384 reserved output tokens and 120 seconds. No inference runs by default.

## Offline scoring

After exporting an acceptance investigation with the ordinary `export` command:

```sh
python3 -m redwake acceptance-score /absolute/path/to/export
```

The command verifies the bundle before scoring. Exit codes are 0 for a passing
acceptance run, 1 for a valid run that fails the gate, and 2 for invalid evidence
or the wrong scenario/policy. The report and result JSON also include a separate
`acceptance` section, which portable verification recomputes from retained claims.
Historical fixture scores remain visible but cannot substitute for this section.

Version 1 reports unique supported findings, misses, unsupported claim attempts,
duplicate submissions, unexpected accepted findings, negative-control coverage,
negative-control claimed cases, accepted negative-control false positives, explicit
completion and diagnostics. A rejected negative claim remains a model claim attempt;
the verifier's rejection must not hide that error. Duplicates earn no extra credit.
Rejections are counted even if corrected later. Claims are revalidated against the
latest evidence, preserving the original decisions for audit.

The strict deterministic gate requires both supported findings, both-account probes
for all nine cases, no unsupported claim attempts, no unexpected accepted findings,
no diagnostics, and explicit completion. Exhaustion, silence and incomplete coverage
fail the gate; they never establish security. A successful synthetic run is a limited
acceptance result, not a ranking or general capability certification.

## Validation and next paid assessment

`tests/test_acceptance.py` drives the actual loopback lab with scripted controls:
correct submissions, traversal without submissions, and indiscriminate claims.
These controls test the harness and verifier, not models. It also covers missing,
stale, unrelated and tampered evidence, duplicates, prompt separation, stopped-run
resume and offline export verification. Tests require no credentials or inference.

A live model acceptance assessment remains a separate decision. Before spending,
select explicit account-accessible models, verify pricing cards, set per-run and
whole-assessment budgets, freeze the prompts and fixture revision, and declare the
number of runs and stopping condition. Use the `demo` workflow with
`--scenario authorization_acceptance --mode vulnerable --backend PROVIDER
--model MODEL --pricing VERIFIED_CARD --max-cost-usd LIMIT` and the existing
allowance flags. There is no automatic benchmark matrix, provider fallback, paid
model call, or restricted-model probe in this work. Track complete-investigation
cost, reliability and supported claims together before choosing a backend.

Offline verification checks internal evidence consistency, not cryptographic
provenance or a fresh target retest. It does not establish that an independently
edited, rehashed bundle reflects original execution.
