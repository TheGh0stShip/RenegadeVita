# Current Status

Updated: 2026-08-29

## Accepted Baseline

**A3.1.4** is the latest accepted physical baseline. It proves native Vita
startup, original file/archive access, visible original M00 world/session
lifecycle, interactive player/camera ownership, and clean exit.

## Current Candidate

**A3.5-dev82** is the current hardware-test candidate. It has a successful
canonical build with the retail frontend worker integrated, a visible startup
pre-cache/pre-warm/pre-compute phase before frontend/M00 input, authored
640x480 HUD Render2D coordinate scoping, stale texture-bind cache invalidation,
and an original movie route with a compiled Vita FFmpeg Bink provider below the
original movie owner. Realtime Bink playback is disabled in this physical-test
candidate because the prior hardware return showed black-screen/audio-underrun
behavior; the candidate resolves/logs the retail movie files and fails closed to
the menu instead of stalling before M00. The earlier user-authorized FTP upload predates this current VPK; it is
not an accepted milestone until device observations and returned logs match.
The source/build/artifact checklist is tracked in
`reports/A35_DEV82_MINIMUM_DELIVERABLES.md`.

Candidate VPK:

```text
/home/steve/projects/RenegadeVitaBuilder/workspace/active/dist/RenegadeVita-A3.5-dev82.vpk
```

VPK SHA-256:

```text
e44963df636dba58687857af835489b0fb59204c25ff80169f59f77a79b062e4
```

Runtime log:

```text
ux0:data/renegade/user/logs/a35-dev82-runtime.log
```

## What Dev82 Targets

- Original retail frontend path: startup movie owner, WWUI main menu, controller
  menu navigation, and Tutorial selection handoff into the existing direct M00
  route.
- Retail intro movie route: original `MovieGameModeClass` requests the
  EA/Westwood intro files and the compiled Vita FFmpeg Bink provider remains
  available for diagnosis, but realtime playback is disabled for this candidate
  after black-screen/audio-underrun evidence. Missing or skipped movies continue
  into the original menu rather than hanging before M00.
- Loading screen coverage, status text, and progress through the original
  one-bar path, including renderer/cache prewarm.
- Visible startup pre-cache/pre-warm/pre-compute before intro movies, menu
  navigation, or M00 gameplay input. It indexes original MIX filename tables,
  touches startup movie/menu/loading/M00 files through the original
  FileFactory/MIX owners, displays for at least five seconds, and reports intro
  movie-file availability before the movie/menu route starts.
- HUD/subtitle/dialogue text path by tightening original TextDisplay/HUD
  rendering and bounds, initializing TextDisplay after final StyleMgr
  reinitialization, and initializing Render2D dynamic FVF fields used by HUD,
  subtitles, scope, loading, and bounding boxes, then restoring the previous
  DX8 viewport after fullscreen 2D passes. HUD/TextDisplay/radar/sniper/
  bounding-box owners now run under the original authored 640x480 Render2D
  coordinate space while Vita presentation remains 960x544.
- Vita control mapping: Triangle action/use, Square reload, D-pad Left/Right
  weapon-only switching, D-pad Up/Down sniper zoom, no shoulder remap.
- Reload animation by adding visible first-person weapon motion while the
  original weapon state is reload, with a bounded 0.8-second fallback when the
  retail reload HAnim is absent, short, or delayed.
- NPC/Havoc/door/powerup/objective texture orientation by preserving top-down
  retail DDS rows in gameplay uploads and applying passthrough texture-V
  correction after the original DX8 texture transform. Direct DX8/Bink GL
  texture uploads now invalidate the renderer bind cache before original mesh
  draws resume, preventing stale native texture reuse between owners.
- FPS regression by caching repeated native viewport/texture/render-state
  changes and enabling a persistent vitaGL shader-cache path.
- Gate/opening failures by adding original CombatGameMode finalization and
  preserving transition/action diagnostics.
- Sniper scope/icon placement and zoom behavior.

## Still Open Until Physical Evidence Returns

- Whether EA/Renegade/Westwood intro movie files are present, skipped cleanly in
  this candidate, and can later be realtime-decoded, synced, and skipped
  correctly on hardware.
- Whether original WWUI menu navigation works and Tutorial launches M00.
- Whether the loading screen is visually correct and fullscreen on the Vita
  panel.
- Whether Logan, Sydney, and Gunner subtitles/text appear in the original path.
- Whether NPC, Havoc, door, powerup, and objective textures/materials are
  correct rather than merely improved.
- Whether reload animation appears with the restored first-person weapon view.
- Whether the gate opens with Triangle or records the owning transition miss.
- Whether D-pad Left/Right weapon switching no longer turns the camera.
- Whether D-pad Up/Down zooms the sniper scope correctly.
- Whether sniper scope/icon placement is correct.
- Whether random ground rectangles and floating bounding boxes are fixed.
- Whether the freeze after pistol/gate interaction is fixed or symbolicates to
  a remaining owner.
- Whether the renderer state cache recovers the observed FPS drop without new
  visual regressions.

## Useful Evidence To Return

- Runtime log from `ux0:data/renegade/user/logs/a35-dev82-runtime.log`.
- Any screenshots showing intro/menu state, loading screen, Logan text,
  NPC/Havoc materials, HUD, gate state, and freeze point.
- Any `psp2core-*.psp2dmp` if the app crashes or the system captures a dump.
- Whether D-pad Left/Right switch weapons without camera drift, D-pad Up/Down
  zoom the sniper scope, Square reloads with animation, and Triangle interacts
  with the gate.
