"""Compare original WWNet greeting bytes to the pinned PC serializer oracle."""
import json
import os
from pathlib import Path
import re
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class GreetingTests(unittest.TestCase):
    def test_original_runtime_reference_and_boundary_contracts(self):
        binary = Path(os.environ.get('RENEGADE_HOST_RUNTIME',
                      ROOT / 'build/host-a31-asan/a31_m00_interactive_runtime'))
        result = subprocess.run([str(binary), '--tt-client-greeting-selftest'],
                                capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        reference = json.loads((ROOT / 'tools/fixtures/tt_client_greeting_b9000.json').read_text())
        self.assertEqual(reference['reference_sha256'],
                         'd520443f5618b7d34d48a2e1d4b8348516d53d3ac9a7e201077e259f64c100db')
        self.assertFalse(reference['real_credentials_used'])
        self.assertFalse(reference['public_server_contacted'])
        found = re.findall(r'^tt_greeting.vector_(\d+)=(\d+):([0-9a-f]+)$', result.stdout, re.M)
        self.assertEqual(len(found), len(reference['cases']))
        for (index, bits, payload), case in zip(found, reference['cases']):
            self.assertEqual(int(bits), case['bits'], index)
            self.assertEqual(payload, case['hex'], index)
        self.assertIn('tt_greeting.vectors_unaligned_bounds_missing_identity_one_shot=PASS', result.stdout)
        self.assertIn('tt_greeting.original_udp_accept_refuse_legacy_reset=PASS', result.stdout)
        self.assertIn('tt_options.layout_bounds_profiles_unaligned=PASS', result.stdout)
        suffix = json.loads((ROOT / 'tools/fixtures/tt_options_tail_b9000.json').read_text())
        self.assertEqual(suffix['reference_sha256'], reference['reference_sha256'])
        found = re.findall(r'^tt_options.suffix_(\d+)=(\d+):([0-9a-f]+)$', result.stdout, re.M)
        self.assertEqual(len(found), len(suffix['cases']))
        for (flag, bits, payload), case in zip(found, suffix['cases']):
            self.assertEqual(int(flag), int(case['flag']))
            self.assertEqual(int(bits), case['bits'])
            self.assertEqual(payload, case['hex'])


if __name__ == '__main__':
    unittest.main()
