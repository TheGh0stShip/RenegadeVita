# FPS round 4 — VERTEX_ARRAYS (client vertex arrays on the per-frame mesh path)

Source only. Nothing here was run on Vita3K or hardware; no gain is measured.

## Hypothesis
Batches of `Submit_Mesh_Internal` that the static mesh cache does not serve
(skins, rigid VOLATILE/INELIGIBLE meshes such as lit/instanced vehicles) emit
every vertex through 3-4 vitaGL immediate calls (glMultiTexCoord2f x1-2,
glColor4f, glVertex3f, each with its own dispatch, display-list check and pool
memcpy). Storing each referenced vertex once per batch in client arrays and
issuing one glDrawElements per batch removes that per-vertex call chain while
keeping the per-vertex CPU evaluation (colour, uv) identical.

## Evidence
- Per-vertex emission: `emit_vertex` lambda, ww3d_vita_renderer.cpp:4123;
  indexed batch end re-emits the last corner then `vglRenegadeEndIndexed` :4229.
- vitaGL immediate: `glVertex3f` copies uv/uv2/rgba per vertex into the legacy
  pool (vitagl ffp.c:1947-2019); `glColor4f`/`glMultiTexCoord2f` :2271/:2455.
- vitaGL client arrays without a bound VBO (draw.c:331-391, ffp.c:1443-1613):
  indices are copied to the frame pool (`setup_elements_indices`, memcpy;
  INDICES_DRAW_SPEEDHACK is not set), the highest index is found by one scan,
  and each enabled attribute copies `(top_idx) * stride` bytes into the
  circular pool (32 MiB, heap fallback on overflow). Hence separate tightly
  packed streams (12+16+8[+8] B/vertex) rather than an interleaved struct,
  which would copy the full stride once per attribute (4x).
- Layout: `reload_ffp_shaders` derives the array layout from enabled texture
  units AND enabled texcoord arrays (ffp.c:479-528); `has_colors` disables the
  tint uniform (ffp_f.h:121), so current colour does not affect an array draw.
- Prototype dc5c977 (skin-only, default off) supplied the design.

## Change (port side only; no upstream/staging/vitaGL patch)
- New `port/renderer/vita/ww3d_vita_vertex_array_batch.h`: per-mesh reusable
  SoA scratch (position/RGBA float/uv0/uv1), remap table (O(batch) reset),
  16-bit index list. `Reserve` fails (immediate fallback) for >65535 vertices
  or allocation failure.
- `Vertex_Array_Batch_Eligible` (:3778): pass-through + D3DTTFF_DISABLE on
  each coordinate-carrying stage, no projective flags on inactive stages (else
  immediate would take `vglRenegadeBeginProjective`), UV arrays present (the
  immediate path would otherwise reuse a stale current UV), detail stage only
  over a textured base, `g_texture_stage_cache` enable state known and equal
  to {texture0, detail} (failed textures keep unit 0 disabled -> immediate),
  and the passthrough-V breadcrumb already logged.
- Batch opens as array (:4344) only for non-procedural passes, after the
  material-lighting breadcrumb fired and with no pending first textured-skin
  colour breadcrumb; otherwise the unchanged glBegin/indexed path runs.
- `array_append` (:4182) makes exactly emit_vertex's calls once per new batch
  vertex (same Evaluate_Material_Vertex_Color arguments incl. the skin
  pass-through flag, same white-RGB override, same Clamp01, same uv sources).
- `Draw_Vertex_Array_Batch` (:3802): invalidate attributes, unbind buffers,
  set 2-4 client arrays, one glDrawElements(GL_TRIANGLES, U16), disable all
  client arrays, invalidate again (immediate layouts re-patch), then restore
  the final corner's colour/uv0/uv1 as current (what the immediate batch end
  leaves current). Counters + first-batch breadcrumb.
- Runtime flag (:1951) `ux0:data/renegade/user/config/vertex-array-v1.flag`:
  exactly `RVVA1 0\n` = off, `RVVA1 1\n` = on; build default
  `RENEGADE_VITA_VERTEX_ARRAY_DEFAULT` (1). Breadcrumbs: `vertex-array
  version=1 enabled=..`, first batch, and every 120 frames
  `batches/corners/vertices/scratch_bytes`. M00 demo never enables it.

## Default: ON (justification)
Host proof of byte-identical corner streams, state sequence, breadcrumbs and
current attributes; every ineligible case falls back per batch to the
unchanged path; `RVVA1 0` restores the exact previous path without a rebuild;
the static mesh cache (default on) already depends on the same vitaGL FFP
client-array draw and invalidation contract. Coordinator may flip the macro
to 0 if a first hardware run should stay conservative.

## Risk & invalidation argument
- Equivalence: values are computed by the same calls with the same inputs;
  only the number of evaluations changes (once per unique vertex). The
  evaluator is deterministic within a pass (its cache is generation-keyed),
  so diagnostic counters `material_color_evaluations/hits/skin_rgb_skips`
  drop (expected); rendered values do not.
- Scratch never outlives a draw: vitaGL copies arrays and indices before
  returning; remap reset each batch; `Reserve` only between batches.
- Main open risk is cost, not correctness: each array draw re-patches the FFP
  vertex program (`sceGxmShaderPatcherCreateVertexProgram` lookup, also done by
  the static cache replay) and the next immediate draw re-patches again. Tiny
  batches (1-3 triangles) could be net slower. Follow-up if measured: skip the
  leading invalidate/pointer setup when the previous FFP draw was this path's
  own array draw in the same pass loop, deferring the trailing invalidate to
  the next immediate begin / end of mesh.
- Relies on `g_texture_stage_cache` tracking GL texture-unit enables (all
  enable paths update it; Bink sets GL directly but cache invalidation then
  makes the state "unknown" -> ineligible).

## Tests
- NEW `python3 -m unittest tools.test_vita_vertex_array_submission`:
  extracts the production pass loop + both helpers, GL shim; 5 fixtures (rigid,
  multi-pass, skin, large) x {indexed on/off} x {colour cache on/off} x
  {breadcrumbs pending/logged}; asserts byte equality of expanded corners,
  ordered state/breadcrumb events, current attributes at every state call,
  colour-evaluation argument sets, vitaGL contracts (no bound buffers, texcoord
  arrays == enabled units, invalidation between layouts, no arrays left
  enabled); ASan+UBSan. 9 production-text mutations must each fail.
  Result: 3/3 OK (40 runs compared; ~24k array draws and ~26k immediate
  fallback draws exercised; all 9 mutations detected).
- Existing renderer host tests: only pre-existing failures (mesh_batch anchor,
  sampler GLint, index_preparation RENEGADE_FRAME_PROFILE, projective needs
  vitaGL tarball — all in HOST_TEST_TRIAGE_2026-10-06; skin_submission_contract
  regex for the pre-hoist `skin_color_passthrough` line, absent at base 95c4976).
- ARM TU: `arm_tu_check.sh ... ww3d_vita_renderer.cpp` -> ARM TU OK, no new
  warnings.

## Alternative: sibling records API (fps-r4/dx8-dynamic-draw 6471912)
vitaGL analysis confirms client arrays without a VBO are also copied into the
frame pool, so arrays have no copy advantage over
`vglRenegadeImmediateVertices` (11-float records appended to the open
immediate primitive). Records keep the immediate layout, so they avoid this
path's two program re-patches per batch and compose with the existing
indexed-immediate dedup (`vglRenegadeEndIndexed`); arrays need no vitaGL patch
and are not limited to 12288 indices per draw. Recommendation: if hardware
shows re-patch cost dominating, keep this commit's eligibility predicate,
`array_append` (once-per-vertex evaluation) and harness, and swap only
`Draw_Vertex_Array_Batch` for packing the batch's unique vertices as records
inside Begin/`vglRenegadeEndIndexed` (records leave current attributes
unchanged, so the same final-corner restore applies). Not done here: that
patch is not on this branch and the coordinator integrates it.

## Expected gain (estimate, unmeasured)
Per unique batch vertex: removes 3-4 vitaGL calls and the immediate pool
append; adds ~44 B CPU stores + vitaGL memcpy of the same bytes. Per batch:
+2 program re-patches, +~15 cheap state calls. CPU evaluation unchanged.
Rough guess 0.2-0.5 us saved per unique vertex -> ~1-4 ms/frame at M13 load
(5-10k unique per-frame vertices), minus re-patch cost on small batches.
Could be ~0 or negative if patching is expensive; measure before keeping on.

## Hardware measurement
Same M13 replay/camera, `RENEGADE_VITA_DETAILED_TIMING` build, two runs:
A = `RVVA1 0\n`, B = no flag (on). Compare `mesh-boundary-time`
estimated_total_us and draw_end totals (array draws are inside end_batch),
render-stage ms p50/p95/p99, and `vertex-array` batches/vertices per frame
(corners/batches gives mean batch size). Visual: skins, lit vehicles, detail
textures, alpha/additive meshes must look identical in screenshots.
