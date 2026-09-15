# Substantial renderer work-reuse batch

Status: source implemented, unbuilt, untested, performance adoption deferred.
Current user direction: implement source-identifiable optimizations now; collect
measurements afterward. No Dev110 tests or further builds/tests during this
optimization pass. Measurements are not a prerequisite for removing demonstrable
redundant work; they remain necessary for quantified gains and release acceptance.
The installed Dev110 fast package predates this work. No new candidate label,
build, test, emulator launch or physical access occurred in this work unit.
Previous goal turn classified as progress: Dev110 correctness integration and
completed fast build; pending install now returned INSTALLED_NOT_LAUNCHED.

## Demonstrated costs, not an FPS promise

Retained Dev109 runtime at 240 gameplay frames reports 138746 sampler updates,
zero sampler skips and 2078089 submitted mesh triangles. Original TextureClass
applies binding, min/mag/mip and U/V sequentially. The native sampler translator
writes all four GL parameters after each changed state. The pinned local VitaGL
implementation mutates the texture object and GXM descriptor on those calls;
binding a texture does not restore an independent stage sampler.

Native Submit_Mesh evaluates material colors, light directions and transformed
normals for each triangle corner, even when another triangle in that same pass
already evaluated the identical vertex. These are demonstrated repeated-work
paths. The log is an uncontrolled user run, not a baseline FPS benchmark.

## Implemented boundary changes

- FreeType preparation caches the selected size and last successfully rendered
  glyph per owned face. Measure/rasterize reuse the same slot; changing size,
  character or bold style invalidates it, as do load/render failures. Emboldening
  is not reapplied to a cached bitmap. Measurement reads height from the selected
  face rather than finding/selecting it again. Aliases with identical ordered
  retail candidate lists share the same face/font bytes. Original hinting flags,
  96-DPI sizing, bearings, spacing, raster coverage and FontChars glyph ownership
  remain. No new glyph bitmap allocation or cross-face glyph sharing.
- TextureClass's existing-native-texture constructor releases its temporary
  GetSurfaceLevel reference after reading metadata. Its separate D3DTexture
  reference remains the long-lived owner. This closes an unbalanced reference
  that could retain CPU surface storage after wrapper lifetimes; it is a source
  ownership correction, not measured leak closure or an FPS result.
- Original native dynamic DX8 and sorting vertex/index buffers share a capped
  approximately 1.5x capacity-growth helper instead of reallocating at every new
  exact-size request. The 5000-entry floor and 65535-entry valid capacity ceiling
  remain; logical draw sizes, FVF, lock flags, reference ownership, offsets and
  frame reset are unchanged. The native-only staging patch leaves desktop growth
  unchanged. Spare/retained old-buffer memory remains a later measurement item.
- Deformed-skin position/normal scratch now grows geometrically (256 through
  16384 entries) instead of reallocating both arrays at every small increase in
  mesh size. Requests above 16384 retain exact allocation, not an artificial
  mesh limit. Original HTree deformation, logical vertex count, failure handling
  and shutdown release remain. This trades bounded spare capacity for fewer
  allocations during increasing-size character encounters, not less animation.
  Growth still temporarily owns old plus new arrays; later peak-memory evidence
  must include that transient allocation, not just retained capacity.
- Original DXT1/DXT5 Get_4x4_Block now prepares a four-color stack palette once
  per block. Pixel loops select existing interpolated colors rather than repeat
  Combine_Colors calls. DXT1 transparent-index detection and DXT5 alpha values
  remain separate and unchanged. No global mutable cache or additional heap.
  Registered zero-fuzz patch: ww3d2-a35-dds-block-palette-precompute.patch.
- Aligned DXT1/DXT5 mip levels use original DDSFileClass::Get_4x4_Block to populate
  four CPU-surface rows at a time. Original color endpoints and DXT5 alpha tables
  are shared across each block rather than reconstructed per pixel. RGBA storage
  and checksums still traverse pixels in row-major order. The already-required
  CPU surface doubles as the decoded row cache, with no extra scratch image or
  per-block allocation. Other formats/layouts retain Get_Pixel and conversion.
  The block API's boolean is alpha presence, not a success code.
- DDS native upload preparation now populates RGBA and the retained CPU surface
  in one pixel traversal instead of two. It retains original DDSFileClass pixel
  decode, RGBA storage helper, surface conversion, checksum order and mip uploads.
  Row addresses and surface byte width are hoisted outside the inner loop. This
  load-time change is independent of renderer mode bits; no encoded asset,
  orientation, format or image dimensions are changed.
- Indexed-draw preparation can combine bounds validation and geometry checksums
  in one traversal. Each reference is checked before vertex access; header and
  checksum word order, repeated references and rejected-draw behavior remain.
  A partial checksum is not committed on failure. No FVF, triangle, transform or
  draw order changes. The separate baseline traversal remains selectable.
- Native original Render2DSentence atlas creation can use the existing
  surface-backed TextureClass constructor, skipping blank texture creation and
  the subsequent CopyRects replacement upload. Only completed A4R4G4B4 atlases
  take this path; other formats retain conversion through the original baseline.
  Glyph layout, original CPU surface ownership, renderer assignment and reference
  release are unchanged. The new zero-fuzz staging patch is registered in the
  single authoritative script; no manual inventory count was changed.
- A fixed 1024-slot native-object sampler memo compares translated GL parameters
  and writes only changed parameters. Hash collisions evict performance history,
  not rendering state. Stage binding remains independent; shared texture objects
  share the memo. Upload/external state invalidation, deletion and logical backend
  reset clear it. Failed writes cannot be memoized as successful state.
  Global object-memo invalidation uses a generation bump rather than clearing
  1024 entries on every upload/delete/external-GL boundary. Generation wrap
  clears the table before reusing one; zero tags represent unknown/failed state.
  Small per-stage caches still reset normally. No resource name or native state
  is treated as valid solely because an entry occupied that slot previously.
- Material color results are reused only inside the current mesh material pass,
  keyed by vertex and guarded by material identity. Original evaluation and
  skin-color handling remain unchanged. Nothing survives semantically across a
  pass, mesh, frame, deformation, lighting change or load. Scratch is bounded to
  8192 vertex entries. Large meshes use direct-mapped entries with explicit
  vertex/material keys; collisions replace cached results rather than returning
  another vertex's color. Smaller meshes remain collision-free. Failed
  allocations use the old path. Generation tags invalidate each pass in O(1),
  avoiding a per-pass sweep of up to 8192 entries. Allocation initializes tags
  once; unsigned generation wrap clears the entire allocated capacity before
  reusing tag one. Zero-tag entries never satisfy an active pass. Shutdown resets
  generation with scratch ownership.
  Scratch is released on logical shutdown. Peak growth temporarily owns old plus
  new arrays; both are individually bounded by 8192 entries.
- With material reuse enabled, normalize the original light environment's at-most
  four directions once per mesh pass instead of once per evaluated vertex. The
  same Normalize_Or_Default operation, default direction, light order, dot product,
  diffuse accumulation and clamp remain. Directions are stack-local, not retained
  across passes or frames. The baseline and scratch-fallback paths still perform
  the original per-vertex normalization. Sampled light_normalizations counters
  expose the actual operation count in each mode. Ambient/material colors and
  per-vertex normals are not replaced by a different lighting model.
- Sampled counters every 120 rendered frames report actual sampler parameter
  writes, material evaluations/hits, fallback passes and retained storage.
- Baseline remains default. A startup-only user config flag provides same-SELF
  mode selection, without frame-time file polling or an emulator modification.

## Exact A/B selector

Optional local file: ux0:data/renegade/user/config/render-work-cache-v1.flag.
Exactly eight ASCII bytes, including LF: `RVRC1 0\n` baseline, `RVRC1 1\n`
sampler only, `RVRC1 2\n` material only, `RVRC1 3\n` sampler plus material.
Bit 4 enables direct atlas upload: `RVRC1 4\n` atlas only, `RVRC1 7\n` all
three; modes 5 and 6 select the corresponding pairs. Bit 8 selects fused indexed
preparation: `RVRC1 8\n` alone, `RVRC1 F\n` all four groups. The single selector
character is uppercase hexadecimal 0..F; logs and manifests use integer 0..15.
Other contents,
missing file or read failure select baseline. Restart is required. Do not ship
development flags or user files. Existing installed Dev110 does not support it.

## Required comparison before adoption

Offline comparison tooling is implemented in tools/compare_render_work_reuse.py,
not executed or tested. It compares consecutive captured benchmark CSV windows,
requires equal SELF/retail/checkpoint/route/emulator/config hashes and warmup,
checks CSV hashes, rejects missing frames, readback and renderer failures, and
withholds timing deltas when frame-by-frame workload counters differ. It reports
median/p95/p99/worst and memory low-water; it never grants adoption or acceptance.

Each input is a JSON manifest with schema `renegade-render-work-run-v1`, `csv`
(path relative to manifest), `csv_sha256`, `self_sha256`, `retail_sha256`,
`checkpoint_sha256`, `route_sha256`, `emulator_sha256`, `emulator_config_sha256`,
integer `mode`, `start_frame`, `end_frame`, `warmup_frames`, and true attestations
`development_input_disabled` and `compiler_idle`. Hashes must be lowercase SHA-256.
Start/end are inclusive capture frame numbers; at least 120 consecutive active
benchmark frames are required. Manifest claims need independent retained receipts.
Invoke with `--baseline manifest.json --candidate manifest.json --output report.json`;
output is exclusively created, never overwritten. Source implementation is not
evidence that any actual comparison has passed.

Use one matching SELF and unchanged retail identity, original save/start state,
fixed camera/input route and equal warmup. Disable the development file-input
channel before performance runs; no concurrent compiler. Compare all modes,
including repeated baseline runs, with median/p95/p99/worst, simulation/render/
present timing, cache counters and system/GPU memory high-water. Keep loading,
shader compilation, capture and diagnostic I/O costs separately labelled.

Correctness checks must cover shared texture stages, alternating filter/wrap,
native-name reuse, upload invalidation, eviction, failed native calls, distinct
materials/passes, animated skins, lighting, scratch fallback and repeat teardown.
Matching geometry counters do not prove visual equality: compare HUD, alpha,
detail textures, world, skins and lighting visually. No changes to original
physics, collision, animation, networking, serialization or scene ownership.

Atlas comparisons must include changing pickup names/counts, target labels,
dialogue and loading text, rectangular surfaces, alpha coverage and repeated
release/recreate. Direct-atlas requests count selection, not successful uploads;
use existing upload/failure/residency counters and visual captures as well.

Before/after timing, visual result and adoption decision: PENDING. No 60 FPS+
or physical performance claim. This is the first integrated part of the larger
batch, not a declaration that the FPS overhaul or M00 demo is complete.
