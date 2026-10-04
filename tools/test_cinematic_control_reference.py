import unittest
from tools.probe_retail_cinematic_control_parser import reference


class ControlReferenceTests(unittest.TestCase):
    def test_frame_conversion_and_stable_equal_time_order(self):
        rows=reference(b'1 First\n-30 Second\n0 Early\n')
        self.assertEqual(len(rows),3)
        self.assertEqual(rows[0].split(':')[0],'00000000')
        self.assertEqual([r.split(':')[0] for r in rows[1:]],['3f800000','3f800000'])
        self.assertEqual(rows[1:],reference(b'1 First\n1 Second\n'))

    def test_original_signed_character_edge_trim(self):
        self.assertEqual(reference(b'0 Command\xa9\n'),reference(b'0 Command\n'))

    def test_comments_tabs_and_truncation(self):
        self.assertEqual(reference(b'; comment\n0\tCommand\n'),reference(b'0 Command\n'))
        self.assertEqual(reference(b'0 '+b'x'*250+b'\n'),reference(b'0 '+b'x'*197+b'\n'))
