# Script-spawned presets outside the cinematic warm set (M01..M13)

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
| M02 (`Mission02.cpp`) | 21 | 11 | 8 |
| M03 (`Mission03.cpp`) | 2 | 32 | 32 |
| M04 (`Mission04.cpp`) | 4 | 28 | 28 |
| M05 (`Mission05.cpp`) | 7 | 10 | 10 |
| M06 (`Mission06.cpp`) | 7 | 15 | 15 |
| M07 (`Mission07.cpp`) | 0 | 7 | 7 |
| M08 (`mission08.cpp`) | 9 | 11 | 9 |
| M09 (`Mission09.cpp`) | 2 | 6 | 6 |
| M10 (`Mission10.cpp`) | 0 | 12 | 12 |
| M11 (`Mission11.cpp`) | 3 | 17 | 17 |

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
- Tables are keyed by archive (`M01.mix`..`M11.mix`, `M13.mix`); M12 has no script unit in staging.
- M02..M11 tables are `kM02ScriptSpawnPresets`..`kM11ScriptSpawnPresets` in `port/platform/vita/a31_vita_runtime.cpp` (generated from the scan).
