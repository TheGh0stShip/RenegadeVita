from pathlib import Path
from contextlib import nullcontext
import os
import hashlib
import json
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class CinematicSaveTests(unittest.TestCase):
    def test_original_script_roundtrip(self):
        retained = os.environ.get("RENEGADE_CINEMATIC_PROBE_DIRECTORY")
        if retained:
            Path(retained).mkdir(parents=True, exist_ok=True)
        context = nullcontext(retained) if retained else tempfile.TemporaryDirectory(prefix="renegade-cinematic-save-")
        with context as directory:
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
            if retained:
                (Path(directory) / "compile.log").write_text(compiled.stdout + compiled.stderr)
            self.assertEqual(compiled.returncode, 0, compiled.stdout + compiled.stderr)
            result = subprocess.run([str(executable)], cwd=ROOT,
                                    capture_output=True, text=True)
            if retained:
                (Path(directory) / "runtime.log").write_text(result.stdout + result.stderr)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("Original cinematic command parameter parsing: 7 cases and independent cursors PASS", result.stdout)
            self.assertIn("Original cinematic save/load camera, clock, slots and commands PASS", result.stdout)
            self.assertIn("Original cinematic pending audio executes once after save/load PASS", result.stdout)
            if retained:
                receipt = {
                    "schema_version": 1,
                    "evidence_class": "host_original_cinematic_parser_and_save_load_asan_ubsan",
                    "binary_sha256": hashlib.sha256(executable.read_bytes()).hexdigest(),
                    "runtime_log_sha256": hashlib.sha256((result.stdout + result.stderr).encode()).hexdigest(),
                    "source_sha256": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                        for name in ("tools/host_cinematic_save_test.cpp", "tools/test_cinematic_save.py",
                                     "staging/scripts/Test_Cinematic.cpp", "staging/scripts/scripts.cpp",
                                     "staging/scripts/ScriptFactory.cpp", "staging/scripts/ScriptRegistrar.cpp",
                                     "staging/scripts/strtrim.cpp")},
                    "parameter_cases": 7, "independent_cursors_passed": True,
                    "save_load_passed": True, "pending_audio_once_passed": True,
                    "asan_ubsan_passed": True,
                    "limits": ["Synthetic mutable strings and fixture chunk transport; no retail payloads.",
                               "Full command dispatch, malformed save fields and retail playback remain open.",
                               "Host LP64 probe does not prove ARM ILP32 serialization or physical behavior."]
                }
                (Path(directory) / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    unittest.main()
