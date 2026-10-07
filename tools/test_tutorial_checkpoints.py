"""Checkpoint archives preserve native bytes without inventing progression evidence."""
import json
from pathlib import Path
import re
import struct
import subprocess
import sys
import tempfile
import unittest

from tools.request_tutorial_checkpoint import clear_sticky, queue_request
from tools.tutorial_checkpoints import (
    CHUNKID_COMBAT, COMBAT_OBJECTIVES, LEVEL_DATA, LEVEL_INFO, OBJECTIVE_ENTRY,
    OBJECTIVE_MANAGER_VARIABLES, OBJECTIVE_VARIABLES, SEGMENTS, derive_segment,
    parse_save_bytes, read_save, slot_name, status_vector)

ROOT = Path(__file__).resolve().parents[1]
TOOL = Path(__file__).with_name("tutorial_checkpoints.py")
CONTENT = "a" * 64
HIDDEN = (3, 0.0)


def chunk(identifier, payload, sub_chunks=False):
    return struct.pack("<II", identifier, len(payload) | (0x80000000 if sub_chunks else 0)) + payload


def micro(identifier, payload):
    return bytes((identifier, len(payload))) + payload


def objective(identifier, status, age):
    variables = (micro(1, struct.pack("<i", identifier)) + micro(2, struct.pack("<i", 1)) +
                 micro(3, struct.pack("<i", status)) + micro(5, b"IDS_SND\0") +
                 micro(7, struct.pack("<i", 1000 + identifier)) + micro(11, struct.pack("<f", age)))
    return chunk(OBJECTIVE_ENTRY, chunk(OBJECTIVE_VARIABLES, variables), True)


def save_bytes(states=(HIDDEN,) * 6, map_name=b"M00_Tutorial.lsd", description="Quicksave A",
               info_extra=b"", tail=b""):
    """A minimal save in the original envelope; states[i] is (status, age) of objective i+1."""
    manager = b"".join(objective(index + 1, *state) for index, state in enumerate(states))
    manager += chunk(OBJECTIVE_MANAGER_VARIABLES, micro(1, struct.pack("<i", 0)))
    combat = chunk(916991654, b"objects", True) + chunk(COMBAT_OBJECTIVES, manager, True)
    level_data = chunk(CHUNKID_COMBAT, combat, True) + chunk(0x00020050, b"physics")
    info = (micro(1, map_name + b"\0") + micro(3, (description + "\0").encode("utf-16-le")) +
            micro(2, struct.pack("<i", 0)) + info_extra)
    return chunk(LEVEL_INFO, info) + chunk(LEVEL_DATA, level_data, True) + tail


def run(*arguments):
    return subprocess.run([sys.executable, str(TOOL), *map(str, arguments)],
                          capture_output=True, text=True)


class NativeEnvelopeTests(unittest.TestCase):
    def test_parses_original_metadata_and_objectives(self):
        info = parse_save_bytes(save_bytes([(1, 600.0), (0, 50.0)] + [HIDDEN] * 4))
        self.assertEqual((info["map"], info["description"], info["mission_description_id"]),
                         ("M00_Tutorial.lsd", "Quicksave A", 0))
        self.assertEqual([(entry["id"], entry["status"]) for entry in info["objectives"]],
                         [(1, 1), (2, 0), (3, 3), (4, 3), (5, 3), (6, 3)])
        self.assertEqual(status_vector(info["objectives"]), "1/0/3/3/3/3")
        # Unknown level-info microchunks are ignored, as the native reader does.
        self.assertEqual(parse_save_bytes(save_bytes(info_extra=micro(9, b"x")))["map"], "M00_Tutorial.lsd")

    def test_rejects_what_the_native_envelope_rejects(self):
        level_data = chunk(LEVEL_DATA, b"data")
        good_info = chunk(LEVEL_INFO, micro(1, b"M00_Tutorial.lsd\0") +
                          micro(2, b"\0" * 4) + micro(3, "d\0".encode("utf-16-le")))
        cases = {
            "must name a .lsd": save_bytes(map_name=b"M00_Tutorial.mix"),
            "Ambiguous map identity": save_bytes(info_extra=micro(1, b"M01.lsd\0")),
            "NUL-terminated string": save_bytes(map_name=b"M00\0_Tutorial.lsd"),
            "level info then level data": level_data + good_info,
            "level info then level data only": good_info + level_data + chunk(7, b""),
            "lacks map, mission or description": chunk(LEVEL_INFO, micro(1, b"M00_Tutorial.lsd\0")) + level_data,
            "empty level data": good_info + chunk(LEVEL_DATA, b""),
            "UTF-16": chunk(LEVEL_INFO, micro(1, b"M00_Tutorial.lsd\0") + micro(2, b"\0" * 4) +
                            micro(3, b"d\0e")) + level_data,
            "Truncated": save_bytes(tail=b"tail"),
        }
        for message, data in cases.items():
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, re.escape(message)):
                parse_save_bytes(data)

    def test_objective_damage_does_not_hide_a_valid_envelope(self):
        data = bytearray(save_bytes())
        marker = struct.pack("<I", OBJECTIVE_VARIABLES)
        data[data.index(marker):data.index(marker) + 4] = struct.pack("<I", 1)
        info = parse_save_bytes(bytes(data))
        self.assertIsNone(info["objectives"])
        self.assertIn("variables chunk", info["objectives_error"])

    def test_slot_grammar_matches_native_request_parser(self):
        for slot in ("quicksave.sav", "M00-1_OK.SAV", "rv_cp_" + "a" * 48 + ".sav", "a" * 64 + ".sav"):
            self.assertEqual(slot_name(slot), slot)
        for slot in ("../a.sav", "a/b.sav", "a\\b.sav", "a:s.sav", ".sav", "_a.sav", "a.sav ",
                     "a.txt", "a b.sav", "a" * 65 + ".sav"):
            with self.subTest(slot=slot), self.assertRaises(ValueError):
                slot_name(slot)


class SegmentTests(unittest.TestCase):
    def segment(self, states):
        return derive_segment(parse_save_bytes(save_bytes(states))["objectives"])["segment"]

    def test_segments_follow_youngest_visible_original_objective(self):
        table = [
            ([HIDDEN] * 6, "logan-course"),
            ([(0, 50.7)] + [HIDDEN] * 5, "to-sydney"),
            ([(1, 10.0)] + [HIDDEN] * 5, "sydney-hud-lesson"),
            ([(1, 644.9), (0, 50.1)] + [HIDDEN] * 4, "to-gunner"),
            ([(1, 970.0), (1, 375.1)] + [HIDDEN] * 4, "gunner-range"),
            ([(1, 900.0), (1, 500.0), (0, 30.0)] + [HIDDEN] * 3, "to-hotwire"),
            ([(1, 1243.4), (1, 648.7), HIDDEN, (1, 96.7), HIDDEN, HIDDEN], "mobius-refinery"),
            ([(1, 1749.3), (1, 1154.7), (1, 261.5), (1, 602.8), HIDDEN, HIDDEN], "hotwire-vehicles"),
            # Trigger zones can complete objectives out of the scripted order.
            ([(1, 686.2), (0, 91.5), HIDDEN, HIDDEN, (1, 36.0), HIDDEN], "petrova-power-plant"),
            ([(1, 9.0)] * 5 + [(0, 3.0)], "to-officers"),
            ([(1, 9.0)] * 6, "mission-end"),
            ([(2, 4.0)] + [HIDDEN] * 5, "failed-sydney"),
            ([(1, 5.0), (1, 5.0)] + [HIDDEN] * 4, "gunner-range"),  # tie: higher ID
        ]
        for states, expected in table:
            with self.subTest(expected=expected):
                self.assertEqual(self.segment(states), expected)
        self.assertEqual(derive_segment(None)["segment"], "unknown")
        self.assertTrue({name for _, name in table[:-2]} <= set(SEGMENTS))


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.user = self.root / "user"
        (self.user / "save").mkdir(parents=True)
        self.vault = self.root / "vault"
        self.evidence = self.root / "receipt.json"
        self.evidence.write_text('{"state": "test position, mission unassessed"}')

    def tearDown(self):
        self.temporary.cleanup()

    def capture(self, checkpoint_id, slot, data):
        (self.user / "save" / slot).write_bytes(data)
        result = run("capture", "--id", checkpoint_id, "--vault", self.vault, "--user-dir", self.user,
                     "--content-id", CONTENT, "--slot", slot, "--build", "A3.5-dev117",
                     "--evidence", self.evidence)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result

    def launch(self, *extra):
        return run("launch", "--vault", self.vault, "--user-dir", self.user,
                   "--content-id", CONTENT, "--offline", *extra)

    def test_unassessed_archive_and_original_restore(self):
        data = save_bytes([(1, 600.0), (0, 50.0)] + [HIDDEN] * 4)
        self.capture("test-position", "source.sav", data)
        master = self.vault / "test-position/checkpoint.sav"
        metadata = json.loads((master.parent / "manifest.json").read_text())
        self.assertEqual(metadata["segment_status"], "UNASSESSED")
        self.assertEqual((metadata["derived_segment"], metadata["derived_status_1_6"]),
                         ("to-gunner", "1/0/3/3/3/3"))
        self.assertFalse(metadata["cross_build_load_validated"])
        self.assertEqual(master.read_bytes(), data)
        self.assertFalse(master.stat().st_mode & 0o222)
        repeated = run("capture", "--id", "test-position", "--vault", self.vault, "--user-dir",
                       self.user, "--content-id", CONTENT, "--slot", "source.sav", "--build", "x",
                       "--evidence", self.evidence)
        self.assertNotEqual(repeated.returncode, 0)
        restore = ["restore", "--id", "test-position", "--vault", self.vault, "--user-dir", self.user,
                   "--content-id", CONTENT, "--slot", "fresh.sav", "--offline"]
        first = run(*restore)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertIn("RESTORED_NEW_SLOT", first.stdout)
        self.assertEqual((self.user / "save/fresh.sav").read_bytes(), data)
        again = run(*restore)
        self.assertEqual(again.returncode, 0, again.stderr)
        self.assertIn("REUSED_IDENTICAL_SLOT", again.stdout)
        (self.user / "save/other.sav").write_bytes(b"live user save, never overwritten")
        clash = run(*restore[:-2], "other.sav", "--offline")
        self.assertNotEqual(clash.returncode, 0)
        self.assertEqual((self.user / "save/other.sav").read_bytes(), b"live user save, never overwritten")
        wrong_content = run(*[("b" * 64 if value == CONTENT else value) for value in restore])
        self.assertIn("Retail content", wrong_content.stderr)
        (self.user / "save/source.sav").write_bytes(data + b"tail")
        with self.assertRaisesRegex(ValueError, "Truncated"):
            read_save(self.user / "save/source.sav")

    def test_launch_queues_one_shot_then_sticky_requests(self):
        data = save_bytes([(1, 970.0), (1, 375.1)] + [HIDDEN] * 4)
        self.capture("m00-gunner", "quicksaveB.sav", data)
        request = self.user / "config/dev-checkpoint-launch-v1.txt"
        flag = self.user / "config/tutorial-checkpoint-v1.flag"
        first = self.launch("--id", "m00-gunner")
        self.assertEqual(first.returncode, 0, first.stderr)
        output = json.loads(first.stdout)
        self.assertEqual(output["segment"], "gunner-range")
        self.assertIn("status_1_6=1/1/3/3/3/3", output["expected_log"][1])
        self.assertEqual(request.read_bytes(), b"RVCP1 rv_cp_m00-gunner.sav\n")
        self.assertEqual((self.user / "save/rv_cp_m00-gunner.sav").read_bytes(), data)
        self.assertTrue(Path(output["receipt"]).is_file())
        pending = self.launch("--id", "m00-gunner")
        self.assertNotEqual(pending.returncode, 0)  # Never replace a pending one-shot.
        request.unlink()  # What the native route does on consumption.
        sticky = self.launch("--segment", "gunner-range", "--sticky")
        self.assertEqual(sticky.returncode, 0, sticky.stderr)
        self.assertIn("REUSED_IDENTICAL_SLOT", sticky.stdout)
        self.assertEqual(flag.read_bytes(), b"RVTC1 rv_cp_m00-gunner.sav\n")
        replaced = self.launch("--id", "m00-gunner", "--sticky", "--slot", "gunner2.sav")
        self.assertEqual(replaced.returncode, 0, replaced.stderr)
        self.assertEqual(flag.read_bytes(), b"RVTC1 gunner2.sav\n")
        self.assertTrue(clear_sticky(self.user))
        self.assertFalse(flag.exists())
        self.assertFalse(clear_sticky(self.user))
        flag.write_bytes(b"not an RVTC1 flag\n")
        with self.assertRaisesRegex(ValueError, "non-RVTC1"):
            clear_sticky(self.user)
        with self.assertRaisesRegex(ValueError, "non-RVTC1"):
            queue_request(self.user, "gunner2.sav", self.root / "r.json", sticky=True)
        self.assertEqual(flag.read_bytes(), b"not an RVTC1 flag\n")

    def test_sticky_requires_an_original_tutorial_save(self):
        (self.user / "save/m01.sav").write_bytes(save_bytes(map_name=b"M01.lsd"))
        with self.assertRaisesRegex(ValueError, "M00 tutorial"):
            queue_request(self.user, "m01.sav", self.root / "r.json", sticky=True)
        self.assertFalse((self.user / "config/tutorial-checkpoint-v1.flag").exists())

    def test_segment_selection_must_be_unambiguous(self):
        self.capture("a-sydney", "a.sav", save_bytes([(0, 5.0)] + [HIDDEN] * 5))
        self.capture("b-sydney", "b.sav", save_bytes([(0, 9.0)] + [HIDDEN] * 5))
        ambiguous = self.launch("--segment", "to-sydney")
        self.assertIn("matches 2 vault checkpoints: a-sydney, b-sydney", ambiguous.stderr)
        missing = self.launch("--segment", "mission-end")
        self.assertIn("matches 0 vault checkpoints", missing.stderr)
        self.assertFalse((self.user / "config").exists())

    def test_catalog_correlates_runtime_log_and_verify_log_checks_reload(self):
        data = save_bytes([(1, 644.9), (0, 50.1)] + [HIDDEN] * 4)
        (self.user / "save/quicksaveA.sav").write_bytes(data)
        (self.user / "save/broken.sav").write_bytes(b"\0" * 32)
        progress = ("A3.5 mission progress: frame={frame} star/control=1/1 objectives=6 "
                    "status_1_6={status} active_conversations=1 active={active} id/state=1/2\n")
        log = self.root / "a35-runtime.log"
        log.write_text(
            progress.format(frame=10, status="1/3/3/3/3/3", active="MTU_SYDNEY_RADAR") +
            progress.format(frame=11, status="1/0/3/3/3/3", active="none") +
            f"A3.5 save write: path=ux0:data/renegade/user/save/quicksaveA.sav bytes={len(data)} "
            "elapsed_us=9000 success=1\n" +
            "A4 checkpoint: RVTC1 sticky tutorial handoff latched=1 source=save/quicksaveA.sav; flag retained\n" +
            progress.format(frame=0, status="1/0/3/3/3/3", active="none"))
        catalog_json = self.root / "catalog.json"
        listed = run("catalog", "--user-dir", self.user, "--log", log, "--json", catalog_json)
        self.assertEqual(listed.returncode, 0, listed.stderr)
        rows = {row["slot"]: row for row in json.loads(catalog_json.read_text())["rows"]}
        self.assertEqual(rows["quicksaveA.sav"]["segment"], "to-gunner")
        self.assertEqual(rows["quicksaveA.sav"]["log"]["status"], "LOG_OBJECTIVES_AGREE")
        self.assertTrue(rows["quicksaveA.sav"]["log"]["bytes_match"])
        self.assertTrue(rows["broken.sav"]["native_envelope"].startswith("REJECTED"))
        verified = run("verify-log", "--save", self.user / "save/quicksaveA.sav", "--log", log)
        self.assertEqual(verified.returncode, 0, verified.stdout + verified.stderr)
        self.assertEqual(json.loads(verified.stdout)["status"], "OBJECTIVES_MATCH_AFTER_LOAD")
        log.write_text(log.read_text().replace("frame=0 star/control=1/1 objectives=6 status_1_6=1/0",
                                               "frame=0 star/control=1/1 objectives=6 status_1_6=3/3"))
        differs = run("verify-log", "--save", self.user / "save/quicksaveA.sav", "--log", log)
        self.assertEqual(differs.returncode, 1)
        self.assertEqual(json.loads(differs.stdout)["status"], "OBJECTIVES_DIFFER_AFTER_LOAD")
        # The original in-game Load menu handoff is recognised as well.
        log.write_text("A4 load: original source handoff after completed session teardown "
                       "source=save\\quicksaveA.sav replay_difficulty=-1\n" +
                       progress.format(frame=0, status="1/0/3/3/3/3", active="none"))
        self.assertEqual(run("verify-log", "--save", self.user / "save/quicksaveA.sav",
                             "--log", log).returncode, 0)


class NativeContractTests(unittest.TestCase):
    def test_sticky_route_is_opt_in_retained_and_first_entry_only(self):
        header = (ROOT / "port/platform/a31_development_checkpoint.h").read_text()
        self.assertIn('return Parse_Save_Slot_Request("RVCP1 ", data, bytes, source, capacity);', header)
        self.assertIn('return Parse_Save_Slot_Request("RVTC1 ", data, bytes, source, capacity);', header)
        runtime = (ROOT / "port/platform/vita/a31_vita_runtime.cpp").read_text()
        sticky = runtime[runtime.index("bool Try_Latch_Sticky_Tutorial_Checkpoint()"):
                         runtime.index("bool Try_Latch_Startup_Development_Checkpoint()")]
        self.assertIn("#if RENEGADE_VITA_DEVELOPMENT_CHECKPOINT", sticky)
        self.assertIn('"ux0:data/renegade/user/config/tutorial-checkpoint-v1.flag"', sticky)
        self.assertIn("Parse_Tutorial_Sticky", sticky)
        self.assertIn('stricmp(archive, "M00_Tutorial.mix") == 0', sticky)
        self.assertIn("A4_Frontend_Is_Tutorial_Source(source)", sticky)
        self.assertNotIn("remove(", sticky)
        self.assertNotIn("CombatManager::Load", sticky)
        self.assertLess(sticky.index("A4_Frontend_Resolve_Single_Player_Archive"),
                        sticky.index("A4_Frontend_Latch_Start_Game(source, -1, 0UL);"))
        startup = runtime[runtime.index("bool Try_Latch_Startup_Development_Checkpoint()"):]
        startup = startup[:startup.index("\n}\n")]
        self.assertIn("static bool first_frontend_entry = true;", startup)
        self.assertIn("return Try_Latch_Development_Save() ||\n\t\t(sticky_allowed && "
                      "Try_Latch_Sticky_Tutorial_Checkpoint());", startup)
        self.assertIn("else if (!Try_Latch_Startup_Development_Checkpoint()) {\n\t\tmovie_mode.Activate();",
                      runtime)
        self.assertNotIn("else if (!Try_Latch_Development_Save()) {", runtime)


if __name__ == "__main__":
    unittest.main()
