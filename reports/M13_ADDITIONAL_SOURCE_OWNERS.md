# Additional original M13 source omissions

2026-09-27, read-only retail/source/existing-ELF audit. No compilation,
game execution, package, installation, or retail mutation.

## Confirmed additional files

These are **three additional missing owners**, beyond the five files already
source-selected in `M13_VIDEO_COVERAGE_AUDIT.md`. They remain absent from both
current host and Vita source lists. This work identifies the omissions; it
does not claim their integration or restored gameplay.

| Original file | Direct M13 evidence | Required behavior |
| --- | --- | --- |
| `Code/Scripts/Mission03.cpp` | `M03_SAM_Site_Logic` is saved on M13 objects **1500015 and 1500016**, preset 82080057. Script-header offsets in M13.ldd: **110511, 110837**. | Enemy detection, aerial-target attack/reset timers, ignore-target events, destroyed-SAM creation and its follow-up sound. `Killed()` attaches `M03_Destroyed_SAM_Site` from the same file and `M01_Destroyed_SAMSITE_JDG` from already selected Mission01. |
| `Code/Scripts/Test_RMV_Toolkit.cpp` | `M00_Play_Sound` is saved on **six** emitters: 100044, 100037, 100034, 100012, 100016, 100017. Offsets **114681, 114773, 114865, 114957, 115046, 115135**. | Authored 2D/3D environmental sounds, randomized offsets/delays, sound monitoring and repeat scheduling after completion. |
| `Code/Scripts/Toolkit_Sounds.cpp` | `M00_BuildingStateSoundSpeaker` is saved on **four** speakers: 1700007, 1700009, 1700011, 1700013. Offsets **115224, 115339, 115454, 115569**. | Normal/destroyed building sounds and explosion-sound events. It dynamically attaches `M00_BuildingStateSoundController`, also in this missing file, to receive building death/state changes. |

These five script factories are missing from the existing Dev207 ARM ELF.
The references are decoded from bounded ScriptManager records, then matched
to original registrations. Serialized owner-pointer tokens are mapped back
to their original persisted objects and instance IDs; they are never treated
as actual host addresses. No conclusions depend on a filename substring scan.

## Audit breadth

`tools/audit_m13_level_owners.py` now reads original little-endian 32-bit
chunks and bounded microchunks from unchanged M13 LDD/LSD and Objects.DDB.
It records:

- 159 placed game objects and 12 spawners.
- 94 saved active-script records plus six spawner-script bindings: 100
  bindings, 34 distinct names across them.
- All 15 cinematic text script names from the prior archive scan.
- 301 reachable definitions from the 15,146-definition database, following
  placed IDs, literal script/cinematic object creation, preset scripts,
  Spawner/Twiddler alternatives, and named Physical/Armed/Weapon/Ammo/Explosion
  links. Every placed/spawner definition resolves.
- A conservative **75-script closure**, up from the earlier text/source-only
  62. The existing ARM ELF lacks **25** of these factories. Ten are newly
  exposed requirements: five belong to the three additional missing files;
  five belong to files source-selected in the earlier correction but absent
  from the unchanged ELF.
- **41 reached persistence-factory types**: all owners appear in the existing
  native target's compile graph and all have defined `Load` methods in its
  ELF. No additional non-script `.cpp` omission was found within this scope.

The earlier 62-script gate remains a bounded source/text gate. Its passing
source-selection result must not be treated as complete M13 closure now that
these additional level/preset roots are known. Before another candidate,
integrate these three original owners and extend that required-root gate to
the expanded level/preset inventory.

## Evidence and limits

Receipt: `build/dev208-m13-level-owner-audit.json`; concise output:
`build/dev208-m13-level-owner-audit-summary.json`.

M13.mix SHA-256:
`54d41ea011bf7c4d273064422de961af76ccc38f32dd9b5368ebfbca365bbfc4`.
Objects.DDB payload SHA-256:
`98253406ee8e99f86db6593e360bf68424ffb432580354038f08838ee5ec94cb`.
Existing Dev207 ELF SHA-256:
`187cfec06117cd0549a8fbb3df387bc5f90908bbb25fe650b84bb6630f95db9d`.
Only metadata is retained in the receipt; no retail payload is exported.

Reproduce without building or launching:

```sh
python3 tools/audit_m13_level_owners.py \
  --archive build/host-m13-diagnostic/retail/Data/M13.mix \
  --definitions build/host-m13-diagnostic/retail/Data/always.dbs \
  --native-build build/vita-fast-candidate \
  --output build/dev208-m13-level-owner-audit.json
python3 -m unittest tools.test_m13_level_owners tools.test_m13_script_coverage tools.test_m13_mission_inventory
```

Eight new asset-free Python parser tests cover fixed widths, nesting and
truncation, repeated fields, pointer-token attribution, spawner scripts,
Twiddler alternatives and local-chunk-ID collisions. Combined audit tests:
17 pass. These tests do not compile or execute game C++.

The conversation subsystem is explicitly skipped rather than misparsing its
raw category prefix as a chunk. Not every definition link, computed preset
name, script parameter containing another script name, physics-only placed
definition or dynamic attachment is traversed. Fifteen referenced IDs from
weapon/Twiddler records do not resolve in this Objects.DDB and are retained
as data-reference questions, not evidence of missing `.cpp` files.
Symbol presence does not prove runtime registration or behavior. The no-build/
no-launch restriction remains active, and no native acceptance gate is closed.
