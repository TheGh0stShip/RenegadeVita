# Dev147 performance checkpoint

Status: canonical build and packaging passed after the interrupted retry was
resumed. This is a dev candidate, not physical-Vita performance acceptance.

## Changes

- Full-port-only original M13 dependency list is prepared during loading,
  before the original threaded level load. Demo load flow is unchanged.
- Full-port framebuffer MSAA is selectable at CMake configure time; 4x stays
  the default and the demo still calls its original `vglInit` path.
- Cumulative original simulation-stage CPU and real/sim clock counters are
  logged every 120 frames to distinguish the intro stall from audio drift.
- Canonical host fixture now guards Vita-only cinematic logging; its score
  screen link shim remains host-only. A stale mission-completion test now
  recognizes only the development-gated diagnostic completion hook.
- The canonical symbol gate now expects the actual six-argument interactive
  runtime entry. This last gate fix has not completed a new canonical run.

## Evidence

- Four isolated Vita3K/OpenGL M13 diagnostic comparisons: no preload,
  original global+mission preload, mission-only preload, and mission-only with
  MSAA off. Exact frame-600 data and limitations are in
  `reports/PERFORMANCE_HYPOTHESIS_LEDGER.md`. No physical Vita run.
- Mission-only preload improves early clock drift in a single comparison but
  still suffers a later roughly seven-second hitch; audio sync remains broken.
  Original global preload and MSAA-off were rejected.
- Focused mission-completion contract: five tests pass.
- Canonical final retry: source/host validation including 169+14 tests,
  ARM compilation, ELF, SELF, VPK, artifact identity, SHA-256 manifest, and
  telemetry-only diagnostics bundle pass. See
  `build/dev147-canonical-final.log` and the managed dist build report.
- The final packaged VPK is
  `build/vita-a35-dev147-candidate-20260921-224502/RenegadeVita-A3.5-dev147.vpk`
  SHA-256 `9f34057b7eec02b54285f3474d27b9ee2cd4464d8f1ae8f0d6935900fabffd5b`.
  Matching SELF SHA-256
  `a39736a08fd9af9d2ae5d1e1e9e40a7ae7ed64effcab8bb353894b654db653d3`.
  Neither hash establishes Vita launch or gameplay correctness.

## Resume

1. Repeat fixed M00 tutorial and M13 intro diagnostic routes at least three
   times each, including a no-preload comparison on a warm cache. Record
   p50/p95/p99/worst, frame stage times, memory high-water, clock drift, and
   visual result. Avoid changing source while benchmarking.
2. Isolate the late M13 multi-second hitch with bounded event tracing; do not
   alter original mission timers or audio clock without a causal test.
3. Use matching physical Vita evidence before accepting native 60 FPS or
   cinematic/audio-sync performance. Do not auto-deploy.

Known user changes in `docs/INSTALLING.md` and `reports/ALPHA_STATE.md` were
preserved and excluded from the Dev147 source commit.
