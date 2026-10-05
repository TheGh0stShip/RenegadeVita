"""Retail availability probes are cached after the first native success."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class RenegadeFileFactoryAvailabilityTests(unittest.TestCase):
    def test_availability_cache_under_sanitizers(self):
        for sanitizer in ('address,undefined', 'thread'):
            with self.subTest(sanitizer=sanitizer), \
                    tempfile.TemporaryDirectory(prefix='renegade-factory-') as folder:
                binary = Path(folder) / 'test'
                # The stub BufferedFileClass counts native probes.
                subprocess.run(['g++', '-std=c++17', '-O1', '-g', '-fsanitize=' + sanitizer,
                                '-fno-omit-frame-pointer', '-Wall', '-Wextra', '-Werror', '-pthread',
                                '-I' + str(ROOT / 'tools/file_factory_stub'),
                                '-I' + str(ROOT / 'port/filesystem'),
                                str(ROOT / 'tools/renegade_file_factory_availability_test.cpp'),
                                str(ROOT / 'port/filesystem/renegade_file_factory.cpp'),
                                str(ROOT / 'port/filesystem/renegade_paths.cpp'),
                                '-o', str(binary)], check=True)
                completed = subprocess.run([str(binary)], check=True, capture_output=True,
                                           text=True, timeout=120)
                self.assertIn('availability cache PASS', completed.stdout)

    def test_only_unforced_retail_successes_are_cached(self):
        source = (ROOT / 'port/filesystem/renegade_file_factory.cpp').read_text()
        available = source[source.index('bool RenegadeRootedFileClass::Is_Available('):
                           source.index('int RenegadeRootedFileClass::Create(')]
        self.assertIn('const bool immutable_retail = !forced && !LastResolution.writable_namespace;',
                      available)
        self.assertIn('if (immutable_retail) Remember_Available(LastResolution.physical);', available)
        self.assertLess(available.index('LastResolution.confirmed_missing &&'),
                        available.index('Is_Known_Available(LastResolution.physical)'))


if __name__ == '__main__':
    unittest.main()
