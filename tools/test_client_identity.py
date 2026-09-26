"""Synthetic protocol and private provisioning tests; no real keys or network."""
import ctypes
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from configure_client_identity import derive, store

ROOT = Path(__file__).resolve().parents[1]


class ClientIdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        library = Path(cls.temp.name) / "identity.so"
        subprocess.run(["c++", "-std=c++17", "-shared", "-fPIC", "-Wall", "-Wextra",
                        "-Wno-unknown-pragmas", "-I" + str(ROOT / "staging/wwlib"),
                        "-I" + str(ROOT / "port/platform"),
                        str(ROOT / "staging/wwlib/md5.cpp"),
                        str(ROOT / "port/platform/renegade_client_identity.cpp"),
                        str(ROOT / "tools/host_client_identity_probe.cpp"),
                        "-o", str(library)], check=True, timeout=30)
        cls.library = ctypes.CDLL(str(library))
        cls.call = cls.library.identity_response
        cls.call.argtypes = (ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint32, ctypes.c_char_p)
        cls.call.restype = ctypes.c_bool
        cls.hash = cls.library.identity_hash
        cls.hash.argtypes = (ctypes.c_char_p, ctypes.c_char_p)
        cls.hash.restype = ctypes.c_bool

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_response_vectors(self):
        seed = hashlib.md5(b"synthetic-protocol-fixture-not-a-key").hexdigest()
        for challenge in ("", "test-challenge", "A" * 128):
            for nonce in (0, 1, 65534, 65535, 0x12345678, 0xffffffff):
                output = ctypes.create_string_buffer(73)
                self.assertTrue(self.call(seed.encode(), challenge.encode(), nonce, output))
                expected = (hashlib.md5(seed.encode()).hexdigest() + "%08x" % nonce +
                            hashlib.md5((seed + str(nonce % 65535) + challenge).encode()).hexdigest())
                self.assertEqual(output.value.decode(), expected)

    def test_greeting_hash_is_second_digest_not_seed(self):
        for seed in (b'0' * 32, b'a' * 32, hashlib.md5(b'synthetic fixture').hexdigest().encode()):
            output = ctypes.create_string_buffer(33)
            self.assertTrue(self.hash(seed, output))
            self.assertEqual(output.value, hashlib.md5(seed).hexdigest().encode())
            self.assertNotEqual(output.value, seed)
        for invalid in (None, b'', b'a' * 31, b'a' * 33, b'G' * 32):
            output = ctypes.create_string_buffer(b'x' * 32, 33)
            self.assertFalse(self.hash(invalid, output))
            self.assertEqual(output.raw, b'\0' * 33)

    def test_invalid_input_clears_output(self):
        seed = b"a" * 32
        for first, second in ((None, b""), (seed, None), (b"a" * 31, b""),
                              (b"g" * 32, b""), (b"A" * 32, b""),
                              (seed, b"b" * 129)):
            output = ctypes.create_string_buffer(b"x" * 72, 73)
            self.assertFalse(self.call(first, second, 0, output))
            self.assertEqual(output.raw, b"\0" * 73)

    def test_numeric_normalization(self):
        self.assertEqual(derive("123456-123456-123456-1234"), derive("1234561234561234561234"))
        for invalid in ("", "a" * 22, "1" * 21, "1" * 23, "1" * 22 + "\n"):
            with self.assertRaises(ValueError):
                derive(invalid)

    def test_private_creation_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tt-identity-v1.txt"
            store(path, "a" * 32)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            with self.assertRaises(FileExistsError):
                store(path, "b" * 32)
            self.assertEqual(path.read_text(), "a" * 32 + "\n")

    def test_public_directory_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            os.chmod(directory, 0o755)
            with self.assertRaises(ValueError):
                store(Path(directory) / "tt-identity-v1.txt", "a" * 32)

    def test_admission_redaction(self):
        for value in ("123456-123456-123456-1234", "1" * 22, "abcdef12" * 9):
            text = ctypes.create_string_buffer(("Rejected " + value + "\nreason").encode())
            self.library.redact_admission(text)
            self.assertEqual(text.value.decode(), "Rejected " + "*" * len(value) + " reason")
        text = ctypes.create_string_buffer(b"TT 4.8 required\x1b")
        self.library.redact_admission(text)
        self.assertEqual(text.value, b"TT 4.8 required ")


if __name__ == "__main__":
    unittest.main()
