"""Compile the target gate with real VitaSDK and reject accidental host-as-Vita."""
from pathlib import Path
import os
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
HEADER = ROOT / 'port/compatibility/include/renegade_target_abi.h'


class VitaTargetABITests(unittest.TestCase):
    def compile(self, compiler, flags=()):
        return subprocess.run([str(compiler), *flags, '-include', str(HEADER),
                               '-x', 'c++', '-fsyntax-only', '-'], input='int abi_probe;\n',
                              text=True, capture_output=True, timeout=15)

    def test_native_vitasdk_contract(self):
        sdk = Path(os.environ.get('VITASDK', '/usr/local/vitasdk'))
        result = self.compile(sdk / 'bin/arm-vita-eabi-g++')
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_host_probe_is_not_misidentified_as_vita(self):
        result = self.compile('c++', ('-DRENEGADE_VITA_PORT=1',))
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_host_cannot_claim_device_abi(self):
        result = self.compile('c++', ('-D__vita__=1',))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('PS Vita requires', result.stderr)


if __name__ == '__main__':
    unittest.main()
