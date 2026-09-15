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

Current Dev100 work supplies shared movie/text/loading/cache correctness fixes
plus an interim M00 ending. Keep that ending and launch restriction selectable
as a demo build profile so full-port development remains unrestricted. Current
canonical compilation is frozen to its source snapshot; profile separation is
the next source unit, not a mid-build mutation. See `DEV100_PRIOR_WORK_AUDIT.md`.

| Milestone | Capability contract | Status |
|---|---|---|
| A3.1.4 | Visible original interactive M00 lifecycle | physically validated; frozen |
| A3.2 | Frozen failed physical evidence: input, animation, projection, material, and exit defects | `A3.2-dev1` immutable; never promote from it |
| v3.5 | Correctness and flight recorder: repair A3.2 defects; matching diagnostic candidate | `A3.5-dev87` is retained physical frontend-usability failure evidence: menu text remained absent, intro A/V was slow/buzzy, and the original dialogue box was empty. `A3.5-dev88` through `A3.5-dev98` are local-only history. `A3.5-dev99` is the current local-only canonical follow-up: it keeps Dev98's startup/loading/deferred Render2D/HUD/BINK/message-window/short-wchar/UTF-16 formatter/WWUI/HUD-presentation fixes and adds a native startup-status repaint worker for the long pre-cache black interval. Intro/menu A/V/text, loading/HUD/dialogue/pickup text, shadows/walls, START-exit, HMVV freeze, and FPS defects remain physically open. |
| v3.6 | Resource, memory, deterministic cache/index, tutorial plus second scene and map smoke | pending v3.5 physical gate |
| v3.7 | Perspective-correct efficient renderer and measured Balanced frame pacing | pending v3.6 infrastructure |
| v3.8 | Original frontend, HUD, essential audio, intro path/fallback | host/ARM closure exists; physical integration pending |
| v3.9 | Representative campaign RC and controlled Direct-IP/LAN foundation | deferred until campaign stability |
| v4.0 | First genuinely playable representative campaign release | deferred; future W3DHub/TT provider remains tracked but optional |

Public milestone identity is reserved for earned capability contracts. Builds and
host-only iterations use internal identities such as `A3.2-devN` and
`A3.2-RC1`.
