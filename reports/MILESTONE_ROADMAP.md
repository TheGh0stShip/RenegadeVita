# Capability roadmap

2026-09-27 checkpoint: Dev202 is the current published fast ARM/Vita3K Practice
candidate. Original Practice/C&C loading-backdrop selection and MultiHUD link;
Practice loading and spawn now have bounded Vita3K evidence, but full Practice
gameplay remains unverified. Dev200's RenCorner
purchase response and Dev195's join/movement evidence are earlier Vita3K
results. Campaign completion, full multiplayer and physical performance remain
open. Current evidence: [multiplayer](MULTIPLAYER_COMPATIBILITY.md). These
checkpoints do not close a physical release gate or establish sustained 60 FPS.

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

Dev100 established the preserved demo/full-port split. Dev134 is a historical
physical deployment checkpoint, not current runtime acceptance. Earlier
campaign runs completed M13 and entered M01 with unresolved stalls, cinematic
pacing and actor defects. Dev195 multiplayer evidence does not resolve them.

| Milestone | Capability contract | Status |
|---|---|---|
| A3.1.4 | Visible original interactive M00 lifecycle | physically validated; frozen |
| A3.2 | Frozen failed physical evidence: input, animation, projection, material, and exit defects | `A3.2-dev1` immutable; never promote from it |
| v3.5 | Correctness and flight recorder: repair A3.2 defects; matching diagnostic candidate | Dev202 is the current published development candidate. Historical physical failures remain immutable; new physical correctness and performance gates remain open. |
| v3.6 | Resource, memory, deterministic cache/index, tutorial plus second scene and map smoke | pending v3.5 physical gate |
| v3.7 | Perspective-correct efficient renderer and measured Balanced frame pacing | pending v3.6 infrastructure |
| v3.8 | Original frontend, HUD, essential audio, intro path/fallback | host/ARM closure exists; physical integration pending |
| v3.9 | Representative campaign RC and controlled Direct-IP/LAN foundation | Direct TT join and package mounting now observed in Vita3K; purchase UI, full gameplay, campaign stability and physical validation remain open. |
| v4.0 | First genuinely playable representative campaign release | Not accepted. Full campaign and multiplayer remain separate completion gates. |

Public milestone identity is reserved for earned capability contracts. Builds and
host-only iterations use internal identities such as `A3.2-devN` and
`A3.2-RC1`.
