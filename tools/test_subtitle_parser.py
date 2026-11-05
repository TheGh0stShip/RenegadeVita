"""Non-play fixtures for the staged original subtitle parser and UTF-16 owners."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SubtitleParserTests(unittest.TestCase):
    def test_actual_parser_with_engine_abi_under_sanitizers(self):
        stage = ROOT / "staging"
        compat = ROOT / "port/compatibility/include"
        with tempfile.TemporaryDirectory(prefix="renegade-subtitle-parser-") as folder:
            binary = Path(folder) / "parser"
            command = [
                "g++", "-std=c++17", "-O1", "-g", "-fshort-wchar", "-fshort-enums",
                "-fsanitize=address,undefined", "-fno-omit-frame-pointer",
                "-fno-pie", "-no-pie", "-fno-strict-aliasing", "-fno-builtin-wcslen",
                "-ffunction-sections", "-fdata-sections", "-Wl,--gc-sections",
                "-D_UNIX=1", "-DRENEGADE_VITA_PORT=1", "-DRENEGADE_HOST_ABI_TEST=1",
                "-DRENEGADE_SHORT_WCHAR_ABI=1", "-DNDEBUG=1",
                "-include", str(compat / "msvc_compat.h"),
            ]
            for include in (compat, stage / "binkmovie", stage / "wwlib", stage / "wwdebug"):
                command.extend(["-I", str(include)])
            for source in (
                ROOT / "tools/host_subtitle_parser_test.cpp",
                stage / "binkmovie/subtitle.cpp", stage / "binkmovie/subtitleparser.cpp",
                stage / "wwlib/straw.cpp", stage / "wwlib/xstraw.cpp",
                stage / "wwlib/readline.cpp", stage / "wwlib/trim.cpp",
            ):
                command.append(str(source))
            compiled = subprocess.run([*command, "-o", str(binary)],
                                      capture_output=True, text=True, timeout=120)
            self.assertEqual(compiled.returncode, 0, compiled.stdout + compiled.stderr)
            result = subprocess.run([str(binary)], capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("original subtitle parser PASS", result.stdout)
            self.assertIn("wchar_bytes=2 enum_bytes=1", result.stdout)
            print(result.stdout.strip())


if __name__ == "__main__":
    unittest.main()
