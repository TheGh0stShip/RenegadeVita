import hashlib
import unittest
from tools.probe_host_mix_text_commands import expected


class TextExpectations(unittest.TestCase):
    def test_lf_only_and_final_line(self):
        digest,count=expected(b'a\rb\nlast')
        self.assertEqual(count,2)
        self.assertEqual(digest,hashlib.sha256(b'a\rb\n\0last').hexdigest())

    def test_original_199_byte_limit_consumes_remainder(self):
        digest,count=expected(b'x'*300+b'\nnext\n')
        self.assertEqual(count,2)
        self.assertEqual(digest,hashlib.sha256(b'x'*199+b'\0next\n').hexdigest())

    def test_empty_and_nul_stop_transport(self):
        self.assertEqual(expected(b''),(hashlib.sha256(b'').hexdigest(),0))
        self.assertEqual(expected(b'\0hidden\nnext'),(hashlib.sha256(b'').hexdigest(),0))
