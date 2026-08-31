# Known gaps

## Current dev98 mandatory frontend and readiness gate (2026-08-31)

The dev84 physical return reported menu audio with a black panel and no intro
movies. Dev85 corrected the proven platform boundary: the original
`GameModeManager` suppresses all rendering when `ConsoleBox` is exclusive, but
Vita has no desktop console to own the framebuffer. It also re-enables the
existing FFmpeg BINK provider and makes one movie upload failure local to that
movie. These corrections have passed focused source validation and canonical
ARM/package validation, not physical acceptance.

The matching dev85 VPK is deployed and its first physical return is a failure,
not acceptance: EA_WW.BIK is visibly present but extremely slow with
buzzy/laggy audio, and Start reaches an original main-menu dialog with missing
items. The returned log proves the BINK path and main-menu owner execute; it
also proves the Vita-only `MainMenuTransition` bypass.

Dev86 restored that original transition/control-placement path, presented a
bootstrap status before retail filesystem/pre-cache work, and prevented BINK
from submitting an empty startup/starvation audio buffer. Its returned physical
result remains a usability failure: intro A/V is slow/buzzy and the menu labels
are absent. The returned log isolates two bounded dev87 leads: Vita procedural
font textures had no native allocation, and EA video uploads consumed
13.48 seconds across 202 frames (68.90 ms worst).

Dev87 restored the existing Vita texture allocation for the original glyph
atlas and changed only the BINK boundary's in-memory upload representation to
RGB565 (the unchanged retail BIK files and original movie owner remain intact),
but its returned physical gate still failed: original menu text was absent,
intro A/V was slow/buzzy, and the original dialogue box was empty. Dev88 then
applied the original indexed glyph texture-stage combiner immediately before
those shared menu/dialogue draws and increased the real decoded BINK audio
startup reserve from one to three output buffers. Dev89 then scoped the
original frontend to its 800×600 logical layout, validated `StyleMgr` font
glyph availability before menu input, tried multiple retail font filename
variants, flushed the native bootstrap screen before filesystem/cache work,
expanded source-owned UI/HUD/M00 pre-cache touches, cleared leaked Render2D
texture-stage state, dropped late BINK video frames after the first visible
frame, and scoped camera-projected target boxes to native WW3D coordinates.

Dev90 kept the debug/status screen alive through original engine setup,
clamped 800×600 retail BINK uploads to an aspect-preserved 640×480 maximum,
fed synchronous M00 level-load milestones into the loading presenter, hardened
font-file reads and FreeType glyph clipping/atlas clearing, prevented gameplay
Start from entering the observed ESC/pause crash path, and returned target
boxes to their original HUD logical-space owner after Dev89's native coordinate
override overcorrected physically. Dev91 then reduced startup artificial holds,
downscaled unchanged retail BINK uploads to 480×360 with a larger audio startup
reserve and earlier late-frame dropping, added loading-progress catch-up
renders, treated empty FreeType bitmaps as valid spacing glyphs while requiring
visible StyleMgr probe pixels, and added bounded vehicle/HMVV proximity
diagnostics. Dev92 is a superseded local-only successor: it measures FreeType
glyph cells from advance plus bitmap bearings before rasterization, requires
visible glyph columns in readiness probes, lowers unchanged retail BINK upload
work to a 320×240 cap with a smaller per-update budget and bounded update
iterations, uses explicit decoder audio-layout fallback for movie resampling,
and adds bounded target-box projection diagnostics before another coordinate
rewrite. Dev93 then held/repainted early
native bootstrap status before filesystem/pre-cache work, fixes Render2D text
atlas height allocation and independent UV scaling, clears new glyph buffers,
adds bounded text-atlas/dialog-template diagnostics, and scopes gameplay
HUD/TextDisplay presentation to native 960×544. Dev94 then kept the bootstrap
framebuffer alive until WW3D initialization,
routes original saveload status/count changes into the active loading
presenter, applies deferred DX8 shader/texture/transform state before indexed
Render2D text/HUD draws, scopes HUD `Think()` geometry through native gameplay
presentation, drops late BINK video frames when queued audio is under pressure,
and host-validates six original main-menu translations from `STRINGS.TDB`.
Dev95 is superseded local-only history: it preserves Dev94 and forces
`MessageWindowClass::On_Frame_Update()` and `Update_Window_Rectangle()` through
the gameplay-HUD presentation scope so update-time dialogue/message layout does
not cache geometry outside the render presentation. Its focused/fast/canonical
closure passes, but it is local only. Dev96 is superseded local-only history:
it preserves Dev95 and adds UTF-16-safe wrappers for `wcsncmp`, `wcsncpy`,
`wcschr`, and `wcsstr` at the Vita short-`wchar_t` boundary, with host probes
and contracts for original frontend/dialogue/HUD call sites. This targets text
paths that can use Windows 16-bit `WCHAR` data against libc wide routines with
a different native ABI. Dev97 is superseded local-only history: it preserves
Dev96, adds a bounded UTF-16 formatter for original formatted menu/dialogue/
HUD/pickup/ammo/health text, and records candidate-scoped startup-precache
status before original retail root/MIX file factory construction. Dev98 is the
current local-only successor: it preserves Dev97, starts BINK presentation
timing only at audio/video presentation, bounds Vita WWUI dialog-template
translation copies into the remaining original text buffer, and scopes
`HUDClass::Init()` through native Vita HUD presentation so persistent Render2D
HUD elements are initialized in the same coordinate range used for per-frame
rebuilds. Its focused/fast/canonical closure passes, but it is also local only.
The
user-required release gate remains: a visible original intro with usable A/V
and a visibly labelled original menu before any further Vita candidate push.
No visual, pacing, or audio acceptance claim is valid until a matching physical
return. HUD/text, shadow, START-exit, HMVV freeze, loading-flash/progress,
front-end readiness, and gameplay performance remain open.

The later user-finalized Dev87 recorder MP4 supplies six settled M00 gameplay
stills in the historical gallery. It proves that this physical run reached
exterior, war-factory, and interior gameplay, but it neither covers a readable
original menu/subtitle state nor reverses the reported frontend, HUD,
performance, freeze, or START-crash failures.

The current Dev87 follow-up adds that the original menu text remains absent,
ammo and health glyphs are mangled, the NPC targeting/bounding-box indicator
has moved further right, and the pre-warm/pre-cache routine still begins after
an opaque black period. Treat these as retained panel observations pending
matching runtime evidence and source diagnosis; do not infer a single common
cause from them.

Current pre-cache is intentionally bounded: it indexes original archives and
warms small readable slices before frontend, including Dev90's inherited
frontend/menu/HUD/subtitle/pickup/shadow/objective/M00 touch list, then
performs one loading-screen frame and 60 M00 scene frames after loading. It does
not construct and retain whole BINK upload resources. A future readiness phase
must measure and retain only real reusable resources; reading/decoding whole
movies at startup would worsen the black period and is not adopted.

## Current dev82 physical-test gaps (2026-08-28)

A3.5-dev82 is built for manual physical testing, but not accepted. It
specifically targets the latest reported M00 tutorial defects: incomplete
loading-screen coverage/text/progress, mangled HUD, missing subtitles/dialogue
text, inverted or drifting camera controls, missing action/use mapping, missing
reload animation, wrong or upside-down NPC/Havoc/door/powerup/objective
textures, wrong sniper scope/icon/zoom behavior, D-pad weapon switching also
turning the camera, bounding boxes floating off target meshes, random rectangle
ground shadows, FPS regression, unopened gate, top-screen white icon during
Logan dialogue, and the freeze after trying the gate after pistol/fire
interaction.

The latest dev82 candidate includes source/build fixes for the highest-risk
visual/input/reload regressions: frontend/menu input is gated from gameplay,
TextDisplay initializes after final StyleMgr reinitialization, Render2D dynamic
FVF normal/UV1 fields are initialized for HUD/loading/subtitle/scope/bounding
box draws, Render2D restores the previous DX8 viewport after fullscreen 2D
passes, passthrough texture V is corrected after original DX8 texture
transforms, DX8 render-state ownership is centralized in the renderer boundary,
and the first-person weapon view has a bounded visible reload fallback while
the original weapon state is reload. The current source also writes persistent
M00/M01 MIX filename cache indexes during the visible startup
pre-cache/pre-warm/pre-compute phase; Vita3K evidence proves those cache indexes
are generated before frontend, movies, or gameplay, but physical Vita
confirmation is still required before removing the defect from this list.

The next engineering decisions must come from the dev82 runtime log and
physical observation. If the gate still fails, inspect transition/action
diagnostics and original `CombatGameModeClass` finalization before changing
mission logic. If dialogue text remains absent, inspect TextDisplay/HUD
initialization and conversation breadcrumbs before adding UI shortcuts. If
skins, doors, objectives, or powerups remain wrong, inspect texture provenance
and DDS row-orientation breadcrumbs before changing material ownership. If the
freeze repeats, collect and symbolicate only against the matching dev82
ELF/map/symbol set.

Bink movie ownership is implemented in the dev82 frontend integration through a
pinned, Bink-only Vita FFmpeg build. The historical dev82 candidate disabled
realtime playback after black-screen/audio-underrun evidence; dev85/dev86
re-enable the provider below the unchanged original `MovieGameModeClass`.
The Vita boundary resolves unchanged retail `.BIK` files and logs their path;
dev86 fails only a failed movie and retains bounded pacing evidence rather than
claiming realtime performance. Physical Vita
validation of movie-file presence, skip behavior, decode speed, orientation,
A/V synchronization, and a later re-enabled playback candidate is still
required before intro playback can be accepted.

## Reconciled program status (2026-08-24)

The frozen A3.2-dev1 package is a failed physical checkpoint, not a candidate
awaiting acceptance. A3.5-dev6 now physically passes original Combat pause;
A3.5-dev7 proves ground contact, movement, Square delivery, and isolated
original fire while its combined external injection sequence remains
nondeterministic. A3.5-dev12 physically restores ordinary NPC body geometry
through the original deformed-skin/identity-world submission and adds a bounded
native route recorder/replayer. Dev13 then physically recorded 4,537 samples
and reached the post-ladder Logan interaction, but failed: NPC materials were
wrong, audio was absent, the sky was black, and the original conversation
remained active with control disabled and no pistol grant. Zero indexed draws
proved the sky bridge was unreachable because Vita initialized original
BackgroundMgr with rendering unavailable. Exact dev7 is restored; the dev13
route is retained.

Dev14 restores original background construction, original mesh
DCG/VertexMaterial color ownership, and observation-only conversation state.
A3.5-dev15 retained those fixes and linked the essential audio device boundary
beneath all 20 selected original WWAudio translation units, but later source
review found its Vita entry point still used lite audio without initialization
or per-frame service. It was never deployed and is superseded.

A3.5-dev16 installs the rooted retail/MIX chain, creates Renegade's
basename-stripping audio adapter, constructs and initializes non-lite original
WWAudio before engine/world setup, requires the original sound scene and
Vita-backed 2D/3D drivers, calls `On_Frame_Update` during active and suspended
frames, and destroys audio before renderer/factory teardown. Fresh D:-retail
M00/M01/City two-cycle routes, ASan, LeakSanitizer, targeted UBSan, 42 tests,
deterministic 113-patch staging, all 482 ARM/package actions, identity,
manifest, linked-symbol, and retail-exclusion gates pass. The provider has
fresh focused/sanitizer/ARM evidence, while the full host harness intentionally
does not claim audible execution. Exact physical route replay remains pending.
Audio is therefore not physically accepted. The restored update is required
for playback completion and sound-ended events, but original conversation
remark timing is separately TimeManager-owned; diagnostics must isolate the
Logan failure before any causality or behavioral claim. Whole-track stream
decode is bounded but not yet resource-measured or incremental, and retail M00
codec coverage is hardware-dependent. The official Mission00 provider's full
completion remains unaccepted. Repeated-session soak remains a v3.9 gate.
The retained dev19 pistol-shot crash is now source-addressed only: VDB
symbolicated its data abort to `GenericDataSafeClass::Get_Entry`, and dev37
adds release-build invalid-handle guards. Dev38 retains that guard and adds
returned schema-v4 loading visual-gate metadata. This does not physically prove
pistol-shot stability or loading-screen correctness; dev38 has no Vita run yet,
and the latest user-reported dump was not retrieved because device FTP refused
`ux0:/data`.

v3.6–v4.0 contracts,
including resource/memory, renderer performance,
authentic frontend/HUD/audio, campaign, and Direct-IP/LAN provider work, are
tracked in `PROGRAM_CHARTER.md` and must not be inferred as complete from this
partial v3.5 return.

- The direct host/Vita Combat route restores the original `PathMgrClass`
  application lifecycle after a canonical LSan run found one retained
  `PathSolveClass` (80,256 bytes). Its focused two-cycle M00 sanitizer rerun
  is clean. A3.5-dev5 now physically completes two successive original
  load/START-exit/teardown sessions; device memory behavior and the later v3.9
  bounded soak remain unvalidated.

- A3.2-dev1 restored the original texture route and diagnostic fallback. The
  matching A3.5-dev5 late spawn capture physically shows the textured M00 subset
  and first-person weapon, while complete texture/material/alpha/multistage
  coverage remains unvalidated; A3.1.4 remains the frozen accepted baseline.
- The official TT 4.8.4 revision-9000 source/diff audit is integrated as an
  out-of-tree, checksum-pinned toolkit step. Its micro-chunk, LineSeg, and
  relative-timer semantics are already/equivalently present in EA source. TT's
  Communications Center crash, controller, WWAudio, lighting, and renderer
  fixes cannot be imported from changelog prose: the public scripts.dll delta
  lacks those engine implementations or they are PC-platform-specific. See
  `TT_PATCH_INTEGRATION.md`.
- A3.1.4 right-stick look was unusable because the platform emitted ±32767 to
  an original consumer expecting ±1000. The central conversion is host-tested
  and A3.5-dev5 physical checkpoints now record bounded logical look values and
  camera input. Longer usability and pause behavior remain open.
- Font3D/HUD now passes the original Targa/Surface/Texture, RadarManager, and
  Render2D path in optimized and ASan two-cycle M00 runs. Native HUD promotion
  remains pending A3.2 hardware evidence and a separate candidate; the audio
  provider is focused-host/sanitizer validated and dev16's original-WWAudio
  lifecycle is contract-checked and ARM-linked, but physical output remains
  unaccepted.
- The authentic `FontCharsClass` provider now obtains Regatta and Arial from
  retail archives through the original file factory and passes ASan memory-safety
  cycles. The current HUD-enabled two-cycle M00 route is leak-free under
  LeakSanitizer after restoring original Combat/GameInit shutdown ordering and
  the `cNetwork` factory-file return. This is host evidence only; repeated
  load/exit behavior still needs physical Vita confirmation before resource
  ownership is considered closed.
- The authentic frontend requires the original WWUI StyleMgr/DialogMgr/MenuDialog
  stack plus controller-facing WWUI input. Its 90-source staging pool and retail
  menu models (`IF_BACK01`, `IF_RENLOGO`, `IF_EVAGIZMO`) are available; no
  substitute menu is used. `StyleMgrClass` now compiles, ARM-links, and performs
  two host `stylemgr.ini` font lifecycles through the provider. The expanded
  52-unit frontend/campaign probe compiles the selected full control set,
  Render2D/StyleMgr, Campaign, GameMode, SaveGame, and GameInitMgr under host,
  ASan/UBSan, and Vita ARM. The earlier frozen-ELF audit found 91 references
  beyond the A3.2 package. A separate 495-unit target now link-closes the
  selected owners normally, under ASan, under UBSan, and as a Vita ARMv7 ELF
  against the production renderer/platform libraries. This still does not
  establish a device runtime menu. The later original `MenuGameModeClass2`
  lifecycle now registers before the original `Goto_Location(LOC_MAIN_MENU)`
  route activates it, then receives three manager-driven Think frames before
  safe removal around the real dialog lifecycle under normal,
  ASan/LeakSanitizer, targeted UBSan, and ARM closure; it still requires the
  physical A3.2 gate before any device-menu or campaign-launch claim.
- The bounded frontend probe now compiles original DialogParser, DialogMgr,
  WWUIInput, DialogControl, MenuDialog/MenuBackDrop, mouse, tooltip, transition,
  `RenegadeDialogMgr`, and real `MainMenuDialogClass`. The real map-enumeration
  boundary resolves only beneath the retail root and passes a normal + ASan
  ten-check case-fold/wildcard/traversal contract. Its Vita selection retains
  only original Main Menu/Start SP/options/difficulty/load/quit factories;
  WOL/LAN factories are explicitly unavailable until their original providers
  are ported. The installed `game2.exe` resource table was rejected: its
  purported dialog leaves resolve to executable bytes, not valid templates.
  The replacement boundary deterministically compiles canonical released
  `chat.rc` records, not handcrafted layouts or retail assets. `DialogBase`,
  dialog text, Button/MenuEntry, ListCtrl/ScrollBar/ListIconMgr now compile,
  but the genuine link/runtime closure and Vita observation remain. Original
  `EditCtrl` requires the full
  IME composition/candidate service. Do not replace it with a synthetic edit
  control; complete a real Vita text-composition boundary before enabling IME
  use at runtime.
- The actual `StartSPGameDialogClass` and `DifficultyMenuClass` bodies are now
  selected from original shared `dialogtests.cpp` under a Vita single-player
  compilation boundary. The tutorial button retains the genuine
  `cGod::Reset_Inventory` → `CampaignManager` → `GameInitMgrClass`
  `Initialize_SP`/`Start_Game("M00_Tutorial.mix")` route, while difficulty
  retains original `Start_Campaign`/replay routing. Its unrelated WOL/LAN and
  GameSpy implementations remain conditionally excluded because their first
  declaration dependency is `gamechannel`/`WWOnline`; full menu linking,
  ownership, and runtime activation remain unproven.
- `GameInitMgrClass` now compiles with its original SP initialization, start,
  load, exit, and return-to-dialog ordering intact. Only retired WOL NAT,
  GameSpy QnR, PC server-control, and auto-restart service endpoints are
  isolated below that branch; they are inactive rather than emulated. The
  original `CombatGameModeClass::Load_Level` owner is now selected into the
  495-unit host link, but the direct M00 harness deliberately does not execute
  its full virtual/menu graph. Its remaining multiplayer presentation and
  desktop-service owners must be closed before this becomes a campaign-launch
  claim.
- The authentic `LoadSPGameMenuClass` now compiles at the same host, sanitizer,
  and Vita ARM boundary. Its original saved-game/map enumeration and launch
  routes use Vita `FindFirstFile`/`FindNextFile` and a bounded pointer-token
  compatibility bridge. It has not been linked into a device runtime: actual
  list ownership, save deletion, map launch, and repeated menu transitions
  require the A3.2 physical gate and a subsequent candidate.
- The original `ListCtrlClass`, embedded scrollbar, and list-icon manager now
  compile with Load-SP and their narrow compatibility contracts are tested,
  but rendering, focus, and repeated ownership behavior are not linked or run
  on Vita yet.
- The frozen A3.2-dev1 diagnostics ZIP and collector are validated. The
  collector now resolves output paths before temporary staging and content-
  prefixes returned evidence to avoid basename collisions. Phase-specific
  screenshots and runtime captures now have matching dev5 physical returns,
  including a clear manual post-readiness M00 capture; the stale automatic
  post-swap capture timing remains a diagnostic-readback defect and is not used
  as visual acceptance evidence.
- The configured Vita3K data root contains only the historical A3.1
  `RNEGA3101` installation; no A3.5 VPK is installed and no executable/log
  location is configured. `VITA3K_EVIDENCE.md` records the observed title
  identity and the controlled user-mediated replacement/collection loop. This
  is an emulator-automation gap, not a reason to delay physical Vita testing.
- Official M00 script registration/creation code is now linked in dev8, but no
  physical script attachment, mission progression, playable campaign slice,
  AI encounter, readable HUD, or essential-feedback claim is made from that
  host/ARM result. Representative campaign acceptance remains an A4.0 gate.
- The returned A3.5-dev4 static-world screenshot observed invisible NPC/player
  bodies, an incorrect first-person weapon, upside-down doors, and an inverted
  static overhead-camera vertical axis. Because its executable identity and
  runtime evidence were contaminated, these are retained as visual/input
  investigation leads, not physical validation of a corrected candidate. Do
  not change original Combat player, NPC, weapon, or door behavior based on
  that capture alone; collect a phase-labelled interactive capture first.
