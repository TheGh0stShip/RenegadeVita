# A2.2 installed vitaGL / shader-stack API audit

Date: 2026-08-07

Scope: read-only inspection of the VitaSDK installation used by A2.2, its
package recipes, installed headers/static archives, matching upstream source,
official samples, symbols, and ARM disassembly. No production source was
changed as part of this audit.

## Determination

The original A2.2 renderer-init failure is a caller-side interpretation error,
not evidence that `vglInit` failed:

```cpp
if (vglInit(4 * 1024 * 1024) == GL_FALSE) {
    return false;
}
```

In the installed vitaGL revision, the return from every `vglInit*` entry point
is a **resolution-fallback flag**, not a success/error flag:

- `GL_FALSE` means the requested display resolution was accepted unchanged.
- `GL_TRUE` means vitaGL replaced an invalid request with the maximum display
  resolution.
- At the normal Vita resolution requested by `vglInit`, 960 x 544, a completed
  initialization normally returns `GL_FALSE` (`0`).

`vglInitWithCustomSizes` sets its internal `vgl_inited` flag and then returns
`res_fallback`. The upstream commit that changed these functions from `void`
to `GLboolean` is
[`c7a3e1a`](https://github.com/Rinnegatamante/vitaGL/commit/c7a3e1a66334e1be8560088ed1fd264a1de1473f),
whose stated purpose is “Added fallback to 960x544 res if requested resolution
is invalid.” The diff creates `res_fallback`, returns it, and contains no
success result.

The physical symptom follows directly:

1. `vglInit` completes and returns `GL_FALSE` because no resolution fallback
   occurred.
2. A2.2 treats that value as failure and never reaches its first render/clear.
3. vitaGL's asynchronous splash thread continues presenting its animated logo.
4. The application remains alive while no WW3D submission occurs.

The minimal correction is to record the raw return as
`resolution_fallback`, never as success/failure, continue initialization, then
issue a scene-producing operation before the first swap:

```cpp
const GLboolean resolution_fallback = vglInit(4 * 1024 * 1024);
// Log resolution_fallback; do not fail when it is GL_FALSE.

glClearColor(r, g, b, a);
glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
vglSwapBuffers(GL_FALSE);
```

The `glClear` is significant: it enters vitaGL's `scene_reset()`, which asks
the splash thread to fade out and joins it. Calling `vglSwapBuffers` alone
while the splash is active does not end it; that function explicitly returns
early in this state.

## Installed component identity

The VitaSDK package list is a file manifest and does not preserve source
revision metadata, so component identity was established from all of the
following:

- package recipes under the current `vitasdk/packages` tree;
- byte comparison of installed headers with tagged/committed upstream source;
- library strings and global symbols;
- a reproduction build with the package recipe flags;
- extraction and comparison of every static-archive object after applying the
  same stripping step.

The installed `libvitaGL.a` contains the splash version text `#6e7fe40`.
Rebuilding commit `6e7fe40292e8f1d10f9a94ff2cd2f4fb1ba452a5` with the package command
`make NO_DEBUG=1` reproduced the installed header and all 30 library objects
byte-for-byte after stripping debug sections. Consequently, behavioral source
analysis in this report is for the exact linked build, not merely a nearby
upstream revision.

| Component | Installed/package identity | Exact upstream source | Installed SHA-256 |
|---|---|---|---|
| vitaGL header | `/usr/local/vitasdk/arm-vita-eabi/include/vitaGL.h` | [`6e7fe402`](https://github.com/Rinnegatamante/vitaGL/tree/6e7fe40292e8f1d10f9a94ff2cd2f4fb1ba452a5) | `ba68004be9faf49fa4b0526ecbcdf26c3b4b8d001f85e119ce35db26a3f70e3a` |
| vitaGL library | `/usr/local/vitasdk/arm-vita-eabi/lib/libvitaGL.a` | same commit; package `pkgver=9999`, `make NO_DEBUG=1` | `bcc414e745a1f29940f7c33418f268c4cd78d0388b7a0da0f036b72355597b69` |
| vitaShaRK header | `/usr/local/vitasdk/arm-vita-eabi/include/vitashark.h` | tag `v.1.5`, commit [`5d99fe81`](https://github.com/Rinnegatamante/vitaShaRK/tree/5d99fe81a4a384c5e4e7a8cba2d851df8dbda5da) | `b746269bf5c22a8fd59d9c2cf8aba482e40a6e7c838ec50f3c809d94bdb620d8` |
| vitaShaRK library | `/usr/local/vitasdk/arm-vita-eabi/lib/libvitashark.a` | same tag/commit | `7b0c4a7aaa3e5e50a5b18083cccf2ce7b98a993380bd3ac1739f863368dd32b6` |
| SceShaccCgExt header | `/usr/local/vitasdk/arm-vita-eabi/include/shacccg_ext.h` | tag `v1.0.1`, commit [`10219236`](https://github.com/bythos14/SceShaccCgExt/tree/102192366c25fe7b8fec073d665494b6172605c3) | `ab9b5fbf06b8c023e846e6e47deef9b7e7d1642e7b1a3e37e2c49602d7884a92` |
| SceShaccCgExt library | `/usr/local/vitasdk/arm-vita-eabi/lib/libSceShaccCgExt.a` | same tag/commit | `dec1d2e58470de4b6cbed8871d173c43e64c45b7ba416ca7651792da4258c211` |

The vitaGL package has declared dependencies on `libmathneon`, `vitaShaRK`,
`taihen`, and `SceShaccCgExt`. `NO_DEBUG=1` defines
`SKIP_ERROR_HANDLING`; it does **not** define `SKIP_SPLASHSCREEN`. No other
optional package switches are set, so the linked archive includes the splash,
runtime shader compiler path, multi-threaded garbage collector, fixed-function
pipeline, and default circular pool. Optional general GLSL shader-cache and
scratch-memory builds are not enabled.

Authoritative source/symbol map for the findings below:

| Source file at the identified revision | Relevant symbols |
|---|---|
| vitaGL `source/vgl.c` | `vglInit`, `vglInitExtended`, `vglInitWithCustomThreshold`, `vglInitWithCustomSizes` |
| vitaGL `source/gxm.c` | `start_shader_compiler`, `init_gxm`, `init_gxm_context`, `create_display_render_target`, `init_display_color_surfaces`, `init_display_depth_stencil_surfaces`, `start_shader_patcher`, `scene_reset`, `vglSwapBuffers` |
| vitaGL `source/splashscreen.c` | `splashscreen_thread`, `invoke_splashscreen`, `clear_splashscreen`, `is_splashscreen_active` |
| vitaGL `source/utils/mem_utils.c` | `vgl_mem_init`, pool allocation/map setup |
| vitaGL `source/utils/gpu_utils.c` | GPU/USSE allocation and mapping helpers |
| vitaGL `source/utils/gxm_utils.c` | `vglSetupUniformCircularPool` |
| vitaGL `source/ffp.c` | fixed-function shader generation and calls to `shark_compile_shader_extended` |
| vitaShaRK `source/vitashark.c` | `shark_init`, `shark_set_allocators`, compiler calls |
| SceShaccCgExt `src/shacccg_ext.c` | `sceShaccCgExtEnableExtensions`, `sceShaccCgExtDisableExtensions` |

Archive symbol/disassembly inspection confirms that the installed library
exports all four `vglInit*` symbols, `vglSwapBuffers`, and the internal
`is_shark_online` variable, but no `vglEnd`. The ARM tail of
`vglInitWithCustomSizes` writes `vgl_inited` and returns its saved
`res_fallback` value, matching the source-level contract.

## Exact installed initialization API

The authoritative declarations in the installed `vitaGL.h` are:

```c
GLboolean vglInit(int legacy_pool_size);
GLboolean vglInitExtended(int legacy_pool_size, int width, int height,
                          int ram_threshold, SceGxmMultisampleMode msaa);
GLboolean vglInitWithCustomSizes(int legacy_pool_size, int width, int height,
                                int ram_pool_size, int cdram_pool_size,
                                int phycont_pool_size, int cdlg_pool_size,
                                SceGxmMultisampleMode msaa);
GLboolean vglInitWithCustomThreshold(int pool_size, int width, int height,
                                    int ram_threshold, int cdram_threshold,
                                    int phycont_threshold, int cdlg_threshold,
                                    SceGxmMultisampleMode msaa);
```

`vglInit(pool_size)` is exactly equivalent to:

```c
vglInitExtended(pool_size, 960, 544, 0x01000000,
                SCE_GXM_MULTISAMPLE_4X);
```

`vglInitExtended` delegates to `vglInitWithCustomThreshold` with zero CDRAM
and physically-contiguous-memory thresholds, and a CDLG threshold of
`SCE_KERNEL_MAX_MAIN_CDIALOG_MEM_SIZE` (`0x008C6000`).

`vglInitWithCustomSizes` also returns `GL_FALSE` if vitaGL was already
initialized. Therefore even outside the resolution case, the return has no
unambiguous “success” interpretation. The installed public API exposes no
`vglEnd` symbol. The EGL façade has `eglTerminate`, but it is a separate
initialization façade and should not be mixed into this direct `vglInit` path.

The installed header provides these relevant pre-init configuration controls:

- `vglSetCircularPoolSize`
- `vglSetDisplayBufferCount` / `vglUseTripleBuffering`
- `vglSetFragmentBufferSize`
- `vglSetParamBufferSize`
- `vglSetUSSEBufferSize`
- `vglSetVDMBufferSize`
- `vglSetVertexBufferSize`
- `vglSetupDisplayRenderTarget`
- `vglSetupGarbageCollector`
- `vglSetupShaderPatcher`
- `vglSetupRuntimeShaderCompiler`
- `vglUseCachedMem`
- `vglUseVramForUSSE`
- `vglUseExtraMem`
- `vglSetShaderCachePath` (compiled to no effect because
  `HAVE_SHADER_CACHE` is not enabled)
- `vglSetupScratchMemory` (compiled to no effect because
  `HAVE_SCRATCH_MEMORY` is not enabled)

The official current vitaGL samples do not test `vglInit*` as a Boolean
success value. They call it and proceed to rendering. Representative cases
are `samples/vertex_array/main.c` and `samples/rotating_cube/main.c`, which
call `vglInit(0x800000)`, and `samples/ssao_deferred_rendering/main.cpp`, which
calls `vglInitExtended(...)` and ignores the return.

## Requested/default graphics and memory configuration

For A2.2's `vglInit(4 * 1024 * 1024)`, the installed source selects:

| Item | Effective value |
|---|---|
| Legacy/immediate-mode pool request | 4 MiB; saved at init and allocated as temporary per-scene storage when a scene begins |
| Display width x height | 960 x 544 |
| Display stride | 960 pixels (`width` aligned to 64) |
| Display buffers | 3 |
| Display/color format | `SCE_GXM_COLOR_FORMAT_A8B8G8R8`, linear, 32-bit output; display callback uses `SCE_DISPLAY_PIXELFORMAT_A8B8G8R8` |
| Depth/stencil format | `SCE_GXM_DEPTH_STENCIL_FORMAT_DF32M_S8`, linear |
| MSAA | `SCE_GXM_MULTISAMPLE_4X` |
| Render-target scenes per frame | 1 |
| VSync interval | 1 |
| RAM threshold | 16 MiB |
| CDRAM threshold | 0 |
| PHYCONT threshold | 0; this build uses PHYCONT-on-demand behavior only if enabled at build, which the package did not enable |
| CDLG threshold | `0x008C6000`; calculated CDLG pool request is therefore 0 |
| GXM parameter buffer | 16 MiB |
| Main-context VDM ring | 128 KiB |
| Main-context vertex ring | 2 MiB |
| Main-context fragment ring | 512 KiB |
| Main-context fragment-USSE ring | 16 KiB |
| Main-context host memory | 2 KiB |
| Shader patcher | 1 MiB buffer + 1 MiB vertex USSE + 1 MiB fragment USSE |
| Uniform circular pool | 2 MiB |
| General circular pool | 32 MiB total, split across 3 display buffers |
| Constant index buffers | 3 x `0xC000` 16-bit entries = 294,912 bytes |
| Memory caching | Internal main-RAM pool is uncached by default |
| Extra/newlib memory fallback | Enabled |
| USSE preference | Main/CPU memory, not CDRAM, by default |
| Runtime compiler policy | `SHARK_OPT_FAST`; fast-math=true, fast-precision=false, fast-int=true |

For a normal application, `vglInitWithCustomThreshold` queries
`sceKernelGetFreeMemorySize` after its early `init_gxm()` call and computes the
pool arguments as follows:

```text
RAM     = max(free_user    - 16 MiB, 0)
CDRAM   = free_cdram
PHYCONT = free_phycont
CDLG    = 0
```

The uncached RAM pool is then capped internally at `0x0C800000` (200 MiB).
Pool sizes are aligned before allocation. In system-application mode vitaGL
instead uses `sceAppMgrGetBudgetInfo`, forces double buffering, and changes
the no-MSAA case; that is not the expected mode for this application.

At 960 x 544, each color buffer request is aligned to 2 MiB, for 6 MiB across
three buffers. The 4x-MSAA depth allocation is 8,355,840 bytes and the stencil
allocation is 2,088,960 bytes. While the splash is active, it also creates a
second GXM context with its own context host memory and VDM, vertex, fragment,
and fragment-USSE rings.

The free-memory values logged immediately before `vglInit` are useful but are
not identical to the values used for the pool calculation: `init_gxm` and the
shader/compiler and collector startup occur before vitaGL performs its own
free-memory query. Exact probe logging should therefore capture both the
pre-call values and the memory allocation API results inside the call.

## Initialization order and failure surface

The installed `vglInit` path performs the following operations in order.
Most low-level return values are discarded by vitaGL, especially in this
`SKIP_ERROR_HANDLING` package build; the one `vglInit` return cannot report
them.

| Stage | Operations that can fail or block | Return handling in installed vitaGL |
|---|---|---|
| 1. Entry/cache directories | Duplicate-init check; shader-cache directory `sceIoMkdir` calls; maximum-display-resolution query | Duplicate init returns `GL_FALSE`; mkdir/query results ignored |
| 2. Runtime shader compiler | Allocator registration; `shark_init(NULL)`; fallback `shark_init("ur0:data/external/libshacccg.suprx")` | Both module-load results reduced to `is_shark_online`; failure does not abort init |
| 3. Garbage collector | Two `sceKernelCreateSema` calls, thread creation, thread start | Results ignored |
| 4. GXM global init | `sceAppMgrGetBudgetInfo`, parameter setup, `sceGxmVshInitialize` | GXM return ignored; internal `gxm_initialized` set true unconditionally |
| 5. Free-memory/pool selection | `sceKernelGetFreeMemorySize` or budget query; threshold arithmetic | Query return ignored |
| 6. Memory heaps | `sceKernelAllocMemBlock`, `sceKernelGetMemBlockBase`, `sceGxmMapMemory`, heap/mspace setup, newlib heap mapping | Most results ignored; a null base prevents adding that pool but no aggregate failure is returned |
| 7. Main graphics context | VDM/vertex/fragment/USSE allocations and maps, host allocation, `sceGxmCreateContext`, 2 MiB uniform pool | Results ignored |
| 8. Display target | `sceGxmCreateRenderTarget` | Helper returns the exact result, but caller discards it |
| 9. Framebuffers | Three aligned color allocations, three `sceGxmColorSurfaceInit` calls, three `sceGxmSyncObjectCreate` calls | Results ignored |
| 10. Depth/stencil | Aligned depth and stencil allocations and surface descriptor init | Allocation results unchecked; descriptor helper cannot supply an aggregate init result |
| 11. Shader patcher/default programs | Buffer and vertex/fragment-USSE allocations/maps, `sceGxmShaderPatcherCreate`, clear-program register/patch calls | Results ignored |
| 12. Splash | Splash program register/patch; two semaphores; second context; thread creation/start | Results ignored; asynchronous thread begins displaying |
| 13. Remaining built-ins | Blit program, mask-update fragment program, state objects | Results ignored |
| 14. State-cache/texture setup | Texture units, custom shader state, VAO, query state, scissor state, 8 x 8 default texture | Allocation and API failures are not summarized by init return |
| 15. Vertex/index setup | 32 MiB circular pool, three constant index buffers, immediate-mode vertex layouts/pool bookkeeping | Allocation results unchecked in the no-debug build |
| 16. Completion | Matrices initialized; `vgl_inited = GL_TRUE`; return `res_fallback` | `GL_FALSE` is expected for 960 x 544 |

Seeing an animated splash is strong evidence that global GXM initialization,
the display render target, color/depth surfaces, shader patcher, precompiled
clear shaders, splash shaders, a second graphics context, and a display queue
were usable enough to render repeatedly. It does not prove every ignored API
returned success, and it does not prove the runtime shader compiler is online.
The hardware breadcrumb written after the `vglInit` call independently proves
that the call itself returned and that execution traversed the remaining
in-function setup after the splash thread was launched.

## libshacccg / vitaShaRK behavior

The exact compiler startup path is:

```text
vitaGL init_gxm
  -> shark_set_allocators(vglMalloc, vglFree)
  -> shark_init(NULL)
       -> sceKernelLoadStartModule("ur0:/data/libshacccg.suprx", ...)
       -> sceShaccCgExtEnableExtensions()
       -> sceShaccCgSetDefaultAllocator(...)
       -> sceShaccCgInitializeCallbackList(...)
  -> on a negative shark_init result, retry:
       shark_init("ur0:data/external/libshacccg.suprx")
```

`shark_init` returns the exact negative `sceKernelLoadStartModule` result if
module loading fails and `0` after its remaining setup. vitaShaRK 1.5 does not
propagate the return from `sceShaccCgExtEnableExtensions` (documented as 0 or
-1) or `sceShaccCgSetDefaultAllocator`; it ignores both. vitaGL ignores total
compiler startup failure and continues its graphics initialization.

SceShaccCgExt 1.0.1 uses taiHEN APIs to locate the loaded `SceShaccCg`
module, accepts module NID `0xEE15880D` or `0x6C3C7547`, retrieves its module
information, applies six code/data injections and one hook, and returns `-1`
if any prerequisite or patch step fails. Because vitaShaRK discards this
return, successful module loading alone does not prove extension setup. This
is a reason to instrument the existing path, not evidence that the user needs
to install or change any unrelated plugin.

The splash and the init-time clear/blit programs are precompiled GXP programs.
They do not require runtime shader compilation. Therefore:

> A spinning vitaGL logo proves neither that `libshacccg.suprx` was found nor
> that the compiler/extensions are usable.

The first fixed-function render path may need to synthesize and compile FFP
vertex/fragment shaders through `shark_compile_shader_extended`. If compiler
startup failed, this can become the next failure after the initialization
return bug is removed. That must be tested before attributing a later failure
to WW3D geometry or textures.

For persistent, exact results without modifying/rebuilding installed vitaGL,
GNU ld wrapping is the cleanest diagnostic boundary:

- wrap `shark_init` and log/flush its input path and exact signed/hex return;
- optionally wrap `sceKernelLoadStartModule`,
  `sceShaccCgExtEnableExtensions`, and
  `sceShaccCgSetDefaultAllocator` to separate module, extension, and allocator
  setup;
- log a before/after around the first FFP shader compile if draw traversal is
  reached.

Do not call `shark_init` manually before `vglInit` merely to probe it. Its
initialization is idempotent; doing so can cause vitaGL's later call to skip
the intended allocator setup sequence and would alter the condition being
diagnosed. `libvitaGL.a` exports an internal `is_shark_online` symbol, but it
is not part of public `vitaGL.h`; a linker wrapper yields the authoritative
return without relying on private ABI.

## Splash lifecycle and required transition

The installed splash implementation is asynchronous:

1. Midway through `vglInitWithCustomSizes`, `invoke_splashscreen` registers and
   patches precompiled splash shaders.
2. It creates a push semaphore, a pull semaphore, and a dedicated
   `vitaGL Splashscreen` thread, starts the thread, and sets
   `is_splashscreen_active = GL_TRUE`.
3. The thread repeatedly begins a scene, clears, draws the rotating logo and
   commit hash, ends the scene, and submits it to the display queue.
4. It waits for the push semaphore only with a short timeout, so absent a
   signal it is intentionally an indefinite animation.
5. After a termination signal it fades out, calls `sceGxmFinish`, signals the
   pull semaphore, releases splash allocations/context, and exits.

The normal signal is sent only by the main renderer's `scene_reset()` path.
That function signals the splash push semaphore, waits for the pull semaphore,
marks the splash inactive, unregisters its programs, deletes its semaphores,
and then begins the main graphics scene.

Operations that call `scene_reset()` include `glClear`, draw paths,
`glFlush`, and `glFinish`. By contrast, `vglSwapBuffers` begins with:

```c
if (is_splashscreen_active)
    return;
```

Thus the reliable initialization-only presentation proof is:

```text
BEFORE glClear
glClearColor(known color)
glClear(color | depth)       # terminates/joins splash and begins main scene
AFTER glClear
BEFORE vglSwapBuffers
vglSwapBuffers(GL_FALSE)     # presents the completed main scene
AFTER vglSwapBuffers
```

Each breadcrumb should be appended and flushed before continuing so the
physical log distinguishes a splash fade/join problem, scene-begin problem,
and display-queue/present problem.

## Classification of the observed A–F cases

| Case | Finding for the original physical run |
|---|---|
| A. `vglInit` never returns | Ruled out by the post-call hardware diagnostic and the caller reaching its `GL_FALSE` branch. |
| B. `vglInit` returns an error | Ruled out as an API interpretation: raw `0` is the expected “no resolution fallback” result, not an error code. |
| C. `vglInit` succeeds but another renderer-init operation fails | Not the cause of the reported coarse failure. Later operations were skipped by the erroneous branch. Still test the compiler and first clear/present explicitly. |
| D. Splash needs an explicit transition/framebuffer action | Proven. It is intentionally asynchronous and remains active until `scene_reset`; `vglSwapBuffers` alone cannot terminate it. |
| E. Shader compiler initialization blocks | Ruled out for this run because it occurs before splash launch and the outer init later returned. Compiler availability/use is not yet proven because startup failure is non-fatal and ignored. |
| F. Graphics-init memory allocation fails | Not supported by the symptom, and not the reason the caller reported failure. The running splash demonstrates substantial allocations succeeded. Exact ignored return codes still require wrappers if the clear/present probe fails. |

## Recommended next-hardware evidence

The smallest useful physical probe, while preserving the original WW3D path,
is:

1. Log/flush renderer entry, installed API identity, display request, every
   requested threshold/pool value, and `sceKernelGetFreeMemorySize` before the
   call.
2. Log/flush immediately before `vglInit`.
3. Capture/log the two `shark_init` paths and exact returns with a linker
   wrapper.
4. Log/flush immediately after `vglInit`, labeling its exact raw value only as
   `resolution_fallback`.
5. Do not return failure on `GL_FALSE`.
6. Log/flush before and after `glClear` of a known color, then before and after
   `vglSwapBuffers(GL_FALSE)`.
7. Continue into the existing original `SimpleScene -> Camera -> WW3D::Render
   -> RenderObj -> MeshClass::Render` path.

If deeper per-operation evidence is still needed, linker-wrap the low-level
undefined calls made by the static vitaGL archive. At minimum useful targets
are `sceGxmVshInitialize`, `sceKernelAllocMemBlock`,
`sceKernelGetMemBlockBase`, `sceGxmMapMemory`,
`sceGxmMapVertexUsseMemory`, `sceGxmMapFragmentUsseMemory`,
`sceGxmCreateContext`, `sceGxmCreateRenderTarget`,
`sceGxmColorSurfaceInit`, `sceGxmSyncObjectCreate`,
`sceGxmShaderPatcherCreate`, `sceGxmShaderPatcherRegisterProgram`, and the
shader-patcher program creation functions. A wrapper must preserve the real
call and return exactly, writing and flushing a BEFORE/AFTER breadcrumb around
it.

Until a clear/present probe fails, rebuilding vitaGL or changing Vita plugins
is not justified. The evidence already provides a minimal, source-proven
correction for the indefinite-logo behavior.
