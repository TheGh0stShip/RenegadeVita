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

## Remaining verification

- Trace natural tutorial and M01 ending producers, including cinematic/helper
  commands; the M13 consumer above does not establish their completion routes.
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
