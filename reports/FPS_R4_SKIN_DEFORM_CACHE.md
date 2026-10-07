# FPS round 4: per-frame deformed-skin cache (SKIN_PATH_COST item 4)

Branch `worktree-agent-aa34ec0abfe4b5cf5` (continues `fps-r3/skin-deform-cache`
c5ad32d, cherry-picked onto main 95c4976). Nothing here is measured on hardware.

## Hypothesis

`Submit_Mesh_Internal` re-runs `MeshClass::Get_Deformed_Vertices` for every
submission of a skin. The same skin is submitted more than once per frame when
`MeshClass::Render` queues material passes after its base pass
(`staging/ww3d2/mesh.cpp:761-771`, flushed later through
`ww3d_dx8_boundary.cpp` `Render_Native_Material_Pass_Queue`), when a
material-pass-only render precedes the main render (BLOBS_PLUS character shadow
`wwphys/phystexproject.cpp:192`, stealth `stealtheffect.cpp:230-234`,
transition/grid effects), and when another camera renders the same pose. The
original `DX8SkinFVFCategoryContainer` deformed each visible skin once per flush.
Deformation of identical inputs is a pure recomputation and can be reused.

## Change

- `port/renderer/vita/ww3d_vita_skin_deform_cache.h` (new): fixed-capacity
  per-frame cache `SkinDeformCache<Vec3>` (32 entries, 8192 vertices, 1024 bone
  snapshots, allocated once on first store, ~244 KiB, recycled every frame, no
  growth). Exhaustion falls back to the original scratch path.
- `ww3d_vita_renderer.cpp` `Fetch_Cached_Deformed_Skin` (~L164), called from
  `Submit_Mesh_Internal` only at the deformation fetch (~L3857). The
  original scratch branch is unchanged:
  1. Every skin submission first tries `Find` (mesh hint + model + vertex count
     + pivot count + bitwise equality of every referenced pivot transform).
  2. On a miss, only a submission that another submission of the same mesh
     follows stores: a base pass that `MeshClass::Render` will follow with
     queued material passes (`Skin_Material_Pass_Follows`, the same predicate
     as mesh.cpp:763) or any material pass. Plain single-render skins keep the
     original scratch path and never allocate the cache.
- `Forget_Static_Mesh_Model` (~L4860) also forgets skin entries, so the
  original model reset/destructor/operator=/Make_Geometry_Unique hooks
  (`staging/ww3d2/meshmdl.cpp:123-166, 428-460`) cover it on every build.
- Statistics breadcrumb `skin-deform-cache` (stores/hits/misses/stale/
  overflows/forgets/allocation_failures, bytes) next to the static-mesh one.
  Misses count every uncached lookup, including plain skins.

## Invalidation argument (why a hit equals a fresh Get_Deformed_Vertices)

`MeshModelClass::get_deformed_vertices(dst_vert,dst_norm,htree)`
(`staging/ww3d2/meshmdl.cpp:300-329`) is a pure function of the model's
`Vertex`, `VertexNorm` and `VertexBoneLink` arrays, `Get_Vertex_Count()`, and
`htree->Get_Transform(bonelink[vi])` for each referenced pivot.
`OPTIMIZE_VNORMS` is undefined, so normals are read raw, and
`Submit_Mesh_Internal` calls `Get_Vertex_Normal_Array()` (dirty-normal
recompute) before every fetch anyway. The VFP code is deterministic: no fast-math,
and GCC does not auto-vectorize non-IEEE NEON floats.
- Model arrays: only mutated by load/Reset/operator=/Make_Geometry_Unique,
  which call `Forget_Static_Mesh_Model` first. `MeshClass::Scale` makes the
  geometry unique before `Model->Scale` (mesh.cpp:478,510). The host test pins
  all of these.
- Bone transforms: each referenced pivot's 48-byte Matrix3D is copied at store
  time and memcmp-compared at lookup. HTree updates, cinematics, Control_Bone,
  Set_HTree/model reassignment, a second render or camera, and
  render-to-texture/shadow/projector passes all either keep the same bits
  (reuse is exact) or miss. There is no original per-HTree serial. The
  hierarchy-valid flag is a boolean that every `Update_Sub_Object_Transforms`
  sets again (animobj.cpp:810), so it cannot prove two renders saw one pose.
  That is why the comparison is by value, not by flag or by "same submit".
- Mesh destruction / address reuse / LOD switch: the mesh pointer is only a
  lookup hint, never dereferenced. A hit still requires the model and transform
  inputs to match, so a recycled address cannot change output. No serial is
  needed. Entries never outlive the frame (`Begin_Frame(g_statistics.frames)`).
  Queued material-pass tasks hold mesh refs.
- Pointer lifetime: returned arrays live until the next frame's first store.
  The draw consumes them immediately (same contract as the existing scratch
  buffer). `Release()` is only called from renderer shutdown.

## Runtime switch

On by default in campaign builds. `ux0:data/renegade/user/config/skin-deform-cache-v1.flag`
containing exactly `RVSD1 0\n` disables it (same pattern as
`static-mesh-cache-v1.flag`/`RVSM1`). The global defaults to off and is enabled
only by `Read_Skin_Deform_Cache_Mode()` (non-M00-demo Vita init), so the M00
demo and any other target keep the original path. Breadcrumb at init:
`skin-deform-cache version=1 enabled=... acceptance=unassessed`.

## Tests run

- `python3 -m unittest tools.test_vita_skin_deform_cache -v`: 6/6 PASS. The C++
  harness `tools/vita_skin_deform_cache_test.cpp` is built with
  `-fsanitize=address,undefined -Werror`. Every simulated submission is
  memcmp-checked against a fresh deformation of the live inputs. It covers base
  pass followed by material passes, another camera reusing the pose, a
  material-pass-only render followed by the main base pass, bones changing
  between two renders in one frame (with and without material passes, and
  reverting to the old pose), bones changing between a base pass and its queued
  material pass, a +0/-0 bitwise miss, unreferenced pivots, the model hook,
  a negative control showing the hook is load-bearing, model reassignment,
  HTree replacement, frame rollover, mesh address reuse, capacity exhaustion
  (entries/vertices/bones), and 30k randomized steps.
- `python3 -m unittest tools.test_vita_indexed_state_contract
  tools.test_vita_static_mesh_cache tools.test_vita_skin_submission_contract`:
  27/28 pass. The one failure,
  `test_vita_boundary_uses_original_material_color_with_textured_skin_passthrough`,
  is pre-existing and unrelated: its regex expects the pre-hoist
  `skin_color_passthrough` line, and main 95c4976 already has
  `= batch_skin_color_passthrough;`. This diff does not touch that code.
- ARM TU (`arm_tu_check.sh ... port/renderer/vita/ww3d_vita_renderer.cpp
  -Werror=shadow=local`, real VitaSDK -O3 flags): `ARM TU OK` (843,984-byte
  object). No new warnings, only the pre-existing staging `rendobj.h:268`
  typedef warning.

## Expected gain (estimate, unmeasured)

Deformation is ~60-120 cycles/vertex (SKIN_PATH_COST). That is ~20-40 us per
155-vertex soldier mesh at 444 MHz, saved per avoided redeform. Validation is
~10 x 48-byte memcmp per hit, about 1 us. Typical M13 frames without material
effects or rendered shadows: about zero gain, with <1 us/skin lookup overhead.
With a BLOBS_PLUS player shadow or stealth/transition/projector passes:
roughly 0.05-0.5 ms/frame. This is a small item. The large skin win is
vertex-array emission (item 1), which is not touched here.

## Hardware measurement to take

Fixed M13 replay/camera, A/B with `skin-deform-cache-v1.flag` = `RVSD1 0\n`:
compare mesh-boundary skin timing (RENEGADE_VITA_DETAILED_TIMING) and frame
p50/p95/p99. Read the periodic `skin-deform-cache` breadcrumb: hits/stores
show the reuse rate, and `stale`/`overflows` show churn. Also run one scene
with a stealth unit or a material effect to see non-zero hits. Visual check:
skinned characters must be pixel-identical between A and B.
