# Dev236 quicksave freeze and finale observation

## Armed-beacon post-load audio ownership

Source review found three independent omissions in the released beacon save
state. The live `ArmedSound` scene object is intentionally not serialized, but
there was no post-load reconstruction. `WarningTimer` was not saved, so warning
cadence restarted from constructor state. `WeaponDefinition` was also not saved,
even though the arming-state `Think()` path dereferences it; a checkpoint made
while the ion beacon was still arming could therefore resume through a null
definition.

`BeaconGameObj` now saves and restores `WarningTimer` and the stable weapon
definition ID, restores its owner before resolving legacy state, and recreates
only a missing armed continuous sound through an idempotent helper. Legacy saves
derive an arming weapon only when exactly one owner-bag weapon references the
loaded beacon definition. An unresolved legacy arming beacon is deleted safely
instead of dereferencing a null definition. Legacy armed saves reconstruct the
warning timer from elapsed detonation time. Calling
`Set_State(STATE_ARMED)` remains avoided because it would reset detonation and
weather state.

The two deterministic staging patches now replay from pristine EA source with
zero fuzz and reproduce the active `beacongameobj.h/.cpp` byte for byte. This
closes source and staging-receipt gaps only. It does not establish Vita save
return, reload correctness, finale completion, or physical stability; those
remain under the active validation hold.

On physical Vita dev236 the user confirms combat no longer runs underneath
the opening cinematic. This is user visual/audio evidence for the original
dispatch restoration, not full cinematic or mission acceptance.

The user subsequently reports a freeze after Select+Square, a repeating ion
beacon routine and no ending cinematic. Original quicksave request reaches
the engine. Two bounded log pulls are identical, SHA-256
`20dbb1446f16dbac8d8758da21d0b77055753543362571e5930731d8862fd429`.
Process 50012773 was present during initial inspection; no matching new dump
exists in the inspected directory. The user subsequently reports quitting
without checking whether saving resumed. Elapsed time before quitting is
unknown; a persistent deadlock has not been established. No agent termination,
restart or synthetic input was performed.
After the user's quit, a new target inventory shows VitaShell only.

Save metadata initially shows 184136 bytes, the first private backup 208982,
then repeated device hashes show 212383 bytes, SHA-256
`59ae9693834bf7ac2adce79d94f4cf9915cfd8a32a26e089e70c5bd2858e49e9`.
Both snapshots are private under `build/device-evidence/A3.5-dev236-20261004/`.
The outer level-data and conversation-category chunks still have temporary
zero lengths. 156 conversation records are complete, followed by an unfinished
conversation record. This is incomplete serialization, not a working checkpoint
or proof of a specific instruction at the hang. No save is published or packaged.

Bounded debug capture preflight fails: execution continue, leased stop,
stack snapshot and register-read capabilities are absent. Cleanup owns no
stopped target or attachment. Candidate ELF also lacks an embedded VDB build
fingerprint; independently verified installed hashes remain the identity evidence.
No inferred stack or fabricated register observation is used.

Source follow-up after dev236: commit `522dabb` stages ChunkSave header
back-patching in memory and writes the completed stream once at Close, directly
removing the thousands of card seeks present in dev236. The partial file therefore
does not establish a remaining infinite ConversationMgr loop in current source.
The rooted writer now also targets a same-directory `.pending` sibling and
renames it over the destination only after staged flush and native close succeed.
A failed/interrupted serialization or close preserves the previous visible slot;
rename/close failure is retained by the existing write-status route. Save bytes,
chunk ordering and the synchronous original serializer remain unchanged. This
follow-up is local, uncommitted and unvalidated; it is not evidence that quicksave
now returns on Vita.

Original `staging/scripts/Test_DLS.cpp` starts the ion sequence, schedules
white fade 22 seconds later and finale 25 seconds later. The beacon actor uses
forced-fire attack. A synchronous save stall stops simulation and those timers.
The user clarifies repetition began while frozen just before the strike fired:
after the cinematic music finished, the perceived strike routine and music
repeated. The native audio thread can continue without main-thread simulation;
this observation does not establish a repeated script callback. An independent
finale defect is not yet proven. First recover save return, then test the
original fade/finale timers and cinematic transition.

Dev237 adds bounded native save phase and every-sixteenth-conversation
begin/end breadcrumbs in the original serializer. It changes no save layout,
subsystem ordering or mission timer behavior. All 502 host checks pass, as do
ARM compilation/linking and package identity checks (658 build actions).
Vita3K installation/readback hashes match without launch. Dev237 is packaged
and has not been deployed to physical Vita. SELF SHA-256:
`b040da0b36ae52249bcef071addf0f9ce5e5ab7c9fc7d2614b2f34c0e1be93e8`;
ELF: `36ccf5960164598519a7fa1bd82d9fd00b07e4acf36f00b91cf4b46cebc9b52c`;
VPK: `85bdbd7021f9c1de0049f19700758210c75e6a12e491c899d06cffd31fb630c6`.
First full host run found one historical patch replay offset caused by added
diagnostic lines. The private fixture now reverses the new diagnostic patch
before replaying the old patch; original expected hashes and zero-offset
checks remain unchanged. The corrected three focused tests and full suite pass.
Do not overwrite the preserved partial checkpoint or claim reload success.

Follow-up tests should first save as soon as normal M13 control returns,
before replaying the final battle. Capture phase progress and write size over
a bounded interval, verify completed outer chunks and original Load Game
restoration, then preserve a development checkpoint. If serialization is
advancing but slow, measure original chunk seek/write costs before changing
the platform I/O boundary. If it stops, identify the final completed phase and
obtain available matching thread evidence. No read/write buffering or memory
staging optimization has been adopted from the incomplete file alone.

## Save writer atomicity and Vita rename (2026-10-05)

Two defects in the rooted save writer (`port/filesystem/renegade_file_factory.cpp`):

1. `RawFileClass::Open` begins with a virtual `Close()`. The override treated
   that as the end of the session it was opening: it dropped `AtomicWrite`,
   restored the target name and the open then landed on, and truncated, the
   destination. Saves were never atomic in practice: an interrupted save
   destroyed the previous slot, consistent with the truncated dev236 file. A
   `NativeOpening` guard now limits that inner Close to the native handle.
2. The final rename relies on POSIX replace semantics. The Vita's
   `sceIoRename` refuses an existing destination (the port's own route
   recorder already removes first). With (1) fixed, every save into an
   occupied slot would have been discarded. `Renegade_Replace_File` now
   moves the old file to `.previous`, renames the new one in and restores the
   old file if that fails.

Staging and atomic replacement now apply only to pure `WRITE` sessions;
`READ|WRITE` keeps the original direct semantics.

Host contract: the staging test adds an overwrite-in-place case and runs once
more with a rename that refuses existing destinations (modelling the Vita).
All four tests pass; removing either fix makes its test fail. The
availability test's ThreadSanitizer case fails identically on the prior
commit (pre-existing, unrelated).

Finale path: `MX0_Area4_Controller_DLS` saves every member, including
`basewall_id`; ion strike, 22 s fade and 25 s finale are original script timers
already logged by `M13 finale:` breadcrumbs. No source defect found there.
Remaining risk: a crash between moving the old slot aside and renaming the new
one leaves only `<slot>.previous`; it is not yet recovered automatically.
