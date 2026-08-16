# A2.2 Vita Renderer Initialization Diagnostics

Date: 2026-08-07

Scope: the Vita graphics boundary only. The physical A2.2 results validate the
original Westwood file, archive, W3D, prototype, hierarchy, material, HLOD, and
`RenderObj` path; none of those systems are implicated here.

## Finding

The reported renderer-init failure was caused by interpreting the return value
of `vglInit` as a success Boolean. It is not a success Boolean in the installed
vitaGL.

The installed declaration is:

```c
GLboolean vglInit(int legacy_pool_size);
```

The implementation returns `res_fallback`:

- `GL_FALSE` means the requested display resolution was accepted unchanged.
- `GL_TRUE` means width/height exceeded the maximum framebuffer resolution and
  vitaGL substituted the maximum supported resolution.
- It does not return a general initialization-success value.
- A repeated call after vitaGL is already initialized also returns `GL_FALSE`,
  so the raw value is not an initialized-state query.

For the normal 960x544 request on a Vita, `vglInit(4 * 1024 * 1024)` is expected
to return zero. The old renderer treated that expected value as failure and
returned before issuing a clear.

The hardware log itself proves `vglInit` returned: the application wrote the
coarse renderer-failure result after the renderer call. Therefore case A
(`vglInit` never returns) is disproved for the tested build.

## Why the vitaGL logo kept spinning

The installed vitaGL starts its splash renderer on a separate thread during
`vglInit`. The splash is deliberately open-ended until normal rendering begins.

- `vglSwapBuffers()` returns immediately while the splash-active flag is set.
- A rendering operation that reaches vitaGL's private `scene_reset()` performs
  the transition: it signals the splash thread, waits for its one-second fade,
  frees the splash resources, and begins the application's GXM scene.
- `glClear()` reaches `scene_reset()` and is the safest explicit first-frame
  transition.

Thus the observed behavior is case D: `vglInit` returned zero (no resolution
fallback), the backend incorrectly returned failure, and no `glClear` ever
requested the transition away from the asynchronous splash. A swap by itself
would not have fixed it.

The decisive initialization-only proof sequence is:

```c
GLboolean resolution_fallback = vglInit(4 * 1024 * 1024);
/* raw value is diagnostic only; do not fail when it is GL_FALSE */
glClearColor(r, g, b, 1.0f);
glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
vglSwapBuffers(GL_FALSE);
```

After that one solid-color clear/present succeeds, execution can immediately
continue through the original `SimpleScene -> Camera -> WW3D::Render ->
RenderObj -> MeshClass::Render` path.

## Installed toolchain authority

The inspected installed files are:

| Component | Installed path | Identification |
| --- | --- | --- |
| vitaGL header | `/usr/local/vitasdk/arm-vita-eabi/include/vitaGL.h` | SHA-256 `ba68004be9faf49fa4b0526ecbcdf26c3b4b8d001f85e119ce35db26a3f70e3a`; exact match for vitaGL commit `6e7fe40292e8f1d10f9a94ff2cd2f4fb1ba452a5` |
| vitaGL archive | `/usr/local/vitasdk/arm-vita-eabi/lib/libvitaGL.a` | SHA-256 `bcc414e745a1f29940f7c33418f268c4cd78d0388b7a0da0f036b72355597b69`; splash embeds short revision `6e7fe40` |
| vitaShaRK header | `/usr/local/vitasdk/arm-vita-eabi/include/vitashark.h` | SHA-256 `b746269bf5c22a8fd59d9c2cf8aba482e40a6e7c838ec50f3c809d94bdb620d8`; matches vitaShaRK commit `5d99fe81a4a384c5e4e7a8cba2d851df8dbda5da` |
| vitaShaRK archive | `/usr/local/vitasdk/arm-vita-eabi/lib/libvitashark.a` | SHA-256 `7b0c4a7aaa3e5e50a5b18083cccf2ce7b98a993380bd3ac1739f863368dd32b6` |

The installed vitaShaRK is the older API with `shark_init`; it does not export
the later `shark_init_simple` interface.

## Safest persistent breadcrumb writer

For a temporary hardware probe, use the native Vita I/O APIs and make each
breadcrumb independently durable:

1. Format one bounded record into a fixed stack buffer.
2. Open `ux0:data/renegade/user/logs/a22-runtime.log` with
   `SCE_O_WRONLY | SCE_O_CREAT | SCE_O_APPEND`.
3. Loop on `sceIoWrite` until every byte has been accepted. Record negative,
   zero-length, and short-write failures; do not assume one call writes all
   bytes.
4. Call `sceIoSyncByFd(fd, 0)`.
5. Call `sceIoClose(fd)`.

Required include/link pair:

```c
#include <psp2/io/fcntl.h>
/* target_link_libraries(... SceIofilemgr_stub) */
```

Minimal write loop:

```c
SceSSize total = 0;
while ((SceSize)total < length) {
    SceSSize rc = sceIoWrite(fd, line + total, length - (SceSize)total);
    if (rc < 0) { result = (int)rc; break; }
    if (rc == 0) { result = LOCAL_SHORT_WRITE_ERROR; break; }
    total += rc;
}
int sync_rc = sceIoSyncByFd(fd, 0);
int close_rc = sceIoClose(fd);
```

Opening, syncing, and closing for every important BEFORE/AFTER marker is slower
than keeping one descriptor open, but initialization is one-shot and this is
the most robust choice for a hang/crash probe. It preserves the last completed
operation even if a later graphics call never returns. The log directory must
already exist; the current platform bootstrap creates it before renderer init.

Use a monotonically increasing sequence number and log every return code in
both signed decimal and unsigned hexadecimal, for example:

```text
[A2.2 renderer-init 006] BEFORE vglInit legacy_pool=4194304
[A2.2 renderer-init 007] AFTER vglInit raw=0/0x00000000 meaning=no-resolution-fallback call_completed=1
```

Do not recursively log a logger failure through the same logger. A sync result
cannot be added to the record that was just synced without performing another
write and sync; retain it for an on-screen fallback or the next successful
record. If diagnostic wrappers can log from multiple threads, protect sequence
allocation and whole-record emission with a Vita kernel mutex. The ordinary
pre-init/post-init path is single-threaded.

## Free-memory diagnostics

Use the public kernel memory query immediately before and after `vglInit`:

```c
#include <psp2/kernel/sysmem.h>

SceKernelFreeMemorySizeInfo info = {};
info.size = sizeof(info);
int rc = sceKernelGetFreeMemorySize(&info);
```

Log `rc`, `size_user`, `size_cdram`, and `size_phycont`, each in decimal and
hexadecimal. Required link library: `SceSysmem_stub`.

After `vglInit` returns, also log vitaGL's public heap counters separately:

```c
vglMemTotal(VGL_MEM_RAM);     vglMemFree(VGL_MEM_RAM);
vglMemTotal(VGL_MEM_VRAM);    vglMemFree(VGL_MEM_VRAM);
vglMemTotal(VGL_MEM_SLOW);    vglMemFree(VGL_MEM_SLOW);
vglMemTotal(VGL_MEM_BUDGET);  vglMemFree(VGL_MEM_BUDGET);
```

`VGL_MEM_VRAM` is CDRAM, `VGL_MEM_RAM` is USER_RW, `VGL_MEM_SLOW` is PHYCONT,
and `VGL_MEM_BUDGET` is CDLG. Individual values are clearer than relying only
on the aggregate `VGL_MEM_ALL` value.

For the current unconfigured `vglInit(4 MiB)` call, the exact requested policy
is:

- display 960x544, stride 960, triple buffering;
- color `SCE_GXM_COLOR_FORMAT_A8B8G8R8`;
- depth/stencil `SCE_GXM_DEPTH_STENCIL_FORMAT_DF32M_S8`;
- `SCE_GXM_MULTISAMPLE_4X`;
- immediate/legacy vertex pool 4 MiB;
- circular pool 32 MiB;
- USER_RW pool: free USER_RW measured after GXM initialization minus a 16 MiB
  reserve (or zero if at/below the reserve);
- CDRAM pool: available CDRAM with a zero reserve;
- PHYCONT pool: available PHYCONT with a zero reserve;
- CDLG pool: zero (`SCE_KERNEL_MAX_MAIN_CDIALOG_MEM_SIZE` is retained as the
  threshold);
- default GXM rings: parameter 16 MiB, VDM 128 KiB, vertex 2 MiB, fragment
  512 KiB, fragment USSE 16 KiB;
- shader patcher allocations: 1 MiB general, 1 MiB vertex USSE, 1 MiB fragment
  USSE.

The pre-call kernel measurement is not byte-for-byte identical to the value
vitaGL uses for its pools, because `vglInitWithCustomThreshold` first runs
`init_gxm()` and only then queries free memory.

## libshacccg/vitaShaRK diagnostics

The two exact paths attempted by the installed libraries are:

1. vitaShaRK default: `ur0:/data/libshacccg.suprx`
2. vitaGL retry: `ur0:data/external/libshacccg.suprx`

The splash uses precompiled GXP shaders, so a visible splash does not prove the
runtime shader compiler is available.

Safe read-only prerequisite checks before `vglInit` are:

```c
#include <psp2/io/stat.h>
#include <psp2/io/fcntl.h>

SceIoStat st = {};
int stat_rc = sceIoGetstat(path, &st);
bool regular = stat_rc >= 0 && SCE_S_ISREG(st.st_mode);
SceUID fd = sceIoOpen(path, SCE_O_RDONLY, 0);
int close_rc = fd >= 0 ? sceIoClose(fd) : 0;
```

Log the exact path, `stat_rc`, type/mode, byte size, open result, and close
result. This proves existence and readability only, not successful module
startup or shader compilation.

Do not use `sceSysmoduleIsLoaded(SCE_SYSMODULE_SHACCCG)` as the deciding probe.
vitaShaRK loads an external SUPRX through `sceKernelLoadStartModule`, which is
not equivalent to the firmware sysmodule-loading path queried by that API.

An optional non-mutating post-init inventory is:

```c
#include <psp2/kernel/modulemgr.h>

SceUID ids[64];
SceSize count = 64;
int list_rc = sceKernelGetModuleList(0x80 | 0x01, ids, &count);
for (SceSize i = 0; list_rc >= 0 && i < count; ++i) {
    SceKernelModuleInfo mi = {};
    mi.size = sizeof(mi);
    int info_rc = sceKernelGetModuleInfo(ids[i], &mi);
    /* log rc/name/path/state; look for the exact libshacccg path */
}
```

This requires `SceKernelModulemgr_stub`. It confirms that a matching module is
loaded, but still does not expose vitaGL's private `is_shark_online` decision.

For exact, side-effect-free initialization return codes, use a diagnostic-only
GNU linker wrapper:

```c
extern "C" int __real_shark_init(const char *path);
extern "C" int __wrap_shark_init(const char *path)
{
    breadcrumb("BEFORE shark_init path=%s", path ? path : "<default>");
    int rc = __real_shark_init(path);
    breadcrumb("AFTER shark_init path=%s rc=%d/0x%08X",
        path ? path : "<default>", rc, (unsigned)rc);
    return rc;
}
```

Link with `-Wl,--wrap=shark_init`. This sees both vitaGL attempts without
changing their order or result. If the exact SUPRX module UID/error and
extension/allocator results are needed, the same diagnostic technique can wrap:

- `sceKernelLoadStartModule`
- `sceShaccCgExtEnableExtensions`
- `sceShaccCgSetDefaultAllocator`

Do not call `shark_init(NULL)` after `vglInit` merely as a status query. It is
idempotent only after a successful earlier call. If vitaGL's attempts failed,
the probe is another state-mutating load attempt; if that new attempt succeeds,
vitaGL's private `is_shark_online` flag can remain false. A zero result is
therefore ambiguous between "already initialized" and "initialized by this
probe." Use the wrapper, module inventory, or an actual compile/link test.

The most authoritative functional test is a tiny shader create/compile/link
operation with `glGetShaderiv(..., GL_COMPILE_STATUS, ...)`,
`glGetProgramiv(..., GL_LINK_STATUS, ...)`, and info logs. That can be deferred
until after the solid-color clear/present proves the immediate failure is fixed.

## Display and presentation diagnostics

These public queries can be performed before and after initialization:

```c
#include <psp2/display.h>

int max_w = 0, max_h = 0;
int max_rc = sceDisplayGetMaximumFrameBufResolution(&max_w, &max_h);

SceDisplayFrameBuf fb = {};
fb.size = sizeof(fb);
int fb_rc = sceDisplayGetFrameBuf(&fb, SCE_DISPLAY_SETBUF_IMMEDIATE);

float refresh = 0.0f;
int refresh_rc = sceDisplayGetRefreshRate(&refresh);
int head = sceDisplayGetPrimaryHead();
```

Log exact return codes plus framebuffer `base`, `pitch`, `pixelformat`, `width`,
and `height`. Required link library: `SceDisplay_stub`.

After `vglInit`, useful public vitaGL/GL postconditions are:

- `glGetString(GL_VENDOR)`, `GL_RENDERER`, and `GL_VERSION`;
- `glGetIntegerv(GL_VIEWPORT, ...)`;
- `glGetIntegerv(GL_DEPTH_BITS, ...)` and `GL_STENCIL_BITS`;
- `vglGetFrameNumber()` before and after the first present;
- a fresh `glGetError()` after each void GL operation.

Drain/log any pre-existing GL errors before a tested operation; otherwise the
next `glGetError()` can be incorrectly attributed to that operation.
`vglSwapBuffers` itself is `void`; a following `glGetError` is not its return
code. The frame counter and `sceDisplayGetFrameBuf` are the useful public
postconditions.

## What cannot be proven outside opaque `vglInit`

The public API has no getters for vitaGL's private GXM context, render target,
depth/stencil allocation, shader patcher, clear programs, default index buffers,
state cache, immediate vertex pool, or default texture. `vglInit` also ignores
many returned GXM/allocation errors internally. Reaching its final return proves
that control traversed those source blocks; it does not prove every internal API
returned success.

Consequently a post-call breadcrumb should say:

```text
vglInit reached final return; internal stages traversed (individual return codes opaque)
```

It should not label every internal subsystem "complete" based solely on that
return.

If a later physical result requires exact internal codes, the least invasive
escalation is a diagnostic link with `--wrap` around the public functions that
the static vitaGL archive calls, including:

- `sceGxmVshInitialize`
- `sceKernelAllocMemBlock` and `sceKernelGetMemBlockBase`
- `sceGxmMapMemory`, vertex-USSE and fragment-USSE map functions
- `sceGxmCreateContext`
- `sceGxmCreateRenderTarget`
- `sceGxmColorSurfaceInit`
- `sceGxmSyncObjectCreate`
- `sceGxmShaderPatcherCreate`
- `sceGxmShaderPatcherRegisterProgram`
- `sceGxmShaderPatcherCreateVertexProgram`
- `sceGxmShaderPatcherCreateFragmentProgram`
- `sceKernelCreateSema`, `sceKernelCreateThread`, and
  `sceKernelStartThread` for splash startup.

Do not wrap the I/O calls used by the breadcrumb writer. Wrappers invoked by
the splash or garbage-collector threads must serialize their log writes.
Depth/stencil initialization in this vitaGL revision is an inlined private
helper that always returns zero after filling the GXM descriptor; exact
source-level breadcrumbs there require rebuilding an instrumented vitaGL.
The vertex/index/texture/state-cache setup is likewise private, and much of it
has no independent return value.

Given the confirmed return-value bug and working animated splash, that invasive
escalation is not justified for the next build.

## Recommended breadcrumb order for the next hardware build

1. Renderer entry.
2. Free kernel memory before init.
3. Maximum/current display information before init.
4. `sceIoGetstat`/read-open results for both libshacccg paths.
5. Exact display, MSAA, heap-threshold, ring-buffer, shader-patcher, circular,
   and legacy-pool configuration.
6. BEFORE `vglInit` (durably synced).
7. AFTER `vglInit`, logging raw return strictly as resolution-fallback state.
8. Free kernel memory and vitaGL heap totals/free after init.
9. Shader-compiler wrapper results or non-mutating module inventory.
10. GL identity, viewport, depth, and stencil queries.
11. BEFORE/AFTER each backend state call, with a fresh GL error result.
12. BEFORE `glClear` with text stating that this begins splash transition.
13. AFTER `glClear`; this proves the splash thread terminated and the main GXM
    scene began.
14. BEFORE/AFTER `vglSwapBuffers`, including frame count and display framebuffer
    query.
15. Successful renderer-init return.
16. Continue into the original scene/camera/WW3D traversal and retain the first
    frame, first mesh, and first present breadcrumbs.

This sequence both fixes the known defect and leaves enough persistent evidence
to isolate the next boundary if physical hardware exposes another one.
