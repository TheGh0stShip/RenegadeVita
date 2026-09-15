# Current status

Updated: 2026-09-15

## Current Dev134 checkpoint

Dev134 is the current native ARM/GXM candidate. Canonical host/sanitizer/ARM
and package identity checks passed, followed by matching Vita3K refinery visuals,
pause Map/statistics/Help checks, resume, and clean native exit. The VPK was
deployed to the physical Vita with executable and package readback verification;
manual LiveArea launch is required because remote control services were
unavailable. Hardware FPS, movie audio, and complete tutorial acceptance remain
open. The tutorial-only public download guide is
[Renegade-Vita-Demo](https://github.com/TheGh0stShip/Renegade-Vita-Demo).

Exact evidence is retained in [DEV134_PHYSICAL_MILESTONE.md](../reports/DEV134_PHYSICAL_MILESTONE.md)
and [DEV134_SKIN_RGB_WORK.md](../reports/DEV134_SKIN_RGB_WORK.md).

The historical entries below are retained for provenance.

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
| A3.5-dev94 published local candidate | **Superseded local-only** | 52 focused identity/staging/frontend/loading/runtime/indexed-state/fast-build contracts, two-cycle host M00/menu validation, fast candidate closure, and canonical ARM/package closure passed. No physical install, launch, screenshot, or acceptance claim exists. |
| A3.5-dev95 published local candidate | **Superseded local-only** | 52 focused identity/staging/frontend/loading/runtime/indexed-state/fast-build contracts, 43 implementation contracts, two-cycle host M00/menu validation, fast candidate closure, and canonical ARM/package closure passed. No physical install, launch, screenshot, or acceptance claim exists. |
| A3.5-dev96 published local candidate | **Superseded local-only** | 54 focused identity/staging/frontend/loading/runtime/indexed-state/short-wchar contracts, UTF-16 boundary selftests, two-cycle host M00/menu validation, fast candidate closure, and canonical ARM/package closure passed. No physical install, launch, screenshot, or acceptance claim exists. |
| A3.5-dev97 published local candidate | **Superseded local-only** | 41 post-formatter focused frontend/loading/runtime/indexed-state/short-wchar contracts, 19 candidate identity/loading/runtime contracts, 63 wider source contracts, UTF-16 formatter selftests, two-cycle host M00/menu validation, fast candidate closure, and canonical ARM/package closure passed. No physical install, launch, screenshot, or acceptance claim exists. |
| A3.5-dev98 published local candidate | **Superseded local-only** | Focused frontend/loading/runtime/indexed-state/identity contracts, full 222-tool unittest discovery, hygiene, fast candidate closure, and canonical ARM/package closure passed after Dev98's BINK presentation-clock, WWUI dialog-template copy, and HUD initialization presentation-scope fixes. No physical install, launch, screenshot, or acceptance claim exists. |
| A3.5-dev99 current candidate | **Local-only** | Focused frontend/loading/runtime/indexed-state contracts, fast candidate closure, and canonical ARM/package closure passed after Dev99's verbose startup-status repaint worker. This targets the long pre-cache black interval only. No physical install, launch, screenshot, or acceptance claim exists. |
| Screenshot/video evidence | **Dev87 recorder recovered; Dev99 capture provider host-built** | No separate Dev87 title-owned screenshot was recovered, but a user-finalized MP4 yielded six reviewed M00 stills. A private `gh-pages` player branch is prepared, but GitHub rejected Pages for this account plan; the user has authorized unlisted YouTube hosting pending account connection. A Dev99-matching exact-title VDB `capture.screen.v1` provider was built host-side, but it is not installed and no Dev99 VDB logical-framebuffer evidence exists. |

Host validation, package identity, and logs are useful engineering evidence. They do not prove panel output, controls, audio quality, frame pacing, or lifecycle behavior on physical hardware.

## Dev99: what changed, and what it has not proved

Dev99 preserves Dev88 through Dev98's shared glyph-state, BINK-audio reserve,
frontend-scope, bootstrap, pre-cache, Render2D, loading-callback, Start-route,
target-box rollback, BINK reductions, vehicle/HMVV diagnostics, deferred
indexed Render2D state, HUD `Think()`/`Init()` presentation scoping,
MessageWindow presentation scoping, short-wchar libc wrappers, bounded UTF-16
formatted output, bounded WWUI dialog-template translation copying, delayed
BINK presentation-clock arming, and host main-menu translation validation.

The new Dev99 change is deliberately narrow: it runs a native startup-status
repaint worker before VitaGL/WW3D startup and before the visible pre-cache
phase. That worker redraws the last known debug status every 250 ms while the
original root and MIX file factories are constructed, then stops before the
existing visible startup pre-cache phase. It targets the reported long opaque
interval before diagnostic pre-cache appears.

Dev99 does not contain a new menu-text, subtitle, HUD-number, target-box,
movie-pacing, wall/shadow, HMVV, FPS, or Start-crash fix beyond preserving the
previous local-only Dev88-Dev98 work. Those defects still require physical VDB
logical-framebuffer evidence and matching logs/dumps.

Dev99 has not physically demonstrated a short visible bootstrap, readable menu
text, paced intro A/V, readable gameplay subtitles, corrected HUD text,
target-box placement, wall/shadow behavior, gameplay performance, loading-bar
progression, HMVV stability, or Start lifecycle behavior. Its canonical VPK
SHA-256 is
`be9939594d7c25f4039f4aefbf77af631ccd6cb1200ed1a50b175cb6534b6c86`;
packaged SELF SHA-256 is
`020f210a129beaaf4d0953c6c56efc82267a52949d6883c5db313e87b0790d6d`;
ELF SHA-256 is
`fdce12071b368326c4b863547a87b58a9fb69fe7290d9425e9895371e4e9888e`;
diagnostics ZIP SHA-256 is
`f13a8f28309821a3c4d408000fccc681e955ba467d267bccab72c21b71302c68`.

## Current physical blockers

The next physical gate must establish, with matching candidate identity:

1. visible and readable original intro/menu text;
2. paced intro video/audio and clean skip behavior;
3. readable original gameplay dialogue text, HUD, pickup feedback, and loading progress;
4. stable M00 gameplay, camera, interaction, and frame pacing; and
5. safe Start/pause/exit behavior without a PSP2 crash.

The developer must not claim any of these from host tests or a runtime log.

## Capture and gallery state

The future screenshot route is VDB's authenticated exact-title `capture.screen.v1` provider. The Dev99-matching host-side bundle is `<VitaDevBridge>/build/exact-title-provider-rnega3101-020f210a-dev99-r26`; it targets `RNEGA3101` plus Dev99 eboot SHA-256 `020f210a129beaaf4d0953c6c56efc82267a52949d6883c5db313e87b0790d6d`. It is not installed. The old VitaCompanion `screen.v1` path is panel control, not a screenshot endpoint, and the on-screen red `R` remains MP4 recorder evidence, not VDB logical-framebuffer evidence.

The [evidence policy](EVIDENCE.md) and [historical timeline](HISTORICAL_SCREENSHOT_TIMELINE.md) explain the resulting gallery boundary. Six Dev87 M00 stills are explicitly labelled as recorder-derived and do not pass its failed frontend gate; no Dev88, Dev89, Dev90, Dev91, Dev92, Dev93, Dev94, Dev95, Dev96, Dev97, Dev98, or Dev99 physical visual evidence exists.

## Authoritative records

- [Program charter](../reports/PROGRAM_CHARTER.md)
- [Current engineering status](../reports/PORT_STATUS.md)
- [Live progress](../reports/LIVE_PROGRESS.md)
- [Known gaps](../reports/KNOWN_GAPS.md)
- [Hardware test matrix](../reports/HARDWARE_TEST_MATRIX.md)
