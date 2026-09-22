# Live engineering progress

## Dev156: M13 rocket aggregate live creates reduced

Renegade Vita - v3.5 active
`[░░░░░░░░░░] 0/10 release acceptance gates complete`

Now: identify the non-aggregate fiery-effect path and remaining simulation
owners. Completed: M13 loading retains original `ag_rocketl`; fresh live
clones take 81-162 us versus Dev155's roughly 101-151 ms creates. The
ineffective `ag_fiery_ex06` experiment was removed. Explosion live setup
remains 7.090 ms.
Evidence: matching asset-free ARM SELF/VPK and managed AppData
`campaign-dev156-final-m13-1` Vita3K/OpenGL receipt/log. Whole-route frame
percentiles did not improve; no A/V, physical or campaign acceptance.
Next: fiery-effect ownership and >400 ms simulation frames.
Blocker: overall cinematic pacing remains far below 60 FPS.

## Dev155: M13 explosion stall moved to loading; A/V still open

Renegade Vita - v3.5 active
`[░░░░░░░░░░] 0/10 release acceptance gates complete`

Now: isolate remaining ambush asset-create and simulation spikes, then
validate authored actor/camera/audio sequence. Completed: an untouched
`X00_AG_Explode` aggregate template is built once during M13 loading;
fresh original `Clone()` instances reduce the first live rocket `Set_Model`
from Dev154's 6.638 s to 9.016 ms in matching final-hash Vita3K evidence.
Full-port M00 direct entry reached 360 frames. The demo profile is unchanged.
Evidence: asset-free ARM SELF/VPK, 193-patch staging, parser tests,
`campaign-dev155-final-m13-1` and `campaign-dev155-final-m00-1` managed
AppData receipts. No physical or full-cinematic acceptance.
Next: remaining >500 ms ambush frames, A/V sync and memory high-water.
Blocker: overall cinematic frame pacing remains far below 60 FPS.

## Dev154 diagnostic: aggregate child creation, not attachment

Renegade Vita - v3.5 active
`[░░░░░░░░░░] 0/10 release acceptance gates complete`

Now: test a retained, assembled original WW3D template for M13 explosion
instances, preserving fresh per-use clones. Completed: original aggregate
`X00_AG_Explode` creates 91 children; child creation totals 6,634,366 us,
attachment 207 us, base 184 us. Class ID 25 did not establish prototype type;
the earlier HLOD-constructor assumption was wrong. Reject attachment-update
batching as a freeze fix.
Evidence: matching asset-free ARM SELF/VPK, 195-patch staging, managed AppData
`campaign-dev154-children-m13-1` Vita3K/OpenGL receipt/log. No physical or
accepted performance evidence. Next: retained-template A/B and M00 regression.
Blocker: live cinematic still freezes for multiple seconds.

## Dev153 diagnostic: M13 HLOD constructor owns repeated create cost

Renegade Vita — v3.5 active
`[░░░░░░░░░░] 0/10 release acceptance gates complete`

Now: time original `HLodClass(const HLodDefClass&)` phases for
`X00_AG_Explode`; retain original instances and animation semantics.
Completed: WW3D asset-manager trace shows its prototype already present;
lookup 4 us, on-demand load 1 us, `proto->Create()` 6,122,860 us.
Class ID 25 is original HLOD. No nested child create exceeded the bounded
100 ms threshold. Pre-create/cache experiments remain rejected.
Evidence: asset-free ARM SELF/VPK, 192-patch staging, managed AppData
`campaign-dev153-assetdepth-m13-1` Vita3K/OpenGL receipt/log. No physical
acceptance or verified A/V fix.
Next: isolate constructor LOD/aggregate/bounds/LOD-factor phase, then fix
the confirmed algorithmic defect or amortize preparation without breaking
per-instance state. Blocker: live cinematic still freezes.

## Dev152 diagnostic: WW3D per-instance create owns M13 freeze

Renegade Vita — v3.5 active
`[░░░░░░░░░░] 0/10 release acceptance gates complete`

Now: isolate recursive WW3D prototype creation versus on-demand child loads.
Completed: rejected Dev151 warmup removed. In matching Dev152 M13 run,
`PhysClass::Set_Model_By_Name("X00_AG_Explode")` spent 6,083,581 us in
`WW3DAssetManager::Create_Render_Obj`, 39 us installing the model into the
physics scene, and 1 us releasing the local reference. This explains why a
prior create/release prewarm did not remove the live cost.
Evidence: asset-free ARM SELF/VPK; 191-patch ordered staging; managed AppData
`campaign-dev152-physmodel-m13-1` Vita3K/OpenGL receipt/log. No physical
acceptance or A/V sync fix.
Next: bounded nested asset-manager timings, then a focused fix to the
confirmed repeated inner work. Blocker: live cinematic still freezes.

## Dev151 rejected: M13 WW3D pre-create does not remove live stall

Renegade Vita — v3.5 active
`[░░░░░░░░░░] 0/10 release acceptance gates complete`

Now: remove the rejected preparation and time the original
`PhysClass::Set_Model_By_Name` inner calls. Completed: one M13-only
loading-phase `WW3DAssetManager::Create_Render_Obj("X00_AG_Explode")`
and release returned a valid object but cost 5.885 s. The same run's live
slot-19 Set_Model still cost 6.005 s. This is no performance gain, and the
candidate must not be retained as an optimization.
Evidence: asset-free ARM SELF/VPK, `campaign-dev151-modelprep-m13-1`
Vita3K/OpenGL receipt/log; unassessed watchdog, no physical evidence.
Next: split WW3D instance creation from `PhysClass::Set_Model` scene
installation, fix only the confirmed inner cost. Blocker: live cinematic
freeze and A/V desync remain unresolved.

## Dev150 diagnostic: M13 slot-19 model setup identified

Renegade Vita — v3.5 active
`[░░░░░░░░░░] 0/10 release acceptance gates complete`

Now: prepare only the authored `X00_AG_Explode` WW3D model during M13 loading,
then A/B the first ambush rocket. Completed: original `Invisible_Object`
1500000007's timer dispatch invokes `Test_Cinematic` `Create_Object, 19`;
retail M13 data maps slot 19 to `X00_AG_Explode`. The isolated Dev150 run
measured object allocation at 377 us and original `Set_Model` at 6,166,481 us
within the 6,168,914 us script timer. No game behavior was bypassed.
Evidence: matching asset-free ARM SELF/VPK and managed AppData
`campaign-dev150-slot19-m13-1` Vita3K/OpenGL receipt/log. Timeouts are
unassessed and do not prove A/V sync, visual sequence, or physical performance.
Next: same-route loading-time WW3D preparation A/B, M00 regression, and
retain only a measured win. Blocker: live cinematic still freezes for about
six seconds at slot 19; audio desync and 60 FPS remain unresolved.

## Dev149 diagnostic: M13 ambush freeze isolated to one original object

Renegade Vita — v3.5 active
`[░░░░░░░░░░] 0/10 release acceptance gates complete`

Now: trace object `1500000007` inside original `Post_Think`; do not claim a
performance fix. Completed: bounded, full-port-only scene/render, Combat Think,
and object timing. An isolated M13 Vita3K/OpenGL run captured a 6.778 s frame
at frame 633: 6.740 s simulation, 37.6 ms render. Original
`GameObjManager::Post_Think` consumed 6.701 s, of which one object callback
consumed 6.700 s; observer and script cleanup each took about 1 us.
Evidence: `campaign-dev149-postowner-m13-2` in managed AppData, matching
SELF SHA-256 `d4035771f2820779c6e33604fcd83d016287213ec433a43d6fcb8f59644ad482`;
189-patch staging inventory and ARM SELF/VPK build pass. Vita3K run timed out
unassessed; no physical evidence. Earlier Dev149 launch attempts with missing
package or unopened title are not runtime evidence. Demo profile logging is
unchanged.
Next: identify that object's definition and the slow inner callback/asset path,
fix it at its owner, and repeat the same M13 route plus M00 regression.
Blocker: root operation inside object `1500000007` is not yet identified;
ambush A/V sync and 60 FPS remain failed/unverified.

## Dev148 diagnostic: M13 cinematic stall and render cost

Renegade Vita — v3.5 active
`[░░░░░░░░░░] 0/10 release acceptance gates complete`

Historical: Dev148's render-side hypothesis was superseded by Dev149's
simulation/object timing. Its diagnostic build was published explicitly
unaccepted; no cinematic clock or performance change was adopted.
Completed: isolated Vita3K M13 traces locate intermittent 0.9-1.3 s frames
inside original foreground `WW3D::Render` / `scene->Render`, across world-space
and dynamic objects; background, HUD, and final flush are not the slow phase.
The WW3D double-sync and camera-wall-clock experiments failed/reverted; the
latter disrupted authored actor sequencing. A loading-only M13 referenced-texture
prewarm moved 183 textures to loading, yet the isolated run still reached a
13.77 s worst frame by frame 480 (p50/p95/p99 100.5/275.9/389.2 ms), so it
was also rejected/reverted. Demo behavior remains unchanged.
Bounded in-memory mesh timing found 6.46 s across 10,382 submissions in
frames 361-480 but only 0.19 s across 25,450 indexed draw completions.
A repeated-color submission candidate still hit a 6.91 s frame by frame 720;
it was rejected/reverted. The diagnostic timer is full-port-only.
Evidence: ARM diagnostic SELF/VPK and isolated `campaign-dev148-textureprep-m13-1`
plus `campaign-dev148-{meshboundary,colorcache}-m13-1` Vita3K/OpenGL receipts
under managed AppData; runs timed out unassessed. No
physical Vita evidence or accepted performance win. Dev148 source commit
`ceef9c0` and its asset-free, explicitly unaccepted diagnostic VPK are
published; Dev147 remains the last performance checkpoint.
Next: distinguish scene traversal/material-state/backend costs in the long
frame with a bounded in-memory probe, then make one focused candidate.
Blocker: intermittent large original scene-render stalls still desynchronize
real-time audio from clamped cinematic/game time; root render cost unconfirmed.

## Dev145 active: original M13 intro camera restored in Vita3K

Renegade Vita — v3.5 active
`[░░░░░░░░░░] 0/10 release acceptance gates complete`

Now: restore original player-death
dialog/restart ownership; do not use bare mission loads as progression proof.
Completed: full-port links original CinematicGameObj factory; diagnostic M13
creates retail `Generic_Cinematic`, takes camera control, hides HUD, shows
moving scripted viewpoints, then restores gameplay HUD/camera. M00 demo source
selection is unchanged. Vita3K sampled 11-14 FPS, so performance is open.
Evidence: `reports/DEV145_M13_CINEMATIC_FACTORY.md`, matching ARM/VPK hashes,
and isolated Vita3K log/captures; no physical Vita acceptance.
Next: original death/failure dialog resources and callback, targeted death/
restart/save test, then prerequisite-aware M13 mission checks.
Blocker: player death currently exits the direct runtime through a latch-only
observer instead of preserving original `cGod::Star_Killed` flow.

## Dev144 active: Score dialog fixed; M13 cinematic camera under investigation

Renegade Vita — v3.5 active
`[░░░░░░░░░░] 0/10 release acceptance gates complete`

Now: isolate the original M13 intro camera-object/control failure; authored
letterbox and audio advance while the view remains static with HUD.
Completed: full-port Score dialog resource 239 and controls, four focused
tests, ARM provider validation, asset-free public VPK build. Diagnostic
Vita3K reached original Score then `R_L01.bik` Movie without the prior crash.
Evidence: `reports/DEV144_SCORE_DIALOG_AND_M13_INTRO.md` and matching
Vita3K capture/log bundles; no physical Vita verification.
Next: instrument camera host/HUD state at M13 intro start, fix the failing
original object/control boundary, then verify normal intro and Movie-to-M01.
Blocker: M13 cinematic camera is not visibly taking over; ordinary objectives
and full campaign continuity remain unverified.

## Dev142 active: original campaign intermission handoff candidate

Renegade Vita — v3.5 active
`[░░░░░░░░░░] 0/10 release acceptance gates complete`

Now: full-port mission success dispatches original CampaignManager Score/Movie
flow and carries its original saved state into a rebuilt next-level session.
Completed: 19 focused tests and asset-free ARM ELF/SELF/VPK build; Dev141
Vita3K confirmed M13 first render and bounded movement. See
`reports/DEV142_CAMPAIGN_INTERMISSION.md`.
Evidence: Dev142 VPK SHA-256
`52927e6cf8f521ad025b2921343ddc2f0c678e88f2817a55eb8228694b24520e`.
Next: bounded diagnostic completion in Vita3K, then ordinary M13 objectives
and M01 continuity. Blocker: new intermission path has no runtime proof yet.

## Dev141 active: campaign Movie owner retained

Renegade Vita — v3.5 active
`[░░░░░░░░░░] 0/10 release acceptance gates complete`

Now: original Movie mode survives full-port mission selection so the original
campaign intermission lookup can find it. Demo mode lifetime is unchanged.
Completed: 18 focused tests and full-port ARM ELF/SELF/VPK build. See
`reports/DEV141_MOVIE_MODE_LIFETIME.md`.
Evidence: asset-free Dev141 VPK SHA-256
`a59090105b74fb7c1d4c7e5bf16f2af558dcbbd547144f5e25c0b9565bb9bb8f`.
Next: Vita3K M13 startup retest, then original Combat-to-Score/Movie/M01
session handoff.
Blocker: completion is still consumed as direct-runtime exit; no normal
campaign transition evidence.

## Dev140 active: M01 direct-entry gameplay evidence

Renegade Vita — v3.5 active
`[░░░░░░░░░░] 0/10 release acceptance gates complete`

Now: M01 can be launched through a build-gated, one-shot diagnostic request;
the public full-port build keeps that route off. M01 retains original lazy
texture loading instead of running M00's eager prewarm.
Completed: 18 focused checks, ARM ELF/SELF/VPK; diagnostic Vita3K M01 load,
first render, player movement, and pistol fire. See
`reports/DEV140_M01_DIRECT_ENTRY.md`.
Evidence: managed AppData `campaign-dev140-m01-diagnostic-trial-2/`; M01
objectives and normal transition remain unverified. The narrowed public M13
build has not passed a complete runtime retest after a transient preflight
archive failure.
Next: establish narrowed-build M13 startup, then implement the original
Combat -> Score -> Movie -> M01 session handoff.
Blocker: direct runtime still consumes mission completion as exit.

## Dev139 active: original score-screen owner

Renegade Vita — v3.5 active
`[░░░░░░░░░░] 0/10 release acceptance gates complete`

Now: the full-port profile links original score capture/dialog callbacks;
the demo profile is unchanged. Dev138 independently reached M13 gameplay in
Vita3K with 357 registered scripts and 31 active script instances.
Completed: Dev139 ARM ELF/SELF/VPK and symbol inspection. See
`reports/DEV139_ORIGINAL_SCORE_OWNER.md`.
Evidence: Dev138 bounded M13 Vita3K runtime; Dev139 bounded Vita3K frontend
startup and M13 selection only, plus ARM build and matching published VPK.
Next: retain original campaign state across M13 completion and execute
Combat -> Score -> Movie -> M01 without double teardown, then test on Vita3K.
Blocker: direct runtime currently consumes completion as an exit event.

## Dev137 active: original M13 script family

Renegade Vita — v3.5 active
`[░░░░░░░░░░] 0/10 release acceptance gates complete`

Now: original `MissionX0.cpp` is linked in the full-port profile. Its
`MX0_*` registrants are present in the ARM ELF; retail M13 references those
names. The demo profile keeps its prior script set.
Completed: deterministic zero-fuzz staging patch for nine MSVC callback
defaults, case-sensitive header alias, ARM ELF/SELF/VPK, and bounded Vita3K
M13 selection/load/first gameplay render. Script registrations increased
from Dev135's 37 to 68 and active instances from 12 to 31. See
`reports/DEV137_MX0_SCRIPT_CLOSURE.md`.
Evidence: `campaign-dev137-trial-1/` in managed AppData, runtime log,
window capture, and 300-second watchdog receipt. No objective completion,
transition, clean in-app exit, or physical Vita evidence.
Next: bring the remaining original campaign mission/shared script units
through their specific legacy C++ compatibility failures, then connect the
original completion -> score/movie -> next-level path and test M13 objectives.
Blocker: direct Vita simulation still observes completion and tears down;
it does not dispatch `CombatGameModeClass::Think` continuation.

## Dev136 active: campaign save handoff

Renegade Vita — v3.5 active
`[░░░░░░░░░░] 0/10 release acceptance gates complete`

Now: full-port post-teardown reload accepts a validated original single-player
save from any numbered campaign mission; demo reload remains M00-only.
Completed: 13 focused frontend checks and full-port ARM ELF/SELF/VPK build.
The host harness exposed all 36 actual retail campaign flow entries: M13,
then M01-M11, with original Score/Movie states and finale movie. See
`reports/DEV136_CAMPAIGN_SAVE_AND_FLOW.md` for the mission checklist.
Evidence: Dev136 VPK SHA-256
`2e770738b23ba0e5d4b00b8ee6c2126025f8f02bb8c1e1403d13ec8db4ec71dc`.
No Vita3K or physical save-reload trial yet. The catalog host run stopped at
an isolated frontend font probe, before the M13 simulation gate.
Next: route mission completion through the original CampaignManager states,
including score/movie callbacks, without midframe level teardown. Then test
M13 save/reload and the first M13-to-M01 transition.
Blocker: current Vita simulation observer exits on mission completion and
bypasses original `CombatGameModeClass::Think` campaign continuation.

## Dev135 active: first original campaign-map trial

Renegade Vita — v3.5 active
`[░░░░░░░░░░] 0/10 release acceptance gates complete`

Now: Dev135 full-port profile selects original Single Player -> Soldier ->
`M13.mix` in Vita3K. Original M13 scene, desert player, HUD, movement,
pistol fire, audio, and EVA pause were observed in a bounded five-minute run.
Completed: mission MIX routing beyond tutorial, distinct `RNEGC3101`
campaign package, 152 focused checks, ARM ELF/SELF/VPK, and two M13 host
load/update/render cycles. Earlier M00 selection is retained as a failed
input trial, not campaign evidence. See `reports/DEV135_CAMPAIGN_TRIAL.md`.
Evidence: `build/vita-dev135-campaign/` and candidate-scoped
`campaign-dev135-trial-6/` under managed AppData. Vita3K runner ended on
watchdog, released inputs, and terminated only its owned process; clean
in-app exit and mission completion were not shown.
Next: trace original M13 objective/completion and mission transition ownership.
Source and asset-free Dev135 VPK are published to GitHub. No physical
deployment or acceptance; no demo source/profile changes in Dev135.
Blocker: physical Vita evidence and later campaign progression remain open.

User steering (2026-09-15): physical Vita tests are authorized after the next
milestone. Gate: Dev134 canonical host/sanitizer/ARM/package closure and matching
Vita3K visual regression. Then recheck target identity/reachability at
10.0.0.202:1337, preserve installed matching artifacts, and conduct bounded physical
tests with frame-time evidence. No device access before that milestone. This
supersedes the earlier indefinite physical hold; emulator FPS remains irrelevant.

## Dev134 active: discarded character RGB work

Renegade Vita — v3.5 active
`[░░░░░░░░░░] 0/10 release acceptance gates complete`

Now: Dev134 canonical and matching visual milestone PASS. Physical executable
and VPK deployed/readback verified; user launch required (command1338 refused).
Completed: Dev133 native SELECT/SELECT/Cross reaches Load Delete, controller No
preserves every save, clean Exit. Return: build/dev133-discovery-return/ (56 files).
Evidence: Dev134 24 focused checks; production material/mesh ASan/UBSan; fixed
host submitted-skin median 164.5 -> 19.6 us, unchanged alpha and scratch storage.
Evidence: build/dev134-refinery-return/return-receipt.json (42 files), native
clean exit, all14 saves intact; physical deployment receipt at
build/device-evidence/dev134-deployment-20260915T024507Z/deployment.json.
Next: physical Dev134 boot/runtime log collection and native frame-time analysis.
Local follow-up: two prewarm 64-bit printf corrections pass strict ARM format
checking and eight loading-screen contracts; deployed Dev134 stays frozen.
Blocker: manual LiveArea launch; FTP available, remote control refuses connections.
The 300-second read-only monitor ended with no Dev134 log; receipt retained next
to deployment. No active monitor remains; resume collection after physical run.
No build/emulator/GDB. No native FPS gain claimed. Earlier entries are history.

## Dev133 active: repeated Load factory lifecycle

Renegade Vita — v3.5 active
`[░░░░░░░░░░] 0/10 release acceptance gates complete`

Now: Dev133 native runtime return retained at build/dev133-reload-return/
return-receipt.json (275 files). Four original reloads, Load Delete No/Yes,
SELECT input without capture, Help label and native clean Exit pass.
Artifacts frozen at build/dev133-closed-incremental/receipt.json (34 files).
Completed: Dev132 native IME cancel/accept/reopen, named original Save/Load,
overwrite No/Yes, Save Delete and native END clean. All 14 existing saves
unchanged; only disposable savegame03.sav removed from Dev132.
Evidence: build/dev132-keyboard-return/return-receipt.json, 168 files, 15 released
native input steps. Repeated Load FAIL confirmed by touch and Cross after reload.
Factory baseline FAIL on cycle two; corrected normal/UBSan PASS. SELECT gesture
and diagnostics/camera contracts PASS (5 focused checks).
Next: native Load list-to-Delete sequence and targeted original vehicle/building
discovery checkpoints, then FPS audit. Follow-up host focus passes both lifetimes:
SELECT from List reaches Back, Delete, Load, List. No production focus bug found.
Frozen Dev133 is running bounded Vita3K check Dev133-discovery-20260915-r2,
owned PID26488, 900-second watchdog. No GDB or build running.
Blocker: none locally. Physical testing held; native 60 FPS remains unproven.
Earlier entries below are historical.

## Dev132 active: native save-description keyboard

Renegade Vita — v3.5 active
`[░░░░░░░░░░] 0/10 release acceptance gates complete`

Now: Dev132 incremental ARM/ELF/SELF/VPK and identity PASS; matching artifacts
frozen in build/dev132-closed-incremental/receipt.json (30 files). Prepare
native IME cancel/accept and named Save/Load tests in Vita3K.
Completed: native-width and host-width session tests pass ASan/UBSan for text
bounds, malformed UTF16, cancellation, owner destruction, failed termination,
repeated entry and release-before-menu-input. Dev131 controller checks retained.
Evidence: build/dev132-text-entry-tests.log; 181 zero-fuzz staging patches pass.
Original host and retained UBSan regression pass two M00 cycles each.
All 151 focused checks PASS. Next: native keyboard cancel/
accept/reopen and named Save/Load checks. Cycle Objectives and populated vehicle/
building pages remain; hardware optimization audit follows menu correctness.
Blocker: none locally. Physical testing held; native FPS and release unaccepted.

Earlier entries below are historical.

## Dev131 active: controller confirmation focus

Renegade Vita — v3.5 active
`[░░░░░░░░░░] 0/10 release acceptance gates complete`

Now: Dev131 controller confirmation, Save/Delete and Exit regression passes in
the native ARM app under Vita3K. Continue native text-entry and populated pages.
Completed: Dev130 independently exercises all pause items. Map and both zooms,
statistics, Help, settings persistence, Save/Load/Delete and Exit pass functional
checks. Fresh Weapons and naturally discovered Mobius Characters show models
and descriptions. Both native runs end clean; no physical acceptance.
Evidence: build/dev130-fresh-return/return-receipt.json (200 files),
build/dev130-mobius-return/return-receipt.json (142 files). Long Mobius pause
did not reproduce the Dev129 hang; its root cause remains unresolved.
Evidence: Dev131 host baseline FAIL; corrected host and retained UBSan two-cycle
checks, 149 focused checks and incremental ARM/package closure PASS. Retained
runtime: build/dev131-controller-return/return-receipt.json. No preserves the
test save hash; Yes deletes only that save. Mobius discovery survives reload.
Native Exit Yes ends clean; owned emulator shell stops without force. Wrapper
reports null process exit separately and is not a zero-exit proof.
Next: native save-description entry, Cycle Objectives binding and representative
populated Vehicle/Building checks; then continue the hardware optimization audit.
Blocker: none for local work. Native save text entry and populated vehicle/
building checks remain. Physical testing held; native 60 FPS and full demo open.

Earlier entries below are historical.

## Dev130 active: fix independently reproduced pause failures

Renegade Vita — v3.5 active
`[░░░░░░░░░░] 0/10 release acceptance gates complete`

Now: Dev130 native ARM build and package identity pass. Independently repeat
every pause action, fresh discovery, settings persistence and save/load.
Completed: Dev129 exercised all seven tabs and every bottom action. Map, Data,
Help and all Options pages render; Save creates a structurally valid original
M00 save. Load is blank; Exit confirmation incomplete; old checkpoint has zero
discovery entries. Mobius START enters EVA during speech, resumes, then hangs
after frame 600. Clean exit, discovery models and save/load remain unaccepted.
Evidence: build/dev129-pause-return/return-receipt.json (101 files),
build/dev129-closed-incremental/receipt.json (30 matching artifact files).
Next: original settings callbacks and disk reload pass two host M00 cycles and
retained UBSan. Install this exact package into Vita3K and start fresh M00.
Blocker: none for local work. Physical testing held; hardware 60 FPS unproven.

Latest: Dev130 retained M00 UBSan, 149 focused checks and ARM package identity
pass (incremental, not canonical acceptance). Controlled Dev129 baseline stays responsive to frame
8160, narrowing the earlier hang to the longer menu sequence or an intermittent
fault. See build/dev129-mobius-debug-return/return-receipt.json. No hang fix or
clean-exit acceptance is claimed.

Earlier entries below are historical.

## Dev129 active: independent pause-menu audit

Renegade Vita — v3.5 active
`[░░░░░░░░░░] 0/10 release acceptance gates complete`

Now: Dev129 build and matching identities passed. Prepare bounded emulator
checks of every pause item, controller save/load, and START during Mobius speech.
Completed: matching Dev128 emulator return shows Map, statistics and objective
text, navigation to all seven tabs, and resumed Mobius gameplay. Four viewer
lists are empty. Bottom actions are disabled; touch conversion is incorrect.
Evidence: build/dev128-pause-return/return-receipt.json; 15 touch/frontend checks,
247 RC controls, 22 save/free-space cases and two M00 UBSan cycles with original
starting-weapon discovery and settings behavior pass. All 147 fast checks pass. See
DEV129_PAUSE_MENU_AUDIT.md for exact limits and remaining steps.
Next: automated all-page/button checks, then settings persistence corrections.
Physical testing remains held; no 60 FPS claim.
Blocker: none for local work.

Earlier work-unit entries below are historical.

## Dev128 active: remaining EVA pages and DDS residency

Renegade Vita — v3.5 active
`[░░░░░░░░░░] 0/10 release acceptance gates complete`

Now: latest user reports black Map, missing statistics text and other pause
items. Trace original MapMgr, player statistics, dialog resources and viewer
reveal data; validate each page in Vita3K after correction.
User reiterates hardware-only tuning: ARM/GXM/memory/CPU specifications govern
implementation. Vita3K is for functional smoke checks, never an FPS target.
The user requires independent checks of every tab and button, including
Help/Save/Load/Options, which the current source explicitly disables.
Completed: canonical Dev127 and matching identity passed. Initial emulator
run reached movies/menu/M00; second run opened EVA and visibly confirmed a
black Map. Developer checkpoint was disabled, so Mobius was not reached.
Evidence: build/dev127-initial-return/ and build/dev127-early-pause-return/.
Dev128 DDS chain source passes ASan/UBSan: 800 compressed layouts, 12 retained
surface chains and 8 production owner transactions. ARM integration is pending.
Confirmed: lazy map/marker dimensions and omitted RC visibility/alignment are
corrected. LLVM RC comparison passes all 116 controls. The unavailable-renderer
row loop is corrected with production sanitizer coverage. Retained M00 UBSan
passes two cycles with map readiness and statistics player identity checked.
Stronger debugging found the host map uses a 2x2 fallback because a serialized
DDS pointer expands on LP64. Positive dimensions alone are insufficient;
fixed-width host parsing and a stronger real-map check are next source work.
Next: Dev128 incremental native package and all identity checks passed, along
with 146 focused checks. Bounded checkpoint and all-tab/button checks are running
in Vita3K. Matching SELF: 3830e5e57191939e33e9eac6f98a607640bcd67c903258aa6d45f761d10d1df0.
Blocker: no local blocker. Physical testing remains held; 60 FPS is unproven.

Older entries below are historical.

## Dev127 expanded optimization work; physical testing still held

Renegade Vita — v3.5 active
`[░░░░░░░░░░] 0/10 release acceptance gates complete`

Now: user authorizes Vita3K for initial testing; physical testing stays held.
Canonical ARM build continues after host/UBSan gates. Six pinned native ports
are compared in DEV127_UPSTREAM_60FPS_COMPARISON.md; 60 FPS remains the target.
Completed: indexed mesh/generic equivalence covers 784,560 corners; pinned GXM
sink covers 540,000 more. Movie transfer/lifetime and sampler tests pass.
Evidence: build/dev127-indexed-final-tests.log; sampler-expanded-sanitizers.log.
New DXT-chain prototype compares 9,762,188 blocks in 800 cases with the pinned
swizzler, plus invalid/allocation-failure cases. It is not integrated yet.
Next: close current artifacts, back up/install only the emulator title, bounded
startup/movie/menu test; continue transactional DDS writable fallback work.
Blocker: no local blocker; native FPS and visual acceptance remain unmeasured.

Older work-in-progress entries below are superseded by this expanded scope.

## Dev127 fixes and pre-hardware FPS audit

Renegade Vita — v3.5 active
`[░░░░░░░░░░] 0/10 release acceptance gates complete`

Now: final canonical Dev127 retry with frozen code, updated dependency and staging;
no deployment. Local optimization route ledger: DEV127_OPTIMIZATION_AUDIT.md.
Completed: bounded MPEG playback/metadata, original encyclopedia lifecycle,
native tutorial caption IDs, deferred movie colour conversion, aligned alternating
audio output with lifetime drain, checked renderer reuse and native clock policy.
Evidence: DEV127_FIX_AND_OPTIMIZATION_PLAN.md; production audio lifetime/ring,
material equivalence, sampler and indexed preparation tests pass with sanitizers.
FFmpeg speed dependency built with final -O3/NEON; compact vitaGL vertex layout
passes baseline/patched production emit/draw tests and ARM dependency build.
Two-minute MPEG test passes ASan/UBSan; native duration math uses 64-bit multiply.
Initial canonical host/ARM link passed, but the shell wrapper stopped because its
script was edited while running. Syntax verified; final stable-script retry reuses
the candidate build directory and reruns all gates. No intermediate deployment.
Next: close canonical artifact identity, warnings and optimization ledger.
Blocker: no local blocker; audible output, native timings and whole-demo progress
remain unaccepted. User requires this audit before another physical test.

## Dev126 physical Mobius/START crash and playability failure

Renegade Vita — v3.5 active
`[░░░░░░░░░░] 0/10 release acceptance gates complete`

Now: symbolicate retained physical START/EVA crash; then measured movie/game
performance, ladder keyboard hint and missing EVA datalinks.
Completed: matching installed SELF, runtime log and new crash dump pulled.
Evidence: dev126-logan-20260914T203526Z/mobius-crash/receipt.json.
Gameplay late-run average 13.1 FPS; render ~59.7 ms, simulation ~16.5 ms.
Mapped main-thread exception PC reaches newlib _kill_r; caller diagnosis pending.
Movie conversion/receive and decode-send dominate; hardware audio API submitted
buffers without recorded errors, but user reports silence (audibility failed).
Next: identify abort caller from matching dump; fix narrow demonstrated defects.
Blocker: none for local diagnosis; native physical acceptance remains failed.

## Physical Logan progression failure — Dev126 investigation

Renegade Vita — v3.5 active
`[░░░░░░░░░░] 0/10 release acceptance gates complete`

Now: Dev126 physical movie failure reported: under 5 FPS and no intro audio.
Timing/audio return pending; read-only FTP monitor running. Logan gate remains open.
Completed: Dev124 physical logs retrieved; controls disabled at frame 1578,
still disabled at frame 2160 with simulation advancing. Prior POKE conversation
finished at 1342. Course-exterior authored waypath 400074 is the suspected wait.
Evidence: build/device-evidence/dev124-boot-20260914T202219Z/return-203104.json.
Movie log confirms four uploads followed by at least 180 consecutive drops.
Dev125 movie fix and 135 package checks passed; superseded before deployment.
Dev126: 135 focused checks, ARM/ELF/SELF/VPK closure, identity and deployment
readback pass; prior Dev124 executable backed up. No retail mutation.
Next: user launches same dev79 bubble, repeats gate, waits 20 seconds if locked,
then returns to FTP for a35-dev126-runtime.log retrieval.
Blocker: remote launch unavailable; user physical replay needed for path state.

## Physical intros reached; movie starvation correction building

Renegade Vita — v3.5 active
`[░░░░░░░░░░] 0/10 release acceptance gates complete`

Now: Dev125 movie presentation-progress correction and decode/draw timing.
Completed: Dev124 physically reaches intros; user reports less than 1 FPS.
Production scheduler reproduces 120 consecutive drops; guard and 19 focused
checks pass with ASan/UBSan. ARM movie unit compiles; package building.
Evidence: DEV125_PHYSICAL_MOVIE_PROGRESS.md; Dev124 physical observation record.
Next: collect Dev124 baseline when FTP returns, close Dev125 package, hardware A/B.
Blocker: physical timing log pending; no performance improvement claimed yet.

## Physical recovery complete

Renegade Vita — v3.5 active
`[░░░░░░░░░░] 0/10 release acceptance gates complete`

Now: native pre-main/bootstrap diagnosis; Dev123 rejected physical candidate.
Completed: failed executable retained; predecessor restored with matching hash.
Evidence: recovery-20260914T201913Z receipt under Dev123 physical evidence root;
no new runtime log or recent dump in checked directories. Nothing relaunched.
Next: inspect early native startup against matching artifacts.
Blocker: failure occurs before established runtime evidence; exact cause unknown.

## Dev123 physical failure — recovery required

Renegade Vita — v3.5 active
`[░░░░░░░░░░] 0/10 release acceptance gates complete`

Now: recover user's unresponsive Vita after Dev123 black-screen launch.
Completed: failed candidate recorded; matching installed backup preserved.
Evidence: user physical observation; both remote ports refuse connections.
Next: user power recovery/FTP, evidence retrieval, exact executable restoration.
Blocker: device unavailable; no physical log/dump or root cause yet.

## Physical full-demo test authorized

Renegade Vita — v3.5 active
`[░░░░░░░░░░] 0/10 release acceptance gates complete`

Now: Dev123 deployed and ready for user's complete physical demo test.
Completed: installed backup; SELF/VPK/font readback hashes match; normal startup
config verified; retail M00 hash matches baseline. 134 local checks passed.
Evidence: build/device-evidence/dev123-full-demo-20260914T201320Z/deployment.json.
Next: user LiveArea launch, full Tutorial, then physical log retrieval.
Blocker: command port 1338 unavailable; launch requires user's Vita controls.
User lifts PS Vita/full-playthrough hold. PSTV testing remains unrequested.

## Connection recovery — Dev123

Renegade Vita — v3.5 active
`[░░░░░░░░░░] 0/10 release acceptance gates complete`

Now: Dev123 capture-regression recovery evidenced; remaining visual work next.
Completed: froze Dev122 failure, reverified Dev121 rollback, same-save Vulkan
control reaches visible Weapons Factory gameplay; nine focused checks pass.
Evidence: DEV123_CAPTURE_REGRESSION_RECOVERY.md and its hashed runtime returns.
Dev123: 134 focused checks and artifact closure pass; same-save Hotwire
gameplay and Vulkan screenshot observed. Runtime ended at watchdog; F12
released. Retained build/dev123-recovery-return/; no clean-exit claim.
Next: credits atlas/layout, matched-camera world defects, repeated lifecycle.
Blocker: native capture/visual issues; final playthrough and physical hold.

## Active resume — 2026-09-14

Renegade Vita — v3.5 active
`[░░░░░░░░░░] 0/10 release acceptance gates complete`

Now: Dev121 presented-frame readback validation, runtime runner 39946.
Completed: 134 focused checks; ARM/ELF/SELF/VPK closure and emulator setup with
Dev120 backup. Pinned Vita3K override fixed; actual Vulkan F12 captures work.
Evidence: build/dev120-vulkan-return/ and reports/DEV121_CAPTURE_SOURCE.md.
Next: compare game-owned front-buffer readback with emulator framebuffer;
continue matching-camera wall/sky/elevator and credits investigation.
Blocker: final playthrough held for known issues; physical tests held.

Renegade Vita — v3.5 active
`[░░░░░░░░░░] 0/10 release acceptance gates complete`

Now: wall/sky/elevator rendering and reliable framebuffer capture.
Completed: Dev120 ARM/package closure; original loading bar visibly fills.
Evidence: 133 focused checks, matching Dev120 runtime; wall image retained at
build/dev120-wall-return/. r4 ended at watchdog; native PNG all black.
Next: r5 verifies corrected backend override and native Select capture input.
Blocker: known visual defects; final user playthrough and physical tests held.
Earlier building/running statements below are historical.

Renegade Vita — v3.5 active
`[░░░░░░░░░░] 0/10 release acceptance gates complete`

Now: Dev120 engineering batch for original loading animation and menu music.
Completed: removed duplicate progress overlay; fixed original animation-name
varargs; added MP3 decoding below original WWAudio ownership. Dev119 returned
to the original menu after ending; credits body cutoff remains open.
Evidence: 133 focused checks; host decode of unchanged menu.mp3 returns
4,082,688 stereo frames at 44,100 Hz, 16,330,752 PCM bytes, nonzero audio.
Next: finish ARM package closure, then visible original loading-bar and menu
playback checks. Continue sky/elevator/credits/repeated-lifecycle corrections.
Blocker: final user playthrough held until known issues fixed; physical hold.
Details: DEV120_ORIGINAL_LOADING_AND_MENU_AUDIO.md.

Now: Dev119 original menu return, credits presentation and actual loading fill
bar, then final user-controlled full tutorial capture/profiling run.
Completed: Dev118 Power Plant reload, Maus/finale progression, original success
at frame 4200, visible thanks/credits and clean native teardown in Vita3K.
Evidence: build/dev118-finale-return/. Physical release gates unchanged.
Next: complete focused Dev119 changes, test lifecycle/replay, batch package and
capture setup. See DEV119_ENDING_AND_FINAL_RUN.md.

Renegade Vita — v3.5 active
`[░░░░░░░░░░] 0/10 release acceptance gates complete`

Now: Dev118 package ready for original NPC movement/finale test.
Completed: restored omitted original per-frame path-resolution service.
Evidence: 18 targeted checks, 130 package contracts, ARM/SELF/VPK identity pass;
Dev117 advancing but locked finale retained at build/dev117-finale-stall/.
Next: Power Plant reload/finale observation; user authorizes proceeding without replies.
Blocker: runtime traversal unverified; physical access remains held.
See DEV118_NPC_PATH_SERVICE.md. No full-M00 or visual acceptance claim.

Power Plant checkpoint archived and structurally validated as
m00-powerplant-dev117. Latest native statuses 1/1/1/1/1/3; reload and full M00
remain unproven. Previous saves preserved, shortcut released, user retains
navigation in recovery r2. Evidence: build/dev117-powerplant-checkpoint/.

Refinery checkpoint retained: user-reported Logan objective completion, native
statuses 1/1/1/1/3/3, active Mobius Refinery conversation. Original save passes
strict archival validation at build/tutorial-checkpoints/m00-refinery-dev117;
reload pending. Prior saves preserved, shortcut released, user session remains
running. No new release gate or full-M00 completion claim.

Hang return: retained stalled Dev117 runtime, screenshot and bounded host thread
stacks after WF/tank progression and Refinery handoff. Cause unconfirmed.
At user request, stopped frozen PID and launched same-package Hotwire reload.
Debugger-enabled r1 stalled before native startup; r2 uses ordinary settings.
Original Hotwire reload now passes with saved player/camera and advancing
frames; user owns navigation in PID 17392, recovery r2.
release gates unchanged. See DEV117_REFINERY_HANG.md.

Latest return: user reports sky/elevator artifacts and objective text squares.
Hotwire/WF checkpoint archived and save shortcut released. Both original
objective-message varargs paths corrected; executable formatting regression,
zero-fuzz staging and objectives ARM compilation pass. Visual acceptance still
pending; sky/elevator causes unconfirmed. See DEV118_VISUAL_DEFECTS.md.

Crash recovery: existing Dev117 Windows process identity and immutable Mobius
checkpoint hash verified. Dev118 tutorial hints recovered; 19 focused tests
and zero-fuzz staging retained, affected scriptcommands/weaponview ARM objects
compiled successfully in the existing fast tree. No package/install/input;
user retains navigation. Evidence: DEV118_PENDING_BATCH.md. Gate count unchanged.

Renegade Vita — v3.5 active
`[░░░░░░░░░░] 0/10 release acceptance gates complete`

Now: user controls gameplay in Dev117-progression-20260914-r1; automated
navigation stopped and development input disabled. Agent handles checkpoints
and the next coherent source/diagnostic batch. No new build.
Completed: rifle animation varargs correction, retired synthetic reload motion,
black EVA margins, latched renderer diagnostic guards, Targa header ABI fix,
and separate historical load evidence from teardown ownership. Focused tests,
two original M00 ASan cycles and ARM/SELF/VPK identity checks pass.
No canonical pipeline retry; the closure retry compiled zero objects.
Evidence: DEV117_WEAPON_EVA_CORRECTIONS.md; fixed-save Dev116 baseline has
240 samples: median 16.59 ms, p95 17.87 ms, p99 29.27 ms (Vita3K only).
Completed: matching replay clean native teardown; rifle pose/reload, black EVA
margins and resumed gameplay visible. Same package used for both runtime tests.
Completed: user-reported Mobius position archived through original quicksave;
structure validates, reload pending. 23 checkpoint/diagnostic tests pass.
Pending source batch and user-session details: DEV118_PENDING_BATCH.md.
Next: batch bounded reload diagnostics with moving/firing performance work and
original M00 progression. Do not package another isolated diagnostic change.
Blocker: full M00/ending unproven; physical Vita/PSTV testing remains held.
This current entry supersedes historical current-candidate and pause statements.

## Current: Dev113 checkpoint restoration follow-up

`[███░░░░░░░] 3/10 evidence gates complete`

Now: prove saved-player restoration after asserting mission mode at the original
checkpoint load seam; completion ending is explicitly M00-map gated.
Completed: dev113 canonical package and fresh M00 runtime; intro/menu/loading
text and gameplay reached; native pause/resume input returns to gameplay; focused
frontend and mission contracts pass.
Evidence: `build/dev113-host-evidence/canonical-rewind-retry.log`,
`D:/Vita3K/RenegadeEvidence/Dev113-Fresh-20260909T052123Z/`.
Next: canonicalize the checkpoint and M00-ending guards, reload the saved tutorial
state, then repair EVA presentation and prove M00 completion fade/credits.
Blocker: checkpoint reload and full M00 completion remain unproven; physical
access remains held. HUD correctness, elevator visuals and 60 FPS remain open.

## Historical dev111 progress, superseded above

`[..........] 0/10 full demo release acceptance gates complete`

Now: canonical r7 PASS; Dev111 running M00 in Vita3K, PID 100, runner 76938.
Completed: ARM/SELF/VPK identity and archive/hash checks. Same-directory retry
had 521 direct hits from 521 cacheable calls. Four directory-admission tests
pass; the separate debug-prefix-map experiment remains unintegrated.
Completed: report inventory and canonical checks now derive source identities
from manifests rather than fixed totals; seven inventory tests pass. The r4
attempt passed 153 contracts before its obsolete count gate. Same production
sampler replay preserves E61BC335 while reducing parameter writes 4800 to 2412.
Evidence: current source identity check returns 516 original, one extracted
owner, 26 native and six frontend units. These counts are outputs, not gates.
Retry reuses the hashed completed r3 host runtime log and reruns current
contracts. r5 passed 155 grouped and three post-staging tests. Fresh retail
reconciliation matches all 51 source files and validates 31 archive indexes;
53 installed files include the retained extras. Installed Vita3K is 4093,
not the 4074 executable associated with the earlier Windows crash.
Canonical package published under dist/. Matching VPK SHA256 begins
0b1b5da54a78b0c3; SELF begins 5ea7ae2151531e81. Full hashes are in BUILD_STATE
and the identity report. New visual/FPS acceptance remains pending.
Returned: EA logo and orange following intro visible; main/SP labels visible;
loading status/90 percent visible; gameplay reached. Original quicksaveA.sav
created and archived unchanged as initial-spawn checkpoint; reload unproven.
Health digits remain malformed. Observed initial-spawn timing is roughly
28-34 FPS, not a controlled before/after benchmark. Left-stick input moved the
original player from (-58.328,-41.527,0.588) to (-56.281,-34.801,-0.159).
Next: normal tutorial progression, further HUD/loading evidence, checkpoint
reload and original pause lifecycle. The checkpoint hook draft remains unapplied.
User lifted build/test hold; physical hold remains. Three read-only agents have
finished. Experimental files stay outside the candidate. Older hold entries
below are historical and must not block authorized validation.


## Latest: original EVA source selection

`[..........] 0/10 full demo release acceptance gates complete`

Completed in source: nine original EVA/tab/viewer units selected; native
dependency boundaries and 64-bit-safe viewer entry indices registered.
Evidence: applied source changes only, not staging/compile/link success.
Next: original pause factory, retained UI/input lifetime and safe resume/exit.
The pause route is not activated yet. No build/test or physical authorization
has changed. See M00_PAUSE_OWNER_DEPENDENCIES.md.


## Latest: original pause dependency preparation

`[..........] 0/10 full demo release acceptance gates complete`

Completed in source: demo Campaign/Load submenu controls stay visible but
disabled, including direct command gating; original EVA abandon-game path
guards absent WOL/LAN modes. EVA is not yet selected or operational.
Evidence: original source trace and registered patches only, no execution.
Next: original EVA/tab selection and correct pause UI/input/Combat lifecycle.
Build/test and physical holds remain. See M00_PAUSE_OWNER_DEPENDENCIES.md.


## Latest: M00 loading handoff and demo menu source batch

`[..........] 0/10 full demo release acceptance gates complete`

Now: user-reported loading presentation, pause crash and M00 preparation gaps.
Completed in source: hidden 60-frame scene warmup, independent loading clock,
final progress reserved for preparation, bounded original texture Init sweep,
visible-but-disabled main-menu options and disabled-control interaction guards.
Evidence: source paths and applied edits only; no builds, tests or new runtime.
Next: original pause dialog lifecycle/factory restoration and secondary menu
restrictions; later consolidated validation after user lifts the hold.
Blocker: pause crash cause remains unproven; physical hold unchanged.
See M00_LOADING_MENU_READINESS_BATCH.md. This entry supersedes the prior pause
at the validation boundary because the user supplied new concrete source work.


## Current consolidated optimization status

`[..........] 0/10 full demo release acceptance gates complete`

Current source batch is ready for consolidated review/validation; user build/test
hold remains. Approval requested for one consolidated build and host/Vita3K cycle,
not physical testing. No new source changes should be invented merely to extend
the pass. The implementation milestone is not full optimization or demo release.

Now: source-first optimization; explicit build/test and physical-device holds.
Completed in source: renderer work reuse, DDS block/palette preparation, FreeType
reuse, dynamic/skin buffer growth, audio decode preparation and resource cleanup.
Evidence: applied source/registered patches, not staging, builds or runtime gains.
Timer investigation found constant frequency plus one monotonic read; retain it.
Next: remaining presentation/submission source work, then measurements only after
the hold is lifted. Dev110 installed binary does not contain this source batch.
Blocker: none for source work; full M00/save/load/ending and visual gates stay open.


## Current: substantial performance batch; existing Dev110 installed

`[..........] 0/10 full demo release acceptance gates complete`

Now: source-only work on redundant renderer computation and sampler churn.
User direction: source optimizations first, measurements afterward; no Dev110
tests or further builds/tests during this pass. Added fused indexed bounds and
checksum preparation as mode bit 8, retaining original safety checks and hash
ordering. Selector now hexadecimal 0..F. No new runtime evidence.
Third batch component: opt-in direct original text-atlas upload avoids creating
an empty texture before copying the finished glyph atlas; modes 0..7 provide
individual and combined comparisons. Registered staging patch, not yet built.
Completed: existing Dev110 installer returned INSTALLED_NOT_LAUNCHED. Added
opt-in bounded material-color and texture-object sampler reuse for same-build
A/B comparison, not yet compiled or measured; see RENDER_WORK_REUSE_BATCH.md.
Evidence: native source trace and retained Dev109 counters, not FPS acceptance.
Next: consolidate substantial submission/save-resume work before another build.
Blocker: none for source work. Physical hold and no-small-build rule unchanged.


## Latest: Dev110 correctness batch integrated; fast build running

`[..........] 0/10 full demo release acceptance gates complete`

Stopped superseded Dev109 canonical explicitly, retaining partial evidence;
Dev108 remains last canonical success. Applied original quicksave dispatch,
font atlas format conversion, Render2D texture readiness and bounded loading
animation diagnostics. Fast Dev110 build launched. No retail files changed.
Next: matching fast package, real original save/load, HUD and loading evidence.
No M00 completion, 60 FPS+ or physical acceptance claim.


## Latest: Dev109 reached M00; Start abort prevented input automation

`[..........] 0/10 full demo release acceptance gates complete`

Matching runtime initialized the native channel, then reported Start during
the intro and disabled the channel by policy. The pending sender timed out
without sending a command. M00 basic movement is visible; HUD/glyph artifacts
remain. User-input ownership clarification is pending without interrupting play.
Dev109 canonical build is running in the background; no physical access.


## Latest: Dev109 fast package passed and emulator installation completed

`[..........] 0/10 full demo release acceptance gates complete`

Fast ARM/ELF/SELF/VPK identity and hash gates passed. Existing retail-checking
installer returned INSTALLED_NOT_LAUNCHED with a candidate-scoped backup receipt.
Requested a hash-bound 1800-second Vita3K run and first native Cross command;
acceptance/release and original UI response are not yet established. No physical
access. Canonical Dev108 closure remains distinct from Dev109 fast evidence.


## Latest: Dev108 canonical BUILD SUCCESS; Dev109 input build launched

`[..........] 0/10 full demo release acceptance gates complete`

Canonical r3 completed with final artifact hash checks. Integrated the opt-in
native input channel at DirectInput and launched Dev109 fast build in the
background. No proven menu action, original checkpoint/load, entire M00 ending
or physical acceptance yet. Next: matching Dev109 build and emulator evidence.


## 2026-09-09 UTC: 147-patch preflight/staging passed; background input prepared

`[..........] 0/10 full demo release acceptance gates complete`

Canonical r3 passed whitespace-independent preflight and staging identity;
host compilation continues. Prepared opt-in native controller input and local
sender without modifying compiling sources. Not integrated or tested yet;
next work unit wires it below original DirectInput and proves menu/save actions.
No emulator fork, physical access, FPS benchmark or full-demo completion claim.

## 2026-09-09 UTC: whitespace-independent patch-command parsing

`[..........] 0/10 full demo release acceptance gates complete`

User authorized the durable fix: parse shell arguments rather than indentation
or physical line layout. Required zero-fuzz flags, paths, uniqueness and identity
checks remain strict. Canonical retry is next; runtime/demo gates remain open.

## 2026-09-09 UTC: persistent demo goal and ordered execution gates

`[..........] 0/10 full demo release acceptance gates complete`

Persistent goal active; exact next gates are in DEMO_EXECUTION_PLAN.md.
Canonical r2 stopped at early preflight, not after compilation: the new parser
rejects 11 indented commands (136 matched / 147 references). Coordinator
disclosed the introduced bug and requested permission for the narrow whitespace
correction. Native fast/sanitizer evidence remains retained. Background input,
original save/load, entire M00 and safe ending remain open; no physical access.

## 2026-09-09 UTC: eliminate recurring patch-count drift

`[..........] 0/10 full demo release acceptance gates complete`

Removed independent report/build count constants rather than incrementing them.
The ordered staging commands now drive a shared identity inventory; both builds
preflight before expensive work. Successful staging records patch identities,
fast reuse requires a matching receipt, and integration checks exact identities
and order. See PATCH_INVENTORY_CONTRACT.md. Canonical retry pending; native
Dev108 behavior, runtime blockers and physical-test hold are unchanged.

## 2026-09-09 UTC: Dev108 dialog ABI and original checkpoint input

`[..........] 0/10 full demo release acceptance gates complete`

Dev107 ASan/leak M00 cycles passed; UBSan menu text failed on remaining libc
UTF-16 parser searches. Dev108 uses existing UTF-16 helpers and adds bounded
focus-free QuickSave chord support to the emulator helper. Dev106 prior run
reached 70,800 frames then runner timeout, not M00 completion; no save exists.
Dev108 fast ARM/package passed; canonical ASan/leak and targeted UBSan
M00/M01/City checks passed. Integration report then rejected 147 patches against
stale expected 145. Coordinator disclosed the missed inventory update and asked
whether to correct it. Background input remains unreliable at difficulty
selection; cursor movement is visible but button activation/save is not proven.
Next: inventory correction with user direction, canonical closure, real save/load.
No physical access or release claim. 60 FPS+ remains the target.

## 2026-09-08: Dev107 host UTF-16/save fix; Dev106 startup failure retained

`[..........] 0/10 full demo release acceptance gates complete`

Dev105 returned 20,175 gameplay frames, clean Start teardown, no M00 completion.
Dev106 canonical failed in host menu text validation: ASan wcslen consumed
16-bit engine text with the host wide ABI. Dev107 uses existing UTF-16 helpers
and adds the original user/save bootstrap directory without removing user/saves.
The emulator directory is created, but no actual checkpoint is proven.
Dev106 first runtime failed before frontend: Always2.dat opened, then stat/read
returned 0x80010051; three other archives passed. Root cause remains unresolved.
Same installed SELF retry (Dev106-probes-retry-20260908T230209Z) reached the
M00 jump segment; focus-free captures show loading text/percentage and gameplay.
Initial 100-second retry log has 28 missing/error entries versus the uncontrolled
Dev105 sample of 1340/60 seconds. Different content/time windows and concurrent
host build preclude a controlled performance claim. Dev107 canonical continues
in background; preserve active gameplay and establish a real original checkpoint.
First-run archive-handle failure remains unresolved. No physical access;
60 FPS+ remains the target.

## 2026-09-08: Playable Dev105 M00 return; Dev106 native probe-cost fix

`[..........] 0/10 full demo release acceptance gates complete`

Updated Vita3K now shows Dev105 M00 with readable HUD and Logan targeting.
User reports continuous missing-file errors during gameplay. Dev106 removes
redundant native file probes after confirmed read-only misses, preserving
original fallback, forced checks and writable behavior. Host and fast ARM/package
closure passed (22 filesystem, 126 fast and 11 DDS checks); canonical is running
in the background. No measured FPS gain or full tutorial completion claimed. Keep the user's
current Dev105 run intact while building. Physical hold unchanged.

## 2026-09-08: Retail source coverage repaired; original runtime reads proven

`[..........] 0/10 full demo release acceptance gates complete`

Dev105 fast passed 126 contracts and ARM/package closure. All 51 current Steam
Data files now match emulator hashes; two extras are preserved and all 31
archive indexes passed structural checks. Added missing THU files, repaired
the stale host link and native loose Data search route. Exact Dev105 startup
successfully read both loose configs and hd_reticle.dds through original MIX.
Full texture/HUD rendering and one malformed W3D-name request remain separate
runtime questions. User updated Vita3K; same SELF retry is running under its
new executable hash. See DEV105_RETAIL_DATA_RETURN.md. Physical hold unchanged.

## 2026-09-08: Dev105 first-frame correction; retail identity audit

`[..........] 0/10 full demo release acceptance gates complete`

Dev104 fast passed and matching emulator readback/prewarm progressed beyond
Dev102's crash location. The new return is native controlled failure on a NULL
shadow-target probe, not a repeated host access violation. Dev105 separates
allocation fallback from draw rejection and preserves restored player/camera.
Exact reticle DDS is present in installed always.dat; full E: Steam versus
emulator Data SHA-256 comparison is pending. Next: build and first gameplay
frame, then original checkpoints. No physical tests or full-demo acceptance.

## 2026-09-08: Dev104 native readback and original checkpoint support

`[..........] 0/10 full demo release acceptance gates complete`

Dev103 fast build passed. Focus-free emulator input reached original Tutorial
and loaded M00 through post-load finalization, then the emulator crashed before
the diagnostic capture returned. Dev104 corrects the CPU-buffer readback API
contract and restores original save-root, quicksave and selected-save loading
paths. A local immutable checkpoint vault is implemented; no gameplay checkpoint
or cross-build load is yet proven. Details: `DEV104_READBACK_AND_CHECKPOINTS.md`.
Next: build and matching route evidence. No physical tests or emulator fork.

## 2026-09-08: Resumed tutorial work; Dev103 cursor clamp integrated

`[..........] 0/10 full demo release acceptance gates complete`

Dev102 canonical log reports successful package/hash closure; its enclosing
exec session later returned 143, so preserve the log/runner distinction.
Previous Vita3K run reached its 600-second deadline at the menu, not mission
completion. Dev103 now registers the cursor-only clamp as patch 146. Resume
bounded M00 progression using installed Dev102 while Dev103 builds separately.
Foreground activation is improved without relaxing the no-input-to-other-app
guard. No physical access or full M00/60 FPS+ acceptance claimed.

## 2026-09-08: Minor cursor-edge artifact reported

User reports a vertical sliver to the right of the menu cursor. Original cursor
draws full-range UVs without edge clamping; a Vita-only cursor U/V clamp proposal
is retained in `DEV103_CURSOR_CLAMP.patch`, with scope in `DEV103_CURSOR_CLAMP.md`.
It is not yet integrated or tested. Keep the compiling Dev102 source/patch
snapshot intact, then include the fix in the next coherent candidate. Do not
delay authentic M00 progression for a cosmetic-only rebuild. No gate count or
physical acceptance changes.

## 2026-09-08: Dev102 visible menu labels and orange intro captured

`[..........] 0/10 full demo release acceptance gates complete`

Fast ARM/package closure passed 126 tests. Matching Vita3K captures now show
all six original menu labels and orange/red Renegade intro colors. EA_WW uploads
195 frames rather than Dev101's one, but complete visual/audio pacing remains
open. Canonical build continues in the background; no hardware access.
Next: tutorial entry, loading/HUD and complete M00. Windows refused automated
keyboard focus, so no input was sent; user asked to click the game window once.
Exact evidence: `DEV102_VITA3K_PRESENTATION_RETURN.md`. This supersedes the
restaged-retry state below, not frozen physical evidence or the full-port goal.

## 2026-09-08: Dev102 presentation fixes; restaged build retry

`[..........] 0/10 demo release acceptance gates complete`

Now: retry Dev102 fast build with deterministic restaging, then canonical in
the background. Completed: source-level cause for skipped original sentence
rendering identified; first-movie cold-draw lateness isolated; native readiness,
first-draw clock/audio gate, and RGBA upload implemented. Evidence: Dev101
fast/canonical closure plus matching failed Vita3K run and user observations;
Dev102 first compile failed against stale generated declarations. No new visual
gate closes. Next: exact-package emulator presentation, then full authentic M00.
Blocker: physical acceptance remains held; no complete-route/60 FPS+ proof.

ETA correction: unsupported days estimate withdrawn. Target a usable M00 alpha
this working session, not 48 hours; next concrete result within 30 minutes.
Presentation and tutorial completion take priority over optional optimization.
Public release acceptance on PS Vita and PSTV remains separate and held.
The complete native port remains the durable end-goal. Details:
`DEV102_PRESENTATION_AND_DEMO_PLAN.md`. Older entries below are history.

## 2026-09-08: Dev100 closed; Dev101 selectable demo profile and user-font fix

`[..........] 0/10 demo release acceptance gates complete`

Durable goal: complete native Renegade Vita port; M00 is an interim showcase.
Dev100 canonical closure passed 148 current contracts and ARM/package gates,
using retained host semantic evidence. A separate hash-bound fast-package
Vita3K run exposed a controlled StyleMgr failure: Arial-based glyphs had zero
width because expected font files were absent. A loading-window screenshot
is not a menu pass. No physical access or full M00/60 FPS claim.

Dev101 source now separates demo-only launch/ending policy behind a selectable
profile, identifies the Renegade Vita project in credits, and adds bounded
user-font fallback through original FileFactory/FreeType ownership. Local
Windows Arial is staged only in the emulator user namespace with provenance;
retail remains unchanged. Fast/canonical builds run in the background while
matching emulator preparation continues. Details and hashes:
`DEV101_FONT_AND_DEMO_PROFILE.md`. Non-demo ARM closure remains open.

Next: exact Dev101 package closure, bounded emulator intro/menu observation,
then authentic route progression. Both PS Vita and PSTV final gates remain
held and unaccepted. Entries below are historical work-unit updates.

## 2026-09-08: Dev100 M00-only demo; local work continues

Latest: user reaffirmed the complete native port as the durable goal; M00 is
an interim community showcase, not the endpoint. Routine corrections are
delegated. The remaining M01 cache check is removed, fast closure passed, and
canonical ARM compilation is running while Windows Vita3K preparation proceeds.
The PID-owned Windows runner is now implemented; no physical access occurred.
Next source unit will separate demo-only policy from the full-port build.
The older compile-blocker update below is retained as attempt history.

`[..........] 0/10 demo release acceptance gates complete`

Now: ARM build blocked by one remaining M01 cache-health reference; no build
is running. Completed locally: prior-work causal audit; sampler, BINK scheduler
and performance-ledger regressions; pinned no-splash VitaGL dependency build;
123 fast-build contracts; executable demo-ending policy; both real retail
intro host decodes. Evidence: `build/dev100-host-evidence/` and
`DEV100_PRIOR_WORK_AUDIT.md`. No physical access or acceptance claim.

The ten release gates are: both intro movies paced; original menu text and
tutorial entry; loading text/progress; gameplay text/HUD; NPC target alignment;
entire authentic M00 progression including HMVV; success/fade/message/credits
and clean exit; fixed-route 60 FPS+ evidence; PS Vita lifecycle/soak; PSTV
lifecycle/soak. Source tests and package closure are prerequisites, not visual
or end-to-end gate completion. Vita3K can supply preliminary route evidence
but cannot complete either physical gate.

Next: with user direction, remove the remaining reference to the deleted
`kM01CacheIndex` at `port/platform/vita/a31_vita_runtime.cpp:2211`, then resume
background ARM/package closure. Canonical build has not started. Retain hashes
and provenance, prepare
the matching title in Vita3K, and collect bounded emulator evidence. Blocking
release conditions remain full-route/visual/performance evidence and the
user's physical-test hold. Do not wait idly for builds or weaken these gates.

Older entries below are historical. At the time of this entry, Dev99 remained
the last closed package until a Dev100 closure entry was added. The earlier
50 FPS preferred-floor language does not replace the user's 60 FPS+ goal.

## 2026-08-31 — No-build performance/fidelity gate preparation

`[░░░░░░░░░░] 0/10 performance acceptance gates complete; no build, deploy, launch, provider install, or device capture`

- Source-only work continued in response to the performance/FPS scope. The
  working target is now explicit: 60 FPS top-end, 50 FPS preferred floor,
  30 FPS degraded floor, and 20 FPS critical floor. The new
  `reports/PERFORMANCE_FIDELITY_PLAN.md` records the required fixed-route
  evidence, optimization lanes, and next build/test gates.
- No renderer draw ordering, mission logic, physics, scripts, original asset
  ownership, or retail data changed. Diagnostic changes prepare the next
  candidate to report p99 frame time and 16.7/20.0/33.3/50.0 ms slow-frame
  bands, plus renderer cache-skip counters for texture binds, sampler state,
  stage enables, texture combiners, and render states.
- Tooling now compares capture bundles against the same FPS bands and parses
  current compact runtime performance lines into the performance ledger.
  Physical performance improvement remains unclaimed until a matching build,
  fixed replay/camera/content run, VDB logical-framebuffer evidence, and
  before/after comparison exist.

## 2026-08-31 — Dev99 canonical source/build candidate; VDB provider host-built; no physical action

`[██████████] 10/10 current evidence gates complete; no Vita deploy, launch, install, or capture`

- Source-only work continued without touching the Vita filesystem. Dev99
  advances identity to `A3.5-dev99`, preserves Dev98's startup/loading/
  deferred Render2D/HUD/BINK/message-window/short-wchar/UTF-16 formatter/
  WWUI/HUD presentation work, and adds one narrow startup visibility fix:
  a native debug-screen repaint worker redraws the current startup status every
  250 ms while original root and MIX file factories are constructed, then stops
  before the existing visible startup pre-cache phase.
- Focused validation passed
  `tools/test_runtime_log_contract.py`,
  `tools/test_vita_loading_screen_contract.py`,
  `tools/test_a4_original_frontend_contract.py`, and
  `tools/test_vita_indexed_state_contract.py` 39/39. Fast candidate closure
  passed 93 focused contracts and package checks in
  `logs/a35-dev99-fast-20260831-090948-build.log`. Canonical
  `bash ./tools/build.sh` passed retained host/current validation,
  deterministic 145-patch staging, 549 ARM/package actions, ELF/SELF/VPK
  identity, compressed VPK validation, diagnostics, SHA manifest, and retail
  exclusion in `logs/a35-dev99-20260831-091109-build.log`.
- Final repo validation passed full `python3 -m unittest discover tools`
  222/222, JSON syntax, `git diff --check`, public-document guardrails,
  repository hygiene, and no `.rej`/`.orig` debris.
- Artifact custody: VPK SHA-256
  `be9939594d7c25f4039f4aefbf77af631ccd6cb1200ed1a50b175cb6534b6c86`;
  packaged SELF SHA-256
  `020f210a129beaaf4d0953c6c56efc82267a52949d6883c5db313e87b0790d6d`;
  ELF SHA-256
  `fdce12071b368326c4b863547a87b58a9fb69fe7290d9425e9895371e4e9888e`;
  diagnostics ZIP SHA-256
  `f13a8f28309821a3c4d408000fccc681e955ba467d267bccab72c21b71302c68`.
- VDB `master` remains the required screenshot-provider source at
  `bc5df9e53dfca9b29c38cbd7635317bbb2aa0770`. The Dev99-matching
  exact-title provider bundle is host-built at
  `<VitaDevBridge>/build/exact-title-provider-rnega3101-020f210a-dev99-r26`.
  It targets live `capture.screen.v1`, `RNEGA3101`, and the Dev99 eboot hash
  above. It is not installed and no logical-framebuffer PNG/raw/metadata
  evidence exists yet.
- Dev99 has not been copied to, installed on, launched on, or visually accepted
  on a Vita. It does not claim menu text, gameplay subtitles, HUD numbers,
  target-box placement, intro A/V, loading-bar behavior, M00 stability, or
  Start/pause/exit correctness.

## 2026-08-31 — Dev98 canonical source/build candidate; VDB provider host-built; no physical action

`[██████████] 10/10 current evidence gates complete; no Vita deploy, launch, install, or capture`

- Source-only work continued under the user's no-physical-test window. Dev98
  advances identity to `A3.5-dev98` and targets the retained Dev87 frontend,
  dialogue, HUD, pickup, loading, intro-A/V, startup-black, target-box, HMVV,
  FPS, and Start failure set without touching the Vita filesystem. It preserves
  Dev97 and adds three focused corrections: BINK presentation timing starts
  only when audio output is armed or the first video upload is submitted; Vita
  WWUI dialog-template translation copies are bounded to the remaining original
  text buffer; and `HUDClass::Init()` runs inside the same native Vita HUD
  presentation scope used by `HUDClass::Think()`.
- Validation passed: focused BINK presentation-clock contract 10/10; combined
  frontend/loading/runtime/indexed-state/identity/source contract set 48/48;
  deterministic 145-patch staging with no `.rej`/`.orig` debris; pristine
  WWUI dialog-template patch apply proof; fast Dev98 candidate closure; and
  canonical `bash ./tools/build.sh` closure in
  `logs/a35-dev98-20260831-081728-build.log`. Final repo validation passed
  full `python3 -m unittest discover tools` 222/222, JSON syntax,
  `git diff --check`, hygiene, and no `.rej`/`.orig` debris.
- Canonical closure passed retained host/current validation, deterministic
  145-patch staging, 549 ARM/package actions, ELF/SELF/VPK identity,
  compressed VPK validation, diagnostics, SHA manifest, and retail exclusion.
  Artifact custody: VPK SHA-256
  `bb2e02eae8b28531735080214949463bcea3022859a8bf35affe33a01be2e870`;
  packaged SELF SHA-256
  `bbd96fe416f834b82054cf63a8680c9124d4c6b20e467bb98210e7241b815e35`;
  ELF SHA-256
  `dc5be03038085387bdf92225ba6a809995cc738a331e1756c320f80f76098dba`;
  diagnostics ZIP SHA-256
  `a2a079302212ef249cf58a399607a0ac48c027151dc85d4e208743dd7da088b2`.
- VDB `master` was synced to
  `bc5df9e53dfca9b29c38cbd7635317bbb2aa0770`, the exact-title framebuffer
  provider docs were read, and a Dev98-matching host-side provider bundle was
  built at `<VitaDevBridge>/build/exact-title-provider-rnega3101-bbd96fe4-dev98-r26`.
  It targets `capture.screen.v1`, `RNEGA3101`, and the Dev98 eboot hash above.
  It is not installed and no logical-framebuffer PNG/raw/metadata evidence
  exists yet.
- Dev98 has not been copied to, installed on, launched on, or visually accepted
  on a Vita. No Dev98 screenshot/video exists. The next physical gate must
  verify fast visible bootstrap, readable intro/menu text, paced intro A/V,
  loading progress during M00 load, readable gameplay dialogue/HUD/pickup
  text, target-box alignment, M00 stability including the HMVV approach, frame
  time, and Start/pause/exit behavior.

## 2026-08-31 — Dev97 canonical source/build candidate; no physical action

`[██████████] 10/10 current evidence gates complete; no Vita deploy or launch`

- Source-only work continued under the user's no-physical-test window. Dev97
  advances identity to `A3.5-dev97` and targets the retained Dev87 frontend,
  dialogue, HUD, pickup, loading, intro-A/V, startup-black, HMVV, and Start
  failure set without touching the Vita filesystem. It preserves Dev96 and
  adds a bounded UTF-16 formatted-output implementation for original
  menu/dialogue/HUD/pickup/ammo/health formatted strings, replacing the prior
  placeholder formatter. It also makes the startup-precache receipt
  candidate-scoped and emits visible status before original root/MIX file
  factory construction.
- Validation passed: short-wchar/loading/frontend/runtime/indexed-state source
  contracts 41/41; candidate identity/loading/runtime contracts 19/19; wider
  focused source contracts 63/63; UTF-16 formatter host selftest 19/19; host
  interactive M00/menu route two-cycle PASS with `STRINGS.TDB` loaded and six
  main-menu translations valid/renderable; fast Dev97 candidate closure; and
  canonical `bash ./tools/build.sh` closure in
  `logs/a35-dev97-20260831-073921-build.log`. Final repo validation passed
  full `python3 -m unittest discover tools` 222/222, JSON syntax,
  `git diff --check`, hygiene, and no `.rej`/`.orig` debris.
- Canonical closure passed retained host/current validation, deterministic
  145-patch staging, 549 ARM/package actions, ELF/SELF/VPK identity,
  compressed VPK validation, diagnostics, SHA manifest, and retail exclusion.
  Artifact custody: VPK SHA-256
  `1b7407f87b26f745deea4bf9047d1594cf14301a65c814fd53852520634ae06f`;
  packaged SELF SHA-256
  `b838cce455fc440b45c4cea4187d5f0589cb1ab97418d26f00d31c6da9b16804`;
  ELF SHA-256
  `8cf74768588f49aaa905c80bc5cbcb86216f4505c9d9c694d89025715475e814`;
  diagnostics ZIP SHA-256
  `d59e240e68b16418f30f8a12a3feaf8e9154794659add5f6321a7d01a103d1a5`.
- Dev97 has not been copied to, installed on, launched on, or visually
  accepted on a Vita. No Dev97 screenshot/video exists. The next physical gate
  must verify fast visible bootstrap, readable intro/menu text, paced intro
  A/V, loading progress during M00 load, readable gameplay dialogue/HUD/pickup
  text, target-box alignment, M00 stability including the HMVV approach, frame
  time, and Start/pause/exit behavior.

## 2026-08-31 — Dev96 canonical source/build candidate; no physical action

`[██████████] 10/10 current evidence gates complete; no Vita deploy or launch`

- Source-only work continued under the user's no-physical-test window. Dev96
  advances identity to `A3.5-dev96` and targets the retained Dev87 frontend,
  dialogue, HUD, pickup, loading, intro-A/V, startup-black, HMVV, and Start
  failure set without touching the Vita filesystem. It preserves Dev95 and
  adds UTF-16-safe Vita wrappers for `wcsncmp`, `wcsncpy`, `wcschr`, and
  `wcsstr` so original Windows 16-bit `WCHAR` text does not pass into libc
  functions that expect a different `wchar_t` ABI.
- Validation passed: short-wchar/loading/frontend/runtime/indexed-state source
  contracts 41/41; candidate identity/staging/frontend/loading/runtime/
  indexed-state/short-wchar contracts 54/54; UTF-16 host helper selftest 16/16;
  host interactive M00/menu route two-cycle PASS with `STRINGS.TDB` loaded and
  six main-menu translations valid/renderable; fast Dev96 candidate closure;
  deterministic 145-patch staging; and canonical
  `bash ./tools/build.sh` closure in
  `logs/a35-dev96-20260831-065932-build.log`.
- Canonical closure passed retained host/current validation, deterministic
  staging, 549 ARM/package actions, ELF/SELF/VPK identity, compressed VPK
  validation, diagnostics, SHA manifest, and retail exclusion. Artifact
  custody: VPK SHA-256
  `226767912ca4e6be9d582811c814155bb37a2a110dcb09c76eeaacd73202ad03`;
  packaged SELF SHA-256
  `05699ebac1ce5f19270f32dc9069e7c5e5400524f774c71135b2b69a4e821613`;
  ELF SHA-256
  `2b1498b0081c77738bf4a0450a0a938580e04af240b32fddd26d977179e2a768`;
  diagnostics ZIP SHA-256
  `6cf3885d8c52b17010230d003f98728b3602c45d0cb379d383ed21da2fbf7cea`.
- Dev96 has not been copied to, installed on, launched on, or visually
  accepted on a Vita. No Dev96 screenshot/video exists. The next physical gate
  must verify fast visible bootstrap, readable intro/menu text, paced intro
  A/V, loading progress during M00 load, readable gameplay dialogue/HUD/pickup
  text, target-box alignment, M00 stability including the HMVV approach, frame
  time, and Start/pause/exit behavior.

## 2026-08-31 — Dev95 canonical source/build candidate; no physical action

`[█████████░] 9/10 current evidence gates complete; no Vita deploy or launch`

- Source-only work continued under the user's no-physical-test window. Dev95
  advances identity to `A3.5-dev95` and targets the retained Dev87 frontend,
  loading, HUD/text, intro-A/V, and startup-black failures without touching
  the Vita filesystem. It preserves Dev94's startup framebuffer retention,
  synchronous loading-presenter callbacks, deferred indexed Render2D state,
  HUD `Think()` presentation scope, BINK audio-pressure frame dropping, and
  host main-menu translation validation. It then scopes
  `MessageWindowClass::On_Frame_Update()` and
  `MessageWindowClass::Update_Window_Rectangle()` through the Vita
  gameplay-HUD presentation guard so update-time dialogue/message layout and
  cached glyph geometry are generated in the same presentation space as render.
- Validation passed: deterministic 145-patch staging; focused identity,
  staging, loading, runtime, original-frontend/BINK, indexed-state, and
  fast-build contracts 52/52; implementation contracts 43/43; host interactive
  M00/menu route two-cycle PASS with `STRINGS.TDB` loaded and six main-menu
  translations valid/renderable; fast Dev95 candidate closure with 93 focused
  tests; and canonical
  `bash ./tools/build.sh` closure in
  `logs/a35-dev95-20260831-062728-build.log`.
- Canonical closure passed retained host/current validation, deterministic
  staging, 549 ARM/package actions, ELF/SELF/VPK identity, compressed VPK
  validation, diagnostics, SHA manifest, and retail exclusion. Artifact
  custody: VPK SHA-256
  `2c4185a62fe298184c0c0de6a83c261863f590ddeeea2732005a5b077cb5df24`;
  packaged SELF SHA-256
  `36329de9a2dc008ae199b7dee5aaba0297988e7fc74e0159b4d69830afba3cfe`;
  ELF SHA-256
  `a046df7f4820907e7468cc03c4db92aed07808f601415d234b3746d6deefa5d2`;
  diagnostics ZIP SHA-256
  `32167907c047ce977f023f1a272e8f2dfe65347d61e86aae172a03ed12b55e0e`.
- Dev95 has not been copied to, installed on, launched on, or visually
  accepted on a Vita. No Dev95 screenshot/video exists. The next physical gate
  must verify fast visible bootstrap, readable intro/menu text, paced intro
  A/V, loading progress during M00 load, readable gameplay dialogue/HUD/pickup
  text, target-box alignment, M00 stability including the HMVV approach, frame
  time, and Start/pause/exit behavior.

## 2026-08-31 — Dev93 canonical source/build candidate; no physical action

`[████████░░] 8/10 current evidence gates complete; no Vita deploy or launch`

- Source-only work continued under the user's six-hour no-physical-test window.
  Dev93 advances identity to `A3.5-dev93` and targets the retained Dev87
  frontend/HUD/startup failures without touching the Vita filesystem: native
  bootstrap/status output is held and repainted before filesystem/pre-cache
  work, original Render2DSentence text atlas allocation now uses width by
  height instead of width by width, glyph buffers are cleared before use, text
  atlas U/V coordinates scale independently, bounded text-atlas/dialog-template
  diagnostics are emitted for missing menu/dialogue/HUD glyphs, and gameplay
  HUD/TextDisplay Render2D presentation now scopes to native 960×544.
- Validation passed: deterministic 143-patch staging; focused original
  frontend/loading/runtime/texture/conversation diagnostics contracts 48/48;
  full `python3 -m unittest discover tools` 219/219 before canonical build;
  `verify_public_docs`, `verify_repo_hygiene`, JSON syntax, and
  `git diff --check` before report refresh.
- Fast candidate and canonical `bash ./tools/build.sh` both passed. Canonical
  closure passed retained host/current validation, deterministic 143-patch
  staging, 549 ARM/package actions, ELF/SELF/VPK identity, compressed VPK
  validation, diagnostics, SHA manifest, and retail exclusion in
  `logs/a35-dev93-20260831-050614-build.log`.
- Dev93 artifact custody: VPK SHA-256
  `a2af15eb6432922b4982387ccdee8261b3535e109d84714f8f47c3fadae373ac`;
  packaged SELF SHA-256
  `5244370a462065296b26fc784cbb3b5d2ce83395df7dfbab850ffd10652f2c78`;
  ELF SHA-256
  `5dc42428484c7342db229e21cea99761ecc39708b554937b289a49df25beaf61`;
  diagnostics ZIP SHA-256
  `beddfbbf4f11b63e37ed7fa8b73916a7aa99c1c456c9629efd0938d03d6c000c`.
- Dev93 has not been copied to, installed on, launched on, or visually accepted
  on a Vita. No Dev93 screenshot/video exists. The next physical gate must
  verify fast visible bootstrap, readable intro/menu text, paced intro A/V,
  loading progress, HUD/pickup/dialogue text, target-box alignment, M00
  stability including the HMVV approach, frame time, and Start/pause/exit
  behavior.

## 2026-08-31 — Dev92 canonical source/build candidate; no physical action

`[████████░░] 8/10 current evidence gates complete; no Vita deploy or launch`

- Source-only work continued under the user's six-hour no-physical-test window.
  Dev92 advances identity to `A3.5-dev92` and targets the retained Dev87
  frontend/HUD failure without touching the Vita filesystem: FreeType glyph
  measurement now includes advance plus bitmap bearings before rasterization,
  `StyleMgr` readiness probes require visible glyph columns, unchanged retail
  BINK uploads are capped at 320×240 with a lower per-update budget and bounded
  update iterations, movie audio resampling uses the decoder channel layout
  with a fallback, and target-box diagnostics now log projected clip-space,
  logical render resolution, device resolution, and camera aspect.
- Pre-build validation passed: deterministic staging, focused runtime/loading/
  original-frontend/conversation/input/gallery/texture contracts 60/60, and
  `git diff --check`.
- Canonical `bash ./tools/build.sh` passed retained host/current validation,
  deterministic 140-patch staging, 549 ARM/package actions, ELF/SELF/VPK
  identity, compressed VPK validation, diagnostics, SHA manifest, and retail
  exclusion in `logs/a35-dev92-20260831-042733-build.log`.
- Dev92 artifact custody: VPK SHA-256
  `16aa490ecbe733f6053212d8d0f9aa0dc2e3ea5e9d7a701d545c2c20b779adf3`;
  packaged SELF SHA-256
  `08e89f0788652746a7c7d7590ee1bdbfaafccfd0e8c58a33266b0f37a305dae1`;
  ELF SHA-256
  `fe945697e1bdf6165ef2afc8e23014f7a2b5cda6be3a8c4811acfd147ad3f411`;
  diagnostics ZIP SHA-256
  `5b24fbc953037ecfab48ab87a38e489ad5702c8d8d52ead15f0903ece1f324be`.
- Dev92 has not been copied to, installed on, launched on, or visually accepted
  on a Vita. No Dev92 screenshot/video exists. The next physical gate must
  verify readable intro/menu text, paced intro A/V, loading progress,
  HUD/pickup/dialogue text, target-box alignment, M00 stability including the
  HMVV approach, frame time, and Start/pause/exit behavior.

## 2026-08-31 — Dev91 canonical source/build candidate; no physical action

`[██████░░░░] 6/10 current evidence gates complete; no Vita deploy or launch`

- Source-only work continued under the user's six-hour no-physical-test window.
  Dev91 advances identity to `A3.5-dev91` and targets the returned frontend/M00
  failures without touching the Vita filesystem: FreeType empty-bitmap glyphs
  now remain valid spacing glyphs, `StyleMgr` probes require visible pixels,
  startup pre-cache artificial holds are reduced to a one-second visible delay,
  unchanged retail BIK uploads are downscaled to 480×360 with a six-buffer audio
  startup reserve and faster late-frame dropping, original loading progress gets
  bounded catch-up renders when phase progress changes, and M00 vehicle
  transition/update/proximity diagnostics are added for the reported HMVV
  freeze.
- Pre-build validation passed: focused runtime/loading/original-frontend/
  conversation/input contracts 40/40, identity precheck for `DEV91`, and
  `git diff --check`.
- Canonical `bash ./tools/build.sh` passed retained host/current validation,
  deterministic 139-patch staging, 549 ARM/package actions, ELF/SELF/VPK
  identity, compressed VPK validation, diagnostics, SHA manifest, and retail
  exclusion in `logs/a35-dev91-20260831-035521-build.log`.
- Dev91 artifact custody: VPK SHA-256
  `20f561ebcdf534ea71da6e421ab47811c99a9bdce14dac84dd7f99481f4c8768`;
  packaged SELF SHA-256
  `42e85952ce85975e05e1385414f9d43ed35e4330a2a91325737c0f412de6c219`;
  ELF SHA-256
  `47cdcc15c57b1efc8bc2da8995e902b4d0e580143091e70b6818198c1a51169e`;
  diagnostics ZIP SHA-256
  `2ac5fc16970e4b1689a91a92e90dd2e6260cd70313136a7e952b4979d6efe767`.
- Dev91 has not been copied to, installed on, launched on, or visually accepted
  on a Vita. No Dev91 screenshot/video exists. The next physical gate must
  verify readable intro/menu text, paced intro A/V, loading progress,
  HUD/pickup/dialogue text, target-box alignment, M00 stability including the
  HMVV approach, frame time, and Start/pause/exit behavior.

## 2026-08-31 — Dev90 local source/build candidate; no physical action

`[████░░░░░░] 4/10 current evidence gates complete; no Vita deploy or launch`

- Source-only work continued under the user's no-physical-test window. Dev90
  keeps Dev88/Dev89's shared indexed-glyph, BINK-audio reserve, frontend-scope,
  bootstrap, pre-cache, and Render2D texture-state work, then adds: a persistent
  debug/status screen through original engine setup before VitaGL handoff,
  aspect-preserved 640×480 maximum BINK uploads for the unchanged 800×600 retail
  movies, synchronous M00 loading-progress callbacks, hardened retail font
  reads and FreeType glyph atlas clipping/clearing, gameplay Start-to-ESC
  suppression, and rollback of Dev89's target-box native-coordinate override to
  original HUD logical-space ownership.
- Focused validation passed: 23/23 runtime/loading/original-frontend/input
  contracts. Canonical `bash ./tools/build.sh` passed retained host/current
  validation, deterministic 138-patch staging, 549 ARM/package actions,
  ELF/SELF/VPK identity, compressed VPK validation, diagnostics, SHA manifest,
  and retail exclusion in `logs/a35-dev90-20260831-032019-build.log`.
- Dev90 artifact custody: VPK SHA-256
  `76766b787869693887428272914f646f92cae50d5009eaab1bb72f8071cc3568`;
  packaged SELF SHA-256
  `35dcbff8cef5d8aa06c291364f22592e2f17c81d16019a79ae95e2a434f2f2d2`;
  ELF SHA-256
  `c48286ebdc2595584c4c2b8d68940cd739c2bd6071ca686e77479faff5d4a698`;
  diagnostics ZIP SHA-256
  `1819fb1575c27063e2cdeec07650e65b1bd889049e12227df1101ec43c0a1772`.
- Dev90 has not been copied to, installed on, launched on, or visually
  accepted on a Vita. No Dev90 screenshot/video exists. The next physical gate
  must verify readable intro/menu text, paced intro A/V, loading progress,
  HUD/pickup/dialogue text, target-box alignment, M00 stability including the
  HMVV approach, frame time, and Start/pause/exit behavior.

## 2026-08-31 — Dev89 local source/build candidate; no physical action

`[████░░░░░░] 4/10 current evidence gates complete; no Vita deploy or launch`

- Source-only work continued under the no-physical-test boundary. Dev89 keeps
  Dev88's shared indexed-glyph texture-stage fix and real BINK audio reserve,
  then adds: original frontend 800×600 render/presentation scoping, real
  `StyleMgr` font glyph validation before menu input, multiple retail
  Regatta/Arial font filename fallbacks, native bootstrap display flushing
  before filesystem/cache work, expanded UI/HUD/subtitle/pickup/shadow/POG/M00
  pre-cache touches, Render2D texture-stage-1 clearing before text/icon draws,
  late BINK video-frame dropping after the first visible frame, and
  native-WW3D coordinate scoping for camera-projected target boxes.
- Focused validation passed: 19/19 runtime/loading/original-frontend
  contracts plus `git diff --check`. Canonical `bash ./tools/build.sh` passed
  retained host/current validation, deterministic 138-patch staging, 549
  ARM/package actions, ELF/SELF/VPK identity, compressed VPK validation,
  diagnostics, SHA manifest, and retail exclusion in
  `logs/a35-dev89-20260831-024834-build.log`.
- Dev89 artifact custody: VPK SHA-256
  `e2754588124910eeea526c056d004986f48f60491ab1a529f6a513248f0757a2`;
  ELF SHA-256
  `acd2a60edb65b7cf415000ee1a114a8cbfd96c999ddbed99685900437ca165f9`;
  diagnostics ZIP SHA-256
  `7bc5d18d1f1607cf10e0aee371f51ac4d73f1fe58f69cef60ab9ac86796b9038`.
- Dev89 has not been copied to, installed on, launched on, or visually
  accepted on a Vita. The next physical gate must verify readable intro/menu
  text, paced intro A/V, loading progress, HUD/pickup/dialogue text,
  target-box alignment, M00 stability including the HMVV approach, frame time,
  and Start/pause/exit behavior.

## 2026-08-31 — Dev87 follow-up retains frontend/HUD failure

`[████░░░░░░] 4/10 current evidence gates complete; no build or Vita mutation`

- User physical observation: original menu text is still absent; ammo and
  health text are mangled; the NPC targeting/bounding-box indicator is further
  right of the NPC; and an opaque black screen remains before the pre-warm/
  pre-cache routine. These add to the retained slow/buzzy intro and empty
  dialogue-box failures.
- No source diagnosis, build, deployment, title launch, or Vita filesystem
  modification is implied by this report. Dev88 remains local-only and held.
- A full MP4 player cannot be embedded in GitHub Markdown: the authenticated
  GitHub renderer strips a tested `<video>` element. The user authorized the
  public Pages route; a dedicated `gh-pages` branch with exactly the MP4,
  player, and poster was pushed, but GitHub rejected Pages creation with HTTP
  422 because this private repository's current plan does not support it. The
  repository was not made public; no public player is live.
- The user has authorized the exact recording for unlisted YouTube hosting,
  which can supply the required functional embedded player without exposing the
  repository. This workspace currently has no connected YouTube upload
  capability; no upload has been attempted.
- Next: connect the authorized upload account, publish the exact verified MP4
  as unlisted with failure-context metadata, verify its player, and link it
  from the gallery/evidence record.

## 2026-08-31 — Dev87 finalized recorder recovered; gallery evidence in publication

`[████░░░░░░] 4/10 current evidence gates complete; no build or Vita mutation`

- The user finalized the installed recorder with L+Start and opened VitaShell
  FTP. Read-only enumeration found
  `ux0:/video/eg/2026-08-31_004224.mp4`, 44,746,182 bytes. The MP4 was pulled
  without changing the Vita and retained locally under
  `build/device-evidence/a35-dev87-video-return-20260831T060240Z/`; local
  SHA-256 is `e6f10ac1add71090bfa83246f4829b668d2d7629f25e5c0f3dfd1eb09ea44aaf`.
- Inspection confirms a 200.917-second 640x368 physical-Vita H.264/AAC
  recording with sustained M00 exterior, war-factory, and interior gameplay.
  Six settled stills are selected for the gallery. The opening black/HUD-only
  transition was reviewed and excluded rather than used as a screenshot.
- Raw video, transfer scratch data, logs, and dumps remain local-only. The
  Dev87 gallery is a record of actual gameplay evidence, not an acceptance
  claim: missing original menu/dialogue text and poor intro A/V remain failed
  physical gates.
- Publication complete: `origin/main` commit
  `efb9adeeb9d326dae04c76893680968aee0c1fb0` contains the six derived PNGs,
  gallery, inventory, and status update. Next: retain the failed Dev87 gates
  and await explicit direction; Dev88 remains held from every Vita action.

## 2026-08-31 — public documentation/GitHub reconciliation; historical capture campaign prepared

`[████░░░░░░] 4/10 current evidence gates complete; no build or Vita action`

- Public-facing status, build, install, control, evidence, capture, contributor,
  security, conduct, issue-template, and repository-hygiene documentation has
  been reconciled to the returned Dev87 failure and local-only Dev88 candidate.
  It explicitly distinguishes physical Vita evidence from host/package closure
  and does not claim a fabricated gallery update.
- The historical gallery generator now preserves the current capture-completeness
  disclosure and strips workstation-specific paths from regenerated public
  inventory/timeline output. The managed README is no longer overwritten by
  gallery generation.
- Read-only local inventory finds reusable VPKs for every A3.5 dev number from
  dev1 through dev88, plus the A3.1.x and frozen A3.2 checkpoint. The planned
  capture campaign is documented in `docs/HISTORICAL_CAPTURE_CAMPAIGN.md` and
  requires no rebuild. It captures only visibly settled, post-render M00 frames;
  old loading/black frame triggers remain diagnostic evidence, not substitutes.
- Validation: timeline/inventory regeneration, Python syntax, public-document
  link/status validation, repository-hygiene validation, and `git diff --check`
  pass. No device file, retail file, capture provider, executable, or running
  process was changed.
- Next: publish the documentation/GitHub update, then await explicit READY for
  the hash-bound historical device-capture pass. Dev88 remains separately held.

## 2026-08-31 — earlier VDB screenshot route verification; no finalized video at that check

`[████░░░░░░] 4/10 current evidence gates complete; no game rebuild or device mutation`

- The checked-in VDB screenshot client can collect repeated post-render,
  exact-title logical-framebuffer evidence through `capture.screen.v1` (up to
  16 labelled captures per bundle). This is the correct replacement for
  game-timed screenshot retuning.
- The paired Vita currently reports VitaCompanion `1.06+vdbftp1` and advertises
  `screen.v1` only. Its `screen on|off` service controls panel power; it does
  not expose `capture.screen.v1` or `capture.screen.cycle.v1`, so no VDB
  screenshot request can succeed on the current device service.
- The observed red `R` is the separately installed title-scoped
  `RenegadeDemoRecorder`, not VDB screenshot capture. It autostarts an MP4
  recording and finalizes with L+Start or clean module stop; a title crash can
  prevent a usable MP4 from being committed. At this earlier retrieval check,
  forced VDB1 search for `*.mp4` below `ux0:/video` returned no files; the
  negative receipt is retained under the Dev87 evidence root. A later user
  finalization and VitaShell FTP retrieval is recorded above.
- Next: prepare the source-matched exact-title VDB agent/gateway route without
  changing the Vita. Before a future physical session, obtain explicit
  authorization for the new device-side capture provider, then collect and
  publish actual post-render frames and any finalized recorder output. Dev88
  remains local-only until explicit physical-test direction.

## 2026-08-31 — Dev87 return fails frontend gate; Dev88 canonical local-only

`[████░░░░░░] 4/10 current evidence gates complete; no Dev88 device action`

- The Dev87 physical frontend gate fails. The user reports original menu text
  is still missing; original intro movies remain very laggy with buzzy audio;
  and the original grey gameplay dialogue/subtitle box is empty. The returned
  partial log is
  `build/device-evidence/a35-dev87-user-return-20260831T022728Z/a35-dev87-runtime.log`
  (SHA-256 `a01c0b54159fefa2fa4c4ebefdaf181f11330f23e0287f2b426e7cbb1eac911c`)
  and ends at original main-menu activation, so it cannot prove dialogue data
  presence or rendered glyph visibility in M00.
- Dev88 corrects the shared original dynamic indexed-draw state path used by
  `Render2DSentence` menu glyphs and `MessageWindow` subtitle glyphs. It now
  applies the original per-stage texture combiner before emission; no overlay,
  string substitution, or replacement UI is introduced. It also delays BINK's
  audio worker until three real decoded output buffers are queued, rather than
  one, to reduce starvation under observed frame stalls. Retail movies are
  unchanged.
- 54 focused contracts and `git diff --check` passed. Canonical Dev88 passed
  retained host validation, 115 current contracts, deterministic 136-patch
  staging, 549 ARM/package actions, identity/archive checks, diagnostics, and
  retail exclusion in `logs/a35-dev88-20260830-214253-build.log`. VPK SHA-256:
  `be78097b98a3c0a0e9e9cd1fbdb0d5cdb9d7d630145bec8736d7ebad0cf07138`; SELF:
  `cd5726251dbdd33c2d19a97aa83ccc95d992ad6800c945497ec473fe40228fce`.
- Dev88 has not been copied to, installed on, or launched on the Vita. Next:
  after Dev87 ends, retrieve every title-scoped returned screenshot/capture,
  inspect and label it accurately, regenerate the gallery/timeline, publish
  the GitHub update, then wait for explicit direction for a new physical test.
- Dev88 source, focused contracts, canonical identity, and the Dev87 physical
  failure record are published at `origin/main` commit
  `0807c1733ea45993ac8fca9f49858a0daafc83f1` (`Fix Dev88 frontend text and
  BINK audio reserve`). No Dev87 image was present in the title-owned
  `screenshots`/Dev87-window `captures` paths, so the gallery is explicitly
  still pending actual returned image evidence rather than being fabricated.

## 2026-08-31 — dev87 text/resource and BINK-upload candidate; physical observation active

`[█████░░░░░] 5/10 current evidence gates complete; hash-matched user observation active`

- Dev86 is returned physical failure evidence. Its matching runtime log proves
  original BINK, menu, loading, and M00 paths execute; the user still reports
  slow/buzzy intro A/V and missing menu labels. The returned loading-screen
  image is now in the historical gallery with that diagnostic-only label; no
  video was returned or published.
- The original UI text path creates a procedural glyph texture and writes it
  through a surface. The Vita branch was not allocating that texture. Dev87
  restores its existing DX8/Vita allocation path. This is the concrete source
  correction for blank labels, not visual acceptance.
- Dev86's EA BINK timing makes upload the leading measured cost:
  13,476,510 us/202 uploads (68,901 us worst), versus 1,561,800 us video decode
  and 671,221 us audio decode. Dev87 changes only the decoded in-memory upload
  format to RGB565; it neither converts nor modifies retail movie files.
- `tools/build_fast_candidate.sh` passes 89 focused contracts, deterministic
  staging, ARM link, identity, archive integrity, and SHA checks in
  `logs/a35-dev87-fast-20260830-204232-build.log`. VPK SHA-256:
  `7e108cffe2c5c858be66136ab0c0498c3c1ee1377aad6dbf513abf0bbbf60185`.
- Canonical `bash ./tools/build.sh` has now independently passed retained
  host/current contracts, deterministic 136-patch staging, 549 ARM/package
  actions, original-runtime symbols, ELF/SELF/VPK identity, compressed archive,
  SHA manifest, diagnostics, and retail exclusion in
  `logs/a35-dev87-20260830-204706-build.log`. VPK SHA-256 is
  `bbb48f91c879c99e2944497b97a56cbf1e015c7af4a20ed75871bf02bb86e521`; SELF is
  `d7bdadbff7296dad0d5460d0febfe70116502c9a80695bfa3577f6c629f9c596`.
- Source, tests, reports, and the explicitly diagnostic gallery item are
  published to `origin/main` at `015c83bde9653fc9bfc58f1a731eb2492e351558`.
  VPK/ELF/SELF, logs, raw capture, video, diagnostics, dumps, retail data,
  saves, and credentials remain excluded.
- Explicit READY received: dev86 was stopped, backed up locally by matching
  SHA-256, and only `ux0:/app/RNEGA3101/eboot.bin` was replaced. Dev87 VPK and
  staged SELF each hash-match their canonical artifacts in the title-scoped
  user area; installed SELF readback is
  `d7bdadbff7296dad0d5460d0febfe70116502c9a80695bfa3577f6c629f9c596`.
  Zero-input launch is accepted and the app remains running. The provider
  reported non-atomic replacement and no remote backup; the verified local
  dev86 backup is retained at
  `build/device-backups/a35-dev87-install-launch-20260831T022343Z/`.
- No runtime log, capture, recording, dump, plugin, retail-data, or synthetic
  input action has followed launch. The user reports screenshots were taken.
  Next: after the user ends the manual run and returns findings, inventory and
  pull every dev87 screenshot/capture, publish only accurately scoped gallery
  entries, regenerate the timeline, then commit and push the complete update.

## 2026-08-30 — dev86 canonical frontend diagnostic candidate; publication/physical handoff pending

`[████░░░░░░] 4/10 current evidence gates complete; hash-matched user observation active`

- The retained dev85 user return remains a frontend usability failure: very long
  black start, slow/buzzy EA movie, and an original main-menu dialog without
  visible menu items. It is not overwritten or relabeled as success.
- Dev86 removes only the Vita early returns that bypassed the original
  `MainMenuTransitionClass` control-placement path; adds a debug-screen
  bootstrap message before filesystem/retail pre-cache; and prevents BINK from
  submitting a zero-filled audio buffer while it waits for decoded samples.
  End-of-movie logs capture audio/video decode/upload time, waits, output, and
  audio-ring high water to diagnose the remaining pacing fault.
- Canonical `bash ./tools/build.sh` passed in
  `logs/a35-dev86-20260830-195426-build.log`: retained host validation (112
  tests), deterministic 136-patch staging, 549 ARM/package actions,
  original-runtime symbols, ELF/SELF/VPK identity, compressed archive/SHA,
  diagnostics, and retail exclusion. VPK SHA-256 is
  `9a9f36c15f699b72e736f2b2a4b29d4e57537e59c3cfeb5b41f206884b85aa10`; SELF
  SHA-256 is `3b20079eca192cdf2d5869fbc3bfb485ec0528cfa2969f006a60f9567b44b4a8`.
- GitHub source/evidence checkpoint `0c5c543` and canonical closure `a05478a`
  are published. After explicit READY, doctor/capability preflight passed; the
  VPK and staged SELF were VDB1 hash-verified under the Renegade user tree,
  the prior dev85 executable was pulled to a hash-verified local backup, and
  only `ux0:/app/RNEGA3101/eboot.bin` was replaced. Installed SELF readback is
  `3b20079e…7b44b4a8`; title status remained running after 15 seconds.
- No synthetic input was sent and no runtime log, dump, screenshot, or video
  has been pulled. The current user observation must visibly verify
  bootstrap/pre-cache, paced intro A/V, Start skip, and placed WWUI controls.

## 2026-08-31 — dev85 physical frontend return: BINK path reached, usability gate failed

`[█████░░░░░] 5/10 current evidence gates complete; transition/pacing repair next`

- The exact VPK (`299c5f79…33b58`) and SELF (`d26321f2…f62f1`) are VDB1
  hash-verified at the Renegade user-tree and installed-title paths. The prior
  dev84 executable is backed up by matching hash. No unrelated Vita file was
  changed and synthetic input is released.
- User physical observation: long initial black screen; pre-cache/VitaGL
  appeared; the EA intro appeared but was extremely slow with buzzy/laggy
  audio; Start skipped it to a main menu whose items are missing. This fails
  frontend usability.
- The matching `a35-dev85-runtime-user-report.log` SHA-256 is
  `409e30186303fb4cf8e3eef688f2b9104e6aaa3a229dc3c472581bd0efcf2596`.
  It proves EA_WW.BIK completion, R_INTRO.BIK decode/upload, the physical
  Start skip, and original main-menu creation/activation. It also records the
  Vita-only original-main-menu transition bypass, the concrete menu-item lead.
- Next: restore the original transition/control-placement owner, then measure
  and repair BINK pacing/audio. No physical visual claim or media publication
  will be made without returned image/video evidence.

## 2026-08-30 — capture-policy route blocked by stale optional recorder

`[████░░░░░░] 4/10 current evidence gates complete; recorder-isolated startup check next`

- User return: prolonged black screen, diagnostic pre-cache, then crash. The
  exact capture-policy SELF remains installed and hash-verified
  (`555f0c1f...0bbe`); the app is stopped and synthetic input is released.
- The retained 14,139-byte log completes startup pre-cache in 5,023/5,027 ms
  but ends before frontend/M00/capture-policy markers. Two new raw PSP2 cores
  are local-only; their verified title-thread PCs share the previous recorder
  display-hook `+0x15fa` offset, while registers are unavailable.
- Device hash readback proves the active recorder user module is stale
  `8a856e76...`, not the guarded `111d2f4f...` build. This is
  recorder-confounded crash evidence, not a capture-policy or gameplay result.
  `ux0:/video` contains no MP4 to retrieve.
- Next: publish this evidence, make a candidate-scoped backup, replace only
  the title-scoped recorder user helper, re-verify its hash, then run one
  finite zero-input startup observation. Do not infer visual correctness.

## 2026-08-30 — guarded recorder reaches interactive M00; panel evidence pending

`[████░░░░░░] 4/10 current evidence gates complete; live physical observation active`

- The stale recorder helper is locally backed up and the device now verifies
  guarded `111d2f4f...`; the Renegade SELF remains exact `555f...0bbe`. A
  rejected cross-mount replacement made no write; the completed same-mount
  replacement was not reported atomic, so the local backup is retained.
- The guarded run survived the former post-precache failure and reached
  original frontend/menu, tutorial load/finalization, 60 M00 pre-warm frames,
  original player control, Logan conversation/audio, and frame-480 checkpoints.
  Later physical stick/touch samples are observed but not attributed.
- No agent gameplay input was sent; controls were released. The automatic
  screenshot remains disabled and Select was not pressed, so there is no new
  gameplay screenshot, gallery item, or finalized MP4 to publish yet.
- Next: retain the live user observation, collect only returned media/log/dump
  evidence after the user reports it, and then use the measured frame-time/state
  data to select one renderer or pre-warm performance blocker.

## 2026-08-30 — explicit visible-gameplay capture candidate; READY received

`[████░░░░░░] 4/10 current evidence gates complete; hash-matched physical route authorized`

- Dev82 proved that `first-interactive-player-frame` at engine frame 1 is not a
  visual acceptance point. The source now disables that automatic screenshot;
  a Select rising edge is honored only after original tutorial/player control,
  scene/star/camera, all render phases, actual submitted geometry, and zero
  rejected/unsupported submissions. The retained bundle reason is
  `manual-select-visible-gameplay`.
- Canonical `bash ./tools/build.sh` passed in
  `logs/a35-dev84-20260830-182029-build.log`: retained host validation, 111
  tests, 136-patch restaging, 549 ARM actions, required symbols, ELF/SELF/VPK
  identity, compressed archive/SHA, diagnostics, and retail exclusion. New
  VPK SHA-256: `99aa5d5c295da232c535489c5e50c0d6fcc55ef9fe7e1704d63ba3ef1fa3e392`;
  packaged SELF SHA-256: `555f0c1f83b46992b0e349b8c1d2c4500daaeb2d945311926d33f3d824590bbe`.
- The user supplied `READY`. Next: publish this exact source/report identity,
  then replace only the title executable after device-side preflight and a
  hash-bound backup; run the bounded route, press Select only at the visibly
  settled gameplay checkpoint, and retain the returned capture/log/crash
  evidence without claiming any other visible issue resolved.

## 2026-08-30 — dev84 recorder crash classified; GitHub-first pause

`[████░░░░░░] 4/10 current evidence gates complete; no physical launch until READY`

- The user-returned dev84 PSP2 core is hash-retained locally as
  `c42665a0a5a10f8e235b4096d4a1d4dbc2962ca68dcd5bafa8050d7f6cb683d8`.
  Its source-derived fault PC lies in the optional title-scoped MP4 recorder
  display hook, outside the matching Renegade RX segment. It is not evidence
  that the dev84 Start-exit lifecycle repair regressed.
- The recorder patch now passes invalid display notifications through before
  dereference and leaves plain Start to Renegade; L+Start remains the recorder
  finalize control. Zero-fuzz patch application, 5/5 workflow tests, and an
  ARM user-plugin rebuild pass. No finalized MP4 exists under `ux0:/video`.
- Sanitized crash metadata is published in `reports/DEV84_RECORDER_CRASH.md`.
  Raw dumps, logs, VPKs, plugins, captures, video, retail data, saves, and
  credentials remain excluded from Git. The prior pause was released only for
  the current hash-matched capture-policy candidate after the user supplied
  `READY`.
- Next: finish the private GitHub commit/push, then
  replace only the title-scoped recorder helper and run the bounded physical
  isolation check.

## 2026-08-30 — Dev82 returned-frame gallery correction; capture policy defect

`[████░░░░░░] 4/10 current evidence gates complete; no physical launch until READY`

- The initial Dev82 gallery publication was inadequate: it had only two PNG
  copies and a diagnostic-inventory row. It did not visibly surface the
  returned physical evidence in the README or historical timeline. The
  correction now presents all four raw returned capture records, with source
  directories and SHA-256 values, in an expressly diagnostic-only section.
- Direct image/hash review shows three distinct rendered images across the
  four records: two inverted loading presentations; a first-interactive record
  (`t64590857`) that is byte-identical to the full-frame loading image; and a
  black first-interactive frame (`t88041059`) with a partial HUD. No Dev82
  image is presented as a gameplay pass.
- The captured `first-interactive-player-frame` trigger fired at engine frame
  1 (roughly six seconds in the returned summaries), which proves it is an
  engine-ownership marker rather than a visual-stability marker. The next
  source change must delay captures until post-transition world/HUD stability
  and collect several intentionally later frames; do not launch to obtain
  them before the user supplies `READY`.
- Next: validate and push the gallery correction, then trace and repair the
  capture trigger without device interaction.

## 2026-08-30 — dev84 lifecycle correction; publication and physical gate active

`[███████░░░] 7/10 current evidence gates complete; recorded physical gate active`

- User-reported Start crash returned one new candidate-scoped PSP2 dump:
  `981a48faa0b949df02b2126149c45fe379e2a208ea84ac48793ea10ab1f69651`.
  VDB reports a data abort at `0x811d4ab2`; source-derived mapping identifies
  original `cPlayer::On_Destroy()` after Combat mode was prematurely removed.
- Dev84 delays only the Combat-mode removal until after original player/session
  teardown. The focused suite passed 35/35; the fast ARM package passed 86
  contracts in `logs/a35-dev84-fast-20260830-162553-build.log`, with content
  ID `EP9000-RNEGA3101_00-RENGADEVITADEV84`.
- Added the returned loading and first-interactive physical screenshots to the
  generated diagnostic gallery. They are failed visual evidence, not an alpha
  acceptance claim. Title-scoped `ux0:/video` has no finalized MP4 currently.
- Canonical `bash ./tools/build.sh` passed in
  `logs/a35-dev84-20260830-163409-build.log`: retained host validation, 111
  tests, deterministic 136-patch restaging, 549 ARM actions, ARM/VPK identity,
  compressed archive/SHA, diagnostics, and retail exclusion. VPK SHA-256 is
  `6352b0e23a51e6943f2992843c97b8a07b9311877bffb69eeed06518e33e8051`; SELF
  SHA-256 is `3c6304cc5fe13dbaf36ea27c6f32fc5fdac9a05c852e0416e519e42eb135d896`.
- Next: commit and push source plus gallery evidence to the private GitHub
  repository, then deploy only this hash-matched dev84 candidate for physical
  confirmation.
- Deployed after the first publication: VPK
  `6352b0e23a51e6943f2992843c97b8a07b9311877bffb69eeed06518e33e8051` is
  hash-verified in the title user tree and SELF
  `3c6304cc5fe13dbaf36ea27c6f32fc5fdac9a05c852e0416e519e42eb135d896` is
  hash-verified at the installed eboot path. The prior dev82 executable and
  tai config have candidate-scoped backups. A recorder was added only to
  `ur0:/tai/` `*KERNEL` and `*RNEGA3101`, verified after reboot, and dev84 has
  launched running with all synthetic input released. Await the user’s new
  findings/Start exit before pulling logs, screenshots, or the finalized MP4.

## 2026-08-30 — dev83 visual-correction candidate; canonical build active

`[██████░░░░] 6/10 current evidence gates complete; canonical source/build gate active`

- Preserved candidate-scoped dev82 runtime log, startup-precache receipt,
  phase-labelled captures, app status, installed SELF receipt, and a
  snapshot-only crash inventory after the user reported findings. The title
  remained running with the expected dev82 SELF; no new matching dump was
  pulled.
- Physical/source correlation identified two bounded renderer corrections:
  remove the additional `loadscreen_*` V flip after the original Targa/DX8
  path, and scope the centered 640x480 presentation rect to the original 2D
  owners rather than all of `CombatManager::Render()` (which includes world
  rendering). The new Combat touch is a deterministic zero-fuzz staging patch;
  no upstream source was changed.
- `logs/a35-dev83-fast-20260830-160756-build.log` passed 86 focused contracts,
  136-patch restaging, ARM link/package, package identity/content ID,
  compressed archive/SHA checks, and retail exclusion. Dev83 is a distinct
  fast candidate; dev82 physical evidence remains immutable.
- Next: run the canonical build, retain full artifacts and diagnostics, then
  perform the next bounded hardware test only with the resulting hash-matched
  dev83 package. Bink re-enable and broader precaching remain deferred pending
  a fixed replay and measurements.

## 2026-08-30 — dev82 installed and running; awaiting user findings

`[██████░░░░] 6/10 current evidence gates complete; hands-on physical gate active`

- VDB package installation is unavailable on the current command surface
  (`CAPABILITY_MISSING app.query.v1`), but no failed package attempt replaced
  the executable. The exact VPK is uploaded and VDB1 hash-verified at
  `ux0:/data/renegade/user/RenegadeVita-A3.5-dev82.vpk`.
- Under the title-scoped authorization, the verified packaged SELF was staged
  in the same user tree and used to replace only
  `ux0:/app/RNEGA3101/eboot.bin`. The prior
  `3e9d4ad5...` executable is locally backed up; VDB1 now reports installed
  SELF `36235779e4fd94886e913a23b4ea203e728612cd90114dc5b2d8fad73145120a`.
- `RNEGA3101` launched successfully and its app-status-only check remains
  running after 15 seconds. No synthetic input was sent and no runtime logs,
  captures, recordings, or dumps have been pulled.
- Next: await the user's observed behavior. After findings are reported, pull
  only the matching runtime artifacts and update the physical evidence gate.

## 2026-08-30 — dev82 canonical CONTENT_ID package respin

`[█████░░░░░] 5/10 current evidence gates complete; physical launch gate active`

- The previous canonical VPK (`2d05da8f...`) is preserved and its VDB install
  receipt confirms `VPK_SFO_INVALID` due to an empty SFO `CONTENT_ID`; no Vita
  executable replacement occurred in that attempt.
- A narrow CMake/package correction now sets
  `EP9000-RNEGA3101_00-RENGADEVITADEV82` and checks it in both canonical and
  fast VPK workflows. The canonical run
  `logs/a35-dev82-20260830-153141-build.log` passed host fingerprints, 111
  tests, deterministic staging, ARM link/package, identity, archive/SHA,
  diagnostics, and retail exclusion.
- The current physical candidate is VPK
  `d9a0cc027be2278eb26d4d056dfeec974aff52e4f11f95c5b66fe87e982d3fad` and
  packaged SELF
  `36235779e4fd94886e913a23b4ea203e728612cd90114dc5b2d8fad73145120a`.
  It has not yet been installed or launched. The current device executable is
  backed up under
  `build/device-backups/a35-dev82-install-launch-20260830-202256/`.
- Next: re-admit the stopped device, install and verify only the exact current
  candidate, then launch without synthetic input. After user findings arrive,
  pull matching runtime artifacts; until then, poll only app/crash status.

## 2026-08-30 — dev82 read-only physical-readiness reconciliation

`[████████████] 12/12 canonical source/build gates complete; physical gate pending`

- Read-only evidence at
  `build/device-evidence/a35-dev82-readiness-20260830-201630/` proves the
  paired physical Vita is reachable and `RNEGA3101` is stopped. The control
  plane reports a read-only authenticated VDB1 debugger and the VitaCompanion
  network transport; no upload, install, launch, input, or device-side write
  was performed.
- Device identity: `ux0:/app/RNEGA3101/eboot.bin` is SHA-256
  `3e9d4ad5a7b90a2f4f4e1fed5177e096aa81851b1967fc86eb4517749e831a04`, which
  does not match the current dev82 packaged SELF
  `08a27d1c8b374171afeb1bc1f1bf1f7a1e0c914a56738a84f3ec3c2e784bf11b` or the
  current VPK SHA-256
  `2d05da8f4868cbaa6a6818c8eecf18026ac655f52ca1ca5b788953dd67d5089b`.
  The pulled runtime log is a 222,309-byte stale append log (SHA-256
  `9311414d5ffb3b4c531bfcea19c8a2158bf30c3b589989113d35e7270824063d`), and
  `a35-dev82-startup-precache.txt` is absent.
- Consequence: existing physical dev82 observations do not validate the
  current visible-precache/aspect-preservation/HUD-presentation/texture-cache
  artifact. The first next physical gate is a hash-matched current-VPK manual
  install followed by phase-labelled M00 observations and both runtime/receipt
  returns; automatic deployment remains disabled.

## 2026-08-29 — dev82 HUD-presentation visible-precache candidate

`[██████████] 12/12 canonical source/build gates complete`

- Runtime boundary: the current dev82 VPK now runs a visible
  pre-cache/pre-warm/pre-compute phase before intro movies, menu navigation, or
  M00 gameplay input. It indexes the retained original MIX filename tables,
  writes persistent M00/M01 cache-index files under
  `ux0:data/renegade/cache/`, touches critical startup movie/menu/loading/M00
  files through the original FileFactory/MIX owners, keeps input disabled
  during that phase, displays for at least five seconds, reports movie-file
  availability, and logs
  `startup-precache begin`, per-file `startup-precache touch`,
  `startup-precache visible hold`, receipt-write, and `startup-precache
  complete` breadcrumbs. It also writes
  `ux0:data/renegade/user/logs/a35-dev82-startup-precache.txt` for the
  physical return.
- Runtime visual fixes: original HUD/TextDisplay/radar/sniper/bounding-box
  owners now run under the authored 640x480 Render2D coordinate space and a
  centered aspect-preserved native presentation rect while the world remains
  native 960x544. Direct DX8/Bink GL texture uploads invalidate the renderer
  texture-bind cache before original mesh draws resume. The original loading
  screen uses the same aspect-preserved native presentation rect (`117,0
  725x544`) instead of stretching 640x480 content to the full panel. This
  specifically targets the reported wrong HUD/loading placement and stale
  character texture reuse such as face textures appearing on Havoc legs.
- Validation: focused pre-cache/loading/skin/texture/frontend/input contracts
  passed 71/71, fast candidate `logs/a35-dev82-fast-20260829-042551-build.log`
  passed 86 focused tests, `git diff --check` passed, and canonical
  `bash ./tools/build.sh` passed in
  `logs/a35-dev82-20260829-050854-build.log` with 111 host unittest checks,
  deterministic 135-patch restaging, DDS/TGA alias 11/11, render-state 13/13,
  ARM link/package, identity, compressed VPK validation, diagnostics bundle,
  SHA manifest, and retail exclusion.
- Artifact: `dist/RenegadeVita-A3.5-dev82.vpk` SHA-256 is
  `2d05da8f4868cbaa6a6818c8eecf18026ac655f52ca1ca5b788953dd67d5089b`;
  ELF SHA-256 is
  `02b20a3074ed21f3638fc1051548c512d0fce957e7be43812c5fc2e016a7e069`;
  MAP SHA-256 is
  `10a7f914e9b3d3da8c5e6c30f956f61e419b0cda79b54584dd7258687981f843`;
  diagnostics bundle SHA-256 is
  `5e8b60c8719036b96255296804a9a9d225327d5d7458db119464dd4ee8565116`.
- Boundary: this newest `2d05da8f...` VPK has not yet been uploaded to Vita. The
  earlier user-authorized `9e67b02c...` upload predates the visible startup
  pre-cache/HUD/texture-cache work and must not be treated as the current
  artifact. A 2026-08-29 upload probe at
  `build/device-evidence/a35-dev82-upload-probe-20260829-052650/` verified the
  current VPK hash, scanned known PS Vita/PSTV and ARP-visible FTP endpoints,
  and found no open VitaShell FTP service. VDB `doctor` passed locally, but
  `status` and VitaCompanion/VitaShell port probes for `10.0.0.202` and
  `10.0.0.186` were disconnected/no-route/closed, so no current VPK transfer
  occurred.
  `tools/upload_dev82_current_vpk.sh --scan-arp` now provides a repeatable
  hash-checked upload/probe path for the next reachability window.
  Dev82 remains physically pending; return both `a35-dev82-runtime.log` and
  `a35-dev82-startup-precache.txt`, and check loading telemetry for
  `native_presentation_x=117`, `native_presentation_width=725`,
  `logical_to_native_fullscreen=false`, and `aspect_preserved=true`.
- Vita3K pre-cache evidence: previous 04:28 installed-title run
  `build/vita3k-evidence/a35-dev82-20260829-044413-canonical-cache-index-precompute/`
  imported the `cc19ce1a...` VPK payload, updated installed `eboot.bin` to
  SHA-256 `eb8585c88e9425e22d12bce8195a2cbc853c4906f882f24c23d82c075dd48f5b`,
  and produced `a35-dev82-startup-precache.txt` with `pass=1`,
  `archives=4/4`, `required_files=14/14`, `movie_files=3/3`,
  `cache_indexes=2/2`, `cache_entries=315`, `elapsed_ms=5001`,
  `visible_minimum_ms=5000`, and
  `before_frontend/before_movies/before_gameplay=1`. Runtime cache health then
  reported `M00_Tutorial.mix` valid with 84 cached entries and `M01.mix` valid
  with 231 cached entries. This is emulator evidence for the pre-cache
  implementation inherited by the current build; it predates the 05:08 HUD
  native-presentation adjustment and does not physically accept dev82.

## 2026-08-28 — dev82 M00 tutorial plus retail frontend/Bink candidate

`[██████████] 12/12 canonical source/build gates complete`

- Runtime boundary: dev82 keeps the dev48-dev81 audio, dialogue, texture,
  material, and render-state chain, then expands the physical-test fixes with
  original `CombatGameModeClass` post-load finalization, building/radar
  initialization, `On_Game_Begin`, texture-loader continuation, shader-cache
  setup, single-bar loading/prewarm progress, and synchronized
  640x480-to-960x544 viewport state. It also integrates the external
  `feature/a35-dev82-retail-frontend` worker commit
  `e7a7fa82fa90981e160035a81ff029169f3412cc`, routing the original
  `MovieGameModeClass`, `MenuGameModeClass2`, `RenegadeDialogMgrClass`, main
  menu dialogs, WWUI controls, and Tutorial launch latch into the existing M00
  path.
- Movie boundary: active supersedes the worker's fail-closed Bink stub with a
  Vita FFmpeg Bink provider, but realtime playback is disabled in this physical
  candidate after black-screen/audio-underrun evidence so the original menu/M00
  route is not blocked by slow movie decode. The canonical ELF retains
  `BINKMovie::Play`,
  `avformat_open_input`, `ff_bink_decoder`, `ff_binkaudio_dct_decoder`,
  `ff_binkaudio_rdft_decoder`, `swr_convert`, and `sws_scale`. The provider
  retains pending FFmpeg packets across decoder `EAGAIN` and restores GL
  texture0 bind/enable state after movie blits for the later playback retry; no
  proprietary RAD code and no retail movie assets are packaged.
- Visual/UI fixes: gameplay DDS uploads now preserve retail top-down row order,
  passthrough texture-V correction now happens after the original DX8 texture
  transform, `Render2DClass` initializes the dynamic FVF normal and UV1 fields
  used by HUD/loading/subtitle/scope/bounding-box draws, and `Render2DClass`
  restores the previous DX8 viewport after fullscreen 2D passes. The original
  loading screen renders status/progress text, HUD/subtitle bounds are
  tightened, sniper scope/icon placement is corrected toward fullscreen Vita
  output, and a visible reload fallback keeps first-person reload motion for
  0.8 seconds while the original weapon state is reload.
- Lifecycle fixes: frontend WWUI/controller input is gated so intro/menu
  navigation cannot also drive gameplay bindings, `TextDisplayGameModeClass`
  initializes after the final `StyleMgrClass` reinitialization, and the
  no-output WWAudio boundary now supplies the original movie temp-disable
  calls used by `MovieGameModeClass`.
- Control map: Triangle is action/use/interact, Square is reload, D-pad
  Left/Right changes weapons without camera turn bindings, D-pad Up/Down zooms
  sniper in/out, front touch maps to the original 640x480 mouse cursor plus
  left click for WWUI/terminal interaction, rear touch toggles first/third-
  person camera, and shoulder buttons are not remapped.
- Validation: focused loading-screen, texture-surface, staging, indexed-state,
  mission-conversation diagnostics, camera-input, and original-frontend
  contracts passed before packaging. The full canonical build passed fresh host
  validation, deterministic restaging, 106 host unittest checks, source
  integration reporting, ARM link/package, identity verification, compressed
  VPK validation, diagnostics bundle generation, SHA manifest verification,
  retail exclusion, and symbol/string retention for Bink, render-state,
  reload, texture-V, TextDisplay diagnostics, Render2D viewport restore, and
  Bink packet/texture-state hardening.
- Source report: the canonical integration report records 506 original Westwood
  translation units plus one staged original-owner extraction, 26 Vita
  platform/renderer/validation/developer files, 6 A4 frontend/Bink boundary
  files, 52 compatibility headers, 134 active deterministic patch files, and
  pristine upstream.
- Artifact: `dist/RenegadeVita-A3.5-dev82.vpk` SHA-256 is
  `9e67b02cae9ae8d26e146d9fbd72694c5848d057e7aeb17b87a65f088240132c`;
  ELF SHA-256 is
  `4bd3f9375e9176215dcc90385f89a5f11e0810773cc98b7c5b78c6fcb001f0f6`;
  MAP SHA-256 is
  `f56321bc46805433a7826317d9953758dad4e3259c258ad34ad00b07e81b4ec9`;
  diagnostics bundle SHA-256 is
  `e157284da790e7df6492991ad78c4e9f78aaf39deac6ed9f7e5248f9fb92ddf7`.
- Minimum deliverables audit: `reports/A35_DEV82_MINIMUM_DELIVERABLES.md`
  records source/build/artifact requirements as PASS and keeps hardware-only
  observations explicitly PENDING.
- Historical visual evidence: `docs/HISTORICAL_SCREENSHOT_TIMELINE.md`
  publishes 171 GitHub-renderable PNGs from `build/device-evidence/`, read-only
  VitaShell FTP pulls, targeted Vita3K AppData checks, and older A3.1 captures
  from `/mnt/e/Projects/RenegadeVitaBuilder/Vita Logs/`. The README and quick
  timeline now show only actual gameplay/world/detail frames, including NPC
  detail crops from dev13 and dev19. Diagnostic-only builds and black/logo,
  magenta, and loading frames remain in the complete manifest and inventory,
  with only one displayed loading-screen regression reference.
- Demo capture workflow: the optional non-USB PSVITA/PSTV recorder builds from
  pinned `Rinnegatamante/Vita-MP4-Recorder@60c966a75356ea9a95f79479a3e647283586cf11`
  with a Renegade title-scoped patch and a local `sceMp4Rec` compatibility
  header when the SDK header is absent. Built artifacts are
  `dist/RenegadeDemoRecorder-A3.5-dev82.suprx`
  SHA-256 `8a856e76b99654b1d21fde65b8040c41cc29225da91076631b5ee76be564270d`
  and `dist/RenegadeDemoRecorder-A3.5-dev82.skprx`
  SHA-256 `e8a695c08fe348ab8cb1b16f2264fe67d593c3e82a7e61629f61f04d9e88eba5`.
  It is manual-install only; no tai config, plugin, retail data, or VPK content
  was pushed by the build.
- Boundary: on user request, that earlier frontend+Bink VPK was uploaded by
  VitaShell FTP to
  `ux0:/data/renegade/user/RenegadeVita-A3.5-dev82.vpk` on 2026-08-28; a
  follow-up FTP listing found the filename. No install, launch, retail-data
  transfer, or other Vita filesystem mutation was attempted. Dev82 is not
  physically accepted. The next run must check intro movie playback/skip,
  original WWUI menu navigation, Tutorial launch, loading screen
  coverage/text/progress, HUD/subtitle placement, Logan/Sydney/Gunner text and
  audio, character/door/powerup/objective texture orientation, bounding boxes,
  random ground rectangles, reload animation, Triangle gate use, sniper
  scope/icon/zoom, FPS, freeze/crash behavior, clean Start exit, and
  `ux0:data/renegade/user/logs/a35-dev82-runtime.log`.

## 2026-08-28 — dev79 M00 tutorial control/HUD/loading candidate

`[██████████] 12/12 canonical source/build gates complete`

- Runtime boundary: dev79 preserves the dev48-dev78 audio, dialogue, texture,
  material, and render-state chain, then addresses the latest physical report:
  loading-screen aspect/orientation/progress, missing HUD/TextDisplay path,
  camera-Y inversion, action/use mapping, first-person weapon/reload ownership,
  D-pad camera/weapon/objectives controls, textured-skin color handling,
  renderer texture/render-state churn, and gate transition diagnostics.
- Control map: Triangle is action/use/interact, Square is reload, D-pad Down
  toggles first/third person, D-pad Left/Right changes weapons, and D-pad Up
  uses the original EVA/objectives path. Touch and rear touch remain unmapped.
- Validation: focused conversation/loading/route/skin/camera contracts passed
  before packaging. The full canonical build passed retained host-validation
  reuse, deterministic restaging, 83 host unittest checks, source integration
  reporting, ARM link/package, identity verification, compressed VPK
  validation, diagnostics bundle generation, SHA manifest verification, and
  retail exclusion.
- Source report: the canonical integration report records 452 upstream
  original Westwood translation units plus one staged original-owner extraction
  (`staging/commando/loadingscreen.cpp`), 26 Vita
  platform/renderer/validation/developer files, 52 compatibility headers, and
  121 deterministic patch files.
- Artifact: `dist/RenegadeVita-A3.5-dev79.vpk` SHA-256 is
  `0c34f954885f097f422c4f3670ccb3d9b20fc606fb0e9416d898855c92b84d74`;
  ELF SHA-256 is
  `b3483c419750cb33821b16205e04fcc97f969e6dfb6b14290b633066325c23c0`;
  MAP SHA-256 is
  `a37cfdaf00498a0e80874cba71462cbd4cf601cc92d4ee307e60110bd9aa462a`;
  diagnostics bundle SHA-256 is
  `7a155ded66cd82b1c094817d43142a7e5099d8aeec2c888ae9ec7bda61874a37`.
- Boundary: the VPK was manually uploaded to the VitaShell FTP user tree on
  request. No retail data was transferred. Physical acceptance is pending
  returned observations, `ux0:data/renegade/user/logs/a35-dev79-runtime.log`,
  screenshots/captures, and any matching crash dump.

## 2026-08-28 — dev78 original material color authority

`[██████████] 12/12 canonical source/build gates complete`

- Renderer boundary: dev78 preserves dev77 rigid user-lighting precedence and
  removes the remaining non-original near-black textured static material
  fallback from the direct Vita mesh backend. Textured rigid meshes now submit
  the original evaluated material/user-lighting color directly instead of
  replacing black results with ambient, emissive, or forced white.
- Runtime purpose: this matches the original WW3D `Set_Material`,
  `Set_Shader`, and vertex-color authority more closely and leaves bad
  material, lighting, texture, or retail-asset state visible in runtime
  breadcrumbs rather than masking it at the Vita backend boundary.
- Validation: focused indexed render-state, texture-provenance, and skin
  submission contracts passed 24/24. The fast no-deploy candidate passed 66
  focused tests, the original `DDSFileClass` `.tga`-to-`.dds` executable
  contract 11/11, package identity checks, and VPK packaging. The full
  canonical no-deploy build passed retained host-validation reuse, the current
  lightweight render-state contract 13/13, the DDS/TGA alias contract 11/11,
  82 host unittest checks, deterministic restaging, source integration
  reporting, ARM link/package, compressed VPK validation, identity
  verification, diagnostics bundle generation, SHA manifest verification, and
  retail exclusion.
- Source report: the canonical integration report records 451 upstream original
  Westwood translation units plus one staged original-owner extraction
  (`staging/commando/loadingscreen.cpp`), 26 Vita platform/renderer/validation
  files, 119 deterministic patch files covering 238 mechanically patched
  staged upstream paths, 52 compatibility headers, and pristine upstream.
- Artifact: `dist/RenegadeVita-A3.5-dev78.vpk` SHA-256 is
  `c0779b68172d13f6ff057c010697d9b65af210719a2e827de4acbfde61ebbb27`;
  ELF SHA-256 is
  `60257b346f579fb5750fb9e92a56dfeb21b44fbe067309ecced396b62d613978`;
  MAP SHA-256 is
  `c9e3a75257a015c177732f0fa7097ac22cf60a792c229c2bf0ac3937434347c1`;
  diagnostics bundle SHA-256 is
  `ce7772d29c9ae3ed996cc795370244ea747016df6029baedb434023573d86080`.
- Boundary: dev78 has not been physically tested and no Vita deployment was
  attempted. The next hardware run should manually install dev78, verify M00
  sky/fog/ambient/material lighting, texture appearance, muzzle rectangle and
  other alpha cutouts, Logan dialogue text, Logan audible dialogue and timing,
  and route fidelity, then inspect
  `ux0:data/renegade/user/logs/a35-dev78-runtime.log`, especially
  `first original user lighting color source`,
  `first original material lighting`, `first original DX8 fog state`,
  `first original DX8 ambient state`, `texture loaded`, `loaded_dds/tga`,
  `checker_bind`, `invalid_bind`, `unsupported_stages`, and confirm
  `first static material black fallback` does not appear.

## 2026-08-28 — dev77 original user-lighting color source

`[██████████] 12/12 canonical source/build gates complete`

- Renderer boundary: dev77 preserves dev76 material-lighting evaluation and
  restores the original rigid-mesh color1 precedence used by
  `DX8FVFCategoryContainer` / `Vertex_Split_Table`: non-skinned direct
  `MeshClass` submissions now prefer `MeshClass::Get_User_Lighting_Array(false)`
  before falling back to model color array 0 and pass-specific DCG. Skinned
  meshes remain on the original model color-array path.
- Runtime purpose: this keeps precomputed/original user lighting available to
  M00 static and rigid world geometry at the Vita backend boundary without
  moving ownership out of WW3D or inventing a replacement material path.
  The runtime logs the first `first original user lighting color source`
  breadcrumb for hardware review.
- Validation: focused indexed render-state, texture-provenance, and skin
  submission contracts passed 24/24. The fast no-deploy candidate passed 66
  focused tests, the original `DDSFileClass` `.tga`-to-`.dds` executable
  contract 11/11, package identity checks, and VPK packaging. The full
  canonical no-deploy build passed retained host-validation reuse, the current
  lightweight render-state contract 13/13, the DDS/TGA alias contract 11/11,
  82 host unittest checks, deterministic restaging, source integration
  reporting, ARM link/package, compressed VPK validation, identity
  verification, diagnostics bundle generation, SHA manifest verification, and
  retail exclusion.
- Source report: the canonical integration report records 451 upstream original
  Westwood translation units plus one staged original-owner extraction
  (`staging/commando/loadingscreen.cpp`), 26 Vita platform/renderer/validation
  files, 119 deterministic patch files covering 238 mechanically patched
  staged upstream paths, 52 compatibility headers, and pristine upstream.
- Artifact: `dist/RenegadeVita-A3.5-dev77.vpk` SHA-256 is
  `0528357e6b4d47d7c1d8e49fef22faaf6e0bd9980c75403dd43c331cd5bf1252`;
  ELF SHA-256 is
  `18c91bfb2851b9515e82851b058e0dd1dd5eca7f62fb0cb774f3e6ac134e0264`;
  MAP SHA-256 is
  `92622879ef7e5747698927dce14e589ce33043e844da5e3b0cc07f5757e5006a`;
  diagnostics bundle SHA-256 is
  `b73067c8ed507fe7d7769e105bafb1d7bdefe49c8fec72168d650c7073352d38`.
- Boundary: dev77 has not been physically tested and no Vita deployment was
  attempted. The next hardware run should manually install dev77, verify M00
  sky/fog/ambient/material lighting, texture appearance, muzzle rectangle and
  other alpha cutouts, Logan dialogue text, Logan audible dialogue and timing,
  and route fidelity, then inspect
  `ux0:data/renegade/user/logs/a35-dev77-runtime.log`, especially
  `first original user lighting color source`,
  `first original material lighting`, `first original DX8 fog state`,
  `first original DX8 ambient state`, `texture loaded`, `loaded_dds/tga`,
  `checker_bind`, `invalid_bind`, `unsupported_stages`,
  `first original indexed VertexMaterial mapper`,
  `first generated texture coordinates`, `output_stream`,
  `last_output_stream`, `last_stream_mix`, active stream
  position/length/cursor/frames/loops/volume/pan, speech duration/dropoff/
  distance, stream bytes/frames/mix counters, and conversation state if
  dialogue or materials remain incorrect.

## 2026-08-28 — dev76 original material lighting/color-source evaluation

`[██████████] 12/12 canonical source/build gates complete`

- Renderer boundary: dev76 preserves dev75 scene fog/fill/ambient restoration
  and changes the direct Vita `MeshClass` path to evaluate original
  `VertexMaterialClass` diffuse, ambient, emissive, opacity, lighting enable,
  color-source, and `LightEnvironmentClass` contribution rules before emitting
  Vita vertex colors. Pass-specific DCG data remains available as the original
  color1/color2 source fallback instead of becoming an unconditional raw color.
- Runtime purpose: this removes another simplified material shortcut from the
  direct mesh backend while keeping WW3D/Scene/VertexMaterial ownership above
  the Vita boundary. The change is aimed at retail M00 material/lighting
  fidelity and the remaining wrong-color/pink-black diagnostic path without
  introducing a replacement renderer.
- Validation: focused indexed render-state, texture-provenance, and skin
  submission contracts passed 23/23. The fast no-deploy candidate passed 65
  focused tests, the original `DDSFileClass` `.tga`-to-`.dds` executable
  contract 11/11, package identity checks, and VPK packaging. The full
  canonical no-deploy build passed retained host-validation reuse, the current
  lightweight render-state contract 13/13, the DDS/TGA alias contract 11/11,
  81 host unittest checks, deterministic restaging, source integration
  reporting, ARM link/package, compressed VPK validation, identity
  verification, diagnostics bundle generation, SHA manifest verification, and
  retail exclusion.
- Source report: the canonical integration report records 451 upstream original
  Westwood translation units plus one staged original-owner extraction
  (`staging/commando/loadingscreen.cpp`), 26 Vita platform/renderer/validation
  files, 119 deterministic patch files covering 238 mechanically patched
  staged upstream paths, 52 compatibility headers, and pristine upstream.
- Artifact: `dist/RenegadeVita-A3.5-dev76.vpk` SHA-256 is
  `371ed075af325d8909a96b492411f9cbef93d5f6698e627f1aa8b1a2d14c9c38`;
  ELF SHA-256 is
  `321915aed3794fb246c1cdd3ecfd9b5d3b98553c2d41324023b9a5a6b97160cc`;
  MAP SHA-256 is
  `0d000574f7f86e956235666e7bbf581bc1fcb45ef0ee3005fbe174feff2a4b07`;
  diagnostics bundle SHA-256 is
  `a4b836233185a53a9e7f979e15cb19bd2402ad1def3eefd6de81536d44a25b7f`.
- Boundary: dev76 has not been physically tested and no Vita deployment was
  attempted. The next hardware run should manually install dev76, verify M00
  sky/fog/ambient/material lighting, texture appearance, muzzle rectangle and
  other alpha cutouts, Logan dialogue text, Logan audible dialogue and timing,
  and route fidelity, then inspect
  `ux0:data/renegade/user/logs/a35-dev76-runtime.log`, especially
  `first original material lighting`, `first original DX8 fog state`,
  `first original DX8 ambient state`, `texture loaded`, `loaded_dds/tga`,
  `checker_bind`, `invalid_bind`, `unsupported_stages`,
  `first original indexed VertexMaterial mapper`,
  `first generated texture coordinates`, `output_stream`,
  `last_output_stream`, `last_stream_mix`, active stream
  position/length/cursor/frames/loops/volume/pan, speech duration/dropoff/
  distance, stream bytes/frames/mix counters, and conversation state if
  dialogue or materials remain incorrect.

## 2026-08-28 — dev75 original scene fog/fill/ambient restoration

`[██████████] 12/12 canonical source/build gates complete`

- Renderer boundary: dev75 preserves dev74 render-state handling and removes
  the remaining Vita early-return from the original `WW3D::Render(SceneClass*)`
  path. Vita now follows the original camera apply, polygon fill-mode,
  scene ambient, scene render, and flush sequence while still excluding only
  desktop-only clear and mesh-renderer camera calls.
- Scene state: staged `SceneClass::Render` now restores the original
  `DX8Wrapper::Set_Fog(FogEnabled, FogColor, FogStart, FogEnd)` call on Vita,
  and `D3DRS_AMBIENT` is routed through the Vita render-state boundary to
  `glLightModelfv(GL_LIGHT_MODEL_AMBIENT, ...)` with a first-state runtime
  breadcrumb.
- Runtime purpose: this keeps original WW3D/Scene ownership of fog, fill mode,
  and scene ambient lighting for M00 instead of treating Vita scene rendering
  as a shortened backend-only path. The change is aimed at the black/fogless
  sky, wrong material lighting, and retail scene-state fidelity gates.
- Validation: focused indexed render-state and texture-provenance contracts
  passed 20/20. The fast no-deploy candidate passed 64 focused tests, the
  original `DDSFileClass` `.tga`-to-`.dds` executable contract 11/11, package
  identity checks, and VPK packaging. The full canonical no-deploy build
  passed retained host-validation reuse, the current lightweight render-state
  contract 13/13, the DDS/TGA alias contract 11/11, 80 host unittest checks,
  deterministic restaging, source integration reporting, ARM link/package,
  compressed VPK validation, identity verification, diagnostics bundle
  generation, SHA manifest verification, and retail exclusion.
- Source report: the canonical integration report records 451 upstream original
  Westwood translation units plus one staged original-owner extraction
  (`staging/commando/loadingscreen.cpp`), 26 Vita platform/renderer/validation
  files, 119 deterministic patch files covering 238 mechanically patched
  staged upstream paths, 52 compatibility headers, and pristine upstream.
- Artifact: `dist/RenegadeVita-A3.5-dev75.vpk` SHA-256 is
  `3d324ae1887860b57c190abe6528bcb5335ca3aa0efec55b79fc719c73b70e45`;
  ELF SHA-256 is
  `bf3e918357f5153b02ad94ee2579949f205fa4e1084e37bee4f38375e990a5b1`;
  MAP SHA-256 is
  `807db91e1c15d7ce44e678612d9b7ba8bda3a3abfe3344a92ba14384f345971b`;
  diagnostics bundle SHA-256 is
  `1289b87f0b9efc504ea31f6a1629aa2da965bab6f36f693dc7280720a6c760ae`.
- Boundary: dev75 has not been physically tested and no Vita deployment was
  attempted. The next hardware run should manually install dev75, verify M00
  sky/material fog, scene ambient/material appearance, muzzle rectangle and
  other alpha cutouts, Logan dialogue text, Logan audible dialogue and timing,
  and route fidelity, then inspect
  `ux0:data/renegade/user/logs/a35-dev75-runtime.log`, especially
  `first original DX8 fog state`, `first original DX8 ambient state`,
  `texture loaded`, `loaded_dds/tga`, `checker_bind`, `invalid_bind`,
  `unsupported_stages`, `first original indexed VertexMaterial mapper`,
  `first generated texture coordinates`, `output_stream`,
  `last_output_stream`, `last_stream_mix`, active stream
  position/length/cursor/frames/loops/volume/pan, speech duration/dropoff/
  distance, stream bytes/frames/mix counters, and conversation state if
  dialogue or materials remain incorrect.

## 2026-08-28 — dev74 original DX8 render-state and fog bridge

`[██████████] 12/12 canonical source/build gates complete`

- Renderer boundary: dev74 preserves dev73 detail-combiner behavior and routes
  original `IDirect3DDevice8::SetRenderState()` calls through the Vita renderer
  instead of treating them as no-ops. The bridge now carries original fog
  enable/color/start/end state, alpha test/reference/compare, alpha blend
  source/destination, depth compare/write, cull mode, and fill mode into the
  fixed-function GL backend.
- Runtime purpose: this keeps `DX8Wrapper::Set_DX8_Render_State()`,
  `DX8Wrapper::Set_Fog()`, and `ShaderClass::Apply()` as the original owners
  of material/render state while making the Vita backend honor the state they
  emit. `IsFogAllowed` is enabled only after the Vita path gained an actual fog
  implementation.
- Validation: focused indexed render-state and texture-provenance contracts
  passed 19/19. The fast no-deploy candidate passed 63 focused tests, the
  original `DDSFileClass` `.tga`-to-`.dds` executable contract 11/11, package
  identity checks, and VPK packaging. The full canonical no-deploy build passed
  retained host-validation reuse, the current lightweight render-state
  contract 11/11, the DDS/TGA alias contract 11/11, 79 host unittest checks,
  deterministic restaging, source integration reporting, ARM link/package,
  compressed VPK validation, identity verification, diagnostics bundle
  generation, SHA manifest verification, and retail exclusion.
- Source report: the canonical integration report records 451 upstream original
  Westwood translation units plus one staged original-owner extraction
  (`staging/commando/loadingscreen.cpp`), 26 Vita platform/renderer/validation
  files, 118 deterministic patch files covering 238 mechanically patched
  staged upstream paths, and pristine upstream.
- Artifact: `dist/RenegadeVita-A3.5-dev74.vpk` SHA-256 is
  `c65767ce6b35c693e7d3abbb0b5bf4764ab89dd2bc8e313b1b143c591f4d07ee`;
  ELF SHA-256 is
  `504718966a606646aecd197c69bb33f94878bb0b37eac358cba13bfc814c7c3a`;
  MAP SHA-256 is
  `dd7aa440c9cf9c83029838857ee0eb04ef2a3366ba2e9a03b66894b634d512c5`;
  diagnostics bundle SHA-256 is
  `81771595a4c18ba79d723d93b80b523fd17d734cbcc1b2dcd791dfc4cd062697`.
- Boundary: dev74 has not been physically tested and no Vita deployment was
  attempted. The next hardware run should manually install dev74, verify M00
  sky/material fog, material/texture appearance, muzzle rectangle and other
  alpha cutouts, Logan dialogue text, Logan audible dialogue and timing, and
  route fidelity, then inspect
  `ux0:data/renegade/user/logs/a35-dev74-runtime.log`, especially
  `first original DX8 fog state`, `texture loaded`, `loaded_dds/tga`,
  `checker_bind`, `invalid_bind`, `unsupported_stages`,
  `first original indexed VertexMaterial mapper`,
  `first generated texture coordinates`, `output_stream`,
  `last_output_stream`, `last_stream_mix`, active stream
  position/length/cursor/frames/loops/volume/pan, speech duration/dropoff/
  distance, stream bytes/frames/mix counters, and conversation state if
  dialogue or materials remain incorrect.

## 2026-08-28 — dev73 original ADDSMOOTH detail combiner

`[██████████] 12/12 canonical source/build gates complete`

- Renderer boundary: dev73 preserves dev72 supported texture-stage telemetry
  and translates original `D3DTOP_ADDSMOOTH` inverse-scale detail color/alpha
  through a fixed-function GL interpolate combiner with a white texture-env
  constant instead of plain `GL_ADD`.
- Runtime purpose: this keeps `ShaderClass::Apply()` ownership in original
  WW3D while making retail detail/lightmap materials render closer to the
  original `local + (1-local)*other` behavior when M00 assets load.
- Validation: focused indexed texture-state and texture-provenance contracts
  passed 18/18. The fast no-deploy candidate passed 62 focused tests, the
  original `DDSFileClass` `.tga`-to-`.dds` executable contract 11/11, package
  identity checks, and VPK packaging. The full canonical no-deploy build passed
  retained host-validation reuse, the current lightweight render-state
  contract 5/5, the DDS/TGA alias contract 11/11, 78 host unittest checks,
  deterministic restaging, source integration reporting, ARM link/package,
  compressed VPK validation, identity verification, diagnostics bundle
  generation, SHA manifest verification, and retail exclusion.
- Source report: the canonical integration report records 451 upstream original
  Westwood translation units plus one staged original-owner extraction
  (`staging/commando/loadingscreen.cpp`), 26 Vita platform/renderer/validation
  files, 118 deterministic patch files covering 238 mechanically patched
  staged upstream paths, and pristine upstream.
- Artifact: `dist/RenegadeVita-A3.5-dev73.vpk` SHA-256 is
  `251d9335c97056f15f69398a2bfd7c4ef9a9ec9242dab55719896d39acf67c32`;
  ELF SHA-256 is
  `a0a9b823b9434e9c7b86ce962462b9ba5bc5078d2bacfff1c3564bd8b1ccf02b`;
  MAP SHA-256 is
  `97fa72861b3598f2522ce4a06fd9f720b19022e4bdff24aa59d30710aae6d8aa`;
  diagnostics bundle SHA-256 is
  `74dee4dea56fe2c49921979c95f6358088b7bfaabdc53f8e74a330628ba48dc0`.
- Boundary: dev73 has not been physically tested and no Vita deployment was
  attempted. The next hardware run should manually install dev73, verify M00
  sky/materials, muzzle rectangle and other alpha cutouts, Logan dialogue text,
  Logan audible dialogue and timing, material/texture appearance, and route
  fidelity, then inspect
  `ux0:data/renegade/user/logs/a35-dev73-runtime.log`, especially
  `texture loaded`, `loaded_dds/tga`, `checker_bind`, `invalid_bind`,
  `unsupported_stages`, `first original indexed VertexMaterial mapper`,
  `first generated texture coordinates`, `output_stream`,
  `last_output_stream`, `last_stream_mix`, active stream
  position/length/cursor/frames/loops/volume/pan, speech duration/dropoff/
  distance, stream bytes/frames/mix counters, and conversation state if
  dialogue or materials remain incorrect.

## 2026-08-28 — dev72 supported texture-stage telemetry

`[██████████] 12/12 canonical source/build gates complete`

- Renderer boundary: dev72 preserves dev71 alpha-test reference semantics and
  changes Vita texture-stage unsupported telemetry to count only stages outside
  the original two-stage `MeshMatDescClass` material contract. DX8 boundary
  calls with stages beyond the emulated device limit are still recorded before
  returning `D3DERR_INVALIDCALL`, but ordinary retail stage-1 material traffic
  no longer pollutes `unsupported_stages`.
- Runtime purpose: this keeps the dev58-dev70 stage-1 material path visible as
  supported traffic in hardware logs, so the next M00 texture/material replay
  can separate real unsupported stage requests from expected lightmap/detail/
  generated-coordinate submissions.
- Validation: focused indexed texture-state and texture-provenance contracts
  passed 17/17. The fast no-deploy candidate passed 61 focused tests, the
  original `DDSFileClass` `.tga`-to-`.dds` executable contract 11/11, package
  identity checks, and VPK packaging. The full canonical no-deploy build passed
  retained host-validation reuse, the current lightweight render-state
  contract 5/5, the DDS/TGA alias contract 11/11, 77 host unittest checks,
  deterministic restaging, source integration reporting, ARM link/package,
  compressed VPK validation, identity verification, diagnostics bundle
  generation, SHA manifest verification, and retail exclusion.
- Source report: the canonical integration report records 451 upstream original
  Westwood translation units plus one staged original-owner extraction
  (`staging/commando/loadingscreen.cpp`), 26 Vita platform/renderer/validation
  files, 118 deterministic patch files covering 238 mechanically patched
  staged upstream paths, and pristine upstream.
- Artifact: `dist/RenegadeVita-A3.5-dev72.vpk` SHA-256 is
  `aec6c8ee0f16743133dff2f4f762470cf66f3c1c0b6deae087e270d76c7315c8`;
  ELF SHA-256 is
  `8d5f7e8ced9f004f3a6703b97a5d7c8e3059826c035a708b8e53fc394c024fa4`;
  MAP SHA-256 is
  `1438f637696c7d7e55de47ab6bbf611af3847cab6fa2f5eed0d0b3319306c53b`;
  diagnostics bundle SHA-256 is
  `901a82aa3d2f9fd6ce805fa288aaba45fc8c3c67272eb6ab2c716561f0783a4d`.
- Boundary: dev72 has not been physically tested and no Vita deployment was
  attempted. The next hardware run should manually install dev72, verify M00
  sky/materials, muzzle rectangle and other alpha cutouts, Logan dialogue text,
  Logan audible dialogue and timing, material/texture appearance, and route
  fidelity, then inspect
  `ux0:data/renegade/user/logs/a35-dev72-runtime.log`, especially
  `texture loaded`, `loaded_dds/tga`, `checker_bind`, `invalid_bind`,
  `unsupported_stages`, `first original indexed VertexMaterial mapper`,
  `first generated texture coordinates`, `output_stream`,
  `last_output_stream`, `last_stream_mix`, active stream
  position/length/cursor/frames/loops/volume/pan, speech duration/dropoff/
  distance, stream bytes/frames/mix counters, and conversation state if
  dialogue or materials remain incorrect.

## 2026-08-28 — dev71 original ShaderClass alpha-test reference semantics

`[██████████] 12/12 canonical source/build gates complete`

- Renderer boundary: dev71 preserves dev70 indexed/dynamic texture-coordinate
  replay and carries original `ShaderClass::Apply()` alpha-test reference and
  compare semantics into the Vita fixed-function backend. Normal cutout
  shaders now translate to reference `0x60` with `PASS_GEQUAL`; inverse source
  alpha cutouts translate to `0xff - 0x60` with `PASS_LEQUAL`.
- Runtime purpose: this replaces the previous zero-threshold
  `glAlphaFunc(GL_GREATER, 0.0f)` approximation below the original shader
  abstraction, reducing alpha-tested fringe or rectangle artifacts such as
  muzzle flashes, sprites, fences, and other retail cutout materials without
  moving shader ownership out of WW3D.
- Validation: focused indexed texture-state contracts passed 11/11. The fast
  no-deploy candidate passed 60 focused tests, the original `DDSFileClass`
  `.tga`-to-`.dds` executable contract 11/11, package identity checks, and VPK
  packaging. The full canonical no-deploy build passed retained
  host-validation reuse, the current lightweight render-state contract 5/5,
  the DDS/TGA alias contract 11/11, 76 host unittest checks, deterministic
  restaging, source integration reporting, ARM link/package, compressed VPK
  validation, identity verification, diagnostics bundle generation, SHA
  manifest verification, and retail exclusion.
- Source report: the canonical integration report records 451 upstream original
  Westwood translation units plus one staged original-owner extraction
  (`staging/commando/loadingscreen.cpp`), 26 Vita platform/renderer/validation
  files, 118 deterministic patch files covering 238 mechanically patched
  staged upstream paths, and pristine upstream.
- Artifact: `dist/RenegadeVita-A3.5-dev71.vpk` SHA-256 is
  `79db5808b4a5e03f1ab5ac0977970ca992ca5fdbc313167072005b7890c89c14`;
  ELF SHA-256 is
  `58d7cad97f54f9e84ce1d9f73bccdd34a6a27f3fb82fc26399a8c329bc644d3e`;
  MAP SHA-256 is
  `681617ebfb098d1ae69299460f83881f7539cbd26a7ce7690c8d204ee143c25d`;
  diagnostics bundle SHA-256 is
  `853c0164b3ba3848a452b6b356dd41c97e9fe6242eda2030c2d14e7ea16bcf16`.
- Boundary: dev71 has not been physically tested and no Vita deployment was
  attempted. The next hardware run should manually install dev71, verify M00
  sky/materials, muzzle rectangle and other alpha cutouts, Logan dialogue text,
  Logan audible dialogue and timing, material/texture appearance, and route
  fidelity, then inspect
  `ux0:data/renegade/user/logs/a35-dev71-runtime.log`, especially
  `texture loaded`, `loaded_dds/tga`, `checker_bind`, `invalid_bind`,
  `unsupported_stages`, `first original indexed VertexMaterial mapper`,
  `first generated texture coordinates`, `output_stream`,
  `last_output_stream`, `last_stream_mix`, active stream
  position/length/cursor/frames/loops/volume/pan, speech duration/dropoff/
  distance, stream bytes/frames/mix counters, and conversation state if
  dialogue or materials remain incorrect.

## 2026-08-28 — dev70 indexed dynamic texture-coordinate replay

`[██████████] 12/12 canonical source/build gates complete`

- Renderer boundary: the indexed Vita `DX8Wrapper` submit path now replays
  original `VertexMaterialClass` texture-coordinate mapper/default state before
  submitting dynamic/indexed geometry. Materials with a
  `TextureMapperClass` call the original `Apply()` path; materials without a
  mapper restore original pass-through `D3DTSS_TEXCOORDINDEX` UV source and
  disabled `D3DTSS_TEXTURETRANSFORMFLAGS` state.
- Indexed submit: the Vita renderer now preserves UV0 and UV1 for the legacy
  dynamic TEX2 layout, captures original DX8 texture-coordinate stage state,
  selects the original material UV source, and evaluates camera-space normal,
  camera-space position, and camera-space reflection-vector generated
  coordinates plus DX8 texture transforms with the submitted row-vector
  world/view matrices.
- Runtime purpose: this extends the dev68/dev69 material-mapper fix beyond the
  direct `MeshClass` path to original indexed/dynamic submissions, covering the
  remaining stage-1 and generated-coordinate cases that can present as
  pink/black or wrongly mapped retail materials without taking ownership away
  from WW3D.
- Validation: focused indexed texture-state contracts passed 10/10. The fast
  no-deploy candidate passed 59 focused tests, the original `DDSFileClass`
  `.tga`-to-`.dds` executable contract 11/11, package identity checks, and VPK
  packaging. The full canonical no-deploy build passed retained
  host-validation reuse, 75 host unittest checks, deterministic restaging,
  source integration reporting, ARM link/package, compressed VPK validation,
  identity verification, diagnostics bundle generation, SHA manifest
  verification, and retail exclusion.
- Source report: the canonical integration report records 451 upstream original
  Westwood translation units plus one staged original-owner extraction
  (`staging/commando/loadingscreen.cpp`), 26 Vita platform/renderer/validation
  files, 118 deterministic patch files covering 238 mechanically patched
  staged upstream paths, and pristine upstream.
- Artifact: `dist/RenegadeVita-A3.5-dev70.vpk` SHA-256 is
  `3693687d9608734ace67d703e5e9347e37273d09e767a91fb9fc869263b708ec`;
  ELF SHA-256 is
  `4e9038f15b13707a362b856f57bd49631fa28d5f90ad0fb0fe98dd7510b464e2`;
  MAP SHA-256 is
  `a83f95df401da2926012af69c5690074c828c9845fe7ded9f4b7ad2803639ccf`;
  diagnostics bundle SHA-256 is
  `97a58b35a2b1477686a4199f1853a68e52e2d64b4901df64bf6a9de1dba5374c`.
- Boundary: dev70 has not been physically tested and no Vita deployment was
  attempted. The next hardware run should manually install dev70, verify M00
  sky/retail texture stage-1 materials, Logan audible dialogue and timing,
  dialog/message text, material/texture appearance, and route fidelity, then
  inspect `ux0:data/renegade/user/logs/a35-dev70-runtime.log`, especially
  `first original indexed VertexMaterial mapper`,
  `first generated texture coordinates`, `texture loaded`, `loaded_dds/tga`,
  `checker_bind`, `invalid_bind`, `unsupported_stages`, `output_stream`,
  `last_output_stream`, `last_stream_mix`, active stream
  position/length/cursor/frames/loops/volume/pan, speech duration/dropoff/
  distance, stream bytes/frames/mix counters, and conversation state if
  dialogue or materials remain incorrect.

## 2026-08-28 — dev69 generated texture-coordinate evaluation

`[██████████] 12/12 canonical source/build gates complete`

- Renderer boundary: the direct Vita `MeshClass` submit path now reads back
  original DX8 texture-coordinate stage state after replaying
  `TextureMapperClass::Apply()`, including `D3DTSS_TEXCOORDINDEX`,
  `D3DTSS_TEXTURETRANSFORMFLAGS`, and the `D3DTS_TEXTURE0+n` transform matrix.
  Because the VitaGL public API available here only exposes 2D immediate
  texture coordinates, dev69 evaluates original generated coordinates on the
  CPU for camera-space normal, camera-space position, and camera-space
  reflection-vector modes, then submits the final 2D coordinates through the
  existing Vita fixed-function path.
- Transform semantics: dev69 applies the original DX8 texture transform flags
  on the CPU, including projected divide for projected mapper states, and
  resets Vita GL texture matrices for direct mesh submissions so mapper
  transforms are not applied twice. Plain pass-through stages still use the UV
  array selected by the original material state rather than the texture-stage
  number.
- Runtime purpose: this closes the next material-mapper gap behind
  pink/black or incorrectly mapped retail materials while preserving original
  WW3D material ownership. The next hardware log should show whether remaining
  visual issues are missing texture loads/fallback binds or material states
  beyond 2D generated-coordinate submission.
- Validation: focused indexed texture-state and generated-coordinate contracts
  passed 9/9. The fast no-deploy candidate passed 58 focused tests, the
  original `DDSFileClass` `.tga`-to-`.dds` executable contract 11/11, package
  identity checks, and VPK packaging. The full canonical no-deploy build passed
  retained host-validation reuse, 74 host unittest checks, deterministic
  restaging, source integration reporting, ARM link/package, compressed VPK
  validation, identity verification, diagnostics bundle generation, SHA
  manifest verification, and retail exclusion.
- Source report: the canonical integration report records 451 upstream original
  Westwood translation units plus one staged original-owner extraction
  (`staging/commando/loadingscreen.cpp`), 26 Vita platform/renderer/validation
  files, 118 deterministic patch files covering 238 mechanically patched staged
  upstream paths, and pristine upstream.
- Artifact: `dist/RenegadeVita-A3.5-dev69.vpk` SHA-256 is
  `bddc2433707a23682cefecca2c9b63c19b9276e0b612bab65da9a5babc08ed2e`;
  ELF SHA-256 is
  `366f1be5ea978a5500041e5052f6a61d95bef476fefbd6338f2031d9e330a626`;
  MAP SHA-256 is
  `07828227773fab269d8f4fa72633f32900d98637d86bddf9fb2da77a6252f114`;
  diagnostics bundle SHA-256 is
  `377016462fbbcb793e1a17b2fb805f1b963ef607204f5786724946912aaca886`.
- Boundary: dev69 has not been physically tested and no Vita deployment was
  attempted. The next hardware run should manually install dev69, verify Logan
  audible dialogue and timing, dialog/message text, material/texture
  appearance, and route fidelity, then inspect
  `ux0:data/renegade/user/logs/a35-dev69-runtime.log`, especially
  `output_stream`, `last_output_stream`, `last_stream_mix`, active stream
  position/length/cursor/frames/loops/volume/pan, speech duration/dropoff/
  distance, stream bytes/frames/mix counters, fact/estimate/untrimmed/trimmed
  values, conversation state, `texture loaded`, `loaded_dds/tga`,
  `checker_bind`, `invalid_bind`, `unsupported_stages`,
  `first original VertexMaterial mapper`, and the new
  `first generated texture coordinates` breadcrumb if dialogue remains silent
  or materials remain incorrect.

## 2026-08-28 — dev68 original material mapper texture-coordinate state

`[██████████] 12/12 canonical source/build gates complete`

- Renderer boundary: the direct Vita `MeshClass` submit path now groups base
  material submissions by original `VertexMaterialClass` as well as texture and
  shader state, then replays original per-stage texture-coordinate state before
  binding textures. If an original material has a `TextureMapperClass`, dev68
  calls its `Apply()` path; otherwise it restores the original default
  `D3DTSS_TEXCOORDINDEX` pass-through UV source and disabled texture transform
  state. The direct emitter now also selects the texture-coordinate arrays by
  that original material UV source instead of assuming stage index equals UV
  array index.
- Vita DX8 boundary: `D3DTSS_TEXCOORDINDEX` and
  `D3DTSS_TEXTURETRANSFORMFLAGS` are now retained as supported sampler-stage
  state, and texture-stage transforms are applied through the Vita texture
  matrix path when `D3DTS_TEXTURE0+n` or transform flags change. This preserves
  original mapper/default UV ownership below WW3D instead of baking a new
  renderer-side interpretation.
- Runtime purpose: the next material/texture hardware log can determine whether
  remaining pink/black or mis-mapped surfaces are caused by missing retail
  texture loads, fallback binds, or previously skipped original mapper/UV
  stage state and UV-array selection.
- Validation: focused indexed texture-state, texture provenance,
  mission-conversation diagnostics, and Vita audio-provider contracts passed
  26/26. The fast no-deploy candidate passed 57 focused tests, the original
  `DDSFileClass` `.tga`-to-`.dds` executable contract 11/11, package identity
  checks, and VPK packaging. The full canonical no-deploy build passed retained
  host-validation reuse, 73 host unittest checks, deterministic restaging,
  source integration reporting, ARM link/package, compressed VPK validation,
  identity verification, diagnostics bundle generation, SHA manifest
  verification, and retail exclusion.
- Source report: the canonical integration report records 451 upstream original
  Westwood translation units plus one staged original-owner extraction
  (`staging/commando/loadingscreen.cpp`), 26 Vita platform/renderer/validation
  files, 118 deterministic patch files covering 238 mechanically patched staged
  upstream paths, and pristine upstream.
- Artifact: `dist/RenegadeVita-A3.5-dev68.vpk` SHA-256 is
  `bccfb2e4ef99b5246331b3bb4d6c09e46364c314eedfc19b98c9fe0e236b80d8`;
  ELF SHA-256 is
  `47248ea91ecf177fe7ad38ed3373d4b68c4a628b71aaf4081b2a60db16c88c7a`;
  diagnostics bundle SHA-256 is
  `4a5707300a4b072cf10609dbf279de68ad44d2be529a423a7eb93875492e6883`.
- Boundary: dev68 has not been physically tested and no Vita deployment was
  attempted. The next hardware run should manually install dev68, verify Logan
  audible dialogue and timing, dialog/message text, material/texture
  appearance, and route fidelity, then inspect
  `ux0:data/renegade/user/logs/a35-dev68-runtime.log`, especially
  `output_stream`, `last_output_stream`, `last_stream_mix`, active stream
  position/length/cursor/frames/loops/volume/pan, speech duration/dropoff/
  distance, stream bytes/frames/mix counters, fact/estimate/untrimmed/trimmed
  values, conversation state, `texture loaded`, `loaded_dds/tga`,
  `checker_bind`, `invalid_bind`, `unsupported_stages`, and the new
  `first original VertexMaterial mapper` breadcrumb if dialogue remains silent
  or materials remain incorrect.

## 2026-08-28 — dev67 null texture stage-disable semantics

`[██████████] 12/12 canonical source/build gates complete`

- Renderer boundary: `IDirect3DDevice8::SetTexture(NULL)` now disables the
  requested Vita texture stage for every stage instead of routing stage 0
  through an invalid texture bind. This matches D3D disable semantics and keeps
  `invalid_bind` focused on real non-null invalid/unuploaded texture binds while
  checkerboard fallback binds remain independently counted.
- Runtime purpose: the next material/texture hardware log can separate
  intentional fixed-function stage disables from actual missing or bad retail
  texture submissions. This helps diagnose any remaining pink/black square
  materials without changing original `TextureClass`, `MeshClass`, or WW3D
  ownership.
- Validation: focused texture/indexed/conversation contracts passed 24/24, the
  fast no-deploy candidate passed 56 focused tests, the original `DDSFileClass`
  `.tga`-to-`.dds` executable contract 11/11, package identity checks, and VPK
  packaging. The full canonical no-deploy build passed retained host-validation
  reuse, 72 host unittest checks, deterministic restaging, source integration
  reporting, ARM link/package, compressed VPK validation, identity
  verification, diagnostics bundle generation, SHA manifest verification, and
  retail exclusion.
- Source report: the canonical integration report records 451 upstream original
  Westwood translation units plus one staged original-owner extraction
  (`staging/commando/loadingscreen.cpp`), 26 Vita platform/renderer/validation
  files, 118 deterministic patch files covering 238 mechanically patched staged
  upstream paths, and pristine upstream.
- Artifact: `dist/RenegadeVita-A3.5-dev67.vpk` SHA-256 is
  `3c6279ed13db704e2416b41ff073dace7d772da20d7424541a1846017efb9403`;
  ELF SHA-256 is
  `681c043c98c706a18f1b1a55a6b539ae19aa542db1f7d2e83d73e189a620ec92`;
  diagnostics bundle SHA-256 is
  `e11222eac9d65f7988eca42bfe71f8f91683c87086a4cabdc4f351047264cb3d`.
- Boundary: dev67 has not been physically tested and no Vita deployment was
  attempted. The next hardware run should manually install dev67, verify Logan
  audible dialogue and timing, dialog/message text, material/texture appearance,
  and route fidelity, then inspect
  `ux0:data/renegade/user/logs/a35-dev67-runtime.log`, especially
  `output_stream`, `last_output_stream`, `last_stream_mix`, active stream
  position/length/cursor/frames/loops/volume/pan, speech duration/dropoff/
  distance, stream bytes/frames/mix counters, fact/estimate/untrimmed/trimmed
  values, conversation state, `texture loaded`, `loaded_dds/tga`,
  `checker_bind`, `invalid_bind`, `unsupported_stages`, and first original
  `MeshClass` stage-1 texture breadcrumbs if dialogue remains silent or
  materials remain incorrect.

## 2026-08-28 — dev66 Vita stream-output submission telemetry

`[██████████] 12/12 canonical source/build gates complete`

- Audio boundary: the Vita Miles-compatible provider now records streamed
  audio that is actually submitted successfully to `sceAudioOutOutput` as
  `output_stream=buffers/frames/nonzero/peak` and
  `last_output_stream=active/frames/nonzero/peak`. Sample restart now rewinds
  exhausted finite sample/stream cursors before playback resumes, preventing a
  restarted handle from reporting `started` while mixing silence.
- Runtime purpose: the next Logan hardware run can separate stream decoded but
  not submitted, stream submitted as silence, and stream submitted with nonzero
  samples. This remains below original WWAudio/conversation ownership.
- Validation: focused audio/dialogue contracts passed 13/13, the fast
  no-deploy candidate passed 56 focused tests, the original `DDSFileClass`
  `.tga`-to-`.dds` executable contract 11/11, package identity checks, and VPK
  packaging. The full canonical no-deploy build passed retained host-validation
  reuse, 72 host unittest checks, deterministic restaging, source integration
  reporting, ARM link/package, compressed VPK validation, identity
  verification, diagnostics bundle generation, SHA manifest verification, and
  retail exclusion.
- Source report: the canonical integration report records 451 upstream
  original Westwood translation units plus one staged original-owner extraction
  (`staging/commando/loadingscreen.cpp`), 26 Vita platform/renderer/validation
  files, 118 deterministic staging patches, and pristine upstream.
- Artifact: `dist/RenegadeVita-A3.5-dev66.vpk` SHA-256 is
  `99ad437fc05c9a8bde760df346816a33103875f620a605ba0fa7c9ca7a316543`;
  ELF SHA-256 is
  `6a1883663e36dd4556564c05fa804307a12f641369e30c6697c2cfcf45e2ce85`;
  diagnostics bundle SHA-256 is
  `46c0cac6a9a46417e96dd5beb9942439ad5ab647dc9262dabe6ed58c4c99705a`.
- Boundary: dev66 has not been physically tested and no Vita deployment was
  attempted. The next hardware run should manually install dev66, verify Logan
  audible dialogue and timing, dialog/message text, material/texture
  appearance, and route fidelity, then inspect
  `ux0:data/renegade/user/logs/a35-dev66-runtime.log`, especially
  `output_stream`, `last_output_stream`, `last_stream_mix`, active stream
  position/length/cursor/frames/loops/volume/pan, speech duration/dropoff/
  distance, stream bytes/frames/mix counters, fact/estimate/untrimmed/trimmed
  values, conversation state, `texture loaded`, `loaded_dds/tga`,
  `checker_bind`, `invalid_bind`, `unsupported_stages`, and first original
  `MeshClass` stage-1 texture breadcrumbs if dialogue remains silent or
  materials remain incorrect.

## 2026-08-28 — dev65 per-buffer stream-mix telemetry

`[██████████] 12/12 canonical source/build gates complete`

- Audio boundary: the Vita Miles-compatible provider now reports the most
  recent streamed-audio mix buffer as
  `last_stream_mix=active/frames/nonzero/peak`, alongside the retained
  cumulative stream mix counters and dev64 active-stream cursor, length, loop,
  volume, and pan telemetry.
- Runtime purpose: the next Logan hardware run can distinguish a stream that
  is active and currently contributing nonzero samples from an active stream
  mixing silence, a paused/not-serviced stream, or a completed stream. This
  remains below original WWAudio ownership and preserves original
  `ActiveConversationClass`, `SoldierGameObj`, and conversation scheduling.
- Validation: focused audio/dialogue/runtime/build contract checks passed
  19/19, the fast no-deploy candidate passed 56 focused tests, the original
  `DDSFileClass` `.tga`-to-`.dds` executable contract 11/11, package identity
  and hash checks, and VPK packaging. The full canonical no-deploy build
  passed retained host-validation reuse, 72 host unittest checks,
  deterministic restaging, source integration reporting, ARM link/package,
  compressed VPK validation, identity verification, diagnostics bundle
  generation, SHA manifest verification, and retail exclusion.
- Source report: the canonical integration report records 451 upstream
  original Westwood translation units plus one staged original-owner extraction
  (`staging/commando/loadingscreen.cpp`), 26 Vita platform/renderer/validation
  files, 118 deterministic staging patches, and pristine upstream.
- Artifact: `dist/RenegadeVita-A3.5-dev65.vpk` SHA-256 is
  `f4d9ff1837d224a3f9a5ec995482801a4c9a21faa3b3bcc83a625787702d995f`;
  ELF SHA-256 is
  `c51f7abc55e4dcb9a7ea09f32d581fcd7dc1c944b8b0797bd0a7702dda85868b`;
  diagnostics bundle SHA-256 is
  `3c93d689ccbc3578079fc8fab006869af963753f2e71fab895d280f21d0738b4`.
- Boundary: dev65 has not been physically tested and no Vita deployment was
  attempted. The next hardware run should manually install dev65, verify Logan
  audible dialogue and timing, dialog/message text, material/texture
  appearance, and route fidelity, then inspect
  `ux0:data/renegade/user/logs/a35-dev65-runtime.log`, especially
  `last_stream_mix=active/frames/nonzero/peak`, active stream
  position/length/cursor/frames/loops/volume/pan, speech duration/dropoff/
  distance, stream bytes/frames/mix counters, fact/estimate/untrimmed/trimmed
  values, conversation state, `texture loaded`, `loaded_dds/tga`,
  `checker_bind`, `invalid_bind`, `unsupported_stages`, and first original
  `MeshClass` stage-1 texture breadcrumbs if dialogue remains silent or
  materials remain incorrect.

## 2026-08-28 — dev64 active streamed-audio telemetry

`[██████████] 12/12 canonical source/build gates complete`

- Audio boundary: the Vita Miles-compatible provider now reports the first
  active streamed sample's playback position, length, cursor frame, total
  frames, loop count, volume, and pan in bounded runtime stats. Finite streams
  that exhaust their final loop now report `loops_remaining=0` before stopping,
  so original loop-count polling no longer sees a stale final-loop value after
  playback has ended.
- Runtime purpose: the next Logan hardware run can distinguish a decoded stream
  that is active but inaudible from a stream that never advances, stalls while
  paused, finishes early, or carries unexpected loop/volume/pan state. This
  stays under the Miles-compatible Vita provider and preserves original
  `ActiveConversationClass`, `SoldierGameObj`, and WWAudio ownership.
- Validation: focused audio/dialogue contract checks passed 19/19, the fast
  no-deploy candidate passed 56 focused tests, the original `DDSFileClass`
  `.tga`-to-`.dds` executable contract 11/11, package identity and hash checks,
  and VPK packaging. The full canonical no-deploy build passed retained
  host-validation reuse, 72 host unittest checks, deterministic restaging,
  source integration reporting, ARM link/package, compressed VPK validation,
  identity verification, diagnostics bundle generation, SHA manifest
  verification, and retail exclusion.
- Source report: the canonical integration report records 451 upstream
  original Westwood translation units plus one staged original-owner extraction
  (`staging/commando/loadingscreen.cpp`), 26 Vita platform/renderer/validation
  files, 118 deterministic staging patches, and pristine upstream.
- Artifact: `dist/RenegadeVita-A3.5-dev64.vpk` SHA-256 is
  `f9c99affa44f24cfa058d1cf9c6021a932c6c61f28cdd31cbe15c78248056706`;
  ELF SHA-256 is
  `64c3b4b43208a09a20a782dd71ca803648420e690ac80f6b3b733fa47cba8efc`;
  diagnostics bundle SHA-256 is
  `800f59e911350b4dbd2f9a6bb076add9fce6451cc4fd5011255a7d7ed376fb67`.
- Boundary: dev64 has not been physically tested and no Vita deployment was
  attempted. The next hardware run should manually install dev64, verify
  Logan audible dialogue and timing, dialog/message text, material/texture
  appearance, and route fidelity, then inspect
  `ux0:data/renegade/user/logs/a35-dev64-runtime.log`, especially active
  stream position/length/cursor/frames/loops/volume/pan, speech duration/
  dropoff/distance, stream bytes/frames/mix/last_stream fields,
  fact/estimate/untrimmed/trimmed values, conversation state, `texture loaded`,
  `loaded_dds/tga`, `checker_bind`, `invalid_bind`, `unsupported_stages`, and
  first original `MeshClass` stage-1 texture breadcrumbs if dialogue remains
  silent or materials remain incorrect.

## 2026-08-28 — dev63 Vita DX8 bound-texture lifetime

`[██████████] 12/12 canonical source/build gates complete`

- Renderer boundary: `IDirect3DDevice8::SetTexture` now retains the texture
  stored in the Vita DX8 bound-stage cache with COM-style `AddRef`/`Release`
  semantics, matching the lifetime contract expected by original
  `DX8Wrapper::Set_DX8_Texture` and D3D texture binding.
- Runtime purpose: material and fallback churn can no longer leave
  `g_texture_stage_textures[]` pointing at a released `TextureClass` backend
  object. This is a narrow Vita DX8 boundary fix aimed at pink/black
  checkerboard fallback and stale retail material binds without changing
  original `TextureClass`, `MaterialPassClass`, `ShaderClass`, or mesh
  ownership.
- Validation: the texture provenance contract now covers bound-stage texture
  lifetime ordering. Focused texture provenance passed 5/5, the broader local
  texture/audio/loading/indexed/staging contract set passed 37/37, and the
  fast no-deploy candidate passed 56 focused tests, the original
  `DDSFileClass` `.tga`-to-`.dds` executable contract 11/11, package identity
  and hash checks, and VPK packaging. The full canonical no-deploy build passed
  retained host-validation reuse, 72 host unittest checks, deterministic
  restaging, source integration reporting, ARM link/package, compressed VPK
  validation, identity verification, diagnostics bundle generation, SHA
  manifest verification, and retail exclusion.
- Source report: the canonical integration report records 451 upstream
  original Westwood translation units plus one staged original-owner extraction
  (`staging/commando/loadingscreen.cpp`), 26 Vita platform/renderer/validation
  files, 118 deterministic staging patches, and pristine upstream.
- Artifact: `dist/RenegadeVita-A3.5-dev63.vpk` SHA-256 is
  `d749f1db9318ffd6b6c03c6edb591a0b1dd6fa81397e922f84d22382ff01ecd9`;
  ELF SHA-256 is
  `1ec4e648bbff13c0f3c8408e06f1fe490395104a3f56872cd4dd21b568c814c6`;
  diagnostics bundle SHA-256 is
  `c276573302ec12b4fef38b1b28a9200fc584c1ddde38c690fffff99dbbfc84bf`.
- Boundary: dev63 has not been physically tested and no Vita deployment was
  attempted. The next hardware run should manually install dev63, verify
  Logan audible dialogue and timing, dialog/message text, material/texture
  appearance, and route fidelity, then inspect
  `ux0:data/renegade/user/logs/a35-dev63-runtime.log`, especially stream
  loop-count behavior, speech duration/dropoff/distance, stream bytes/frames/
  mix/last_stream fields, fact/estimate/untrimmed/trimmed values,
  conversation state, `texture loaded`, `loaded_dds/tga`, `checker_bind`,
  `invalid_bind`, `unsupported_stages`, and first original `MeshClass` stage-1
  texture breadcrumbs if dialogue remains silent or materials remain
  incorrect.

## 2026-08-28 — dev62 WWAudio stream loop-count return

`[██████████] 12/12 canonical source/build gates complete`

- Audio boundary: staged original `SoundStreamHandleClass` now returns the
  provider value from `AIL_stream_loop_count(StreamHandle)` instead of
  discarding it and always reporting zero. The deterministic WWAudio runtime
  correctness patch carries the same fix so clean restaging preserves it.
- Runtime purpose: any original WWAudio or conversation-side caller that polls
  stream loop completion now sees the Miles-compatible provider state. This is
  a source-side correctness fix under original WWAudio ownership, not a custom
  conversation scheduler.
- Validation: focused dialogue/audio diagnostics passed 12/12, the Vita audio
  provider loop-count contract passed, the combined local provider/dialogue/
  staging contract set passed 16/16, and the fast no-deploy candidate passed
  55 focused tests, the original `DDSFileClass` `.tga`-to-`.dds` executable
  contract 11/11, ARM package identity/hash checks, and VPK packaging. The
  full canonical no-deploy build passed retained host-validation reuse, 72
  host unittest checks, deterministic restaging, source integration reporting,
  ARM link/package, compressed VPK validation, identity verification,
  diagnostics bundle generation, SHA manifest verification, and retail
  exclusion.
- Source report: the canonical integration report records 451 upstream
  original Westwood translation units plus one staged original-owner extraction
  (`staging/commando/loadingscreen.cpp`), 26 Vita platform/renderer/validation
  files, 118 deterministic staging patches, and pristine upstream.
- Artifact: `dist/RenegadeVita-A3.5-dev62.vpk` SHA-256 is
  `f501288b7bb302923502fcf89e0b74c3f35a5aaa824f0eb68531b05cf05acddd`;
  ELF SHA-256 is
  `9d16c948e3212c705333fddb50fd42cc6eed7816d8af350cdd8312e062d03ef7`;
  diagnostics bundle SHA-256 is
  `f0eda4ec27dc3c292fed92d3fc415738c069548a94951f600e4c472eaff15f9b`.
- Boundary: dev62 has not been physically tested and no Vita deployment was
  attempted. The next hardware run should manually install dev62, verify
  Logan audible dialogue and timing, dialog/message text, material/texture
  appearance, and route fidelity, then inspect
  `ux0:data/renegade/user/logs/a35-dev62-runtime.log`, especially stream
  loop-count behavior, speech duration/dropoff/distance, stream bytes/frames/
  mix/last_stream fields, fact/estimate/untrimmed/trimmed values,
  conversation state, and texture/material provenance if dialogue remains
  silent or materials remain incorrect.

## 2026-08-28 — dev61 streamed-dialogue fact runtime telemetry

`[██████████] 12/12 canonical source/build gates complete`

- Audio boundary: dev61 preserves exact RIFF `fact` frame handling and now
  carries fact, estimated, untrimmed, and trimmed streamed-dialogue frame
  metadata into Miles runtime stats. The A3.5 audio log line now includes
  `frames/fact/estimate/untrimmed/trimmed/rate/vol/pan`.
- Runtime purpose: the next Logan hardware run can prove whether streamed
  dialogue used exact `fact` frames or estimated frames, and whether padded
  decode output was trimmed, while original `ActiveConversationClass`,
  `SoldierGameObj`, and WWAudio ownership remain unchanged.
- Validation: focused dialogue/audio diagnostics passed 12/12, and the broader
  local texture/audio/loading/indexed/skin contract set passed 39/39. The fast
  no-deploy candidate passed 54 focused tests, the original `DDSFileClass`
  `.tga`-to-`.dds` executable contract 11/11, ARM package identity/hash
  checks, and the full canonical no-deploy build passed retained
  host-validation reuse, 71 host unittest checks, deterministic restaging,
  source integration reporting, ARM link/package, compressed VPK validation,
  identity verification, diagnostics bundle generation, SHA manifest
  verification, and retail exclusion.
- Source report: the canonical integration report records 451 upstream
  original Westwood translation units plus one staged original-owner extraction
  (`staging/commando/loadingscreen.cpp`), 26 Vita platform/renderer/validation
  files, 118 deterministic staging patches, and pristine upstream.
- Artifact: `dist/RenegadeVita-A3.5-dev61.vpk` SHA-256 is
  `37c0bcf7d1ffdfff45787437fd2128915bc18d83a8b7c3ac23144704b9108d23`;
  ELF SHA-256 is
  `cfae7e566d9eccbee058f5b82df5ff03fbc8d13d2d386bf32fdfc90165a0442a`;
  diagnostics bundle SHA-256 is
  `cde3d3817cfb19cd5c99d655bccd9e2d577a97cdba9e71141f806d6fc0e1b017`.
- Boundary: dev61 has not been physically tested and no Vita deployment was
  attempted. The next hardware run should manually install dev61, verify
  Logan audible dialogue and timing, dialog/message text, material/texture
  appearance, and route fidelity, then inspect
  `ux0:data/renegade/user/logs/a35-dev61-runtime.log`, especially speech
  duration/dropoff/distance, stream bytes/frames/mix/last_stream fields, the
  new fact/estimate/untrimmed/trimmed values, conversation state, and
  texture/material provenance if dialogue remains silent or materials remain
  incorrect.

## 2026-08-28 — dev60 WAVE fact-duration metadata

`[██████████] 12/12 canonical source/build gates complete`

- Audio boundary: the Vita WAVE inspector now reads RIFF `fact` chunks and
  preserves the exact decoded sample-frame count as `fact_sample_frames`.
  Streamed-dialogue `sample_frames` prefers that exact metadata before falling
  back to bounded estimates, and decoded ADPCM output is trimmed to the exact
  frame count before playback. `AILSOUNDINFO.samples` still feeds the original
  WWAudio `SoundBufferClass::Determine_Stats` duration path.
- Runtime purpose: this tightens Logan conversation timing and trims padded
  ADPCM tails without moving ownership out of original
  `ActiveConversationClass`, `SoldierGameObj`, or WWAudio scheduling.
- Validation: focused dialogue/audio diagnostics passed 12/12, and the broader
  local texture/audio/loading/indexed/skin contract set passed 39/39. The fast
  no-deploy candidate passed 54 focused tests, the original `DDSFileClass`
  `.tga`-to-`.dds` executable contract 11/11, ARM package identity/hash
  checks, and the full canonical no-deploy build passed retained
  host-validation reuse, 71 host unittest checks, deterministic restaging,
  source integration reporting, ARM link/package, compressed VPK validation,
  identity verification, diagnostics bundle generation, SHA manifest
  verification, and retail exclusion.
- Source report: the canonical integration report records 451 upstream
  original Westwood translation units plus one staged original-owner extraction
  (`staging/commando/loadingscreen.cpp`), 26 Vita platform/renderer/validation
  files, 118 deterministic staging patches, and pristine upstream.
- Artifact: `dist/RenegadeVita-A3.5-dev60.vpk` SHA-256 is
  `98c32184861058c3168f511c8bef9fe9bb9db77055626d3a506ef217f556ad51`;
  ELF SHA-256 is
  `dd7b7b02c073dc3ba75583b3178a3d0ebc79f55f214e1d0170291689444c99be`;
  diagnostics bundle SHA-256 is
  `e57bb82db926688e87b88a65e58401b4696a8c4cf4a6727424b192096a8422fb`.
- Boundary: dev60 has not been physically tested and no Vita deployment was
  attempted. The next hardware run should manually install dev60, verify
  Logan audible dialogue and timing, dialog/message text, material/texture
  appearance, and route fidelity, then inspect
  `ux0:data/renegade/user/logs/a35-dev60-runtime.log`, especially speech
  duration/dropoff/distance, stream bytes/frames/mix/last_stream fields,
  conversation state, WAVE duration behavior, and texture/material provenance
  if dialogue remains silent or materials remain incorrect.

## 2026-08-28 — dev59 streamed-dialogue duration metadata

`[██████████] 12/12 canonical source/build gates complete`

- Audio boundary: the Vita Miles-compatible WAVE inspection path now reports
  decoded sample-frame counts through `AILSOUNDINFO.samples`. The staged
  original `SoundBufferClass::Determine_Stats` path computes streamed-dialogue
  duration from `samples / rate`, falling back to the old byte-length estimate
  only when frame metadata is unavailable.
- Runtime purpose: original `ActiveConversationClass` and `SoldierGameObj`
  conversation scheduling use `speech->Get_Duration()`. For streamed ADPCM
  dialogue, using compressed RIFF byte length could skew Logan conversation
  timing and route fidelity even when the sound object and stream provider
  were present.
- Validation: focused dialogue/audio diagnostics passed 12/12, and the broader
  local texture/audio/loading/indexed/skin contract set passed 39/39. The fast
  no-deploy candidate passed 54 focused tests, the original `DDSFileClass`
  `.tga`-to-`.dds` executable contract 11/11, ARM package identity/hash checks,
  and the full canonical no-deploy build passed retained host-validation reuse,
  71 host unittest checks, deterministic restaging, source integration
  reporting, ARM link/package, compressed VPK validation, identity
  verification, diagnostics bundle generation, SHA manifest verification, and
  retail exclusion.
- Source report: the canonical integration report records 451 upstream
  original Westwood translation units plus one staged original-owner extraction
  (`staging/commando/loadingscreen.cpp`), 26 Vita platform/renderer/validation
  files, 118 deterministic staging patches, and pristine upstream.
- Artifact: `dist/RenegadeVita-A3.5-dev59.vpk` SHA-256 is
  `f183d356ae60692f88d7676e06f8077af1537bb0398c6c5766e7f1225d7e5ab4`;
  ELF SHA-256 is
  `13d823d8f2d3641e4af4e34e9ddfdfc5acb08de658750d8ce720d2c3242b227e`.
- Boundary: dev59 has not been physically tested and no Vita deployment was
  attempted. The next hardware run should manually install dev59, verify
  Logan audible dialogue, dialog/message text, material/texture appearance, and
  route fidelity, then inspect
  `ux0:data/renegade/user/logs/a35-dev59-runtime.log`, especially speech
  duration/dropoff/distance, stream bytes/frames/mix/last-stream fields,
  conversation state, and texture/material provenance if dialogue remains
  silent or materials remain incorrect.

## 2026-08-28 — dev58 stage-1 multitexture boundary

`[██████████] 12/12 canonical source/build gates complete`

- Renderer boundary: the Vita DX8/WW3D boundary now treats the original two
  texture stages as real backend state instead of declaring stage 1
  unsupported. `IDirect3DDevice8::SetTexture`, sampler state, and texture-stage
  combiner state now track both original stages, and the direct Vita
  `MeshClass` submitter binds texture units 0/1 while emitting stage-1 UVs for
  original post-detail materials.
- Runtime purpose: retail materials that depend on original detail,
  scale/invscale, add/subtract, blend, and detail-blend stage-1 texture
  semantics now reach vitaGL through a bounded fixed-function combiner mapping.
  This preserves original `ShaderClass`, `TextureClass`, `MaterialPassClass`,
  and `MeshModelClass` ownership while removing the dev57 stage-1 unsupported
  renderer gap.
- Validation: focused texture surface/provenance/loading/indexed-state and
  skin/material contracts passed 27/27. The fast no-deploy candidate passed
  the expanded 53-test focused gate, the original `DDSFileClass`
  `.tga`-to-`.dds` executable contract 11/11, and package identity/hash checks.
  The full no-deploy canonical build passed retained host-validation reuse,
  70 host unittest checks, deterministic restaging, source integration
  reporting, ARM link/package, identity verification, compressed VPK
  validation, diagnostics bundle generation, SHA manifest verification, and
  retail exclusion.
- Source report: the canonical integration report records 451 upstream
  original Westwood translation units plus one staged original-owner extraction
  (`staging/commando/loadingscreen.cpp`), 26 Vita platform/renderer/validation
  files, 118 deterministic staging patches, and pristine upstream.
- Artifact: `dist/RenegadeVita-A3.5-dev58.vpk` SHA-256 is
  `d9555d54aa3a577a8bb5a3b5ef6f32bf67aa96de4cc128e8726137a1798d0bb3`;
  ELF SHA-256 is
  `82be35efe2d243d04f29844aa0bc196573a33573f57353ab198166a4d4153ae6`.
- Boundary: dev58 has not been physically tested and no Vita deployment was
  attempted. The next hardware run should manually install dev58, verify
  audible Logan dialogue, message/dialog text, and material/texture appearance,
  then inspect `ux0:data/renegade/user/logs/a35-dev58-runtime.log`, especially
  `first original MeshClass stage1 texture`, `unsupported_stages`, `texture
  loaded`, `loaded_dds/tga`, `checker_bind`, `invalid_bind`, `speech=`, and
  `stream_mix` if dialogue is still inaudible or materials remain incorrect.

## 2026-08-28 — dev57 direct mesh base-pass replay

`[██████████] 12/12 canonical source/build gates complete`

- Renderer boundary: the direct Vita `MeshClass` submitter now replays every
  original base material pass instead of drawing only pass 0. Each pass reads
  its own stage-0 texture, shader, UV array, DCG colors, and vertex material
  from `MeshModelClass`, while the existing geometry fingerprint counters
  remain stable for host regression checks.
- Runtime purpose: retail lightmap/detail/emissive/shiny-mask material data
  that survived W3D load under original ownership now reaches the Vita draw
  boundary as pass-specific work instead of being silently skipped. Stage-1
  multitexture remains a bounded renderer gap.
- Validation: focused texture surface/provenance/loading/indexed-state
  contracts passed 24/24. The fast no-deploy candidate passed the expanded
  52-test focused gate, the original `DDSFileClass` `.tga`-to-`.dds`
  executable contract 11/11, and package identity/hash checks. The full
  no-deploy canonical build passed retained host-validation reuse,
  deterministic restaging, source integration reporting, ARM link/package,
  identity verification, compressed VPK validation, diagnostics bundle
  generation, SHA manifest verification, and retail exclusion.
- Source report: the canonical integration report records 451 upstream
  original Westwood translation units plus one staged original-owner extraction
  (`staging/commando/loadingscreen.cpp`), 26 Vita platform/renderer/validation
  files, 118 deterministic staging patches, and pristine upstream.
- Artifact: `dist/RenegadeVita-A3.5-dev57.vpk` SHA-256 is
  `b318946facbd3a732ae8bc314965985d7aebb918d09f15ea38df38a222165d90`;
  ELF SHA-256 is
  `176fc44a0139e59492c25ab1f54710290f3676b27bbb503efab51ec6b0bdb597`.
- Boundary: dev57 has not been physically tested and no Vita deployment was
  attempted. The next hardware run should manually install dev57, verify
  audible Logan dialogue, message/dialog text, and material/texture appearance,
  then inspect `ux0:data/renegade/user/logs/a35-dev57-runtime.log`, especially
  `texture loaded`, `loaded_dds/tga`, `checker_bind`, `invalid_bind`,
  `unsupported_stages`, `speech=`, and `stream_mix` if dialogue is still
  inaudible or materials remain incorrect.

## 2026-08-28 — dev56 DDS retained surface levels

`[██████████] 12/12 canonical source/build gates complete`

- Renderer boundary: DDS retail texture loads now retain decoded CPU-backed
  `D3DFMT_A8R8G8B8` surface levels for every mip while preserving DX8
  `SourceFormat` descriptor metadata from
  `WW3DFormat_To_D3DFormat(dds.Get_Format())`.
- Runtime purpose: original `GetSurfaceLevel()` callers no longer receive
  blank descriptor-only surfaces after DDS loads. The retained decoded retail
  pixels are available under original WW3D ownership for
  `SurfaceClass`, texture-loader, D3DX, missing-texture, and message/dialog
  text surface-copy paths.
- Validation: focused texture surface/provenance/loading/indexed-state
  contracts passed 23/23. The fast no-deploy candidate passed the expanded
  51-test focused gate, the original `DDSFileClass` `.tga`-to-`.dds`
  executable contract 11/11, and package identity/hash checks. The full
  no-deploy canonical build passed retained host-validation reuse,
  deterministic restaging, source integration reporting, ARM link/package,
  identity verification, compressed VPK validation, diagnostics bundle
  generation, SHA manifest verification, and retail exclusion.
- Source report: the canonical integration report records 451 upstream
  original Westwood translation units plus one staged original-owner extraction
  (`staging/commando/loadingscreen.cpp`), 26 Vita platform/renderer/validation
  files, 118 deterministic staging patches, and pristine upstream.
- Artifact: `dist/RenegadeVita-A3.5-dev56.vpk` SHA-256 is
  `ecea466be07e7648429c2f0daa653530a37aeb60c60940fe6befa444caebca17`;
  ELF SHA-256 is
  `fe25fdfa6b2dcc4e36be8c02b1defacd0e12207c4501d4d0f9ee5b086482a2ab`.
- Boundary: dev56 has not been physically tested and no Vita deployment was
  attempted. The next hardware run should manually install dev56, verify
  audible Logan dialogue, message/dialog text, and material/texture appearance,
  then inspect `ux0:data/renegade/user/logs/a35-dev56-runtime.log`, especially
  `texture loaded`, `loaded_dds/tga`, `checker_bind`, `invalid_bind`,
  `speech=`, and `stream_mix` if dialogue is still inaudible or materials
  remain incorrect.

## 2026-08-28 — dev55 DX8 surface-copy boundary

`[██████████] 12/12 canonical source/build gates complete`

- Renderer boundary: the Vita `IDirect3DDevice8::CopyRects` compatibility
  path now performs bounded CPU-backed surface copies instead of returning an
  invalid-call stub. Copies validate source/destination rectangles, preserve
  same-surface overlap with row-safe `memmove`, reject block-compressed
  formats, and upload a changed destination texture owner once after the copy.
- D3DX compatibility: `D3DXLoadSurfaceFromSurface` and `D3DXFilterTexture`
  are now declared and implemented for the original surface/mip frontier. The
  direct same-format path uses byte copies; scaled or format-converting paths
  use bounded RGBA sampling. Palette and color-key paths fail closed until an
  original caller proves they are needed.
- Runtime purpose: this restores the original `Render2DSentenceClass`
  pending-surface to texture-surface copy behavior used by message, loading,
  and dialogue text rendering, while also giving the staged original
  texture-loader frontier real surface/mip generation semantics.
- Validation: focused texture surface/provenance/loading/indexed-state
  contracts passed 22/22. The fast no-deploy candidate passed the expanded
  50-test focused gate, the original `DDSFileClass` `.tga`-to-`.dds`
  executable contract 11/11, and package identity/hash checks. The full
  no-deploy canonical build passed retained host-validation reuse, 68 host
  unittest checks, deterministic restaging, source integration reporting, ARM
  link/package, identity verification, compressed VPK validation, diagnostics
  bundle generation, SHA manifest verification, and retail exclusion.
- Source report: the canonical integration report records 451 upstream
  original Westwood translation units plus one staged original-owner extraction
  (`staging/commando/loadingscreen.cpp`), 26 Vita platform/renderer/validation
  files, 118 deterministic staging patches, and pristine upstream.
- Artifact: `dist/RenegadeVita-A3.5-dev55.vpk` SHA-256 is
  `559b91c07e871a9171f704b59433c33dee14602edeba742ff51278925a24ca4d`;
  ELF SHA-256 is
  `3fa450de230e964b6da6794d607453ec0a157c7bf2226985473e4b322f528e11`.
- Boundary: dev55 has not been physically tested and no Vita deployment was
  attempted. The next hardware run should manually install dev55, verify
  audible Logan dialogue, message/dialog text, and material/texture appearance,
  then inspect `ux0:data/renegade/user/logs/a35-dev55-runtime.log`, especially
  `texture loaded`, `loaded_dds/tga`, `checker_bind`, `invalid_bind`,
  `speech=`, and `stream_mix` if dialogue is still inaudible or materials
  remain incorrect.

## 2026-08-28 — dev54 DX8 texture surface ownership

`[██████████] 12/12 canonical source/build gates complete`

- Renderer boundary: the Vita `IDirect3DTexture8` boundary now owns
  refcounted CPU-backed surface levels for lockable textures and implements
  `GetSurfaceLevel`, `LockRect`, `UnlockRect`, `GetPriority`/`SetPriority`,
  and width/height `_Create_DX8_Texture`. `SurfaceClass(IDirect3DSurface8*)`
  now mirrors desktop COM ownership by adding a reference and reading the
  surface description, so original `TextureClass::Get_Surface_Level()` can wrap
  and release the raw D3D surface safely.
- Runtime purpose: this removes the descriptor-only texture-surface stub that
  blocked original texture surface semantics in current `texture.cpp` and the
  staged `missingtexture.cpp`/`textureloader.cpp`/`dx8texman.cpp` frontier.
  Writable texture unlocks now upload the changed mip level through the Vita
  backend instead of losing the CPU-side update.
- Validation: focused texture surface/provenance/loading/indexed-state
  contracts passed 19/19. The fast no-deploy candidate passed the expanded
  47-test focused gate plus package identity/hash checks. The full no-deploy
  canonical build passed retained host-validation reuse, 68 host unittest
  checks, deterministic restaging, source integration reporting, the original
  `DDSFileClass` `.tga`-to-`.dds` executable contract 11/11, ARM link/package,
  identity verification, compressed VPK validation, diagnostics bundle
  generation, and SHA manifest verification.
- Source report: the canonical integration report records 451 upstream
  original Westwood translation units plus one staged original-owner extraction
  (`staging/commando/loadingscreen.cpp`), 26 Vita platform/renderer/validation
  files, 118 deterministic staging patches, and pristine upstream.
- Artifact: `dist/RenegadeVita-A3.5-dev54.vpk` SHA-256 is
  `11d78031946e7e5b8becd710d7dfe3bce04d52ad5f88e347f5850feeef55a4b2`;
  packaged eboot/SELF SHA-256 is
  `82a66e1d06e244ef6a1bc1a82a3f06dd73d296f079f7f501645abfe7df0fb657`;
  ELF SHA-256 is
  `3b2afcd0337b316fff4b9a1c24a0877d94156c24b67b0596fc6d9517cd236b08`.
- Boundary: dev54 has not been physically tested and no Vita deployment was
  attempted. The next hardware run should manually install dev54, verify
  audible Logan dialogue and material/texture appearance, then inspect
  `ux0:data/renegade/user/logs/a35-dev54-runtime.log`, especially `texture
  loaded`, `loaded_dds/tga`, `checker_bind`, `invalid_bind`, `speech=`, and
  `stream_mix` if dialogue is still inaudible or materials remain incorrect.

## 2026-08-28 — dev53 texture provenance telemetry

`[██████████] 12/12 canonical source/build gates complete`

- Texture diagnostics: the Vita DX8 boundary now records successful retail
  texture loads by source path (`dds` or `tga`) and logs the first 24 loaded
  textures with size, mip count, DX8 format, resident bytes, checksum, alpha,
  fallback state, and native texture id. Checkerboard fallback binds are counted
  separately from invalid/null texture binds so pink/black visibility can be
  tied to missing/decode/upload fallback rather than generic bind failure.
- Runtime breadcrumbs: the `A3.5 perf` line now includes
  `loaded_dds/tga=%llu/%llu` and
  `source/invalid/unsupported/decode/upload_fail/checker/checker_bind/invalid_bind`.
  Capture JSON and capture-bundle comparisons now carry `texture_dds_loads`,
  `texture_tga_loads`, and `texture_checkerboard_binds`.
- Validation: focused texture provenance, loading-screen, indexed-state, and
  capture-compare contracts passed 17/17. The fast no-deploy candidate passed
  the expanded 42-test focused gate plus package identity/hash checks. The full
  no-deploy canonical build passed retained host validation reuse,
  deterministic restaging, source integration reporting, the original
  `DDSFileClass` `.tga`-to-`.dds` executable contract 11/11, ARM link/package,
  identity verification, compressed VPK validation, diagnostics bundle
  generation, and SHA manifest verification.
- Source report: the canonical integration report records 451 upstream
  original Westwood translation units plus one staged original-owner extraction
  (`staging/commando/loadingscreen.cpp`), 26 Vita platform/renderer/validation
  files, 118 deterministic staging patches, and pristine upstream.
- Artifact: `dist/RenegadeVita-A3.5-dev53.vpk` SHA-256 is
  `bf3116fb0e122edd359b3a0ce2dffaa90df0b58599e77cfd803d825fa8d85699`;
  packaged eboot/SELF SHA-256 is
  `c384aba19d06450fc8cd1f6071083028001f12d1a3252ccffa7bbf1362030b49`;
  ELF SHA-256 is
  `ea279c8848c6f9df15f20b9c582855fb5c4a252662a495ec9e320db66ca6badb`.
- Historical boundary: dev53 was not physically tested before dev54 superseded
  it. Its diagnostics remain retained for comparing texture provenance,
  checkerboard fallback binds, active speech state, and stream-mix evidence if
  a later physical log needs source-level comparison.

## 2026-08-28 — dev52 active-conversation speech object diagnostics

`[██████████] 12/12 canonical source/build gates complete`

- Dialogue diagnostics: the active conversation state now reports the original
  speech object that actually owns playback. Soldier/orator remarks are read
  from `SoldierGameObj::CurrentSpeech`; non-orator conversation sounds still
  use `ActiveConversationClass::CurrentSound`. The probe is read-only and does
  not start, stop, advance, or create sounds.
- Runtime breadcrumbs: the `A3.5 mission progress` line now includes
  `speech=speaker:%d src:%d present/scene/culled/playing=%d/%d/%d/%d`,
  `class/type/state=%d/%d/%d`, and `dur/dropoff/dist=%u/%.3f/%.3f`. Combined
  with dev51 `stream_mix`, this separates "no original speech object",
  "speech exists but is culled", "speech is in the scene but not playing", and
  "speech is playing while decoded stream samples are zero or nonzero."
- Validation: focused mission-conversation diagnostics passed 10/10, the Vita
  audio provider contract passed 1/1, the route-session runner passed 11/11,
  the fast no-deploy build passed package identity/hash checks, the executable
  original `DDSFileClass` `.tga`-to-`.dds` alias contract passed 11/11, and
  the full no-deploy canonical build passed retained host validation reuse,
  deterministic restaging, source integration reporting, ARM link/package,
  identity verification, compressed VPK validation, diagnostics bundle
  generation, and SHA manifest verification.
- Source report: the canonical integration report records 451 upstream
  original Westwood translation units plus one staged original-owner extraction
  (`staging/commando/loadingscreen.cpp`), 26 Vita platform/renderer/validation
  files, 118 deterministic staging patches, and pristine upstream. The
  conversation diagnostics patch now explicitly covers `soldier.h`.
- Artifact: `dist/RenegadeVita-A3.5-dev52.vpk` SHA-256 is
  `d411723bb38a34afb68e4e324799c0f6bccab2e61f08d02fbdf47ea8afc6d8c8`;
  packaged eboot/SELF SHA-256 is
  `536bb10b276ac2b1ead72869d8331692f419fcc2c5b8161fcb88ac29211fa666`;
  ELF SHA-256 is
  `602b35d8d9832937610e729a603d2ff871f14a1943e0d3e530ce2016364f0f9f`.
- Boundary: dev52 has not been physically tested and no Vita deployment was
  attempted. The next hardware run should manually install dev52, verify
  audible Logan dialogue and material/texture appearance, then inspect
  `ux0:data/renegade/user/logs/a35-dev52-runtime.log`, especially the
  `speech=` and `stream_mix` fields if dialogue is still inaudible.

## 2026-08-28 — dev51 streamed-dialogue mix isolation candidate

`[██████████] 12/12 canonical source/build gates complete`

- Audio diagnostics: the Vita Miles provider now marks opened streams,
  isolates their contribution into a stream-only mix accumulator, and reports
  stream buffers, frames, nonzero buffers, peak sample, and active streamed
  sample count. This preserves original WWAudio/conversation ownership while
  separating "stream decoded but silent in the output mix" from "stream mixed
  nonzero samples but still not audible on hardware."
- Runtime breadcrumbs: the `A3.5 audio` line now includes
  `stream_mix=buffers:%llu frames:%llu nonzero:%llu peak:%u` and
  `allocated/active/streams=%u/%u/%u`, alongside the existing dialogue,
  cinematic, stream-read/decode/start, and Vita output counters.
- Validation: the host Vita Miles provider test now asserts stream-only mixed
  buffer/frame/nonzero/peak behavior and post-close active-stream accounting.
  Focused audio/build-script/diagnostic contracts passed 14/14, the fast
  no-deploy candidate passed 37/37 focused contracts, the executable original
  `DDSFileClass` `.tga`-to-`.dds` alias contract passed 11/11, and the full
  no-deploy canonical build passed retained host validation reuse,
  deterministic restaging, source integration reporting, ARM link/package,
  identity verification, compressed VPK validation, diagnostics bundle
  generation, and SHA manifest verification.
- Source report: the canonical integration report records 451 upstream
  original Westwood translation units plus one staged original-owner extraction
  (`staging/commando/loadingscreen.cpp`), 26 Vita platform/renderer/validation
  files, 118 deterministic staging patches, and pristine upstream.
- Artifact: `dist/RenegadeVita-A3.5-dev51.vpk` SHA-256 is
  `5e4d371ac6f1c509a31f0b6c3fb47580dcb7dc4fef15a20aa6da01532f4f2e74`;
  packaged eboot/SELF SHA-256 is
  `10ff2488c2ea19d003c4ec328c74a683b0654b4f8a4f2917a7c3e97794293e24`;
  ELF SHA-256 is
  `e43764f3a6eacec16544c59340fa7bcadfc8f17ca3bcdf0035ad6b1fe7452e6d`.
- Boundary: dev51 has not been physically tested and no Vita deployment was
  attempted. The next hardware run should manually install dev51, verify
  audible Logan dialogue and material/texture appearance, then inspect
  `ux0:data/renegade/user/logs/a35-dev51-runtime.log`, especially the
  `stream_mix` fields if dialogue is still inaudible.

## 2026-08-28 — dev50 texture descriptor and SDK-root canonical candidate

`[██████████] 12/12 canonical source/build gates complete`

- Source correction: the Vita DX8 texture boundary now reports DDS texture
  descriptors in original DX8 `D3DFORMAT` terms instead of raw `WW3DFormat`
  enum values. This preserves the original `TextureClass::Init()` round trip
  through `D3DFormat_To_WW3DFormat()` and prevents the shipped
  `WW3D_FORMAT_DXT1` value from being misread as `D3DFMT_R8G8B8`.
- Audio contract: the Vita Miles provider mixer test now validates the whole
  four-frame mixed buffer for mono/pan-left and stream/pan-center cases, locking
  the single-rate cursor behavior needed for streamed dialogue.
- Build-system fix: the canonical and fast build scripts now default to the
  documented `/usr/local/vitasdk` via `RENEGADE_VITASDK`, and CMake detects
  vitaGL physical-contiguous memory names with declaration-aware enum matching.
  The dev50 canonical configure selected `VGL_MEM_SLOW` from `/usr/local/vitasdk`.
- Validation: focused audio/loading/build-script contracts passed 10/10, the
  fast no-deploy candidate passed 37/37 focused contracts, the executable
  original `DDSFileClass` `.tga`-to-`.dds` alias contract passed 11/11, and the
  full no-deploy canonical build passed retained host validation reuse,
  deterministic restaging, source integration reporting, ARM link/package,
  identity verification, compressed VPK validation, diagnostics bundle
  generation, and SHA manifest verification.
- Source report: the canonical integration report records 451 upstream original
  Westwood translation units plus one staged original-owner extraction
  (`staging/commando/loadingscreen.cpp`), 26 Vita platform/renderer/validation
  files, 118 deterministic staging patches, and pristine upstream.
- Artifact: `dist/RenegadeVita-A3.5-dev50.vpk` SHA-256 is
  `2c9fe46c04596171ba1bc5fa7f47b13d7b95ba565b751b9e528147d982d722b1`;
  packaged eboot/SELF SHA-256 is
  `f9df6d460599154a061a1240465ca1fcfa5ec4fd29d717384c1ff42ba1e673ff`;
  ELF SHA-256 is
  `3b5ed7597bfc36f14240cff75fbe2d4437e2ae8298eba57a4aa3ce22d0238725`.
- Boundary: dev50 has not been physically tested and no Vita deployment was
  attempted. The next hardware run should manually install dev50, verify
  audible Logan dialogue and material/texture appearance, then inspect
  `ux0:data/renegade/user/logs/a35-dev50-runtime.log`.

## 2026-08-28 — dev49 canonical dialogue telemetry and DDS-first texture candidate

`[██████████] 12/12 canonical source/build gates complete`

- Source correction: the Vita DX8 texture boundary now tries the original
  `DDSFileClass` route before the loose Targa route, so retail material names
  ending in `.tga` can resolve to the shipped `.dds` payloads through the
  original MIX/FileFactory chain. Targa remains as the fallback for real
  uncompressed `.tga` assets, and the first 16 texture fallbacks now log
  bounded reason/name breadcrumbs.
- Audio diagnostics: the Vita Miles-compatible provider now records stream
  bytes read, decoded frames, stream start success/silent/zero-volume counts,
  last stream name/rate/volume/pan, mix buffer/frame/nonzero/peak counters, and
  Vita output write counts. Runtime `A3.5 audio` breadcrumbs include those
  fields alongside dialog/cinematic category volumes.
- Build-system fix: canonical CMake now detects whether the installed vitaGL
  headers expose physical-contiguous memory as `VGL_MEM_PHYCONT` or
  `VGL_MEM_SLOW`, keeping the renderer memory telemetry portable across the
  two VitaSDK layouts present on this machine. The canonical build script also
  records the no-retail retained-host-validation fallback instead of failing
  when the local Steam retail tree is unavailable in WSL.
- Validation: focused fast contracts passed 37/37, including a new WWAudio
  stream-callback provider test and the updated DDS-first texture boundary
  contract. A new executable host contract also links original `DDSFileClass`
  and verifies `.tga` material names map to `.dds` factory lookups: 9/9. The
  full no-deploy canonical build passed retained host validation reuse,
  deterministic restaging, source integration reporting, ARM link/package,
  identity verification, compressed VPK validation, diagnostics bundle
  generation, and SHA manifest verification.
- Source report: the canonical integration report now records 451 upstream
  original Westwood translation units plus one staged original-owner extraction
  (`staging/commando/loadingscreen.cpp`), 26 Vita platform/renderer/validation
  files, 118 deterministic staging patches, and pristine upstream.
- Artifact: `dist/RenegadeVita-A3.5-dev49.vpk` SHA-256 is
  `abb0d3f8a6f895504ee78808ec834de3446d903ea912a8855d2f8e157fc75207`;
  SELF SHA-256 is
  `d6212ac5abd77f825c7d19eca3b9d549b3087d0919be7e7296d066476d0b38e0`;
  ELF SHA-256 is
  `78c76b5da8af4692a3ea20327d80b95fdc85ffd37547932e65eebe66ccd5c270`.
- Boundary: dev49 has not been physically tested and no Vita deployment was
  attempted. The next hardware run should manually install dev49, verify
  audible Logan dialogue and texture appearance, then inspect
  `ux0:data/renegade/user/logs/a35-dev49-runtime.log`.

## 2026-08-25 — broad Vita open-source reference toolkit

`[██████████] 10/10 current tooling gates complete`

- Scope: implemented the non-audio open-source reuse pass as isolated tooling
  and provenance. No gameplay/runtime source was changed, no external source
  tree was imported into the port, no retail data was packaged, and the Vita
  filesystem was not touched.
- Reference pull: `tools/vita_open_source_references.yml` pins 14 repositories
  for the current broad blockers: VitaSDK build/toolchain/samples, vitaGL,
  Vita3K, vita-crashdump, vita-parse-core, libvcp, Sokol audio,
  DaedalusX64-vitaGL, SRB2Kart Vita, Alisa-Vita, Vita Recorder, and psp2spvc.
  `python3 tools/fetch_vita_open_source_references.py` fetched 14/14 into
  `/tmp/renegade-vita-reference-cache`; the provenance report is
  `reports/generated/vita_open_source_reference_fetch.json`.
- License boundary: GPL-2.0-only and NOASSERTION projects are explicitly
  study-only. The compatible references are still fetched outside the source
  tree until a future blocker justifies a minimal copied implementation and
  reuse-ledger entry.
- Tooling added: `tools/fetch_vita_open_source_references.py` validates the
  manifest, uses the skill fetch helper with anchored sparse paths, verifies
  exact commits, counts materialized files, and writes the fetch report.
  `tools/run_vita3k_candidate.py` provides an optional Vita3K emulator-only
  runner and writes receipts with `physical_acceptance=false`.
- Source review: `reports/VITA_OPEN_SOURCE_REFERENCE_INSIGHTS.md` records the
  validated reference findings: Vita3K CLI flags, vitaGL renderer diagnostic
  flags and texture-cache conflict, Sokol's current Vita SceAudio backend,
  crash-dump parser feature targets, and license-based study-only boundaries.
- Validation: `python3 -m py_compile` passed for the new scripts; `bash -n`
  passed for the fetch helper; 62 focused Python tool tests passed, including
  `tools.test_vita_open_source_references`; the full reference fetch passed;
  the dev48 Vita3K dry-run generated
  `build/vita3k-evidence-dry-run/A3.5-dev48-20260825T174200Z/` against VPK
  SHA-256 `7830e41ef8ea98f1ce914091a292a7cceacb2b4bb5b5f20381047af446e2e067`.
- Boundary: no Vita3K executable was found; actual emulator execution remains
  unavailable until `VITA3K_EXE` or `--vita3k-exe` points to one. Emulator
  evidence will remain separate from physical Vita acceptance.

## 2026-08-24 — physical handoff read-only check

The Vita endpoint is online and exposes the admitted input/file capabilities, but
the installed executable is still the restored A3.5-dev46 SELF
`bb42fa9fbbf80e6eb90add5d3ae1bed708f1a9847f61ddc3d3fa441b4a10b244`. The device
still contains only the stale pre-dialogue route
`5ef2ee8f2ed5d4f301ec20ef95c73fe7aea9956a32e9cc41aecf84999191e895`. No app was
launched, no files were changed, and no dev48 deployment was performed. The
next approved hardware action is dev48 installation followed by a fresh
user-controlled record; the stale route remains inadmissible.

## 2026-08-25 — stale pre-dialogue replay closed

The retained route `5ef2ee8f2ed5d4f301ec20ef95c73fe7aea9956a32e9cc41aecf84999191e895`
is now explicitly rejected by the dev48 route runner. Device evidence showed
that it was recorded before the TranslateDB object-factory fix: Logan's initial
conversation ended near frame 545 in the recording but remained active to about
frame 1345 in the corrected runtime, after which the replay reached no pistol
and settled in a corner. The route checksum was valid; its mission timing was
not. A new user-controlled record on the corrected candidate is required before
another replay can be admitted. Runner syntax and the 11-case route-runner
contract pass.

## 2026-08-25 — dev48 dialog-volume source/build candidate

`[██████████] 10/10 current evidence gates complete`

- Source correction: the Vita WWAudio path now initializes
  `m_DialogVolume` and `m_CinematicVolume` to original defaults in the
  constructor path used by `application_audio.Initialize()` without the desktop
  registry/default-volume route. This is a narrow audio-category fix below the
  dev47 string/sound-id lookup repair; it does not replace WWAudio,
  ConversationMgr, or retail data ownership.
- Diagnostics: `A3.5 audio` runtime breadcrumbs now include
  `volumes_dialog/cinematic`, so the next hardware run can distinguish
  category-volume failure from stream decode/mix/routing failure if dialogue is
  still inaudible.
- Build evidence: deterministic restage applied the WWAudio constructor patch,
  focused fast contracts passed 37/37, the dev48 package completed 15
  incremental ARM/package steps, identity verification passed, compressed VPK
  validation passed, and `SHA256SUMS` verified. VPK SHA-256 is
  `7830e41ef8ea98f1ce914091a292a7cceacb2b4bb5b5f20381047af446e2e067`;
  SELF SHA-256 is
  `0e61044df081b36b1a74da88c6157149cc27e818fca26f7bde537d00f710ec23`;
  ELF SHA-256 is
  `a4416e16a4678c645e492c91f55c4fc0decae095fb4589d947d9559ee1dc63bd`.
- Automation: the route runner is updated to exact dev48 hashes and runtime
  log path. It keeps dev46 and earlier exact hashes as rollback predecessors
  and intentionally does not admit failed dev47 as a predecessor.
- Boundary: dev48 is not deployed and has no physical audio acceptance. The
  retained dev43 no-dialogue route remains invalid for acceptance after dev47/
  dev48 dialogue timing changes. Next hardware should first verify audible
  dialogue and then record a fresh route; replay should come after that.

## 2026-08-25 — dev47 physical replay failed: lookup fixed, route/audio failed

`[██████████] 10/10 current evidence gates complete`

- Physical result: the approved dev47 replay failed. User observation reported
  the retained route was not followed, the player got stuck in a corner, and
  there was still no audible dialogue.
- Evidence is under
  `build/device-evidence/a3.5-dev47-route-replay-20260825-035432/`. The run
  reached `REPLAY_ACTIVE` with route SHA-256
  `5ef2ee8f2ed5d4f301ec20ef95c73fe7aea9956a32e9cc41aecf84999191e895`, but was
  manually aborted after route divergence. The app was stopped and no new crash
  dump was recorded (`new_count=0`).
- Diagnostic split: dev47 did fix the concrete `STRINGS.TDB` object-row
  problem. Early `MTU_LOGAN_START` lines changed from dev46's `str=0` and
  `sound=-1` to `str=1` with valid sound ids such as `163849115`,
  `163849120`, `163849130`, `163849447`, and `163849137`. Audio counters also
  showed stream opens and starts with `last_error=no error`.
- Failure interpretation: because dialogue rows and durations now participate
  in runtime state, the old route recorded under no-dialogue timing is no
  longer timing-equivalent. That explains route divergence. It does not accept
  dialogue audio, because the user still heard no dialogue despite valid sound
  ids and stream counters.
- Device end state: the runner's VitaCompanion FTP rollback failed with
  `550 Could not allocate memory`, so dev46 was restored manually through a
  VDB1 staged replace. Final installed SELF is dev46
  `bb42fa9fbbf80e6eb90add5d3ae1bed708f1a9847f61ddc3d3fa441b4a10b244`; app
  status is stopped. A best-effort removal of the temporary rollback stage file
  reported file-remove failure, likely because the staged replace had already
  moved it.
- Boundary: dev47 is failed physical evidence. Next source work must diagnose
  inaudible streamed dialogue separately from SFX and must use a route strategy
  that waits for the new dialogue/control timing or records a fresh route after
  dialogue behavior is accepted.

## 2026-08-25 — dev47 TranslateDB object-factory source/build candidate

`[██████████] 10/10 current evidence gates complete`

- Diagnosis from dev46 physical replay: dialogue reached active M00
  conversations, the message-window render pass ran, and audio SFX output
  worked, but every active tutorial text lookup returned no string object and
  no sound id. Representative `MTU_LOGAN_*` entries logged
  `text/sound/str/def=<id>/-1/0/0`, while provider counters showed successful
  output start, sample-file loads, and sample starts for footsteps, weapons,
  reload, and impacts. This separates the current no-dialogue failure from the
  audio device/provider path.
- Source correction: the A31 original-source closure now links
  `wwtranslatedb/translateobj.cpp` and `wwtranslatedb/stringtwiddler.cpp`, the
  original translation database object factories required for
  `SaveLoadSystemClass::Load()` to instantiate `STRINGS.TDB` rows. No
  replacement dialogue system, asset conversion, or runtime data mutation was
  added.
- Build evidence: focused dialogue/audio/route/physical-gate contracts passed
  before packaging, then A3.5-dev47 fast package passed 35 focused contracts,
  ELF/SELF/VPK identity, compressed VPK validation, SHA manifest, and retail
  exclusion. VPK SHA-256 is
  `4845d1f5124ecab4b3c2657f3c9910bc697a65d4f3afa7e9064ba6b348a1facf`;
  SELF SHA-256 is
  `525b3d8af2f8cb44d5f1a9f05be3e0e79c1c0fc7846a11dd627e1141b197112e`;
  ELF SHA-256 is
  `cf2ed4da5107e63a026bb343bb7d8795d2f2ffa8db18b7ddf9d9aa24840e9089`.
- Automation: the route runner is locally updated to exact dev47, admits exact
  dev47 plus known exact prior dev46-through-dev7 executables, uses dev47
  runtime/evidence paths, and supplies the dev47 ELF/SHA to VDB crash reports.
- Boundary: dev47 is a source/build/package candidate only. Do not deploy or
  touch the Vita filesystem without explicit approval. The next physical gate
  is the same retained route replay, with user-observed dialogue plus returned
  text/sound/string/definition and provider counters.

## 2026-08-25 — dev46 dialogue presentation and audio-diagnostic candidate

`[██████████] 10/10 current evidence gates complete`

- Source correction: the direct Vita render envelope now restores the original
  interactive message-window pass after `CombatManager::Render()` and before
  the objective viewer/end-render path. This addresses the concrete text
  dialogue presentation gap without replacing ConversationMgr, DialogMgr, HUD,
  or Combat ownership.
- Diagnostics: mission-progress logging now records the active conversation
  remark text id, sound id, `STRINGS.TDB` object availability, and sound
  definition availability. The Vita Miles-compatible provider exposes bounded
  runtime counters for output start, sample-file load, stream open, sample
  start, active/allocated sounds, and the last provider error. The direct
  runtime logs these after audio init, periodically, and at final teardown.
- Build evidence: focused dialogue/render/audio-provider/physical-gate
  contracts passed, then A3.5-dev46 fast package passed 34 focused contracts,
  ELF/SELF/VPK identity, compressed VPK validation, SHA manifest, and retail
  exclusion. VPK SHA-256 is
  `bbf57d346ca373042cc4e2d4be0600617c6f9b4031466a4c08324e221f5aece9`;
  SELF SHA-256 is
  `bb42fa9fbbf80e6eb90add5d3ae1bed708f1a9847f61ddc3d3fa441b4a10b244`;
  ELF SHA-256 is
  `06d602aa57884f1a9d3f3e47cec0370849f6d4c87751417fc843fb28084eb680`.
- Physical replay evidence is under
  `build/device-evidence/a3.5-dev46-route-replay-20260825-034048/`. It used
  the retained dev43 route SHA-256
  `5ef2ee8f2ed5d4f301ec20ef95c73fe7aea9956a32e9cc41aecf84999191e895`,
  returned PASS, verified `SHA256SUMS`, and returned to LiveArea cleanly.
  User observation: no dialogue, only SFX such as footsteps, walking, shooting,
  reloading, bullet puffs, ricochet, and impacts.
- Runtime diagnosis: message-window render closure was active, but every
  logged tutorial conversation lookup had `sound=-1`, `str=0`, and `def=0`.
  Audio provider counters remained healthy for SFX. Dev46 therefore proves the
  no-dialogue defect is upstream of sound creation/decode/output: the
  `STRINGS.TDB` object rows were not being instantiated into TranslateDB.

## 2026-08-25 — dev45 replay auto-exit pass

`[██████████] 10/10 current evidence gates complete`

- Source fix: route replay now requests clean exit only after all recorded
  samples are consumed, and the direct Vita runtime's START-exit poll also
  accepts that bounded route-complete signal. Physical START remains a live
  abort; original Input/Combat action ownership is unchanged.
- Build evidence: A3.5-dev45 fast package passed 33 focused contracts, ELF/
  SELF/VPK identity, compressed VPK validation, SHA manifest, and retail
  exclusion. VPK SHA-256 is
  `760995ea23896216349d75fc4c20caba7caa54c3fd73311d331051a31d5e939f`;
  SELF SHA-256 is
  `950950e04e6ae541ef076a9ae017f47af846ebaab169879621c2b7ea54d741b5`;
  ELF SHA-256 is
  `fe67954914c13d66af07b45786897c22f887acbc662931c0e5f3a4140900743b`.
- Replay evidence is under
  `build/device-evidence/a3.5-dev45-route-replay-20260825-025927/`. The runner
  admitted the dev43 route SHA-256
  `5ef2ee8f2ed5d4f301ec20ef95c73fe7aea9956a32e9cc41aecf84999191e895`,
  returned PASS, and verified `SHA256SUMS`.
- Runtime evidence: `latest-session.log` records
  `replay complete: injecting clean exit sample=5958/5958`,
  `START exit request detected`, and
  `[LIFECYCLE] END status=clean candidate=A3.5-dev45`. Route validation remains
  version 2, 5,958 samples, complete, untruncated, exact-size, checksum
  matched; retail M00 remains unchanged at
  `84f14f6267dd8a88563b3d31540bf857df0b8e111144944cb582edd246f2d438`.
- Device end state: user observed automatic LiveArea return; VDB app status is
  stopped, crash delta reports `new_count=0`, and installed SELF is exact
  dev45 `950950e04e6ae541ef076a9ae017f47af846ebaab169879621c2b7ea54d741b5`.
- Boundary: this accepts the current route/replay clean-exit automation gate.
  It does not by itself accept loading-screen visual correctness, NPC material
  correctness, sky/material appearance, Havoc arm/weapon visibility, audio, or
  longer mission stability.

## 2026-08-25 — dev43 replay fidelity pass with manual-exit caveat

`[█████████░] 9/10 current evidence gates complete`

- Replay evidence is under
  `build/device-evidence/a3.5-dev43-route-replay-20260825-023903/`. The runner
  admitted explicit route source
  `build/device-evidence/a3.5-dev43-route-record-20260825-022835/input-route-v1.bin`
  with SHA-256
  `5ef2ee8f2ed5d4f301ec20ef95c73fe7aea9956a32e9cc41aecf84999191e895`.
- User-observed replay fidelity: gate, ladder, pistol obtain, and pistol
  firing were 1:1 with the recording.
- Runtime evidence: replay receipt PASS, clean lifecycle, no new PSP2DMP,
  unchanged retail M00 SHA-256
  `84f14f6267dd8a88563b3d31540bf857df0b8e111144944cb582edd246f2d438`,
  `Weapon_Pistol_Player`, `fired_total=36`, skin deformation failures `0`,
  indexed submissions rejected `0`, and loading capture validation PASS.
- Caveat: the replay froze at the end and did not return to LiveArea until the
  user pressed START manually. The log then records `START exit request
  detected` and clean teardown. Do not count this as an automatic clean-exit
  replay pass.
- End state: exact dev43 SELF remains installed on the Vita:
  `c81cf891597d97720190b997d79cb67b56fe12911349f31b7ae9e3dfffaba935`.

## 2026-08-25 — dev43 clean route recording recovered after harness false-reject

`[█████████░] 9/10 current evidence gates complete`

- Now: A3.5-dev43 is the current physical route/runtime evidence point. It
  retains the dev40 loading path and later crash/runner fixes, then corrects
  the route activation gate so the runner does not pull an active player out
  when objective states are already hidden.
- Physical run: the user pressed START after the range gate opened. Runtime
  evidence under
  `build/device-evidence/a3.5-dev43-route-record-20260825-022835/` shows
  `route_activation_observed=1`, clean lifecycle end, no new PSP2DMP, 5,958
  recorded route samples, original Combat teardown, and unchanged retail M00
  SHA-256 `84f14f6267dd8a88563b3d31540bf857df0b8e111144944cb582edd246f2d438`.
- Progression: the route reached `Weapon_Pistol_Player`, fired the pistol
  (`fired_total=36`), observed the Logan/range transition, and exited cleanly.
  The retained route SHA-256 is
  `5ef2ee8f2ed5d4f301ec20ef95c73fe7aea9956a32e9cc41aecf84999191e895`.
- Harness correction: the original dev43 runner falsely rejected the recording
  because its pistol regex required positive `rounds=N/M`; the original runtime
  logs pistol state as `rounds=-1/N`. The runner now requires
  `Weapon_Pistol_Player` plus `fired_total > 0`, and focused route/mission/input
  tests pass 21/21.
- Capture evidence: loading-screen frame/state and pre-clean-exit state were
  pulled after the false-reject. `tools/validate_vita_loading_capture.py` passes
  for the returned loading BMP/state. This remains capture/metadata evidence;
  it does not by itself accept loading-screen visual correctness.
- Device end state: the failed-run cleanup restored exact prior dev18 SELF
  `058a10a594a8038833d8cced9a4b7a5207a4100079da44beef5c645a7ca69278`.

## 2026-08-24 — dev40 original TGA orientation candidate

`[█████████░] 9/10 current evidence gates complete`

- Historical: A3.5-dev40 was the active source/build/package candidate at this
  point. No dev40 Vita deployment or runtime iteration was attempted.
- Source correction: original `TextureLoader` keeps a Targa open, toggles
  `TGAIDF_YORIGIN`, then calls `Targa::Load()`. Dev39 admitted `.tga`
  textures but closed/reopened before load and still retained a
  loadscreen-only UV flip. Dev40 restores the original TGA Y-origin ordering,
  removes `Should_Flip_Loading_Texture_V` / `flip_texture_v` from mesh and
  indexed submissions, and records `loading_texture_v_flip_enabled=false` in
  returned loading visual-gate metadata.
- Retained fixes: dev40 keeps the shared original LoadingScreenClass owner,
  CombatManager progress ownership, original `loading_screen.Render(true)`
  callback semantics, scoped 640x480 loading resolution mapped to Vita 960x544,
  the required returned loading BMP/state capture gate, dev35's heap
  `A31FrameHistory` stack-frame fix, dev36's camera-Y boundary correction,
  dev37's DataSafe invalid-handle guard, dev38's schema-v4 visual gate, dev39's
  `.tga` texture admission, and the indexed shader/texture state fix for
  original sky/star/cloud dynamic indexed submissions.
- Evidence: focused loading/capture/comparator contracts pass 13/13. Broader
  route/loading/crash no-device contracts pass 28/28. Fast package focused
  contracts now pass 27/27 including camera/input route checks. The host
  loading-backdrop probe still passes against
  local retail data at
  `/mnt/d/SteamLibrary/steamapps/common/Command & Conquer Renegade`.
- Package evidence: ARM ELF compile/link, SELF/VPK identity, packaged eboot
  match, compressed VPK validation, SHA manifest, and retail-payload exclusion
  pass; the VPK contains only `eboot.bin` and `sce_sys/param.sfo`.
- Exact hashes: VPK
  `7dcd50a14b95c5ba899ae5cc557221eff7b449ed664bf58471dccf82e4f756d7`;
  packaged SELF `f59209cdecd00dcc398e8c8a13b7af96e2a2c75ad6d737c2ec33b80069ae9461`;
  ELF `15ecc59aecc8736c1dbeffddc81d42f58e53f3715be3925ae6424a5f55fbe77d`;
  map `ddad433bdb5c03f289c4f1e3c07442c60164732a1728d8f1d20768851ade0b15`;
  symbols `a7fe14f19acc20c07140a62d31e0fe7411f17cd3ed05dbc4ba633e03d0c43123`.
- Constraint: do not claim loading-screen correctness, camera correctness,
  pistol-shot stability, or visual/audio correctness until physical Vita
  evidence returns. The first approved physical gate remains loading-screen
  visual acceptance using user observation plus the returned BMP/state metadata.
  Only after that gate passes should user manual input establish a fresh route
  recording.

## 2026-08-24 — dev39 original loading TGA route candidate

`[█████████░] 9/10 current evidence gates complete`

- Historical: A3.5-dev39 is superseded by A3.5-dev40. No dev39 Vita deployment
  or runtime iteration was attempted.
- Source correction: the original-retail host probe proves the Renegade
  multiplayer loading model `if_lvl94load.w3d` resolves
  `loadscreen_beam.tga` and `loadscreen_cnc_1..4.tga` through the original
  FileFactory/MIX/WW3DAssetManager owner with full-tile UVs. The Vita DX8
  boundary now routes `.tga` texture filenames through `_Create_DX8_Surface()`
  before creating the texture instead of sending them through the DDS-only
  archive loader. This addresses the concrete black/missing loading-texture
  cause without replacing the original loading-screen owner.
- Retained fixes: dev39 keeps the shared original LoadingScreenClass owner,
  CombatManager progress ownership, original `loading_screen.Render(true)`
  callback semantics, scoped 640x480 loading resolution mapped to Vita 960x544,
  the bounded `loadscreen_*` V correction, the required returned loading
  BMP/state capture gate, dev35's heap `A31FrameHistory` stack-frame fix,
  dev36's camera-Y boundary correction, dev37's DataSafe invalid-handle guard,
  and dev38's schema-v4 returned loading visual-gate metadata. It also retains
  the indexed shader/texture state fix for original sky/star/cloud dynamic
  indexed submissions.
- Evidence: fast package focused contracts pass 18/18. Independent
  route-runner/loading/capture contracts pass 20/20 after moving the hardware
  runner to exact dev39. A broader no-device crash/loading/route suite passed
  25/25 before the runner relabel. The host loading-backdrop probe passes
  against local retail data at
  `/mnt/d/SteamLibrary/steamapps/common/Command & Conquer Renegade`.
- Package evidence: ARM ELF compile/link, SELF/VPK identity, packaged eboot
  match, compressed VPK validation, SHA manifest, and retail-payload exclusion
  pass; the VPK contains only `eboot.bin` and `sce_sys/param.sfo`.
- Exact hashes: VPK
  `bce09a36607770bdfb4f78f22573b04637dc48bbf5f9b2ba214ee8e770bb71b1`;
  packaged SELF `ccd306883de8d18f6dd72c2d247e905727c970f31ad095aa52c8b19dde435d0f`;
  ELF `aaf5340ccc4c1b4c84414bdfa4a6af77781e85afed6b288df6f0148e08fd29a0`;
  map `ad45ee98bc2d24112ff3c4c2cd87b479c053157aa1f917c1ccb5705b0fe46c70`;
  symbols `03d712510862ac7ab6132f040c8da2b3845d39ff698b930cf465202b1048e868`.
- Constraint: do not claim loading-screen correctness, camera correctness,
  pistol-shot stability, or visual/audio correctness until physical Vita
  evidence returns. The first approved physical gate remains loading-screen
  visual acceptance using user observation plus the returned BMP/state metadata.
  Only after that gate passes should user manual input establish a fresh route
  recording.

## 2026-08-24 — dev38 loading visual-gate schema candidate

`[█████████░] 9/10 current evidence gates complete`

- Now: A3.5-dev38 is the active source/build/package candidate. No dev38 Vita
  deployment or runtime iteration has been attempted.
- Source correction: returned loading-screen capture evidence now uses schema
  v4 and writes `loading_visual_gate` metadata into `loading-screen-state.json`
  and the summary. The metadata records the expected 640x480 original loading
  logical size, 960x544 native display/framebuffer size, fullscreen mapping,
  original `LoadingScreenClass` ownership, direct VitaGL loading overlay
  disabled, `loadscreen_*` V flip enabled, and gameplay UVs unchanged.
- Retained fixes: dev38 keeps the shared original LoadingScreenClass owner,
  CombatManager progress ownership, original `loading_screen.Render(true)`
  callback semantics, scoped 640x480 loading resolution mapped to Vita 960x544,
  the bounded `loadscreen_*` V correction, the required returned loading
  BMP/state capture gate, dev35's heap `A31FrameHistory` stack-frame fix,
  dev36's camera-Y boundary correction, and dev37's DataSafe invalid-handle
  guard.
- Evidence: loading-screen capture/comparator contracts pass 7/7. Focused
  data-safe, conversation, route-runner, and VDB crash snapshot-delta contracts
  pass 19/19. Fast package focused contracts pass 17/17. ARM ELF compile/link,
  SELF/VPK identity, compressed VPK validation, SHA manifest, and
  retail-payload exclusion pass; the VPK contains only `eboot.bin` and
  `sce_sys/param.sfo`.
- Evidence-gate hardening: the returned loading capture validator now rejects
  bar-only or tiny/misplaced nonblack evidence by measuring full-frame content
  width/height extent and preserving bounding-box, edge-band, and quadrant
  diagnostics. Focused loading/comparison tests pass 12/12; the broader
  no-device crash/loading/route tooling suite passes 30/30 plus shell syntax
  and `BUILD_STATE.json` parsing. This strengthens the next physical loading
  gate but does not claim visual correctness.
- Automation prep: `tools/run_a35_vita_route_session.sh` now targets dev38,
  admits only the exact dev38 SELF plus known exact prior dev37 through dev7
  predecessors, uses dev38 runtime/evidence paths, prints a
  `LOADING_SCREEN_VISUAL_GATE` before launch, requires the loading-screen PASS
  log, pulls `loading-screen-frame.bmp` and `loading-screen-state.json`, then
  validates schema-v4/candidate/runtime-log identity, exact visual-gate
  metadata, native 960x544 24-bit BMP dimensions, nonblank/color evidence,
  broad full-frame content extent, and unchanged retail M00 hash before
  setting `new_route_retained=1`. It
  records the loading capture path and validation report in the receipt,
  snapshots VDB1 crash state before launch, takes a post-run snapshot on
  non-clean/failure paths, compares snapshots locally with
  `tools/vdb_crash_snapshot_delta.py`, directly pulls only new `ux0:/data`
  dumps through VDB1, verifies dump hashes, and supplies the dev38 ELF/SHA to
  VDB crash reports.
- Manual crash retrieval: `tools/collect_latest_vita_crash_dump.sh` now exposes
  the same read-only VDB crash snapshot/delta/pull/hash-check/report path for a
  user-driven crash that happens outside the route runner. The first dev38
  manual-crash collection under
  `build/device-evidence/A3.5-dev38-manual-crash-20260825T005958Z/` found no
  new dump beyond the 16-entry dev37 baseline and reports
  `device_mutation=false`.
- Exact hashes: VPK
  `61627ffbd4ce78d73b6d91fe6c59ab7c50ee3f2cacc77cf6e5fca1648362b34e`;
  packaged SELF `d8293dc331ee4460f5ee4527f08d05085aed263fbfb9846550cf35b575b1184b`;
  ELF `0b7b5f5d442c7e7ffae0e5e4292fc0a266dba42446290cbbdaf89d475a6aa066`;
  map `1ee5f2e1acfea715f72e4ac1f6e04a28c4d902f6b7de495664fcd470b4f54536`;
  symbols `d5ba4c8d5b869134841f7c1164d81c48ac6549ac8dcc88f22a05cc424b048401`.
- Constraint: do not claim loading-screen correctness, camera correctness,
  pistol-shot stability, or visual/audio correctness until physical Vita
  evidence returns. The first approved physical gate remains loading-screen
  visual acceptance using user observation plus the returned BMP/state metadata.
  Only after that gate passes should user manual input establish a fresh route
  recording.

## 2026-08-24 — dev37 VDB-symbolicated DataSafe pistol-crash guard candidate

`[█████████░] 9/10 current evidence gates complete`

- Historical: A3.5-dev37 is superseded by A3.5-dev38. No dev37 Vita deployment
  or runtime iteration was attempted.
- Crash evidence: the VDB PSP2 DMP analyzer was used on the retained dev19
  pistol-shot dump
  `build/device-evidence/a3.5-dev19-route-record-20260824-203126/crash-dumps/psp2core-1787603646-0x0000a634eb-eboot.bin.psp2dmp`
  with dump SHA-256
  `43490e2ed2c52a70fbb6821b3234cc30af83f5735cb373ca46146718d9c3eb90`.
  With descriptor-pinned dev19 ELF SHA-256
  `4eb15480cb7cadb926487a277b157af15326a0f200e75fe7d95b53337c69788e`
  and source-derived module base `0x81012000`, VDB maps the data-abort PC
  `0x810a2d8e` to `GenericDataSafeClass::Get_Entry` at `datasafe.cpp:350`.
- Source correction: dev37 adds deterministic staging patch
  `port/patches/commando-a35-datasafe-invalid-handle-guard.patch`. Release
  builds now fail closed before dereferencing `Safe[list]` in
  `GenericDataSafeClass::Get_Entry`, `Get_Entry_Type`, and
  `Get_Entry_By_Index`; debug `ds_assert` ownership remains intact.
- Retained fixes: dev37 keeps the shared original LoadingScreenClass owner,
  CombatManager progress ownership, original `loading_screen.Render(true)`
  callback semantics, scoped 640x480 loading resolution mapped to Vita 960x544,
  the bounded `loadscreen_*` V correction, the required returned loading
  BMP/state capture gate, dev35's heap `A31FrameHistory` stack-frame fix, and
  dev36's camera-Y boundary correction.
- Evidence: DataSafe crash contract passes 3/3. Focused data-safe,
  conversation, route-runner, and VDB crash snapshot-delta contracts pass
  19/19. Fast compile/package focused contracts pass. ARM ELF compile/link,
  SELF/VPK identity, compressed VPK validation, SHA manifest, and
  retail-payload exclusion pass; the VPK contains only `eboot.bin` and
  `sce_sys/param.sfo`.
- Automation prep at the time: `tools/run_a35_vita_route_session.sh` targeted
  dev37, admitted only the exact dev37 SELF plus known exact prior dev36
  through dev7 predecessors, used dev37 runtime/evidence paths, printed a
  `LOADING_SCREEN_VISUAL_GATE` before launch, requires the loading-screen PASS
  log, pulled `loading-screen-frame.bmp` and `loading-screen-state.json`,
  recorded the loading capture path in the receipt, snapshotted VDB1 crash
  state before launch, took a post-run snapshot on non-clean/failure paths,
  compared snapshots locally with `tools/vdb_crash_snapshot_delta.py`, directly
  pulled only new `ux0:/data` dumps through VDB1, verified dump hashes, and
  supplied the dev37 ELF/SHA to VDB crash reports. It passed shell syntax plus
  10/10 route-session runner tests and the 1/1 crash snapshot-delta comparator
  test.
- Exact hashes: VPK
  `ab2842fb52c8d8349346232d6d2c8d7e58c020aba70a441a635db7d1568d75f4`;
  packaged SELF `f4d05d0c79d0a63ec9c24a94e875f9a46555d8e813aa6272ec3eb50f20e23bce`;
  ELF `f99795324fa3dea5660d9abc750b85ae00167ea705057dbaabd4573ff56887fc`;
  map `66b1f533ebd2c85cf24dea6b1e78674110cb44737ad2ee77b0c9be43b4c7fd54`;
  symbols `a75863d852f446b27448a715b8e148bdf6d381e059816602ddb3e090afd67790`.
- Constraint: do not claim pistol-shot stability, loading-screen correctness,
  camera correctness, or visual/audio correctness until physical Vita evidence
  returns. Latest read-only VDB1 crash retry under
  `build/device-evidence/a3.5-dev37-readonly-crash-retry-20260825T003102Z`
  found 16 existing `ux0:/data` crash entries, matching the older dev34
  snapshot count, with `new_count=0`; the latest user-reported crash is not
  present in that crash root. VDB `debug crash collect --since-bundle` rejects
  both old and fresh snapshots with `crash baseline snapshot schema is invalid`,
  so the route runner intentionally avoids that VDB path and uses local
  snapshot comparison plus direct VDB1 pull/report for future approved cycles.

## 2026-08-24 — dev36 camera-Y/loading-capture source/build/package candidate

`[████████░░] 8/10 current evidence gates complete`

- Historical: A3.5-dev36 is superseded by A3.5-dev37. No dev36 Vita
  deployment or runtime iteration was attempted.
- Source correction: after the latest physical feedback still reported inverted
  camera up/down, dev36 changes only the Vita right-stick Y mouse-delta default
  from inverted to non-inverted. Original `Input::Update_Sliders()` and
  `CCamera` remain unchanged and continue to own action/camera integration.
- Retained fixes: dev36 keeps the shared original LoadingScreenClass owner,
  CombatManager progress ownership, original `loading_screen.Render(true)`
  callback semantics, scoped 640x480 loading resolution mapped to Vita 960x544,
  the bounded `loadscreen_*` V correction, the required returned loading
  BMP/state capture gate, and dev35's heap `A31FrameHistory` stack-frame fix.
- Evidence: compiled Vita controller axis contract passes 22/22. Focused
  input/route/loading/conversation contracts pass 25/25. Fast compile/package
  focused contracts pass 17/17. ARM ELF compile/link, SELF/VPK identity,
  compressed VPK validation, SHA manifest, and retail-payload exclusion pass;
  the VPK contains only `eboot.bin` and `sce_sys/param.sfo`.
- Automation prep at the time: `tools/run_a35_vita_route_session.sh` targeted dev36,
  admits only the exact dev36 SELF plus known exact prior dev35 through dev7
  predecessors, uses dev36 runtime/evidence paths, prints a
  `LOADING_SCREEN_VISUAL_GATE` before launch, requires the loading-screen PASS
  log, pulls `loading-screen-frame.bmp` and `loading-screen-state.json`, records
  the loading capture path in the receipt, and passes shell syntax plus
  route-session runner tests.
- Exact hashes: VPK
  `5fcfcce9c32cb5b09881b79c07f98720d42763659f3c7612665db19b1878ce00`;
  packaged SELF `4451964aeefd1c0e5f690852e7111986f28006dc45900aff292b06d8cdb9e636`;
  ELF `e1ff05515cff40ba224aec1782b204e3a166479b92f1e2de84aefc2aea5d36e2`;
  map `508343cecb2794079d7dda0d259eca5e2e01a6a3f1117fd4ec4b9a0e1a8dfdb1`;
  symbols `dc82fd98fa0b7b852e1bfea443b747189ae2e1d609158957c48ab118ac8e8520`.
- Constraint: do not claim visual or camera correctness until physical Vita
  evidence returns. If explicitly approved for a device run, the first gate is
  still loading-screen layout, orientation, scaling, text placement, and
  progress acceptance using both user observation and the returned loading BMP;
  stop immediately if it is still wrong.

## 2026-08-24 — dev35 stack-frame crash fix source/build/package candidate

`[████████░░] 8/10 current evidence gates complete`

- Historical: A3.5-dev35 is superseded by A3.5-dev36. No dev35 Vita deployment
  or runtime iteration was attempted.
- Crash evidence: the approved dev34 route-record attempt produced
  `psp2core-1787615083-0x0004072f45-eboot.bin.psp2dmp` under
  `build/device-evidence/a3.5-dev34-route-record-20260824-234411/`; SHA-256
  is `fd27001824bccc038c28788ec25be7f4cb51ba8183af2319f652ff05d6eab05c`.
  VDB PSP2 analyzer with module `RenegadeVitaA31` base `0x81047000` maps the
  data-abort PC to `A31_Vita_Run_Interactive_Runtime()` line 605, the function
  prologue. The runtime log stopped after retail preflight.
- Source correction: dev35 moves `A31FrameHistory` off the Vita stack, reuses
  one heap history for loading and gameplay capture, resets it between the
  loading-screen capture and interactive capture stream, and deletes it during
  teardown. The original LoadingScreenClass path and capture gate are retained.
- Evidence: focused loading/route/conversation contracts pass 18/18. Fast
  compile/package focused contracts pass 17/17. ARM ELF compile/link, SELF/VPK
  identity, compressed VPK validation, SHA manifest, and retail-payload
  exclusion pass; the VPK contains only `eboot.bin` and `sce_sys/param.sfo`.
  Objdump shows the `A31_Vita_Run_Interactive_Runtime()` prologue stack
  subtraction reduced from about 276 KB in dev34 to about 17 KB in dev35.
- Automation prep at the time: `tools/run_a35_vita_route_session.sh` targeted
  dev35, admitted only the exact dev35 SELF plus known exact prior dev34
  through dev7 predecessors, used dev35 runtime/evidence paths, printed a
  `LOADING_SCREEN_VISUAL_GATE` before launch, requires the loading-screen PASS
  log, pulls `loading-screen-frame.bmp` and `loading-screen-state.json`, records
  the loading capture path in the receipt, and passes shell syntax plus 9/9
  route-session runner tests.
- Exact hashes: VPK
  `1c6b0926e420962a6eb04518863fd0c949f63b361a403d7ed0f50a968017a709`;
  packaged SELF `1dbb00a3191b1cb11272ee1faf0ca083e480284b9e6d78d7c1c94a287ea3ec56`;
  ELF `b3f63883571dd59ed9831f6935430d02e3e8d3a0a98bd7ad94ed27665b502727`;
  map `85ce85a442890eda324bb7d82f56254d966a9581cb152378b46972006d12ee87`;
  symbols `56e6a804918c91805e6eccd24bb0b35cb7f995d8d9ebdfdf53f7c4d3972f70fa`.
- Constraint: do not claim visual correctness until physical Vita evidence
  returns. If explicitly approved for a device run, the first gate is still
  loading-screen layout, orientation, scaling, text placement, and progress
  acceptance using both user observation and the returned loading BMP; stop
  immediately if it is still wrong.

## 2026-08-24 — dev34 loading-screen capture-gated route source/build/package candidate

`[████████░░] 8/10 current evidence gates complete`

- Historical: A3.5-dev34 is superseded by A3.5-dev35. The approved route-record
  attempt crashed before first original-runtime log and before loading-screen
  capture; rollback restored the prior executable.
- Source correction: dev34 retains dev33's `loadscreen_*` V-orientation bridge
  and adds a required loading-screen capture bundle at original
  `level_ready`. The capture is labelled
  `phase=original-loading-screen reason=level-ready` and is written before
  interactive gameplay capabilities are applied.
- Reuse boundary: the loading path remains the reusable original owner:
  Campaign backdrop parsing, `MenuBackDropClass`, `Render2DSentenceClass`,
  `SaveLoadStatus`, CombatManager progress, and
  `loading_screen.Render(true)` callback behavior; Vita adds only scoped
  resolution mapping, the loading-texture orientation bridge, and the
  evidence-only capture.
- Evidence: focused loading/route/indexed/staging contracts pass 21/21. Fast
  compile/package focused contracts pass 17/17. ARM ELF compile/link, SELF/VPK
  identity, compressed VPK validation, SHA manifest, and retail-payload
  exclusion pass; the VPK contains only `eboot.bin` and `sce_sys/param.sfo`.
- Automation prep: `tools/run_a35_vita_route_session.sh` now targets dev34,
  admits only the exact dev34 SELF plus known exact prior dev33 through dev7
  predecessors, uses dev34 runtime/evidence paths, prints a
  `LOADING_SCREEN_VISUAL_GATE` before launch, requires the loading-screen PASS
  log, pulls `loading-screen-frame.bmp` and `loading-screen-state.json`, records
  the loading capture path in the receipt, and passed shell syntax plus 9/9
  route-session runner tests. It was executed once for an approved route
  recording and crashed before the capture gate; rollback completed.
- Exact hashes: VPK
  `da0a3124b280d700f331a057533b1d71b7013764ef7f889ebef36257c6be3691`;
  packaged SELF `72aa828d090d3e74180b03582378c73c25a737b0ea7ffdc728c80564c35260ef`;
  ELF `0e5a9a4dcd59165ff541f4bcf40e03d37384cffe9f88463f8f10dd14d0997cdb`;
  map `1d9cf27b682bfd9fb0c168709af86b20fcbf40ca4ac09256df38796f7b132e25`;
  symbols `dce75f31cd39b3f62d914eae04a53505a1f4dfb58f86cdebe781b8e0a3d8a188`.
- Constraint: do not claim visual correctness until physical Vita evidence
  returns. If explicitly approved for a device run, the first gate is still
  loading-screen layout, orientation, scaling, text placement, and progress
  acceptance using both user observation and the returned loading BMP; stop
  immediately if it is still wrong.

## 2026-08-24 — dev33 loading-screen texture-orientation source/build/package candidate

`[████████░░] 8/10 current evidence gates complete`

- Historical: A3.5-dev33 is superseded by A3.5-dev34. It was a source/build/package candidate only. No Vita
  filesystem was accessed and no deployment or runtime iteration was attempted.
- Source correction: dev32 kept the original `LoadingScreenClass` owner but
  still inherited a concrete Vita renderer orientation mismatch for
  `loadscreen_*` textures used by the original C&C multiplayer loading W3D.
  Dev33 keeps global gameplay/world UV semantics unchanged and flips V only
  when the bound original texture basename starts with `loadscreen_`.
- Reuse boundary: this remains the reusable loading-screen path. The original
  owner still performs Campaign backdrop parsing, `MenuBackDropClass`,
  `Render2DSentenceClass`, `SaveLoadStatus`, CombatManager progress, and
  `loading_screen.Render(true)` callback behavior; Vita adds only scoped
  resolution mapping and the loading-texture orientation bridge.
- Evidence: focused loading/indexed/staging contracts pass 12/12. Fast package
  focused contracts pass 17/17. ARM ELF compile/link, SELF/VPK identity,
  compressed VPK validation, SHA manifest, and retail-payload exclusion pass;
  the VPK contains only `eboot.bin` and `sce_sys/param.sfo`.
- Automation prep: `tools/run_a35_vita_route_session.sh` now targets dev33,
  admits only the exact dev33 SELF plus known exact prior dev32 through dev7
  predecessors, uses dev33 runtime/evidence paths, prints a
  `LOADING_SCREEN_VISUAL_GATE` before launch, records that logs cannot prove
  visual acceptance, and passes shell syntax plus 9/9 route-session runner
  tests. It has not been executed against the Vita.
- Exact hashes: VPK
  `d7a7386922ab8e8daa887890e7b3bfe71daa8e1ee9e4c03798f44dd3086c1dad`;
  packaged SELF `3f3f0519c16280137ab656d2761f7c659e54170cebeed00a09d316db0d515465`;
  ELF `b36afa9a0841f8d2b41fa808e3dc0aff4069bcd99b086c66465ca3389e4f0171`;
  map `cad0bdadfe9d0ceb0c5cb64ab9e6188fc47dec65e1b0eb895e550311d01d4de1`;
  symbols `7a84eb83de43e8b6046269e5f6433b6f04ab3a1590c98df0c2f1191068b9bb01`.
- Constraint: do not claim visual correctness until physical Vita evidence
  returns. If explicitly approved for a device run, the first gate is still
  loading-screen layout, orientation, scaling, text placement, and progress
  acceptance; stop immediately if it is still wrong.

## 2026-08-24 — dev32 restage-proven shared LoadingScreenClass source/build/package candidate

`[████████░░] 8/10 current evidence gates complete`

- Historical: A3.5-dev32 is superseded by A3.5-dev33. It was a source/build/package candidate only. No Vita
  filesystem was accessed and no deployment or runtime iteration was attempted.
- Source correction: dev31's shared original `LoadingScreenClass` extraction is
  now durable under deterministic staging. `tools/stage_sources.sh` applies
  `commando-a35-shared-loadingscreen-owner.patch`, which creates
  `loadingscreen.cpp/.h` and disables the duplicate in `combatgmode.cpp`.
  A forced-restage build no longer depends on reused staged files.
- Retained loading correction: direct Vita still creates/renders/destroys the
  shared original owner through the bridge, with original Campaign backdrop
  parsing, `MenuBackDropClass`, `Render2DSentenceClass`, `SaveLoadStatus`,
  CombatManager progress, original `loading_screen.Render(true)` callback, and
  scoped 640x480 WW3D/DX8Wrapper/Render2D loading layout mapped to Vita 960x544.
- Evidence: forced-restage A3.5-dev32 fast package passes 17/17 focused
  contracts. Staging/loading contracts pass 7/7. ELF/SELF/VPK identity,
  compressed VPK validation, SHA manifest, and retail-payload exclusion pass;
  the VPK contains only `eboot.bin` and `sce_sys/param.sfo`.
- Exact hashes: VPK
  `075682f499fd41f7783d79bcde25d1bc523224330bc58d2d3374d34288d9cb2d`; packaged
  SELF `a45d2a8b54c48e89327eab498bf9a439f497093e85719ffbce76de664a3eef12`;
  ELF `a9b3831cd6f7d296c61de26b2387e38cc3248e6623b2e787e699595c9c69dc82`;
  map `a6b4a7afcc5a221b2de1d85c752d0cf56814c45885e956391f3940e08ab7962d`;
  symbols `6b897415564fc0858d542332c57b7101f629c325e3bc72b6112581b7d1e941c1`.
- Constraint: the route runner is not updated to dev32 yet. Do not run another
  Vita iteration without explicit approval. If approved, the first gate is
  loading-screen layout, orientation, scaling, text placement, and progress
  acceptance; stop immediately if it is still wrong.

## 2026-08-24 — dev31 shared original LoadingScreenClass source/build/package candidate

`[████████░░] 8/10 current evidence gates complete`

- Historical: A3.5-dev31 is superseded by A3.5-dev32. It was a source/build/package candidate only. No Vita
  filesystem was accessed and no deployment or runtime iteration was attempted.
- Source correction: dev30 still used a Vita-side loading presenter clone.
  Dev31 links a shared original `LoadingScreenClass` implementation from
  `staging/commando/loadingscreen.cpp` and has direct Vita create/render/destroy
  that original owner through a narrow bridge. The scoped original 640x480
  WW3D/DX8Wrapper/Render2D loading layout and Vita 960x544 presentation mapping
  are retained.
- Reuse boundary: because the original owner now handles Campaign backdrop
  parsing, `MenuBackDropClass`, `Render2DSentenceClass`, `SaveLoadStatus`,
  CombatManager progress, and the original `loading_screen.Render(true)`
  callback, the same path can be bootstrapped to other original loading states
  instead of being a one-screen Vita overlay.
- Evidence: focused loading-screen and mission-conversation contracts pass 9/9.
  The final targeted loading/conversation/input-route/route-validator suite
  passes 16/16. A3.5-dev31 fast package passes 17/17 focused contracts.
  ELF/SELF/VPK identity, compressed VPK validation, SHA manifest, and
  retail-payload exclusion pass; the VPK contains only `eboot.bin` and
  `sce_sys/param.sfo`.
- Exact hashes: VPK
  `0a1fd7c2bb5b06f448970529d247c25b30f0acd0265458e2e680a2e7a26a5b83`; packaged
  SELF `8375f3f30fe57e309bcf2b68b25a1e5f4a3a99f24953bbd36bd940cc2005c424`;
  ELF `058ed16d0ed5e3e87dcf5abaaf38edafb5e3943c57a48cbd160359385e5d049d`;
  map `94e3b6154242e6b17263963da8195a671c8090c9215634e9bdf13b3d4a6413e6`;
  symbols `f66dbd7f6798deb74acb62293a6d989f6f550022cde653b6ed3961382f1046ea`.
- Constraint at the time: the route runner was not updated to dev31. The
  current route-runner constraint is governed by the dev32 section above.

## 2026-08-24 — dev30 original WW3D/DX8 loading logical-resolution source/build/package candidate

`[████████░░] 8/10 current evidence gates complete`

- Historical: A3.5-dev30 is superseded by A3.5-dev31. It was a source/build/package candidate only. No Vita
  filesystem was accessed and no deployment or runtime iteration was attempted.
- Source correction: dev29 scoped `Render2DClass` to 640x480, but original
  `Render2DClass::Render()` and `CameraClass::Apply()` still get viewport
  dimensions from WW3D/DX8 resolution queries. Dev30 scopes
  WW3D/DX8Wrapper/Render2D together to the original 640x480 loading logical
  resolution, then maps that logical viewport to the full 960x544 Vita
  framebuffer at the native boundary. Native resolution is restored before
  gameplay/HUD rendering.
- Retained loading correction: the failed direct VitaGL tile overlay remains
  absent. The path uses `STRINGS.TDB`, `StyleMgrClass`, original in-game fonts,
  `SaveLoadStatus`, original Campaign backdrop description 94,
  `MenuBackDropClass`, both `Render2DSentenceClass` text layers,
  `CombatManager::Set_Load_Progress(0)`,
  `CombatManager::Get_Load_Progress()`, and the original
  `cNetwork::Update` render callback semantics.
- Evidence: focused loading-screen and mission-conversation contracts pass 9/9.
  The final targeted loading/conversation/input-route/route-validator suite
  passes 16/16. A3.5-dev30 fast package passes 17/17 focused contracts.
  ELF/SELF/VPK identity, compressed VPK validation, SHA manifest, and
  retail-payload exclusion pass; the VPK contains only `eboot.bin` and
  `sce_sys/param.sfo`.
- Exact hashes: VPK
  `6984647ae9e8503f1ca3c2aaea7f0dbbec5191839456046f85a82809505d2741`; packaged
  SELF `c3810e776f21ce7937c6a261893aed92ed3e5e0cafadf99e15020cb91094c52b`;
  ELF `93ef8f52749375b9f815ee475f1ab66b787569ad6afa85fbe86c7c4ca7389ca8`;
  map `87021178e4f20c57b522b7f06a1780d1f3008430edc938415b0b24a42fcfc487`;
  symbols `bef4bde4c6ed0d08c90e3b243b61d006b5a33b52064e44081a4ef63fe13740c6`.
- Constraint at the time: the route runner was not updated to dev30. The
  current route-runner constraint is governed by the dev31 section above.

## 2026-08-24 — dev29 original loading logical-resolution source/build/package candidate

`[████████░░] 8/10 current evidence gates complete`

- Historical: A3.5-dev29 is a superseded source/build/package candidate only. No Vita
  filesystem was accessed and no deployment or runtime iteration was attempted.
- Source correction: dev28 restored original `loading_screen.Render(true)`
  callback behavior but still built `MenuBackDropClass` camera/view-plane math
  and `Render2DSentenceClass` text/wrap coordinates while
  `Render2DClass::ScreenResolution` was Vita native 960x544. Dev29 scopes
  `Render2DClass` to the original 640x480 loading logical resolution for
  loading-screen construction/rendering, then restores the Vita resolution
  before gameplay/HUD rendering.
- Retained loading correction: the failed direct VitaGL tile overlay remains
  absent. The path uses `STRINGS.TDB`, `StyleMgrClass`, original in-game fonts,
  `SaveLoadStatus`, original Campaign backdrop description 94,
  `MenuBackDropClass`, both `Render2DSentenceClass` text layers,
  `CombatManager::Set_Load_Progress(0)`,
  `CombatManager::Get_Load_Progress()`, and the original
  `cNetwork::Update` render callback semantics.
- Evidence: focused loading-screen and mission-conversation contracts pass 9/9.
  The final targeted loading/conversation/input-route/route-validator suite
  passes 16/16. A3.5-dev29 fast package passes 17/17 focused contracts.
  ELF/SELF/VPK identity, compressed VPK validation, SHA manifest, and
  retail-payload exclusion pass; the VPK contains only `eboot.bin` and
  `sce_sys/param.sfo`.
- Exact hashes: VPK
  `3e6b5211fb0e82214bd4ea93a6641b560559c2e232b1fc48896d84b4f8d35470`; packaged
  SELF `899df03c98153d8888d00192cf7ef40875901f77aaca96b7c7a2434883cd53f0`;
  ELF `d284b8f92861e3b8da643552bfbc0bf74999215f73ea9004b9feb77112b01d97`;
  map `1404cae05c451799e6e9e4e337f7e84874e45c12172b10cf4d55efc04327475b`;
  symbols `2f0cab60b085f4c81ca43953a954de1a6cb28261c0bbd8e983670cf3485e528f`.
- Constraint: the route runner is not updated to dev29 yet. Do not run another
  Vita iteration without explicit approval. If approved, the first gate is
  loading-screen layout, orientation, scaling, text placement, and progress
  acceptance; stop immediately if it is still wrong.

## 2026-08-24 — dev28 original loading render-callback source/build/package candidate

`[████████░░] 8/10 current evidence gates complete`

- Historical: A3.5-dev28 is a superseded source/build/package candidate only. No Vita
  filesystem was accessed and no deployment or runtime iteration was attempted.
- Source correction: dev27 restored original `CombatManager` load-progress
  ownership but still missed the callback behavior used by original
  `loading_screen.Render(true)`. Dev28 now forwards `cNetwork::Update` through
  `WW3D::Begin_Render` during loading presentation, while retaining
  `CombatManager::Set_Load_Progress(0)`, `CombatManager::Get_Load_Progress()`,
  and the original `LoadPercentage / LoadTime` progress calculation.
- Retained loading correction: the failed direct VitaGL tile overlay remains
  absent. The path uses `STRINGS.TDB`, `StyleMgrClass`, original in-game fonts,
  `SaveLoadStatus`, original Campaign backdrop description 94,
  `MenuBackDropClass`, and both `Render2DSentenceClass` text layers.
- Evidence: focused loading-screen and mission-conversation contracts pass 9/9.
  A3.5-dev28 fast package passes 17/17 focused contracts. ELF/SELF/VPK
  identity, compressed VPK validation, SHA manifest, and retail-payload
  exclusion pass; the VPK contains only `eboot.bin` and `sce_sys/param.sfo`.
- Exact hashes: VPK
  `f05e59cd0d8ad57308a819c20729859ff12dfc1be763938d758f6dc0bb036178`; packaged
  SELF `5d1226557ac8b2ce5d66c0f9ae8b59977af3fa3bc16fbb2b18ffbc39802b5aed`;
  ELF `7e6e47453987e8c18f251d2df36d4d0ce0e45e1874130c2b59ec239dec0bd7ea`;
  map `4b1515431f7d5d76b96f35fbb740fc67d18321f14db6fcb196bcd4c17cc62846`;
  symbols `0a4b2848ec685193125d98d851a1b969d574ddb6df8070f4dca03b75a7aa4808`.
- Constraint: the route runner is not updated to dev28 yet. Do not run another
  Vita iteration without explicit approval. If approved, the first gate is
  loading-screen layout, orientation, scaling, text placement, and progress
  acceptance; stop immediately if it is still wrong.

## 2026-08-24 — dev27 original loading-progress source/build/package candidate

`[████████░░] 8/10 current evidence gates complete`

- Historical: A3.5-dev27 is a superseded source/build/package candidate only. No Vita
  filesystem was accessed and no deployment or runtime iteration was attempted.
- Source correction: dev26 completed the original loading model/text/string/style
  path but still used manual terminal progress fractions. Dev27 now matches the
  original `LoadingScreenClass::Render` progress owner: it calls
  `CombatManager::Set_Load_Progress(0)` before loading-screen construction,
  samples `CombatManager::Get_Load_Progress()` inside each render after
  `TimeManager::Update_Frame_Time()`, calculates `LoadPercentageRate` from
  `LoadPercentage / LoadTime`, and removes the manual `0.985f`, `0.995f`, and
  forced-`1.0f` terminal updates.
- Retained loading correction: the failed direct VitaGL tile overlay remains
  absent. The path uses `STRINGS.TDB`, `StyleMgrClass`, original in-game fonts,
  `SaveLoadStatus`, original Campaign backdrop description 94,
  `MenuBackDropClass`, and both `Render2DSentenceClass` text layers.
- Evidence: focused loading-screen and mission-conversation contracts pass 9/9.
  A3.5-dev27 fast compile and fast package each pass 17 focused contracts.
  ELF/SELF/VPK identity, compressed VPK validation, SHA manifest, and
  retail-payload exclusion pass; the VPK contains only `eboot.bin` and
  `sce_sys/param.sfo`.
- Exact hashes: VPK
  `11a801347791528fd4ee6487e90e536dc14019474dd4c94a0b9c2e9ffe05eaa8`; packaged
  SELF `aa37b69ed826d4fbf5ad93506727a5aba4426bbddb16741afe48dfdc5bf9806d`;
  ELF `25fa4ecb6696eec1d09b786fbee8031394e08b905ecebe469ace53aa59ae81f7`;
  map `2a459ec0272c095c5da2aa20294cc0e6ef5dc217af35223ed93e21e15ecf88d6`;
  symbols `23389cf0fb397e1bd1c29b91cbfc5eb4815c0c1942d4ce922c3635bbabc6494e`.
- Constraint: the route runner was not updated to dev27. Do not run another
  Vita iteration without explicit approval. Dev28 is now the active source
  candidate; if approved, the first gate is
  loading-screen layout, orientation, scaling, text placement, and progress
  acceptance; stop immediately if it is still wrong.

## 2026-08-24 — dev26 full original loading-screen source/build/package candidate

`[████████░░] 8/10 current evidence gates complete`

- Now: A3.5-dev26 is the active source/build/package candidate only. No Vita
  filesystem was accessed and no deployment or runtime iteration was attempted.
- Source correction: dev25 restored only the original `MenuBackDropClass` model
  animation. Dev26 completes the original `LoadingScreenClass` path by loading
  `STRINGS.TDB` through the current retail MIX file factory, initializing
  `StyleMgrClass` from `stylemgr.ini`, verifying the in-game normal and big
  fonts, resetting `SaveLoadStatus`, parsing original backdrop description 94
  records (`Model`, `Text`, `Text2`, `Wrap`, `Wrap2`, `Color`, `Test`), and
  rendering the `MenuBackDropClass` plus both `Render2DSentenceClass` text
  layers. The failed direct VitaGL tile overlay remains out of the active path.
- Evidence: focused loading-screen and mission-conversation contracts pass 9/9;
  the final targeted loading/conversation/input-route/route-validator check
  passes 13/13. A3.5-dev26 fast compile links `RenegadeVitaA31`. A3.5-dev26
  fast package passes 17 focused contracts, produces ELF/SELF/VPK artifacts,
  verifies compressed VPK data, passes identity verification, and confirms the
  VPK contains only `eboot.bin` and `sce_sys/param.sfo`.
- Exact hashes: VPK
  `8b5131f97f8e80242303629fd6e2316c05faf26066da2485083de40f69899df1`; packaged
  SELF `8b2ff768f64d2f6d1ac0e79061eb734bb6c9cfa77246bdaebb82924a44de5b6f`;
  ELF `cd89110df49061af29094356bee1ba0a1b7ac7890f910c18a0f9d15f30bd31f9`;
  map `6b66e6f288031c4be7ef5676821c48b526a19ebbfca9ad83c467ef8391d61e16`;
  symbols `e1105f9d026684650492aa9e2b53483777c63f95214da71058d6180fdc888918`.
- Constraint: the route runner is not updated to dev26 yet. Do not run another
  Vita iteration without explicit approval. If approved, the first gate is
  loading-screen layout, orientation, scaling, text placement, and progress
  acceptance; stop immediately if it is still wrong.

## 2026-08-24 — dev25 original MenuBackDrop loading-screen source/build candidate

`[████████░░] 8/10 current evidence gates complete`

- Now: A3.5-dev25 is a source/build/package candidate only. No Vita filesystem
  was accessed and no deployment or runtime iteration was attempted.
- Source correction: the failed direct VitaGL four-tile loading overlay is no
  longer the active path. The direct Vita runtime initializes
  `CampaignManager`, selects original backdrop description 94 for the Renegade
  multiplayer loading screen, parses the original `Model` field, and drives
  `MenuBackDropClass::Set_Model`, `Set_Animation`, `Render`, and
  `Set_Animation_Percentage`. Runtime diagnostics identify this as
  `direct_vitagl_tiles=0` and `progress_owner=model_animation`.
- Evidence: focused loading-screen, input-route ABI, and route-validator
  contracts pass 11/11. The fast package run passes 17 focused contracts,
  produces ELF/SELF/VPK artifacts, verifies compressed VPK data, passes
  identity verification, and confirms the VPK contains only `eboot.bin` and
  `sce_sys/param.sfo`.
- Exact hashes: VPK
  `c34cabb08d56104a95032dcdda4e713ff5245140e38208963fb90bca098496fa`; packaged
  SELF `08cdf12864c0eb67d0675983f61bc7543085f4713d89975015847189f5684d4c`;
  ELF `ba882419108eb8898d8916b1c69775465a555c92d60acd1e0b1b52313e465c97`;
  map `4a2285abc89c1e7cfa511d211133ef37fcd31b188cfa9a5728225ba94f436ba3`;
  symbols `0ee73ee472682e5e52a725670b60e94a6600d05a076be3a8320a7b219db0fe72`.
- Constraint: the route runner is not updated to dev25 yet. Do not run another
  Vita iteration without explicit approval. If approved, the first gate is
  loading-screen layout/orientation/scaling/progress acceptance; stop
  immediately if it is still wrong.

## 2026-08-24 — dev24 physical loading failure; source repair only

`[████████░░] 8/10 current evidence gates complete`

- Now: dev24 is failed/unaccepted physical evidence. Do not run another Vita
  iteration until loading-screen correctness is fixed in source against the
  original Renegade loading-screen owner.
- Physical/user result: dev24 launched with matching SELF
  `1738526a3d556d56a02a077fc92ba115021d44144f4bdf1cbb0e673a0f251e30`, and logs
  under `build/device-evidence/a3.5-dev24-route-replay-20260824-220839/` show
  the four loading tiles resident (`tiles_ready=4/4`). The user-visible loading
  screen still remained wrong, invalidating the direct VitaGL four-tile
  shortcut.
- Secondary route result: the legacy replay did not arm. Runtime input telemetry
  stayed `route_mode/active/index/count/truncated=2/0/0/4880/0`; Mission00
  objective state was already `3/3/3/3/3/3`, so the activation predicate was
  too strict for this build.
- Safety/evidence: the interrupted session was killed and the runner completed
  rollback. Retail data was not mutated.
- Supersession: dev25 replaces this source action by selecting the original
  `CampaignManager`/`MenuBackDropClass` loading path. This section remains only
  as the dev24 failure record.

## 2026-08-24 — dev24 loading orientation/scale package candidate

`[████████░░] 8/10 current evidence gates complete`

- Historical package state before the failed physical replay above: A3.5-dev24
  was built as an unaccepted fast hardware candidate.
- Source review after dev23: transient local retail inspection confirmed the
  coherent original loading screen is `loadscreen_cnc_1..4.dds` in 1,2/3,4
  order with no per-tile vertical flip. Dev23 had the right four textures and
  route activation gate, but its loading draw still inverted each tile and
  cover-cropped the square 1024x1024 composition.
- Source correction: the loading presenter still initializes all four original
  CNC loading tiles and requires native non-fallback upload, but now maps them
  top-left/top-right/bottom-left/bottom-right with unflipped UVs and stretches
  the composed backdrop across the full 960x544 display behind the existing
  progress bar. The world mesh texture path is unchanged.
- Route status: original-control synchronized record/replay from dev23 is
  retained. Replay remains neutral before the gameplay activation gate except
  START abort. The runner is pinned to dev24 while admitting exact dev23/dev22/
  dev21/dev20/dev19/dev18/dev17/dev16/dev7 rollback predecessors.
- Evidence: focused loading, route ABI, validator, and route-runner contracts
  pass 19/19. A3.5-dev24 fast package passed 16 focused build contracts,
  compressed VPK validation, identity checks, SHA manifest verification, and
  retail-payload exclusion.
- Exact hashes: VPK
  `37a96dba2f19b2c3d534ff1ef60246220f9bb612e90f80226afffcd200778445`; packaged
  SELF `1738526a3d556d56a02a077fc92ba115021d44144f4bdf1cbb0e673a0f251e30`;
  ELF `39567a08fc260930fccc5574bebd1bd1eea7c8b94b0fdc71ba7f5d5774dba1d8`;
  map `5186f073a511dbac4173f925265f7efa83aff02b657c4b73d8054a2a5db6b7e1`;
  symbols `0c708ccbfec1d3f67486e71c462508a2720982b7954fad8fd4c252302bee6669`.
- Superseded result: the following physical replay invalidated dev24's loading
  screen. Do not retry dev24; repair the original loading path first.

## 2026-08-24 — dev23 four-tile loading and control-synced route candidate

`[████████░░] 8/10 current evidence gates complete`

- Now: A3.5-dev23 is the current unaccepted fast hardware candidate. A
  read-only device status check stopped because the Vita at `10.0.0.202` was
  unreachable (`No route to host`); no install, launch, route write, or
  retail-data operation occurred.
- Physical/user dev22 result: the loading screen remained wrong and the
  recording did not follow the prior path. Source review found dev22 drew only
  `loadscreen_cnc_1.dds`; retail `always.dat` contains the four 512x512 DXT1
  CNC loading tiles `loadscreen_cnc_1..4.dds`. Dev22 also admitted route
  record/replay before the same original player-control phase, so timed samples
  could still start from a different game epoch.
- Source corrections: the loading presenter now initializes all four original
  CNC loading tiles, requires native non-fallback upload for all four, logs
  tile/composed/display dimensions, and draws a centered cover-fit tiled
  backdrop behind the existing full-screen progress bar. The world mesh texture
  path is unchanged.
- Route corrections: record/replay still uses v2 `delta_us` samples, but the
  route stays inactive until Mission00 reports objective 1 pending with
  original player control enabled. Replay stays neutral before activation
  except START abort. The runner now requires the gameplay-activation log gate
  and is pinned to dev23 while admitting exact dev22/dev21/dev20/dev19/dev18/
  dev17/dev16/dev7 rollback predecessors.
- Evidence: focused loading, route ABI, validator, and route-runner contracts
  pass 19/19. A3.5-dev23 fast package passed 16 focused build contracts,
  compressed VPK validation, identity checks, SHA manifest verification, and
  retail-payload exclusion.
- Exact hashes: VPK
  `38be588b9709f628243509a8b3bc11e7e3ed2a6aeaed2ffe82145844393e3f7d`; packaged
  SELF `9dbfbce006634472aec5ce13b300d3924f14e6d24fde6e6cd3730acbe22a12cd`;
  ELF `6a0bbcd2c594ede7f7ba979862f08d8eeec93fd5cf31c1537e061684c4f7ccc8`;
  map `a6a51b29de9ac797c9f9bd503dd015469935cff00d73f904aeb02a8e257a235e`;
  symbols `3f97629638e913d04095c2ec410632488aaa1d19578639181442be6e7049608f`.
- Blocker: physical Vita network reachability is currently unavailable. Retry
  the dev23 `record` cycle when the device is awake/on-network and explicit
  install/run authorization is present.

## 2026-08-24 — dev22 loading residency and timed-route candidate

`[████████░░] 8/10 current evidence gates complete`

- Now: A3.5-dev22 is the current unaccepted fast hardware candidate. The first
  hardware record attempt stopped at the initial read-only status check because
  the Vita at `10.0.0.202` was unreachable (`No route to host`); no install,
  launch, route write, or retail-data operation occurred.
- Physical dev21 result: the retained 4,880-sample legacy v1 replay route ran
  but timed out without reaching pistol/conversation progression. Device logs
  showed the loading presenter reached the native full-screen path while the
  retail `loadscreen_cnc_1.dds` texture was not native-resident
  (`ready=0`), so dev21 is failed/unaccepted evidence.
- Source corrections: the loading presenter now calls original
  `TextureClass::Init()` before latching readiness, rejects native fallback,
  logs source and full-screen dimensions, and inverts V only for the direct
  hand-authored loading quad because the DDS upload stores source rows
  bottom-up. The world mesh texture path is unchanged.
- Route corrections: new recordings write v2 route samples with per-sample
  `delta_us`; old v1 routes remain readable only as legacy 60 Hz fallback.
  The runner pulls candidate logs before and after killing a failed session.
- Evidence: focused loading, route ABI, validator, and route-runner contracts
  pass 19/19. A3.5-dev22 fast package passed 16 focused build contracts,
  compressed VPK validation, identity checks, SHA manifest verification, and
  retail-payload exclusion.
- Exact hashes: VPK
  `530a3b22d8f6df5eb69554e842209ee1f66f21a8b8cf94254bacd128226945ae`; packaged
  SELF `528e1e87b97a88047c0b5ab65f1d7bba6d0f03a9edb37a1bca16b04bc3900bcf`;
  ELF `d9d32d84eeb28a7298369d9b6be1f235816ac0f9637e4dcf7af95ddb00185828`;
  map `8dbbf27d4104ef2e0507555eb4adf1244aa39d7f9244a3aecd77ff94d57fd863`;
  symbols `37c9acd07e046a6ce1b0a5b42e8fcb4e22c845818ef10f35ca377ee5559f5be4`.
- Blocker: physical Vita network reachability is currently unavailable. Retry
  the dev22 `record` cycle when the device is awake/on-network.

## 2026-08-24 — dev21 loading/replay correction candidate

`[████████░░] 8/10 current evidence gates complete`

- Now: A3.5-dev21 is the current unaccepted fast hardware candidate. No dev21
  Vita filesystem write has occurred.
- Physical dev20 result: the old 2,214-sample replay route was too short and
  frame-dependent; the user observed route drift and a still-wrong loading
  screen. The dev20 session was terminated and the previous executable was
  restored, so dev20 is failed/unaccepted evidence.
- Source corrections: the loading backdrop now draws the retail multiplayer
  `loadscreen_cnc_1.dds` as one native full-screen quad through the same
  top-left orthographic VitaGL path as the working progress bar, using normal
  D3D top-left UVs because DDS rows are already flipped at upload. Legacy v1
  route replay now advances by elapsed time at a 60 Hz sample timebase instead
  of one sample per current frame.
- Automation: replay can now upload a selected local route with
  `RENEGADE_ROUTE_FILE`, rejects replay routes under 4,000 samples by default,
  and restores the prior route if selected-route replay fails. The runner is
  pinned to exact dev21 SELF and admits exact dev20/dev19/dev18/dev17/dev16/dev7
  predecessor hashes for rollback-safe replacement.
- Evidence: focused loading, route, validator, and route-runner contracts pass
  17/17. A3.5-dev21 fast compile linked 14 affected actions and verified
  ELF/header/map/symbols. A3.5-dev21 fast package passed 16 focused contracts,
  compressed VPK data, identity, manifest, and two-file VPK inventory.
- Exact hashes: VPK
  `526ea4b10dc42ffae29b6010bad14e4d8fc4497249e1bcb7967a018a2dbd03eb`; packaged
  SELF `93ad509992d1f2e286dbcb56648da1bf8fe966911d6fe0707a9ca7f07b9b66ec`;
  ELF `07829f31cadef4f652c9fc25be62a01698c2a0e756a535b3cfb2b923c5f0d9a2`;
  map `784096b71f7753392ffc2356d4ee666591d302739b70df054ac808e49f0a1cb3`;
  symbols `e118d784bfe6e70846150710eea2bf1c5b66b2fbf46bb279ea6fa4fb66d69fc7`.
- Blocker: explicit authorization is required before installing/running dev21
  on the Vita. The next device cycle should be a fresh record, not the drifted
  short replay.

## 2026-08-24 — dev20 camera/loading/particle-crash candidate

`[████████░░] 8/10 current evidence gates complete`

- Now: A3.5-dev20 is the current unaccepted fast hardware candidate; no Vita
  filesystem write occurred during this work unit.
- Physical dev19 result: Logan progression and pistol acquisition were proven
  on hardware. The route reached `MTU_LOGAN_POKE` at frame 2648, restored
  control, granted `Weapon_Pistol_Player`, fired six rounds at the dummy, and
  captured the manual SELECT point. The app then crashed after the pistol-shot
  segment, so dev19 is not accepted.
- Crash evidence: PSP2 dump
  `build/device-evidence/a3.5-dev19-route-record-20260824-203126/crash-dumps/psp2core-1787603646-0x0000a634eb-eboot.bin.psp2dmp`
  has SHA-256
  `43490e2ed2c52a70fbb6821b3234cc30af83f5735cb373ca46146718d9c3eb90`.
  GDB did not recover registers; schema-inferred private thread notes point at
  `ParticleBufferClass::Reset_Size` dereferencing a suspect particle size
  keyframe pointer. The older filename-PC heuristic points elsewhere and is
  recorded only as heuristic.
- Source corrections: camera up/down is flipped back at the Vita
  device-to-mouse-delta boundary; loading now draws the retail multiplayer
  `loadscreen_cnc_1.dds` directly through original `Render2DClass` as a
  full-screen upright panel with the existing VitaGL progress bar over it; the
  particle size-keyframe path now refuses null, unaligned, out-of-range, or
  implausibly large keyframe arrays before dereference.
- Evidence: focused contracts pass 20/20 before build and 15/15 after runner
  update. A3.5-dev20 fast compile linked the ELF and validated compile
  artifacts. A3.5-dev20 fast package passed focused contracts 16/16, VPK
  compressed-data validation, identity checks, and SHA manifest verification.
- Exact hashes: VPK
  `8650d6f5cf65bef9c033551f2e14704db3411ca50867cf4ad5bf85bf36a7af26`; packaged
  SELF `5e4cc4a4ac44173158b5b897a733de6d46fb33390d7233641b760f83a86ce24f`;
  ELF `d7f6e8826cb2d6d26e4b9db70ae9776331656ff0a9052169e9b880c18e468fa0`;
  map `3202979b290677ffbec04c969dd93efb7e421f8e0e3aec1aef5c0877963f7981`;
  symbols `65c0a32a8f194fb76099b2dfd988db02948eda72e20888c7527ff15607a0e355`.
- Automation: `tools/run_a35_vita_route_session.sh` is now pinned to exact
  dev20 SELF and admits only exact dev19/dev18/dev17/dev16/dev7 predecessor
  hashes for rollback-safe replacement. It writes/reads
  `a35-dev20-runtime.log`.
- Blocker: explicit authorization is required before installing/running dev20
  on the Vita. Physical acceptance still requires camera direction, loading
  orientation/scale, pistol-shot stability, sky/materials, audio, and clean
  route exit.

## 2026-08-24 — dev19 Logan progression and camera-Y candidate

`[██████░░░░] 6/10 current evidence gates complete`

- Now: A3.5-dev19 is the current unaccepted fast hardware candidate; no Vita
  filesystem write occurred during this work unit.
- Physical diagnosis from the latest dev18 recording: the app did not crash or
  hard-freeze. Rendering and input telemetry continued to frame 3003, START
  exited cleanly, Logan jump control returned at frame 1640, and
  `MTU_LOGAN_EVA` completed at frame 2520. The first missing checkpoint is that
  `MTU_LOGAN_POKE` never became active, so the original pistol grant and
  `MTU_PARAM_CONTROL_ENABLE` never fired.
- Source correction: `MTU_LOGAN_POKE` is present in retail `M00_Tutorial.mix`.
  `ConversationMgrClass::Think()` now protects the active conversation during
  script callbacks and removes only that same pointer from
  `ActiveConversationList`, preventing a chained conversation from being
  deleted by a stale index after EVA completion.
- Input correction: Vita right-stick camera Y is flipped at the
  device-to-mouse-delta boundary based on the latest physical report; original
  `Input` and `CCamera` remain unchanged.
- Evidence: deterministic staging patch dry-run passes; focused contracts pass
  18/18; A3.5-dev19 package focused contracts pass 16/16; route-runner
  contracts pass 8/8; SHA manifest and VPK zip verification pass. Fast compile
  took 7.9 seconds; fast package took 16.9 seconds.
- Exact hashes: A3.5-dev19 VPK
  `9aa587203223d5bae22581491d67e97a8a822341f8723a5f3872d739946ad4d2`; packaged
  SELF `901fd5a0d7cb137a782ee42c666a91e9d9ca56a7f95397703468b3044f92e125`;
  ELF `4eb15480cb7cadb926487a277b157af15326a0f200e75fe7d95b53337c69788e`.
  The VPK contains only `sce_sys/param.sfo` and `eboot.bin`.
- Remaining visual blockers: loading-screen backdrop is still reported
  mis-scaled/upside-down, and NPC skin/material textures are still wrong though
  bodies are visible. These require phase-labelled physical capture after the
  progression candidate runs; no visual correctness claim is made.
- Blocker: explicit authorization is required before installing/running dev19
  on the Vita.

## 2026-08-24 — dev18 fast-candidate build path added

`[██████░░░░] 6/10 current evidence gates complete`

- Now: use `tools/build_fast_candidate.sh` for hardware-testable iteration
  builds when full canonical acceptance is not required. The canonical
  `tools/build.sh` remains the acceptance path.
- Build-overhead correction: the fast path uses a stable incremental CMake
  tree (`build/vita-fast-candidate` by default), keeps ccache stats, skips the
  full retained host/sanitizer route by default, and restages sources only when
  `RENEGADE_FAST_RESTAGE=1` or staging is missing.
- Compile-loop correction: `RENEGADE_FAST_SCOPE=compile` now builds only the
  linked `RenegadeVitaA31` ELF and intentionally skips the always-dirty VitaSDK
  SELF/VPK packaging steps. `RENEGADE_FAST_SCOPE=package` keeps the existing
  hardware-testable package path. `RENEGADE_FAST_TESTS=none` is available for a
  pure compile/link check; `focused` remains the default.
- Incremental-staging correction: `RENEGADE_INCREMENTAL_STAGE=1` now stages
  into a temporary tree and syncs only changed files into the managed staging
  subdirectories. Fast restage uses that mode by default; canonical staging
  remains destructive unless explicitly opted into incremental mode.
- Dev18 link correction: the direct Vita runtime uses the original
  `MenuBackDropClass` with retail-backed `IF_LVL94LOAD`/`IF_LVL94LOAD.IF_LVL94LOAD`
  and a VitaGL progress bar, without pulling `CampaignManager` into the direct
  runtime loading path.
- Evidence: focused contracts pass 13/13; the fast builder's internal focused
  tests pass 15/15; the existing dev18 build tree completed the final package
  path in 6 Ninja steps after the initial link; identity verification, ELF
  header, symbol, VPK zip, two-file VPK inventory, and retail-exclusion checks
  pass. ccache reported 82.16% hits.
- Incremental-staging evidence: shell syntax plus
  `tools.test_sync_staged_tree`,
  `tools.test_stage_sources_incremental_contract`, and
  `tools.test_fast_candidate_build_contract` pass 7/7. A no-op full stage
  reported `copied=0`, `removed=0`, `unchanged=1943`; the fast builder with
  `RENEGADE_FAST_RESTAGE=1` passed focused contracts 15/15 and identity/VPK
  checks. After the one-time recovery rebuild, Ninja dry-run reports only the
  six Vita SELF/VPK packaging steps and no C++ recompiles.
- Compile-scope evidence: `bash -n tools/build_fast_candidate.sh` and focused
  fast-build/staging contracts pass 8/8. A no-op run with
  `RENEGADE_FAST_SCOPE=compile RENEGADE_FAST_TESTS=none` completed in 2.1s,
  reported `ninja: no work to do`, validated ELF identity, and wrote
  `<managed-dist>/A3.5-dev18-FAST-COMPILE-SHA256SUMS.txt`.
- Route-runner update: `tools/run_a35_vita_route_session.sh` now admits exact
  dev18 SELF `058a10a594a8038833d8cced9a4b7a5207a4100079da44beef5c645a7ca69278`
  and exact predecessor hashes for dev17/dev16/dev7 only. Shell syntax and
  `tools.test_vita_route_session_runner` pass 7/7. No Vita filesystem was
  accessed by this metadata update.
- Fast candidate hash: VPK SHA-256
  `1d4daca0cca2972dcaf76714d558bb21a34fa18dd03a39a02262180e4c82d092`
  after the incremental-staging validation rebuild.
  Dist manifest:
  `<managed-dist>/A3.5-dev18-FAST-SHA256SUMS.txt`.
- Boundary: no Vita filesystem was accessed and no deployment was attempted.
  This is not physical acceptance and not a substitute for the full canonical
  build gate before milestone acceptance.
- Blocker: none for fast-build iteration; physical visual/audio/progression
  acceptance remains pending.

## 2026-08-24 — dev16 original WWAudio lifecycle candidate ready

`[████████░░] 8/10 current evidence gates complete`

- Now: await explicit authorization for the exact-hash dev16 physical replay;
  the Vita was not modified by this work unit. Read-only admission at
  `build/device-evidence/a3.5-dev16-admission-20260824-185719/` confirms the
  device is reachable, app stopped, exact dev7 is installed, retail M00 and the
  retained route match expected hashes, and no dev16 runtime log exists.
- Root cause correction: dev15 linked the complete original WWAudio/provider
  source graph but still constructed lite audio, omitted `Initialize()`, and
  never serviced it per frame. Dev16 first installs the rooted retail/MIX
  chain, creates the original basename-stripping audio adapter, then constructs
  and initializes non-lite original WWAudio before engine/world setup. It
  admits the session only with a sound scene and Vita-backed 2D/3D drivers,
  updates once after active render or during the suspended branch, and destroys
  audio before renderer/factory teardown.
- Ownership boundary: original WWAudio continues to own sounds, scene/listener
  state, callbacks, playback and events; only decode/mixing and SceAudio output
  remain platform-owned. Original ActiveConversation/TimeManager still owns
  remark progression, so Logan causality is not claimed.
- TT audit: the pinned official 4.8.4 r9000 archive/diff audit passes 5/5. It
  corroborates the constructor/frame-update interface but contains no audio,
  main-loop, or conversation implementation to import; no TT source or binary
  is included.
- Fresh retail evidence: D:-retail M00/M01/City two-cycle routes, ASan,
  LeakSanitizer, targeted UBSan, and the canonical 42-test selection pass;
  post-build full tool discovery passes 90/90. Host log SHA-256 is
  `d5503bf47ea37f184b268e18a3ec89101177fbbf8705538240ba033cabeda3fd`.
  Provider codec/mixer code has focused sanitizer coverage; the full host M00
  harness does not claim audible execution.
- Canonical evidence: deterministic 113-patch staging, all 482 ARM/package
  actions, identity 15/15, required symbols, compressed-package, manifest,
  diagnostics, and retail-exclusion checks pass. Source counts are 447
  original and 26 native boundary TUs.
- Exact hashes: ELF
  `684f15da87bb8e2d3fcdc45d7646132cb8f0ac65ec2612c0010d0365d10b8dea`;
  SELF `4dd1f7fd4a10ee26605986c58c1aad9e63986fbbf5c91e48326c9d4a0c81169f`;
  VPK `fa7903ba94442c7f18b554dd986d868bd90fe4dedfbcbcfc732b9f506e741a63`;
  diagnostics `9d7de514cb7a597ad59c037ef921770994102cd6aae57b06cc15580f6c49fabd`.
  The VPK contains only `eboot.bin` and `sce_sys/param.sfo`.
- Automation: the route runner admits exact dev16 SELF or exact installed dev7
  fallback only, retains the 4,537-sample route plus live START abort, and
  rolls back every failed deployed session.
- Blocker: physical observation must still accept audio, original sky/material
  appearance, Havoc arm/weapon geometry, Logan progression, and clean exit.

## 2026-08-24 — dev15 original WWAudio/Vita provider linkage superseded

`[████████░░] 8/10 current evidence gates complete`

- Historical state: no dev15 device write occurred. Post-build review found its
  Vita audio lifecycle inactive; dev16 above supersedes it.
- Original ownership: 15 additional EA/Westwood WWAudio translation units now
  own definitions, buffers, playlists, scene objects, callbacks, 2D/3D sound,
  priorities, looping, and timing above a narrow Miles-compatible Vita device
  boundary. The source report records all 20 WWAudio TUs selected.
- Native boundary: bounded RIFF PCM8/16, Microsoft IMA ADPCM, and Microsoft
  ADPCM decode; 48 kHz stereo rate conversion/mixing; pan, volume, loop, rate,
  encoded-byte seek/timing, and linear 3D distance attenuation; a blocking
  `sceAudioOutOutput` worker; original file callbacks for streams.
- TT integration: the official TT 4.8.4 revision-9000 reference remains pinned
  and audited out of tree. Its callback/schema/timing contracts informed the
  compatibility audit, but no TT source, binary, or Windows Miles runtime was
  imported. Five portable semantics are retained or equivalent.
- Focused evidence: PCM8/16, mono/stereo IMA, mono/stereo Microsoft ADPCM,
  bounded/truncated parsing, encoded-byte 3D seek, mixer, pan, and distance
  tests pass; ASan/UBSan and Vita ARM `-Werror` pass.
- Canonical evidence: deterministic 113-patch staging, 41 build-time contracts,
  482 ARM/packaging actions, identity 15/15, required audio symbols,
  ELF/SELF/VPK, compressed-package, manifest, diagnostics, and the post-restage
  89/89 suite pass. Unique source counts are 447 original plus 26 native TUs.
- Exact hashes: ELF
  `db96d327219e77d4df99d0a2942a635eda1872b311aa0c6dceb2b2a42d2eb0c9`;
  SELF `c4d5aaa1c04d93329617a086a7f57a423ff50ad40ee510f92a37ae9f8f9bfc1f`;
  VPK `e2036901c8edceaaee73a0bfb6d94f620476c794ab8dc94207feeb00b8ca17d3`;
  diagnostics `1cf8c7f118bb151c3308edfc11886c264bf1e95e1f303ea8399927cbb1906a6a`.
  The VPK contains only eboot and SFO.
- Validation boundary: the local retail link remains unavailable, so only the
  unchanged full retail M00 sanitizer route reused the matching retained log
  SHA-256 `97fc49202c76a04710964cf3939dd128329df88acc6b3005241632b69df5ec1e`.
  Changed audio code was tested freshly; no fresh retail sanitizer claim is
  made.
- Resource boundary: whole-track streaming is limited to 64 MiB but is not yet
  incremental or physically memory-measured; that remains v3.6 work.
- Historical automation: dev15 was formerly admitted with exact dev7 fallback,
  but is no longer in the current runner because it was never deployed and its
  activation gap is corrected by dev16.

## 2026-08-24 — dev14 host/ARM/package candidate superseded

`[████████░░] 8/10 current evidence gates complete`

- Historical state: dev14 was not physically replayed; the retained route and
  accepted dev7 fallback remained on the Vita while later candidates advanced.
- Physical dev13: exact SELF ran 4,507 frames and cleanly exited. The committed
  4,537-sample route SHA-256 is
  `39d915e02611079b29fb43cb2ea11ede583b063745e9675efe15010c606b7cf8`.
  Skin deformation recorded 37,606 submissions / 7,207,630 vertices / zero
  deformation or backend failures. The user nevertheless observed wrong NPC
  materials, no audio, black sky, and a post-ladder Logan interaction that did
  not progress; indexed draws/state applications remained zero.
- Rollback: exact dev7 SELF
  `7367b04a3fd19121e5360a0bfc8dd088d377c1063f060811a282056bbefeefd5`
  is installed and stopped. Retail M00 remains SHA-256
  `84f14f6267dd8a88563b3d31540bf857df0b8e111144944cb582edd246f2d438`.
- Source diagnosis: Vita passed rendering unavailable to original BackgroundMgr,
  preventing Sky/Dazzle construction; the mesh bridge also invented RGB from
  normals instead of using original DCG/VertexMaterial ownership.
- Dev14 correction: original background construction is enabled, unavailable
  DazzleLayer rendering is a bounded no-op, original material color/opacity is
  restored, and read-only conversation identity/state/remark timing is logged.
  No conversation is stopped or advanced and no weapon is granted by the port.
- Timing correction: `run_a35_vita_route_session.sh` now emits the play notice
  before launch; the later message is explicitly telemetry-ready.
- TT integration: official 4.8.4 revision 9000 source/diff are checksum-pinned
  and audited out of tree. Three portable semantics are already/equivalently
  in EA source; unavailable/PC-specific fixes are tracked without guessed code.
- Build evidence: deterministic 111-patch staging, 87/87 full contracts, the
  affected 504-action host target, all 465 ARM actions, ELF/SELF/VPK identity,
  compressed-package, manifest, symbol, and retail-exclusion gates pass. VPK
  SHA-256 is
  `6528991ca58877cb159a5c57b396c84e0a29c55ffa74487e5bb22f9af3e7e0e4`;
  SELF SHA-256 is
  `eda78f4f3dd57a064cb915af9cab677e3e64fc340c16ad09f0c74e6839ca6860`.
  The VPK contains only eboot and SFO; no Vita filesystem was accessed.
- Validation boundary: the local retail link was unavailable, so the package
  explicitly reused dev13's matching complete runtime/sanitizer log while
  freshly rebuilding the affected host and ARM targets. This is not a fresh
  retail sanitizer execution.
- Historical replay tooling: dev14 admitted only exact dev14 or exact dev7,
  kept the prelaunch play notice, and retained the live START abort plus
  unchanged-retail gate. The current runner is superseded by dev16 above.
- Historical blocker: dev14 had no native WWAudio output. Dev15 added provider
  source/link evidence; dev16 activates the original lifecycle. Physical
  visual, audio, and progression acceptance remains pending. The next replay
  must identify the exact original Logan conversation state; do not force
  completion.

## 2026-08-16 — v3.5 active

`[█████████░] 9/10 current evidence gates complete`

- Now: A3.5-dev2 physical Vita acceptance.
- Last focused step: A3.5-dev3 observer-loader chunk-open breadcrumb routing: deterministic WWLib `Open_Chunk` null-parent/required-root/short-read breadcrumbs and bounded contract coverage.
- Completed: A3.2 artifact identities verified; button state contract 10/10;
  axis/camera contract 22/22; weapon-style table deterministic repair; shader
  state contract 4/4; renderer lifecycle contract 11/11; bounded PSP2 note
  inventory; rate-limited deferred audio diagnostics.
- Completed: host observer-loader contract now directly exercises
  `PersistentGameObjObserverManager::Load` plus `ChunkLoadClass::Open_Chunk` null-file,
  truncated-root, parent-exhaustion, and repeated-open balance paths with `46` checks.
- Evidence: focused host tests pass and the changed ARM sources link locally.
- Retained host/sanitizer closure: PASS. The first canonical package attempt
  found and corrected a stale 14-versus-15 capture-test fingerprint; fresh ARM/VPK/hash/ZIP is next.
- ARM/VPK/hash/ZIP: PASS. Candidate VPK SHA-256 is
  `26445efb9ece7f64a86b38e6b49767233a7c3321f19c90e96ead6ef7c6073244`;
  it contains only `eboot.bin` and `sce_sys/param.sfo`.
- Remaining gate: authoritative physical Vita controls/visuals/lifecycle
  evidence.
- Blocker: user-performed physical test required; no automatic deployment was attempted.

The current package is `RenegadeVita-A3.5-dev2.vpk` SHA-256
`8ac77116c19d9eaf5093634ad9b5ff888ce9d42dcd42f34727ea52b9603a8b53` with
matching `A3.5-dev2-BUILD-DIAGNOSTICS-20260816-124825.zip`. Its packaging
reused the completed canonical host gate after only provenance/build-script
changes, then deterministically restaged and rebuilt the ARM candidate. ELF,
VPK and every SHA-manifest entry verified PASS. Physical evidence remains the
only open A3.5 gate.

Focused diagnostics, provenance, performance, asset/cache auditing, warning
trend, parser-fixture, and network-inventory work remains subject to narrow
file ownership and deterministic validation. The post-run diagnostic tool
recognizes this project's `*-SHA256SUMS.txt` manifests; its frozen VPK/ELF
manifest checks and two-run output comparison pass. A missing runtime log is
reported explicitly as `unknown`.

## 2026-08-16 — v3.6 host infrastructure

`[██░░░░░░░░] 2/10 current evidence gates complete`

- Added `tools/renegade_asset_manifest.py`: deterministic, read-only,
  content-hash inventory with required-archive validation and case-conflict
  detection. It does not extract, convert, or package retail assets.
- Unit tests: PASS (3 tests). Real local retail `Data` inventory: 51 files,
  required files present, no case conflicts, `always3.dat` present, digest
  `a3cc696b1d938c2780f1514875234a2ea9a9aac7b57bd5ac6f0d1599f01f4264`.
- This is host-only evidence; Vita cache/residency/memory/load behavior and
  second-scene validation remain open.

- Resource-boundary telemetry now accounts fixed-size `Read`/`Write` calls and
  bytes (13/13 focused host contract; ARM link PASS). No paths or file content
  are recorded, and original MIX routing remains unchanged.

The original-engine M01 archive preflight now passes: `MixFileFactoryClass`
enumerated 231 entries and found LDD/LSD/DEP content. It is integrated into the
canonical host runner but is not yet a full M01 PhysicsScene load.

M01 now has a separate original `CombatManager::Load_Level_Threaded` host proof:
two lifecycle cycles and 120 render/update frames each pass with zero rejected
or unsupported submissions. This remains host-only.

Cache-key v1 tests pass: source digest, cache/tool schema, and canonical
conversion options deterministically select a cache identity; invalid source
manifests are refused. No converted retail data is generated.

The expanded canonical host gate now passes M01 preflight and two original
Combat load/render/teardown cycles in addition to the retained M00 sanitizer
cycles. Evidence remains host-only.

Capture telemetry schema v2 is host- and ARM-link-validated. It records a
bounded periodic low-water free-memory sample for Vita system/VitaGL pools;
the capture self-test passes 17/17 and the capture comparison tests pass 2/2
with backward-compatible schema-v1 input. No device memory conclusion is made
without a returned physical capture bundle.

`C&C_City.mix` now passes a host-only original Combat load/render/teardown
smoke twice (120 frames each, first frame 43 meshes / 4,115 vertices / 2,963
triangles, zero rejected/unsupported). It is explicitly not a multiplayer
gameplay or network claim.

The host-only v1 archive-index precursor now enumerates through original
`MixFileFactoryClass` rather than a replacement parser. M01's 231-entry index
is byte-identical across two writes; City indexes 83 names. No retail content
is extracted, converted, or packaged.

The frozen A3.2 frame-2400 performance record has been re-extracted directly:
39.418 average FPS, p50/p95 21.874/24.446 ms, simulation/render 6.427/18.938
ms, and zero indexed submissions. It is now a hypothesis baseline only;
no optimization has been adopted without corrected-candidate A/B evidence.

Vita3K inspection is now recorded: the configured data root contains a
historical A3.1 `RNEGA3101` app only, with no configured emulator executable or
session logs. No emulator state changed; the documented loop remains a future
rapid-regression aid and never physical acceptance evidence.

The asset manifest now has explicit M01 and City profiles. Unit contracts pass
9/9 across capture/manifest/cache-key tools, and both real profiles are valid
against the same local 51-file content digest. The canonical host runner
regenerates them without extracting retail content.

The host cache-format precursor now writes versioned M01 index metadata and
verifies it against manifest/options identity and artifact hashes. The focused
contract suite passes 14/14; unsafe, stale, missing, and corrupt cache states
are explicit. Native device consumption is still unimplemented.

Final canonical revalidation now passes after correcting the runner to invoke
cache tools via `python3` rather than relying on their executable bits. The
retained M00 normal/ASan/LeakSanitizer/targeted-UBSan cycles, M01 two-cycle
original Combat route, and City two-cycle original Combat smoke all completed;
the complete host log is
`<managed-log-root>/a30-20260816-114055-host-runtime.log`.
The real M01 cache sidecar verifies `valid` for key
`55d93acb1240e2b7ddb4416660d0a3b0e7330eb7499eed10099fcd177c762538` and the
two generated index writes share SHA-256
`7a277d47fd50388ccec9c7841d3127cb452903b502f67b8dfa2df82605531b34`.

`[█████████░] 9/10 current evidence gates complete`

- Now: persist host v3.6 evidence and prepare the next native cache-consumer
  boundary without bypassing original MIX loading.
- Next: optional device cache validation, resource/memory/storage capture, and
  the pending A3.5-dev1 physical correctness test.
- Blocker: no engineering blocker; all device conclusions remain untested.

The next native v3.6 boundary is now implemented and host/ARM-closed. The
startup-only `Renegade_Inspect_Mix_Index_Cache` probe is constrained to the
existing `cache/` namespace and validates a bounded v1 M01 filename-index
structure. Its 9/9 contract covers absent, valid, malformed, retail-path, and
traversal cases. Invalid or absent indexes only produce a diagnostic state;
the original retail `MixFileFactoryClass` path remains authoritative.

The canonical gate including this contract passed at
`<managed-log-root>/a30-20260816-115428-host-runtime.log`:
M00 normal/ASan/LeakSanitizer/targeted-UBSan, M01, and City cycles all pass.
The current production executable ARM-links and exports the cache-health
symbols. No VPK was repackaged and no physical cache behavior is claimed.

## 2026-08-16 — v3.6 resource telemetry and lifecycle correction

`[█████████░] 9/10 current evidence gates complete`

- Completed: rooted original-file-factory telemetry contract 12/12; counters
  record Get/Return, read/write resolution, prepared-resolution hits, and
  open/availability/create/delete attempts/failures without names, payloads,
  allocations, or a replacement loader. The Vita runtime emits one teardown
  summary; original `MixFileFactoryClass` ownership is unchanged.
- Corrected: the next canonical host run exposed an 80,256-byte
  `PathSolveClass` retention after the direct harness omitted the original
  `PathMgrClass` process lifecycle. Both host and Vita paths now initialize it
  after `WWMath` and shut it down after `WW3DAssetManager`, precisely matching
  original Commando application order.
- Evidence: focused two-cycle M00 ASan/LeakSanitizer rerun is PASS at
  `build/host-a31-asan/a36-pathmgr-lsan.log` with no sanitizer finding; the
  ARM EABI5 closure links and exports `PathMgrClass::{Initialize,Shutdown}`
  and `Renegade_File_Factory_{Reset,Get}_Statistics`.
- Next: rerun the full canonical host gate once, then obtain physical A3.5
  evidence before any candidate promotion. The in-tree rebuilt VPK is not a
  candidate: it lacks a matching diagnostics package and physical validation.

Canonical revalidation is now PASS at
`<managed-log-root>/a30-20260816-122251-host-runtime.log`:
the retained M00 normal/ASan/LeakSanitizer/targeted-UBSan cycles and the M01
and City two-cycle original Combat paths all completed. The focused PathMgr
LSan proof remains at `build/host-a31-asan/a36-pathmgr-lsan.log`.

## 2026-08-16 — A3.5-dev3 hardware candidate

`[████████░░] 8/10 current candidate evidence gates complete`

- Completed: canonical host execution/sanitizer validation, ARM EABI5 link,
  VPK packaging, compressed-VPK validation, and generated-artifact hash
  verification for A3.5-dev3.
- Evidence: build log
  `<managed-log-root>/a35-dev3-20260816-135706-build.log`
  exited 0; diagnostics bundle
  `A3.5-dev3-BUILD-DIAGNOSTICS-20260816-135706.zip` is present; VPK SHA-256 is
  `286eaf0bd0bef9bd62802228df0e947c1d0310085f750320deed7bd49d837ded`.
- Next: manual physical Vita validation of controls, perspective, muzzle alpha,
  release behavior, pause/resume, and clean LiveArea exit. No physical result
  is claimed.

## 2026-08-16 — A3.5-dev3 physical-crash correction

`[████░░░░░░] 40% — exact dev3 crash reconstruction`

- Verified: the returned dump and dev3 ELF/map/symbol/VPK identities match the
  supplied SHA-256 values. VitaSDK ARM Thumb disassembly proves PC
  `0x810EAFBE` is the `bl ChunkLoadClass::Open_Chunk()` instruction in
  `PersistentGameObjObserverManager::Load`, not the historical HumanState
  crash.
- Corrected: the Vita controller boundary no longer reverses left Y and no
  longer defaults camera invert-Y on. The revised 22-check input contract
  passes on host.
- Corrected: future candidate packaging writes an explicit no-matching-dump
  status instead of copying the old A3.2 symbolication report.
- Pending: establish why the observer loader reaches an invalid FileClass or
  chunk state; no new VPK is promoted while that root cause is unresolved.
- Added: combat observer loader diagnostics patch (`combat-a35-observer-load-diagnostics.patch`)
  applied via staging (`tools/stage_sources.sh`), plus new deterministic host contract
  target `a35_persistent_observer_loader_contract_selftest` in
  `tools/host_a30_definitions/CMakeLists.txt`.
- Added: `port/validation/persistent_observer_loader_contract.cpp` directly covers
  `PersistentGameObjObserverManager::Load` with deterministic fixtures and a narrow
  registered factory hook: required-root open/ID failures, truncated headers, known
  vs. unknown children, repeated invocation, and chunk depth/close balance.
- Validation: `a35_persistent_observer_loader_contract_selftest` and `a36_file_factory_telemetry_contract_selftest`
  both pass (including ASan and UBSan build routes) with exit status `0`.
- Still pending: physical Vita breadcrumb evidence for the `0x810EAFBE` session remains
  unverified; this step intentionally validates only deterministic host fixtures.

## 2026-08-16 — A3.5-dev4 candidate identity correction

`[██░░░░░░░░] 20% — candidate integrity gate, no physical acceptance`

- Invalidated: `A3.5-dev4` physical evidence is not a valid candidate result.
  Its VPK/report filename was dev4, but the returned ELF retained dev1/A3.1
  runtime labels and the dev1 runtime-log path. The return does not prove the
  observer, axis, player, NPC, weapon, or camera paths ran.
- Returned static capture: framebuffer readback is valid, but the capture state
  records static-world rather than interactive-player conditions. The empty
  orderly-exit bundle is a failed evidence result, not a clean exit claim.
- In progress: generated-at-configure build identity, final ELF/SELF/VPK
  lineage verification, unified runtime log identity, phase-labelled capture
  metadata, post-write artifact checks, and a fixed-width overlay formatter.
- Gate: no successor VPK is called hardware-ready until a fresh ARM build and
  retained diagnostics prove candidate identity, nonempty evidence artifacts,
  and the candidate-specific runtime-log path.
- Added: the live ARM interactive path now emits a first
  `interactive-player-owned` capture only after original Combat reports both
  its player object and camera. Static-world, simulated-host-interactive, and
  device-interactive evidence remain explicitly distinct.
- Built: fresh canonical `A3.5-dev5` host/ARM/VPK candidate. The complete host
  gate and focused contracts pass; the ARM target selected 424 original plus
  21 port translation units and completed 456 build actions.
- Verified: final VPK SHA-256
  `e69919b557b8b2a807ac6437310d4c62072635ce1a493e63eee604a0c935287c`;
  final ELF SHA-256
  `bf1a250554f0666fbc3814f0a47b784cd399a410bd823bf12885c8a92ebd2e05`.
  All 15 identity/lineage checks pass and the VPK contains only `eboot.bin`
  and `sce_sys/param.sfo`.
- Physical gate: pending. The tester must stop immediately unless startup says
  `A3.5-dev5` and `a35-dev5-runtime.log` is created. No visual defect or
  milestone acceptance is claimed from host/ARM evidence.

## 2026-08-24 — A3.5-dev5 physical M00 loader isolation and recovery

`[████░░░░░░] 4/10 current evidence gates complete`

- Initial physical evidence in this work unit entered the original Combat/M00
  static-object loader but did not reach a first rendered frame. Those durable
  breadcrumbs repeatedly stopped
  inside object 116 after nested on-demand W3D loading; the last completed
  breadcrumb is the return from loading `E_FLAME01.w3d`, before the outer
  `Create_Render_Obj` returns. This is a loader blocker, not visual acceptance.
- The Vita-only original `LoadLevelThreadClass::Thread_Function` now runs
  synchronously on the vitaGL-owning main thread. Exact-source comparisons with
  vitaGL, OpenLara, vitaXash3D, and vitaRTCW support that ownership boundary.
  A physical rerun reached the same object-116 endpoint, so the correction is
  retained but is not claimed as the root fix.
- Sampled memory at objects 0, 25, 50, 75, 100, and 108-116 remained byte-for-byte
  flat across all exposed system and vitaGL free pools. A speculative vitaGL
  pool-size change is rejected as the immediate fix; internal heap pressure is
  still a separate unmeasured possibility.
- The remote-test wake blocker is resolved by the device-specific GPL
  `renegade_nolockscreen` SceShell user plugin. It fingerprinted the exact retail
  3.65 SceShell module, applied and post-validated both bounded injections, and
  the user physically confirmed that the main screen appears with the wipe
  bypassed. The active config/plugin and exact pre-change config backup are
  hash-retained; temporary probe files were removed. This closes an automation
  prerequisite and does not increment a game gate.
- Diagnostic plan at that point: trace bounded recursive
  `WW3DAssetManager::Create_Render_Obj` entry,
  prototype lookup, and `PrototypeClass::Create` return depth around object 116,
  then run one time-bounded physical diagnostic with Renegade killed afterward.

### Follow-up physical result

`[█████░░░░░] 5/10 current evidence gates complete`

- The fresh recursive trace proves object 116 is not hung. `MGWEP_AG_3`
  completes its nested depth-2 prototype work, returns through render and
  physics persistence, and the loader continues through all 495 static objects.
  `Load_Game` and the original loader-thread function return, M00 completes in
  the current direct route, and the original player/session/camera path reaches
  its first Combat frame.
- Canonical A3.5-dev5 ARM build `20260824-004956` passed all 456 actions, ELF,
  SELF, VPK, identity, inventory, and diagnostic-manifest checks. The physically
  installed SELF SHA-256 is
  `ec08e891087243a6a44da8db29ef80bf9c485d31a6ef1b0f27423ea9626b59b1`;
  the prior installed SELF was pulled and retained before replacement.
- Retail recopy was not required. On-device `M00_Tutorial.mix` is 5,802,816
  bytes with SHA-256
  `84f14f6267dd8a88563b3d31540bf857df0b8e111144944cb582edd246f2d438`;
  `always.dat` remains present at 578,539,390 bytes. The current run loads and
  renders from that unchanged retail tree.
- The first automatic interactive readback sampled a stale post-swap vitaGL
  splash buffer. A readiness-gated manual Select capture at frame 355, after
  three untouched interactive seconds, returned a clear textured original M00
  yard with the player-owned camera and first-person weapon. Raw BMP SHA-256 is
  `13f4f1173f452d039c1d14f3cc15e89bb1a9a8ef6c38ef981ec5b57f85f6607e`.
- A separate readiness-gated run exercised forward movement, camera look,
  strafe, jump-button, action-button, a second forward/look segment, and a late
  manual capture. Device telemetry records the stick states and the player moved
  from `(-58.328,-41.527,0.588)` to `(-46.290,-43.339,0.607)`. Jump and action
  input delivery are observed; their world effects are not yet accepted.
- Both physical runs reported zero rejected submissions and zero renderer
  backend errors. The spawn control ran 355 frames and the interaction run
  reached frame 1,321. Each run ended with release-all, app kill, sleep restore,
  and verified `running=false`.
- Evidence is retained under
  `build/device-evidence/a35-dev5-recursive-create-20260824/`. Remaining v3.5
  gates are collision/grounding and action-effect observation, pause/clean exit,
  and restart/repeat stability; bounded repeated-session soak remains v3.9,
  while HUD/audio and mission progression remain later capability gates.

### Clean exit and restart follow-up

`[██████░░░░] 6/10 current evidence gates complete`

- A readiness-gated clean-exit run reached 417 frames, passed the 120/240/360
  checkpoints, then responded to START by completing original Combat level
  unload, session teardown, GameInit SP shutdown, network shutdown, logical
  renderer shutdown, and application audio teardown. It self-exited within one
  second with `exit=1 render_error=0 teardown=1` and lifecycle `END status=clean`.
- A second launch proved restart/repeat: it again reached interactive M00,
  recorded forward/look/Cross/Square at frame checkpoints, completed 894 frames,
  and self-exited through the same clean teardown within one second. Neither run
  required its safety-kill fallback; both ended `running=false`, no-sleep off,
  and all synthetic input released.
- Clean-session SHA-256 values are
  `7e688b37f3103f7009fee1f2abd07418adc38dcb17b1148647881fa2878c74b4`
  and `3145a860d94cc92d370e567d799ec7cf9c5f3eb404dfce5cb7f02f3dd4230b48`.
  Remaining v3.5 physical gates are pause behavior, collision/grounding,
  and observable action effects. Repeated-session soak remains a v3.9 gate.

### Original Combat pause candidate work unit

`[██████░░░░] 6/10 current evidence gates complete`

- Source trace identified the authentic owner: desktop
  `CombatGameModeClass::Combat_Keyboard` consumes
  `INPUT_FUNCTION_MENU_TOGGLE`, then suspends the original Combat game mode;
  the base `GameModeClass` already owns the state transition.
- The minimal Vita seam maps the currently unused Triangle button to the
  original menu-toggle key, keeps START as clean exit, and makes the direct M00
  loop obey `GameModeClass::Suspend/Resume`. During suspension it continues
  input, time, and local-network servicing while preserving the last original
  Combat frame because the desktop menu presenter is not yet linked.
- Focused dev6 validation passes: the exact changed boundary/direct-input
  sources compile normally and with ASan, the runtime-log/identity tests pass
  4/4, and the static pause contract passes 6/6. A fresh full host retail run
  was unavailable without copying retail data, so the canonical package
  honestly reuses the byte-identical completed dev5 host log SHA-256
  `9f9f544a0463e6b786a003957a3c117284d5c3498339efcd92af0a495964db53`.
- Canonical A3.5-dev6 build `20260824-013626` completed all 456 ARM actions and
  passed ELF/SELF/VPK inspection, the 15-check candidate-identity gate, VPK
  integrity, retail exclusion, and the diagnostics manifest. ELF SHA-256 is
  `2b820d533815a135db020804b287affe6521ecc68ff8dc0602e9c7e74c4473a2`,
  SELF SHA-256 is
  `293768e9d79769b9872e1ad9d472c66305310032c74727d6e08a1a444ad52360`,
  VPK SHA-256 is
  `929bdbcfbf10292f250c799faf74b254384482ddc1e8cb43d6d2b21e7f573bae`,
  and diagnostics ZIP SHA-256 is
  `6c597157e5462297dd1174830059710be348d9f78c17c6035fa227d2e03d4b43`.
  The VPK contains only `eboot.bin` and `sce_sys/param.sfo`, and its eboot is
  byte-identical to the verified SELF.
- Matching physical pause/resume evidence is pending; no dev5 physical result
  is transferred to the new executable. Nothing was deployed during build.
- Device preflight failed closed before staging: the paired physical Vita at
  its last address `.202` is offline. The only VitaCompanion endpoint currently
  visible at `.186` authenticates as the separate PS TV (`model=pstv`) and has
  no Renegade data tree, so it was not modified. The dev6 eboot swap and run
  wait for the target Vita to reconnect.

### Original collision and action-effects telemetry work unit

`[██████░░░░] 6/10 current evidence gates complete`

- The physical wait remains 30 seconds after the VitaGL logo, with a bounded
  45-second readiness timeout. The paired PS Vita was retried and remains
  disconnected; no fallback device or retail-data mutation was attempted.
- The existing capture schema had fields for player identity, transform,
  velocity, health, physics registration, and ground contact, but the
  interactive route populated only position and type. The boundary now samples
  those fields from the original `SoldierGameObj` and `HumanPhysClass` owners.
- A bounded first-frame/120-frame flight-recorder record also samples the
  original weapon definition, clip/total rounds, total rounds fired, trigger
  and fire state, plus original `ActionClass` count/active/busy state. This is
  observation-only and does not modify game, physics, weapon, or mission state.
- The capture comparator now accepts the already-current schema version 3 and
  reports player position/orientation/velocity/health/physics/grounding as a
  separate gameplay category. Its three unit tests pass; normal and ASan
  capture-writer self-tests pass; both changed translation units pass the ARM
  Vita ABI syntax compile; the first-mission skill validates; `git diff --check`
  passes.
- A3.5-dev6 remains frozen byte-for-byte for the pending pause run. The new
  telemetry source will be packaged as a separate candidate so physical
  evidence cannot be transferred between executables.
- Canonical A3.5-dev7 build `20260824-020540` completed all 456 ARM actions and
  passed the 15/15 identity gate, VPK inventory, retail exclusion, and
  diagnostic manifest. ELF/SELF/VPK SHA-256 are
  `6063c5eb2c5136ee4376fe6dc0b3944c54ce728ff7b59af76b90ffdaf6e62e21`,
  `7367b04a3fd19121e5360a0bfc8dd088d377c1063f060811a282056bbefeefd5`,
  and `234139c2411fed7be8f2003a15ba015bc2270608ef8e3ec5406308e5c3c1443e`;
  diagnostics ZIP SHA-256 is
  `45d77a0378b0f06050263fda4ec602e2906e8b691cc9db3677a33c5d1b23bce2`.
  The VPK contains only eboot and SFO. No Vita deployment occurred.
- Input ownership was rechecked before automation: Cross -> `DIK_SPACE` ->
  original jump; Square -> `DIK_R` -> original action; Triangle -> original
  menu toggle; START -> clean exit. The stale build handoff text saying
  Square was reload is corrected for future packages without mutating the
  already retained dev6/dev7 artifacts.
- Added a candidate-scoped physical runner and independent log/state validator.
  The runner rejects non-PS-Vita identity, unknown installed executable hashes,
  stale readiness lines, and dev7 without an exact dev6 PASS receipt. It backs
  up the installed executable before replacement, restores it automatically on
  launch/readiness failure, uses a bounded 45-second readiness timeout, walks,
  looks, jumps, fires, attempts Square action at multiple positions, captures,
  exits with START, and unconditionally releases synthetic input. Focused pause
  and effects validator fixtures pass 2/2; the effects result explicitly does
  not infer visual correctness or environmental action success.
- The first live dev6-runner invocation at `20260824-072911` failed at the
  initial read-only status request with `DISCONNECTED` / no route to the exact
  PS Vita `.202`. It did not reach identity, application state, hash, backup,
  staging, replacement, launch, or retail data. The separate PS TV was not
  queried or modified. Offline receipt:
  `build/device-evidence/a3.5-dev6-pause-20260824-072911/status.json`.

### Original Mission00 native static provider work unit

`[██████░░░░] 6/10 current evidence gates complete`

- Replaced only the unavailable Windows script-DLL platform boundary with a
  native static provider. Original Combat `ScriptManager` remains the owner and
  now receives official `ScriptCommands`, `ScriptFactory`, `ScriptRegistrar`,
  `ScriptImp`, and `Mission00` implementations; no replacement mission system
  or asset format was introduced.
- Fixed the provider create-function binding to target the global official
  `Create_Script` implementation rather than recurse into `ScriptManager`.
  Focused provider tests pass 4/4, the current core-tool suite passes 52/52,
  diagnostics pass 29/29, zero-fuzz restaging is clean, and upstream is
  pristine.
- Canonical A3.5-dev8 build `20260824-031918` selected 430 unique original plus
  22 port translation units, completed all 463 ARM actions, passed 15/15
  identity checks, and contains the required create/registrar/M00 controller
  symbols. ELF/SELF/VPK SHA-256 are
  `3d4b1f56e82782d1958c9a82dd5f9f773ebd3f8046652caae4c8ecd01d9b4b21`,
  `7d944a8f0fe0425007cbb22b3ea039f8c173b64c4f8f6c4dce71a5670ee02c20`,
  and `86b00a0d4a07a2fde9bd1734934e9bb31bdae848a2d84da551545281ad8219ac`.
  The VPK contains only `eboot.bin` and SFO; no retail or device data changed.
- The candidate-scoped validator requires `provider_active=1`, registered and
  attached counts above zero, and capture `scripts_active=true`. The runner
  waits up to 45 seconds for the normal approximately 30-second readiness,
  then walks, looks, jumps, fires, attempts Square action, captures, exits with
  START, and releases every synthetic input.
- Physical evidence remains pending and the bar remains 6/10. The exact `.202`
  PS Vita is offline; dev8 may run only after exact dev6 pause and dev7 effects
  PASS receipts. No deployment was attempted.

### Direct Mission00 script-attachment closure candidate

`[███████░░░] 7/10 current evidence gates complete`

- Audited every literal original `Mission00.cpp` `Attach_Script` target. Fourteen
  are registered in Mission00 itself; the two missing provider dependencies are
  original `Test_Cinematic.cpp` and `Toolkit_Powerup.cpp`. Those two pinned
  EA/Westwood translation units are now linked unchanged beneath the existing
  Combat `ScriptManager`; the provider source contract proves all 16 literal
  attachment targets resolve and exactly 37 factories are compiled.
- GCC required one additional call-site-only bridge for the original MSVC
  function-pointer default in `Create_Explosion_At_Bone`. It supplies the
  omitted creator as `NULL`; the official source and ScriptCommands ABI layout
  remain unchanged. Focused ARM compile/link/package completed, then canonical
  A3.5-dev9 build `20260824-035114` completed all 465 actions.
- Dev9 selects 432 unique original plus 22 port translation units and passes
  15/15 identity, 54/54 core-tool, 29/29 diagnostics, SHA-256 manifest, archive,
  and independent candidate-provenance checks. ELF/SELF/VPK SHA-256 are
  `e5a7e0e379fba388945e02147feffa4bbbcec700e828bae7a41384b85285fa10`,
  `231fa510a9d39219df93aa2e4b442fe1cd0c9489c1f09f3596df63eea0bf0d88`,
  and `812baacb6bb482d8407fb0fc3ab33588af9a9f877cb5e4c305d790925529f8a5`.
  VPK inventory remains only `eboot.bin` and SFO; upstream is pristine.
- The offline physical gate now supports `dev9-m00-closure`. It retains the
  45-second readiness ceiling around the observed approximately 30-second load,
  performs the bounded requested walk/look/jump/fire/Square route only after
  original first-render readiness, and requires exactly 37 registered factories
  plus active attached scripts. Validator fixtures prove 37 passes and 36 fails.
- A fresh read-only `.202` status request at `20260824-090149` again returned
  `DISCONNECTED` / no route. No device identity, filesystem, app, or input
  operation followed; no deployment was attempted and physical acceptance is
  not claimed.

### Original mission-completion observer candidate

`[███████░░░] 7/10 current evidence gates complete`

- The authentic original path is `Commands->Mission_Complete(true)` into
  `CombatManager::Mission_Complete`. The direct Vita route previously had no
  `CombatMiscHandler`, so that terminal event had no lifecycle consumer.
- A3.5-dev10 installs a bounded Vita `CombatMiscHandler` immediately before
  original level pre-load, observes only original mission-complete and
  star-killed events after each original simulation frame, latches the first
  terminal result, and uninstalls before teardown. It does not call mission
  completion, mutate objectives, advance campaign state, or introduce a game
  loop.
- Canonical build `20260824-042339` passed 465 ARM actions, focused completion
  contracts, 15/15 identity, manifest and VPK checks, provenance, and retail
  exclusion. ELF/SELF/VPK SHA-256 are
  `01159d2cd4ed9dd9ac2999cb8a9d75085aada49e328c8ba587a5fddf17e76cb6`,
  `32eac8d6471d4a60689678dae854b1850682a700161a2e36c61301cfdff0d339`,
  and `7fb2d6f8df0ec1707303a2ce8a168e9dae86c799c91c01a802dee59e12e15090`.
- The new `dev10-completion-smoke` physical route requires an exact dev9 PASS
  receipt, waits up to 45 seconds around the corrected approximately 30-second
  VitaGL-to-playable load, then walks, looks, strafes, jumps, fires, attempts
  Square interaction, captures, and exits with START. Its validator requires
  exactly 37 factories, active scripts, `start_exit=1`, and no terminal mission
  event; the claim boundary explicitly excludes mission completion and visual
  correctness. All 60 tool unit tests and shell syntax pass.
- Read-only `.202` status at `20260824-093330` returned `DISCONNECTED` / no
  route. No deployment, filesystem, application, or input operation occurred;
  the evidence-gate count remains unchanged.

### Original M00 tutorial-control progress candidate

`[███████░░░] 7/10 current evidence gates complete`

- Static tracing confirmed that M00 intentionally disables player control
  during its opening tutorial conversation. The first original render frame is
  therefore a render-readiness marker, not proof that movement input is yet
  accepted by the original player owner.
- A3.5-dev11 adds a change-only, read-only flight-recorder sample of the
  original Star/control state, official ObjectiveManager IDs 1 through 6, and
  active ConversationMgr count after original simulation/render. It emits a
  dedicated automation handoff only when objective 1 is pending and the
  original player has control. It calls no objective, conversation, input, or
  mission mutator.
- Canonical build `20260824-043938` completed all 465 ARM actions and passed
  candidate identity 15/15, VPK/manifest integrity, linked-symbol inspection,
  provenance, retail exclusion, and the diagnostics bundle manifest. ELF/SELF/
  VPK SHA-256 are
  `706d94302bcde7df36a8506f1ead5928d766aa5e70371a5d4a62d284da65ff4f`,
  `ceb491c609c92657f63cf3cd978d4f7674f41d360cda86b657929210441681ad`,
  and `8cdbe4e289ffcf66e8ed5418255ccd8848484f485a4eb744d83c9638ee657c2e`.
  The VPK contains only `eboot.bin` and SFO; no retail data was copied or
  packaged.
- `dev11-progress-smoke` requires an exact dev9 PASS receipt, permits only the
  exact dev9 or dev10 installed predecessor hash, waits up to 45 seconds for
  first render and then up to 60 seconds for the original tutorial-control
  handoff, and only then performs the bounded walk/look/strafe/jump/fire/Square
  route. Its validator requires the same-session progress record and handoff,
  37 original factories, active scripts, a clean START-owned exit, and terminal
  completion/success/star `0/0/0`. Its claim boundary explicitly excludes
  mission completion, visual correctness, and environmental action success.
- The focused validator and completion contracts pass 11/11; full tool
  discovery passes 62/62 and shell syntax/diff hygiene pass. A fresh read-only
  `.202` request at `20260824-0949` again returned `DISCONNECTED` / no route.
  Nothing was deployed or written to the Vita, and the physical-evidence bar
  remains 7/10.

## 2026-08-24 — A3.5-dev6 physical original-Combat pause PASS

`[████████░░] 8/10 current evidence gates complete`

- The exact `.202` physical PS Vita returned online. Authenticated readback
  proved the installed dev5 SELF SHA-256 before replacement, retained a local
  hash-matched backup, and proved the installed dev6 SELF SHA-256
  `293768e9d79769b9872e1ad9d472c66305310032c74727d6e08a1a444ad52360`.
  Only `ux0:/app/RNEGA3101/eboot.bin` changed; the retail M00 archive remained
  byte-identical and no retail path was written.
- The physical dev6 session reached original first-render readiness, then
  original Combat suspended and resumed at frame 206 with identical player
  position `(-58.328,-41.527,0.588)` while 316 paused input frames were
  serviced. The bounded post-resume walk/look/strafe/jump/fire/Square route
  moved the player to `(-54.177,-19.666,0.810)` before the clean START exit.
- Completion recorded 1,334 frames, `render_error=0`, teardown complete,
  pause/resume `1/1`, clean lifecycle END, app stopped, all synthetic inputs
  released, and sleep restored. The independent validator PASS is
  `build/device-evidence/a3.5-dev6-pause-20260824-130016/gate-validation.json`;
  its runtime log, final state, and receipt SHA-256 values are respectively
  `a6087cb07ee259e46786ec0a3e78d2ef3ad1ade249e22ad9f2aa977bea0a7416`,
  `303ff04a57670b69974714f07518e8f452c0dc3a457fba99c4cf64fc3839733b`, and
  `3d173c3fd77be1fd9dfe14cb4d8d6d26899617c88e30d3311203e490840487af`.
- This is telemetry-backed original pause stability and post-resume movement,
  not a visual-correctness or environmental-action claim. Dev7 remains the
  next physical collision/action-effects gate and is admitted only by this
  exact PASS receipt.

## 2026-08-24 — A3.5-dev7 input-provider isolation and physical visual report

`[████████░░] 8/10 current evidence gates complete`

- Four bounded full-route runs of the exact dev7 SELF rendered and exited
  cleanly, proved original physics registration, grounding, movement, and the
  Square raw bit, but did not receive the external synthetic R-trigger bit in
  the same sessions. The final retained run is
  `build/device-evidence/a3.5-dev7-effects-20260824-132016/`; its runtime log,
  state, and receipt SHA-256 values are respectively
  `7d32500eb97a0084e28a5fd6ecd74a26d80b4397388800cad6727904f7955569`,
  `ffb0f46ac3c202675cfbb7189290ffb9e6fbb4c4f7fa413c500552d288dc1103`, and
  `88cf796f6408414a747e06f131d7193a7757907de48eb6b40eed2b0aea746abf`.
- A separate exact-dev7 isolated probe retained under
  `build/device-evidence/a3.5-dev7-input-probe-20260824-131124/` delivered raw
  `0x00000200` for R and advanced the original weapon fired count from 0 to 17.
  This proves the VitaSDK mapping, DirectInput button B binding, and original
  weapon path; it does not combine with another session to pass dev7. Further
  repeats of the nondeterministic external route are stopped.
- Physical user observation after the approximately 30-second load: Havoc's
  first-person forearm/hand is absent or misplaced while the wristband and
  pistol remain visible, and NPC bodies are invisible while rigid weapons,
  headgear, belts, and boots remain visible. This is recorded as a physical
  visual defect, not inferred from telemetry. The shared boundary under
  investigation is original skinned-mesh deformation at Vita submission;
  retail repopulation is not indicated by the attachment evidence.
- The next candidate will keep original Input/Combat ownership while adding a
  bounded, versioned raw-controller route recorder/replayer at the existing
  DirectInput platform boundary. It will also restore original deformed skin
  vertices and identity-world submission beneath WW3D. VDB remains the
  preferred external injector when its negotiated server capability permits;
  the native recording is intentionally provider-independent.

## 2026-08-24 — A3.5-dev12 skin and deterministic-route hardware candidate

`[████████░░] 8/10 current evidence gates complete`

- Source comparison found one shared platform-boundary defect matching both
  physical observations: the Vita mesh path submitted undeformed model-space
  vertices and the mesh world transform for `SKIN`, while the original DX8
  skin container obtains HTree-deformed positions/normals and submits them
  under identity world. A3.5-dev12 restores exactly those original semantics;
  rigid meshes and original scene/animation ownership are unchanged.
- Added bounded counters and first-use breadcrumbs for skinned submissions,
  deformed vertices, allocation/deformation failures, and identity-world use.
  This can prove the corrected path executed but cannot prove visual
  correctness without a returned physical capture and user observation.
- Added a version-1 controller route below the original DirectInput API: eight
  bytes per sample, maximum 18,000 samples, FNV-1a payload checksum, exact file
  length/header validation, temporary-file sync/rename commit, invalid-route
  rejection, and live physical START emergency abort during replay. Exact
  one-shot marker files select record or replay; conflicts fall back safely to
  passthrough and are logged. Original Input/Combat owns all bindings/actions.
- Focused route/skin/runner tests pass, complete tool discovery passes 74/74,
  renderer lifecycle remains 11/11, shell/Python syntax passes, affected host
  units compile, and upstream is pristine. VDB capability negotiation remains
  first choice; VitaCompanion is admitted only for hash-guarded writes when VDB
  advertises no write capability.
- Canonical build `20260824-083354` completed all 465 ARM actions and passed
  ELF/SELF/VPK identity, exact VPK inventory, retail exclusion, archive test,
  SHA-256 manifest, and diagnostics bundle validation. ELF/SELF/VPK SHA-256 are
  `cbf956dbd001ef13dd94da465ef756d69f882bcfb8b25d621045065f905dd1d0`,
  `805b853e737c884acc9f590a3c5793f9ba6f32f5ff80542454919bf1d2750b99`,
  and `86f08c02dab2829e9ef7e25c12983313c1eb3664d2d9a3aeebaf962ff037e284`.
  The VPK contains only `eboot.bin` and SFO. No device was accessed by the
  build.
- The one-shot physical runner is bound to the exact dev7 predecessor and
  dev12 candidate hashes. It backs up before replacement, verifies the retail
  M00 hash before/after, waits for original first-render and tutorial-control
  handoff, records the user's requested 30-second walk/interact route, returns
  log/route/capture, and then replays only the checksum-verified route. Physical
  record/replay and visual acceptance are pending; the evidence bar remains
  8/10.
- The first record attempt failed closed before launch because the current VDB
  debugger is read-only and VitaCompanion supports upload but the CLI's native
  `touch` requires VDB write capability. No marker or route was created. Retail
  M00 readback SHA-256 was
  `84f14f6267dd8a88563b3d31540bf857df0b8e111144944cb582edd246f2d438`.
  Receipts prove dev12 was staged and then exact dev7 SELF SHA-256
  `7367b04a3fd19121e5360a0bfc8dd088d377c1063f060811a282056bbefeefd5`
  was restored before exit. The runner now uploads a zero-byte marker through
  the negotiated, hash-verifying VitaCompanion file-write path; generic exact
  file removal remains available for failed-start cleanup.

## 2026-08-24 — A3.5-dev12 physical skin pass and indexed-sky diagnosis

`[████████░░] 8/10 current evidence gates complete`

- Physical dev12 observation confirms ordinary NPC body skins now render. The
  retained runtime reached frame 4,800 with 67,209 original skinned-mesh
  submissions, 13,343,536 HTree-deformed vertices, zero deformation failures,
  and zero renderer backend errors. This physically accepts the shared NPC
  deformation correction, but not the whole candidate.
- The same physical session reports Havoc's arm/pistol absent and the sky
  entirely black. Matching logs show dev12 has no selected weapon from frame 0
  onward, while dev7 had `Weapon_Pistol_Player` and exactly four additional
  meshes (250 vertices / 279 triangles). Original `MTU_Commando::Created`
  deliberately deselects the weapon and original Mission00 selects the pistol
  only after Logan's poke instruction. This is authentic tutorial state, not a
  skin regression; no platform-owned weapon grant is admitted.
- Source tracing found the independent sky defect at the existing DX8 boundary:
  original Haze, Starfield, CloudLayer, sun and moon use dynamic indexed draws,
  but the Vita draw bridge submitted their geometry without consuming the
  deferred original `ShaderClass` and stage-0 `TextureClass`. The narrow repair
  applies those original owners immediately before indexed submission and
  records indexed state-application telemetry. No custom sky or asset format is
  introduced.
- The route runner now recognizes the observed original `star/control=1/1`
  handoff instead of waiting for objective 1 to be pending. The six objectives
  are correctly hidden (`OBJECTIVE_STATUS_HIDDEN == 3`) at the opening state.
  Exact dev7 was restored after the failed visual candidate; no route or marker
  remains on the device.

## 2026-08-24 — A3.5-dev13 pre-build lifecycle closure

`[████████░░] 8/10 current evidence gates complete`

- The indexed sky-state correction passes its focused contract and the native
  renderer lifecycle remains 11/11. Physical sky correctness is still pending;
  host evidence cannot accept the visual gate.
- Clean staging of the original Scripts pool exposed and corrected the original
  mismatched `new[]`/`delete` parameter-array lifetime without changing script
  ownership or importing a replacement provider.
- Strict LeakSanitizer then identified a disabled-teardown lifecycle gap:
  original object destruction detached scripts into `PendingDestroyList`, but
  the disabled `Post_Think` path never drained that queue. `Destroy_All` now
  completes the original pending-script lifecycle after object deletion.
- Headless validation no longer allocates presentation-only powerup icons when
  the original HUD render resources were never initialized. This guard does not
  affect the Vita HUD path, where both original powerup renderers exist.
- The focused strict-ASan run completes two authentic M00 load, 120-frame
  render, and teardown cycles with zero AddressSanitizer/LeakSanitizer findings.
  Fresh canonical host ASan/LeakSanitizer, targeted UBSan, M00/M01/City routes,
  deterministic staging, and complete tool discovery 81/81 pass.
- Canonical build `20260824-093614` completed all 465 ARM actions and passed
  candidate identity, ELF/SELF/VPK inspection, retail exclusion, archive,
  SHA-256 manifest, and diagnostics validation. ELF/SELF/VPK SHA-256 are
  `d3b7d69e40f1968a9beda0b46312c0609d73522b8ce30799cecb169a352d8b1b`,
  `5c254b8a914a603baca2c9b343bb075df58c7d05ed05448db267f2d599a14555`,
  and `7f7e31b37afff79ea1ab662cd9afc5d0e366f9252be6dd236b2ac8fabdf5d63d`.
  The VPK contains only eboot and SFO; no device was accessed by the build.
- The physical runner is now bound to exact dev7/dev13 executable hashes and
  waits for original `star/control=1/1`. Physical record/replay, sky observation,
  and Havoc viewmodel observation after Mission00 grants the pistol remain the
  two uncompleted evidence gates.

## 2026-08-24 — A3.5-dev14 candidate and TT reuse closure

`[████████░░] 8/10 current evidence gates complete`

- Dev14 passed the canonical 465-action ARM build and exact ELF/SELF/VPK,
  manifest, symbols, diagnostics, VPK-inventory, and retail-exclusion gates.
  It restores original background creation, original material/DCG color and
  opacity, bounded conversation state diagnostics, and safe absent-dazzle
  handling. Physical visual and mission acceptance remain pending.
- The official TT 4.8.4 revision-9000 archive/diff remain out of tree and are
  MD5+SHA-256 pinned. The audit now proves five TT/EA equivalences, adding the
  audio callback contract and complete retail audible-definition schema to
  the prior chunk, line-segment, and timer checks. It machine-records TT's
  unqualified dependent-base calls and missing-return WWAudio header defect;
  no Windows/Miles audio boundary or TT runtime source is imported.
- Focused TT and route-runner validation passes 9/9. The unattended runner now
  restores exact dev7 after any failed deployed session, including failures
  after readiness. Read-only Vita admission verified app stopped, dev7
  installed, the retained route SHA-256 `39d915e02611079b29fb43cb2ea11ede583b063745e9675efe15010c606b7cf8`,
  and unchanged retail M00 SHA-256
  `84f14f6267dd8a88563b3d31540bf857df0b8e111144944cb582edd246f2d438`.
- No candidate was deployed because the current contract forbids automatic
  Vita filesystem mutation. The replay remains prepared; work continues on
  the native audio provider beneath original WWAudio ownership using dev13's
  physical `sound_scene=null` and deferred-sound evidence.
# Dev112 canonical completion

Build and artifact identity passed; see `DEV112_CANONICAL_RETURN.md`.
Now: title-scoped Vita3K install, then queued post-Sydney reload and EVA pause.
Release acceptance remains 0/10; build closure is not mission completion.
# Latest: checkpoint load defect corrected in source

Dev112 canonical passed, but saved-game loading faulted before gameplay.
Confirmed cause and ARM/staging evidence: `DEV112_CHECKPOINT_LOAD_FAILURE.md`.
Dev113 is the next corrected candidate. Pause, full M00 and ending remain open.
# Latest: dev113 stopped at reproduced ASan post-load fault

Original M00 world host checks passed; interactive ASan then found a null
HumanPhys during soldier post-load. Replay reproduced it. ARM packaging and
checkpoint runtime return are pending. Details: `DEV113_ACTIVE_BUILD.md`.
# Latest: causal host regression isolated

A/B and GDB prove that the new compatibility reader exposes an incorrect
buffered rewind, skipping required objects. The previous reader passes the
same ASan fixture. See `DEV113_BUFFERED_REWIND_CAUSE.md` for the proposed fix.
# Latest: reproduced host regression corrected

Buffered rewind fix passed zero-fuzz staging, ARM compilation, and both original
M00 ASan cycles. See `DEV113_BUFFERED_REWIND_FIX.md`. Full canonical retry and
Vita3K checkpoint restoration are next; release acceptance remains unchanged.
# Latest: dev113 tested; session stopped as requested

Canonical PASS. Fresh M00 gameplay and pause/resume observed; EVA controls/text
are missing. Checkpoint restoration ends in controlled player-identity failure.
Vita3K closed, inputs released, no build running. See `DEV113_OVERNIGHT_RETURN.md`.
## Dev114 canonical return and integrated EVA correction

This entry supersedes older current-candidate statements below.

Completed: checkpoint-enabled A3.5-dev114 canonical build and artifact identity
checks passed. After its process exited, the original EVA shell/seven child
resources and captionless-edit parser fix were integrated, with permanent
C++ contract coverage. Integrated host contract passed in
`build/eva-integrated-twmhL1/`. That source correction is not in Dev114.

Now: bounded Dev114 Vita3K post-Sydney checkpoint run, with matching installed
SELF and unchanged archived-save hash.

Next: distinguish inactive-player restoration from missing star/control-owner
identity, apply the original-owner fix if supported, then consolidate with EVA
for the next candidate. Complete M00, ending, HUD fidelity and 60 FPS remain
unproven. Details: `DEV114_CHECKPOINT_CANDIDATE_RETURN.md` and
`DEV114_CHECKPOINT_SESSION_TRACE.md`.
## Dev114 runtime result; Dev115 consolidated fixes

Dev114 proved the saved star/control owner survive loading, while active-player
lookup returns null and active count is zero. The native guard then controlled-
exited. Vita3K subsequently logged a Windows access violation during shutdown;
do not treat its process result as clean or as physical-Vita evidence.

Implemented for Dev115: strict unique inactive-player/star admission followed
by original cGod reactivation, with object-identity checks; original EVA shell
and seven tabs, captionless-edit parsing and permanent resource regression
coverage. Five checkpoint tests and the integrated EVA C++ contract pass.

Next: checkpoint-enabled Dev115 canonical build, original post-Sydney reload,
pause/resume capture, then authentic M00 progression. Neither repaired runtime
behavior nor complete-demo acceptance is yet established.
## Dev115 canonical pass; Dev116 HUD-format correction integrated

Dev115 canonical build and packaged-SELF identity passed. Its unchanged package
is being installed for the original post-Sydney checkpoint/EVA test.

Substantial new finding: the Vita WW3D initialization branch omitted original
`Init_D3D_To_WW3_Conversion`, leaving CPU surface formats UNKNOWN. Restoring
that call made all ten digits in both HUD fonts match source pixels exactly
across two original M00 ASan host cycles. This is CPU evidence, not a screenshot
or a physical visual acceptance claim.

Integrated after Dev115 exited: original format initialization, fixed-width
TGA disk fields (native layout preserved), permanent host pixel comparison,
explicit non-sanitized cross-scene target build, repaired dialog validator,
and visible-disabled EVA Options for the demo. Deterministic restaging is
running; the current source is ahead of the Dev115 package.

Next: Dev115 checkpoint/EVA runtime result, then consolidated Dev116 build
and visual confirmation. M00 ending and complete-demo acceptance remain open.
# Dev115 checkpoint and EVA return; Dev116 building

Original post-Sydney save reload reached gameplay with original player/star
and saved camera preserved. Native unfocused Start opened the original EVA
Objectives screen with readable tabs, rows and description. Native Circle
returned to visible gameplay (`step-20260909T151717741Z.png`).
Evidence: `reports/DEV115_CHECKPOINT_RELOAD_RETURN.md` and the matching
`Dev115-checkpoint-20260909T1513Z` Vita3K capture directory.
These close checkpoint reload and one pause/resume cycle on Vita3K only.

Dev116 canonical build is running in the background with the integrated HUD
format initialization, fixed-width host TGA layout, stronger atlas regression,
and disabled demo Options action. Log: `build/dev116-canonical.log`.
Next: continue original M00 toward Infantry Barracks; assess Dev116 when ready.
Full M00 completion, ending presentation and physical acceptance remain open.
# Dev115 new-save reliability blocker

Latest state, 2026-09-09: user paused work. Dev116 canonical closure passed;
readable HUD digits, fresh original save/reload and reaching Gunner have
Vita3K evidence. Full M00/ending and current-candidate pause/resume remain
open. Resume from the archived Gunner checkpoint, not a new tutorial run.
Current handoff: `reports/HANDOFF_DEV116_20260909.md`. Older updates below
are historical, not active build/install instructions.

Dev116 runtime update: readable health/armor digits observed; fresh original
quicksave passed structure validation and original-engine reload. Two emulator
runs then failed in Windows Qt6Core.dll with matching exception/offset, one
during pause and one during gameplay. A same-build comparison without the
PrintWindow helper is active; no game or emulator workaround has been applied.
See `reports/DEV116_CANDIDATE_RETURN.md` for hashes and run-scoped evidence.

Dev116 canonical retry is now SUCCESS with matching ELF/SELF/VPK identities.
Runtime installation and checkpoint validation are next, not yet passed.
Authoritative candidate hashes: `reports/DEV116_CANDIDATE_RETURN.md`.

Dev116 retry milestone: integrated host digit comparisons passed with zero
pixel mismatches for both font sizes; original M00 host runtime passed two
in-process cycles. ARM compilation reached 321/558. Artifact closure and
visual HUD checks remain pending. See `reports/DEV116_BUILD_RETRY.md`.

Update: isolated original rooted WRITE/chunk overwrite host probe passed
(15 bytes replaced by 11 bytes). Dev116 include-order compile failure was
corrected and canonical retry launched. Existing quicksave slots are preserved
outside the live user tree for a fresh-versus-overwrite native comparison.
The next runtime sequence is recorded in `reports/DEV116_RUNTIME_PLAN.md`.

Original checkpoint reload and pause/resume passed, and the player reached
outdoors. A subsequent original quicksave overwrite failed strict archival:
four bytes remain beyond the declared level-data end. Preserved the rejected
save privately; did not trim it or relax validation. See
`reports/DEV115_SAVE_OVERWRITE_FAILURE.md`.
Next: distinguish save chunk accounting from native write/truncate behavior.
Dev116 build remains separate, running with the existing integrated fixes.
# Dev138 campaign source integration (2026-09-21)

Full-port-only M01 original script unit now builds and registers on ARM using
a M01-scoped callback-default compatibility header. VPK SHA-256:
`31f846ce145ddf2834f8d0153b8e7a48b6975e3a1debd0fcfa93535e744d5520`.
See `reports/DEV138_M01_SCRIPT_INTEGRATION.md`. M01 gameplay and normal M13
completion-to-M01 transition remain unverified; physical gates remain 0/10.
# Dev143 campaign loading-screen correction (2026-09-21)

Full-port M13 loading no longer forces original multiplayer backdrop 94; it
selects the original mission-indexed backdrop 13 and suppresses demo-only
status/progress presentation. Demo profile remains unchanged. Deterministic
staging, 13 focused tests, and ARM/VPK build pass; Vita3K trials 1 and 2
stalled before launch and do not prove visual parity. See
`reports/DEV143_RETAIL_CAMPAIGN_LOADING.md`. Physical acceptance gates remain
open; no new physical acceptance is claimed.
# Dev146 campaign death/effect lookup (2026-09-21)

Full-port original death UI resources and `cGod::Star_Killed` callback are
connected; death Restart/Load remains unverified because the 240-second
Vita3K direct-entry run did not reach the post-intro lethal event. The original
WW3D aggregate lookup now uses retail/MIX instead of a Windows cwd probe:
isolated Vita3K M13 `app0:/\\e_*.w3d` errors fell 96 to 0. Frame pacing and
audio sync still fail; post-fix frame-120 average was 4.840 FPS on Vita3K,
with 110.101 ms simulation and 96.479 ms render-submission CPU per frame.
Public VPK SHA-256 `c51cef550898a980fb76ab6a29f56c6d2bc01b6bf92456aef7f3f5a3306f1b41`.
See `reports/DEV146_M13_DEATH_AND_EFFECT_LOOKUP.md`. Physical gates unchanged.

# Dev147 performance checkpoint (2026-09-21)

Mission-only M13 dependency preparation and original simulation/clock timing
are implemented in the full-port source. Single-run Vita3K comparisons show
better early drift than no preload, but the late multi-second hitch and audio
desync remain. 4x MSAA stays default after the off experiment regressed there.
Canonical host checks, ARM packaging, artifact identity and diagnostics bundle
now pass after the resumed retry. The asset-free prerelease is published at
`A3.5-dev147-campaign`. No physical acceptance. See
`reports/DEV147_PERFORMANCE_CHECKPOINT.md`. Evidence gates remain 4/10.
