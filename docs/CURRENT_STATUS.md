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
| A3.5-dev92 current candidate | **Local-only** | 60 focused frontend/loading/runtime/input/conversation/gallery/texture contracts and the canonical 117-contract ARM/package closure passed. No physical install, launch, screenshot, or acceptance claim exists. |
| Screenshot/video evidence | **Dev87 recorder recovered** | No separate Dev87 title-owned screenshot was recovered, but a user-finalized MP4 yielded six reviewed M00 stills. A private `gh-pages` player branch is prepared, but GitHub rejected Pages for this account plan; the user has authorized unlisted YouTube hosting pending account connection. The current device has no VDB framebuffer-capture capability. |

Host validation, package identity, and logs are useful engineering evidence. They do not prove panel output, controls, audio quality, frame pacing, or lifecycle behavior on physical hardware.

## Dev92: what changed, and what it has not proved

Dev92 preserves Dev88 through Dev91's shared glyph-state, BINK-audio reserve,
frontend-scope, bootstrap, pre-cache, Render2D, loading-callback, Start-route,
target-box rollback, and vehicle/HMVV diagnostics, then adds the next
source-only fixes for the latest returned physical failures:

- It changes FreeType glyph measurement to include advance, bitmap width, and
  left/right bearings, then rasterizes into that cell instead of clipping
  positive left-bearing glyphs into narrow strips.
- It strengthens `StyleMgr` font probes to require visible glyph columns, not
  just any nonzero pixel, for real menu/HUD glyph readiness.
- It reduces unchanged retail BINK upload work to a 320×240 maximum, lowers
  the per-update decode/upload budget, caps update iterations, and configures
  the audio resampler from the decoder channel layout with a sane fallback.
- It adds bounded target-box diagnostics logging the projected normalized box,
  logical render resolution, WW3D device resolution, and combat camera aspect
  before changing any target-box math again.

Dev92 has not physically demonstrated readable menu text, paced intro A/V,
readable gameplay subtitles, corrected HUD text, target-box placement,
wall/shadow behavior, gameplay performance, loading-bar progression, HMVV
stability, or Start lifecycle behavior. Its canonical VPK SHA-256 is
`16aa490ecbe733f6053212d8d0f9aa0dc2e3ea5e9d7a701d545c2c20b779adf3`;
packaged SELF SHA-256 is
`08e89f0788652746a7c7d7590ee1bdbfaafccfd0e8c58a33266b0f37a305dae1`;
ELF SHA-256 is
`fe945697e1bdf6165ef2afc8e23014f7a2b5cda6be3a8c4811acfd147ad3f411`;
diagnostics ZIP SHA-256 is
`5b24fbc953037ecfab48ab87a38e489ad5702c8d8d52ead15f0903ece1f324be`.

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

The [evidence policy](EVIDENCE.md) and [historical timeline](HISTORICAL_SCREENSHOT_TIMELINE.md) explain the resulting gallery boundary. Six Dev87 M00 stills are explicitly labelled as recorder-derived and do not pass its failed frontend gate; no Dev88, Dev89, Dev90, Dev91, or Dev92 physical visual evidence exists.

## Authoritative records

- [Program charter](../reports/PROGRAM_CHARTER.md)
- [Current engineering status](../reports/PORT_STATUS.md)
- [Live progress](../reports/LIVE_PROGRESS.md)
- [Known gaps](../reports/KNOWN_GAPS.md)
- [Hardware test matrix](../reports/HARDWARE_TEST_MATRIX.md)
