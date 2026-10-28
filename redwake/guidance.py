"""Public API documentation, independent of verifier fixtures."""

ACTOR_NAMES = ("alice", "bob")
DISCOVERY_SCENARIOS = ("discovery", "discovery_ids", "discovery_links",
                       "discovery_deep", "discovery_branch")


def discovery_scenario(scenario):
    return scenario in DISCOVERY_SCENARIOS


API_GUIDANCE = """Two test accounts, alice and bob, are available through probe(actor, path).
GET /api/projects lists the current account's projects. Project responses link to
record collections. Collections link to record details; details may link to files
or exports. Follow relative API links to discover these resources. Listings are
account-specific. Record representations expose an owner and visibility (private
or public). Compare a known owner's response with the other account's response;
check actual content, and distinguish public sharing and service errors from an
unauthorised read. Only GET requests are supported. Start discovery with both
accounts before testing discovered records across accounts."""

GRAPH_GUIDANCE = """Two test accounts, alice and bob, are available through probe(actor, path).
GET /api/projects lists the current account's projects. Project responses link to
further navigation nodes or record collections. Follow returned relative API links;
a project can have intermediate nodes or multiple collections. Collections link
to record details; details may link to files or exports. Listings are account-specific.
Record representations expose an owner and visibility (private or public).
Compare a known owner's response with the other account's response; check actual
content, and distinguish public sharing and service errors from an unauthorised
read. Only GET requests are supported. Start discovery with both accounts before
testing discovered records across accounts."""


def response_links(body):
    """Read the API's links at any nesting depth, without knowing fixture IDs."""
    found = []
    def visit(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if key == "links" and isinstance(item, dict):
                    found.extend(path for path in item.values() if isinstance(path, str))
                else:
                    visit(item)
        elif isinstance(value, list):
            for item in value:
                visit(item)
    visit(body)
    return list(dict.fromkeys(found))
