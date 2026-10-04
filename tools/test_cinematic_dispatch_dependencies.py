from pathlib import Path
import unittest
from tools.audit_cinematic_dispatch_dependencies import inventory
from tools.audit_cinematic_slots import KNOWN_COMMANDS


class DispatchInventoryTests(unittest.TestCase):
    def test_current_branches_match_existing_control_vocabulary(self):
        root=Path(__file__).resolve().parents[1]
        result=inventory((root/'staging/scripts/Test_Cinematic.cpp').read_text())
        self.assertEqual([row['title'].lower() for row in result['rows']],list(KNOWN_COMMANDS))
        self.assertEqual(result['total'],18)
        self.assertEqual(len(result['unique_engine_commands']),32)

    def test_comments_do_not_create_branches_or_calls(self):
        code='''void Parse_Command(char *command) {
// if (Title_Match(&command,"Fake")) Missing(command);
if (Title_Match(&command,"Real")) Handler(command);
} void Handler(char *params) {
// Commands->Fake();
Commands->Create_2D_Sound(params);
}'''
        result=inventory(code)
        self.assertEqual(result['unique_engine_commands'],['Create_2D_Sound'])
        self.assertEqual(result['rows'][0]['status'],'unknown')

    def test_missing_dispatch_is_explicit(self):
        with self.assertRaises(ValueError):inventory('void Parse_Command(char *command) {}')
