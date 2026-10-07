# M06 completion readiness

Evidence class: source and retail-metadata inspection only (2026-10-07). No
build, host test run, emulator or Vita run. Mission 06 is not physically
accepted.

## Summary

- `staging/scripts/Mission06.cpp` is byte-identical to upstream
  (`script_portability.json`: staged SHA-256 equals the original). No Vita
  patch touches it.
- All 644 authored M06 script bindings resolve through the static registry
  (`reports/generated/sweeps/live_script_bindings.json`, M06 row: 644/644,
  no missing names).
- Retail `M06_Objective_Controller` does **not** own the success transition.
  The released `Mission_Complete(true)` comes from the engine-side
  `MendozaBossGameObjClass` death sequence. The script-side success branch
  (objective 604) is unreachable in retail data because `M06_Mendoza` is bound
  nowhere: there are 0 authored bindings and the `Attach_Script` call is
  commented out at `Mission06.cpp:505`. Retail PC behaves the same way.
- I found no blocking source defect in the completion chain and made no code
  change. One original latent issue (time-scale leak) is listed under risks.

## Objective chain (file:line)

Controller `M06_Objective_Controller` (`Mission06.cpp:48`) is persisted on
object 100018 together with `M06_Destruction_Stub` and
`M06_Flyover_Controller`, each with one persisted binding.

1. Start: `Created` (`:63-90`) plays conversation M06_CON059 and adds hidden
   objectives 605, 607 and 608. When the conversation ends, `Action_Complete`
   (`:270-276`) adds 601, "Hack War Room Computer".
2. War room: `M06_WarRoom_Computer::Poked` (`:328-345`) on 106952 plays
   M06_CON001 and drops `Level_03_Keycard`. On completion (`:355-356`) 601 is
   accomplished and 603, "Rescue Scientists", is added.
3. Midtro B: the `M06_Activate_Midtro` zone (`:638-683`) opens doors
   1300001615 and 1553454 and runs `Test_Cinematic X6B_MIDTRO.txt`
   (M06.mix). At frame 2380 the cinematic sends `Send_Custom 101010, 6027, 0`
   to Sydney.
4. `M06_Sydney_Mobius::Custom` with M06_RELOCATE param 0 (`:456-478`):
   - relocates Havoc through the level start script `M06_Havoc_DLS`
     (`:3450-3462`), attached in `god.cpp:186` by CombatManager start script;
   - arms the MidtroC zone 108285 (`:464`);
   - starts the destruction stub (`:469`);
   - accomplishes 603 (`:471`) and adds 611, "Escort Sydney" (`:473`).
5. Midtro C: the `M06_Activate_MidtroC` zone (`:5557-5624`) runs
   `X6C_MIDTRO.txt`. At frame 494 it sends `Send_Custom 101010, 6027, 1`.
6. `M06_Sydney_Mobius::Custom` with param 1 (`:481-518`) accomplishes 611
   (`:485`), runs `Create_Object("Mendoza Boss")` (`:497`), adds 604 (`:509`),
   gives Sydney a "Blamo" shield (`:512-513`), and sends logical sound
   M06_CLEAR_FOR_MENDOZA to remove spawners (`:517`, `M06_Clear_For_Mendoza`
   `:5626`).
7. Boss (`staging/combat/mendozabossgameobj.cpp`):
   - `Initialize_Boss` binds Sydney 101010 (`:691-705`). `Think` runs only
     while the star and Sydney exist (`:830`).
   - `Apply_Damage_Extended` (`:942-1030`): at or below 25% health it switches
     to SYDNEY_BOLTS. Sydney bolts, trips and cowers (`:3080-3199`). While she
     cowers, each hit has a 1-in-4 chance of starting the DEATH_SEQUENCE
     (`:976-979`).
   - The death sequence runs FACE_ZOOM (`:1365-1436`), then WAYPATH_FOLLOW
     along waypath 3000100 (`:1447-1537`), then LOOK_AT_DEAD_BOSS
     (`:1547-1585`).
   - Finally `CombatManager::Mission_Complete(true)` (`:1583`) calls
     `MiscHandler` (`combat.cpp:1093`). This is the same owner the script
     command uses (`scriptcommands.cpp:1970`).
8. Failure: when Sydney is killed (`:610-615`), 611 is failed and
   `Mission_Complete(false)` runs (`:250-254`).

## Data and registry checks (retail Vita3K copy, read-only)

- The `Mendoza Boss` preset is present in objects.ddb. MendozaBossGameObjDef
  class 12311 is found in the host definition registry with its ARM symbol.
  `mendozabossgameobj.cpp` is linked through
  `cmake/A35MultiplayerBuildingSources.cmake:17`.
- Assets `CAMBONE` and `AG_MENDOZA_DIE` are in always.dat. Waypath 3000100 is
  in m06.lsd. The waypath persist factory is linked (`A30OriginalSources.cmake`).
- Level IDs 101010, 100018, 106952, 108285, 107606, 108277 and 101527 are in
  m06.ldd. Static anim IDs 1300001615 and 1553454 are in both m06.lsd and
  m06.ldd.
- `x6b_midtro.txt` (144 records) and `x6c_midtro.txt` (76 records) parse
  identically on the host (`host_retail_cinematic_parser.json`).
- M06 has no train, elevator or moving-platform scripting. Its vehicles are
  ambient Apache/Chinook flyovers and `M06_Escort_Tank`.

## Blockers

- Found: none blocking in source or data.
- Fixed (2026-10-07): `combat-a36-boss-waypath-release-guard.patch` guards the
  waypath 3000100 lookup (risk 2). Host ARM syntax-check only.

## Risks (non-blocking, unverified)

1. **Time-scale leak (original).** FACE_ZOOM sets `TimeManager` scale to 0.25
   and LOOK_AT_DEAD_BOSS sets it to 0.5. Scale goes back to 1.0 only at the
   end of the sequence. `TimeManager::Reset` is called only from the network
   timer path (`combatgmode.cpp:1427`). Quitting or loading during the roughly
   15-second death sequence could leave the next level in slow motion.
   Mitigated on Vita: `A31_Vita_Run_Interactive_Runtime` sets the time scale to
   1.0 at every session start, so the next level cannot inherit slow motion.
   Within the same session the original behaviour is unchanged.
2. **Waypath dereference (fixed).** `Find_Waypath(3000100)` was guarded only by
   `WWASSERT`. `combat-a36-boss-waypath-release-guard.patch` now skips the
   camera path when the waypath is missing or has fewer than two keys, goes
   straight to LOOK_AT_DEAD_BOSS (which still calls `Mission_Complete(true)`),
   and logs `A3.5 Mendoza death camera: waypath 3000100 unusable`. The data is
   present, so the fallback should never fire.
3. **Missing flyover texts.** Retail lacks `M06_XG_VehicleDrop0/1/2.txt`. When
   the flyover controller picks one of them (`:4941-4980`), Test_Cinematic
   destroys its empty controller and the ambient flyover chain stops. Retail PC
   does the same, and it does not affect completion.
4. **Radar blip lookup.** Objective 604 looks up 108275, which is not
   serialized (null-guarded at `:127`), so Mendoza gets no radar blip.
   Objective 604 also stays Pending at success because the boss class, not the
   script, completes the mission.
5. **Sydney pathing.** Sydney must reach `SYDNEY_END_POS` within 5 m
   (`:3106-3113`) for the cowering state and death trigger. This depends on
   the pathfind `Goto` working on the Vita.
6. **Natural flow after success.** Score, movie and progression into M07
   after `Mission_Complete(true)` is the shared campaign path. It still has no
   executable or physical evidence (see KNOWN_GAPS).

## Physical test route

1. Load M06 from New Campaign or the mission select. Check that the
   CON059/CON060 EVA lines play and objective 601 appears.
2. Hack the war room computer. Expect 601 to complete, 603 to appear and the
   keycard to drop.
3. Go to the lab or basement. Expect MidtroB to play (camera, explosions),
   then Havoc and Sydney to relocate, 603 to complete and 611 to appear.
4. Escort Sydney through the collapse. Check that the collapse zones fire,
   the MidtroC zone triggers, Mendoza spawns and 604 appears.
5. Bring Mendoza below 25% health. Expect Sydney to bolt, trip and cower.
   Keep shooting until the face-zoom death camera starts.
6. Wait about 15 seconds. Check that time returns to normal speed, then the
   success screen appears and M07 continuation starts.
7. Negative check: let Sydney die before step 6. Expect 611 to fail and the
   mission-failed flow to run.

Breadcrumbs to collect: script lookup misses (expected none), mission
completion log, time-scale state after a reload taken during step 6.

## Full audit (2026-10-07)

Evidence class: source review plus read-only host tools against the retail
Vita3K copy (`M06.mix` sha256 `cf98d879…573a`). No build, emulator or Vita
run. Detailed receipts stay in the ignored `build/` tree. Tools used:
`tools.audit_mission_content_bindings`, `tools.audit_mission_conversations`,
`tools.audit_mission_text_routes` and
`tools/renegade_cinematic_dependency_scan.py` (all with `--map M06.mix`),
`reports/generated/sweeps/live_script_{bindings,parameters}.json`, and ad-hoc
literal and ID sweeps over `Mission06.cpp`.

Result: no new blocking defect, and no new patch. The objective chain to
`Mission_Complete(true)` is intact with the current port patches. I decided
against a CAMBONE guard (reasons in section 4).

### 1. Script names and parameter counts

- 644/644 bindings resolve: 607 level bindings plus 37 definition bindings,
  across 99 scripts. No shipped script name is unknown.
- Parameter shapes: 264 have an equal count and 379 have an excess count.
  Every excess binding has one value for a script with no parameter
  descriptor, so the value is never read. One is unrecorded: the
  `M06_Havoc_DLS` combat start script, which takes no parameters.
  **None has fewer values than its descriptor.**
- I checked the parameter-carried content as well:
  - Move_Loc values 1-12 index the 13-entry `Sydney_Move_Table`.
  - 20 patrol `Waypath_ID` values are in `m06.lsd`.
  - The servant location IDs are serialized objects, and its animation
    `H_A_A0F0` is in always.dat.
  - All 13 `M00_Play_Sound*` sound presets are in objects.ddb.

### 2. Events, timers and hard-coded IDs

- **Custom events.** Every `Send_Custom_Event` type in the 99 scripts has a
  `Custom` receiver. Types 601-611 to 100018 are handled by
  `switch (param)` in the controller (`:209-262`).
- **Cinematic sends.** `x6b_midtro.txt` sends `Send_Custom 101010, 6027, 0`
  at frame 2380. `x6c_midtro.txt` sends `… 6027, 1` at frame 494. Type 6027
  is `M06_RELOCATE` (`mission6.h:77`), and the receiver is
  `M06_Sydney_Mobius::Custom` (`:455-518`).
- **Receiver with no sender.** `M06_MidtroB_Explosion_Controller` (`:620`)
  listens for `M06_MIDTRO_EXPLOSION` (6028), but nothing sends it, in source
  or in any cinematic. Retail PC behaves the same; the effect is cosmetic.
- **Timers.** Every `Start_Timer` id has a branch in the same script's
  `Timer_Expired`. The only exception is id 0 in the shared
  `M00_Play_Sound*`, `Test_Cinematic` and `RMV_Camera_Behavior` helpers, which
  handle any id.
- **`Find_Object` literals.** Of 147, 146 are serialized objects. The
  remaining one, 108275, is null-guarded at `:127`.
- **All 198 integer literals** of 6 or more digits in `Mission06.cpp`:
  - Waypaths 101023, 101100-101102, 101428, 101520, 101552, 102252 and
    3000100 are in `m06.lsd`.
  - Static-anim targets 1300001615, 1553454 and 1553207 (the secret door
    parameter) are in both `m06.lsd` and `m06.ldd`.
- **IDs not located in the level data:**
  - 110908, 101021 and waypoints 101024/101027 appear only in the unbound
    `M06_Gate_Guards` (`:1143`).
  - 101035/101036 are passed to `Enable_Spawner` in `M06_Nod_Tower` (`:2517`)
    and `M06_Enable_Exterior_Courtyard` (`:2902`). `Spawner_Enable` just
    loops without a match (`spawn.cpp:1100`).
  - 100823, 1010211, 1109081 and 300xxx are conversation action IDs, not
    objects.

### 3. Content references

- Literal presets from `Create_Object`, `Create_Explosion` and `Create_Sound`:
  0 missing.
- Conversations: all 62 names in `Mission06.cpp` are in `m06.ldd`, and all 38
  computed calls resolve.
- Text: 25 direct text IDs and 6 objective POG textures resolve.
- Models: all 51 `Set_Model` names exist as `.w3d`.
- Animations: every dotted animation literal resolves except `BK.BK`. That
  animation is embedded in `M06.mix:book_dr3.w3d`, the secret-door model,
  so the static object loads it.
- Cinematics: 14 `.txt` controls resolve. Every animation, audio, model and
  real-object preset they use resolves. `M06_XG_VehicleDrop0/1/2.txt` are
  still missing, as on retail PC (risk 3).
- Mendoza Boss assets, all present:
  - model `c_ag_nod_mdz.w3d` and the 13 `S_A/S_B_HUMAN` animations;
  - `AG_MENDOZA_DIE` and `CAMBONE` (hierarchy plus HLOD, 364 bytes);
  - `Fight Whoosh/Impact Sound Twiddler`, `SFX.Fire_Small_01` and
    `POW_Health_025`;
  - the `Blamo` armor type, in always.dat `armor.ini`.
- **Definitions not located:**
  - 8 of the 13 choices of `M06_Barracks_Powerups_Twiddler` (81950011-81950049)
    are absent from objects.ddb. The only creator is
    `M06_Barracks_Patrol` (`:2429`) through `Commands->Create_Object`. There,
    `TwiddlerClass::Create` returns NULL (`twiddler.cpp:142-148`) and both
    `Create_Object` layers tolerate NULL. About 8 of 13 drops therefore spawn
    no powerup, as on retail PC.
  - No spawner references the twiddler. The unguarded
    NULL path in `SpawnerClass::Spawn` (`spawn.cpp:694-698`) is not reachable
    from M06 data.
  - The other not-located IDs are global, not M06-specific: weapon
    muzzle-flash and eject phys defs, and Death Cries Twiddler choice 3413.

### 4. Crash review and the CAMBONE decision

- **Array indexing.** `flyovers[11]` uses `Get_Int_Random(0,10)`, which is
  inclusive and clamped (`toolkit.h:186`). `barracks_drop[5]` uses (0,4) and
  `barracks_pickup[6]` uses (0,5). The `conv_name[N]` arrays are guarded by
  `random < N`. `explode_loc[param]` cannot be reached (see section 2).
- **NULL objects in commands.** The commands M06 passes `Find_Object` results
  to are `SCRIPT_PTR_CHECK` guarded (`scriptcommands.cpp:103-104`):
  `Get_Position`, `Set_Position`, `Send_Custom_Event` and `Set_Facing`.
  `Join_Conversation(NULL)` is the original anonymous-orator path, and
  `Action_Goto` with a NULL move object falls back to `MoveLocation`
  (`action.cpp:930`).
- **CameraBoneModel (CAMBONE): no guard added.**
  - It is created in the constructor (`mendozabossgameobj.cpp:468`) and
    dereferenced unguarded:
    - in FACE_ZOOM (`:1373-1374`, `:1396`, `:1437`);
    - in WAYPATH_FOLLOW_Think (`:1553`);
    - in `Save_Variables` (`:721`) and `Load_Variables` (`:794`).
  - It can be NULL only in two cases:
    - **The asset fails to load.** `cambone.w3d` is in always.dat and is a
      plain hierarchy plus HLOD, loaded by the same asset-manager path as
      every other HLOD.
    - **After `LOOK_AT_DEAD_BOSS_Think` releases it (`:1604`)**, just before
      `Mission_Complete(true)`. On the Vita there is no save opportunity in
      that window, for three reasons:
      - Quicksave input is sampled before `CombatManager::Think`
        (`a31_gameplay_boundary.cpp:766-769` versus `:797`).
      - The completion latch (`:418`) is consumed after that same frame, and
        the intermission runs immediately (`a31_vita_runtime.cpp:6412-6446`).
      - The original handler also runs `CampaignManager::Continue` within the
        same `Think` (`combatgmode.cpp:1601`).
  - With retail data, a guard would only change unreachable behaviour, so it
    would be speculative. Revisit it if a log ever shows a NULL
    `CameraBoneModel`.
- **Sydney.** Her dereferences in the boss state handlers rely on
  `Think`'s `Sydney == NULL` gate (`:830`) and on her Blamo shield
  (`Mission06.cpp:511-512`). This is original behaviour.

### 5. Objective chain

I re-traced the chain from the controller `Created` (`:63`) to
`MendozaBossGameObjClass` `LOOK_AT_DEAD_BOSS_Think` →
`CombatManager::Mission_Complete(true)`. It matches the "Objective chain"
section above. Two more points:

- **Order dependence.** Objective 601 is added only when M06_CON059 ends or
  is interrupted (`:270-276`). If the war room computer is hacked before
  that, 601 is added after it was accomplished and stays Pending. This is
  cosmetic and does not block the boss-owned success.
- **The two cinematic hand-offs** (frames 2380 and 494, both to 101010) are
  the only links into the escort and boss phases. They depend on
  `Test_Cinematic` running to the end. That is a shared cinematic path, with
  no M06-specific patch.

### 6. Port patches on the M06 path

- **`combat-a36-boss-save-status.patch` and `combat-a36-boss-load-status.patch`**
  only add status propagation (including `CameraSpline.Load`). They do not
  change behaviour.
- **`combat-a36-boss-waypath-release-guard.patch` is correct.** The nested
  `CameraState.Set_State (LOOK_AT_DEAD_BOSS, true)` inside a Begin handler is
  safe. `StateMachineClass::Set_State` (`statemachine.h:334-372`) assigns
  `CurrState` before calling Begin, and WAYPATH_FOLLOW has no End handler.
  The time scale then goes from 1.0 to 0.5 exactly as on the normal path.
- **That guard is not in the dev238 ELF yet.** Its log string is absent from
  `build/vita-fast-candidate/RenegadeVitaA31`, so it needs the next build.
- **Shared patches on the M06 path:**
  - the `scripts-a35-cinematic-*` series (`Test_Cinematic`);
  - `scripts-a35-vector-parameter-initialization.patch`, for the empty
    `Offset` values in M06 `M00_Play_Sound` bindings;
  - the spawner load/field admission patches;
  - the Vita completion latch and intermission owners.

  None is M06-specific. No patch touches `Mission06.cpp`.

### Deferred (no change; retail-identical or non-blocking)

- **Unsaved arrays.** `M06_Barracks_Patrol` `barracks_drop`/`barracks_pickup`
  (`:2342-2343`) are initialized only in `Created` and are not registered.
  After a load they hold indeterminate IDs, so `Find_Object` returns NULL
  and the patrol walks to `MoveLocation`. The failure is safe. This adds to
  the M06 entries in `SCRIPT_SAVE_STATE_GAPS.md`.
- **Collapse zones.** Only 5 of the 9 `M06_Collapse_Zone` objects receive
  `M06_CHATEAU_COLLAPSE` from the destruction stub (`:696-700`). The other 4
  zones never arm, so some rubble and falling-rock effects do not appear:
  Zone_ID 5, 6, 7 and 9, on objects 101324, 101583, 101585 and 101390. This
  is cosmetic.
- **The flyover chain** stops when the controller rolls 0 (no case), or 1 or
  2 (the missing texts). This is cosmetic.
- **Runtime risks** 1, 2, 5 and 6 above are still unverified at runtime.

## Soft-lock hunt (2026-10-07)

Evidence class: staged-source review plus a read-only parse of the retail
Vita3K `M06.mix:m06.ldd` conversation flags (`ConversationClass` VARID 13 =
`IsKey`). No build, emulator or Vita run. Result: **no reachable blocker
found and no patch added.** `Mission06.cpp` is still byte-identical to
upstream.

Two facts govern every objective race in M06:

- Objectives cannot block success. `Mission_Complete(true)` is owned by the
  Mendoza boss (`mendozabossgameobj.cpp:1609`). `CombatGameMiscHandlerClass::
  Mission_Complete` (`combatgmode.cpp:1716-1723`) does not inspect
  objectives. `Set_Objective_Status` on a missing ID and `Add_Objective` on an
  existing ID are no-ops (`objectives.cpp:558-561`, `:491-493`).
- Only three M06 conversations are key: **M06_CON001** (war room hack),
  **M06_CON059** (intro) and **M06_CON060** (alarm warning). All 61 others are
  non-key (priority 30, interruptable).

### Objective 601 (hack before M06_CON059 ends): not reachable, not blocking

The earlier note in "Full audit" section 5 is corrected here.

- Poking 106952 starts CON001, which is key (`Mission06.cpp:328-345`).
  `Start_Conversation` does not stop a key conversation
  (`activeconversation.cpp:385-391`).
- On the next frame, `ConversationMgrClass::Think` scans from the newest
  entry. It keeps the newest key conversation and stops every older one,
  including older key ones, with ENDED (`conversationmgr.cpp:1134-1175`,
  identical to upstream `:1058-1075`). CON059 is older, so it is stopped.
  `Action_Complete(300601, ENDED)` then adds 601 synchronously (`:270-276`,
  delay 0).
- CON001 has two remarks and needs several frames to end, so 601 is always
  added before `601,1` arrives (`:352-356`). If a later key conversation
  (CON060) preempts CON001, the reason is ENDED, which is also accepted.
- The order "accomplish, then add" therefore cannot happen through CON059. The
  original code needs no change.

### (a) Non-key conversation callbacks

Pattern: a non-key conversation started while CON001, CON059 or CON060 is
active is stopped inside `Start_Conversation` before `Monitor_Conversation`
registers (`activeconversation.cpp:397-401`), so the callback is lost.

| Script (line) | Conversation | Effect if lost | Impact |
|---|---|---|---|
| `M06_GDI_Prisoner` (:866-892) | CON008 | 607 never accomplished; prisoner stays stationary | hidden objective |
| `M06_Activate_Secret_Door` (:950-969) | CON061 | bookcase 1553207 never opens; 608 lost (`already_poked` set) | hidden objective and loot |
| `M06_Civ_Prisoner` (:1009-1059) | CON009/CON063 | `conversation` stays true; 605 lost | hidden objective |
| `M06_Resistance_Raider_DLS` (:3496-3527) | CON045 | no grenade-launcher drop | cosmetic |
| `M06_KaneHead` (:4289-4309), `M06_Assistance_Farmer_DLS` (:3571-3616) | flavour | none | cosmetic |

- No primary objective and no door, zone or NPC on the success chain depends
  on a non-key callback.
- The success-chain links are all callback-free: war room keycard drop
  (`:343`, inside `Poked`), MidtroB zone, cinematic customs and MidtroC zone.
- Retail-identical. Deferred.

### (b) Other completion-before-activation races

These are reachable, but neither blocks success. Retail-identical, deferred.

- **609 "Deactivate alarm system" (secondary).**
  - Order: the player pokes or destroys an `M06_Alarm_Terminal_DLS`
    (`:1866-1880`) before entering zone 101055 or before CON060 ends.
  - The Alarm_Controller timer sends `609,1` (`:1474`). The objective does not
    exist yet, so the status change is a no-op, but `accomplished_609` is set
    (`:241`).
  - CON060 later adds 609 as Pending (`:5696-5701`). The guard at `:229` then
    rejects every later `609,1`.
  - Result: 609 stays Pending, with a stale HUD pointer to the alarm.
- **603 "Rescue Scientists" (primary, cosmetic).**
  - Order: freeing the GDI prisoner grants Havoc key 3 (`:880`). If key 3
    alone opens the basement route, the player can trigger MidtroB without
    hacking 106952. Spatial reachability is unverified.
  - Relocation sends `603,1` before 603 exists (`:471`). A later hack then
    adds 603, which stays Pending, while 601 stays Pending from CON059.
  - Neither objective gates the boss.

### (c) N-of-M counters

- The only counters are spawner controllers: `dead_courtyard_eagle`
  (`:2547`), `dead_hedgemaze_eagle` (`:2594`), `dead_barracks_eagle`
  (`:2657`) and `dead_interior_patrol` (`:2714`). All use `==` thresholds.
- They only disable spawners. An undercount keeps reinforcements spawning;
  it does not lock progress.
- The objective chain has no counter.

### (d) One-shot triggers in the wrong state

- **Collapse zones 5/6/7/9 are cosmetic (confirmed).** Every `Zone_ID` case
  (`:5342-5552`) only creates `Invisible_Object` instances with
  `L6_fall*` models. There is no `Destroy_Object`, door, custom or spawner
  call. A zone that is never armed means fewer debris props, never a closed
  path.
- **`M06_Activate_MidtroC`** starts disarmed (`:5573`). It is armed only by
  Sydney's relocate param 0 (`:464`, saved flag `:5567`), and that is the
  only route to it, so it cannot fire early.
- **`M06_Activate_Midtro`** is one-shot and saved (`:648`). It has no
  prerequisite beyond reaching it.
- **Objective controller.** The `type > 611` filter (`:221`) keeps all
  `mission6.h` customs (6000+, 16600+) away from the objective switch. The
  destruction stub's `100,100` matches no case.

### (e) Required NPCs stuck or lost

- **The escort is not gating.** MidtroC triggers on Havoc alone
  (`:5579`). X6C then teleports Sydney to 108277 (`:481`), so Sydney stalling
  on the escort path cannot soft-lock the mission. Her death fails the mission
  through 611 (`:610-615`, `:250-254`). That is a failure, not a lock.
- **Boss end positions.** These states have no timeout or fallback:
  - Sydney's bolt needs her within 5 m of `SYDNEY_END_POS`
    (`mendozabossgameobj.cpp:3124-3139`).
  - Tripping advances only once Mendoza is within 2 m of `MENDOZA_END_POS`
    (`:3007-3012`, `:3171-3183`).
  - The death roll needs `SYDNEY_STATE_COWERING` (`:979`).
- **How those states could stall.**
  - A body blocking the path only pauses movement until it clears
    (`action.cpp:1279-1284`).
  - A permanent stall needs a pathfind error, which completes the goto with
    `ACTION_COMPLETE_MOVE_NO_PROGRESS_MADE` (`action.cpp:1297-1303`). That
    depends on data and is retail-identical.
  - Sydney's own script goto (priority 85, `:525-534`, `:560-567`) cannot
    override the boss goto (priority 100).
- Not shown reachable from source. Deferred; no speculative boss fallback was
  added. Physical signature: overall state stuck in RUN_AFTER_SYDNEY or
  TOY_WITH_SYDNEY with Sydney in BOLTING or TRIPPING, and an action
  completion reason of NO_PROGRESS for action 777.

### (f) Save/load and death/restart

- **Saved state on the chain.** The flags MidtroB, MidtroC, war room
  `already_poked`, Sydney `poke_id`/`dont_move`/`current_move_loc` and
  objective-controller `accomplished_609` are all `SAVE_VARIABLE`s. Active
  conversations save their monitors (CONVERSATION_COMPLETION.md section 3).
- **The boss rebinds Sydney after a load.** `On_Post_Load` calls
  `Initialize_Boss` (`:680-708`), and the boss state machines are saved.
- **Death sequence after a load.** `FACE_ZOOM` does not re-run its Begin, so
  the camera is not re-hosted. Its Think still converges by position
  (`:1390-1436`) into `WAYPATH_FOLLOW` (scale 1.0), then `LOOK_AT_DEAD_BOSS`
  (0.5, then 1.0) and `Mission_Complete(true)`. The effect is visual only.
- **Slow motion.** Every reload, restart and continuation re-enters
  `A31_Vita_Run_Interactive_Runtime` (`a30_main.cpp:235-243`), which sets the
  time scale to 1.0 (`a31_vita_runtime.cpp:4653-4657`). Dying during the
  0.25x window therefore cannot carry slow motion into the restarted mission.
  Within one session, the original behaviour is unchanged.

### Deferred (no change)

- 609 and 603 can stay Pending (cosmetic).
- Callbacks for the non-key hidden objectives 605, 607 and 608 can be lost.
- Boss end-position stalls with no fallback (runtime-only).
- The camera host is not restored after a load mid death sequence (visual).
- Any fix for the conversation-drop pattern shares the open design decision
  recorded in M10_READINESS.md: late `Register_Monitor` delivery versus
  per-mission resends.

## Follow-up fixes (2026-10-07)

Evidence class: staged-source change, `arm-vita-eabi-g++ -fsyntax-only` on
both files, `tools/stage_sources.sh` exit 0 with zero fuzz and no offsets,
and a re-run of `tools.audit_conversation_gated_objectives --mission M06`
(M06: 3 FIXED, 0 REVIEW, 0 AT RISK). No build, emulator or Vita run.
This supersedes the Summary note that `Mission06.cpp` is byte-identical to
upstream, and the deferred items for 605/607/608, the boss end positions and
603/609 in the soft-lock hunt.

**`scripts-a38-m06-conversation-preempt-rearm.patch`** (applied after the M10
resend patch). Each site now registers `Monitor_Conversation` before
`Start_Conversation`, with the poke state set first. A start refused by a
playing key conversation (CON001/059/060) then reaches `Action_Complete`
synchronously with INTERRUPTED. Without a key conversation, Start never
touches the monitor array, so the ENDED path and its timing are unchanged.

| Script (staged line) | Fix |
|---|---|
| `M06_GDI_Prisoner` (:890-899, :906-912) | INTERRUPTED of 300607 re-arms `conversation`/`poked` and the indicator; key 3 is still granted at the poke, as in retail |
| `M06_Activate_Secret_Door` (:982-986, :994-998) | INTERRUPTED of 300608 clears `already_poked`, so the bookcase can be poked again and 608 and the stash stay reachable |
| `M06_Civ_Prisoner` (:1053-1062, :1081-1084, :1099-1104) | the existing INTERRUPTED branch clears `conversation`; the health drop and indicator-off are skipped when the start is refused; INTERRUPTED of 300123 re-shows the indicator |
| `M06_Resistance_Raider_DLS` (:3556-3561, :3567-3573) | INTERRUPTED of 100823 re-arms `talking` and the indicator |
| `M06_Assistance_Farmer_DLS` (:3595, :3636-3642, :3665-3670) | an INTERRUPTED raised inside Start (transient, unsaved `talk_starting`) runs the ENDED branch once: grenade launcher and the custom to zone 101357 |
| `M06_KaneHead` (:4361-4364, :4377-4379) | reorder only; the existing INTERRUPTED branches start CON064 and then remove the head |

Poke re-arms also fire on a later INTERRUPTED (player left range, AI state
change), as in the M05 Deadeye patch. Retail lost the objective in that case
too.

**Cosmetic 603/609** (same patch, `M06_Objective_Controller` :52, :63,
:247-250, :267-274). When 603 or 609 is added after its `,1` custom has
already arrived, it is marked accomplished at once. 609 reuses
`accomplished_609`. 603 adds `accomplished_603` on unused save id 3, which
older saves load as false.

**`combat-a38-mendoza-end-position-timeout.patch`** (applied after
`combat-a36-boss-waypath-release-guard.patch`; `__vita__` only).
`VITA_END_POS_TIMEOUT` = 15 s of `TimeManager::Get_Frame_Seconds` sim time
(`mendozabossgameobj.cpp:99`).

- In RUN_AFTER_SYDNEY (:3022-3030), Mendoza proceeds to TOY_WITH_SYDNEY as
  if within 2 m.
- In SYDNEY_STATE_BOLTING (:3158-3166), Sydney trips in place as if within
  5 m.
- Each fallback writes one `A3.8 Mendoza ...` log line, once per state entry.
- The counters reuse saved timers that are idle in those states. They count
  up from 0 (`OverallStateTimer` at RUN_AFTER Begin, `SydneyStateTimer` at
  BOLTING Begin; COWERING re-initialises the latter), so the save format is
  unchanged.
- Arrival before 15 s behaves exactly as in retail. The death sequence still
  snaps Mendoza to `MENDOZA_END_POS` (:1418).

Physical signature if a fallback fires: the log line above, then
TOY_WITH_SYDNEY, COWERING and the normal death sequence.

### Still deferred

- Runtime confirmation of all of the above, on Vita3K or hardware.
- Camera host after a load mid death sequence (visual).
- Unsaved `M06_Barracks_Patrol` arrays, collapse zones 5/6/7/9 and the
  flyover chain (cosmetic).
- The engine-level design choice (late `Register_Monitor` delivery) is still
  open. These per-script fixes do not depend on it.
