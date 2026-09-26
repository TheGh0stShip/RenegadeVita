# Renegade Vita

An evidence-led, native ARM PlayStation Vita source port of *Command & Conquer: Renegade*. The original EA/Westwood engine remains the owner of game logic, MIX/archive access, W3D/WW3D rendering ownership, Combat, Commando, mission scripts, HUD, and networking. This project replaces only the platform boundaries needed to run that original code on Vita.

It is not a PSP/Adrenaline build, a W3D viewer, a new game engine, or an asset conversion runtime.

> **Development status — source-available development repository.** The current
> campaign candidate is **A3.5-dev194**. It passed build and host checks and was
> installed in Vita3K, but has not been launched there. The separate
> [Renegade-Vita-Demo](https://github.com/TheGh0stShip/Renegade-Vita-Demo)
> has a tutorial setup guide; its download is not a Dev194 campaign release.
> No retail data is in this repository or its VPKs. Use your own legally
> obtained retail data.

This repository publishes source code and build instructions only. It is not a public game release; it does not include retail game data or a redistributable game release.

## Where the port stands

The current campaign candidate is **A3.5-dev194**. Canonical host/sanitizer,
174 existing tests, original M00/M01 host-runtime cycles, ARM build, SELF/VPK
identity, and diagnostics packaging passed. It was installed in Vita3K but
**has not been launched**. Its VPK SHA-256 is
`8b7ba2c0bcb8a57eaee978041ca47765807492b09d14329e6c0652e4da61c15c`.
The four animated M01 models at the end of the Dev192 trace are now warmed
without retaining mutable live instances; that change has no verified runtime
result yet. See [port status](reports/PORT_STATUS.md) and
[live progress](reports/LIVE_PROGRESS.md).

| Evidence area | Current state |
| --- | --- |
| Host/build | Dev194 canonical host/sanitizer, 174 existing tests, M00/M01 host-runtime cycles, ARM, package identity, and diagnostics passed. The two new source contracts passed directly after build and are registered for the next canonical run. |
| Vita3K | Dev194 installed, **not launched**. Earlier candidate traces show M13 completion and M01 entry, but M01 aircraft startup and other reported faults remain unresolved. |
| Physical Vita/PSTV | A3.1.4 remains the accepted physical baseline for native startup, visible original M00 world/session lifecycle, player/camera ownership, and clean exit. Dev134 deployment/readback was verified without a corresponding physical runtime return. Issue #1 reports Dev142 PSTV tutorial and M01 observations, including blocked progression and save/load; these are user reports, not Dev194 acceptance. |
| Visual evidence | The gallery contains labelled historical frames. Earlier Vita3K images and Dev87 physical recorder stills do not prove Dev194 visual or physical acceptance. |

Read the concise [current status](docs/CURRENT_STATUS.md) before treating any candidate as playable. The durable engineering record is in [reports/PORT_STATUS.md](reports/PORT_STATUS.md); it distinguishes host, Vita3K, and physical-Vita evidence.

## Visual evidence, honestly presented

The [historical screenshot timeline](docs/HISTORICAL_SCREENSHOT_TIMELINE.md) contains the reviewed GitHub-hosted frames, their labels, hashes, and diagnostic inventory. It intentionally does not fill later builds with black, loading, or early-frame captures just to create a visual sequence. Dev87's six frames are derived from the user-finalized physical-Vita recorder output and remain explicitly failure-context evidence, not acceptance proof.

<table>
<tr>
<td width="25%"><img src="docs/history/screenshots/a31-vita-log-select-capture-f2278.png" width="210" alt="A3.1 early visible M00 world"><br>A3.1 — early visible M00 world</td>
<td width="25%"><img src="docs/history/screenshots/a35-dev5-walk-manual.png" width="210" alt="A3.5-dev5 manual M00 movement"><br>Dev5 — manual M00 movement</td>
<td width="25%"><img src="docs/history/screenshots/a35-dev13-selected-frame.png" width="210" alt="A3.5-dev13 material-defect route frame"><br>Dev13 — material-defect route frame</td>
<td width="25%"><img src="docs/history/screenshots/a35-dev86-vita-original-loading-screen-level-ready-t119137636-annotated.png" width="210" alt="A3.5-dev86 diagnostic loading frame with absent UI labels"><br>Dev86 — diagnostic loading frame, not gameplay</td>
</tr>
</table>

<table>
<tr>
<td width="33%"><img src="docs/history/screenshots/a35-dev87-vita-recorder-m00-exterior-npc-t0040s.png" width="260" alt="A3.5-dev87 recorder-derived exterior NPC encounter"><br>Dev87 — recorder-derived exterior M00 evidence</td>
<td width="33%"><img src="docs/history/screenshots/a35-dev87-vita-recorder-m00-warfactory-door-t0080s.png" width="260" alt="A3.5-dev87 recorder-derived war-factory door approach"><br>Dev87 — recorder-derived war-factory approach</td>
<td width="33%"><img src="docs/history/screenshots/a35-dev87-vita-recorder-m00-interior-console-t0120s.png" width="260" alt="A3.5-dev87 recorder-derived M00 interior console"><br>Dev87 — recorder-derived interior M00 evidence</td>
</tr>
</table>

Those images are historical, not a same-camera benchmark. A verified post-render VDB capture sequence will replace ad-hoc engine-timed capture for future comparison frames.

## Start here

- [Quickstart](docs/QUICKSTART.md) — clone and produce a local canonical or fast candidate build.
- [Installing on Vita](docs/INSTALLING.md) — retail-data boundaries and manual installation safeguards.
- [Current status](docs/CURRENT_STATUS.md) — accepted baseline, historical build checkpoints, Dev194 campaign evidence, and open runtime gates.
- [Evidence and capture policy](docs/EVIDENCE.md) — what images, logs, videos, and builds can and cannot prove.
- [Historical screenshot timeline](docs/HISTORICAL_SCREENSHOT_TIMELINE.md) — reviewed visual history and complete image manifest.
- [Historical capture campaign](docs/HISTORICAL_CAPTURE_CAMPAIGN.md) — the no-rebuild plan for comparable in-game frames, held until a physical session is explicitly authorized.
- [Controls](docs/CONTROLS.md) — current mapping and known lifecycle caveat.
- [Building](docs/BUILDING.md), [development](docs/DEVELOPMENT.md), and [troubleshooting](docs/TROUBLESHOOTING.md) — contributor workflow.

## Build locally

WSL2 Ubuntu or Linux with VitaSDK is the supported host environment.

```bash
git clone --recurse-submodules https://github.com/TheGh0stShip/RenegadeVita.git
cd RenegadeVita
git submodule update --init --recursive
bash ./tools/build.sh
```

`tools/build.sh` is the canonical candidate path. It preserves validation, deterministic staging, ARM package identity, diagnostics, and retail-exclusion checks. A fast build is useful for iteration only; it never substitutes for a canonical candidate or physical proof.

## Project boundaries

- `upstream/CnC_Renegade/` is the pinned official released source and stays pristine.
- `port/` holds Vita boundaries, compatibility work, renderer/audio providers, validation, and deterministic staging patches.
- `staging/` is generated; do not edit it as the source of record.
- `reports/` holds durable evidence and status. Generated build outputs, logs, raw captures/videos, dumps, retail data, saves, and credentials are excluded from Git.

## License and retail data

The released Renegade source carries GPLv3 plus EA's additional terms; see the upstream notice after initializing the submodule. You must supply your own retail data at `ux0:data/renegade/retail/Data/`. The application writes only to `ux0:data/renegade/user/`.

See [LICENSE.md](LICENSE.md), [CONTRIBUTING.md](CONTRIBUTING.md), and [SECURITY.md](SECURITY.md) before contributing or sharing diagnostics.
