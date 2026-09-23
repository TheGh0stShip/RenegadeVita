from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class Vita3KBuildInstallContractTests(unittest.TestCase):
    def test_canonical_package_is_installed_after_hash_verification(self):
        script = (ROOT / "tools/build.sh").read_text(encoding="utf-8")
        hash_check = script.index('sha256sum -c "$rv_candidate_label"-SHA256SUMS.txt')
        install = script.index('tools/install_vita3k_candidate.sh')
        success = script.index('echo "$rv_candidate_label BUILD SUCCESS"')
        self.assertLess(hash_check, install)
        self.assertLess(install, success)
        self.assertIn('"$rv_dist/RenegadeVita-$rv_candidate_label.vpk"', script[install:])

    def test_fast_packaged_candidate_installs_but_compile_scope_does_not_reuse_stale_vpk(self):
        script = (ROOT / "tools/build_fast_candidate.sh").read_text(encoding="utf-8")
        compile_scope = script[script.index('if [[ "$rv_fast_scope" == "compile" ]]'):]
        self.assertLess(compile_scope.index("exit 0"), compile_scope.index("tools/install_vita3k_candidate.sh")
                        if "tools/install_vita3k_candidate.sh" in compile_scope else len(compile_scope))
        self.assertIn('tools/install_vita3k_candidate.sh', script)
        self.assertIn('No physical Vita filesystem was accessed', script)
        package_hash = script.index('sha256sum -c "$rv_candidate_label"-FAST-SHA256SUMS.txt')
        self.assertLess(package_hash, script.index('tools/install_vita3k_candidate.sh'))

    def test_installer_is_title_scoped_backed_up_and_hash_verified_without_launch(self):
        script = (ROOT / "tools/install_vita3k_candidate.sh").read_text(encoding="utf-8")
        self.assertIn("tools/prepare_vita3k_demo.py", script)
        self.assertIn('RNEGA3101', script)
        self.assertIn('INSTALLED_NOT_LAUNCHED', script)
        self.assertIn('installed == expected', script)
        self.assertIn('launch not requested', script)
        self.assertIn('RENEGADE_VITA3K_VFS', script)
        self.assertNotIn('run_vita3k', script)
        self.assertNotIn('package install', script)


if __name__ == "__main__":
    unittest.main()
