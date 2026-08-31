# Current status

Updated: 2026-08-31

## Evidence snapshot

| Class | Status | What it establishes |
| --- | --- | --- |
| Accepted physical baseline | **A3.1.4** | Native Vita boot, original data access, visible M00 world/session lifecycle, player/camera ownership, and clean exit. |
| A3.5-dev87 physical return | **Failed frontend/HUD gate** | The exact executable was installed and run, but original menu text remained absent; intro movies were very slow with buzzy audio; the gameplay dialogue panel appeared without text; ammo/health glyphs were mangled; NPC target bounds moved further right; and an opaque black period still preceded pre-warm/pre-cache. |
| A3.5-dev88 published local candidate | **Superseded local-only** | 54 focused contracts and the canonical 115-contract ARM/package closure passed. No physical install, launch, screenshot, or acceptance claim exists. |
| A3.5-dev89 published local candidate | **Superseded local-only** | 19 focused frontend/loading/runtime contracts and the canonical 115-contract ARM/package closure passed. No physical install, launch, screenshot, or acceptance claim exists. |
| A3.5-dev90 current candidate | **Local-only** | 23 focused frontend/loading/runtime/input contracts and the canonical 116-contract ARM/package closure passed. No physical install, launch, screenshot, or acceptance claim exists. |
| Screenshot/video evidence | **Dev87 recorder recovered** | No separate Dev87 title-owned screenshot was recovered, but a user-finalized MP4 yielded six reviewed M00 stills. A private `gh-pages` player branch is prepared, but GitHub rejected Pages for this account plan; the user has authorized unlisted YouTube hosting pending account connection. The current device has no VDB framebuffer-capture capability. |

Host validation, package identity, and logs are useful engineering evidence. They do not prove panel output, controls, audio quality, frame pacing, or lifecycle behavior on physical hardware.

## Dev90: what changed, and what it has not proved

Dev90 preserves Dev88/Dev89's shared glyph, BINK-audio reserve, frontend-scope, bootstrap, and Render2D state work, then adds the next source fixes for the latest returned physical failures:

- It keeps the native debug/status screen alive through original audio/cache/math/path/asset setup and only releases it when VitaGL/WW3D takes the display, targeting the 20-second opaque black interval before the visible diagnostic loader.
- It clamps 800×600 retail BINK frame uploads to an aspect-preserved 640×480 maximum while preserving the unchanged retail movie files and logging source/upload dimensions.
- It routes synchronous M00 level-load milestones back into the original loading presenter so the loading screen can visibly advance while Vita executes the non-threaded load path.
- It opens retail font files before sizing/reading, validates all frontend/HUD/subtitle `StyleMgr` font slots, clears glyph atlas memory, and clips FreeType bitmaps safely so menu, dialogue, ammo, health, and pickup text use valid raster data instead of stale vertical-line garbage.
- It stops mapping gameplay Start to original `DIK_ESCAPE`; the runtime clean-exit poll remains responsible for Start so the observed gameplay Start PSP2 crash is not retriggered through the menu/pause path.
- It removes Dev89's target-only native coordinate override and returns NPC target boxes to the original HUD logical-space owner after the physical report showed the native override overcorrected from left-shift to far-right shift.

Dev90 has not physically demonstrated readable menu text, paced intro A/V, readable gameplay subtitles, corrected HUD text, target-box placement, wall/shadow behavior, gameplay performance, loading-bar progression, HMVV stability, or Start lifecycle behavior. Its canonical VPK SHA-256 is `76766b787869693887428272914f646f92cae50d5009eaab1bb72f8071cc3568`; packaged SELF SHA-256 is `35dcbff8cef5d8aa06c291364f22592e2f17c81d16019a79ae95e2a434f2f2d2`; diagnostics ZIP SHA-256 is `1819fb1575c27063e2cdeec07650e65b1bd889049e12227df1101ec43c0a1772`.

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

The [evidence policy](EVIDENCE.md) and [historical timeline](HISTORICAL_SCREENSHOT_TIMELINE.md) explain the resulting gallery boundary. Six Dev87 M00 stills are explicitly labelled as recorder-derived and do not pass its failed frontend gate; no Dev88, Dev89, or Dev90 physical visual evidence exists.

## Authoritative records

- [Program charter](../reports/PROGRAM_CHARTER.md)
- [Current engineering status](../reports/PORT_STATUS.md)
- [Live progress](../reports/LIVE_PROGRESS.md)
- [Known gaps](../reports/KNOWN_GAPS.md)
- [Hardware test matrix](../reports/HARDWARE_TEST_MATRIX.md)
