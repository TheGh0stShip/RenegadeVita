import unittest
import struct
from tools.audit_all_wave_headers import summarize, physical_chunks, match_definitions
from tools.audit_mission_wave_headers import inspect_wave
from tools.test_mission_wave_headers import wave, fmt, wave_chunk


class AllWaveTests(unittest.TestCase):
    def test_definition_matching_retains_duplicates_and_labels_basename_candidates(self):
        definitions = {1: {'filename': 'Voice.WAV', 'name': 'a', 'offset': 10},
                       2: {'filename': 'voice.wav', 'name': 'b', 'offset': 20},
                       3: {'filename': 'folder/voice.wav', 'name': 'c', 'offset': 30},
                       4: {'name': 'twiddler', 'offset': 40}}
        matches = match_definitions(definitions, ['VOICE.WAV', 'absent.wav'])
        self.assertEqual([r['definition_id'] for r in matches['VOICE.WAV']], [1, 2, 3])
        self.assertEqual(matches['VOICE.WAV'][2]['filename_match'], 'basename_casefold')
        self.assertEqual(matches['absent.wav'], [])

    def test_outer_size_mismatch_does_not_hide_intact_physical_chunks(self):
        data = wave(fmt(), wave_chunk(b'data', b'\0' * 4))
        altered = data[:4] + struct.pack('<I', len(data) + 100) + data[8:]
        row = physical_chunks(altered)
        self.assertEqual(row['declared_minus_source_bytes'], 108)
        self.assertEqual(row['errors'], [])
        self.assertTrue(row['single_format_and_data'])
        self.assertTrue(row['data_payloads_within_source'])
        self.assertEqual(row['remaining_source_bytes'], 0)

    def test_truncated_payload_and_short_trailer_stay_distinct(self):
        data = wave(fmt(), wave_chunk(b'data', b'\0' * 4))
        self.assertEqual(physical_chunks(data[:-2])['errors'], ['chunk_exceeds_actual_source'])
        self.assertFalse(physical_chunks(data[:-2])['data_payloads_within_source'])
        self.assertEqual(physical_chunks(data + b'x')['errors'], ['incomplete_chunk_header_trailer'])

    def test_odd_unpadded_final_chunk_is_bounded(self):
        row = physical_chunks(wave(fmt(bits=8, align=1), wave_chunk(b'data', b'x', pad=False)))
        self.assertEqual(row['errors'], [])
        self.assertTrue(row['final_odd_padding_absent'])

    def test_duplicates_and_unidentified_formats_remain_in_denominator(self):
        good = wave(fmt(), wave_chunk(b'data', b'\0' * 4))
        members = [{'member': 'VOICE.WAV', 'index_record': index, 'offset': index * 100,
                    'bytes': len(data), 'sha256': 'fixture', 'metadata': inspect_wave(data)}
                   for index, data in enumerate((good, good, b'invalid'))]
        row = summarize('M11.mix', members)
        self.assertEqual(row['wave_members'], 3)
        self.assertEqual(sum(f['members'] for f in row['formats']), 3)
        self.assertEqual(row['header_finding_members'], 1)
        self.assertEqual(row['findings'][0]['index_record'], 2)
        self.assertEqual(row['status'], 'unknown')

    def test_empty_archive_has_explicit_zero_row(self):
        row = summarize('Always2.dat', [])
        self.assertEqual(row['wave_members'], 0)
        self.assertEqual(row['findings'], [])
