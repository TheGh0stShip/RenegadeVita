"""RVTP1 tutorial first-use prewarm list contract (pure Python, no compiler).

Checks that every root in port/platform/vita/a35_tutorial_prewarm.h comes
from the tutorial's own scripts or reviewed discovery evidence, that every
preset the tutorial scripts create is covered (or explicitly excluded), and
that the runtime wiring keeps the flag default-off. When the M00 discovery
receipt (build/dev208-m00-aggressive-typed.json) or the read-only retail data
(retail-pc/Data) is present in this checkout or a parent checkout, names are
also resolved against them; otherwise those checks are skipped.
"""
from __future__ import annotations

import json
import os
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HEADER = ROOT / "port/platform/vita/a35_tutorial_prewarm.h"
IMPL = ROOT / "port/platform/vita/a35_tutorial_prewarm.inc"
RUNTIME = ROOT / "port/platform/vita/a31_vita_runtime.cpp"
MISSION00 = ROOT / "staging/scripts/Mission00.cpp"
POWERUP_TABLE = ROOT / "staging/scripts/Toolkit_Powerup.cpp"
RECEIPT_NAME = "dev208-m00-aggressive-typed.json"

# Presets the tutorial scripts create that carry no loadable assets.
EXCLUDED = {
    # Null physics model; host object for the X0I_Drop02.txt Test_Cinematic.
    "invisible_object": "null model, cinematic host only",
}

# Roots that do not appear as a Mission00.cpp literal, with the tracked file
# and text that proves why they are reached during the tutorial.
INDIRECT_ROOTS = {
    # Mission00.cpp attaches Test_Cinematic "X0I_Drop02.txt" (always.dat), whose
    # Create_Real_Object line creates this preset (M00_AGGRESSIVE_DISCOVERY.md).
    "nod_transport_helicopter": (MISSION00, '"X0I_Drop02.txt"'),
    # M00_Soldier_Powerup_Grant (attached by the Nod_Minigunner_0 definition)
    # drops these twiddled power-ups when the star kills a tutorial Nod soldier.
    "tw_pow00_health": (POWERUP_TABLE, '"tw_POW00_Health"'),
    "tw_pow00_armor": (POWERUP_TABLE, '"tw_POW00_Armor"'),
}

SPAWN_PATTERNS = (
    re.compile(r'Create_Object\s*\(\s*"([^"]+)"'),
    re.compile(r'Give_PowerUp\s*\([^,;]+,\s*"([^"]+)"'),
    re.compile(r'Select_Weapon\s*\([^,;]+,\s*"([^"]+)"'),
    re.compile(r'\bvehicle\s*=\s*"([^"]+)"'),
)


def header_lists() -> dict[str, list[str]]:
    text = HEADER.read_text(encoding="latin1")
    lists = {}
    for match in re.finditer(r"static const char \*const (kTutorialPrewarm\w+)\[\]\s*=\s*\{(.*?)\};",
                             text, re.DOTALL):
        body = re.sub(r"//[^\n]*", "", match.group(2))
        lists[match.group(1)] = re.findall(r'"([^"]+)"', body)
    return lists


def tutorial_script_text() -> str:
    text = MISSION00.read_text(encoding="latin1")
    # The MTU_ tutorial scripts precede the MSK_ skirmish scripts in the file.
    end = text.find("DECLARE_SCRIPT (MSK_Controller")
    if end < 0:
        raise AssertionError("Mission00.cpp MSK_Controller boundary changed")
    return text[:end]


def tutorial_script_spawns() -> set[str]:
    text = re.sub(r"//[^\n]*", "", tutorial_script_text())
    names = set()
    for pattern in SPAWN_PATTERNS:
        names.update(name for name in pattern.findall(text) if name)
    return names


def find_upwards(relative: str) -> Path | None:
    for base in (ROOT, *ROOT.parents):
        candidate = base / relative
        if candidate.exists():
            return candidate
    return None


class TutorialPrewarmListTests(unittest.TestCase):
    def setUp(self):
        self.lists = header_lists()

    def all_roots(self) -> list[str]:
        return [name for key in ("kTutorialPrewarmPlayerWeapons", "kTutorialPrewarmPlayerPresets",
                                 "kTutorialPrewarmWorldPresets") for name in self.lists[key]]

    def test_header_lists_are_present_unique_and_bounded(self):
        self.assertEqual(set(self.lists), {"kTutorialPrewarmPlayerWeapons",
                                           "kTutorialPrewarmPlayerPresets",
                                           "kTutorialPrewarmWorldPresets",
                                           "kTutorialPrewarmSounds"})
        names = [name.lower() for values in self.lists.values() for name in values]
        self.assertEqual(len(names), len(set(names)), "duplicate prewarm root")
        self.assertTrue(all(values for values in self.lists.values()))
        self.assertLessEqual(len(names), 64, "prewarm roots must stay a small bounded list")

    def test_every_tutorial_script_spawn_is_covered_or_excluded(self):
        covered = {name.lower() for name in self.all_roots()}
        for name in sorted(tutorial_script_spawns()):
            with self.subTest(name=name):
                self.assertTrue(name.lower() in covered or name.lower() in EXCLUDED,
                                f"{name} is created by the tutorial scripts but not prewarmed")

    def test_every_root_comes_from_tracked_tutorial_source(self):
        spawns = {name.lower() for name in tutorial_script_spawns()}
        for name in self.all_roots():
            with self.subTest(name=name):
                key = name.lower()
                if key in spawns:
                    continue
                self.assertIn(key, INDIRECT_ROOTS, f"{name} has no tutorial provenance")
                path, needle = INDIRECT_ROOTS[key]
                self.assertIn(needle, path.read_text(encoding="latin1"))
        # The twiddled drops come from the original grant script.
        self.assertIn("DECLARE_SCRIPT(M00_Soldier_Powerup_Grant",
                      POWERUP_TABLE.read_text(encoding="latin1").replace(" ", ""))

    def test_roots_resolve_in_m00_discovery_receipt(self):
        override = os.environ.get("RENEGADE_M00_TYPED_RECEIPT")
        receipt = Path(override) if override else find_upwards(f"build/{RECEIPT_NAME}")
        if receipt is None or not receipt.exists():
            self.skipTest("M00 discovery receipt not present")
        data = json.loads(receipt.read_text())
        self.assertEqual(data.get("archive_name", "").lower(), "m00_tutorial.mix")
        known = {entry["name"].strip().lower() for entry in data["selected_definitions"]}
        for key, names in self.lists.items():
            for name in names:
                with self.subTest(list=key, name=name):
                    self.assertIn(name.lower(), known)
        roots = {name.lower() for name in data.get("reviewed_preset_roots", [])}
        self.assertIn("nod_transport_helicopter", roots)

    def test_retail_player_weapon_assets_are_outside_tutorial_dependency_list(self):
        override = os.environ.get("RENEGADE_RETAIL_DATA")
        data_dir = Path(override) if override else find_upwards("retail-pc/Data")
        if data_dir is None or not (data_dir / "always.dbs").exists():
            self.skipTest("read-only retail data not present")
        from tools.audit_m13_level_owners import chunks, definitions, flatten, microchunks, reference_fields
        from tools.renegade_cinematic_dependency_scan import MixArchive, parse_enum_constants

        symbols: dict[str, int] = {}
        parse_enum_constants(ROOT / "staging/combat/weaponmanager.cpp", symbols)
        variables = symbols["CHUNKID_WEAPON_DEF_VARIABLES"]
        model_fields = {symbols["MICROCHUNKID_WEAPON_DEF_MODEL"]: "model",
                        symbols["MICROCHUNKID_WEAPON_DEF_BACK_MODEL"]: "back",
                        symbols["MICROCHUNKID_WEAPON_DEF_FIRST_PERSON_MODEL"]: "first_person"}
        nodes = chunks(MixArchive(data_dir / "always.dbs").read_binary("objects.ddb"))
        defs = definitions(nodes, reference_fields(ROOT))
        by_name = {value["name"].lower(): key for key, value in defs.items()}
        factories = {}
        for manager in nodes:
            for group in manager.children if manager.kind == 0x101 else ():
                for factory in group.children if group.kind == 0x101 else ():
                    factories[factory.offset] = factory

        def weapon_models(weapon_id):
            factory = factories[defs[weapon_id]["offset"]]
            result = {}
            for node in flatten(factory.children):
                if node.kind == variables and not node.children:
                    for kind, value in microchunks(node.data):
                        if kind in model_fields and value.endswith(b"\0") and len(value) > 1:
                            name = value[:-1].decode("latin1").replace("/", "\\").rsplit("\\", 1)[-1]
                            result[model_fields[kind]] = name.lower()
            return result

        player_weapons = [by_name[name.lower()] for name in self.lists["kTutorialPrewarmPlayerWeapons"]]
        for name in self.lists["kTutorialPrewarmPlayerPresets"]:
            for prov in defs[by_name[name.lower()]]["definition_reference_provenance"]:
                if prov.get("field_name") == "MICROCHUNKID_DEF_GRANT_WEAPON_ID" and prov["id"] in defs:
                    player_weapons.append(prov["id"])
        self.assertGreaterEqual(len(set(player_weapons)), 9)

        def dep_names(archive, member):
            payload = MixArchive(data_dir / archive).read_binary(member)
            return {raw.decode("latin1").lower()
                    for raw in re.findall(rb"([A-Za-z0-9_\-\.\^ ]{2,})\x00", payload)}

        tutorial_dep = dep_names("M00_Tutorial.mix", "m00_tutorial.dep")
        always = {record[0].lower() for record in MixArchive(data_dir / "always.dat").entry_records}
        for weapon_id in sorted(set(player_weapons)):
            models = weapon_models(weapon_id)
            with self.subTest(weapon=defs[weapon_id]["name"]):
                first_person = models.get("first_person")
                self.assertTrue(first_person and first_person.startswith("f_gm_"), models)
                for filename in models.values():
                    self.assertIn(filename, always)
                    # The Vita loader reads only the mission dependency list, so
                    # these load on first use unless RVTP1 prepares them.
                    self.assertNotIn(filename, tutorial_dep)
                hands_idle = "f_ha_" + first_person[len("f_gm_"):-len(".w3d")] + "_idle.w3d"
                self.assertIn(hands_idle, always)

    def test_runtime_wiring_is_default_off_and_reuses_level_preparation(self):
        runtime = RUNTIME.read_text(encoding="latin1")
        impl = IMPL.read_text(encoding="latin1")
        self.assertIn('#include "a35_tutorial_prewarm.h"', runtime)
        self.assertIn('#include "a35_tutorial_prewarm.inc"', runtime)
        self.assertIn('"ux0:data/renegade/user/config/tutorial-prewarm-v1.flag"', impl)
        self.assertIn('memcmp(value, "RVTP1 ", 6U) == 0', impl)
        self.assertRegex(impl, r"TUTORIAL_PREWARM_DEFAULT\s*=\s*0U")
        for key in self.lists:
            self.assertIn(key, impl)
        # The implementation is included after the RVPL1 helpers it reuses.
        include_at = runtime.index('#include "a35_tutorial_prewarm.inc"')
        for helper in ("static bool Level_Preload_Memory_Floor_Reached()",
                       "static LevelSoundPrewarmOutcome Prewarm_Level_Sound_Definition(",
                       "bool Prepare_Explosion_Choice(", "bool A35_Vita_Warm_Render_Obj("):
            self.assertLess(runtime.index(helper), include_at, helper)
        for helper in ("Prewarm_Level_Sound_Definition(", "Prepare_Explosion_Choice(",
                       "A35_Vita_Warm_Render_Obj(", "Level_Preload_Memory_Floor_Reached()"):
            self.assertIn(helper, impl)
        # Only the tutorial reads the flag; assets load after the RVPL1 sounds
        # and before the HUD glyph/geometry steps and the M00 texture prewarm.
        body = runtime[runtime.index("void Prepare_Original_Level_Loading_Resources("):]
        body = body[:body.index("\n}\n")]
        self.assertIn('const bool tutorial = stricmp(archive, "M00_Tutorial.mix") == 0;', body)
        self.assertIn("tutorial ? Read_Tutorial_Prewarm_Mode() : 0U", body)
        sounds = body.index("Warm_Level_Sound_Pcm(presenter, label);")
        warm = body.index("Warm_Tutorial_First_Use_Resources(presenter, label, tutorial_mode, tutorial_plan);")
        glyphs = body.index("Warm_Original_HUD_Font_Glyphs(label);")
        self.assertLess(sounds, warm)
        self.assertLess(warm, glyphs)
        self.assertIn("? tutorial_plan.style_mask : 0U", body)

    def test_rvpl1_sound_warm_uses_the_shared_helper(self):
        runtime = RUNTIME.read_text(encoding="latin1")
        start = runtime.index("static void Warm_Level_Sound_Pcm(")
        body = runtime[start:runtime.index("\n}\n", start)]
        self.assertIn("Prewarm_Level_Sound_Definition(sound_ids[index].first, read_bytes, retained_bytes)", body)
        self.assertNotIn("Renegade_Miles_Prewarm_Pcm(", body)
        helper_start = runtime.index("static LevelSoundPrewarmOutcome Prewarm_Level_Sound_Definition(")
        helper = runtime[helper_start:runtime.index("\n}\n", helper_start)]
        self.assertEqual(helper.count("Renegade_Miles_Prewarm_Pcm("), 1)
        # Same path stripping as AudibleSoundDefinitionClass::Create_Sound.
        self.assertIn("name[1] != ':'", helper)


if __name__ == "__main__":
    unittest.main()
