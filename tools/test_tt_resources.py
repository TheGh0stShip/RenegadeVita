"""TT resource messages using original bitpacker, including unaligned fields."""
import ctypes
import json
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def header(group=1, name=b'fixture', count=0):
    return struct.pack('>IIH', 0, group, len(name)) + name + struct.pack('>I', count)


class ResourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        library = Path(cls.directory.name) / 'resource.so'
        subprocess.run(['c++', '-std=c++17', '-shared', '-fPIC', '-D_UNIX=1', '-DNDEBUG',
                        '-DRENEGADE_HOST_ABI_TEST=1',
                        '-fsanitize=undefined', '-fno-sanitize-recover=all', '-Wno-unknown-pragmas',
                        '-include', str(ROOT / 'port/compatibility/include/msvc_compat.h'),
                        *['-I' + str(ROOT / path) for path in ('port/platform', 'port/compatibility/include',
                          'staging/wwbitpack', 'staging/wwlib', 'upstream/CnC_Renegade/Code/wwdebug')],
                        str(ROOT / 'staging/wwbitpack/BitPacker.cpp'),
                        str(ROOT / 'tools/host_tt_resources_probe.cpp'), '-o', str(library)],
                       check=True, timeout=30)
        cls.api = ctypes.CDLL(str(library))
        cls.api.resources_create.restype = ctypes.c_void_p
        for name in ('destroy', 'reset', 'groups', 'remaining', 'generation'):
            getattr(cls.api, 'resources_' + name).argtypes = (ctypes.c_void_p,)
        cls.api.resources_receive.argtypes = (ctypes.c_void_p, ctypes.c_char_p, ctypes.c_uint, ctypes.c_uint)
        for name in ('id', 'name', 'count'):
            getattr(cls.api, 'resources_' + name).argtypes = (ctypes.c_void_p, ctypes.c_uint)
        cls.api.resources_id.restype = ctypes.c_uint
        cls.api.resources_name.restype = ctypes.c_char_p
        cls.api.resources_package.argtypes = (ctypes.c_void_p, ctypes.c_uint, ctypes.c_uint)
        cls.api.resources_package.restype = ctypes.c_uint

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def setUp(self):
        self.state = self.api.resources_create()

    def tearDown(self):
        self.api.resources_destroy(self.state)

    def feed(self, payload, bits=None, prefix=0):
        return bool(self.api.resources_receive(self.state, payload,
                    len(payload) * 8 if bits is None else bits, prefix))

    def test_reference_serializer_fixtures(self):
        # Synthetic bytes emitted by the independently executed pinned TT code.
        fixture = ROOT / 'tools/fixtures/tt_resource_b9000.json'
        record = json.loads(fixture.read_text())
        self.assertEqual(record['reference_sha256'],
                         'd520443f5618b7d34d48a2e1d4b8348516d53d3ac9a7e201077e259f64c100db')
        for case in record['cases']:
            for prefix in range(8):
                self.api.resources_reset(self.state)
                for packet in case['packets']:
                    self.assertTrue(self.feed(bytes.fromhex(packet['hex']), packet['bits'], prefix),
                                    (case['id'], prefix, packet))
                self.assertEqual(self.api.resources_groups(self.state), 1)
                self.assertEqual(self.api.resources_remaining(self.state), 0)
                self.assertEqual(self.api.resources_id(self.state, 0), case['id'])
                self.assertEqual(self.api.resources_name(self.state, 0), case['name'].encode())
                self.assertEqual(self.api.resources_count(self.state, 0), len(case['packages']))
                got = [self.api.resources_package(self.state, 0, i) for i in range(len(case['packages']))]
                self.assertEqual(got, list(reversed(case['packages'])))
                self.assertTrue(self.feed(bytes.fromhex(case['remove'][0]['hex']), prefix=prefix))
                self.assertEqual(self.api.resources_groups(self.state), 0)

    def test_every_truncation_and_trailing_bit(self):
        for payload, pending in ((header(), False), (struct.pack('>II', 1, 1), False),
                                 (struct.pack('>II', 0, 123), True)):
            for bits in range(len(payload) * 8):
                self.api.resources_reset(self.state)
                if pending:
                    self.assertTrue(self.feed(header(count=1)))
                self.assertFalse(self.feed(payload, bits))
                self.assertEqual(self.api.resources_groups(self.state), 0)
                self.assertFalse(self.feed(header()))  # Failure is sticky until disconnect/reset.
            self.api.resources_reset(self.state)
            if pending:
                self.assertTrue(self.feed(header(count=1)))
            self.assertFalse(self.feed(payload + b'\0', len(payload) * 8 + 1))

    def test_atomic_replacement_limits_and_reset(self):
        self.assertTrue(self.feed(header(name=b'old')))
        self.assertTrue(self.feed(header(name=b'new', count=2)))
        self.assertEqual(self.api.resources_name(self.state, 0), b'old')
        self.assertTrue(self.feed(struct.pack('>II', 0, 10)))
        self.assertEqual(self.api.resources_name(self.state, 0), b'old')
        self.assertTrue(self.feed(struct.pack('>II', 0, 11)))
        self.assertEqual(self.api.resources_name(self.state, 0), b'new')
        self.assertEqual(self.api.resources_generation(self.state), 2)
        for group in range(2, 65):
            self.assertTrue(self.feed(header(group=group)))
        self.assertFalse(self.feed(header(group=65)))
        for invalid in (header(count=4097), header(name=b'x' * 256),
                        header(name=b'bad\0name'), header(name=b'bad\nname'), struct.pack('>II', 2, 0)):
            self.api.resources_reset(self.state)
            self.assertFalse(self.feed(invalid))
        self.api.resources_reset(self.state)
        self.assertTrue(self.feed(header(count=4096)))
        for _ in range(4096):
            self.assertTrue(self.feed(struct.pack('>II', 0, 123)))
        self.assertFalse(self.feed(header(group=2, count=1)))
        self.api.resources_reset(self.state)
        self.assertEqual(self.api.resources_generation(self.state), 0)
        self.assertTrue(self.feed(header()))


if __name__ == '__main__':
    unittest.main()
