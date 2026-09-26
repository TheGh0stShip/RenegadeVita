import json
import os
from pathlib import Path
import re
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class C4Tests(unittest.TestCase):
    def test_retained_reference_and_truncations(self):
        binary = os.environ.get('RENEGADE_HOST_RUNTIME', str(ROOT / 'build/host-a31-asan/a31_m00_interactive_runtime'))
        run = subprocess.run([binary, '--tt-c4-selftest'], capture_output=True, text=True, timeout=30)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        fixture = json.loads((ROOT / 'tools/fixtures/tt_c4_b9000.json').read_text())
        self.assertEqual(fixture['reference_sha256'], 'd520443f5618b7d34d48a2e1d4b8348516d53d3ac9a7e201077e259f64c100db')
        found = re.findall(r'^tt_c4.vector_(\d+)=(\d+):([0-9a-f]+)$', run.stdout, re.M)
        self.assertEqual(len(found), 4)
        for (_, bits, payload), case in zip(found, fixture['cases']):
            self.assertEqual(int(bits), case['bits'])
            self.assertEqual(payload, case['hex'])
        self.assertIn('result=PASS', run.stdout)


if __name__ == '__main__':
    unittest.main()
