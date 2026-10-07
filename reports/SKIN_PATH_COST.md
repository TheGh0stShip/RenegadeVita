# Skin path cost analysis (report-only, no build/hardware run)

Source: `port/renderer/vita/ww3d_vita_renderer.cpp` `Submit_Mesh_Internal`
(skin branch ~L3652-3690, pass loop ~L3851-4108, `Evaluate_Material_Vertex_Color` L1650).
Input evidence: dev236 M13 log, cumulative "A3.5 skin:" stats at frame 3840:
~40k skinned submissions, ~6.2M deformed vertices.

## Per-frame estimate (derived, not measured)

| Quantity | Value |
|---|---|
| Skin submissions / frame | 40,000 / 3840 ~= 10.4 |
| Deformed vertices / frame | 6.2M / 3840 ~= 1,615 |
| Mean vertices / submission | ~155 |
| Corners emitted / frame (tri ~= 1.5-2x verts, x3) | ~5-10k (fewer when indexed batch mode bit 8 dedupes) |

Cost model on Cortex-A9 @444 MHz (assumptions, must be confirmed with
`RENEGADE_VITA_DETAILED_TIMING` mesh-boundary samples):
- `MeshClass::Get_Deformed_Vertices` (original WW3D, per-vertex bone matrix
  transform of position + normal): ~60-120 cycles/vertex -> **~0.2-0.45 ms/frame**.
- Immediate-mode corner emission (lambda `emit_vertex`: `material_for`,
  `Evaluate_Material_Vertex_Color`, up to 2x `Emit_Original_Texture_Coordinate`,
  `glColor4f`, `glVertex3f`; each vitaGL immediate call appends to its internal
  buffer with state checks): ~0.5-1.5 us/corner -> **~3-12 ms/frame**.
- Per-batch state rebinding (`Apply_Original_Shader_State`,
  `Apply_For_Platform_Boundary`, texcoord state capture, `glEnd`/
  `vglRenegadeEndIndexed`): small per batch, tens of batches/frame.

Conclusion: deformation itself is minor; **submission overhead dominates**
(roughly 10-30x the deform cost). Skin is excluded from
`Submit_Static_Mesh_Cache` (L3846) so it always takes the per-corner path.

## Identified Vita-side overhead

1. **Per-corner function-call chain.** Every corner (not vertex) runs the full
   lambda; without indexed batching, shared vertices are re-evaluated ~6x.
2. **Material evaluation per corner.** `material_for(vertex_index, pass)` and
   `Evaluate_Material_Vertex_Color` run per corner. For textured skins
   (`skin_color_passthrough`) RGB is discarded to white anyway; the mode-2
   fast path still calls `Evaluate_Original_Diffuse_Alpha` per corner. For
   untextured/lit skin passes the full original lighting runs, cached only in
   the 8192-entry scratch keyed by generation.
3. **Redundant normal work.** Skin world is identity, but
   `Prepare_Material_Light_Directions` / lighting still treat normals through
   `original_world_transform`; normals are already world-space after deform,
   so the transform is a no-op multiply per lit vertex.
4. **Per-pass/per-call re-deformation risk.** Deformation happens per
   `Submit_Mesh_Internal` call. `Submit_Material_Pass` (procedural/material
   passes) calls it again for the same mesh in the same frame, re-running
   `Get_Deformed_Vertices` (the procedural active-polygon path is skipped for
   skins, but the deform is not).
5. **Diagnostic predicates in the hot loop.** `record_original_skin_color`
   evaluates `Is_Loading_Screen_Diagnostic_Name` (string compares) only when
   `!g_logged_first_skin_texture_color`; cheap after first log, but the
   `Get_Texture_Name().Peek_Buffer()` and flag checks remain per corner.
6. **Texcoord emission.** `Emit_Original_Texture_Coordinate` takes view/world
   transforms and texture name per corner; for PASSTHRU mode it only needs
   `uvs[i]`.

## Proposed behaviour-preserving optimizations (ranked by expected gain)

1. **Vertex-array submission of deformed buffers (est. 60-80% of skin submit
   time).** After deformation, build per pass one interleaved array
   (pos, color, uv0[, uv1]) per *unique vertex* and draw each material/shader
   batch with an index list (`glDrawElements` / existing
   `vglRenegadeEndIndexed` index path). Material color is a per-vertex
   function of (vertex, material, pass) so it can be computed once per unique
   vertex with identical results. Requires the texcoord generator to emit into
   an array (PASSTHRU = copy; env/generated modes computed once per vertex).
   Must preserve the "restore last corner attribute" semantics only for
   following immediate callers (set glColor once after draw).
2. **Per-vertex (not per-corner) color/uv evaluation (est. 30-50% if #1 is
   deferred).** Force the indexed batch path (mode bit 8) for skins and hoist
   `material_for`/color/uv evaluation into a per-pass pre-pass over
   `vertex_count` into scratch arrays; the corner loop then only appends
   indices. Equivalent outputs because evaluation inputs do not depend on the
   triangle.
3. **Textured-skin fast path (est. 10-20%).** When `skin_color_passthrough`
   holds for the whole batch, fill RGB=1 and compute alpha once per vertex (or
   once per batch when the alpha source is constant material opacity, via
   `Try_Evaluate_Constant_Material_Vertex_Color`).
4. **Cache deformation per mesh per frame (est. 5-15% of deform, larger on
   multi-pass/material-pass characters).** Key scratch by
   (MeshClass*, frame counter, model) and skip `Get_Deformed_Vertices` on
   subsequent `Submit_Material_Pass`/pass calls in the same frame. Original
   DX8SkinFVFCategoryContainer also deforms once per render per mesh; keep
   invalidation on any transform/visibility change within the frame (render
   from multiple cameras must re-key with camera id or simply frame+mesh,
   since deform is camera-independent).
5. **Skip identity-world normal transform for skins (est. <5%).** Pass a flag
   so lighting uses deformed normals directly; numerically identical with
   identity matrix (avoid fused-multiply drift by only skipping exact identity).
6. **Hoist diagnostic/texture-name lookups out of the corner loop (<2%).**
   Compute per batch; keep first-occurrence breadcrumbs unchanged.

## Validation plan for any adoption

Per charter: fixed M13 replay/camera, before/after median/p95/p99/worst of
mesh-boundary timing for skin meshes only, unchanged first-skin breadcrumbs,
host contract tests (`Submit_Mesh_Internal` indexed-state/skin tests) asserting
identical per-vertex color/uv/position outputs between immediate and array
paths, then physical Vita capture comparison. No fast-math.
