# Performance hypothesis ledger

## Dev147 campaign preparation and MSAA (2026-09-21)

Source request: `/mnt/e/Renegade_Vita_Performance_Prompt.md`, "Execution prompt".
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
