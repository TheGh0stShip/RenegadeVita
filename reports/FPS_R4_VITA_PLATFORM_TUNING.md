# FPS round 4: Vita platform tuning (vitaGL sizing, threads, API use)

Static reading of the pinned vitaGL (`build/deps/vitagl-demo/source/source`, 6e7fe40 + port
patches), of the port, and of the dev238 physical counters. **Nothing here was measured on
hardware.**

## Hypothesis
vitaGL/GXM sizing, thread placement or blocking Vita calls cost game-thread time.

## Evidence: vitaGL sizing
- **The `vglInitExtended` arguments.** The call is
  `vglInitExtended(4 MiB, 960, 544, 0x1000000, msaa)`.
  - The first argument is the GL1 **immediate vertex pool**.
  - The fourth argument is the **user RAM reserve kept outside vitaGL's RAM pool**
    (`vgl.c:554-578`). It is not the parameter buffer.
  - The parameter buffer is the GXM default of 16 MiB (`gxm.c:29,382`), allocated in
    CDRAM. dev238 shows CDRAM free drop by 16 MiB at init.
- **Where the immediate pool comes from.** vitaGL reserves it once per frame from that
  frame's circular slice (`gxm.c:582-586`, `vgl.c:124-146`). The 32 MiB circular pool is
  split across 3 buffers, so each slice is 10.67 MiB. Each slice is a separate RAM-pool
  allocation (`vgl.c:360-369`).
- **Immediate pool overflow neither wraps nor waits. It corrupts memory.**
  - Only the Renegade projective path bounds-checks, and it drops the primitive
    (`ffp.c:1962-1971,2564-2570`).
  - Ordinary `glVertex3f` writes past `legacy_pool_end`.
  - The `glEnd` check is compiled out by `SKIP_ERROR_HANDLING` (`ffp.c:2722-2727`).
  - An overrun first overwrites the frame's copied indices, then the neighbouring heap
    block.
- **Circular slice overflow.** Every later transient allocation in that frame becomes a
  heap allocation with a deferred free (`vgl.c:128-135`). Only total out-of-memory reaches
  the stall path: `glFinish` plus up to 4 × `sceKernelDelayThread(1 s)`
  (`utils/gpu_utils.c:156-179`).
- **Per-frame immediate bytes (estimate from counters, not measured as bytes).**
  - dev238 `mesh_unique` was 35.2M over 3,240 frames, about 10.9k indexed-immediate
    vertices per frame.
  - The compact unlit stride is 36 B, or 44 B with 2 UVs. Each projective stage adds 12 B.
  - That gives about 0.4-0.5 MB per frame, plus HUD, sorted geometry and particles. This is
    well under 4 MiB on average. Peaks were never logged.
  - The static mesh cache moves rigid meshes into VBOs, which lowers this further.
- **GXM rings.** These are the SDK defaults: VDM 128 KiB, vertex 2 MiB, fragment 512 KiB,
  USSE 16 KiB (`gxm.c:29-33`). Uniforms go to vitaGL's own 2 MiB circular buffer
  (`utils/gxm_utils.c:26-56`). A full ring blocks the draw call. That is plausible at about
  300 draws per frame, but unproven.
- **Memory placement is already right.**
  - Per-frame CPU-written pools go to uncached RAM first (`gpu_utils.c:91-101`,
    `mem_utils.c:26,469`).
  - Textures and `GL_STATIC_DRAW` VBOs go to VRAM first (`gpu_utils.c:103-113`,
    `buffers.c:393-397`).
  - `vglUseCachedMem` is **rejected**. No dcache clean happens before GPU reads.
- **Speedhacks: all rejected. Each also needs a vitaGL rebuild.**
  - `DRAW` and `SAFER_DRAW` only skip client-array copies. The port's array draws use
    bound VBO/IBO offsets (static mesh cache), which are never copied
    (`ffp.c:1543-1546`, `draw.c:31-33`), and immediate mode is unaffected. There is no
    gain, and any client-array use would become unsafe.
  - `INDICES` skips the per-stream `indexSource` setup (`ffp.c:865-869`) and gives nothing
    for IBO draws.
  - `MATH` turns glOrtho/glFrustum into an overwrite instead of a multiply
    (`matrices.c:170-236`). That changes semantics.
  - `TEXTURES` drops the `last_frame` stamps that deferred texture frees rely on.
  - `SAMPLERS` affects only the custom-shader path, which the port does not use.

## Evidence: threads, clocks and blocking calls
- **Core placement.**
  - The game thread is on core 0 (`a30_main.cpp`).
  - The mixer self-pins to core 1 (`renegade_miles_provider.cpp` `Output_Thread`).
  - The log writer, flight flusher and vitaGL GC (priority 0x10000100) run on core 2.
  - No port worker targets core 0.
- **Unpinned threads, all negligible.**
  - The power callback thread wakes at 1 Hz.
  - The startup-status thread runs only before vitaGL.
  - The Bink audio thread runs only during movies.
  - The GXM display-queue thread is probably on core 0, unverified; the SDK only exposes
    `..._AFFINITY_CPU_1/2` flags (`psp2/gxm.h:56-57`). It runs one short callback per
    flip. Moving it needs a vitaGL patch, because vitaGL hardcodes its init flags
    (`gxm.c:375`). **Deferred**: under 0.1 ms per frame expected.
- **Not used:**
  - The 4th core (`SCE_KERNEL_CPU_MASK_SYSTEM`) is not used.
  - Loading work stays single-threaded, because the original loaders and vitaGL are
    single-owner.
- **Loading catch-up cost.** It waits 3 vblanks per progress change
  (`a31_vita_runtime.cpp:365,1626-1633`). dev238 had 8 changes, about 0.4 s.
- **Clocks.** 444/222/222/166 is requested at boot and re-checked every 120 frames with 4
  getters. No change.
- **No blocking API use found in the per-frame path.**
  - `sceDisplayWaitVblankStart` appears only in bootstrap, debug status and loading.
  - Gameplay-loop `sceKernelDelayThread` calls sit in paused, credits or replication-wait
    branches that `continue` without rendering.
  - Port `sceIo`/`fopen` calls are init or session-entry one-shots.
  - vitaGL FFP shader-cache misses open a file and run a SceShaccCg compile on the game
    thread (`ffp.c:664-705,877-980`). This is a first-run hitch only.

## Change made
- New `port/renderer/vita/ww3d_vita_gxm_tuning.h`:
  - `VitaGLSizing` defaults, equal to the shipped sizes.
  - A strict flag parser.
  - `VitaGLPoolWindow` peak accounting.
- `ww3d_vita_renderer.cpp`:
  - `Read_VitaGL_Sizing` and `Apply_VitaGL_Sizing` call a vitaGL setter only for fields
    the flag names. `vglInitExtended` then takes the immediate pool size and RAM reserve
    from that struct. **With no flag, the call sequence and values are unchanged.**
  - A one-shot `renderer-init vitagl-effective:` line, read back from vitaGL.
  - A one-shot `renderer-init game-thread:` line with priority, affinity and CPU.
  - `Sample_VitaGL_Transient_Pools` runs before each `vglSwapBuffers` (about 10 loads per
    frame). Every 120 frames it logs `vitagl-pools`: immediate peak, average, capacity and
    overruns; circular peak, slice and overruns; and the CPU.
  - vitaGL internals are read through read-only `extern "C"` declarations. Their types are
    checked against the pinned source.
- **Default-on:** telemetry only. **Flag-gated:** all sizing.

## Runtime switch
`ux0:data/renegade/user/config/vitagl-sizing-v1.flag` holds one line: `RVGX1`, then one or
more ` key=value` tokens, then `\n`.

| Key | Size | Range | Default |
| --- | --- | --- | --- |
| `imm` | immediate pool, MiB | 1-16 | 4 |
| `circ` | circular pool, MiB | 16-64 | 32 |
| `bufs` | display buffers | 2-3 | 3 |
| `vdm` | VDM ring, KiB | 128-1024 | 128 |
| `vtx` | vertex ring, KiB | 2048-8192 | 2048 |
| `frag` | fragment ring, KiB | 512-4096 | 512 |
| `usse` | fragment USSE ring, KiB | 16-64 | 16 |
| `pb` | parameter buffer, MiB | 8-64 | 16 |
| `ramres` | RAM reserve, MiB | 16-64 | 16 |

Rules:
- KiB values must be multiples of 4.
- Each key may appear at most once.
- `circ/bufs` must be at least `imm + 1 MiB`.
- Any violation rejects the whole file, logs the rejection and keeps the defaults.

## Risk and invalidation
- **Without the flag:** the only additions are read-only sampling and log lines.
- **With the flag:** only sizes vitaGL allows before `vglInit*` change, and the slice rule
  keeps the immediate pool inside its slice.
- **Memory cost:** each extra 16 MiB of `pb` takes 16 MiB of CDRAM, and each display
  buffer 3 MiB. `vitagl-effective` and `vitaGL pools` show the result.
- **On a vitaGL upgrade:** recheck the externs. The host test pins them.

## Tests
- `python3 -m unittest tools.test_vita_gxm_tuning` passed, 4/4. It covers the parser
  (boundaries, 47 rejects, 200k random mutations, ASan/UBSan), the pool window, the
  defaults against SDK `SCE_GXM_DEFAULT_*`, the init/present wiring order, and the extern
  types against the pinned vitaGL. A scratch mutation run caught 8/8 non-equivalent mutants.
- `tools.test_vita_diagnostic_hotpath` and `tools.test_vita_static_mesh_cache` passed.
  `test_vita_index_preparation` fails, as already listed in HOST_TEST_TRIAGE_2026-10-06.
- ARM TU compile (VitaSDK GCC 15.2, -O3, recorded flags) of
  `port/renderer/vita/ww3d_vita_renderer.cpp`: OK. A run with `-Werror=unused-*` reports
  only pre-existing unused symbols (`Float_Bits`, `Texture_Stage_Index_Valid`, two timing
  counters) and no format errors. Not linked here: the coordinator's full build links it,
  and no new vitaGL symbols are needed (all externs exist in the current `libvitaGL.a`).

## Expected gain (unmeasured)
- **Default:** none. This change is instrumentation, plus detection of silent
  immediate-pool overruns.
- **Flag A/B:** helps only if hardware shows GXM ring or parameter-buffer stalls, or a
  pacing loss.

## Hardware measurement (M13 ambush fixed replay)
1. **Run with no flag.**
   - Record `vitagl-effective` and `game-thread`. Expect affinity 00010000 and cpu=0.
   - Record the `vitagl-pools` series.
   - If `immediate_overruns` is above 0, test `RVGX1 imm=8\n` and consider making it the
     default.
   - If `circular_overruns` is above 0, test `RVGX1 circ=48\n`.
2. **Compare `RVGX1 bufs=2\n` with the default.** Use frame p50/p95/p99, `Vita Swap
   Buffers` p50/p95 and `frame-vblank` missed vblanks.
3. **Compare `RVGX1 vdm=512 vtx=4096 frag=1024 pb=32\n` with the default.** Adopt it only
   if Swap or frame p95 improves beyond noise and VRAM free stays at or above 24 MiB.
