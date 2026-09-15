# Capability roadmap

2026-09-15 checkpoint: Dev134 canonical/package/matching Vita3K visual milestone
PASS; physical deployment/readback verified under the user's post-milestone test
authorization. Manual LiveArea launch is required (remote command1338 refused).
This engineering checkpoint does not close any physical release gate or prove
60 FPS. Current execution: DEV134_PHYSICAL_MILESTONE.md. Older candidate labels
in the roadmap table below describe historical evidence.

## Durable destination and interim demo

The end-goal is the complete native Renegade Vita port. The M00-only community
demo is an interim showcase that identifies the Renegade Vita project's porting
work; it is not a replacement for the game or the completion criterion for
this roadmap. Likewise, v4.0's representative campaign release is an
intermediate capability milestone, not full-game completion.

After the representative campaign milestones, expand evidence to every
campaign mission and its original dependencies, complete remaining original
presentation/gameplay/lifecycle systems, and validate original networking
through the supported provider boundaries. Do not invent a public release
number or claim these gates have passed. Preserve original owners and retail
formats throughout. Both PS Vita and PSTV final validation remain required.

Dev100 established the interim demo/full-port profile split and is now
historical. Current work is Dev134: canonical host/sanitizer/ARM/package
closure and matching Vita3K visual evidence passed, and the exact package was
deployed/readback-verified on physical Vita. Physical runtime logs, visuals,
audio and frame-time evidence are pending manual LiveArea launch. See
`DEV134_PHYSICAL_MILESTONE.md`.

| Milestone | Capability contract | Status |
|---|---|---|
| A3.1.4 | Visible original interactive M00 lifecycle | physically validated; frozen |
| A3.2 | Frozen failed physical evidence: input, animation, projection, material, and exit defects | `A3.2-dev1` immutable; never promote from it |
| v3.5 | Correctness and flight recorder: repair A3.2 defects; matching diagnostic candidate | `A3.5-dev87` is retained physical frontend-usability failure evidence. `A3.5-dev88` through `A3.5-dev123` are superseded source/build/Vita3K history, with Dev123 also retaining a failed physical launch/recovery. Dev124 and Dev126 returned physical failure/debug evidence. `A3.5-dev134` is the current checkpoint: canonical/package and matching Vita3K visual milestone passed, and physical deployment/readback is verified. Intro/menu A/V/text, loading/HUD/dialogue/pickup text, shadows/walls, START-exit, Logan/HMVV/Mobius stability, and native FPS remain physically open until the Dev134 runtime return is collected. |
| v3.6 | Resource, memory, deterministic cache/index, tutorial plus second scene and map smoke | pending v3.5 physical gate |
| v3.7 | Perspective-correct efficient renderer and measured Balanced frame pacing | pending v3.6 infrastructure |
| v3.8 | Original frontend, HUD, essential audio, intro path/fallback | host/ARM closure exists; physical integration pending |
| v3.9 | Representative campaign RC and controlled Direct-IP/LAN foundation | deferred until campaign stability |
| v4.0 | First genuinely playable representative campaign release | deferred; future W3DHub/TT provider remains tracked but optional |

Public milestone identity is reserved for earned capability contracts. Builds and
host-only iterations use internal identities such as `A3.2-devN` and
`A3.2-RC1`.
