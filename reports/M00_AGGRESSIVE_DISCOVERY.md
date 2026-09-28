# Tutorial aggressive source discovery — 2026-09-27

One newly confirmed missing original unit: **Scripts/Test_DAK.cpp**, absent
from both current Vita and host source lists. No source integration, C++ build,
game execution, installation, device action or retail mutation in this sweep.

## Confirmed omissions

`M00_BUILDING_EXPLODE_NO_DAMAGE_DAK` (Test_DAK.cpp:189) is saved on four
tutorial buildings and attached by their definitions:

| Object | Definition | Building | Script-header offset in m00_tutorial.ldd |
| --- | --- | --- | --- |
| 450936 | 491530022 | Weapons factory | 96700 |
| 450937 | 491530023 | Power plant | 96561 |
| 450938 | 491530024 | Infantry barracks | 96422 |
| 450935 | 491530025 | Tiberium refinery | 96839 |

The original Killed callback shakes the camera (radius 25, intensity 0.1,
duration 4). Its Create_Explosion call is commented out. Do not describe this
omission as missing explosion damage or a missing tutorial segment.

The unchanged Dev207 ARM ELF lacks three required script factory methods:

- M00_BUILDING_EXPLODE_NO_DAMAGE_DAK: newly missing Test_DAK.cpp.
- M00_Disable_Transition: Toolkit_Objects.cpp, already source-selected during
  the M13 correction, not rebuilt. Nod_Buggy (1315) and Nod_Light_Tank
  (82080027), created by the tutorial range controller, attach this script.
  Created disables vehicle entry/exit transitions.
- M00_Disable_Physical_Collision_JDG: Toolkit.cpp, also already source-selected
  but not rebuilt. The GDI transport flyover preset attaches this script.

## Scope and indirect-call review

- Retail archive: M00_Tutorial.mix. Seed family: MTU_, explicitly excluding
  unrelated MX0_ campaign and MSK_ skirmish roots.
- 74 persisted game objects, nine spawners, 128 physics records (35 dynamic,
  93 static), 60 saved script bindings and seven distinct saved script names.
- **301 typed/reviewed preset dependencies and 27 required scripts**.
- **53 reached persistence-factory types**: all original owners appear in
  the existing native compile graph and all have defined Load methods in ELF.
- **97 referenced ScriptCommands callbacks**, all source-bound to functions.
- Conservative discovery: **567 possible presets, 30 script names**. This
  includes false-positive lookup keys, not 567 proven tutorial dependencies.

Mission00.cpp:278–311 selects GDI_Orca or GDI_Transport_Helicopter into a
variable and creates the flyover. Both were manually verified and added as
reviewed roots. The instructor at line 2632 attaches Test_Cinematic with
X0I_Drop02.txt; this file resolves in always.dat, not the tutorial MIX.
Its real-object commands create Nod_Transport_Helicopter and Nod_Minigunner_0
and attach MTU_Nod_Soldier. The extra transport root is included. Raw cinematic
Create_Object names refer to render models, not game-object presets.

The conservative extra Mission11.cpp lead comes from a soldier lookup key in
Soldier_Powerup_Table, not demonstrated tutorial spawning. Extra mutant-radar
and stationary-soldier sound scripts likewise arise from shared-table keys.
Do not count these as confirmed tutorial omissions. Three unmapped envelope
factory IDs are LevelEdit tile/VIS-point/dummy definitions (0x50001/16/19),
not demonstrated missing runtime owners. All mapped envelope owners are in
the existing native compile graph.

## Reproduction

```sh
python3 tools/audit_m13_level_owners.py \
  --archive build/host-m13-diagnostic/retail/Data/M00_Tutorial.mix \
  --definitions build/host-m13-diagnostic/retail/Data/always.dbs \
  --native-build build/vita-fast-candidate --script-prefix mtu_ \
  --preset-root GDI_Orca --preset-root GDI_Transport_Helicopter \
  --preset-root Nod_Transport_Helicopter \
  --output build/dev208-m00-aggressive-typed.json
python3 -m tools.discover_m13_indirect_owners \
  --typed-receipt build/dev208-m00-aggressive-typed.json \
  --data build/host-m13-diagnostic/retail/Data \
  --output build/dev208-m00-aggressive-discovery.json
python3 -m unittest tools.test_m13_level_owners tools.test_m13_script_coverage tools.test_m13_mission_inventory tools.test_script_provider_contract
```

25 Python tests pass, including tutorial/campaign/skirmish root isolation.
Shared audit now accepts explicit script-prefix and reviewed preset roots,
handles absent cinematic preset entries, and records archive identity so the
discovery pass cannot silently scan M13 instead of the tutorial.

Tutorial archive SHA-256:
`84f14f6267dd8a88563b3d31540bf857df0b8e111144944cb582edd246f2d438`.
Objects.DDB SHA-256:
`98253406ee8e99f86db6593e360bf68424ffb432580354038f08838ee5ec94cb`.
Existing Dev207 ELF SHA-256:
`187cfec06117cd0549a8fbb3df387bc5f90908bbb25fe650b84bb6630f95db9d`.

All placed definition IDs resolve; eleven indirectly referenced IDs do not.
Those remain data-reference questions. Conversation binary semantics,
all possible computed/parameter-driven names, runtime branch execution and
registration are not exhaustively verified. Source/symbol presence does not
prove tutorial behavior or physical acceptance. Next: integrate Test_DAK,
retain the two previously selected owners, and gate tutorial registration on
this expanded inventory before runtime verification when builds are allowed.
