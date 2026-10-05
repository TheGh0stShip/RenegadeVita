"""Write-only rooted files are staged in memory and written once at Close,
with bytes, returns and cursors identical to direct writes."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / 'staging'
UPSTREAM = ROOT / 'upstream/CnC_Renegade/Code'


class RenegadeFileFactoryStagingTests(unittest.TestCase):
    def build_and_run(self, flags):
        with tempfile.TemporaryDirectory(prefix='renegade-staging-') as folder:
            binary = Path(folder) / 'test'
            subprocess.run(['g++', '-std=c++17', *flags, '-g', '-D_UNIX=1', '-DRENEGADE_VITA_PORT=1',
                            '-DNDEBUG=1', '-fno-strict-aliasing', '-w',
                            '-include', str(ROOT / 'port/compatibility/include/msvc_compat.h'),
                            '-I' + str(ROOT / 'port/compatibility/include'),
                            '-I' + str(ROOT / 'port/filesystem'),
                            '-I' + str(STAGE / 'wwlib'), '-I' + str(STAGE / 'wwmath'),
                            '-I' + str(UPSTREAM / 'wwdebug'), '-I' + str(UPSTREAM / 'wwlib'),
                            str(ROOT / 'tools/renegade_file_factory_staging_test.cpp'),
                            str(ROOT / 'port/filesystem/renegade_file_factory.cpp'),
                            str(ROOT / 'port/filesystem/renegade_paths.cpp'),
                            str(STAGE / 'wwlib/rawfile.cpp'), str(STAGE / 'wwlib/bufffile.cpp'),
                            str(STAGE / 'wwlib/wwstring.cpp'), str(STAGE / 'wwlib/chunkio.cpp'),
                            '-o', str(binary)], check=True)
            completed = subprocess.run([str(binary)], check=True, capture_output=True,
                                       text=True, timeout=300)
            self.assertIn('write staging PASS', completed.stdout)

    def test_sanitized(self):
        self.build_and_run(['-O1', '-fsanitize=address,undefined', '-fno-omit-frame-pointer'])

    def test_optimized(self):
        self.build_and_run(['-O2'])

    def test_vita_rename_refuses_existing_destination(self):
        # sceIoRename does not replace; repeated saves to one slot must still land.
        self.build_and_run(['-O1', '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
                            '-DRENEGADE_TEST_REFUSING_RENAME=1'])

    def test_only_write_only_opens_stage(self):
        source = (ROOT / 'port/filesystem/renegade_file_factory.cpp').read_text()
        self.assertIn('const bool write_only = rights == FileClass::WRITE;', source)
        self.assertIn('} else if (write_only) {', source)
        destructor = source[source.index('RenegadeRootedFileClass::~RenegadeRootedFileClass(void)'):]
        self.assertIn('if (Staging) Close();', destructor[:destructor.index('\n}\n')])


if __name__ == '__main__':
    unittest.main()
