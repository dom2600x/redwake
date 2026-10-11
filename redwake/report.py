import json
from pathlib import Path
from .runner import assess


def write_report(state, directory):
    directory = Path(directory) / state["id"]
    directory.mkdir(parents=True, exist_ok=True)
    results = assess(state["evidence"])
    report = ["# Redwake investigation", "", "Run: `%s`" % state["id"], "",
              "Backend: **%s** · Lab: **%s** · Status: **%s**" % (
                  state["config"]["backend"], state["config"]["mode"], state["status"]), "",
              state.get("reason", "Investigation finished."), "",
              "| Resource | Verdict | Evidence |", "|---|---|---|"]
    for result in results:
        report.append("| `%s` | %s | %s |" % (result["path"], result["verdict"],
                                             ", ".join(str(i) for i in result["evidence_ids"])))
    report += ["", "## Usage", "",
               "Requests reserved: %d. Model calls reserved: %d. Recorded input/output tokens: %d/%d." % (
                   state["requests"], state["model_calls"], state["input_tokens"], state["output_tokens"]),
               "Output tokens reserved: %d. Recorded active time: %.2fs." % (
                   state["reserved_output_tokens"], state["elapsed"]),
               "Provider usage complete: %s. Dollar cost is not available from this harness." % state["usage_complete"],
               "", "## Interpretation", "",
               "A vulnerable verdict requires the private record to be returned to both its owner and another actor. "
               "Protected means the tested cross-account read was denied with an owner success control. "
               "Inconclusive never means secure. These results cover only the listed synthetic GET cases.",
               "", "## Evidence", "",
               "Requests are GETs against an ephemeral 127.0.0.1 lab. Actor aliases select synthetic lab credentials. "
               "The adjacent evidence.json contains the captured responses; replay performs no network requests.", ""]
    for e in state["evidence"]:
        report += ["### Evidence %d" % e["id"], "", "```json", json.dumps(e, indent=2), "```", ""]
    (directory / "report.md").write_text("\n".join(report))
    (directory / "evidence.json").write_text(json.dumps(state["evidence"], indent=2) + "\n")
    (directory / "result.json").write_text(json.dumps({"run_id": state["id"], "results": results,
                                                      "status": state["status"]}, indent=2) + "\n")
    return directory / "report.md"
