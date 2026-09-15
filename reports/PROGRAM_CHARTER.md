# Renegade Vita program charter

## Evidence-led objective

Deliver a complete native PlayStation Vita port of Renegade, retaining authentic
EA/Westwood engine and gameplay ownership and using legally user-supplied,
unchanged retail data. The durable end-state is the complete game, not M00,
a demo, or only a representative campaign slice. Full campaign coverage,
original gameplay/presentation systems, lifecycle stability, performance, and
original networking capability through supported provider boundaries remain
tracked toward that end-state. This is not a new game, PSP application, viewer,
or asset-conversion runtime.

The user's 2026-09-08 clarification makes the M00-only community demo an interim
showcase of the Renegade Vita project's work. Its release gates do not replace
the full-port roadmap. Demo-only launch restrictions and completion credits
belong to a separate build profile, not permanent restrictions on the engine.
The existing representative-campaign milestones are intermediate deliveries,
not a declaration that the full port is finished. The target remains 60 FPS+.
Final physical acceptance requires both PS Vita and PSTV; physical testing is
authorized on PS Vita by the user's 2026-09-14 full-demo test request.
PSTV testing remains on hold. Earlier emulator evidence does not establish
physical correctness, and emulator incompatibilities alone do not justify
changes to the native port.

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
- A3.5-dev91: superseded canonical local-only candidate. It reduces startup
  artificial holds, downscales unchanged retail BINK uploads to 480×360 with a
  larger audio reserve and earlier late-frame dropping, adds bounded
  loading-progress catch-up renders, strengthens visible glyph probes, and adds
  bounded M00 vehicle/HMVV proximity diagnostics. It is not installed, launched,
  or physically accepted.
- A3.5-dev92: superseded canonical local-only candidate. It measures FreeType
  glyph cells from advance plus bitmap bearings to avoid clipped text strips,
  strengthens visible glyph-column probes, lowers BINK upload/update work to a
  320×240 cap with explicit decoder audio-layout fallback, and adds bounded
  target-box projection diagnostics. It is not installed, launched, or
  physically accepted.
- A3.5-dev93: superseded canonical local-only candidate. It holds/repaints early
  native bootstrap status, fixes Render2D text-atlas height allocation and
  independent UV scaling, adds bounded text/dialog diagnostics, and scopes
  gameplay HUD/TextDisplay presentation to native 960×544. It is not
  installed, launched, or physically accepted.
- A3.5-dev94: superseded canonical local-only candidate. It keeps the startup
  framebuffer visible through WW3D initialization, routes synchronous saveload
  status/count changes into the loading presenter, applies deferred DX8 render
  state before indexed Render2D text/HUD draws, scopes HUD `Think()` geometry
  through native gameplay presentation, and drops late BINK video frames when
  audio is under pressure. It is not installed, launched, or physically
  accepted.
- A3.5-dev95: superseded canonical local-only candidate. It preserves Dev94 and
  adds a `MessageWindowClass` presentation-scope guard for update-time
  dialogue/message text layout and cached glyph geometry. It is not installed,
  launched, or physically accepted.
- A3.5-dev96: superseded canonical local-only candidate. It preserves Dev95 and
  adds UTF-16-safe Vita wrappers for `wcsncmp`, `wcsncpy`, `wcschr`, and
  `wcsstr` so original Windows `WCHAR` frontend/dialogue/HUD text does not
  cross into the wrong libc `wchar_t` ABI. It is not installed, launched, or
  physically accepted.
- A3.5-dev97: superseded canonical local-only candidate. It preserves Dev96 and
  adds bounded UTF-16 formatted-output support for original menu/dialogue/HUD
  formatted strings, plus candidate-scoped startup-precache receipt/status
  output before original retail root/MIX file factory construction. It is not
  installed, launched, or physically accepted.
- A3.5-dev98: superseded canonical local-only candidate. It preserves Dev97 and
  adds BINK presentation-clock arming at audio/video presentation, bounded
  Vita WWUI dialog-template translation copying, and HUD initialization
  presentation scoping so persistent Render2D HUD elements are born in native
  Vita HUD space. It is not installed, launched, or physically accepted.
- A3.5-dev99: current canonical local-only candidate. It preserves Dev98 and
  adds a native startup-status repaint worker so verbose debug status is
  redrawn during the long original root/MIX factory construction phase before
  visible pre-cache. It is not installed, launched, captured, or physically
  accepted.

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
