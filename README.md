# Renegade Vita

Renegade Vita is a native PlayStation Vita port of *Command & Conquer:
Renegade*. The project uses EA/Westwood's released source as the gameplay and
engine owner, reads unchanged retail Renegade data, and replaces only platform
boundaries such as Win32, DirectInput, DirectX 8, Miles, Bink, and desktop
filesystem behavior.

This is not a PSP/Adrenaline build, a W3D viewer, an asset-conversion runtime,
or a replacement Renegade engine.

## Historical Visual Progress

The first project artifact a GitHub reader sees is a gameplay-first visual progression grid. It deliberately excludes black/logo, magenta diagnostic, and loading-only frames; the clearly labelled Dev82 block below is the sole exception, so the returned physical evidence is visible without being misrepresented as gameplay.
The full [historical screenshot timeline](docs/HISTORICAL_SCREENSHOT_TIMELINE.md) includes every useful gameplay screenshot found per build, the four exact returned Dev82 diagnostic frames, and a complete manifest of all GitHub-hosted evidence PNGs.

<table>
<tr>
<td width="20%"><img src="docs/history/screenshots/a31-vita-log-select-capture-f2278.png" width="180" alt="Select Capture F2278"></td>
<td width="20%"><img src="docs/history/screenshots/a35-dev5-spawn-control.png" width="180" alt="Spawn Control"></td>
<td width="20%"><img src="docs/history/screenshots/a35-dev5-walk-manual.png" width="180" alt="Walk Manual"></td>
<td width="20%"><img src="docs/history/screenshots/a35-dev5-vita-manual-select-interactive-f355-t39869172.png" width="180" alt="Vita Manual Select Interactive F355 T39869172"></td>
<td width="20%"><img src="docs/history/screenshots/a35-dev7-effects-131326.png" width="180" alt="Effects 131326"></td>
</tr>
<tr>
<td width="20%"><img src="docs/history/screenshots/a35-dev7-vita-manual-select-interactive-f1527-t61897982.png" width="180" alt="Vita Manual Select Interactive F1527 T61897982"></td>
<td width="20%"><img src="docs/history/screenshots/a35-dev13-selected-frame.png" width="180" alt="Selected Frame"></td>
<td width="20%"><img src="docs/history/screenshots/a35-dev13-npc-crop.png" width="180" alt="Npc Crop"></td>
<td width="20%"><img src="docs/history/screenshots/a35-dev16-selected-frame.png" width="180" alt="Selected Frame"></td>
<td width="20%"><img src="docs/history/screenshots/a35-dev17-selected-frame.png" width="180" alt="Selected Frame"></td>
</tr>
<tr>
<td width="20%"><img src="docs/history/screenshots/a35-dev18-capture2.png" width="180" alt="Capture2"></td>
<td width="20%"><img src="docs/history/screenshots/a35-dev18-vita-manual-select-interactive-f2184-t75384736.png" width="180" alt="Vita Manual Select Interactive F2184 T75384736"></td>
<td width="20%"><img src="docs/history/screenshots/a35-dev19-vita-manual-select-interactive-f2570-t85917941.png" width="180" alt="Vita Manual Select Interactive F2570 T85917941"></td>
<td width="20%"><img src="docs/history/screenshots/a35-dev19-npc-detail-crop.png" width="180" alt="Npc Detail Crop"></td>
<td width="20%"><img src="docs/history/screenshots/a35-dev19-vita-manual-select-interactive-f4146-t118405956.png" width="180" alt="Vita Manual Select Interactive F4146 T118405956"></td>
</tr>
</table>

### A3.5-dev82 — Returned Physical Diagnostic Frames

These are the four raw physical-Vita capture records returned for Dev82. They document two inverted loading presentations, a byte-identical loading-image capture marked first-interactive, and a black initial interactive capture with a partial HUD; they are diagnostic evidence only, not gameplay acceptance.

<table>
<tr>
<td width="50%"><img src="docs/history/screenshots/a35-dev82-vita-original-loading-screen-t54494725.png" width="260" alt="Original loading frame t54494725 — full-frame vertically inverted loading UI"><br>Original loading frame t54494725 — full-frame vertically inverted loading UI</td>
<td width="50%"><img src="docs/history/screenshots/a35-dev82-vita-original-loading-screen-t67280479.png" width="260" alt="Original loading frame t67280479 — letterboxed vertically inverted loading UI"><br>Original loading frame t67280479 — letterboxed vertically inverted loading UI</td>
</tr>
<tr>
<td width="50%"><img src="docs/history/screenshots/a35-dev82-vita-first-interactive-frame-t64590857.png" width="260" alt="First interactive record t64590857 — byte-identical to full-frame inverted loading image"><br>First interactive record t64590857 — byte-identical to full-frame inverted loading image</td>
<td width="50%"><img src="docs/history/screenshots/a35-dev82-vita-first-interactive-frame-t88041059.png" width="260" alt="First interactive frame t88041059 — black framebuffer with partial weapon/ammo HUD"><br>First interactive frame t88041059 — black framebuffer with partial weapon/ammo HUD</td>
</tr>
</table>

## Current State

The current engineering candidate is **A3.5-dev82**. It builds, links, packages
as a native Vita VPK, and is waiting on physical M00 tutorial validation for
the latest fixes to loading-screen coverage/text/progress, combined loading
prewarm, HUD/text display, dialogue subtitles, controls, reload/sniper
behavior, character/door/powerup/objective texture orientation, original
CombatGameMode finalization, transition diagnostics, and renderer state churn.

Dev82 also source-routes the original startup movie and retail main-menu owners.
Its Vita movie boundary uses a reproducible, Bink-only FFmpeg software build to
decode the user-owned `EA_WW.BIK` and `R_INTRO.BIK` files in place; neither
retail movies nor proprietary RAD code are included in the repository or VPK.

The latest accepted physical baseline is **A3.1.4**, which proves visible
interactive M00 lifecycle. Later A3.5 builds are internal candidates until the
matching VPK, logs, and physical Vita observations pass their gates.

Start here:

- [Quickstart](docs/QUICKSTART.md) for cloning, building, and installing.
- [Current Status](docs/CURRENT_STATUS.md) for what works and what is still
  under test.
- [Controls](docs/CONTROLS.md) for the current Vita input map.
- [Demo Capture](docs/DEMO_CAPTURE.md) for the non-USB PSVITA/PSTV recording
  workflow.
- [Architecture](docs/ARCHITECTURE.md) for the source-port boundaries.
- [Development](docs/DEVELOPMENT.md) for how to modify the port safely.
- [Troubleshooting](docs/TROUBLESHOOTING.md) for common build/runtime failures.

## Repository Layout

- `upstream/CnC_Renegade/` is the pinned official EA source submodule.
- `port/` contains Vita platform, renderer, audio, filesystem, compatibility,
  validation, and patch material.
- `port/patches/` contains deterministic patches applied to staged copies of
  upstream source.
- `staging/` is generated by `tools/stage_sources.sh`; do not treat it as the
  source of record.
- `tools/` contains the canonical build, staging, validation, packaging,
  diagnostics, and optional device-helper scripts.
- `reports/` contains durable engineering evidence, status records, milestone
  records, and generated integration reports.
- `dist/`, `build/`, and `logs/` are generated local outputs and are ignored.

## Build

WSL2 Ubuntu plus VitaSDK is the supported development environment. From the
repo root:

```bash
git submodule update --init --recursive
bash ./tools/build.sh
```

The build writes a VPK, ELF, map, logs, source-integration report, identity
report, and diagnostics bundle to `dist/` under the managed builder root when
available, otherwise under the checkout.

The optional Windows wrapper only launches the same Bash script:

```powershell
.\RenegadeVita_BUILD.ps1
```

## Install

The VPK contains only `eboot.bin` and `sce_sys/param.sfo`. It does not contain
retail Renegade assets.

The Vita must already have user-owned retail data at:

```text
ux0:data/renegade/retail/Data/
```

Writable runtime files go under:

```text
ux0:data/renegade/user/
```

See [Installing](docs/INSTALLING.md) for manual VitaShell and FTP workflows.

## License And Retail Data

EA's released Renegade source is GPLv3 with additional terms. The upstream
notice is available in `upstream/CnC_Renegade/LICENSE.md` after submodule
initialization. You must own the retail game to use its data; no retail assets
are included in this repository.
