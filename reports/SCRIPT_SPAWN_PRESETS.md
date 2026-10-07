# Script-spawned presets outside the cinematic warm set (M13, M01)

Method: cinematic set = every `Create_Real_Object` preset (arg 2) in all `*.txt`
entries of the retail level MIX, parsed with
`tools/renegade_cinematic_dependency_scan.py` (`MixArchive`, `parse_command`).
Script set = string literals passed to `Create_Object` / `Create_Real_Object`
in comment-stripped `staging/scripts/*.cpp`. Comparison is case-insensitive.
Literals only; presets chosen via variables/arrays/params are not captured.
Retail MIX was read in place (Vita3K ux0 tree); nothing retail is committed.

| Mission | Cinematic presets | Script literals | Not in cinematic set |
|---|---|---|---|
| M13 (`Test_DLS.cpp`, `MissionX0.cpp`) | 27 | 11 | 5 |
| M01 (`Mission01.cpp`) | 16 | 19 | 18 |

## Proposed static supplement table

```cpp
// Warmed in addition to cinematic Create_Real_Object presets.
static const char *const kM13ScriptSpawnPresets[] = {
    "Generic_Cinematic", "Invisible_Object", "Large_Blocker",
    "MX0_GDI_Medium_Tank_Destroyed", "Obelisk Effect",
};
static const char *const kM01ScriptSpawnPresets[] = {
    "Invisible_Object", "Level_01_Keycard", "Level_02_Keycard",
    "Level_03_Keycard", "M01_GDI_Gunboat", "NOD_Apache", "Nod_Buggy",
    "Nod_FlameThrower_0", "Nod_Harvester", "Nod_Light_Tank_Dec",
    "Nod_MiniGunner_0", "Nod_MiniGunner_1Off", "Nod_Turret_Destroyed",
    "POW_Data_Disc", "POW_Health_100", "POW_IonCannonBeacon_Player",
    "POW_Medal_Armor",
};
```

Notes:
- `Mission01.cpp` uses both `Nod_MiniGunner_0` and `Nod_Minigunner_0`; preset
  lookup is case-insensitive, so the table keeps one (17 unique entries).
- `Invisible_Object`, `Generic_Cinematic`, `Large_Blocker` are typically
  model-less/helper presets; warming them should be a cheap no-op, but verify
  they resolve via the definition manager before relying on them.
- Missing presets must be skipped with a log line, never fatal.
- Key the table by level name (`M13`, `M01`); other missions are unscanned.
