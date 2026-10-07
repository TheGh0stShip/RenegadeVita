"""Source contracts for the Mission 08 completion route and mobile-vehicle slot.

These checks inspect staged/original source only. They do not prove native
mission progression, which still requires a physical Vita run.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
STAGED = ROOT / "staging/scripts/mission08.cpp"
PATCH = ROOT / "port/patches/scripts-a36-m08-mobile-vehicle-attack-slot.patch"
STAGE_SCRIPT = ROOT / "tools/stage_sources.sh"
RAVESHAW = ROOT / "staging/combat/raveshawbossgameobj.cpp"


def script_body(source, name):
    start = re.search(r"DECLARE_SCRIPT\s*\(\s*%s\s*," % re.escape(name), source).start()
    following = source.find("DECLARE_SCRIPT", start + 1)
    return source[start:following if following != -1 else len(source)]


class MobileVehicleAttackSlot(unittest.TestCase):
    def setUp(self):
        self.body = script_body(STAGED.read_text(encoding="latin-1"), "M08_Mobile_Vehicle")

    def test_created_sentinel_is_retained(self):
        self.assertIn("loc = 100;", self.body)

    def test_every_slot_read_is_bounded(self):
        unguarded = re.findall(r"attack_loc\s*\[\s*loc\s*\]", self.body)
        self.assertEqual(len(unguarded), 1, "only the guarded accessor may index by loc")
        accessor = self.body[self.body.index("int Current_Attack_Location_ID"):]
        accessor = accessor[:accessor.index("}\n\n") + 1]
        self.assertIn("if (loc < 0 || loc > 10)", accessor)
        self.assertIn("return 0;", accessor)
        self.assertEqual(self.body.count("Find_Object (Current_Attack_Location_ID())"), 2)

    def test_patch_is_applied_after_apache_bounds(self):
        text = STAGE_SCRIPT.read_text()
        apache = text.index("scripts-a35-apache-controller-bounds.patch")
        mobile = text.index(PATCH.name)
        self.assertLess(apache, mobile)
        self.assertTrue(PATCH.exists())


class RaveshawReleaseGuards(unittest.TestCase):
    def setUp(self):
        self.text = RAVESHAW.read_text(encoding="latin-1")

    def test_lightning_strike_roll_never_divides_by_zero(self):
        self.assertIn("if (star_dist > 0 && FreeRandom.Get_Int (star_dist) == 1) {", self.text)
        self.assertNotIn("if (FreeRandom.Get_Int (star_dist) == 1)", self.text)

    def test_stealth_soldier_create_is_checked_before_use(self):
        body = self.text[self.text.index("RaveshawBossGameObjClass::Create_Stealth_Soldier"):]
        body = body[:body.index("Link_Thrown_Object_To_Hands")]
        guard = body.index("if (soldier == NULL || soldier->Peek_Physical_Object () == NULL) {")
        self.assertLess(guard, body.index("StealthSoldier = phys_game_obj;"))
        self.assertLess(guard, body.index("soldier->Set_Transform (tm);"))
        self.assertNotIn("phys_game_obj->As_SoldierGameObj ();\n\tsoldier->", body)

    def test_guards_apply_after_waypath_guard(self):
        text = STAGE_SCRIPT.read_text()
        waypath = text.index("combat-a36-boss-waypath-release-guard.patch")
        self.assertLess(waypath, text.index("combat-a36-raveshaw-star-dist-modulo-guard.patch"))
        self.assertLess(waypath, text.index("combat-a36-raveshaw-stealth-soldier-create-guard.patch"))


class CompletionRoute(unittest.TestCase):
    def test_original_raveshaw_boss_reports_success(self):
        text = RAVESHAW.read_text(encoding="latin-1")
        landing = text[text.index("STATE_IMPL_THINK(RAVESHAW_STATE_DEATH_LANDING)"):]
        self.assertIn("CombatManager::Mission_Complete (true);", landing[:1200])

    def test_relocation_creates_raveshaw_and_objective_805(self):
        source = STAGED.read_text(encoding="latin-1")
        havoc = script_body(source, "M08_Havoc_DLS")
        self.assertIn("Commands->Create_Object (\"Raveshaw\"", havoc)
        self.assertIn("805, 3", havoc)
        controller = script_body(source, "M08_Objective_Controller")
        self.assertIn("type == M08_RELOCATE", controller)
        self.assertIn("Commands->Mission_Complete ( true );", controller)


def function_body(text, signature):
    start = text.index(signature)
    return text[start:text.index("\n}\n", start)]


class RaveshawThrownObjectLiveness(unittest.TestCase):
    def setUp(self):
        self.text = RAVESHAW.read_text(encoding="latin-1")
        self.header = (ROOT / "staging/combat/raveshawbossgameobj.h").read_text(encoding="latin-1")

    def test_reference_tracks_pointer(self):
        self.assertIn("GameObjReference\t\t\tThrownObjectRef;", self.header)
        begin = function_body(self.text, "STATE_IMPL_BEGIN(OVERALL_STATE_THROWING_OBJECT) (void)")
        self.assertIn("ThrownObject = Find_Object_To_Throw ();\n\tThrownObjectRef = ThrownObject;", begin)
        self.assertIn("ThrownObjectRef = ThrownObject;", function_body(self.text, "::On_Post_Load (void)"))
        verify = function_body(self.text, "::Verify_Thrown_Object (void)")
        self.assertIn("if (ThrownObject == NULL || ThrownObjectRef.Get_Ptr () != NULL) {", verify)
        self.assertIn("ThrownObject = NULL;", verify)

    def test_verified_before_think_and_save(self):
        think = function_body(self.text, "RaveshawBossGameObjClass::Think (void)")
        self.assertLess(think.index("Verify_Thrown_Object ();"), think.index("OverallState.Think ();"))
        save = function_body(self.text, "RaveshawBossGameObjClass::Save (ChunkSaveClass & csave)")
        self.assertLess(save.index("Verify_Thrown_Object ();"), save.index("csave.Begin_Chunk"))

    def test_every_dereference_is_guarded(self):
        goto = function_body(self.text, "STATE_IMPL_THINK(MOVE_STATE_GOTO_THROW_OBJECT) (void)")
        self.assertLess(goto.index("if (ThrownObject == NULL) {"), goto.index("ThrownObject->Get_Position"))
        self.assertIn("OverallState.Set_State (OVERALL_STATE_CHASE_STAR);", goto)
        for state in ("STATE_IMPL_BEGIN(THROWN_OBJECT_STATE_FLYING) (void)",
                      "STATE_IMPL_THINK(THROWN_OBJECT_STATE_FLYING) (void)"):
            body = function_body(self.text, state)
            self.assertLess(body.index("if (ThrownObject == NULL) {"), body.index("ThrownObject->Get_Position"))

    def test_patch_applies_after_grounded_landing(self):
        text = STAGE_SCRIPT.read_text()
        self.assertLess(text.index("combat-a38-raveshaw-jump-grounded-landing.patch"),
                        text.index("combat-a38-raveshaw-thrown-object-liveness.patch"))


class ObjectiveConversationGates(unittest.TestCase):
    GATES = (("M08_Activate_Objective_802", "300502"), ("M08_Activate_Objective_803", "300803"),
             ("M08_Activate_Objective_804", "300804"), ("M08_Activate_Objective_806", "300806"))

    def test_monitor_precedes_start_and_sends_once(self):
        source = STAGED.read_text(encoding="latin-1")
        for name, action in self.GATES:
            body = script_body(source, name)
            self.assertLess(body.index("Commands->Monitor_Conversation (obj, conv_id);"),
                            body.index("Commands->Start_Conversation (conv_id, %s);" % action), name)
            self.assertIn("SAVE_VARIABLE( objective_sent, 2 );", body)
            self.assertIn("objective_sent = false;", body)
            self.assertIn("if(action_id == %s && !objective_sent && " % action, body)
            self.assertEqual(body.count("objective_sent = true;"), 1, name)

    def test_patch_applies_after_mobile_vehicle_slot(self):
        text = STAGE_SCRIPT.read_text()
        self.assertLess(text.index(PATCH.name),
                        text.index("scripts-a38-m08-objective-conversation-monitor-first.patch"))


if __name__ == "__main__":
    unittest.main()
