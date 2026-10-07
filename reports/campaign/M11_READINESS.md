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
