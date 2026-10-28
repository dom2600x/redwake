"""Verifier-only synthetic ownership and expected outcomes. Never sent to models."""

from .guidance import DISCOVERY_SCENARIOS, discovery_scenario
RESOURCES = {
    "/api/documents/101": {"owner": "alice", "private": True, "marker": "alice-private-document"},
    "/api/invoices/inv_b7": {"owner": "bob", "private": True, "marker": "bob-private-invoice"},
    "/api/documents/public": {"owner": "alice", "private": False, "marker": "public-handbook"},
}
DISCOVERY_RESOURCES = {
    "/api/records/doc_k4": {"owner": "alice", "private": True, "marker": "quarterly-draft", "behaviour": "vulnerable"},
    "/api/files/file_x9": {"owner": "alice", "private": True, "marker": "draft-attachment", "behaviour": "vulnerable"},
    "/api/records/inv_m8": {"owner": "bob", "private": True, "marker": "supplier-invoice", "behaviour": "fixed"},
    "/api/records/note_q2": {"owner": "bob", "private": True, "marker": "planning-note", "behaviour": "concealed"},
    "/api/records/guide_h6": {"owner": "alice", "private": False, "marker": "team-handbook", "behaviour": "public"},
    "/api/exports/export_z3": {"owner": "bob", "private": True, "marker": "billing-export", "behaviour": "broken"},
}
SCENARIOS = ("classic",) + DISCOVERY_SCENARIOS


def discovery_layout(scenario="discovery"):
    if not discovery_scenario(scenario):
        raise ValueError("Unknown discovery layout")
    projects = {"alice": "prj_c7", "bob": "prj_d2"} if scenario == "discovery_ids" else {
        "alice": "prj_a5", "bob": "prj_b9"}
    collection_paths = ({"alice": "/api/collections/set_l6", "bob": "/api/collections/set_n8"}
                        if scenario == "discovery_links" else
                        {actor: "/api/projects/" + project + "/records" for actor, project in projects.items()})
    return {"projects": projects, "collection_paths": collection_paths}


def resources_for(scenario="classic"):
    if scenario not in SCENARIOS:
        raise ValueError("Unknown lab scenario")
    if scenario == "discovery_ids":
        paths = ("/api/records/doc_r8", "/api/files/file_t4", "/api/records/inv_s3",
                 "/api/records/note_v1", "/api/records/guide_w6", "/api/exports/export_y5")
        return {path: dict(record) for path, record in zip(paths, DISCOVERY_RESOURCES.values())}
    return DISCOVERY_RESOURCES if discovery_scenario(scenario) else RESOURCES


def expected_verdicts(mode, scenario="classic"):
    results = []
    for record in resources_for(scenario).values():
        behaviour = record.get("behaviour", mode)
        if mode == "broken" or behaviour == "broken":
            results.append("inconclusive")
        elif not record["private"]:
            results.append("public_allowed")
        else:
            results.append("vulnerable" if behaviour == "vulnerable" and mode == "vulnerable" else "protected")
    return results
