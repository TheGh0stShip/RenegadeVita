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
