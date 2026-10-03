import unittest
from tools.audit_all_wave_headers import summarize
from tools.audit_mission_wave_headers import inspect_wave
from tools.test_mission_wave_headers import wave, fmt, wave_chunk


class AllWaveTests(unittest.TestCase):
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
