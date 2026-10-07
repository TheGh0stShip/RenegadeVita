# M11 readiness (final campaign mission)

Evidence class: source inspection of `staging/scripts/Mission11.cpp` plus
read-only retail-data checks against the Vita3K copy of the unchanged retail
`Data/`. No build, no Vita3K launch, no physical run. Physical completion is
not established by this report.

M11 is the last `Level` entry in retail `campaign.ini` (M13, then M01..M11).

## Objective chain to `Mission_Complete(true)`

Mission controller: `M11_Mission_Controller_JDG` (`Mission11.cpp:196`).
All line numbers refer to `staging/scripts/Mission11.cpp`.

1. Controller `Created` sends `M11_ATTACH_HAVOCS_SCRIPT_JDG` to itself (219),
   which starts `M11_Level_Intro_Conversation` once `STAR` exists, else
   retries every second (276-292).
2. Intro conversation ended -> add objective 2 "locate Sydney" (225-229,
   348-355) and play `M11_Level_Intro_Conversation02` (295-308). That
   conversation ended -> add objective 1 "infiltrate lower levels" (232-235,
   323-331).
3. `M11_End_First_Objective_Zone_JDG` (4798) on player entry -> objective 1
   accomplished (4804 -> 335-345) and EVA "Sydney pinged" conversation, whose
   end sets the objective-2 HUD marker (237-240, 358-372).
4. `M11_Start_Third_Objective_Zone_JDG` (4817) -> conversation
   `M11_Add_Third_Objective_Conversation` ended -> objective 3 "power core"
   (4853 -> 386-397). Power-core entry zone -> objective 3 accomplished
   (5512 -> 402-411).
5. Real Sydney (`M11_Sydney_Script_JDG`, 9368) initial conversation ended ->
   objective 2 accomplished (9800 -> 376-380), which queues objective 4
   "protect Sydney" (414-428). Sydney walks waypaths to rally zones and
   elevators.
6. Objective 5 "sabotage nuke": EVA nuke conversation is started either by
   `M11_Start_Fifth_Objective_Zone_JDG` (4868) or Sydney finishing waypath 2
   (9953); its end adds objective 5 with the end-switch marker (243-258,
   439-445).
7. Sydney reaches the missile switch (waypath 6, 9999-10011), plays the
   console attack/animation, then `M11_End_Mission_Conversation` (10014-10026).
   Conversation ended -> `Action_Play_Animation("S_A_HUMAN.H_A_CON2")` with
   action `M01_DOING_ANIMATION_02_JDG` (9822-9826). Animation complete ->
   `M11_END_MISSION_PASS_JDG` to the controller (10029-10032) ->
   `Commands->Mission_Complete(true)` (312-315).

`M11_END_FORTH_OBJECTIVE_JDG` / `M11_END_FIFTH_OBJECTIVE_JDG` are never sent
by any released script except the controller's own unreachable branch; the
pass path at step 7 does not depend on them. This is original behavior.

Failure routes: Sydney `Killed` -> `M11_END_MISSION_FAIL_JDG` (9513 ->
318-321); end switch `Killed` -> `Mission_Complete(false)` (4904).

## Checks performed

| Item | Result |
| --- | --- |
| Live `Attach_Script` names in Mission11.cpp | 32/32 resolve to a `DECLARE_SCRIPT` in linked script sources. The only unresolved literal, `M11_Havocs_Script_JDG`, is commented out (280). |
| Script registry linkage | `Mission11.cpp` is compiled directly into the executable (`CMakeLists.txt` campaign list, 13-unit gate), not a static archive, so its static `ScriptRegistrant`s are retained. |
| Conversations | 26 literal `Create_Conversation` names; `tools.audit_mission_conversations --map M11.mix` reports 0 unlocated names (27 level conversations in `m11.ldd`, 3,606 global). |
| Conversation audio dependence | Remark timing comes from `SoldierGameObj::Say_Dynamic_Dialogue` (`staging/combat/soldier.cpp:3563`): 2.0 s default when no sound is created, otherwise the sound duration. A missing or rejected WAV shortens or defaults the remark; the conversation still reaches `ACTION_COMPLETE_CONVERSATION_ENDED` (`activeconversation.cpp:443-456, 553`). The one M11 remark that cites a flagged WAV (ALL_ARCHIVE_WAVE_SWEEP) cannot stall the chain. All gating conversations use max distance 1000, so audience-distance interruption is not a practical risk. |
| Cinematics | All 12 control files exist: `X11A_Flyover_01..04`, `X11D_C130Troopdrop` in `always.dat`; `X11D_Repel_Part1/1b/2/3/4`, `X11M_MIDTRO`, `X11N_MIDTRO` in `M11.mix`. None gates the pass path. |
| Script-spawned presets | 18 literal `Create_Object` matches (SCRIPT_SPAWN_PRESETS counts 17, all outside the cinematic warm set and carried in `kM11ScriptSpawnPresets`). Existence of each preset in `objects.ddb` was not re-verified here. |
| Final animation | `h_a_con2.w3d` present in `always.dat`. |
| Boss classes | Petrova (`M11_MUTANT_PETROVA_JDG` 300303) is a script-owned soldier (`M11_Petrova_Script_JDG`, 6226). `m11.lsd`/`m11.ldd` contain no Raveshaw/Mendoza boss object chunks (IDs 262473-262476, 0 hits). Raveshaw's owner script is `M08_Raveshaw`. `raveshawbossgameobj.cpp` is still linked for full-port builds via `cmake/A35MultiplayerBuildingSources.cmake`. |
| Petrova dependence | Her `Killed` drops `Level_03_Keycard` with `M11_Level03Key_Script_JDG` (6305-6314) and removes the stealth controller. Killing her is needed for route access, not for an objective event. |
| Missing fodder scripts | `M11_ObeliskWall_FodderGuy01/02_JDG` and `M11_TempleRoof_FodderGuy02_JDG` (spawners 100581/100582/100586) are referenced only by retail spawner data. No released script reads those spawner IDs or the fodder controller 100588, and the only senders to the mission controller are the eight sites cited above (4804, 4853, 4868, 5512, 9513, 9800, 9953, 10031). Missing scripts therefore cannot gate any objective; the soldiers spawn without per-unit scripts (graceful NULL path, KNOWN_GAPS). |

## Blockers found and fixed

None. Within the timebox, no Vita-specific source defect was found on the M11
objective chain, so no code changed.

## Residual risks (not source-closable)

- Sydney escort pathfinding over elevators and waypaths (`ACTION_COMPLETE_PATH_BAD_*`
  retry branches, 9831-9870) depends on original pathfind data; a stall there is
  the most likely physical failure.
- The pass requires `Action_Play_Animation` to complete normally on Sydney.
  An interrupted action (for example damage reaction) would leave the mission
  waiting; this is original behavior.
- Petrova fight (stealth reinforcements, taunts, midtro gating of damage at
  6286-6302) is unverified on hardware.
- Score screen, end movie and the end-of-campaign return after the last
  `campaign.ini` entry are separate frontend gates (DEV136 table: "Finale open").
- Memory high-water in M11 with cinematic prewarm is unmeasured.

## Physical test route

1. Load M11 from a campaign save or the level select. Confirm the intro
   conversations play and objectives 1 and 2 appear.
2. Reach the museum (objective 1 done), the power-core entry conversation
   (objective 3 added) and the power core (objective 3 done).
3. Kill Petrova; confirm the Level 3 keycard drops and opens the route.
4. Reach Sydney; after her conversation confirm objective 2 done, objective 4
   added, and that she follows waypaths through every elevator.
5. Confirm the EVA nuke conversation adds objective 5 with the switch marker.
6. Keep Sydney alive to the missile switch; confirm the end conversation, her
   animation, and then mission success, score screen and the campaign end flow.
7. Pull `ux0:data/renegade/user/logs/` and the flight recorder; check for
   "native provider missing script" lines (expect exactly the three fodder
   names) and conversation transition records for `M11_End_Mission_Conversation`.

## Full audit (2026-10-07)

Evidence class: host source review of `staging/scripts/Mission11.cpp` and a
read-only check of the unchanged retail `Data/` (Vita3K copy). Tools:
`tools.audit_mission_content_bindings --map M11.mix` (receipt under ignored
`build/`), `reports/generated/sweeps/live_script_{bindings,parameters}.json`,
`missing_cinematic_names.json`, `renegade_cinematic_dependency_scan.scan`,
`check_campaign_chain.py`, plus throwaway scanners for event receivers, timer
ids, waypath ids and literal asset names. Only `arm-vita-eabi-g++
-fsyntax-only` was run on the patched unit. Nothing here is a runtime or
visual result.

### Results by area

| Area | Result |
| --- | --- |
| Level script bindings | 517 bindings (465 persisted, 44 definition, 8 spawner). 514 are registered. The 3 unregistered names are the known fodder spawner scripts (100581/100582/100586), unchanged from retail. Parameter shape: 67 equal-count, 447 `excess_values` where the level supplies one empty value to a `""` descriptor (harmless), 0 `fewer_values`. |
| Custom events | 453 `Send_Custom_Event` sites in 171 scripts. Each type/param has a matching `Custom` comparison in the unit, except `M00_CUSTOM_POWERUP_GRANT_DISABLE` (179), which is received by the shared `M00_Soldier_Powerup_Disable`. Cinematic `send_custom` targets (X11M: 101449 p0, 106230 p0/p1; X11N: 101607, 157366, 101606, 100697 p0, 101449 p1) all have handlers. |
| Timers | 28 `Start_Timer` sites. Handlers that do not compare `timer_id` accept every id. No timer lacks a handler. |
| Hard-coded object IDs | 76 literal and 51 named `Find_Object` IDs. Not serialized: 100012 (`:406`, the power-core zone cleanup), `M11_MUSEUM_GUARD_04/06` (100259/100261). All three lookups are NULL-guarded, so they are a retail no-op. `Enable_Spawner` 102421-102426 (power-core pickups) have no spawner. `Spawner_Enable` loops over existing spawners, so this is a no-op. Missile lifts 167620-167623 and doors 1300001123/1124 are present in `m11.lsd`. |
| Waypaths | All 67 `WaypathID`/`WaypointStartID`/`WaypointEndID` values, including Petrova's 21-route table and Sydney's 4 lift legs (105199, 105205, 104839, 104845, 104850), are present in the M11 level data. This is a byte-presence check only. |
| Presets/sounds/models | Content-binding closure: 0 missing literal presets and 0 missing cinematic texts. 215 string-array, `Set_Model`, explosion and weapon literals resolve. Retail-identical miss: Petrova taunt `M00GCTK_KIOV0004I1MBPT_SND` (`:7569`), where `Create_Sound` returns 0 and nothing plays. Sound twiddlers `M11_Exterior_{NOD,GDI}Troops_Twiddler_JDG` include definition IDs that are absent from `objects.ddb` (2539, 3323-3325, 3330, 3339, 3349, 3379). `TwiddlerClass::Twiddle` then returns NULL and `Create_Sound` skips the sound. The weapon eject and muzzle-flash phys IDs that are absent are global and not M11-specific. |
| Animations | All 12 cinematics resolve their models, animations and presets across `always.dat`, `Always2.dat` and `M11.mix`. Retail-identical miss: `X11C_BN_Sydney.X11C_SYD_A..D` (`:6955-6976`). The archive registers these as `X11C_BN_SYDNEY.X11C_BN_SYD_*`, so `Get_HAnim` returns NULL and the torture-bone helper does not animate. Sydney's own `S_B_HUMAN.H_B_X11C_SYD_*` loop, which drives `Animation_Complete`, does resolve. |
| Strings/conversations | 0 unresolved objective or HUD strings (`OBJECTIVE_TEXT_READINESS.md`). 0 unlocated conversations (earlier section). `ShieldKevlar` and `Blamo` are in `armor.ini`. |
| Random/array bounds | Every `Get_Random_Int(0,N)` index is within its array (`CRandom::Get_Int` is `[min,max)`). Each `while (random == last)` loop draws from a range of more than one value, so it terminates. `flyovers[last]` wraps at 4. Petrova's `_waypaths[CurrentLocation]` is only reached after `START_ACTING` sets `SOUTH0`. |
| Pass/end chain | Re-verified from the earlier section. Mid-mission, Sydney appears only through X11N `send_custom 101449 p1` (frame 494), which follows the Level 3 keycard pickup. The port has no in-engine cinematic skip that could drop that command. `check_campaign_chain.py`: 0 failures, state 35 END goes to `Display_End_Game_Menu`. `Movies/R_Finale.BIK` is present. |
| Port patches on M11 | `scripts-a36-m11-save-variable-ids.patch` is correct: Petrova taunt ids are now 1/2/3. The shared action watchdog, elevator and pathfinding patches are reviewed in `ESCORT_PATHING_REVIEW.md` and `ELEVATORS.md`. |

### Defect fixed

- **Uninitialized conversation-ID members on the objective chain** (medium,
  completion-blocking if it occurred). `M11_Sydney_Script_JDG::Created`
  leaves `sydney_conv01`, `sydney_damaged_conv01..03` and `missionEndConv`
  uninitialized (`new T` default-init). When `M11_End_Mission_Conversation`
  ends, `Action_Complete` tests the damaged-conversation IDs before
  `missionEndConv`. If Sydney was never hurt, a stale heap value equal to the
  end conversation's ID would take the damage branch. The `H_A_CON2`
  animation would then never play and `M11_END_MISSION_PASS_JDG` would never
  be sent. On Vita, 12 in-process campaign sessions reuse newlib heap memory
  that can hold earlier conversation IDs (which start at 1000 in every
  level). The controller's 4 conversation members have the same pattern, and
  could misroute the objective-5 HUD step. Fix:
  `scripts-a36-m11-conversation-id-init.patch` zeroes these 9 members in
  `Created`. The controller's members are zeroed before its synchronous
  self-custom. Active conversation IDs are never 0, so no original route
  changes. Staged with zero fuzz (526 ordered patches, inventory PASS);
  `-fsyntax-only` passes.

### Deferred

- The same uninitialized `int` conversation-member pattern exists in
  `M11_Barracks_Scientist_JDG`, `..._TechnicianConversation_Blackhand_JDG`,
  `..._MutantConversationGuy_01_JDG`, `M11_Start_Third_Objective_Zone_JDG`
  and `M11_Temple_Hologram_Controller_JDG`, and across other missions.
  A single value-initialising `new T()` in `ScriptRegistrant::Create` would
  close it everywhere. That changes shared script plumbing, so it was not
  done in this M11-scoped unit.
- `M11_Flyover_Contoller_JDG` starts a new `Test_Cinematic` every 10 s for the
  whole mission (original). Its memory and object churn on Vita is unmeasured.
- Fodder spawner scripts, `X11C_BN_Sydney` bone animations, the
  `M00GCTK_KIOV0004I1MBPT_SND` taunt and missing twiddler choices are
  retail-identical misses. Each one degrades without crashing.

## Soft-lock hunt (2026-10-07)

Evidence class: staged-source review of `Mission11.cpp`, `activeconversation.cpp`,
`conversationmgr.cpp`, `action.cpp`, `scriptcommands.cpp`, `scriptablegameobj.cpp`,
plus a read-only parse of `m11.ldd` (`M11.mix`, Vita3K retail copy) for the
`ConversationClass` key flag. One `arm-vita-eabi-g++ -fsyntax-only` of the patched
unit (exit 0, no new warnings). No build, emulator or device run. Line numbers are
staged `Mission11.cpp` after the patches below.

### Key conversations (m11.ldd)

27 level conversations, 3 key: `M11_Initial_Sydney_Conversation_JDG`,
`M11_Kane_Regarding_Seth_Conversation` (zone 101103, :5267) and
`M11_KanesRoom_Kane_Conversation` (:5955). Every completion-gating conversation other
than the initial Sydney one is not key, including `M11_End_Mission_Conversation`.
Delivery rules that matter here: `Start_Conversation` stops a non-key conversation with
INTERRUPTED when any key conversation is active, before the script's
`Monitor_Conversation`, so nobody is told. A newer key conversation that preempts a
playing one in `ConversationMgrClass::Think` uses the default ENDED reason, so it
advances the chain early instead of blocking it. Sydney's and the controller's
`Action_Complete` act only on ENDED.

### Issues

| # | Site | Reachability | Severity | Status |
| --- | --- | --- | --- | --- |
| 1 | End conversation started while a Kane key conversation plays (:9805 before the fix) is stopped inside `Start_Conversation`. No H_A_CON2, no `M11_END_MISSION_PASS_JDG`. | Low. The player must trigger Seth's or Kane's room zone in the seconds when Sydney finishes the console animation. Retail behaves the same. | Completion blocker (permanent). | Fixed, patch A. |
| 2 | `M11_Silo_ElevatorZone01_Top_JDG` (100705, :10300) never resets its flags and is not one-shot. Any later STAR entry re-sends `M01_MODIFY_YOUR_ACTION_JDG` and rewinds Sydney to the elevator-2 leg at priority 100. That cancels the switch walk, the console attack/animation or the H_A_CON2 action (LOW_PRIORITY is ignored). The bottom lift zones are already destroyed, so she cannot come back up. Top zones 02-04 re-send on any Sydney re-entry in the same way. | Low to moderate. The player has to drop back to silo level 2 and walk into the zone after the escort has moved on. | Completion blocker. | Fixed, patch B. |
| 3 | Cryo controller `M01_SPAWNER_SPAWN_PLEASE_JDG` (:8266) retries with a synchronous `Send_Custom_Event(...,0)`. A caged mutant killed outright (`Killed` with `freed==false`, :8548) sends no death custom, so `deadMutantCount` undercounts. Once all 15 cages are empty below 15, the next spawn request recurses without end (stack overflow). | Low. Needs one-hit kills of caged mutants; the heal-on-`Damaged` handler only stops chip damage. | Crash (mission blocker). | Fixed, patch C. |
| 4 | Rally legs (`M01_WALKING_WAYPATH_01..04`) leave `sydneys_location` at IDLE, so the PATH_BAD/NO_PROGRESS retry branches ignore them. A failed rally-leg solve leaves Sydney standing. Blocked movement does not fail a goto (`Is_Soldier_Blocked` only waits). | Pathfind-data dependent; same data as retail. | Blocker if it occurs. | Deferred (needs hardware evidence; a retry would change original AI). |
| 5 | Rally zones need STAR to *enter* after Sydney arrives. If the player already stands inside, nothing happens until they step out and back in. | Common, recoverable by the player. | Confusing, not a lock. | Original; not changed. |
| 6 | Real Sydney appears only through X11N `send_custom 101449 p1` (frame 494). It needs the Level 3 keycard (`CUSTOM_EVENT_POWERUP_GRANTED`, always granted) and the `Test_Cinematic` dispatch. Custom timers, actions and Test_Cinematic state are saved. | Normal path. | Blocker only if the cinematic aborts. | Covered by the existing cinematic work; not re-verified here. |
| 7 | Elevator ENTERING has no timeout (`ESCORT_PATHING_REVIEW.md` risk 5). This applies if any Sydney leg crosses an ElevatorPhys. Her silo lifts are StaticAnimPhys driven by `M11_Silo_ElevatorZone0n_JDG` polling every 2 s. | Low FPS only. | Possible stall. | Deferred, as recorded there. |

Other checks: the console attack and the first H_A_CON2 share action id
`M01_DOING_ANIMATION_01_JDG`, but the replaced attack completes with LOW_PRIORITY, so
the end conversation is created once. The two-orator end conversation does not take
over Sydney's action (`OratorList.Count() <= 2`), and damage conversations have one
orator. The Play_Animation stall watchdog guarantees H_A_CON2 completes. Audience distance
is 1000 m. Save/load: Sydney's state, active conversations with monitors, the custom
timers (`scriptablegameobj.cpp` CHUNKID_CUSTOM_TIMER) and the actions are all
persisted. Death or restart reloads the level, and Sydney's `Killed` sends the
original fail custom.

### Fixes (scripts-a38, registered after `scripts-a36-m11-conversation-id-init`)

- **A `scripts-a38-m11-end-conversation-replay.patch`**: monitor the end conversation
  before `Start_Conversation`, so an immediate key-preemption stop reaches Sydney. On
  INTERRUPTED/UNABLE_TO_INIT for `missionEndConv` (and Sydney alive), clear it and
  replay the same conversation 2 s later through `M01_MODIFY_YOUR_ACTION_06_JDG`.
  Guarded by `missionEndConv == 0`, so it is idempotent, and the state is saved. On the
  normal path the only difference is the registration order before the first `Think`.
- **B `scripts-a38-m11-sydney-route-monotonic.patch`**: Sydney ignores a route custom
  for a stage she has already passed (`WAYPATH_05/07` above ELEVATOR01,
  `MODIFY_YOUR_ACTION`/`_02`/`_03` above ELEVATOR02/03/04). She ignores `_04` once the
  new saved flag `reachedMissileSwitch` (id 14, set when the switch walk completes) is
  true. Her own retries re-send the current stage, which is still accepted. Old saves
  load the flag as false (value-initialised factory).
- **C `scripts-a38-m11-cryo-spawn-recursion-bound.patch`**: a spawn request is acted on
  only while at least one caged mutant still resolves. On the normal path a caged
  mutant always remains, so behaviour is unchanged.

Staging: 546 ordered patches, inventory PASS, zero fuzz; only `Mission11.cpp`
changes.

### Physical signature

The flight recorder should show a conversation-monitor kind-3 call for
`M11_End_Mission_Conversation` with reason ENDED, then the H_A_CON2 action completion,
then `Mission_Complete(true)`. A kind-3 record with reason INTERRUPTED, followed about
2 s later by a second creation of the same conversation, means patch A fired.

## Follow-up fixes (2026-10-07)

Evidence class: staged-source change plus static checks. One
`arm-vita-eabi-g++ -fsyntax-only` of the patched unit passed (exit 0, 175
warnings, the same count as the unpatched unit). Staging applied 573 ordered
patches with zero fuzz and the inventory passed. The host unittests
`test_audit_conversation_gated_objectives`, `test_m10_objective_conversation_resend`,
`test_objective_state_lifecycle`, `test_audit_campaign_source_surface`,
`test_audit_campaign_script_closure` and `test_mission_conversations` pass.
`tools.audit_conversation_gated_objectives --mission M11` was re-run with the
pre-change staged `Mission11.cpp` as baseline. M11 now has 0 AT RISK (was 4),
0 REVIEW (was 1) and 7 FIXED (was 2). No build, emulator or device run.
Line numbers refer to the staged `Mission11.cpp`.

### Engine check

The controller's `Action_Complete` acted only on ENDED. A key-conversation stop
inside `Start_Conversation` arrives as INTERRUPTED (`activeconversation.cpp:400`),
and an initialisation timeout arrives as UNABLE_TO_INIT (`:464`). So, for these
ids only, the switch now also accepts both reasons. `Release_Level` also sends
INTERRUPTED to live monitors (`Reset_Active_Conversations`, `level.cpp:58`)
before `Destroy_All`. The replay therefore runs from a 1 s script timer, which
dies with the outgoing level. This is the same choice as the M09 intro fix.

### Fixes

| Issue | Fix | Patch, site |
| --- | --- | --- |
| `M11_Level_Intro_Conversation` stopped at start: objective 2, the second intro and floor-1 security acting never come. | Monitor before Start. On INTERRUPTED/UNABLE_TO_INIT (or create id < 0), a 1 s timer runs the original ENDED branch (`Deliver_Intro_Conversation`) once. | `scripts-a38-m11-objective-conversation-preemption.patch`: start :404, delivery :236, interrupt case :358, timer :287 |
| `M11_Level_Intro_Conversation02` stopped at start: objective 1 is never added. | Same pattern (`Deliver_Intro_Conversation02`). The museum guard inside `M11_ADD_FIRST_OBJECTIVE_JDG` is unchanged. | same patch: start :428, delivery :244 |
| REVIEW `M11_EVA_SydneyPinged_Conversation`: losing it loses only the objective-2 HUD marker refresh (`M11_ADD_SECOND_OBJECTIVE_POG_JDG`). That is cosmetic, not a lock. | Same pattern, for consistency. | same patch: start :472, delivery :251 |
| `M11_EVA_Activate_Nuke_Conversation` stopped at start: objective 5 and the switch blip are never added. Both senders (fifth-objective zone, Sydney leg 2) can overlap Sydney's key conversation. | Same pattern (`Deliver_EVA_Nuke_Conversation`). A second `M11_ADD_FIFTH_OBJECTIVE_JDG` still creates a second conversation as in retail. Only the first delivery acts (retail repeated a duplicate `Add_Objective`, which is rejected). | same patch: start :578, delivery :258 |
| `M11_Add_Third_Objective_Conversation` (zone) stopped at start: objective 3 is never added and the zone is never removed. | Monitor before Start. INTERRUPTED/UNABLE_TO_INIT (or id < 0) starts a 1 s zone timer for the original branch: send `M11_ADD_THIRD_OBJECTIVE_JDG`, then destroy the zone. Saved `objectiveSent` (id 3); the conversation id is zeroed in `Created`. | same patch: zone :4956, start :5013, delivery :4981, interrupt case :5037 |
| Soft-lock #4: a failed rally leg (`WAYPATH_01..04`) leaves Sydney at IDLE with no retry. | Each rally goto records its action id and waypath (start/end). PATH_BAD_START, PATH_BAD_DEST or MOVE_NO_PROGRESS_MADE for that leg, while she is IDLE and alive, re-issues the same goto after 2 s, at most 3 times per leg. Each retry and the limit leave a log line. The timer id is the leg's action id, so a stale retry does nothing. Saved ids 15-19. | `scripts-a38-m11-rally-leg-retry.patch`: record :10032, :10060, :10245; failure :10325, :10360, :10394; helpers :9791-9822 |
| Soft-lock #5: a rally zone fires only on player entry after Sydney arrives. | `Entered`/`Exited` track STAR (saved id 2). When Sydney's arrival custom finds STAR inside, a 0.5 s timer runs the original `Entered` branch for STAR if the player is still inside. A saved `fired` flag (id 3) makes it run once whichever way it is reached. | `scripts-a38-m11-rally-zone-recheck.patch`: zones 01 :9146, 02 :9222, 03 :9298, 03b :9384 |

On the normal path these changes add only the monitor-before-start ordering,
the leg record and the presence flag. Conversation content, objective timing
and routes are unchanged.

### Physical signature

If these paths fire, `ux0:data/renegade/user/logs/` should show:
- `A4 M11 controller: <conversation> stopped before ending; objective step deferred 1 s`
- `A4 M11 third-objective zone: ... deferred 1 s`
- `A4 M11 Sydney rally leg <action> waypath <id> failed (reason <r>); retry <n>/3 in 2 s`, or `... retry limit 3 reached`
- `A4 M11 M11_Sydney_Rally_Zone_0x_JDG: player already inside when Sydney arrived; firing rally`

Leaving the level while one of the controller conversations is playing also
prints the controller line. That is harmless, because the timer dies with the
level.

### Deferred

- `CONVERSATION_GATED_OBJECTIVES.md` was not regenerated here, because that
  needs the canonical baseline staging. The M11 re-run above is the evidence.
- A rally path that fails deterministically fails 3 times. Sydney then stays
  put as in retail, and a breadcrumb records it. Switching legs 2/3 to their
  alternate route was not done, because it changes which rally zone is armed.
- A save made before this patch loads `starInside` as false. If STAR is
  already in the restored zone `InsideList`, the re-check cannot fire until the
  player steps out and back in, which is retail behaviour.
- Soft-lock #7 (elevator ENTERING timeout) is unchanged.
