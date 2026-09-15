# Performance and fidelity plan

## Goal

Make the native Renegade Vita port scale from the current M00 tutorial path to
larger campaign scenes without turning into a 20-30 FPS title. The user's
target is 60 FPS or better throughout the representative playable route.
50/30/20 FPS bands are diagnostic severity bands, not alternate acceptance
targets. Prewarm and synthetic call-count improvements do not establish FPS.

Frame-time gates:

| Band | Frame budget | Interpretation |
| --- | ---: | --- |
| 60 FPS target | 16.667 ms | User's target for the representative route |
| 50 FPS diagnostic band | 20.000 ms | Below target; investigate frame-time cost |
| 30 FPS diagnostic band | 33.333 ms | Severely below target; not acceptance |
| 20 FPS critical floor | 50.000 ms | Treat as unacceptable for gameplay |

No performance gain is accepted without a fixed content hash, replay/camera
identifier, matching build mode, before/after p50/p95/p99/worst frame times,
slow-frame counts for all four bands, CPU-stage timing, renderer/resource
counters, memory low-water, and visual/correctness evidence.

## Current evidence

- A3.2-dev1 failed physical evidence recorded 39.418 average FPS,
  21.874/24.446 ms p50/p95 ordinary-frame time, 231 frames over 33.3 ms,
  6.427 ms simulation, 18.938 ms rendering, 216,621 texture binds, 16,800
  state changes, and zero indexed submissions by frame 2400.
- Guarded Dev84 physical data recorded p50/p95 ordinary frame time of
  33.344/48.957 ms by frame 480, 431/480 frames over 33.3 ms, 975,308
  cumulative state changes, 139,350 texture binds, and zero current backend
  errors.
- Dev99 is local-only and has no physical FPS/capture evidence. It cannot be
  used as a performance baseline until built, deployed with permission, run on
  hardware, captured through VDB `capture.screen.v1`, and compared against the
  fixed route.

## No-build changes prepared in this work unit

- Capture-bundle comparison now classifies runs into target/preferred/degraded/
  critical FPS bands and reports 16.7, 20.0, 33.3, and 50.0 ms slow-frame
  counts and percentages.
- Runtime-log ledger parsing now understands current `A3.5 perf` fields:
  `avg_fps`, `perf_fps`, compact frame percentile summaries, compact
  `stage_us sync/sim/render`, and the new slow-frame bands.
- Renderer telemetry now counts redundant-call skips for texture binds,
  sampler state, texture-stage enable, texture combiner state, and render
  state. These counters prove whether cache work is actually avoiding platform
  calls on the same scene rather than merely changing the rendered workload.
- Interactive runtime logging now emits p99 and all 60/50/30/20 FPS budget
  slow-frame counts.

## Optimization lanes

1. Evidence lane: require one fixed M00 route and one heavier route before any
   renderer/performance claim. Every run must include parsed logs, capture
   bundle CSV/state, VDB logical-framebuffer screenshots, and screenshot visual
   inspection.
2. Renderer submission lane: measure the existing immediate-mode `MeshClass`
   path first. If it remains dominant, prototype original-owned indexed or
   buffered submission behind a narrow switch while preserving W/clipping,
   FVF layout, material pass order, alpha/depth/fog state, and transparency
   ordering.
3. State/bind lane: use the new skip counters to find repeated VitaGL calls.
   Reduce only redundant platform calls with matching original DX8 state,
   never by sorting or reordering gameplay/world materials.
4. Texture/pre-warm lane: separate startup, intro movie, menu, loading screen,
   and gameplay warm-up timing. Replace fixed warm-frame guesses with
   convergence gates where possible: no new uploads/decodes, stable resident
   texture count, stable backend error count, and visible progress during slow
   work.
5. Frame pacing lane: measure present/sync cost separately from simulation and
   render submission. Avoid adding fixed delays to hide timing issues; any
   frame cap or quality mode must be explicitly profiled.
6. NPC/effects lane: keep original simulation ownership, but profile dynamic
   object count, skinned vertices, emitters, explosions, shadows, vehicles,
   and script activity as separate counters before adding larger scenes.
7. Fidelity lane: treat resolution scale, MSAA, shadow quality, and effect
   density as profiled profiles only. Do not trade away text readability,
   target-box correctness, HUD/dialogue placement, original asset semantics,
   or mission scripting for FPS.

## Acceptance gates for the next build/test window

1. Canonical and fast builds pass with no `.rej`/`.orig` debris.
2. Candidate identity, VPK/SELF/ELF hashes, and diagnostics ZIP are retained.
3. Fixed M00 replay/camera/content identifiers are present in logs and bundles.
4. VDB logical-framebuffer PNG/raw/metadata evidence is retrieved and visually
   inspected.
5. Runtime logs parse with FPS, p50/p95/p99/worst, slow-frame counts for all
   four bands, CPU stages, renderer counters, and memory low-water.
6. Capture-bundle comparison shows unchanged world/player/render checksums
   unless a difference is intentionally explained.
7. Mean FPS, p95, p99, and slow-frame counts are compared against the previous
   matching candidate before any optimization is accepted.
8. Menu text, dialogue text, HUD health/armor/ammo, pickup text, loading
   progress, target box placement, intro A/V, Start/pause/exit, and HMVV
   stability remain in the physical gate.
9. Memory low-water and texture residency do not regress enough to threaten
   larger scenes.
10. GitHub/report/gallery/evidence updates describe only proven results and do
    not claim physical success without returned artifacts.
