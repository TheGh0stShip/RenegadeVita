"""Run actual BINK update/read-ahead/drop code with deterministic media and time."""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class BinkSchedulerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix="renegade-bink-")
        cls.addClassCleanup(cls.temporary.cleanup)
        directory = Path(cls.temporary.name)
        source = (ROOT / "port/platform/a4_binkmovie_boundary.cpp").read_text()

        def section(start, end):
            offset = source.index(start)
            return source[offset:source.index(end, offset)]

        (directory / "bink-scheduler-production.inc").write_text("\n".join([
            section("bool Drop_Pending_Video_If_Late(", "bool Submit_Video_Packet()"),
            section("bool Prefetch_Audio_For_Pending_Video()", "void Flush_Decoders()"),
            section("void BINKMovie::Update()", "void BINKMovie::Render()"),
        ]))
        cls.executable = directory / "bink-scheduler"
        command = ["g++", "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror",
                   f"-I{directory}", str(ROOT / "tools/vita_bink_scheduler_test.cpp"),
                   "-o", str(cls.executable)]
        if os.environ.get("RENEGADE_BINK_SANITIZE") == "1":
            command[2:3] = ["-O1", "-g", "-fsanitize=address,undefined", "-fno-omit-frame-pointer"]
        subprocess.run(command, check=True, capture_output=True, text=True)

    def run_case(self, name):
        result = subprocess.run([str(self.executable), name], check=True,
                                capture_output=True, text=True)
        self.assertIn(f"bink_scheduler={name} PASS", result.stdout)

    def test_interleaved_playback(self): self.run_case("interleaved-playback")
    def test_early_frame(self): self.run_case("early-frame")
    def test_late_frame_progress(self): self.run_case("late-frame-progress")
    def test_queue_limit(self): self.run_case("queue-limit")
    def test_byte_limit(self): self.run_case("byte-limit")
    def test_allocation_failure(self): self.run_case("allocation-failure")
    def test_skip(self): self.run_case("skip")


if __name__ == "__main__":
    unittest.main()
