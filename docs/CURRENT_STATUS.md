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
| A3.5-dev91 published local candidate | **Superseded local-only** | 40 focused frontend/loading/runtime/input/conversation contracts and the canonical 117-contract ARM/package closure passed. No physical install, launch, screenshot, or acceptance claim exists. |
| A3.5-dev92 published local candidate | **Superseded local-only** | 60 focused frontend/loading/runtime/input/conversation/gallery/texture contracts and the canonical 117-contract ARM/package closure passed. No physical install, launch, screenshot, or acceptance claim exists. |
| A3.5-dev93 published local candidate | **Superseded local-only** | 48 focused frontend/loading/runtime/texture/conversation contracts, full 219-tool unittest discovery, fast candidate closure, and canonical ARM/package closure passed. No physical install, launch, screenshot, or acceptance claim exists. |
| A3.5-dev94 current candidate | **Local-only** | 52 focused identity/staging/frontend/loading/runtime/indexed-state/fast-build contracts, two-cycle host M00/menu validation, fast candidate closure, and canonical ARM/package closure passed. No physical install, launch, screenshot, or acceptance claim exists. |
| Screenshot/video evidence | **Dev87 recorder recovered** | No separate Dev87 title-owned screenshot was recovered, but a user-finalized MP4 yielded six reviewed M00 stills. A private `gh-pages` player branch is prepared, but GitHub rejected Pages for this account plan; the user has authorized unlisted YouTube hosting pending account connection. The current device has no VDB framebuffer-capture capability. |

Host validation, package identity, and logs are useful engineering evidence. They do not prove panel output, controls, audio quality, frame pacing, or lifecycle behavior on physical hardware.

## Dev94: what changed, and what it has not proved

Dev94 preserves Dev88 through Dev93's shared glyph-state, BINK-audio reserve,
frontend-scope, bootstrap, pre-cache, Render2D, loading-callback, Start-route,
target-box rollback, BINK reductions, and vehicle/HMVV diagnostics, then adds
the next source-only fixes and diagnostics for the latest returned physical
failures:

- It retains the debug/bootstrap framebuffer until WW3D takes over, targeting
  the long black interval before visible diagnostics.
- It routes original saveload status and progress-count changes into the active
  Vita loading presenter during synchronous M00 loading, targeting the stuck
  loading bar.
- It applies deferred original DX8 shader, texture-stage, world, and view state
  before indexed Render2D text/HUD submissions, targeting absent menu labels,
  empty dialogue/subtitle text, and mangled HUD/pickup glyphs.
- It builds dynamic HUD/target/pickup geometry from `HUDClass::Think()` inside
  the native gameplay presentation scope, targeting HUD and target-box
  placement.
- It lets unchanged retail BINK playback drop late video frames when queued
  audio is under pressure, targeting buzzy/laggy intro A/V without repackaging
  retail movies.
- It host-validates that `STRINGS.TDB` loads and six original main-menu labels
  resolve to valid/renderable text.

Dev94 has not physically demonstrated a short visible bootstrap, readable menu text, paced intro A/V,
readable gameplay subtitles, corrected HUD text, target-box placement,
wall/shadow behavior, gameplay performance, loading-bar progression, HMVV
stability, or Start lifecycle behavior. Its canonical VPK SHA-256 is
`8b857cc4141ed9450a4f796f1c612bfbb72c163d5cb4f484bc5e16f70364ab73`;
packaged SELF SHA-256 is
`84d1c643b8da03350aa2769a88a9cd3dde7c9385900196bb07941fdc5ec02737`;
ELF SHA-256 is
`9ad4881aa257018e40ecaedb70d3b78519462ed9649875e67d8262e4714d2373`;
diagnostics ZIP SHA-256 is
`0d193857eca20b33dbfef2f02a434e6ff02c0ed77d4a0293c4c1ab4e2dd2c152`.

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

The [evidence policy](EVIDENCE.md) and [historical timeline](HISTORICAL_SCREENSHOT_TIMELINE.md) explain the resulting gallery boundary. Six Dev87 M00 stills are explicitly labelled as recorder-derived and do not pass its failed frontend gate; no Dev88, Dev89, Dev90, Dev91, Dev92, Dev93, or Dev94 physical visual evidence exists.

## Authoritative records

- [Program charter](../reports/PROGRAM_CHARTER.md)
- [Current engineering status](../reports/PORT_STATUS.md)
- [Live progress](../reports/LIVE_PROGRESS.md)
- [Known gaps](../reports/KNOWN_GAPS.md)
- [Hardware test matrix](../reports/HARDWARE_TEST_MATRIX.md)
