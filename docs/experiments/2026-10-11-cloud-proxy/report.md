# Cloud proxy compatibility validation


2026-10-11, managed Linux cloud environment, Python 3.12.

- `python3 -m unittest discover -s tests -v`: all 28 tests passed with socket access. New regressions exercise a real environment-selected proxy, redirect refusal and response limits through that proxy, direct lab traffic with an empty `NO_PROXY`, and cloud/local adapter proxy selection.
- `python3 -m redwake demo --backend ollama --model gpt-oss:120b`: run `a5ad25dba4d8` completed with default budgets through the required environment proxy, using the configured credential and default TLS verification. Both private resources were classified `vulnerable`; the public control was `public_allowed`. Six lab probes and six model calls recorded 4,049 input tokens and 382 output tokens, with complete provider usage.

The transport previously disabled environment proxies for every request. Only Ollama Cloud now opts into standard proxy inheritance; local Ollama and lab probes remain direct. This historical summary cites run `a5ad25dba4d8`. Its raw state and response files are not included in the uploaded Mac archive or the currently available cloud artifacts. Socket-based tests and the demo required running outside the command sandbox, which disallows socket creation.


## Artifact availability

This is a historical summary only. The original cloud run's artifacts are pending
import, so this report is excluded from retained-bundle verification. Its recorded
metrics and historical test count have not been reverified from raw evidence here.
The [Mac archive](../2026-10-10-mac/report.md) and
[discovery comparison](../2026-10-11-discovery/report.md) have complete retained
evidence bundles.
