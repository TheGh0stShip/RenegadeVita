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
- A3.5-dev87: retained physical frontend-usability failure evidence. The user
  reports absent original menu text, slow/buzzy intro A/V, and an empty original
  gameplay dialogue box; the matching partial log ends at main-menu activation.
- A3.5-dev88: published local-only follow-up to Dev87. It restored the original
  indexed glyph texture-stage combiner before menu/dialogue draws and raised the
  real BINK audio-start reserve to three decoded output buffers. It was not
  installed, launched, or physically accepted.
- A3.5-dev89: superseded canonical local-only candidate. It added original
  frontend 800×600 presentation scope, font fallback/glyph validation,
  bootstrap display flushing before filesystem/cache work, expanded UI/HUD/M00
  pre-cache touches, Render2D texture-state isolation, late BINK video-frame
  dropping for A/V pacing, and native-coordinate target-box scoping. It is not
  installed, launched, or physically accepted.
- A3.5-dev90: superseded canonical local-only candidate. It kept the
  debug/status display through original engine setup, clamped retail BINK
  uploads to an aspect-preserved 640×480 maximum, fed synchronous M00 load
  milestones into the original loading presenter, hardened FreeType/font/glyph
  atlas paths, prevented gameplay Start from entering the crashing ESC/pause
  path, and rolled back the overcorrected target-box native-coordinate
  override. It was not installed, launched, or physically accepted.
- A3.5-dev91: current canonical local-only candidate. It reduces startup
  artificial holds, downscales unchanged retail BINK uploads to 480×360 with a
  larger audio reserve and earlier late-frame dropping, adds bounded
  loading-progress catch-up renders, strengthens visible glyph probes, and adds
  bounded M00 vehicle/HMVV proximity diagnostics. It is not installed, launched,
  or physically accepted.

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
