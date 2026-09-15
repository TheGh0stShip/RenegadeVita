# First-mission alpha state

Current: Dev134 canonical/package/matching Vita3K visual milestone PASS.
Resume and native clean exit observed; all 14 saves intact, inputs released.
Physical Vita identity/backup and title-scoped deployment/readback PASS at
10.0.0.202:1337. User asked to launch existing dev79 bubble; command1338 refuses.
Next automatic action: bounded physical Dev134 log collection and assessment.
Native performance/full demo remain unaccepted. No emulator or build running.
See DEV134_PHYSICAL_MILESTONE.md; earlier current entries below are historical.

Current: Dev134 production character-RGB shortcut passes output/transparency
comparisons and sanitizers; canonical host/ARM/package closure is active. Dev133
controller Load Delete traversal is now visibly verified with all saves intact.
Vehicle/Building pages are empty in the unchanged refinery checkpoint; populated
checks, native performance and full demo remain open. See DEV134_SKIN_RGB_WORK.md.
Physical testing held. Earlier current entries are historical.

Current: Dev133 incremental ARM/package closure passes 152 checks. Matching
Vita3K evidence passes four full original reloads, reopened Load, native named
save, Load Delete No/Yes, SELECT input and its Help label, and clean Exit. All
14 existing saves remain unchanged. Original host baseline fails factory
re-entry; normal and UBSan correction pass. Follow-up host focus regression is
active; naturally populated Vehicle/Building and visible objective cycling still
need evidence. No emulator running. Physical testing held; native FPS remains
unproven. Read DEV133_REPEATED_LOAD_AND_OBJECTIVES.md. Earlier entries are history.

Current: Dev131 corrects D-pad confirmation/button focus after Dev130's two
independent all-item runs. Native clean exits and original save/load/settings/
map/weapon/character functionality are retained as emulator evidence only.
Host reproducer fails on baseline and passes the correction; retained UBSan,
incremental ARM closure and Vita3K controller No/Yes Save/Delete/Exit pass.
See DEV130_PAUSE_MENU_VALIDATION.md. No physical acceptance or FPS claim.
Earlier current entries below are historical.

Current: Dev129 independently audits every pause item. Dev128 is archived with
matching binaries/dependencies and shows visible Map/statistics in Vita3K.
Help/Save/deferred Load pass host compilation and two original M00 cycles;
restored Tech Options links and 247 RC controls match LLVM. Settings behavior,
controller save defaults and user-save deletion are under focused validation.
Next: finish those checks, ARM closure and bounded all-item emulator audit.
See DEV129_PAUSE_MENU_AUDIT.md. Physical testing remains held; 60 FPS and full
demo acceptance remain open. Older current-work entries below are historical.

## Current: Dev128 EVA correction and optimization continuation

Latest user reports black pause Map, missing statistics text and other items.
Dev127 canonical closed; bounded Vita3K returns are retained in
build/dev127-initial-return/ and build/dev127-early-pause-return/. The latter
confirms black Map visually but did not load the requested checkpoint because
the public build profile disables it. No Mobius replay or physical acceptance.
Continue tracing original EVA owners, then consolidate with the tested native
DDS chain work in a checkpoint-enabled Dev128 emulator candidate. Physical
testing is held pending further optimization. See current LIVE_PROGRESS.md.

Earlier active statements below are historical.

## Active resume — 2026-09-14

Dev125 package closure now passes 135 focused checks and ARM/artifact identity.
User asked to close Renegade and reopen FTP after the current menu check so
Dev124 logs can be retained before installing Dev125. No current-session
interruption or deployment attempted while FTP is unavailable. Read-only
monitor 24358 remains bounded to 15 minutes from 20:23 UTC.

Dev125 builds a reproduced movie starvation correction plus honest send/draw
timing. Actual drop function can discard 120 consecutive frames under sustained
50ms decoding of 33ms media. New guard presents a due frame after two source
intervals without upload; 19 focused checks pass with scheduler ASan/UBSan.
See DEV125_PHYSICAL_MOVIE_PROGRESS.md. No physical performance gain claimed.
Dev124 user session stays untouched; awaiting FTP/log return under monitor
24358. Next: physical baseline log, Dev125 closure, then hardware comparison.

New physical return: Dev124 reaches intros, but user reports less than 1 FPS.
Startup progress is established by user observation; Dev123 hang cause remains
unproven. User advised to skip intros and check menu, then reopen FTP for logs.
Read-only monitor 24358 continues. Source audit finds movie decode timers omit
avcodec_send_packet cost; inspect physical counters and correct timing coverage
before choosing a measured performance change. No emulator evidence is required.

Dev124 deployed/readback verified at 20:22 UTC. SELF
1f3408f7472a2fbd1e31d811ca99a508779c968025a35fece922c1d305a5f485;
checkpoint feature disabled. User instructed to launch existing bubble with
plugins still disabled. FTP became unavailable afterward; launch outcome is
not yet known. Bounded read-only monitor runs under session 24358 for 900s,
collecting boot/runtime logs when FTP returns. No remote launch/control exists.
Next: read physical trace immediately, isolate boundary, continue correction.

User directs continuous fixing without stopping. Dev124 native boot trace is
building; checkpoint feature disabled. Original display/filesystem work occurred
before runtime logging, so no Dev123 log does not prove pre-main failure.
Raw SceIo early-constructor/main/display/filesystem markers pass host ASan/UBSan
and ARM startup compilation. See DEV124_NATIVE_BOOT_DIAGNOSIS.md. Next: finish
incremental closure, deploy/readback, user manual LiveArea launch while command
port remains unavailable, then collect exact physical trace and fix its cause.

Recovery complete: user reports plugins disabled and VitaShell running. FTP
works. No a35-dev123-runtime.log in original logs directory, and no recent
eboot dump found in ux0:/data or ur0:/data. Preserved directory inventories and
readback of failed Dev123 executable. Exact pre-deployment SELF restored and
readback verified: d7bdadbff7296dad0d5460d0febfe70116502c9a80695bfa3577f6c629f9c596.
Nothing launched. Receipt: build/device-evidence/dev123-full-demo-20260914T201320Z/
recovery-20260914T201913Z/receipt.json. Plugin state at original failed launch
is not established. Next: native pre-main/bootstrap investigation against the
retained matching binaries, before requesting another physical launch.

PHYSICAL FAILURE: user reports Dev123 never launches, black screen and Vita
unresponsive. Both 10.0.0.202 ports 1337/1338 refuse connections after report.
No physical runtime log/dump retrieved; failure phase and cause unknown.
Dev123 is rejected for further playthrough attempts. User advised power-button
recovery and reopening VitaShell FTP. Next: pull candidate logs/crash evidence
before restoring exact backed-up predecessor; do not relaunch Dev123 or infer
a Vita root cause from emulator evidence. Backup and deployment receipt remain
at build/device-evidence/dev123-full-demo-20260914T201320Z/.

Physical deployment complete: Dev123 SELF readback matches
5b033c8ae067910a03df1345574e2e89d97e8bd14d5b54afc71040c59cb634df.
Installed predecessor backed up, matching VPK uploaded, original Arial MT
copied to user/fonts and verified. Retail M00 hash matches accepted baseline.
Receipt: build/device-evidence/dev123-full-demo-20260914T201320Z/deployment.json.
Awaiting user LiveArea launch because only FTP is available. User plays normal
startup/menu/full Tutorial/thanks/credits/menu return; no synthetic input.
Next: assess user observations and pull a35-dev123-runtime.log after FTP returns.

User scope change: physical Vita 10.0.0.202:1337 is available and user requests
the entire demo. Physical hold is lifted for this PS Vita test; PSTV unchanged.
No further port adaptation to emulator behavior is authorized. Dev123 is an
unaccepted native hardware candidate, not a proven physical capture fix.
FTP admission passes; remote command port 1338 refuses connections. Prepare
verified Dev123 executable replacement with installed backup and matching VPK
under user/, normal startup (no checkpoint/input flags). User launches through
LiveArea and owns all gameplay. Next: deploy/readback, hand over full demo,
then collect matching physical runtime evidence when FTP is available.

Latest result 20:10 UTC: Dev123 same-save recovery reaches visible Hotwire
gameplay and nonblack Vulkan F12 capture. Hashed evidence retained at
build/dev123-recovery-return/receipt.json. Run ended at its 90-second watchdog;
owned process terminated and F12 release confirmed. No clean-exit or native
readback acceptance. Dev123 is installed, no build/runtime remains active.
Next automatic action: diagnose credits cutoff using original sentence/atlas
ownership, then match wall/sky/elevator camera evidence and repeat lifecycle.
Final user playthrough and physical device testing remain held.

Dev123 incremental package passes 134 checks and artifact closure; installed
with Dev121 backup. Runtime Dev123-hotwire-recovery-20260914-r1 now tests the
same Hotwire save with Vulkan and a 90-second bound, no synthetic navigation.
Correction removes Dev122 GPU-transfer capture regression; native CPU readback
remains visually unproven. Details: DEV123_CAPTURE_REGRESSION_RECOVERY.md.
Next: retain this runtime result and resume remaining visual checks.

Connection recovery at 20:05 UTC: Dev122 r1 is PROCESS_FAILED, not running.
Its emulator log reports a Windows access violation after level-ready, before
the loading capture return. Frozen copy and hashes: build/dev122-resume-failure-return/.
Dev121 rollback had already completed; installed SELF reverified as
7f79e0016d2d09bd65242370c6ac99fa51f505ba27b557bd7b270b9a7a43e0b4.
No emulator was running and native input opt-in was absent. Current comparison:
Dev121-hotwire-resume-20260914-r1, same unchanged Hotwire save, Vulkan,
90-second watchdog, no synthetic input. Next: assess this control before
attributing failure to Dev122 readback. Final playthrough and physical hold
remain in force. This supersedes all older running/install statements below.

Latest: Dev121 front-buffer selection still returns black native BMP; Vulkan
F12 works. Evidence build/dev121-capture-return/. r1 is terminal at its
19:59:25 UTC watchdog. Native Select released and marker removed. Dev122 GPU
transfer readback (mapped RAM + finish + transfer + copy/free) passes initial
134 checks and package closure. Final pre-runtime hardening zero-initializes
the temporary pool allocation; final incremental build runner 36985,
build/dev122-fast-final.log. Earlier pre-runtime package retained under
build/dev122-pre-runtime-package/. Dev122 not installed yet. No source edits
during the active build. Final user playthrough/physical tests remain held.

Current Dev121: 134 focused checks and ARM/package closure pass; installed with
Dev120 backup. Starting Dev121-gunner-capture-20260914-r1, 180-second bound,
Vulkan and native Select input. This verifies explicit front-buffer selection
after presentation. Dev120 r5 proved Vulkan F12 captures work; game-owned BMP
was black. Retained build/dev120-vulkan-return/; r5 is stopped (forced after
close deadline), native inputs released. User's Logan line was original
PREPARE_INFANTRY and completed; WF handoff has not occurred in the old Gunner
save. See DEV121_CAPTURE_SOURCE.md. Older live/build states below superseded.

Current continuation: r4 is terminal TIMEOUT_UNASSESSED, owned process stopped
at 19:45:29 UTC. r5 starts unchanged Dev120/Gunner save with native input enabled
and uppercase Vulkan config to bypass pinned emulator default-value merge.
Runner 46883, 180-second bound; verify actual backend and capture result.
Source identity unchanged; only test tooling changed. Final user run held.
Previous live process statements below are superseded.

Latest user return: broken walls; screenshot and framebuffer inspection requested.
Retained build/dev120-wall-return/ shows a broad brown terrain-like polygon
intruding through the left wall. Root cause unconfirmed. Emulator native PNG
is all black; two posted Select attempts and one bounded focused scan-code
Select produced no new native capture bundle. All keys released, no navigation
since user resumed. Current engineering r4 PID 31076, runner 39896, 300-second
bound from 19:40:29 UTC; verify process before action. Despite YAML and explicit
CLI Vulkan requests, title/log still say OpenGL: not Vulkan evidence. Original
render cache mode F restored with matching backup hash. Physical access held.
Temporary host credits-atlas probe compiled/linked against existing host
objects but segfaulted; backtrace under build/dev120-credits-probe-backtrace.log
(session 83189). Investigate harness compatibility before treating as game bug.
Final user playthrough remains held; loading bar visually fixed, music native
decode/output evidenced; wall/sky/elevator, credits cutoff, capture/repeat
lifecycle remain open. See DEV120_RENDER_COMPARISON.md.

Dev120 fast package passes 133 checks and ARM/ELF/SELF/VPK closure. Installed
with Dev119 backup; fresh startup/menu engineering run active, PID 30032,
runner 4301, 900-second bound. Evidence Dev120-menu-loading-engineering-
20260914-r1 under D:/Vita3K/RenegadeEvidence. Native input remains disabled.
Original loading-bar and menu music visual/audible validation pending.
See DEV120_ORIGINAL_LOADING_AND_MENU_AUDIO.md and BUILD_STATE.json hashes.

User correction: remove Dev119's duplicate loading overlay and repair the
original animated loading model. Dev119 logs show a corrupted animation name
and null binding; LoadingScreenClass passes StringClass through `%s` varargs.
Correct the argument ABI, retain original progress/frame ownership, and prove
visible fill before acceptance. Main menu music is also missing; trace original
MenuGameMode/WWAudio/Miles decode. Credits atlas cutoff, sky/elevator artifacts,
and repeat lifecycle remain open. Final user playthrough stays held.

Dev119 engineering package is installed and launching Power Plant recovery in
Dev119-powerplant-engineering-20260914-r1 (runner 50246, max 1800s, F12 native
screenshots and bounded native-input channel enabled). 131 focused checks and
artifact closure pass; runtime/visual/repeated-lifecycle validation pending.
Final user run held until all known fixes. DEV119_ENDING_AND_FINAL_RUN.md has
hashes and current plan; earlier stopped/Dev118-install statements superseded.

Current: Dev118 original finale succeeds in Vita3K; thanks/credits captured and
clean teardown retained at build/dev118-finale-return/. User requests original
main-menu return after credits, polished credits imagery/layout, and animated
loading fill bar. Dev119 source work started; no new build. Then prepare a full
user-controlled startup/menu/tutorial run with capture, profiling and native
framebuffer inspection where supported. See DEV119_ENDING_AND_FINAL_RUN.md.
Emulator PID 3148 has stopped. User owns navigation during the final run;
proceed with engineering/setup autonomously without awaiting replies.

User now explicitly requests autonomous action without waiting for replies.
Stopped the identity-matched locked Dev117 session; installed verified Dev118
with title backup and restored the immutable Power Plant save into fresh slot
dev118-powerplant-20260914.sav. Launching Dev118-powerplant-20260914-r1,
runner session 31699, bounded 1800 seconds. Native input enabled for bounded
original gameplay validation; release every command. No physical device work.
Setup receipt: D:/Vita3K/RenegadeEvidence/
A3.5-dev118-setup-20260914T190038342035Z/setup-receipt.json.
This supersedes the request to await permission to replace the user session.

Current blocker: user reports Logan never follows his scripted routes and the
finale locks player controls without lieutenant approach. Runtime continues
through frame 33120. Restored omitted original PathMgr::Resolve_Paths service
at the frame boundary; 18 focused checks and affected ARM compilation pass.
Dev118 consolidated fast package now passes 130 focused contracts and artifact
identity/closure; matching files in dist/. Next: validate NPC traversal/finale
from the preserved Power Plant checkpoint. Runtime acceptance pending; user session
has not been interrupted. See DEV118_NPC_PATH_SERVICE.md.

Newest checkpoint: Power Plant, original save archived unchanged at
build/tutorial-checkpoints/m00-powerplant-dev117, SHA-256
f2bfd52e17f9127daf22268974a6d6521614e343a5a9eae6c472adcbc5e51ddd.
Strict save structure passes; reload unassessed. Latest mission breadcrumb
frame 19986: statuses 1/1/1/1/1/3, no active conversation, player
(-44.966,19.480,-7.981). Previous Refinery quicksave backed up before fresh
save; all immutable masters retained. Save shortcut released; PID 17392
continues under user navigation. Evidence: build/dev117-powerplant-checkpoint/.

Latest checkpoint: user reports Logan's Refinery objective complete. Original
quicksave archived unchanged at build/tutorial-checkpoints/m00-refinery-dev117,
SHA-256 d46e268940d3c149bc90c7fcc7df6db4c370408cf7ef32e5539a685f5e702c23.
Strict save structure passes; reload unassessed. At capture, native objective
statuses were 1/1/1/1/3/3 and MTU_MOBIUS_REFINERY conversation was active.
Prior quicksave backed up under build/dev117-refinery-checkpoint/previous-slots;
Hotwire/Mobius masters untouched. Save chord released, no navigation input.
Same recovery-r2 user session continues, PID 17392.

Current: Dev117 froze after the WF/tank segment and Refinery handoff. Evidence
retained before forced stop; original objective 4 became pending and movement
continued to frame 38400 before logs stalled. Cause remains unconfirmed.
User requested Hotwire/Gunner reload for visual inspection. Same Dev117 now
launching original Hotwire checkpoint in Dev117-hotwire-recovery-20260914-r2.
Debugger-enabled r1 stalled at module loading and ended without starting the
game; ordinary debugger-disabled settings restored for r2. Hotwire original
reload now passes with restored player/camera and advancing frames; PID 17392,
runner 72933. User retains navigation; next is user-positioned defect capture.
See DEV117_REFINERY_HANG.md; this supersedes prior live PID.

Latest steering: sky rectangles, moving black elevator artifacts, and objective
message squares after Gunner. Original Hotwire/WF checkpoint now archived with
released save shortcut; user retains gameplay control. Dev118 corrects both
ObjectiveManager WideStringClass varargs descriptions, with executable original
formatting and ARM-object tests passed. Sky/elevator root causes remain open;
await a user-positioned defect capture before choosing a renderer correction.
Details and exact checkpoint hash: DEV118_VISUAL_DEFECTS.md.

Crash recovery: preserved the running Dev117 user session and verified the
Mobius master hash. Recovered the newer Dev118 tutorial-hint source changes;
retained 19 passing focused tests and deterministic staging, then compiled
scriptcommands/weaponview ARM objects successfully in the existing fast tree.
No new package or runtime claim. Details: DEV118_PENDING_BATCH.md.
Next automatic engineering action: consolidate demonstrated corrections while
user controls M00 progression; package only a coherent batch. Mission ending,
moving/firing performance and hint visibility are still unproven.

Latest user steering: user owns gameplay input/navigation. Stop automated
movement and repeated screenshot-navigation loops. Agent owns original-engine
checkpoint creation/backup and engineering/diagnostics. Dev117 progression run
is handed to user control; inspect the owned Windows receipt before any process
action. Native development input disabled. Do not launch another run or kill
this one merely to collect more navigation evidence. No per-fix package builds.
Mobius checkpoint now archived from original quicksave, structurally valid;
reload unassessed. Pending batch and live session details: DEV118_PENDING_BATCH.md.

This entry supersedes historical current/paused statements below. Workspace is
the active bash tree, main at f28578a with retained uncommitted Dev100–116 work.
User resumed demo completion followed by the complete native port. Dev116 canonical closure passed; installed
SELF was rechecked against 5c9102d72098fcad8fade3f7cb1385814422fd58f50f9fa20850bcdac369f3c7.
See HANDOFF_DEV116_20260909.md for matching artifacts and immutable saves.

Plan: restore the Gunner master into a fresh offline slot; prove its original
reload and Dev116 EVA pause/resume; complete original M00 range/vehicle/final
tasks and observe success/ending/exit. Then close platform prompts, remaining
presentation and measured performance gaps before the full-port milestones.
Physical PS Vita/PSTV access remains held. A3.1.4 remains the accepted physical
baseline; no demo-release gate is newly accepted. Full M00 and ending remain
the earliest unproven mission dependency. No external source was imported.

Dev116 Gunner reload and one visible EVA pause/resume cycle now passed on
Vita3K. User redirected priority to rifle hand pose, grey EVA margins and
measured 60 FPS polish. Runtime shows corrupted first-person animation names
and pistol-idle fallback; original StringClass objects crossed a varargs ABI.
Source corrections use explicit string-pointer conversion and black menu clear
color while Combat is suspended. The consolidated Dev117 fast package passed
identity/closure and matching Vita3K replay, rifle/reload/EVA visual checks,
using the existing tree after focused tests and the ASan Targa fix.
The checkpoint option is now scoped to its one source consumer, avoiding future
engine-wide recompilation when that setting changes. No canonical retry.
User's latest workflow correction: use focused executable tests and incremental
object compilation in existing build directories; accumulate coherent fixes
before a fast runtime package. Full canonical validation belongs at milestone/
release gates, not each small batch. Do not restart Dev117 canonical now.
Its host pass stopped at an ASan Targa constructor/caller layout mismatch;
inspect header/cache provenance and fix through the focused existing target.
Next: retain this tested package, batch bounded reload diagnostics with fixed
moving/firing profiling and original M00 progression. No build for that isolated
diagnostic. See DEV117_WEAPON_EVA_CORRECTIONS.md for final hashes and evidence.

## Current: Dev112 consolidated source; canonical closure pending

Original EVA pause/resume and safe exit, culling inversion/cache correction,
and opt-in original checkpoint startup are implemented. Eight changed native
units compile and 23 focused contracts pass. Fresh original M00 host validation
and semantic fingerprints passed; one additional obsolete lifecycle assertion
in the wider suite has been corrected for canonical retry.

The retained dev111 emulator session ended at timeout after progression through
Sydney and a later Petrova encounter. Four original saves were archived; their
reload is not proven. Post-Sydney is restored to a new dev112 slot and queued.
No dev112 package/runtime acceptance yet. HUD digits, elevator artifacts,
loading presentation, complete M00/ending, and 60 FPS remain open.
See DEV111_M00_RUNTIME_RETURN.md and DEV112_RETAIL_FONT_RETURN.md.

## Historical dev111 work, superseded above

Dev111 r7 passed canonical closure after correcting the optional EVA desktop
include and obsolete decoder symbol check. ARM/SELF/VPK identity and package
hash checks passed. The same-directory retry achieved 521/521 cacheable direct
hits. Build/test work is authorized; Vita3K installation is running.

Fresh retail comparison matches all 51 source files and validates 31 archives.
Dev111 is running in Vita3K 4093 in the retained 20260909T030903Z session.
Original M00 progressed through the ladder/jump area, EVA and poke briefings,
GDI soldier interaction, opened gate and course-exit "Follow Me" trigger.
Two original quicksaves were created and archived unchanged: initial spawn and
post-obstacle. Reload remains unproven. First intro, orange/red second intro,
menu labels, objective image and pistol are visible in retained captures;
bitmap HUD digits and sky remain visibly defective. Next: follow Logan to the
guard tower, retain further original progression and close save-load/UI gaps.
See DEV111_M00_OBSTACLE_RETURN.md. Full M00 and presentation acceptance remain
unproven.
Pause requires retained DialogMgr ownership and original resume/exit routing.
Developer checkpoint parser/request tooling passes four host tests but is
not connected to runtime; its isolated hook draft failed dry-run validation.
Older hold/current-candidate descriptions below are historical.

## Current: loading presentation and original pause restoration

Source-only loading/menu batches are implemented; no new build or runtime
evidence. Hidden warmup, loading-clock/progress and bounded texture preparation
are described in M00_LOADING_MENU_READINESS_BATCH.md. Main-menu and SP-submenu
demo restrictions preserve labels and reject unsupported interaction.
Next: original EVA pause owner and tab dependency selection, persistent UI
lifetime and authentic resume/abandon routing. An optional-network null guard
is staged as a registered patch but has not been executed. See
M00_PAUSE_OWNER_DEPENDENCIES.md. Build/test and physical holds remain.


## Current: substantial performance batch, no further small-step builds

Dev110 existing fast package installed successfully, not launched. Source-only
work adds opt-in native sampler-object and per-pass material-color reuse with
bounded storage and baseline/individual/combined A/B modes. These changes are
not in the installed binary and have not been compiled or measured. See
RENDER_WORK_REUSE_BATCH.md. No new build, tests or physical access in this unit.
Next: consolidate the substantial performance/save-resume batch, establish a
fixed original M00 benchmark/checkpoint and retain honest before/after evidence.
Full tutorial, original save/load, HUD/loading correctness and ending remain open.


## Latest return: Dev105 retail repair and updated Vita3K retry

Dev105 fast closure passed. Retail repair and original-owner runtime reads
are evidenced in DEV105_RETAIL_DATA_RETURN.md: 51 source files match, 31
archive indexes valid, loose Data routing restored, reticle DDS read from MIX.
Next: assess same-SELF run under updated Vita3K at
D:/Vita3K/RenegadeEvidence/Dev105-updated-20260908T223341Z/; continue M00.
No full-M00, checkpoint, 60 FPS+ or physical acceptance. One malformed W3D
request remains a native diagnostic lead, not a demonstrated copy gap.

## 2026-09-08: Dev105 active first-frame correction

Current source: Dev105. Dev104 fast passed; exact emulator runtime passed
loading capture and 60 prewarm frames but controlled-exited on the first-frame
gate. Original projector NULL fallback was misclassified as a rejected draw.
Dev105 corrects that classification and saved-player startup reuse without
changing original serialization or fresh-spawn ownership. No emulator fork.
Next automatic action: fast build, matching M00 route past the first frame,
then original save/load proof. User authorized routine fixes; physical hold
unchanged. Complete M00, checkpoints, HUD fidelity and 60 FPS+ remain unproven.
Retail audit: exact reticle DDS is in installed always.dat; whole Data identity
comparison uses E: Steam, because the old C: retail-pc link is stale.
Details: DEV105_FIRST_FRAME_AND_SAVE_REUSE.md. Older entries are history.

## 2026-09-08: Dev102 current continuation

This entry supersedes historical active-candidate wording below. Dev101 fast
and canonical builds passed; its emulator presentation failed according to
the user and matching logs. Dev102 targets original sentence readiness,
first-draw movie timing, and explicit RGBA colors. First fast compile failed
because staging was reused; restaged retry is next, not a claim of closure.
See `DEV102_PRESENTATION_AND_DEMO_PLAN.md` for evidence and the route plan.
No physical access, full tutorial completion, or 60 FPS+ claim. The complete
native game remains the durable destination; M00 demo is an interim profile.

## 2026-09-08: Dev100 active M00-only demo source candidate

The complete native Renegade Vita port remains the durable destination. M00
is an interim community showcase, not a reduction of the full campaign and
original-system scope. Charter and roadmap now state this explicitly. Fast
Dev100 closure passed after removing the leftover M01 cache check; canonical
compilation is running. A hash-bound fast-package Vita3K intro/menu observation
is in progress, with title backups and unchanged retail. No hardware access.

- Current scope: all authentic M00, original-success fade / exact thank-you /
  credits / safe teardown; no later mission launch or retail redistribution.
- Current source changes and retained evidence: `DEV100_PRIOR_WORK_AUDIT.md`.
  No complete Dev100 tutorial run or visual acceptance is claimed.
- Last canonical package remains Dev99 until Dev100 build closure is recorded.
- Vita3K preliminary testing is authorized with the user's existing Windows
  installation and emulator retail files; setup tooling is title-scoped.
- Both PS Vita and PSTV are required for final acceptance. Physical testing
  remains on hold; accepted A3.1.4 and frozen failure evidence are unchanged.
- Performance target is 60 FPS+; lower bands are diagnostics, not new goals.

## 2026-08-31 — Dev99 local candidate; physical frontend gate still failed

- Workspace: active bash tree on `main`; upstream remains separate and pristine.
- Last completed implementation: Dev99 preserves Dev88 through Dev98's shared glyph-state, BINK-audio reserve, frontend-scope, bootstrap, Render2D, synchronous loading, Start-route, target-box rollback, BINK reductions, text-atlas, native gameplay HUD presentation, vehicle/HMVV diagnostics, startup framebuffer retention, synchronous loading callbacks, deferred indexed Render2D state, HUD `Think()`/`Init()` scoping, BINK audio-pressure frame dropping, host main-menu translation validation, MessageWindow presentation scoping, short-wchar libc wrappers, bounded UTF-16 formatted output, candidate-scoped startup-precache receipts, delayed BINK presentation-clock arming, and bounded Vita WWUI dialog-template translation copying. It adds a startup-status repaint worker that redraws the current native debug status during original root/MIX factory construction before visible pre-cache. It preserves original UI/movie/HUD/world owners and unchanged retail data.
- Latest canonical candidate: `dist/RenegadeVita-A3.5-dev99.vpk`, VPK SHA-256 `be9939594d7c25f4039f4aefbf77af631ccd6cb1200ed1a50b175cb6534b6c86`; matching ELF SHA-256 `fdce12071b368326c4b863547a87b58a9fb69fe7290d9425e9895371e4e9888e`; packaged SELF SHA-256 `020f210a129beaaf4d0953c6c56efc82267a52949d6883c5db313e87b0790d6d`; diagnostics ZIP SHA-256 `f13a8f28309821a3c4d408000fccc681e955ba467d267bccab72c21b71302c68`. Deterministic 145-patch staging, focused contracts, fast closure, and canonical 549-action closure passed. Dev99 is local only.
- Latest physical checkpoint: Dev87 is a retained frontend usability failure. The matching partial runtime log ends at main-menu activation; the user reports missing menu text, slow/buzzy intro A/V, empty gameplay dialogue text, mangled HUD text, target-box drift, black pre-cache delay, HMVV freeze, and Start crash. It cannot establish Dev99 correctness.
- Media/capture: the later user-finalized Dev87 recorder MP4 was pulled read-only and yielded six labelled M00 stills. VDB `capture.screen.v1` is now the required future screenshot route; a Dev99-matching exact-title provider bundle was built host-side under `<VitaDevBridge>/build/exact-title-provider-rnega3101-020f210a-dev99-r26`, but it is not installed and has captured no PNG/raw/metadata evidence.
- Current blocker: physical verification of readable original frontend/dialogue text, paced intro A/V, readable HUD/loading feedback, stable M00 progression, safe Start/pause/exit, and fixed-route frame pacing.
- Exact next automatic action: continue source-only performance/fidelity preparation: keep FPS targets at 60 FPS top-end, 50 FPS preferred floor, 30 FPS degraded floor, and 20 FPS critical floor; retain renderer cache-skip and slow-frame-band telemetry for the next build; then build/test only when authorized. Do not deploy Dev99, install the VDB provider, launch the title, or modify the Vita without explicit direction.
# Latest state: stopped after dev113 test

Canonical dev113 passed. Fresh M00 starts; pause/resume control works with blank
EVA presentation. Saved-player identity restoration remains a controlled failure.
Vita3K is closed and all active sessions are terminal. User requested session
end; resume details are in `DEV113_OVERNIGHT_RETURN.md`. No completion claim.
