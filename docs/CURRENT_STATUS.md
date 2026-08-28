# Current Status

Updated: 2026-08-28

## Accepted Baseline

**A3.1.4** is the latest accepted physical baseline. It proves native Vita
startup, original file/archive access, visible original M00 world/session
lifecycle, interactive player/camera ownership, and clean exit.

## Current Candidate

**A3.5-dev82** is the current hardware-test candidate. It has a successful
canonical build and has been uploaded by user-authorized VitaShell FTP, but it
is not an accepted milestone until device observations and returned logs match.

Candidate VPK:

```text
RenegadeVita-A3.5-dev82.vpk
```

VPK SHA-256:

```text
0bd150942a13e39a84277449637e2ca7ce9a5ccce4329dcd2b05695fb4a24750
```

Runtime log:

```text
ux0:data/renegade/user/logs/a35-dev82-runtime.log
```

## What Dev82 Targets

- Loading screen coverage, status text, and progress through the original
  one-bar path, including renderer/cache prewarm.
- HUD/subtitle/dialogue text path by tightening original TextDisplay/HUD
  rendering and bounds.
- Vita control mapping: Triangle action/use, Square reload, D-pad Left/Right
  weapon-only switching, D-pad Up/Down sniper zoom, no shoulder remap.
- Reload animation by adding visible first-person weapon motion while the
  original weapon state is reload.
- NPC/Havoc/door/powerup/objective texture orientation by preserving top-down
  retail DDS rows in gameplay uploads.
- FPS regression by caching repeated native viewport/texture/render-state
  changes and enabling a persistent vitaGL shader-cache path.
- Gate/opening failures by adding original CombatGameMode finalization and
  preserving transition/action diagnostics.
- Sniper scope/icon placement and zoom behavior.

## Still Open Until Physical Evidence Returns

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
- Any screenshots showing loading screen, Logan text, NPC/Havoc materials, HUD,
  gate state, and freeze point.
- Any `psp2core-*.psp2dmp` if the app crashes or the system captures a dump.
- Whether D-pad Left/Right switch weapons without camera drift, D-pad Up/Down
  zoom the sniper scope, Square reloads with animation, and Triangle interacts
  with the gate.
