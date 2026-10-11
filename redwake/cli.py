import argparse
import fcntl
import json
import sys
from pathlib import Path

from .lab import MODES, lab
from .providers import Ollama
from .report import write_report
from .runner import DEFAULT_LIMITS, assess, investigate
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
    demo.add_argument("--mode", choices=MODES, default="vulnerable")
    demo.add_argument("--backend", choices=("baseline", "ollama"), default="baseline")
    demo.add_argument("--model", default="gpt-oss:120b")
    demo.add_argument("--endpoint", choices=("https://ollama.com", "http://127.0.0.1:11434"), default="https://ollama.com")
    for name, default in DEFAULT_LIMITS.items():
        demo.add_argument("--max-" + name.replace("_", "-"), type=positive, default=default)
    resume = commands.add_parser("resume", help="Resume saved work with its original budgets")
    resume.add_argument("run_id")
    replay = commands.add_parser("replay", help="Regenerate a report from saved evidence, offline")
    replay.add_argument("run_id")
    evaluate = commands.add_parser("evaluate", help="Evaluate the scripted baseline across four lab behaviours")
    evaluate.add_argument("--repeat", type=positive, default=1)
    args = parser.parse_args(argv)
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
                            config = {"backend": "baseline", "mode": mode, "limits": dict(DEFAULT_LIMITS)}
                            state = store.create(config)
                            with lab(mode) as origin:
                                investigate(store, state, origin)
                            verdicts = [r["verdict"] for r in assess(state["evidence"])]
                            expected = (["inconclusive"] * 3 if mode == "broken" else
                                        ["vulnerable" if mode == "vulnerable" else "protected"] * 2 + ["public_allowed"])
                            rows.append({"mode": mode, "repeat": repetition + 1, "run_id": state["id"],
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
                              "endpoint": args.endpoint, "limits": {
                                  k: getattr(args, "max_" + k) for k in DEFAULT_LIMITS}}
                    state = None
                provider = Ollama(config["model"], config["endpoint"]) if config["backend"] == "ollama" else None
                if state is None:
                    state = store.create(config)
                print("Run: " + state["id"], flush=True)
                with lab(config["mode"]) as origin:
                    investigate(store, state, origin, provider)
                print(write_report(state, args.reports).resolve())
                print("Status: " + state["status"])
                return 0 if state["status"] == "completed" else 2
            finally:
                store.close()
    except (ValueError, OSError) as exc:
        print("redwake: " + str(exc), file=sys.stderr)
        return 2
