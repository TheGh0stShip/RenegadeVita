# FPS round 4: STATIC_CACHE_THRASH

Branch `worktree-agent-a6217459056938ebf`. This finishes the partial round-3 branch
`fps-r3/static-cache-thrash` (0693bf9, cherry-picked onto main 95c4976), which
had stopped before testing. Nothing was measured on hardware or Vita3K.

## Hypothesis
`reports/STATIC_MESH_CACHE_REVIEW.md` covers the static mesh cache:
- Lit rigid instances that share one `MeshModelClass` and have no user lighting
  all map to one entry. Different rotations or light environments then
  invalidate each other on every draw. Within about 3 frames that shared entry
  goes VOLATILE, and VOLATILE was sticky, so every copy of the model fell back
  to per-corner immediate mode for the rest of the level.
- A vehicle that moves and then parks never regained caching. A VOLATILE entry
  also kept its GPU buffers.

## Change (default on; `static-mesh-cache-v1.flag` = `RVSM1 0` still disables the whole cache)
All code is port-side. No upstream or staging change, and no new patch.
- `port/renderer/vita/ww3d_vita_static_mesh_cache.h`: the state machine is now
  `Static_Mesh_Cache_Lookup<Ops>`, plain data that runs on the host.
  - **Per-instance lit entries (goal 1).** When a shared (model, user-lighting)
    entry builds with lit colours, it becomes a storage-less
    `PER_INSTANCE` family marker. The streams are then cached per drawing
    `MeshClass` (key: model, user lighting, instance; the entry carries the
    family id). Unlit entries stay shared. When a model or user-lighting key is
    forgotten, its marker is removed. The instance entries are then retired
    lazily by a family-id mismatch, and their material pointers are never read
    first.
  - **VOLATILE with hysteresis (goal 2).** Going VOLATILE frees the GPU buffers
    and batches (`Release_Buffers`) but keeps the snapshots. A VOLATILE entry
    compares its inputs once every 30 frames, and only when it is drawn. After
    4 unchanged samples (about 4 s) it rebuilds with no rebuild headroom left.
    Each further episode doubles the required samples, up to 64 samples (about
    64 s). A 1800-frame stable hit resets both the rebuild count and the level.
  - A change on the frame right after a build (`rapid`), or a key that is drawn
    again in the same frame with different inputs (`collision`), goes VOLATILE
    at once, so there is no burst of 5 wasted builds.
  - An oversize stream (more than a quarter of the budget) is now its own
    outcome. The entry is held ineligible until its inputs change and is no
    longer counted as an allocation failure.
- `ww3d_vita_renderer.cpp`: `Submit_Static_Mesh_Cache` is a thin
  `StaticMeshCacheOps` adapter over the production
  `Static_Mesh_Entry_Current` (now returns a reason),
  `Observe_Static_Mesh_Entry`, `Build_Static_Mesh_Streams` and
  `Upload_Static_Mesh_Entry`. A second line with the same `static-mesh-cache`
  tag is logged at the same time as the existing one (an extra field set would
  not fit the 512-byte breadcrumb). It shows rebuild reasons
  (counts/alternate/material/ambient/lights/world), collisions, rapid,
  `volatile_resident` (live count), recovered, oversize, `upload_bytes`,
  `max_frame_builds`, `max_frame_upload_bytes`, `lit_families` and
  `stale_instances`.
- Review fix (defensive): a marker reached without an instance key draws immediate.

## Goal 3: in-place texture/material swaps. Shown impossible from the original source; no per-draw check added
- Per-polygon texture/shader and per-vertex material pointers live in
  `MeshModelClass`'s private `MeshMatDescClass`. Every post-load writer is a
  `MeshModelClass` mutator, and those already forget the model
  (`ww3d2-a36-static-mesh-cache-lifetime.patch`; staged `meshmdl.h` has 12
  hooks and `meshmdl.cpp` has 5): `Set_*`, `Set_Single_*`, `Get_*_Array(create)`,
  `Make_*_Unique`, `Set_Pass_Count`, `Enable_Alternate_Material_Description`,
  `Reset`, `operator=`. Outside meshmdl, only `meshmdlio.cpp` touches
  `CurMatDesc`/`DefMatDesc`, and it runs at load time after `Reset`.
- `MeshModelClass::Replace_Texture` and `Replace_VertexMaterial` are `#if 0` in
  the original `meshmdl.cpp:209-266`, so `MeshClass::Replace_*` are no-ops.
  `MaterialInfoClass::Replace_Texture` has no callers.
- Building damage and power swaps use `Enable_Alternate_Materials`
  (`combat/building.cpp:774-780`). That path is hooked, and the alternate flag
  is also compared on every draw.
- Texture objects are bound live at replay (`Apply_For_Platform_Boundary`).
  Material object state is compared through the per-draw snapshot, which
  covers every field `Evaluate_Original_Material_Vertex_Color` and the UV
  state read.
- User lighting is filled in place only in `Load_User_Lighting`. It runs right
  after the persist factory creates the object (`rendobj.cpp:1243`), before
  any draw. `Install_User_Lighting_Array` forgets first.

## Invalidation argument (why replay equals recomputation)
The cache key only chooses which candidate entry to test. An entry replays
only after `Validate` has passed against this draw's inputs:
- counts and the alternate flag;
- every material snapshot;
- for lit entries, the equivalent ambient, up to 4 light directions and
  diffuse colours, the DX8 ambient, and the world 3x3 when lights > 0.

`Build_Static_Mesh_Streams` reads no `MeshClass` state except the
user-lighting pointer, which is part of the key. A reused `MeshClass` address
therefore cannot replay wrong streams. Model state is covered by the forget
hooks, and a forgotten family is never validated, only removed.
Equivalence of the builder with the immediate loop is unchanged and re-proven
(below).

## Tests (host, ASan + UBSan)
- `python3 -m unittest tools.test_vita_static_mesh_cache`: **6 tests OK**. It
  adds a lookup-wiring/telemetry pin and 7 C++ state-machine cases
  (`tools/vita_static_mesh_cache_test.cpp`): unlit sharing; lit instances
  replay without thrash; collision frees buffers; rapid change, 30-frame
  sampling, recovery after 4 then 8 samples, 1800-frame forgiveness; rebuild
  limit; forgotten family retired unread; oversize/allocation/ineligible holds.
- Mutation checks (each aborts the harness): no per-instance path; no family
  check; no collision detection.
- `python3 -m unittest tools.test_vita_static_mesh_equivalence`: **OK**. This
  fixes the triage `ValueError: substring not found`. The immediate loop moved
  from `Submit_Mesh` to `Submit_Mesh_Internal` and now loops on
  `draw_pass_count`. The harness gained those locals
  (`procedural_pass`/`triangle_at`/`texture_for`/...) and a
  `RENEGADE_FRAME_PROFILE` no-op. Result: 9 eligible, 2 lit and 10 ineligible
  fixtures, 387,522 corners matched.
- Not fixed: `tools.test_vita_mesh_batch` has the same anchor failure (out of
  scope).

## ARM
`arm_tu_check.sh ... port/renderer/vita/ww3d_vita_renderer.cpp`: **ARM TU OK**
for the cherry-pick and for the final tree (see the commit body).

## Risk
- Lit instances each hold their own GPU copy, bounded by the existing 24 MiB
  LRU budget and the 16384-slot table. Entries of destroyed `MeshClass`es keep
  buffers until LRU/stale eviction; a MeshClass-free hook needs a new ww3d2
  patch (follow-up).
- A moving lit instance costs at most one wasted build before VOLATILE, plus
  one per recovery attempt (with backoff). Table grows ~8 B/slot (~128 KiB .bss).

## Expected gain (UNMEASURED estimate)
Only scenes with several static lit copies of one model gain (parked vehicles,
turrets, repeated lit props). Each recovered mesh moves from per-corner
immediate mode to replay. At dev238's mesh-boundary cost of about 0.6 ms per
mesh, an estimate is 0–3 ms/frame in M13. Unlit level geometry is unaffected.

## Hardware measurement
On the M13 ambush, compare A/B runs with and without
`user/config/static-mesh-cache-v1.flag` = `RVSM1 0`:
- render p50/p95 and frame-profile totals for `Vita Render Immediate Mesh
  Pass` and `Vita Render Static Cache Build/Upload/Replay`;
- on the `static-mesh-cache` lines: `hits/(builds+rebuilds)` well above 1;
  `collisions`/`rapid` flat once units park; `volatile_resident` falling after
  vehicles stop with `recovered` > 0; `max_frame_builds`/`max_frame_upload_bytes`
  spikes; `oversize` separate from `allocation_failures`.
