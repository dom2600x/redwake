from collections import Counter
from contextlib import contextmanager, redirect_stdout
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from redwake.comparison import PROFILES, experiment_controls
from redwake.contracts import expected_verdicts, navigation_for, resources_for
from redwake.discovery_suite import (TOPOLOGY_FIXTURES, aggregate, config_for,
                                     controls_for, main, plan)
from redwake.lab import lab, allowed_paths
from redwake.providers import initial_messages
from redwake.runner import investigate
from redwake.transport import probe
from redwake.store import Store
from redwake.verifier import assess, discovery_coverage
from scripts.export_experiment import export_bundle
from scripts.verify_experiments import verify_bundle
from test_discovery_suite import LinkModel


class TopologyTests(unittest.TestCase):
    def test_graphs_differ_in_depth_and_branching_with_matched_navigation_cost(self):
        control = navigation_for('discovery_links')
        deep = navigation_for('discovery_deep')
        branch = navigation_for('discovery_branch')
        project = '/api/projects/prj_a5'
        self.assertEqual(len(control), 4)
        self.assertEqual(len(deep), 6)
        self.assertEqual(len(branch), 6)
        self.assertEqual(len(control[project]['body']['links']), 1)
        self.assertEqual(len(branch[project]['body']['links']), 2)
        hub = deep[project]['body']['links']['navigation']
        self.assertIn(hub, deep)
        self.assertIn(deep[hub]['body']['links']['records'], deep)
        for scenario in TOPOLOGY_FIXTURES:
            self.assertEqual(resources_for(scenario), resources_for('discovery'))
            self.assertNotIn('/api/projects/prj_a5/records', allowed_paths(scenario))

    def test_graph_guidance_is_explicit_equal_and_keeps_historical_controls_unchanged(self):
        for profile in PROFILES.values():
            original = experiment_controls(profile)
            self.assertEqual(controls_for(profile, 1), original)
            graph = controls_for(profile, 2)
            self.assertEqual(graph['guidance_variant'], 'graph')
            self.assertNotEqual(original['initial_messages_sha256'], graph['initial_messages_sha256'])
            for scenario in TOPOLOGY_FIXTURES:
                self.assertEqual(graph['initial_messages'], initial_messages(scenario, profile.prompt_variant, 'graph'))
                text = json.dumps(graph['initial_messages'])
                for path in allowed_paths(scenario) - {'/api/projects'}:
                    self.assertNotIn(path, text)
        with self.assertRaises(ValueError): initial_messages('classic', guidance_variant='graph')

    def test_baseline_and_link_model_complete_both_new_graphs_at_twenty_requests(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'runs.db')
            try:
                for scenario in TOPOLOGY_FIXTURES:
                    for mode in ('vulnerable', 'fixed'):
                        for backend in ('baseline', 'ollama'):
                            slot = dict(experiment_profile='sequential', model='baseline' if backend == 'baseline' else 'gpt-oss:120b',
                                        scenario=scenario, mode=mode)
                            state = store.create(config_for(slot, 2))
                            with self.subTest(scenario=scenario, mode=mode, backend=backend), lab(mode, scenario) as origin:
                                investigate(store, state, origin, LinkModel() if backend == 'ollama' else None)
                            self.assertEqual(state['requests'], 18 if scenario == 'discovery_links' else 20)
                            self.assertEqual(state['status'], 'completed')
                            self.assertEqual(state['messages'][:2], state['config']['initial_messages'])
                            self.assertEqual([r['verdict'] for r in assess(state['evidence'], scenario)], expected_verdicts(mode, scenario))
                            self.assertTrue(discovery_coverage(state['evidence'], scenario))
            finally: store.close()

    def test_three_repeats_counterbalance_positions_inside_every_condition(self):
        slots = plan(3, 2)
        self.assertEqual(len(slots), 216)
        self.assertEqual(sum(s['model'] == 'baseline' for s in slots), 54)
        for scenario in TOPOLOGY_FIXTURES:
            for mode in ('vulnerable', 'fixed'):
                for profile in PROFILES:
                    rows = [s for s in slots if s['scenario'] == scenario and s['mode'] == mode and s['experiment_profile'] == profile]
                    self.assertEqual(Counter(s['profile_position'] for s in rows), {1:4, 2:4, 3:4})
                    for model in ('gpt-oss:120b', 'nemotron-3-super', 'nemotron-3-ultra'):
                        self.assertEqual({s['model_position'] for s in rows if s['model'] == model}, {1,2,3})

    def test_new_navigation_nodes_remain_account_specific(self):
        for scenario in ('discovery_deep', 'discovery_branch'):
            with self.subTest(scenario=scenario), lab('fixed', scenario) as origin:
                for path, route in navigation_for(scenario).items():
                    other = 'bob' if route['actor'] == 'alice' else 'alice'
                    response = probe(origin, other, path, scenario=scenario)
                    self.assertEqual(response['status'], 404)
                    self.assertNotIn('links', response['body'])

    def test_resume_retains_graph_guidance_fixture_and_consumed_reservations(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'runs.db')
            try:
                slot = dict(experiment_profile='sequential', model='gpt-oss:120b',
                            scenario='discovery_deep', mode='vulnerable')
                state = store.create(config_for(slot, 2))
                count = [0]
                def interrupt(*args, **kwargs):
                    count[0] += 1
                    if count[0] == 2: raise KeyboardInterrupt()
                    return probe(*args, **kwargs)
                with lab('vulnerable', 'discovery_deep') as origin, patch('redwake.runner.probe', side_effect=interrupt):
                    investigate(store, state, origin, LinkModel())
                restored = store.load(state['id'])
                with lab('vulnerable', 'discovery_deep') as origin:
                    investigate(store, restored, origin, LinkModel())
                self.assertEqual(restored['config'], state['config'])
                self.assertEqual(restored['status'], 'completed')
                self.assertEqual(restored['requests'], 21)
                self.assertEqual(restored['messages'][:2], controls_for(PROFILES['sequential'], 2)['initial_messages'])
            finally: store.close()

    def test_topology_suite_exports_and_rejects_changed_graph_guidance(self):
        @contextmanager
        def unused_lab(*args): yield 'unused'
        def stop(store, state, *args):
            state.update(status='stopped', reason='Model-call budget exhausted',
                         messages=state['config']['initial_messages'])
            store.save(state)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); source = root / 'suite'
            with patch('redwake.discovery_suite.lab', unused_lab), patch('redwake.discovery_suite.Ollama', return_value=object()), patch(
                    'redwake.discovery_suite.investigate', side_effect=stop), redirect_stdout(io.StringIO()):
                main(['--topologies', '--repeat', '1', '--directory', str(source)])
            report = root / 'report.md'; report.write_text('Test bundle; no inference.')
            export_bundle(source, root / 'bundle', report)
            self.assertEqual(verify_bundle(root / 'bundle')['runs'], 72)
            batch = json.loads((source / 'comparison.json').read_text())
            self.assertEqual(batch['suite_version'], 2)
            self.assertEqual(batch['kind'], 'topology_discovery')
            batch['treatments']['current']['guidance_variant'] = 'standard'
            (source / 'comparison.json').write_text(json.dumps(batch))
            with self.assertRaisesRegex(ValueError, 'treatments'): export_bundle(source, root / 'bad', report)
