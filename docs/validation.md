# Initial validation

## Cloud proxy compatibility validation

2026-10-11, managed Linux cloud environment, Python 3.12.

- `python3 -m unittest discover -s tests -v`: all 28 tests passed with socket access. New regressions exercise a real environment-selected proxy, redirect refusal and response limits through that proxy, direct lab traffic with an empty `NO_PROXY`, and cloud/local adapter proxy selection.
- `python3 -m redwake demo --backend ollama --model gpt-oss:120b`: run `a5ad25dba4d8` completed with default budgets through the required environment proxy, using the configured credential and default TLS verification. Both private resources were classified `vulnerable`; the public control was `public_allowed`. Six lab probes and six model calls recorded 4,049 input tokens and 382 output tokens, with complete provider usage.

The transport previously disabled environment proxies for every request. Only Ollama Cloud now opts into standard proxy inheritance; local Ollama and lab probes remain direct. The live report and evidence are saved under `.redwake/reports/a5ad25dba4d8/` in this workspace. Socket-based tests and the demo required running outside the command sandbox, which disallows socket creation.

## Original validation

2026-10-10, macOS, Python 3.9.6.

- `python3 -m unittest discover -s tests -v`: 26 tests passed, including missing-check recovery and tool-call transcript preservation.
- `python3 -m redwake evaluate --repeat 3`: 12/12 lab runs matched expected outcomes.
- `python3 -m redwake replay b1a0f456b5b1`: report regenerated from saved evidence.

| Lab behaviour | Runs | Private resource verdicts per run | Public resource verdict |
|---|---:|---|---|
| Vulnerable | 3 | 2 vulnerable | public_allowed |
| Fixed, 403 denial | 3 | 2 protected | public_allowed |
| Fixed, 404 concealment | 3 | 2 protected | public_allowed |
| Broken, 503 outage | 3 | 2 inconclusive | inconclusive |

Tests exercise real loopback HTTP, redirect refusal, response-size limits, path/origin scope checks, evidence controls, interruption/resumption, persisted request budgets, token/call/time limits, failed-call reservations, mocked provider payloads and offline report replay.

The model-loop regression cases verify that an early finish prompts only the remaining checks, a failed owner control is retried, conclusive coverage completes at the exact request/model/token allowance, and unresolved coverage stops at its budget without extra provider calls. These cases use controlled model responses against the real HTTP lab.

Run `98e26ef93957` exposed an execution queue that shared the assistant message's tool-call list. Removing executed work erased the calls from the transcript, leaving tool responses without their originating calls. The queue now owns a separate list. A regression drives the production Ollama adapter through two real probes, unexecuted result claims, an explicit recovery prompt, and the remaining four real probes; it completes in four mocked provider calls. Another verifies that tool calls remain in subsequent provider requests and saved SQLite messages after execution. The exhausted original run is retained as recorded; it is not relabelled completed.

Loopback servers required execution outside the desktop filesystem sandbox; the lab remained bound to `127.0.0.1` on ephemeral ports.

At initial validation, live Ollama inference was not run: `OLLAMA_API_KEY` was absent and the local server was not listening on port 11434. The model loop and adapter tests use controlled responses. Subsequent user-executed cloud runs have now been checked against saved evidence; see the [first live model comparison](model-comparison.md). Repeated fixture runs are not independent vulnerability classes.
