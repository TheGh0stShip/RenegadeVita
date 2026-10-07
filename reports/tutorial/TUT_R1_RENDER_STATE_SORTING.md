# TUT-R1-13 — RENDER_STATE_SORTING (render-sort-v1, `RVSO1`)

Branch `tut-r1-13-render-sort`, based on `tutorial-r1/base` (45c6cf5, dev240).
This was source work only. Nothing was compiled, staged by script, run in
Vita3K or run on hardware. Every gain below is an estimate.

## Findings

### 1. The port draws every mesh as soon as it is traversed, in scene order

- Original: in `MeshClass::Render` (non-Vita branch, `staging/ww3d2/mesh.cpp:818`),
  each polygon renderer is linked into its texture category. Then
  `DX8RigidFVFCategoryContainer::Render` (`staging/ww3d2/dx8renderer.cpp:779-803`)
  draws, for each **pass**, every visible category (textures + material +
  shader) with all of that category's meshes. ZBIAS is raised by one per
  pass. `DX8MeshRendererClass::Flush` (`:1992-2027`) runs this for rigid
  containers first, then skins, then decals, then delayed passes.
- Vita: `mesh.cpp:749` calls `RenegadeVitaRenderer::Submit_Mesh` straight away.
  `Submit_Mesh_Internal` (`ww3d_vita_renderer.cpp:5083`) loads transforms and
  replays the mesh's static-cache entry (`Replay_Static_Mesh_Entry`, `:3411`).
  The replay draws pass 0 and then pass 1 for **that mesh**, then moves to
  the next mesh. The original per-texture/per-material bucketing is gone.

### 2. Bucketing *inside* a mesh is already as good as it gets

`tools/tutorial_render_state_census.py` parses the 639 meshes in
`M00_Tutorial.mix`. It selects passes the way `PRELIT_MODE_LIGHTMAP_MULTI_PASS`
(the default) does, and rebuilds the static builder's batch runs:

- Pass 0: 716 runs against 713 distinct states.
- Pass 1+: 359 runs against 311 distinct states.

The W3D exporter already groups polygons by material, so merging same-state
runs within a mesh would save about 3 draws across the whole level. **Rejected.**

### 3. The real cost is a pass-0/pass-1 flip on every lightmapped mesh

- 259 of the 639 meshes have two or three passes. These are the
  `tut_lm015` terrain and the `*_int_lm00x` building interiors.
- Pass 0 is opaque: LEQUAL, depth write on, MODULATE, `FOG_ENABLE`.
- Pass 1 is the lightmap: `SRCBLEND_ZERO`/`DSTBLEND_SRC_COLOR`, no depth write,
  primary gradient disabled (so `GL_REPLACE`), `FOG_WHITE` (fog setup at
  `meshmdlio.cpp:1700-1712` and `shader.cpp:280-297`).
- Under the per-mesh replay, every lightmapped mesh changes blend, depth
  mask, texenv and fog colour **twice**: base to lightmap, then lightmap to
  the next mesh's base.

In vitaGL (`build/deps/vitagl-demo/source/source/ffp.c`):

- `reload_ffp_shaders` builds the fixed-function mask from alpha test,
  texture count, colours, fog and texenv modes (`:461-528`).
- Texenv and fog are fragment-only fields (`:206-221`). A mask change looks
  up the fragment program cache and forces a blend relink (`:608-658`).
- Each relink calls `sceGxmShaderPatcherCreateFragmentProgram` (`:1016-1021`).
- A changed mask also re-uploads the whole fragment uniform block (`:1039-1105`).
- A blend change on its own also relinks.

Grouping by texture alone saves little: vitaGL sets the fragment textures on
every draw anyway (`:1506-1531`).

### 4. vitaGL re-patches the vertex program for every static mesh, by design

- Each replay starts and ends with `vglRenegadeInvalidateVertexAttributes`
  (`ffp.c:3953`, `ffp_dirty_vert_attr = 0xFFFF`).
- `glVertexPointer` and the other pointer calls mark attributes dirty
  (`ffp.c:78`, `:1723`).
- The next draw therefore calls `patch_vertex_program`, i.e.
  `sceGxmShaderPatcherCreateVertexProgram` (`:722-870`). That happens once
  per mesh, and once per pointer window.
- The pointers must be set again when the bound VBO changes, because vitaGL
  captures `vertex_array_unit` at pointer time. Merging draws across meshes
  is therefore impossible without a shared VBO.
- Vertex materials are separate objects for each mesh (`meshmdlio.cpp:972-986`),
  so the replay's state predicate changes at every mesh boundary.

Observed scale: the dev238 tutorial telemetry from the private device logs
works out to roughly 50–65 `Submit_Mesh` calls and 120–200 texture binds
per frame. So this is about a few dozen state flips per frame, not hundreds.

## Change

The window is open only in `PhysicsSceneClass::Render_Objects`'
world-space-mesh loop (identity-transform static meshes, i.e. the
lightmapped level geometry). It is opened by the new zero-fuzz patch
`port/patches/wwphys-tut1-render-sort.patch`, which is applied last in
`tools/stage_sources.sh` and is also present in tracked `staging/wwphys/pscene.cpp`.

Inside the window:

1. A cache-hit static replay is **queued** instead of drawn when every one
   of its batches passes `Opaque_Sort_Entry_Eligible`
   (`port/renderer/vita/ww3d_vita_opaque_sort.h`, `Opaque_Sort_Enqueue` `:3081`).
   The rule:
   - pass 0 may only contain BASE batches (no blend, depth and colour
     writes on, LESS/LEQUAL) or BASE_CUTOUT batches (the same, alpha tested);
   - later passes may contain BASE or OVERLAY batches (depth write off,
     EQUAL/LEQUAL);
   - an alpha-tested pass 0 is not allowed under later passes;
   - BARRIER classes (blended pass 0, ALWAYS/GREATER, colour-masked depth
     writers) never qualify.
2. **Anything else draws immediately, after flushing the queue.** That covers
   ineligible hits, cache misses, the immediate path, skins, procedural
   passes, and buffer releases (the release callback flushes first).
   Defensive flushes also sit at frame begin/end, every DX8 render-state
   change, viewport and render-target changes, and cache invalidate/forget.
   When `End_Opaque_Sort_Window` runs it flushes.
3. `Opaque_Sort_Flush` (`:2982`) replays the queue with
   `Replay_Static_Mesh_Entry`'s exact state sequence, in the order chosen by
   `OpaqueSortQueue::Plan`:
   - mode 1: pass-major (all pass 0, then all pass 1), submission order
     kept inside each pass;
   - mode 2: pass-major, grouped by texture/shader bucket in order of first
     appearance;
   - mode 3: submission order kept (a control).

   Consecutive batches with identical state skip reapplication even across
   meshes. Each mesh change rebinds its buffers and reloads its transforms
   through the GL-state shadow. Only one invalidate pair is issued per flush.

**Exactness argument.** BASE fragments end up as the nearest fragment
whatever order they are drawn in. OVERLAY passes run after their own mesh's
complete pass 0, so they can only pass where that mesh is the stored depth.
Order is therefore irrelevant except for exact depth ties between meshes.
Mode 1 keeps pass-0 order, so pass-0/pass-0 ties resolve exactly as before.
Mode 2 may resolve ties differently; it follows the original category idea
rather than traversal order. Copied batch records and the release-callback
flush mean a queued draw never sees freed buffers.

## Flag and default

`ux0:data/renegade/user/config/render-sort-v1.flag` must contain exactly
`RVSO1 N\n`, where N is 0 (off), 1, 2 or 3. The build default is
`RENEGADE_VITA_OPAQUE_SORT_DEFAULT` = **0 (off)**.

With the flag off the window never opens. Every added barrier is then a
no-op compare, so the GL call sequence is the same as dev240.

Telemetry:

- at init: `render-sort version=1 mode=…`
- every 120 frames:
  `render-sort frame=… windows flushes items batches ineligible oversize capacity_flushes state=submitted/executed shader=… binds=…`
- profiler scope: `Vita Render Opaque Sort Flush`

## Hypothesis ledger entry

| Field | Value |
| --- | --- |
| Hypothesis | Pass-major replay of lightmapped world meshes removes ~2 fragment-program/blend switches per mesh in exchange for ~1 extra VBO bind/vertex patch per multipass mesh. |
| Census (40 eligible meshes per window, archive order / random order) | Shader changes 44.0→14.7 (mode 1), →6.2 (mode 2) / 51.2→29.8, →10.1. Texture changes 55.8→40.1, →20.9 / 64.9→63.8, →38.5. Mesh binds 40→58.6, →63.4 / 40→58.0, →61.1. |
| Estimated gain | 0–0.5 ms/frame in world-heavy tutorial views (about 1% of the 33–41 ms dev238 render stage). The net can be **≈0 or negative** if vertex-patch lookups cost more than fragment relinks. |
| Risk | Exact depth ties between coplanar world meshes (mode 2 most, mode 1 overlay-only); a GL state user inside the world-space loop that was missed (none found: only `MeshClass::Render` runs there, and material passes, decals and static-sort meshes are queued until `WW3D::Flush`). |
| How to measure | See the A/B steps below. |
| Decision | Deferred until hardware A/B. Default off. |

## Verified vs unverified

Verified (host, no compiler):

- `python3 -m unittest tools.test_vita_opaque_sort` passes 13/13.
  - The Python reference model (`tools/vita_opaque_sort_model.py`) covers
    the classification table, eligibility, and stable pass-major / grouped
    / identity plans.
  - A depth-buffer rasterizer finds 0 differences over 1,500 random
    tie-free scenes (more than 1,000 queued multipass meshes) for modes 1, 2 and 3.
  - Negative control: queueing alpha-tested bases under overlays does diverge.
  - With exact ties, mode 1 stays exact for pass 0 and mode 2 can diverge
    (documented).
  - Wiring/contract checks pass, and a zero-fuzz reverse dry-run of the
    patch against tracked staging succeeds.
- Ad-hoc mutation runs in the rasterizer:
  - drawing higher passes first: 535 of 800 scenes diverge;
  - queueing everything: 138 diverge;
  - allowing a pass-0 overlay: 33 diverge;
  - the real rule: 0 diverge.
- Existing compiler-free contracts pass: `test_vita_indexed_state_contract`,
  `test_vis_culling_contract`, the text tests of `test_vita_static_mesh_cache`
  and `test_vita_skin_deform_cache`, and the shadow raw-call contract.
- `renegade_patch_inventory.py --count` reports 578 and the registry is
  valid.

Unverified:

- **Not compiled.** The ARM build, the host harnesses that compile
  production slices, and the new `tools/test_vita_opaque_sort_native.py`
  (which compiles the header against the model) have **not** been run.
- The native test's Python side was exercised only with an emulated driver.
- `staging/PATCH_INVENTORY.json` is stale (577 → 578). The coordinator must
  re-run `tools/stage_sources.sh` to refresh the receipt.
- No Vita3K run, no hardware run, no visual check.

## Hardware A/B (tutorial route)

1. Use one build and the same save. Stand at three fixed points: the
   tutorial start inside the building, the Gunner range, and the base
   overlook (terrain plus building interiors in view). Hold the camera
   still for 600 frames at each.
2. Run four times with: no flag (mode 0), `RVSO1 3`, `RVSO1 1` and `RVSO1 2`.
3. Compare:
   - frame p50/p95/p99;
   - the render stage;
   - the frame-profile scopes `Vita Render Opaque Sort Flush`,
     `Vita Render Static Cache Replay` and `Vita Render Submit Mesh`;
   - the `render-sort` state/shader/binds ratios;
   - `gl-state-shadow` raster skips.
4. Reading the results:
   - Mode 3 against mode 0 isolates the cost of the queue itself.
   - Modes 1 and 2 against mode 3 isolate the cost of reordering.
5. Visual check: take screenshots at the same spots. Look for:
   - lightmap intensity on terrain and interiors;
   - the 3-pass `BLEND` terrain layers;
   - alpha-tested ladders, cracks and fences;
   - coplanar road/terrain seams (z-fight tie risk);
   - decals and HUD.

   Modes 3 and 1 should look identical to mode 0. Report any difference in
   mode 2 as a tie.
6. With `RENEGADE_VITA_DETAILED_TIMING`, note that `mesh-boundary-time` no
   longer contains the time of queued draws; that time moves into the flush
   scope.

## Files

New:

- `port/renderer/vita/ww3d_vita_opaque_sort.h`
- `port/patches/wwphys-tut1-render-sort.patch`
- `tools/vita_opaque_sort_model.py`
- `tools/test_vita_opaque_sort.py`
- `tools/test_vita_opaque_sort_native.py`
- `tools/vita_opaque_sort_test.cpp`
- `tools/tutorial_render_state_census.py`

Modified:

- `port/renderer/vita/ww3d_vita_renderer.cpp` (one new block next to the
  static cache, plus one-line barriers)
- `ww3d_vita_renderer.h` (the window API)
- `ww3d_vita_static_mesh_cache.h` (`StaticMeshBatch::pass`)
- `staging/wwphys/pscene.cpp`
- `tools/stage_sources.sh` (one apply line at the end)

Follow-ups, if hardware shows a gain:

- Extend the window to the static-objects loop. This first needs barriers
  on the DX8 boundary's texture and texture-stage entry points.
- Add a vitaGL patch that skips the vertex re-patch when only buffer
  addresses change. That would remove the extra-bind cost entirely.
