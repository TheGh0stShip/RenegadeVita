# Current status

Updated: 2026-08-31

## Evidence snapshot

| Class | Status | What it establishes |
| --- | --- | --- |
| Accepted physical baseline | **A3.1.4** | Native Vita boot, original data access, visible M00 world/session lifecycle, player/camera ownership, and clean exit. |
| A3.5-dev87 physical return | **Failed frontend gate** | The exact executable was installed and run, but original menu text remained absent; intro movies were very slow with buzzy audio; and the original gameplay dialogue panel appeared without text. |
| A3.5-dev88 canonical candidate | **Local-only** | 54 focused contracts and the canonical 115-contract ARM/package closure passed. No physical install, launch, screenshot, or acceptance claim exists. |
| Screenshot/video evidence | **Dev87 recorder recovered** | No separate Dev87 title-owned screenshot was recovered, but a user-finalized MP4 yielded six reviewed M00 stills. The raw MP4 remains local-only; the current device has no VDB framebuffer-capture capability. |

Host validation, package identity, and logs are useful engineering evidence. They do not prove panel output, controls, audio quality, frame pacing, or lifecycle behavior on physical hardware.

## Dev88: what changed, and what it has not proved

Dev88 makes two narrow boundary corrections:

- It restores the original texture-stage combiner immediately before dynamic indexed glyph draws used by `Render2DSentence` menu text and `MessageWindow` dialogue text. It does not substitute text, add an overlay, or change retail assets.
- It starts the original BINK audio worker only after three real output buffers are queued, rather than one, to provide roughly 64 ms of reserve against observed decode/upload stalls. Retail BIK files remain unchanged.

Dev88 has not repaired or physically demonstrated Start lifecycle behavior, the current HUD placement defects, gameplay performance, loading flashes, or the missing VDB capture provider. Its canonical VPK SHA-256 is `be78097b98a3c0a0e9e9cd1fbdb0d5cdb9d7d630145bec8736d7ebad0cf07138`.

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

The [evidence policy](EVIDENCE.md) and [historical timeline](HISTORICAL_SCREENSHOT_TIMELINE.md) explain the resulting gallery boundary. Six Dev87 M00 stills are explicitly labelled as recorder-derived and do not pass its failed frontend gate; no Dev88 physical visual evidence exists.

## Authoritative records

- [Program charter](../reports/PROGRAM_CHARTER.md)
- [Current engineering status](../reports/PORT_STATUS.md)
- [Live progress](../reports/LIVE_PROGRESS.md)
- [Known gaps](../reports/KNOWN_GAPS.md)
- [Hardware test matrix](../reports/HARDWARE_TEST_MATRIX.md)
