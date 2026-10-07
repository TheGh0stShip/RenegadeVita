# Frame pacing review: vitaGL present path

Status: a code review only. Nothing was built or run, and no hardware was used. All
statements come from reading the source. None of them are measurements.

## Present path as implemented

- Init (`port/renderer/vita/ww3d_vita_renderer.cpp` ~2905-2917): the campaign build calls
  `vglInitExtended(4 MiB, 960, 544, 0x1000000, msaa)`. The demo build calls `vglInit`.
  The port never calls `vglUseTripleBuffering`, `vglSetDisplayBufferCount` or `vglWaitVblankStart`.
  The "buffers=3" in the init breadcrumb is a label only. It matches the vitaGL default
  `gxm_display_buffer_count = 3` (gxm.c:48). The port does not set this value.
- vitaGL defaults: `vsync_interval = 1` (vgl.c:93). `displayQueueMaxPendingCount = buffers-1 = 2`
  (gxm.c:379).
- Per frame (`End_Frame`, ~3095-3106): `RENEGADE_FRAME_PROFILE("Vita Swap Buffers")` wraps one
  `vglSwapBuffers(textEntryActive)` call. The port has no `glFinish` and no `sceGxmFinish` in the
  steady-state loop. vitaGL's own `sceGxmFinish` runs only when the resolution changes.
- Inside `vglSwapBuffers` (gxm.c:740-926), the steps are:
  1. `scene_end()`, which calls `sceGxmEndScene` for the display scene.
  2. An optional common-dialog update.
  3. `sceGxmDisplayQueueAddEntry(back, front, cb)`.
  4. A rotation of the back-buffer index.
  The vsync wait (`sceDisplayWaitVblankStartMulti(1)`) runs in the **display queue callback
  thread** (gxm.c:258-262), not on the game thread. The next frame's `sceGxmBeginScene` runs
  lazily on the first draw. The GPU waits on the sync object, not the CPU.
- Outside the main loop, `sceDisplayWaitVblankStart` is also called in
  `port/platform/vita/a31_vita_runtime.cpp`, at :789 (debug status flush) and :1618 (loading-screen
  catch-up frames). Both calls block the CPU directly, but only during loading or debug screens,
  not during gameplay.

## CPU/GPU overlap

The pipeline is normal GXM triple buffering. The CPU can record frame N+1 while the GPU renders
frame N and frame N-1 waits for vblank. The CPU blocks only in two places:
- `sceGxmDisplayQueueAddEntry`, when 2 flips are already pending. This is back-pressure from the
  display, and therefore from vsync.
- `sceGxmEndScene` or a draw call, when the VDM, vertex or fragment ring buffers or the parameter
  buffer are full. This means the GPU is behind.

The CPU does not wait for the GPU to finish each frame.

## Reading the "Vita Swap Buffers" profile time

The timer measures **EndScene submission plus any display-queue back-pressure**. It is not GPU
execution time.

- **Small (<1 ms) with frame time >16.7 ms**: the game is CPU-bound. Look at the other profile
  scopes.
- **Large, and frame time locks to 16.7/33.3 ms**: the time is mostly a vsync or queue wait. The
  CPU is ahead, so this time is idle headroom, not cost.
- **Large, and frame time is irregular or above 16.7 ms without locking to vblank multiples**:
  the game is probably GPU-bound. The queue is full because the GPU has not released buffers.
- Because the wait sits in a different thread, Swap time cannot tell "waiting for vblank" apart
  from "waiting for the GPU". It only shows that the CPU outran the display pipeline. One
  experiment below separates the two cases.

## Recommended measurable experiments

Use the fixed replay/camera benchmark for each experiment and record median/p95/p99/worst for
frame time and for each scope.

1. **Vsync off flag**: add a build or config flag that calls `vglWaitVblankStart(GL_FALSE)` after
   init.
   - If Swap time collapses and FPS rises above 60, the old cost was vsync wait.
   - If Swap time stays high and FPS stays roughly the same, the game is GPU-bound.
   - Use this for diagnostics only. Tearing is expected.
2. **Buffer count A/B**: call `vglSetDisplayBufferCount(2)` before init and compare it with 3.
   Under double buffering a GPU-bound frame shows a larger Swap time and more 33 ms hitches.
   This confirms how much the third buffer absorbs.
3. **GPU completion timestamp**: in a trace-only build, wrap `sceGxmFinish` directly after
   `vglSwapBuffers`, or add `sceGxmNotification` writes. This gives true GPU frame time, which
   separates GPU cost from queue wait. Do not ship it, because it serialises the pipeline.
4. **Split the scope**: time `scene_end`/EndScene separately from `DisplayQueueAddEntry`. This
   needs a small vitaGL patch, or `-DHAVE_PROFILING`, which already logs `gpu_stall_cnt` around
   the queue add. Large EndScene time points to ring-buffer or parameter-buffer exhaustion.
   Consider the `vglInitExtended` ring sizes or the `0x1000000` parameter buffer. Large queue-add
   time points to vsync or GPU back-pressure.
5. **MSAA A/B** (4x, 2x, none): this tests the fragment cost directly. A GPU-bound result should
   respond to it strongly.
6. **Vblank-phase logging**: log `sceDisplayGetVcount()` at frame start. A steady increment of 1
   means a 60 Hz lock and an increment of 2 means 30 Hz. Jitter shows missed vblanks.

## Observations / risks

- When the text entry is active, `has_commondialog=GL_TRUE` runs `sceCommonDialogUpdate` inside
  Swap. Expect Swap time to rise during IME, and leave it out of benchmarks.
- `vglSetupGarbageCollector` on core 2 keeps deferred frees off the game thread. This is good.
- Loading catch-up frames block on vblank directly. That is acceptable, but loading-time
  measurements include up to `kLoadingProgressCatchupFrames` x 16.7 ms of wait for each
  progress change.
