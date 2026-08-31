# Capability roadmap

| Milestone | Capability contract | Status |
|---|---|---|
| A3.1.4 | Visible original interactive M00 lifecycle | physically validated; frozen |
| A3.2 | Frozen failed physical evidence: input, animation, projection, material, and exit defects | `A3.2-dev1` immutable; never promote from it |
| v3.5 | Correctness and flight recorder: repair A3.2 defects; matching diagnostic candidate | `A3.5-dev87` is retained physical frontend-usability failure evidence: menu text remained absent, intro A/V was slow/buzzy, and the original dialogue box was empty. `A3.5-dev88` through `A3.5-dev93` are local-only history. `A3.5-dev94` is the current local-only canonical follow-up: it keeps the startup framebuffer visible through WW3D init, routes synchronous saveload status/count changes into the loading presenter, applies deferred DX8 render state before indexed Render2D text/HUD draws, scopes HUD `Think()` geometry through native gameplay presentation, and drops late BINK video frames when audio is under pressure. Intro/menu A/V/text, loading/HUD/dialogue/pickup text, shadows/walls, START-exit, HMVV freeze, and FPS defects remain physically open. |
| v3.6 | Resource, memory, deterministic cache/index, tutorial plus second scene and map smoke | pending v3.5 physical gate |
| v3.7 | Perspective-correct efficient renderer and measured Balanced frame pacing | pending v3.6 infrastructure |
| v3.8 | Original frontend, HUD, essential audio, intro path/fallback | host/ARM closure exists; physical integration pending |
| v3.9 | Representative campaign RC and controlled Direct-IP/LAN foundation | deferred until campaign stability |
| v4.0 | First genuinely playable representative campaign release | deferred; future W3DHub/TT provider remains tracked but optional |

Public milestone identity is reserved for earned capability contracts. Builds and
host-only iterations use internal identities such as `A3.2-devN` and
`A3.2-RC1`.
