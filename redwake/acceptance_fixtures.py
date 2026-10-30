"""Reserved synthetic acceptance cases; expected outcomes are verifier-only.

These are novel relative to the historical owner-only discovery fixtures, not a
claim that published repository fixtures are secret or training-contamination free.
"""

SCENARIO = 'authorization_acceptance'
# Roles, tenant membership and sharing resolve to an explicit allowed actor set.
# The current finding contract supports record reads, not arbitrary write/role escalation.
RESOURCES = {
    '/api/workspaces/ws_n4/payroll/pay_p8': dict(owner='alice', private=True, marker='payroll-n4-p8', behaviour='vulnerable'),
    '/api/cases/case_j3/notes/note_r6': dict(owner='bob', private=True, marker='confidential-case-j3-r6', behaviour='vulnerable'),
    '/api/workspaces/ws_n4/keys/key_d2': dict(owner='alice', private=True, marker='restricted-key-d2', behaviour='fixed'),
    '/api/cases/case_j3/sealed/seal_t9': dict(owner='bob', private=True, marker='sealed-case-t9', behaviour='concealed'),
    '/api/teams/team_f2/handovers/hand_k5': dict(owner='alice', private=True, allowed_actors=['alice', 'bob'], marker='delegated-handover-k5', behaviour='public'),
    '/api/bulletins/bul_s7': dict(owner='bob', private=False, marker='published-bulletin-s7', behaviour='public'),
    '/api/archives/arc_m3': dict(owner='bob', private=True, marker='archive-m3', behaviour='broken'),
    '/api/workspaces/ws_n4/reports/rep_a6': dict(owner='alice', private=True, marker='financial-report-a6', behaviour='mismatched'),
    '/api/cases/case_j3/exports/exp_q4': dict(owner='bob', private=True, marker='case-export-q4', behaviour='owner_unavailable'),
}
RULE_IDS = ('tenant_payroll', 'confidential_case_note', 'restricted_key', 'sealed_case',
            'delegated_handover', 'published_bulletin', 'archive_record',
            'workspace_report', 'case_export')


def contract():
    return dict(version=1, actors=['alice', 'bob'], rules=[
        dict(id=rule_id, path=path, owner=r['owner'],
             allowed_actors=list(r.get('allowed_actors', [r['owner']] if r['private'] else ['alice', 'bob'])),
             identity={'/owner': r['owner'], '/data': r['marker']})
        for rule_id, (path, r) in zip(RULE_IDS, RESOURCES.items())])


def expected_findings():
    return {(rule_id, 'bob' if r['owner'] == 'alice' else 'alice')
            for rule_id, r in zip(RULE_IDS, RESOURCES.values()) if r['behaviour'] == 'vulnerable'}
