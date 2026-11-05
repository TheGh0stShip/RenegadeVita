"""Run original subtitle owners across the FFmpeg/engine enum ABI boundary.

The movie caller uses int-sized enums, while the production adapter, original
manager/parser/caption classes, file factories and straws use short enums.
The UTF-16 file, parser, schedule, font retention and rooted read path are real
production code; glyph/GPU presentation is observed by the fixture. Complete
Bink entry/render/cleanup bodies additionally run against fake decoder/GPU APIs
while calling those real subtitle owners. No retail assets, media decoding,
emulator or gameplay launch is involved.
"""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class MovieSubtitleAbiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix="renegade-subtitle-abi-")
        cls.addClassCleanup(cls.temporary.cleanup)
        directory = Path(cls.temporary.name)
        cls.directory = directory
        stage = ROOT / "staging"
        for name in ("subtitle", "subtitlemanager", "subtitleparser"):
            if not (stage / "binkmovie" / (name + ".cpp")).is_file():
                raise RuntimeError("Run tools/stage_sources.sh before the subtitle ABI contract")

        # These two original line helpers call libc wcslen. The production
        # native runtime resolves that spelling to rv_utf16_length. Redirect
        # only those helper objects to the same implementation for the host;
        # do not replace the original line-reading/trimming algorithms or
        # interpose a 16-bit wcslen on the host's 32-bit-wchar sanitizer runtime.
        wide_shim = directory / "subtitle-host-wide.h"
        wide_shim.write_text(
            '#include "msvc_compat.h"\n#include <wchar.h>\n'
            'static inline size_t subtitle_host_wcslen(const wchar_t *value)\n'
            '{ return rv_utf16_length(value); }\n'
            '#define wcslen subtitle_host_wcslen\n'
        )

        # Exercise the original font Add_Ref/Release_Ref path, not a copied
        # ownership model. Hooks count construction/destruction; drawing and
        # unused GPU/GDI cleanup remain fixture observations.
        renderer = (stage / "ww3d2/render2dsentence.cpp").read_text()

        def function(signature, hook=None):
            start = renderer.index(signature)
            body = renderer[start:renderer.index("\n}\n", start) + 3]
            if hook:
                body = body.replace("\treturn ;", "\t" + hook + ";\n\treturn ;", 1)
            return body

        (directory / "subtitle-renderer-ownership.inc").write_text("\n".join([
            function("Render2DSentenceClass::Render2DSentenceClass (void)",
                     "Fixture_Renderer_Created(this)"),
            function("Render2DSentenceClass::~Render2DSentenceClass (void)",
                     "Fixture_Renderer_Destroyed(this)"),
            function("void\nRender2DSentenceClass::Set_Font (FontCharsClass *font)"),
            function("FontCharsClass::FontCharsClass (void)"),
            function("FontCharsClass::~FontCharsClass (void)",
                     "++g_destroyed_fonts"),
        ]))
        bink = (ROOT / "port/platform/a4_binkmovie_boundary.cpp").read_text()

        def bink_function(signature):
            start = bink.index(signature)
            return bink[start:bink.index("\n}\n", start) + 3]

        (directory / "subtitle-bink-routing.inc").write_text("\n".join(
            bink_function(signature) for signature in (
                "void Release_Decoder_State()", "void Mark_Failed(",
                "void BINKMovie::Play(", "void BINKMovie::Stop()",
                "void BINKMovie::Shutdown()", "void BINKMovie::Render()",
            )))

        common = [
            "g++", "-std=c++17", "-O1", "-g", "-fshort-wchar",
            "-fsanitize=address,undefined", "-fno-omit-frame-pointer",
            "-fno-strict-aliasing", "-ffunction-sections", "-fdata-sections",
            "-Wno-unknown-pragmas", "-pthread",
            "-DNDEBUG=1", "-D_UNIX=1", "-DRENEGADE_HOST_ABI_TEST=1",
            "-DRENEGADE_VITA_PORT=1", "-DRENEGADE_SHORT_WCHAR_ABI=1",
            "-include", str(ROOT / "port/compatibility/include/msvc_compat.h"),
        ]
        include_dirs = [
            directory, ROOT / "port/compatibility/include", ROOT / "port/platform",
            ROOT / "port/filesystem", stage / "binkmovie", stage / "wwlib",
            stage / "wwdebug", stage / "wwmath", stage / "ww3d2",
            stage / "wwsaveload", stage / "wwphys", stage / "combat",
            stage / "wwaudio", stage / "commando", stage / "wwui",
        ]
        common.extend("-I" + str(path) for path in include_dirs)
        source_files = [
            ROOT / "port/platform/renegade_movie_subtitles.cpp",
            stage / "binkmovie/subtitle.cpp",
            stage / "binkmovie/subtitlemanager.cpp",
            stage / "binkmovie/subtitleparser.cpp",
            stage / "wwlib/ffactory.cpp", stage / "wwlib/rawfile.cpp",
            stage / "wwlib/bufffile.cpp", stage / "wwlib/wwstring.cpp",
            stage / "wwlib/realcrc.cpp", stage / "wwlib/straw.cpp",
            stage / "wwlib/xstraw.cpp", stage / "wwlib/readline.cpp",
            stage / "wwlib/trim.cpp",
            ROOT / "port/filesystem/renegade_paths.cpp",
            ROOT / "port/filesystem/renegade_file_factory.cpp",
        ]
        objects = []
        for index, source in enumerate(source_files):
            output = directory / ("engine-" + str(index) + ".o")
            command = [*common, "-fshort-enums"]
            if source.name in {"readline.cpp", "trim.cpp"}:
                command.extend(["-include", str(wide_shim)])
            cls.compile([*command, "-c", str(source), "-o", str(output)])
            objects.append(output)

        fixture = ROOT / "tools/movie_subtitle_abi_test.cpp"
        for name, enum_flag, defines in (
            ("engine-fixture", "-fshort-enums", ["-DMOVIE_SUBTITLE_ENGINE_FIXTURE=1"]),
            ("int-enum-caller", "-fno-short-enums", []),
        ):
            output = directory / (name + ".o")
            cls.compile([*common, enum_flag, *defines, "-c", str(fixture),
                         "-o", str(output)])
            objects.append(output)
        cls.executable = directory / "movie-subtitle-abi"
        cls.compile(["g++", "-fsanitize=address,undefined", "-pthread",
                     "-Wl,--gc-sections", *map(str, objects),
                     "-o", str(cls.executable)])

        retail = directory / "retail" / "Data"
        retail.mkdir(parents=True)
        # Only path admission is real here; the fixture supplies a fake decoder.
        (retail / "fixture.bik").write_bytes(b"synthetic movie path fixture\n")
        (retail / "SubTitle.INI").write_bytes((
            '\ufeffBeginMovie fixture\r\n'
            '<Time="00:00:01:00", Duration="00:00:01:00", '
            'Position="14:Left", Color="12:34:56", Text="Alpha">\r\n'
            '<Time="00:00:02:00", Duration="00:00:00:50", '
            'Position="13:Right", Text="Beta">\r\n'
            'EndMovie\r\n'
            'BeginMovie high\r\n'
            '<Time="19884:06:28:00", Duration="00:00:01:00", Text="High">\r\n'
            'EndMovie\r\n'
        ).encode("utf-16-le"))

    @staticmethod
    def compile(command):
        result = subprocess.run(command, capture_output=True, text=True, timeout=120)
        if result.returncode:
            raise AssertionError("subtitle compile failed:\n" + result.stdout + result.stderr)

    def run_case(self, case):
        # Preserve caller sanitizer options (e.g. detect_leaks=0 where the
        # execution environment cannot enumerate /proc threads). Ownership is
        # also checked explicitly by renderer and file-return counters.
        environment = dict(os.environ)
        environment.setdefault("ASAN_OPTIONS", "halt_on_error=1")
        environment.setdefault("UBSAN_OPTIONS", "halt_on_error=1:print_stacktrace=1")
        result = subprocess.run([str(self.executable), case, str(self.directory)],
                                capture_output=True, text=True, timeout=30,
                                env=environment)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("movie_subtitle_abi=" + case + " PASS", result.stdout)

    def test_mixed_enum_schedule_and_original_layout(self):
        self.run_case("schedule")

    def test_optional_invalid_and_rooted_paths(self):
        self.run_case("admission")

    def test_repeated_creation_and_destruction(self):
        self.run_case("lifecycle")

    def test_unsigned_tick_boundary(self):
        self.run_case("high-ticks")

    def test_font_survives_original_callers_reference_release(self):
        self.run_case("font-retention")

    def test_overflow_safe_sixty_hz_conversion(self):
        self.run_case("tick-conversion")

    def test_production_bink_presentation_and_cleanup_routes(self):
        self.run_case("bink-routing")


if __name__ == "__main__":
    unittest.main()
