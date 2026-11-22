"""Tests for the discrete milk-target scan built on the native optimizer."""
import json
import unittest

from services.milk_targets import formulate
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from support import guelph_payload


class MilkTargetTests(unittest.TestCase):
    def test_integrated_scan_reports_reference_and_both_sides(self):
        payload = guelph_payload(evaluate_milk_targets=True)
        result = formulate(payload)
        self.assertTrue(result.get('ok'), result.get('message'))
        self.assertEqual(len(result['target_results']), 15)
        reference = result['reference_result']
        highest = result['highest_feasible_result']
        self.assertAlmostEqual(reference['milk_target'], 25.062)
        self.assertGreaterEqual(highest['milk_target'], reference['milk_target'])
        levels = [row['milk_target'] for row in result['target_results']]
        self.assertTrue(any(level < reference['milk_target'] for level in levels))
        self.assertTrue(any(level > reference['milk_target'] for level in levels))
        for row in result['target_results']:
            self.assertIsNotNone(row['milk_allowed'])
            self.assertIn(row['milk_status'], {'maintained', 'increased', 'below_reference', 'unavailable'})
        json.dumps(result, allow_nan=False)

    def test_exploration_returns_feasible_and_dominated_diets(self):
        payload = guelph_payload(evaluate_milk_targets=True)
        payload['explore_alternatives'] = True
        payload['alternative_samples'] = 60
        result = formulate(payload)
        self.assertTrue(result.get('ok'), result.get('message'))
        alternatives = result['alternative_solutions']
        self.assertTrue(alternatives)
        self.assertTrue(any(item['dominated'] for item in alternatives))
        self.assertTrue(result['exploration_frontier'])
        self.assertAlmostEqual(result['milk_target'], 25.062)
        self.assertTrue(result['milk_floor_enforced'])
        json.dumps(result, allow_nan=False)

    def test_beyond_optimum_solutions_are_dominated(self):
        payload = guelph_payload(evaluate_milk_targets=True)
        payload['beyond_optimum_attempts'] = 3
        result = formulate(payload)
        self.assertTrue(result.get('ok'), result.get('message'))
        highest = result['highest_feasible_result']
        beyond = result['beyond_optimum_solutions']
        self.assertTrue(beyond)
        self.assertLessEqual(len(beyond), 6)
        for item in beyond:
            self.assertTrue(item['dominated'])
            self.assertLessEqual(item['milk_allowed'], highest['milk_target'] + 1e-4)
            self.assertGreaterEqual(item['cost_day'], highest['cost_day'] - 1e-4)
        json.dumps(result, allow_nan=False)

    def test_fixed_targets_are_clamped_to_the_reference(self):
        payload = guelph_payload(reference=26.062)
        payload['milk_targets'] = [24, 26.062, 27.062]
        result = formulate(payload)
        self.assertTrue(result.get('ok'), result.get('message'))
        levels = [row['milk_target'] for row in result['target_results']]
        self.assertEqual(levels, [26.062, 27.062])

    def test_reference_is_shared_across_all_targets(self):
        payload = guelph_payload(reference=26.0, evaluate_milk_targets=True)
        result = formulate(payload)
        for row in result['target_results']:
            self.assertAlmostEqual(
                row['milk_floor_margin'],
                row['milk_allowed'] - 26.0,
                places=5,
            )


if __name__ == '__main__':
    unittest.main()
