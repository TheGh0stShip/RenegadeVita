# Campaign script save-state gaps (2026-10-07)

Scope: `staging/scripts/` Mission01-07, mission08, Mission09-11, MissionX0, Test_DLS.
Tool: `python3 tools/audit_script_save_state_gaps.py [--json out.json] [--top N]`
(heuristic static pass; host-only; no build). The top items below were checked by hand.

## How script save works (verified, same as the PC game)

- Only variables registered through `REGISTER_VARIABLES()` / `SAVE_VARIABLE(x,id)` are
  written. `ScriptImpClass::Save/Load` (`staging/scripts/scripts.cpp:594-660`) match
  upstream `Code/Scripts/scripts.cpp`. The only changes in staging are the
  `delete[] mArgV` and Vector3 parameter-init patches. The
  `Save_Data/Load_Data` call is commented out in the original. None of the files
  in scope use `SAVE_DATA`.
- `Auto_Save_Variable` (`scripts.cpp:673`) silently rejects (DebugPrint only) any
  **duplicate id**, id outside 0..255, or size >250 bytes. The variable is then
  never saved.
- On a savegame load, `Created()` is **not** re-run.
  `ScriptableGameObj::On_Post_Load` only sets `ObserverCreatedPending` on
  `Is_First_Load()` (`staging/combat/scriptablegameobj.cpp:636`). Scripts are
  built with `new T` (`ScriptRegistrant.h:52`), and most have no constructor,
  so an unregistered POD member is **indeterminate heap content** after a load,
  on PC and on Vita.

## Totals (tool output)

| File | DECLARE_SCRIPT | with REGISTER | gap classes | gap vars | dupe-id drops |
|---|---|---|---|---|---|
| Mission01 | 289 | 112 | 5 | 5 | 2 |
| Mission02 | 26 | 10 | 3 | 3 | 0 |
| Mission03 | 86 | 50 | 1 | 1 | 1 |
| Mission04 | 138 | 56 | 2 | 3 | 1 |
| Mission05 | 111 | 83 | 8 | 10 | 2 |
| Mission06 | 85 | 60 | 9 | 17 | 0 |
| Mission07 | 122 | 67 | 10 | 10 | 0 |
| mission08 | 114 | 69 | 9 | 15 | 0 |
| Mission09 | 96 | 50 | 5 | 5 | 0 |
| Mission10 | 79 | 36 | 6 | 8 | 0 |
| Mission11 | 171 | 84 | 1 | 1 | 1 |
| MissionX0 | 31 | 24 | 3 | 3 | 1 |
| Test_DLS | 58 | 21 | 4 | 6 | 0 |

Coverage is high overall. Mission11 and Mission03 register nearly all of their
state. Most gaps are AI patrol and ambient state, not objective state.

## Classification

**Vita-only issues found: none in these files.**
- **Registered raw pointers:** 0. Every registered variable is an `int`, `float`,
  `bool`, `Vector3`, or an array of these. Each has the same size and layout
  under MSVC x86 and GCC ARM-EABI, so the save format has no
  pointer-width or ABI hazard on Vita. A host x86_64 ABI test would only be
  affected if a pointer were registered, and none is.
- No Vita patch touches the save path or a registered member in these files.
  The patched mission files are M01 (Duncan logging only), M03 (host-only
  pointer exchange), M08/M09/M10 (bounds) and MX0 (default arguments).
- The precedent fix for a related Vita-side gap is
  `port/patches/scripts-a35-cinematic-camera-save.patch` (Test_Cinematic,
  outside this scope).

Every item below is an **original-game bug (document only)**. Where noted, the
Vita *consequence* can differ. Vita heap and garbage contents differ from the
MSVC CRT, so an indeterminate value can take a different branch. A stale or
garbage pointer usually data-aborts on Vita, where PC often continued silently.

## Top risks by mission (file:line)

Ranking: **H** = objective or mission-fail outcome. **M** = one-shot event replay or
skip, or a garbage value fed to the engine. **L** = cosmetic or AI only.

### M02
- **M** `Mission02.cpp:50` `M02_Objective_Controller::rocket_soldier_speech` is
  set at `:166` and not registered. After a load the one-shot
  `M02_MORE_ROCKET_SOLDIERS` conversation can replay or be skipped. This is
  dialogue only and does not change objective state.
- **L** `Mission02.cpp:3886` `M02_Obelisk::info_given` and `:3962`
  `M02_Power_Plant::info_given`: the classes have no REGISTER block, so the
  damage-hint text can repeat or be lost.

### M03
- **M** `Mission03.cpp:3196` `M03_Chinook_Drop_Soldiers_GDI::count2`. **Dupe id 2**
  (`:3202`, it collides with `count`), so it is never saved. After a load
  `sprintf("%d", count2)` at `:3240` passes a garbage `Number` to
  `M03_Beach_Soldier_GDI`. Check that consumer for unchecked indexing.

### M04
- **L** `Mission04.cpp:8989` `M04_Firefight_Prisoner::warningPlayed`: **dupe id 3**
  (`:8996`). The warning line can repeat.
- **L** `Mission04.cpp:10199-10200` `M04_BigSam_Script_JDG::civWarning`,
  `missileStuckSound`: no REGISTER block, so the sound and conversation can repeat.

### M05
- **H (narrow window)** `Mission05.cpp:6750` `M05_Dead6_Help::mission_failed_text`
  is set in `Entered` at `:6824/6835/6846` and consumed in `Action_Complete` at
  `:6876`. That path sends custom `503,2` to objective controller 100001.
  A save between zone entry and conversation end leaves a garbage value, so the
  objective-fail HUD text and the `503` failure report can be dropped.
- **M** `Mission05.cpp:5420` `M05_Inn_Tank::attacking`: **dupe id 2** (`:5429`)
  causes AI state drift.
- **L** `Mission05.cpp:2877-2879` `M05_Park_Controller::artillery_loc1..3`: explosion
  and sound positions are garbage until the next timer refresh at `:2993`.
- **L** `Mission05.cpp:7390` `M05_Cathedral_Artillery`: `fire_loc[0]` and
  `fire_loc[1]` are both registered with id 1. The second registration is
  dropped (`:7393`) and only element 0 is saved.

### M06
- **M** `Mission06.cpp:1501` `M06_Alarm_Behavior::alarm_switch_id` is set in
  `Custom` at `:1639`. After a load the alarm engineer can target a garbage
  object id (Find_Object returns NULL, so it fails safe).
- **L** `Mission06.cpp:3168` `M06_Alarm_Engineer::broken_alarm_id` is
  set by `Sound_Heard` (`:3230`).
- **L** `Mission06.cpp:1893`, `:1999`, `:2104` patrol `waypath_id` values are
  created-only, so patrols can stall after a load. `M06_Lab_Patrol`,
  `M06_Flyover` and `M06_Clear_For_Mendoza` have no REGISTER block.

### M07
- **L** The `apc_id` members are set only in `Created` and read in `Killed`, at
  `Mission07.cpp:1841`, `:1874`, `:4017`, `:4172`, `:4205` and `:4723`.
  On death the APC gets no notification. Eight classes have no REGISTER block,
  including `M07_Encounter_Unit`, which loses all four of its members.

### M08 (`mission08.cpp`)
- **L** `:4642` `M08_Patrol_Inactive::waypath_id` and `:4963`
  `M08_Facility_Scientist_Inactive::point1_id` are activated in `Custom`. A unit
  activated before a save can stall after the load.
- (False positive) `:4966` `controller_id` is shadowed by locals from
  `Get_Int_Parameter`.
- **L** The created-only `waypath_id` and `apc_id` members at `:626`, `:1339` and
  `:1980` behave like the M06 and M07 ones above.

### M09
- **H (fail path only)** `Mission09.cpp:50` `M09_Objective_Controller::objective[3]`
  is set at `:246/252/258` and not registered. Mobius death (`:974-993`)
  queries it to decide which objective to mark failed. After a load the
  garbage byte is sent as `param`, so the wrong objective pog may be failed.
  The mission still ends through `Mission_Complete(false)`.
- **M (Vita crash-amplified)** `Mission09.cpp:4342` `M09_KeyCard_Zone::mobius`
  (`GameObject *`) is not registered and is set in `Created`, `Entered` and
  `Action_Complete`. `Custom` uses it without refreshing it (`Join_Conversation`
  at roughly `:4424-4450`). If `Custom` arrives after a load and before
  `Entered` or `Action_Complete`, an indeterminate pointer is dereferenced.
  A safe fix is to re-run `Find_Object(2000010)` in `Custom`.
- **L** `:3228` `M09_Invincible_MrShuman::invincible`: no REGISTER block. After a
  load Shuman can lose (or gain) invincibility.

### M10
- **H** `Mission10.cpp:2647` `M10_Gate_Check::first`, `second` are not registered;
  only `already_poked` is. They are set in `Action_Complete` at `:2667/2673`.
  They gate which of objective events 1005/1006/1007 reach controller 1100154
  (`:2706-2745`). After a load, garbage flags can route the 1006 completion
  through conversation `M10CON017` instead of sending it directly, or can skip
  the 1007 send.
- **L** `:4399` `M10_SoldierPoke::count` and `:1045` `M10_Obelisk::curr_health`.

### M11
- **L** `Mission11.cpp:7529` `M11_Petrova_Taunt_Controller_JDG::last`: **dupe id 2**
  (`:7535`). The taunt rotation can repeat.

### M01
- **L** `Mission01.cpp:19264` `M01_MediumTank_ReminderZone_JDG::reminderConv` is a
  conversation id that is lost on load.
- **L** `:6985` `M01_TailgunRun_NOD_Commander_JDG::playerSeen` (**dupe id 2**, `:6991`)
  and `:12094` `M01_Church_Priest_JDG::prayerSound` (**dupe id 1**, `:12099`).

### MX0 (tutorial)
- **M** `MissionX0.cpp:2547` `MX0_A03_FIRST_PLAYER_ZONE::first_time`: **dupe id 1**
  (`:2552`, it collides with `Trooper_One_Id`). After a load the Nod ledge-drop
  cinematic (`:2578-2580`) can fire a second time or not at all.
- **L** `:1412` `MX0_GDI_ORCA::Trooper_One_Id` and `:2627`
  `MX0_A03_END_ZONE::Trooper_One_Id` are ids received over `Custom`, with no
  REGISTER block. `Find_Object` on a garbage id returns NULL.

### Test_DLS (M13 support)
- **L** `Test_DLS.cpp:488` `DLS_Filing_Cabinet::destroyed_state`, `:807`
  `DLS_Test_Pickup::already_entered` and `:182` `DLS_Camera_Test::seen_cnt`.
  None of these are on the finale objective path.

## Recommendation

1. Fix nothing in upstream semantics without a save/load repro. These are PC-original.
   Physical gating is unchanged, and campaign saving is not yet a Vita acceptance gate.
2. If the port adopts save-safety fixes later, the minimal candidates are:
   - re-fetch `mobius` in `M09_KeyCard_Zone::Custom`, which is the only
     pointer dereference hazard;
   - register `M10_Gate_Check::first`/`second` and
     `M05_Dead6_Help::mission_failed_text`;
   - give the dupe ids unique values, which is backward-compatible because
     loaders ignore unknown ids.

   Ship each as a separate `port/patches/scripts-*` patch.

   **Adopted (2026-10-07):** the first two candidates are now staged as
   `scripts-a36-m09-keycard-mobius-refetch.patch`,
   `scripts-a36-m10-gate-check-save-flags.patch` (ids 2/3) and
   `scripts-a36-m05-dead6-help-failed-text-save.patch` (id 4, zeroed in
   `Created`). They are host syntax-checked only and have no save/load
   repro or Vita evidence yet. The dupe-id fixes are not adopted.
3. Heuristic limits: method-local shadowing (M08 `controller_id`) and
   objective links made through custom events are not fully resolved. Treat
   tool scores as triage only.
