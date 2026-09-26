"""Check original bitstream soldier suffix against pinned retail serialization."""
import json
import os
from pathlib import Path
import re
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SoldierRareTests(unittest.TestCase):
    def test_soldier_frequent_reference(self):
        binary = os.environ.get('RENEGADE_HOST_RUNTIME',
                                str(ROOT / 'build/host-a31-asan/a31_m00_interactive_runtime'))
        result = subprocess.run([binary, '--tt-soldier-frequent-selftest'],
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        fixture = json.loads((ROOT / 'tools/fixtures/tt_soldier_frequent_b9000.json').read_text())
        self.assertEqual(fixture['reference_sha256'],
                         'd520443f5618b7d34d48a2e1d4b8348516d53d3ac9a7e201077e259f64c100db')
        found = re.findall(r'^tt_soldier_frequent.vector_(\d)=(\d+):([0-9a-f]+)$', result.stdout, re.M)
        self.assertEqual(len(found), 9)
        for (_, bits, payload), case in zip(found, fixture['cases']):
            self.assertEqual(int(bits), case['bits'])
            self.assertEqual(payload, case['hex'])

        outgoing = re.findall(r'^tt_soldier_cs.vector_(\d)=(\d+):([0-9a-f]+)$', result.stdout, re.M)
        self.assertEqual(len(outgoing), 2)
        for (_, bits, payload), case in zip(outgoing, fixture['client_state_cases']):
            self.assertEqual(int(bits), case['bits'])
            self.assertEqual(payload, case['hex'])

    def test_defense_reference(self):
        binary = os.environ.get('RENEGADE_HOST_RUNTIME',
                                str(ROOT / 'build/host-a31-asan/a31_m00_interactive_runtime'))
        result = subprocess.run([binary, '--tt-defense-selftest'],
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        fixture = json.loads((ROOT / 'tools/fixtures/tt_defense_b9000.json').read_text())
        self.assertEqual(fixture['reference_sha256'],
                         'd520443f5618b7d34d48a2e1d4b8348516d53d3ac9a7e201077e259f64c100db')
        found = re.findall(r'^tt_defense.vector_(\d)=(\d+):([0-9a-f]+)$', result.stdout, re.M)
        self.assertEqual(len(found), 3)
        for (_, bits, payload), case in zip(found, fixture['cases']):
            self.assertEqual(int(bits), case['bits'])
            self.assertEqual(payload, case['hex'])

    def test_shared_frequent_reference(self):
        binary = os.environ.get('RENEGADE_HOST_RUNTIME',
                                str(ROOT / 'build/host-a31-asan/a31_m00_interactive_runtime'))
        result = subprocess.run([binary, '--tt-smart-frequent-selftest'],
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        fixture = json.loads((ROOT / 'tools/fixtures/tt_smart_frequent_b9000.json').read_text())
        self.assertEqual(fixture['reference_sha256'],
                         'd520443f5618b7d34d48a2e1d4b8348516d53d3ac9a7e201077e259f64c100db')
        found = re.findall(r'^tt_smart.vector_(\d)=(\d+):([0-9a-f]+)$', result.stdout, re.M)
        self.assertEqual(len(found), 3)
        for (_, bits, payload), case in zip(found, fixture['cases']):
            self.assertEqual(int(bits), case['bits'])
            self.assertEqual(payload, case['hex'])

    def test_reference_and_atomic_truncation(self):
        binary = os.environ.get('RENEGADE_HOST_RUNTIME',
                                str(ROOT / 'build/host-a31-asan/a31_m00_interactive_runtime'))
        result = subprocess.run([binary, '--tt-soldier-rare-selftest'],
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        fixture = json.loads((ROOT / 'tools/fixtures/tt_soldier_rare_b9000.json').read_text())
        self.assertEqual(fixture['reference_sha256'],
                         'd520443f5618b7d34d48a2e1d4b8348516d53d3ac9a7e201077e259f64c100db')
        found = re.findall(r'^tt_soldier.vector_(\d)=(\d+):([0-9a-f]+)$', result.stdout, re.M)
        self.assertEqual(len(found), 3)
        for (_, bits, payload), case in zip(found, fixture['cases']):
            self.assertEqual(int(bits), case['bits'])
            self.assertEqual(payload, case['hex'])
        self.assertIn('tt_soldier.transactional_truncations=5904 result=PASS', result.stdout)


if __name__ == '__main__':
    unittest.main()
