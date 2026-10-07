from pathlib import Path
import os
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
PATCHES = ("wwmath-a36-arm-int-floor-helpers.patch",
           "wwmath-a36-quat-matrix-single-precision.patch")


def build(executable, extra):
    command = ["c++", "-std=gnu++17", "-O2", "-g", "-fpermissive", "-pthread",
               "-ffunction-sections", "-fdata-sections", "-DNDEBUG=1",
               "-D_UNIX=1", "-DRENEGADE_HOST_ABI_TEST=1", "-DRENEGADE_VITA_PORT=1",
               "-include", str(ROOT / "port/compatibility/include/msvc_compat.h")] + extra
    for relative in ("port/compatibility/include", "staging/wwmath", "staging/wwlib",
                     "upstream/CnC_Renegade/Code/wwdebug"):
        command += ["-I", str(ROOT / relative)]
    for source in ("tools/host_a36_wwmath_arm_equivalence_test.cpp",
                   "staging/wwmath/wwmath.cpp", "staging/wwmath/quat.cpp",
                   "staging/wwmath/matrix3d.cpp", "staging/wwmath/matrix3.cpp"):
        command.append(str(ROOT / source))
    command += ["-Wl,--gc-sections", "-o", str(executable)]
    return subprocess.run(command, cwd=ROOT, capture_output=True, text=True)


class WWMathArmEquivalenceTests(unittest.TestCase):
    def test_patches_registered_after_fabs(self):
        script = (ROOT / "tools/stage_sources.sh").read_text()
        anchor = script.index("wwmath-a36-fabs-vabs.patch")
        for name in PATCHES:
            self.assertTrue((ROOT / "port/patches" / name).is_file(), name)
            self.assertGreater(script.index(name), anchor, name)
        header = (ROOT / "staging/wwmath/wwmath.h").read_text()
        self.assertIn("WWINLINE float WWMath::Floor(float x)", header)
        self.assertIn("(bits & 0x7FFFFFFFU) >= 0x4F000000U", header)
        for name in ("quat.cpp", "matrix3d.cpp", "matrix3.cpp"):
            source = (ROOT / "staging/wwmath" / name).read_text()
            self.assertNotIn("(float)(1.0 - 2.0", source, name)
            self.assertNotIn("(float)(2.0 * (", source, name)

    def test_exhaustive_bit_identity(self):
        with tempfile.TemporaryDirectory(prefix="renegade-wwmath-arm-") as directory:
            executable = Path(directory) / "wwmath-arm"
            result = build(executable, [])
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            # Every 2^32 bit pattern takes minutes; the default run checks every
            # 13th pattern (all exponents/signs). RENEGADE_WWMATH_EXHAUSTIVE=1
            # runs the full proof recorded in reports/FPS_R4_WWMATH_ARM.md.
            stride = "1" if os.environ.get("RENEGADE_WWMATH_EXHAUSTIVE") == "1" else "13"
            result = subprocess.run([str(executable), stride], cwd=ROOT, capture_output=True,
                                    text=True, timeout=3600)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn(f"PASS scalar helpers 2^32/stride={stride} flush=0", result.stdout)
            self.assertIn(f"PASS scalar helpers 2^32/stride={stride} flush=1", result.stdout)
            self.assertIn("PASS quaternion matrices bit-identical flush=0", result.stdout)

    def test_sanitized_sampled_bit_identity(self):
        with tempfile.TemporaryDirectory(prefix="renegade-wwmath-arm-san-") as directory:
            executable = Path(directory) / "wwmath-arm-san"
            result = build(executable, ["-fsanitize=address,undefined,float-cast-overflow",
                                        "-fno-sanitize-recover=all"])
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            result = subprocess.run([str(executable), "4099"], cwd=ROOT, capture_output=True,
                                    text=True, timeout=900)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("PASS scalar helpers 2^32/stride=4099 flush=0", result.stdout)
            self.assertNotIn("runtime error", result.stderr)


if __name__ == "__main__":
    unittest.main()
