# Independent Review — A3.0 Generic Indexed Vita Backend

Date: 2026-08-07

Result: PASS after one concrete transform defect was corrected. The original
DX8Wrapper ownership and indexed-range semantics are preserved, the current
terrain/world vertex layout is interpreted correctly, host and Vita objects
compile, and the accepted A2.2 mesh path is untouched.

## Defect found and production correction

The first implementation multiplied world/view/projection on the CPU, divided
XYZ by homogeneous W, and submitted NDC through `glVertex3f`. Although its
D3D `[0,1]` to OpenGL `[-1,1]` depth arithmetic was correct, pre-dividing
discarded W before rasterization. That breaks homogeneous near/behind-camera
clipping and makes texture interpolation affine rather than perspective
correct.

The corrected implementation:

1. retains the original D3D-row world, view, and projection states;
2. combines only world and view in their retained row representation;
3. converts D3D clip Z to OpenGL clip Z as `z_gl = 2*z_d3d - w` while
   preserving W;
4. loads modelview and projection through vitaGL `glLoadMatrixf`;
5. submits untouched object-space XYZ, normals, diffuse color, and UV;
6. restores identity matrices after the generic draw so the separately
   accepted A2.2 CPU-projected path remains compatible if both paths execute
   in one diagnostic frame.

This is a platform-boundary correction. It does not alter Westwood mesh,
scene, camera, buffer, material, or object architecture.

## Matrix-layout proof

`DX8Wrapper::Set_Transform` documents that it accepts Westwood convention and
stores `m.Transpose()` for Direct3D. Denote these retained row matrices by
`Dw`, `Dv`, and `Dp`. Direct3D transforms a row position as:

`p * Dw * Dv * Dp`.

At official vitaGL revision
`6e7fe40292e8f1d10f9a94ff2cd2f4fb1ba452a5`, `source/matrices.c` stores
`glLoadMatrixf` input as `internal[i][j] = input[j*4+i]`.
`source/ffp.c` forms `projection * modelview`, and the generated fixed-function
vertex shader in `source/shaders/ffp_v.h` evaluates that matrix against the
input position and emits the four-component result as `POSITION`.

Therefore loading row-memory `Dw * Dv` makes vitaGL's internal modelview
`(Dw * Dv)^T = V * W`. Loading `Dp * C^T`, with
`C(x,y,z,w)=(x,y,2z-w,w)`, makes its internal projection `C * P`. The complete
GPU operation is consequently `C * P * V * W * p`, the expected column form
of the original Direct3D operation with only the clip-depth convention
changed.

No additional projection-Y inversion is required for the display target:
vitaGL's `glViewport` implementation programs a negative display Y scale,
which supplies the same NDC-to-top-left-window orientation used by Direct3D.
Future cull-state translation must still account for the requested original
front-face/cull mode, but it must not duplicate this viewport inversion.

The host semantic test independently emulates vitaGL's load convention with
non-identity matrices and confirms:

- X and Y clip coordinates equal the original Direct3D result;
- GL clip Z equals `2 * D3D_clip_z - D3D_clip_w`;
- homogeneous W exactly equals the original Direct3D W and is not one;
- NDC depth equals `2 * D3D_NDC_z - 1`;
- an equal-screen-weight UV example with W values 2 and 4 evaluates to `1/3`,
  not the affine `1/2` characteristic of the old pre-divided path.

## DX8Wrapper ownership and offset semantics

The boundary matches pristine upstream behavior:

- every bind releases the prior `Engine_Ref` through `REF_PTR_SET` and adds
  one engine reference to the newly bound object;
- static vertex binding resets `vba_offset` and `vba_count`;
- static index binding resets `iba_offset`;
- dynamic vertex binding retains `VertexBufferOffset` and `VertexCount` and
  invalidates index state because the base changed;
- dynamic index binding retains `IndexBufferOffset`;
- submitted first index is `start_index + iba_offset`;
- submitted base vertex is `index_base_offset + vba_offset`;
- the original `vertex_count < 3` fallback is preserved, including dynamic
  accessor count versus static physical-buffer capacity.

The CPU-backed handles reject any lock whose byte offset/size exceeds their
physical allocation. Before drawing, the backend checks the index byte range,
the declared min/count range, integer overflow, and every referenced physical
vertex. The logical count on a genuine dynamic accessor still follows the
original caller contract; physical buffer bounds remain enforced independently.

Source inspection of `RenegadeTerrainPatchClass` shows that its normal world
path retains ordinary static DX8 vertex/index buffers and passes
`BUFFER_TYPE_DYNAMIC_DX8` as a submission hint. An inactive `#if 0` branch is
the path that would use a true dynamic index accessor. The implemented static
buffer plus dynamic-hint behavior therefore matches the currently reached
original terrain path; unsupported true-dynamic layouts fail safely.

## Vertex layout and attribute interpretation

FVF `0x00000152` is exactly `XYZ | NORMAL | DIFFUSE | TEX1` and maps to
original `VertexFormatXYZNDUV1`:

- stride: 36 bytes;
- XYZ: byte 0, three floats;
- normal: byte 12, three floats;
- diffuse: byte 24, D3D ARGB `0xAARRGGBB`;
- UV0: byte 28, two floats.

The vitaGL call receives diffuse bytes as R, G, B, A and UV as U, V. No channel
swap or stride error was found. FVF/stride combinations other than this exact
first world-demanded layout are rejected rather than misinterpreted.

## Validation evidence

- Raw indexed host semantic test: 14/14 PASS, checksum `65E5F668`.
- Original DX8Wrapper/FVF/buffer boundary test: 8/8 PASS, checksum `65E5F668`.
- Raw indexed ASan+UBSan test: 14/14 PASS, no sanitizer finding.
- VitaSDK ARM compile: `ww3d_vita_renderer.cpp` PASS, ARM EABI5.
- VitaSDK ARM compile: `ww3d_dx8_boundary.cpp` PASS, ARM EABI5.
- Full A2 regressions: 19/19, 10/10, 14/14 PASS; 8 meshes, 357 vertices,
  324 triangles, unsupported 0, checksum `5704AB7D`.
- Canonical upstream checkout: clean.
- Staging/port `.orig` and `.rej`: none found.

Logs:

- `../../logs/a30-20260807-indexed-homogeneous-host.log`
- `../../logs/a30-20260807-indexed-homogeneous-wrapper-host.log`
- `../../logs/a30-20260807-indexed-homogeneous-sanitizer.log`
- `../../logs/a30-20260807-indexed-homogeneous-vita-object.log`
- `../../logs/a30-20260807-indexed-homogeneous-vita-boundary-object.log`
- `../../logs/a30-20260807-indexed-homogeneous-a22-regression.log`

The accepted A2.2 `Submit_Mesh` function was compared directly with
`../../baselines/A2.2/source/port/renderer/vita/ww3d_vita_renderer.cpp` and is
byte-for-byte identical. Both extracted bodies have SHA-256
`6cbcf7e8405b4fef9f5985741ce470e5f182fde33e7ff9d730503bc4071b1979` and
length 3029 bytes.

## Remaining limitations

These are explicit next-world-path boundaries, not regressions in the reviewed
indexed submission:

- only FVF XYZNDUV1 is implemented;
- original material/shader/texture render-state translation remains pending;
- texture decode, residency, and binding remain pending;
- sorting-buffer submission remains pending;
- the now-validated non-null CurrentCaps/camera/viewport/projection boundary
  still requires the exact staged `WW3D::Render` `cam->Apply()` call-through
  documented in `reports/A30_CAMERA_STATE_BOUNDARY.md`;
- true dynamic-buffer layouts such as XYZNDUV2 remain unsupported and reject
  safely until an actual original call path demands them.

Near/frustum clipping and perspective interpolation are no longer deferred:
the corrected path preserves homogeneous coordinates and delegates standard
clipping/interpolation to the Vita GPU through vitaGL.
