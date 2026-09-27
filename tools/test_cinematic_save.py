from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class CinematicSaveTests(unittest.TestCase):
    def test_original_script_roundtrip(self):
        with tempfile.TemporaryDirectory(prefix="renegade-cinematic-save-") as directory:
            executable = Path(directory) / "cinematic-save"
            command = ["c++", "-std=c++17", "-O1", "-g", "-fpermissive",
                       "-fsanitize=address,undefined", "-fno-sanitize-recover=all",
                       "-include", str(ROOT / "port/compatibility/include/msvc_compat.h"),
                       "-include", str(ROOT / "port/compatibility/include/renegade_script_call_defaults.h")]
            for relative in ("staging/scripts", "staging/wwmath", "staging/wwlib",
                             "port/compatibility/include"):
                command += ["-I", str(ROOT / relative)]
            command.append(str(ROOT / "tools/host_cinematic_save_test.cpp"))
            for source in ("scripts.cpp", "ScriptFactory.cpp", "ScriptRegistrar.cpp", "strtrim.cpp"):
                command.append(str(ROOT / "staging/scripts" / source))
            command += ["-o", str(executable)]
            compiled = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(compiled.returncode, 0, compiled.stdout + compiled.stderr)
            result = subprocess.run([str(executable)], cwd=ROOT,
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("Original cinematic save/load camera, clock, slots and commands PASS", result.stdout)
            self.assertIn("Original cinematic pending audio executes once after save/load PASS", result.stdout)


if __name__ == "__main__":
    unittest.main()
