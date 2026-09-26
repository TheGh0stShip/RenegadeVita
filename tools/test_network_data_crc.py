"""Compile original cNetwork CRC method against bounded synthetic file providers."""
from pathlib import Path
import subprocess
import tempfile
import unittest
import zlib

ROOT = Path(__file__).resolve().parents[1]


class NetworkDataCRCTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        directory = Path(cls.temp.name)
        source = (ROOT / 'staging/commando/cnetwork.cpp').read_text()
        start = source.index('int cNetwork::Get_Data_Files_CRC(void)')
        end = source.index('//-----------------------------------------------------------------------------', start)
        (directory / 'network_data_crc.inc').write_text(source[start:end])
        cls.binary = directory / 'crc-test'
        subprocess.run(['c++', '-std=c++17', '-D_UNIX=1', '-DNDEBUG',
                        '-fsanitize=address,undefined', '-fno-sanitize-recover=all',
                        '-Wno-unknown-pragmas', '-Wno-write-strings',
                        '-I' + str(ROOT / 'port/compatibility/include'),
                        '-I' + str(ROOT / 'staging/wwlib'), '-I' + str(directory),
                        '-I' + str(ROOT / 'upstream/CnC_Renegade/Code/wwdebug'),
                        '-include', str(ROOT / 'port/compatibility/include/msvc_compat.h'),
                        str(ROOT / 'staging/wwlib/realcrc.cpp'),
                        str(ROOT / 'tools/host_network_data_crc_probe.cpp'),
                        '-o', str(cls.binary)], check=True, timeout=30)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def run_case(self, mode, chunk):
        result = subprocess.run([str(self.binary), str(mode), str(chunk)],
                                capture_output=True, text=True, check=True, timeout=5)
        values = tuple(map(int, result.stdout.split()))
        self.assertEqual(values[4], values[5])
        self.assertEqual(values[6], 0)
        return values

    def test_short_reads_empty_eof_missing_files_and_cache(self):
        expected = zlib.crc32(bytes(range(256)) * 131 + b'repeated-entry' * 2)
        for chunk in (31, 4096, 16384):
            result = self.run_case(0, chunk)
            self.assertEqual(result[:4], (expected, 1, expected, 1))
            self.assertEqual(result[7], result[8], 'cached CRC must not reopen files')
        result = self.run_case(4, 31)
        self.assertEqual(result[:4], (0, 1, 0, 1))
        self.assertEqual(result[7], result[8])

    def test_failed_open_negative_and_oversized_read_do_not_cache_partial_key(self):
        expected = zlib.crc32(bytes(range(256)) * 131 + b'repeated-entry' * 2)
        for mode in (1, 2, 3):
            result = self.run_case(mode, 31)
            self.assertEqual(result[:4], (0, 0, expected, 1))
            self.assertGreater(result[8], result[7])


if __name__ == '__main__':
    unittest.main()
