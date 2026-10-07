"""Asset-free checks for the cinematic command coverage audit."""
import unittest

from tools.audit_cinematic_command_coverage import (
    NAMES, argument_findings, classify, parse_payload, split_lines,
)


def first(text):
    records, _ = parse_payload(text.encode('latin1'))
    return classify(records[0])


class CinematicCommandCoverageTest(unittest.TestCase):
    def test_titles_match_original_title_match_order(self):
        self.assertEqual(len(NAMES), 18)
        self.assertEqual(NAMES[0], 'Create_Object')
        self.assertEqual(NAMES[-1], 'Set_Screen_Fade_Opacity')

    def test_case_insensitive_title_and_negative_frame_time(self):
        records, _ = parse_payload(b'-30\tCREATE_object, 3, Model\r\n')
        self.assertEqual(records[0]['seconds'], 1.0)
        info = classify(records[0])
        self.assertEqual((info['command'], info['args']), ('Create_Object', ['3', 'Model']))
        self.assertIn('title_case_differs_from_canonical', argument_findings(info))

    def test_banner_without_semicolon_is_time_zero_unknown(self):
        records, notes = parse_payload(b'*********** MIDTRO 2K ****\n5 Destroy_Object, 1\n')
        self.assertEqual(records[0]['seconds'], 0.0)
        self.assertIsNone(classify(records[0])['command'])
        self.assertIn('time_token_not_numeric_atof_zero', [n for _, n in notes])

    def test_comment_blank_and_time_only_lines_are_skipped(self):
        records, notes = parse_payload(b'; comment\n\n7\n10 Move_Slot, 1, 2\n')
        self.assertEqual(len(records), 1)
        self.assertIn('time_without_command_ignored', [n for _, n in notes])

    def test_no_comma_means_original_handler_reads_empty_arguments(self):
        info = first('0 Destroy_Object')
        self.assertEqual(info['args'], [])
        self.assertIn('no_args_default_slot0_or_empty', argument_findings(info))

    def test_text_in_numeric_slot_positions_is_flagged(self):
        info = first('0 Attach_To_Bone, 3, Bn_Trajectory')
        self.assertIn('nonnumeric_host_slot', argument_findings(info))

    def test_attach_detach_slots(self):
        self.assertIn('detach_host_slot_minus1', argument_findings(first('0 Attach_To_Bone, 3, -1, Bone')))
        self.assertIn('detach_via_out_of_range_host_slot', argument_findings(first('0 Attach_To_Bone, 3, -2, Bone')))

    def test_unguarded_host_slot_out_of_range_is_flagged(self):
        self.assertIn('UNGUARDED_slot_out_of_range_host_slot',
                      argument_findings(first('0 Create_Real_Object, 1, Preset, 55, Bone')))

    def test_extra_arguments_and_long_line_truncation(self):
        self.assertIn('extra_args_ignored', argument_findings(first('0 Create_Object, 1, M, 0, 0, 0, 0')))
        line = b'0 Create_Object, 1, ' + b'x' * 400 + b'\n'
        self.assertTrue(split_lines(line)[0][2])
        self.assertEqual(len(split_lines(line)[0][1]), 199)

    def test_unsigned_char_does_not_treat_high_bytes_as_blanks(self):
        payload = b'\xa05 Move_Slot, 1, 2\n'
        signed, _ = parse_payload(payload, signed_char=True)
        unsigned, _ = parse_payload(payload, signed_char=False)
        self.assertEqual(signed[0]['token'], '5')
        self.assertEqual(unsigned[0]['token'], '\xa05')


if __name__ == '__main__':
    unittest.main()
