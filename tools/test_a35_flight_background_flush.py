"""Background flight-recorder flushing persists what synchronous flushing does."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class FlightBackgroundFlushTests(unittest.TestCase):
    def test_background_matches_synchronous_under_sanitizers(self):
        for sanitizer in ('address,undefined', 'thread'):
            with self.subTest(sanitizer=sanitizer), \
                    tempfile.TemporaryDirectory(prefix='renegade-flight-bg-') as folder:
                binary = Path(folder) / 'test'
                subprocess.run(['g++', '-std=c++17', '-O1', '-g', '-fsanitize=' + sanitizer,
                                '-fno-omit-frame-pointer', '-Wall', '-Wextra', '-Werror', '-pthread',
                                '-I' + str(ROOT / 'port/developer'),
                                str(ROOT / 'tools/host_a35_flight_background_test.cpp'),
                                str(ROOT / 'port/developer/a35_campaign_flight_recorder.cpp'),
                                str(ROOT / 'port/developer/a35_script_lookup_telemetry.cpp'),
                                '-o', str(binary)], check=True)
                subprocess.run([str(binary)], check=True, timeout=300)

    def test_only_final_reasons_block_the_game_thread(self):
        source = (ROOT / 'port/developer/a35_campaign_flight_recorder.cpp').read_text()
        final = source[source.index('bool Is_Final_Flush('):]
        final = final[:final.index('\n}\n')]
        for reason in ('shutdown', 'pre-clean-exit', 'best-effort-fatal-snapshot', 'final'):
            self.assertIn('"' + reason + '"', final)
        for reason in ('checkpoint', 'mission-progress-change', 'slow-frame-over-250ms'):
            self.assertNotIn('"' + reason + '"', final)
        flush = source[source.index('bool A35_Campaign_Flight_Flush(const char *reason)'):]
        self.assertLess(flush.index('Wait_For_Flush_Idle();'),
                        flush.index('return Write_Flight_Files(gRecorder, reason);'))


if __name__ == '__main__':
    unittest.main()
