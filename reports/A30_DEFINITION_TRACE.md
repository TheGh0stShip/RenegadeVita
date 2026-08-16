# A3.0 Definition / Database Trace for M00 Static-World Loading

Date: 2026-08-07  
Canonical upstream: `electronicarts/CnC_Renegade` revision
`3e00c3a1b97381bb28be89a35b856375e0629a08`  
Scope: source-authoritative dependency trace and read-only retail-data
fingerprinting. This report does not alter the canonical source, staging, build
manifests, or retail data.

## Conclusion

The original definition path required before loading `M00_Tutorial.lsd` is:

```text
original FileFactoryListClass
  -> original MixFileFactoryClass for Always.dbs
  -> biased original FileClass for Objects.DDB
  -> ChunkLoadClass
  -> SaveLoadSystemClass (top-level subsystem 0x00000101)
  -> global DefinitionMgrClass
  -> registered PersistFactoryClass for each definition chunk
  -> original concrete WWPhys/Combat definition classes
  -> sorted DefinitionMgr registry
```

The retail `M00_Tutorial.mix` deliberately contains `m00_tutorial.lsd` and
`m00_tutorial.ldd`, but no `m00_tutorial.ddb`. The original loader derives and
attempts that optional level DDB. With the original file-factory fallback, the
missing file becomes an unavailable base `FileClass`; `Open(READ)` fails and
`ChunkLoadClass` yields no chunks. This leaves the already loaded `Objects.DDB`
definitions unchanged. A Vita port must preserve that no-data behavior and
must not synthesize a level DDB.

The M00 static physics data contains 687 objects in the seven relevant object
factory classes. Ninety-three objects carry a definition ID, and every one of
those 93 IDs resolves to one of six genuine persisted definition factory
classes in `Objects.DDB`. The other 594 are valid definitionless objects: 192
lights and 402 embedded-model `StaticPhysClass` instances.

## Original startup and file lookup

### Factory order

The original Commando initialization adds factories in this order:

1. base/raw factory;
2. `Always2.dat`;
3. `Always.dbs`;
4. `Always.dat`;
5. discovered `Data\\*.mix` archives.

Evidence: `Code/Commando/init.cpp:725-767`, especially lines 739-742 and 757.
The current rooted Vita/POSIX factory remains the platform boundary below this
original list.

`FileFactoryListClass::Get_File` checks the selected/search-start factory and
then every other registered factory for availability. If all providers miss,
it returns an unchecked file object from factory zero (the base factory):
`Code/Combat/ffactorylist.cpp:136-188`. `SimpleFileFactoryClass::Get_File`
constructs that raw/buffered object, while `RawFileClass::Open(READ)` returns
false for a missing file: `Code/wwlib/ffactory.cpp:233-303` and
`Code/wwlib/rawfile.cpp:381-469`.

### Retail archive evidence

A temporary read-only host probe used the already integrated original
`FileFactoryListClass`, `MixFileFactoryClass`, biased `FileClass`, and
`ChunkLoadClass`. It did not implement a replacement MIX or W3D parser.

| Archive | Original enumeration | Entries | Relevant content |
|---|---:|---:|---|
| `always.dat` | PASS | 15,161 | A2.1/A2.2 asset archive |
| `always.dbs` | PASS | 3 | contains `objects.ddb` |
| `Always2.dat` | PASS | 181 | supplemental archive |
| `M00_Tutorial.mix` | PASS | 84 | contains `.lsd` and `.ldd`, no `.ddb` |

`Objects.DDB` was found through the original list, opened through a biased
archive `FileClass`, and measured 5,157,396 bytes. Its top chunk is
`CHUNKID_SAVELOAD_DEFMGR == 0x00000101`.

`M00_Tutorial.lsd` was found in the real unchanged retail MIX and measured
526,835 bytes. `m00_tutorial.ldd` measured 148,616 bytes.

## Exact original load call path

`SaveGameManager::DefaultDefinitionFilename` is `"Objects.DDB"` at
`Code/Combat/savegame.cpp:67-71`.

The real world-load sequence is:

1. `CombatManager` frees definitions and calls
   `SaveGameManager::Load_Definitions()` before preprocessing/loading the map:
   `Code/Combat/combat.cpp:375-424`.
2. `SaveGameManager::Load_Definitions` calls
   `Load_Save_Load_System(filename, true)`:
   `Code/Combat/savegame.cpp:508-513`.
3. `Load_Save_Load_System` obtains the file from `_TheFileFactory`, opens it,
   constructs `ChunkLoadClass`, and invokes `SaveLoadSystemClass::Load`:
   `Code/Combat/savegame.cpp:542-555`.
4. `SaveLoadSystemClass::Load` resets the pointer remapper, dispatches each
   top-level chunk to its registered `SaveLoadSubSystemClass`, processes pointer
   remaps, and optionally runs post-load callbacks:
   `Code/wwsaveload/saveload.cpp:73-107`.
5. `_TheDefinitionMgr` is the global definition subsystem
   (`Code/wwsaveload/definitionmgr.cpp:51-55`) and reports chunk ID `0x101`
   (`definitionmgr.h:154-161`).
6. `DefinitionMgrClass::Load_Objects` looks up the exact persisted chunk ID in
   `SaveLoadSystemClass`, calls that registered factory, appends the returned
   `DefinitionClass`, sorts by definition ID, and assigns manager links:
   `definitionmgr.cpp:791-831`.
7. An unregistered definition chunk is intentionally skipped at lines 800-813.
   This makes a partial registration frontier possible without replacing the
   original database loader, although any definitions needed by loaded world
   objects must be registered and validated explicitly.

### Registration semantics

- Every `SaveLoadSubSystemClass` self-registers in its constructor:
  `Code/wwsaveload/saveloadsubsystem.cpp:42-53`.
- Every `PersistFactoryClass` self-registers in its constructor:
  `Code/wwsaveload/persistfactory.cpp:41-50`.
- Every `DefinitionFactoryClass` self-registers with
  `DefinitionFactoryMgrClass`: `definitionfactory.cpp:46-63`.
- `SimplePersistFactoryClass<T, ID>` reads the old serialized object token,
  allocates `T`, invokes `T::Load`, and registers old-to-new pointer remapping:
  `persistfactory.h:90-140`.
- `DefinitionClass` loads its stable 32-bit definition ID and `WWString` name
  from its base variables chunk: `definition.cpp:80-138`.
- `DefinitionMgr` performs Twiddler resolution in all normal lookup paths:
  `definitionmgr.cpp:161-170`, `202-211`, and `298-307`.
  `twiddler.cpp:48-72` declares both the original persist and definition
  factories. The retail DDB contains 260 `CHUNKID_TWIDDLER (0x102)` records.

## Missing `m00_tutorial.ddb` is a valid optional override miss

`SaveGameManager::Load_Game` reads the map name from the `.ldd`, strips its
four-character extension, appends `.ddb`, calls `Load_Definitions`, and then
calls `Load_Level`: `Code/Combat/savegame.cpp:238-305`, specifically lines
271-283.

For M00 this derives `m00_tutorial.ddb`. Read-only retail inspection proved:

```text
FileClass pointer: non-null (base-factory fallback)
Is_Available:      false
Open(READ):        false
Size:              -1
```

`Load_Save_Load_System` does not inspect the `Open` return code
(`savegame.cpp:544-549`). On an unopened raw file, the implicit read/open path
returns zero, and `ChunkLoadClass::Open_Chunk` returns false when it cannot read
an eight-byte chunk header (`Code/wwlib/chunkio.cpp:413-429`). Therefore
`SaveLoadSystemClass::Load` processes zero additional chunks. This is a benign
no-op after `Objects.DDB`, not a reason to fail M00 startup and not permission
to create a custom definition file.

Required semantic check: record the definition count before and after the
missing optional DDB attempt and require it to be unchanged.

## Definition factories present in `Objects.DDB`

The following counts were derived by walking the original `ChunkLoadClass`
structure and matching the canonical constants in
`Code/WWPhys/wwphysids.h:48-114`.

| Persist chunk | Original definition class | Count |
|---:|---|---:|
| `0x00020500` | `DecorationPhysDefClass` | 405 |
| `0x00020501` | `HumanPhysDefClass` | 219 |
| `0x00020502` | Light definition slot (no concrete retail class) | 0 |
| `0x00020503` | `MotorcycleDefClass` | 8 |
| `0x00020504` | `MotorVehicleDefClass` | 0 |
| `0x00020505` | `Phys3DefClass` | 97 |
| `0x00020506` | `ProjectileDefClass` | 5 |
| `0x00020507` | `RigidBodyDefClass` | 0 |
| `0x00020508` | `StaticPhysDefClass` | 44 |
| `0x00020509` | `WheeledVehicleDefClass` | 23 |
| `0x0002050A` | `StaticAnimPhysDefClass` | 101 |
| `0x0002050B` | `TimedDecorationPhysDefClass` | 102 |
| `0x0002050C` | `VehiclePhysDefClass` | 0 |
| `0x0002050D` | `TrackedVehicleDefClass` | 47 |
| `0x0002050E` | `VTOLVehicleDefClass` | 26 |
| `0x0002050F` | `DynamicAnimPhysDefClass` | 49 |
| `0x00020510` | `ShakeableStaticPhysDefClass` | 0 |
| `0x00020511` | `AccessiblePhysDefClass` | 25 |
| `0x00020C00` | `DoorPhysDefClass` | 102 |
| `0x00020C01` | `ElevatorPhysDefClass` | 64 |
| `0x00020C02` | `DamageableStaticPhysDefClass` | 331 |
| `0x00020C03` | `BuildingAggregateDefClass` | 249 |

The table contains 1,897 WWPhys/external-physics definitions. The definition
types on the M00 static-display critical spine (Static, StaticAnim, Accessible,
Door, Elevator, Damageable, and BuildingAggregate) total 916 records. Loading
the full already-compiled WWPhys module will naturally register and load the
other original WWPhys types too; they should not be artificially hidden.

## Exact M00 static-object definition references

Definition IDs were read from the source-defined `PhysClass` variables chunk
`0x00660055`, microchunk index 6 (`PHYS_VARIABLE_DEFID`), as declared and used
at `Code/WWPhys/phys.cpp:91-107` and `496-565`. The probe used the original
archive/file/chunk stack; it was forensic validation only, not runtime code.

| Object persist factory | Object type | Objects | Definition-backed | Valid no-definition |
|---:|---|---:|---:|---:|
| `0x00020102` | `LightPhysClass` | 192 | 0 | 192 |
| `0x00020109` | `StaticPhysClass` | 424 | 22 | 402 |
| `0x0002010B` | `StaticAnimPhysClass` | 5 | 5 | 0 |
| `0x00020A00` | `DoorPhysClass` | 10 | 10 | 0 |
| `0x00020A01` | `ElevatorPhysClass` | 4 | 4 | 0 |
| `0x00020A02` | `DamageableStaticPhysClass` | 5 | 5 | 0 |
| `0x00020A03` | `BuildingAggregateClass` | 47 | 47 | 0 |
| **Total** | | **687** | **93** | **594** |

Exact ID fingerprint:

- StaticPhys: `327750002 x22` -> factory `0x20508`.
- StaticAnim: `327760008 x1`, `327760009 x1`, `327760028 x3` ->
  factory `0x2050A`.
- Door: `328960003 x1`, `328960081 x2`, `328960102 x7` ->
  factory `0x20C00`.
- Elevator: `328970059 x4` -> factory `0x20C01`.
- Damageable: `328980076 x2`, `328980127 x3` -> factory `0x20C02`.
- BuildingAggregate -> factory `0x20C03`:
  `328990129..328990139 x1 each`; `328990141..328990146 x1 each`;
  `328990199 x2`; `328990200 x2`; `328990202 x2`; `328990203 x2`;
  `328990204 x2`; `328990215 x1`; `328990216 x1`; `328990218 x1`;
  `328990219 x1`; `328990220 x1`; `328990234 x2`; `328990237 x4`;
  `328990238 x4`; `328990240 x4`; `328990247 x1`.

All 93 serialized IDs matched a definition identity in `Objects.DDB`; unresolved
count was zero. These generated static-physics definitions have empty names in
the retail DDB, so ID, concrete class ID, persist factory ID, and object count
are the stable semantic fingerprint—not the display name.

## Exact translation-unit closure

### WWSaveLoad definition/database runtime

The complete release-mode loading closure is:

- `Code/wwsaveload/saveload.cpp` (already in A2.2)
- `Code/wwsaveload/persistfactory.cpp` (already in A2.2)
- `Code/wwsaveload/pointerremap.cpp` (already in A2.2)
- `Code/wwsaveload/saveloadsubsystem.cpp`
- `Code/wwsaveload/saveloadstatus.cpp`
- `Code/wwsaveload/definition.cpp`
- `Code/wwsaveload/definitionmgr.cpp`
- `Code/wwsaveload/definitionfactory.cpp`
- `Code/wwsaveload/definitionfactorymgr.cpp`
- `Code/wwsaveload/twiddler.cpp`
- `Code/wwsaveload/wwsaveload.cpp` when using the original public lifecycle
  (`Init` is empty; `Shutdown` frees definitions).

`parameter.cpp` is not part of the release runtime closure while
`PARAM_EDITING_ON` is undefined. `Code/wwsaveload/editable.h:276-300` reduces
all editor parameter declarations to empty macros. Keep this build mode for the
runtime; do not pull editor parameter systems into A3.0.

`Code/Combat/savegame.cpp` is the genuine facade for `Load_Definitions` and
`Load_Save_Load_System`. It should be compiled rather than reproducing those
operations in a Vita-only loader. With function/data sections and linker GC,
unused save-game, translation/UI, and thumbnail routines can be discarded;
verify the retained-symbol closure at link time.

### WWPhys static-world spine

The 93-TU original WWPhys runtime project is the correct coherent implementation
closure and has already reached a clean host compile frontier. The
definition/static-object-critical TUs inside it are:

- `phys.cpp`: `PhysClass` / `PhysDefClass`, serialized definition lookup, model
  persistence;
- `staticphys.cpp`: object `0x20109`, definition `0x20508`;
- `staticanimphys.cpp`: object `0x2010B`, definition `0x2050A`;
- `accessiblephys.cpp`: Accessible object/definition and Door/Elevator parent
  implementation (`0x20511`);
- `dynamicphys.cpp`, `decophys.cpp`, `lightphys.cpp`: the Light inheritance and
  object factory (`0x20102`);
- `pscene.cpp`, `pscene_saveload.cpp`: original scene ownership and LSD static
  data/object loading;
- `physstaticsavesystem.cpp`: global registered static-data and static-object
  SaveLoad subsystems (`0x20000`, `0x20001`);
- pathfinding, culling, visibility, animation-collision, and resource-manager
  TUs supplied by the full original WWPhys manifest.

Do not reduce the module to a custom object decoder. The definition list alone
is not a world; `PhysStaticDataSaveSystemClass` loads scene/culling/pathfinding
state and `PhysStaticObjectsSaveSystemClass` populates the PhysicsScene:
`Code/WWPhys/physstaticsavesystem.cpp:48-144` and
`Code/WWPhys/pscene_saveload.cpp:52-109,186+`.

### Combat-owned external WWPhys types in M00

These concrete original TUs are mandatory:

- `Code/Combat/doors.cpp`: object `0x20A00`, def `0x20C00`, class ID `0x9080`;
- `Code/Combat/elevator.cpp`: object `0x20A01`, def `0x20C01`, class ID `0x9081`;
- `Code/Combat/damageablestaticphys.cpp`: object `0x20A02`, def `0x20C02`,
  class ID `0x9082`;
- `Code/Combat/buildingaggregate.cpp`: object `0x20A03`, def `0x20C03`,
  class ID `0x9083`;
- `Code/Combat/buildingstate.cpp`: real BuildingAggregate state semantics;
- `Code/Combat/damage.cpp`: `DefenseObjectDefClass` and
  `DefenseObjectClass` used by Damageable definitions/objects;
- `Code/Combat/reflist.cpp`: Elevator rider and Damageable owner reference
  persistence;
- `Code/Combat/assets.cpp`: original `_TheFileFactory`-backed `Get_INI`, required
  by the armor/warhead initialization described below.

Door/Elevator definitions and objects load their current Accessible parent and
support legacy StaticAnim parent chunks. Damageable definitions load
`StaticAnimPhysDefClass` plus embedded `DefenseObjectDefClass`; objects load
`StaticAnimPhysClass`, embedded defense state, and current animation state.
BuildingAggregate definitions load StaticAnim plus ten original building-state
animation records; object post-load reapplies the persisted state.

### Required armor database initialization

`DefenseObjectDefClass::Load` maps serialized armor save IDs through
`ArmorWarheadManager::Find_Armor_Save_ID`:
`Code/Combat/damage.cpp:1213-1247`. The original order calls
`ArmorWarheadManager::Init` from `CombatManager::Init` before definitions are
later reloaded (`Code/Combat/combat.cpp:157-174,375-382`). Init obtains
`armor.ini` through original `Get_INI` and the current `_TheFileFactory`:
`damage.cpp:114-303` and `assets.cpp:45-57`.

If a temporary A3.0 startup shortcut bypasses full `CombatManager::Init`, it
must still call the original `ArmorWarheadManager::Init` before loading
`Objects.DDB`. Otherwise the save-ID table is empty and
`Find_Armor_Save_ID` silently maps every value to armor zero
(`damage.cpp:419-433`), producing a superficially successful but semantically
wrong definition load.

## Link-retention and external-boundary classification

Many original factories exist only as translation-unit static constructors.
When built into an archive, a member whose only purpose is registration may be
dropped. Preserve the original force-link intent from `wwhack.h:44-48`:

- `Force_Link_WWSaveLoad` retains Twiddler (`saveload.cpp:303-306`);
- `PhysicsSceneClass`'s module linker covers core WWPhys types
  (`pscene.cpp:2128-2152`);
- `Force_Link_Combat` covers Door, Elevator, Damageable, and BuildingAggregate
  (`Combat/objlibrary.cpp:91-128`), but also references many later Combat types.

For the incremental frontier, use direct object-library inclusion,
`--whole-archive` around a narrow registration archive, or explicit references
to the four original `_Force_Link_*` symbols. Do not call the broad Combat
force-link aggregator unless its full referenced cluster is being integrated.
After link, assert each required persist factory ID is present before reading
retail data.

The retained Door and Elevator vtables pull real runtime methods beyond their
narrow Load functions. Those methods reference original `CombatManager`
single-player/server state, `GameObjManager`, Soldier/Vehicle interactions,
PhysicsScene collection, and WWAudio. Keep the classes intact. Satisfy gameplay
dependencies with original Combat code and satisfy audio with a non-null silent
or real implementation at the original WWAudio boundary. Do not patch calls out
of Door/Elevator. Multiplayer does not need to be pulled merely because dirty
state or `I_Am_Server` is referenced.

Damageable explosion creation is reached only when damage kills the object and
can be deferred at the original Explosion boundary for first static display.
BuildingAggregate itself has no real WWAudio call despite stale includes.

## Disk-format and ABI hazards

### 1. Generic SimplePersistFactory token (known patch)

Retail simple-factory wrappers store the old-object token as exactly four
bytes (`0x00100100`). Canonical `persistfactory.h:110-135` reads
`sizeof(T *)`, which is correct on original Win32 and Vita ILP32 but consumes
zero bytes on host LP64 because the four-byte child cannot satisfy an eight-byte
read. The staged `wwsaveload-a30-abi.patch` correctly reads a `uint32` token and
converts it to a pointer-shaped remap key. Saving must likewise emit exactly
four bytes. This is a host ABI accommodation, not a disk-format change.

### 2. `PhysClass` multiple-inheritance pointer tokens (must patch next)

Canonical `PhysClass::Save` writes three old-address tokens with
`WRITE_MICRO_CHUNK`:

- `CullableClass *`;
- `WidgetUserClass *`;
- `EditableClass *`.

Evidence: `Code/WWPhys/phys.cpp:462-483`. `PhysClass::Load` reads those tokens
directly into pointer variables using `READ_MICRO_CHUNK` at lines 496-520 and
then registers the three adjusted multiple-inheritance addresses at lines
546-548 and 574+.

`READ_MICRO_CHUNK` uses `sizeof(var)` (`Code/wwlib/chunkio.h:325-340`). The
retail microchunks are four bytes. On host LP64 an eight-byte request is rejected
by `ChunkLoadClass::Read` at `chunkio.cpp:737-763`; the variables remain null,
and critical cullable/widget/editable pointer remaps are silently omitted. Vita
ILP32 happens to read them correctly.

Required semantic patch:

1. keep on-disk tokens exactly `uint32`;
2. read each into a `uint32` local;
3. convert the token to the corresponding pointer-shaped remap key with
   `reinterpret_cast<T *>(static_cast<uintptr_t>(token))`;
4. preserve all existing `Register_Pointer` calls and adjusted destination
   pointers;
5. save by explicitly narrowing the runtime address to a `uint32` token and
   writing four bytes;
6. clean-restage with fuzz zero and test both host LP64 and Vita ILP32.

Do not change the actual runtime pointer members or globally redefine pointer
widths. These values are serialized remap tokens, not live disk pointers.

### 3. Combat reference-list tokens (must patch before full object load)

`Code/Combat/reflist.cpp:44-76` and the reference templates in
`Combat/reflist.h:154-178` serialize old reference targets through generic
microchunk macros and therefore inherit the same host `sizeof(pointer)` bug.
This affects Elevator `CurrentAIRider` and Damageable `DefenseObject` owner
state. Apply the same explicit four-byte-token rule at that narrow persistence
boundary.

### 4. Additional WWPhys pointer-token audit

Before accepting host LSD/LDD loading as authoritative, audit the same pattern
in:

- `WWPhys/Path.cpp:1475-1482,1563-1568`;
- `WWPhys/PathfindPortal.cpp:98,156`;
- `WWPhys/pathsolve.cpp:1858-1862,1929-1930`;
- `WWPhys/rbody.cpp:2102,2130`;
- `WWPhys/waypoint.cpp:201-209`;
- `WWPhys/waypath.cpp:268-288`.

The pathfinding records can be reached from M00's static-data subsystem, so
this is not merely a future save-game concern. Patch only fields that
semantically store Win32 old-address remap tokens; never widen serialized IDs,
file offsets, or actual format structures to `uintptr_t`.

### 5. Other fixed-layout checks

- Definition IDs, factory IDs, chunk headers, and armor save IDs remain
  explicit 32-bit integers.
- Door/Elevator persist `OBBoxClass`; assert its expected Matrix3 + two Vector3
  60-byte layout on host and Vita before accepting retail reads.
- `WCHAR` is correctly fixed to 16 bits in the compatibility layer; Linux
  `wchar_t` width must never leak into `.ldd`/save formats.
- Existing MIX `long`/`unsigned long` fixes must remain fixed-width; A2.1's
  biased-file semantics are already physical-hardware validated.
- Networking-only `DefenseObjectClass::Export` uses `unsigned long`; audit that
  separately when networking returns, but it is not on the static LSD load
  path.

## Concrete next compile/link steps

1. Add the eight missing release WWSaveLoad definition TUs to the existing A2.2
   three-TU SaveLoad set; optionally add `wwsaveload.cpp` for lifecycle.
2. Compile original `Combat/savegame.cpp` and retain only the genuine loader
   sections through normal section GC.
3. Add original `assets.cpp`, `damage.cpp`, `reflist.cpp`, `buildingstate.cpp`,
   `doors.cpp`, `elevator.cpp`, `damageablestaticphys.cpp`, and
   `buildingaggregate.cpp` atop the now-green complete WWPhys frontier.
4. Implement exact four-byte host token patches for `PhysClass`, Combat
   references, and any M00-reached pathfinding token sites; regenerate against
   pinned upstream and require `--fuzz=0`.
5. Guarantee factory TU retention and assert required registration IDs before
   file loading.
6. Initialize the current original file-factory list, initialize original
   `ArmorWarheadManager`, then call original
   `SaveGameManager::Load_Definitions("Objects.DDB")`.
7. Attempt original `SaveGameManager::Pre_Load_Game("M00_Tutorial.mix", ...)`
   and `Load_Game`, preserving the optional missing level-DDB no-op.
8. Let the registered original WWPhys static SaveLoad subsystems populate the
   genuine `PhysicsSceneClass`; do not manually instantiate the 687 objects.
9. Resolve actual retained Door/Elevator gameplay/audio link edges at their
   original subsystem boundaries and proceed into world traversal.

## Required semantic validation fields

Log and assert at minimum:

```text
file_factory.objects_ddb.available = true
file_factory.objects_ddb.size = 5157396
definition_mgr.subsystem_registered = 0x00000101
definition_mgr.twiddler_factory_registered = 0x00000102
definition_mgr.twiddlers_loaded = 260

definitions.static = 44
definitions.static_anim = 101
definitions.accessible = 25
definitions.door = 102
definitions.elevator = 64
definitions.damageable = 331
definitions.building_aggregate = 249
definitions.required_type_total = 916

armor_ini.initialized = true
armor_save_id_count = <original derived host value>
warhead_save_id_count = <original derived host value>

m00.optional_ddb.available = false
m00.optional_ddb.open = false
m00.definition_count_before_optional_ddb = N
m00.definition_count_after_optional_ddb = N

m00.light_objects = 192
m00.static_objects = 424
m00.static_anim_objects = 5
m00.door_objects = 10
m00.elevator_objects = 4
m00.damageable_objects = 5
m00.building_aggregate_objects = 47
m00.relevant_object_total = 687
m00.definition_backed_objects = 93
m00.valid_definitionless_objects = 594
m00.definition_ids_resolved = 93
m00.definition_ids_unresolved = 0

saveload.pointer_remap_requests = <derived original count>
saveload.pointer_remap_failures = 0
physics_scene.static_subsystem_loaded = true
physics_scene.static_objects_subsystem_loaded = true
```

Also preserve every A2.0/A2.1/A2.2 regression fingerprint. Derive new pointer,
scene, culling, object, mesh, and memory counts from the first successful
original host load; do not invent expected values and do not accept a host PASS
until the LP64 remap-token accommodations above are active.

## Approaches not to take

- Do not create `m00_tutorial.ddb`.
- Do not pre-extract or convert `Objects.DDB`, `.lsd`, or `.ldd`.
- Do not replace DefinitionMgr with a table generated by a probe.
- Do not manually instantiate static objects from the fingerprint above.
- Do not globally widen serialized fields to `uintptr_t`.
- Do not treat missing unregistered definition types as proof of success; assert
  the exact required factories and all 93 M00 references.
- Do not patch Door/Elevator gameplay methods out merely to satisfy their
  vtables; integrate original engine dependencies and use legitimate platform
  or middleware boundaries.

