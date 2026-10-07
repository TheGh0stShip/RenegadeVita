# TUT-R1-16 — Tutorial performance log analyzer

Status: host tooling only. No runtime change, no flag, nothing compiled, no
device or emulator action. Branch `tut-r1-16-perf-log-analyzer`, based on
`tutorial-r1/base` (45c6cf5). The requested `git merge --ff-only` failed
because the worktree started on a newer `main` (campaign commits), so the
branch was created from `tutorial-r1/base` directly.

## What it does

`tools/tutorial_perf_report.py LOG [LOG_B]` turns a returned runtime log into
a Markdown and/or JSON report in under a second (0.5 s on the WSL host for a
1.48 MB, 5,899-line full-tutorial log). Stdlib only.

- Per-segment table: frames, time, FPS, mean, p50/p95/p99, worst, frames
  over 33/50 ms, sync/sim/render split. Segments come from the original
  Mission00 breadcrumbs, in route order: boot, load, spawn, logan, sydney,
  gunner, vehicles, mobius, base, end, post (`gameplay` for other levels).
- Top `A3.6 frame-profile` scopes per segment, plus the profiler's own clock
  cost.
- Memory and pool high-water: heap, vitaGL immediate and circular pools
  (plus overruns), static mesh cache, skin cache, decoded PCM, and audio
  failures with first-seen `last_error` values.
- Renderer and simulation counters: static-mesh hits per frame and
  builds/rebuilds, vertex-array batches, GL-shadow and sampler skip rates,
  FFP compiles (count and ms), missed vblanks, Combat µs and casts, awake
  soldiers, VIS census, and campaign-pacing sim/real drift.
- Hitch list (default over 50 ms, `--hitch-ms`). Each hitch shows its exact
  or approximate frame and the nearest preceding breadcrumb (conversation,
  objective or load milestone). It merges `A4 slow frame` and
  `A3.6 frame-profile-worst` entries for the same frame. Window rows show
  only the >50 ms frames that are not listed individually.
- Level-load milestones (with `elapsed_ms` where logged), logged switches
  (RVVA1/RVGS1/RVSM1/RVSD1/RVFP1/RVPL1/RVPW1/RVVS1/RVIR1 announcement lines)
  and integrity notes. Integrity covers the session cap, dropped/suppressed
  lines, a cut final line, NUL tails, missing windows, counter resets, the
  session choice, never-entered segments, profile/perf window alignment, and
  a log that ends mid-segment.
- A/B (`LOG_A LOG_B`): per-segment deltas, switch differences, and a noise
  screen. The screen compares the mean frame-time delta with 2× the standard
  error of the per-window means. It also flags routes whose segment frame
  counts differ by more than 2×.

```sh
python3 tools/tutorial_perf_report.py a35-dev240-runtime.log --out-md dev240.md --out-json dev240.json
python3 tools/tutorial_perf_report.py A.log B.log --label default --label RVVA1-0 --out-md ab.md
# runtime log is opened O_APPEND: compare two launches inside one file
python3 tools/tutorial_perf_report.py run.log run.log --session 0 --session 1
```

## Existing tools checked (extended rather than duplicated)

| Tool | Scope | Why not reused as the base |
| --- | --- | --- |
| `tools/diagnostics/renegade_vita_performance_ledger.py` | Generic `key=value` metric extraction with identity-gated A/B | No segmentation, breadcrumbs, hitches or windowed/cumulative distinction |
| `tools/diagnostics/renegade_vita_postrun.py` | Candidate bundles, `[PERF]`/`[LIFECYCLE]` markers | The runtime does not emit `[PERF]` lines |
| `tools/analyze_runtime_gaps.py`, `analyze_conversation_transitions.py` | Campaign flight-bundle sidecars | Flight frames are a 4096-frame ring (`a35_campaign_flight_recorder.cpp:24`), so they can't cover the whole route |
| `tools/test_frame_profile.py` | C++ harness for the profiler (compiles, not run here) | Emitter-side test |
| `tools/collect_a35_diagnostics.sh` | Zips artifacts | Not an analysis hook; left untouched (shared file) |

## Line-format survey (A3.5-dev240 tree)

`A30_Vita_Log` (`port/platform/vita/a30_vita_runtime.cpp:427`) adds no
timestamp. Renderer breadcrumbs are `[<milestone> <subsystem> <seq>] body`
(`port/platform/vita/vita_platform.cpp:169`).

| Family | Emitter | Cadence / semantics used |
| --- | --- | --- |
| `A3.5 perf` | `a31_vita_runtime.cpp:2767` (called at 7257 every 120 frames, 7318 at exit) | p50/p95/p99 over the last 120 frames (`kTimingWindowFrames`, :373). `avg_fps`, min/max, slow counts and stage averages are cumulative, so window time = Δ(frames·1e6/avg_fps) |
| `A4 slow frame` | `a31_vita_runtime.cpp:2664` | Only frames ≥500 ms; exact frame and stage split |
| `A4 campaign pacing` | `:2721` | Cumulative integer averages; `avg·frames` can dip by truncation, so deltas are signed |
| `A4 combat casts` | `:2750` | Windowed |
| `A3.5 heap`, `A3.5 audio` | `:2844`, `:2853` | Per checkpoint; audio triplets are attempts/successes/failures; `last_error` is sticky |
| `A3.5 mission progress` | `:2321` (on any change, call at 7033); control at 7051 | `active=<conversation>`, `status_1_6` |
| `A3.5 mission completion` | `:6871` (`success=`), `:6909` (star-killed, no `success=`) | Completion ends the tutorial; star-killed is a breadcrumb only |
| `A3.6 frame-profile` / `-worst` / clock-cost / configured | `renegade_vita_frame_profile.cpp:186/209/273/354` | Per 120 profiled frames, top 16 scopes. `frame_index` is within the window (:377) |
| vitagl-pools, static-mesh-cache (+thrash), skin-deform-cache, vertex-array | `ww3d_vita_renderer.cpp:2399, 2547/2564, 2613, 2653` | Pools are windowed; cache counters are cumulative; `frame=` is the renderer counter (resets at gameplay entry) |
| gl-state-shadow, texture-state, frame-vblank, render-work-cache | `:794` (reset at 803), `:4145`, `:4119`, `:4128` | Shadow and vblank are windowed; texture-state is cumulative |
| ffp-program-cache prewarm/window | `ww3d_vita_ffp_program_warm.cpp:145/189` | Window lines always on first use, otherwise every 10th window |
| `A3.6 vis-census` | `a31_gameplay_boundary.cpp:939` | Sampled |
| Switch announcements | renderer :471, :785, :2537, :2602, :2646, :3817, :3892 | `version=1` lines without `frame=` |
| Log integrity | `renegade_async_log.h:27, 92–104, 117–119, 185–192` | 4 MB soft cap, then priority lines only; drop and suppression notes |

Tutorial route mapping (`staging/scripts/Mission00.cpp`). Conversation names
are set in `Say_Something` (:1830–2212). Objectives are accomplished at
SYDNEY_START (:1958), GUNNER_START (:2003), HOTWIRE_INTRO (:2081),
MOBIUS_REFINERY (:2148) and PETROVA_POWER (:2159), and when the second
officer dies (:1199). The actual order is Logan → Sydney → Gunner →
**Hotwire vehicles → Mobius** → Petrova/Lieutenant (base) → end. That puts
vehicles before Mobius, which differs from the brief's list. Logan's
transitional lines map to the segment they introduce (for example
PREPARE_INFANTRY → gunner, WHATSNEXT → mobius, OUTRO → base). A test checks
that every `MTU_*` conversation name in Mission00 is classified.

## Findings worth acting on (no runtime change made here)

1. **No timestamps and only ≥500 ms per-frame records.** Individual 50–500 ms
   hitches are visible only as window counts or one profile-worst frame per
   window. A flag-gated per-frame hitch line (frame, stage split, ≥50 ms,
   rate-limited) would make the hitch list complete. It would be a runtime
   change, so it is left as a follow-up.
2. **The log appends across launches** (`SCE_O_APPEND`,
   `a30_vita_runtime.cpp:405`). A/B runs of one build share a file, so the
   tool splits sessions at `[LIFECYCLE] START`.
3. **4 MB session cap.** dev230's full tutorial used 1.48 MB. dev240's extra
   per-window lines probably stay under the cap, but a profiler-on run plus
   several retries could exceed it. The tool reports `TRUNCATED`.
4. **Baseline from the private physical dev230 full-tutorial log**
   (pre-FPS-round-4; only derived aggregates are quoted here, no raw log
   content is committed):

   | Segment | Frames | FPS | p95 ms | >50 ms frames |
   | --- | ---: | ---: | ---: | ---: |
   | logan | 4,080 | 25.8 | 76 | 493 |
   | sydney | 6,240 | 59.9 | 17 | 59 |
   | gunner | 6,960 | 24.1 | 113 | 2,146 |
   | vehicles | 3,240 | 27.1 | 79 | 610 |
   | mobius | 3,480 | 51.3 | 44 | 108 |
   | base | 3,840 | 29.0 | 74 | 626 |

   The Gunner range is the worst segment. Render dominates there (35 ms of
   render against 6 ms of sim per frame), and simulated time fell 10.4 s
   behind real time. The largest single stalls (1.6–1.75 s) were in the
   render stage right after objective 1 / Sydney start, Gunner reticule, and
   mid-Sydney, which is consistent with first-use loads. Segment frames sum
   to 27,960, matching the final perf line.

## Hypothesis-ledger entry

- **Hypothesis:** per-segment numbers in seconds shorten hardware A/B
  turnaround. They also expose segment regressions (Gunner range, base
  assault) that the cumulative `avg_fps` and `A3.1 interactive: complete`
  summary hide.
- **Risk:** no runtime risk (host only). Analysis caveats:
  - a 120-frame window is attributed to the segment active at its end, so at
    most one window per boundary is affected;
  - multi-window percentiles are mixture estimates (single-window values are
    exact);
  - worst can be a lower bound (shown as `≥`);
  - the noise screen is optimistic because windows are autocorrelated and
    each arm is a single run;
  - FPS precision is about 2e-5 relative per line;
  - stage-average error is ≤ `stage_avg_error_us`.
- **Estimated gain:** developer loop only, from manual grep to under 1 s.
  No in-game gain is claimed.
- **How to measure:** time from log pull to table. Check correctness by
  comparing the summed segment frames with the final perf `frames=`, and
  that the switch differences show only the intended flag.

## Verified vs unverified

- **Verified (host, pure Python):** 34 tests pass
  (`python3 -m unittest tools.test_tutorial_perf_report`).
  - Each parser and aggregate is covered with synthetic fixtures, along with
    segmentation and forward-only movement, hitch merge and remainder, counter
    resets, truncated/NUL/garbage/empty logs, sessions, the A/B verdicts and
    the CLI.
  - Contract tests read the printf formats from the current `port/` emitters
    (runtime, profiler, renderer, FFP, VIS, breadcrumb wrapper, async-log
    markers), synthesize lines from them and parse them, so format drift
    fails.
  - The tool ran without errors on 9 private device logs (dev42–dev238).
    The dev230 tutorial segment starts land exactly on the original route
    breadcrumbs.
- **Unverified:**
  - No dev240 hardware log exists yet. The profiler, vitagl-pools, cache,
    vertex-array, GL-shadow, texture-state, FFP-window, VIS, heap and casts
    paths were exercised only with lines synthesized from source formats.
  - Profile/perf window alignment on hardware has not been confirmed.
  - Mixture-percentile accuracy has not been checked against a true
    per-frame distribution. The 4096-frame flight CSV could validate it for
    one segment.

## Hardware A/B steps

1. Install the candidate and launch twice (the first launch rebuilds the FFP
   cache). Play the tutorial on a fixed route through to "officers down",
   then pull `ux0:data/renegade/user/logs/a35-devNNN-runtime.log`.
2. `python3 tools/tutorial_perf_report.py A.log --out-md A.md --out-json A.json`.
   Check the integrity notes: no `TRUNCATED`, no never-entered segments.
3. Write exactly one switch file (for example `vertex-array-v1.flag` =
   `RVVA1 0\n`), run the same route, and pull the log. Because of append
   mode, either pull a fresh file or use `--session`.
4. `python3 tools/tutorial_perf_report.py A.log B.log --label default --label RVVA1-0 --out-md ab.md`.
   Confirm that "Switch differences" lists only that switch, then read the
   per-segment Δ and noise.
5. Repeat each arm at least 3 times before recording a gain in the ledger.
