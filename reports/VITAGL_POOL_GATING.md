# vitaGL pool gating for static-mesh cache and texture prepare floors

Static analysis only (no build, no Vita run). 2026-10-06.

## Current gates
- Static mesh upload: `port/renderer/vita/ww3d_vita_renderer.cpp:2170`
  `vglMemFree(VGL_MEM_ALL) < STATIC_MESH_CACHE_FREE_RESERVE_BYTES (16 MiB, :1830) + total_bytes`.
  Allocation itself is `glBufferData(..., NULL, GL_STATIC_DRAW)` at :2194 (VBO) and :2201 (IBO).
- Texture prepare: `port/platform/vita/a31_vita_runtime.cpp:1947`
  `memory.all_free < free_memory_floor (24 MiB, :1938)`; `all_free` is
  `vglMemFree(VGL_MEM_ALL)` from `ww3d_vita_renderer.cpp:4540`.
- RAM/VRAM/BUDGET pools are already queried separately (`ww3d_vita_renderer.cpp:4533-4540`,
  logged at :1732-1741), so per-pool gating needs no new plumbing.

## Which pool these allocations use
- The repo never calls `vglUseVram`, `vglUseCachedMem` or `vglUseVramForUSSE`
  (grep over `port/`), so vitaGL defaults apply. Init: `vglInitExtended(4 MiB, 960, 544,
  0x1000000, msaa)` at `ww3d_vita_renderer.cpp:2851`; RAM pool is the user-memory remainder
  after the 192 MiB newlib heap (`port/platform/vita/a30_main.cpp:25-29`).
- Pool enum per installed header `/usr/local/vitasdk/arm-vita-eabi/include/vitaGL.h:1118-1123`:
  VRAM=CDRAM, RAM=USER_RW, SLOW=PHYCONT, BUDGET=CDLG, EXTERNAL=newlib, ALL=sum.
- Upstream vitaGL default (from vitaGL source knowledge; vitaGL source is NOT vendored here,
  so this is unverified against the exact linked `libvitaGL.a`): texture storage and
  `glBufferData` storage request VRAM (CDRAM) first while `use_vram` is true (default), and the
  allocator falls back to RAM (then other pools) when VRAM is exhausted. So static mesh
  buffers and textures land in CDRAM first and spill into the USER_RW RAM pool.

## Why VGL_MEM_ALL is wrong as a floor
ALL sums CDRAM + RAM (+ PHYCONT/BUDGET where present). Because allocations spill, ALL is a
reasonable "can this one allocation succeed" estimate, but it hides the case where CDRAM is
already gone and RAM is nearly full: ALL can still read above the floor via residual
CDRAM/BUDGET fragments that cannot hold a large contiguous block, and the RAM pool is also
what vitaGL's own non-spillable runtime allocations (per-frame vertex/uniform staging,
dynamic textures, shader patcher growth) consume. Exhausting RAM there is the failure mode,
not exhausting ALL.

## Recommendation
Replace the ALL checks with explicit per-pool checks:
1. Require `vglMemFree(VGL_MEM_RAM) >= RAM_RESERVE` always (keep 16 MiB for mesh, 24 MiB for
   texture prepare) - this protects the pool vitaGL needs for runtime allocations.
2. Admit the allocation if `vglMemFree(VGL_MEM_VRAM) >= bytes` (it will land in CDRAM) or
   `vglMemFree(VGL_MEM_RAM) >= RAM_RESERVE + bytes` (it will spill into RAM).
   Do not count SLOW/BUDGET toward the floor.
3. Log which branch admitted/rejected using the existing BackendMemoryStatistics fields.
Do not switch to VRAM-only gating: textures/buffers legitimately spill to RAM and VRAM-only
would reject loads that succeed today.

Validation needed before adopting: confirm the linked vitaGL revision's allocation order
(grep its `gpu_alloc_mapped`/`vgl_malloc` callers or log per-pool deltas across one
`glBufferData` and one texture upload on hardware/Vita3K).
