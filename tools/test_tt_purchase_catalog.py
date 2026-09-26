"""Original catalog import/export/factory conformance against pinned retail execution."""
import json
import os
from pathlib import Path
import re
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PurchaseCatalogTests(unittest.TestCase):
    def test_original_owners_against_reference(self):
        binary = os.environ.get('RENEGADE_HOST_RUNTIME', str(ROOT / 'build/host-a31-asan/a31_m00_interactive_runtime'))
        result = subprocess.run([binary, '--tt-purchase-catalog-selftest'], capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        fixture = json.loads((ROOT / 'tools/fixtures/tt_purchase_catalog_b9000.json').read_text())
        self.assertEqual(fixture['reference_sha256'], 'd520443f5618b7d34d48a2e1d4b8348516d53d3ac9a7e201077e259f64c100db')
        for label in ('vector', 'factory'):
            found = re.findall(r'^tt_purchase.' + label + r'_(\d+)=(\d+):([0-9a-f]+)$', result.stdout, re.M)
            self.assertEqual(len(found), len(fixture['cases']))
            prefix = '' if label == 'vector' else 'factory_'
            for (_, bits, payload), case in zip(found, fixture['cases']):
                self.assertEqual(int(bits), case[prefix + 'bits'])
                self.assertEqual(payload, case[prefix + 'hex'])
        self.assertIn('tt_purchase.transactional_truncations=1215 result=PASS', result.stdout)


if __name__ == '__main__':
    unittest.main()
