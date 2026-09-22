# Dev147 performance checkpoint

Status: work-in-progress source checkpoint, not a validated release or
physical-Vita performance acceptance. The user requested wrap-up before the
canonical retry finished. Do not publish the Dev147 VPK as a release yet.

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
- Canonical pass 3: source/host validation including 169+14 tests passes;
  ARM compilation, ELF, SELF, and VPK packaging pass. Final validation stopped
  at the obsolete linked-symbol signature in `tools/build.sh`, corrected after
  that run. A full retry was interrupted at the user's wrap-up request.
- The unpromoted packaged VPK is
  `build/vita-a35-dev147-candidate-20260921-224502/RenegadeVita-A3.5-dev147.vpk`
  SHA-256 `9bfc3de794903b0b2a6cbbdc83588c210d21e9f940dc0c453d7a299df16d2ba7`.
  Matching SELF SHA-256
  `a39736a08fd9af9d2ae5d1e1e9e40a7ae7ed64effcab8bb353894b654db653d3`.
  These hashes are retained for diagnosis only, not a release receipt.

## Resume

1. Run `RENEGADE_INCREMENTAL_STAGE=1 RENEGADE_CANONICAL_RETRY_DIR="$PWD/build/vita-a35-dev147-candidate-20260921-224502" RENEGADE_CANDIDATE_LABEL=A3.5-dev147 RENEGADE_M00_DEMO=0 RENEGADE_DEVELOPMENT_CHECKPOINT=0 RENEGADE_BUILD_JOBS=12 bash ./tools/build.sh` through final artifact verification.
2. Repeat fixed M00 tutorial and M13 intro diagnostic routes at least three
   times each, including a no-preload comparison on a warm cache. Record
   p50/p95/p99/worst, frame stage times, memory high-water, clock drift, and
   visual result. Avoid changing source while benchmarking.
3. Isolate the late M13 multi-second hitch with bounded event tracing; do not
   alter original mission timers or audio clock without a causal test.
4. Use matching physical Vita evidence before accepting native 60 FPS or
   cinematic/audio-sync performance. Do not auto-deploy.

Known user changes in `docs/INSTALLING.md` and `reports/ALPHA_STATE.md` were
preserved and excluded from the Dev147 source commit.
