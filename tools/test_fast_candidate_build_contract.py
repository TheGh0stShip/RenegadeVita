import pathlib
import re
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


class FastCandidateBuildContractTests(unittest.TestCase):
    def test_fast_candidate_build_uses_stable_incremental_tree(self):
        script = (ROOT / "tools/build_fast_candidate.sh").read_text(encoding="utf-8")
        self.assertIn('rv_build=${RENEGADE_FAST_BUILD_DIR:-"$rv_root/build/vita-fast-candidate"}', script)
        self.assertIn("-DRENEGADE_USE_CCACHE=ON", script)
        self.assertIn("cmake --build \"$rv_build\" --target RenegadeVitaA31 --parallel \"$rv_build_jobs\"", script)
        self.assertIn("cmake --build \"$rv_build\" --parallel \"$rv_build_jobs\"", script)
        self.assertNotIn("vita-${rv_candidate_stem}-candidate-${rv_timestamp}", script)
        self.assertNotIn("ccache --zero-stats", script)

    def test_fast_candidate_build_skips_canonical_host_and_unconditional_restaging(self):
        script = (ROOT / "tools/build_fast_candidate.sh").read_text(encoding="utf-8")
        self.assertNotIn("tools/run_a30_host.sh", script)
        self.assertIn('RENEGADE_FAST_RESTAGE:-0', script)
        self.assertIn('RENEGADE_INCREMENTAL_STAGE="${RENEGADE_INCREMENTAL_STAGE:-1}"', script)
        self.assertIn('bash "$rv_root/tools/stage_sources.sh"', script)
        self.assertNotIn('echo "Building and running retained A2 plus original A3 M00 host validation', script)

    def test_fast_candidate_build_keeps_identity_and_retail_exclusion_checks(self):
        script = (ROOT / "tools/build_fast_candidate.sh").read_text(encoding="utf-8")
        self.assertIn("verify_candidate_identity.py", script)
        self.assertIn("arm-vita-eabi-readelf", script)
        self.assertIn("arm-vita-eabi-nm", script)
        self.assertIn("unzip -Z1", script)
        self.assertIn("Retail or custom asset content was unexpectedly packaged", script)
        self.assertIn("not canonical acceptance", script)

    def test_vpk_packaging_requires_a_bounded_content_id(self):
        cmake = (ROOT / "CMakeLists.txt").read_text(encoding="utf-8")
        fast_build = (ROOT / "tools/build_fast_candidate.sh").read_text(encoding="utf-8")
        canonical_build = (ROOT / "tools/build.sh").read_text(encoding="utf-8")
        content_id_match = re.search(
            r'set\(RENEGADE_VITA_CONTENT_ID "([^"]+)"', cmake
        )
        self.assertIsNotNone(content_id_match)
        content_id = content_id_match.group(1)
        self.assertEqual(36, len(content_id))
        self.assertRegex(content_id, r"^[A-Z0-9_-]+$")
        self.assertIn(content_id, cmake)
        self.assertIn("VITA_MKSFOEX_FLAGS", cmake)
        self.assertIn(content_id, fast_build)
        self.assertIn(content_id, canonical_build)
        self.assertIn("sce_sys/param.sfo | strings", fast_build)
        self.assertIn("sce_sys/param.sfo | strings", canonical_build)

    def test_canonical_build_refreshes_lightweight_host_contracts(self):
        script = (ROOT / "tools/build.sh").read_text(encoding="utf-8")
        for target in (
            "a31_capture_telemetry_selftest",
            "a31_vita_input_contract_selftest",
            "a35_vita_button_state_contract_selftest",
        ):
            self.assertIn(target, script)
        self.assertIn('a31_capture_telemetry_selftest" | tee -a "$rv_host_output"', script)
        self.assertIn('a31_vita_input_contract_selftest" | tee -a "$rv_host_output"', script)
        self.assertIn('a35_vita_button_state_contract_selftest" | tee -a "$rv_host_output"', script)

    def test_fast_candidate_build_has_compile_scope_and_optional_tests(self):
        script = (ROOT / "tools/build_fast_candidate.sh").read_text(encoding="utf-8")
        self.assertIn("RENEGADE_FAST_SCOPE", script)
        self.assertIn("compile|package", script)
        self.assertIn("SELF/VPK packaging is skipped", script)
        self.assertIn("Built target: RenegadeVitaA31", script)
        self.assertIn("RENEGADE_FAST_TESTS", script)
        self.assertIn("focused|none", script)
        self.assertIn("Focused fast contracts skipped by RENEGADE_FAST_TESTS=none", script)
        self.assertIn("rv_vitasdk=${RENEGADE_VITASDK:-/usr/local/vitasdk}", script)
        self.assertIn("tools.test_vita_hanim_combo_guard", script)
        self.assertIn("tools.test_vita_camera_input_contract", script)
        self.assertIn("tools.test_input_route_contract", script)
        self.assertIn("tools.test_validate_vita_input_route", script)
        self.assertIn("camera/input route", script)


if __name__ == "__main__":
    unittest.main()
