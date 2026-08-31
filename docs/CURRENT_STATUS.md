# Current status

Updated: 2026-08-31

## Evidence snapshot

| Class | Status | What it establishes |
| --- | --- | --- |
| Accepted physical baseline | **A3.1.4** | Native Vita boot, original data access, visible M00 world/session lifecycle, player/camera ownership, and clean exit. |
| A3.5-dev87 physical return | **Failed frontend/HUD gate** | The exact executable was installed and run, but original menu text remained absent; intro movies were very slow with buzzy audio; the gameplay dialogue panel appeared without text; ammo/health glyphs were mangled; NPC target bounds moved further right; and an opaque black period still preceded pre-warm/pre-cache. |
| A3.5-dev88 published local candidate | **Superseded local-only** | 54 focused contracts and the canonical 115-contract ARM/package closure passed. No physical install, launch, screenshot, or acceptance claim exists. |
| A3.5-dev89 published local candidate | **Superseded local-only** | 19 focused frontend/loading/runtime contracts and the canonical 115-contract ARM/package closure passed. No physical install, launch, screenshot, or acceptance claim exists. |
| A3.5-dev90 published local candidate | **Superseded local-only** | 23 focused frontend/loading/runtime/input contracts and the canonical 116-contract ARM/package closure passed. No physical install, launch, screenshot, or acceptance claim exists. |
| A3.5-dev91 current candidate | **Local-only** | 40 focused frontend/loading/runtime/input/conversation contracts and the canonical 117-contract ARM/package closure passed. No physical install, launch, screenshot, or acceptance claim exists. |
| Screenshot/video evidence | **Dev87 recorder recovered** | No separate Dev87 title-owned screenshot was recovered, but a user-finalized MP4 yielded six reviewed M00 stills. A private `gh-pages` player branch is prepared, but GitHub rejected Pages for this account plan; the user has authorized unlisted YouTube hosting pending account connection. The current device has no VDB framebuffer-capture capability. |

Host validation, package identity, and logs are useful engineering evidence. They do not prove panel output, controls, audio quality, frame pacing, or lifecycle behavior on physical hardware.

## Dev91: what changed, and what it has not proved

Dev91 preserves Dev88 through Dev90's shared glyph-state, BINK-audio reserve,
frontend-scope, bootstrap, pre-cache, Render2D, loading-callback, Start-route,
and target-box rollback work, then adds the next source-only fixes for the
latest returned physical failures:

- It reduces the forced startup pre-cache visible hold to one second and
  flushes status text instead of inserting extra blocking sleeps before
  original engine/VitaGL handoff.
- It downscales unchanged 800×600 retail BINK uploads to a 480×360 maximum,
  switches scaling to the faster software path, starts with a six-buffer
  audio reserve, and drops late video frames sooner after the first visible
  frame to reduce movie wall-time pressure without repackaging BIK files.
- It renders bounded catch-up loading frames when synchronous M00 phase
  progress changes, so the original loading presenter has more opportunities
  to show progress during the non-threaded load path.
- It treats zero-pixel FreeType glyphs as valid spacing glyphs, but requires
  visible pixels from real `StyleMgr` probes before claiming the menu/HUD font
  path is ready.
- It keeps the gameplay Start warning visible in diagnostic text while the
  runtime exit poll remains the only Start owner during M00 gameplay.
- It adds bounded original `VehicleGameObj` diagnostics for vehicle creation,
  init, update, and star-player proximity, targeting the reported M00
  war-factory/HMVV freeze without changing vehicle gameplay semantics.

Dev91 has not physically demonstrated readable menu text, paced intro A/V,
readable gameplay subtitles, corrected HUD text, target-box placement,
wall/shadow behavior, gameplay performance, loading-bar progression, HMVV
stability, or Start lifecycle behavior. Its canonical VPK SHA-256 is
`20f561ebcdf534ea71da6e421ab47811c99a9bdce14dac84dd7f99481f4c8768`;
packaged SELF SHA-256 is
`42e85952ce85975e05e1385414f9d43ed35e4330a2a91325737c0f412de6c219`;
ELF SHA-256 is
`47cdcc15c57b1efc8bc2da8995e902b4d0e580143091e70b6818198c1a51169e`;
diagnostics ZIP SHA-256 is
`2ac5fc16970e4b1689a91a92e90dd2e6260cd70313136a7e952b4979d6efe767`.

## Current physical blockers

The next physical gate must establish, with matching candidate identity:

1. visible and readable original intro/menu text;
2. paced intro video/audio and clean skip behavior;
3. readable original gameplay dialogue text, HUD, pickup feedback, and loading progress;
4. stable M00 gameplay, camera, interaction, and frame pacing; and
5. safe Start/pause/exit behavior without a PSP2 crash.

The developer must not claim any of these from host tests or a runtime log.

## Capture and gallery state

The current Vita command service advertises `screen.v1`, which is panel on/off—not a screenshot endpoint. The checked-in VDB client supports the separate authenticated `capture.screen.v1` protocol, but its target-local agent and gateway are not installed on this device. The on-screen red `R` is a separate MP4 recorder; it is not a screenshot service and a crash can prevent the MP4 from finalizing.

The [evidence policy](EVIDENCE.md) and [historical timeline](HISTORICAL_SCREENSHOT_TIMELINE.md) explain the resulting gallery boundary. Six Dev87 M00 stills are explicitly labelled as recorder-derived and do not pass its failed frontend gate; no Dev88, Dev89, Dev90, or Dev91 physical visual evidence exists.

## Authoritative records

- [Program charter](../reports/PROGRAM_CHARTER.md)
- [Current engineering status](../reports/PORT_STATUS.md)
- [Live progress](../reports/LIVE_PROGRESS.md)
- [Known gaps](../reports/KNOWN_GAPS.md)
- [Hardware test matrix](../reports/HARDWARE_TEST_MATRIX.md)
