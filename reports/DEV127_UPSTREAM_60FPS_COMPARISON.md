# Native Vita port comparison — Dev127, 2026-09-14

Target: 60 FPS / 16.667 ms per presented gameplay frame. This comparison does
not establish that Renegade or every referenced port sustains 60 FPS. Physical
testing remains held by the user's instruction. Source was inspected at the
pins below in the external reference cache; no game implementation was copied.

## What the comparable projects actually do

| Project and pinned revision | Primary evidence and technique | Transfer to Renegade |
|---|---|---|
| vitaQuake, `fbe7c5e7fe77aa35c69421b721ddf5dbb58adc27` | [README](https://github.com/Rinnegatamante/vitaQuake/blob/fbe7c5e7fe77aa35c69421b721ddf5dbb58adc27/README.md) advertises native resolution and optional MSAA, not a fixed-scene sustained-60 result. `source/gl_vidpsp2.c` uses a small set of shader variants and array/object submission; `sys_psp2.c` selects clocks and configurable presentation. GPLv3 project. | Current candidate requests native clocks, caches invariant state/material work and keeps original WW3D material batches. Do not assume a much simpler Quake scene proves Renegade's budget. |
| vitaQuakeIII, `7da5c6fbd8d80364ef46aeb936c5ad49ec8126ec` | [Author's release post](https://www.psx-place.com/threads/release-vitaquakeiii-ioquake3-port-for-psvita-quake-iii-quake-iii-team-arena-openarena.34480/) credits multitexturing and compression; also offers lower resolutions and later renderer threading. [tr_shade.c](https://github.com/Rinnegatamante/vitaQuakeIII/blob/7da5c6fbd8d80364ef46aeb936c5ad49ec8126ec/code/renderergl1/tr_shade.c) uses indexed draws and original tessellation batches. `code/psp2` implements renderer-thread handoff. No general native-resolution sustained-60 proof found. GPLv2 code treated as study-only. | Indexed reuse is now implemented below WW3D, without reordering materials or transparency. Two texture stages already share a draw. Compression is promising but requires the boundary work below. A render thread needs an immutable command/geometry snapshot; moving live MeshClass/HTree/texture owners between threads is unsafe. |
| vitaRTCW, `21fe39f2018ce55757cb3ac7cfd4b40a30adc0dd` | [Renderer](https://github.com/Rinnegatamante/vitaRTCW/blob/21fe39f2018ce55757cb3ac7cfd4b40a30adc0dd/code/renderer/tr_shade.c) preserves id-engine indexed shader batches; `tr_cmds.c` separates command construction/execution, and the platform sets clocks. No primary fixed-scene sustained-60 result found. GPLv3 project with upstream file notices. | Useful campaign/AI comparison, but its command architecture is not a drop-in WW3D renderer. Preserve original Renegade simulation and scripting; do not lower NPC cadence to match a benchmark. |
| vitaXash3D, `37ec148715d8aa9b9e116bc71175106853d02390` | [Releases](https://github.com/fgsfdsfgs/vitaXash3D/releases) report memory/stability and modest performance improvements. `engine/platform/vita/vid_vita.c` explicitly selects no MSAA and supports configurable resolution. Current repository is deprecated. No primary universal-60 proof found. GPLv3. | Its visual workload differs from Renegade's current 960x544/4x-MSAA configuration. Larger pools can avoid allocation failure but do not establish faster frames; budget from high-water evidence. |
| OpenLara, `3b268ca4bf986c380f44a26ffd9218bf6d376249` | [Native GXM backend](https://github.com/XProger/OpenLara/blob/3b268ca4bf986c380f44a26ffd9218bf6d376249/src/gapi/gxm.h) keeps static GPU vertex/index data, rotates dynamic storage, caches texture binding and uses compiled shaders. BSD-2-Clause. No primary representative sustained-60 measurement found in the inspected source. | Persistent geometry is a strong next architectural route. Our current reuse removes repeated corners within a batch; persistent buffers additionally require original mesh/lighting/UV mutation generations and deferred GPU retirement. OpenLara is a different engine, so importing its scene/animation system would violate this port's ownership contract. |
| SRB2Kart Vita, `8d7ff0d9579f523185760d502dc4612f448e0f30` | [Maintainer README](https://github.com/Esodland/SRB2Kart-PSVita-PSTV/blob/8d7ff0d9579f523185760d502dc4612f448e0f30/README.md) reports roughly 60 FPS average at 640x368, versus roughly 40 at 960x544. Its performance preset also disables models/skyboxes and limits sprite range. Profiling identified presentation and mid-race asset I/O; bounded precaching removed stalls. GPLv2 study-only. | Strong evidence for separating CPU, GPU/presentation and I/O measurements. It does not prove native-resolution full-quality 60 FPS. Renegade now bounds music decoding and removes redundant movie transfers; no corresponding quality cuts were adopted. |

## Work implemented and checked locally

- Preserve indexed vertices through the existing native fixed-function path:
  486834 corner emissions become 99138 unique emissions in the fixed host mesh
  fixture, with the same 41 draws. Production mesh and generic DX8 loops compare
  784560 corners; the pinned VitaGL/GXM recording sink compares another 540000.
  Original final color/UV/normal state and deferred index storage are covered.
- Compact unlit immediate vertices: single-texture stride 96 to 36 bytes. Lit
  layout remains unchanged. Do not multiply this reduction into a claimed FPS.
- Reuse per-pass material/light results and texture-object sampler parameters.
  Material fixture evaluations 2621440 to 163840; normalized light computations
  10485760 to 160. These are operation counts, not native timing measurements.
- Movie upload storage 524288 to 307200 bytes at the same 320x240 upload
  dimensions; steady full-update copying 831488 to 307200 bytes. Preserve the
  old GPU image until retirement, and skip conversion of dropped frames.
- Bound MPEG PCM storage, correct audio buffer lifetime, enable the pinned
  FFmpeg speed build and request/log native clocks. Keep original audio rates,
  simulation, asset ownership and render resolution/MSAA.

## Compression route: concrete prerequisites, not a disabled-capability guess

Renegade's `Load_DDS_Texture` currently decodes DXT into retained CPU surfaces
and uploads RGBA. VitaGL maps DXT1/3/5 to native UBC formats. Source block payloads
would need approximately one eighth/one quarter of RGBA storage for DXT1/DXT5
before mip/alignment overhead, and could reduce texture bandwidth without new
retail compression. This is a design estimate, not a measured frame-time gain.

Inspection of the actual pinned dependency `6e7fe40292e8f1d10f9a94ff2cd2f4fb1ba452a5`,
`source/utils/gpu_utils.c::gpu_alloc_compressed_texture`, found blockers:

1. The generic power-of-two transfer branch uses `w/4,h/4`, including 1x1/2x2
   dimensions, which become zero block extents. However, original DDSFileClass
   drops its two smallest levels and clamps dimensions to at least 4x4. This is
   not a blocker for its usual chain. A bounded compressed path should validate
   every retained level and fall back for incompatible/non-square mip layouts.
2. Failed mip reallocation falls back to allocation followed by an unchecked
   copy. Initial allocation failure also needs reliable propagation to callers;
   the current GL error check alone is insufficient.
3. `Upload_Texture_Level_From_Surface` currently updates one RGBA level. An
   edited compressed texture must transactionally reconstruct its entire RGBA
   chain, retain every original CPU SurfaceLevel and account for new resident
   bytes. Mixed compressed/RGBA levels in one GXM texture are invalid.
4. Original DDS RGB565 expansion shifts bits without replication; its color
   interpolation uses integer weights summing to 255 then divides by 256.
   Native UBC output cannot be assumed byte-identical to that software fallback.
   Compare transparent DXT1, DXT5 alpha, mip tails and non-square textures while
   preserving original source payloads and intended hardware texture semantics.

Compression is therefore **investigated, not integrated or exhausted**. A safe
next implementation requires production-function allocator/swizzle tests and a
transactional writable fallback before native sampling can be assessed. Do not
globally enable DX8Caps::SupportDXTC or alter retail files to bypass these gates.

## Remaining performance decisions

The last physical session averages about 13.1 FPS, with cumulative render59.7ms
and simulation16.5ms; it is changing gameplay, not a fixed benchmark. Its total
budget is roughly 4.6 times the 60-FPS frame budget. The local operation reductions
are substantial but cannot predict the new bottleneck, GPU wait or tail latency.

Persistent GPU geometry, immutable renderer command handoff, native compressed
textures and Bink YUV presentation remain architectural routes with explicit
ownership/lifetime prerequisites. Resolution/MSAA changes need a GPU-bound
measurement and visual comparison. Compiler speedhacks, reduced NPC/physics
cadence and a replacement renderer are rejected. The IDCT prototype did not
improve host median and was not integrated. No claim that every route is
exhausted, no new physical test presented, and no 60-FPS acceptance claimed.
