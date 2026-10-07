#!/usr/bin/env python3
"""Text contracts: build-time cache knobs are opt-in and default-preserving."""

import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


def block(text: str, opener: str) -> str:
    """Return the body of the CMake if()/endif() block that starts at opener."""
    start = text.index(opener)
    depth = 0
    for match in re.finditer(r"^\s*(if|endif)\(", text[start:], re.MULTILINE):
        depth += 1 if match.group(1) == "if" else -1
        if depth == 0:
            return text[start:start + match.end()]
    raise AssertionError(f"unterminated block: {opener}")


class CcacheModuleContract(unittest.TestCase):
    def setUp(self):
        self.module = (ROOT / "cmake/RenegadeCcache.cmake").read_text(encoding="utf-8")

    def test_default_launcher_matches_the_historical_per_tree_launcher(self):
        self.assertIn('set(RENEGADE_CCACHE_DIR "${RENEGADE_CCACHE_ROOT}/build/ccache" CACHE PATH', self.module)
        self.assertIn('set(RENEGADE_CCACHE_EFFECTIVE_DIR "${RENEGADE_CCACHE_DIR}")', self.module)
        self.assertIn(
            '"${CMAKE_COMMAND};-E;env;CCACHE_DIR=${RENEGADE_CCACHE_EFFECTIVE_DIR};'
            'CCACHE_BASEDIR=${RENEGADE_CCACHE_ROOT}")',
            self.module,
        )
        self.assertIn('list(APPEND RENEGADE_CCACHE_LAUNCHER "${RENEGADE_CCACHE_EXECUTABLE}")', self.module)

    def test_shared_directory_is_environment_opt_in_and_absolute(self):
        shared = block(self.module, 'if(NOT "$ENV{RENEGADE_CCACHE_DIR}" STREQUAL "")')
        self.assertIn("IS_ABSOLUTE", shared)
        self.assertIn("set(RENEGADE_CCACHE_SHARED ON)", shared)
        sloppiness = block(self.module, "if(RENEGADE_CCACHE_SHARED)")
        self.assertIn("CCACHE_SLOPPINESS=locale", sloppiness)
        self.assertEqual(1, self.module.count("CCACHE_SLOPPINESS"))

    def test_debug_prefix_map_is_off_by_default_and_never_disables_hash_dir(self):
        self.assertRegex(self.module, r'option\(RENEGADE_CCACHE_RELOCATABLE_DEBUG\n\s+"[^"]*" OFF\)')
        relocatable = block(self.module, "if(RENEGADE_CCACHE_RELOCATABLE_DEBUG_ACTIVE)")
        self.assertEqual(self.module.count("-fdebug-prefix-map="), relocatable.count("-fdebug-prefix-map="))
        self.assertNotIn("-ffile-prefix-map", self.module)
        self.assertNotIn("-fmacro-prefix-map", self.module)
        # Correctness guards stay on: never reuse objects with a wrong CWD or
        # skip the too-new-include race check.
        for forbidden in ("NOHASHDIR", "hash_dir", "time_macros", "include_file_mtime",
                          "include_file_ctime", "system_headers"):
            self.assertNotIn(forbidden, self.module)


class SourceCountDefinesContract(unittest.TestCase):
    def test_unused_count_defines_are_kept_unless_opted_out(self):
        cmake = (ROOT / "CMakeLists.txt").read_text(encoding="utf-8")
        self.assertIn('option(RENEGADE_OMIT_SOURCE_COUNT_DEFINES\n  "Drop the unused target-wide source-count definitions" OFF)', cmake)
        kept = block(cmake, "if(NOT rv_omit_source_count_defines)")
        self.assertIn("RENEGADE_VITA_A31_ORIGINAL_SOURCES=${RENEGADE_A31_INTERACTIVE_ORIGINAL_SOURCE_COUNT}", kept)
        self.assertIn("RENEGADE_VITA_A30_PORT_SOURCES=${RENEGADE_A30_PORT_SOURCE_COUNT}", kept)
        self.assertEqual(1, cmake.count("RENEGADE_VITA_A31_ORIGINAL_SOURCES="))
        self.assertEqual(1, cmake.count("RENEGADE_VITA_A30_PORT_SOURCES="))

    def test_no_translation_unit_reads_the_count_defines(self):
        for path in list((ROOT / "port").rglob("*")) + list((ROOT / "staging").rglob("*")):
            if path.suffix.lower() not in (".c", ".cpp", ".h", ".hpp", ".inc", ".inl"):
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            self.assertNotIn("RENEGADE_VITA_A31_ORIGINAL_SOURCES", text, path)
            self.assertNotIn("RENEGADE_VITA_A30_PORT_SOURCES", text, path)


class BuildScriptContract(unittest.TestCase):
    def test_scripts_default_to_the_per_tree_cache_and_check_the_effective_one(self):
        for name in ("tools/build.sh", "tools/build_fast_candidate.sh", "tools/run_a30_host.sh"):
            script = (ROOT / name).read_text(encoding="utf-8")
            self.assertIn('rv_ccache_dir=${RENEGADE_CCACHE_DIR:-"$rv_root/build/ccache"}', script, name)
            self.assertIn('export CCACHE_DIR="$rv_ccache_dir"', script, name)
            self.assertIn('export CCACHE_BASEDIR="$rv_root"', script, name)
            self.assertIn('grep -Fq "CCACHE_DIR=$rv_ccache_dir" "$rv_build/build.ninja"', script, name)
            self.assertNotIn('grep -Fq "CCACHE_DIR=$rv_root/build/ccache"', script, name)


if __name__ == "__main__":
    unittest.main()
