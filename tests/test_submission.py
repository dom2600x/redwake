import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from redwake.artifacts import export_run, verify_bundle
from redwake.lab import lab
from redwake.runner import investigate, DEFAULT_LIMITS
from redwake.store import Store
from redwake.submission import recheck, guidance, SUBMISSION_TOOLS


def call(name, args):
    return {'function': {'name': name, 'arguments': args}}


class Model:
    def __init__(self, turns): self.turns = iter(turns); self.histories = []
    def chat(self, messages, *args):
        self.histories.append(copy.deepcopy(messages))
        return dict(message=dict(role='assistant', tool_calls=next(self.turns)), prompt_eval_count=10, eval_count=10)


class SubmissionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name); self.store=Store(self.root/'db'); self.addCleanup(self.store.close)
        self.contract=json.loads(Path('examples/findings/contract.json').read_text())
        self.finding=json.loads(Path('examples/findings/finding.json').read_text())
        self.probes=[call('probe',dict(actor=a,path='/api/documents/101')) for a in ('alice','bob')]

    def state(self, **limits):
        return self.store.create(dict(backend='ollama',mode='vulnerable',access_contract=self.contract,
                                     limits=dict(DEFAULT_LIMITS,**limits)))

    def test_model_submits_after_exact_request_cap_and_exports_offline(self):
        model=Model([self.probes,[call('submit_finding',self.finding),call('finish_investigation',{})]])
        state=self.state(requests=2)
        with lab('vulnerable') as origin: investigate(self.store,state,origin,model)
        self.assertEqual(state['status'],'completed'); self.assertEqual(state['requests'],2)
        self.assertEqual(state['model_calls'],2)
        self.assertTrue(recheck(state)[0]['current_validation']['accepted'])
        self.assertNotIn('alice-private-document',json.dumps(guidance(self.contract)))
        with patch('urllib.request.OpenerDirector.open',side_effect=AssertionError('network')):
            export_run(state,self.root/'bundle'); verify_bundle(self.root/'bundle')
        self.assertEqual(len(SUBMISSION_TOOLS),3)

    def test_provider_sends_submission_tools_without_changing_default_schema(self):
        from redwake.providers import Ollama, TOOLS
        with patch.dict('os.environ', {'OLLAMA_API_KEY': 'test-key'}), patch(
                'redwake.providers.request_json', return_value=(200, {'message': {'role': 'assistant'}})) as request:
            Ollama('test', tools=SUBMISSION_TOOLS).chat([], 1024, 1)
            self.assertEqual(request.call_args.args[2]['tools'], SUBMISSION_TOOLS)
            Ollama('test').chat([], 1024, 1)
            self.assertEqual(request.call_args.args[2]['tools'], TOOLS)
            self.assertEqual(len(TOOLS), 1)

    def test_rejected_claim_feedback_can_be_corrected(self):
        bad=dict(self.finding,evidence_ids=[1,99])
        model=Model([self.probes,[call('submit_finding',bad)],[call('submit_finding',self.finding),call('finish_investigation',{})]])
        state=self.state()
        with lab('vulnerable') as origin: investigate(self.store,state,origin,model)
        records=recheck(state)
        self.assertFalse(records[0]['validation']['accepted']); self.assertTrue(records[1]['validation']['accepted'])
        self.assertIn('unknown_evidence',model.histories[2][-1]['content'])

    def test_explicit_finish_without_findings_is_not_automatic_detection(self):
        state=self.state()
        with lab('vulnerable') as origin: investigate(self.store,state,origin,Model([self.probes,[call('finish_investigation',{})]]))
        self.assertEqual(recheck(state),[]); self.assertTrue(state['finding_finished'])

    def test_no_finish_exhausts_model_budget_and_resume_keeps_submissions(self):
        state=self.state(model_calls=2)
        with lab('vulnerable') as origin: investigate(self.store,state,origin,Model([self.probes,[call('submit_finding',self.finding)]]))
        self.assertEqual(state['reason'],'Model-call budget exhausted')
        saved=self.store.load(state['id'])
        with lab('vulnerable') as origin: investigate(self.store,saved,origin,Model([]))
        self.assertEqual(saved['model_calls'],2); self.assertEqual(len(recheck(saved)),1)
        changed=copy.deepcopy(saved); changed['submissions'][0]['validation']['accepted']=False
        with self.assertRaises(ValueError): recheck(changed)

    def test_accepted_claim_is_rechecked_after_later_denial(self):
        state=self.state()
        with lab('vulnerable') as origin: investigate(self.store,state,origin,Model([self.probes,[call('submit_finding',self.finding),call('finish_investigation',{})]]))
        state['evidence'].append(dict(state['evidence'][1],id=3,status=403,body={}))
        self.assertTrue(recheck(state)[0]['validation']['accepted'])
        self.assertFalse(recheck(state)[0]['current_validation']['accepted'])
