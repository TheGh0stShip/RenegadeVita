# Renegade Vita port status

Updated: 2026-08-31. Engineering changes use source-driven review, bounded
ownership, deterministic staging, and independent validation.

## 2026-08-31 Dev87 physical failure; Dev88 local candidate

Dev87 is retained physical frontend usability failure evidence. Despite a
hash-matched installed executable, the user reports absent original menu text,
very laggy/buzzy intro movies, and an empty original grey gameplay
dialogue/subtitle box. The matching partial log,
`build/device-evidence/a35-dev87-user-return-20260831T022728Z/a35-dev87-runtime.log`
(SHA-256 `a01c0b54159fefa2fa4c4ebefdaf181f11330f23e0287f2b426e7cbb1eac911c`),
ends at original main-menu activation; it does not prove gameplay subtitle
data availability or visible glyph correctness. User-taken Dev87 screenshots
remain pending title-scoped retrieval, visual review, accurate gallery/timeline
labelling, and GitHub publication.

Read-only device discovery later established the actual capture boundary. The
checked-in VDB client can collect repeated, exact-title logical-framebuffer
screens through `capture.screen.v1` (up to 16 labelled captures per evidence
bundle), but this Vita currently runs VitaCompanion and advertises only
`screen.v1`; its `screen on|off` route controls panel power, not capture. The
separate VDB target-local agent and authenticated gateway are not installed.
The top-left red `R` is instead the installed title-scoped MP4 recorder: it
autostarts with `RNEGA3101` but finalizes only on L+Start or clean module stop,
so a crash need not leave a recoverable file. After the user's explicit video
retrieval request, forced VDB1 search `ux0:/video` for `*.mp4` returned zero
matches; receipt:
`build/device-evidence/a35-dev87-user-return-20260831T022728Z/video-find-after-user-request.json`.
No game rebuild, retimed capture, Vita filesystem change, or capture-provider
installation occurred during this discovery.

The original `MessageWindow` dialogue `TextWindowClass` and original menu
`Render2DSentence` both use dynamic indexed glyph draws. Dev88 applies the
original `ShaderClass` texture-stage combiner state immediately before those
draws, preventing the A4R4G4B4 atlas from inheriting an incompatible alpha
rule from a previous mesh. It changes no game owner, text database, or retail
asset. Dev88 also raises the BINK audio start reserve to three real output
buffers (about 64 ms) to tolerate a frame upload/decode stall without instant
audio starvation; no BIK is repackaged or modified.

Focused tests (54) and `git diff --check` pass. Canonical Dev88 passed 115
current contracts, deterministic staging, 549 ARM/package actions, identity,
archive, diagnostics, and retail-exclusion checks in
`logs/a35-dev88-20260830-214253-build.log`. VPK SHA-256 is
`be78097b98a3c0a0e9e9cd1fbdb0d5cdb9d7d630145bec8736d7ebad0cf07138`; packaged
SELF SHA-256 is `cd5726251dbdd33c2d19a97aa83ccc95d992ad6800c945497ec473fe40228fce`.
It is local only: no Dev88 file has been copied to, installed on, or launched
on the Vita.

Dev88 source, focused contracts, canonical identity, and the explicit Dev87
failure record are published at `origin/main`
`0807c1733ea45993ac8fca9f49858a0daafc83f1` (`Fix Dev88 frontend text and BINK
audio reserve`). No Dev87 image is present in the title-owned `screenshots` or
Dev87-window `captures` entries. The gallery update is therefore pending the
actual screenshot evidence, not represented as completed.

## 2026-08-31 dev87 frontend repair candidate — historical pre-return record

Dev86 is now retained physical failure evidence, not a pending observation. Its
matching runtime log proves the original BINK, menu, loading-screen, and M00
owners executed, but the user reports that the main-menu labels are still
missing and the intro is still extremely slow with buzzy/laggy audio. The one
returned capture is explicitly labelled an `original-loading-screen`/
`level-ready` diagnostic; it is not a menu or gameplay acceptance frame.

The concrete text lead is source-owned. Original `Render2DSentence` constructs
a procedural A4R4G4B4 glyph texture and writes glyph data through its surface.
The Vita-only branch had deliberately left that texture unallocated. Dev87
restores the existing Vita DX8 texture allocation path for that original
procedural texture, while retaining the unsupported desktop tracker solely in
the non-Vita branch. This is a candidate fix for blank WWUI, HUD, loading, and
dialogue glyphs, not a visual success claim.

The matching dev86 BINK statistics identify video upload rather than retail
asset conversion as the leading measured movie cost: EA_WW.BIK took
13,476,510 us across 202 uploads (68,901 us worst) versus 1,561,800 us video
decode and 671,221 us audio decode. Dev87 keeps the original movie owner and
unchanged retail BIK files, but uses an in-memory RGB565 upload surface for the
same 800x600 decoded frame, reducing the padded 1024x1024 upload from 4 MiB to
2 MiB. Its visual/color and physical A/V result remain unmeasured.

`tools/build_fast_candidate.sh` passed 89 focused contracts, deterministic
staging, ARM link/SELF/VPK identity, compressed-archive integrity, and SHA
validation in `logs/a35-dev87-fast-20260830-204232-build.log`. FastBuild is an
iteration gate only; canonical `bash ./tools/build.sh` has now independently
passed retained host/current contracts, deterministic 136-patch staging, 549
ARM/package actions, original-runtime symbols, ELF/SELF/VPK identity,
compressed VPK validation, diagnostics, and retail exclusion in
`logs/a35-dev87-20260830-204706-build.log`. Canonical VPK/ELF/SELF SHA-256 are
`bbb48f91c879c99e2944497b97a56cbf1e015c7af4a20ed75871bf02bb86e521`,
`cd50c8a7c1c406bf324996d09fe74755e757230619ac003099bf103d9b829194`, and
`d7bdadbff7296dad0d5460d0febfe70116502c9a80695bfa3577f6c629f9c596`.
Source, tests, reports, and the explicitly diagnostic gallery item are now
published to `origin/main` at `015c83bde9653fc9bfc58f1a731eb2492e351558`
(`Fix dev87 frontend glyphs and BINK upload`). VPK/ELF/SELF, logs, raw capture,
video, diagnostics ZIP, dumps, retail data, saves, and credentials are excluded.

After explicit READY, dev86 was stopped and backed up locally under
`build/device-backups/a35-dev87-install-launch-20260831T022343Z/`; its hash
matched `3b20079eca192cdf2d5869fbc3bfb485ec0528cfa2969f006a60f9567b44b4a8`.
The exact dev87 VPK and staged SELF were hash-verified in the title-scoped user
area, and only `ux0:/app/RNEGA3101/eboot.bin` was replaced. The provider reports
`atomic=false` and no remote backup, while the verified local backup is retained.
Installed readback is the canonical dev87 SELF
`d7bdadbff7296dad0d5460d0febfe70116502c9a80695bfa3577f6c629f9c596`; the
zero-input launch was accepted and `RNEGA3101` remained running. This is a
handoff fact only, not physical frontend acceptance. Runtime logs, captures,
recordings, and dumps have not been pulled. The user has reported screenshots
were taken; after the manual run ends, every returned dev87 image must be
inventoried, accurately labelled, added to the gallery/timeline, and published
with the matching evidence receipt.

## 2026-08-30 dev86 frontend evidence candidate — canonical package, physical usability failure

Dev85's exact physical return is retained as a failure: the EA movie was
visible but extremely slow with buzzy/laggy audio, and Start reached a
main-menu dialog whose items were missing. Its matching log proves that the
original BINK and main-menu owners executed, and specifically records the
Vita-only `MainMenuTransition` bypass.

Dev86 makes three bounded corrections without replacing the original owners:

- It removes only those Vita-only early returns so original
  `MainMenuTransitionClass` can run its control-placement update again.
- It prints native bootstrap progress immediately after debug-screen setup and
  before user-tree/filesystem/retail pre-cache work, replacing the otherwise
  opaque initial black period with progress information.
- Its FFmpeg BINK boundary never submits a zero-filled startup/starvation
  audio buffer. It waits for real decoded samples and emits bounded end-of-movie
  timing/output statistics to measure the slow video/audio path.

Focused contracts (18 tests) pass. Canonical `bash ./tools/build.sh` passed
retained host validation (112 tests), deterministic 136-patch staging, 549
ARM/package actions, original-runtime symbols, ELF/SELF/VPK identity,
compressed VPK validation, diagnostics, and retail exclusion in
`logs/a35-dev86-20260830-195426-build.log`. VPK/ELF/SELF SHA-256 values are
`9a9f36c15f699b72e736f2b2a4b29d4e57537e59c3cfeb5b41f206884b85aa10`,
`954be81d22f9c0ec527549b84b39ce9e87e5ed61eddcd130b74ac53021ec540d`, and
`3b20079eca192cdf2d5869fbc3bfb485ec0528cfa2969f006a60f9567b44b4a8`.
The VPK contains only `eboot.bin` and `sce_sys/param.sfo`.

After explicit READY, doctor/capability preflight passed. The VPK and staged
SELF are VDB1 hash-verified in the allowed Renegade user tree; the prior dev85
SELF is retained locally by hash. Only `ux0:/app/RNEGA3101/eboot.bin` was
replaced, and installed readback matches dev86 SELF
`3b20079eca192cdf2d5869fbc3bfb485ec0528cfa2969f006a60f9567b44b4a8`.
The launch request was accepted and title status was running after 15 seconds,
with no synthetic input. The provider did not retain a remote replacement
backup, but the local dev85 backup is verified; this is a launch receipt, not
a visual or A/V acceptance result.

The returned physical gate fails: the user reports a long initial black period,
original EA intro that remains very slow with buzzy/laggy audio, and a main
menu whose labels are missing. The matching returned runtime log is
`a35-dev86-runtime-user-report.log`, SHA-256
`2294297c434034fee78c0d92285346cb913265b501fb7793217b640c739cb9c4`; it shows
both original movies, Start skip, original loading/progress ownership, and M00
prewarm. The only returned capture was published to the historical gallery as
an explicitly diagnostic original loading-screen frame. No finalized video was
returned, so none is claimed or published. Detailed evidence and the dev87
performance decision are in `reports/A35_DEV86_DEV87_FRONTEND_EVIDENCE.md`.

## 2026-08-30 dev85 mandatory frontend correction gate — canonical package, not physical proof

The user prohibited another Vita candidate push unless the original intro
movies and original menu black-screen fault are addressed. Dev85 therefore
keeps the original `GameModeManager`, `MovieGameModeClass`, `MenuGameModeClass2`
and BINK owner paths, while correcting two Vita-only boundary conditions:

- `ConsoleModeClass` is non-exclusive on Vita and the runtime explicitly clears
  `ConsoleBox` before the original frontend loop. The original
  `GameModeManager::Render()` otherwise deliberately suppresses WWUI and BINK
  rendering while a desktop console is exclusive; this explains menu audio with
  a black panel without substituting a menu renderer.
- The Vita FFmpeg BINK provider no longer contains dev82's deliberate
  playback-disable branch. Provider failure now releases only the failed movie,
  rather than disabling every later startup movie after one texture upload
  failure.

`git diff --check`, Python syntax checks, and 27 focused frontend/loading,
candidate, and recorder workflow tests pass. Canonical `bash ./tools/build.sh`
also passed retained host validation (112 tests), deterministic staging, 549
ARM actions, original-runtime symbol checks, ELF/SELF/VPK identity, compressed
VPK validation, diagnostics, and retail exclusion in
`logs/a35-dev85-20260830-191010-build.log`. The retained VPK and packaged SELF
SHA-256 values are respectively
`299c5f79bd7657a4b9598f300688d4620abc9ece483d23542172ede34d033b58` and
`d26321f2702b467eb8cd2ecfe8379af081715558a3d0b6b90659616db78f62f1`.

Before the current physical test this was local build evidence only. It has now
been deployed as the hash-matched dev85 candidate, but there remains no
acceptance claim for intro frames or menu visibility: the returned physical
result must satisfy both mandatory gates with matching media and logs.

That physical test is now returned and fails the mandatory usability gate. The
exact VPK and SELF were VDB1 hash-verified before launch. The user observed
the EA intro but reports it is extremely slow with buzzy/laggy audio; Start
skips to a main menu with missing items. The matching dev85 runtime log records
EA_WW.BIK completion, R_INTRO.BIK decode/upload, the physical Start skip, and
original menu construction/activation. It also records that the Vita-only
`MainMenuTransition` bypass was taken. Therefore video playback and menu
visibility are not accepted: the next source work restores original transition
control placement and measures the BINK audio/video pacing fault.

The corresponding source, tests, and durable reports are published at
`origin/main` commit `4f9dacacdc157636058bb8626e02b4310b7f2ba9` (`Fix dev85
original frontend presentation`). Build artifacts, PSP2 dumps, captures, video,
and retail data are intentionally excluded from Git.

## 2026-08-30 dev84 capture-policy route: stale recorder crash, not M00 evidence

The user reported a prolonged black screen, eventual diagnostic pre-cache, and
crash. The title is stopped and all synthetic input was released. The installed
SELF still hash-matches the capture-policy rebuild
`555f0c1f83b46992b0e349b8c1d2c4500daaeb2d945311926d33f3d824590bbe`.
The returned 14,139-byte runtime log completed the original-owner pre-cache in
5,023/5,027 ms but has no subsequent frontend, M00, or capture-policy
breadcrumb.

Two newly returned PSP2 cores are retained locally only. Their verified title
thread PCs are `0x8146d5fa` and `0x814255fa`; source-derived module/load-bias
correlation places both at the same `+0x15fa` recorder display-hook offset as
the earlier recorder fault. Their private register records are unavailable, so
no framebuffer or full engine frame is claimed. Device readback proves the
configured title-scoped recorder user module is still stale
`8a856e76...`, whereas the guarded rebuild is `111d2f4f...`. This blocks
interpretation of the crash as a Renegade or capture-policy failure. There is
no finalized MP4 to upload. The detailed sanitized record is
`reports/DEV84_CAPTURE_POLICY_RECORDER_CRASH.md`.

Next is deliberately narrow: back up the stale title-scoped user recorder,
replace only it with the hash-verified guarded module, then perform a no-input,
finite startup check. The VPK/SELF and tai config are unchanged; no visual or
mission outcome is claimed.

The follow-up completed that narrow helper replacement. The stale helper is
backed up locally by hash; device readback now verifies guarded user helper
`111d2f4f...`, while the installed Renegade SELF remains `555f...0bbe`.
The first cross-mount atomic request was rejected before replacement; the
same-mount replacement succeeded but reports `atomic=false`, so the retained
local backup is the rollback receipt. The guarded run surpassed the former
crash point and reached original frontend, M00 finalization, original player
control, Logan conversation/audio, and frame-480 checkpoints. Physical stick
and touch samples appeared later in the log, but their actor is not inferred;
the agent injected no gameplay input and released controls. Automatic capture
remained disabled and no Select edge occurred, so this is not a screenshot or
visual-correctness result. The process remains live for the user’s observation.

## 2026-08-30 dev84 capture-policy rebuild; user READY received

The returned dev82 records prove that the former automatic
`first-interactive-player-frame` screenshot fired at engine frame 1. That is
an engine-ownership signal, not proof that the physical panel had settled: the
retained results include a duplicate loading image and a black/HUD-only image.
The capture-policy rebuild removes that automatic branch rather than guessing a
later frame delay. A capture now requires the original tutorial control handoff,
player control, scene/star/camera, all render phases, nonzero mesh/vertex/
triangle submissions, and no rejected or unsupported submissions; it is then
requested by a Select rising edge and labelled `manual-select-visible-gameplay`.
A recorded route may use that same Select edge at a fixed checkpoint.

Canonical validation passed in `logs/a35-dev84-20260830-182029-build.log`:
retained host validation, 111 tests, deterministic 136-patch staging, 549 ARM
actions, required-symbol checks, ARM ELF/SELF/VPK identity, compressed VPK,
SHA manifest, diagnostics, and retail exclusion. VPK/ELF/SELF SHA-256 are
`99aa5d5c295da232c535489c5e50c0d6fcc55ef9fe7e1704d63ba3ef1fa3e392`,
`15d2ecdd6fdb304f558a2f15d9ba37ef992813b5bf4fda3400284c4dff90430f`, and
`555f0c1f83b46992b0e349b8c1d2c4500daaeb2d945311926d33f3d824590bbe`.
The VPK inventory is exactly `eboot.bin` and `sce_sys/param.sfo`. It is a new
hash-distinguished `A3.5-dev84` rebuild, not the prior deployed dev84 binary.

The user supplied `READY` after the candidate completed. Before launch, the
bounded physical route will read back device identity/capabilities, back up the
currently installed title executable by hash, replace only `RNEGA3101` with
this matching build, verify its device-side hash, and release all synthetic
input after the fixed route. The visual/HUD/dialogue/texture/camera defects are
not claimed fixed by this capture-policy-only rebuild.

## 2026-08-30 dev84 recorder-confounded crash; device launch paused

The user-returned dev84 PSP2 core is retained at
`build/device-evidence/a35-dev84-start-crash-20260830T215650Z/` with SHA-256
`c42665a0a5a10f8e235b4096d4a1d4dbc2962ca68dcd5bafa8050d7f6cb683d8`.
Source-derived core records place the data-abort PC in the temporary,
title-scoped `VitaMP4Recorder` display-hook RX segment, not in the Renegade
RX segment. The core lacks usable thread-register evidence, so this is not an
engine-root-cause claim and does not validate the dev84 Start-exit correction.

The recorder patch now guards null/empty/malformed display notifications and
does not consume plain Start; its zero-fuzz patch application, 5/5 focused
workflow suite, and ARM user-plugin rebuild pass. No MP4 was finalized under
the title-scoped `ux0:/video` folders. Raw cores, runtime logs, and video
captures remain out of Git; the sanitized analysis is
`reports/DEV84_RECORDER_CRASH.md`. No new Vita launch or interaction may occur
until the user explicitly supplies `READY`. That release was supplied for the
current capture-policy candidate; this prior recorder evidence remains
historical and does not validate the engine Start-exit repair.

## 2026-08-30 dev84 Start-exit lifecycle correction

The physical dev82 Start crash produced one new PSP2 dump, retained under
`build/device-evidence/a35-dev82-start-crash-20260830T211316Z/` (SHA-256
`981a48faa0b949df02b2126149c45fe379e2a208ea84ac48793ea10ab1f69651`). VDB
reports a data abort at `0x811d4ab2`. The matching source location is
source-derived, not VDB verified: original `cPlayer::On_Destroy()` queried
Combat mode after runtime teardown had removed it. Dev84 now delays that mode
removal until after original player/session teardown; it introduces no
replacement game loop or teardown owner.

The fast dev84 package passed 35 focused source tests and 86 fast ARM/VPK
contracts in `logs/a35-dev84-fast-20260830-162553-build.log`: VPK
`86dea853d112c5eba9b088e0a107fd21b68a02bbfa9a029ee5b63aee1cf43bfd`, SELF
`6c61b6b656a3d2d74425a73885b6c8d78b11cbaa238e5079d800cdb1ef2ab332`, and
ELF `c96fa9169b61c6f31b42cdc9b8ef6c5cac394f22b2cf11354481ece203d0dc4f`.
Canonical validation passed in `logs/a35-dev84-20260830-163409-build.log`:
retained host validation, 111 tests, deterministic 136-patch staging, 549 ARM
actions, ELF/SELF/VPK identity, compressed VPK/SHA, diagnostics, and retail
exclusion. Its VPK/ELF/SELF SHA-256 values are
`6352b0e23a51e6943f2992843c97b8a07b9311877bffb69eeed06518e33e8051`,
`492501614f02c2477ecdfe253a54e853fdcc06a871c2b0ebf5985b72143a75f7`, and
`3c6304cc5fe13dbaf36ea27c6f32fc5fdac9a05c852e0416e519e42eb135d896`.
Hash-matched physical evidence is still pending.

The current exact dev84 VPK is hash-verified at
`ux0:/data/renegade/user/RenegadeVita-A3.5-dev84.vpk`, and its packaged SELF
is hash-verified at `ux0:/app/RNEGA3101/eboot.bin`. The previous dev82 SELF is
backed up in `build/device-backups/a35-dev84-recorder-20260830T215406Z/`.
Title-scoped recorder modules were added only to the `*KERNEL` and
`*RNEGA3101` tai entries with a backed-up config; both module and config hashes
were rechecked after upload. The returned recorder-enabled run stopped on a
recorder-hook data abort. It must not be counted as a Renegade Start-exit test.

The initial Dev82 gallery publication was insufficient: it left two copied
frames in an inventory row without a visible Dev82 gallery section. The
corrected README and historical timeline now display all four raw returned
capture records, their source paths, and their hashes. Direct review confirms
that `t54494725` and first-interactive `t64590857` are byte-identical inverted
loading images, `t67280479` is the letterboxed inverted variant, and
first-interactive `t88041059` is black with a partial HUD. These remain failed
diagnostic evidence, not gameplay acceptance. There is no finalized
title-scoped MP4 on the Vita to upload.

## 2026-08-30 dev83 visual-correction candidate

Dev82 physical return evidence is preserved, not overwritten. It shows that
the original tutorial reaches interactive M00 with controls, objective start,
corrected NPC skins, and upright doors, but loading is inverted and initial
interactive capture is black with HUD-only content. The current log also
proves retail dialogue data resolves and Bink playback is deliberately skipped
by the existing slow-software safety gate; neither problem is a missing retail
asset.

Dev83 removes only the confirmed extra loading V flip and confines the 4:3
presentation rect to original HUD/text ownership. In dev82, that rect enclosed
the entire `CombatManager::Render()` call, unintentionally changing the
world/camera viewport; dev83 keeps the world at 960x544 and applies 640x480
only around original HUD, fade, message, objective, and text drawing. The
fast ARM/VPK candidate passed 86 focused tests, zero-fuzz 136-patch staging,
identity/archive/SHA checks, and retail exclusion. Its canonical build then
passed 111 tests in `logs/a35-dev83-20260830-161033-build.log`; it is retained
but superseded for deployment by the dev84 Start-exit correction. Do not claim
the user-visible defects fixed yet.

## 2026-08-30 dev82 package admission correction

The prior dev82 canonical VPK (`2d05da8f...`) is retained with a VDB
`VPK_SFO_INVALID` receipt: its generated SFO had an empty `CONTENT_ID`, and
the Vita installer rejected it before it replaced `eboot.bin`. The narrow
package-only correction supplies developer content ID
`EP9000-RNEGA3101_00-RENGADEVITADEV82`. Canonical
`logs/a35-dev82-20260830-153141-build.log` passed host fingerprints, 111
tests, deterministic staging, ARM link/package, identity/archive/SHA checks,
diagnostics, and retail exclusion. The new physical candidate VPK is
`d9a0cc027be2278eb26d4d056dfeec974aff52e4f11f95c5b66fe87e982d3fad`; its
packaged SELF is
`36235779e4fd94886e913a23b4ea203e728612cd90114dc5b2d8fad73145120a`.
It is host-validated only and remains physically unaccepted. The stopped
device's prior SELF (`3e9d4ad5...`) is candidate-scoped backed up before the
authorized install/launch handoff. Runtime artifact pulls remain deferred
until the user reports findings.

The device package command cannot run against the current VitaCompanion command
surface because it lacks `app.query.v1`; its rejected call did not replace the
title executable. The VPK was uploaded to the Renegade user tree and VDB1
hash-verified. Under the title-scoped fallback authorization, the matching
packaged SELF was staged, hash-verified, and used to replace only
`ux0:/app/RNEGA3101/eboot.bin`; VDB1 confirms installed SHA-256
`36235779e4fd94886e913a23b4ea203e728612cd90114dc5b2d8fad73145120a`.
`RNEGA3101` launched and remained running at the 15-second app-status poll.
No input or runtime artifact pull occurred. This proves neither visual nor
mission correctness; user observations and matching returned diagnostics remain
the next physical gate.

Current candidate: **A3.5-dev82 M00 tutorial plus retail frontend/Bink
physical-test build**. It keeps the dev48-dev81
audio/dialogue/texture/material/render-state chain and targets the latest
physical defects by moving direct M00 load completion back through original
`CombatGameModeClass` finalization, rendering loading-screen text/progress,
using one progress stream for loading and prewarm, running a visible startup
pre-cache/pre-warm/pre-compute phase before intro/menu/M00 input with a
five-second minimum display, separate movie-file availability reporting, and
persistent M00/M01 MIX filename cache-index writes,
setting a persistent Vita shader-cache path, presenting the original 640x480
loading layout as an aspect-preserved native `117,0 725x544` rect instead of
stretching it, synchronizing HUD/loading viewports, preserving top-down
retail DDS rows for gameplay textures, tightening HUD/subtitle/sniper
presentation, adding visible reload motion, and applying the requested
controls: Triangle action/use, Square reload, D-pad Left/Right weapon-only
switching, D-pad Up/Down sniper zoom, no shoulder remap, and Render2D viewport
restoration after fullscreen 2D passes. Current source/build also scopes
original HUD/TextDisplay/radar/sniper/bounding-box owners to the authored
640x480 Render2D coordinate space while Vita presents at 960x544, and
invalidates the renderer texture-bind cache after direct DX8/Bink GL texture
uploads to prevent stale texture reuse on character meshes. It also integrates
the external `feature/a35-dev82-retail-frontend` worker and wires a Vita FFmpeg
Bink provider below the original movie owner. Realtime movie playback is
disabled in this physical-test candidate after black-screen/audio-underrun
evidence; the provider resolves/logs the retail movie paths and fails closed
into the original menu instead of stalling before M00. It
has a full canonical build; acceptance still
depends on returned Vita evidence.

Dev82 canonical evidence: `bash ./tools/build.sh` passed on 2026-08-29 in
`logs/a35-dev82-20260829-050854-build.log` with 111 host unittest checks,
deterministic staging, source integration checks, DDS/TGA alias 11/11,
lightweight render-state 13/13, ARM link/package, identity, compressed VPK
validation, diagnostics bundle, SHA manifest, retail exclusion, and retained
Bink symbols/source contracts. The source report records 506 original Westwood
translation units plus one staged original-owner extraction, 26 Vita
platform/renderer/validation/developer files, 6 A4 frontend/Bink boundary
files, 52 compatibility headers, and 135 active deterministic staging patches.
The VPK SHA-256 is
`2d05da8f4868cbaa6a6818c8eecf18026ac655f52ca1ca5b788953dd67d5089b`. The
earlier user-authorized FTP upload predates this visible-startup-precache/
loading-aspect/HUD/texture-cache artifact and must not be treated as the
current VPK. The 2026-08-29 upload probes verified the current hash but found
no reachable VitaShell FTP endpoint. A newer read-only readiness check at
`build/device-evidence/a35-dev82-readiness-20260830-201630/` finds the paired
Vita reachable and idle at `10.0.0.202`; its installed `eboot.bin` is
`3e9d4ad5a7b90a2f4f4e1fed5177e096aa81851b1967fc86eb4517749e831a04`, not the
current dev82 packaged SELF `08a27d1c8b374171afeb1bc1f1bf1f7a1e0c914a56738a84f3ec3c2e784bf11b`.
The pulled dev82 runtime log is stale and the current startup-precache receipt
is absent, so no current-candidate physical acceptance is implied.

Recent evidence chain through dev78: **post-dev77 original user-lighting color source and material
lighting/color-source evaluation in direct Vita mesh submissions, original
Scene/WW3D fog, fill-mode, and
ambient state restoration,
original DX8 render-state/fog bridge,
original ADDSMOOTH detail combiner,
supported texture-stage telemetry,
original ShaderClass alpha-test reference semantics,
indexed dynamic texture-coordinate replay,
generated texture-coordinate evaluation, original material mapper
texture-coordinate state, null texture-stage disable semantics,
Vita stream-output submission telemetry, stream restart handling, per-buffer
stream-mix telemetry, active streamed-audio telemetry, Vita DX8 bound-texture
lifetime,
WWAudio stream loop-count return, streamed-dialogue fact runtime telemetry, WAVE fact-duration metadata,
streamed-dialogue duration metadata, dialogue/audio
diagnostics, texture provenance, DX8
texture surface ownership, DX8
surface-copy compatibility, DDS retained surface levels, direct mesh base-pass
replay, native stage-1 multitexture boundary, and DX8 bound-texture lifetime
for the restage-proven shared
original `LoadingScreenClass` loading path, the dev35 stack fix, dev36 camera-Y
boundary correction, dev37 DataSafe guard, dev38 loading capture metadata,
dev39/dev40 TGA loading fixes, original WWAudio/background/material/conversation
corrections, dev43 no-pullout route gate, dev45 replay-complete clean-exit
bridge, dev46 original message-window render plus dialogue/audio diagnostics,
and dev47 original TranslateDB object-factory closure. Dev48 adds a narrow
WWAudio category-volume fix by initializing dialog/cinematic volume defaults in
the Vita constructor path and logging those volumes in runtime audio
breadcrumbs. Dev49 preserves that fix, adds stream/read/decode/start/mix/output
counters for the Logan dialogue path, and changes the Vita DX8 texture boundary
to try original `DDSFileClass` lookup before loose Targa decode so `.tga`
material names can resolve retail `.dds` assets through the FileFactory/MIX
chain; that original DDS alias path is now covered by an executable host
contract. Dev50 fixes DDS descriptor metadata so original `TextureClass::Init()`
receives DX8 `D3DFORMAT` values instead of raw `WW3DFormat` values, avoiding
the DXT1/RGB888 enum collision; it also pins the documented
`/usr/local/vitasdk` default through `RENEGADE_VITASDK`, tightens vitaGL enum
detection, and extends the audio mixer/source contracts. Dev51 keeps those
source fixes and adds stream-only mix isolation counters inside the Vita Miles
provider: opened streams are tracked separately from ordinary samples, mixed
into a diagnostic accumulator, and reported as streamed buffers, frames, nonzero
buffers, peak sample, and currently active streams. Dev52 keeps those counters
and adds read-only original speech-object diagnostics from the active
conversation path: source owner, speaker presence, sound object presence, scene
membership, cull state, playing state, class/type/state, duration, dropoff
radius, and listener distance. Dev53 keeps those dialogue diagnostics and adds
texture provenance telemetry: successful DDS/TGA load counters, first-load
breadcrumbs with dimensions/format/checksum/native texture id, checkerboard
fallback bind counts, runtime `loaded_dds/tga` breadcrumbs, and capture-bundle
comparison coverage for those fields. Dev54 keeps those diagnostics and
restores the Vita DX8 texture surface boundary: texture-owned refcounted surface
levels, original `GetSurfaceLevel`, texture `LockRect`/`UnlockRect` with
writable mip uploads, priority storage, and width/height `_Create_DX8_Texture`.
Dev55 keeps that ownership and replaces the remaining
`IDirect3DDevice8::CopyRects` invalid-call stub with bounded CPU-backed surface
copies plus texture-owner uploads, and exposes fail-closed
`D3DXLoadSurfaceFromSurface` / `D3DXFilterTexture` compatibility for original
surface/mip call sites. This restores original `Render2DSentence` pending
surface-to-texture copy semantics needed by message, loading, and dialogue text
textures. Dev56 preserves dev55 and gives DDS-loaded retail textures decoded
CPU-backed `D3DFMT_A8R8G8B8` surface levels for every mip while keeping the DX8
source-format descriptor metadata from `DDSFileClass`, so original
`GetSurfaceLevel`/D3DX/`SurfaceClass` callers receive actual decoded retail
pixels instead of blank descriptor surfaces after DDS loads. Dev57 preserves
dev56 and makes the direct Vita `MeshClass` submitter replay every original
base material pass, reading pass-specific stage-0 texture, shader, UV, DCG, and
vertex material data instead of drawing only pass 0. This restores the original
multi-pass fallback shape for lightmap/detail/emissive/shiny-mask material data
that survived W3D load under the current direct mesh boundary. Dev58 preserves
dev57 and removes the stage-1 unsupported renderer gap by translating original
DX8 sampler and texture-stage combiner state for both WW3D texture stages,
binding Vita texture units 0/1, and emitting stage-1 UVs for original
post-detail materials. Dev59 preserves dev58 and fixes streamed dialogue timing
metadata by carrying decoded WAVE sample-frame counts through
`AILSOUNDINFO.samples` and computing original `SoundBufferClass` duration from
frames/rate before falling back to byte-length estimates. Dev60 preserves
dev59 and reads exact WAVE `fact` sample-frame metadata, preferring it over
estimated frame counts and trimming decoded ADPCM output to the exact frame
count before playback. Dev61 preserves dev60 and makes the WAVE
fact/estimate/untrimmed/trimmed frame decision visible in runtime audio stats
and the A3.5 audio log beside the post-trim streamed frame count. Dev62
preserves dev61 and fixes staged original `SoundStreamHandleClass` so
`Get_Sample_Loop_Count()` returns the Miles-compatible provider
`AIL_stream_loop_count` value instead of discarding it and always reporting
zero. Dev63 preserves dev62 and fixes the Vita DX8 bound texture-stage cache
so `IDirect3DDevice8::SetTexture` retains bound textures with `AddRef`/
`Release` semantics instead of storing raw potentially stale backend pointers
during retail material and checkerboard-fallback churn. Dev64 preserves dev63
and adds active-stream cursor/length/loop/volume/pan telemetry while forcing
exhausted finite streams to report zero remaining loops before stop, so Logan
dialogue logs can distinguish active but inaudible streams from stalled or
completed streams. Dev65 preserves dev64 and adds per-buffer stream-mix
telemetry (`last_stream_mix=active/frames/nonzero/peak`) so Logan dialogue
logs can prove whether the most recent active stream buffer is contributing
nonzero samples or silence. Dev66 preserves dev65 and records streamed-audio
buffers that are actually submitted successfully to `sceAudioOutOutput`
(`output_stream=buffers/frames/nonzero/peak` and
`last_output_stream=active/frames/nonzero/peak`), while rewinding exhausted
sample/stream cursors before restart so a restarted Logan dialogue stream cannot
report started and then mix silence at end-of-buffer. A full canonical
no-deploy dev66 build now passes retained host-validation reuse, deterministic
restaging, 72 host unittest checks, source integration reporting, ARM
link/package, identity verification, compressed VPK validation, diagnostics
generation, and SHA verification. The canonical VPK SHA-256 is
`99ad437fc05c9a8bde760df346816a33103875f620a605ba0fa7c9ca7a316543`.
Dev67 preserves dev66 and changes `IDirect3DDevice8::SetTexture(NULL)` to use
the Vita renderer stage-disable path for all stages. That keeps `invalid_bind`
from counting intentional stage-0 fixed-function texture disables, so the next
material/texture hardware log better separates real non-null invalid/unuploaded
texture submissions from normal D3D stage-disable traffic. A full canonical
no-deploy dev67 build now passes retained host-validation reuse, deterministic
restaging, 72 host unittest checks, source integration reporting, ARM
link/package, identity verification, compressed VPK validation, diagnostics
generation, and SHA verification. The canonical VPK SHA-256 is
`3c6279ed13db704e2416b41ff073dace7d772da20d7424541a1846017efb9403`.
Dev68 preserves dev67 and replays original `VertexMaterialClass`
texture-coordinate mapper/default UV-source state in the direct Vita
`MeshClass` path. Base-pass submissions now split when the original vertex
material changes, call the original `TextureMapperClass::Apply()` path when a
mapper exists, restore original default `D3DTSS_TEXCOORDINDEX` /
`D3DTSS_TEXTURETRANSFORMFLAGS` state otherwise, carry texture-stage transforms
through the Vita DX8 boundary texture matrix path, and emit UV arrays selected
by the original material UV source rather than assuming texture stage equals UV
array index. A full canonical no-deploy dev68 build now passes retained
host-validation reuse, deterministic restaging, 73 host unittest checks, source
integration reporting, ARM link/package, identity verification, compressed VPK
validation, diagnostics generation, and SHA verification. The canonical VPK SHA-256 is
`bccfb2e4ef99b5246331b3bb4d6c09e46364c314eedfc19b98c9fe0e236b80d8`.
Dev69 preserves dev68 and evaluates original generated texture-coordinate
states on the CPU for the direct Vita `MeshClass` path. After replaying the
original material mapper state, the renderer reads back
`D3DTSS_TEXCOORDINDEX`, `D3DTSS_TEXTURETRANSFORMFLAGS`, and
`D3DTS_TEXTURE0+n`, generates camera-space normal/position/reflection-vector
coordinates when the original mapper requested them, applies DX8 texture
transforms including projected divide, and resets Vita GL texture matrices for
direct submissions so mapper transforms are not double-applied. A full
canonical no-deploy dev69 build now passes retained host-validation reuse,
deterministic restaging, 74 host unittest checks, source integration reporting,
ARM link/package, identity verification, compressed VPK validation, diagnostics
generation, and SHA verification. The canonical VPK SHA-256 is
`bddc2433707a23682cefecca2c9b63c19b9276e0b612bab65da9a5babc08ed2e`.
Dev70 preserves dev69 and extends that original mapper/generated-coordinate fix
to the indexed/dynamic Vita submit boundary. `Submit_Bound_Triangles` now
replays original `VertexMaterialClass` mapper/default texture-coordinate state
before `Submit_Indexed_Triangles`; the indexed renderer captures original DX8
texture-coordinate state, preserves UV0/UV1 from the legacy dynamic TEX2
layout, selects the original material UV source, and evaluates camera-space
normal/position/reflection-vector generated coordinates plus texture transforms
with the submitted row-vector world/view matrices. A full canonical no-deploy
dev70 build now passes retained host-validation reuse, deterministic restaging,
75 host unittest checks, source integration reporting, ARM link/package,
identity verification, compressed VPK validation, diagnostics generation, and
SHA verification. The canonical VPK SHA-256 is
`3693687d9608734ace67d703e5e9347e37273d09e767a91fb9fc869263b708ec`.
Dev71 preserves dev70 and restores the original `ShaderClass::Apply()`
alpha-test reference semantics at the Vita render-state boundary. The
translated state now carries normal cutouts as `0x60` plus `PASS_GEQUAL` and
inverse-source-alpha cutouts as `0xff - 0x60` plus `PASS_LEQUAL`, replacing
the previous zero-threshold `glAlphaFunc(GL_GREATER, 0.0f)` approximation
without moving shader ownership out of WW3D. A full canonical no-deploy dev71
build now passes retained host-validation reuse, current lightweight
render-state contract 5/5, DDS/TGA alias contract 11/11, deterministic
restaging, 76 host unittest checks, source integration reporting, ARM
link/package, identity verification, compressed VPK validation, diagnostics
generation, and SHA verification. The canonical VPK SHA-256 is
`79db5808b4a5e03f1ab5ac0977970ca992ca5fdbc313167072005b7890c89c14`.
Dev72 preserves dev71 and tightens Vita texture-stage unsupported telemetry so
supported retail stage-1 material traffic no longer increments
`unsupported_stages`; only stages outside the original two-stage material
contract or beyond the emulated device limit are recorded. A full canonical
no-deploy dev72 build now passes retained host-validation reuse, current
lightweight render-state contract 5/5, DDS/TGA alias contract 11/11,
deterministic restaging, 77 host unittest checks, source integration reporting,
ARM link/package, identity verification, compressed VPK validation, diagnostics
generation, and SHA verification. The canonical VPK SHA-256 is
`aec6c8ee0f16743133dff2f4f762470cf66f3c1c0b6deae087e270d76c7315c8`.
Dev73 preserves dev72 and translates original `D3DTOP_ADDSMOOTH` inverse-scale
detail color/alpha through a Vita fixed-function GL interpolate combiner with a
white texture-env constant instead of plain `GL_ADD`, matching the original
`local + (1-local)*other` material behavior without moving shader ownership out
of WW3D. A full canonical no-deploy dev73 build now passes retained
host-validation reuse, current lightweight render-state contract 5/5, DDS/TGA
alias contract 11/11, deterministic restaging, 78 host unittest checks, source
integration reporting, ARM link/package, identity verification, compressed VPK
validation, diagnostics generation, and SHA verification. The canonical VPK
SHA-256 is
`251d9335c97056f15f69398a2bfd7c4ef9a9ec9242dab55719896d39acf67c32`.
Dev74 preserves dev73 and replaces the remaining Vita
`IDirect3DDevice8::SetRenderState()` no-op boundary with a source-backed
renderer bridge. Original `DX8Wrapper::Set_DX8_Render_State()`,
`DX8Wrapper::Set_Fog()`, and `ShaderClass::Apply()` now drive Vita fog
enable/color/start/end, alpha test/reference/compare, alpha blend
source/destination, depth compare/write, cull mode, and fill mode. The Vita
caps now allow original fog only after the backend applies it. A full canonical
no-deploy dev74 build now passes retained host-validation reuse, current
lightweight render-state contract 11/11, DDS/TGA alias contract 11/11,
deterministic restaging, 79 host unittest checks, source integration reporting,
ARM link/package, identity verification, compressed VPK validation,
diagnostics generation, and SHA verification. The canonical VPK SHA-256 is
`c65767ce6b35c693e7d3abbb0b5bf4764ab89dd2bc8e313b1b143c591f4d07ee`.
Dev75 preserves dev74 and removes the remaining Vita early-return from the
original `WW3D::Render(SceneClass*)` path. Vita now follows the original
camera apply, polygon fill-mode state, scene ambient state, scene render, and
flush sequence while excluding only desktop-only clear and mesh-renderer camera
calls. Staged `SceneClass::Render` again calls original
`DX8Wrapper::Set_Fog(FogEnabled, FogColor, FogStart, FogEnd)` on Vita, and
`D3DRS_AMBIENT` now reaches the Vita backend through
`glLightModelfv(GL_LIGHT_MODEL_AMBIENT, ...)` with a first-state breadcrumb.
A full canonical no-deploy dev75 build now passes retained host-validation
reuse, current lightweight render-state contract 13/13, DDS/TGA alias contract
11/11, deterministic restaging, 80 host unittest checks, source integration
reporting, ARM link/package, identity verification, compressed VPK validation,
diagnostics generation, and SHA verification. The canonical VPK SHA-256 is
`3d324ae1887860b57c190abe6528bcb5335ca3aa0efec55b79fc719c73b70e45`.
Dev76 preserves dev75 and replaces the direct Vita mesh path's simplified
material color shortcut with original `VertexMaterialClass` diffuse, ambient,
emissive, opacity, lighting, color-source, and `LightEnvironmentClass`
evaluation. Pass-specific DCG data is now used as the original color1/color2
source fallback, and the runtime logs the first evaluated material-lighting
breadcrumb for M00 hardware review. A full canonical no-deploy dev76 build now
passes retained host-validation reuse, current lightweight render-state
contract 13/13, DDS/TGA alias contract 11/11, deterministic restaging, 81 host
unittest checks, source integration reporting, ARM link/package, identity
verification, compressed VPK validation, diagnostics generation, and SHA
verification. The canonical VPK SHA-256 is
`371ed075af325d8909a96b492411f9cbef93d5f6698e627f1aa8b1a2d14c9c38`.
Dev77 preserves dev76 and restores the original rigid direct-mesh color1
precedence from `DX8FVFCategoryContainer` / `Vertex_Split_Table`: non-skinned
`MeshClass` submissions now prefer `MeshClass::Get_User_Lighting_Array(false)`
before model color array 0 and pass-specific DCG fallback, while skinned meshes
remain on the model color-array path. The runtime logs
`first original user lighting color source` for physical M00 material review.
A full canonical no-deploy dev77 build now passes retained host-validation
reuse, current lightweight render-state contract 13/13, DDS/TGA alias contract
11/11, deterministic restaging, 82 host unittest checks, source integration
reporting, ARM link/package, identity verification, compressed VPK validation,
diagnostics generation, and SHA verification. The canonical VPK SHA-256 is
`0528357e6b4d47d7c1d8e49fef22faaf6e0bd9980c75403dd43c331cd5bf1252`.
Dev78 preserves dev77 and removes the remaining non-original near-black
textured static material fallback from the direct Vita mesh backend. Textured
rigid meshes now submit the original evaluated material/user-lighting color
directly instead of replacing black results with ambient, emissive, or white,
matching the original WW3D `Set_Material`/`Set_Shader`/vertex-color authority
and leaving bad lighting/material state visible in breadcrumbs for hardware
review. A full canonical no-deploy dev78 build now passes retained
host-validation reuse, current lightweight render-state contract 13/13,
DDS/TGA alias contract 11/11, deterministic restaging, 82 host unittest checks,
source integration reporting, ARM link/package, identity verification,
compressed VPK validation, diagnostics generation, and SHA verification. The
canonical VPK SHA-256 is
`c0779b68172d13f6ff057c010697d9b65af210719a2e827de4acbfde61ebbb27`.
Dev46 physical replay used
the retained dev43 route, returned PASS and LiveArea cleanly, and proved SFX
audio works, but all active M00 tutorial dialogue lookups returned missing
strings and sound ids (`str=0`, `sound=-1`). Dev47 fixed those lookups
(`str=1`, valid sound ids) by linking `wwtranslatedb/translateobj.cpp` and
`wwtranslatedb/stringtwiddler.cpp`, but its physical replay failed: no audible
dialogue was heard and the old route diverged/stuck because dialogue timing/
control changed. Dev78 is built but not deployed; dev46 remains restored on
device. Text-dialogue/audio acceptance, texture/material acceptance,
fog/material-state acceptance, and a valid post-dialogue route remain pending
physical evidence**.
Exact-dev6 pause passed on physical Vita.
Exact-dev7 physically proved grounding, movement, Square delivery, and an
isolated original weapon-fire path, while exposing a nondeterministic external
input-provider sequence and invisible skinned bodies. The v3.6 host
resource/memory work remains subordinate to the current visual-correctness
gate. A3.2-dev1 remains frozen failed evidence, A3.5-dev4 is invalid identity
evidence, and neither is the active candidate. Dev13 completed one matching
physical record but failed sky/material/audio/Logan-progression acceptance;
its route is retained and exact dev7 is restored. Dev15 proved provider/link
closure but left the Vita runtime in lite, uninitialized, unserviced audio mode.
Dev16 corrected that lifecycle. Dev19 physically proved Logan-to-pistol
progression but crashed after six pistol shots. Dev43 supersedes that
progression point for route/runtime only: 5,958 recorded samples, clean
lifecycle, no new PSP2DMP, `Weapon_Pistol_Player`, `fired_total=36`, unchanged
retail M00, and route SHA-256
`5ef2ee8f2ed5d4f301ec20ef95c73fe7aea9956a32e9cc41aecf84999191e895` under
`build/device-evidence/a3.5-dev43-route-record-20260825-022835/`. Dev45
replays that route to automatic clean exit under
`build/device-evidence/a3.5-dev45-route-replay-20260825-025927/`. Dev20 through dev24 are failed
or superseded loading/replay attempts; dev24 physically proved the direct
VitaGL loading shortcut still looked wrong despite tile residency. Dev25
removed that shortcut and restored original `MenuBackDropClass` model-animation
ownership. Dev26 completed the original loading text, string, style, and status
lifecycle: `STRINGS.TDB`, `StyleMgrClass`, `Render2DSentence`,
`SaveLoadStatus`, and Campaign backdrop description parsing. Dev27 restored
original `CombatManager::Set_Load_Progress(0)` /
`CombatManager::Get_Load_Progress()` ownership and removed manual terminal
progress fractions. Dev28 supersedes it by restoring original
`loading_screen.Render(true)` behavior: loading presentation passes
`cNetwork::Update` through `WW3D::Begin_Render` instead of rendering as a
network-idle frame. Dev29 supersedes dev28 by scoping `Render2DClass` to the
original 640x480 loading logical resolution for `MenuBackDropClass` and
`Render2DSentenceClass` layout, then restoring Vita 960x544 before gameplay.
Dev30 supersedes dev29 by scoping WW3D/DX8Wrapper/Render2D together during
loading, so original `Render2DClass::Render()` and `CameraClass::Apply()` use
the same 640x480 logical viewport, while the Vita renderer scales that viewport
to the full 960x544 framebuffer. Dev31 supersedes dev30 by removing the
Vita-side loading-presenter clone and linking a shared original
`LoadingScreenClass` owner in `staging/commando/loadingscreen.cpp`; direct Vita
now constructs/renders/destroys that original owner through a narrow bridge,
so the same implementation can be reused for other original loading states.
Dev32 supersedes dev31 by making that extraction deterministic under
`tools/stage_sources.sh` through `commando-a35-shared-loadingscreen-owner.patch`
and proving it with a forced-restage fast package. Dev33 supersedes dev32 by
leaving gameplay/world UV semantics unchanged while flipping V only for original
loading-screen texture basenames beginning with `loadscreen_`, covering the
original loading W3D/DDS orientation mismatch. Dev34 superseded dev33 by
retaining that path and writing a returned loading-screen BMP/state capture at
original `level_ready`; the route runner required that capture before accepting
the user's fresh movement recording. Dev34 was deployed once for an approved
route-record attempt and crashed before the first original-runtime log; VDB
PSP2 analyzer maps the dump to `A31_Vita_Run_Interactive_Runtime()` line 605,
the function prologue, and objdump showed a roughly 276 KB stack subtraction
from stack-local `A31FrameHistory` diagnostics. Dev35 supersedes dev34 by
moving that history storage off the Vita stack, reusing one heap history for
loading/gameplay capture, and reducing the prologue stack subtraction to about
17 KB. Dev36 supersedes dev35 by changing only the Vita right-stick Y
mouse-delta default after the latest physical camera-inversion feedback, while
leaving original Input and CCamera ownership unchanged. Dev37 supersedes dev36
by fail-closing invalid `GenericDataSafeClass` list indexes in release builds:
VDB symbolicated the retained dev19 pistol-shot PSP2 dump to
`GenericDataSafeClass::Get_Entry` at `datasafe.cpp:350`, where compiled-out
`ds_assert` checks allowed `Safe[list]` to be dereferenced. Dev38 supersedes
dev37 by making the returned loading capture auditable with schema-v4 visual
gate metadata. Dev39 supersedes dev38 by proving the original retail loading
W3D uses `.tga` tiles (`loadscreen_beam.tga`, `loadscreen_cnc_1..4.tga`) and
routing those requests through the existing TGA decoder at the Vita DX8
boundary. Dev40 supersedes dev39 by matching original TextureLoader TGA
Y-origin handling and removing the loadscreen-only UV workaround from mesh and
indexed submissions. Dev46 restores the original message-window render pass
and adds audio/dialogue diagnostics; its physical replay is the current
no-dialogue diagnostic evidence. Dev47 links the missing original TranslateDB
object factories and physically proves string/sound-id lookup, but fails
audible dialogue and route fidelity. The next hardware gate requires a new
source fix and either dialogue-aware replay synchronization or a fresh route;
do not claim audible dialogue until physical output and provider counters
support it.

Recent host diagnostics cover post-run evidence, resource-manifest deltas,
cache consistency, warning trends, and PSP2 parser fixtures. Their focused
tests and repeatability checks pass; they remain host tooling and do not read,
convert, package, or publish retail payloads. The PSP2 parser does not infer
private Sony register fields.

A3.1.4 is frozen as the first physically accepted visible original interactive
M00 baseline: geometry, original player/session/camera path, 1,226 stable
frames, and clean START exit physically passed. It remains untextured and its
right-stick input was delivered at approximately 32 times the original logical
range. See `A3.1.4-HARDWARE-CANDIDATE.md` and `../../baselines/A3.1.4/`.

`RenegadeVita-A3.2-dev1.vpk` is frozen as a failed physical-hardware checkpoint
(SHA-256 `d5b1df3a06139bc4522a4b5faba3893bd29cd4a985e98919e210d2bf507e4627`).
The returned dump and exact matching symbols establish a release-blocking
`HumanStateClass::Update_Animation` fault; physical observation also reported
stuck fire/crouch, reversed axes, perspective warp, muzzle transparency error,
and non-clean exit. Its evidence remains immutable and must not be overwritten.

### A3.5-dev5 — visible physical M00 and movement pass; acceptance incomplete

The fresh canonical build passed the complete host gate, deterministic
restaging, focused observer contract (46/46), input normalization (22/22),
capture/evidence contract (24/24), renderer state (4/4), renderer lifecycle
(11/11), ASan, LeakSanitizer, and targeted UBSan routes. The final ARM closure
contains 424 original and 21 port translation units and completed 456 Ninja
build actions. A mandatory post-link verifier passed all 15 identity and
lineage checks against the exact final ELF, SELF, and VPK: the intended dev5
display/capture/log identities are present, all prohibited dev1/A3.1 strings
are absent, and packaged `eboot.bin` is byte-identical to the verified SELF.
The current recursive-trace build is `20260824-004956`: ELF SHA-256
`b8f0c6c6be2b9aba79000050ea2301e3700eafd7afc4e5cb174976c516e6d4c3`,
SELF SHA-256
`ec08e891087243a6a44da8db29ef80bf9c485d31a6ef1b0f27423ea9626b59b1`,
and VPK SHA-256
`0316009326b5c043edbb80f87f70792f02e9f597382f2cf0370fcc7bc675a5e6`.
Its Vita-only trace is paired with the byte-identical retained completed host
validation log; it does not claim a fresh host execution for the trace-only
change.

Physical Vita now proves that all 495 static objects load, the original loader
returns, the original player/session/camera reaches visible textured M00, and
movement/look input changes the player position. An untouched late capture at
frame 355 is visually coherent; a separate interaction run reached frame 1,321
with zero rejected submissions and zero renderer backend errors. This is not an
A3.5 milestone acceptance claim: jump/action effects, collision/grounding, and
pause remain unaccepted. Clean exit and restart/repeat now pass. Door/NPC
interaction, HUD, audio, device-memory work, and repeated-session soak remain
later milestone gates.

### A3.5-dev6 — original Combat pause physical pass

Triangle now enters the existing `INPUT_FUNCTION_MENU_TOGGLE` path and toggles
original `GameModeClass::Suspend/Resume`; START remains the proven clean-exit
control. While suspended, the direct M00 boundary continues time, input, and
local-network service, skips original Combat simulation, and preserves the last
original frame because the desktop pause-menu presenter is not linked.

Focused normal and ASan compilation passed for the changed sources, as did the
6/6 static pause contract. Canonical build `20260824-013626` completed all 456
ARM actions and passed 15/15 identity checks. ELF, SELF, and VPK SHA-256 are
`2b820d533815a135db020804b287affe6521ecc68ff8dc0602e9c7e74c4473a2`,
`293768e9d79769b9872e1ad9d472c66305310032c74727d6e08a1a444ad52360`,
and `929bdbcfbf10292f250c799faf74b254384482ddc1e8cb43d6d2b21e7f573bae`.
The VPK contains only eboot and SFO. The build reused the exact completed dev5
host log because no local retail tree was available; retail was not copied.
Matching physical evidence proves one original Combat suspend/resume pair,
stable player position across 316 paused input frames, resumed movement, zero
renderer errors, clean teardown, and stopped app state. This raises the
physical evidence gate count to 8/10 without claiming visual correctness.

### A3.5-dev7 — physical effects observation and provider isolation

The separate observation-only candidate samples the original player identity,
state, transform, velocity, health, physical-object registration and
`HumanPhysClass::Is_In_Contact`, plus original `WeaponClass` rounds/fire state
and `ActionClass` activity. It does not mutate player, physics, weapon, action,
mission, renderer, or asset state. The existing schema-3 capture comparator now
reports these gameplay fields independently.

Focused comparator, runtime-contract, hygiene, normal capture, ASan capture,
and ARM syntax checks pass. Canonical build `20260824-020540` completed all 456
ARM actions and passed 15/15 identity checks. ELF, SELF, and VPK SHA-256 are
`6063c5eb2c5136ee4376fe6dc0b3944c54ce728ff7b59af76b90ffdaf6e62e21`,
`7367b04a3fd19121e5360a0bfc8dd088d377c1063f060811a282056bbefeefd5`,
and `234139c2411fed7be8f2003a15ba015bc2270608ef8e3ec5406308e5c3c1443e`.
The VPK contains only eboot and SFO. Four matching physical sessions proved
original physics registration, ground contact, movement, Square delivery,
clean teardown, and stopped app state, but the external combined route did not
deliver R in those same sessions. A separate exact-dev7 probe delivered raw R
and fired 17 original weapon rounds, isolating the remaining failure to the
external injection sequence rather than the VitaSDK/DirectInput/WeaponClass
path. User observation also found missing Havoc forearm/hand geometry and NPC
bodies while rigid attachments remained visible. Those visual defects are not
a retail-data absence signal; they share the Vita skinned-mesh submission seam.

### A3.5-dev12 — deformed skins physically pass; sky fails

The Vita backend now follows the original DX8 skin container semantics:
`MeshClass::Get_Deformed_Vertices` obtains HTree-owned animated positions and
normals, and skinned vertices submit with identity world transform. Rigid mesh
submission remains unchanged. Bounded runtime counters distinguish skin
submissions, deformed vertices, and allocation/deformation failures.

The existing DirectInput platform boundary can record or replay one version-1
raw-controller route selected by exact one-shot marker files. The route is
capped at 18,000 eight-byte samples, FNV-1a checksummed, committed through a
temporary file and rename, and replay retains live physical START as an
emergency abort. Original Input/Combat bindings and update ownership remain
unchanged. VDB input control remains available for lifecycle/input release;
recorded replay removes dependence on nondeterministic external sequencing.

Canonical build `20260824-083354` completed all 465 ARM actions and passed
identity, ELF/SELF/VPK, retail-exclusion, archive, and diagnostics-manifest
checks. ELF/SELF/VPK SHA-256 are
`cbf956dbd001ef13dd94da465ef756d69f882bcfb8b25d621045065f905dd1d0`,
`805b853e737c884acc9f590a3c5793f9ba6f32f5ff80542454919bf1d2750b99`,
and `86f08c02dab2829e9ef7e25c12983313c1eb3664d2d9a3aeebaf962ff037e284`.
The VPK contains only eboot and SFO. Post-build tool discovery passes 74/74;
the ARM symbols contain both `MeshClass::Get_Deformed_Vertices` and the Vita
skin submission/scratch path. Physical observation confirms ordinary NPC body
skins now render with zero deformation failures. The same run begins in the
authentic unarmed tutorial state and reports a black sky, so dev12 is not a
fully accepted candidate and exact dev7 was restored afterward.

### A3.5-dev13 — physical route recorded; visual/progression failure

Original Haze, Starfield, CloudLayer, sun, and moon retain their existing
dynamic indexed geometry ownership. The Vita DX8 boundary now consumes the
deferred original `ShaderClass` and stage-0 `TextureClass` immediately before
indexed submission and records bounded indexed-state applications. It does not
add a custom sky, scene graph, shader, or asset format.

Clean staging also closes the official Scripts parameter-array `new[]`/`delete`
lifetime, drains scripts queued by original object detach when teardown's
`Post_Think` is disabled, and prevents headless validation from allocating HUD
presentation icons without HUD resources. Fresh strict LeakSanitizer and
targeted UBSan complete two authentic M00 cycles, plus retained M01 and City
smokes. Canonical build `20260824-093614` completed all 465 ARM actions and all
identity, ELF/SELF/VPK, retail-exclusion, archive, and diagnostics checks.
ELF/SELF/VPK SHA-256 are
`d3b7d69e40f1968a9beda0b46312c0609d73522b8ce30799cecb169a352d8b1b`,
`5c254b8a914a603baca2c9b343bb075df58c7d05ed05448db267f2d599a14555`,
and `7f7e31b37afff79ea1ab662cd9afc5d0e366f9252be6dd236b2ac8fabdf5d63d`.
Post-build tool discovery passes 81/81. The VPK contains only eboot and SFO.
Physical record evidence under
`build/device-evidence/a3.5-dev13-route-record-20260824-144843` contains a
committed 4,537-sample route (SHA-256
`39d915e02611079b29fb43cb2ea11ede583b063745e9675efe15010c606b7cf8`),
4,507 frames, clean START exit, 37,606 skin submissions, 7,207,630 deformed
vertices, and zero skin/backend errors. The user observed wrong NPC materials,
no audio, a black sky, and a Logan cutscene after the ladder that remained
active with control disabled and did not reach the pistol grant. Indexed
submissions and state applications were exactly zero. Capture frame 4,209
corroborates the black sky and wrong material appearance. Retail M00 remained
unchanged; exact dev7 was restored and verified.

### A3.5-dev14 — original background/material correction; hardware candidate

Source tracing found two concrete platform-boundary defects. The Vita runtime
passed `false` to original `CombatManager::Pre_Load_Level`, so
`BackgroundMgrClass::Init` never constructed its original Sky/Dazzle objects;
the indexed bridge therefore could not execute. The runtime now declares world
rendering available while retaining the separate HUD-resource gate. The absent
Vita DazzleLayer is a bounded no-op, not a rejected world draw.

The Vita mesh bridge also invented RGB from vertex normals. It now consumes the
original pass-0 DCG color, or the original `VertexMaterialClass` diffuse and
opacity when DCG is absent. Original TextureClass, HTree, mesh, shader, scene,
and animation owners remain intact. Bounded first-skin telemetry records mesh,
texture, UV/DCG, and pass presence without asset payloads.

Read-only diagnostics expose the first active original conversation's name,
ID, state, action, current/total remark, and remaining remark duration. They do
not call `Stop_Conversation`, grant a weapon, or advance Mission00. The route
runner now prints the user play instruction before launch; the later status is
explicitly telemetry-ready because the former human prompt arrived after the
game was already interactive.

Deterministic 111-patch staging, focused contracts, complete 87-test discovery,
and the affected 504-action host link pass. The fresh Vita build completed all
465 ARM actions and passed ELF/SELF/VPK identity, compressed-package, manifest,
symbol, and retail-exclusion gates. Exact ELF/SELF/VPK SHA-256 values are
`0cc4b9f68967cfaef29d3927ebfd1c6791924b5c442e03f0a7c7fd5c738de8e0`,
`eda78f4f3dd57a064cb915af9cab677e3e64fc340c16ad09f0c74e6839ca6860`,
and `6528991ca58877cb159a5c57b396c84e0a29c55ffa74487e5bb22f9af3e7e0e4`.
The VPK contains only `eboot.bin` and `sce_sys/param.sfo`; no Vita filesystem
was accessed. Because the local retail link was unavailable, the package
explicitly reused dev13's matching complete sanitizer/runtime log while
freshly rebuilding the affected host and ARM targets; it does not claim a
fresh retail sanitizer execution.

The TT 4.8.4 revision-9000 reference audit is integrated; portable TT
correctness semantics were already/equivalently present in EA source, while
campaign/audio/controller/lighting engine changes remain study-only because
their public implementations are absent or platform-specific. The historical
dev14 route runner admitted the exact dev14 SELF and exact installed dev7
fallback. Dev14 was not physically replayed and is superseded below.

### A3.5-dev15 — original WWAudio/Vita-native provider linkage; superseded

The source/link closure expanded without moving game ownership into platform
code. Fifteen additional original WWAudio TUs retain definitions,
buffers, sound/scene/listener objects, callbacks, playlists, priorities,
looping, transforms, and timing. Together with the previously selected logical
audio units and AudioSaveLoad, the source report records all 20 WWAudio TUs.

The local Miles-compatible boundary provides bounded RIFF PCM8/16, Microsoft
IMA ADPCM, and Microsoft ADPCM decode; 48 kHz stereo rate conversion/mixing;
pan, volume, loop, playback rate, encoded-byte 3D seek/timing, and linear
distance attenuation; original file callbacks; and blocking Vita
`sceAudioOutOutput`. This is independently implemented platform code, not a
TT or Windows Miles import. Whole-track stream decode is capped at 64 MiB and
remains subject to v3.6 incremental-streaming and physical memory measurement.

Fresh focused tests cover PCM8/16, mono/stereo IMA, mono/stereo Microsoft
ADPCM, bounded/truncated inspection, encoded-byte timing, manual mixing, pan,
and distance. ASan/UBSan and standalone Vita ARM `-Werror` checks pass. Full
post-restage discovery passes 89/89.

The canonical run completed deterministic 113-patch staging and all 482
ARM/packaging actions. Identity 15/15, required original-WWAudio/provider
symbols, ELF/SELF/VPK, compressed-package, manifest, diagnostics, and retail-
exclusion gates pass. Source integration records 447 unique original and 26
native boundary TUs. Exact ELF/SELF/VPK SHA-256 values are
`db96d327219e77d4df99d0a2942a635eda1872b311aa0c6dceb2b2a42d2eb0c9`,
`c4d5aaa1c04d93329617a086a7f57a423ff50ad40ee510f92a37ae9f8f9bfc1f`,
and `e2036901c8edceaaee73a0bfb6d94f620476c794ab8dc94207feeb00b8ca17d3`.
The VPK contains only eboot and SFO; no Vita filesystem was accessed.

Because the local retail link is unavailable, the unchanged full M00 sanitizer
route explicitly reuses the matching retained log SHA-256
`97fc49202c76a04710964cf3939dd128329df88acc6b3005241632b69df5ec1e`.
That is not a fresh retail sanitizer claim. The changed provider has the fresh
focused/sanitizer/ARM evidence above. Source review after packaging found that
the Vita entry point still constructed `WWAudioClass(true)`, did not call
`Initialize()`, and never called `On_Frame_Update`; dev15 was never deployed and
cannot support an audible-runtime claim. Its former route admission is retired.

### A3.5-dev16 — original WWAudio lifecycle activation; hardware candidate

Dev16 makes the smallest original-lifecycle correction at the Vita boundary.
After the direct runtime installs the rooted retail/MIX chain, it creates the
original basename-stripping audio adapter, constructs `WWAudioClass(false)`,
calls `Initialize()` before engine/world setup, and refuses entry unless the
original sound scene and Vita-backed 2D/3D drivers exist. The frame loop services
`WWAudioClass::On_Frame_Update(0)` after each active render, matching original
Commando ordering, and during the intentionally suspended Combat branch. Audio
is destroyed after Combat/session/input teardown and before asset, WW3D, WWPhys,
and factory teardown. This does not move conversation timing or mission
progression into platform code.

The pinned TT 4.8.4 r9000 audit passes 5/5 portable-pattern checks, but its
607-file public scripts archive and nine-file update delta contain no WWAudio
constructor, frame-update, main-loop, or conversation implementation. No TT
implementation is interpolated; the correction restores semantics from the
authoritative EA sources. `ActiveConversationClass` still owns remark timing,
so the missing audio lifecycle is not represented as the proven cause of the
Logan hang.

The final canonical build used the retail tree at
`/mnt/d/SteamLibrary/steamapps/common/Command & Conquer Renegade` and freshly
passed M00/M01/City two-cycle host routes, ASan, LeakSanitizer, targeted UBSan,
the canonical 42-test selection, deterministic 113-patch staging, all 482
ARM/package actions, and identity 15/15. Post-build full discovery passes
90/90. The host log SHA-256 is
`d5503bf47ea37f184b268e18a3ec89101177fbbf8705538240ba033cabeda3fd`.
Source integration records 447 unique original TUs, all 20 WWAudio TUs, and 26
native boundary TUs. Exact ELF/SELF/VPK SHA-256 values are
`684f15da87bb8e2d3fcdc45d7646132cb8f0ac65ec2612c0010d0365d10b8dea`,
`4dd1f7fd4a10ee26605986c58c1aad9e63986fbbf5c91e48326c9d4a0c81169f`,
and `fa7903ba94442c7f18b554dd986d868bd90fe4dedfbcbcfc732b9f506e741a63`.
The VPK contains only `eboot.bin` and `sce_sys/param.sfo`; no Vita filesystem
was accessed.

The route runner now admits only exact dev16 SELF or exact installed dev7
fallback and retains the 4,537-sample route plus live START abort. Physical
audio, sky/material appearance, Havoc first-person meshes, original Logan
progression, clean lifecycle, and matching visual evidence remain required.

### A3.5-dev8 — native Mission00 script provider; physical pending

The original Combat `ScriptManager` now uses a native static provider composed
of the official `ScriptCommands`, `ScriptFactory`, `ScriptRegistrar`,
`ScriptImp`, and `Mission00` sources. This preserves original script
registration and attachment ownership without a Windows DLL loader or a
replacement mission system. The selected closure is 430 unique original plus
22 port translation units; only the script ABI translation units receive the
scoped compatibility compilation mode. Provenance remains the existing
pristine EA repository at revision
`3e00c3a1b97381bb28be89a35b856375e0629a08`, licensed under GPL v3 with the
repository's additional terms; no external source tree or retail asset was
imported.

The provider contract passes 4/4, the current core-tool suite passes 52/52,
diagnostics pass 29/29, deterministic zero-fuzz staging is clean, and upstream
is pristine. Canonical build `20260824-031918` completed all 463 ARM actions
and passed 15/15 identity checks. ELF, SELF, and VPK SHA-256 are
`3d4b1f56e82782d1958c9a82dd5f9f773ebd3f8046652caae4c8ecd01d9b4b21`,
`7d944a8f0fe0425007cbb22b3ea039f8c173b64c4f8f6c4dce71a5670ee02c20`,
and `86b00a0d4a07a2fde9bd1734934e9bb31bdae848a2d84da551545281ad8219ac`.
Required original create/registrar/M00 controller symbols are present. The VPK
contains only eboot and SFO; no retail data or device write occurred.

This is host/ARM/package evidence only. On hardware, dev8 must report its
provider active, a nonzero registered-script count, a nonzero attached-script
count, and `scripts_active=true`, then complete the bounded walk/look/jump/
fire/Square-action and clean-exit route. It may run only after exact dev6 and
dev7 PASS receipts. The approximately 30-second normal load is covered by a
45-second readiness timeout.

### v3.6 — bounded host foundation in progress

The new deterministic read-only asset manifest validates the local user-owned
Data tree (51 files, required archives present, no case conflicts), and cache
key v1 deterministically binds content identity, tool/schema version, and
conversion options without converting or packaging retail data. The original
`M01.mix` path is preflighted by `MixFileFactoryClass` and then exercised by
two 120-frame original `CombatManager::Load_Level_Threaded` load/render/
teardown cycles on host. Capture schema v2 adds bounded periodic free-memory
low-water telemetry; host self-test 17/17, comparison tests 2/2, and ARM link
pass. The host-only v1 archive-index precursor also uses the original factory:
M01's 231 names are byte-identical across two writes and City has 83 names.
These are host/ARM facts only; device scene, cache, memory, storage, and
performance acceptance remain open. The complete canonical revalidation log
is `../../logs/a30-20260816-114055-host-runtime.log`: retained M00
normal/ASan/LeakSanitizer/targeted-UBSan cycles, M01 two-cycle original Combat
load/render/teardown, and City two-cycle original Combat smoke all passed. The
runner explicitly calls the cache scripts through `python3`; real M01 cache
metadata verifies valid against its manifest/options key. This adds no native
cache consumer or physical claim.

The runtime now has a bounded optional cache-index health check in the existing
`cache/` namespace. It verifies the generated M01 index schema, archive,
count, ordering, and absence of trailing data, while missing/corrupt/unsafe
indexes remain diagnostic-only and always fall back to the unchanged original
MIX factory route. The 9/9 host contract and an ARM EABI5 link passed; the
complete follow-up host gate is
`../../logs/a30-20260816-115428-host-runtime.log`. This is neither device
cache consumption nor a hardware result.

Post-freeze revalidation (2026-08-16): the complete 17-file A3.2-dev1
SHA-256 manifest and VPK archive test remain exact. The current 495-source
host closure again completed its two retail M00 cycles under AddressSanitizer,
LeakSanitizer, and targeted UBSan: each retained original campaign catalog,
Main Menu lifecycle, `GameInitMgrClass::Initialize_SP`, session/player/camera
ownership, 205/12,426/8,661 first-frame mesh/vertex/triangle telemetry, zero
rejected/unsupported submissions, and clean teardown. This is regression
evidence only; the frozen A3.2-dev1 package, its hash, and its physical gate
are unchanged.

After freezing A3.2-dev1, the direct original M00 route was brought into the
same level/session teardown order used by `CombatGameModeClass` and
`GameInitMgrClass`: `cGod::Exit`, `CombatManager::Unload_Level`, session
flush, client/server cleanup, player/team removal, and pending-network-object
drain. A missing `Return_File` in original `cNetwork::Get_Data_Files_CRC` is
now an explicit staged patch, and the no-output WWAudio boundary implements
the original cache-clear state transition required by level unload. The
HUD-enabled normal, ASan/LeakSanitizer, and UBSan two-cycle M00 runs all pass;
LeakSanitizer now reports no leaks. The un-packaged ARM A4 closure now links
after 495 build actions with SHA-256
`19925dc85bde73f645100ca61883e84442bf1f86094f18c84b143b928cd6ed9a`.
`tools/run_a30_host.sh` now repeats this path with LeakSanitizer enabled as a
canonical regression gate; its freshly rebuilt 495-action ASan target passed
the two-cycle M00 run without a sanitizer report.
The candidate's complete 17-file SHA-256 manifest and VPK integrity were
rechecked afterward and remain exact. The known VitaSDK 2-byte/4-byte
`wchar_t` linker warning remains identical to accepted A3.2-dev1; no new ABI
claim is made from this host/ARM closure.

The final canonical host gate is recorded in
`<managed-log-root>/a30-20260816-073250-host-runtime.log`.
It passes the retained A2.2 checks (19/19 bitpack, 10/10 filesystem/MIX, and
14/14 W3D), A3.0 45/45 world runtime, capture 15/15, Vita input 20/20, and
texture upload 4/4 contracts, followed by normal, ASan, LeakSanitizer, and
targeted UBSan two-cycle M00 runs. Fresh staging had exposed stale host target
link closures for original AssetManager/WW3D Font3D/Render2D symbols; those
targets now explicitly link the existing original Font3D/Render2D/Targa owners
and existing Vita surface/FreeType boundary. This changes host validation only,
not the frozen candidate.

A4 host closure restored the original Font3D/Targa/Surface/Texture path,
CombatGameMode-owned RadarManager ordering, renderer preset initialization,
and the 44-byte original Render2D dynamic vertex layout. A HUD-enabled ASan
two-cycle M00 run passed 120 frames per cycle with zero rejected/unsupported
submissions. GDB then isolated an LP64 host-only retail observer-token read:
`ScriptableGameObj::Load` read eight bytes from a four-byte serialized pointer.
The host reader now uses the existing token-width helper while the Vita ILP32
branch retains the original four-byte read. Optimized and ASan host two-cycle
runs pass. The font-provider boundary now reads the original `54251___.TTF`
(Regatta) and `ARI_____.TTF` (Arial) through the original file factory, caches
FreeType faces, and returns original `FontCharsClass` alpha-4444 glyph data.
Two optimized and two ASan memory-safety cycles rasterized both families;
Regatta produced 7x19/67-covered-pixel and Arial 12x18/60-covered-pixel
glyphs. The original `StyleMgrClass::Initialize_From_INI` now
passes twice against retail `stylemgr.ini`: the original menu and in-game font
slots are populated through the provider, not Win32 font registration. Its
UTF-16 wrapped-text byte calculation is pointer-safe on LP64 hosts. The staged
ARM closure compiled and linked 448/448 units; its un-packaged ARM executable
is SHA-256 `08204a96a72e5ecbf71147c851738ae6bbc5560f390424cf7af5d8a879a93455`.
The original 90-file WWUI pool is deterministic staging input. The original
`DialogParserClass` now compiles with DialogMgr, controller input, controls,
MenuDialog/MenuBackDrop, mouse, tooltip, and transitions. A deterministic
build-time resource boundary compiles five canonical `chat.rc` records
(main/start-SP/difficulty/splash1/splash2) into native `RT_DIALOG` bytes; its
contract passed main menu 128 (nine controls) and splash 255. The generator
sets the original `DS_SETFONT` bit before appending font data, and an
ASan-validated parser-equivalent walk verifies font skipping, DWORD alignment,
all serialized main-menu controls, and the exact canonical `FONT 8, "MS Sans
Serif"` declaration. The generator aligns the first `DLGITEMTEMPLATE` after
each variable-length font field; all five selected canonical frontend records
now pass normal and ASan parser-equivalent walks. The normal
440-unit interactive M00 host build and its two 120-frame cycles still pass.
This is not a hardware HUD or menu claim, and the frozen A3.2 VPK is unchanged.

The next original bridge, `RenegadeDialogMgrClass`, now compiles with that WWUI
frontier on host and under the Vita ARM compiler. Its Vita single-player
selection retains the original Main Menu, Start SP, options, difficulty, load,
and quit factories; unsupported WOL/LAN factories remain null rather than
being replaced. The manager's `Goto_Location` and command routes retain only
the providers available to this initial single-player path. Canonical dialog
resources are present; the separate original string-table resource boundary
and full DialogBase/control link closure remain next. This is compilation
evidence only, not a menu-runtime or hardware claim.
The isolated canonical dialog-resource contract also passed AddressSanitizer
with leak detection enabled.
`bash tools/validate_a4_dialog_resources.sh` now deterministically regenerates
those templates, runs the host contract, and ARM-compiles the provider as a
32-bit Vita EABI object without repackaging the frozen candidate.

The next authentic frontend translation unit, `MainMenuDialogClass`, now joins
that same bounded host/ARM probe. Its real single-player handlers still
enumerate practice maps and transition through original Start SP/difficulty
logic; only unavailable WOL/LAN routes are conditional. The Vita filesystem
boundary now supplies that original `FindFirstFile`/`FindNextFile` contract
from the read-only retail root with case-insensitive DOS `*`/`?` matching and
traversal rejection. Its 10-check normal and ASan contracts passed, and the
Dialog Manager, MainMenu, and enumeration source passed Vita ARM syntax
validation. This remains compile/logic evidence only: no menu code is linked
into the frozen A3.2-dev1 VPK.

The original Start-SP implementation was also traced, not recreated: its
tutorial command calls `cGod::Reset_Inventory`, `CampaignManager`, then
`GameInitMgrClass::Initialize_SP` and `Start_Game("M00_Tutorial.mix")`.
Its shared `dialogtests.cpp` now has an explicit Vita single-player
compilation boundary: the released Start-SP, Difficulty, and Quit bodies are
selected while unrelated WOL/LAN/GameSpy implementations (whose first missing
declaration is `gamechannel` → `WWOnline\RefPtr.h`) remain excluded. The
resulting 13-unit DialogMgr/MainMenu/Start-SP/Difficulty/Quit probe compiles
normally, under ASan/UBSan flags, and under the Vita ARM compiler; the
retail-root enumeration contract remains 10/10 normal + ASan. This is still
compile-path evidence, not a linked/menu-runtime or hardware claim. The A3.2
candidate hashes still match every entry in its 17-file manifest.

The original `LoadSPGameMenuClass` now joins the same bounded frontend probe.
It retains its released saved-game and map-list construction, ranking, delete,
and genuine `Start_Game` routes. The Vita file-enumeration boundary records
directory attributes and last-write `FILETIME` values while resolving only
within the approved retail/user roots. A small pointer-token bridge keeps the
original 32-bit list-control payload contract safe on LP64 host validation
without changing Vita's ILP32 representation. The expanded 16-object probe
compiled normally, under ASan/UBSan flags, and under the Vita ARM compiler;
file enumeration passed 11/11 and pointer tokens 5/5 in both normal and
sanitizer runs. This remains a compile/logic boundary: Load-SP is not linked
into, nor does it modify, the frozen A3.2-dev1 VPK.

The original `ListCtrlClass` and its embedded `ScrollBarCtrlClass`, required by
that released Load-SP dialog, now also join the probe. Its verified
compatibility surface is deliberately narrow:
the original `LVS_NOCOLUMNHEADER` style bit, page/home/end key values, and
UTF-16 `CompareStringW` three-way sort result. Three VC6 loop-scope uses are
an explicit staged portability patch, not a behavior rewrite. The 19-source
frontend probe compiles normally, under ASan/UBSan, and under the Vita ARM
compiler; its focused sort contract passes 5/5 alongside enumeration 11/11
and pointer-token 5/5. The frozen candidate VPK/ELF hashes remain exactly
`d5b1df3a…e4627` / `69a75b50…5a00` after this host-only work.

The frontier now reaches actual menu construction rather than only parsing:
the original `DialogBaseClass`, `DialogTextClass`, `ButtonCtrlClass`, and
flat-menu `MenuEntryCtrlClass` compile with the canonical Main Menu and
Load-SP dialog records. Their serialized style semantics remain original
(`WS_*`, `BS_*`, `SS_*`, and `ES_*` values); six DialogBase and one ButtonCtrl
VC6 loop-scope uses are staged mechanical portability fixes. The 23-source
probe passes normal, ASan/UBSan, and Vita ARM compilation. Its focused
contracts now total 23 checks: UTF-16 sort/integer conversion 7/7, file
enumeration 11/11, and pointer tokens 5/5. This establishes the next genuine
boundary precisely: full original control/link closure and device lifecycle,
not a replacement menu. The A3.2-dev1 VPK remains unchanged.

Preflight provenance (2026-08-15): upstream is pristine at
`3e00c3a1b97381bb28be89a35b856375e0629a08`; deterministic source inventory is
423 original translation units and 97 applied patches. The historical un-applied
WOL NAT experiment is retained but excluded from that inventory. The baseline
host harness passed A2.1 10/10, A2.2 14/14, A3.0 45/45, A3.1 two-cycle ASan,
targeted UBSan, capture 14/14, and the new controller-axis 9/9 check. Persistent
native-ext4 ccache is present (1.5 GiB; 4,361 / 5,648 cacheable-call hits at the
time of this record).

The durable program objective is **A4.0 — First Playable Campaign Slice**. It
remains active after the A3.2 hardware gate; no A4.0 gameplay implementation
will merge onto an unvalidated A3.2 foundation.

The control frontier now compiles 52/52 selected original/frontend and
single-player lifecycle units in normal host, ASan/UBSan, and Vita ARM builds. It covers the original edit,
combo/dropdown, slider, tab, tree, map, viewer, input, shortcut, merchandise,
progress, health-bar, child, menu-entry, tooltip, and transition controls in
addition to DialogMgr, MainMenu, and Load-SP. Four focused contracts pass:
ListCtrl 10/10, retail-root enumeration 11/11, pointer tokens 5/5, and canonical
dialog resources. A deliberate Vita unresolved-symbol audit found 418 unique
frontend references, with 302 absent from the frozen A3.2 ELF. Adding the
original Render2D, StyleMgr, campaign, GameMode, GameInitMgr, savegame, and
offline Bink boundary owners reduces the remaining frozen-ELF link gap to 91.
The next closure is real renderer/audio/network/resource ownership, not a
substitute menu.
This precisely defines the next authentic link boundary; it is not a
menu-runtime claim. The frozen A3.2-dev1 VPK remains unchanged. A small staged
WWMath patch also removes the VitaSDK `__fastcall` macro-redefinition warning
while retaining the original non-MSVC default-calling-convention intent.

The unchanged 440-unit original interactive runtime was rebuilt after these
boundaries and passed two in-process retail M00 cycles: each completed 120
frames, retained original session/player/camera ownership, submitted its first
frame with 205 meshes / 12,426 vertices / 8,661 triangles and zero
rejected/unsupported submissions, then tore down cleanly. This proves the
frontend boundary did not regress the existing M00 runtime; it does not enable
or claim a device menu yet.

The subsequent A4 source/link closure now selects 495 original and boundary
translation units into one host runtime. Normal, AddressSanitizer, and
UndefinedBehaviorSanitizer builds each linked, then completed two retail M00
cycles of 120 frames with the same 205 meshes / 12,426 vertices / 8,661
triangles first-frame checkpoint and zero rejected/unsupported submissions.
The same 495-unit selection now compiles and links to a Vita ARMv7 ELF against
the production VitaGL, vitaShaRK, FreeType, and platform-stub library closure
(`19925dc85bde73f645100ca61883e84442bf1f86094f18c84b143b928cd6ed9a`).
`CombatGameModeClass`, original `GameMode`, campaign, dialog, and lifecycle
owners are therefore source- and ARM-link-closed. The host still registers a
deliberately narrow M00 harness rather than executing the full
`CombatGameModeClass` virtual/menu graph: its remaining multiplayer
presentation and desktop service owners are not yet portable. This is source
closure and regression evidence only, not a campaign/menu or hardware claim.
It does not modify the frozen A3.2-dev1 candidate.

The direct route now uses original `GameInitMgrClass::Initialize_SP` to create
the single-player data/session owner and `GameInitMgrClass::Shutdown` for its
matching cleanup, rather than manually duplicating that ownership. It does not
call original `Start_Game`/`End_Game`: those functions require the complete
registered Menu/Combat mode graph, which this direct harness intentionally
does not fabricate. Normal, ASan/LeakSanitizer, and UBSan runs each reached
both `original_gameinit_sp_initialized=true` checkpoints and completed two
120-frame M00 cycles; the new ARM ELF above contains the same source boundary.

The bounded lifecycle now executes the authentic `RenegadeDialogMgrClass` and
`MainMenuDialogClass` before the existing direct M00 route: original
`MainMenuTransitionClass` ran three update/render frames with nine original
controls, then shut down cleanly. GDB exposed that the first six transition
controls had been serialized as ID 0 because `chat.rc` aliases from
`dialogresource.h` were not resolved. The deterministic generator now resolves
those source-header expressions; its contract checks the exact IDs
`11000, 11029, 11030, 1563, 11003, 11018`. Normal, ASan, and UBSan two-cycle
M00 validation and the 495-action VitaSDK closure pass. The original
`MenuGameModeClass2` now registers before the original
`Goto_Location(LOC_MAIN_MENU)` call, which itself activates the mode; the
original `GameModeManager` then dispatches three `Think` frames before safe
deactivation and removal around that real dialog lifecycle. Its
single-player staging patch excludes only the unused WOL include, retains
original `gamemenu.cpp` ownership of `g_is_loading`, and uses the existing
silent WWAudio boundary only where original menu code already accepts a null
sound effect. This is original menu lifecycle evidence only; it neither
enables nor replaces the frozen A3.2 device route.

The original campaign catalog is now exercised through the same retail
FileFactory/MIX chain before frontend construction. `CampaignManager::Init`
loads 36 `campaign.ini` flow entries in each of two in-process M00 cycles, and
its matching `Shutdown` clears the flow table before the next cycle. The
catalog contract passed normal and ASan/LeakSanitizer runs, and the current
unpackaged 495-action ARM closure is ELF32 ARM hard-float with SHA-256
`bb58ea315062b70593ade55425fe8fdc00fe72b52d11c2aa7e251ca16582d5e6`.
This proves original campaign content discovery and lifecycle only;
`CampaignManager::Start_Campaign` remains correctly withheld until the real
Combat mode graph can own its `GameInitMgr::Start_Game` transition.

The direct original M00 lifecycle now also retains `PathMgrClass` in the exact
original application position: initialize after `WWMath`, release after
`WW3DAssetManager`. A new canonical host run found that this ownership was
previously omitted, leaving one `PathSolveClass` (80,256 bytes including its
heap) after a two-cycle run. The focused M00 ASan/LeakSanitizer rerun is now
clean and ends PASS; the matching ARM runtime links the same calls. This is a
lifecycle correction, not physical-Vita evidence. Full canonical revalidation
passes at `logs/a30-20260816-122251-host-runtime.log` before the next hardware
package.
