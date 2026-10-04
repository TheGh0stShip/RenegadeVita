import os
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest
from tools.test_mission_wave_headers import wave, fmt, wave_chunk

ROOT = Path(__file__).resolve().parents[1]


class WaveArchiveProbeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        cls.executable = Path(cls.directory.name) / 'probe'
        subprocess.run(['g++', '-std=c++17', '-O2', '-fsanitize=address,undefined',
                        '-fno-omit-frame-pointer', '-Wall', '-Wextra', '-Werror',
                        '-I' + str(ROOT / 'port/audio/vita'),
                        str(ROOT / 'tools/host_wave_archive_probe.cpp'),
                        str(ROOT / 'port/audio/vita/renegade_wave_decoder.cpp'),
                        '-o', str(cls.executable)], check=True)

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def invoke(self, data):
        return subprocess.run([str(self.executable)], input=data, capture_output=True, timeout=60,
                              env=dict(os.environ, ASAN_OPTIONS='detect_leaks=1:halt_on_error=1',
                                       UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1'))

    def test_multiple_frames_return_metadata_without_samples(self):
        good = wave(fmt(), wave_chunk(b'data', b'\0' * 4))
        packet = struct.pack('<I', len(good)) + good
        result = self.invoke(packet + packet)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, b'1\t2\tnone\n' * 2)
        self.assertEqual(result.stderr, b'')

    def test_oversized_riff_preserves_bounded_audio_payload(self):
        good = wave(fmt(), wave_chunk(b'data', b'\0' * 4))
        bad = good[:4] + struct.pack('<I', len(good) + 100) + good[8:]
        result = self.invoke(struct.pack('<I', len(bad)) + bad)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, b'1\t2\tnone\n')
        self.assertEqual(result.stderr, b'')

    def test_truncated_protocol_and_allocation_ceiling_fail(self):
        for data, code in ((b'\x01', 2), (struct.pack('<I', 4) + b'xx', 4),
                           (struct.pack('<I', 64 * 1024 * 1024 + 1), 3)):
            result = self.invoke(data)
            self.assertEqual(result.returncode, code)
            self.assertEqual(result.stdout, b'')
            self.assertEqual(result.stderr, b'')

    def test_trailing_content_keeps_fact_and_payload_checks(self):
        from tools.test_mission_wave_headers import wave_chunk
        good = wave(fmt(), wave_chunk(b'data', b'\0' * 4))
        trailing = wave(fmt(), wave_chunk(b'data', b'\0' * 4), b'junk' + struct.pack('<I', 0xffffffff))
        bad_before = wave(b'junk' + struct.pack('<I', 0xffffffff), fmt(), wave_chunk(b'data', b'\0' * 4))
        duplicate = wave(fmt(), wave_chunk(b'data', b'\0' * 4), wave_chunk(b'data', b'\0' * 4))
        truncated = good[:-1]
        fact_after = wave(fmt(tag=17, align=8, bits=4), wave_chunk(b'data', b'\0' * 8),
                          wave_chunk(b'fact', struct.pack('<I', 5)))
        packets = b''.join(struct.pack('<I', len(data)) + data
                           for data in (trailing, bad_before, duplicate, truncated, fact_after))
        result = self.invoke(packets)
        self.assertEqual(result.returncode, 0)
        lines = result.stdout.splitlines()
        self.assertEqual(lines[0], b'1\t2\tnone')
        self.assertTrue(all(line.startswith(b'0\t0\t') for line in lines[1:4]))
        self.assertEqual(lines[4], b'1\t5\tnone')
        self.assertEqual(result.stderr, b'')
