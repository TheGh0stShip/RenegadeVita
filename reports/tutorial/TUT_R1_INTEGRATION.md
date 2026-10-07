# Tutorial round 1 — integrated development branch

Status: 20 parallel agent work items on the tutorial (M00) and on build and
developer-loop speed, integrated on `tutorial-r1/integration`. **Agents were
not allowed to build. Nothing in this round has been compiled, packaged,
installed, or run in Vita3K or on a Vita.** Every gain is an estimate.
Per-item detail: `reports/tutorial/TUT_R1_<SLUG>.md`.

## Identity

| Item | Value |
| --- | --- |
| Base | `tutorial-r1/base` 45c6cf5 = main 6528a8e + unmerged `fps-r4/integration` (A3.5-dev240) |
| Branch | `tutorial-r1/integration` (not merged to main; main has since moved on with campaign work) |
| Staging | 585 ordered patches, inventory PASS, sha256 `f6db6d53b811ce1c22da2996e66009d08f1998d12d2113f9df0bdecfe1969410`; regeneration reproduces all 1,947 tracked staged files byte for byte |
| Host evidence | `tools/run_host_tests.py --pure-only --allow-known-failures`: 171 modules, 1,301 tests, PASS in 34 s; the only failures are the 5 known ones listed in `tools/host_test_known_failures.json` |

## Runtime items (every switch is a file under `ux0:data/renegade/user/config/`)

| # | Item | Change | Switch | Default |
| --- | --- | --- | --- | --- |
| 01 | Texture budget | 16-bit archive TGAs stay 16-bit on the GPU instead of being expanded to 32-bit (about 0.8 MB in M00, 28 MB in M08) | `tutorial-texture-v1.flag` `RVTX1 1` | off |
| 02 | First-use prewarm | Loads the tutorial's weapons, presets, explosions, sounds and hold-style animations while the loading screen is shown. dev230 shows a 0.5–0.85 s stall on the first select of each weapon | `tutorial-prewarm-v1.flag` `RVTP1 <mask>` | off |
| 03 | Script think cost | Measurement only: profile scopes for objectives, conversations and spawners. The script layer is estimated at 0.03–0.15 ms per frame | `script-cost-v1.flag` `RVSC1 1` | off |
| 04 | AI/pathfind | Skip the soldier personal-space probe when the result would be ignored. Engine state is identical | `pathfind-cost-v1.flag` `RVPF1 0` disables | **on** |
| 05 | Physics/collision | No change. The port adds no per-frame scene queries. Audit and analyzer tools only | `RVPH1` reserved | — |
| 06 | Particles | Skip the visual update of particles that the same render will not draw (bit-identical output); log line; fix for an original defect where low-LOD clones draw stale colour (bit 1) | `particle-cost-v1.flag` `RVPE1 <hex>` | **5** (bits 0 and 2) |
| 07 | Audio | Exact ADPCM reserve (264 `always.dat` voices over-allocate about 2×), cache check before decode, second-open stream caching, bounded image slabs | `audio-cost-v1.flag` `RVAU1 <hex>` | off |
| 08 | HUD/text | The message window keeps its measured text build instead of rebuilding the same rows in the same frame | `hud-cost-v1.flag` `RVHD1 1` | off |
| 09 | Frame allocations | Texture-atlas conversion reuses the bounded upload scratch; the HUD target name uses a WWLib temp buffer | `frame-alloc-v1.flag` `RVAL1 0` disables | **on** (3) |
| 10 | Load I/O | Unbuffered retail reads (newlib's 1 KiB stdio buffer split each 16 KiB refill into 16 reads), no second MIX open just to get the size, 250 ms sub-status repaints | `load-io-v1.flag` `RVIO1 <0-7>` | off |
| 11 | Frame pacing | Locked 30 Hz or adaptive 30/60 through `eglSwapInterval`; game timing is unchanged | `frame-pacing-v1.flag` `RVFR1 off\|30\|auto` | absent = unchanged |
| 12 | Clocks/threads | Re-apply max clocks after any resume and every 10 s; move light helper threads off core 0; keep-awake during cinematics and conversations | `clocks-v1.flag` `RVCK1 <0-7>` | off |
| 13 | Render ordering | Pass-major replay of opaque static-cache world draws (259 lightmapped tutorial meshes switch state twice each) | `render-sort-v1.flag` `RVSO1 0-3` | off |
| 14 | Benchmark | Fixed 11-viewpoint tutorial benchmark using the original camera; per-viewpoint frame percentiles plus a submission fingerprint; CSV output and `tools/compare_tutorial_bench.py` | `tutorial-bench-v1.flag` `RVTB1 1-5\|C` | off |
| 15 | Dev checkpoints | Every launch enters the same original tutorial save (development-checkpoint builds only); host catalog, launch and verify-log tooling | `tutorial-checkpoint-v1.flag` `RVTC1 <slot>.sav` | off |

The three default-on items were reviewed by the coordinator before merge:
- **04:** `Is_Safe_To_Disable_Ghost_Collision` only reads the grid and
  rebuilds a temporary list that later code resets first.
- **06:** the keyframe cursors still advance for skipped particles.
- **09:** nothing else uses the shared scratch buffer during conversion or
  upload, and every pixel is written before it is read.

## Build and developer-loop items

| # | Item | Result |
| --- | --- | --- |
| 16 | Perf log analyzer | `tools/tutorial_perf_report.py`: per-segment p50/p95/p99, profiler scopes, hitch list, A/B. dev230: the Gunner range is worst (24.1 FPS, p95 113 ms, render 35 ms against sim 6 ms) |
| 17 | Compile time | Opt-in shared ccache dir, relocatable debug info, and removal of unused source-count defines; `tools/ninja_log_report.py`. Canonical ARM builds currently never get ccache hits (`-g` plus a new build directory each time) |
| 17+ | Coordinator follow-up | `commando-tut1-gamedata-include-spelling.patch`: `gamedata.h` includes `notify.h`/`signaler.h` directly. The literal-backslash shims stopped all 63 includers from being cached |
| 18 | Staging speed | `stage_sources.sh` takes about 16.5 s → 5.9 s; fingerprint skip with `RENEGADE_STAGE_IF_CHANGED=1` (about 0.5 s); canonical builds still always restage |
| 19 | Dependency cache | Opt-in content-addressed cache for vitaGL, FFmpeg and HTTPS, which take about 9–10 minutes per fresh worktree; off unless `RENEGADE_DEPENDENCY_CACHE[_DIR]` is set |
| 20 | Host test runner | `tools/run_host_tests.py`: manifest classifier, `--changed`, parallel lanes, a `--pure-only` fast lane (about 25–34 s against about 65 s sequentially), and a known-failure ledger |

## Coordinator integration fixes

- **Demo build (main since 5b25988):** the M00 demo build called the
  undefined `Read_Vsync_Enabled()`. The vsync and frame-pacing block now sits
  behind `!RENEGADE_VITA_M00_DEMO`.
- **Patch stacking:** the benchmark camera patch was rebased onto the
  script-cost scopes (both patch `combat.cpp`), so it applies at zero fuzz
  and zero offset. Three contract tests were re-anchored for the
  combined code.
- **Shared registrations:** `stage_sources.sh` entries were union-merged
  (each tut1 patch touches a distinct file, except the stacked
  `combat.cpp` pair).
- **Receipts:** the staging receipt and host-test manifest were refreshed.
- **FPS round 4 reports:** two claims were corrected. `HAnimComboDataClass`
  is pool-allocated, and the weapon chart is not rebuilt every frame.
- **Pre-existing quirk:** `RENEGADE_INCREMENTAL_STAGE=1` (since dev49)
  rewrites staged file modes from 755 to 644. They were restored before
  committing.

## Not verified

- **Compilation:** the ARM build has not run, and neither have the compiled,
  sanitizer and artifact host lanes. This includes
  `test_vita_audio_cost_equivalence`, `test_vita_opaque_sort_native`,
  `test_development_checkpoint` and `test_frame_profile`.
- **Device evidence:** no Vita3K install and no physical evidence.
- **Runtime behaviour:** no visual parity or measured gain.

## Leads for other workstreams (unverified)

- **Campaign:** the campaign cinematic preset warm passes path-form model
  names to `Create_Render_Obj`, so it may load nothing (TUT-R1-02).
- **Power callbacks:** the suspend and low-battery counters are probably never
  delivered to a normal app (TUT-R1-12).
- **Test isolation:** 17 pure test modules import only because another test
  adds `tools/` to `sys.path` first (TUT-R1-20).

## Hardware plan (after an ARM build of this branch)

1. **Defaults:** full tutorial route. Run `tools/tutorial_perf_report.py`
   on the log and check the three default-on items visually: soldiers at
   ladders, muzzle and impact effects, subtitles and target names.
2. **Benchmark:** run with `RVTB1 C` once for viewpoint screenshots. Then
   run `RVTB1 3`, twice per candidate, because the first launch rebuilds the
   shader cache.
3. **Switch A/B:** change one switch per arm, three runs each, and compare
   with `compare_tutorial_bench.py`. Priority order:
   - `RVFR1 auto`, then `RVFR1 30` (judder and input lag);
   - `RVSO1 1` and `2` (lightmaps, coplanar seams);
   - `RVTP1 F` with and without `RVAU1 4` (they share the 4 MiB PCM cache);
   - `RVIO1 7` (load time);
   - `RVCK1 7` (resume during load, dimming);
   - `RVTX1 1` (PCT/MCT screen colour).
