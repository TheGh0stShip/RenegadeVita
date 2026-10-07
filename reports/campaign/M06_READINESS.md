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
