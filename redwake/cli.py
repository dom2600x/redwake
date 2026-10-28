import argparse
import fcntl
import json
import sys
from pathlib import Path

from .lab import MODES, lab
from .contracts import SCENARIOS, expected_verdicts
from .providers import Ollama
from .guidance import discovery_scenario
from .report import write_report
from .runner import DEFAULT_LIMITS, DISCOVERY_LIMITS, assess, investigate, score
from .store import Store


def positive(value):
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("Must be a positive integer")
    return number


def main(argv=None):
    parser = argparse.ArgumentParser(description="Redwake: evidence-first API authorisation lab")
    parser.add_argument("--db", default=".redwake/runs.sqlite3")
    parser.add_argument("--reports", default=".redwake/reports")
    commands = parser.add_subparsers(dest="command", required=True)
    demo = commands.add_parser("demo", help="Investigate an ephemeral local lab")
    demo.add_argument("--scenario", choices=SCENARIOS, default="classic")
    demo.add_argument("--mode", choices=MODES, default="vulnerable")
    demo.add_argument("--backend", choices=("baseline", "ollama"), default="baseline")
    demo.add_argument("--model", default="gpt-oss:120b")
    demo.add_argument("--endpoint", choices=("https://ollama.com", "http://127.0.0.1:11434"), default="https://ollama.com")
    for name in DEFAULT_LIMITS:
        demo.add_argument("--max-" + name.replace("_", "-"), type=positive, default=None)
    resume = commands.add_parser("resume", help="Resume saved work with its original budgets")
    resume.add_argument("run_id")
    replay = commands.add_parser("replay", help="Regenerate a report from saved evidence, offline")
    replay.add_argument("run_id")
    evaluate = commands.add_parser("evaluate", help="Evaluate the scripted baseline across four lab behaviours")
    evaluate.add_argument("--scenario", choices=SCENARIOS, default="classic")
    evaluate.add_argument("--repeat", type=positive, default=1)
    args = parser.parse_args(argv)
    default_limits = DISCOVERY_LIMITS if discovery_scenario(getattr(args, "scenario", "classic")) else DEFAULT_LIMITS
    Path(args.db).parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(str(args.db) + ".lock", "w") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            store = Store(args.db)
            try:
                if args.command == "replay":
                    print(write_report(store.load(args.run_id), args.reports).resolve())
                    return 0
                if args.command == "evaluate":
                    rows = []
                    for repetition in range(args.repeat):
                        for mode in MODES:
                            config = {"backend": "baseline", "mode": mode, "scenario": args.scenario,
                                      "limits": dict(default_limits)}
                            state = store.create(config)
                            with lab(mode, args.scenario) as origin:
                                investigate(store, state, origin)
                            verdicts = [r["verdict"] for r in assess(state["evidence"], args.scenario)]
                            expected = expected_verdicts(mode, args.scenario)
                            rows.append({"scenario": args.scenario, "mode": mode, "repeat": repetition + 1, "run_id": state["id"],
                                         "metrics": dict(score(state["evidence"], mode, args.scenario),
                                                         requests=state["requests"], model_calls=state["model_calls"],
                                                         input_tokens=state["input_tokens"], output_tokens=state["output_tokens"],
                                                         seconds=state["elapsed"], usage_complete=state["usage_complete"]),
                                         "verdicts": verdicts, "passed": verdicts == expected and state["status"] == "completed"})
                            write_report(state, args.reports)
                    output = Path(args.reports) / "evaluation.json"
                    output.write_text(json.dumps(rows, indent=2) + "\n")
                    print("%d/%d lab runs passed. %s" % (sum(r["passed"] for r in rows), len(rows), output.resolve()))
                    return 0 if all(r["passed"] for r in rows) else 1
                if args.command == "resume":
                    state = store.load(args.run_id)
                    config = state["config"]
                else:
                    config = {"backend": args.backend, "mode": args.mode, "model": args.model,
                              "endpoint": args.endpoint, "scenario": args.scenario, "limits": {
                                  k: getattr(args, "max_" + k) or default_limits[k] for k in DEFAULT_LIMITS}}
                    state = None
                provider = Ollama(config["model"], config["endpoint"]) if config["backend"] == "ollama" else None
                if state is None:
                    state = store.create(config)
                print("Run: " + state["id"], flush=True)
                with lab(config["mode"], config.get("scenario", "classic")) as origin:
                    investigate(store, state, origin, provider)
                print(write_report(state, args.reports).resolve())
                print("Status: " + state["status"])
                return 0 if state["status"] == "completed" else 2
            finally:
                store.close()
    except (ValueError, OSError) as exc:
        print("redwake: " + str(exc), file=sys.stderr)
        return 2
