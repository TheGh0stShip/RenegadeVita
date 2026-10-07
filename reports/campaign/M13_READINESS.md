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
