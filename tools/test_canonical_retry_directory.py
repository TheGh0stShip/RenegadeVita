"""Exercise the actual shell retry-directory admission, without starting a build."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


class CanonicalRetryDirectoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = (Path(__file__).resolve().parents[1] / "tools/build.sh").read_text()
        cls.selection = source[source.index('rv_build="$rv_root/build/vita-'):
                               source.index('rv_host_output=')]

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="rv retry with spaces ")
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.build = self.root / "build/vita-a35-dev111-candidate-old"
        self.build.mkdir(parents=True)
        self.write_cache(self.root, "A3.5-dev111")

    def write_cache(self, home, candidate):
        (self.build / "CMakeCache.txt").write_text(
            f"CMAKE_HOME_DIRECTORY:INTERNAL={home}\n"
            f"RENEGADE_CANDIDATE_LABEL:STRING={candidate}\n")

    def select(self, retry):
        env = dict(os.environ, rv_root=str(self.root), rv_candidate_stem="a35-dev111",
                   rv_candidate_label="A3.5-dev111", rv_timestamp="fresh",
                   RENEGADE_CANONICAL_RETRY_DIR=str(retry))
        return subprocess.run(["bash", "-Eeuo", "pipefail", "-c",
                               self.selection + '\nprintf "%s\\n" "$rv_build"'],
                              env=env, text=True, capture_output=True)

    def test_matching_workspace_and_candidate_accepted(self):
        result = self.select(self.build)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), str(self.build))

    def test_unset_keeps_fresh_default(self):
        result = self.select("")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(),
                         str(self.root / "build/vita-a35-dev111-candidate-fresh"))

    def test_cache_identity_mismatch_rejected(self):
        for home, candidate in ((self.root / "other", "A3.5-dev111"),
                                (self.root, "A3.5-dev110")):
            with self.subTest(home=home, candidate=candidate):
                self.write_cache(home, candidate)
                self.assertEqual(self.select(self.build).returncode, 2)

    def test_external_and_wrong_candidate_paths_rejected(self):
        for path in (self.root / "external", self.root / "build/vita-a35-dev110-candidate-old"):
            with self.subTest(path=path):
                path.mkdir()
                (path / "CMakeCache.txt").write_text((self.build / "CMakeCache.txt").read_text())
                self.assertEqual(self.select(path).returncode, 2)


if __name__ == "__main__":
    unittest.main()
