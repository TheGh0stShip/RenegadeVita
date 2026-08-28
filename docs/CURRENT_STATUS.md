# Current Status

Updated: 2026-08-28

## Accepted Baseline

**A3.1.4** is the latest accepted physical baseline. It proves native Vita
startup, original file/archive access, visible original M00 world/session
lifecycle, interactive player/camera ownership, and clean exit.

## Current Candidate

**A3.5-dev79** is the current hardware-test candidate. It has a successful
canonical build and has been prepared for manual physical testing, but it is
not an accepted milestone until device observations and returned logs match.

Candidate VPK:

```text
RenegadeVita-A3.5-dev79.vpk
```

VPK SHA-256:

```text
0c34f954885f097f422c4f3670ccb3d9b20fc606fb0e9416d898855c92b84d74
```

Runtime log:

```text
ux0:data/renegade/user/logs/a35-dev79-runtime.log
```

## What Dev79 Targets

- Loading screen orientation, aspect scaling, and progress-bar render order.
- Logan text/display path by enabling original TextDisplay handling.
- No-HUD M00 by admitting the original HUD/TextDisplay render path.
- Vita control mapping, including Triangle as action/use and D-pad camera,
  weapon, and objectives functions.
- Reload animation by restoring first-person default for the direct M00 route.
- NPC/Havoc skin color by avoiding Vita material tinting on textured skinned
  meshes.
- FPS regression by caching repeated native texture/render-state changes.
- Gate/opening failures by adding transition/action diagnostics.

## Still Open Until Physical Evidence Returns

- Whether the loading screen is visually correct on the Vita panel.
- Whether Logan subtitles/text appear in the original path.
- Whether NPC and Havoc materials are correct rather than merely improved.
- Whether reload animation appears with the restored first-person weapon view.
- Whether the gate opens with Triangle or records the owning transition miss.
- Whether the freeze after pistol/gate interaction is fixed or symbolicates to
  a remaining owner.
- Whether the renderer state cache recovers the observed FPS drop without new
  visual regressions.

## Useful Evidence To Return

- Runtime log from `ux0:data/renegade/user/logs/a35-dev79-runtime.log`.
- Any screenshots showing loading screen, Logan text, NPC/Havoc materials, HUD,
  gate state, and freeze point.
- Any `psp2core-*.psp2dmp` if the app crashes or the system captures a dump.
- Whether D-pad Down toggles camera view, D-pad Left/Right switch weapons, and
  Triangle interacts with the gate.
