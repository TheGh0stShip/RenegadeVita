# A36/A37/A38 patch interplay QA (2026-10-07)

This review is report-only. Nothing was built, staged, or changed in a patch.
Evidence class: static host review of `staging/scripts` and `staging/combat`.
Staging was refreshed at `3c31e6e`, which is after every reviewed patch landed.
No runtime evidence was collected.

## Scope

Reviewed together: the 2026-10-07 `scripts-a36-*`, `scripts-a37-*`, `scripts-a38-*`,
`combat-a36-*` (the new null-guard and Raveshaw patches), `combat-a37-*` and
`combat-a38-*` patches. That includes the value-initialising factory
(`scripts-a37-script-factory-value-init`). `combat-a47-ccamera-cinematic-sniper-handoff`
also landed today but falls outside this naming scope and was not reviewed.

## Methods

* `python3 tools/audit_script_save_state_gaps.py`: no dropped (duplicate or
  out-of-range) SAVE_VARIABLE ids in M01–M11, MX0 or Test_DLS.
* An independent per-class scan of every `staging/scripts/*.cpp` `DECLARE_SCRIPT`
  checked duplicate ids, duplicate variables, ids outside 0–255, and array sizes
  against the 250-byte limit. No new collision. The only duplicates are in
  upstream (listed below).
* Engine semantics were read from source:
  * `ActiveConversationClass::Start_Conversation` stops a non-key conversation
    synchronously with `INTERRUPTED` when a key conversation is active.
  * `Notify_Monitors_On_End` calls `Action_Complete` on every observer of the
    monitor object.
  * `Send_Custom_Event` with delay 0 runs synchronously. A delay > 0 becomes a
    saved custom timer.
  * `LevelManager::Release_Level` calls `Reset_Active_Conversations` (which
    sends `INTERRUPTED` to monitors) before `GameObjManager::Destroy_All`.
  * `ObjectiveManager::Add_Objective` ignores a duplicate id.
    `Set_Objective_Status` on a missing id does nothing.
    `Update_Object_Blip` clears the blip of an objective that is not pending.
  * `CRandom::Get_Int(0,15)` is `[0,15)`.

## Findings

| # | Patch | Issue | Severity | Suggested fix |
|---|---|---|---|---|
| 1 | scripts-a38-m01-open-gate-objective-fallback | The shared helper `A38_Add_Open_Gate_Objective` (`Mission01.cpp:276-291`) checks only `open_gate_objective_added`. The fallback custom checks `gate_objective_done` (`:1383`), but the normal `unlocked_gate_conv` ENDED callback (`:2583-2586`) goes straight to the helper. The pen unlocks when the CLEAR custom is sent, and `M01_Remove_Unlock_Gate_Objective` then plays. A player who pokes the gate during that conversation sets `gate_objective_done` and accomplishes a not-yet-existing objective (no-op, `:1426-1429`). The ENDED callback then adds primary `M01_OPEN_THE_GATE_JDG` as PENDING, with an HUD pog and a radar position blip at the open gate, for the rest of the mission. The end check (`:1612`) does not consult it, so the mission still completes. This is the same late-add race the M03 patches close, but it sits inside the new shared helper. The retail race also existed. | Medium | In the helper, after `open_gate_objective_added = true;`, use `if (gate_objective_done) { Commands->Add_Objective(M01_OPEN_THE_GATE_JDG, …PENDING…); Commands->Set_Objective_Status(M01_OPEN_THE_GATE_JDG, OBJECTIVE_STATUS_ACCOMPLISHED); return; }`. Skip the blip, pog and help text in that branch. No new save id is needed. |
| 2 | scripts-a38-m09-keycard-zone-distance-recheck (with a36-m09-keycard-mobius-refetch) | `Entered` (`Mission09.cpp:4451-4469`) starts a new 2 s `DIST_CHECK` chain on every entry. A chain survives only while `star_in_zone` is true at its tick, so an exit and re-entry within 2 s (zone-edge jitter, or swept-entry Enter/Exit pairs) leaves several live chains. Before the patch the extra chains kept the stale distance and never fired. With the re-measure (`:4430-4434`), each live chain sends `CHECK` once Mobius arrives. A `COUNT 1` reply (no key) then starts `IDS_M09_D15` once per chain. A `COUNT 2` reply is safe because the first reply moves `key_counter` to 3. | Low | Add a saved `dist_check_pending` flag (next free id 5). Start the timer only when it is false. Clear it when a chain sends `CHECK` or finds `star_in_zone == false`. |
| 3 | scripts-a38-m05-deadeye-poke-rearm | The INTERRUPTED re-arm (`Mission05.cpp:1279-1284`) also runs when Deadeye dies mid-talk (the conversation Think stops on a dead orator) and at `Release_Level`, where conversations reset before objects are destroyed. In both cases it calls `Enable_HUD_Pokable_Indicator(obj, true)` on a dying or outgoing object. The effect is cosmetic: a poke icon can appear over the corpse. Mission state is unaffected because `Killed` already sent 502/2. | Low | Guard the re-arm with `Commands->Get_Health(obj) > 0.0f`. |
| 4 | scripts-a38-m11-sydney-route-monotonic | `reachedMissileSwitch` is set on arrival (`Mission11.cpp:10060`) and never cleared. Before the patch, re-entering the top silo zone re-sent `M01_MODIFY_YOUR_ACTION_04_JDG`, which restarted the walk, the console animation and `M11_End_Mission_Conversation`. That was the only recovery if the console action never completed NORMAL, and the patch removes it. No path that interrupts that action was found (Sydney is innate-disabled at priority 100, and damage talks join with `allow_move=false`), so this is speculative. | Low / Info | Optional. Clear `reachedMissileSwitch` when `M01_DOING_ANIMATION_01_JDG` completes with a non-NORMAL reason and `missionEndConv == 0`. |
| 5 | scripts-a38-m03-village-sam-objective-late-add | When 1002 is credited at add time (`Mission03.cpp:420-434`), the same case still starts timer 911 (`:447`), so the key conversation `M03CON024` plays 15 s after an objective that is already accomplished. The shore (1004) and keycard (1007) late-adds have no equivalent follow-up. | Info | Check the M03CON024 text. If it is a "destroy the SAMs" prompt, skip `Start_Timer(…, 911)` when bit 1 was already set. |
| 6 | combat-a37-scriptzone-swept-entry | At low frame rate, every zone crossed between two Thinks fires `Entered` in the same frame, in GameObj/zone Think order rather than path order. Each zone fires `Exited` on the next Think. M03 base-entry zones that destroy siblings through `RMV_Trigger_Zone` can resolve in a different order than at 30 fps. No concrete M03/M09 break was found: the M09 keycard zone and the M03 late-add flags tolerate either order. | Info | Watch on hardware. Optionally sort swept candidates by entry parameter `t` along the segment. |
| 7 | (upstream, unchanged) | These duplicate registrations are not from the new patches but sit next to them. `M03_Announce_Refinery_Controller_JDG` registers `spkr_8_spot` as both 18 and 19 (`Mission03.cpp:2310-2311`), so `spkr_9_spot` is never saved: a latent save gap. `M04_Objective_Controller_JDG` registers `firstmateConv` as 37 and 45 (`:150,:159`; harmless, and 47/48 do not collide). `M08_Sakura` registers `flee` as 2 and 5 (`mission08.cpp:5696,5699`; harmless). | Info | Optionally change `SAVE_VARIABLE(spkr_8_spot, 19)` to `spkr_9_spot, 19`. |

## Checks that found no defect

| Patch(es) | Check | Result |
|---|---|---|
| a38-m03 keycard/mainframe/shore/village late-adds + village report fallback | Ids 9–12 in `M03_Objective_Controller` (previously 1–8); timer 3020 vs 0/911/912/1002/1004/1007/2004; bit-1/bit-2 credit order; `Report_Village_Sams` idempotent; no `307,4` sender, so the timer-1007 re-pend cannot fire; `308,2` (fail) and `308,1` (poke) are mutually exclusive through `mct_accessed`; accomplished-then-blip leaves no stale blip | OK |
| a38-m04 torpedo race + missile briefing drop | Ids 47/48 are free; param 441 does not collide with 400–600; the fallback calls `Action_Complete(missileConv, ENDED)`, which is guarded by `missile_objective_activated` and also covers `Create_Conversation == -1`; a late or repeated 450 accomplishes 400 instead of re-pending it | OK |
| a38-m01 PCT watchdog + open-gate fallback | Customs 438001/438002 do not collide with the mission1.h enum (≤ ~4006); id 90 is free; the watchdog and the Comm Center path both gate on `player_has_unlocked_pen`; zeroed EVA ids cannot match a live sound | OK apart from #1 |
| a38-m05 gunner rearm | Monitor-before-Start: all state changes run before `Start`, and nothing after `Start` assumes the talk is pending; `poke_id` is reset only when it is still 2, so a Custom-500 move to 3 or 4 mid-talk is kept | OK |
| a38-m07 hotwire SAM fallback + path failure | Timer id 1 is the only timer; `capture_sent` is saved as id 2 and makes the send once-only; the path-failure remap is limited to `GO_SAM1/2` with `!evac` and `ARRIVE_EVAC_SPOT` with `evac`, and sends one evac custom per failure | OK |
| a38-m09 intro resume | Timers 9021/9022 vs 20; `escort_started` is saved as id 2; the resume is deferred by 1 s, so the `Release_Level` INTERRUPTED path creates nothing on the outgoing world; `Start_Escort` is idempotent | OK |
| a38-m10 objective resend (Monitor-before-Start) | Per-script `objective_sent` ids are free; the synchronous `Action_Complete` inside `Killed`/`Poked` sends the objective before the rest of the callback, and nothing later depends on it. In `M10_Gate_Check`, `first` becomes true synchronously, but the `1007` and `1006` branches key on the instance `Objective` param, so they cannot run in the same call. `primary_count` cannot be double-counted. A teardown INTERRUPTED matches the retail reason-agnostic behaviour. | OK |
| a38-m11 end-conversation replay | Param `M01_MODIFY_YOUR_ACTION_06_JDG` has no other sender to Sydney in M11; the replay runs only with `missionEndConv == 0` and `!killedYet`; a synchronous INTERRUPTED inside `Start` only schedules a 2 s custom, so there is no `Reset_Active_Conversations` loop; `MaxDist` 1000 means no audience-distance loop | OK |
| a38-m11 cryo recursion bound | `simpleMutant_id[15]` is saved as ids 18–32; the index range is `[0,15)`; the guard terminates recursion | OK |
| a38-m13 firehole register | `engineer_02_id` and `entered_tank` are saved (19/22) and set to 0/false in `Created`; the missed cue fires at most once | OK |
| a36 save-variable-id renumbers (M01/M03/M04/M05/M11/MX0) | No new id collides inside its class; old saves fall back to the value-initialised 0 | OK |
| a36-m05 fire-loc save / m09 objective save / m02 speech save / m10 gate flags / m05 dead6 text | Arrays of 12, 40 and 3 bytes and the M02 per-area arrays (26/104 bytes) are all under 250 bytes; ids are free | OK |
| a37-script-factory-value-init vs a36 explicit inits | Every `DECLARE_SCRIPT` in campaign files has an implicit constructor, so `new T()` zero-fills it. The only user-provided constructor, `GTH_Create_Object_On_Enter` (`Test_GTH.cpp:191`), initialises its own members. The a36 patches that explicitly set 0/-1 (M01 ids, M11 conversation ids, MX0 area-4 ids, M05 `last = -1`) agree with the zero fill. M05's `Index` `Min>=Max` shortcut also covers the post-load `last == 0`. No patch depends on garbage values. | OK |
| combat-a37 face clamp / HUD index / elevator timeout / encyclopedia flush / overlay clamp; combat-a38 Raveshaw landing | No script-visible id or ordering interplay | OK |

## Coverage notes (not interplay)

The existing `CONVERSATION_GATED_OBJECTIVES.md` still lists M04/M11 non-key
gates as AT RISK. M10 `Hand_Of_Nod` (1008), `Refinery` (1009) and the
`Gate_Check` 1006/1007 branches keep Start-then-Monitor. Those are separate
work items.
