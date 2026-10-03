import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from tools.audit_campaign_source_surface import ROOT


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


if __name__ == "__main__":
    unittest.main()
