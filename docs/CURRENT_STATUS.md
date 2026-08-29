# Current Status

Updated: 2026-08-28

## Accepted Baseline

**A3.1.4** is the latest accepted physical baseline. It proves native Vita
startup, original file/archive access, visible original M00 world/session
lifecycle, interactive player/camera ownership, and clean exit.

## Current Candidate

**A3.5-dev82** is the current hardware-test candidate. It has a successful
canonical build with the retail frontend worker integrated and a real Vita
FFmpeg Bink playback boundary wired below the original movie owner. It is not
an accepted milestone until device observations and returned logs match.

Candidate VPK:

```text
/home/steve/projects/RenegadeVitaBuilder/workspace/active/dist/RenegadeVita-A3.5-dev82.vpk
```

VPK SHA-256:

```text
3be156223c7ace92e10d42eabc0e39a1ca90a6920c1491678559be061f50c4ea
```

Runtime log:

```text
ux0:data/renegade/user/logs/a35-dev82-runtime.log
```

## What Dev82 Targets

- Original retail frontend path: startup movie owner, WWUI main menu, controller
  menu navigation, and Tutorial selection handoff into the existing direct M00
  route.
- Retail intro movie playback: Vita FFmpeg Bink video/audio decode without RAD
  code and without packaging retail movie assets in the VPK.
- Loading screen coverage, status text, and progress through the original
  one-bar path, including renderer/cache prewarm.
- HUD/subtitle/dialogue text path by tightening original TextDisplay/HUD
  rendering and bounds, initializing TextDisplay after final StyleMgr
  reinitialization, and initializing Render2D dynamic FVF fields used by HUD,
  subtitles, scope, loading, and bounding boxes, then restoring the previous
  DX8 viewport after fullscreen 2D passes.
- Vita control mapping: Triangle action/use, Square reload, D-pad Left/Right
  weapon-only switching, D-pad Up/Down sniper zoom, no shoulder remap.
- Reload animation by adding visible first-person weapon motion while the
  original weapon state is reload, with a bounded 0.8-second fallback when the
  retail reload HAnim is absent, short, or delayed.
- NPC/Havoc/door/powerup/objective texture orientation by preserving top-down
  retail DDS rows in gameplay uploads and applying passthrough texture-V
  correction after the original DX8 texture transform.
- FPS regression by caching repeated native viewport/texture/render-state
  changes and enabling a persistent vitaGL shader-cache path.
- Gate/opening failures by adding original CombatGameMode finalization and
  preserving transition/action diagnostics.
- Sniper scope/icon placement and zoom behavior.

## Still Open Until Physical Evidence Returns

- Whether EA/Renegade/Westwood intro movies play, sync, and skip correctly on
  hardware.
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
