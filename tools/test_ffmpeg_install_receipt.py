"""Check that stale/corrupt dependency outputs cannot satisfy local reuse."""
from pathlib import Path
import tempfile
import unittest

from tools.ffmpeg_install_receipt import LIBRARIES, RECEIPT, record, verify


class InstallReceiptTests(unittest.TestCase):
    def test_identity_and_every_installed_file_are_required(self):
        with tempfile.TemporaryDirectory() as directory:
            prefix = Path(directory)
            (prefix / 'lib').mkdir()
            (prefix / 'include/libavutil').mkdir(parents=True)
            header = prefix / 'include/libavutil/tx.h'
            header.write_text('enum AVTXType;\n')
            for name in LIBRARIES:
                (prefix / f'lib/lib{name}.a').write_bytes(b'archive')
            key = 'a' * 64
            self.assertFalse(verify(prefix, key))
            record(prefix, key)
            self.assertTrue(verify(prefix, key))
            self.assertFalse(verify(prefix, 'b' * 64))
            extra = prefix / 'include/libavutil/new.h'
            extra.write_text('new header\n')
            self.assertFalse(verify(prefix, key))
            extra.unlink()
            header.write_text('changed ABI\n')
            self.assertFalse(verify(prefix, key))
            record(prefix, key)
            link = prefix / 'lib/libextra.a'
            link.symlink_to(prefix / 'lib/libavutil.a')
            self.assertFalse(verify(prefix, key))
            with self.assertRaisesRegex(ValueError, 'symlink'):
                record(prefix, key)
            link.unlink()
            archive = prefix / 'lib/libavcodec.a'
            archive.write_bytes(b'corrupt archive')
            self.assertFalse(verify(prefix, key))
            record(prefix, key)
            archive.unlink()
            self.assertFalse(verify(prefix, key))
            with self.assertRaises(ValueError):
                record(prefix, key)

    def test_malformed_receipt_and_symlinks_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            prefix = Path(directory)
            (prefix / RECEIPT).write_text('{bad json')
            self.assertFalse(verify(prefix, 'a' * 64))
            (prefix / 'include').symlink_to(prefix, target_is_directory=True)
            self.assertFalse(verify(prefix, 'a' * 64))
            with self.assertRaisesRegex(ValueError, 'directory symlink'):
                record(prefix, 'a' * 64)

    def test_invalid_identity_cannot_create_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            prefix = Path(directory)
            for key in ('A'*64, 'a'*63, ''):
                with self.assertRaisesRegex(ValueError, 'identity'):
                    record(prefix, key)
                self.assertFalse((prefix / RECEIPT).exists())


if __name__ == '__main__':
    unittest.main()
