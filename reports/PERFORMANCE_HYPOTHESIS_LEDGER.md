# Performance hypothesis ledger

This ledger accepts changes only with a fixed content hash, camera/input replay,
settings, build mode, p50/p95/p99/worst frame timing, CPU-stage timing, memory
high-water, and visual/correctness comparison. The frozen A3.2-dev1 data is a
diagnostic baseline, not an A/B result for the corrected source.

| Hypothesis | Evidence | Proposed change | Correctness risk | Benchmark / decision |
| --- | --- | --- | --- | --- |
| CPU-side projected normal meshes lose homogeneous W and expand indexed triangles | A3.2-dev1 frame 2400 has render 18.938 ms, 0 indexed submissions; source inspection found CPU perspective division in the normal path | Preserve GPU model/view/projection W (implemented for correctness); evaluate indexed/buffered submission separately | Projection, clipping, UV interpolation, ordering | Correctness repair is ARM-built; performance decision **deferred** until corrected physical capture and visual checkpoints exist. |
| Immediate-mode expanded triangles cause avoidable vertex/submission work | Existing renderer still expands normal mesh indices; no post-fix measured cost split | Prototype a bounded indexed/buffered backend only behind a renderer switch | Mesh offsets, FVF translation, transparency ordering, VitaGL behavior | **Deferred**; require M00/M01/City replay A/B and screenshot fingerprints. |
| Texture/state churn dominates render CPU time | Failed log has 216,621 cumulative binds and 16,800 changes by frame 2400; values are cumulative, not per-material root cause | Add first-use state/resource evidence, then reduce redundant binds only where ordering permits | Alpha/depth/material semantics | **Deferred**; no batching or sort change without material-state capture and A/B. |
| 4x MSAA / fill rate harms pacing | A3.2 startup configuration used native 960x544 triple buffering and 4x MSAA; no controlled device comparison exists | Benchmark MSAA, resolution scale, and frame cap as independent profiles | Visual quality and image correctness | **Deferred**; needs physical fixed-route captures. |
| Deferred no-output audio boundary performs repeated work | Frozen log has 282 repeated messages | A3.5 rate-limits diagnostics and retains a stateful boundary without synthetic sounds | Original audio lifecycle | **Deferred** for performance; no post-fix timing evidence. |
