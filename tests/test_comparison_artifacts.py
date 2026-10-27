import copy
import unittest
from redwake.comparison import PROFILES, experiment_controls, json_sha256
from scripts.verify_experiments import verify_comparison_controls


class ComparisonControlTests(unittest.TestCase):
    def setUp(self):
        controls = experiment_controls(PROFILES['current'])
        self.batch = dict(controls, limits=PROFILES['current'].limits,
                          endpoint='https://ollama.com', scenario='discovery', repeat=1,
                          modes=['vulnerable'], models=['gpt-oss:120b'], rows=[
                              dict(run_id='a', repeat=1, mode='vulnerable', model='baseline'),
                              dict(run_id='b', repeat=1, mode='vulnerable', model='gpt-oss:120b')])
        self.states = {key: dict(config=copy.deepcopy(self.batch),
                                messages=copy.deepcopy(controls['initial_messages']),
                                model_calls=1, requests=0, status='stopped') for key in ('a', 'b')}

    def test_matching_failed_runs_verify(self):
        verify_comparison_controls(self.batch, self.states)

    def test_rehashed_plan_must_match_executed_prompt(self):
        altered = copy.deepcopy(self.batch['initial_messages'])
        altered[1]['content'] += ' Different advice.'
        self.batch.update(initial_messages=altered, initial_messages_sha256=json_sha256(altered))
        for state in self.states.values():
            state['config'].update(initial_messages=altered, initial_messages_sha256=json_sha256(altered))
        with self.assertRaisesRegex(ValueError, 'Executed prompt'):
            verify_comparison_controls(self.batch, self.states)

    def test_allowance_change_is_detected(self):
        self.states['b']['config']['limits']['model_calls'] += 1
        with self.assertRaisesRegex(ValueError, 'Run controls'):
            verify_comparison_controls(self.batch, self.states)

    def test_baselines_and_failures_cannot_be_omitted(self):
        for index in (0, 1):
            with self.subTest(index=index):
                batch = copy.deepcopy(self.batch)
                removed = batch['rows'].pop(index)
                states = {k: v for k, v in self.states.items() if k != removed['run_id']}
                with self.assertRaisesRegex(ValueError, 'Comparison plan'):
                    verify_comparison_controls(batch, states)

    def test_setup_failure_can_lack_prompt_but_executed_run_cannot(self):
        self.states['b'].update(messages=[], model_calls=0)
        verify_comparison_controls(self.batch, self.states)
        self.states['b']['model_calls'] = 1
        with self.assertRaisesRegex(ValueError, 'lacks its initial prompt'):
            verify_comparison_controls(self.batch, self.states)

    def test_raw_diagnostic_details_cannot_be_published(self):
        self.states['b']['diagnostics'] = [dict(source='provider', category='timeout', detail='secret')]
        with self.assertRaisesRegex(ValueError, 'diagnostic schema'):
            verify_comparison_controls(self.batch, self.states)
