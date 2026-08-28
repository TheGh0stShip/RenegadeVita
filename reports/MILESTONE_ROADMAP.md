# Capability roadmap

| Milestone | Capability contract | Status |
|---|---|---|
| A3.1.4 | Visible original interactive M00 lifecycle | physically validated; frozen |
| A3.2 | Frozen failed physical evidence: input, animation, projection, material, and exit defects | `A3.2-dev1` immutable; never promote from it |
| v3.5 | Correctness and flight recorder: repair A3.2 defects; matching diagnostic candidate | `A3.5-dev79` is the current source/build/package and manual physical-test candidate. It preserves the dev48-dev78 audio/texture/material/render-state chain and targets the latest physical defects: loading-screen orientation/scaling/progress, missing HUD/TextDisplay/Logan text, camera-Y inversion, action/use mapping, reload/camera controls, NPC/Havoc skin materials, FPS state churn, gate interaction diagnostics, and freeze triage. Physical acceptance remains pending; soak remains v3.9 |
| v3.6 | Resource, memory, deterministic cache/index, tutorial plus second scene and map smoke | pending v3.5 physical gate |
| v3.7 | Perspective-correct efficient renderer and measured Balanced frame pacing | pending v3.6 infrastructure |
| v3.8 | Original frontend, HUD, essential audio, intro path/fallback | host/ARM closure exists; physical integration pending |
| v3.9 | Representative campaign RC and controlled Direct-IP/LAN foundation | deferred until campaign stability |
| v4.0 | First genuinely playable representative campaign release | deferred; future W3DHub/TT provider remains tracked but optional |

Public milestone identity is reserved for earned capability contracts. Builds and
host-only iterations use internal identities such as `A3.2-devN` and
`A3.2-RC1`.
