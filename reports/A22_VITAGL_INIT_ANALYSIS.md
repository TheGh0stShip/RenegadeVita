# A2.2 vitaGL Initialization and Splash-Screen Analysis

Date: 2026-08-07

## Result

The physical Vita did **not** hang inside `vglInit`, and `vglInit` did **not**
return an error. The shipped A2.2 executable calls `vglInit(4 MiB)`, receives
`0`, mistakes that value for failure, and returns from the Renegade Vita
renderer before issuing its first clear/draw.

In the exact installed vitaGL revision, the `GLboolean` returned by every
`vglInit*` entry point is a **resolution-fallback flag**, not a success flag:

- `GL_FALSE` (`0`): the requested resolution was accepted; initialization ran
  to its end.
- `GL_TRUE` (`1`): the requested resolution exceeded the maximum and was
  clamped; initialization still ran to its end.
- An already-initialized call is suppressed and also returns `GL_FALSE`, so the
  return value cannot be used as an initialization-status indicator at all.

The animated logo is a dedicated render thread with no elapsed-time exit. It
continues indefinitely until the main rendering thread enters vitaGL's
`scene_reset()`. A first `glClear`, draw, `glFlush`, or `glFinish` reaches that
transition. `vglSwapBuffers` alone explicitly returns while the splash is
active and therefore does not dismiss it.

The required application correction is therefore:

1. Treat the raw `vglInit` return only as `resolution_fallback` and continue for
   either `0` or `1`.
2. Perform the normal renderer state setup.
3. Issue `glClearColor`, then `glClear(...)` to enter `scene_reset()` and stop
   the splash thread.
4. Call `vglSwapBuffers(GL_FALSE)` only after that clear.
5. Continue through the original `SimpleScene -> Camera -> WW3D::Render ->
   RenderObj -> MeshClass::Render` path.

No filesystem, W3D loader, asset-manager, prototype, HLOD, mesh-model,
material, hierarchy, or object-lifetime change is implicated.

## Evidence set and identity

The analysis is against the exact artifacts used by the failed physical A2.2
run, not an API assumption from an old sample. In the table, `dist/` denotes
the managed builder distribution directory two levels above this workspace.

| Artifact | Size | SHA-256 |
|---|---:|---|
| `/usr/local/vitasdk/arm-vita-eabi/lib/libvitaGL.a` | 724,606 | `bcc414e745a1f29940f7c33418f268c4cd78d0388b7a0da0f036b72355597b69` |
| `/usr/local/vitasdk/arm-vita-eabi/include/vitaGL.h` | - | `ba68004be9faf49fa4b0526ecbcdf26c3b4b8d001f85e119ce35db26a3f70e3a` |
| `/usr/local/vitasdk/arm-vita-eabi/lib/libvitashark.a` | - | `7b0c4a7aaa3e5e50a5b18083cccf2ce7b98a993380bd3ac1739f863368dd32b6` |
| `/usr/local/vitasdk/arm-vita-eabi/include/vitashark.h` | - | `b746269bf5c22a8fd59d9c2cf8aba482e40a6e7c838ec50f3c809d94bdb620d8` |
| `dist/RenegadeVita-A2.2.elf` | 13,943,160 | `f0c44269fe8c0ccbf0270c17a8ffcc10eafb787fb65189d7019ba5d0a036440e` |
| `dist/RenegadeVita-A2.2.vpk` | 630,103 | `fd7dadbc09aed6b32e3631738ee8b851cf6f29f3635a89638720cea86b83081a` |
| `dist/a22-runtime.log` | 2,697 | `3c07075953c61e93b194ff724134bb56594087463918182e0a5c14eb3a3bce6d` |

The installed archive identifies its source revision directly. Extracting
`splashscreen.o` and scanning it produces the embedded string `#6e7fe40`.
The installed public header is byte-identical to `source/vitaGL.h` at full
upstream commit:

`6e7fe40292e8f1d10f9a94ff2cd2f4fb1ba452a5`

As an additional binary-source check, that commit was rebuilt with the package
command `make NO_DEBUG=1`. All 30 objects extracted from the installed archive
compare byte-for-byte equal to the corresponding rebuilt objects. The key
object hashes on both sides are `vgl.o`
`536afb137fbf2c9ec8bd7bf1cbbe8dd9c30458fa8a128dfb906a04e7e880e32b`,
`gxm.o`
`996dfcba13f46694ea05034db2ab6263dcc47a33904d12c3a7c0aae7d5773b25`,
and `splashscreen.o`
`a74565e99a578481f82c9a2198bf6cee1a6c0ef5a6ba329b6f2aab55a47afa60`.
This establishes exact behavioral source identity for the entire static
library, not just the public header and embedded revision text.

The relevant exact-revision source is:

- [vitaGL `vgl.c` at 6e7fe40](https://github.com/Rinnegatamante/vitaGL/blob/6e7fe40292e8f1d10f9a94ff2cd2f4fb1ba452a5/source/vgl.c)
- [vitaGL `gxm.c` at 6e7fe40](https://github.com/Rinnegatamante/vitaGL/blob/6e7fe40292e8f1d10f9a94ff2cd2f4fb1ba452a5/source/gxm.c)
- [vitaGL `splashscreen.c` at 6e7fe40](https://github.com/Rinnegatamante/vitaGL/blob/6e7fe40292e8f1d10f9a94ff2cd2f4fb1ba452a5/source/splashscreen.c)
- [vitaGL `mem_utils.c` at 6e7fe40](https://github.com/Rinnegatamante/vitaGL/blob/6e7fe40292e8f1d10f9a94ff2cd2f4fb1ba452a5/source/utils/mem_utils.c)

The installed vitaShaRK header is byte-identical to tag `v.1.5`, commit
`5d99fe81a4a384c5e4e7a8cba2d851df8dbda5da`.

The VitaSDK packages recipe at commit
`3c2a993afd5f30cb820cb900e7bc7f4d2b45d308` builds vitaGL as:

```sh
make NO_DEBUG=1 -j$(nproc)
```

and declares `libmathneon`, `vitaShaRK`, `taihen`, and `SceShaccCgExt` as
dependencies. `NO_DEBUG=1` defines `SKIP_ERROR_HANDLING`; it does not disable
the splash. Consequently, most internal SceGxm return codes are discarded and
normal GL validation paths are compiled out in this installed archive.

## Final-ELF proof of the application defect

The shipped ELF contains these resolved symbols:

```text
8100308c T RenegadeVitaRenderer::Initialize()
8104c22c T start_shader_compiler
8104c280 T init_gxm
8104c850 T scene_reset
8104cf28 T vglSwapBuffers
81052208 T splashscreen_thread
810530f4 T invoke_splashscreen
8105adb8 t vglInitWithCustomSizes.part.0
8105b8c4 T vglInitWithCustomSizes
8105b8f8 T vglInitWithCustomThreshold
8105b9e0 T vglInitExtended
8105ba08 T vglInit
8113bc20 B is_splashscreen_active
8121c824 b vgl_inited
8121d884 B is_shark_online
```

The call-site disassembly is conclusive:

```text
810030a4: mov.w r0, #4194304
810030aa: bl    8105ba08 <vglInit>
810030b0: cmp   r0, #0
810030b2: beq   8100309e
```

The branch target returns the existing zero value from
`RenegadeVitaRenderer::Initialize()`. All following calls (`glViewport`, depth
state, cull state, and matrix setup) occur only on the nonzero branch.

The linked vitaGL implementation shows what that zero means:

```text
8105ae40: cmp   requested_width, max_width
8105ae46: ble   8105b81e           ; normal resolution path
8105ae4a: movs  r2, #1
8105ae4c: str   r2, [sp, #92]      ; fallback flag = 1
...
8105b81e: movs  r2, #0
8105b824: str   r2, [sp, #92]      ; fallback flag = 0
...
8105b7ec: ldr   r0, [sp, #92]      ; return fallback flag
8105b7ee: strb  #1, [vgl_inited]    ; initialization marked complete
```

`invoke_splashscreen` is called at `0x8105b82a` during this function, and the
function later loads the fallback flag, sets `vgl_inited`, and returns. For the
native 960x544 request, the ordinary result is zero.

Historical upstream evidence removes any remaining ambiguity. Commit
[`c7a3e1a66334e1be8560088ed1fd264a1de1473f`](https://github.com/Rinnegatamante/vitaGL/commit/c7a3e1a66334e1be8560088ed1fd264a1de1473f),
whose subject is "Added fallback to 960x544 res if requested resolution is
invalid," changed the init APIs from `void` to `GLboolean`, introduced
`res_fallback`, and returned that flag. It did not introduce a success/error
return.

The physical runtime log then completes the proof: it contains `Vita renderer
initialization: FAIL` and all later summary lines. Those lines can only be
written after `WW3D::Init` and the renderer call returned to the validation
harness. Therefore case A (`vglInit` never returns) is impossible for the
tested executable.

## Exact splash lifecycle

`invoke_splashscreen()` performs the following:

1. Registers and patches precompiled splash vertex and fragment programs.
2. Creates two semaphores (`Push` and `Pull`).
3. Creates and starts the dedicated `vitaGL Splashscreen` thread.
4. Sets `is_splashscreen_active = GL_TRUE`.

The splash thread allocates/decompresses its model, creates a second GXM
context, and enters an unconditional `for (;;)` rendering loop. On every
iteration it waits on the push semaphore with a 10,000-microsecond timeout. A
timeout merely renders the next spinning-logo frame. There is no automatic
maximum duration. Only a successful semaphore wait sets `must_terminate`.
After that request, it fades out for `SPLASH_FADE_SEC` (one second), calls
`sceGxmFinish`, signals the pull semaphore, frees its context resources, and
exits the thread.

`scene_reset()` is the main-thread owner of that handshake:

```text
if (is_splashscreen_active) {
    signal splash push semaphore;
    wait indefinitely for splash pull semaphore;
    clear is_splashscreen_active;
    unregister/release splash programs;
    delete both semaphores;
}
begin the main GXM scene;
```

The final ELF confirms the semaphore signal/wait at `0x8104cc8c` and
`0x8104cc96`. It also confirms that `vglSwapBuffers` checks
`is_splashscreen_active` at entry and branches directly to `bx lr` at
`0x8104d19c` when it is set. A swap is therefore not the transition trigger.

`glClear()` calls `scene_reset()` before drawing the clear quad. Draw entry
points, `glFlush`, and `glFinish` also reach `scene_reset()`. The shipped caller
returns before all such operations, leaving the splash thread in its intended
wait-for-first-scene state forever.

## Classification of the observed cases

| Case | Finding | Proof |
|---|---|---|
| A. `vglInit` never returns | **Ruled out** | The application emitted the post-renderer result summary, which requires the init call to have returned. |
| B. `vglInit` returns an error | **Ruled out** | Raw zero is `res_fallback == GL_FALSE`, not an error. There is no error-return contract. |
| C. A later renderer-init operation fails | **Not the observed cause** | The shipped caller branches out immediately on the zero returned by `vglInit`; no later backend setup runs. |
| D. Splash needs an explicit transition | **Confirmed** | `scene_reset()` performs the semaphore handshake; `vglSwapBuffers` alone is ignored during the splash. |
| E. Shader compiler initialization blocks | **Ruled out as the hang** | `start_shader_compiler()` executes before GXM initialization and before the splash can be launched. A visible animated splash proves that call returned, though not that it succeeded. |
| F. Graphics-init allocation fails | **No evidence; not this failure** | `vglInit` ran through its completion path and returned. Internal allocation return values are not exposed by this optimized archive, so a future issue still needs direct instrumentation. |

## Shader compiler and libshacccg behavior

The exact vitaGL order is:

```text
vglInit
  -> vglInitExtended
    -> vglInitWithCustomThreshold
      -> init_gxm
        -> start_shader_compiler
          -> shark_set_allocators(vglMalloc, vglFree)
          -> shark_init(NULL)
          -> if failed: shark_init("ur0:data/external/libshacccg.suprx")
        -> GXM initialization
      -> free-memory query
      -> vglInitWithCustomSizes
        -> full graphics resource setup
        -> invoke_splashscreen
        -> remaining resource setup
        -> return res_fallback
```

vitaShaRK v1.5 resolves `shark_init(NULL)` to the default path
`ur0:/data/libshacccg.suprx`. It calls `sceKernelLoadStartModule`; a negative
module-load result is returned unchanged. On success it enables ShaccCg
extensions, installs the vitaGL allocators/callbacks, marks itself initialized,
and returns zero. A later `shark_init` call returns zero immediately when the
module is already initialized.

vitaGL does not abort init if both compiler paths fail. It stores the result in
the externally linked `is_shark_online` byte and continues. The splash programs
are precompiled GXP data, so the animated logo proves only that the compiler
attempt **returned**, not that libshacccg loaded successfully.

For the next hardware probe, the least-perturbing compiler evidence is:

- `sceIoGetstat` both exact paths before `vglInit`, logging each raw return and
  file size;
- after `vglInit`, log the linked `is_shark_online` byte; or, with the exact
  installed vitaShaRK v1.5, call `shark_init(NULL)` and log its raw result (safe
  because an already-initialized instance returns zero without reloading);
- retain a compiler diagnostic callback for the first lazy fixed-function
  shader compilation.

The current fixed-function path uses cache directory
`ux0:data/shader_cache/v28`. On a cache miss, the first mesh path attempts to
start the compiler if it is offline and calls `shark_compile_shader_extended`.
That later lazy event is separate from the splash lifecycle.

## Exact default configuration selected by `vglInit(4 MiB)`

The legacy argument is not vitaGL's total allocation. It reserves a 4 MiB
immediate-mode pool allocation when the first scene begins.

| Setting | Exact value |
|---|---:|
| Requested display | 960 x 544 |
| Display stride | 960 pixels (width aligned to 64) |
| MSAA | `SCE_GXM_MULTISAMPLE_4X` |
| Display buffers | 3 (2 only for system-app mode) |
| Display pixel format | `SCE_DISPLAY_PIXELFORMAT_A8B8G8R8` |
| GXM color format | `SCE_GXM_COLOR_FORMAT_A8B8G8R8` |
| Color surface | linear, MSAA downscale, 32-bit output |
| Depth/stencil | `SCE_GXM_DEPTH_STENCIL_FORMAT_DF32M_S8`, linear |
| Render-target scenes/frame | 1 |
| RAM threshold retained | 16 MiB |
| CDRAM threshold retained | 0 (request all reported free CDRAM) |
| PHYCONT threshold retained | 0 (request all reported free PHYCONT) |
| Common-dialog pool | 0 (`0x8c6000` threshold equals maximum) |
| Circular temporary pool | 32 MiB total, divided among display buffers |
| Uniform circular pool | 2 MiB |
| Parameter buffer | 16 MiB |
| VDM ring/context | 128 KiB |
| Vertex ring/context | 2 MiB |
| Fragment ring/context | 512 KiB |
| Fragment USSE ring/context | 16 KiB |
| Context host memory/context | 2 KiB |
| Shader patcher general buffer | 1 MiB |
| Shader patcher vertex USSE | 1 MiB |
| Shader patcher fragment USSE | 1 MiB |
| Constant index buffers | 3 x (`0xC000` x 2 bytes) = 288 KiB |
| Default texture | 8 x 8 RGBA |

For a non-system app, after `init_gxm` has run, vitaGL calls
`sceKernelGetFreeMemorySize` and requests these heap sizes:

```text
RAM     = max(size_user    - 16 MiB, 0)
CDRAM   = max(size_cdram   - 0,      0)
PHYCONT = max(size_phycont - 0,      0)
CDLG    = max(0x8c6000     - 0x8c6000, 0) = 0
```

`vgl_mem_init` aligns RAM to 4 KiB, CDRAM to 256 KiB, and PHYCONT to 1 MiB.
The runtime values cannot be stated statically; the next build should log
`sceKernelGetFreeMemorySize` before and after `vglInit`, plus
`vglMemTotal/vglMemFree` per pool after return.

At 960x544 with 4x MSAA, each of the three color allocations is rounded to
2 MiB (6 MiB total). The display depth allocation is 8,355,840 bytes and the
stencil allocation is 2,088,960 bytes. The splash creates a second GXM context
using the same ring-size defaults while it is active.

## Internal init operation audit

The exact source executes the following potentially failing operations, in
order. "Ignored" means the installed archive does not propagate the return to
`vglInit` and, in most cases, does not log it.

1. Attempt `shark_init` at the default and fallback module paths (results
   reduced to `is_shark_online`; compiler failure does not abort).
2. Create/start garbage-collector semaphores and thread (returns ignored).
3. Call `sceAppMgrGetBudgetInfo`; zero is used as the system-app-mode test.
4. Call `sceGxmVshInitialize` (return ignored; `gxm_initialized` is set true
   unconditionally).
5. Query free memory with `sceKernelGetFreeMemorySize` for a normal app, or
   query the app budget again for a system app (return ignored). The visible
   splash proves the tested process followed normal-app mode because vitaGL
   suppresses the splash in system-app mode.
6. Enter `vglInitWithCustomSizes`, create shader-cache directories with
   `sceIoMkdir`, and ignore the returns.
7. Query maximum framebuffer resolution with
   `sceDisplayGetMaximumFrameBufResolution` (return ignored; inputs are
   initialized to the requested dimensions), set display/viewport globals,
   then make a no-op second `init_gxm` call because GXM is already marked
   initialized.
8. Allocate/mount vitaGL RAM, CDRAM, PHYCONT, and newlib heaps using
   `sceKernelAllocMemBlock`, `sceKernelGetMemBlockBase`, `sceGxmMapMemory`, and
   `sceClibMspaceCreate` (individual returns not surfaced).
9. Allocate the main context's ring/USSE/host buffers and call
   `sceGxmCreateContext` (return ignored).
10. Create the display render target with `sceGxmCreateRenderTarget` (helper
    returns an `int`, but this caller ignores it).
11. Allocate three color buffers; call `sceGxmColorSurfaceInit` and
    `sceGxmSyncObjectCreate` (returns ignored).
12. Allocate depth and stencil storage and initialize the local surface
    descriptor.
13. Allocate shader-patcher general/vertex-USSE/fragment-USSE buffers and call
    `sceGxmShaderPatcherCreate` (return ignored).
14. Allocate clear resources; register, find parameters for, and patch the
    precompiled clear programs (return values ignored in this build).
15. Register/patch splash programs; create two splash semaphores and create/
    start the splash thread (returns ignored), then mark splash active.
16. Register and patch blit programs (returns ignored).
17. Create the scissor mask program and allocate its vertex storage (returns
    ignored).
18. Reset texture-unit/custom-shader/VAO/query state.
19. Allocate the 32 MiB circular data pool (unchecked).
20. Allocate and fill the three 96 KiB constant index buffers (unchecked).
21. Record the 4 MiB legacy vertex-pool size; actual allocation is deferred to
    the first `scene_reset()`.
22. Create the default 8x8 texture via `glTexImage2D`.
23. Initialize matrices, set `vgl_inited = GL_TRUE`, and return only the
    resolution-fallback flag.
24. On the first clear/draw: allocate the deferred legacy pool, signal/wait out
    the splash, then call `sceGxmBeginScene`.
25. On the first fixed-function mesh: locate or compile the lazy FFP programs
    and patch them.

Because the installed library is a `NO_DEBUG=1` static archive, an application
breadcrumb before and after `vglInit` can prove whether the complete function
returned, but it cannot recover the discarded raw return from every internal
SceGxm call. `glGetError` is also not a substitute: nearly all sites that set
`vgl_error` are under `#ifndef SKIP_ERROR_HANDLING`, so this build will commonly
report `GL_NO_ERROR` even when an internal return was ignored.

If exact raw codes for every internal call are still required after the known
caller bug is fixed, use an instrumented build of the **same** vitaGL commit
`6e7fe40` (or link-time wrappers for the imported Vita APIs). Do not change the
init signature, allocation policy, splash behavior, or compiler paths while
instrumenting; otherwise the probe would no longer reproduce this archive.

## Minimal probe expectations

A corrected initialization-only probe should produce this ordering in the
persistent runtime log:

```text
renderer init entry
free memory before
libshacccg default/fallback stat results
vglInit entry
vglInit return raw=0 semantic=resolution_fallback/no-clamp
free memory and vitaGL pool totals after
shader compiler online/result
first glClear entry
first glClear return             # splash signal, fade, join, main BeginScene
first vglSwapBuffers entry
first vglSwapBuffers return
renderer initialized return
```

The screen should transition from the logo to the chosen solid clear color,
present at least one frame, and then continue into the original WW3D path. If
it stops before `vglInit return`, the last internal stage would need a same-
revision instrumented vitaGL archive. If it stops at `first glClear entry`, the
next focus is the splash semaphore/fade join or `sceGxmBeginScene`, not W3D
mesh submission.

## Reproduction commands

These commands produced the archive and final-ELF evidence above:

```sh
sha256sum \
  /usr/local/vitasdk/arm-vita-eabi/lib/libvitaGL.a \
  /usr/local/vitasdk/arm-vita-eabi/include/vitaGL.h \
  /usr/local/vitasdk/arm-vita-eabi/lib/libvitashark.a \
  /usr/local/vitasdk/arm-vita-eabi/include/vitashark.h \
  ../../dist/RenegadeVita-A2.2.elf \
  ../../dist/RenegadeVita-A2.2.vpk \
  ../../dist/a22-runtime.log

/usr/local/vitasdk/bin/arm-vita-eabi-ar t \
  /usr/local/vitasdk/arm-vita-eabi/lib/libvitaGL.a

mkdir -p /tmp/vgl-proof
cd /tmp/vgl-proof
/usr/local/vitasdk/bin/arm-vita-eabi-ar x \
  /usr/local/vitasdk/arm-vita-eabi/lib/libvitaGL.a \
  vgl.o gxm.o splashscreen.o custom_shaders.o
strings -a splashscreen.o | grep '#6e7fe40'

# With commit 6e7fe402 checked out in /tmp/vitaGL-6e7fe40:
make -C /tmp/vitaGL-6e7fe40 clean
make -C /tmp/vitaGL-6e7fe40 NO_DEBUG=1 -j"$(nproc)"
mkdir -p /tmp/vgl-installed-objects /tmp/vgl-rebuilt-objects
(cd /tmp/vgl-installed-objects && \
  /usr/local/vitasdk/bin/arm-vita-eabi-ar x \
  /usr/local/vitasdk/arm-vita-eabi/lib/libvitaGL.a)
(cd /tmp/vgl-rebuilt-objects && \
  /usr/local/vitasdk/bin/arm-vita-eabi-ar x \
  /tmp/vitaGL-6e7fe40/libvitaGL.a)
for object in /tmp/vgl-installed-objects/*.o; do
  cmp "$object" "/tmp/vgl-rebuilt-objects/$(basename "$object")" || exit 1
done

/usr/local/vitasdk/bin/arm-vita-eabi-nm -nC \
  ../../dist/RenegadeVita-A2.2.elf | \
  grep -E 'RenegadeVitaRenderer::Initialize|vglInit|scene_reset|splash|shark'

/usr/local/vitasdk/bin/arm-vita-eabi-objdump -d -C \
  --start-address=0x8100308c --stop-address=0x810030f8 \
  ../../dist/RenegadeVita-A2.2.elf

/usr/local/vitasdk/bin/arm-vita-eabi-objdump -d -C \
  --start-address=0x8105adb8 --stop-address=0x8105b830 \
  ../../dist/RenegadeVita-A2.2.elf

/usr/local/vitasdk/bin/arm-vita-eabi-objdump -d -C \
  --start-address=0x8104c850 --stop-address=0x8104cce0 \
  ../../dist/RenegadeVita-A2.2.elf

/usr/local/vitasdk/bin/arm-vita-eabi-objdump -d -C \
  --start-address=0x8104cf28 --stop-address=0x8104d1a0 \
  ../../dist/RenegadeVita-A2.2.elf

/usr/local/vitasdk/bin/arm-vita-eabi-objdump -d -C \
  --start-address=0x81052208 --stop-address=0x81052e70 \
  ../../dist/RenegadeVita-A2.2.elf
```
