# M13 readiness (first campaign mission)

## Full audit (2026-10-07)

Evidence class: static source audit plus read-only retail metadata (the
unchanged Vita3K retail `Data/`, `M13.mix` SHA-256 `54d41ea0…bbfc4`). Also
deterministic staging and an `arm-vita-eabi-g++ -fsyntax-only` check of the
changed TU. No build, no link, no VPK, no Vita3K and no physical run. This
report does not claim that M13 completes, renders or sounds correct on any
target.

Tools: `tools.audit_mission_content_bindings --map M13.mix`,
`tools/renegade_cinematic_dependency_scan.py --mission-inventory`, the existing
`reports/generated/sweeps/live_script_parameters.json` M13 row, and
direct `MixArchive` lookups over `M13.mix`, `always.dat` and `Always2.dat`.
Receipts are under `build/m13-audit/` (private, not committed).

### 1. Script bindings and parameter counts

| Check | Result |
| --- | --- |
| Level and definition bindings | 100 level and 144 total bindings, 67 scripts discovered, **0 unknown**. |
| Owners | MissionX0, Test_DLS, Test_RAD, Test_DAY, Test_RMV_Toolkit, Toolkit, Toolkit_Objects, Toolkit_Powerup, Toolkit_Sounds and Mission03. Cinematic-attached scripts add Test_Cinematic and mission08 (`M08_Petra_C_Helo`). Every owner is a TU in the Vita compile database (`build/vita-fast-candidate`, 44 script TUs). |
| Parameter shape (sweep row for M13) | 55 equal, 89 excess, **0 fewer**. All 89 excess entries are an authored `"0"` placeholder on a script whose descriptor is empty (`M00_Disable_Transition`, `M00_Soldier_Powerup_Grant`, the `MX0_*` controllers, and others). `Set_Parameters_String` ignores the extra field, as it does on retail PC. |
| Controller objects | `MX0_MissionStart_DME` on 1200001, `MX0_A02_Controller` on 1100000, `MX0_A03_CONTROLLER_DAK` on 1400041, `MX0_Area4_Controller_DLS` on 1500017. All four are serialized in `m13.ldd`. |

### 2. Events, timers and object IDs

- Every `Start_Timer` id in the MX0 controllers is handled in the same
  script's `Timer_Expired`. Cinematic `Send_Custom` records and their
  receivers:
  - `X00_Intro.txt` sends 117, 99 and 100001 to 1200001.
  - `X0E_Obelisk.txt` sends 445018 (`MX0_DESTROY_OBELISK`) and 445007
    (`MX0_FIRE_SAM`) to 1500017.
  - `X0D_A10_Crash.txt` sends 445008 (`MX0_A10_STRIKE`) to 1500017.
  - `X0Z_Finale.txt` frame 440 sends 445009 (`MX0_MISSION_SUCCESS`) to
    1500017.
  All of these are handled.
- Literal `Find_Object` IDs that are not serialized in M13:
  - 1200017: `MX0_Engineer1` `KILL` attack target (`MissionX0.cpp:677`).
    `Set_Attack(NULL)` is accepted.
  - 100389: `M08_Petra_C_Helo::Killed`, attached by
    `MX0_A03_NOD_LedgeDrop.txt`. The event goes to NULL and
    `SCRIPT_PTR_CHECK` drops it.
  - 1400035: `DAK_MX0_Sec_3_Humvee`, which is not bound in M13.
  All three behave the same on retail PC.
- `M00_SEND_OBJECT_ID` slots that `MX0_Area4_Controller_DLS` reads but that
  no released script, cinematic or level record ever sends: 4
  (`medium_tank_escort_id`), 11 (`gdi_trooper1_id`), 19 and 20 (the
  `gdi_reinforcement*_id` pair). See the defect below.

### 3. Content references

- Cinematic control files: all 18 that M13 scripts name resolve. Sixteen are
  in `M13.mix`. `MX0_GDI_TroopDrop_Area4.txt` and `MX0_GDI_Reinforce_Area4.txt`
  are in `always.dat`.
- Literal script presets: 0 missing.
- Text and conversation candidates: 0 missing.
- Cinematic `Create_Real_Object` presets: all 27 resolve
  (`M13_MISSION_INVENTORY.md`).
- Twenty definition IDs are not in the database: weapon eject and muzzle-flash
  physics definitions (2166, 2575, 2576, 2648, 2753-2758, 2761, 2763,
  2765-2767, 2813) and three twiddler choices (2247, 2249, 2250, 3413). They
  are also missing on retail PC. They are data references, not completion
  blockers, and were not "fixed".

### 4. Crash-prone code on the M13 path

- MissionX0.cpp, the Test_RAD.cpp MX0_A02 scripts and the Test_DLS.cpp
  MX0 scripts dereference pointers **only through `Commands->`**. Every
  command used checks for NULL (`SCRIPT_PTR_CHECK`, `staging/combat/scriptcommands.cpp`).
- Array indexing is in range:
  - `Get_Random_Int(a,b)` returns values in `[a,b)`
    (`CRandom::Get_Int`, `crandom.h`). Conversation tables of size 4 and 6
    use `(0,4)` and `(0,6)`.
  - `MX0_A02_UNIT_ID[9]` is indexed with 1..8 and the `NOD_START` loops.
  - `attack_loc[4]` is indexed with 0..2.
  - `Wrong_Way_Conv_Table` wraps at 4.
  - No call has `min == max`, so there is no `% 0`.
- The script bodies have no `sprintf`, `strcpy` or local buffers.

### 5. Objective chain and handoff

`MX0_Area4_Zone_DLS` zones (1500001-1500006, `Area` 0-3) report the player's
area to 1500017. The controller runs: AREA4_ACTIVATED, then
HUMMVEE/MEDIUM_TANK, then OBELISK (`X0E_Obelisk.txt`), then SAMS (the SAMs are
also destroyed by timer after 20 s and 24 s), then A10_STRIKE
(`X0D_A10_Crash.txt`), then ION_CANNON_STRIKE (`Test_DLS.cpp:2414`), then
FINALE at 25 s (`:2452`, `X0Z_Finale.txt`). `X0Z_Finale.txt` frame 440 sends
445009, which reaches `Mission_Complete(true)` (`:2050`). That only latches
`PendingCampaignContinue` (`combatgmode.cpp:1720`). Then
`CampaignManager::Continue` advances `campaign.ini`:
`1=Level M13.mix` → `2=Score` → `3=Movie R_L01.bik` → `4=Level M01.mix`. The
only failure route is `Havoc_Script::Killed` → `Mission_Complete(false)`
(`MissionX0.cpp:466`).

### 6. Port patches touching M13 scripts

- `scripts-a37-mx0-default-arguments`: only explicit GCC default arguments.
- `scripts-a36-mx0-save-variable-ids`: `MX0_A03_FIRST_PLAYER_ZONE` ID 1 → 2.
- `scripts-a36-m13-finale-delivery-trace`: logs only, plus NULL guards around
  the ion-beacon spawn and the finale owner. 1500087 is serialized, so the
  original path is unchanged in practice.
- The cinematic dispatch and timing patches are covered in
  `M13_CINEMATIC_DISPATCH.md`.

No incorrect hunk was found.

### Defect found and fixed

- **Indeterminate object IDs in `MX0_Area4_Controller_DLS`** (Test_DLS.cpp
  `Created`, :1870). Severity: medium (behavioral, not a crash).
  - `Created` never initialized the 18 `*_id` members, and four of them are
    never assigned by released data.
  - They are read through `Find_Object` and `Attach_Script`: AREA4_ACTIVATED
    attaches `MX0_GDI_Soldier_DLS`/`MX0_Vehicle_DLS`, and `Relocate_Soldiers`
    sends `MX0_SOLDIER_MOVE`.
  - On the Vita heap, recycled memory can hold a live object's ID, so these
    calls could target an unrelated object.
  - Fix: `port/patches/scripts-a37-mx0-area4-controller-id-init.patch`
    initializes the IDs to 0 in `Created`.
  - Values that are sent later still overwrite 0.
  - Loaded saves restore the saved values; `Created` does not run on load.
  - The patch is anchored to Test_DLS.cpp SHA-256 `357ac12b…caab`.
  - Staging now has 526 ordered patches at fuzz 0, inventory `15b0502c…a787`.
  - Syntax check of the staged TU and 13 provider/M13 coverage tests pass.

### Deferred / residual (need runtime evidence)

- `MX0_A02_Controller::MX0_A02_UNIT_ID` is also not cleared in `Created`. All
  eight slots are assigned at startup when their units exist, so this was not
  changed.
- The ion-beacon, flash-to-white and finale timing, and Test_Cinematic
  reaching frame 440 of `X0Z_Finale.txt`, need a Vita3K/physical run. Look for
  the `M13 finale:` breadcrumbs in the runtime log.
- The Score → `R_L01.bik` → M01 handoff depends on the score-screen and movie
  frontend gates (`M13_VIDEO_COVERAGE_AUDIT.md`).

## Soft-lock hunt (2026-10-07)

Evidence class: static source review of staged `MissionX0.cpp`, `Test_RAD.cpp`
and `Test_DLS.cpp`, the engine paths they call, and read-only parsing of the
unchanged retail `M13.mix` (`m13.ldd`) and its cinematic text files. Also
deterministic staging and an `arm-vita-eabi-g++ -fsyntax-only` check of the
patched TU. No build, no emulator and no device run. Line numbers refer to
staged files.

Method notes:
- Key flags come from `ConversationClass` micro-chunk `VARID_ISKEY` (id 13).
  The same parser reproduces the 23 key conversations listed for M10.
- Zone bounds are the saved `ScriptZoneGameObj` OBBoxes.

### Key conversations (pattern a)

- Only `MX0_A03_01` through `MX0_A03_10` are key (10 of 564 level
  conversations). Every A01, A02 and A04 line whose end callback advances the
  mission is non-key.
- No key line can be playing when one of those non-key lines starts:
  - A03 key lines start only after `ENTERED_TANK`. `START_ZONE` follows at
    +2 s, the humvee drop at frame 148, then `MX0_A03_01`.
  - The other A03 key lines need zones beyond the A02 rubble.
  - `MX0_A03_HAVOC_TANK` is never attached, so it cannot send an early
    `START_ZONE`.
- A non-key line that is still running when a key line starts is stopped by
  `ConversationMgrClass::Think` after its monitor is registered. The callback
  is delivered, and `MX0_A02_ACTOR::Action_Complete` accepts ENDED,
  INTERRUPTED and UNABLE_TO_INIT.
- `MX0_GDI_ORCA` acts only on ENDED. Its `MX0_A03_02` line is key, has only
  NULL orators, and can only be ended by a newer key line, which uses the
  default reason ENDED. A03 also completes through end zone 1400069.
- Result: no reachable case of pattern (a).

### Fixed: A02 fire-in-the-hole lost to an engineer registration race

`scripts-a38-m13-firehole-engineer-register.patch` (Test_RAD.cpp :821).
Reachability: timing-dependent, low probability. Severity: hard soft-lock.

How the race happens:
- The A02 rubble (`Simple_Level_x0_A02_Blockage`) is removed only by
  `EXPLODE` (:2162). `EXPLODE` is sent when engineer 2's
  `MX0_ENGINEER2_123` line ends.
- That line starts only from `ENTERED_TANK` (:834). The handler sends
  `SAY_FIREHOLE` to `engineer_02_id`.
- `X0I_GDI_Drop02_Engineer.txt` creates engineer 1 at frame 401 and
  engineer 2 at frame 581. Engineer 2 registers 4 s later (:2580), about
  23.4 s after the drop starts.
- The replacement tank appears at about 22.4 s plus engineer 1's travel to
  `MX0_A02_MOVE_OBJ_06` (:2552). `ENGINEER_01_MEDTANK` (:2326) proceeds on
  any completion reason, including an immediate path failure.
- If that travel takes under about 1 s and Havoc enters the tank at once,
  `ENTERED_TANK` finds engineer 0 and the cue is dropped.
  `MX0_A02_GDI_MEDTANK.entered` (:2945) latches, so re-entering cannot
  recover it, and the path to A03 stays blocked.

The fix:
- When `ENGINEER_02_REGISTER` arrives after `ENTERED_TANK` while the engineer
  was still unregistered, it sends the missed `SAY_FIREHOLE` once, after
  1.0 s. The delay matches the normal order, in which the engineer's rubble
  goto has already started.
- Both inputs are already saved (`engineer_02_id` id 19, `entered_tank`
  id 22). The delayed custom is a saved object timer.
- On the normal path `entered_tank` is still false at registration, so
  nothing changes.
- Anchor: Test_RAD.cpp SHA-256 `5699f1fc…753a` (pristine; no earlier patch).
  Staging: 544 ordered patches, PASS, inventory `b351588e…37c8`.
- The staged TU passes `-fsyntax-only` with 0 errors.

### Races and one-shot triggers (b, d)

- **Unreachable:** STARTUP zone 1100022 arriving before `MAIN_STARTUP`.
  - The intro sends 99 at frame 1998. The `SNIPER_CREATE` (1 s) and
    `SNIPER_EXCHANGE` (2 s) timers then send `MAIN_STARTUP` at about frame
    2088.
  - The camera returns at frame 2130, and the zone is about 45 m from the
    start.
  - Zero-delay customs are synchronous (`Send_Custom_Event`), so the ID
    replies that `MX0_GDI_ORCA` and `MX0_A03_END_ZONE` request are set
    before use.
- **Not a blocker:** an early STARTUP from a non-star enterer. The zone has no
  `Is_A_Star` check, but the GDI greeting waits on a 50 m distance check and
  walks to Havoc, so the chain still completes.
- **Deferred, geometry-dependent:** `MX0_Area4_Zone_DLS` (Test_DLS.cpp:2482)
  fires once per zone.
  - The zones are thin plane pairs:
    - 1500006 (area 0) and 1500001 (area 1), about x 38-41.
    - 1500003 (area 1) and 1500002 (area 2), about x 83-86.
    - 1500004 (area 2) and 1500005 (area 3), about x 97-100.
  - A forward pass fires them in the order 0, 1, 1, 2, 2, 3 and ends at
    3.
  - The area-3 pair's north end meets the area-2 pair's plane, and the
    area-2 pair extends about 17 m beyond that point. A player who reaches
    area-3 ground without crossing the area-3 pair, then crosses it backward
    (1500005, then 1500004), ends at `star_area` 2.
  - In that case the A04 timers loop in `case 2` forever. Every zone is
    spent and only the area-3 zone could restore progress.
  - Candidate fix: let the Area 3 zone re-report on re-entry. It is a no-op
    on the normal path.
  - Not applied: whether the terrain is walkable there needs runtime
    evidence.
  - Telemetry signature: `MEDIUM_TANK`, `OBELISK`, `SAMS` or `A10` timers
    re-arming every 5 s with no `X0E_Obelisk.txt` start.

### Counters and required units (c, e)

- **A03:** buggie and harvester deaths are an early exit only. End zone
  1400069 has no star or state gate.
- **A02 Nod spawning:** it re-polls itself through `PREVENT_SPAWNS` (3 s)
  after the first Nod kill.
- **A02 helicopters:** `X0I_Drop02_A02_E02.txt` attaches a second
  `MX0_A02_HELICOPTER "1"` to the real helicopter. Its 23 s self-kill always
  sends `HELI_DESTROYED_02`.
- **A04 SAMs:** they receive `M00_ENABLE_DAMAGE_MOD 0` before the 20 s and
  24 s `DESTROY_SAM` timers. Neither the 0.10 modifier nor the retail
  `Killable_ByNotStar` name mismatch (which reads 0) can keep them alive.
- **Required units:** the A02 GDI actors and both engineers cannot die while
  `active_actor` is set. `Damaged` restores health before
  `DamageableGameObj::Apply_Damage` checks for death, and `MAIN_ENDING` is
  never sent. The replacement tank restores full health. Trooper One and
  the reinforcement counter are not on the completion chain.

### Save/load and death (f)

- The chain state is registered in `MX0_A02_Controller`, `MX0_A02_ACTOR`,
  `MX0_A02_GDI_MEDTANK`, `MX0_A03_CONTROLLER_DAK`,
  `MX0_Area4_Controller_DLS` and the zone `first_time` flags.
- Unsaved members are not on the chain:
  - `Trooper_One_Id` in `MX0_GDI_ORCA` and `MX0_A03_END_ZONE` is
    re-requested synchronously before use.
  - `MX0_A02_GDI_APC::can_damage` is used only within the same call.
- With the value-initializing factory, a load restores defined values.
- Havoc's death goes through `Havoc_Script` to `Mission_Complete(false)`. A
  restart reloads the level and runs fresh `Created` handlers.
