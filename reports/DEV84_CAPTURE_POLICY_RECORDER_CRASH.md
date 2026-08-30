# A3.5-dev84 capture-policy physical recorder crash

Status: retained physical evidence; this does not validate the capture-policy
change, the original frontend, M00, HUD, dialogue, or Start-exit lifecycle.

## Exact candidate and returned artifacts

- Installed `RNEGA3101` SELF: SHA-256
  `555f0c1f83b46992b0e349b8c1d2c4500daaeb2d945311926d33f3d824590bbe`.
- Matching ELF/map/symbol SHA-256 values: `15d2ecdd6fdb304f558a2f15d9ba37ef992813b5bf4fda3400284c4dff90430f`,
  `f1d5d30f18100495c942ccb4fc8341570ad656fa57e24d8676b192c44e4ec13a`,
  and `82cea58cbd0c05721fb699d5d86c058656ef3e2480260b179f5c417c1f34f406`.
- Runtime log: 14,139 bytes, SHA-256
  `d71f5b46a2c21f489f5738b7a7efee2921e30bfe25275075a4e35bc13dca9009`.
- New returned raw cores, retained locally only under
  `build/device-evidence/a35-dev84-capture-policy-20260830T182029Z/`:
  `57778ec977683c893119973a10e2150ebb2410b7484dbadbf73d633641f7c8c9`
  and `8f3dab71a4363a3d9a897430a5ec5be84f98f51a7871c0afed7ce736aebe720e`.

## Classification

The runtime log records an original-owner startup pre-cache success in
5,023 ms and 5,027 ms before ending without a frontend, load, M00, or
capture-policy breadcrumb. It therefore does not support a claim that the
capture-policy branch ran or that M00 rendered.

The parsed Vita `THREAD_INFO` records have verified title-thread PCs
`0x8146d5fa` and `0x814255fa`. The module records and load-bias attribution
are source-derived, but both PCs have the same `+0x15fa` offset as the prior
recorder display-hook crash and strings in both cores name `VitaMP4Recorder`,
`record_thread`, and the stale embedded display label `Renegade Vita A3.5-dev79`.
Both reports lack usable private thread-register payloads, so neither a
framebuffer value nor a full engine stack is asserted.

Device-side hash verification proves the configured title-scoped user recorder
was still the stale `8a856e76b99654b1d21fde65b8040c41cc29225da91076631b5ee76be564270d`
module. The locally built guarded module is
`111d2f4f8e9e467e72a1212587d9e882d0c24e67f46e82302b9be16c565ee9a2`.
Consequently this is recorder-confounded physical failure evidence, not a
symbolicated failure in the matching Renegade SELF. The kernel companion hash
already matches and requires no replacement.

No `.mp4` was present below `ux0:/video` after the failure, so there is no
video to publish. Raw dumps, logs, and any future recordings remain excluded
from Git.

## Guarded-recorder follow-up

The stale user helper was pulled into the candidate-scoped local backup
`build/device-backups/a35-dev84-capture-policy-recorder-20260830T234415Z/`
and the guarded helper was staged, read back, and installed at the configured
title-scoped path with SHA-256
`111d2f4f8e9e467e72a1212587d9e882d0c24e67f46e82302b9be16c565ee9a2`.
The unchanged Renegade SELF read back as `555f...0bbe` after replacement.
The first attempted cross-mount atomic replacement was rejected before a write;
the successful same-mount replacement reports `atomic=false`, so the retained
local hash-bound backup is the rollback receipt.

With no synthetic gameplay input, the guarded run remained alive beyond the
former crash point. Its retained 90-second log reaches original frontend/menu
construction, original tutorial load/finalization, a 60-frame M00 scene
pre-warm, original player-control handoff, the Logan conversation/audio path,
and frame-480 checkpoints. Subsequent log samples contain physical stick/touch
activity; their actor is not inferred. Agent controls remained released.
This proves only that the optional recorder guard removes the observed immediate
recorder abort on this run. It does not prove the panel is visually correct or
that a user-requested gameplay capture was taken: the automatic capture remains
disabled and the retained checkpoints report Select unpressed.
