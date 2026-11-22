"""Unit tests for the NASEM milk-potential metric."""
import unittest

from services.milk_potential import (
    FLOOR_TOLERANCE_KG_DAY, classify_status, evaluate, milk_energy_per_kg,
    resolve_reference,
)


class MilkEnergyTests(unittest.TestCase):
    def test_energy_per_kg_matches_nasem_equation(self):
        expected = 0.0929 * 3.8 + (0.0547 / 0.93) * 3.5 + 0.0395 * 4.65
        self.assertAlmostEqual(milk_energy_per_kg(3.8, 3.5, 4.65), expected, places=12)

    def test_energy_per_kg_rejects_zero_composition(self):
        self.assertEqual(milk_energy_per_kg(0, 0, 0), 0.0)


class StatusTests(unittest.TestCase):
    def test_equal_allowed_is_maintained(self):
        status, margin = classify_status(30.0, 30.0)
        self.assertEqual(status, 'maintained')
        self.assertAlmostEqual(margin, 0.0, places=12)

    def test_clear_gain_is_increased(self):
        status, _ = classify_status(31.0, 30.0)
        self.assertEqual(status, 'increased')

    def test_shortfall_is_below_reference(self):
        status, margin = classify_status(29.9, 30.0)
        self.assertEqual(status, 'below_reference')
        self.assertAlmostEqual(margin, -0.1, places=12)


class ReferenceTests(unittest.TestCase):
    def test_explicit_current_production_wins(self):
        reference, source = resolve_reference({
            'milk_reference_kg_day': '30,5',
            'parameters': {'milk_production': 25},
        })
        self.assertAlmostEqual(reference, 30.5)
        self.assertEqual(source, 'current_production')

    def test_absent_reference_falls_back_to_target(self):
        reference, source = resolve_reference({'parameters': {'milk_production': 25.062}})
        self.assertAlmostEqual(reference, 25.062)
        self.assertEqual(source, 'optimization_target_fallback')

    def test_invalid_reference_is_rejected(self):
        with self.assertRaises(ValueError):
            resolve_reference({'milk_reference_kg_day': -1,
                               'parameters': {'milk_production': 25}})


class UnavailableTests(unittest.TestCase):
    def test_missing_composition_is_unavailable(self):
        result = evaluate([], {'parameters': {}, 'body_weight_kg': 600}, None, None, 25)
        self.assertEqual(result['status'], 'unavailable')
        self.assertEqual(result['reason'], 'missing_milk_composition')
        self.assertTrue(result['margin_kg_day'] is None)

    def test_zero_true_protein_is_unavailable(self):
        animal = {'parameters': {
            'milk_fat': 3.8, 'milk_true_protein': 0, 'milk_lactose': 4.65,
            'milk_production': 25,
        }, 'body_weight_kg': 600}
        result = evaluate([], animal, None, None, 25)
        self.assertEqual(result['status'], 'unavailable')
        self.assertEqual(result['reason'], 'invalid_milk_true_protein')

    def test_floor_tolerance_is_exposed(self):
        self.assertGreater(FLOOR_TOLERANCE_KG_DAY, 0)
