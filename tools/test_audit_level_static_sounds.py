"""Synthetic-data tests for tools.audit_level_static_sounds (no retail data)."""
import struct
import unittest

from tools import audit_level_static_sounds as audit


def chunk(chunk_id, payload, children=False):
    return struct.pack('<II', chunk_id, len(payload) | (0x80000000 if children else 0)) + payload


def micro(micro_id, payload):
    return bytes((micro_id, len(payload))) + payload


def sound_record(class_id, filename, drop_off=50.0, max_vol=2.0, loop=0, sound_type=1):
    identity = struct.pack('<12f', 1, 0, 0, 7.0, 0, 1, 0, 8.0, 0, 0, 1, 9.0)
    audible = b''.join([
        micro(2, struct.pack('<i', sound_type)), micro(6, struct.pack('<i', loop)),
        micro(10, identity), micro(14, struct.pack('<f', drop_off)),
        micro(15, filename.encode() + b'\0'), micro(16, b'\0\0\0\0')])
    sound3d = micro(5, struct.pack('<f', max_vol)) + micro(6, b'\x01')
    audible_chunks = chunk(0x101, b'', False) + chunk(audit.CHUNKID_AUDIBLE_VARIABLES, audible)
    base = chunk(0x11090956, audible_chunks, True)
    body = chunk(0x100100, b'\0\0\0\0') + chunk(
        0x100101, base + chunk(0x11090955, sound3d), True)
    return chunk(class_id, body, True)



def wave(tag=1, channels=1, rate=22050, bits=16, frames=100):
    align = channels * bits // 8
    data = b'\0' * (frames * align)
    fmt = struct.pack('<HHIIHH', tag, channels, rate, rate * align, align, bits)
    body = b'WAVE' + chunk(0x20746d66, fmt) + chunk(0x61746164, data)
    return b'RIFF' + struct.pack('<I', len(body)) + body


class LevelStaticSoundTests(unittest.TestCase):
    def test_static_sound_parsing_and_classes(self):
        sounds = (sound_record(audit.CHUNKID_SOUND3D, 'amb_a.wav') +
                  sound_record(audit.CHUNKID_PSEUDO_SOUND3D, 'amb_b.wav', loop=-1))
        static = chunk(audit.CHUNKID_STATIC_SOUNDS, sounds, True)
        scene = chunk(audit.CHUNKID_SCENE_VARIABLES, b'') + static
        lsd = chunk(0x20000, b'') + chunk(
            audit.CHUNKID_STATIC_SAVELOAD, chunk(audit.CHUNKID_STATIC_SCENE, scene, True), True)
        records, findings = audit.static_sounds(lsd)
        self.assertEqual(findings, [])
        self.assertEqual([r['class'] for r in records], ['Sound3DClass', 'SoundPseudo3DClass'])
        self.assertEqual([r['filename'] for r in records], ['amb_a.wav', 'amb_b.wav'])
        self.assertEqual(records[1]['loop_count'], -1)
        self.assertAlmostEqual(records[0]['drop_off'], 50.0)
        self.assertAlmostEqual(records[0]['max_vol_radius'], 2.0)
        self.assertEqual(records[0]['position'], (7.0, 8.0, 9.0))

    def test_missing_subsystem_is_reported(self):
        records, findings = audit.static_sounds(chunk(0x20000, b''))
        self.assertEqual(records, [])
        self.assertEqual(findings, ['static_audio_subsystem_chunk_absent'])

    def test_dynamic_audio_nested_under_level_wrapper(self):
        variables = micro(4, struct.pack('<f', 1.0)) + micro(5, b'07-song.mp3\0')
        dynamic = chunk(audit.CHUNKID_DYNAMIC_VARIABLES, variables) + chunk(audit.CHUNKID_DYNAMIC_SCENE, b'')
        ldd = chunk(0x3C51C460, b'') + chunk(
            0x3C51C461, chunk(audit.CHUNKID_DYNAMIC_SAVELOAD, dynamic, True), True)
        result = audit.dynamic_audio(ldd)
        self.assertTrue(result['subsystem_present'])
        self.assertEqual(result['background_music'], '07-song.mp3')
        self.assertEqual(result['dynamic_scene_bytes'], 0)

    def test_stream_threshold_for_3d_files(self):
        data = wave(frames=10)
        info, findings = audit.check_file({'class': 'Sound3DClass'}, data)
        self.assertEqual(findings, [])
        self.assertFalse(info['streaming_buffer'])
        big = wave(frames=audit.MAX_3D_PRELOAD_BYTES // 2 + 1)
        info, findings = audit.check_file({'class': 'Sound3DClass'}, big)
        self.assertTrue(info['streaming_buffer'])
        self.assertIn('3d_file_exceeds_preload_threshold_stream_buffer_has_no_raw_buffer', findings)
        # The same size is acceptable for a 2D sound only below its own smaller threshold.
        info, findings = audit.check_file({'class': 'AudibleSoundClass'}, big)
        self.assertTrue(info['streaming_buffer'])
        self.assertNotIn('3d_file_exceeds_preload_threshold_stream_buffer_has_no_raw_buffer', findings)

    def test_unsupported_wave_tag_and_channel_count(self):
        _, findings = audit.check_file({'class': 'Sound3DClass'}, wave(tag=85))
        self.assertIn('unsupported_wave_tag_in_current_provider', findings)
        _, findings = audit.check_file({'class': 'AudibleSoundClass'}, wave(channels=2, frames=4))
        self.assertEqual(findings, [])
        _, findings = audit.check_file({'class': 'Sound3DClass'}, wave(channels=2, frames=4))
        self.assertEqual(findings, ['stereo_3d_source_provider_mixes_channels_review'])

    def test_mpeg_frame_walk(self):
        # MPEG-1 Layer III, 128 kbps, 44.1 kHz, joint stereo, no padding: 417-byte frames.
        frame = bytes((0xFF, 0xFB, 0x90, 0x44)) + b'\0' * 413
        info, findings = audit.check_file({'class': 'AudibleSoundClass'}, frame * 10)
        self.assertEqual(findings, [])
        self.assertEqual(info['container'], 'mpeg')
        self.assertEqual(info['mpeg']['frames'], 10)
        self.assertEqual(info['mpeg']['sample_rate'], 44100)
        self.assertEqual(info['mpeg']['channels'], 2)
        self.assertEqual(info['mpeg']['layer'], 3)

    def test_basename_strips_windows_paths(self):
        self.assertEqual(audit.basename('c:\\x\\y\\snd.wav'), 'snd.wav')
        self.assertEqual(audit.basename('snd.wav'), 'snd.wav')


if __name__ == '__main__':
    unittest.main()
