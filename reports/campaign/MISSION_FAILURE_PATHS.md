# Campaign mission-failure paths and Vita failure/restart trace

2026-10-07 source inspection only. No build, launch, Vita or emulator action.
Everything below is source evidence; physical failure-dialog behavior is not
claimed. Line numbers refer to `staging/scripts` at this commit.

## 1. Failure inventory (original scripts)

`Commands->Mission_Complete(false)` has 22 campaign call sites (Mission01..11,
MissionX0/M13). Two more are in `Test_GTH.cpp` (test scripts, not campaign).
M00, M02, M08 and M10 have no `Mission_Complete(false)`; their only terminal
failure is player death (`Star_Killed`). Objective-failed status alone never
ends a mission unless it is one of the ids listed below.

| Mission | File:line | Trigger | Kind |
|---|---|---|---|
| M00 tutorial | Mission00.cpp | none (success only, line 275) | death only |
| M01 | Mission01.cpp:8170 | `M01_DetentionPen_CivDeathMonitor::Killed` (civilian prisoner dies) | protect-target death |
| M01 | Mission01.cpp:8218 | `M01_DetentionPen_GDIDeathMonitor::Killed` | protect-target death |
| M01 | Mission01.cpp:8283 | `M01_DetentionPen_Evac_Controller01_JDG` custom `M01_CIVILIAN_KILLED_JDG`, first kill only (`deadPrisonerTally == 1`) | protect-target death (second call, idempotent) |
| M02 | Mission02.cpp:125 | objective param 2 sets FAILED only | objective only, no mission end |
| M03 | Mission03.cpp:6095 | `M03_CommCenter_Arrow::Timer_Expired(MISSION_FAIL)`, 4 s timer armed at 6125/6141 when Comm Center or Power Plant dies before the MCT is accessed | protect-target death + timer |
| M04 | Mission04.cpp:9157 | `M04_Firefight_Controller_JDG` custom param 11, sent 3 s after param 10 (prisoner killed, plays `00-n100e`) | protect-target death + delay |
| M05 | Mission05.cpp:315/319/323 | `M05_Objective_Controller` param 2 for objective ids 503, 501, 502 | objective-failed condition |
| M05 | Mission05.cpp:947 | `M05_DEAD6_Engineer2::Killed` (also sends 503/param 2) | protect-target death |
| M05 | Mission05.cpp:1448 | `M05_DEAD6_Grenadier::Killed` | protect-target death |
| M06 | Mission06.cpp:253 | `M06_Objective_Controller` param 2 for id 611 | objective-failed condition |
| M07 | Mission07.cpp:255/259/263/267 | `M07_Objective_Controller` param 2 for ids 701, 702, 709, 710 | objective-failed condition |
| M07 | Mission07.cpp:399 | `M07_Havoc_DLS::Killed` (escorted Havoc dies) | protect-target death |
| M08 | mission08.cpp:244 | objective param 2 sets FAILED only | objective only, no mission end |
| M09 | Mission09.cpp:313 | controller `Timer_Expired(40)`, 4 s after `MOBIUS_KILLED` (line 234) | protect-target death + timer |
| M09 | Mission09.cpp:993 | `M09_Mobius_Follow::Killed` (fails 901/902/903 first) | protect-target death |
| M09 | Mission09.cpp:3980 | `M09_Evac_Helicopter::Killed` | protect-target death |
| M10 | Mission10.cpp:556 | objective param 2 sets FAILED only | objective only, no mission end |
| M11 | Mission11.cpp:320 | `M11_Mission_Controller_JDG` custom `M11_END_MISSION_FAIL_JDG`, sent with 5 s delay at 9513 | critical objective + delay |
| M11 | Mission11.cpp:4904 | `M11_End_Mission_Switch_JDG::Killed` | protect-target death |
| M13 (MissionX0) | MissionX0.cpp:466 | `Havoc_Script::Killed` | protect-target death |

Not traced: which scripts send param 2 for M05 ids 501/502, M06 611 and M07
701/702/709/710. They route through the objective controllers above.

Player death is separate: `ScriptableGameObj` death calls
`CombatManager::Star_Killed()` -> misc handler -> `cGod::Star_Killed()`.

All failure callbacks are `CombatManager::Mission_Complete(false)`. A mission
may call it repeatedly (M01 and M05 do); the first terminal result is kept.

## 2. What the original does on failure

- `CombatGameMiscHandlerClass::Mission_Complete(false)` -> `cGod::Mission_Failed()`
  (combatgmode.cpp:1722), only when `IS_MISSION`.
- `cGod::Mission_Failed()` (god.cpp:638): only when `State == SINGLE_RUNNING`,
  sets `SINGLE_DEAD`, opens `FailedOptionsPopupClass` (Restart / Load / Main Menu).
- `cGod::Star_Killed()` (god.cpp:534): `SINGLE_RUNNING` -> `SINGLE_DEAD`, stores
  death inventory, opens `DeathOptionsPopupClass` (Restart / Load / Quit).
- Both popups flush the WWAudio playlist, activate the Menu mode and suspend Combat.
- Success is different: the original sets `PendingCampaignContinue`, consumed at
  the end of the same `Think()` (combatgmode.cpp:1601).

## 3. What the Vita runtime does

Layers, in order:

1. `A31VitaCombatMiscHandler::Mission_Complete` (a31_gameplay_boundary.cpp:417)
   records the first result in `A31MissionCompletionLatch` and, for the native
   frontend build, calls `cGod::Mission_Failed()` directly when `!success`.
   `Star_Killed` does the same with `cGod::Star_Killed()`.
2. a31_vita_runtime.cpp:6166 observes the latch after the original simulation.
   For `IS_MISSION && !succeeded` it calls `cGod::Mission_Failed()` again. This is
   redundant but benign: the `SINGLE_RUNNING` guard makes the second call a no-op
   (and covers a callback fired during reload/start-script creation, before RUNNING).
3. a31_vita_runtime.cpp:6236: while Combat is suspended and
   (`star_killed_observed` or failed completion) with a live dialog, the runtime
   enters `Run_Original_Gameplay_Pause_Menu(..., death_dialog=true)`, a WWUI pump
   over the original popup. START does not bypass the dialog.
4. Dialog outcomes, all through original popup code:
   - Restart: `Continue_Game()` + `cGod::Request_Restart()` (deferred; the popup
     must not unload the world the native frame retains). The pump ends because
     Combat is active again; the runtime sees `Has_Pending_Restart()` and does
     not queue an exit.
   - Main Menu / Quit: `GameInitMgrClass::Set_Needs_Game_Exit(true)`; the runtime
     consumes it as the original pending-exit and returns to the frontend.
   - Load: `cGod::Load_Game()` keeps Combat suspended and opens the original load
     menu; a started load becomes `reload_requested` and goes through session
     cleanup. Cancelling the load menu sets `Needs_Game_Exit` (returns to the menu),
     which matches the original, where `Load_Game` ends the game.
   - Popup closed with Combat inactive: ends the session.
5. Success is observed from the same latch and runs
   `Run_Original_Campaign_Intermission` (original `CampaignManager::Continue`).
   If a death occurs in the same frame as a success callback, success wins. That
   matches the original, where `Think()` consumes `PendingCampaignContinue` after
   the death popup is created. No change is needed.
6. Saves: manual/quick/autosave reject `SINGLE_DEAD` (KNOWN_GAPS), so a failed
   mission cannot write an ambiguous terminal save.

## 4. Restart-from-failure verification (source trace)

Block at a31_vita_runtime.cpp:5721-5920 (`campaign_restart`):

- Preconditions: `IS_MISSION`, not a multiplayer client, `Has_Pending_Restart()`,
  Combat active, `The_Game()` non-null. Archive name is re-resolved from
  `selected_archive` with `A4_Frontend_Resolve_Single_Player_Archive`.
  `selected_archive` is already the resolved `Mxx.mix`, so the `!is_save` check is
  always true for a restart. A map change is rejected into the normal
  failed-load recovery (deferred frontend route owns map changes).
- Teardown before reload: input route gameplay-inactive, `Input::Flush`,
  `DialogMgrClass::Flush_Dialogs`, `TextWindowClass::Shutdown`,
  `A35_Vita_Clear_Prepared_Render_Objs()`.
- Reload: `cGod::Restart()` -> `Core_Restart()` (`Core_Shutdown`, then
  `Load_Level` using `CombatManager::Get_Last_LSD_Name()` converted `.LSD`->`.MIX`)
  -> new `Create_Commando` + start script.
- Same level: `LastLSDName` is set by `Pre_Load_Game` even for save/checkpoint
  loads, so a restart after a checkpoint load reloads the level from its start,
  as the original does. The MIX factory is not swapped (map unchanged).
- Difficulty: `CombatManager::DifficultyLevel` is a static that `Core_Shutdown`
  and `Load_Level` do not reset; only campaign start/replay and save load write it.
  `Create_Commando` re-derives player max health from it (200/100/75).
- Campaign state: failure never calls `CampaignManager::Continue`, so the
  campaign State/BackdropIndex chunk is untouched. The autosave request is made
  only by a campaign Level directive, not by restart.
- Inventory: `Create_Commando` restores start-of-level inventory when
  `Remember_Inventory()`; player stats reset in `cGod::Restart`.
- Completion state: `Load_Level` re-arms the native observer
  (`A31_Interactive_Restart_Mission_Completion_Observation` resets the latch,
  reinstalls the handler). After the reload the runtime clears
  `result.mission_completion_observed/succeeded/star_killed_observed`,
  `mission_progress_recorded`, `last_render_trace`, tutorial gate and
  `world_first_render_pending`; repeated failures can therefore re-enter the dialog.
- Cinematic freeze and camera host: released by the original unload
  (combat.cpp:623), so a failure during a cinematic does not leave a frozen world.
- Failure inside the reload (`A35_Level_Load_Get_Failure()` set) goes through
  `Queue_Local_Load_Failure_Recovery` and session cleanup, never a half-built world.

Conclusion: no defect found that stops a restart from returning to the same
level with the same difficulty and unchanged campaign state.

## 5. Gaps and unverified items (no code change made)

1. Prepared-object prewarm is not repeated on restart (performance, not
   correctness). M01 and M13 retain cinematic render objects during the initial
   Vita load (`A35_Vita_Prepare_Render_Obj`, runtime ~5195-5330). Restart clears
   them (`A35_Vita_Clear_Prepared_Render_Objs`) and the original `Load_Level`
   path does not re-prepare them or re-run `Warm_Original_Campaign_Referenced_Textures`.
   `PhysClass` (wwphys/phys.cpp:214) falls back to `Create_Render_Obj` when
   `A35_Vita_Take_Prepared_Render_Obj` returns NULL, so M01/M13 cinematics after a
   failure-restart load models on demand and may hitch. Fixing means lifting the
   M01/M13 model lists out of the load block into a reusable function; deferred
   as larger than a minimal fix and needing a hardware frame-time comparison.
2. Theoretical soft-lock if a failure popup is never created. The dialog branch
   needs `Get_Dialog_Count() > 0`. Combat is suspended only by the popup's
   `On_Init_Dialog`, so a failed popup creation leaves Combat running, not stuck.
   No exit guard was added because dialog registration timing relative to this
   check cannot be proven without running it.
3. Physical failure-dialog evidence (Restart/Load/Menu choices, audio flush,
   restart timing on M01/M05/M07/M09/M11) was not located in this inventory and
   remains a hardware item. Candidate scripted tests: M01 civilian kill, M03
   Comm Center kill before MCT, M05 Engineer2 death, M07 Havoc death, M09 Mobius
   death, M11 End_Mission_Switch death, M13 Havoc death.
4. Objective-only failures (M02, M08, M10 and non-fatal ids in M05/M06/M07/M11)
   can leave an unwinnable mission with no failure dialog. This is original
   retail behavior and is intentionally preserved.
5. Existing guard: `tools/test_mission_completion_contract.py` (6 tests, pass)
   covers latch first-result semantics and the runtime observation order.
