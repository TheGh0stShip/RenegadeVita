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
| A3.5-dev94 published local candidate | **Superseded local-only** | 52 focused identity/staging/frontend/loading/runtime/indexed-state/fast-build contracts, two-cycle host M00/menu validation, fast candidate closure, and canonical ARM/package closure passed. No physical install, launch, screenshot, or acceptance claim exists. |
| A3.5-dev95 published local candidate | **Superseded local-only** | 52 focused identity/staging/frontend/loading/runtime/indexed-state/fast-build contracts, 43 implementation contracts, two-cycle host M00/menu validation, fast candidate closure, and canonical ARM/package closure passed. No physical install, launch, screenshot, or acceptance claim exists. |
| A3.5-dev96 published local candidate | **Superseded local-only** | 54 focused identity/staging/frontend/loading/runtime/indexed-state/short-wchar contracts, UTF-16 boundary selftests, two-cycle host M00/menu validation, fast candidate closure, and canonical ARM/package closure passed. No physical install, launch, screenshot, or acceptance claim exists. |
| A3.5-dev97 published local candidate | **Superseded local-only** | 41 post-formatter focused frontend/loading/runtime/indexed-state/short-wchar contracts, 19 candidate identity/loading/runtime contracts, 63 wider source contracts, UTF-16 formatter selftests, two-cycle host M00/menu validation, fast candidate closure, and canonical ARM/package closure passed. No physical install, launch, screenshot, or acceptance claim exists. |
| A3.5-dev98 current candidate | **Local-only** | Focused frontend/loading/runtime/indexed-state/identity contracts, full 222-tool unittest discovery, hygiene, fast candidate closure, and canonical ARM/package closure passed after Dev98's BINK presentation-clock, WWUI dialog-template copy, and HUD initialization presentation-scope fixes. No physical install, launch, screenshot, or acceptance claim exists. |
| Screenshot/video evidence | **Dev87 recorder recovered; Dev98 capture provider host-built** | No separate Dev87 title-owned screenshot was recovered, but a user-finalized MP4 yielded six reviewed M00 stills. A private `gh-pages` player branch is prepared, but GitHub rejected Pages for this account plan; the user has authorized unlisted YouTube hosting pending account connection. A Dev98-matching exact-title VDB `capture.screen.v1` provider was built host-side, but it is not installed and no Dev98 VDB logical-framebuffer evidence exists. |

Host validation, package identity, and logs are useful engineering evidence. They do not prove panel output, controls, audio quality, frame pacing, or lifecycle behavior on physical hardware.

## Dev98: what changed, and what it has not proved

Dev98 preserves Dev88 through Dev97's shared glyph-state, BINK-audio reserve,
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
- It forces `MessageWindowClass::On_Frame_Update()` and
  `MessageWindowClass::Update_Window_Rectangle()` through the same Vita
  gameplay-HUD presentation scope used for rendering, targeting dialogue and
  pickup/message text geometry that can be rebuilt during update before the
  render scope is active.
- It keeps Dev96's UTF-16-safe Vita boundary wrappers for `wcsncmp`,
  `wcsncpy`, `wcschr`, and `wcsstr`, and adds a bounded UTF-16 implementation
  for the compatibility `vswprintf`/`vsnwprintf` path. This targets original
  frontend/dialogue/HUD/pickup/menu code that formats Windows 16-bit `WCHAR`
  text and numbers before Render2D sees them.
- It writes the startup pre-cache receipt to an `A3.5-dev98` candidate-scoped
  path and prints/logs visible status before root and MIX file factory
  construction. This targets the reported opaque black interval before the
  diagnostic pre-cache screen, if the stall is inside original retail-data
  factory setup.
- It starts the BINK movie presentation clock only after audio output is armed
  or the first video upload becomes visible. This avoids charging slow Vita
  decode/prebuffer setup time against visible intro playback timing.
- It bounds the Vita WWUI dialog-template translation copy into the original
  fixed text buffer and logs source/copy/truncation lengths. This targets
  missing menu labels and empty dialogue text without replacing original
  `STRINGS.TDB` ownership.
- It scopes `HUDClass::Init()` through the same native Vita HUD presentation
  range already used by `HUDClass::Think()`, so persistent Render2D HUD,
  target-box, ammo/health, and pickup renderers are initialized in the same
  coordinate space they use for per-frame rebuilds.

Dev98 has not physically demonstrated a short visible bootstrap, readable menu text, paced intro A/V,
readable gameplay subtitles, corrected HUD text, target-box placement,
wall/shadow behavior, gameplay performance, loading-bar progression, HMVV
stability, or Start lifecycle behavior. Its canonical VPK SHA-256 is
`bb2e02eae8b28531735080214949463bcea3022859a8bf35affe33a01be2e870`;
packaged SELF SHA-256 is
`bbd96fe416f834b82054cf63a8680c9124d4c6b20e467bb98210e7241b815e35`;
ELF SHA-256 is
`dc5be03038085387bdf92225ba6a809995cc738a331e1756c320f80f76098dba`;
diagnostics ZIP SHA-256 is
`a2a079302212ef249cf58a399607a0ac48c027151dc85d4e208743dd7da088b2`.

## Current physical blockers

The next physical gate must establish, with matching candidate identity:

1. visible and readable original intro/menu text;
2. paced intro video/audio and clean skip behavior;
3. readable original gameplay dialogue text, HUD, pickup feedback, and loading progress;
4. stable M00 gameplay, camera, interaction, and frame pacing; and
5. safe Start/pause/exit behavior without a PSP2 crash.

The developer must not claim any of these from host tests or a runtime log.

## Capture and gallery state

The future screenshot route is VDB's authenticated exact-title `capture.screen.v1` provider. The Dev98-matching host-side bundle is `<VitaDevBridge>/build/exact-title-provider-rnega3101-bbd96fe4-dev98-r26`; it targets `RNEGA3101` plus Dev98 eboot SHA-256 `bbd96fe416f834b82054cf63a8680c9124d4c6b20e467bb98210e7241b815e35`. It is not installed. The old VitaCompanion `screen.v1` path is panel control, not a screenshot endpoint, and the on-screen red `R` remains MP4 recorder evidence, not VDB logical-framebuffer evidence.

The [evidence policy](EVIDENCE.md) and [historical timeline](HISTORICAL_SCREENSHOT_TIMELINE.md) explain the resulting gallery boundary. Six Dev87 M00 stills are explicitly labelled as recorder-derived and do not pass its failed frontend gate; no Dev88, Dev89, Dev90, Dev91, Dev92, Dev93, Dev94, Dev95, Dev96, Dev97, or Dev98 physical visual evidence exists.

## Authoritative records

- [Program charter](../reports/PROGRAM_CHARTER.md)
- [Current engineering status](../reports/PORT_STATUS.md)
- [Live progress](../reports/LIVE_PROGRESS.md)
- [Known gaps](../reports/KNOWN_GAPS.md)
- [Hardware test matrix](../reports/HARDWARE_TEST_MATRIX.md)
