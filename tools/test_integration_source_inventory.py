"""Source-list growth and layout must not require a report count edit."""
from pathlib import Path
import tempfile
import unittest

from tools.generate_integration_report import read_native_source_sets, read_world_manifest
from tools.verify_source_inventory import verify_report


class IntegrationSourceInventoryTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        (self.root / "cmake").mkdir()
        for name in ("A22OriginalSources", "A30OriginalSources", "A31OriginalSources"):
            (self.root / "cmake" / (name + ".cmake")).write_text("# fixture\n")

    def write_cmake(self, body):
        (self.root / "CMakeLists.txt").write_text(body)

    def test_original_growth_uppercase_and_comments(self):
        self.write_cmake('${RENEGADE_STAGE}/commando/first.cpp\n')
        self.assertEqual(read_world_manifest(self.root), ["Code/Commando/first.cpp"])
        self.write_cmake(
            '${RENEGADE_STAGE}/commando/first.cpp\n'
            '  "${RENEGADE_STAGE}/wwlib/TARGA.CPP"\r\n'
            '${RENEGADE_SCRIPT_SOURCE}/Mission00.cpp\n'
            '# ${RENEGADE_STAGE}/commando/not_selected.cpp\n'
            '${RENEGADE_STAGE}/commando/first.cpp\n'
        )
        self.assertEqual(read_world_manifest(self.root), [
            "Code/Commando/first.cpp", "Code/Scripts/Mission00.cpp", "Code/wwlib/TARGA.CPP"
        ])

    def test_empty_original_inventory_rejected(self):
        self.write_cmake("# no selected sources\n")
        with self.assertRaises(RuntimeError):
            read_world_manifest(self.root)

    def native_fixture(self, base):
        self.write_cmake(
            '  set ( RENEGADE_A30_PORT_SOURCES\r\n' + base + '\r\n )\n'
            'set(RENEGADE_A4_FRONTEND_PORT_SOURCES\n'
            '\t"${RENEGADE_ROOT}/port/frontend.cpp" # selected\n)\n'
            'set(RENEGADE_A4_FRONTEND_PORT_SOURCES)\n'
        )

    def test_native_growth_and_whitespace(self):
        self.native_fixture('\t${RENEGADE_ROOT}/port/first.cpp')
        self.assertEqual(read_native_source_sets(self.root)["RENEGADE_A30_PORT_SOURCES"],
                         ["port/first.cpp"])
        self.native_fixture(' "${RENEGADE_ROOT}/port/first.cpp"\n'
                            '\t${RENEGADE_ROOT}/port/second.CPP')
        self.assertEqual(read_native_source_sets(self.root)["RENEGADE_A30_PORT_SOURCES"],
                         ["port/first.cpp", "port/second.CPP"])

    def test_duplicate_native_entry_rejected(self):
        self.native_fixture('${RENEGADE_ROOT}/port/first.cpp\n'
                            '${RENEGADE_ROOT}/port/first.cpp')
        with self.assertRaisesRegex(RuntimeError, "Duplicate"):
            read_native_source_sets(self.root)

    def test_unresolved_or_escaping_native_tokens_rejected(self):
        for token in ('${SOME_OTHER_LIST}', '${RENEGADE_ROOT}/port/../outside.cpp'):
            with self.subTest(token=token):
                self.native_fixture(token)
                with self.assertRaisesRegex(RuntimeError, "Unsupported"):
                    read_native_source_sets(self.root)

    def test_report_checks_paths_not_just_totals(self):
        self.native_fixture('${RENEGADE_ROOT}/port/first.cpp')
        (self.root / "cmake/A22OriginalSources.cmake").write_text(
            '${RENEGADE_STAGE}/commando/first.cpp\n')
        report = {
            "milestone": "fixture",
            "original_translation_units": ["Code/Commando/first.cpp"],
            "original_source_files_compiled": 1,
            "staged_original_owner_paths": ["staging/commando/loadingscreen.cpp"],
            "staged_original_owner_files": 1,
            "vita_translation_units": ["port/first.cpp"],
            "vita_platform_renderer_validation_files": 1,
            "a4_frontend_boundary_paths": ["port/frontend.cpp"],
            "a4_frontend_boundary_files": 1,
        }
        self.assertEqual(verify_report(self.root, report, "fixture"), (1, 1, 1, 1))
        for key, value in (("milestone", "stale"),
                           ("original_source_files_compiled", 2),
                           ("vita_translation_units", ["port/wrong.cpp"])):
            with self.subTest(key=key), self.assertRaises(ValueError):
                verify_report(self.root, dict(report, **{key: value}), "fixture")

    def test_canonical_inventory_has_no_manual_total_gate(self):
        source = (Path(__file__).resolve().parents[1] / "tools/build.sh").read_text()
        self.assertNotRegex(source, r'"(?:original_source_files_compiled|staged_original_owner_files|vita_platform_renderer_validation_files|a4_frontend_boundary_files)":\s*\d+')
        self.assertIn('tools/verify_source_inventory.py', source)


if __name__ == "__main__":
    unittest.main()
