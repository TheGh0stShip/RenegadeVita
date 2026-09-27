from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class RawAnimationTests(unittest.TestCase):
    def test_original_sampler_output(self):
        with tempfile.TemporaryDirectory(prefix="renegade-raw-animation-") as directory:
            executable = Path(directory) / "raw-animation"
            command = ["c++", "-std=gnu++17", "-O1", "-g", "-fpermissive",
                       "-ffunction-sections", "-fdata-sections", "-DNDEBUG=1",
                       "-D_UNIX=1", "-DRENEGADE_HOST_ABI_TEST=1", "-DRENEGADE_VITA_PORT=1",
                       "-include", str(ROOT / "port/compatibility/include/msvc_compat.h")]
            for relative in ("port/compatibility/include", "staging/ww3d2",
                             "staging/wwmath", "staging/wwlib", "staging/wwsaveload",
                             "upstream/CnC_Renegade/Code/wwdebug"):
                command += ["-I", str(ROOT / relative)]
            for source in ("tools/host_raw_animation_test.cpp", "staging/ww3d2/motchan.cpp",
                           "staging/wwmath/wwmath.cpp", "staging/wwmath/quat.cpp",
                           "staging/wwmath/matrix3d.cpp"):
                command.append(str(ROOT / source))
            command += ["-Wl,--gc-sections", "-o", str(executable)]
            result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            result = subprocess.run([str(executable)], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("PASS samples=32 including wrap", result.stdout)

            # A private generated copy proves the fixture rejects the old ARM rounding.
            source = (ROOT / "staging/ww3d2/hrawanim.cpp").read_text()
            corrected = "static_cast<int>(WWMath::Floor(frame))"
            self.assertEqual(source.count(corrected), 3)
            legacy = Path(directory) / "legacy-hrawanim.cpp"
            legacy.write_text(source.replace(corrected, "WWMath::Float_To_Long(frame - 0.499999f)"))
            command.insert(1, f'-DRAW_ANIMATION_SOURCE="{legacy}"')
            result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            result = subprocess.run([str(executable)], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("Raw animation output mismatch", result.stderr)


if __name__ == "__main__":
    unittest.main()
