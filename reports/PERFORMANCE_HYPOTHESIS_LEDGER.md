# Performance hypothesis ledger

## Dev186 track animation and Vita mapper-state cache (2026-09-23)

- Hypothesis: part of the remaining vehicle/effect cost is avoidable repeated
  Vita GL texture-matrix submission, while static treads are a separate naming
  mismatch rather than a missing original animation path. A tighter cinematic
  command budget should prevent authored bursts from monopolizing simulation
  long enough to let audio drift.
- Evidence: Dev185 recorder showed M13 render spikes of 0.53 s and simulation
  spikes up to 1.90 s; M01 frame 1 was 6.336 s (5.356 s simulation). The
  tracked-vehicle code only searched after `.` and therefore rejected direct
  retail names such as `V_TRACK-L`/`V_TREAD-L`. The Vita texture-stage boundary
  performed GL matrix setup for every identical mapper state.
- Change: accept direct track mesh names; cache per-stage transform/flags and
  skip identical Vita GL matrix work; reduce full-port campaign cinematic
  batches from 12 ms/4 commands to 4 ms/2 commands before yielding.
- Guardrails: original mapper, render ownership, track UV updates, cinematic
  command order, AI, collision, objectives, audio callbacks, and progression
  remain intact. Cache is only at the platform boundary and does not reuse
  volatile render objects.
- Evidence retained: focused source contracts, ARM/SELF/VPK identity, and
  Vita3K install PASS. Runtime A/B and visual/audio acceptance remain pending.
- Decision: adopt for Dev186 as a bounded, measurable candidate; keep or revert
  after the same M13 ambush/tiberium/Ion and M01 beach/ladder route is captured.

## Dev185 retained cinematic/effect physics models (2026-09-23)

- Hypothesis: Dev184's remaining M13 ambush/Ion and M01 beach stalls are not
  solved by warm-only create/release because the expensive render-object
  construction still happens when scripted physics models are first attached
  during live cinematics.
- Evidence: Dev184 runtime logs show `PhysClass::Set_Model_By_Name` taking
  about 2.57 s for `X0F_AG_EFFECTS` from `X0F_Harvester.txt` and about 2.85 s
  for `X0D_AG_Explode` from `X0D_A10_Crash.txt`. The flight recorder shows
  M01 frame 1 at 6.16 s, including 5.21 s simulation and 0.94 s render, right
  after warm-only preparation and at the user-reported beach plane/vehicle
  freeze.
- Change: Allow duplicate retained preparation slots, retain only selected
  scripted M13/M01 cinematic/effect aggregate render objects during loading,
  and consume them only in `PhysClass::Set_Model_By_Name` before falling back
  to original `WW3DAssetManager::Create_Render_Obj`.
- Guardrails: The earlier Dev181 broad cache remains rejected. Dev185 does not
  consume prepared render objects in bullets or surface effects, does not skip
  cinematic commands, does not force objectives, and does not alter AI,
  collision, animation semantics, or mission progression.
- Evidence retained: direct M13/M01 preparation assertions PASS, Dev184
  animation action completion contract PASS, development checkpoint PASS,
  campaign profile defaults PASS, 158 focused fast contracts PASS, ARM/SELF/VPK
  identity PASS, Vita3K install PASS.
- Decision: Adopt as the next runtime candidate because it targets measured
  multi-second live creation stalls while preserving Dev182's volatile-object
  safety boundary. Runtime acceptance is pending M13 ambush/tiberium/Ion and
  M01 beach evidence; no physical performance or A/V-sync acceptance is claimed.

## Dev182 volatile render-object warm-only correction (2026-09-23)

- Hypothesis: Dev181's retained live render-object cache moved first-use work
  into loading, but reusing those live objects for original cinematic real
  objects, missiles, explosions, trails, and particle emitters can age
  one-shot animation/particle state and corrupt actor/effect presentation.
- Evidence: The Dev181 user run and flight recorder reached M13 completion and
  M01, but user-observed regressions included disappearing helicopter
  engineers, the ambush rocket soldier walking in place, severe M13 ambush
  audio/video drift, and an M01 ladder freeze. Runtime logs show the live
  prepared cache being consumed during scripted creation, including
  `vxag_nod_heli`, `X1c_AG_xplosion`, `VxAG_X1Borca`,
  `X0Z_Orca01_Traj`, `X0Z_Orca02_Traj`, and `X0Z_Effects`.
- Change: Keep M13/M01 load-time model preparation, but immediately release
  created render objects after warming the WW3D asset/prototype path. Remove
  Vita-only prepared-object consumption from physics model assignment, bullets,
  and surface emitters so runtime objects are fresh original instances.
- Risk: This may reintroduce some runtime first-use cost compared with Dev181
  for objects whose prototypes were not fully warmed by create/release. It
  intentionally rejects reusing live volatile objects as unsafe.
- Evidence retained: focused source contracts PASS, 156 fast contracts PASS,
  ARM/SELF/VPK identity PASS, Vita3K title install PASS. No runtime A/B has
  been performed yet.
- Decision: Adopt as a correctness correction for Dev181's unsafe optimization.
  M13 ambush/Ion performance and M01 ladder/plane behavior remain pending
  runtime verification; no physical performance acceptance is claimed.

## Dev159 persistent runtime-log handles (2026-09-22)

- Hypothesis: Vita3K console/file-open flood from per-record runtime-log
  open/sync/close contributes measurable overhead in the M13 intro run.
- Change: retain file handles for both `A30_Vita_Log` and the legacy
  `Vita_Append_A22_Runtime_Breadcrumb` path while preserving per-record sync.
- Evidence: `campaign-dev159-persistent-all-logs-m13-installedtitle-1`
  compared against the valid Dev158 installed-title evidence.
- Result: runtime-log open records fell from 52 to 2 and total
  `export_sceIoOpen` console records fell from 1061 to 888. Dev159 reached
  frame 720 with 15.266 FPS, but frame 720 p95 remained 178292 us and frame
  703 still spiked 564717 us.
- Decision: keep as a diagnostics-overhead reduction, not a campaign
  performance acceptance. Continue with measured render/scene traversal and
  residual simulation spikes.

## Dev147 campaign preparation and MSAA (2026-09-21)

Source request: `/mnt/e/Renegade_Vita_Performance_Prompt.md`, "Execution prompt".
Dev148 M13 cinematic-stall continuation (2026-09-22): duplicate WW3D sync
and a separate camera-wall-clock experiment did not fix the render stall; the
latter disrupted authored actor sequencing. Both are reverted. The original
`TimeManager` clamps simulation time after a long render frame while audio
continues in real time, so eliminating the render stall is still necessary.
No audio-sync or performance fix is accepted.

An M13 loading-only referenced-texture prewarm prepared 183 textures in a
diagnostic ARM build. Its Vita3K/OpenGL run had zero texture requests through
frame 240 versus 39 in the prior object-timing probe, but by frame 480 it
reached p50/p95/p99/worst 100.5/275.9/389.2/13769.6 ms and 1 new texture
request. The earlier probe at frame 480 had 64.4/107.8/142.7/2482.1 ms.
These are not fixed-input repeats, but the severe stall persisted despite
eliminating early uploads. The prewarm was rejected and reverted. Evidence:
managed AppData `campaign-dev148-textureprep-m13-1` receipt, status
`TIMEOUT_UNASSESSED`; no physical-Vita measurement.

Follow-up source/evidence check: the production mesh boundary still feeds
vitaGL immediate-mode attributes for each original mesh/material batch, then
calls the project-specific indexed end path. At frame 480 the diagnostic
counter had about 29,539 mesh submissions and 2.53 million triangles
cumulatively; texture prewarm did not change this work. The isolated
texture-prewarm emulator stdout contained 13 `getstat`, 5 `open`, and 4
`mkdir` warning records, not a contemporaneous high-volume error flood.
These facts do not yet distinguish CPU attribute submission, shader first-use,
GPU queue backpressure, or Vita3K host-driver stalls. Next experiment must
separate those costs within the same frame without per-object disk logging;
do not apply another clock or texture-cache change as a stall fix.

Dev148 bounded mesh-boundary probe: a full-port-only ARM diagnostic build
measured each original mesh submission and indexed draw completion in memory,
logging one aggregate per 120 frames. In the isolated M13 Vita3K/OpenGL run,
frames 361-480 accumulated 6.46 s across 10,382 mesh submissions, but only
0.19 s across 25,450 indexed draw completions. The slowest individual mesh
was 371 ms; its draw completion was not the long operation. The run's frame
480 p50/p95/p99 was 58.7/93.5/282.5 ms, with 2.19 s worst from startup.
Evidence: managed AppData `campaign-dev148-meshboundary-m13-1`; candidate
SELF SHA-256 `4d55f724ae94e1eb9eb7d8281945b29d05c3bce1e140bf94a3d6907497ede4eb`.

A following full-port-only repeated-color suppression candidate compiled and
ran once against the same direct-entry route. By frame 720 it still had a
6.91 s worst frame (p50/p95/p99 82.5/377.8/471.6 ms); the indexed draw-end
maximum was 0.13 ms in frames 601-720. Differences in scene timing/object
counts prevent claiming an aggregate CPU win. The color change was rejected
and reverted; no audio-sync or 60 FPS improvement is accepted. Evidence:
`campaign-dev148-colorcache-m13-1`; candidate SELF SHA-256
`ab691c1d6f7f64a2b01073aecbaff0f7f28d42116b81f9d60da36d871900269c`.
Both runs timed out unassessed and do not prove physical behavior. The 6.91 s
frame exceeds the maximum individual mesh time by orders of magnitude, so
the next bounded probe must distinguish scene traversal, material/state
setup, and other backend calls rather than assuming indexed draw completion.
After reverting the color experiment, the ARM/package rebuild reproduced the
mesh-timer candidate SELF SHA-256 exactly; five mission-completion contract
tests passed. This is only diagnostic build consistency, not gameplay or
performance acceptance.

Separate isolated Vita3K/OpenGL Dev148 M13 probes measured foreground
`CombatManager::Render` as the slow phase. A timed frame at ambush frame 667
spent 1.290 s in `WW3D::Render(COMBAT_SCENE)`, including 1.287 s in
`scene->Render`; its world-space list took 0.977 s and dynamic list 0.305 s.
Another run observed 1.107 s in `scene->Render` at frame 726. `Flush`,
background, dazzle, and HUD were not the dominant phases. Per-object threshold
logs identify distinct original models (for example `MX0_BASEWALL` at 0.336 s
and `X0E_OBELISK_GD` at 0.307 s), but do not prove shader compilation,
texture upload, geometry cost, or driver synchronization as the cause. No
render policy change is adopted. Evidence: managed AppData isolated
`campaign-dev148-*` receipts; runtime status `TIMEOUT_UNASSESSED`, not hardware
acceptance. Development-only object probes were removed after diagnosis.

These are isolated Vita3K/OpenGL M13 diagnostic direct-entry observations, not
physical-Vita acceptance or a fixed-input three-repeat benchmark. The route
includes the authored intro with no synthetic movement. The same retail data
tree was used; shader/cache warmth and scene timing may differ between runs.

| Experiment | Preparation | Frame 600 FPS; p50/p95/p99/worst (ms) | Frame 600 simulation/render CPU (ms); clock drift (s) | Decision |
| --- | --- | --- | --- | --- |
| No dependency preload, 4x MSAA | none | 14.51; 66.5/142.2/145.9/3649.8 | 21.82/47.09; 5.69 | Comparison baseline only |
| Original global + mission `.dep`, 4x | original loading phase | 7.33; 23.3/282.1/513.9/15804.3 | 69.89/66.61; 28.05 | Rejected: severe late hitch and clock loss |
| Mission `.dep` only, 4x | 9.52 s before threaded map load | 16.96; 79.8/212.9/279.1/2212.7 | 15.12/43.84; 3.60 | Provisional: better early drift, late hitch remains; repeat and physical test required |
| Mission `.dep` only, MSAA off | 8.36 s before threaded map load | 12.09; 87.4/203.0/239.3/7039.2 | 34.32/48.42; 10.62 | Rejected for public default; 4x retained |

The original simulation stage timer places nearly all measured simulation CPU
time inside `CombatManager::Think`, which includes scene/render work; it does
not establish GPU time. Later mission-only runs reach a roughly 6.86-7.04 s
single-frame hitch and 14+ s clock drift. Audio uses real time while the
original simulation clock is capped after long frames, a plausible mechanism
for the observed desync, not yet a proven root cause. Do not solve this by
changing mission-script timers or forcing audio clock changes. Next experiment:
bounded frame-event capture around the late hitch, then fixed-route repeated
M00/M13 A/B on physical Vita before native acceptance. Diagnostic receipts:
managed AppData `campaign-dev147-{profile,preload,missiononly,msaa-off}-m13-1`.


Current continuation: Dev127 implemented measured CPU-work reductions and
Dev128 integrated native DDS chains; their reports supersede older pending
implementation entries below. Physical performance adoption remains open.
Dev134 is in canonical validation, with no physical test requested or performed.

| Current route | Evidence and candidate action | Remaining acceptance |
| --- | --- | --- |
| Discarded textured-character RGB | Production path calculated lighting then submitted white RGB. Dev134 retains diffuse alpha and first diagnostics while skipping the discarded calculation. 192000 full-color, 96000 submitted-skin and 15360 alpha cases pass; production draw ordering/state and sanitizers pass. Fixed host median/p95/p99/worst 164.5/221.1/317.0/317.0 -> 19.6/21.8/29.9/29.9 us; same scratch high-water. | Candidate implementation; ARM/canonical closure active. Matching native visual and physical fixed-route frame-time/memory results pending. See DEV134_SKIN_RGB_WORK.md. |
| Native YUV movie sampling | Actual Bink inputs are 800x600 limited-range YUV420; pinned VitaGL/GXM supports planar CSC textures. At unchanged 320x240, packed payload is 115200 rather than 307200 bytes. | Prototype pending transactional GPU replacement, plane/stride tests, color comparison and native timing. See DEV134_NEXT_RENDER_ROUTES.md. |
| Persistent geometry and render handoff | Original mesh/UV/color/user-lighting arrays expose mutable pointers without generations; direct mesh submissions bypass DX8 buffers. | Requires original mutation/lifetime tracking or a validated immutable snapshot and GPU retirement. Pointer-only caching is not safe; route remains open. |

Earlier ledger entries follow as historical hypotheses, not current implementation
status. Host gains never establish hardware FPS.

This ledger accepts changes only with a fixed content hash, camera/input replay,
settings, build mode, p50/p95/p99/worst frame timing, CPU-stage timing, memory
high-water, and visual/correctness comparison. The frozen A3.2-dev1 data is a
diagnostic baseline, not an A/B result for the corrected source.

| Hypothesis | Evidence | Proposed change | Correctness risk | Benchmark / decision |
| --- | --- | --- | --- | --- |
| The project needs explicit 60/50/30/20 FPS gates before optimizing larger M00/M01 scenes | User target is 60 FPS top-end, less than 50 FPS undesirable, and 30/20 FPS unacceptable for gameplay; prior tooling only exposed 16.7 and 33.3 ms slow-frame counts | Capture comparison now reports pacing tier plus 16.7/20.0/33.3/50.0 ms slow-frame counts and percentages; runtime logs now emit p99 and all four slow-frame bands | None to runtime behavior; reporting-only until built | **Adopted as evidence contract**; no performance gain claimed until matching physical A/B captures exist. |
| Existing renderer state cache cannot be tuned responsibly without knowing skip/applied ratios | Dev84 and A3.2 data show high cumulative state/bind counts, but do not distinguish unavoidable material transitions from redundant platform calls | Add counters for texture bind, sampler, stage-enable, combiner, and render-state skips in renderer logs, state.json, and frames.csv | Low; counters are diagnostic and preserve current state ordering | **Prepared, unbuilt**; use next fixed-route capture to decide whether cache expansion, call removal, or a different renderer path is justified. |
| CPU-side projected normal meshes lose homogeneous W and expand indexed triangles | A3.2-dev1 frame 2400 has render 18.938 ms, 0 indexed submissions; source inspection found CPU perspective division in the normal path | Preserve GPU model/view/projection W (implemented for correctness); evaluate indexed/buffered submission separately | Projection, clipping, UV interpolation, ordering | Correctness repair is ARM-built; performance decision **deferred** until corrected physical capture and visual checkpoints exist. |
| Immediate-mode expanded triangles cause avoidable vertex/submission work | Existing renderer still expands normal mesh indices; no post-fix measured cost split | Prototype a bounded indexed/buffered backend only behind a renderer switch | Mesh offsets, FVF translation, transparency ordering, VitaGL behavior | **Deferred**; require M00/M01/City replay A/B and screenshot fingerprints. |
| Texture/state churn dominates render CPU time | Failed log has 216,621 cumulative binds and 16,800 changes by frame 2400; values are cumulative, not per-material root cause | Add first-use state/resource evidence, then reduce redundant binds only where ordering permits | Alpha/depth/material semantics | **Deferred**; no batching or sort change without material-state capture and A/B. |
| 4x MSAA / fill rate harms pacing | A3.2 startup configuration used native 960x544 triple buffering and 4x MSAA; no controlled device comparison exists | Benchmark MSAA, resolution scale, and frame cap as independent profiles | Visual quality and image correctness | **Deferred**; needs physical fixed-route captures. |
| Deferred no-output audio boundary performs repeated work | Frozen log has 282 repeated messages | A3.5 rate-limits diagnostics and retains a stateful boundary without synthetic sounds | Original audio lifecycle | **Deferred** for performance; no post-fix timing evidence. |
| vitaGL's default 16 MiB system-RAM reserve leaves too little non-pool memory during M00 static-object creation | Physical A3.5-dev5 diagnostic samples at objects 0, 25, 50, 75, 100, and 108-116 were identical: system user free 16,777,216 bytes; CDRAM/phycont free 0; vitaGL RAM/VRAM/slow/all free 54,998,160 / 80,124,896 / 27,262,336 / 162,385,392 bytes | Consider a larger reserve only after direct internal-heap/high-water evidence identifies pressure | Reduces renderer pools; may move rather than fix exhaustion and can regress textures/geometry | **Rejected as the immediate object-116 fix**: no measured pool consumption across the stall window. Internal heap pressure remains unmeasured, so pool tuning is deferred. |
| M00 scene pre-warm repeats full original scene rendering and loading-overlay viewport transitions after assets are already resident | Guarded Dev84 physical log: 60 M00 pre-warm frames took 11,489 ms, with 22 resident textures, 23 binds, 0 uploads, 1,515 cumulative backend errors at its completion; the run then reached original M00 control | First add phase-separated timing for original scene render, original loading overlay, resolution/presentation changes, texture work, and forced delay; only then benchmark a reduced warm-frame budget or convergence-based stop against the same fixed M00 camera/content route | Reducing warm coverage can reintroduce shader/texture compilation hitches or change original loading presentation ownership | **Deferred**: the returned run includes later un-attributed physical input, has no fixed replay/camera identifier or p99, and has no A/B capture comparison. No scope, frame budget, or render behavior has changed. |
| Steady M00 pacing is limited by renderer state/bind churn | Guarded Dev84 physical frame-480 summary: p50/p95 ordinary frame time 33.344/48.957 ms, 431/480 frames over 33.3 ms, 975,308 cumulative state changes, 139,350 texture binds, 75,956 meshes, 3,291,682 triangles, and zero current backend errors | Record state-change categories and redundant-call skips in a fixed M00 camera replay; reduce only proven duplicate platform calls while preserving original material/depth/alpha/fog ordering | DX8 material, alpha, depth, fog, texture-stage, and viewport semantics; sorting or batching would exceed this investigation | **Deferred**: current evidence establishes a cost signal but not a causal category or controlled A/B result. No cache, batching, renderer-profile, or quality setting has been adopted. |
## Dev149 M13 ambush freeze attribution (2026-09-22)

The earlier scene-render hypothesis did not explain the repeated multi-second
ambush frame. In isolated Vita3K/OpenGL M13 direct-entry runs, Dev149 bounded
timers placed a 6.997 s frame in simulation (6.964 s) rather than render
(33.6 ms); Combat Think then attributed a matching 6.285 s frame to its post
phase (6.248 s). The final matching candidate captured frame 633 at 6.778 s,
with 6.740 s simulation and 37.6 ms render. `GameObjManager::Post_Think`
took 6.701 s; a single original object callback, ID `1500000007`, took
6.700 s. Observer deletion and pending script destruction each took about
1 us. This is CPU process-clock timing, not GPU timing. The object definition
and inner operation remain unverified, so no performance fix is adopted.

Evidence: managed AppData `campaign-dev149-postsplit-m13-3` and
`campaign-dev149-postowner-m13-2` Vita3K receipts/logs; final diagnostic
SELF SHA-256 `d4035771f2820779c6e33604fcd83d016287213ec433a43d6fcb8f59644ad482`.
The final run timed out unassessed, not physical acceptance. Next experiment:
record the object's definition and split its original post-think callback
around animation completion/observer dispatch and resource requests; then
apply a load-time or boundary fix only to the confirmed operation. Fixed-route
before/after frame p50/p95/p99/worst, clock drift, visual/script sequence,
and M00 regression are still required before accepting any optimization.
Dev150 narrowed the same M13 event to original `Test_Cinematic` slot 19,
`X00_AG_Explode` in unchanged M13 retail control text. Within the timer's
6.169 s, object allocation was 0.377 ms and `Commands->Set_Model` was
6.166 s. The original latter path creates a WW3D render object by name and
installs it into the physics object/scene. A loading-time creation/release
of this exact model is now a testable preparation hypothesis, not an accepted
fix; it may merely move cost or fail to remove scene-notification cost.
Evidence: managed AppData `campaign-dev150-slot19-m13-1` matching
SELF `1ba9212ececdb4406e4e6dccb59da0740c12444e1392b6deb6296dbf0136493a`.
Dev151 tested the exact loading-time WW3D object pre-create/release hypothesis.
In the isolated M13 Vita3K/OpenGL route, it added 5.885 s to loading and the
live `Set_Model("X00_AG_Explode")` still took 6.005 s (Dev150: 6.166 s).
This is **rejected**: no demonstrated live improvement and greater total
cost. It suggests a per-instance or scene-installation cost rather than only
first prototype load, but that is an inference, not a proved root cause.
Evidence: managed AppData `campaign-dev151-modelprep-m13-1`, matching
SELF `c7c65ef3001f21ace248b68d3963dc7b0e6b61df262f69eabbb1c8721cae025d`.
Dev152 removed the rejected pre-create and split the original physics setter.
In the same M13 route, `WW3DAssetManager::Create_Render_Obj` consumed
6.084 s, while `PhysClass::Set_Model` scene installation consumed 39 us and
reference release 1 us. Thus the repeated per-instance asset-manager create,
not physics scene notification, owns the stall. Whether prototype creation,
nested child requests, or on-demand file I/O dominates is still unmeasured.
Evidence: managed AppData `campaign-dev152-physmodel-m13-1`, matching SELF
`ce01e50e2cf93e273cacfdb91ab3005a9b29f2c94405c47d56964dbabf1307f3`.
Dev153 split the asset manager: `X00_AG_Explode` had an existing prototype
whose resulting object has HLOD class ID 25; lookup 4 us, load phase 1 us, `proto->Create()`
6.123 s. No nested child call exceeded 100 ms in the bounded trace.
Repeated on-demand file loading is not the immediate 6 s cause. The original
prototype's inner work remained to be timed; no optimization is accepted.
Evidence: managed AppData `campaign-dev153-assetdepth-m13-1`, matching
SELF `d73dfcfcd3f25df0c3d889b5472382e49188631dba7f6ac21f363bb96d24e225`.
Dev154 identified the actual prototype as an aggregate, not an HLOD or HModel
prototype. `X00_AG_Explode` has 91 child render objects; in the matching M13
run their creation consumed 6.634 s while attachment consumed 0.207 ms.
The base model took 0.184 ms. Repeated bounds updates during attachment are
therefore not the freeze cause; no performance change is accepted. Next test
is an assembled retained template with fresh clones, compared against this
same route and M00. Evidence: managed AppData `campaign-dev154-children-m13-1`,
matching SELF `e89f3402e43ac431400cea0a6cdfcc6127114f74b0d161316227e07ef830e77d`.
Dev155 retains one fully assembled original `X00_AG_Explode` aggregate
template at M13 loading and returns fresh `Clone()` instances thereafter.
In final-hash M13 Vita3K/OpenGL evidence, preparation cost 8.268 s and the
first live rocket's original script `Set_Model` cost 9.016 ms versus Dev154's
6.638 s. This is an adopted event-local win, not an overall 60 FPS result.
Final-hash M13 frame-480 cumulative p50/p95/p99/worst remained
101.4/328.5/378.4/2559.1 ms; route frame distributions are not directly
comparable because the bounded runs reached different content. Template
memory high-water and physical visual/audio result are unmeasured. Full-port
M00 direct entry reached frame360. Evidence: managed AppData
`campaign-dev155-final-m13-1` and `campaign-dev155-final-m00-1`, SELF
`980640b313ccca8a9dde948497296ee0681b6e3122f226a903aa7d721f8fc96f`.
Dev156 extends retained aggregate templates to measured M13 `ag_rocketl`.
Final-hash live clones took 162 and 81 us versus Dev155's roughly 101-151 ms
per create. Loading preparation added 134 ms. An `ag_fiery_ex06` attempt did
not enter the aggregate path and was removed before the final build. This is
an adopted event-local win only: final frame-480 p50/p95/p99/worst were
90.3/412.9/449.4/2846.0 ms, so overall performance did not improve cleanly.
Evidence: managed AppData `campaign-dev156-final-m13-1`, matching SELF
`f738f786a2dabe07cb701e77b14a436494f1bb32de981c297a722766a2192001`.

Dev157 adds a separate full-port-only retained HLOD template for
`ag_fiery_ex06`, the non-aggregate fiery effect observed after Dev156. In
managed AppData `campaign-dev157-fiery-hlod-m13-1`, loading preparation took
92.263 ms and no later `ag_fiery_ex06` slow-create record appeared. This is
only a narrow event-local improvement. The same route still measured frame-720
average 18.744 FPS with p50/p95/p99/worst 44.3/138.0/148.6/1928.0 ms, and a
later frame 784 cost 642.050 ms. Audio stats still reported
`11-ambient beach.mp3` as the active stream through the intro; that filename is
present in `M13.mix`, so this is not proven cross-map leakage. The remaining
accepted blocker is route-level renderer/scene traversal and audio timing under
frame starvation, not this individual HLOD create. Evidence: matching SELF
`de39b87f8e55c616891835db8f6f35013e93891ff18e3cbf80d4b89f48a4f714`, runtime
SHA-256 `f1ed16493bb4c8a885949091ccdd003272f16eea5ea5f1fad7d7ce5600909986`.
