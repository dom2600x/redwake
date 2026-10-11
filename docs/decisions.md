# Initial engineering decisions

Date: 2026-10-10

The project starts as a Python CLI with no runtime dependencies. This makes the first lab runnable on the existing Mac without provisioning infrastructure. SQLite retains investigation state. A standard-library HTTP lab gives us actual requests and responses while keeping all records synthetic.

The lab-only target is an intentional first boundary. Scope is enforced by code, not model instructions. Models see actor aliases and a resource access contract. They never receive lab bearer credentials or permission to choose an origin. An independent verifier checks owner controls and exact record markers; it does not trust the model's conclusion.

The first evaluation includes public content and server failure to catch two misleading interpretations: treating any cross-account success as a vulnerability, and treating any failure as protection. The suite is a harness baseline, not evidence that either hosted model can conduct novel investigations.

Ollama is an interchangeable model backend. Model calls reserve allowances before execution to make retries and resumption conservative. Actual usage is recorded when the provider returns it. Dollar accounting is deferred until there is a trustworthy account usage or pricing source; hard dollar caps cannot be inferred from output tokens alone.

No cloud model call was needed to build or validate the initial baseline. Live model validation depends on a configured Ollama API key or a running, configured local Ollama server.
