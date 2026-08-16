# A3.0 Renegade Terrain / Indexed-Buffer Rendering Boundary

Date: 2026-08-07  
Canonical EA revision: `3e00c3a1b97381bb28be89a35b856375e0629a08`  
Scope: read-only source audit; no upstream, staging, build, or renderer files were
changed while producing this report.

## Result

The first static-world terrain boundary is narrow and well defined. Original
`RenegadeTerrainPatchClass` already owns the loaded terrain grid, material/pass
partitioning, lazy buffer construction, transforms, lighting selection, and
draw sequencing. It must remain unchanged. The missing Vita functionality is a
generic implementation of the existing `VertexBufferClass`,
`IndexBufferClass`, and selected `DX8Wrapper` contracts beneath WW3D.

The correct path is:

```text
M00_Tutorial.lsd
  -> SaveLoadSystemClass / PhysStaticObjectsSaveSystemClass
  -> PhysicsSceneClass static-object factories and AAB linkage
  -> StaticPhysClass -> PhysClass embedded RenderObj factory
  -> RenegadeTerrainPatchClass (persist factory 0x00010003)
  -> original lazy base/alpha material-pass buffers
  -> original VertexBufferClass / IndexBufferClass ownership and locks
  -> selected original DX8Wrapper state/draw contract
  -> thin generic Vita indexed-draw backend
  -> vitaGL / Vita GPU
```

There is no architectural reason to add `Submit_Terrain`, extract terrain
vertices in the application, or construct a second terrain/world renderer.

## 1. Original M00 static-world path

The source-authoritative load path is:

1. `CombatGameModeClass::Load_Level` calls
   `CombatManager::Pre_Load_Level`, starts the original threaded load, and
   performs original post-load processing
   (`Code/Commando/combatgmode.cpp:614-717`).
2. The load thread reloads definitions, calls
   `SaveGameManager::Pre_Load_Game`, optionally preloads original dependencies,
   and calls `SaveGameManager::Load_Game`
   (`Code/Combat/combat.cpp:301-424`).
3. For a `.mix` request, `Pre_Load_Game` derives `<root>.ldd` and `<root>.lsd`.
   `Load_Game` reads the LDD level-info map filename, attempts the optional
   level DDB, then calls `SaveGameManager::Load_Level`; that loads the LSD via
   the ordinary `SaveLoadSystemClass` dispatch
   (`Code/Combat/savegame.cpp:150-282,493-497`).
4. `PhysStaticObjectsSaveSystemClass::Load` receives its registered scene
   chunk and calls `PhysicsSceneClass::Load_Level_Static_Objects`
   (`Code/wwphys/physstaticsavesystem.cpp:126-143`).
5. `Load_Level_Static_Objects` dispatches the original static-object and
   static-light chunks. `Load_Static_Objects` looks up each outer persist
   factory, loads the `StaticPhysClass`, restores original AAB-tree linkage,
   then calls `Internal_Add_Static_Object`
   (`Code/wwphys/pscene_saveload.cpp:272-298,428-464`).
6. `StaticPhysClass::Load` delegates its base chunk to `PhysClass::Load`.
   `PhysClass::Load` looks up the embedded `PHYS_CHUNK_MODEL` persist factory,
   loads the genuine `RenderObjClass`, and installs it through `Set_Model`
   (`Code/wwphys/staticphys.cpp:591-620`, `Code/wwphys/phys.cpp:496-572`).
7. Terrain models are constructed by the original static
   `SimplePersistFactoryClass<RenegadeTerrainPatchClass,
   WW3D_PERSIST_CHUNKID_RENEGADE_TERRAIN>`
   (`Code/wwphys/renegadeterrainpatch.cpp:91-93`). The ID is
   `CHUNKID_WW3D_BEGIN + 3 == 0x00010003`
   (`Code/wwsaveload/saveloadids.h:59`, `Code/ww3d2/ww3dids.h:70-76`).
8. `Internal_Add_Static_Object` places the physical object in the ref-counted
   `StaticObjList`, notifies the inherited `SceneClass` about its model, and
   registers timestep/static-animation membership where applicable
   (`Code/wwphys/pscene.cpp:514-524`).
9. `Pre_Render_Processing` uses the original PVS/frustum/AAB culling and fills
   `VisibleStaticObjectList` and `VisibleWSMeshList` with Umbra disabled
   conservatively (`Code/wwphys/pscene.cpp:1087-1158`).
10. `Customized_Render -> Render_Objects -> Render_Object -> PhysClass::Render
    -> Model->Render` performs the original visible-world traversal and installs
    an object-specific `LightEnvironmentClass`
    (`Code/wwphys/pscene.cpp:1246-1253,1391-1474`,
    `Code/wwphys/phys.cpp:238-248`).

The durable M00 scan in `reports/A30_DEFINITION_TRACE.md` establishes 495
static physical objects and 192 lights. This audit does **not** yet claim a
terrain-patch instance count; that count must be derived from the first
successful original LSD runtime load, not guessed from filenames.

## 2. Ownership and lifetime

### Static world and model

- `RefPhysListClass` is `RefMultiListClass<PhysClass>`; adding to
  `StaticObjList` takes a reference and removing/resetting releases it
  (`Code/wwlib/multilist.h:332-432`, `Code/wwphys/physlist.h:50-54`).
- `Load_Static_Objects` releases the factory-returned temporary reference after
  `Internal_Add_Static_Object`, leaving scene ownership in the ref list.
- `PhysClass::Set_Model` takes a `RenderObjClass` reference; the destructor
  releases it (`Code/wwphys/phys.cpp:133-149,174-197`).
- `SceneClass::Add_Render_Object` only performs `Notify_Added`; PhysicsScene's
  physical lists, rather than a second render-object list, drive traversal
  (`Code/ww3d2/scene.cpp:153-172`).

### Terrain object and material passes

- `RenegadeTerrainPatchClass` owns the CPU arrays `Grid`, `GridNormals`,
  `VertexColors`, and `QuadFlags`, plus its `MaterialPassList`. It holds
  ref-counted `BaseMaterial` and `LayerMaterial`. `AreBuffersDirty` starts true.
- Each `RenegadeTerrainMaterialPassClass` owns persisted CPU data for both
  `PASS_BASE` and `PASS_ALPHA`: `VertexAlpha`, `GridUVs`, `QuadList`,
  `VertexRenderList`, and `VertexIndexMap`. It holds a ref-counted
  `TerrainMaterialClass`, plus runtime-only `VertexBuffers[2]` and
  `IndexBuffers[2]`
  (`Code/wwphys/renegadeterrainmaterialpass.h:63-110`).
- Save/load serializes the CPU pass lists/maps, not GPU buffers. First render
  lazily rebuilds every non-empty base/alpha buffer. A later dirty update first
  releases all old buffers, then recreates them
  (`Code/wwphys/renegadeterrainpatch.cpp:315-323,602-634`).
- Terrain and pass destructors use `REF_PTR_RELEASE` for buffers. The platform
  implementation must therefore preserve the ordinary `RefCountClass`
  contract; raw GPU/CPU allocations are subordinate resources, not owners of
  terrain objects.
- `TerrainMaterialClass::Set_Texture` retains the original asset-manager path:
  it normalizes the stored basename in release mode and calls
  `WW3DAssetManager::Get_Instance()->Get_Texture`
  (`Code/wwphys/terrainmaterial.cpp:94-118`).

## 3. Vertex and index buffer contract

Terrain requires only default/static buffers for its inherent base and alpha
passes. The disabled per-polygon branch in
`Render_Procedural_Material_Pass` is inside `#if 0`; the live procedural path
reuses the base static buffers (`Code/wwphys/renegadeterrainpatch.cpp:395-507`).
Dynamic ring and sorting buffers are therefore not required for the first
terrain draw, although the generic API should leave room for them.

| Contract | Original behavior to preserve |
|---|---|
| Counts | Vertex and index counts are `unsigned short`; indices are 16-bit. Reject overflow rather than silently truncate. |
| Creation | Terrain creates `DX8IndexBufferClass(poly_count * 3)` and `DX8VertexBufferClass(DX8_FVF_XYZNDUV1, vert_count)` with default/static usage. |
| Full write lock | Requires non-null buffer and `Engine_Refs()==0`, takes one ordinary ref, locks the complete resource, then unlocks and releases that ref in the lock destructor. |
| Append lock | Also checks `start + range <= count`; vertex offset is `start * FVF stride`, index offset is `start * sizeof(uint16_t)`. |
| Engine binding | `DX8Wrapper::Set_Vertex_Buffer` / `Set_Index_Buffer` release the previous engine reference, transfer ordinary pointer ownership with `REF_PTR_SET`, then add one engine reference to the new bound buffer. |
| Mutation rule | A bound buffer cannot be write-locked. Ordinary lifetime refs and `engine_refs` are distinct and both must remain correct. |
| Accounting | Preserve the original total buffer/count/byte counters so Vita memory pressure is measurable. |

Original evidence is in `Code/ww3d2/dx8vertexbuffer.cpp:76-209`,
`Code/ww3d2/dx8indexbuffer.cpp:70-128,184-268`, and
`Code/ww3d2/dx8wrapper.cpp:1601-1681`.

The smallest CPU resource behind each original buffer is an exact-size byte
allocation plus `{size, locked, lock_offset, lock_length, usage}` metadata.
For terrain:

- vertex bytes = `FVF_Info().Get_FVF_Size() * vertex_count`;
- index bytes = `sizeof(uint16_t) * index_count`;
- `Lock(0, 0)` means the whole vertex resource in the original DX8 contract;
- unlock makes writes immediately visible to a later indexed draw;
- allocation failure must propagate/fail visibly and be logged, never return a
  writable null pointer.

This CPU allocation can be the authoritative backing store initially. VitaGL
may consume it directly with client arrays or upload it lazily; no duplicate
terrain representation is needed.

## 4. Exact terrain vertex/index ABI

The original FVF is:

```text
DX8_FVF_XYZNDUV1 =
    D3DFVF_XYZ | D3DFVF_NORMAL | D3DFVF_DIFFUSE | D3DFVF_TEX1
```

`VertexFormatXYZNDUV1` is exactly:

| Offset | Field | Type |
|---:|---|---|
| 0 | `x, y, z` | three `float` |
| 12 | `nx, ny, nz` | three `float` |
| 24 | `diffuse` | `uint32` D3D ARGB |
| 28 | `u1, v1` | two `float` |
| 36 | end/stride | |

Source: `Code/ww3d2/dx8fvf.h:55-65,118-129`. Add compile-time assertions
for `sizeof(VertexFormatXYZNDUV1) == 36` and each offset on host and Vita.

`Build_Rendering_Buffers` constructs two triangles for each selected quad:

```text
v0, v2, v3
v2, v0, v1
```

Indices are remapped through the pass-local `VertexIndexMap`. Vertices copy
the original position, normal, UV, and packed color. Base alpha is 1.0;
alpha-pass color uses `VertexAlpha`
(`Code/wwphys/renegadeterrainpatch.cpp:646-780`).

The packed color value is `0xAARRGGBB`. On little-endian ARM the bytes in
memory are `BB GG RR AA`; do not blindly interpret offset 24 as an RGBA byte
array. Swizzle at the generic upload/attribute boundary or use a shader/input
format that explicitly consumes BGRA. Preserve the original CPU buffer bytes
for checksums and lock semantics.

## 5. Exact draw arguments

For every non-empty base/alpha pass, terrain binds its original buffers with
base vertex zero, binds stage-0 texture and null stage 1, selects the original
material/shader, then calls:

```cpp
DX8Wrapper::Draw_Triangles(
    BUFFER_TYPE_DYNAMIC_DX8,
    0,
    quad_count * 2,
    0,
    vert_count);
```

Source: `Code/wwphys/renegadeterrainpatch.cpp:516-590`.

The first argument is frequently misread. In this overload it only selects
sorting insertion when it is `BUFFER_TYPE_SORTING` or
`BUFFER_TYPE_DYNAMIC_SORTING`; every other value calls the ordinary indexed
`Draw`. It does **not** assert or imply that the actually bound terrain buffers
are dynamic (`Code/ww3d2/dx8wrapper.cpp:1905-1917`).

The generic indexed-draw meanings are:

- `start_index`: index-element offset, not a byte offset;
- `polygon_count`: triangle primitive count;
- `min_vertex_index`: minimum referenced vertex for D3D validation/range;
- `vertex_count`: number of vertices in the validated range;
- effective index start: `start_index + render_state.iba_offset`;
- effective base vertex: `render_state.index_base_offset +
  render_state.vba_offset`.

Terrain's offsets are all zero and every generated index must be less than
`vert_count`. A generic vitaGL mapping is:

```text
mode        = GL_TRIANGLES
index count = polygon_count * 3
index type  = GL_UNSIGNED_SHORT
index ptr   = bound_index_bytes + 2 * (start_index + iba_offset)
base vertex = index_base_offset + vba_offset
```

The installed vitaGL headers expose `glDrawElementsBaseVertex` and
`glDrawRangeElementsBaseVertex`; use the base-vertex form when the effective
base is nonzero. Do not pre-add the base into the persistent 16-bit index data.

## 6. Required state, camera, lighting, and textures

### Camera and scene state

The normal original render path supplies state above terrain:

- `CameraClass::Apply` updates the frustum and installs viewport, projection,
  and view (`Code/ww3d2/camera.cpp:712-733`).
- `SceneClass::Render` installs scene fog before customized traversal
  (`Code/ww3d2/scene.cpp:209-238`).
- terrain installs its world transform and the per-object light environment
  (`Code/wwphys/renegadeterrainpatch.cpp:315-339`).

The A2.2 Vita patch currently skips `CameraClass::Apply` in `WW3D::Render` and
skips the base `SceneClass` fog/state path. Those shortcuts were sufficient for
the CPU-projected DSP_O2TANK proof but must be narrowed/restored when the
generic wrapper boundary is available. Terrain will otherwise have neither the
original view/projection nor the intended scene state.

### Terrain material passes

`Initialize_Material` creates two original lit `VertexMaterialClass` objects:

- white ambient/diffuse, black specular/emissive, opacity 1, shininess 0;
- layer ambient and diffuse sources are `COLOR1`;
- prelit terrain also changes base ambient/diffuse sources to `COLOR1`.

Base uses `_PresetOpaqueShader` with fog forced on: LEQUAL, depth write,
ONE/ZERO blending, texture multiplied by primary diffuse, culling enabled.
Layer uses `_PresetAlphaShader` with fog forced on: LEQUAL, depth write off,
SRC_ALPHA/INV_SRC_ALPHA blending, texture multiplied by diffuse, culling
enabled (`Code/wwphys/renegadeterrainpatch.cpp:793-826`,
`Code/ww3d2/shader.cpp:55-86`).

`DX8Wrapper::Apply_Render_State_Changes` preserves the intended ordering:
shader, textures, material, lights, world/view, vertex buffer, index buffer,
then draw (`Code/ww3d2/dx8wrapper.cpp:1956-2058`). The Vita implementation
must at least map:

- viewport and world/view/projection matrices;
- depth compare and depth-write enable;
- cull enable/winding;
- alpha blend enable and source/destination factors;
- stage-0 texture enable/bind, texture-times-diffuse, U/V wrap/clamp, and
  min/mag/mip filtering;
- vertex material/color-source selection;
- scene fog state (it may be one-shot diagnosed and disabled for the first
  geometry proof if not yet implemented, but not silently discarded);
- ambient plus up to four directional lights.

`Set_Light_Environment` sets equivalent ambient and converts each Westwood
light to a D3D directional light, negating its direction; it disables remaining
slots up to four (`Code/ww3d2/dx8wrapper.cpp:2415-2443`). Preserve that
direction convention at the backend edge.

### Capability hazard

`ShaderClass::Apply` immediately dereferences
`DX8Wrapper::Get_Current_Caps()` for texture-operation and fog capability
decisions, while the current Vita boundary defines `CurrentCaps = NULL`.
Original buffer constructors also query T&L capability. Do not enter the new
state path with a null capability object.

Implement a small explicit Vita capability contract at the wrapper boundary,
advertising only operations that are genuinely mapped (at minimum
SELECTARG/MODULATE, the actual texture-stage count, ordinary T&L behavior, and
fog policy). Do not instantiate the original hardware-probing `dx8caps.cpp` or
invent support for bump maps, N-patches, or render-to-texture. If introducing a
full `DX8Caps` object is disproportionately coupled to Direct3D enumeration, a
small exact `RENEGADE_VITA_PORT` capability query used by `ShaderClass::Apply`
and buffer construction is the cleaner platform seam.

### Current texture gap

The current A2.2 Vita patch marks `TextureClass` initialized while retaining a
null `D3DTexture`. Therefore original terrain texture names and
`TextureClass` ownership load correctly, but no pixels become resident. Do not
replace `TerrainMaterialClass` or asset lookup. For the earliest world geometry
proof, the generic texture boundary may bind a logged neutral white fallback
when no native resource exists, so original vertex/material lighting remains
visible. The adjacent real fix is decode/upload/residency beneath the existing
`TextureClass`/`TextureLoader` relationship, keyed by the original texture
object; it is not a terrain-specific texture system.

## 7. Render-target/projector boundary

Terrain itself does not create or select a render target. It renders to the
current target.

`PhysicsSceneClass` defaults to static projectors off, dynamic projectors off,
and `SHADOW_MODE_NONE` (`Code/wwphys/pscene.cpp:199-201`). Even with both
projector classes disabled, `Pre_Render_Processing` calls `Apply_Projectors`,
whose final operation is the unconditional:

```cpp
DX8Wrapper::Set_Render_Target((IDirect3DSurface8 *)NULL);
```

Source: `Code/wwphys/pscene.cpp:1141-1145` and
`Code/wwphys/pscene_projectors.cpp:668-830`.

The initial Vita boundary must therefore accept null as “restore/retain the
default framebuffer” without failing. Non-null render targets are a distinct
projector/shadow feature and may remain a one-shot diagnosed unsupported
operation while the original defaults remain disabled. Never reinterpret a
non-null target as the default target.

## 8. Current port gap

The current renderer deliberately stops before this boundary:

- `port/renderer/vita/d3d8.h` is a compile-time DX8 scalar/data contract. It
  forward-declares vertex/index resources and has no buffer creation, lock, or
  indexed-draw surface.
- `port/renderer/vita/ww3d_dx8_boundary.cpp` currently stores transform and
  texture-stage skeleton state only. It does not implement original buffer
  binding, render/material/light state, viewport, default render-target restore,
  or indexed draws.
- `port/renderer/vita/ww3d_vita_renderer.cpp` exposes `Submit_Mesh`; it reads
  `MeshModelClass` CPU arrays, calls `CameraClass::Project`, and emits immediate
  `glBegin` triangles. This is the accepted A2.2 visual proof, but it cannot
  render `RenegadeTerrainPatchClass` and must not grow a terrain-specific path.
- `cmake/A22OriginalSources.cmake` does not include original
  `dx8vertexbuffer.cpp`, `dx8indexbuffer.cpp`, or `dx8wrapper.cpp`. The A3
  manifest compiles terrain/PhysicsScene as a compile frontier but does not yet
  link their real GPU boundary.
- `tools/host_a30_definitions/wwphys_definition_dx8_boundary.cpp` is correctly
  fail-fast for unexpected GPU calls. It is a definition-load sentinel, not a
  production renderer implementation.

## 9. Smallest correct implementation slice

Implement one coherent generic indexed-buffer slice; do not add an object-type
special case.

1. **Preserve the original buffer classes.** Compile the original
   `dx8vertexbuffer.cpp`, `dx8indexbuffer.cpp`, and `dx8fvf.cpp` behavior as far
   as practical. Put only resource allocation/lock/unlock/destruction beneath
   centralized platform hooks, or provide port-owned method bodies with exactly
   the original public/ref/lock/accounting semantics. Avoid a general fake
   Direct3D device implementation.
2. **Add CPU backing resources.** Support default/static VB/IB creation, full
   and append locks, unlock, destruction, exact size/count/FVF metadata, and
   memory counters. Treat dynamic/sorting access as a separately diagnosed
   unsupported path until a real caller reaches it; terrain inherent passes do
   not need it.
3. **Implement selected `DX8Wrapper` methods in the Vita boundary.** Required
   first: `Set_Vertex_Buffer`, `Set_Index_Buffer`, `Release_Render_State`,
   `Set_Viewport`, matrix setters, low-level render/texture-stage/material/light
   setters, `Set_Light_Environment`, null `Set_Render_Target`,
   `Apply_Render_State_Changes`, both indexed `Draw_Triangles` overloads, and
   ordinary triangle-list `Draw`.
4. **Expose one backend primitive, not a terrain API.** A suitable internal
   contract is:

   ```text
   BindVertexBuffer(buffer, fvf, stride, vertexOffset)
   BindIndexBuffer(buffer, indexOffset, baseVertex)
   ApplyState(transforms, viewport, shader, material, textures, lights)
   DrawIndexedTriangles(startIndex, triangleCount, minVertex, vertexCount)
   ```

5. **Use VitaGL client arrays initially.** For `XYZNDUV1`, bind position at
   offset 0, normal at 12, converted color at 24, UV at 28, stride 36, then
   issue `glDrawElements`/`glDrawElementsBaseVertex`. CPU-resident buffers are a
   valid first backend; later persistent GPU upload can remain invisible above
   the same abstraction.
6. **Restore original camera/scene setup.** Once viewport/matrix/fog methods are
   functional, remove the Vita skips around `CameraClass::Apply` and the normal
   `SceneClass::Render` state setup. Keep A2.2 `Submit_Mesh` temporarily as a
   regression fallback, then migrate MeshClass onto the same generic buffer and
   state route rather than deleting working evidence prematurely.
7. **Defer only genuine adjacent features.** Non-null render targets,
   dynamic/sorting buffers, procedural projector passes, bump mapping,
   N-patches, and texture compression variants can remain explicit one-shot
   unsupported diagnostics until the real world path reaches them.

This slice is sufficient for an original loaded terrain patch to allocate its
own buffers, populate them through original locks, bind its original material
passes, and submit genuine indexed geometry without bypassing WW3D.

## 10. Validation contract

Before hardware testing, add a host CPU backend fingerprint generated by the
original terrain draw path:

- loaded `RenegadeTerrainPatchClass` object count, names, and class IDs;
- material count and non-empty base/alpha pass counts;
- total original VB/IB objects, bytes, vertices, indices, and triangles;
- FVF/stride and per-buffer CPU byte checksums;
- zero indices outside each bound vertex range;
- draw argument log including effective index start and base vertex;
- PhysicsScene visible static/world-space list counts;
- state fingerprint for transforms, depth, blend, cull, textures, and lights;
- exact first unsupported state/resource request, logged once;
- clean buffer unbind, reference release, and teardown under ASan.

The Vita runtime should append the same semantic fingerprint plus actual draw
counts, GL/backend errors, memory totals, and the first terrain submission to
`ux0:data/renegade/user/logs/a30-runtime.log`. Hardware remains the authority
for visible correctness. No retail files belong in the VPK, and no automatic
deployment is required.

## Implementation order recommendation

The shortest low-risk order is:

1. CPU buffer resources and host checksum test.
2. Generic wrapper bind/draw with zero transforms/state, then full original
   terrain buffer construction and draw fingerprint on host.
3. Viewport plus original camera world/view/projection matrices.
4. Opaque and alpha depth/cull/blend state.
5. Null/default render-target restore.
6. Vertex color and ambient/directional lighting.
7. Neutral logged texture fallback, followed immediately by original
   `TextureClass` native residency as world evidence demands it.
8. Run original PhysicsScene culling/traversal and package the first A3 world
   hardware candidate.

This order crosses the actual platform boundary while keeping the full
original M00 load, ownership, culling, terrain, material, and draw architecture
intact.
