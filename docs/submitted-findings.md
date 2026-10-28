# Submitted authorization findings

A submitted finding is a claim to validate, rather than an automatically generated
fixture verdict. This first version supports a bounded claim: an actor outside the
resource's declared read permissions received the identified record, with a successful
owner control. It does not validate account takeover, writes or arbitrary impact prose.

Contracts declare actor aliases and exact resource paths, an owner, permitted readers
and identity assertions expressed as JSON pointers into response objects. Identity
assertions identify the actual record, not merely a successful HTTP status. Declare
public/shared access through the permitted-reader list. Contracts express supplied policy;
Redwake does not prove that the policy itself is correct. They never grant network scope.

A submission identifies one rule, the unauthorized actor, two evidence IDs (owner first),
an exact GET reproduction sequence and the typed impact `unauthorized_record_read`.
Both referenced responses must be successful and match the declared record identity.
References must identify the latest observation for each actor/path pair, so earlier
successes cannot hide a later denial or outage. Unsupported claims are rejected without
converting absent evidence into an assertion of protection.

## Run the example

Create a classic vulnerable baseline run and substitute its printed ID below:

```sh
python3 -m redwake demo --mode vulnerable
python3 -m redwake export RUN_ID --output .redwake/source-proof
python3 -m redwake validate-finding \
  --contract examples/findings/contract.json \
  --finding examples/findings/finding.json \
  --bundle .redwake/source-proof --output .redwake/finding-proof
python3 -m redwake verify .redwake/finding-proof
```

The example's evidence IDs apply to that baseline traversal; other runs need their actual
IDs. Validation makes no requests or model calls and does not access SQLite. It consumes
a verified single-investigation export, snapshots it with the contract and submission,
and writes a hash-inventoried proof containing `validation.json`. Rejected submissions
also produce a proof. Exit codes: 0 accepted, 1 unsupported/rejected claim, 2 invalid input.
Output destinations must be new directories.

`verify` checks the complete proof inventory, re-verifies the source export and recomputes
the submitted claim. Verification success means the saved acceptance or rejection is
consistent, not that every submission was accepted. Copied proof directories need no
original database. Hashes detect changes, not authorship or authenticity; saved evidence
and the supplied policy are trusted inputs, not a signed observation from the target.

## Model-loop submission

Enable the opt-in protocol with a saved contract:

```sh
python3 -m redwake demo --backend ollama --model YOUR_MODEL \
  --contract examples/findings/contract.json
```

This command makes live provider calls and needs the usual provider configuration.
The model receives policy rule IDs, paths, ownership and permitted readers; identity
assertions and expected fixture verdicts remain private. Its tools are `probe`,
`submit_finding` and `finish_investigation`. Submission returns validation feedback.
Malformed tool arguments still stop the run; a well-formed unsupported claim is retained
and rejected, allowing correction within the original model/time/token allowances.

Coverage alone no longer finishes these runs. The model explicitly finishes, possibly
with no findings. Reporting tools do not consume network-request allowance, so a model
may report after spending its final probe, while model-call and time limits still apply.
Resume preserves the contract, pending tools, submitted claims and consumed allowances.
Ordinary `export` and `verify` support these runs without a live provider.

Reports separate fixture scores from submitted claims. Each submission retains its
validation at the recorded evidence boundary plus a current validation using the latest
observations. An earlier acceptance is not presented as current proof after contradictory
evidence. Completion means reporting finished; it does not assert security or completeness.
Historical comparisons retain their original probe-only tools and completion behavior.

## Current boundary

The evaluator accepts nonfixture actor names, paths and nested JSON-object identities.
The capture workflow still uses the existing bounded lab executor and its export format.
This milestone does not support external targets or grade natural-language security
reasoning. Those integrations follow this bounded submission workflow. No new model-capability claims arise from these tests.
