import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
import sys

TOOLS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS_DIR))
from verify_repo_hygiene import verify_repo


def _repo_init(path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.email", "validator@example.com"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Repo Hygiene Test"], cwd=path, check=True)


def _run_verify(repo_root: Path) -> int:
    script = TOOLS_DIR / "verify_repo_hygiene.py"
    return subprocess.run(
        ["python3", str(script), "--root", str(repo_root)],
        cwd=repo_root,
        capture_output=True,
        text=True,
    ).returncode


class RepoHygieneTests(unittest.TestCase):
    def _make_repo_with_file(self, filename: str, content: str = "") -> tuple[Path, int]:
        temp_root = Path(tempfile.mkdtemp())
        _repo_init(temp_root)
        repo_root = temp_root
        tracked = repo_root / filename
        tracked.parent.mkdir(parents=True, exist_ok=True)
        tracked.write_text(content, encoding="utf-8")
        subprocess.run(["git", "add", filename], cwd=repo_root, check=True)
        return repo_root, _run_verify(repo_root)

    def _run_verify_and_clean(self, repo_root: Path) -> int:
        try:
            return _run_verify(repo_root)
        finally:
            shutil.rmtree(repo_root)

    def test_clean_path_and_placeholders_pass(self):
        repo_root = Path(tempfile.mkdtemp())
        try:
            _repo_init(repo_root)
            safe_file = repo_root / "tools/safe.md"
            safe_file.parent.mkdir(parents=True, exist_ok=True)
            safe_file.write_text(
                "<managed-dist> should map to managed output and <managed-log-root> is expected",
                encoding="utf-8",
            )
            subprocess.run(["git", "add", "tools/safe.md"], cwd=repo_root, check=True)
            self.assertEqual(_run_verify(repo_root), 0)
        finally:
            shutil.rmtree(repo_root)

    def test_forbidden_artifact_extension_is_blocked(self):
        root, result = self._make_repo_with_file("dist/game.elf", "binary")
        try:
            self.assertEqual(result, 1)
        finally:
            shutil.rmtree(root)

    def test_local_path_leak_in_text_is_blocked(self):
        repo_root = Path(tempfile.mkdtemp())
        try:
            _repo_init(repo_root)
            file = repo_root / "notes.txt"
            file.write_text(r"C:\Users\local-user\AppData\Local\example", encoding="utf-8")
            subprocess.run(["git", "add", "notes.txt"], cwd=repo_root, check=True)
            self.assertEqual(_run_verify(repo_root), 1)
        finally:
            shutil.rmtree(repo_root)

    def test_machine_specific_symlink_is_blocked(self):
        temp_root = Path(tempfile.mkdtemp())
        try:
            _repo_init(temp_root)
            os.symlink("/home/local-user/.cache", temp_root / "cache-link.txt")
            subprocess.run(["git", "add", "cache-link.txt"], cwd=temp_root, check=True)
            self.assertEqual(_run_verify(temp_root), 1)
        finally:
            shutil.rmtree(temp_root)

    def test_fixture_psp2_dmp_is_allowed(self):
        repo_root = Path(tempfile.mkdtemp())
        try:
            _repo_init(repo_root)
            fixture = repo_root / "tools/fixtures/psp2_core/sample.psp2dmp"
            fixture.parent.mkdir(parents=True, exist_ok=True)
            fixture.write_bytes(b"\x00" * 8)
            subprocess.run(["git", "add", "tools/fixtures/psp2_core/sample.psp2dmp"], cwd=repo_root, check=True)
            self.assertEqual(_run_verify(repo_root), 0)
        finally:
            shutil.rmtree(repo_root)


if __name__ == "__main__":
    unittest.main()
