import io
import unittest
from audit_archive_literal_references import matches


class LiteralScanTest(unittest.TestCase):
    def test_boundary_matches_are_complete_and_not_duplicated(self):
        data = b'XXAbCdABCDabcd'
        self.assertEqual(list(matches(io.BytesIO(data), 2, 12, [b'abcd'], 3)),
                         [('abcd', 0), ('abcd', 4), ('abcd', 8)])

    def test_member_bounds_exclude_neighbor_bytes(self):
        self.assertEqual(list(matches(io.BytesIO(b'fooabcd'), 0, 5, [b'abcd'], 2)), [])

    def test_truncation_is_not_silent_negative_evidence(self):
        with self.assertRaises(ValueError):
            list(matches(io.BytesIO(b'ab'), 0, 4, [b'abcd'], 2))
