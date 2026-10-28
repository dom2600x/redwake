"""Private evidence validation and fixture scoring; never used as model guidance."""

import json
from .contracts import resources_for, expected_verdicts
from .guidance import ACTOR_NAMES


def contains_record(observation, resource):
    return bool(observation and observation["status"] == 200
                and isinstance(observation["body"], dict)
                and observation["body"].get("owner") == resource["owner"]
                and observation["body"].get("data") == resource["marker"])


def denied_record(observation, resource):
    return bool(observation and observation["status"] in (403, 404)
                and resource["marker"] not in json.dumps(observation["body"]))


def missing_checks(evidence, scenario="classic"):
    """Return absent or inconclusive observations, including failed owner controls."""
    observations = {(e["actor"], e["path"]): e for e in evidence}
    checks = []
    for path, resource in resources_for(scenario).items():
        for actor in ACTOR_NAMES:
            observation = observations.get((actor, path))
            valid = contains_record(observation, resource)
            if resource["private"] and actor != resource["owner"]:
                valid = valid or denied_record(observation, resource)
            if not valid:
                checks.append({"actor": actor, "path": path})
    return checks


def assess(evidence, scenario="classic"):
    """Only matched successful owner/cross-account responses can prove a leak."""
    observations = {(e["actor"], e["path"]): e for e in evidence}
    results = []
    for path, resource in resources_for(scenario).items():
        owner = observations.get((resource["owner"], path))
        other_actor = next(a for a in ACTOR_NAMES if a != resource["owner"])
        other = observations.get((other_actor, path))

        verdict = "inconclusive"
        if contains_record(owner, resource) and other:
            if resource["private"]:
                if contains_record(other, resource):
                    verdict = "vulnerable"
                elif denied_record(other, resource):
                    verdict = "protected"
            elif contains_record(other, resource):
                verdict = "public_allowed"
        results.append({"path": path, "verdict": verdict,
                        "evidence_ids": [e["id"] for e in (owner, other) if e]})
    return results


def score(evidence, mode, scenario="classic"):
    """Score proven findings against private fixture expectations, including misses."""
    actual = [r["verdict"] for r in assess(evidence, scenario)]
    expected = expected_verdicts(mode, scenario)
    return {
        "correct_findings": sum(a == e == "vulnerable" for a, e in zip(actual, expected)),
        "missed_flaws": sum(e == "vulnerable" and a != e for a, e in zip(actual, expected)),
        "false_positives": sum(a == "vulnerable" and e != a for a, e in zip(actual, expected)),
        "correct_verdicts": sum(a == e for a, e in zip(actual, expected)),
        "inconclusive": actual.count("inconclusive"),
    }


def discovery_coverage(evidence, scenario="discovery"):
    """Coverage means attempted account pairs, not successful access or security."""
    observed = {(e["actor"], e["path"]) for e in evidence}
    return all((actor, path) in observed for path in resources_for(scenario) for actor in ACTOR_NAMES)
