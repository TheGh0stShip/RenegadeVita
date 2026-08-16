# A3.0 Original Camera / Vita State Boundary

Date: 2026-08-07  
Status: production boundary and original `WW3D::Render` call-through complete;
independently validated and exercised by the 45/45 live M00 world frame.

## Purpose

The accepted A2.2 Vita branch deliberately rendered a single object without
calling `CameraClass::Apply`. The A3.0 indexed world path cannot do that:
original terrain and world draws reach `DX8Wrapper` and need the original
camera viewport, view matrix, and D3D projection matrix. Before this change,
`DX8Wrapper::CurrentCaps` was null and original
`Set_Projection_Transform_With_Z_Bias` would dereference it.

The implemented seam preserves the original chain:

```
CameraClass::Apply
  -> WW3D::Get_Render_Target_Resolution
  -> DX8Wrapper::Set_Viewport
  -> IDirect3DDevice8::SetViewport
  -> Vita viewport/depth-range boundary

  -> CameraClass::Get_D3D_Projection_Matrix
  -> DX8Wrapper::Set_Projection_Transform_With_Z_Bias
  -> real DX8Caps policy + retained D3D projection

  -> DX8Wrapper::Set_Transform(D3DTS_VIEW)
  -> retained original RenderStateStruct view
  -> original indexed draw boundary
```

No camera, scene, projection, or frustum algorithm was replaced.

## Production changes

- `port/renderer/vita/d3d8.h`
  - declares the narrow `SetViewport` / `GetViewport` device contract;
  - provides the original D3D8 invalid-call value used by that contract.
- `port/renderer/vita/ww3d_vita_renderer.h`
  - declares the fixed 960x544x32 display contract;
  - exposes a pure, host-testable D3D-to-native viewport conversion.
- `port/renderer/vita/ww3d_vita_renderer.cpp`
  - validates non-empty, in-bounds D3D viewports and 0..1 depth ranges;
  - converts D3D top-left Y to vitaGL lower-left Y as
    `native_y = 544 - d3d_y - height`;
  - applies `glViewport` and `glDepthRangef` only after renderer init;
  - writes a one-shot persistent camera-state breadcrumb with D3D/native
    rectangles, depth range, prior GL error, and operation GL error.
- `port/renderer/vita/ww3d_dx8_boundary.cpp`
  - owns a real original `DX8Caps` object rather than fake storage or a null
    pointer;
  - supplies a conservative Vita capability policy;
  - owns the original wrapper's display, projection, clip, and Z-bias state;
  - retains D3D viewport state and exposes original default-target resolution;
  - routes `DX8Wrapper::Set_Viewport` through the narrow device contract.

`port/validation/a30_camera_boundary_selftest.cpp` is an isolated validation
driver. It is intentionally not added to a production manifest or CMake target.

## Capability policy

The original `DX8Caps` Direct3D enumeration implementation is not compiled on
Vita. Constructing its hardware-probe path would misrepresent the native
backend. The port instead constructs the same original capability class with
only proven native behavior advertised:

- hardware/native vertex transformation: true;
- native D3D8 Z-bias render state: false;
- DXTC, gamma, N-patches, bump environment mapping, anisotropic filtering,
  multi-pass and fog: false;
- texture stages per pass: zero until the original material path demands and
  the backend implements them;
- texture/render-target formats: false until individually implemented.

`Support_ZBias == false` is important. It makes the unchanged original
`DX8Wrapper::Set_Projection_Transform_With_Z_Bias` select its projection-matrix
pseudo-bias path. No unimplemented D3D render state is advertised.

## Viewport convention proof

Original `ViewportClass` documents `(0,0)` as upper-left. `CameraClass::Apply`
multiplies its normalized rectangle by the current target dimensions and emits
a D3D8 viewport in that convention.

Installed vitaGL revision `6e7fe40292e8f1d10f9a94ff2cd2f4fb1ba452a5`
implements display viewport Y as:

```
y_scale = -(height / 2)
y_port  = DISPLAY_HEIGHT - gl_y + y_scale
```

Therefore an original D3D viewport `(240,68 480x272)` must be passed to vitaGL
as `(240,204 480x272)`. That maps the same physical top/bottom edges (68 and
340) without flipping the WW3D projection matrix. The host semantic test proves
this asymmetric case; a full-screen viewport naturally remains `(0,0 960x544)`.

vitaGL's `glDepthRangef` maps near/far to the GXM viewport Z offset/scale, so
the original Camera depth interval is retained directly.

## Projection and matrix semantics

`CameraClass::Get_D3D_Projection_Matrix` remains authoritative. The unchanged
original wrapper transposes that Westwood matrix, applies its pseudo-Z-bias
when native Z bias is unavailable, and passes the resulting D3D row-vector
memory to `SetTransform(D3DTS_PROJECTION)`.

The indexed Vita backend then:

- combines retained D3D world and view matrices as `Dworld * Dview`;
- maps D3D clip depth `[0,W]` to GL/vitaGL `[-W,W]` by replacing every
  projection column-2 element with `2*column2-column3`;
- passes raw object-space vertices to vitaGL so homogeneous W survives clipping
  and perspective interpolation.

The camera self-test uses non-identity translation, asymmetric viewport,
0.2..0.8 depth range, clip planes 0.5..500 and nonzero retained Z-bias. It
compares the exact matrix produced by original `CameraClass::Apply` with the
device-boundary projection, verifies the original view matrix in
`RenderStateStruct`, and proves both matrices are consumable by the indexed
transform seam.

## Default render-target scope

The A3.0 first-world traversal renders only to the native display target.
`WW3D::Get_Render_Target_Resolution` therefore truthfully reports the default
960x544x32 fullscreen target and does not fabricate a render-to-texture
surface. The test verifies this default/null-target behavior separately.

Non-default render targets remain deliberately unsupported. Projectors are
disabled for the first M00 traversal. Render-to-texture dimensions and surface
lifetime must be implemented when an actual original call path requires them,
not advertised speculatively.

## Completed staged call-through

The accepted A2.2 `ww3d2-a22-vita-boundaries.patch` makes the Vita branch of
`WW3D::Render(SceneClass *, CameraClass *, ...)` return before the original
non-Vita `cam->Apply()` statement. A3 restores that call with the separate
exact patch `port/patches/ww3d2-a30-camera-apply.patch`, rather than rewriting
the frozen A2.2 patch history.

The exact minimum change for the current world callback is:

```diff
 #if defined(RENEGADE_VITA_PORT)
     (void)clear;
     (void)clearz;
     (void)color;
+    cam->Apply();
     scene->Render(rinfo);
     Flush(rinfo);
```

The A3 patch is wired into `tools/stage_sources.sh` with
`--batch --forward --fuzz=0 --no-backup-if-mismatch` against pinned canonical
revision `3e00c3a1b97381bb28be89a35b856375e0629a08`. The live M00 host runtime
then executes original `CameraClass::Apply` and the full
Pre_Render/Begin/WW3D::Render/End/Post_Render envelope: PASS 45/45, 652 mesh
submissions, 30,603 vertices, 16,939 triangles, checksum `34FFAD42`, with zero
unsupported or unexpected GPU calls.

For symmetry when the separate original
`WW3D::Render(RenderObjClass &, RenderInfoClass &)` overload becomes active,
its Vita branch should likewise restore `rinfo.Camera.Apply()` immediately
before `obj.Render(rinfo)`. That second call is not needed by the current
PhysicsScene scene callback and should not be confused with the minimum current
change.

The renderer/capability changes themselves are all port-owned and require no
upstream patch or restage.

## Validation

Isolated original camera boundary:

- 16 checks, 0 failures;
- real non-null `DX8Caps` object;
- conservative capability flags;
- default target 960x544x32 fullscreen;
- top-left/lower-left viewport conversion;
- invalid/null viewport rejection with retained previous state;
- original depth interval;
- exact original pseudo-Z-bias projection;
- exact original view state;
- indexed transform boundary acceptance.

Log: `../../logs/a30-20260807-camera-boundary-host.log`  
SHA-256: `6e4f1b92e9d733be41ef62233f54bc66f8a4dec286cafcbb37046d5b72f2959f`

ARM/Vita object compilation passed for both production units:

- `../../logs/a30-20260807-camera-state-vita-renderer-object.log`
- `../../logs/a30-20260807-camera-state-vita-boundary-object.log`

Full A2 regression remains:

- A2.0: 19/19;
- A2.1: 10/10, 15161 / 32081 / 32 / `00000100`;
- A2.2: 14/14, 8 meshes / 357 vertices / 324 polygons,
  checksum `5704AB7D`.

Log: `../../logs/a30-20260807-camera-state-a22-regression.log`  
SHA-256: `093bdcc20379315643d5cfe5139f1fcc5f65155ff7c0d78abafddccb2eabbe14`

The accepted A2.2 `Submit_Mesh` function is byte-identical to the immutable
baseline: 3029 bytes, SHA-256
`6cbcf7e8405b4fef9f5985741ce470e5f182fde33e7ff9d730503bc4071b1979`.

Canonical upstream is clean at the pinned revision. No `.orig` or `.rej` files
exist. No source staging, patch, CMake, manifest, durable-state, or deployment
operation was performed during this boundary review.
