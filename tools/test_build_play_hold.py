"""Verify the canonical build cannot accidentally enter fresh gameplay loops."""
from pathlib import Path
import os
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class BuildPlayHoldTests(unittest.TestCase):
    def test_actual_script_stops_before_any_build_when_no_retained_log_is_selected(self):
        result = subprocess.run(['bash', str(ROOT / 'tools/build.sh')], cwd=ROOT,
                                env={**os.environ, 'RENEGADE_REUSE_HOST_VALIDATION_LOG': ''},
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 12)
        self.assertIn('gameplay validation is held', result.stderr)
        self.assertNotIn('Verifying the pinned', result.stdout)

    def test_only_explicit_nonfresh_mode_can_pass_the_early_guard(self):
        source = (ROOT / 'tools/build.sh').read_text()
        guard = source.split('# BEGIN_RETAIL_CONTENT_PLAY_HOLD\n')[1].split('# END_RETAIL_CONTENT_PLAY_HOLD')[0]
        # Exercise the production guard in isolation: never run a full build
        # or gameplay harness for the retained-log branch of this fixture.
        for log, expected in [('', 12), ('/fixture/retained.log', 0)]:
            result = subprocess.run(['bash', '-c', guard],
                                    env={**os.environ, 'RENEGADE_REUSE_HOST_VALIDATION_LOG': log},
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, expected)


if __name__ == '__main__':
    unittest.main()
