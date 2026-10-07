# Campaign fail-and-retry flow (source trace, 2026-10-07)

Evidence class: host source review, ARM `-fsyntax-only` of
`port/platform/vita/a31_vita_runtime.cpp` (exit 0, pre-existing warnings only)
and source-contract tests (`python3 tools/test_fail_and_retry_flow.py`, 14
tests). Nothing was built, linked, emulated or run on a Vita. No physical or
Vita3K evidence of any failure popup exists. This extends
[MISSION_FAILURE_PATHS.md](MISSION_FAILURE_PATHS.md), which inventories the 22
`Mission_Complete(false)` sites and the Vita observer order; that material is
not repeated here.

Line numbers: `R` = `port/platform/vita/a31_vita_runtime.cpp`, `G` =
`port/platform/a31_gameplay_boundary.cpp`, others are under `staging/`.

## Verdict

No soft-lock found: every terminal path reaches a popup or session teardown
that the Vita buttons can drive. One state leak was found and fixed (time
scale after a boss slow-motion death). Everything else already resets, or is
original behavior that is deliberately preserved. Hardware still has to prove
all of it.

## The common path

1. Producer. Either `Mission_Complete(false)` (script) or the star soldier's
   `Set_Delete_Pending` (scriptablegameobj.cpp:442, after the death animation
   and `CORPSE_PERSIST_TIME`, soldier.cpp:2631) calls the Vita misc handler
   (G:417-431). It records the first result in the latch and calls
   `cGod::Mission_Failed` (god.cpp:638) or `cGod::Star_Killed` (god.cpp:534).
   Both are gated on `SINGLE_RUNNING`, so a second producer in the same life is
   a no-op.
2. The popup (`DeathOptionsPopupClass` / `FailedOptionsPopupClass`,
   dialogtests.cpp:1586-1730) flushes the playlist, activates Menu and
   suspends Combat in `On_Init_Dialog`.
3. R:6514-6545: Combat suspended, terminal event latched and `Get_Dialog_Count()
   > 0` enters `Run_Original_Gameplay_Pause_Menu(..., true)` (R:2938), a WWUI
   pump with its own `TimeManager`, input and render calls.
4. Outcome. Restart: popup calls `Continue_Game` + `cGod::Request_Restart`, the
   pump ends because Combat is active, the loop head consumes
   `Has_Pending_Restart` (R:5960). Quit / Main Menu: `Set_Needs_Game_Exit`,
   consumed at the loop head. Load: `cGod::Load_Game` (god.cpp:623) keeps Combat
   suspended and opens the original load menu; starting a load sets
   `reload_requested` and the session is cleaned up and re-entered by
   `a30_main.cpp`; cancelling it leaves zero dialogs, which the pump turns into
   `Set_Needs_Game_Exit` (R:3008-3014) so a dead world is never resumed.

Navigation: while any dialog exists, `DirectInput` routes D-pad Up/Down/Left/
Right to the WWUI arrow keys, Cross to `VK_RETURN`, Circle to `VK_ESCAPE`, and
suppresses gameplay stick, camera and button mapping
(renegade_directinput.cpp:638-723). Front touch is the mouse. START
maps to `DIK_ESCAPE` only (gameplay menu toggle), so it does nothing inside a
popup. The pump calls `A4_Frontend_Prime_WWUI_Key_Transitions` (R:2964) before the first
`Think`, so a button held when the popup opens (Cross for
jump, Circle for crouch) is not a selection.
`Failed` ignores Cancel (dialogtests.cpp:1718), `Death` maps Cancel/Circle to
Quit, as in the original.

## Scenario matrix

| Scenario | Trace | Result |
|---|---|---|
| `Mission_Complete(false)`: escort dies, timer expires, building lost | Same handler, `cGod::Mission_Failed`, Failed popup (Restart / Load / Main Menu). Timer cases (M03, M09, M11) are ordinary script timers in `CombatManager::Think`, so the popup follows the delay. A concurrent star death is a no-op (state already DEAD). | OK |
| Death on foot | Soldier DEATH to DESTROY animation first; the world keeps running (scripts, enemies) until `Set_Delete_Pending` fires `Star_Killed`. START during that window opens EVA as in the original; Resume continues to the popup. | OK |
| Death in a vehicle | Same trigger (the soldier object). `Post_Load_Level` sets `CombatMode = NONE` (combat.cpp:525-528), so the camera profile ("Death" / vehicle) is re-derived for the new star. `_DeathInventory` is unused by restart. | OK |
| Death or failure during a cinematic | Failure popup works under a host camera. Star death under a freeze waits for the freeze to end (the star is frozen). Restart: `Unload_Level` drops the host and calls `Activate_Cinematic_Freeze(false)` (combat.cpp:586+), `Pre_Load_Level` resets letterbox, overlay opacity, HUD enable and sight scale (combat.cpp:318-376), `Set_Host_Model(NULL)` clears cinematic sniping (ccamera.cpp:560-578). | OK |
| Death or failure during the Mendoza slow-motion sequence | Scale 0.25 then 0.5 (mendozabossgameobj.cpp:1379, 1579) is process-global; `Core_Shutdown`/`Load_Level` never reset it. Restart used to keep the slow motion. | Defect, fixed (D1) |
| Conversation or dialog open | `Flush_Playlist` at popup init. `Release_Level` calls `Reset_Active_Conversations` (level.cpp:58) and `TransitionManager::Reset()`. No WWUI dialog is open during campaign gameplay (the objective viewer is hidden on `Combat::Suspend`, combatgmode.cpp:1757). | OK |
| Level-start autosave frame | `Process_Autosave_Request` (combatgmode.cpp:1659) returns without clearing the request while the state is not `SINGLE_RUNNING`, so a first-frame death defers it. Restart then writes the autosave from the restarted level start. Quit or Load clears it at session end (R:7169). | OK |
| Death while the pause/EVA menu is opening | START sets `g_gameplay_pause_requested` and the frame returns before `CombatManager::Think` (G:737-742), so no popup can be created on that frame. The flag is consumed at the next loop head (R:6247), where Combat is still active. If a popup is already up, `Run_Original_Gameplay_Pause_Menu(...,false)` returns at once (Combat not active) and the flag is cleared. Power-resume auto-pause is guarded by `Is_Active` and the cinematic check (R:6235-6245). | OK |

## Stale-state audit across Restart

| State | Owner and reset | Result |
|---|---|---|
| Time scale | `TimeManager::TimeScale`, set by Mendoza only | Fixed (D1) |
| Letterbox, screen overlay opacity | `Pre_Load_Level` (time 0, immediate). Overlay RGB is not reset (original; opacity is 0). | OK |
| Cinematic freeze, host camera | `Unload_Level` | OK |
| Input disable | Per-object `Control_Enable` dies with the star. `Input::Menu_Enable(false)` and `Input::Flush` at pump end and restart. Route gameplay flag re-armed from `Is_Control_Enabled` (R:6624). | OK |
| HUD hidden | `HUDClass::Enable(true)` + `Reset` in `Pre_Load_Level` | OK |
| Sniper | Cinematic sniping cleared on host release. `IsStarSniping` re-derived from `CombatMode` (reset to NONE). `SniperZoom` and the Sniper profile zoom persist as in the original. | OK, original |
| Conversations | `Release_Level` (INTERRUPTED callbacks, as in the original) | OK |
| Pending success | `Load_Level` clears `PendingCampaignContinue` | OK |
| Mission latch | Re-armed by `A31_Interactive_Restart_Mission_Completion_Observation` in `Load_Level`; `result.*` terminal flags cleared in R after reload | OK |
| EVA pause request | Only set inside the sim frame that skips `Think`; consumed next loop head; no popup can coexist | OK |
| Autosave request | See matrix; cleared at session end unless a campaign handoff completed | OK |
| Difficulty, inventory | `CombatManager::DifficultyLevel` is not reset by reload; `Create_Commando` restores `LevelStartInventory` when `Remember_Inventory()` (god.cpp:400-404) | OK |

## Defect and fix

**D1. Boss slow motion leaked into the restarted mission.**
`MendozaBossGameObjClass` sets `TimeManager` scale 0.25 (face zoom) and 0.5
(look at dead boss) and restores 1.0 only at waypath follow and at the end,
just before `Mission_Complete(true)`. The player can die, or a failure can fire,
inside that window (the world is unfrozen at face zoom). The popup then ran with
a scaled `FrameSeconds`, and Restart rebuilt the level at that scale. Only the
session start reset it (R:4665), and Quit and Load enter a new session. An
in-session restart did not.

Fix (Vita boundary only, no upstream or patch change):

- R:2959 `if (death_dialog) TimeManager::Set_Time_Scale(1.0F);` at popup-pump
  entry. Both popups end in restart, load or quit, so the dead world is never
  resumed; the ordinary EVA pause keeps its scale because that world resumes.
- R:6057 the same reset immediately before `cGod::Restart()`, so a restarted
  generation always starts at normal speed, matching the session-start rule.

Guard: `tools/test_fail_and_retry_flow.py` pins the premise (Mendoza is the only
`Set_Time_Scale` owner in Combat and Commando), both reset sites and their
ordering, the restart-requester set (the two original popups only), the popup
Cancel semantics, the load hand-off, the level-load resets above, autosave
deferral, and the navigation mapping.

## Deferred, not changed

1. **Circle quits the Death popup with no confirmation.** Original `IDCANCEL`
   semantics, but Circle is also crouch. The prime step stops a held Circle;
   a deliberate new tap exits to the main menu. A Vita-side confirm needs a
   hardware judgment. The Failed popup ignores Cancel.
2. **Failure in the first frame of a world generation then Quit exits the app.**
   `a30_main.cpp:286-298` requires `world_generations_rendered ==
   started`, and the popup branch `continue`s before the first render, so
   `runtime_ok` would be false (exit code 1) instead of reopening the menu. No
   producer can fail in the first frame today (all 22 are death, timer or
   objective driven), so this is theoretical.
3. **Stale WWUI dialog under a popup** would keep the pump alive after Quit until
   the lower dialog closes. No campaign dialog is open during gameplay, so no
   guard was added.
4. **Success and death in one `Think`.** Success wins (original) but the death
   popup stays in the dialog list through the intermission. Same as retail.
5. **Power resume while a popup is up** queues an EVA open that fires on the
   first frame after the restart. Cosmetic.
6. Prepared-object prewarm is not repeated on restart (see
   MISSION_FAILURE_PATHS.md section 5, unchanged).

## Physical checklist (nothing here is verified)

For M01, M05, M07, M09, M11 and M13: kill the star, then fail the mission, then
pick each of Restart, Load, Quit. Confirm D-pad and Cross navigation, that a
held button does not select, that the restarted mission runs at normal speed
(Mendoza boss missions M05 and M06 per BOSS_CLASS_SUPPORT.md, after the Mendoza death camera starts), that Quit reaches the main
menu, and that a failed-load recovery returns to the menu. Look for log lines
`A4 death: original popup active`, `A4 campaign-restart: original reload begin`,
and `[LIFECYCLE] SESSION residual`.
