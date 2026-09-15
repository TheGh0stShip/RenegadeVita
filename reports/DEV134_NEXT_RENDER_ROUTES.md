# Remaining native renderer routes inspected during Dev134 closure

| Field | Value |
| --- | --- |
| Candidate | A3.5-dev134 |
| Scope | Native renderer performance routes |
| Evidence | Source inspection and dependency comparison |
| Status | Open; no route is accepted or exhausted |
| Emulator policy | No emulator-specific tuning |

## Summary

These findings are source/host evidence. No emulator performance policy or
physical setting was changed. They supplement the Dev127 pinned-port comparison;
Dev128 already integrated native compressed DDS chains, superseding that older
comparison's pending-compression statement.

## Route 1 — Native movie YUV

Pinned vitaGL 6e7fe40292e8f1d10f9a94ff2cd2f4fb1ba452a5 includes
samples/immediate_mode_texture_yuv/main.c using VGL_YUV420P_BT601. Its
source/textures.c maps that format to GXM YUV420P3 CSC0, and BT709 to CSC1.
The installed VitaSDK independently declares those formats. No Vulkan API is
involved in the native route.

Read-only ffprobe of the user's EA_WW.BIK and R_Intro.BIK finds both are original
800x600 Bink yuv420p with television range. Color-space metadata is absent; BT601
matches the current default swscale conversion assumption but requires color
verification. Current provider retains the decoded AVFrame until presentation,
then sws_scale produces 320x240 RGBA with FAST_BILINEAR and uploads that image.

A planar route could retain those same dimensions and cadence, scaling YUV
without RGB conversion and using the GXM sampler. Packed CPU payload would be
115200 versus 307200 bytes. The pinned allocator rounds plane storage to 512x256
plus two 256x128 planes: 196608 bytes. These are layout calculations, not native
memory high-water or frame-time gains.

Concrete prerequisites from the actual dependency:

- Validate source plane stride, chroma order, even dimensions, size arithmetic,
  color range and color-space choice; retain RGBA fallback for unsupported input.
- gpu_alloc_planar_texture frees the prior texture before replacement succeeds.
  Make replacement transactional and prove delayed GPU retirement and failure
  propagation before using it for streaming.
- The generic direct-copy branch checks plane width but not every padded-height
  condition. Restrict admitted layouts or correct and test the production copy
  branches before allowing other movie dimensions.
- Preserve source-frame ownership, original scheduling/audio and sampler
  filtering. Compare actual color bars, chroma edges and repeated frame updates.

Next: production planar allocator/copy contracts and a bounded provider prototype.
Do not import a different movie loop, reduce image dimensions further, or claim
the GXM sampler is validated by the SDK enum alone.

## Route 2 — Persistent geometry and immutable handoff

Original MeshGeometryClass::Get_Vertex_Array returns a writable pointer;
MeshMatDescClass exposes mutable UV/color arrays, and MeshClass exposes mutable
user lighting. Current DX8 buffer Lock/Unlock has no mutation generation, and
the MeshClass submission path reads model arrays directly rather than owning a
persistent DX8 vertex buffer. Pointer identity alone cannot validate a cache.

Persistent packed data therefore needs an original lifetime/mutation contract
for positions, colors, material sources and animated texture coordinates. A
safe fallback is required for untracked writes, skinned deformation and changing
lighting. Native retirement must outlive queued draws. The same dependencies
prevent sending live original objects to another thread; commands must contain
immutable copied or retained data. This remains work to implement and measure,
not an exhausted route or permission to replace WW3D ownership.

## Route 3 — Diagnostic sampling

A31_Interactive_Run_Render_Frame currently counts both physics lists and formats
player/weapon diagnostic strings each frame. GenericMultiListClass::Count is
also linear; substituting it would not remove the traversal. Any sampling change
needs explicit freshness in capture state, first-frame readiness and pause/exit
snapshots. Profile the collection cost separately before adopting a cache.
