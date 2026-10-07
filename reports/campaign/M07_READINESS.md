# M07 campaign readiness (source and retail-metadata review)

Evidence class: source inspection and a read-only host audit of user-owned
retail metadata. No build, emulator or physical Vita run. Nothing here proves
that M07 completes on Vita.

## Result

No M07-specific port defect was found. No source or patch change was made. The
success chain is complete in source, and every object it uses is present in the
retail `m07.ldd` with the expected script attached. All 567 M07 script bindings
resolve through the static registry. The two lookup leads below behave the same
way on retail PC and fail without crashing.

## Success chain (`staging/scripts/Mission07.cpp`)

1. The level start script `M07_Havoc_DLS` (`:332`) is the `combat_start_script`
   binding in `m07.ldd`. It gives the starting weapons and calls
   `Mission_Complete(false)` if Havoc dies (`:399`).
2. Placed object 100657 has `M07_Objective_Controller` (`:44`) attached.
   `Created` adds objective 709, then starts timers for the `M07_CON001`
   conversation (`:286`). When conversation 300701 ends (`:308`), it adds 701,
   starts the nuke countdown on 100663 and sends the Dead6 team to assembly.
3. Placed object 100663 has `M07_Cathedral_Controller` (`:1391`) attached. Its
   countdown runs about 2 minutes (`M07_CON003`–`M07_CON012`) and attaches
   `Test_Cinematic` `XG_NukeStrike.txt` (`:1479`). At impact it sends a logical
   sound, `M07_NUKE_IMPACT` (`:1529`). Havoc dies if he is still marked
   `nuke_blast` (`:364`). That flag is cleared by the in/out blast zones
   `M07_In_Nuke_Blast`/`M07_Out_Nuke_Blast` (`:1555`+). `ESCAPED` sends
   710/param 1 (`:1545-1549`).
4. Objective 703 is added (param 3) after conversation 300703 (`M07_CON017`)
   ends (`:5986-5989`). The trigger is the fifth Dead6 evacuation climb.
5. **Completion.** Placed objects 100796 and 100798 both have `M07_Park_SSM`
   (`:3354`, definition 82080098). Each one's `Killed` sends
   `M07_ARTILLERY_KILLED` to 100799 (`:3404`). Object 100799 has
   `M07_Park_Controller` (`:3322`). After the second kill it sends 703/param 1
   to 100657 with a 5 s delay (`:3346`). That delay goes through
   `Start_Custom_Timer` (`staging/combat/scriptcommands.cpp:671`). The
   controller's `Custom` handler then calls `Mission_Complete(true)` (`:237-239`).
   This does not depend on objective 703 having been added first.
6. These failure routes call `Mission_Complete(false)`: param 2 for 701, 702,
   709 or 710 (`:253-267`), and Havoc being killed.

## Data / registry checks

All of the following were run read-only against the user's retail data. The
receipt was written to the git-ignored `build/m07/` and is not committed.

- **Script bindings.** 567/567 bindings resolve:
  - 438 persisted
  - 83 spawner
  - 45 definition
  - 1 combat-start

  This matches the M07 row of `reports/generated/sweeps/live_script_bindings.json`.
- **Discovered closure.** 124 scripts, with no unknown shipped scripts and no
  binding decode findings.
- **Cinematic text files.** M07's cinematic text files (13 files) live in
  `always.dat`, not `M07.mix`. All 13 are present. In
  `host_retail_cinematic_parser.json` each one has `records_match: true`.
- **Scripts attached from those text files.** Eight scripts are attached from
  them, and all 8 are registered: `M07_Para_Drop_Unit`, `M07_Player_Vehicle`,
  `M07_V01_Unit`, `M07_V05_Unit`, `M07_Triangle_Unit`,
  `M07_Deadeye_Nod_Chinook`, `M08_Mobile_Vehicle` and
  `M00_No_Falling_Damage_DME`. The names that text `Create_Object` uses are
  W3D model names, not presets.
- **Literal `Find_Object` IDs.** Every literal ID in `Mission07.cpp` matches a
  serialized object except 100952. This includes the chain IDs 100657, 100663,
  100665, 100666, 100796, 100798, 100799 and 119890–119893.
- **Unresolved definition IDs.** 22 typed sub-definition IDs did not resolve.
  They are weapon eject/muzzle-flash physics defs and Small Explosion Sounds
  Twiddler choices. They are global `objects.ddb` gaps, not M07 owners, and
  they do not affect progression.

## Leads (not blockers, retail-identical)

- `M07_Activate_V01` (`:4255`) sends to 100952, which is not in M07's
  serialized IDs (100952 is an M04 spawner ID). `SCRIPT_PTR_CHECK(to)` returns
  early (`scriptcommands.cpp:657`). The optional V01 encounter will not start
  from that zone. 100953 (`:4380`) is the follow-on.
- `Create_Object("Ramjet_Weapon_Powerup")` (`:5024`): no preset has that name.
  The call returns NULL and the result is not used, so no powerup drops.

## Risks

- **Nuke-escape timing.** The player has about 2 minutes from the end of
  `M07_CON001`. Frame pacing, conversation timing and blast-zone `Entered`
  delivery are physical gates. If the player is still flagged in the blast at
  impact, the mission fails.
- **Objective 709/701 failure routes.** These depend on Dead6/Sydney AI pathing
  and survival. Any AI/pathfind regression turns into a mission failure, not a
  stall.
- **SSM targets.** The completion targets 100796 and 100798 must be damageable
  and killable. Their logical sounds `M07_SSM_DAMAGED`/`FIXED` drive the
  engineer repair AI, which can make the kills take longer.
- **Vehicle sections.** The player-vehicle drop (`M07_Activate_Present`
  `:2929`, `M07_Player_Vehicle` `:2968`, `M07_Vehicle_Drop_Controller` `:3008`)
  depends on Vita vehicle entry/exit and the drop cinematic. It is optional for
  completion, but it is the normal route to the park.
- The authored parameter surface has 331 excess-value bindings. These are
  common across maps and follow the original parser behavior.
- The general mission-complete handoff, autosave and save stall remain as in
  `reports/SINGLE_PLAYER_COMPLETION_WIRING.md`.

## Physical test route

1. Start M07 from campaign or the development launcher.
2. Confirm the `M07_CON001` audio/subtitles play and that objectives 709, 701
   and 710 appear.
3. Leave the blast radius before impact. Confirm the nuke cinematic, the
   ash/wind and that Havoc survives. Objective 710 should be accomplished.
4. Continue through the SAM and inn-evac sections until `M07_CON017` adds 703.
5. Optionally collect the vehicle drop at the `M07_Activate_Present` zone.
6. Destroy both park SSM launchers (100796 and 100798).
7. Expect `Mission_Complete(true)` about 5 s after the second kill, followed by
   the score screen and the M08 handoff.
8. Capture the runtime log for "native provider missing script" (expect none
   for M07) and the NULL Script Ptr lines (expect the 100952 one only if that
   zone is entered).

## Full audit (2026-10-07)

Evidence class: source review, read-only host audits of the user's retail data,
ARM `-fsyntax-only` of the patched `Mission07.cpp`/`Mission05.cpp` (rc 0), and
`objdump` of the existing `vita-fast-candidate` object. No build, emulator or
physical Vita run. Receipts are in the git-ignored `build/m07audit/`.

### Fixed

| Patch | Severity | Defect |
|---|---|---|
| `scripts-a36-m07-evac-param-id-buffer.patch` | Medium (main path) | `M07_Inn_Evac::Custom` (`Mission07.cpp:5931`) writes `sprintf("%d")` into `char param1[10]`. Sydney2 and the three DEAD-6 "2" units come from spawners 103833-103836, so their ids are 10-digit dynamic ids (`NETID_DYNAMIC_OBJECT_MIN` = 1,500,000,000). That is an 11-byte write for 4 of the 5 inn evacuations. In the current object the extra NUL lands in padding (`param1` at `sp+20`, `evacPosition` at `sp+32`), so the stack layout is all that keeps it safe. The fix uses 16 bytes plus `snprintf`. The same pattern at `:4135`/`:5138` (`M07_Inn_APC`, `M07_APC_Dec`) is fixed too; neither script is bound in retail M07. |
| `scripts-a36-m07-vehicle-drop-zone-bounds.patch` | Low | `M07_Vehicle_Drop_Controller` (`:3056`) stores the park zone's `10` as `drop_zone` once 7 or more player vehicles have been lost. The next drop then reads `vehicle_drop[10]` of 8. Only params 0-7 are now accepted. |
| `scripts-a36-m05-resistance-poke-index-hang.patch` (M05 audit; covers M07 too) | Medium (hang, optional) | `M05_Resistance_Poke_Conversation` (bound to M07 spawners 101057, 101058, 101109 and 101114) never initializes `last`. Retail spawner definition `M07_Civ_Resist_dsbl` (82050294) can spawn `Civ_Resist_Male_v2b`/`v2c`, which match none of the three `strncmp` groups. That gives `Min == Max == 0`, so `Index()` never ends on the first poke if `last` happens to be 0. `last` now starts at -1. |

Staging was verified with `bash tools/stage_sources.sh`: exit 0, zero fuzz,
528 ordered patches. `renegade_patch_inventory.py --check-staging` passes. No
existing sha256 anchor touches these files.

### (1) Script bindings and parameter counts

- 567/567 bindings are registered (`live_script_bindings.json`, M07 row). The
  discovered closure is 124 scripts; 100 of the 122 `Mission07.cpp` scripts are
  reachable.
- Parameter-count categories: 235 equal, 331 excess, 1 unrecorded. Every excess
  binding is the standard single `"0"` value on a script with no parameters.
  The unrecorded one is `M07_Havoc_DLS`, the combat start script, which has no
  parameters. No M07 binding has fewer values than its descriptor.
- All 74 named `Get_*_Parameter` reads in `Mission07.cpp` match their
  `DECLARE_SCRIPT` descriptors (`script_parameter_reads.json`). Shared outliers
  owned by other units: `RMV_Camera_Behavior` (indexed reads) and
  `M00_Play_Sound_Object_Bone_DAY` (reads `Offset`, which is not declared).

### (2) Event, timer and object-id routes

- Every `Send_Custom_Event` aimed at a literal or macro object id reaches a
  script that handles that type. The objective controller handles all of them
  through `switch(param)`. Unhandled routes, all in scripts not bound in M07 or
  identical on retail PC:
  - `M07_Park_Zone` → 100801 `M07_MOVE_STEALTH_TANK` (unbound)
  - `M07_Prisoner_Gate` → `M07_FREE_CIV` (unbound)
  - `M07_Biohazard_Barrel` (unbound)
  - `M07_Fancy_Inn_Controller` starts timer `CONTROL_SAMS` but has no
    `Timer_Expired` (harmless)
  - Objective controller timer `HAVOCS_SCRIPT` (harmless)
- The duplicate value 7002 (`M07_CUSTOM_ACTIVATE` and
  `M07_REINFORCEMENT_KILLED`) never reaches an object that handles both.
- Literal object ids: 137/138 are serialized; 100952 remains the known lead.
- Waypath ids: all are in the 39 serialized waypaths except 101033
  (`M07_Triangle_Apache`, unbound). A missing waypath fails safe
  (`PathClass::Initialize(NULL)`).
- Spawner ids 100795 and 101010 are not in `m07.ldd`. `Spawner_Enable` is a
  no-op loop, and the callers are optional.
- `M07_Custom_Activate` targets 107794, 107802 and 109138 and
  `M07_Deactivate_Encounter` 111205 are absent. The calls return early through
  `SCRIPT_PTR_CHECK`, the same as on PC.

### (3) Content

- All 21 literal cinematic `.txt` names are present except
  `X7A_Apache_00-03`/`X7A_CPlane_00-03`. Those are used only by
  `M07_Flyover_Controller`, which is not bound.
- From the 13 reachable files: 16 models, 38 animations, 6 audio presets and 9
  real-object presets all resolve.
- All 29 `M07_CON*` conversations and all 38 direct text ids resolve, as do all
  objective POG textures (`audit_mission_conversations`,
  `audit_mission_text_routes`).
- Source misses:
  - `Ramjet_Weapon_Powerup` (known)
  - `M07_Nod_APC` and `o_barrl_bio`: unbound scripts only
  - `Set_Background_Music("Raveshaw_Act on Instinct")` has no extension. Only
    the `.mp3` exists, so playback depends on the original audio lookup. The
    source is retail-identical. This is a physical audio check, not a blocker.

### (4) Crash review

- `Mission07.cpp` has no raw `->` dereference outside `Commands`. Every
  `Commands` entry point M07 uses checks its `GameObject*`. The unchecked ones
  (`Create_3D_*_At_Bone`, `Monitor_Sound`, `Has_Key`) are not called.
- Arrays:
  - `move_loc`: Hotwire params 1-9 into `[10]`
  - `para_drop`: zones 0-6 into `[7]`
  - `ignore_ids`: guarded
  - `attack_id`: `Get_Random_Int(0,2)` is in [0,2)
  - The vehicle-drop case is fixed above.
- Leads (not patched; on retail PC they behave the same and fail safe):
  - `M07_Para_Drop_Controller::para_drop` is not registered for save (the
    `SAVE_VARIABLE` is commented out). After a load, troop drops look up
    indeterminate ids, so `Find_Object` returns NULL and the drop lands at
    the origin.
  - `M08_Mobile_Vehicle` on 100801 is covered by the existing attack-slot
    patch.

### (5) Objective chain

Unchanged and intact:

1. Havoc start (`:332`).
2. 709 → `M07_CON001` → 701 + nuke countdown (100663).
3. 710 accomplished on escape (`:1549`).
4. SAM conversion (`:2091`) → inn evac.
5. The fifth `M07_DEAD6_EVAC` → `M07_CON017` → 703 added (`:5989`); 701/709
   accomplished (`:6047-6049`).
6. 100796 + 100798 killed → 100799 → 703/param 1 after 5 s →
   `Mission_Complete(true)` (`:237-239`).

None of the new patches touch this chain, except that the inn-evac step no
longer overflows. `Set_Wind(90,5,2,0)` at `:1531` is rejected by
`WeatherMgrClass::Set_Wind` (variability > 1). It returns before changing any
parameter, as on PC, while `Set_Ash(0.15,3)` applies.

### (6) Port patches on the M07 path

No earlier patch touches `Mission07.cpp`. Reviewed and consistent for M07:

- `scripts-a36-m08-mobile-vehicle-attack-slot` (`loc` sentinel 100)
- `scripts-a36-m05-apc-deploy-param-buffer` (9 `M05_APC_Deploy` bindings in M07)
- The Test_Cinematic dispatch/load-bounds patches (shared)
- `Start_Custom_Timer` / `SCRIPT_PTR_CHECK` behavior in `scriptcommands.cpp`

### Deferred

- Physical check of the inn evac with spawned evacuees (patched path).
- Raveshaw music playback.
- A >7-vehicle-loss park entry.
- `para_drop` after a mid-mission load.

## Soft-lock hunt (2026-10-07)

Evidence class: source review of staged `Mission07.cpp` and the conversation and
action engine (`activeconversation.cpp`, `conversationmgr.cpp`, `action.cpp`,
`spawn.cpp`), plus a read-only parse of `VARID_ISKEY` in the retail `m07.ldd`.
Checks: ARM `-fsyntax-only` of the patched file (rc 0, 0 errors, no diagnostics in
the new code), `bash tools/stage_sources.sh` (exit 0, zero fuzz, 545 ordered
patches) and `renegade_patch_inventory.py --check-staging` PASS. No build,
emulator or physical Vita run. Line numbers below are for the staged file after
the patches.

### Where completion is really gated

`Mission_Complete(true)` needs only the two park SSM kills (100796/100798 →
100799 `== 2` → 703/param 1, `:3385`). Nothing makes the SSMs invulnerable.
However, the `M07_Hotwire_Help`/`M07_Hotwire_Dead` zones (100971/100987,
`:6719`) play M07_CON029 while Hotwire (100658) still exists, and its ENDED
callback fails 709 (`:6759`). Hotwire is removed only by the inn-evac rope climb.
So any stall in the chain from SAM capture to inn evacuation leaves the player
two choices: wait forever, or go past and fail. The hunt therefore follows the
chain from M07_CON002 through Hotwire to M07_CON017.

### Key flags (retail m07.ldd)

- Key: 001, 002, 013, 014, 017, 018, 019, 020, 021, 022, 028, 029.
- Not key: 003–012 (nuke countdown), 015, 016, 023–027.

A non-key conversation started while a key one plays is stopped with INTERRUPTED
inside `Start_Conversation` (`activeconversation.cpp:399`), before
`Monitor_Conversation`, so no callback is delivered. When a newer key
conversation preempts, `ConversationMgrClass::Think` stops the older one with the
default reason, ENDED.

### Fixed

| Patch | Issue | Reachability / severity |
|---|---|---|
| `scripts-a38-m07-hotwire-sam-conversation-fallback.patch` | `M07_Activate_Hotwire` (`:1915`) sends `M07_HOTWIRE_CAPTURE_SAMS` only from the ENDED callback of **non-key** M07_CON016. If a key conversation is playing when Hotwire enters zone 100684, no callback arrives. `already_entered` stays set, so Hotwire never captures the SAMs: 702, the inn evac, M07_CON017 and 703 never happen, and M07_Hotwire_Dead later fails the mission. | Reachable. The player triggers `M07_Move_Hotwire` 9 in the same zone, so the player is nearby. Key M07_CON013/014 (blast zones, until impact), M07_CON018–022 (objective zones) and M07_CON028 each run 2–15 s. Same on retail PC. **High** (mission becomes unwinnable). Fix: a saved once-only `capture_sent` (ID 2) and a 15 s `CAPTURE_SAMS_FALLBACK` timer (`:1963`/`:1970`). On the normal path the one-line conversation ends first, so the timer is a no-op. Saves made before this patch load `capture_sent=false` and have no timer pending, so they behave as before. |
| `scripts-a38-m07-hotwire-path-failure-fallback.patch` | Hotwire (`:1168`) continues GO_SAM1/GO_SAM2 only on NORMAL, and counts as the fifth inn evacuee only on NORMAL or MOVE_NO_PROGRESS_MADE, through the designers' own "pathfinding around dec_phys vehicles at inn" hack (`:1189`). PATH_BAD_START/PATH_BAD_DEST on the evac goto, or a failed or no-progress SAM goto, leaves Hotwire idle. The SAMs are never converted, or the evac stops at 4 of 5. | Reachable only if pathfinding fails, which is unproven. The designers saw NO_PROGRESS at the inn. **High** if it happens. Fix: map these failures onto the existing branches. A SAM goto failure takes the NORMAL branch (attack plus the timer-driven conversion). An evac goto path failure takes the no-progress branch. `ActionClass::Done` clears the action before notifying, so there is never a second notification. LOW_PRIORITY is deliberately not remapped, because a rejected request notifies synchronously inside `M07_Inn_Evac::Custom`, and re-entering it would start M07_CON017 twice. |

### Reviewed, not changed

- **(a) Other conversation gates.**
  - 300701 (M07_CON001, key, ENDED only, `:308`). INTERRUPTED comes only from a
    dead orator (Gunner or Havoc, both of which already fail the mission) or from
    Havoc being more than 200 m from the centre during the briefing. In that case
    the nuke, 701 and 710 are skipped, but M07_CON002 still drives the chain
    (`M07_Move_To_Evac` moves the team). Not a completion blocker. Same on retail.
    Low.
  - 300702, 300703 and 300704–300708 accept ENDED or INTERRUPTED, and all are key.
  - M07_CON015's monitor checks 300702, so 707 is never added from Havoc. This is
    a dead branch in the original; 707 comes from zone 100804.
- **(b) Order.**
  - 703/param 1 does not need 703 to have been added.
  - 701/709/710/702 accomplish events can only come after their adds.
  - Secondary 704–708 can be accomplished before their briefing zone adds them,
    and then stay pending. Same on retail; secondary only.
  - If the SAMs are captured before nuke impact, the ESCAPED check (`:1560`)
    sees `SYDNEY` already destroyed, so 710 stays pending. This does not block
    completion.
- **(c) Counters.**
  - Inn evac (5, `:5984`/`:5989`): Sydney2 and the three DEAD-6 "2" units send on
    **any** completion reason of their waypath. If one is killed, the mission
    fails (710/701 param 2), so the count is never stuck short. If a spawn point
    is blocked, `Check_Auto_Spawn` retries every frame. Hotwire's `Destroyed`
    sends a sixth event (Find_Object(1) is NULL), which is harmless. Duplicate
    events can only overcount, and `== 4`/`== 5` then fire early, which does not
    block.
  - Evac site (`:1792`, needs 4): 2 APCs plus 6 gun emplacements, counted on
    any killer.
  - SAM (`:2129`): converted `== 1`. Killed `== 2` fails the mission.
  - Park (`== 2`): placed SSMs, counted on any killer, with no STAR filter.
  - No M07 counter filters `Killed` by killer.
- **(d) One-shot triggers.**
  - `TANK_STILL_THERE` (`:1157`) retries until 100905 (a killable light tank) is
    gone. That is by design.
  - Entering `M07_Hotwire_Dead` while Hotwire is still climbing fails the
    mission. Same on retail.
- **(e) Lost units.**
  - Player vehicles and para drops are optional. `para_drop[]` is still not
    saved, so after a load the drops fall back to the origin (enemy-only, known
    lead). `vehicle_drop[]` is saved.
  - Hotwire has no damage path other than mission failure.
- **(f) Save/load.**
  - All chain counters and flags are saved: `dead6_cnt`, `already_entered`,
    Hotwire's `evac`/`dont_move`, the inn/park/evac-site counters, and the new
    `capture_sent`.
  - Script timers and delayed customs persist (`GameObjObserverTimerClass` /
    `GameObjCustomTimerClass`). That includes the 5 s 703 delay and the new
    fallback timer.
  - Death or restart reloads the level from scratch.

### Deferred (physical)

- The inn evac with a key briefing overlapping Hotwire's zone entry (the patched
  path). Expected telemetry: a conversation start/stop for M07_CON016 with no
  kind-3 observer call, then Hotwire moving to the SAMs about 15 s later.
- Save/load during the rope climb (bone attachment persistence). If Hotwire
  survives a load still attached to the rope, M07_Hotwire_Dead would fail the
  mission.
- M07_CON001 audience distance (200 m) during the opening briefing.

## Follow-up fixes (2026-10-07)

Evidence class: source review of the staged `Mission07.cpp` and of the engine
save state (`physicalgameobj.cpp`, `animcontrol.cpp`, `action.cpp`,
`activeconversation.cpp`, `conversationmgr.cpp`), plus a read-only parse of the
retail `always.dat` animation headers. Checks: `bash tools/stage_sources.sh`
(exit 0, zero fuzz, 571 ordered patches), `renegade_patch_inventory.py
--check-staging` PASS, ARM `-fsyntax-only` of the patched file (rc 0, no
diagnostics in the new code). `audit_script_save_state_gaps.py` no longer
lists `para_drop`. No build, emulator or physical Vita run. Patch:
`scripts-a38-m07-followup-climb-briefing-evac-paradrop.patch`, registered after
`scripts-a38-m07-hotwire-path-failure-fallback.patch`. Line numbers are for the
staged file.

| # | Issue | Decision / fix |
|---|---|---|
| 1 | **Rope climb across save/load.** The engine saves everything the climb needs: Hotwire's bone attachment (`HostGameObj` and bone index), both animation channels (name, frame and mode), the `PlayAnimation` action code and its parameters (observer id and action id), and script timers. After a load the climb resumes. It completes NORMAL when the animation finishes, or through the port's 5 s stall guard. The retail animations are short: `XG_EV5_Troop` is 30 frames at 15 fps (2 s), and so is `XG_EV5_troopBN`. The remaining hole is in the script. `M07_Climb_Rope` only finishes on a NORMAL completion, so a preempted climb (LOW_PRIORITY) or one that is lost leaves Hotwire on the rope, and `M07_Hotwire_Dead` then fails the mission. | Added a saved, once-only `climb_finished` (ID 1) and a 10 s `CLIMB_ROPE_FALLBACK` timer (`:6203`, `:6227`, `:6230`, `:6251`). Timers are saved, so a mid-climb save keeps it. On the normal path the evacuee is destroyed at 2 s and the timer never fires. It applies to all five climbers. |
| 2 | **M07_CON001 / 300701 cut short.** INTERRUPTED (Havoc more than 200 m from the centre, or a dead orator) or UNABLE_TO_INIT skipped the whole ENDED block. Besides 701/710 and the nuke countdown, this also skipped the `M07_GO_ASSEMBLY` order to the team. That hides two primary objectives and the countdown guidance; 709's blip at 100717 is the only pointer left. It does not block completion. | Hidden guidance, so I added a minimal fallback. The ENDED block moved unchanged into `Briefing_Ended` (`:335`), which runs once under a saved `briefing_done` flag (ID 3). INTERRUPTED/UNABLE_TO_INIT start a 1 s `BRIEFING_FALLBACK` timer (`:331`). The timer runs the block only if Havoc and Gunner are alive (`:304`). If an orator died, the mission has already failed. Stops during level teardown never fire the timer. ENDED behaves as before. |
| 3 | **LOW_PRIORITY on ARRIVE_EVAC_SPOT.** A rejected or preempted evac goto left Hotwire idle at 4 of 5 evacuees. A rejection is notified synchronously inside `M07_Inn_Evac::Custom`, so reporting from there could start M07_CON017 twice. | Added a saved `evac_reported` (ID 9). `Report_Evac` (`:1041`) sends `M07_DEAD6_EVAC` at most once. LOW_PRIORITY never reports; instead it starts a 2 s `ARRIVE_EVAC_RETRY` timer (`:1260`) that repeats the same goto through `Go_Evac_Spot` (`:1033`, `:1218`) until she reports. This is the designers' GO_SAM1 retry pattern. NORMAL and NO_PROGRESS report exactly as before. |
| 4 | **`para_drop` not saved.** It was assigned only in `Created`, so after a load the drops looked up id 0 and landed at the origin. | Saved under unused ID 8 (`:5511`). The literals moved unchanged into `Init_Para_Drop` (`:5514`). A save from before this change restores nothing, and the table is then re-seeded at the drop site (`:5565`). Drop behavior on the normal path is identical. |

Compatibility: all new members are zero-initialized by the script factory, and
each fallback timer is only ever started by the new code. Saves made before
this patch therefore load with the old behavior, except that `para_drop` is now
re-seeded.

### Deferred

- Physical check of a mid-climb save/load: Hotwire should vanish within 2 s of
  the load, or at the latest within 10 s.
- Physical check of the CON001 fallback (leave the audience radius during the
  opening briefing). Expect 701, then 710 2 s later, the countdown, and the
  team's assembly move.
- `apc_id` in eight soldier scripts and `M07_Encounter_Unit::stationary` are
  still Created-only according to `audit_script_save_state_gaps.py`. These are
  optional enemy counters, unchanged here.
