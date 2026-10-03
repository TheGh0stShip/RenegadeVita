# Mission completion and objective ownership review

2026-10-03 source inspection; no compilation, launch or device action.
Native mission/runtime gates remain 0/10. This review establishes source
linkage, not successful progression.

## Success-to-next-level route

The M13 success handler is in `staging/scripts/Test_DLS.cpp`: the
`MX0_MISSION_SUCCESS` custom event calls `Commands->Mission_Complete(true)`.
It is a dependency beyond `MissionX0.cpp`; seeing the opener's script file
alone does not establish finale coverage. Delivery of that event remains
unverified by this inspection.

`Combat/scriptcommands.cpp` delegates to `CombatManager::Mission_Complete`,
which forwards to the installed `CombatMiscHandlerClass`. The native handler
in `port/platform/a31_gameplay_boundary.cpp` records the terminal callback.
The gameplay loop observes it after simulation and, for successful non-client
full-port sessions, calls `Run_Original_Campaign_Intermission`.

That function invokes the original `CampaignManager::Continue`. Original
campaign code saves score statistics before ending combat, routes Score/Movie/
Level entries from the campaign catalog, and uses `GameInitMgrClass::End_Game`
to deactivate combat. Its initial `Suspend` is not the terminal state check:
the later `End_Game` deactivation makes `combat->Is_Inactive()` meaningful.
No missing success forwarding was established.

The intermission runs original game modes and UI until exit or an original
Start_Game request. The existing frontend latch captures that request. The
adapter saves the original campaign chunk into a 64-byte session buffer,
retains the next source, and marks the handoff only after a successful write
and a positive bounded size. `a30_main.cpp` copies the result after session
cleanup; the next runtime initializes the campaign catalog, checks the source
and 64-byte limit, then loads the original chunk. This is an in-process handoff,
not a persisted user save or proof of a working transition.

The original campaign chunk contains two `int` values: State and BackdropIndex.
Native ARMv7 ILP32 gives each four bytes; no pointers are serialized here.
The source-defined header/payload sizes fit the buffer. This inspection did
not execute the writer, reader or RAMFile implementation.

## Objective behavior and diagnostic limits

Original `ObjectiveManager::Add_Objective` rejects duplicate IDs with a debug
message. `Set_Objective_Status` searches by ID; an absent ID produces only a
debug message and no status mutation. Existing IDs update radar, translated
messages, HUD and sorting. A hidden objective becoming visible resets its age;
an accomplished hidden objective uses the completion message route. Preserve
these rules rather than inventing missing objectives automatically.

The existing progress snapshot retains at most six objective records. It does
not prove all objectives were added, changed, rendered or restored. The new
observer-timer diagnostics do not cover absent objective IDs. These are
diagnostic coverage gaps, not confirmed retail or port gameplay defects.

## Tutorial and M01 natural producers

The tutorial completion producer is `MTU_Tutorial_Controller::Timer_Expired`
for `MTU_TIMER_ENDGAME`. Its scheduling route is not simply destruction of an
MCT. The lieutenant's completed MCT speech moves the player, requests barracks
destruction, restores control and sends `MTU_TYPE_MOCK_INVASION`. That controller
event creates two officers, each with `MTU_Nod_Soldier` parameter `2`. Their
Killed callbacks resolve the controller and send `MTU_TYPE_COUNT_OFFICERS`.
After the counter exceeds one, the controller marks objective06 accomplished,
sets the final HUD help text and starts a three-second endgame timer. Missing
officer creation, script attachment, death delivery, controller lookup or timer
dispatch could prevent success. None is proven operational by source presence.
The source counter does not deduplicate sender IDs; preserve retail behavior
rather than adding a new counting policy from this review.

M01's controller handles custom type0, parameter
`M01_DO_END_MISSION_CHECK_JDG`. Its executable condition is
`commcenter_sam_objective_active != true && prisoners_are_freed == true`, not
a scan of every primary objective suggested by the nearby comment. A one-shot
`final_conv_played` guard then changes weather, removes detention actors,
repositions the player, creates an invisible cinematic controller and attaches
`Test_Cinematic` with `X1Z_Finale.txt`. It separately schedules
`M01_END_MISSION_PASS_JDG` after20 seconds. That consumer stops the propaganda
controller when found and calls mission success. Completion is timer-driven;
this route does not wait for a cinematic-finished callback. Original simulation
timer scaling/pause/clamping still applies.

Two additional source success entrances exist in the same M01 controller:
type0/parameter0 directly reports success, and an `endMission_conv` observer
completion schedules the end-mission parameter after three seconds. The latter
appears under `ACTION_COMPLETE_CONVERSATION_ENDED`. No assignment to
`endMission_conv` was located in the inspected file; do not count it as a
proven reachable alternative or treat a matching variable name as runtime
evidence.

The direct parameter0 entrance now has verified authored producer provenance:
`X1Z_Finale.txt` sends type0/parameter0 to controller object100376 at authored
frame618 (approximately20.6 seconds). Original Test_Cinematic converts negative
frame timestamps at30 frames/second, treats the destination as a numeric object
ID, resolves it through Find_Object and sends only when the object exists.
The event audit receipt's original source hashes, M01 archive hash, binding
receipt hash and this control member hash were rechecked against current files.
Control member SHA-256:
`62821a4434bd705be36b1ce6f3478d59d0278971e6fac6d891cb9903b28d8b20`.
Detailed control data remains private; no retail control file is published.

This is a second authored success route alongside the controller's separately
scheduled20-second delayed event. Its later nominal timestamp does not prove
that it executes after that event in a running session: observer scheduling,
cinematic command budgeting, original sync-time rounding and session teardown
need matching runtime evidence. Nor does this establish that all cinematic
media has completed before success. Preserve both original routes rather than
extending a timer or deleting an apparently redundant event from speculation.

The M01 failure calls in prisoner/death-related scripts remain separate from
these success producers. Source completion does not establish whether the
finale renders, plays all media, retains actors for its duration or reaches the
score/movie/next-map flow.

## Inventory and encyclopedia continuation correction

Original `InventoryClass` stores scalar defense values and weapon ID/ammunition/
ownership records; it does not store pointers to departing soldiers or weapons.
Restore merges larger health/armor values into the new soldier and raises ammo
to the stored count, preserving the original unlimited-ammo sentinel. This is
not an exact replacement of the new preset's inventory. Keys belong to the
soldier's separate KeyRing/save state and are not in this cross-level inventory.

`cGod::LevelStartInventory` survives the in-process native teardown:
`cGod::Reset` changes only its state machine, and campaign Init/Shutdown do not
reset inventory. Fresh campaign, replay and explicit load actions have separate
original reset calls. Original single-player game data enables Remember_Inventory
and `cGod` restores it when spawning a mission soldier. Runtime merging still
requires verification; no weapon/health policy was changed.

A source-confirmed EVA discovery loss was found alongside that route.
`cGod::Store_Inventory` also calls `EncyclopediaMgrClass::Store_Data`, copying
live discovery vectors. Native session cleanup calls Encyclopedia Shutdown,
which clears live vectors but leaves the stored copy. The following runtime
previously called Initialize unconditionally; Initialize builds fresh vectors
and calls Store_Data, overwriting the carried discoveries before the new spawn
could restore them. Original desktop startup initializes the encyclopedia once,
not between every campaign level.

The native boundary now calls original Restore_Data for a validated non-demo
campaign handoff, after the existing campaign-state/source validation and Load.
Fresh sessions and checkpoint routes retain Initialize. Original inventory,
encyclopedia implementations and save formats are unchanged. This correction
is uncompiled and unverified on native hardware under the build/launch hold.
Verify discoveries in each category across natural M13-to-M01 continuation,
then fresh campaign/replay/load reset behavior and repeated session teardown.

Eleven focused source checks pass (`test_campaign_discovery_handoff`,
`test_requested_mission_owner_contract`, `test_campaign_profile_defaults`).
The five lifecycle checks verify source selection/order and original
copy ownership; they do not execute vector copying or mission progression.

Further source verification confirms fixed category enum values (character,
weapon, vehicle, building), with bits indexed by authored INI object IDs.
Build_Bit_Vector sizes each category to its maximum ID plus one; INI section
enumeration order is not the discovery index. BooleanVector assignment copies
both BitArray and BitCount, so Restore_Data supplies the previous category
length as well as its bits after Shutdown. This assumes unchanged retail
encyclopedia definitions within the same process; live content changes are not
a supported or validated handoff scenario.

The inspected outer caller supplies campaign_source only after a successful
runtime reports a completed handoff and clears pending source/state after each
call. A failed initialization does not manufacture a continuation token. A fresh
session calls Initialize and Store_Data, replacing the prior copy. Consecutive
successful transitions still depend on original End_Game storage each time.
Combat Init/Shutdown do not assign DifficultyLevel in the inspected source;
per-level objectives, conversation instances and HUD have their own reset
owners. No second carried-state reset defect was established by this pass.

## Remaining verification

- Verify the tutorial officer/death/counter/timer chain and M01 prisoner/SAM/
  cinematic/delayed-event chain above with matching runtime evidence. Trace
  the direct finale event's actual delivery as distinct from the20-second
  controller timer. The conversation entrance remains unproven.
- Observe natural M13 success, score statistics, movie completion/skip, next
  map selection and restored campaign state with matching candidate identity.
- Verify inventory preservation through the clean session handoff. Original
  End_Game stores `cGod::LevelStartInventory`; that static owner is separate
  from the two-field campaign chunk. This review found no evidence of its loss,
  but did not prove restoration in the next session.
- Verify objectives beyond the six-record snapshot, duplicate/missing-ID
  attempts, save restoration, HUD/radar and objective-screen presentation.
- Exercise failure/death Restart and Load separately. The native handler calls
  original `cGod::Mission_Failed` on failure; success-route evidence cannot
  establish those flows.
- The latch preserves the first terminal result until Reset, not merely for
  one frame. Contradictory terminal callbacks and reset boundaries need runtime
  evidence; no policy change was made from speculation.

Build and launch remain on hold. No source linkage in this report closes a
native or physical acceptance gate.
