import copy
from collections import Counter
from contextlib import contextmanager, redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from redwake.comparison import PROFILES
from redwake.contracts import discovery_layout, expected_verdicts, resources_for
from redwake.discovery_suite import (FIXTURES, PROFILE_NAMES, aggregate, config_for,
                                     main, plan, suite_row, verify_comparison)
from redwake.lab import allowed_paths, lab
from redwake.providers import initial_messages
from redwake.runner import DISCOVERY_LIMITS, discovery_checks, investigate
from redwake.store import Store
from redwake.transport import probe
from redwake.verifier import assess, discovery_coverage
from scripts.export_experiment import export_bundle
from scripts.verify_experiments import verify_bundle


class LinkModel:
    def chat(self, messages, output_limit, timeout):
        evidence = [json.loads(m['content']) for m in messages if m['role'] == 'tool']
        checks = discovery_checks(evidence)
        return dict(message=dict(role='assistant', tool_calls=[
            dict(function=dict(name='probe', arguments=args)) for args in checks]),
            prompt_eval_count=10, eval_count=10)


class SuiteTests(unittest.TestCase):
    def test_profile_order_balanced_in_pilot_and_each_condition_over_three_repeats(self):
        pilot = plan(1)
        self.assertEqual(len(pilot), 72)
        self.assertEqual(sum(s['model'] == 'baseline' for s in pilot), 18)
        for profile in PROFILE_NAMES:
            blocks = {(s['block'], s['profile_position']) for s in pilot if s['experiment_profile'] == profile}
            self.assertEqual(Counter(position for _, position in blocks), {1: 2, 2: 2, 3: 2})
        full = plan(3)
        for scenario in FIXTURES:
            for mode in ('vulnerable', 'fixed'):
                for profile in PROFILE_NAMES:
                    positions = {s['profile_position'] for s in full if s['scenario'] == scenario
                                 and s['mode'] == mode and s['experiment_profile'] == profile}
                    self.assertEqual(positions, {1, 2, 3})
                    for model in ('gpt-oss:120b', 'nemotron-3-super', 'nemotron-3-ultra'):
                        model_positions = {s['model_position'] for s in full if s['scenario'] == scenario
                                           and s['mode'] == mode and s['experiment_profile'] == profile
                                           and s['model'] == model}
                        self.assertEqual(model_positions, {1, 2, 3})

    def test_variants_preserve_case_semantics_and_initial_prompts(self):
        original = list(resources_for('discovery').values())
        for scenario in FIXTURES:
            self.assertEqual(list(resources_for(scenario).values()), original)
            for profile in PROFILES.values():
                self.assertEqual(initial_messages(scenario, profile.prompt_variant),
                                 initial_messages('discovery', profile.prompt_variant))
                text = json.dumps(initial_messages(scenario, profile.prompt_variant))
                for path in resources_for(scenario): self.assertNotIn(path, text)
        self.assertNotEqual(set(resources_for('discovery_ids')), set(resources_for('discovery')))
        layout = discovery_layout('discovery_links')
        self.assertNotIn('/api/projects/prj_a5/records', allowed_paths('discovery_links'))
        self.assertIn(layout['collection_paths']['alice'], allowed_paths('discovery_links'))

    def test_baselines_and_link_model_cover_every_variant_without_scope_expansion(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'runs.db')
            try:
                for scenario in FIXTURES:
                    for mode in ('vulnerable', 'fixed'):
                        for backend in ('baseline', 'ollama'):
                            state = store.create(dict(scenario=scenario, mode=mode, backend=backend,
                                                      limits=dict(DISCOVERY_LIMITS)))
                            with self.subTest(scenario=scenario, mode=mode, backend=backend), lab(mode, scenario) as origin:
                                investigate(store, state, origin, LinkModel() if backend == 'ollama' else None)
                            self.assertEqual(state['status'], 'completed')
                            self.assertEqual(state['requests'], 18)
                            self.assertEqual([r['verdict'] for r in assess(state['evidence'], scenario)],
                                             expected_verdicts(mode, scenario))
                            self.assertTrue(discovery_coverage(state['evidence'], scenario))
                self.assertFalse(discovery_coverage(state['evidence'], 'discovery_ids'))
            finally:
                store.close()
        with self.assertRaises(ValueError):
            probe('http://127.0.0.1:1234', 'alice', '/api/projects/prj_a5/records', scenario='discovery_links')

    def make_stopped_suite(self, directory):
        @contextmanager
        def unused_lab(*args): yield 'unused'
        def stop(store, state, *args):
            state.update(status='stopped', reason='Model-call budget exhausted',
                         messages=initial_messages(state['config']['scenario'], state['config']['prompt_variant']))
            store.save(state)
        with patch('redwake.discovery_suite.lab', unused_lab), patch(
                'redwake.discovery_suite.investigate', side_effect=stop), patch(
                'redwake.discovery_suite.Ollama', return_value=object()), redirect_stdout(io.StringIO()):
            self.assertEqual(main(['--directory', str(directory)]), 0)
        return json.loads((directory / 'comparison.json').read_text())

    def test_all_failed_slots_export_and_verify_with_controls_and_order_intact(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'source'
            batch = self.make_stopped_suite(source)
            report = root / 'report.md'; report.write_text('Fixture suite test, no inference.')
            export_bundle(source, root / 'bundle', report)
            self.assertEqual(verify_bundle(root / 'bundle')['runs'], 72)
            store = Store(source / 'runs.sqlite3')
            try:
                states = {r['run_id']: store.load(r['run_id']) for r in batch['rows']}
            finally: store.close()
            self.assertEqual(len(verify_comparison(batch, states)), 72)
            for mutation in ('omit', 'prompt', 'fixture', 'order'):
                changed = copy.deepcopy(batch)
                altered = copy.deepcopy(states)
                if mutation == 'omit': changed['rows'].pop()
                if mutation == 'prompt': altered[changed['rows'][0]['run_id']]['config']['initial_messages'][0]['content'] = 'changed'
                if mutation == 'fixture': altered[changed['rows'][0]['run_id']]['config']['scenario'] = 'discovery_ids'
                if mutation == 'order': changed['rows'][0]['profile_position'] = 3
                changed['summary'] = aggregate(changed['rows'])
                with self.subTest(mutation=mutation), self.assertRaises(ValueError): verify_comparison(changed, altered)
            with self.assertRaises(FileExistsError): main(['--directory', str(source)])

    def test_setup_errors_are_retained_without_arbitrary_text(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'suite'
            @contextmanager
            def broken_lab(*args):
                raise RuntimeError('PRIVATE_SETUP_SENTINEL')
                yield 'unused'
            with patch('redwake.discovery_suite.Ollama', side_effect=RuntimeError('PRIVATE_SETUP_SENTINEL')), patch(
                    'redwake.discovery_suite.lab', broken_lab), redirect_stdout(io.StringIO()):
                main(['--directory', str(source)])
            text = (source / 'comparison.json').read_text()
            self.assertNotIn('PRIVATE_SETUP_SENTINEL', text)
            batch = json.loads(text)
            self.assertEqual(len(batch['rows']), 72)
            self.assertTrue(all(r['stop_category'] == 'harness_failure' for r in batch['rows']))
