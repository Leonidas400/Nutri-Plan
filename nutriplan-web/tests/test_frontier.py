"""Tests for the cost x milk frontier summary returned by the API."""
import json
import unittest
import sys
from pathlib import Path

from services.milk_targets import formulate

sys.path.insert(0, str(Path(__file__).resolve().parent))
from support import guelph_payload  # noqa: E402


class FrontierTests(unittest.TestCase):
    def test_integrated_scan_returns_non_dominated_frontier(self):
        payload = guelph_payload(evaluate_milk_targets=True)
        result = formulate(payload)
        self.assertTrue(result.get('ok'), result.get('message'))
        frontier = result['frontier']
        self.assertTrue(frontier)
        dominated = [row for row in result['target_results'] if row.get('non_dominated')]
        self.assertEqual(len(frontier), len(dominated))
        for row in frontier:
            self.assertIn('milk_target', row)
            self.assertIn('cost_day', row)
            self.assertIn('milk_allowed', row)
        json.dumps(result, allow_nan=False)

    def test_fixed_target_contract_also_returns_frontier(self):
        payload = guelph_payload(reference=25.062)
        payload['milk_targets'] = [25.062, 27.062]
        result = formulate(payload)
        self.assertTrue(result.get('ok'), result.get('message'))
        self.assertEqual(len(result['target_results']), 2)
        self.assertTrue(result['frontier'])


if __name__ == '__main__':
    unittest.main()
