"""HTTP contract tests for the local NutriPlan server."""
import json
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

from server import Handler
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from support import guelph_payload


class HttpContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Handler.log_message = lambda *args, **kwargs: None
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f'http://127.0.0.1:{cls.server.server_address[1]}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def post(self, path, payload):
        request = urllib.request.Request(
            self.base + path,
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST',
        )
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                return response.status, json.loads(response.read())
        except urllib.error.HTTPError as error:
            return error.code, json.loads(error.read())

    def test_requirements_endpoint_returns_native_requirements(self):
        status, data = self.post('/api/nutritional-requirements', guelph_payload())
        self.assertEqual(status, 200)
        self.assertEqual(data['status'], 'success')
        self.assertIn('net_energy', data['requirements'])

    def test_formulation_endpoint_returns_milk_potential(self):
        status, data = self.post('/api/rufas-native', guelph_payload())
        self.assertEqual(status, 200)
        self.assertTrue(data.get('ok'), data.get('message'))
        self.assertIn('milk_potential', data)
        self.assertIn('fixed_inclusions', data)
        self.assertGreaterEqual(
            data['milk_potential']['allowed_kg_day'],
            data['milk_potential']['reference_kg_day'] - 1e-4,
        )

    def test_fixed_targets_endpoint_returns_frontier(self):
        payload = guelph_payload(reference=25.062)
        payload['milk_targets'] = [25.062, 27.062]
        status, data = self.post('/api/rufas-native', payload)
        self.assertEqual(status, 200)
        self.assertTrue(data.get('ok'), data.get('message'))
        self.assertTrue(data['frontier'])
        self.assertEqual(len(data['target_results']), 2)

    def test_invalid_bounds_are_rejected(self):
        payload = guelph_payload()
        payload['feeds'] = [
            {'rufas_id': 51, 'price_as_fed': 0.35,
             'minimum_kg_dm': 5, 'maximum_kg_dm': 2, 'available': True},
            {'rufas_id': 31, 'price_as_fed': 1.57,
             'minimum_kg_dm': 0, 'maximum_kg_dm': 10, 'available': True},
        ]
        status, data = self.post('/api/rufas-native', payload)
        self.assertEqual(status, 422)
        self.assertIn(data.get('error_code'), {'ingredient', 'invalid_input', 'price'})

    def test_target_below_reference_returns_error_code(self):
        status, data = self.post('/api/rufas-native', guelph_payload(reference=30))
        self.assertEqual(status, 200)
        self.assertEqual(data.get('error_code'), 'milk_target_below_reference')

    def test_heifer_stage_has_no_milk_potential(self):
        payload = {
            'animal_category': 'heifer_I',
            'body_weight_kg': 300,
            'evaluate_milk_targets': True,
            'parameters': {
                'mature_body_weight': 700,
                'body_condition_score_5': 3,
                'average_daily_gain_heifer': 0.8,
                'housing': 'Barn',
                'distance': 0,
                'ndf_percentage': 30,
            },
        }
        status, data = self.post('/api/rufas-native', payload)
        self.assertEqual(status, 200)
        self.assertTrue(data.get('ok'), data.get('message'))
        self.assertEqual(data['stage_type'], 'growth')
        self.assertIsNone(data.get('milk_potential'))
        self.assertNotIn('target_results', data)


if __name__ == '__main__':
    unittest.main()
