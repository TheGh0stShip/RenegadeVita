# Dev127 optimization route audit

Scope: native Vita M00 demo. Physical Dev126 shows render ~59.7ms and simulation
~16.5ms cumulative means; these include changing gameplay, not a fixed camera
benchmark. CPU fixture results below never establish native FPS or visual quality.
No new physical test or deployment during this audit. The user's further
optimization request expanded the implementation after the initial audit.
Final artifact closure is still pending; this is not a performance acceptance.
Latest upstream comparison: DEV127_UPSTREAM_60FPS_COMPARISON.md records six
pinned native ports, their actual FPS evidence and transferable techniques.
Compression, persistent geometry and immutable render handoff remain open;
the route audit is not claimed exhausted. Physical testing stays held.

| Route | Finding and disposition | Evidence / remaining limit |
|---|---|---|
| Compiler target / SIMD | Retain native ARMv7-A+SIMD, Thumb, NEON, hard float and Cortex-A9 tuning. These are installed compiler defaults already. | `arm-vita-eabi-g++ -Q --help=target`; no missing-NEON claim. |
| Engine optimization flags | Retain engine -O2, ABI flags and original floating-point semantics. No global fast-math or -Ofast. | Native compile commands inspected. Broad flag changes lack a measured native benefit and can change code size/cache behavior. |
| Video dependency speed | Candidate: replace FFmpeg size configuration/final -Os with speed configuration/final -O3. | Dependency rebuilt, CONFIG_SMALL off, NEON enabled. Native decode timing comparison pending. |
| Native power policy | Candidate: request 444/222/222/166 CPU/BUS/GPU/XBAR through ScePower APIs, log before/return/actual values. | No kernel/plugin override; actual device policy and battery/thermal behavior require native return. |
| Repeated material lighting | Candidate: per-pass vertex/material cache and normalized light directions. No cross-pass/mesh reuse. | 192000 production result comparisons; collisions, generation wrap, missing inputs, allocation failure; ASan/UBSan pass. Evaluations 2621440 -> 163840; light normalizations 10485760 -> 160 on fixed fixture. |
| Repeated sampler writes | Candidate: texture-object memo plus stage binding cache with generation invalidation. | Ten production object-state cases in both modes, ASan/UBSan; aliasing, failed calls, external writes and name reuse covered. |
| Indexed CPU preparation | Candidate: fuse bounds and checksum traversals; keep original checksum order and delayed commit. | Thirty production cases compare baseline/fused status and checksum, including overflow/rejection; ASan/UBSan. |
| Font atlas uploads | Candidate: seed original TextureClass from its completed A4R4G4B4 atlas. | Same pixel converter and original lifetime; avoids empty upload plus CopyRects. Original other-format fallback retained. Native alpha/visual acceptance remains pending. |
| Immediate GPU vertex storage | Candidate dependency patch: unlit 7/9/11-float layouts instead of 22/24/26; lit path unchanged. | Pinned production glVertex3f/glEnd tested in baseline/patched variants with recording GXM sink, 48 draws each and ASan/UBSan. Single texture 96 -> 36 bytes per vertex. GPU execution/visual acceptance pending. |
| Draw grouping / ordering | Retain existing contiguous texture/material/shader grouping; do not reorder transparent draws or replace WW3D traversal. | Submit_Mesh already keeps a primitive open across equal-state triangles. Cross-owner reordering needs per-draw native timing and visual evidence; no justified local rewrite. |
| Indexed vertex reuse | Further candidate implementation: retain triangle indices through the existing vitaGL immediate FFP draw. Emit each source vertex once within an unchanged WW3D material batch; apply the same reuse to generic DX8 indexed draws. | Production mesh/generic loops compare 784560 corners with baseline; patched vitaGL sink compares another 540000. Material/pass changes, collisions, invalid triangles, 16-bit limits, bounded flushes, unaligned FVF 36/44, base offsets and final inherited attributes pass. No new client-array state or shader path. Native execution pending. |
| Shader/program cache | Retain pinned persistent shader cache and current prewarm. | Lazy shader compilation is separately observed; movie first-draw cost ~23.5ms once, not its steady low FPS. Skipping vitaGL dirty/program updates lacks a complete native state proof; deferred to profile. |
| Video decode vs conversion | Candidate: retain decoded AVFrame until presentation/drop, scale only presented frames. | Dev126 converts 230 decoded frames but drops 115; seven production scheduler tests pass sanitizers. Ownership release covers upload/drop/stop. |
| Movie texture transfer | Further candidate implementation: native linear texture at actual upload dimensions; skip old-pixel copy on a complete aligned RGBA replacement while retaining new GPU allocation/deferred retirement. Configure owned sampler once per texture. | Pinned native allocation and copy/write bodies pass ASan/UBSan, 14 update cases plus allocation failure. 320x240 storage 524288 -> 307200 bytes; used-texture full-update copies 831488 -> 307200 bytes. No additional downscaling. GPU execution/edge sampling and native timings pending. |
| Movie audio buffers | Candidate: aligned alternating blocks, no mutation of submitted pointer before next output, final drain within storage lifetime. | Production queue/thread tests retain pointers, test wrap/order/partial buffers; ASan/UBSan. User audibility remains unverified despite prior API-success counters. |
| Audio queue copy/allocation | Candidate: two contiguous copies instead of modulo per sample; reusable conversion buffer. | Production wrap cases at four offsets and final padding pass. Sample rate, channel order, queue capacity and owner unchanged. |
| MPEG music memory / pause cost | Candidate: fixed ~16KiB PCM window and owned encoded input; scan headers for metadata instead of whole-track decode. | Matching Dev126 crash reaches abort; heuristic stack identifies vector growth in Decode_Mpeg. Generated 1/120-second, mono/stereo, three-rate tests cover seeks, loops, sample output and cleanup with sanitizers. Duration multiplication promoted to 64-bit to avoid native 32-bit overflow above ~90 seconds. |
| MPEG seeking correctness | Candidate: bounded 16-frame pre-roll restores reservoir history for low-rate mono seeks. | Expanded test caught a 320-LSB error at frame21000 with default pre-roll; fixed. Stereo exact; mono feeder/reader quantization differs by at most one signed-16 LSB. |
| WAV/ADPCM decode | Retain existing estimate-based bounded reserve and original codec semantics. | Existing decoder/mixer contract passes; no new measured steady-state defect warrants codec replacement. |
| Asset I/O and lookup | Retain current original MIX/file-owner cache and readonly resolution cache; writable invalidation remains distinct. | Existing file-factory/lookup tests and fresh canonical retail host validation. No evidence of per-frame retail decoding that justifies a new runtime asset format. |
| Resident texture/skin memory | Retain owned textures and bounded reusable skin/material scratch; avoid speculative pool enlargement. | Exact native high-water/fragmentation after reduced music and vertex storage is still needed. No retail compression/resolution changes. |
| Gameplay timers / pacing | Retain monotonic timer units and original simulation cadence. | No unconditional 16.7ms sleep in active gameplay; delays are frontend/suspended/ending paths. vglSwapBuffers(GL_FALSE) already selected. Native presentation wait vs GPU execution remains unmeasured. |
| Physics / AI / path budget | Retain original owners, work cadence and path solver budget. | Reducing NPC or physics work would change the tutorial behavior already reported broken. No algorithmic defect established from shifted Dev126 Logan log fields (format bug corrected). |
| Visibility / LOD / draw distance | Retain original scene/frustum/static-sort/LOD ownership. | No culling/geometry omission introduced to improve a benchmark. Requires representative native camera comparisons before changing render quality policy. |
| Resolution / MSAA / filtering | Retain 960x544 and current 4x MSAA/filtering. | Confirmed vglInit convenience default is 4x MSAA. Reducing quality without a GPU-bound measurement/image comparison is not an evidence-backed optimization; native A/B prerequisite. |
| Diagnostics cost | Retain bounded sampled logs and crash persistence; fix malformed varargs. | Steady render-cache log every120 frames; mission progress logs on state changes, not countdown ticks. Scene census traversal remains diagnostic work; quantify before changing its freshness contract. |
| Networking / frame ownership | Retain original local single-player lane and provider boundary. | Host owner contracts pass. Network or AI cadence cuts are rejected as gameplay changes. |

Expanded implementation details:

- Indexed scratch is fixed at 122896 bytes; maximum 12288 indices per batch.
  Hash collisions emit an identical duplicate rather than changing any triangle.
  Batches close before changing textures/materials; final color/UV/normal state is
  restored even if the last source vertex was reused. GPU indices are copied into
  vitaGL's existing transient pool. Failed allocation reports GL_OUT_OF_MEMORY
  and performs no invalid draw. Mode bit8 controls indexed reuse and preparation;
  RVRC1 0 remains the baseline work mode. Compact dependency layout is separate.
- Fixed production mesh host fixture: 486834 -> 99138 vertex emissions across
  41 draws in both modes. Normal host run median618057 ->292387ns,
  p951361911 ->328814ns, p99/worst7645240 ->342684ns. The slow baseline tail was
  under host build contention; these are CPU fixture numbers, not native FPS or
  adoption evidence. Sanitized equivalents and memory bounds also pass.
- Bink's pinned decoder exposes DR1 but no frame/slice-thread capability. Merely
  raising thread_count does not establish parallel decode; no speculative thread
  rewrite was added. Its DSP and speed-build configuration remain separately
  auditable. A direct YUV shader or asynchronous decoder redesign requires new
  native timing and A/V correctness evidence after these demonstrated fixes.
- Additional isolated IDCT-put experiment (not integrated): use the original
  integer IDCT through an intermediate 64-element block to encourage NEON. ARM
  inspection shows add/scale routines already vectorized by the speed build;
  put remains mostly scalar. The experiment preserves all 16384 block/stride
  comparisons and input coefficients, and generates NEON, but host median
  514964 ->524338ns did not improve (p95717592 ->627556; p99/worst1221270
  ->815244 under contention). Adds 256 bytes of temporary stack storage.
  Decision: retain the tested prototype under build/dev127-bink-put-probe.*;
  do not integrate without native benefit evidence. No decoder semantics change.
- The dependency's pre-existing nonzero-mip subimage branch appears to use an
  uninitialized mip stride after copy-on-write. Active port subimage calls use
  level0; this optimization excludes nonzero levels. Do not describe the level0
  pixel tests as validation of that unrelated mip path.

Pending closure: expanded canonical ARM/ELF/SELF/VPK/identity audit and final
hashes. The preceding local run linked/packaged, then failed an obsolete capture
symbol signature gate; corrected before the expanded retry. Source and scripts
are frozen during the running build. Physical testing stays held. Neither host
timings nor artifact closure prove 60FPS, movie audibility, Mobius stability or
whole-demo completion.
