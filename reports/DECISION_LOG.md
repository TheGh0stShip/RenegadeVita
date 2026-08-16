# Architectural decisions

- **2026-08-16 — Candidate identity is a compiled and post-link gate.** One
  generated build-identity header owns executable, runtime-log, capture, and
  report identity. Every hardware candidate uses a fresh ARM build directory;
  the final ELF must contain the intended identities and no prohibited stale
  identities, and packaged `eboot.bin` must hash-identically match the verified
  SELF. Report/file renaming is never sufficient evidence.

- **2026-08-15 — A3.1.4 frozen.** It is the visible original interactive M00
  baseline, not a playable-game milestone. Raw evidence is immutable.
- **2026-08-15 — Input repair location.** Vita byte axes map centrally to
  original DirectInput ±1000. No camera-side compensation or second sensitivity
  system is permitted.
- **2026-08-15 — Texture repair location.** Original `TextureClass`, asset
  identifiers, DDS decoder, and factory/MIX path remain owners. Vita decodes
  in memory and owns only native upload/bind/release; no retail conversion or
  VPK asset packaging.
- **2026-08-15 — Fidelity before gameplay expansion.** A3.2 receives the next
  hardware gate. A4.0 implementation begins only after physical A3.2 evidence.
- **2026-08-15 — Performance discipline.** Measurement is allowed; renderer,
  scene, visibility, texture, and simulation optimization is not.
- **2026-08-15 — Patch inventory reconciliation.**
  `wwnet-a31-network-posix.patch` is retained as historical investigation but
  excluded from the deterministic applied-patch inventory because it is not
  registered by staging and A3.2 must not reopen networking work. The applied
  count is now 99 (including the narrow later frontend include boundary); the
  original translation-unit manifest count is 423.
- **2026-08-16 — A4 HUD closure.** Original Font3D/Targa/Surface/Texture,
  `RadarManager`, `VertexMaterialClass`, and `Render2D` ownership are retained.
  The 44-byte dynamic FVF is mapped at the Vita renderer edge. This path passed
  two ASan M00 cycles; it is not enabled in the frozen A3.2 package.
- **2026-08-16 — Frontend boundary.** Main-menu asset availability is proven
  through original `WW3DAssetManager`; the next real closure is WWUI dialogs
  and Vita controller input, not a replacement menu.
- **2026-08-16 — Host serialized-observer boundary.** GDB showed the first
  optimized HUD-frame fault came from an eight-byte host read of a four-byte
  retail observer pointer. The maintained Combat patch now invokes the existing
  token-width reader only under `RENEGADE_HOST_ABI_TEST`; target ILP32 keeps its
  original read and the frozen A3.2 package is unchanged.
- **2026-08-16 — Deterministic WWUI frontier.** Stage the complete original
  `wwui` source/header pool now, but do not select it into the runtime until
  `StyleMgr`/`DialogMgr`/controller-input ownership is closed as one boundary.
- **2026-08-16 — WWUI font boundary.** The first Vita `StyleMgr` probe exposes
  genuine Windows font registration and old MSVC loop-scope assumptions. Do not
  paper over `AddFontResource` with a success no-op; define the font-provider
  contract before enabling original menu initialization.
- **2026-08-16 — Retail FontChars provider.** The provider uses the original
  file-factory/MIX contract to obtain `54251___.TTF` and `ARI_____.TTF`, caches
  FreeType faces, and supplies alpha-4444 glyph rasters only at the original
  `FontCharsClass` GDI edge. It neither bundles fonts nor replaces UI layout or
  asset ownership. Optimized and ASan memory-safety two-cycle M00 runs prove
  both families; the full-engine LeakSanitizer report remains a separate
  pre-existing ownership gap and the frozen A3.2 package remains unchanged.
- **2026-08-16 — Original StyleMgr selected.** `StyleMgrClass` now remains the
  owner of menu/in-game font selection and layout. Vita skips only its obsolete
  process-global registration calls because `FontCharsClass` loads the same
  retail bytes through `_TheFileFactory`; no font or UI asset is bundled. The
  headless static cache is excluded only in this real-StyleMgr target. A
  pointer-subtraction repair replaces the source's LP64-unsafe cast-before-
  subtraction in wrapped-text copying.
- **2026-08-16 — WWUI resource fidelity.** The original DialogParser stays the
  owner of dialog-template interpretation. Its required `RT_DIALOG` input is
  absent from the current Vita executable; a future provider must preserve the
  original template bytes and resource identities. Hand-authored substitute
  dialogs are explicitly out of scope.
- **2026-08-16 — Canonical WWUI resource source.** The installed Steam
  `game2.exe` advertises dialog resource leaves that resolve into executable
  code and therefore fails structural validation. The A4 boundary instead
  deterministically compiles selected official `Code/Commando/chat.rc` dialog
  definitions into the native templates consumed unchanged by
  `DialogParserClass`. It packages no retail executable or asset and preserves
  source resource IDs, layout, text identifiers, styles, and control classes.
- **2026-08-16 — GameInitMgr offline service boundary.** The original
  single-player `Initialize_SP`/`Start_Game`/exit ordering is compiled intact.
  WOL NAT, GameSpy QnR, PC server-control, slave-process, and auto-restart
  endpoints are inert below that route; they do not create a substitute
  campaign, menu, or network stack. This 52-unit frontier compiled normally,
  under ASan/UBSan, and for ARM; its 91-symbol link remainder must be closed
  with original owners before runtime activation.
- **2026-08-16 — A4 host link closure.** The initial 494-unit host target selects and
  links the original GameMode, CombatGameMode, campaign, dialog, WWUI, and
  lifecycle owners. Normal, ASan, and UBSan two-cycle M00 runs pass. The
  existing direct M00 harness remains the registered runtime mode because
  entering CombatGameMode's full virtual/menu graph would activate still
  unported multiplayer-presentation and desktop-service owners. This is a
  bounded original-source closure, not a substitute frontend and not a new
  device candidate.
- **2026-08-16 — A3.2 diagnostics collector hardening.** Resolve the requested
  ZIP path before changing into temporary staging, and content-prefix returned
  evidence filenames. This prevents relative-output loss and duplicate basename
  collisions without retaining source paths. Archive integrity tests pass; the
  frozen candidate and its existing evidence archive are unchanged.
- **2026-08-16 — A4 ARM closure.** The initial 494-unit authentic frontend/campaign
  selection now links as a Vita ARMv7 ELF with the same VitaGL, vitaShaRK,
  FreeType, and platform-stub boundary as the packaged target. The build uses
  VitaSDK FreeType rather than an x86 host ELF and admits the existing Vita
  breadcrumb owner only for cross compilation. This is a source-closure check;
  it does not alter or supersede the frozen A3.2-dev1 hardware candidate.
- **2026-08-16 — Main-menu resource alias closure.** GDB caught
  `MainMenuTransitionClass::Update_Controls` dereferencing a null control in
  the host lifecycle run. The cause was deterministic: the `chat.rc` template
  generator read only `resource.h`, leaving `dialogresource.h` expression
  aliases at ID 0. It now resolves the restricted macro-expression graph from
  both official headers, and the resource contract asserts the exact six
  original transition IDs. `RenegadeDialogMgr`/`MainMenuDialog` then complete
  three original update/render frames and clean shutdown in normal, ASan, and
  UBSan M00 runs. This changes no A3.2 artifact or device behavior.
- **2026-08-16 — Original MenuGameMode lifecycle.** Select original
  `gamemenu.cpp` in the A4 closure and isolate its unused `wolgmode.h` include
  under the existing Vita single-player boundary; WOL behavior is neither
  compiled nor emulated. Let the original file own `g_is_loading` rather than
  keeping a duplicate boundary global. A silent `WWAudioClass` edge returns no
  fabricated sound effect and records only the original active sound-page
  state; original menu code safely handles the null result. The resulting
  495-action normal, ASan/LeakSanitizer, targeted-UBSan, and ARM closure
  registers `MenuGameModeClass2` before original
  `Goto_Location(LOC_MAIN_MENU)`, verifies that that original route activates
  it, dispatches three manager-driven Think frames, then safely deactivates
  and removes it around real `MainMenuDialog` construction. This is not device
  activation and does not alter the frozen A3.2-dev1 package.
- **2026-08-16 — Original campaign catalog lifecycle.** Before attempting a
  full campaign start, execute `CampaignManager::Init` and its matching
  `Shutdown` around each direct M00 cycle with the original retail factory
  stack. Both normal and ASan/LeakSanitizer runs load 36 `campaign.ini` flow
  records, then clear the original flow table before the second cycle; the
  same closure ARM-links. Do not invoke `Start_Campaign` merely to obtain a
  screenshot: its genuine next owner is `GameInitMgrClass::Start_Game` through
  the registered `CombatGameModeClass` graph, which is not yet device-ready.
- **2026-08-16 — Direct M00 teardown closure.** The direct development route
  now follows the original level and session owners rather than terminating
  after process-level Combat shutdown: it unloads the level, flushes local
  transport, removes original players/teams, and drains pending network
  objects. A focused staged `cNetwork` patch returns the temporary factory
  file used for data CRC, while the existing no-output WWAudio boundary clears
  its empty cache state when Combat unloads. Normal, ASan/LeakSanitizer, and
  UBSan two-cycle M00/HUD runs pass; this did not alter frozen A3.2-dev1.
- **2026-08-16 — Direct M00 single-player owner.** Replace the direct
  harness's duplicate `cSinglePlayerData`/`cGameDataSinglePlayer` setup and
  teardown with original `GameInitMgrClass::Initialize_SP` and matching
  `Shutdown`. Retain the direct original M00 loader between those owners:
  original `Start_Game`/`End_Game` require the complete registered Menu and
  Combat virtual-mode graph, which the harness must not counterfeit. Normal,
  ASan/LeakSanitizer, UBSan, and ARM closure pass with this boundary; it does
  not change the frozen A3.2-dev1 package.
- **2026-08-16 — Retained host-render regression closure.** Fresh deterministic
  staging made the existing original `AssetManager`/`WW3D` Font3D and Render2D
  references visible to the A2.2 and A3 world/seed host targets. Add their
  existing original Font3D, Render2D, Render2DSentence, Targa, bitmap-format
  owners plus the already-production Vita surface/FreeType boundary to those
  host-only test targets. This restores the canonical retained gate without
  altering the A2.2 manifest, renderer behavior, or frozen A3.2-dev1 package.
