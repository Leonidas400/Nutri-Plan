"""Validation tests for milk composition and the NASEM requirement wrapper."""
import unittest

from services.nutrition import calculate
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from support import guelph_payload


def _payload(**parameter_overrides):
    payload = guelph_payload()
    # Direct requirement previews do not derive NDF from a previous ration.
    payload['parameters'] = {
        **payload['parameters'], 'ndf_percentage': 30.0, **parameter_overrides,
    }
    return payload


class MilkCompositionTests(unittest.TestCase):
    def test_composition_above_one_hundred_is_rejected(self):
        result = calculate(_payload(milk_fat=60, milk_true_protein=30, milk_lactose=20))
        self.assertEqual(result['status'], 'invalid_input')
        self.assertEqual(result['error_code'], 'invalid_milk_composition')

    def test_valid_composition_succeeds(self):
        result = calculate(_payload())
        self.assertEqual(result['status'], 'success')
        self.assertGreater(result['requirements']['net_energy'], 0)

    def test_phosphorus_minimum_uses_process_requirement(self):
        result = calculate(_payload(process_based_phosphorus_requirement=0.45))
        self.assertEqual(result['status'], 'success')
        self.assertGreaterEqual(
            result['constraints']['phosphorus']['minimum'],
            result['requirements']['phosphorus'],
        )

    def test_calving_interval_must_be_positive(self):
        result = calculate(_payload(calving_interval=0))
        self.assertEqual(result['status'], 'invalid_input')


if __name__ == '__main__':
    unittest.main()
