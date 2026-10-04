from pathlib import Path
import tempfile
import unittest

from tools.audit_database_chunk_inventory import archive_names


class DatabaseScopeTests(unittest.TestCase):
    def test_case_aliases_and_additional_archives(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            for file in ['ALWAYS.DBS', 'extra.dat', 'M01.MIX', 'ignore.txt']:
                (root / file).touch()
            names = archive_names(root)
            self.assertIn('ALWAYS.DBS', names)
            self.assertNotIn('always.dbs', names)
            self.assertIn('extra.dat', names)
            self.assertNotIn('M01.mix', names)
            self.assertNotIn('ignore.txt', names)
            self.assertIn('M11.mix', names)


if __name__ == '__main__':
    unittest.main()
