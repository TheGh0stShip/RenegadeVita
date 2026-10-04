"""Source contracts only: no C++ compilation or runtime failure injection."""
from pathlib import Path
import hashlib
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class RequiredLevelLoadTests(unittest.TestCase):
    def test_patch_replays_without_fuzz_or_offset_and_optional_defs_stay_optional(self):
        with tempfile.TemporaryDirectory() as directory:
            for name in ('savegame.cpp', 'savegame.h'):
                (Path(directory) / name).write_bytes((ROOT / 'staging/combat' / name).read_bytes())
            # Restore the historical anchor before replaying the earlier
            # required-load patch. Current save diagnostics add source lines
            # but must not weaken the immutable source hashes or offset gate.
            if 'RV_SAVE_PHASE' in (Path(directory) / 'savegame.cpp').read_text():
                diagnostics = (ROOT / 'port/patches/combat-a35-save-phase-diagnostics.patch').read_bytes()
                save_only = diagnostics.split(b'--- a/conversationmgr.cpp', 1)[0]
                undo = subprocess.run(['patch', '--batch', '--reverse', '--fuzz=0',
                                       '--no-backup-if-mismatch', '-p1', '-d', directory],
                                      input=save_only, capture_output=True, check=True)
                self.assertNotIn(b'offset', undo.stdout)
            patch = (ROOT / 'port/patches/combat-a35-required-level-load-failure.patch').read_bytes()
            # Future build entrypoints run after staging. Reverse only this
            # patch in the private copy before replaying the anchored contract.
            if 'A35_LOAD_DYNAMIC_UNAVAILABLE' in (Path(directory) / 'savegame.cpp').read_text():
                reverse = subprocess.run(['patch', '--batch', '--reverse', '--fuzz=0',
                                          '--no-backup-if-mismatch', '-p1', '-d', directory],
                                         input=patch, capture_output=True, check=True)
                self.assertNotIn(b'offset', reverse.stdout)
            anchors = {'savegame.cpp': '8589a02e13ce7de0c505f0d4d0250c82233160b92524e54e59849f8be0726564',
                       'savegame.h': 'a380d7e66a3f000c03a7bb2db2019cbaa659f25ee868efb84d02d3cf37f23e07'}
            for name, digest in anchors.items():
                self.assertEqual(hashlib.sha256((Path(directory) / name).read_bytes()).hexdigest(), digest)
            result = subprocess.run(['patch', '--batch', '--forward', '--fuzz=0',
                                     '--no-backup-if-mismatch', '-p1', '-d', directory],
                                    input=patch,
                                    capture_output=True, check=True)
            self.assertNotIn(b'offset', result.stdout)
            source = (Path(directory) / 'savegame.cpp').read_text()
            header = (Path(directory) / 'savegame.h').read_text()
        self.assertIn('bool required_level = false', header)
        self.assertIn('Load_Save_Load_System( MapFilename, false, true );', source)
        self.assertIn('Load_Save_Load_System( filename, true );', source)
        helper = source.split('void\tSaveGameManager::Load_Save_Load_System', 1)[1]
        self.assertIn('if (required_level) A35_Level_Load_Record_Failure(A35_LOAD_STATIC_OPEN_FAILED);', helper)
        self.assertIn('if (required_level) A35_Level_Load_Record_Failure(A35_LOAD_STATIC_UNAVAILABLE);', helper)
        self.assertIn('!SaveLoadSystemClass::Load(cload, auto_post_load) && required_level', helper)
        self.assertIn('_TheFileFactory->Return_File(file);\n\t\t\treturn;', helper)
        dynamic = source.split('void\tSaveGameManager::Load_Game', 1)[1].split('bool\tSaveGameManager::Smart_Peek', 1)[0]
        for name in ('DYNAMIC_UNAVAILABLE', 'DYNAMIC_OPEN_FAILED', 'DYNAMIC_SUBSYSTEM_FAILED'):
            self.assertIn('A35_LOAD_' + name, dynamic)
        self.assertIn('_TheFileFactory->Return_File(file);\n\t\treturn;', dynamic)
        self.assertIn('if (!level_info_found) A35_Level_Load_Record_Failure(A35_LOAD_DYNAMIC_INFO_MISSING);', dynamic)
        self.assertIn('CombatManager::I_Am_Server() && !level_data_found', dynamic)
        self.assertIn('A35_LOAD_DYNAMIC_DATA_MISSING', dynamic)
        self.assertIn('file->Close();\n\t\t_TheFileFactory->Return_File(file);\n\t\treturn;', dynamic)

    def test_failure_admission_preserves_reference_closure_and_skips_finalization(self):
        runtime = (ROOT / 'port/platform/vita/a31_vita_runtime.cpp').read_text()
        reset = runtime.index('A35_Level_Load_Reset_Failure();')
        load = runtime.index('CombatManager::Load_Level_Threaded(load_source, false);', reset)
        post = runtime.index('SaveLoadSystemClass::Post_Load_Processing(NULL);', load)
        guard = runtime.index('if (load_failure != A35_LOAD_NO_FAILURE)', post)
        finalize = runtime.index('CombatManager::Post_Load_Level();', guard)
        self.assertLess(reset, load)
        self.assertLess(post, guard)
        failure = runtime[guard:finalize]
        self.assertIn('NetworkObjectMgrClass::Set_Is_Level_Loading(false);', failure)
        self.assertIn('result.render_error = true;', failure)
        self.assertIn('break;', failure)
        self.assertNotIn('result.level_loaded = true', failure)
        self.assertIn('a35_level_load_status.cpp', (ROOT / 'CMakeLists.txt').read_text())

    def test_latch_has_fixed_width_no_strings_and_no_opt_in_dependency(self):
        status = (ROOT / 'port/platform/vita/a35_level_load_status.cpp').read_text()
        self.assertIn('std::atomic<uint32_t>', status)
        self.assertIn('compare_exchange_strong', status)
        self.assertIn('memory_order_acquire', status)
        for forbidden in ('malloc', 'new ', 'pthread', 'gRecorder', 'fopen', 'coverage.flag'):
            self.assertNotIn(forbidden, status)


if __name__ == '__main__':
    unittest.main()
