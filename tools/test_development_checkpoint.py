from pathlib import Path
import subprocess
import tempfile
import unittest

from tools.request_tutorial_checkpoint import queue_request


class DevelopmentCheckpointTests(unittest.TestCase):
    def test_runtime_reactivates_only_the_unique_saved_player_before_admission(self):
        root = Path(__file__).resolve().parents[1]
        runtime = (root / "port/platform/vita/a31_vita_runtime.cpp").read_text()
        start = runtime.index("// WWSaveLoad restores the player/star links")
        end = runtime.index("result.player_created =", start)
        checkpoint = runtime[start:end]
        activate = checkpoint.index("local_player = cGod::Create_Player")
        for guard in (
            "local_player == NULL && cPlayerManager::Count() == 0",
            "saved_node->Next() == NULL",
            "saved_player == NULL || saved_player->Is_Active()",
            "saved_player->Get_Id() != cNetwork::Get_My_Id()",
            "saved_player->Get_GameObj() != restored_star",
            "restored_star->Get_Player_Data() != saved_player",
            "cPlayerManager::Find_Inactive_Player(saved_player->Get_Name()) != saved_player",
        ):
            self.assertLess(checkpoint.index(guard), activate)
        self.assertIn("saved_player->Get_Name(), -1, 0", checkpoint)
        self.assertGreater(checkpoint.index("local_player != saved_player"), activate)
        self.assertGreater(checkpoint.index("FAIL restored local player/star identity"), activate)
        self.assertNotIn("Set_Is_Active(", checkpoint)
        self.assertNotIn("Create_Commando(", checkpoint)

    def test_native_parser(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "parser.cpp"
            executable = Path(directory) / "parser"
            source.write_text(r'''
#include "a31_development_checkpoint.h"
#include <assert.h>
int main() {
    char output[96];
    const char *valid[] = {"RVCP1 quicksave.sav\n", "RVCP1 M00-1_OK.SAV\r\n"};
    for (auto value : valid) {
        assert(A31DevelopmentCheckpoint::Parse(value, strlen(value), output, sizeof(output)));
        assert(strncmp(output, "save/", 5) == 0);
    }
    const char *bad[] = {"", "RVCP1 a.sav", "RVCP2 a.sav\n", "RVCP1 ../a.sav\n",
        "RVCP1 /a.sav\n", "RVCP1 a/b.sav\n", "RVCP1 a\\b.sav\n", "RVCP1 a:s.sav\n",
        "RVCP1 .sav\n", "RVCP1 _a.sav\n", "RVCP1 a.sav\nextra", "RVCP1 a.sav \n",
        "RVCP1 a.sav\n\n", "RVCP1 a.sav\r\r\n", "RVCP1 a.txt\n", "RVCP1 a b.sav\n"};
    for (auto value : bad) {
        assert(!A31DevelopmentCheckpoint::Parse(value, strlen(value), output, sizeof(output)));
        assert(output[0] == 0);
    }
    assert(!A31DevelopmentCheckpoint::Parse(valid[0], strlen(valid[0]), output, 5));
    assert(!A31DevelopmentCheckpoint::Parse(NULL, 12, output, sizeof(output)));
    assert(!A31DevelopmentCheckpoint::Parse(valid[0], strlen(valid[0]), NULL, 0));
    const char *missions[] = {"RVMS1 M13.mix\n", "RVMS1 M01.mix\r\n"};
    for (auto value : missions) {
        assert(A31DevelopmentCheckpoint::Parse_Mission(value, strlen(value), output, sizeof(output)));
        assert(strcmp(output + 3, ".mix") == 0);
    }
    const char *bad_missions[] = {"RVMS1 ../M01.mix\n", "RVMS1 M01.sav\n",
        "RVMS1 M01.mix\nextra", "RVMS1 m01.mix\n", "RVMS1 M0x.mix\n",
        "RVMS1 M01.mix\r\r\n", "RVMS1 M01.mix", "RVMS1 M01.mix \n"};
    for (auto value : bad_missions) {
        assert(!A31DevelopmentCheckpoint::Parse_Mission(value, strlen(value), output, sizeof(output)));
        assert(output[0] == 0);
    }
    assert(!A31DevelopmentCheckpoint::Parse_Mission(missions[0], strlen(missions[0]), output, 7));
    assert(A31DevelopmentCheckpoint::Parse_M13_Completion("RVMC1 M13.mix\n", 14));
    assert(!A31DevelopmentCheckpoint::Parse_M13_Completion("RVMC1 M01.mix\n", 14));
    assert(!A31DevelopmentCheckpoint::Parse_M13_Completion("RVMC1 M13.mix", 13));
    assert(!A31DevelopmentCheckpoint::Parse_M13_Completion(NULL, 14));
}
''')
            subprocess.run(["c++", "-std=c++11", "-Wall", "-Wextra", "-Werror",
                            "-I", str(root / "port/platform"), str(source), "-o", str(executable)],
                           check=True, capture_output=True, text=True)
            subprocess.run([str(executable)], check=True)

    def test_queue_preserves_save_and_existing_request(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "save").mkdir()
            save = root / "save/quicksave.sav"
            save.write_bytes(b"fixture only, not a valid game save")
            original = save.read_bytes()
            record = queue_request(root, save.name, root / "receipt.json")
            self.assertFalse(record["reload_proven"])
            self.assertEqual(save.read_bytes(), original)
            request = root / "config/dev-checkpoint-launch-v1.txt"
            self.assertEqual(request.read_bytes(), b"RVCP1 quicksave.sav\n")
            with self.assertRaises(FileExistsError):
                queue_request(root, save.name, root / "another-receipt.json")
            self.assertEqual(request.read_bytes(), b"RVCP1 quicksave.sav\n")

    def test_bad_names_and_missing_save_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for slot in ("../a.sav", "a/b.sav", "_a.sav", "a.sav\n", "a" * 65 + ".sav", "missing.sav"):
                with self.subTest(slot=slot), self.assertRaises(ValueError):
                    queue_request(root, slot, root / "receipt.json")
            self.assertFalse((root / "config").exists())

    def test_symlink_save_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "save").mkdir()
            (root / "outside").write_bytes(b"unchanged")
            (root / "save/a.sav").symlink_to(root / "outside")
            with self.assertRaises(ValueError):
                queue_request(root, "a.sav", root / "receipt.json")


if __name__ == "__main__":
    unittest.main()
