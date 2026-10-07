# Tutorial round 1: FRAME_PACING (RVFR1)

Status: source and pure-Python tests only. Nothing was compiled, run in Vita3K or run on
hardware. Every gain below is an unmeasured hypothesis. Default OFF: with no flag file the
present path is unchanged. The new code returns on its first branch.

Base: `tutorial-r1/base` 45c6cf5 (main + FPS round 4 / dev240).

## Problem

With vsync on and the tutorial running between 30 and 60 fps, each frame is shown for one
or two vblanks in an irregular pattern (16.7/33.3 ms). That irregular pattern is judder.
With `vsync-v1.flag` `RVVS1 0` there is no vblank wait, so the image tears. Neither is an
acceptable "Balanced" profile (v3.7: p95 <= 33.33 ms, `PROGRAM_CHARTER.md:148`).

## Findings (file:line evidence)

- **vitaGL vsync is a single global.** `uint32_t vsync_interval = 1` (`vgl.c:93`).
  - `vglWaitVblankStart` can only set it to 0 or 1 (`vgl.c:600-601`).
  - `eglSwapInterval(display, n)` sets any `n` (`egl.c:287-289`). It is declared in `vitaGL.h:1065`, and `vitaGL.h:1306`
    names it as the fine-grained control.
  - `egl.c` is compiled into the pinned archive by the Makefile wildcard (`Makefile:2-4`). The symbol name appears in
    `build/deps/vitagl-demo/libvitaGL.a`. No vitaGL patch is needed.
  - Paths are relative to `build/deps/vitagl-demo/source/source/` (pinned 6e7fe40).
- **The interval is applied on the display-queue thread, per flip.** `display_queue_callback` (`gxm.c:236-263`) does
  `sceDisplaySetFrameBuf(..., NEXTFRAME)` and then `sceDisplayWaitVblankStartMulti(vsync_interval)`.
  - The queue does not start the next entry until that callback returns. So `n = 2` shows every frame for at least
    two vblanks, which is a 30 Hz lock.
  - The value is read at every callback. A runtime change also applies to frames that are already queued.
- **The CPU blocks only on back-pressure.** `displayQueueMaxPendingCount = buffers - 1 = 2` (`gxm.c:379`). The block
  happens in `sceGxmDisplayQueueAddEntry` inside `vglSwapBuffers` (`gxm.c:916`). See also `reports/FRAME_PACING_REVIEW.md`.
- **Current port behaviour.** All references below are to `port/renderer/vita/ww3d_vita_renderer.cpp`.
  - `Read_Vsync_Enabled` (:2687) selects interval 1 or 0 once, at init (:4018).
  - `End_Frame` (:4205) calls `vglSwapBuffers` once per presented frame.
  - The `frame-vblank` log counts `missed_vblanks` on the game thread.
  - No code chooses an interval of 2.
- **Simulation timing.** `TimeManager::Update_Frame_Time` (`staging/combat/timemgr.cpp:165-176`) reads real
  milliseconds (`TIMEGETTIME`, :144) every frame and caps the step at `TICKS_PER_SECOND / SLOWEST_FPS` (5 fps, :176).
  - A 30 Hz lock only produces steadier ~33 ms steps. This uses the same variable-timestep path as today.
  - Nothing in this change writes simulation time.
- **Loading presents in bursts.** `Render_Original_Progress` presents once, then 3 catch-up frames with a
  `sceDisplayWaitVblankStart` between them (`port/platform/vita/a31_vita_runtime.cpp:1641-1646`), then goes back to
  loading.
  - Holding those frames for 2 vblanks would add queue waits to loading time. Pacing therefore releases during stalls.
- **The IME draws inside the swap.** `vglSwapBuffers(has_commondialog)` runs `sceCommonDialogUpdate` (`gxm.c:800-813`).
  Pacing is suspended while `RenegadeVitaTextEntry::Active()`, the same rule RVIR1 uses.
- **Pre-existing issue (not fixed, not compiled).** `Read_Vsync_Enabled` is defined inside
  `#if defined(__vita__) && !RENEGADE_VITA_M00_DEMO` (:2493-3481), but it is called without a demo guard at :4018.
  An `-DRENEGADE_VITA_M00_DEMO=ON` build therefore looks like it no longer compiles since 5b25988.
  - The new RVFR1 calls are guarded with `#if !RENEGADE_VITA_M00_DEMO`, like RVIR1, so they add nothing to that issue.

## Why swap interval 2, not a CPU vblank wait

The alternative is to keep interval 1 and make the game thread wait until an even vblank before starting each frame.
With frame costs that straddle 16.7 ms, that still judders:

- A 15 ms frame started at V0 is shown at V1.
- The next frame starts at V2, costs 18 ms, and is shown at V4.
- The display intervals are then 50 ms and 16.7 ms.

Only a display-side minimum hold gives a guaranteed 33.3 ms cadence, and that is exactly what
`sceDisplayWaitVblankStartMulti(2)` in the display callback provides. A CPU-side throttle might still be worth adding
later to reduce queue latency (see the risks). It is not part of this change.

## Change

**New `port/renderer/vita/frame_pacing.h`.** It is platform-free: only `stddef.h`, `stdint.h` and `string.h`. It holds:

- The flag grammar. The file must contain exactly `RVFR1 off\n`, `RVFR1 30\n` or `RVFR1 auto\n`. Anything else is
  rejected and logged.
- `Cadence`: a histogram of the vblank delta between consecutive present returns (0/1/2/3+), plus a count of
  consecutive-delta changes. That change count is the judder proxy.
- `Controller`: chooses the swap interval. Constants:

  | Constant | Value |
  |---|---|
  | `WINDOW` | 60 |
  | `DOWN_P95_US` | 17500 |
  | `UP_BUSY_P95_US` | 13000 |
  | `UP_DWELL` | 3 |
  | `PROBATION_WINDOWS` | 3 |
  | `STALL_US` | 200000 |
  | `ARM_FRAMES` | 60 |
  | `BACKOFF_INITIAL` | 4 |
  | `BACKOFF_MAX` | 256 |

  The modes:
  - **off**: the controller never changes the interval. It always reports interval 1.
  - **lock30**: interval 2 whenever armed.
  - **adaptive**:
    - Starts at 60.
    - At 60: if the p95 of present-to-present time over a full window is above 17.5 ms, drop to 30. 17.5 ms is
      16.7 ms plus margin for measurement jitter. 3 slow frames out of 60 are enough.
    - At 30: present intervals are pinned by vsync, so they show no headroom. Instead the controller judges *busy*
      time, which is the interval minus the time inside `vglSwapBuffers`. After `UP_DWELL` consecutive windows with
      busy p95 <= 13 ms, it probes 60.
    - If any of the first 3 windows after a probe misses 60, the probe is reverted and up steps are locked out for
      4, 8 ... up to 256 windows. Busy time cannot see GPU cost, which is why probes can fail.
    - A drop after probation is an ordinary down and is not locked out.
  - **Stalls and the IME (lock30 and adaptive).** A present gap > 200 ms (loading or level transitions), or an IME
    frame, suspends pacing: interval 1, window dropped, headroom cleared. 60 consecutive steady presents re-arm it, and
    the adaptive target is kept.

**`tools/frame_pacing_model.py`.** A **line-for-line Python mirror** of the header: same names, constants and
statement order. The C++ header is the production policy. The Python file exists so the policy can be tested without a
compiler. Change both together.

**`port/renderer/vita/ww3d_vita_renderer.cpp`.** One new block (:2704-2829) and three call sites. All call sites are
guarded with `#if !RENEGADE_VITA_M00_DEMO`.

- **`Read_Frame_Pacing_Mode(vsync_enabled)`.**
  - Runs right after the existing vsync choice in `Initialize` (:4024).
  - Reads `ux0:data/renegade/user/config/frame-pacing-v1.flag`.
  - Logs `renderer-init frame-pacing: version=1 mode=... enabled=... vsync=... vsync_conflict=...` and the
    thresholds.
  - `RVVS1 0` (vsync off) forces pacing off and logs `vsync_conflict=1`.
- **`Frame_Pacing_Before_Present()` / `Frame_Pacing_After_Present()`.**
  - Placed around the existing `vglSwapBuffers` profile scope (:4215, :4227), before
    `Update_Internal_Resolution_After_Present`.
  - They time the swap, feed the controller, and call `eglSwapInterval(NULL, n)` only when the mode is not off and the
    wanted interval differs from the one last applied.
- **Logging.**
  - A `frame-pacing` line for each interval transition: the first 32, then every 32nd. Fields: event, from->to, p95
    interval, p95 busy, headroom, up_lock, count.
  - A `frame-pacing-cadence` line every 1200 judged presents: vblanks0/1/2/3plus, cadence_changes, transitions,
    suspended frames.
  - `off` mode logs the cadence only, so A/B runs share one metric.
- **Comment fix.** The comment on the read-only vitaGL externs now says that `vsync_interval` changes only through
  `eglSwapInterval`.

**Not touched:** vitaGL and its patches, `staging/` (no patch needed), `a31_vita_runtime.cpp`, `tools/build.sh`,
CMake, TimeManager, and the shared reports.

## Flag and default

| File | Content | Effect |
|---|---|---|
| (none) | — | **Default.** Current behaviour, bit-identical presentation; pacing code returns immediately. |
| `frame-pacing-v1.flag` | `RVFR1 off\n` | Current presentation; logs cadence histogram for A/B. |
| `frame-pacing-v1.flag` | `RVFR1 30\n` | Locked 30 Hz presentation (swap interval 2) outside loading/IME. |
| `frame-pacing-v1.flag` | `RVFR1 auto\n` | Adaptive 60/30 with hysteresis. |

**Default-off justification.** Without the file:

- `g_frame_pacing_enabled` is false.
- `Before`/`After` each cost one well-predicted branch.
- No timer, vcount or `eglSwapInterval` call is made.
- No log line is added except one init breadcrumb.

## Hypothesis ledger entry

- **Hypothesis.** In tutorial scenes that run between 30 and 60 fps, `RVFR1 30` and `auto` replace the irregular
  16.7/33.3 ms display cadence with a steady 33.3 ms one.
  - Expected result: `frame-pacing-cadence` `vblanks2` near 100% and `cadence_changes` near 0, instead of a 1/2 mix with
    many changes.
  - In scenes that hold 60, `auto` stays at interval 1.
  - Below 30 fps, neither mode helps or hurts much: frames already take 2-3 vblanks.
- **Risk.**
  - **Input latency.** At interval 2 with a CPU faster than 30 fps, the display queue can hold 2 frames. Latency then
    rises from roughly frame + <=16.7 ms to roughly frame + 2 x 33.3 ms. In a 40 fps scene that is about +30-40 ms.
    It is not measured. The A/B is `vitagl-sizing-v1.flag` with 2 display buffers.
  - **Halved motion rate** in scenes that ran at 50-59 fps. This is deliberate. The 17.5 ms p95 threshold locks once 5%
    of frames miss.
  - **Failed probes in GPU-bound scenes.** The worst case is about 1 s of judder per probe. Probes are logarithmically
    bounded: 9 failed probes in 1000 windows in the model.
  - **Interaction with RVIR1 `auto`.** Its up step needs present p50 <= 25 ms, which cannot happen at a 30 lock. Do not
    combine RVIR1 auto with RVFR1 30/auto when judging either.
  - **Existing telemetry under pacing:**
    - The `frame-vblank` `missed_vblanks` counter rises by design (about 1 per frame at 30).
    - The RVFP1 "Vita Swap Buffers" scope grows by the vsync hold. That time is idle headroom, not cost.
  - **v3.7 gate.** Under a lock, CPU-measured frame p95 sits at about 33.3-33.6 ms because of jitter. Judge the gate
    on cadence, or with a jitter tolerance.
- **Estimated gain.** No FPS gain. This is a perceived smoothness and frame-time variance change. Expected: frame-time
  p95-p50 spread drops from about 16.7 ms to under 1 ms in the 30-60 band. Unmeasured.
- **How to measure on the tutorial route.** Use the same route for each run: Logan, Sydney, the gunner range, Mobius,
  the HMVV, then the base buildings, from a fixed save or recording.
  - Compare the RVFP1 frame p50/p95/p99/worst.
  - Compare `frame-pacing-cadence` (vblanks1/2/3plus, cadence_changes) and the count of `frame-pacing` transitions.
  - Note subjective judder and input feel at the gunner range (fast camera pans) and in the HMVV.

## Verified vs unverified

**Verified.** All on the host, pure Python, with no compiler invoked.

- `python3 -m unittest tools.test_vita_frame_pacing` passes: 30 tests.
  - **Flag grammar:** 3 accepted forms and 14 rejected ones.
  - **Cadence histogram and change counting.**
  - **Controller traces:**
    - off never changes the interval;
    - lock30 arms after 60 frames and holds;
    - a stall releases and re-arms;
    - loading bursts never arm;
    - the IME suspends;
    - fast content stays at 60, with 0 transitions;
    - 45 fps content locks once, on the first window;
    - content that gets lighter returns to 60 after the dwell;
    - the hold band does not oscillate;
    - in a GPU-bound case where busy time looks like headroom: 9 failed probes, 19 transitions in 1000 windows, 98.9%
      at 30;
    - adversarial alternation is bounded;
    - jitter of +-0.8 ms plus 2 hitches per window does not lock, while 3 hitches do;
    - the exact threshold boundaries;
    - the backoff sequence is 4, 8, ... 256;
    - a down after probation is not locked out.
  - **C++/Python parity** (parses the header):
    - the constants, mode values, flag table, and decision enum and names are equal;
    - per method (`Reset`, `Interval`, `Record_Frame`, `P95`, `Lock_Up`, `Decide`, `Cadence::Record`/`Break`), the
      token multisets are equal, as is the ordered sequence of state mutations and decision results;
    - mutation checks showed that swapping two statements, dropping a reset, or swapping two decision returns all fail
      the test.
  - **Renderer wiring:**
    - the flag is read after `vglWaitVblankStart`;
    - Before precedes the swap, which precedes After, which precedes IR;
    - the first statement is `if (!g_frame_pacing_enabled) return;`;
    - there is exactly one `eglSwapInterval` call, behind `mode != MODE_OFF`;
    - the glue has no TimeManager, delay or vblank-wait calls;
    - logging is rate-limited.
- **Existing pure static tests still pass:**
  - `test_cinematic_presentation_contract`
  - `test_vita_indexed_state_contract`
  - `test_vita_texture_surface_contract`
  - `test_vita_texture_provenance_contract`
  - `test_vita_skin_submission_contract`
  - `test_vita_loading_screen_contract`
  - `test_vita_internal_resolution` `test_production_wiring`
  - the 3 static methods of `test_vita_gxm_tuning`

**Unverified:**

- C++ compilation. The header and glue were written to match the surrounding code (the `internal_resolution.h`
  patterns and existing format conventions), but no ARM or host compiler was run.
- On hardware:
  - whether `sceDisplayWaitVblankStartMulti(2)` counts from the call or from the previous wait (either gives at least
    2 vblanks per frame);
  - the real busy-time distribution at 30;
  - the threshold suitability;
  - the latency impact;
  - Vita3K behaviour.

## Hardware A/B steps (one candidate build; flags only, no rebuild)

1. **Baseline.** Write `RVFR1 off\n` to `ux0:data/renegade/user/config/frame-pacing-v1.flag` (no `RVIR1 auto`, vsync
   default). Run the tutorial route, about 3-5 min. Collect the log: `frame-pacing-cadence`, the RVFP1 frame
   percentiles, `frame-vblank`.
2. **Lock.** Change the flag to `RVFR1 30\n` and repeat the same route. Expect `renderer-init frame-pacing: mode=lock30`,
   then an `event=arm interval=1->2` line after each load, and `event=suspend` at each loading screen.
3. **Adaptive.** Change the flag to `RVFR1 auto\n` and repeat. Count `down`/`up`/`revert-up` events and note where they
   happen on the route.
4. **Optional latency check.** Repeat step 2 with `vitagl-sizing-v1.flag` set to 2 display buffers. Compare input feel,
   and Swap time in the RVFP1 scopes.
5. **Report back:**
   - per run: vblanks1/2/3plus, cadence_changes, frame p50/p95/p99/worst, transitions;
   - subjective judder and latency;
   - any IME (Direct-IP text entry) or loading-screen regressions.

   Delete the flag file to return to default behaviour.
