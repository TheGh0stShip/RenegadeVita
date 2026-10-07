# Static mesh cache review (report only)

Scope: `port/renderer/vita/ww3d_vita_static_mesh_cache.h`, its use in
`port/renderer/vita/ww3d_vita_renderer.cpp` (`Submit_Static_Mesh_Cache`,
`Static_Mesh_Entry_Current`, `Capture_Static_Mesh_Lighting`,
`Upload_Static_Mesh_Entry`), and `port/patches/ww3d2-a36-static-mesh-cache-lifetime.patch`.
This is a static code review. Nothing was built and no host, Vita3K, or physical evidence was gathered.

## Rules as implemented

- **Key:** `(MeshModelClass*, user lighting array)`. Mesh instances that share a model and have no user lighting share one entry.
- **Eligibility:** the mesh must be non-skin, and every active stage must be `D3DTSS_TCI_PASSTHRU` with `D3DTTFF_DISABLE`. An entry that fails these checks becomes `INELIGIBLE`. It is reconsidered only when its counts, material snapshots, or alternate-material flag change, or when an allocation retry falls due.
- **Validity check on every draw:** vertex, triangle, and pass counts; `Is_Alternate_Material_Description_Enabled`; a field-by-field material snapshot (diffuse/ambient/emissive/opacity, mapper pointers, UV source, lighting/colour sources); and, for lit entries only, the lighting signature. The signature holds the environment flag, the DX8 ambient value (when there is no environment), equivalent ambient, up to 4 light directions and diffuse colours, and the world rotation/scale 3x3. Translation is excluded, and so is the world matrix when the light count is 0. All comparisons are exact float equality.
- **Volatility:** each miss on a READY entry, or each changed state, increments `rebuilds`. When `rebuilds > MaxRebuilds (4)` the entry becomes `VOLATILE`, so the 5th rebuild flips it. `rebuilds` is reset to 0 only on a hit where `frame - built_frame > 1800`. So the rule is "5 rebuilds with no 1800-frame stable gap between them", not a sliding 1800-frame window. VOLATILE is **sticky**: nothing ever clears it except `Invalidate_Static_Mesh_Cache` or `Forget_*`. `last_used_frame` keeps advancing while the mesh is drawn, so `Evict_Stale` never reclaims a VOLATILE entry either.
- **Budget:** 24 MiB total. One entry may use at most budget/4 = 6 MiB. When an entry does not fit, `Enforce_Budget` evicts least-recently-used READY entries that were not drawn this frame. If eviction fails, an allocation failure is recorded and the entry retries after `STATIC_MESH_CACHE_RETRY_FRAMES`. The table holds 16384 slots, and `Evict_Stale(1800)` runs only when an insert fails.
- **Invalidation hooks:** the device reset/teardown path (`ww3d_dx8_boundary.cpp:163`, `ww3d_vita_renderer.cpp:3058`) clears the whole cache, mirroring `DX8MeshRendererClass::Invalidate`. The a36 patch adds `Forget_Static_Mesh_Model` (model destruction/reinit) and `Forget_Static_Mesh_User_Lighting` (user-lighting array free/replace).

## M13 thrash risks

1. **Several lit instances sharing one model (highest risk).** Vehicles, turrets, and infantry props that use one `MeshModelClass` and have no user lighting map to a single entry. If two lit instances with different rotations, or different light environments, are visible together, each draw invalidates the other. The entry can rebuild twice per frame and turns VOLATILE within about 3 frames, after which it stays on immediate mode for every instance of that model. Cost: a few wasted builds plus GL buffer uploads, then permanent loss of caching for that model. That includes parked copies that would otherwise be cache-friendly. This defeats the cache rather than thrashing it indefinitely, but the early rebuilds come in bursts.
2. **Lit vehicles moving or turning under dynamic lights.** Any change to yaw, pitch, or turret rotation alters `world[]` when light_count > 0. The per-object `LightEnvironmentClass` also recomputes equivalent ambient and light directions as the object moves (translation does matter indirectly through this path). Because comparisons are exact floats, sub-ULP jitter also counts as a change. Result: about 5 consecutive rebuilds, then VOLATILE forever, even after the vehicle parks. The cost is bounded, but the steady-state saving is lost.
3. **Building power changes.** A single power-down/up changes ambient or light diffuse once, which costs one rebuild. With five or more changes without an 1800-frame (about 60 s at 30 fps) stable gap, every lit mesh inside the light radius becomes permanently VOLATILE. Flickering or blinking emissive/light sources (alarm lights, damaged-building flicker) cause the same thing quickly. A material whose colour is animated by script or a `VertexMaterial` time-driven change rebuilds every frame until it flips.
4. **Damage material swaps.**
   - An alternate-material toggle is detected and costs one rebuild (fine).
   - **Possible correctness gap, not thrash:** batches store `texture0/texture1/material` pointers captured at build time. The validity check compares only the cached material pointers against their own current state. A damage swap that changes which material or texture a pass references, without changing counts, the alternate flag, or the model (for example a texture replaced in the model's texture arrays, or a different `VertexMaterialClass` assigned), may not invalidate the entry. The cache would then replay stale textures. Verify whether M13 damage states use alternate materials (detected) or a model swap (Forget hook) rather than in-place texture replacement.
   - A swap to a whole new damaged model goes through Forget/Insert, which costs one cold build per model with no thrash.
5. **Budget churn.** Large M13 outdoor meshes, plus many building interiors drawn in alternating views (base interiors), can push past 24 MiB. LRU eviction protects only entries drawn in the current frame, so camera panning can evict and rebuild the same entries over and over. These rebuilds go through Insert, which means the eviction counter rises while `rebuilds` does not. Separately, a mesh above 6 MiB is never cached and is counted as an upload failure. Check the counters to tell it apart from a genuine allocation failure.

## Telemetry that would show it

These are the existing counters in the periodic cache log line (`ww3d_vita_renderer.cpp:~1920`):
- `rebuilds` rising in step with frames: per-frame thrash before entries go volatile.
- `volatile_entries` stepping up when vehicles start moving or power changes. A large total means caching has been lost (cases 1-3).
- The ratio of `hits` to `builds + rebuilds` per interval should be well above 1. Below about 1 means thrash.
- `evictions` and `allocation_failures` rising together while `Bytes()` sits near 24 MiB indicates budget churn (case 5).
- `Live()` and `Bytes()` show residency.

Missing fields worth adding (trace or sampled only):
- The **reason** for each rebuild: counts, alternate flag, material snapshot, lighting ambient, light direction/diffuse, or world matrix. This separates case 1 (alternating world matrices) from case 2.
- **Rebuilds per frame**, with a maximum, and the **number of distinct keys rebuilt per frame**.
- A **current VOLATILE resident count**, and the model name of each entry when it goes volatile. The existing counter is cumulative.
- An **instance-collision flag**: a rebuild where the same key was already used earlier in the same frame (`last_used_frame == frame` before the build). This directly detects case 1.
- **Evict-then-rebuild-within-N-frames** count for case 5, and an **oversize (>6 MiB) reject** counter separate from allocation failures.
- **Upload bytes per frame** from `Upload_Static_Mesh_Entry`.

## Suggested follow-ups (not implemented)
- When a key is reused in the same frame with a different lit signature, mark it volatile immediately (or later key lit entries per instance) so it skips the burst of wasted builds.
- Let VOLATILE entries decay back to eligible after a stable period, so parked vehicles and powered-down buildings regain caching.
- Include the batch texture pointers in the validity check, or confirm that the damage path never swaps textures in place.
