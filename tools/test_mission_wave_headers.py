"""Asset-free malformed WAV and stale/scope receipt counterexamples."""
import contextlib
import io
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from tools.audit_mission_wave_headers import ROOT, audit, basename, candidate_bytes, inspect_wave, main
from tools.audit_mission_conversations import digest
from tools.test_mission_conversations import FakeArchive


class WaveAuditEntrypoint(unittest.TestCase):
    def test_direct_script_help_outside_repository(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [sys.executable, str(ROOT / 'tools/audit_mission_wave_headers.py'), '--help'],
                cwd=directory, capture_output=True, text=True, check=True)
        self.assertIn('--conversations-directory', result.stdout)
        self.assertEqual(result.stderr, '')


def wave_chunk(kind, data, pad=True):
    return kind + struct.pack('<I', len(data)) + data + (b'\0' if pad and len(data) & 1 else b'')


def wave(*children):
    body = b'WAVE' + b''.join(children)
    return b'RIFF' + struct.pack('<I', len(body)) + body


def fmt(tag=1, channels=1, rate=22050, align=2, bits=16, spb=9, count=1):
    data = struct.pack('<HHIIHH', tag, channels, rate, rate * align, align, bits)
    if tag in (2, 17):
        data += struct.pack('<HH', 2, spb)
    if tag == 2:
        data += struct.pack('<H', count) + struct.pack('<hh', 256, 0) * count
    return wave_chunk(b'fmt ', data)


class MissionWaveHeadersTests(unittest.TestCase):
    def test_supported_pcm_metadata_is_not_a_decode_or_playback_pass(self):
        row = inspect_wave(wave(fmt(), wave_chunk(b'data', b'\0' * 8)))
        self.assertEqual(row['estimated_frames'], 4)
        self.assertEqual(row['estimated_pcm_bytes'], 8)
        self.assertTrue(row['header_conditions_satisfied'])
        self.assertFalse(row['runtime_decode_or_playback_verified'])

    def test_pcm8_stereo_width_and_rate_are_explicit(self):
        row = inspect_wave(wave(fmt(channels=2, bits=8, rate=44100), wave_chunk(b'data', b'\0' * 4)))
        self.assertEqual(row['estimated_frames'], 2)
        self.assertEqual(row['format']['sample_rate'], 44100)

    def test_unknown_chunks_and_odd_padding_do_not_shift_format_or_data(self):
        row = inspect_wave(wave(wave_chunk(b'JUNK', b'x'), fmt(), wave_chunk(b'data', b'\0' * 2)))
        self.assertEqual(row['header_findings'], [])
        self.assertEqual(row['unparsed_riff_bytes'], 0)
        self.assertEqual(row['estimated_frames'], 1)

    def test_final_odd_chunk_without_pad_retains_current_header_behavior(self):
        row = inspect_wave(wave(fmt(bits=8, align=1), wave_chunk(b'data', b'x', pad=False)))
        self.assertTrue(row['final_odd_chunk_padding_absent'])
        self.assertTrue(row['header_conditions_satisfied'])

    def test_riff_lengths_are_checked_against_actual_bytes(self):
        valid = wave(fmt(), wave_chunk(b'data', b'\0' * 2))
        for size in [0, len(valid) + 10]:
            bad = valid[:4] + struct.pack('<I', size) + valid[8:]
            self.assertIn('riff_length_outside_source', inspect_wave(bad)['header_findings'])

    def test_trailing_source_bytes_are_not_promoted_to_riff_chunks(self):
        row = inspect_wave(wave(fmt(), wave_chunk(b'data', b'\0' * 2)) + b'trailing')
        self.assertEqual(row['trailing_source_bytes'], 8)
        self.assertEqual(row['estimated_frames'], 1)

    def test_chunk_size_overrun_and_absent_format_or_data_stay_findings(self):
        self.assertIn('chunk_outside_riff', inspect_wave(wave(b'fmt ' + struct.pack('<I', 0xffffffff)))['header_findings'])
        self.assertIn('format_absent', inspect_wave(wave(wave_chunk(b'data', b'\0' * 2)))['header_findings'])
        self.assertIn('data_absent', inspect_wave(wave(fmt()))['header_findings'])

    def test_duplicate_format_and_data_are_not_accepted_as_one_header(self):
        for children, finding in [( [fmt(), fmt(), wave_chunk(b'data', b'\0' * 2)], 'duplicate_format_chunk'),
                                   ([fmt(), wave_chunk(b'data', b'\0' * 2), wave_chunk(b'data', b'\0' * 2)], 'duplicate_data_chunk')]:
            row = inspect_wave(wave(*children))
            self.assertIn(finding, row['header_findings'])
            self.assertNotIn('header_conditions_satisfied', row)

    def test_unknown_codecs_and_format_limits_are_recorded(self):
        for arguments, finding in [({'tag': 0x55}, 'unsupported_wave_tag_in_current_provider'),
                                   ({'channels': 3}, 'invalid_format_values'),
                                   ({'rate': 7999}, 'invalid_format_values'),
                                   ({'align': 0}, 'invalid_format_values'),
                                   ({'bits': 24}, 'invalid_pcm_layout')]:
            row = inspect_wave(wave(fmt(**arguments), wave_chunk(b'data', b'\0' * 4)))
            self.assertIn(finding, row['header_findings'])

    def test_short_format_and_adpcm_extensions_are_rejected(self):
        row = inspect_wave(wave(wave_chunk(b'fmt ', b'\0' * 15), wave_chunk(b'data', b'\0' * 4)))
        self.assertIn('truncated_format_chunk', row['header_findings'])
        payload = struct.pack('<HHIIHH', 17, 1, 22050, 1, 8, 4)
        row = inspect_wave(wave(wave_chunk(b'fmt ', payload), wave_chunk(b'data', b'\0' * 8)))
        self.assertIn('truncated_adpcm_extension', row['header_findings'])

    def test_ima_step_index_counterexample_passes_format_but_not_block_metadata(self):
        row = inspect_wave(wave(fmt(tag=17, align=8, bits=4), wave_chunk(b'data', bytes([0, 0, 89, 0]) + b'\0' * 4)))
        self.assertTrue(row['header_conditions_satisfied'])
        self.assertEqual(row['block_findings'], [{'kind': 'ima_step_index_outside_table', 'count': 1}])

    def test_partial_ima_block_and_fact_trimming_are_separate_metadata(self):
        row = inspect_wave(wave(fmt(tag=17, align=8, bits=4), wave_chunk(b'fact', struct.pack('<I', 10)),
                                wave_chunk(b'data', b'\0' * 13)))
        self.assertEqual(row['complete_block_count'], 1)
        self.assertEqual(row['remainder_bytes'], 5)
        self.assertEqual(row['estimated_frames'], 12)
        self.assertEqual(row['metadata_frames'], 10)
        self.assertEqual(row['fact_minus_estimated_frames'], -2)
        self.assertEqual(row['adpcm_blocks_inspected'], 2)

    def test_short_adpcm_block_and_reserved_byte_have_distinct_treatment(self):
        short = inspect_wave(wave(fmt(tag=17, align=8, bits=4), wave_chunk(b'data', b'\0' * 3)))
        self.assertEqual(short['block_findings'][0]['kind'], 'adpcm_block_header_truncated')
        reserved = inspect_wave(wave(fmt(tag=17, align=8, bits=4), wave_chunk(b'data', b'\0\0\0\x01' + b'\0' * 4)))
        self.assertEqual(reserved['ima_reserved_nonzero'], 1)
        self.assertEqual(reserved['block_findings'], [])

    def test_last_fact_write_wins_and_zero_uses_estimate(self):
        row = inspect_wave(wave(fmt(), wave_chunk(b'fact', struct.pack('<I', 100)),
                                wave_chunk(b'data', b'\0' * 8), wave_chunk(b'fact', struct.pack('<I', 0))))
        self.assertEqual(row['metadata_frames'], 4)
        self.assertEqual(row['fact_frames'], 0)

    def test_ms_adpcm_coefficients_and_block_predictor_are_checked_separately(self):
        bad_coeff = inspect_wave(wave(fmt(tag=2, align=8, bits=4, count=0), wave_chunk(b'data', b'\0' * 8)))
        self.assertIn('invalid_ms_adpcm_coefficient_layout', bad_coeff['header_findings'])
        bad_predictor = inspect_wave(wave(fmt(tag=2, align=8, bits=4), wave_chunk(b'data', b'\x01' + b'\0' * 7)))
        self.assertEqual(bad_predictor['block_findings'][0]['kind'], 'ms_adpcm_predictor_outside_coefficients')

    def test_empty_data_can_pass_headers_without_proving_decoded_audio(self):
        row = inspect_wave(wave(fmt(), wave_chunk(b'data', b'')))
        self.assertTrue(row['header_conditions_satisfied'])
        self.assertEqual(row['metadata_frames'], 0)
        self.assertFalse(row['runtime_decode_or_playback_verified'])

    def test_candidate_hash_size_and_path_mismatches_are_rejected(self):
        archive = FakeArchive('always.dat', {'voice.wav': b'fixture'})
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for candidate in [{'archive': 'always.dat', 'member': 'voice.wav', 'sha256': 'wrong', 'bytes': 7},
                              {'archive': 'always.dat', 'member': 'voice.wav', 'sha256': digest(b'fixture'), 'bytes': 8},
                              {'archive': '../always.dat', 'member': 'voice.wav', 'sha256': 'wrong', 'bytes': 7}]:
                with self.assertRaises(ValueError):
                    candidate_bytes(root, candidate, {'always.dat': archive})
        for name in ('../voice.wav', 'a\\voice.wav', '', '.'):
            with self.assertRaises(ValueError):
                basename(name)

    def test_outside_root_loose_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / 'data'; root.mkdir()
            target = Path(temp) / 'outside'; target.write_bytes(b'fixture')
            (root / 'voice.wav').symlink_to(target)
            with self.assertRaises(ValueError):
                candidate_bytes(root, {'archive': None, 'member': 'voice.wav', 'sha256': digest(b'fixture')}, {})

    def test_receipt_without_definition_provenance_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            data = Path(temp); (data / 'M13.mix').write_bytes(b'fixture')
            with self.assertRaisesRegex(ValueError, 'definition database provenance'):
                audit(ROOT, data, {'map': 'M13.mix', 'archive_sha256': digest(b'fixture')},
                      archives={'M13.mix': FakeArchive('M13.mix', {})})

    def scoped_fixture(self):
        good = wave(fmt(), wave_chunk(b'data', b'\0' * 4))
        unsupported = wave(fmt(tag=0x55), wave_chunk(b'data', b'\0' * 4))
        archives = {'M13.mix': FakeArchive('M13.mix', {'m13.ldd': b'level'}),
                    'always.dbs': FakeArchive('always.dbs', {'objects.ddb': b'definitions', 'conv10.cdb': b'global',
                                                           'strings.tdb': b'first', 'second.wav': unsupported}),
                    'always.dat': FakeArchive('always.dat', {'strings.tdb': b'second', 'first.wav': good})}
        def identity(archive, member):
            payload = archives[archive].read_binary(member)
            return {'archive': archive, 'member': member, 'sha256': digest(payload), 'bytes': len(payload)}
        variants = []
        for database, archive, member in [('always.dbs', 'always.dat', 'first.wav'), ('always.dat', 'always.dbs', 'second.wav')]:
            candidate = identity(archive, member)
            chain = {'text_id': 1001, 'sound_leaves': [{'id': 7, 'candidates': [candidate]}]}
            global_only = {'text_id': 2001, 'sound_leaves': [{'id': 8, 'candidates': [candidate]}]}
            variants.append({**identity(database, 'strings.tdb'), 'chains': [chain, global_only], 'findings': []})
        return archives, {'map': 'M13.mix', 'archive_sha256': digest(b'fixture'),
                          'level_members': [identity('M13.mix', 'm13.ldd')],
                          'definition_databases': [identity('always.dbs', 'objects.ddb')],
                          'global_databases': [identity('always.dbs', 'conv10.cdb')],
                          'level_conversations': [{'remarks': [{'text_id': 1001}]}],
                          'string_database_candidates': variants}

    def test_authored_scope_and_string_alternatives_stay_independent(self):
        archives, receipt = self.scoped_fixture()
        with tempfile.TemporaryDirectory() as temp:
            data = Path(temp); (data / 'M13.mix').write_bytes(b'fixture')
            result = audit(ROOT, data, receipt, archives=archives)
        variants = result['database_variants']
        self.assertEqual([v['summary']['candidate_references'] for v in variants], [1, 1])
        self.assertEqual([v['summary']['header_finding_files'] for v in variants], [0, 1])
        self.assertFalse(result['runtime_or_physical_acceptance'])
        self.assertFalse(result['complete_mission_closure'])

    def test_stale_definition_and_translation_members_are_rejected(self):
        for member in ['objects.ddb', 'strings.tdb']:
            archives, receipt = self.scoped_fixture()
            archives['always.dbs'].entries[member] = b'changed'
            with tempfile.TemporaryDirectory() as temp:
                data = Path(temp); (data / 'M13.mix').write_bytes(b'fixture')
                with self.assertRaisesRegex(ValueError, 'no longer matches'):
                    audit(ROOT, data, receipt, archives=archives)

    def test_private_output_is_required_before_reading_receipts(self):
        with tempfile.TemporaryDirectory() as temp, contextlib.redirect_stderr(io.StringIO()), \
             patch('sys.argv', ['audit', '--root', temp, '--data', temp, '--conversations-directory', temp,
                                '--output-directory', str(Path(temp) / 'reports')]), self.assertRaises(SystemExit):
            main()


if __name__ == '__main__':
    unittest.main()
