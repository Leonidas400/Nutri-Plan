"""Interface local NutriPlan e integração com o RuFaS instalado na pasta pai."""
from __future__ import annotations

import json
import os
import sys
import traceback
import subprocess
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from services.messages import validation_error
from services.nutrition import categories, calculate

ROOT = Path(__file__).resolve().parent
RUFAS_ROOT = ROOT.parent
HOST = '127.0.0.1'
PORT = int(os.environ.get('PORT', '8765'))
MAX_BODY = 2_000_000


class Handler(BaseHTTPRequestHandler):
    def _send(self, data, status=200):
        raw = json.dumps(data, ensure_ascii=False, allow_nan=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        request_path = self.path.partition('?')[0]
        if request_path in ('/', '/index.html'):
            data = (ROOT / 'index.html').read_bytes()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        elif request_path == '/styles.css':
            data = (ROOT / 'styles.css').read_bytes()
            self.send_response(200)
            self.send_header('Content-Type', 'text/css; charset=utf-8')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        elif request_path == '/api/nasem-feeds':
            from services.native_ration import available_feeds
            self._send({'feeds': available_feeds()})
        elif request_path == '/api/animal-categories':
            self._send({'categories': categories()})
        elif request_path == '/api/health':
            feed_path = RUFAS_ROOT / 'input/data/feed/NASEM_Comp_with_TDN.csv'
            try:
                revision = subprocess.run(['git', '-C', str(RUFAS_ROOT), 'rev-parse', 'HEAD'],
                                          capture_output=True, text=True, check=False)
                commit = revision.stdout.strip() if revision.returncode == 0 else None
            except OSError:
                commit = None
            self._send({'ok': True, 'solver': 'SLSQP', 'numerical_library': 'SciPy',
                        'native': (RUFAS_ROOT / 'RUFAS' / 'biophysical' / 'animal' / 'ration' / 'ration_optimizer.py').is_file(),
                        'rufas_commit': commit,
                        'feed_library_sha256': hashlib.sha256(feed_path.read_bytes()).hexdigest() if feed_path.is_file() else None})
        else:
            self._send({'error_code': 'unknown_route'}, 404)

    def do_POST(self):
        if self.path not in ('/api/rufas-native', '/api/nutritional-requirements', '/api/sensitivity-analysis', '/api/economic-comparison'):
            return self._send({'error_code': 'unknown_route'}, 404)
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if size <= 0 or size > MAX_BODY:
                return self._send({'error_code': 'invalid_request_size'}, 413)
            payload = json.loads(self.rfile.read(size))
            if self.path == '/api/nutritional-requirements':
                if isinstance(payload, dict) and payload.get('previous_ration'):
                    from services.native_ration import prepare_animal_payload
                    payload = prepare_animal_payload(payload)
                data = calculate(payload)
            elif self.path == '/api/sensitivity-analysis':
                from services.sensitivity import run_sensitivity
                data = run_sensitivity(payload)
            elif self.path == '/api/economic-comparison':
                from services.economic_comparison import compare_diets_economically
                from services.native_ration import feed_library
                if not isinstance(payload, dict):
                    raise ValueError('Economic comparison input must be an object.')
                data = compare_diets_economically(
                    baseline_ration=payload.get('baseline_ration'),
                    optimized_ration=payload.get('optimized_ration'),
                    price_records=payload.get('price_records'),
                    feed_catalog=feed_library(),
                    batch_size=payload.get('batch_size'),
                    milk_data=payload.get('milk_data'),
                )
            else:
                if not isinstance(payload, dict) or 'animal_category' not in payload:
                    return self._send({'error_code': 'invalid_input'}, 422)
                from services.milk_targets import formulate
                data = formulate(payload)
            if data.get('ok') is False:
                data.setdefault('error_code', data.get('status', 'solver_failure'))
            self._send(data)
        except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            self._send(validation_error(exc), 422)
        except Exception:
            traceback.print_exc()
            self._send({'error_code': 'calculation_error'}, 500)


if __name__ == '__main__':
    print(f'RuFaS Dietas - abrir http://{HOST}:{PORT}')
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
