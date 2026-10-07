# TUT-R1-14 — Fixed tutorial performance benchmark (RVTB1)

Status: source, staging patch, pure-Python mirror tests and comparison tool
on branch `worktree-agent-aa3e0476058041b6d`. **Nothing was compiled, packaged,
installed or run.** No frame-time figure in this report is a measurement.

Base: the worktree could not fast-forward to `tutorial-r1/base` because `main`
had moved past its merge base (`6528a8e`); the untouched fresh worktree branch
was moved to `tutorial-r1/base` (`45c6cf5`, main + FPS round 4 / dev240)
before any work.

## What it does

`ux0:data/renegade/user/config/tutorial-bench-v1.flag` (exactly 8 bytes):

| Content | Effect |
| --- | --- |
| absent or `RVTB1 0\n` | off (default). No log line, no file I/O beyond the one flag `fopen` per level load. |
| `RVTB1 1\n` … `RVTB1 5\n` | 1–5 passes of the fixed route |
| `RVTB1 C\n` | one pass plus one capture bundle (BMP + state.json) per viewpoint, for visually validating the viewpoints |
| anything else | rejected, logged once, off |

With `M00_Tutorial.mix` loaded and the flag on, the existing native frame loop
waits until original player control is available (the existing
`tutorial_control_ready_observed` gate), at least 300 control frames have passed
and no original conversation has been active for 120 consecutive frames (or 5400
control frames as a timeout, logged `quiet=0`). It then holds the **original
Combat camera** at 11 fixed viewpoints for 30 settle + 120 measured frames each.
Gameplay input is neutral below DirectInput only during those frames. START
stays live: it opens the original pause menu and the run aborts with partial
results. The simulation, scripts, AI, audio and rendering keep running through
the unchanged original frame. There is no separate loop, no frozen world and no
custom camera object.

Per viewpoint it records the frame interval (frame start to next frame start),
work time, simulation/render split, and per-frame deltas of the renderer
counters. It then reports:

* `interval_us p50/p95/p99/worst/mean` (nearest-rank percentiles),
  `work_us p50/p95/worst`, `sim/render_mean_us`, and `settle_worst_us` (first-use
  hitches, kept apart from the measured window);
* median meshes/vertices/triangles/material passes, indexed draws/triangles,
  texture binds and state changes;
* a **correctness fingerprint**: FNV-1a over (version, viewpoint, CRC of the
  rendered pose read back from the original camera, and the modal per-frame
  MeshClass submission tuple meshes/vertices/triangles/material passes). It also
  reports `mode=k/120`, the share of frames that matched that tuple, and the
  `pose` CRC;
* validity flags: camera not applied, frame gap, pose changed, counter reset
  (any of these invalidates the result). It also reports long interval and
  active conversation, which do not invalidate.

Output:

* runtime log (`a35-<label>-runtime.log`): `A4 tutorial-bench: armed|start`,
  one line per viewpoint, `summary` per pass (pooled over all measured frames),
  and `complete` or `aborted`;
* `ux0:data/renegade/user/logs/tutorial-bench-<label>-rNN.csv`: one row per pass
  and viewpoint, plus an `ALL` route row;
* `…-rNN-frames.csv`: every raw frame (settle and measured), so the comparison
  tool can pool exact percentiles across passes and recompute the fingerprints.

`rNN` is the first unused run number (bounded to 99), so repeated launches of one
candidate never overwrite each other. Summaries, CSV writes and the optional
capture are done between holds. Their cost lands in the next viewpoint's
unmeasured settle frames.

## Viewpoints (route order, M00 world metres)

| # | Name | Camera → target | Source |
| --- | --- | --- | --- |
| 0 | spawn_course_start | (-57,-43,2.8) → (-50,-20,1.5) | spawn (-58.3,-41.5,0.6), Dev134 physical log |
| 1 | logan_course_overlook | (-40.5,-42,7.5) → (-55,-14,1) | obstacle course bounds (OB_WALL*/CRATES in tut_lm015.w3d) |
| 2 | agt_keycard_yard | (-14.9,34,2.4) → (-11.5,18,4) | `MTU_LOGAN_KEYCARDS` position (-14.9,29.0) |
| 3 | sydney_agt_interior | (-11.9,25.13,-8.33) → (-11.45,20.14,-8.6) | Sydney conversation positions, eye height |
| 4 | gunner_range_lane | (-34,76,2.65) → (-34.56,52.91,1.84) | range lane positions; Mission00.cpp light-tank target |
| 5 | hotwire_vehicle_yard | (8,-48,5) → (-10,-30,1.5) | `MTU_HOTWIRE_*` positions; HMVV create (-10.5,-34.2) |
| 6 | refinery_exterior | (18.9,33,2.2) → (25,14,8) | `MTU_LOGAN_INTRODUCE_REFINERY` (18.9,27.5) |
| 7 | mobius_refinery_interior | (22.97,16.95,-8.35) → (29.63,11.98,-8.3) | Mobius position; refinery MCT radar marker |
| 8 | refinery_tib_dump_east | (51,26,3) → (42.5,16,2.5) | squish-target ground (50.9,25.6); refinery roll door |
| 9 | petrova_power_interior | (-45.61,19.48,-6.36) → (-43.23,25.66,-6.8) | Petrova position; power-plant MCT marker |
| 10 | base_overview_elevated | (0,-50,25) → (-10,20,2) | elevated base overview (worst-case breadth) |

The projection is also fixed: horizontal FOV 75° (`cameras.ini` `[Default]`
profile; the vertical FOV follows the camera aspect exactly as on the original
profile path), and clip planes 0.26/300 (`CCAMERA_NEARZ`/`CCAMERA_FARZ`). This
means first/third-person state cannot change the view. The first-person weapon
view still renders with the camera, so `first_person` is logged and the
comparison tool rejects a mode mismatch.

M00 has **no Tiberium field**. The only Tiberium asset in `M00_Tutorial.mix` is
the refinery's `ref_tib_dump` (strings in `m00_tutorial.lsd/.ldd/.dep`), and no
`tut_lm015.w3d` mesh uses a Tiberium texture. Viewpoint 8 (the refinery's east
dump/road side) stands in for it.

## Evidence (file:line)

* No interactive tutorial benchmark existed. `A31M00BenchmarkRoute`
  (`port/developer/a31_capture_telemetry.cpp:573-705`) drives only the A3.0
  static-world viewer's own orbit camera (`port/platform/vita/a30_vita_runtime.cpp:595,689`),
  not Combat. The interactive `A3.5 perf` line is a rolling 120-frame window over
  whatever the player does (`a31_vita_runtime.cpp` `InteractiveTiming::Percentile`,
  `Log_Timing_Statistics`).
* Camera seam: `CombatManager::Think` updates the original camera in its
  non-host branch before `Post_Think` (`staging/combat/combat.cpp:776-782`). The
  same Think then passes `MainCamera` to `SoundEnvironment->Update`,
  `BackgroundMgrClass::Update` and `WeatherMgrClass::Update` (combat.cpp:808,
  814, 819). `SkyClass::Update` re-centres a 100 m sky on `camera->Get_Position()`
  (`staging/combat/backgroundmgr.cpp:2180` Extent, `3759`). An override placed
  after the simulation would leave the sky, sun dazzle and weather centred on
  the player while the view is up to ~100 m away. The hook therefore sits
  directly after `MainCamera->Update()` (combat.cpp:780).
* Not persistent: the original update rewrites the view plane and clip planes
  every frame (`staging/combat/ccamera.cpp:836`, `882`, `937`, `951/953`). Star
  targeting is computed inside that update from the player camera, before the
  hook.
* Host-model alternative rejected: `Set_Host_Model` activates
  `GameObjManager::Activate_Cinematic_Freeze` (ccamera.cpp:606). That would
  freeze the simulated workload being measured.
* Renderer counters (`mesh/vertex/triangle_submissions`, `material_passes`)
  increment before the static-cache and client-array path decisions
  (`port/renderer/vita/ww3d_vita_renderer.cpp:4953-4961` vs `5043`, `5094`).
  Fingerprints therefore stay comparable across `RVSM1`/`RVVA1`/`RVGS1` A/B runs.
  The chained `geometry_checksum` (`Mix_Checksum`, :2449, :4956) depends on all
  history since `Reset_Statistics` and cannot be isolated per frame without a
  renderer change, hence the modal-tuple fingerprint.
* Viewpoint data come from:
  * the physical Dev134 runtime log (`build/device-evidence/dev134-user-pull-*`,
    conversation-change player positions; not committed);
  * `Mission00.cpp` coordinates (`staging/scripts/Mission00.cpp:124-128` MCT
    markers, `446-784` range targets, `967` HMVV, `999-1034` squish targets);
  * union bounds of the 133 meshes in `tut_lm015.w3d`
    (-110,-109.4,-1.5)…(121.5,119,39.3).

## Changes

| File | Change |
| --- | --- |
| `port/platform/renegade_vita_tutorial_bench.h` (new) | Engine-free controller: viewpoint table, flag parser, nearest-rank percentiles, FNV, modal tuple, readiness, per-frame recording, summaries, log/CSV output, `Session_Guard` |
| `port/compatibility/include/renegade_vita_bench_hooks.h` (new) | C++17 inline hook state shared by loop/Combat/DirectInput |
| `port/compatibility/include/renegade_vita_bench_camera.h` (new) | `Renegade_Vita_Bench_Apply_Camera`: `Look_At` → `CameraClass::Set_Transform`, `Set_View_Plane`, `Set_Clip_Planes`; returns at once unless armed |
| `port/patches/combat-tut1-bench-camera.patch` (new) + `tools/stage_sources.sh` (last combat entry) + `staging/combat/combat.cpp` | include + one guarded call after `MainCamera->Update()` |
| `port/platform/renegade_directinput.cpp` | neutral pad (START kept) and no touch while armed, before route recording |
| `port/platform/vita/a31_vita_runtime.cpp` | configure + guard before the loop; arm/release around `A31_Interactive_Run_Simulation_Frame()`; `End_Frame` after frame timing; optional capture |
| `tools/compare_tutorial_bench.py` (new) | baseline vs candidate from logs or CSVs; pooled exact percentiles; fingerprint integrity check against raw frames; exit 0/1/2 |
| `tools/test_tutorial_bench.py` (new) | 33 pure-Python tests |

## Default and inertness

Default **OFF** (flag absent). With the flag absent:

* `Configure` returns before any state change or log line.
* `Running()`/`Enabled()` are false, so no counters, pose or I/O are touched per
  frame.
* The only residue is one load and branch in `CombatManager::Think`, one load
  and branch in `DirectInput::Read`, and two byte stores of `false` after each
  simulation call.

The hooks are armed only for the duration of one
`A31_Interactive_Run_Simulation_Frame` call and released immediately after it.
Pause menus, loading screens and the frontend can therefore never see a
suppressed pad.

## Hypothesis-ledger entry (for the coordinator to file)

| Field | Value |
| --- | --- |
| ID / switch | TUT-R1-14, `tutorial-bench-v1.flag` `RVTB1` (dev-only, default off) |
| Hypothesis | A fixed M00 viewpoint route through the original camera, with neutral input, gives reproducible per-viewpoint p50/p95/p99/worst plus a render-submission fingerprint. That lets every tutorial optimisation be A/B measured like-for-like. |
| Expected gain | None by itself (measurement infrastructure). Overhead while measuring is estimated at well under 0.01 ms/frame (counter copy, pose read, one `Look_At`). Sorting and I/O happen only in unmeasured settle frames. |
| Risks | A viewpoint may be inside or behind geometry until validated with `RVTB1 C`. Idle nag conversations or dynamic actors lower `mode` share. The elevated overview's PVS sector lookup is not a gameplay position. Vsync quantises intervals. On the first launch after install, FFP shaders compile (`RVPW1`), inflating settle and measured times. |
| Measure on hardware | Same candidate, 2 launches × `RVTB1 3`, vsync on and `RVVS1 0`: between-launch per-viewpoint p50 delta should be within ±2% with identical fingerprints, which establishes the noise floor for the default 3% A/B threshold. |
| Decision | Deferred until the first physical run validates the viewpoints (captures) and the noise floor. |

## Verified vs unverified

Verified (host, no compiler):

* `python3 -m unittest tools.test_tutorial_bench`: 33 tests pass:
  * percentile, mean, FNV and modal-tuple mirrors against independent definitions;
  * flag table;
  * viewpoint bounds and the interior eye-height anchors;
  * CSV header/row field counts extracted from the C++ format strings;
  * C log format → parser round trip;
  * compare-tool verdicts (identical, faster, fingerprint mismatch, invalid,
    tampered summary, camera-mode mismatch);
  * hook placement contracts;
  * `patch -R --dry-run --fuzz=0` proves tracked staging contains exactly the
    new patch.
* `tools/renegade_patch_inventory.py --root .`: registry PASS (578 ordered
  patches, unified-diff validation).
* Adjacent pure-Python contract suites still pass (frontend, loading screen,
  cinematic, flight recorder, stage-sources, runtime log, vis-culling,
  checkpoints and others; 140+ tests).

Unverified:

* Not compiled for ARM or host.
* `--check-staging` reports the receipt `staging/PATCH_INVENTORY.json` stale, as
  expected. It is regenerated by `tools/stage_sources.sh`, which I did not run
  and must not edit.
* Viewpoint visual quality, PVS behaviour at the elevated view, run-to-run noise
  and any frame-time number are all unverified.
* The port-guard sweep (`tools/audit_sweep_port_guards.py`) may list the new
  guarded hunk as unreviewed.

## Hardware run and A/B comparison

1. Install the candidate VPK. Create the flag with exactly `RVTB1 C\n` the first
   time (on a PC: `printf 'RVTB1 C\n' > tutorial-bench-v1.flag`, 8 bytes, LF
   only) in `ux0:data/renegade/user/config/`.
2. Launch, then start the Tutorial from the menu as a fresh start, not a save
   (the log records `source=fresh|save`). After control is given, do not touch
   the controls. Logan's opening lines finish, then after 2–4 quiet seconds
   the camera starts cycling through the 11 views. One pass is 1650 frames
   (about 28–55 s).
3. When `A4 tutorial-bench: complete` is logged (the camera returns to the
   player), exit normally. Pull the runtime log,
   `logs/tutorial-bench-<label>-rNN.csv` and `-frames.csv`, and for `C` the
   `captures/tutorial-bench-rNN-vpXX-*` bundles. Check the screenshots before
   trusting the route.
4. For measurement, set `RVTB1 3\n`. Launch twice per candidate and discard the
   first launch after a fresh install (shader cache). Optionally repeat with
   `vsync-v1.flag` = `RVVS1 0\n` for uncapped sensitivity.
5. Compare: `python3 tools/compare_tutorial_bench.py base-r02.csv cand-r02.csv`
   (or two runtime logs, with `--baseline-run/--candidate-run rNN`).
   * Exit 0 `COMPARABLE`: per-viewpoint and route `p50/p95/p99/worst` deltas are
     like-for-like.
   * Exit 2 `FINGERPRINT-MISMATCH`: rendered content or pose changed (for
     example a LOD change); explain it before using the timings.
   * Exit 1 `INVALID`: aborted, disturbed, mismatched mode/source, or a corrupt
     CSV; rerun.
6. Single-switch A/B within one candidate (for example `RVVA1 0`): toggle only
   that flag between launches. Runs become r01/r02/… of the same label; compare
   those CSVs.

## Shared files touched (conflict risk)

* `port/platform/vita/a31_vita_runtime.cpp`: 4 small hunks (include, sink
  function, pre-loop setup, around the sim call, after frame-profile end).
* `port/platform/renegade_directinput.cpp`: 1 hunk plus include.
* `tools/stage_sources.sh`: appended after the last combat patch.
* `staging/combat/combat.cpp`: two 1–4 line hunks.

No edits to the renderer, `build.sh`, shared reports or `PATCH_INVENTORY.json`.
