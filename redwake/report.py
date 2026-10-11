import json
from pathlib import Path
from .verifier import assess, score


def write_report(state, directory):
    directory = Path(directory) / state["id"]
    directory.mkdir(parents=True, exist_ok=True)
    scenario = state["config"].get("scenario", "classic")
    results = assess(state["evidence"], scenario)
    metrics = dict(score(state["evidence"], state["config"]["mode"], scenario),
                   requests=state["requests"], model_calls=state["model_calls"],
                   input_tokens=state["input_tokens"], output_tokens=state["output_tokens"],
                   seconds=state["elapsed"], usage_complete=state["usage_complete"])
    report = ["# Redwake investigation", "", "Run: `%s`" % state["id"], "",
              "Backend: **%s** · Lab: **%s** · Status: **%s**" % (
                  state["config"]["backend"], state["config"]["mode"], state["status"]), "",
              "Scenario: **%s**" % scenario, "",
              state.get("reason", "Investigation finished."), "",
              "| Resource | Verdict | Evidence |", "|---|---|---|"]
    for result in results:
        report.append("| `%s` | %s | %s |" % (result["path"], result["verdict"],
                                             ", ".join(str(i) for i in result["evidence_ids"])))
    report += ["", "## Fixture score", "",
               "Correct findings: %d. Missed flaws: %d. False positives: %d. Inconclusive cases: %d." % (
                   metrics["correct_findings"], metrics["missed_flaws"], metrics["false_positives"], metrics["inconclusive"]),
               "Scores compare verifier-proven findings with private synthetic expectations; they do not grade model prose.",
               "", "## Usage", "",
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
                                                      "status": state["status"], "scenario": scenario,
                                                      "metrics": metrics}, indent=2) + "\n")
    return directory / "report.md"
