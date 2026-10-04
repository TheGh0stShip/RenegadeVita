"""Exercise unchanged original warning owners using a bounded host transport."""
from contextlib import nullcontext
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from tools.audit_script_warning_routes import script_section

ROOT = Path(__file__).resolve().parents[1]


class WarningRouteTests(unittest.TestCase):
    def test_comment_aware_owner_selection(self):
        source = '/*DECLARE_SCRIPT(Fake, "") {}*/\nDECLARE_SCRIPT (Real, "") {}\nDECLARE_SCRIPT(Next, "") {}'
        self.assertIn('Real', script_section(source, 'Real'))
        with self.assertRaises(ValueError):
            script_section(source, 'Fake')

    def test_actual_original_warning_routes(self):
        retained = os.environ.get('RENEGADE_WARNING_ROUTE_PROBE_DIRECTORY')
        if retained:
            Path(retained).mkdir(parents=True, exist_ok=True)
        with (nullcontext(retained) if retained else tempfile.TemporaryDirectory()) as directory:
            work = Path(directory).resolve()
            sources = {name: (ROOT / 'staging/scripts' / name).read_text(encoding='latin1')
                       for name in ('Mission10.cpp', 'mission08.cpp', 'Test_PDS.cpp', 'Test_RMV_Toolkit.cpp')}
            originals = {name: (ROOT / 'upstream/CnC_Renegade/Code/Scripts' / name).read_text(encoding='latin1')
                         for name in sources}
            pds = sources['Test_PDS.cpp']
            rmv = sources['Test_RMV_Toolkit.cpp']
            shared = [pds[pds.index('\nenum\n{\n\tINVENTORY_EMPTY'):pds.index('DECLARE_SCRIPT(PDS_Test_Inventory')],
                      rmv[rmv.index('\nenum {'):rmv.index('DECLARE_SCRIPT(RMV_Trigger_Zone')],
                      script_section(sources['Test_PDS.cpp'], 'PDS_Test_Inventory')]
            self.assertEqual(shared[2], script_section(originals['Test_PDS.cpp'], 'PDS_Test_Inventory'))
            headers = {}
            binaries = {}
            environment = os.environ.copy()
            environment.setdefault('ASAN_OPTIONS', 'detect_leaks=0')
            for label, selected in (('original', originals), ('corrected', sources)):
                sections = shared[:]
                sections.append(script_section(selected['Test_RMV_Toolkit.cpp'], 'RMV_Engineer_Wander'))
                for name, owner in (('Mission10.cpp', 'M10_Apache_Controller'),
                                    ('mission08.cpp', 'M08_Apache_Controller')):
                    sections.append(script_section(selected[name], owner))
                header = work / (label + '-owners.h')
                header.write_text('\n'.join(sections), encoding='latin1')
                binary = work / label
                command = ['c++', '-std=c++17', '-O1', '-g', '-fpermissive', '-DRENEGADE_HOST_ABI_TEST',
                           '-fsanitize=address,undefined', '-fno-sanitize-recover=all', '-pthread',
                           '-DWARNING_PROBE_SOURCE="' + str(header) + '"']
                for name in ('msvc_compat.h', 'renegade_script_call_defaults.h', 'renegade_campaign_script_defaults.h'):
                    command += ['-include', str(ROOT / 'port/compatibility/include' / name)]
                for name in ('staging/scripts', 'staging/wwmath', 'staging/wwlib', 'port/compatibility/include', 'port/platform'):
                    command += ['-I', str(ROOT / name)]
                command += [str(ROOT / 'tools/host_script_warning_routes_test.cpp')]
                command += [str(ROOT / 'staging/scripts' / name) for name in
                            ('scripts.cpp', 'ScriptFactory.cpp', 'ScriptRegistrar.cpp', 'strtrim.cpp')]
                command += [str(ROOT / 'port/platform/renegade_ui_pointer_tokens.cpp'), '-o', str(binary)]
                compiled = subprocess.run(command, capture_output=True, text=True, env=environment)
                (work / (label + '-compile.log')).write_text(compiled.stdout + compiled.stderr)
                self.assertEqual(compiled.returncode, 0, compiled.stderr)
                headers[label] = header
                binaries[label] = binary
            results = []
            for owner in ('M08_Apache_Controller', 'M10_Apache_Controller'):
                for mode in ('valid', 'negative_destroy', 'inactive_reload', 'timer_gap',
                             'negative_timer', 'high_timer'):
                    for label in ('original', 'corrected'):
                        result = subprocess.run([str(binaries[label]), mode, owner], capture_output=True,
                                                text=True, env=environment)
                        (work / (label + '-' + owner + '-' + mode + '.log')).write_text(result.stdout + result.stderr)
                        expected_failure = label == 'original' and mode in (
                            'negative_destroy', 'inactive_reload', 'timer_gap', 'negative_timer')
                        if expected_failure:
                            self.assertNotEqual(result.returncode, 0)
                            self.assertIn('out of bounds', result.stderr)
                        else:
                            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                            self.assertIn('PASS', result.stdout)
                        results.append({'source': label, 'owner': owner, 'mode': mode,
                                        'returncode': result.returncode})
            for owner, mode in (('RMV_Engineer_Wander', 'technician'), ('PDS_Test_Inventory', 'medkit_null')):
                result = subprocess.run([str(binaries['corrected']), mode, owner], capture_output=True,
                                        text=True, env=environment)
                (work / (owner + '-' + mode + '.log')).write_text(result.stdout + result.stderr)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn('PASS', result.stdout)
                results.append({'owner': owner, 'mode': mode, 'returncode': result.returncode})
            receipt = {'schema_version': 1, 'evidence_class': 'host_actual_original_script_routes_asan_ubsan',
                       'results': results, 'runtime_cpp_changed': True,
                       'binary_sha256': {label: hashlib.sha256(path.read_bytes()).hexdigest()
                                         for label, path in binaries.items()},
                       'extracted_owners_sha256': {label: hashlib.sha256(path.read_bytes()).hexdigest()
                                                  for label, path in headers.items()},
                       'limits': ['Unchanged original script sections, real registration and callbacks; synthetic transport and opaque objects.',
                                  'Invalid-route reproducers are not proof that authored retail events take those routes.',
                                  'No non-null medkit pointer sender, native execution or full mission validation.']}
            (work / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')


if __name__ == '__main__':
    unittest.main()
