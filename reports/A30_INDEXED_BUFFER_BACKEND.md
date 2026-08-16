# A3.0 Generic Indexed-Buffer Vita Boundary

Status: implemented and independently reviewed; host, sanitizer, and Vita-object
validation passed on 2026-08-07.

## Architecture

The implementation stays below the original WW3D abstractions:

`RenegadeTerrainPatchClass / original renderer`
-> `DX8Wrapper::Set_Vertex_Buffer / Set_Index_Buffer / Draw_Triangles`
-> original `VertexBufferClass`, `IndexBufferClass`, `FVFInfoClass`
-> CPU-backed DX8-shaped Vita handles
-> `RenegadeVitaRenderer::Submit_Indexed_Triangles`
-> vitaGL fixed-function matrices and homogeneous vertex pipeline.

There is no terrain-specific submission function, custom level parser, custom
world object, or replacement scene graph. The accepted A2.2 `MeshClass`
submission path is unchanged.

## Preserved original semantics

- Static and dynamic bind overloads retain the pristine `REF_PTR_SET` ownership
  and `Add_Engine_Ref` / `Release_Engine_Ref` behavior.
- A static bind resets its corresponding dynamic offset.
- A dynamic vertex bind retains `VertexBufferOffset` and `VertexCount` and
  marks the index state changed because the base vertex changed.
- A dynamic index bind retains `IndexBufferOffset`.
- The submitted first index is `start_index + iba_offset`.
- The submitted base vertex is `index_base_offset + vba_offset`.
- `min_vertex_index` / `vertex_count` remain the original declared Direct3D 8
  index range; indices are not rewritten or rebased.
- The original `vertex_count < 3` fallback is retained, including the dynamic
  access count versus static-buffer capacity behavior.
- Bound 16-bit indices and every referenced vertex are bounds checked before a
  native draw is attempted.

## Current supported layout

The first world-demanded layout is supported exactly:

- FVF `0x00000152`: `XYZ | NORMAL | DIFFUSE | TEX1`
- original `VertexFormatXYZNDUV1`
- stride 36 bytes
- offsets: position 0, normal 12, ARGB diffuse 24, UV0 28
- 16-bit indices

Other FVF/stride combinations fail safely and produce a one-shot persistent
diagnostic. Sorting buffers likewise remain an explicit deferred boundary.

On Vita, the backend passes original object-space XYZ to vitaGL and loads
converted world/view/projection matrices into its fixed-function matrix path.
Homogeneous W therefore remains available to the GPU for clipping and
perspective-correct interpolation. The production path does not CPU-divide to
NDC. Raw indexed geometry is fingerprinted before submission for deterministic
host/hardware comparison.

## Matrix convention and clip-depth boundary

Original `DX8Wrapper::Set_Transform` stores the transpose of Westwood's
column-vector matrix, which is the Direct3D row-vector representation retained
by `RenderStateStruct`. If those stored matrices are `Dworld`, `Dview`, and
`Dprojection`, the original operation is:

`p * Dworld * Dview * Dprojection`.

The installed vitaGL `glLoadMatrixf` transposes OpenGL column-major input into
its internal matrix, and its fixed-function path evaluates
`projection * modelview * position`. The backend therefore supplies:

- modelview API memory: `Dworld * Dview`, which vitaGL stores internally as
  `view * world`;
- projection API memory: `Dprojection * transpose(C)`, where `C` maps the D3D
  clip vector `(x,y,z,w)` to OpenGL `(x,y,2z-w,w)`.

The row-memory projection conversion is consequently
`column2 = 2 * column2 - column3`, with the other columns unchanged. This maps
D3D clip depth `[0,W]` exactly to OpenGL/vitaGL `[-W,W]` without changing W.
The implementation was checked against installed/official vitaGL revision
`6e7fe40292e8f1d10f9a94ff2cd2f4fb1ba452a5`: `glLoadMatrixf` performs the
described transpose, vitaGL forms `projection * modelview`, and the generated
fixed-function vertex shader emits the homogeneous result as `POSITION`.
vitaGL's display `glViewport` uses a negative Y scale, matching Direct3D's
NDC-to-top-left-window orientation without an extra projection-Y inversion.

## Validation

Host raw-view semantic test: 14/14 PASS, checksum `65E5F668`. In addition to
buffer/range/fingerprint checks, it uses non-trivial world, view, and
perspective matrices to prove the D3D row convention, homogeneous W retention,
D3D-to-OpenGL clip-depth mapping, perspective interpolation (`1/3`, not the
affine `1/2` produced by pre-division), and rejection of an unavailable
transform.

Host original-object boundary test: 8/8 PASS. This exercises original
`FVFInfoClass`, `DX8VertexBufferClass`, `DX8IndexBufferClass`, CPU handle locks,
static buffer binding with the terrain-style dynamic submission hint,
start-index/base-vertex semantics, bound engine references, draw accounting,
fingerprint `65E5F668`, and released engine references.

VitaSDK ARM object compilation passes for:

- `ww3d_vita_renderer.cpp`
- `ww3d_dx8_boundary.cpp`
- original `dx8fvf.cpp`
- original `dx8vertexbuffer.cpp`
- original `dx8indexbuffer.cpp`

The A2 host regression also remains green: 19/19, 10/10, 14/14, 8 meshes,
357 vertices, 324 triangles, unsupported 0, checksum `5704AB7D`.

The raw test is also ASan/UBSan-clean. The accepted A2.2 `Submit_Mesh`
function remains byte-for-byte identical to the immutable A2.2 baseline
(extracted-function SHA-256
`6cbcf7e8405b4fef9f5985741ce470e5f182fde33e7ff9d730503bc4071b1979`).

Logs:

- `../../logs/a30-20260807-indexed-homogeneous-host.log`
- `../../logs/a30-20260807-indexed-homogeneous-wrapper-host.log`
- `../../logs/a30-20260807-indexed-homogeneous-sanitizer.log`
- `../../logs/a30-20260807-indexed-homogeneous-vita-object.log`
- `../../logs/a30-20260807-indexed-homogeneous-vita-boundary-object.log`
- `../../logs/a30-20260807-indexed-homogeneous-a22-regression.log`

## Remaining world-render dependencies

This boundary deliberately does not invent renderer state above the original
engine. The original Camera/DX8 capability, viewport, view, and projection
boundary is now implemented and validated separately in
`reports/A30_CAMERA_STATE_BOUNDARY.md`. The staged Vita branch of
`WW3D::Render` still needs the documented exact `cam->Apply()` patch follow-on
before that proven state reaches the first PhysicsScene draw. Remaining work:

- original shader/material state translation (depth, cull, blend, alpha,
  lighting, fog and texture-stage state);
- original `TextureClass` decode/residency/binding, with only a temporary
  neutral texture fallback if required to expose geometry;
- additional FVF layouts only when actual world submissions demand them;
- sorting-renderer integration when an actual sorted world pass reaches it.

Standard homogeneous frustum/near-plane clipping is now owned by the Vita GPU
through vitaGL rather than a deferred CPU approximation.

No staging directory or upstream source was modified by this backend work.
