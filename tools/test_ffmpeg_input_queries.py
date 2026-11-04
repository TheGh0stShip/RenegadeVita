"""Exercise production GCC identity queries with controlled driver responses."""
import os
from pathlib import Path
import shlex
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class InputQueryTests(unittest.TestCase):
    def test_target_flags_and_unresolved_or_failed_queries(self):
        script = (ROOT / 'tools/build_ffmpeg_bink_vita.sh').read_text()
        block = script[script.index('rv_target_flags=('):script.index('rv_identity_args=(')]
        with tempfile.TemporaryDirectory() as directory:
            sdk = Path(directory)
            (sdk / 'bin').mkdir()
            (sdk / 'include').mkdir()
            (sdk / 'cc1').touch()
            (sdk / 'libgcc.a').touch()
            driver = sdk / 'bin/arm-vita-eabi-gcc'
            driver.write_text('''#!/usr/bin/env python3
import os, pathlib, sys
for flag in ('-mcpu=cortex-a9', '-mfpu=neon', '-mfloat-abi=hard'):
    if flag not in sys.argv: sys.exit(9)
mode=os.environ['RV_FAKE_MODE']
if mode=='failure': sys.exit(7)
query=sys.argv[-1]
leaf={'-print-prog-name=cc1':'cc1', '-print-libgcc-file-name':'libgcc.a',
      '-print-file-name=include':'include'}[query]
if mode=='relative': print(leaf)
elif mode=='missing': print('/absent/ffmpeg-query/'+leaf)
else: print(pathlib.Path(__file__).resolve().parents[1]/leaf)
''')
            driver.chmod(0o755)
            code = 'set -euo pipefail\nrv_vitasdk=' + shlex.quote(str(sdk)) + '\n' + block
            for mode in ('valid', 'relative', 'missing', 'failure'):
                with self.subTest(mode=mode):
                    result = subprocess.run(['bash', '-c', code], cwd=sdk,
                                            env={**os.environ, 'RV_FAKE_MODE': mode},
                                            capture_output=True, text=True)
                    self.assertEqual(result.returncode == 0, mode == 'valid', result.stderr)


if __name__ == '__main__':
    unittest.main()
