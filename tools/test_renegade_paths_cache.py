"""Cached retail case resolution must match a direct directory scan."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class RenegadePathsCacheTests(unittest.TestCase):
    def test_cached_resolution_under_sanitizers(self):
        for sanitizer in ('address,undefined', 'thread'):
            with self.subTest(sanitizer=sanitizer), \
                    tempfile.TemporaryDirectory(prefix='renegade-paths-') as folder:
                binary = Path(folder) / 'test'
                subprocess.run(['g++', '-std=c++17', '-O1', '-g', '-fsanitize=' + sanitizer,
                                '-fno-omit-frame-pointer', '-Wall', '-Wextra', '-Werror', '-pthread',
                                '-I' + str(ROOT / 'port/filesystem'),
                                str(ROOT / 'tools/renegade_paths_cache_test.cpp'),
                                str(ROOT / 'port/filesystem/renegade_paths.cpp'),
                                '-o', str(binary)], check=True)
                subprocess.run([str(binary)], check=True, timeout=120)

    def test_only_the_retail_root_is_cached(self):
        source = (ROOT / 'port/filesystem/renegade_paths.cpp').read_text()
        self.assertIn('!result.writable_namespace)) {', source)
        self.assertIn('if (immutable_root && Select_From_Cached_Listing(', source)


if __name__ == '__main__':
    unittest.main()
