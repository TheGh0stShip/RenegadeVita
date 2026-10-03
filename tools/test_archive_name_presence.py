import unittest
from tools.audit_archive_name_presence import resolve


class NamePresenceTests(unittest.TestCase):
    def test_case_matching_duplicate_records_and_loose_locations(self):
        rows = resolve(['A.TXT', 'absent.txt'],
                       [('always.dat', 1, 'a.txt', 100, 5),
                        ('always.dat', 2, 'A.TXT', 200, 8)], ['sub/A.txt', 'other.txt'])
        self.assertEqual(len(rows[0]['archive_candidates']), 2)
        self.assertEqual(rows[0]['loose_candidates'], ['sub/A.txt'])
        self.assertEqual(rows[1]['archive_candidates'], [])
        self.assertTrue(all(row['status'] == 'unknown' for row in rows))
