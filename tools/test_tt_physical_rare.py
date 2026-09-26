"""Original physical rare fields must match the pinned TT serializer fixtures."""
import json
import os
from pathlib import Path
import re
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PhysicalRareTests(unittest.TestCase):
    def test_reference_bytes_and_bounded_preflight(self):
        binary = os.environ.get('RENEGADE_HOST_RUNTIME',
                                str(ROOT / 'build/host-a31-asan/a31_m00_interactive_runtime'))
        result = subprocess.run([binary, '--tt-physical-rare-selftest'],
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        fixture = json.loads((ROOT / 'tools/fixtures/tt_physical_rare_b9000.json').read_text())
        self.assertEqual(fixture['reference_sha256'],
                         'd520443f5618b7d34d48a2e1d4b8348516d53d3ac9a7e201077e259f64c100db')
        found = re.findall(r'^tt_physical.vector_(\d)=(\d+):([0-9a-f]+)$', result.stdout, re.M)
        self.assertEqual(len(found), len(fixture['cases']))
        for (modern, bits, payload), case in zip(found, fixture['cases']):
            self.assertEqual(int(modern), int(case['modern']))
            self.assertEqual(int(bits), case['bits'])
            self.assertEqual(payload, case['hex'])
        self.assertIn('tt_physical.profiles_unaligned_truncations=5728 result=PASS', result.stdout)


if __name__ == '__main__':
    unittest.main()
