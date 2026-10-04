"""Reproduce the original camera overrun and test the bounded staged callback."""
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess
import tempfile
from contextlib import nullcontext
import unittest

ROOT = Path(__file__).resolve().parents[1]


def bounded_source(source):
    declarations = list(re.finditer(r'\bDECLARE_SCRIPT\s*\(\s*(\w+)', source))
    match = next(item for item in declarations if item[1] == 'M09_Camera_Activate')
    start = match.start()
    end = next(item.start() for item in declarations if item.start() > start)
    body = source[start:end]
    old = 'for (int x = 0; x < 10; x++)'
    if body.count(old) != 1:
        raise ValueError('Camera callback loop identity changed')
    changed = body.replace(old, 'for (int x = 0; x < int(sizeof(camera) / sizeof(camera[0])); x++)')
    return source[:start] + changed + source[end:]


class CameraTests(unittest.TestCase):
    def test_original_failure_and_bounded_experiment(self):
        retained = os.environ.get('RENEGADE_M09_CAMERA_PROBE_DIRECTORY')
        if retained:
            Path(retained).mkdir(parents=True, exist_ok=True)
        with (nullcontext(retained) if retained else tempfile.TemporaryDirectory()) as directory:
            work = Path(directory).resolve()
            source = ROOT / 'upstream/CnC_Renegade/Code/Scripts/Mission09.cpp'
            staged = ROOT / 'staging/scripts/Mission09.cpp'
            experiment = work / 'Mission09-bounded.cpp'
            experiment.write_text(bounded_source(source.read_text(encoding='latin1')), encoding='latin1')
            self.assertEqual(experiment.read_bytes(), staged.read_bytes())
            receipts = []
            for label, cpp in (('original', source), ('bounded_staged', staged)):
                command = ['c++', '-std=c++17', '-O1', '-g', '-fpermissive',
                           '-DRENEGADE_HOST_ABI_TEST', '-fsanitize=address,undefined',
                           '-fno-sanitize-recover=all', '-pthread',
                           '-DM09_PROBE_SOURCE="' + str(cpp) + '"']
                for header in ('msvc_compat.h', 'renegade_script_call_defaults.h',
                               'renegade_campaign_script_defaults.h'):
                    command += ['-include', str(ROOT / 'port/compatibility/include' / header)]
                for name in ('staging/scripts', 'staging/wwmath', 'staging/wwlib',
                             'port/compatibility/include', 'port/platform'):
                    command += ['-I', str(ROOT / name)]
                command += [str(ROOT / 'tools/host_m09_camera_test.cpp')]
                command += [str(ROOT / 'staging/scripts' / name) for name in
                            ('scripts.cpp', 'ScriptFactory.cpp', 'ScriptRegistrar.cpp', 'strtrim.cpp')]
                command += [str(ROOT / 'port/platform/renegade_ui_pointer_tokens.cpp'),
                            '-o', str(work / label)]
                compiled = subprocess.run(command, capture_output=True, text=True)
                (work / (label + '.compile.log')).write_text(compiled.stdout + compiled.stderr)
                self.assertEqual(compiled.returncode, 0, compiled.stderr)
                result = subprocess.run([str(work / label)], capture_output=True, text=True)
                (work / (label + '.runtime.log')).write_text(result.stdout + result.stderr)
                if label == 'original':
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("index 5 out of bounds for type 'int [5]'", result.stderr)
                else:
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertIn('PASS camera_cases=4', result.stdout)
                receipts.append({'label': label, 'returncode': result.returncode,
                                 'source_sha256': hashlib.sha256(cpp.read_bytes()).hexdigest(),
                                 'binary_sha256': hashlib.sha256((work / label).read_bytes()).hexdigest()})
            receipt = {'schema_version': 1, 'evidence_class': 'host_actual_m09_callback_asan_ubsan',
                       'runs': receipts, 'runtime_patch_adopted': True,
                       'bounded_cases_passed': 4,
                       'limits': ['Actual registered script and callback; synthetic command transport and opaque objects.',
                                  'Staged source differs from original only by the bounded camera loop.',
                                  'No actual zone entry, camera effects, full mission or native execution.']}
            (work / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')


if __name__ == '__main__':
    unittest.main()
