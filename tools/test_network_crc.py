"""Original checksum width, unaligned and streaming regression vectors."""
import ctypes
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def expected(data, initial=0):
    value = initial
    for offset in range(0, len(data), 4):
        word = int.from_bytes(data[offset:offset + 4].ljust(4, b'\0'), 'little')
        value = (((value << 1) | (value >> 31)) + word) & 0xffffffff
    return value


def compile_probe(library):
    subprocess.run(['c++', '-std=c++17', '-shared', '-fPIC', '-D_UNIX=1',
                    '-fsanitize=undefined', '-fno-sanitize-recover=all',
                    '-DNDEBUG', '-Wno-unknown-pragmas',
                    '-I' + str(ROOT / 'port/compatibility/include'),
                    '-I' + str(ROOT / 'staging/wwlib'),
                    '-I' + str(ROOT / 'upstream/CnC_Renegade/Code/wwdebug'),
                    '-include', str(ROOT / 'port/compatibility/include/msvc_compat.h'),
                    str(ROOT / 'staging/wwlib/crc.cpp'),
                    str(ROOT / 'tools/host_network_crc_probe.cpp'), '-o', str(library)],
                   check=True, timeout=30)
    api = ctypes.CDLL(str(library)).network_crc
    api.argtypes = (ctypes.c_void_p, ctypes.c_int, ctypes.c_uint32, ctypes.c_int)
    api.restype = ctypes.c_uint32
    return api


class NetworkCRCTests(unittest.TestCase):
    def test_original_word_width_streaming_and_unaligned_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            call = compile_probe(Path(directory) / 'crc.so')
            for length in (0, 1, 2, 3, 4, 5, 7, 8, 9, 15, 31, 64, 129):
                data = bytes((index * 157 + 91) % 256 for index in range(length))
                for offset in range(4):
                    buffer = ctypes.create_string_buffer(b'x' * offset + data)
                    for initial in (0, 1, 0x80000000, 0xffffffff):
                        for split in (-1, 0, length // 2, length):
                            with self.subTest(length=length, offset=offset, initial=initial, split=split):
                                self.assertEqual(call(ctypes.byref(buffer, offset), length, initial, split),
                                                 expected(data, initial))


if __name__ == '__main__':
    unittest.main()
