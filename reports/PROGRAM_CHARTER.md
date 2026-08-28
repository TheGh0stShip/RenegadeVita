# Renegade Vita program charter

## Evidence-led objective

Deliver a native Vita port that retains authentic EA/Westwood Renegade engine
and gameplay ownership, uses legally user-supplied unchanged retail data, and
reaches a physically tested, representative playable campaign path. This is a
Vita-only source port, not a new game, PSP application, viewer, or asset
conversion runtime.

Evidence precedence is: immutable physical evidence with matching artifacts;
current source/build/test evidence; reconciled state/status reports; then
planning records. Build/host/Vita3K/physical results must remain distinct.

## Active status

- A3.1.4: accepted physical interactive M00 baseline.
- A3.2-dev1: frozen failed physical checkpoint: held input, inverted axes,
  perspective warp, muzzle alpha defect, and animation crash/unclean exit.
- A3.5-dev45: active automated replay-exit evidence point. It retains the
  accepted A3.1.4 baseline, later physical partial returns, the original
  loading-screen owner/capture gate, the dev35 stack-frame crash fix, the dev36
  right-stick Y boundary correction, the dev37 release-build DataSafe
  invalid-handle guard, dev38 schema-v4 returned loading-screen visual-gate
  metadata, dev39/dev40 original retail loading W3D TGA handling, dev43 clean
  route recording through gate/ladder/pistol/fire, and now automatic replay
  return to LiveArea after route exhaustion. It is not physically accepted until
  visual/audio correctness and longer first-mission stability return matching
  Vita evidence.

## Milestone contracts

| Milestone | Earned only when |
| --- | --- |
| v3.5 | A3.2 defects are fixed with host/sanitizer/ARM evidence, bounded crash/flight diagnostics and matching package exist, and physical Vita validates controls, visuals, interaction, pause/exit/restart. |
| v3.6 | Deterministic user-owned resource manifest/index/cache, measured memory/residency, repeat load/unload, tutorial plus a second campaign scene and multiplayer-map render smoke, all physically evidenced. |
| v3.7 | Perspective-correct efficient mesh submission, profiles, correct FOV/aspect, measured reproducible A/B renderer gains, and physical Balanced p95 target at or below 33.33 ms in the declared workload without regression. |
| v3.8 | Original frontend, controller navigation, initial original HUD, essential audio boundary, legal intro path/fallback, and coherent menu-to-gameplay-to-exit flow physically evidenced. |
| v3.9 | Representative campaign launch/play progression, interaction/combat/objectives/checkpoint, repeated sessions/soak, and controlled original-network direct-IP/LAN foundation. |
| v4.0 | Reproducible local asset importer, authentic representative campaign release, controls/render/HUD/audio/lifecycle/profiles/diagnostics, bounded memory, matching symbols, and honest physical evidence. |

## Non-negotiable implementation rules

Preserve original MIX/filesystem/W3D/WW3D/Combat/Commando/WWNet ownership;
replace boundaries narrowly. No custom runtime worlds, physics, game loop, or
retail redistribution. Do not deploy automatically. Every candidate preserves
VPK/ELF/map/symbol/header hashes, patch/source provenance, logs, VPK inventory,
and a telemetry-only evidence ZIP.

Performance work uses a hypothesis ledger and fixed content/camera/input replay
with correctness fingerprints. No speculative optimization, global fast-math,
or gameplay-semantic shortcut. Diagnostics use bounded local recording and no
arbitrary memory service.

Original networking remains a deliberate workstream: Direct-IP and LAN live
beneath a provider seam; W3DHub/TT is future, licensed, optional compatibility
work only. Campaign correctness has priority.
