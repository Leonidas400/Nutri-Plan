"""Integration tests for milk potential and the milk floor in the native optimizer."""
import json
import unittest

from services.native_ration import optimize_native
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from support import guelph_payload


class NativeRationTests(unittest.TestCase):
    def test_guelph_first_lactation_keeps_floor_and_constraints(self):
        result = optimize_native(guelph_payload())
        self.assertTrue(result.get('ok'), result.get('message'))
        self.assertEqual(result['status'], 'success')
        self.assertEqual(len(result['constraints']), 11)
        self.assertTrue(all(item['satisfied'] for item in result['constraints']))
        potential = result['milk_potential']
        self.assertGreaterEqual(
            potential['allowed_kg_day'],
            potential['reference_kg_day'] - 1e-4,
        )
        self.assertIn(potential['status'], {'maintained', 'increased'})
        self.assertEqual(result['milk_reference_source'], 'current_production')
        self.assertEqual(result['fixed_inclusions'], [])
        # The HTTP layer requires strict JSON; numpy scalars would break it.
        json.dumps(result, allow_nan=False)

    def test_guelph_multiparous_keeps_floor(self):
        result = optimize_native(guelph_payload(animal_category='multiparous_lactating_cow'))
        self.assertTrue(result.get('ok'), result.get('message'))
        self.assertEqual(len(result['constraints']), 11)
        self.assertGreaterEqual(
            result['milk_potential']['allowed_kg_day'],
            result['milk_potential']['reference_kg_day'] - 1e-4,
        )

    def test_target_below_reference_is_rejected(self):
        result = optimize_native(guelph_payload(reference=30.0))
        self.assertFalse(result['ok'])
        self.assertEqual(result['error_code'], 'milk_target_below_reference')

    def test_exploration_allows_below_reference_targets(self):
        payload = guelph_payload(reference=30.0)
        payload['allow_below_reference'] = True
        result = optimize_native(payload)
        self.assertTrue(result.get('ok'), result.get('message'))
        self.assertFalse(result['milk_floor_enforced'])
        self.assertEqual(result['milk_potential']['status'], 'below_reference')

    def test_missing_reference_falls_back_to_target(self):
        payload = guelph_payload()
        payload.pop('milk_reference_kg_day')
        result = optimize_native(payload)
        self.assertTrue(result.get('ok'), result.get('message'))
        self.assertEqual(result['milk_reference_source'], 'optimization_target_fallback')

    def test_constraints_expose_bounds_supply_and_unit(self):
        result = optimize_native(guelph_payload())
        self.assertTrue(result.get('ok'), result.get('message'))
        by_name = {item['name']: item for item in result['constraints']}
        for item in result['constraints']:
            for field in ('minimum', 'maximum', 'supply', 'unit'):
                self.assertIn(field, item)
        calcium = by_name['calcium_constraint']
        self.assertAlmostEqual(calcium['minimum'], result['requirements']['calcium'], places=6)
        self.assertAlmostEqual(calcium['supply'], calcium['minimum'] + calcium['slack'], places=6)
        self.assertEqual(calcium['unit'], 'g/day')
        upper = by_name['protein_constraint_upper']
        self.assertAlmostEqual(
            upper['maximum'],
            result['requirements']['metabolizable_protein'] * 1.5,
            places=6,
        )

    def test_zero_true_protein_cannot_prove_the_floor(self):
        payload = guelph_payload()
        payload['parameters'] = {**payload['parameters'], 'milk_true_protein': 0}
        result = optimize_native(payload)
        self.assertFalse(result['ok'])
        self.assertIn(result['error_code'], {'milk_potential_unavailable', 'invalid_input'})


if __name__ == '__main__':
    unittest.main()
