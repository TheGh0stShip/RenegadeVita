# A3.6 Vita performance overhaul (source checkpoint)

Status: source changes with host contracts, local ARM syntax checks and the
CI ARM compile. **No physical PS Vita/PSTV or Vita3K run has been made with
these changes.** Nothing here claims a frame rate; it removes measured and
code-evidenced costs from the game thread. Physical A/B runs are the next step.

## Why

Physical play of the campaign slows down heavily. The repository's own
telemetry ([performance ledger](PERFORMANCE_HYPOTHESIS_LEDGER.md)) and a code
audit of every per-frame path pointed at work the original engine never did
per frame:

- **Mesh submission.** Every visible `MeshClass` was re-emitted vertex by
  vertex through vitaGL immediate mode, with material colour evaluation per
  corner. The Dev194 M13 trace sampled about 17.7 ms of mesh-boundary CPU per
  frame (about 142 meshes, about 393 draw batches) against a 26.5 ms p50 frame.
  The original DX8 renderer instead registered each mesh once in static vertex
  buffers and drew them with hardware transform.
- **First-use texture decode.** Each DDS texture was fully decoded to 32-bit
  on the CPU inside the frame that first drew it, even when the GPU received
  the original DXT blocks. The ledger records 621-780 ms frames with 14-15
  texture decodes and a 2.61 s first M01 frame with 28 decodes. Only M13 and
  M01 prepared their textures during loading.
- **Synchronous memory-card I/O on the game thread.** Every renderer
  breadcrumb synced the card, the 120-frame checkpoint ended with a blocking
  log sync, and the flight recorder reopened and rewrote four sidecar files at
  every checkpoint, objective change and slow frame.
- **Per-frame diagnostics.** A per-index geometry checksum on every indexed
  draw, a full physics-object census and seven allocator statistics walks per
  frame.

## Changes

### Renderer

- **GPU-resident static meshes** (`port/renderer/vita/ww3d_vita_static_mesh_cache.h`,
  `Submit_Static_Mesh_Cache` in `ww3d_vita_renderer.cpp`). Rigid meshes are
  recorded once per (model, user-lighting array), exactly in the immediate
  path's state-run order, uploaded to vitaGL buffers and replayed with the same
  shader/texture/stage state sequence and one indexed draw per run.
  - Eligible: non-skin meshes whose active stages use pass-through UVs without
    a texture transform or mapper. Lit materials are included; their inputs
    (light environment ambient and up to four world-space lights, the DX8
    ambient without an environment, and the world transform when a light
    contributes) are compared every frame.
  - Lifetime follows the original registration: `DX8MeshRendererClass::Invalidate()`
    (level load, lighting solve, sorting changes) clears the cache, and a
    staged patch forgets entries on model reset/assignment and user-lighting
    replacement. Alternate material descriptions (building power) and material
    state are validated every frame. An entry rebuilt more than four times
    within 1800 frames of each other is marked volatile and returns to the
    per-frame path; 1800 frames without a rebuild forgive earlier ones.
  - Budget: 24 MiB of cached streams (LRU), and builds keep 16 MiB of vitaGL
    memory free. Allocation failures fall back to the per-frame path.
  - A vitaGL dependency patch (`vitagl-attribute-invalidation.patch`) forces a
    full vertex-attribute rebind between array and immediate draws that share
    one fixed-function program.
- Indexed DX8 draws no longer hash every referenced vertex on Vita; bounds
  validation is unchanged.
- Framebuffer MSAA defaults to 2x (was 4x); see the switches below.

### Texture loading

- Natively uploadable DXT textures skip the CPU decode and the retained 32-bit
  copies of every mip; CPU surfaces are decoded lazily on the first
  `GetSurfaceLevel`/`LockRect` (no compiled caller does this for archive
  textures today).
- Non-square DXT textures keep their compressed chain: sub-4-pixel tail mips
  are dropped instead of expanding the whole texture to linear RGBA8888.
- Every non-tutorial level prepares its referenced textures on the loading
  screen, as the original `TextureLoader` did. The budget is 48 MiB of
  additional resident textures with a 24 MiB vitaGL free-memory floor.

### Logging and diagnostics

- `A30_Vita_Log` and renderer breadcrumbs enqueue complete lines into a
  256 KiB ring; one writer thread on user core 2 appends in order and syncs
  within one second. Fatal, final and process-exit paths still block until the
  log is synced. Overflow drops lines and later reports the count.
- The flight recorder's periodic flushes run on a worker that copies the
  recorder under a short lock; shutdown, pre-clean-exit, fatal and final
  flushes remain synchronous once the worker is idle. The copy takes only the
  scalar sections and the ring ranges the flush will write, not the whole
  recorder.
- Flight-recorder audio statistics are sampled every 30 frames instead of
  taking the Miles lock against the mixer every frame.
- The physics census refreshes every 120 frames and backend memory every 30
  frames; the 120-frame checkpoint re-requests the 444/222/222/166 MHz clocks
  if a system transition lowered them.

### Filesystem

- Case-insensitive lookups under the read-only retail data root reuse a
  process-lifetime directory listing instead of rescanning the directory on
  every asset open. Writable roots (saves, configuration) are still scanned
  each time, so files created at runtime are always found.

### Build

- Renderer, WW3D, WWMath and WWPhys translation units build at `-O3`
  (`RENEGADE_VITA_HOT_PATH_O3`, default ON); the target and vitaGL add the
  value-preserving `-fno-math-errno -fno-trapping-math`.
- `WWMath::Fabs` compiles to one VABS (bit-identical).

## Runtime switches for A/B testing

Create these files under `ux0:data/renegade/user/config/` (exact contents,
one trailing newline):

| File | Contents | Effect |
| --- | --- | --- |
| `static-mesh-cache-v1.flag` | `RVSM1 0` | Disable the static mesh cache (per-frame path for every mesh). |
| `msaa-v1.flag` | `RVMSAA1 0`, `RVMSAA1 2` or `RVMSAA1 4` | Framebuffer MSAA samples. |
| `render-work-cache-v1.flag` | `RVRC1 0` .. `RVRC1 F` | Existing render-work cache bits (unchanged). |

Build-time: `-DRENEGADE_VITA_HOT_PATH_O3=OFF` restores `-O2` everywhere;
`-DRENEGADE_VITA_CAMPAIGN_MSAA_SAMPLES=0|2|4` sets the default MSAA.

The runtime log prints a `static-mesh-cache` line every 120 frames (entries,
bytes, hits, builds, rebuilds, ineligible, volatile, evictions,
invalidations, allocation failures) next to the existing `render-work-cache`
and `mesh-boundary-time` lines, which makes before/after comparisons direct.

## Verification

- Host contracts:
  - `tools/test_vita_static_mesh_cache.py`: data model, windows, budget,
    lifetime, lighting signature (ASan/UBSan).
  - `tools/test_vita_static_mesh_equivalence.py`: the production builder
    against both an independent reference and the production immediate loop,
    corner by corner, including mutation checks.
  - `tools/test_renegade_async_log.py`: ordering, overflow, sync cadence
    (ASan/UBSan and TSan).
  - `tools/test_a35_flight_background_flush.py`: background flight flushing
    against synchronous flushing (ASan and TSan).
  - `tools/test_renegade_paths_cache.py`: cached retail lookups against
    uncached lookups, writable roots uncached (ASan/UBSan and TSan).
- The full Python contract suite passes locally apart from the pre-existing
  environment-only errors (no VitaSDK or reference archives in the container).
- The host probe build had two pre-existing failures: a link failure
  (`Debug_Statistics::Record_Texture`), fixed by linking `statistics.cpp`
  into every host target that links `texture.cpp`, and the audio decoder's
  allocation `try`/`catch` under `-fno-exceptions`, fixed by compiling that
  unit with exceptions as the Vita build does.

## Not verified / limits

- No device or emulator run. Frame rate, hitch removal and visual parity are
  unmeasured on hardware.
- Cached colours are 8 bits per channel (the immediate path passes floats);
  the error is below half a step of the 8-bit framebuffer.
- Several instances of one lit model at different positions share a cache key
  and become volatile (per-frame path), as before this change.
- Skinned characters, mapper-animated and environment-mapped materials keep
  the per-frame path.
- Longer loading screens are expected on missions that previously deferred
  their textures.
