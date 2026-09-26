# Renegade Vita

An evidence-led, native ARM PlayStation Vita source port of *Command & Conquer: Renegade*. The original EA/Westwood engine remains the owner of game logic, MIX/archive access, W3D/WW3D rendering ownership, Combat, Commando, mission scripts, HUD, and networking. This project replaces only the platform boundaries needed to run that original code on Vita.

It is not a PSP/Adrenaline build, a W3D viewer, a new game engine, or an asset conversion runtime.

> **Current development candidate: A3.5-dev195.** The native ARM client joined
> RenCorner in Vita3K, downloaded server packages, rendered City_U1, accepted
> movement input, and returned cleanly to the menu. Full multiplayer, complete
> campaign progression, and physical Vita performance remain unverified.

[Download Dev195](https://github.com/TheGh0stShip/RenegadeVita/releases/tag/A3.5-dev195)
| [Setup](docs/INSTALLING.md) | [Current status](docs/CURRENT_STATUS.md)
| [Multiplayer setup](docs/MULTIPLAYER.md)

Development prereleases contain the executable and package metadata only. This
is not a finished game release. Supply your own legally obtained retail data.
The separate [tutorial demo](https://github.com/TheGh0stShip/Renegade-Vita-Demo)
is preserved; its data subset is not sufficient for the full-port candidate.

## Where the port stands

Dev195 is a **fast-build development checkpoint**, installed and run in
Vita3K. It is not canonical or physical acceptance. See the
[candidate report](reports/DEV195_RENCORNER_NATIVE_JOIN.md) for hashes,
verification scope, performance caveats, and remaining defects.

| Evidence area | Current state |
| --- | --- |
| Accepted physical baseline | **A3.1.4**: native startup, original M00 world/session lifecycle, player/camera ownership, and clean exit. |
| Dev195 build | 171 fast contracts and the original DDS alias test passed; 266 deterministic patches; ARM ELF/SELF/VPK produced and installation hashes verified. |
| Dev195 multiplayer | Vita3K joined RenCorner, mounted five packages, rendered 9,723 frames, moved the player, and completed session teardown. The public list showed `PSVita`; the client requested `PS Vita`. The name-normalization boundary is unresolved. |
| Remaining multiplayer work | Purchase dialog did not appear; early text had malformed glyphs. Combat, vehicles, death/respawn, chat, round transitions, and sustained performance are not accepted. |
| Campaign | Earlier runs completed M13 and entered M01. M13 cinematic/effects/animation defects and M01 stalls remain open; Dev195's multiplayer test does not resolve them. |
| Physical testing | Dev134 deployment/readback is historical, not Dev195 acceptance. Issue #1 contains Dev142 PSTV user observations, including blocked progression and save/load. No Dev195 physical test is claimed. |
| Visual evidence | The gallery below is historical. Emulator captures and historical physical stills do not establish current physical acceptance or stable 60 FPS. |

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
- [Current status](docs/CURRENT_STATUS.md) — Dev195 evidence, campaign limitations, and physical gates.
- [Multiplayer](docs/MULTIPLAYER.md) — experimental direct entry, private identity, trusted TLS, and downloaded-asset boundaries.
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
RENEGADE_CANDIDATE_LABEL=A3.5-dev195 RENEGADE_M00_DEMO=0 bash ./tools/build.sh
```

`tools/build.sh` is the canonical candidate path. It preserves validation, deterministic staging, ARM package identity, diagnostics, and retail-exclusion checks. A fast build is useful for iteration only; it never substitutes for a canonical candidate or physical proof.

## Project boundaries

- `upstream/CnC_Renegade/` is the pinned official released source and stays pristine.
- `port/` holds Vita boundaries, compatibility work, renderer/audio providers, validation, and deterministic staging patches.
- `staging/` is generated; do not edit it as the source of record.
- `reports/` holds durable evidence and status. Generated build outputs, logs, raw captures/videos, dumps, retail data, saves, and credentials are excluded from Git.

## License and retail data

The released Renegade source carries GPLv3 plus EA's additional terms; see the upstream notice after initializing the submodule. You must supply your own retail data at `ux0:data/renegade/retail/Data/`. User state lives under `ux0:data/renegade/user/`; downloaded TTFS packages are separate at `ux0:data/renegade/cache/ttfs/`.

See [LICENSE.md](LICENSE.md), [CONTRIBUTING.md](CONTRIBUTING.md), and [SECURITY.md](SECURITY.md) before contributing or sharing diagnostics.
