# Dev236 quicksave freeze and finale observation

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
