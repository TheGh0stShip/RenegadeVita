import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from tools.audit_campaign_source_surface import ROOT
from tools.check_m13_script_coverage import selected_owners


class RenegadeScriptDspCmakeTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("cmake"), "cmake is not installed")
    def test_cmake_function_reads_all_dsp_sources_except_dll_entrypoint(self):
        helper = ROOT / "cmake/RenegadeScriptSources.cmake"
        upstream = ROOT / "upstream/CnC_Renegade/Code/Scripts"
        staged = ROOT / "staging/scripts"
        with tempfile.TemporaryDirectory() as temporary:
            script = Path(temporary) / "inventory.cmake"
            script.write_text(
                f'include("{helper}")\n'
                f'renegade_collect_script_dsp_sources("{upstream}" "{staged}" sources)\n'
                'list(LENGTH sources count)\n'
                'if(NOT count EQUAL 44)\n message(FATAL_ERROR "bad count=${count}")\n endif()\n'
                'if("${sources}" MATCHES "DLLmain.cpp")\n message(FATAL_ERROR "DLLmain was not replaced")\n endif()\n'
                'message(STATUS "static source count=${count}")\n', encoding="utf-8")
            result = subprocess.run(["cmake", "-P", str(script)], capture_output=True,
                                    text=True, timeout=10, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("static source count=44", result.stdout)

    def test_manifest_must_be_attached_to_both_actual_targets(self):
        for target, cmake_name in (("vita", "CMakeLists.txt"),
                                    ("host", "tools/host_a30_definitions/CMakeLists.txt")):
            with self.subTest(target=target), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                for name in ("CMakeLists.txt", "tools/host_a30_definitions/CMakeLists.txt",
                             "cmake/RenegadeScriptSources.cmake",
                             "upstream/CnC_Renegade/Code/Scripts/Scripts.dsp"):
                    destination = root / name
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(ROOT / name, destination)
                source = (root / cmake_name).read_text()
                # Preserve configure calls and COMPILE_OPTIONS references;
                # only remove the actual target source reference.
                source = source.replace("  ${RENEGADE_SCRIPT_DSP_SOURCES}\n", "", 1)
                (root / cmake_name).write_text(source)
                self.assertNotIn("Test_Cinematic.cpp", selected_owners(root)[target])

    @unittest.skipUnless(shutil.which("cmake"), "cmake is not installed")
    def test_script_helper_definition_is_source_local_and_missing_site_fails(self):
        for missing in (None, "scripts.cpp", "strtrim.cpp"):
            with self.subTest(missing=missing), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                helper = (ROOT / "cmake/RenegadeScriptSources.cmake").read_text()
                if missing:
                    helper = helper.replace(f'    "${{staged_script_dir}}/{missing}"\n', "")
                (root / "helper.cmake").write_text(helper)
                (root / "CMakeLists.txt").write_text(
                    'cmake_minimum_required(VERSION 3.16)\n'
                    'project(ScriptPropertyProbe LANGUAGES NONE)\n'
                    'include("${CMAKE_CURRENT_SOURCE_DIR}/helper.cmake")\n'
                    'renegade_configure_script_static_helpers("${CMAKE_CURRENT_SOURCE_DIR}/scripts")\n'
                    'foreach(name scripts.cpp strtrim.cpp)\n'
                    ' get_source_file_property(defs "${CMAKE_CURRENT_SOURCE_DIR}/scripts/${name}" COMPILE_DEFINITIONS)\n'
                    ' if(NOT "strtrim=Renegade_Script_strtrim" IN_LIST defs)\n'
                    '  message(FATAL_ERROR "missing source-local isolation: ${name}")\n'
                    ' endif()\n'
                    'endforeach()\n'
                    'get_source_file_property(other "${CMAKE_CURRENT_SOURCE_DIR}/scripts/Mission00.cpp" COMPILE_DEFINITIONS)\n'
                    'if(other)\n message(FATAL_ERROR "isolation leaked to unrelated source")\n endif()\n',
                    encoding="utf-8")
                result = subprocess.run(["cmake", "-S", str(root), "-B", str(root / "probe")],
                                        capture_output=True, text=True, timeout=10, check=False)
                if missing:
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(f"missing source-local isolation: {missing}", result.stderr)
                else:
                    self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
