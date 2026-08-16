# A2.x/A3.0 Runtime Dependency Analysis

Canonical source: `electronicarts/CnC_Renegade`, pinned for A2.0 to commit
`3e00c3a1b97381bb28be89a35b856375e0629a08`.

The repository contains 1,490 C/C++ translation units. The initial runtime
slice follows the original dependency direction instead of introducing a new
engine or asset format:

```text
Vita bootstrap
  -> original BitStreamClass / cBitPacker
     -> original cEncoderList / cEncoderTypeEntry
        -> original cMathUtil::Round
           -> WWMath inline primitives
```

Five original translation units are linked in A2.0: all four sources in
`Code/wwbitpack` plus `Code/wwutil/mathutil.cpp`. Compatibility is centralized
around fixed platform types, MSVC spellings, the `MISCUTIL_EPSILON` dependency,
and Windows-compatible 16-bit `WCHAR` semantics. Upstream remains pristine;
staged copies receive one tracked mechanical patch for three GCC 15 syntax
issues.

The next source-integration boundary is the original `wwlib` file abstraction,
path translation, and MIX/archive access. DirectX, Miles, Bink, Umbra,
GameSpy/WOL, tools, installers, and editor code are outside this bootstrap and
are not represented by fake runtime implementations.

## A2.1 original filesystem/archive slice

Source inspection traced the retail startup architecture in
`Code/Commando/init.cpp` through `SimpleFileFactoryClass`,
`MixFileFactoryClass`, and `FileFactoryListClass`. The smallest viable read
slice is:

```text
original Commando-style factory chain
  -> Combat/FileFactoryListClass
     -> wwlib/MixFileFactoryClass
        -> wwlib/FileFactoryClass
           -> port-owned rooted factory boundary
              -> wwlib/BufferedFileClass
                 -> wwlib/RawFileClass
                    -> POSIX/newlib file operations

Mix lookup dependencies
  -> wwlib/CRC_Stringi
  -> wwlib/StringClass
  -> wwlib/DynamicVectorClass and SimpleDynVecClass
```

A2.1 adds eight original translation units: `wwfile.cpp`, `rawfile.cpp`,
`bufffile.cpp`, `ffactory.cpp`, `realcrc.cpp`, `mixfile.cpp`, `wwstring.cpp`,
and `Combat/ffactorylist.cpp`. With the five A2.0 units, 13 original
translation units are now built and linked.

`port/filesystem` is a thin platform boundary. It normalizes Windows path
separators, rejects absolute/device/traversing logical paths, resolves existing
retail components case-insensitively without altering them, routes reads to
the retail root, and routes writes to user/cache/mods. It returns an original
`BufferedFileClass` derivative, so MIX subfiles retain original
`RawFileClass::Bias` behavior. It is not an archive parser.

The host integration test opens unchanged `Data/always.dat` using original
`MixFileFactoryClass`, enumerates 15,161 stored filenames, locates
`dsp_o2tank.w3d`, and reads its 32,081-byte biased subfile through the original
factory chain. The first four bytes are `00000100` in the diagnostic's
little-endian hexadecimal presentation. No retail files are converted,
packaged, copied, or modified.

## A2.2 original WW3D runtime chain

`cmake/A22OriginalSources.cmake` is now the shared host/Vita manifest for a
coherent 105-translation-unit original-source slice:

| Original module | Translation units |
| --- | ---: |
| wwbitpack | 4 |
| wwutil | 1 |
| wwlib | 23 |
| WWMath | 21 |
| wwsaveload | 3 |
| Combat | 1 |
| ww3d2 | 52 |
| **Total** | **105** |

The achieved A2.2 path is no longer a W3D parser or direct custom-model draw.
The host semantic test and Vita target link the same original manifest. The
host semantic run executes, and both targets are wired to, the original asset,
object, scene, and camera ownership chain:

```text
original FileFactoryListClass / MixFileFactoryClass
  -> biased FileClass for Data/always.dat:dsp_o2tank.w3d
  -> WW3DAssetManager::Load_3D_Assets(FileClass &)
     -> ChunkLoadClass
     -> HTreeManager / HAnimManager
     -> registered PrototypeLoaderClass instances
        -> MeshLoaderClass::Load_W3D
           -> MeshClass / MeshModelClass / materials / textures / hierarchy
  -> WW3DAssetManager::Create_Render_Obj("DSP_O2TANK")
     -> PrototypeClass::Create
        -> original HLOD/RenderObj hierarchy
  -> SimpleSceneClass::Add_Render_Object
  -> WW3D::Init
  -> WW3D::Begin_Render
  -> WW3D::Render(SimpleSceneClass, CameraClass)
     -> CameraClass::On_Frame_Update
        (CameraClass::Apply is the DX8 device-state seam on Vita)
     -> SimpleSceneClass::Customized_Render
     -> RenderObjClass::Render
        -> MeshClass::Render
           -> Vita renderer at the former DX8 submission boundary
  -> WW3D::End_Render
```

This is the same minimal scene pattern used by
`Code/Commando/overlay.cpp:Overlay3DGameModeClass`: create an original
`SimpleSceneClass` and `CameraClass`, request an object through the original
asset manager, add it to the scene, and call `WW3D::Render`.

The accepted `dsp_o2tank.w3d` has 12 top-level chunks, including hierarchy
`DSP_O2TANK` with 11 pivots, an animation, a box, eight meshes, and an HLOD.
The achieved semantic run registers 10 prototypes, creates the original
10-node RenderObj hierarchy, and traverses eight meshes containing 357
vertices, 324 triangles, eight materials, and 12 texture references. One
complete original Scene/Camera frame submits all eight meshes through the
Vita boundary with geometry checksum `5704AB7D`. Thus parsing, prototype
creation, reference ownership, frustum/scene traversal, RenderObj dispatch,
and Mesh dispatch are original Westwood behavior; only graphics state,
texture residency, buffers, and actual GPU submission belong below the port
boundary.

Proven source compatibility changes remain tracked in
`wwlib-a22-gcc15.patch` and `ww3d2-a22-gcc15.patch`. The compile-time DX8 data
contract remains centralized in `port/renderer/vita/d3d8.h`.

## Original Commando startup and per-frame path

The canonical runtime startup above the platform boundary is:

```text
Code/Commando/WINMAIN.CPP:Start_Application
  -> create the application window/platform surface
  -> Code/Commando/mainloop.cpp:Game_Main_Loop
     -> Code/Commando/init.cpp:Game_Init
        -> construct the original retail FileFactoryListClass chain
           -> Always2.dat / always.dbs / Always.dat / Data/*.mix
        -> new WW3DAssetManager
           -> built-in mesh, hierarchy, collection, box, HLOD, aggregate,
              null, dazzle, and related prototype loaders
        -> WWMath::Init
        -> PathMgrClass::Initialize
        -> WW3D::Init
        -> WWPhys::Init
        -> WWSaveLoad::Init
        -> CombatManager::Scene_Init
           -> singleton PhysicsSceneClass
        -> CombatManager::Init
           -> CCameraClass::Init
           -> MainCamera = new CCameraClass
```

`Game_Main_Loop` repeatedly calls `_Game_Main_Loop_Loop`, which advances time,
input, and active game modes before `GameModeManager::Render`. The original
Combat frame envelope is:

```text
Code/Commando/gamemode.cpp:GameModeManager::Render
  -> PhysicsSceneClass::Pre_Render_Processing(*COMBAT_CAMERA)
  -> WW3D::Begin_Render
  -> active GameModeClass::Render calls
     -> Code/Combat/combat.cpp:CombatManager::Render
        -> WW3D::Render(BackgroundScene, MainCamera)
        -> WW3D::Render(COMBAT_SCENE, MainCamera)
  -> WW3D::End_Render
  -> PhysicsSceneClass::Post_Render_Processing
```

`PhysicsSceneClass::Pre_Render_Processing` performs the original static and
dynamic culling/PVS collection. Its non-Umbra branch is already an original
conservative fallback. `PhysicsSceneClass::Customized_Render` then walks the
visible `PhysClass` objects and dispatches their original RenderObjs into the
same WW3D path proven by the A2.2 object test.

## Original first-level and static-world load path

The concrete tutorial/single-player entry selects `M00_Tutorial.mix` in
`Code/Commando/dialogtests.cpp:StartSPGameDialogClass::On_Command`:

```text
GameInitMgrClass::Initialize_SP
  -> GameInitMgrClass::Start_Game
     -> Start_Client_Server
     -> activate CombatGameModeClass
     -> CombatGameModeClass::Load_Level
        -> LevelManager::Release_Level
        -> CombatManager::Pre_Load_Level
        -> CombatManager::Load_Level_Threaded
           -> LoadThreadClass::Thread_Function
              -> load Objects.DDB definitions
              -> AssetDependencyManager::Load_Level_Assets (.dep)
              -> SaveGameManager::Load_Game
        -> SaveLoadSystemClass::Post_Load_Processing
        -> CombatManager::Post_Load_Level
```

`Code/Combat/savegame.cpp:SaveGameManager::Pre_Load_Game` maps the MIX name to
the root `.lsd` static world and `.ldd` dynamic state. `Load_Game` reads the
level-specific `.ddb`, then passes the `.lsd` and `.ldd` through the original
`ChunkLoadClass` and `SaveLoadSystemClass`. The static physics dispatch is:

```text
Code/wwsaveload/saveload.cpp:SaveLoadSystemClass::Load
  -> Code/wwphys/physstaticsavesystem.cpp
     -> PhysStaticDataSaveSystemClass::Load
        -> PhysicsSceneClass::Load_Level_Static_Data
     -> PhysStaticObjectsSaveSystemClass::Load
        -> PhysicsSceneClass::Load_Level_Static_Objects
           -> Load_Static_Objects
              -> PersistFactoryClass::Load
              -> Internal_Add_Static_Object
           -> Load_Static_Lights
```

`Load_Level_Static_Data` restores scene settings, the static AAB tree, light
tree, dynamic-visibility tree, visibility tables, sun, and ambient state.
`Load_Static_Objects` uses registered original persist factories and retains
the serialized culling linkage rather than constructing a replacement world.

Read-only inspection of the unchanged retail `M00_Tutorial.mix` found
`m00_tutorial.dep`, `m00_tutorial.ldd`, and `M00_Tutorial.lsd`. The LSD has the
following top-level subsystems:

| Chunk | Original subsystem |
| --- | --- |
| `0x20000` | WWPhys static scene data |
| `0x20001` | WWPhys static objects and lights |
| `0x30005` | WWAudio static sound data |
| `0x40126` | Combat background manager |
| `0x40147` | Combat map manager |
| `0x40800` | Combat weather manager |

The static-object payload contains 495 objects plus 192 lights:

| Factory/class ID | Original class | Count |
| --- | --- | ---: |
| `0x20109` | `StaticPhysClass` | 424 |
| `0x2010B` | `StaticAnimPhysClass` | 5 |
| `0x20A00` | `DoorPhysClass` | 10 |
| `0x20A01` | `ElevatorPhysClass` | 4 |
| `0x20A02` | `DamageableStaticPhysClass` | 5 |
| `0x20A03` | `BuildingAggregateClass` | 47 |
|  | **Static objects** | **495** |
| `0x20102` | `LightPhysClass` | **192** |

These counts define the concrete persist-factory closure for the first M00
world milestone. `PhysClass::Load` also resolves definition IDs through the
original definition manager and restores persisted RenderObjs, so
`Objects.DDB`, the required definition factories, and the achieved WW3D object
graph are required dependencies rather than data that can be synthesized by
the port. An original `MixFileFactoryClass` probe confirms that the retail
provider chain contains no `M00_Tutorial.ddb`; the optional level-specific DDB
lookup in `SaveGameManager::Load_Game` therefore misses and continues by
design. Do not invent or generate that absent file.

## Optional boundaries and next coherent subsystem slice

`SaveLoadSystemClass::Load` skips unregistered top-level subsystem chunks.
The first static-world milestone can therefore retain the two WWPhys chunks
while deliberately deferring static WWAudio, background, weather, and map
manager state. Other clean boundaries are:

- compile with `UMBRASUPPORT=0` and use the original AAB/PVS fallback;
- use base `CameraClass` before taking on Combat-heavy `CCameraClass`, HUD,
  weapons, and camera collision behavior;
- use synchronous level loading initially before adapting the original
  `ThreadClass` boundary;
- permit asset-manager on-demand W3D loading initially, then add original
  `.dep` preloading after Vita memory use is measured;
- defer `.ldd` dynamic objects, GameObj gameplay, Miles/WWAudio, Bink,
  GameSpy/WOL, menus, and UI until the static world is visible;
- do not enter `GameInitMgrClass::Start_Game` yet, because original
  single-player currently starts a local network client and server.

The next coherent original-source slice after the achieved object/scene proof
is therefore an **M00 static-world kernel**, not full Commando startup:

```text
existing original MIX/FileFactory + WW3D asset/scene/camera slice
  -> WWPhys::Init + PhysicsSceneClass and original culling systems
  -> WWSaveLoad static-data/static-object dispatch
  -> original definition manager and Objects.DDB
  -> the seven required M00 persist-factory classes listed above
  -> consume M00_Tutorial.ldd level-info header
  -> load M00_Tutorial.lsd through ChunkLoadClass/SaveLoadSystemClass
  -> PhysicsSceneClass::Pre_Render_Processing
  -> WW3D::Render(PhysicsSceneClass, CameraClass)
  -> PhysicsSceneClass::Post_Render_Processing
```

After that world is visible, immediately add `.ldd` dynamic state and
GameObj/Combat systems, then `CCameraClass`, Vita input, and the original frame
update envelope. These are integration phases inside A3.0, not proposed tiny
milestones. The principal engineering risks are completing
material/texture/render-state behavior at the DX8/Vita boundary, preserving
retail 32-bit serialized pointer-remap identifiers on ARM, registering the
exact persist and definition factories, managing asset memory/VRAM, and
adapting the original thread boundary without changing save/load semantics.

## A3.0 verified retail route and exact call chain

Read-only host probes made through the already-integrated original
`MixFileFactoryClass`, `FileFactoryListClass`, biased `FileClass`, and
`ChunkLoadClass` establish the first-world contract without a replacement MIX
or level parser:

| Evidence | Verified value |
| --- | --- |
| First campaign archive | `Data/M00_Tutorial.mix` |
| Archive valid / filename enumeration | yes / **84 entries** |
| `m00_tutorial.ldd` | present, **148,616 bytes** |
| `M00_Tutorial.lsd` | present, **526,835 bytes** |
| `m00_tutorial.dep` | present, **4,619 bytes** |
| `m00_tutorial.ddb` | **absent** from M00 and the complete active provider chain |
| LDD first top-level chunk | `0x3C51C460` (`CHUNKID_LEVEL_INFO`) |
| LDD map-filename microchunk | ID 1, **`M00_Tutorial.lsd`** |
| LDD second top-level chunk | `0x3C51C461` (`CHUNKID_LEVEL_DATA`) |
| Global definitions | `Objects.DDB`, **5,157,396 bytes** |
| Definition provider | original `Data/always.dbs` `MixFileFactoryClass` |

`M00_Tutorial.mix` is the source-authentic tutorial choice at
`Commando/dialogtests.cpp:1049-1059`, and at 5,802,816 bytes it is the smallest
normal campaign MIX in this retail install. The original route is:

```text
StartSPGameDialogClass::On_Command
  -> GameInitMgrClass::Initialize_SP
  -> GameInitMgrClass::Start_Game("M00_Tutorial.mix", ...)
     -> Start_Client_Server                         [defer at network boundary]
     -> activate CombatGameModeClass
     -> CombatGameModeClass::Load_Level
        -> LevelManager::Release_Level
        -> CombatManager::Pre_Load_Level
        -> CombatManager::Load_Level_Threaded
           -> DefinitionMgrClass::Free_Definitions
           -> SaveGameManager::Load_Definitions("Objects.DDB")
           -> SaveGameManager::Pre_Load_Game
              -> m00_tutorial.ldd / M00_Tutorial.lsd
           -> optional AssetDependencyManager .dep preload
           -> SaveGameManager::Load_Game("m00_tutorial.ldd")
              -> read M00_Tutorial.lsd from CHUNKID_LEVEL_INFO
              -> attempt M00_Tutorial.ddb (absent; original no-op miss)
              -> SaveGameManager::Load_Level
                 -> SaveLoadSystemClass::Load(M00_Tutorial.lsd, false)
                    -> PhysStaticDataSaveSystemClass::Load
                       -> PhysicsSceneClass::Load_Level_Static_Data
                       -> PathfindClass::Load
                    -> PhysStaticObjectsSaveSystemClass::Load
                       -> PhysicsSceneClass::Load_Level_Static_Objects
        -> SaveLoadSystemClass::Post_Load_Processing
        -> CombatManager::Post_Load_Level
```

The static world is not a collection of manually placed meshes. Each observed
physics object is constructed by its original registered `PersistFactoryClass`;
`PhysClass::Load` restores its definition ID through `_TheDefinitionMgr`, then
loads its model through the already-proven `RenderObjPersistFactoryClass`,
which calls `WW3DAssetManager::Create_Render_Obj(name)`. The resulting render
path is:

```text
PhysicsSceneClass::Pre_Render_Processing(CameraClass &)
  -> original PVS/AAB/grid culling and LOD collection
WW3D::Render(PhysicsSceneClass, CameraClass)
  -> PhysicsSceneClass::Customized_Render
     -> PhysicsSceneClass::Render_Objects
        -> PhysClass::Render
           -> original RenderObjClass/MeshClass traversal
              -> existing Vita WW3D backend
PhysicsSceneClass::Post_Render_Processing()
```

## A3.0 subsystem classification

| Subsystem | Classification | Source evidence / reason |
| --- | --- | --- |
| FileFactory/MIX and on-demand WW3D assets | **REQUIRED FOR FIRST WORLD DISPLAY** | Every LDD/LSD/DDB/model request remains on the A2.1/A2.2 original factory chain. |
| `WWSaveLoad`, pointer remap, persist factories | **REQUIRED FOR FIRST WORLD DISPLAY** | LSD subsystem dispatch, serialized object construction, pointer fixups, and post-load callbacks. |
| `DefinitionMgrClass` + `Objects.DDB` | **REQUIRED FOR FIRST WORLD DISPLAY** | `PhysClass::Load` resolves every persisted `defid`; M00 has no substitute level DDB. |
| `PhysicsSceneClass`, PVS/AAB/grid/light culling | **REQUIRED FOR FIRST WORLD DISPLAY** | LSD chunks `0x20000`/`0x20001` restore the scene trees and 687 static objects/lights. |
| Original Pathfind database load | **REQUIRED FOR FIRST WORLD DISPLAY** | `PhysStaticDataSaveSystemClass::Load` dispatches its pathfind child directly to the `PathfindClass` owned by `PhysicsSceneClass`. |
| Seven observed M00 static persist classes | **REQUIRED FOR FIRST WORLD DISPLAY** | Exact LSD payload: StaticPhys, StaticAnimPhys, Door, Elevator, DamageableStaticPhys, BuildingAggregate, LightPhys. |
| `SaveGameManager` LDD/LSD routing | **REQUIRED FOR FIRST WORLD DISPLAY** | This is the original level-name and static-world load architecture; it should not be replaced with a port loader. |
| `CombatManager::Scene_Init` ownership | **REQUIRED FOR FIRST WORLD DISPLAY** | Creates/configures the canonical `PhysicsSceneClass`; a direct construction is acceptable only as a documented temporary compile bridge. |
| Texture decode/residency and material states | **REQUIRED FOR RECOGNIZABLE WORLD FIDELITY** | Implement below original Texture/Material abstractions as actual world submissions demand. |
| LDD `CHUNKID_LEVEL_DATA`, GameObj, scripts, star/player | **REQUIRED FOR FIRST INTERACTIVE GAMEPLAY** | In the retail SP route it loads only after the local server exists; static LSD loading is independent. |
| `CCameraClass`, `CombatManager::Think`, PhysicsScene update | **REQUIRED FOR FIRST INTERACTIVE GAMEPLAY** | Original camera/player and simulation sequencing. Base `CameraClass` suffices only for first static display. |
| `Input` over SceCtrl and `TimeManager` over monotonic Vita time | **REQUIRED FOR FIRST INTERACTIVE GAMEPLAY / PLATFORM BOUNDARY** | Preserve original input states and frame timing above the boundary. |
| `ThreadClass` level-loader execution | **PLATFORM BOUNDARY** | Synchronous invocation is a temporary valid bring-up route; preserve `Thread_Function` ordering before adding pthread/Vita execution. |
| DirectX/DX8 renderer implementation | **PLATFORM BOUNDARY, ALREADY PARTLY REPLACED** | WW3D/PhysicsScene remain original; expand the Vita backend only for states used by the real world. |
| Umbra | **OPTIONAL / DEFERRABLE EXTERNAL** | `UMBRASUPPORT=0` selects Westwood's original conservative PVS/AAB path. |
| WWAudio/Miles and LSD `0x30005` | **OPTIONAL / DEFERRABLE EXTERNAL** | Skip at registered audio subsystem boundary for first world; do not remove animation/game logic. |
| Background manager `0x40126`, map manager `0x40147`, weather `0x40800` | **OPTIONAL FOR FIRST GEOMETRY; LATER VISUAL/GAMEPLAY** | `SaveLoadSystemClass::Load` safely skips unregistered subsystem chunks; integrate immediately after the physics world is stable. |
| `.dep` bulk preloading | **OPTIONAL OPTIMIZATION** | `_preload_assets` is already conditional; on-demand loading preserves original asset manager behavior and reduces first memory risk. |
| UI/GDI fonts, menus, Bink | **OPTIONAL / DEFERRABLE EXTERNAL** | Not on the static world ownership or render chain. |
| GameSpy/WOL/multiplayer | **OPTIONAL / DEFERRABLE EXTERNAL** | Not needed for SP world display. |
| Local SP network client/server | **TEMPORARILY DEFER FOR FIRST WORLD; REQUIRED BY UNMODIFIED `Start_Game`** | `Initialize_SP` sets both required; `Start_Client_Server` starts both and waits for connection. Reconnect after static/dynamic Combat loading works. |

## Exact coherent source seeds and integration order

These are exact source-inspection seeds, not a claim that the cluster already
links. Old VC6 vtables and static factory registration can retain additional
methods even with section GC; compile/link diagnostics must expand the genuine
closure rather than replacing classes or stubbing engine-level behavior.

1. Complete the small original WWSaveLoad/definition layer. A2.2 already has
   `persistfactory.cpp`, `pointerremap.cpp`, and `saveload.cpp`; add all nine
   remaining runtime TUs as one coherent unit:

```text
Code/wwsaveload/definition.cpp
Code/wwsaveload/definitionfactory.cpp
Code/wwsaveload/definitionfactorymgr.cpp
Code/wwsaveload/definitionmgr.cpp
Code/wwsaveload/parameter.cpp
Code/wwsaveload/saveloadstatus.cpp
Code/wwsaveload/saveloadsubsystem.cpp
Code/wwsaveload/twiddler.cpp
Code/wwsaveload/wwsaveload.cpp
```

2. Add the first exact WWPhys static-world seed. This deliberately includes
   the scene's own static-data, culling, visibility, pathfind, projector/decal,
   and base-object ownership instead of fabricating a smaller world system:

```text
Code/wwphys/wwphys.cpp
Code/wwphys/physcon.cpp
Code/wwphys/physresourcemgr.cpp
Code/wwphys/pscene.cpp
Code/wwphys/pscene_collision.cpp
Code/wwphys/pscene_decal.cpp
Code/wwphys/pscene_lighting.cpp
Code/wwphys/pscene_projectors.cpp
Code/wwphys/pscene_saveload.cpp
Code/wwphys/pscene_vis.cpp
Code/wwphys/physstaticsavesystem.cpp
Code/wwphys/phys.cpp
Code/wwphys/staticphys.cpp
Code/wwphys/staticanimphys.cpp
Code/wwphys/accessiblephys.cpp
Code/wwphys/decophys.cpp
Code/wwphys/lightphys.cpp
Code/wwphys/animcollisionmanager.cpp
Code/wwphys/camerashakesystem.cpp
Code/wwphys/materialeffect.cpp
Code/wwphys/projectormanager.cpp
Code/wwphys/widgets.cpp
Code/wwphys/widgetuser.cpp
Code/wwphys/staticaabtreecull.cpp
Code/wwphys/dynamicaabtreecull.cpp
Code/wwphys/physaabtreecull.cpp
Code/wwphys/physgridcull.cpp
Code/wwphys/lightcull.cpp
Code/wwphys/vistable.cpp
Code/wwphys/vistablemgr.cpp
Code/wwphys/dyntexproject.cpp
Code/wwphys/phystexproject.cpp
Code/wwphys/physdecalsys.cpp
Code/wwphys/Pathfind.cpp
Code/wwphys/PathDebugPlotter.cpp
Code/wwphys/heightdb.cpp
Code/wwphys/PathfindPortal.cpp
Code/wwphys/PathfindSector.cpp
Code/wwphys/waypath.cpp
Code/wwphys/waypoint.cpp
```

3. Add the exact observed external static-object factories and original loader
   entry point:

```text
Code/Combat/doors.cpp
Code/Combat/elevator.cpp
Code/Combat/damageablestaticphys.cpp
Code/Combat/buildingaggregate.cpp
Code/Combat/savegame.cpp
Code/Combat/combat.cpp                 # retain Scene_Init first
```

The four external physics TUs have real vtables that reference Combat,
GameObj, and WWAudio behavior. Resolve genuine engine dependencies with
original TUs; isolate only WWAudio/platform calls at their subsystem boundary.

4. Add immediate WW3D dependencies exposed by `PhysicsSceneClass` and normal
   Commando loader registration, then expand only where real M00 assets demand:

```text
Code/ww3d2/light.cpp
Code/ww3d2/lightenvironment.cpp
Code/ww3d2/part_ldr.cpp
Code/ww3d2/part_emt.cpp
Code/ww3d2/part_buf.cpp
Code/ww3d2/sphereobj.cpp
Code/ww3d2/ringobj.cpp
Code/ww3d2/soundrobj.cpp               # audio behavior at WWAudio boundary
Code/ww3d2/textureloader.cpp            # platform decode/upload edge below it
Code/ww3d2/sortingrenderer.cpp
```

5. First semantic host route: create the original Combat physics scene, add the
   M00 factory to the existing list, load `Objects.DDB`, consume the LDD header,
   load the LSD synchronously through `SaveGameManager`, execute original
   post-load callbacks, then render through PhysicsScene/Base Camera. Record
   definition count, 495 objects, 192 lights, render-object count, geometry
   totals, missing factories/assets, and memory.

6. Without making a new milestone, reconnect `CombatManager::Pre_Load_Level`,
   the `.ldd` dynamic subsystem and original GameObj factories, `CCameraClass`,
   `CombatManager::Think`, `TimeManager`, and SceCtrl beneath original Input.
   Finally reconnect `CombatGameModeClass`, `GameModeManager`, and
   `GameInitMgrClass::Start_Game`; provide an offline/local-SP network boundary
   only if the original local client/server cannot yet be made operational.

## A3.0 terrain rendering boundary

The source-complete audit is retained in
`reports/A30_TERRAIN_RENDER_BOUNDARY.md`. The M00 terrain path remains entirely
original above the platform edge:

```text
SaveGameManager / LSD SaveLoad dispatch
  -> PhysStaticObjectsSaveSystemClass
  -> PhysicsSceneClass static factory and AAB linkage
  -> PhysClass embedded RenderObj persist factory
  -> RenegadeTerrainPatchClass (persist ID 0x10003)
  -> original lazy material-pass buffer construction
  -> original DX8Wrapper indexed-draw abstraction
  -> Vita graphics backend
```

`RenegadeTerrainPatchClass` must remain unchanged. Its real boundary is the
generic original `VertexBufferClass` / `IndexBufferClass` / `DX8Wrapper`
contract, not a terrain-specific Vita submission function. The first required
layout is static/default CPU-backed storage with 16-bit indices and the
original `XYZNDUV1` 36-byte vertex stride (position 0, normal 12, ARGB 24, UV
28). Preserve lock ownership (`Engine_Refs == 0`), ordinary versus engine
references, append offsets, draw counters, and the fact that the first
`Draw_Triangles` argument selects sorting behavior while already-bound buffers
remain the geometry source.

The first backend implementation must also provide a truthful Vita capability
object before any original shader or buffer constructor can dereference
`DX8Wrapper::CurrentCaps`. It should implement the state actually requested by
M00 traversal: viewport/matrices, depth test/write, culling, opaque and alpha
blend, stage-zero texture state, material/color sources, ambient light, and up
to four directional lights. Projectors default off, but the original path still
restores a null/default render target, so that operation must succeed while
non-null render targets may remain explicitly diagnosed. Texture residency may
initially use a one-shot-logged neutral fallback only to unblock first world
geometry; it must subsequently be implemented beneath the original
`TextureClass` ownership and lookup path. Do not introduce `Submit_Terrain`, a
custom terrain format, or manual terrain extraction.

## A3.0 executed integration frontier — 2026-08-07

The dependency map above has now been exercised substantially beyond compile
archaeology:

- The complete original 93-TU WWPhys runtime and 11-TU release WWSaveLoad
  closure compile for both host and Vita ARM.
- A 244-object host executable links the 209-source original definition/physics
  manifest plus the required original LZO/light/particle/shatter/render support.
- Against unchanged retail data, original FileFactoryList/MIX/biased FileClass
  -> ChunkLoad -> SaveLoadSystem -> DefinitionMgr passes 34/34. It loads 1,411
  definitions: 260 Twiddlers and 1,151 definitions from all 17 core WWPhys
  factories. The class fingerprint is
  `405/219/8/0/97/5/0/44/23/101/102/0/47/26/49/0/25`; the absent optional M00
  DDB remains a no-op and no fail-fast host GPU call occurs.
- The exact original M00 Combat factory slice (`assets`, `damage`, `reflist`,
  `buildingstate`, `doors`, `elevator`, `damageablestaticphys`,
  `buildingaggregate`, `savegame`) compiles 9/9 on host and Vita ARM.
- Original Commando `datasafe.cpp` and Combat `crandom.cpp` now compile on both
  ABIs. DataSafe preserves four-byte cipher words/keys/checksums through the
  explicit host-LP64 `DWORD` accommodation. Only its multiplayer chat tamper
  notification is routed through `RenegadeOptionalServices`; encryption,
  shuffling, integrity checks, handles, and detection stay original. This
  closes 32 of the prior 68 Combat linker symbols.
- `port/validation/a30_world_runtime.cpp` compiles on both ABIs and is the
  active executable continuation. It requires the three real save/load
  subsystems and 33 persist factories before loading, initializes original
  ArmorWarheadManager before definitions, preserves the optional DDB miss,
  loads `M00_Tutorial.lsd` with original WWSaveLoad/WWPhys, fingerprints the
  live PhysicsScene/RenderObj graph, then tears down in original ownership
  order. It contains no retail parser.
- The complete 248-original-source host target now links and executes that
  route against unchanged retail data: PASS 35/35 exact derived assertions.
  `Objects.DDB` yields 2,157 definitions with checksum
  `90DB91BE`; `M00_Tutorial.lsd` populates 495 static objects and 192 lights.
  Original iterators expose 1,615 RenderObj nodes, 1,288 meshes, 38,158
  vertices, 21,537 polygons, 1,177 prototypes, 1,684 visibility objects and
  347 sectors. The exact object/render/prototype checksums are
  `4A930F8A/BFA9C255/E835A45F`. Pathfind, post-load, optional-DDB no-op and
  teardown pass; no target-scoped optional GPU boundary is entered. The
  executable and three evidence logs are retained under
  `build/a30-m00-world-runtime-35of35/`, whose `SHA256SUMS.txt` verifies.
- The same live original world now completes the genuine render envelope twice
  with byte-identical logs: `CameraClass::Apply` ->
  `PhysicsSceneClass::Pre_Render_Processing` -> `WW3D::Begin_Render` ->
  `WW3D::Render` -> `WW3D::End_Render` ->
  `PhysicsSceneClass::Post_Render_Processing`. PASS 45/45; one frame submits
  652 original MeshClass objects, 30,603 vertices and 16,939 triangles with
  checksum `34FFAD42`. Indexed, rejected, unsupported, and unexpected GPU
  calls are zero. Exactly one NULL/default-target restore is the original
  projector cleanup contract; non-NULL targets remain fail-fast and unentered.
  Evidence is checksummed under `build/a30-m00-world-render-45of45/` and
  documented in `reports/A30_M00_WORLD_RUNTIME.md`.

The generic indexed renderer boundary is also implemented beneath original
`DX8Wrapper`, `FVFInfoClass`, `VertexBufferClass`, and `IndexBufferClass`.
Static/dynamic buffer reference ownership and offsets remain original; the
first supported real-world layout is FVF `0x152` (`XYZNDUV1`, stride 36) with
16-bit indices. Independent review corrected the initial CPU pre-divide at the
platform edge: the production path now loads the original world/view and
D3D-to-OpenGL depth-converted projection matrices through vitaGL, submits raw
object-space XYZ, and preserves homogeneous W for GPU clipping and
perspective-correct interpolation. Host semantic tests pass 14/14 and 8/8 with
checksum `65E5F668`, ASan/UBSan is clean, the renderer/boundary/original
FVF/VB/IB objects compile for Vita ARM, and the A2 `Submit_Mesh` body remains
byte-identical to the accepted baseline. Evidence is in
`reports/A30_INDEXED_BUFFER_BACKEND_REVIEW.md`.

At canonical-candidate time the build frontier was physical rather than host or
linker closure. The
shared Vita definition of `DX8Wrapper::Create_Render_Target(int,int,WW3DFormat)`
truthfully records an unsupported render-to-texture creation and returns `NULL`;
this is the original projector caller's allocation-failure path, not fabricated
offscreen rendering. The obsolete host-only duplicate was removed, so host and
Vita targets link the same boundary. The canonical `tools/build.sh` now clean
restages all 22 patches, validates retained A2 plus A3 host fingerprints,
compiles 248 original ARM translation units, and audits ELF/SELF/VPK output.
The accepted candidate is `../../dist/RenegadeVita-A3.0.vpk` with SHA-256
`b236b1b80361860f059dae9858bdc2fef67ee93df836e52df2cee3d89267270b`.
It contains only `eboot.bin` and `sce_sys/param.sfo`; the physical result is
recorded below.

The two-session contract now passes an isolated host test 11/11: one native
backend initialization, two logical renderer sessions, two logical shutdowns,
and lifecycle state preserved across frame-statistics reset. A separate timing
hazard was removed at the Vita callback boundary: A2.2 leaves the original
static `WW3D::SyncTime` advanced, and `WW3D::Shutdown` does not reset it, so A3
must call `WW3D::Sync(WW3D::Get_Sync_Time() + elapsed_ms)` rather than restart
at zero and unsigned-underflow `Get_Frame_Time()` on its first world frame.
This preserves WW3D's monotonic time contract without modifying its algorithm.

## A3.0 physical closure and A3.1 frontier — 2026-08-15

The canonical candidate passed physical Vita validation. The physical A3.0 set
is 36/36 and is intentionally distinct from the deterministic host 45/45 set.
The physical semantic world is 495 static objects, 192 lights, 1,615 nodes,
1,288 meshes, 38,158 vertices, and 21,537 polygons with fingerprints
`90DB91BE/4A930F8A/BFA9C255/E835A45F`. Its first presented frame is
654/30,795/17,041 checksum `0C3D50E4`; the host callback remains
652/30,603/16,939 checksum `34FFAD42`. Both preserve the same source ownership
and semantic world checks; their platform-specific traversal conditions and
validation counts are not conflated. Visual fidelity is not fully assessed
from log evidence.

The bounded A3.1 developer capture/telemetry facility is now complete alongside
the existing runtime/backend. SELECT writes a correlated resolved-frame clean
BMP, annotated BMP, JSON state, 240-frame in-memory-history CSV, and summary;
SELECT+L+R runs deterministic four-point `M00-fixed-camera-v1`. Capture and
write stalls are excluded from ordinary timing. The host C++ facility test is
14/14, its bundle comparator test passes, the retained M00 host runtime remains
45/45, and the Vita ARM target links and packages the capture path. This
instrumentation does not move the renderer boundary or change original
world/gameplay state.

The immediate frontier is therefore the original dynamic `.ldd` closure below,
followed by source-proven player/session ownership, physics registration, camera
ownership, centralized input/action translation, and original Combat update
order. Because this architecture is already source- and retail-payload-traced
in `reports/A30_COMMANDO_NEXT_RUNTIME.md`, the next phase is manifest expansion,
compatibility patching, and linker closure rather than further open-ended design.

In parallel, the next original engine frontier is the retail M00 `.ldd`
dynamic continuation. Original ChunkLoad inspection proves six top-level
subsystems: Combat (102,007 bytes), Conversation (25,396), PhysDynamic
(20,914), Encyclopedia (40), DynamicAudio (25), and Map (141). The Combat
payload creates 74 original GameObjs (22 Soldier, 31 ScriptZone, 8 PowerUp,
5 Simple, 4 Transition, 4 Building) and the physics payload creates 35 dynamic
Phys objects (5 Deco, 22 Human, 8 Phys3). Pointer remap and
`SaveLoadSystemClass::Post_Load_Processing` ordering remain mandatory. This
closure must replace the static-target-only scalar link shims with their
original owners (`combat.cpp`, `gameobjmanager.cpp`, `smartgameobj.cpp`,
`vehicle.cpp`, and `diaglog.cpp`) before progressing into player/camera/input
and the original Combat frame loop. The exact source trace is in
`reports/A30_COMMANDO_NEXT_RUNTIME.md`.
