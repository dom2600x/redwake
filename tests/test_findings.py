import copy
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from redwake.cli import main
from redwake.artifacts import export_run, verify_bundle
from redwake.findings import evaluate, export_proof, validate_contract, inventory
from redwake.lab import lab
from redwake.runner import investigate, DEFAULT_LIMITS
from redwake.store import Store


class FindingTests(unittest.TestCase):
    def setUp(self):
        self.contract = dict(version=1, actors=['owner', 'reader', 'guest'], rules=[dict(
            id='private-read', path='/v2/items/7', owner='owner', allowed_actors=['owner'],
            identity={'/item/id': 7, '/item/secret': 'record-seven'})])
        self.evidence = [dict(id=i, actor=a, path='/v2/items/7', status=200,
                              body={'item': {'id': 7, 'secret': 'record-seven'}})
                         for i, a in ((1, 'owner'), (2, 'reader'))]
        self.finding = dict(rule_id='private-read', actor='reader', evidence_ids=[1, 2],
                            impact='unauthorized_record_read', reproduction=[
                                dict(method='GET', actor=e['actor'], path=e['path'], evidence_id=e['id'])
                                for e in self.evidence])

    def test_nonfixture_policy_and_nested_identity_prove_submitted_read(self):
        result = evaluate(self.contract, self.finding, self.evidence)
        self.assertTrue(result['accepted'])
        self.assertEqual(result['impact'], 'unauthorized_record_read')
        # No submission means no automatically generated finding.
        with self.assertRaises(ValueError): evaluate(self.contract, {}, self.evidence)

    def test_public_and_shared_access_are_not_findings(self):
        for allowed in (['owner', 'reader'], ['owner', 'reader', 'guest']):
            self.contract['rules'][0]['allowed_actors'] = allowed
            self.assertEqual(evaluate(self.contract, self.finding, self.evidence)['reason'], 'access_permitted')

    def test_failed_controls_wrong_record_denials_and_outages_are_not_proof(self):
        for index, status, body in ((0, 503, {}), (1, 403, {}), (1, 404, {}), (1, 503, {}), (1, 200, {'message':'ok'})):
            with self.subTest(index=index,status=status):
                evidence = copy.deepcopy(self.evidence); evidence[index].update(status=status, body=body)
                self.assertFalse(evaluate(self.contract, self.finding, evidence)['accepted'])
        evidence = copy.deepcopy(self.evidence); evidence[1]['body']['item']['id'] = True
        self.assertFalse(evaluate(self.contract, self.finding, evidence)['accepted'])

    def test_unknown_or_misattributed_evidence_and_stale_success_are_rejected(self):
        f = copy.deepcopy(self.finding); f['evidence_ids'] = [1,99]
        self.assertEqual(evaluate(self.contract,f,self.evidence)['reason'],'unknown_evidence')
        evidence = copy.deepcopy(self.evidence); evidence[1]['actor']='guest'
        self.assertEqual(evaluate(self.contract,self.finding,evidence)['reason'],'evidence_mismatch')
        evidence = copy.deepcopy(self.evidence); evidence.append(dict(evidence[1],id=3,status=403,body={}))
        self.assertEqual(evaluate(self.contract,self.finding,evidence)['reason'],'superseded_evidence')

    def test_claimed_impact_and_reproduction_are_bounded(self):
        f = copy.deepcopy(self.finding); f['impact']='account_takeover'
        self.assertEqual(evaluate(self.contract,f,self.evidence)['reason'],'unsupported_impact')
        f = copy.deepcopy(self.finding); f['reproduction'][1]['path']='/v2/items/8'
        self.assertEqual(evaluate(self.contract,f,self.evidence)['reason'],'reproduction_mismatch')

    def test_contract_rejects_duplicate_rules_invalid_paths_and_empty_identity(self):
        for change in (lambda c:c['rules'].append(copy.deepcopy(c['rules'][0])),
                       lambda c:c['rules'][0].update(path='https://other.test/item'),
                       lambda c:c['rules'][0].update(path='/v2/../secret'),
                       lambda c:c['rules'][0].update(identity={}),
                       lambda c:c['rules'][0].update(allowed_actors=['reader'])):
            c=copy.deepcopy(self.contract); change(c)
            with self.assertRaises(ValueError): validate_contract(c)

    def test_portable_proof_offline_rechecks_accepted_and_rejected_submissions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); store=Store(root/'db')
            try:
                state=store.create(dict(backend='baseline',mode='vulnerable',limits=DEFAULT_LIMITS))
                with lab('vulnerable') as origin: investigate(store,state,origin)
            finally: store.close()
            export_run(state,root/'source')
            contract=dict(version=1, actors=['alice','bob'],rules=[dict(id='document',path='/api/documents/101',
                owner='alice',allowed_actors=['alice'],identity={'/owner':'alice','/data':'alice-private-document'})])
            finding=dict(rule_id='document',actor='bob',evidence_ids=[1,2],impact='unauthorized_record_read',
                reproduction=[dict(method='GET',actor=a,path='/api/documents/101',evidence_id=i) for a,i in [('alice',1),('bob',2)]])
            with patch('urllib.request.OpenerDirector.open',side_effect=AssertionError('network')):
                self.assertTrue(export_proof(root/'source',contract,finding,root/'proof')['accepted'])
                self.assertTrue(verify_bundle(root/'proof')['finding']['accepted'])
                finding['impact']='account_takeover'
                self.assertFalse(export_proof(root/'source',contract,finding,root/'rejected')['accepted'])
                self.assertFalse(verify_bundle(root/'rejected')['finding']['accepted'])
            finding['impact']='unauthorized_record_read'
            (root/'contract.json').write_text(json.dumps(contract))
            (root/'finding.json').write_text(json.dumps(finding))
            with redirect_stdout(io.StringIO()):
                self.assertEqual(main(['--db',str(root/'absent'/'db'),'validate-finding',
                    '--contract',str(root/'contract.json'),'--finding',str(root/'finding.json'),
                    '--bundle',str(root/'source'),'--output',str(root/'cli-proof')]),0)
                self.assertEqual(main(['verify',str(root/'cli-proof')]),0)
            self.assertFalse((root/'absent').exists())
            result=root/'proof'/'validation.json'; result.write_text('{}')
            with self.assertRaises(ValueError): verify_bundle(root/'proof')
            manifest_path=root/'proof'/'manifest.json'
            manifest=json.loads(manifest_path.read_text())
            manifest['files']=inventory(root/'proof')
            manifest_path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, 'validation differs'):
                verify_bundle(root/'proof')
