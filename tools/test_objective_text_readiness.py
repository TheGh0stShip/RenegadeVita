"""Asset-free checks for the objective text/glyph readiness audit helpers."""
import struct
import unittest

from tools.audit_objective_text_readiness import glyph_rows, render_report, ttf_codepoints


def synthetic_ttf(first, last, delta):
    """Minimal TrueType with one format-4 cmap segment (plus the 0xFFFF terminator)."""
    segments = [(first, last, delta, 0), (0xFFFF, 0xFFFF, 1, 0)]
    count = len(segments)
    body = struct.pack('>HHHHHHH', 4, 0, 0, count * 2, 0, 0, 0)
    body += b''.join(struct.pack('>H', s[1]) for s in segments) + b'\0\0'
    body += b''.join(struct.pack('>H', s[0]) for s in segments)
    body += b''.join(struct.pack('>h', s[2]) for s in segments)
    body += b''.join(struct.pack('>H', s[3]) for s in segments)
    body = body[:2] + struct.pack('>H', len(body)) + body[4:]
    cmap = struct.pack('>HH', 0, 1) + struct.pack('>HHI', 3, 1, 12) + body
    header = struct.pack('>IHHHH', 0x00010000, 1, 16, 0, 0) + struct.pack('>4sIII', b'cmap', 0, 28, len(cmap))
    return header + cmap


class ObjectiveTextReadinessTests(unittest.TestCase):
    def test_format4_cmap_reports_only_nonzero_glyph_mappings(self):
        data = synthetic_ttf(0xE0, 0xE2, 1)  # U+00E0..U+00E2 -> glyphs 0xE1..0xE3
        self.assertEqual(ttf_codepoints(data), {0xE0, 0xE1, 0xE2})
        self.assertEqual(ttf_codepoints(synthetic_ttf(0x20, 0x21, -0x20)), {0x21})  # code 0x20 maps to glyph 0

    def test_newline_is_a_row_break_not_a_glyph_gap(self):
        maps = [{'glyph_gaps': [
            {'candidate': 'a', 'language_index': 0, 'codepoint': 10, 'covered': {'f': False}, 'ids': [1]},
            {'candidate': 'a', 'language_index': 4, 'codepoint': 0x4E00, 'covered': {'f': False}, 'ids': [2]},
            {'candidate': 'a', 'language_index': 4, 'codepoint': 0xE9, 'covered': {'f': True}, 'ids': [2]}]}]
        rows = {r['language']: r for r in glyph_rows(maps, ['f'])}
        self.assertEqual(rows[0]['codepoints'], 0)
        self.assertEqual(rows[4]['uncovered'], {'f': [0x4E00]})

    def test_report_names_unresolved_ids_without_text(self):
        summary = {'candidates': {'always.dat': {'sha256': 'x', 'ids': 1, 'languages_per_id': [1]}},
                   'fonts': {'f': {'role': 'primary', 'bytes': 1, 'sha256': 'y', 'codepoints': 1}},
                   'maps': [{'map': 'M99.mix', 'findings': [{'id': 77, 'names': ['IDS_X'], 'kind': 'missing_in_tdb',
                                                             'candidate': 'always.dat', 'calls': [{'script': 'S', 'line': 5}]}],
                             'unresolved_expressions': [], 'per_command': {'Add_Objective': 1}, 'unique_text_ids': 1,
                             'closure_vs_owner': {'closure_text_ids': 1, 'owner_lead_only_text_ids': 0},
                             'objective_refs_without_add': [], 'radar_marker_calls': 0, 'radar_invalid_literals': [],
                             'encyclopedia_calls': [], 'glyph_gaps': []}]}
        text = render_report(summary, 'z')
        self.assertIn('ID 77 [\'IDS_X\'] missing_in_tdb in always.dat (S:5)', text)
        self.assertIn('**1**', text)


if __name__ == '__main__':
    unittest.main()
