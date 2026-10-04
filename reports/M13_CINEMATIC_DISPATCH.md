# M13 cinematic dispatch ordering

## Physical observation and matching log

On dev234 fresh Recruit campaign startup now succeeds, according to the user.
The user observes Havoc's ground view before cinematic camera ownership and
post-ambush activity during the ambush cinematic. These timing defects remain
physical correctness blockers; no corrected behavior is claimed.

Private log `build/device-evidence/A3.5-dev234-20261004/runtime-m13-intro-order.log`
has SHA-256 `ba31eabf4c73a7e16437525075ce48e06006f6c09ca71a4e63cee7be9f75650c`.
It belongs to installed SELF
`2311c5b24d70f46f84b4601ec56cdd274fa6829ac452ab0f6f51cb20e1ba5354`.

The log records a port-added X00 intro budget yield after one command at
cinematic time0, with another zero-time command pending. Frame0 then has
camera_host0, HUD enabled, player control enabled and ground-position Havoc.
Later callbacks yield repeatedly while zero-time commands remain pending;
cinematic time advances to0.200,0.400 and beyond between those batches.
A model creation command later takes approximately591 ms. These are observed
costs from this run, not general frame-rate measurements.

## Owning defect and correction

Original `Test_Cinematic::Created` loads the control file and immediately
calls Parse_Commands. Original Parse_Commands processes every due control
before scheduling the next authored timer. The native added budget returned
after4 ms, scheduled a1 ms retry, and allowed original simulation to run
between due commands. That makes partially initialized cinematic state
observable. The earlier count-of-two budget was superseded by a time-only
budget; the latter still violates the same command-dispatch contract.

Dev235 appends deterministic
`port/patches/scripts-a35-cinematic-original-dispatch.patch` and restores
original due-command dispatch. Original commands, control-file timestamps,
FrameSync, timer scheduling, cinematic freeze and script ownership remain.
No retail control file, authored gameplay event or player placement changes.
The unused budget classifier and bookkeeping are removed; bounded slow-command
diagnostics remain. Stage replay succeeds without fuzz with318 ordered patches.

`tools/test_vita_m13_cinematic_preparation.py` compiles actual production
Parse_Commands and verifies four zero-time controls complete before returning,
camera-state setup completes, the next authored timer is1 second, and a late
callback retains original FrameSync15 and finishes the due batch. A source
check rejects the old native budget. All502 host checks and six ARM compile/link
plus seven package actions pass; Vita3K installed hashes match without launch.
The first full run had two historical patch-anchor failures; those tests now
reverse the later dispatch patch before checking their unchanged historical
hashes. All11 focused dispatch/patch tests and the repeated full run pass.
This establishes dispatch semantics, not physical
visual ordering or complete cinematic acceptance.

## Remaining checks

Repeat fresh Recruit startup on the corrected matching artifact: confirm
camera ownership before any ground view, correct ambush/rope/audio ordering,
no premature post-ambush combat/events, proper control handoff and repeated
loads. Existing shader/model upload stalls, audio clock behavior, frame clamp,
and any independently early script/zone events remain separate leads.
Restoring original dispatch can expose a longer setup stall; future changes
must prepare resources without advancing simulation or exposing partial
authored state. Do not reintroduce command yielding to hide that stall.

Dev234's current user run is left untouched. Development saves remain private;
write and original reload still need physical verification. No PSTV evidence.

## Later dev234 pause failure and measured costs

The user reports a crash dump after Select+Start and major M13 performance
problems. Quicksave uses Select+Square; this action is not a completed save
test. Matching log `runtime-select-start-crash.log` (same private evidence
directory), SHA-256
`a468506eab90257576b17efa63900ec97ffe249817cdfe71a5e362ce42beab99`,
ends at START routing through original menu-toggle input after the last
M13 ending conversation. The process is no longer listed. Two bounded dump
metadata queries found no new file yet; await completed dump/dismissed error
before assigning a cause. Do not infer an abort from the absence of a file.

At frame3960 reported cumulative average is13.382 FPS. The logged stage
simulation/render values are22.372/52.348 ms; cumulative worst frame is
2.167 seconds. Rolling frame percentiles p50/p95/p99 are84.536/225.224/305.747 ms.
These are this candidate's logged measurements, not acceptance or a fixed
benchmark comparison. Sampled mesh-cost estimates are leads, not precise
full measurements. The audio provider logs allocation failures while gameplay
continues; failure containment executes, but audio correctness/memory adequacy
does not pass. No speculative broad optimization is adopted here.
