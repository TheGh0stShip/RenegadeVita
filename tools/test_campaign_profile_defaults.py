import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


class CampaignProfileDefaultTests(unittest.TestCase):
    def test_build_defaults_to_full_port_not_demo(self):
        cmake = (ROOT / "CMakeLists.txt").read_text(encoding="utf-8")
        build = (ROOT / "tools" / "build.sh").read_text(encoding="utf-8")
        fast = (ROOT / "tools" / "build_fast_candidate.sh").read_text(encoding="utf-8")

        self.assertIn(
            'option(RENEGADE_VITA_M00_DEMO "Interim M00 community showcase; not the full-port completion target" OFF)',
            cmake,
        )
        self.assertIn("rv_m00_demo=${RENEGADE_M00_DEMO:-0}", build)
        self.assertIn("rv_m00_demo=${RENEGADE_M00_DEMO:-0}", fast)
        self.assertNotIn("rv_m00_demo=${RENEGADE_M00_DEMO:-1}", build)
        self.assertNotIn("rv_m00_demo=${RENEGADE_M00_DEMO:-1}", fast)

    def test_demo_mode_still_exists_as_explicit_opt_in(self):
        cmake = (ROOT / "CMakeLists.txt").read_text(encoding="utf-8")
        lifecycle = (
            ROOT / "port" / "platform" / "a4_frontend_lifecycle_boundary.cpp"
        ).read_text(encoding="utf-8")

        self.assertIn("if(RENEGADE_VITA_M00_DEMO)", cmake)
        self.assertIn('set(RENEGADE_BUILD_PROFILE "M00-DEMO")', cmake)
        self.assertIn('set(RENEGADE_BUILD_PROFILE "FULL-PORT-DEVELOPMENT")', cmake)
        self.assertIn("#if defined(__vita__) && RENEGADE_VITA_M00_DEMO", lifecycle)
        self.assertIn("A4_Frontend_Is_Tutorial_Source(source.Peek_Buffer())", lifecycle)


if __name__ == "__main__":
    unittest.main()
