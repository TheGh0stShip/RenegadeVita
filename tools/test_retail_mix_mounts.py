"""Original factory lookup fixtures only; no game loop or retail mutation."""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest

from tools.test_collect_retail_content_baseline import write_mix

ROOT = Path(__file__).resolve().parents[1]


class RetailMixMountTests(unittest.TestCase):
    def test_original_owners_under_sanitizers(self):
        with tempfile.TemporaryDirectory(prefix='retail-mix-fixture-') as temporary:
            folder = Path(temporary)
            stage = ROOT / 'staging'
            compat = ROOT / 'port/compatibility/include'
            sources = ['rawfile.cpp', 'bufffile.cpp', 'wwstring.cpp', 'chunkio.cpp',
                       'mixfile.cpp', 'ffactory.cpp', 'realcrc.cpp', 'crc.cpp']
            command = ['g++', '-std=c++17', '-O1', '-g', '-fsanitize=address,undefined',
                       '-fno-omit-frame-pointer', '-D_UNIX=1', '-DRENEGADE_VITA_PORT=1',
                       '-DRENEGADE_HOST_ABI_TEST=1', '-DNDEBUG=1', '-fno-strict-aliasing', '-w',
                       '-include', str(compat / 'msvc_compat.h')]
            for include in [compat, ROOT / 'port/filesystem', stage / 'wwlib', stage / 'wwmath',
                            stage / 'combat', ROOT / 'upstream/CnC_Renegade/Code/wwdebug']:
                command += ['-I' + str(include)]
            command += [str(ROOT / 'tools/retail_mix_mounts_test.cpp'),
                        str(ROOT / 'port/filesystem/renegade_file_factory.cpp'),
                        str(ROOT / 'port/filesystem/renegade_paths.cpp'),
                        str(ROOT / 'port/filesystem/renegade_find_files.cpp'),
                        str(stage / 'combat/ffactorylist.cpp')]
            command += [str(stage / 'wwlib' / name) for name in sources]
            binary = folder / 'probe'
            subprocess.run([*command, '-o', str(binary)], check=True)
            for mode in ('valid', 'invalid', 'missing-tutorial', 'empty'):
                root = folder / mode
                data = root / 'Data'
                data.mkdir(parents=True)
                for name, members in {
                    'Always.dat': [('shared.txt', b'global')],
                    'M00_Tutorial.mix': [('tutorial.txt', b'tutorial')],
                    'M01.mix': [('local.txt', b'local')],
                    'M02.mix': [('cross_mission.txt', b'other mission')],
                    'M09.mix': [('shared.txt', b'm09')],
                    'network.dat': [('shared.txt', b'network')],
                }.items():
                    if name.endswith('.mix') and (mode == 'empty' or
                            (mode == 'missing-tutorial' and name == 'M00_Tutorial.mix')):
                        continue
                    write_mix(data / name, members)
                (data / 'folder.mix').mkdir()
                (data / 'nested').mkdir()
                write_mix(data / 'nested/extra.mix', [('cross_mission.txt', b'nested')])
                if mode == 'invalid':
                    (data / 'broken.mix').write_bytes(b'not an archive')
                completed = subprocess.run([str(binary), str(root), mode],
                                           capture_output=True, text=True, timeout=60)
                self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
                self.assertIn('retail MIX mounts PASS', completed.stdout)
            reference = os.environ.get('RENEGADE_RETAIL_MIX_REFERENCE')
            if reference:
                completed = subprocess.run([str(binary), reference, 'reference'],
                                           capture_output=True, text=True, timeout=60)
                self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
                self.assertIn('cross-mission DDS header PASS', completed.stdout)
                print(completed.stdout.strip())


if __name__ == '__main__':
    unittest.main()
