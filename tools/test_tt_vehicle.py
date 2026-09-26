"""Compare original bitstream vehicle updates with pinned b9000 serializers."""
import json
import os
from pathlib import Path
import re
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class VehicleTests(unittest.TestCase):
    def test_reference_vectors_and_truncation(self):
        binary = os.environ.get('RENEGADE_HOST_RUNTIME',
                                str(ROOT / 'build/host-a31-asan/a31_m00_interactive_runtime'))
        result = subprocess.run([binary, '--tt-vehicle-selftest'],
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        fixture = json.loads((ROOT / 'tools/fixtures/tt_vehicle_b9000.json').read_text())
        self.assertEqual(fixture['reference_sha256'],
                         'd520443f5618b7d34d48a2e1d4b8348516d53d3ac9a7e201077e259f64c100db')
        found = re.findall(r'^tt_vehicle.vector_(\d+)=(\d+):([0-9a-f]+)$', result.stdout, re.M)
        self.assertEqual(len(found), len(fixture['cases']))
        for (_, bits, payload), case in zip(found, fixture['cases']):
            self.assertEqual(int(bits), case['bits'], case)
            self.assertEqual(payload, case['hex'], case)
        self.assertRegex(result.stdout, r'tt_vehicle.transactional_truncations=[1-9][0-9]+ result=PASS')
        soldiers = re.findall(r'^tt_soldier_occasional.vector_(\d+)=(\d+):([0-9a-f]+)$', result.stdout, re.M)
        self.assertEqual(len(soldiers), 2)
        for (_, bits, payload), case in zip(soldiers, fixture['soldier_occasional_cases']):
            self.assertEqual(int(bits), case['bits'])
            self.assertEqual(payload, case['hex'])


if __name__ == '__main__':
    unittest.main()
