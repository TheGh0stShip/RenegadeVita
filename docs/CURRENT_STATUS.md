# Current status

Updated: 2026-09-26

## Current A3.5-dev197 checkpoint

Dev197 repairs the M13 EVA exit handoff: after original Combat/session teardown,
the Vita outer loop reopens the original frontend rather than ending the app.
Canonical host/ARM/package checks passed and the VPK was installed and
hash-verified in Vita3K. The user then loaded the pre-Ion-beacon
`savegame03.sav`, confirmed the restored game was correct, and exited back
to the main menu. A subsequent physical PSTV run passed the same bounded
save-load/menu-return check. The installed SELF hash matches the package; the
matching runtime log records original save-load and post-load completion,
saved player/camera reuse, clean session teardown and frontend reopening.
M13 dependency preparation took 12.4 seconds and the first gameplay frames
were slow, so later Ion progression, steady FPS, and full physical acceptance
remain open. Issue #1 stays open for its other reported symptoms.
See [Dev197 evidence and limits](../reports/DEV197_ISSUE1_SAVE_MENU.md).

## Dev195 multiplayer evidence

Dev195 is a fast-build native ARM candidate, packaged, installed and run in
Vita3K. It joined RenCorner, downloaded and mounted five TTFS packages, loaded
City_U1, rendered 9,723 frames, accepted bounded player movement, and completed
original session teardown back to the menu. The public player list showed
`PSVita`; the client requested `PS Vita`. The normalization boundary is unknown.

| Evidence class | Current result |
| --- | --- |
| Build and package | 171 fast contracts, DDS alias executable test, ARM ELF/SELF/VPK, package inventory and installed hashes passed. This was not a new canonical acceptance run. |
| Host | Original state-machine callback/save-load and loaded-replication sanitizer checks passed. Host tests do not establish Vita gameplay. |
| Vita3K | Native join, world/weapon/HUD rendering, movement and session teardown observed. Purchase-terminal inputs did not produce a dialog; early multiplayer text had malformed glyphs. |
| Performance | Short mostly stationary multiplayer run: average 59.578 FPS, median 16.463 ms, p95 17.912 ms, worst 1,870.567 ms. Not a representative campaign benchmark or a lag-free claim. |
| Physical Vita | A3.1.4 remains the accepted baseline. Dev195 physical testing pending; 60 FPS remains a goal, not acceptance. |

The outer four-minute runner ended `TIMEOUT_UNASSESSED` at the returned main
menu. That status is not a crash and is not an unqualified full-run pass.
Full combat, purchases, vehicles, death/respawn, chat, round transitions and
sustained multiplayer performance remain unaccepted. START leaves the server;
it does not yet provide the complete multiplayer pause/menu flow.

See [Dev195 evidence and hashes](../reports/DEV195_RENCORNER_NATIVE_JOIN.md),
[installation](INSTALLING.md), [multiplayer setup](MULTIPLAYER.md), and
[verified publication](../reports/DEV195_PUBLICATION.md).

## Campaign status

Earlier candidate traces show M13 completion and transition to M01, not a
complete campaign. M13 ambush/effects pacing, audio synchronization, actors and
animations, and M01 aircraft-related stalls remain open. Dev194 warmed and
released four animated M01 models while preserving fresh cinematic instances;
its canonical host/build checks passed, but those changes were not runtime
accepted. Dev195's multiplayer run does not validate those campaign fixes.

[Issue #1](https://github.com/TheGh0stShip/RenegadeVita/issues/1) records Dev142
PSTV tutorial/M01 observations, including blocked progression and save/load.
These are candidate-specific user reports, not Dev195 hardware acceptance.
The [tutorial demo](https://github.com/TheGh0stShip/Renegade-Vita-Demo) is separate
and unchanged. No New Game-to-ending completion is claimed.

The historical entries below are retained for provenance.

Older candidate rows are Local-only engineering records unless they carry
matching physical-Vita evidence.

## Post-Dev99 checkpoint history

This table indexes historical Dev100-Dev134 work. Later campaign and multiplayer
evidence is in [port status](../reports/PORT_STATUS.md); the current checkpoint
above takes precedence over historical candidate descriptions.

| Candidate | Public status | Evidence |
| --- | --- | --- |
| Dev100-Dev105 | Demo profile, presentation, retail-data and first-frame repair work. Dev102 restored menu labels in Vita3K; Dev105 produced usable emulator M00 runtime evidence, not physical acceptance. | [Dev100 audit](../reports/DEV100_PRIOR_WORK_AUDIT.md), [Dev102 return](../reports/DEV102_VITA3K_PRESENTATION_RETURN.md), [Dev105 retail return](../reports/DEV105_RETAIL_DATA_RETURN.md) |
| Dev106-Dev113 | Filesystem probe, UTF-16, checkpoint input, local input, HUD/loading, culling, frontend, and buffered-rewind fixes. These are source/host/Vita3K milestones. | [Dev106](../reports/DEV106_READONLY_PROBE_COST.md), [Dev108](../reports/DEV108_DIALOG_UTF16_AND_CHECKPOINT_INPUT.md), [Dev113](../reports/DEV113_OVERNIGHT_RETURN.md) |
| Dev114-Dev120 | Original checkpoint reload, HUD/font fixes, weapon/EVA visual corrections, tutorial finale work, original loading/menu-audio work, and capture/render comparison. Dev118 reached the original finale in Vita3K; Dev120 remained visual/capture engineering. | [Dev114](../reports/DEV114_CHECKPOINT_CANDIDATE_RETURN.md), [Dev117](../reports/DEV117_WEAPON_EVA_CORRECTIONS.md), [Dev120](../reports/DEV120_ORIGINAL_LOADING_AND_MENU_AUDIO.md) |
| Dev121-Dev123 | Presented-frame capture recovery and Hotwire gameplay checks. Dev123 fast package passed emulator recovery evidence, then physical launch failed and the predecessor was restored. | [Dev121/122](../reports/DEV121_CAPTURE_SOURCE.md), [Dev123](../reports/DEV123_CAPTURE_REGRESSION_RECOVERY.md) |
| Dev124-Dev126 | Physical testing returned real hardware failures: movie starvation, Logan/control stall, Mobius/START crash, low gameplay FPS, and missing EVA datalinks. Dev126 deployed diagnostics but was not accepted. | [Dev124](../reports/DEV124_NATIVE_BOOT_DIAGNOSIS.md), [Dev125](../reports/DEV125_PHYSICAL_MOVIE_PROGRESS.md), [Dev126](../reports/DEV126_LOGAN_PHYSICAL_STALL.md) |
| Dev127-Dev134 | Renderer/FPS audit, EVA/DDS, complete pause-menu audit, save/load/delete/settings, native save text entry, repeated Load lifecycle, Cycle Objectives, discarded textured-skin RGB work, and Dev134 canonical milestone. Dev134 has matching Vita3K visual evidence and physical deployment/readback verification; runtime return is pending manual launch. | [Dev127](../reports/DEV127_FIX_AND_OPTIMIZATION_PLAN.md), [Dev129/130](../reports/DEV129_PAUSE_MENU_AUDIT.md), [Dev132](../reports/DEV132_NATIVE_TEXT_ENTRY.md), [Dev133](../reports/DEV133_REPEATED_LOAD_AND_OBJECTIVES.md), [Dev134](../reports/DEV134_PHYSICAL_MILESTONE.md) |

## Historical evidence through Dev134

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
| A3.5-dev99 historical candidate | **Superseded local-only** | Retained for provenance. Dev134 was a later checkpoint with separate canonical, Vita3K, and physical deployment evidence. |
| Screenshot/video evidence | **Historical gallery plus later emulator/physical diagnostics** | No separate Dev87 title-owned screenshot was recovered, but a user-finalized MP4 yielded six reviewed M00 stills. Later Dev100-Dev134 reports retain Vita3K visual/capture returns and physical failure/deployment receipts where applicable. Physical Dev134 runtime visual evidence is still pending manual LiveArea launch. |

Host validation, package identity, and logs are useful engineering evidence. They do not prove panel output, controls, audio quality, frame pacing, or lifecycle behavior on physical hardware.

## Dev99 historical boundary

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

The future physical screenshot route remains an authenticated, exact-title
post-render capture provider when available. The old VitaCompanion `screen.v1`
path is panel control, not a screenshot endpoint, and the on-screen red `R`
remains MP4 recorder evidence, not VDB logical-framebuffer evidence.

The [evidence policy](EVIDENCE.md) and [historical timeline](HISTORICAL_SCREENSHOT_TIMELINE.md)
explain the resulting gallery boundary. Six Dev87 M00 stills are explicitly
labelled as recorder-derived and do not pass its failed frontend gate. Later
Dev100-Dev134 screenshots/captures remain classified by evidence class in their
reports; Vita3K visuals are not physical acceptance, and Dev134 physical
runtime visual evidence has not returned yet.

## Authoritative records

- [Program charter](../reports/PROGRAM_CHARTER.md)
- [Current engineering status](../reports/PORT_STATUS.md)
- [Live progress](../reports/LIVE_PROGRESS.md)
- [Known gaps](../reports/KNOWN_GAPS.md)
- [Hardware test matrix](../reports/HARDWARE_TEST_MATRIX.md)
