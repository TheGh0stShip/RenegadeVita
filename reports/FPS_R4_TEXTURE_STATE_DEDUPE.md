# FPS round 4: TEXTURE_STATE_DEDUPE

Status: source change, host-tested, ARM TU compiled. **Nothing is measured on
hardware.** This continues the stopped round-3 branch
`fps-r3/texture-state-dedupe`. Its commit 636793d was cherry-picked; it held
only struct fields, which were reworked.

## Hypothesis

dev238 (M13, physical) logged about 129 binds, 99 sampler updates and 133
`glTexParameteri` writes per frame (`runtime-observation-3.log:1184`, 600
frames: binds 77455, `texture_sampler_updates` 59350, `sampler_writes`
79636). `texture_sampler_updates == texture_bind_skips` exactly, so every
sampler update came from the same place:

- The boundary's `SetTexture` binds the new object, then configures it with
  the stage's *previous* sampler request.
- The original `TextureClass::Apply` (staging/ww3d2/texture.cpp:645) then
  sends MIN/MAG/MIP/ADDRESSU/ADDRESSV one at a time, and each one reaches the
  GL object.
- When textures with different address modes alternate, each switch writes
  the object about four times and ends where it started.

The combiner has a similar problem. `Apply_Original_Shader_State` rewrites
`GL_TEXTURE_ENV_MODE` and clears `combiner_known`. The next stage-state apply
then resends the whole combiner (7-15 `glTexEnvi`), even if only the mode
changed.

## vitaGL cost model (build/deps/vitagl-demo/source, read-only)

- `glActiveTexture` and `glBindTexture` only store an int (textures.c:2169,
  1777).
- `sceGxmSetFragmentTexture` runs on every draw for each enabled unit,
  whether or not the binding changed (ffp.c:1190).
- `glTexParameteri` rebuilds the `SceGxmTexture` control words through
  `vglSetTex*` (textures.c:278-400). This is cheap but not free.
- `glTexEnvi` always sets `ffp_dirty_frag`, even for an equal value
  (ffp.c:2873ff). `reload_ffp_shaders` recomputes the mask on every draw and
  clears the flag when the mask is unchanged (ffp.c:607), so a redundant
  texenv reselects no program.
- `glDeleteTextures` unbinds the name from every unit (textures.c:1860).
  `glGenTextures` reuses the lowest free name with default parameters
  (textures.c:1737).

Conclusion: no single redundant call is expensive. The gain is call volume
only.

## Change (port/renderer/vita only; upstream and staging untouched)

1. **One sampler batch per TextureClass::Apply.**
   - `Apply_Platform_Texture_Stage` (ww3d_vita_renderer.cpp:3759) wraps
     `Apply_For_Platform_Boundary` in `Begin/End_Texture_Sampler_Batch`
     (:3612). It replaces the 5 renderer call sites (:2435, :2437, :4066,
     :4320, :4325) and the boundary site (ww3d_dx8_boundary.cpp:1882).
   - Inside a batch, `Configure_Texture_Sampler_Stage` (:3629) keeps only the
     stage's final request, and only for the object the stage already binds.
     `TextureClass::Apply` binds first, so deferring never changes a binding.
   - A pending request is applied immediately when something supersedes it:
     a request for another object on the same stage, the same object on
     another stage, or an immediate request. `Bind_Texture_Stage` (:3451)
     also applies a pending request before the stage switches objects.
   - `End` applies what remains through the unchanged immediate path,
     `Apply_Texture_Sampler_Now` (:3508), which keeps the object memo, alias
     invalidation and glGetError handling.
   - Binds and combiner calls stay immediate.
2. **Per-unit texenv shadow.**
   - `Set_Texture_Env` (:1164) and `Set_Texture_Env_White_Constant` (:1182)
     remember the last values sent to each unit: 15 slots (mode,
     `COMBINE_RGB/ALPHA`, `SRC0-2`, `OPERAND0-2`) plus the `ENV_COLOR`=white
     flag. An equal resend is skipped.
   - All texenv writers go through the shadow, including the 4 env-mode
     writes in `Apply_Original_Shader_State`. No raster, blend, depth or fog
     code was touched.
   - A GL error in `Apply_DX8_Texture_Stage_State` clears the unit's shadow.
3. **Name-scoped release invalidation.** `Release_Texture` (:3915) now calls
   `Invalidate_Texture_Object_State` (:334) instead of wiping all texture
   state. That function drops only:
   - the deleted name's object memo,
   - stage binding and sampler memos that refer to the name,
   - any pending request for the name.
4. **Diagnostics.** A new 120-frame breadcrumb `texture-state` (:3320)
   reports `sampler_updates`, `sampler_skips`, `sampler_deferrals`,
   `texenv_writes`, `texenv_skips`, `binds` and `bind_skips`.

Switch: RVRC1 bit 0, the existing "sampler" bit, which is on by default
(mode 15). With bit 0 clear, configure calls are immediate, the texenv shadow
always writes and the object memo is unused, which is the old path. Change 3
is unconditional; it is exact.

## Invalidation and equivalence argument

- **Sampler state.** It belongs to the GL object and only a draw reads it.
  - A batch covers one `TextureClass::Apply`. Between its `SetTexture` and its
    last stage-state call there is no draw and no upload (`Init()` runs
    before `SetTexture`).
  - Each object therefore ends with its last request in call order, as in the
    immediate path. The supersede rules keep that order across stages and
    objects.
- **Name reuse.** Every creation path (boundary uploads, Bink) still calls the
  global `Invalidate_Texture_State_Cache`, which bumps the generation and
  wipes the stage caches. `Release_Texture` drops the deleted name's memo and
  pending request. A recycled name never inherits a memo.
- **Texenv.** It is unit state, independent of bindings and deletion. Both
  global invalidations memset the stage cache, including the shadow, so Bink,
  render-target switches and context resets resend everything.
- **Known edge, unreachable today.** If an upload ran inside a batch after a
  deferral, `End` would rebind the deferred object. That matches D3D stage
  semantics rather than the old unit-0 clobber.

## Tests (host, run from repo root)

- `python3 -m unittest tools.test_vita_sampler_cache`: **16/16 OK**. Also
  16/16 OK with `RENEGADE_SAMPLER_SANITIZE=1` (ASan+UBSan).
  - Harness fix: the GLint error came from an extraction range that had grown
    over `Bind_Offscreen_Render_Target` and `Submit_Mesh_Internal`.
  - New directed cases: batch-final-request, batch-cross-stage-order,
    batch-release, release-scope, texenv-shadow.
  - New randomized equivalence test: 200 seeds × 600 ops. Ops are uploads
    with lowest-name reuse, re-uploads, releases (also mid-batch), batched
    applies with stale stage requests, bind and cross-stage perturbations,
    combiner and env-mode changes, invalidations and draws.
  - At each draw, bindings, enables and bound-object parameters must match an
    immediate-semantics oracle.
  - Mode 0, mode 1 without batches and mode 1 must produce identical trace
    hashes over all objects and unit envs, with non-increasing call counts.
  - Mutation check: removing any one of the bind flush, the cross-stage
    flush, the release pending-drop, the bound-only deferral rule or the
    env-value compare fails the random test. Removing the release
    binding-drop fails the directed release-scope case.
  - Synthetic counts (seed 1, mode 0 / mode 1 without batches / mode 1):
    `glTexParameteri` 1100/572/418, `glTexEnv` 2341/1386/1386, binds
    124/124/124. These are not a hardware prediction.
- `tools.test_vita_indexed_state_contract`,
  `tools.test_vita_texture_provenance_contract` and
  `tools.test_vita_loading_screen_contract`: **33/33 OK**. `upstream/` was
  symlinked for the run and then restored. Four source-text anchors were
  updated to the new helper names.
- `tools.test_vita_mesh_batch` and `tools.test_vita_static_mesh_equivalence`
  already failed before this change with "substring not found"
  (HOST_TEST_TRIAGE). Their repair will need an `Apply_Platform_Texture_Stage`
  shim.

## Expected gain (estimate, unmeasured)

Per frame in steady state, with each texture keeping its own sampler state:

- sampler updates fall from about 99 to near 0,
- about 130 fewer `glTexParameteri` calls,
- about 200 fewer `glActiveTexture` calls,
- about 100 fewer `glGetError` calls,
- dozens of `glTexEnvi` calls skipped.

At roughly 0.1-0.3 µs per call, that is **about 0.05-0.2 ms of a 41 ms
render frame (≤0.5%)**. The ~129 binds per frame are real texture changes
and do not go down. The per-draw texture cost inside vitaGL
(`sceGxmSetFragmentTexture`, mask rebuild) can only be reduced by batching or
a vitaGL patch, not by dedupe.

## Hardware measurement

On M13 with the same route, compare RVRC1 `F` (new default) against RVRC1
`E` (bit 0 off, old immediate path).

- **Counters:** `texture-state` per frame (`sampler_updates`,
  `sampler_deferrals`, `texenv_writes`, `texenv_skips`) and
  `render-work-cache` `sampler_writes` per frame.
- **Timing:** A3.5 perf render-stage p50/p95 and mesh-boundary time.
- **Expected:** `sampler_updates` near 0, `sampler_writes` down by about 130
  per frame, render-stage change within noise.
- **Visual:** no change in wrap or filtering; check HUD clamp and road seams.
