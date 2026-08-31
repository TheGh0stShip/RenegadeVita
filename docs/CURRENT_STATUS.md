# Current status

Updated: 2026-08-31

## Evidence snapshot

| Class | Status | What it establishes |
| --- | --- | --- |
| Accepted physical baseline | **A3.1.4** | Native Vita boot, original data access, visible M00 world/session lifecycle, player/camera ownership, and clean exit. |
| A3.5-dev87 physical return | **Failed frontend/HUD gate** | The exact executable was installed and run, but original menu text remained absent; intro movies were very slow with buzzy audio; the gameplay dialogue panel appeared without text; ammo/health glyphs were mangled; NPC target bounds moved further right; and an opaque black period still preceded pre-warm/pre-cache. |
| A3.5-dev88 published local candidate | **Superseded local-only** | 54 focused contracts and the canonical 115-contract ARM/package closure passed. No physical install, launch, screenshot, or acceptance claim exists. |
| A3.5-dev89 current candidate | **Local-only** | 19 focused frontend/loading/runtime contracts and the canonical 115-contract ARM/package closure passed. No physical install, launch, screenshot, or acceptance claim exists. |
| Screenshot/video evidence | **Dev87 recorder recovered** | No separate Dev87 title-owned screenshot was recovered, but a user-finalized MP4 yielded six reviewed M00 stills. A private `gh-pages` player branch is prepared, but GitHub rejected Pages for this account plan; the user has authorized unlisted YouTube hosting pending account connection. The current device has no VDB framebuffer-capture capability. |

Host validation, package identity, and logs are useful engineering evidence. They do not prove panel output, controls, audio quality, frame pacing, or lifecycle behavior on physical hardware.

## Dev89: what changed, and what it has not proved

Dev89 preserves Dev88's shared glyph and BINK-audio reserve corrections, then adds the next source fixes for the latest returned physical failures:

- It presents original frontend WWUI through its original 800×600 logical coordinate space and validates real `StyleMgr` font glyphs before admitting menu input.
- It makes the Vita font provider try the known retail Regatta/Arial filename variants and fail closed on empty/corrupt font files.
- It flushes the native bootstrap/debug screen after each startup progress print and before filesystem/cache work, so the pre-diagnostic period has a chance to show text instead of remaining opaque black.
- It expands the source-owned startup pre-cache touch list for menu, HUD, subtitle/dialogue, pickup, shadow, objective/POG, and M00 assets without packaging or altering retail data.
- It clears leaked second texture-stage state before Render2D text/icon draws and scopes projected target boxes to the native WW3D device resolution while leaving authored static HUD layout in the original 640×480 space.
- It lets the original BINK boundary drop late video frames after the first visible frame to protect audio wall-time, while logging uploaded/dropped counts. Retail BIK files remain unchanged.

Dev89 has not physically demonstrated readable menu text, paced intro A/V, readable gameplay subtitles, corrected HUD text, target-box placement, wall/shadow behavior, gameplay performance, loading-bar progression, or Start lifecycle behavior. Its canonical VPK SHA-256 is `e2754588124910eeea526c056d004986f48f60491ab1a529f6a513248f0757a2`; diagnostics ZIP SHA-256 is `7bc5d18d1f1607cf10e0aee371f51ac4d73f1fe58f69cef60ab9ac86796b9038`.

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

The [evidence policy](EVIDENCE.md) and [historical timeline](HISTORICAL_SCREENSHOT_TIMELINE.md) explain the resulting gallery boundary. Six Dev87 M00 stills are explicitly labelled as recorder-derived and do not pass its failed frontend gate; no Dev88 or Dev89 physical visual evidence exists.

## Authoritative records

- [Program charter](../reports/PROGRAM_CHARTER.md)
- [Current engineering status](../reports/PORT_STATUS.md)
- [Live progress](../reports/LIVE_PROGRESS.md)
- [Known gaps](../reports/KNOWN_GAPS.md)
- [Hardware test matrix](../reports/HARDWARE_TEST_MATRIX.md)
