# FPS round 4 — INTERNAL_RESOLUTION

Status: source, host tests and ARM TU compiles only. Nothing measured on hardware or Vita3K. Default OFF: with no flag
the build behaves as before.

## Hypothesis
Fewer pixels means less SGX543MP4+ fill, blend, texture and MSAA-resolve work. That shortens frames only when the GPU
is the bottleneck. On dev238 the 41 ms render stage was mostly CPU time in the mesh boundary (24-29 ms), so any gain
depends on how GPU-bound frames are after the A3.6 CPU work.

## Approaches evaluated
**(A) Hardware scan-out scaling. Implemented.**
- vitaGL sizes the display buffers from `vglInitExtended(pool, w, h, ...)`
  (`build/deps/vitagl-demo/source/source/vgl.c:210-259`).
- `display_queue_callback` passes `DISPLAY_WIDTH/HEIGHT/STRIDE` to `sceDisplaySetFrameBuf` (`gxm.c:236-258`). The
  display controller then scales 720x408, 640x368 or 480x272 to the panel at no GPU cost.
- Runtime changes use `vglSwapResolution` (`vgl.c:583-597`, `vitaGL.h:1286`). Inside the next `vglSwapBuffers` it runs
  `sceGxmFinish`, recreates the render target and reallocates the colour surfaces (`gxm.c:928-946`).
- It keeps the depth/stencil buffer from init (`gxm.c:478-523`), so auto mode starts at 960x544 and that buffer covers
  every smaller level.

**(B) 3D-only FBO plus a bilinear blit, with the HUD at native resolution. Not implemented.**
- There is no platform-boundary point between world and HUD: the original Commando/Combat render runs scene passes,
  then Render2D/HUD, through the same WW3D/DX8 calls. Splitting them needs a staging patch in the original render loop
  or a heuristic in the DX8 boundary.
- Projector passes restore the "default" target by binding FBO 0 (`Restore_Default_Render_Target`). During a world FBO
  pass that would have to mean the world FBO, and the 1d3c105 clip-Y/front-face flip would have to be skipped.
- B costs an extra GXM scene and a fullscreen blit every frame. MSAA on the FBO colour path has not been audited
  (render targets inherit the global `msaa_mode`, `gxm.c:150-158`).
- B needs wide edits in the two hottest shared files.

A has one mapping point, no extra GPU pass and no change to game-loop ownership. B stays the long-term option if
hardware shows the lower-res HUD is unacceptable.

## Change made
**New `port/renderer/vita/internal_resolution.h`** (platform-free, host-tested):
- flag grammar and the level table: 100 = 960x544, 75 = 720x408, 67 = 640x368, 50 = 480x272 (the sizes
  `sceDisplaySetFrameBuf` accepts)
- `Scale_Edge` (floor leading edge, ceil trailing edge)
- in-place nearest-neighbour capture expansion
- the dynamic `Controller`

**`ww3d_vita_renderer.cpp`**
- Reads `ux0:data/renegade/user/config/internal-resolution-v1.flag` the same way as `msaa-v1.flag`. The file must
  contain exactly `RVIR1 100|75|67|50|auto` plus `\n`.
- Logs an `internal-resolution` init breadcrumb (mode, source, effective/physical/logical size). The `display request`
  breadcrumb now shows the physical size.
- `vglInitExtended` gets the physical size.
- `Build_Native_Viewport` scales the final 960x544 presentation-space edges into the physical buffer. The init and
  reactivation full-target viewports use the physical size.
- `Capture_Resolved_Frame_RGBA` reads the physical buffer and expands it to 960x544, so capture consumers are
  unchanged.
- New accessor `Get_Physical_Display_Size`.
- Auto mode: `Update_Internal_Resolution_After_Present()` runs after `vglSwapBuffers` in `End_Frame`. It:
  1. commits a pending size on the swap that applied it (viewport-cache invalidation plus a full `glViewport`), so no
     frame mixes sizes;
  2. records the present-to-present interval;
  3. evaluates on the shared `frames % 120` checkpoint;
  4. calls `vglSwapResolution` when the level changes. It logs every change, plus a status line every 1200 frames.

**`a4_binkmovie_boundary.cpp`:** the movie viewport now covers the physical buffer. The glOrtho layout stays 960x544.

**Unchanged:** the original Render2D/HUD/camera coordinates (the logical device is still 960x544), touch mapping
(panel space), offscreen render targets, the M00 demo path, `staging/` and vitaGL (no new patch).

## Controller (anti-thrash)
- Input: p50/p95 of 120 present-to-present intervals.
- **Down** one level when p50 > 34.0 ms.
- **Up** when p50 <= 25.0 ms and p95 <= 33.4 ms, and the level has held for 3 evaluations.
- **Hold** between the two bands.
- Stall windows (p50 > 200 ms, i.e. loading) are never judged.
- A down step that does not cut p50 by at least 5% (CPU-bound) is reverted. An up step that falls back into the down
  band is reverted. Each revert locks that direction for 4, then 8, and so on up to 256 evaluations (30,720 frames).
- No sampling or resizing while the IME dialog is active. Partial windows are discarded.

## Risk and invalidation argument
- **100% is bit-identical.** `Scale_Edge(e, 960, 960) == e`. A host test checks the production function against the
  pre-change code over 240k random viewports. The flag is read only at init, and the controller runs only in `auto`.
- **Visual trade-off:** the HUD and FreeType text also render at the lower size and are upscaled by the display, so
  they look softer and glyphs may alias. Aspect is preserved: logical-to-physical-to-panel is identity, with slight
  anisotropy at 640x368.
- **Auto resize:** vitaGL frees and reallocates the display buffers right after queuing a frame. Expect a possible
  ~1-refresh black or stale flash, a `sceGxmFinish` hitch and VRAM reallocation (fragmentation risk) per change. The
  rate limits above bound the number of changes.
- **Hardware-unverified for this title:**
  - `sceDisplaySetFrameBuf` acceptance of the three smaller sizes (other vitaGL ports use them);
  - `sceCommonDialogUpdate` (the Direct-IP IME) on a smaller buffer in the fixed modes.
- **Capture:** right after an auto resize, a capture may read a zeroed buffer.
- **Odd viewport widths:** vitaGL truncates them (`width >> 1`). This already happened; lower resolutions make it more
  frequent, but the error stays at most 1 px.

## Tests run (host, all pass)
- `python3 -m unittest tools.test_vita_internal_resolution` (new; ASan/UBSan, `-Werror`). It covers:
  - the flag grammar (14 cases)
  - production `Build_Native_Viewport` identical to the pre-change reference at 100%
  - all scaled levels: bounds, coverage, no gaps in split views, and acceptance independent of scan-out size
  - capture expansion at every level
  - controller models:
    - GPU-bound: settles at 75%, 1 change
    - heavy GPU: 50% for 97% of the time
    - CPU-bound: 18 changes in 1,000 evaluations, 99.1% at 100%
    - stall windows: 0 changes
    - an adversarial alternating signal: 21 changes in 1,000 evaluations
  - production wiring order
- `tools.test_frame_capture_source`: updated harness with a reduced-buffer expansion case.
  `tools.test_vita_touch_presentation`: unchanged, passes.
- All 21 host tests that reference the touched files were run with `upstream/` symlinked. The same 7 fail identically
  on unmodified base 95c4976 (git archive), so they are not regressions: projective_coordinates, index_preparation,
  mesh_batch, sampler_cache, static_mesh_equivalence, bink_scheduler and skin_submission_contract.

## ARM TU compiles
- `port/renderer/vita/ww3d_vita_renderer.cpp`: OK (final version, `-Werror=format`). Adding `-Werror=unused-*` trips
  only existing unused symbols (`Float_Bits`, `Texture_Stage_Index_Valid`, `g_*_timing_sequence`), not this change.
- `port/platform/a4_binkmovie_boundary.cpp`: OK.

## Expected gain (UNMEASURED estimate)
| Level | Pixels (share of native) | Fill saved |
|---|---|---|
| 75% | 293,760 (56.25%) | ~44% |
| 67% | 235,520 (45.1%) | ~55% |
| 50% | 130,560 (25%) | ~75% |

- The saving applies to per-pixel and per-sample work (overdraw, particles, MSAA 2x resolve). Vertex and CPU work stay
  the same.
- Fixed-mode VRAM saved: about 2.2 MB at 75% (depth/stencil only; the colour buffers still round to 2 MB each), and
  about 5.8-6.8 MB at 67% and 50%. Auto mode saves no VRAM.
- Frame-time gain is 0 when CPU-bound, and at most the GPU share of the frame when GPU-bound.
- 75% with no MSAA may beat 100% with MSAA 2x; this also needs measuring.

## Hardware measurement to take
1. On M13 (ambush) and the M01 beach, with a fixed camera path, test four configurations: no flag, `RVIR1 75`,
   `RVIR1 50`, and `RVIR1 75` with `RVMSAA1 0`. For each, compare p50/p95/p99 of the `Vita Swap Buffers` frame-profile scope
   (the GPU wait) and of the total frame, plus the `frame-vblank` missed vblanks. If the swap-wait p50 is near 0 at
   native, resolution scaling cannot help.
2. Check the init breadcrumb, HUD/text/Bink placement, menu touch, a Direct-IP IME entry at 75%, and loading-screen
   capture.
3. Run a `RVIR1 auto` soak of at least 15 minutes. Count `internal-resolution decision=` lines, watch for a blink at
   each change, and record VRAM before and after.
