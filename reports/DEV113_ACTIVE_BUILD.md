# Dev113 active build and exact next action

## Latest: rewind correction passed; canonical retry running

The host failure below is corrected; see `DEV113_BUFFERED_REWIND_FIX.md`.
Canonical retry is live in unified exec session 5497, with log
`build/dev113-host-evidence/canonical-rewind-retry.log` and eventual exit receipt
`build/dev113-host-evidence/canonical-rewind-retry.exit`. Do not restart it while
live. Use this retry's result, not the historical canonical.exit=134.
The unchanged post-Sydney request remains queued; Vita3K is stopped.

On success: read matching dev113 identity, use prepare_vita3k_demo.py to install
the title, launch a unique Windows runner evidence directory with its SELF hash,
then check original saved-game restoration, EVA pause/resume, and remaining M00.

Read-only build-cache observation: retained dev112 ARM commands use -g and no
debug-prefix-map, while ccache defaults hash_dir=true and builds use unique
candidate directories. Cross-candidate cache misses therefore have a concrete
potential cause; no cache/debug-path settings were changed during this build.

## Current: canonical failed; no build running

Session 77073 ended with exit 134 during the ASan interactive host gate, before
ARM packaging. A separate bounded replay reproduced the same failure:
HumanStateClass::Set_Anim_Control dereferences unresolved HumanPhys during
SoldierGameObj::On_Post_Load. The null-page read is at address 0x60.
The earlier dev112 matching host validation passed this phase. Causality with
the conversation serialization change is not established; do not bypass this
gate or claim the corrected checkpoint has loaded.

Evidence: `build/dev113-host-evidence/canonical.log` and
`build/dev113-host-evidence/asan-postload-reproduce.log`.
GDB session 5921 finished. At the failing soldier post-load, HumanPhys is null
while AnimControl is valid. Thus this is physics-reference restoration, not a
missing animation controller. GDB evidence is retained in
`build/dev113-host-evidence/asan-postload-gdb.log`. Next: trace that HumanPhys
pointer token through original load/remapping; do not add a null guard that
silently discards required soldier state. No build or debugger remains running.
Existing dev112 binaries and queued checkpoint remain unchanged.

## Historical launch record

Canonical dev113 build is running in unified exec session 77073.
Command: `RENEGADE_CANDIDATE_LABEL=A3.5-dev113 RENEGADE_DEVELOPMENT_CHECKPOINT=1 bash tools/build.sh`.
Log: `build/dev113-host-evidence/canonical.log`; terminal status will be written
to `build/dev113-host-evidence/canonical.exit`. Do not start a competing build.

The unchanged post-Sydney save is already requeued for this candidate.
Receipt: `build/dev113-host-evidence/checkpoint-launch-request.json`.
After build success, check matching identity, install dev113, launch a new
candidate-scoped Vita3K run, then inspect actual original saved-game restoration.
Do not requeue again blindly or overwrite the save. Pause and M00 ending remain
unproven. No emulator process remains from the dev112 failure.

Independent diagnostics finding: dev112 stdout explicitly reports unimplemented
`sceClibMspaceMallocStats`. The linked VitaGL free-space provider reads an
uninitialized SceClibMspaceStats structure after that call and subtracts its
fields. This explains why that emulator telemetry is unusable; it must not be
treated as measured memory availability or physical-Vita allocator evidence.
No emulator or allocator implementation was changed for this finding.
