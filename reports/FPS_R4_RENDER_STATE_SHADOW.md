# FPS round 4: RENDER_STATE_SHADOW

Branch `worktree-agent-afe90f589faf2379c` continues the recovered
`fps-r3/render-state-shadow` (53af718, cherry-picked cleanly onto 95c4976),
then reviews and finishes it. Default on. Runtime switch: `RVGS1 0\n` in
`ux0:data/renegade/user/config/gl-state-shadow-v1.flag` restores the old call sequence.

## Hypothesis
The per-batch path re-issues raster state (blend/alpha/depth/colour mask/cull/
polygon offset/fill mode) and FFP transforms to vitaGL with unchanged values.
In vitaGL (build/deps/vitagl-demo source):
- `glLoadMatrixf`/`glLoadIdentity` (matrices.c:270,487) always set `mvp_modified`
  and dirty the vertex uniforms (`flag_dirty_matrix_unif`, matrices.c:26). A
  texture-matrix load dirties `TEX_MATRIX_UNIF`. On the next draw `reload_ffp_shaders`
  (ffp.c:1027-1152) rebuilds the MVP, reserves a fresh vertex default uniform
  buffer, copies the whole FFP uniform block and re-sets the dirty uniforms.
  Every indexed submission loaded projection+modelview, reset both texture
  matrices to identity, then reloaded identity projection+modelview: the
  vertex uniform upload ran on every draw even for identical HUD/text transforms.
- `glDepthFunc` = 4 GXM calls, `glDepthMask` = 2 (tests.c:394-465);
  `glCullFace`/cull enable call `sceGxmSetCullMode`; polygon offset/mode issue
  2-4 GXM depth-bias/polygon-mode calls (misc.c:153-320).
- `glAlphaFunc` and `GL_ALPHA_TEST` toggles set `ffp_dirty_frag`
  (tests.c:217). That is cleared cheaply when the FFP mask still matches
  (ffp.c:608), so these are cheap; blend calls only rewrite `blend_info`.
So the ranking is: matrix loads (uniform upload per draw), then GXM depth/cull/
bias calls, then the rest.

## Change
`port/renderer/vita/ww3d_vita_renderer.cpp`:
- An exact GL-level shadow (`NativeGLStateShadow`) with `Shadow_*` setters. A call
  is skipped only when the field is known and the argument is identical
  (floats and matrices compare bitwise with `memcmp`, never with a tolerance;
  -0.0 vs 0.0 and NaN payloads are distinct). Call order is unchanged.
- `Apply_Original_Shader_State` and the `Apply_DX8_Render_State` switch route
  every raster call through the shadow. A GL error after the switch invalidates it.
- `Submit_Mesh_Internal` and `Submit_Indexed_Triangles` load transforms with
  `Shadow_Load_Transforms`. The post-draw identity reload (`Release_Submission_Transforms`)
  is dropped while the shadow is on. Audit: every FFP draw site loads its own
  projection/modelview first (mesh immediate path, static-mesh replay inside
  `Submit_Mesh_Internal`, indexed path). Bink pushes and pops its own. glClear and
  blits use vitaGL's own programs. `Begin_Frame` requests identity through the shadow.
- `Reset_Texture_Matrix_Stage` skips `glLoadIdentity` when that stage's
  GL_TEXTURE matrix is known to be identity.
- Invalidation: `Invalidate_Native_State_Cache` (init, reactivation success,
  offscreen render-target bind/restore, shutdown). `Reactivate_Native_Backend_State`
  now invalidates before its raw calls, which also covers its error return.
  `Initialize` invalidates (via `Read_GL_State_Shadow_Mode` and the cache reset)
  before its raw calls. The `Apply_DX8_Render_State` GL-error path also invalidates.
- Telemetry: a `gl-state-shadow` breadcrumb at init (mode) and every
  120 frames, giving raster calls/skips, transform loads/skips and texture-matrix loads/skips.

`ww3d_vita_renderer.h` and `ww3d_dx8_boundary.cpp`: the boundary's D3DTS_TEXTUREn
GL_TEXTURE load (`Apply_Texture_Stage_Transform`) now calls
`RenegadeVitaRenderer::Invalidate_Texture_Matrix_Shadow(stage)`. This was a real
bug in the recovered WIP: it skipped the identity reset after the boundary had
loaded a non-identity texture matrix. Fog, texture bind, sampler and texenv
state are untouched.

## Risk and invalidation argument
Raw GL state writers are audited (`grep` of port/ and staging/): the renderer
(only the shadowed functions plus init and reactivation, both invalidating), the
boundary's texture-matrix load (hooked), and the Bink presenter. Bink saves
depth/cull/blend enables, restores them exactly and pushes and pops both matrices,
so the shadow stays true. vitaGL's internal clear/blit/scissor paths reset GXM
state and then restore it from the same variables the setters write (misc.c:640-738,
framebuffers.c:805-908). The GXM context state persists across scenes (vitaGL
restores only the viewport, gxm.c:672). The renderer already relied on this:
`GL_DEPTH_TEST` is set once at init, and the existing ShaderClass-bits cache
skips whole raster blocks across frames. vitaGL marks all uniforms dirty at
frame end (gxm.c:790-792). Residual risk: unknown GXM mutation behind vitaGL, e.g. by
the IME common dialog. This is no new class of reliance, and RVGS1 0 is the A/B escape.

## Tests (host, worktree; upstream symlinked for the run only)
- NEW `python3 -m unittest tools.test_vita_render_state_shadow`: 4/4 OK. This
  extracts the real shadow block, `Reset_Texture_Matrix_Stage`, the DX8
  translators and the `Apply_DX8_Render_State` switch, and compiles them twice
  (shadow on/off) over a GL shim (`tools/vita_render_state_shadow_test.cpp` +
  `_run.inc`). Randomized protocol-following sequences run in lockstep: shader
  applies, DX8 states, draws, Begin_Frame, boundary texture loads, Bink, invalidation and reactivation.
  Raster state, texture matrices, matrix mode and active unit match after every op.
  Projection/modelview match at every draw and at the end.
  ASan+UBSan: 600x400 ops. -O3: 3000x600 ops (GL calls 10.80M vs 15.59M, -31%).
  A negative control (boundary hook removed) diverges in 200/200 seeds. A
  scratch mutation run also caught element-wise matrix equality, a texture-identity
  skip without the known bit, an uncompared cull face, an uncompared alpha
  reference and a no-op invalidation (5/5 detected). A source-contract test
  rejects raw raster or transform calls outside the shadow except in the invalidating init and reactivation paths.
- `tools.test_vita_indexed_state_contract` (alpha-func assertion updated to
  `Shadow_Alpha_Func`), `test_vita_loading_screen_contract`,
  `test_vita_material_cache`, `test_vita_diagnostic_hotpath`,
  `test_vita_static_mesh_cache`, `test_frame_capture_source`: OK.
- Pre-existing failures, unchanged and listed in HOST_TEST_TRIAGE_2026-10-06:
  `test_vita_mesh_batch` (anchor not found), `test_vita_sampler_cache`
  (GLint/stale extraction), `test_original_decal_submission` (patch identity).
- ARM TU (VitaSDK, current flags, -O3): `ww3d_vita_renderer.cpp` OK,
  `ww3d_dx8_boundary.cpp` OK. Only pre-existing staging-header warnings appear.
  With `-Werror=unused-function` the only hits are the pre-existing `Float_Bits`
  and `Texture_Stage_Index_Valid`; no new function is unused.

## Expected gain (unmeasured, estimate)
About 3-4 us per indexed submission whose transforms repeat (HUD, text, particles,
sorted geometry): no MVP rebuild, no uniform reserve or copy, and about 9
fewer GL entry calls. About 1-3 us per ShaderClass change with mostly-equal
raster state. With roughly 100-300 indexed draws and 100-200 shader changes per
frame, that is about 0.5-1.5 ms/frame (1-3% of the dev238 ~41 ms render stage).
It is not a large win. The dominant per-corner immediate-mode cost is untouched.

## Hardware measurement to take
Use the same M13 replay/camera, A/B between default and `RVGS1 0\n`:
1. Collect the `gl-state-shadow` breadcrumbs (skip ratios per 120 frames) and the render stage,
   "Vita Render Indexed Triangles" and mesh-boundary p50/p95/p99.
2. Visual check of ZBIAS decals, alpha-tested fences and foliage, additive and
   alpha effects, inverted-cull reflections, HUD and text, a Bink movie followed
   by gameplay, render-target switches, and save/load reactivation. Hardware
   screenshots must match between A and B.
