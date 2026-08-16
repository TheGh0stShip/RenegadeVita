# A3.0 Serialized Pointer / Remap Token ABI Audit

Date: 2026-08-07  
Canonical upstream: `electronicarts/CnC_Renegade` revision
`3e00c3a1b97381bb28be89a35b856375e0629a08`  
Scope: original WWSaveLoad, the complete 93-TU WWPhys runtime frontier, and
the current M00 static-world Combat closure. Canonical upstream and retail
data were inspected read-only.

## Conclusion

Renegade's save/load pointer fields are not persisted machine pointers. They
are opaque **32-bit old-address identity tokens** used only as keys by
`SaveLoadSystemClass` while reconstructing the object graph. That format is
correct on the original Win32 build and on Vita ILP32, but generic
`sizeof(pointer)` reads/writes are wrong in the Linux x86-64 host harness.

The host compiler reports an 8-byte pointer and 8-byte `long`; VitaSDK reports
a 4-byte pointer and 4-byte `long`. The port's shadow `bittype.h` correctly
defines `uint32` as `uint32_t`, so explicit `uint32` token locals are exactly
four bytes on both targets.

`READ_MICRO_CHUNK` and `WRITE_MICRO_CHUNK` use `sizeof(var)` verbatim
(`Code/wwlib/chunkio.h:297-300,338-339`). A host read of an eight-byte pointer
from a four-byte retail microchunk fails without consuming data because
`ChunkLoadClass::Read` rejects reads past the microchunk boundary
(`chunkio.cpp:737-763`). This can silently omit remaps; in two paths it also
passes an uninitialized pointer to `Register_Pointer`.

Every disk-facing token below must therefore use this narrow boundary rule:

```cpp
uint32 token = static_cast<uint32>(reinterpret_cast<uintptr_t>(runtime_ptr));
// write exactly sizeof(token)

uint32 token = 0;
// read exactly sizeof(token)
T *old_ptr = reinterpret_cast<T *>(static_cast<uintptr_t>(token));
```

The actual object members, `PointerRemapClass` tables, pointers-to-remap, and
new host pointers must remain native pointer width. Do not globally change
pointer fields to `uint32`, and do not widen serialized tokens to `uintptr_t`.

## Current patch status

Two critical boundaries are already covered by active exact patches:

- `port/patches/wwsaveload-a30-abi.patch` fixes the generic
  `SimplePersistFactoryClass` wrapper token.
- `port/patches/wwphys-a30-gcc15.patch` now fixes all three `PhysClass`
  multiple-inheritance identity tokens.

The other sites in this report remained canonical/unpatched at audit time.
They have since been encoded in two standalone patches and activated in the
deterministic staging order:

- `port/patches/wwphys-a30-pointer-tokens.patch`
  (`e7ff7b79d1240e2cb2b615625084d74fbeef83fcd1ff551e76ebc45062ccf990`)
  covers Path, PathfindPortal/action-portal, MoveablePhys, PathSolve,
  PhysicsScene static-object state, RigidBody, Waypath, and Waypoint.
- `port/patches/combat-a30-pointer-tokens.patch`
  (`18bacb9f28392e239b052871fed686eeb349cbdf35d98c7a7a6c74d237530d90`)
  covers ReferencerClass and ReferenceableClass.

Both patches were generated against the pinned canonical files (with the
existing `wwphys-a30-gcc15.patch` applied first for WWPhys), then reproduced
in a second temporary tree using `patch --batch --forward --fuzz=0
--no-backup-if-mismatch`. Every hunk applied exactly, the reproduced trees
were byte-identical to their edited source trees, and no `.orig` or `.rej`
was created. `tools/stage_sources.sh` now applies both patches with the same
strict zero-fuzz options after the existing A3.0 patches.

## Immediate M00 static-world paths

### Generic `SimplePersistFactoryClass` — already patched

Canonical source: `Code/wwsaveload/persistfactory.h:109-140`.

- Load at line 117 requests `sizeof(T *)` from the four-byte
  `SIMPLEFACTORY_CHUNKID_OBJPOINTER` child.
- Save already emits a `uint32`, but canonical line 133 uses a pointer-to-small
  integer cast rejected by modern GCC.
- Semantic role: register each persisted object's old identity with its newly
  allocated object. This is reached by definitions, W3D persist objects,
  WWPhys objects, waypaths, and waypoints.

The active patch reads a `uint32 old_obj_token`, widens it only into the
pointer-shaped lookup key, and uses `uintptr_t` for the explicit save cast.
This is the correct pattern.

### `PhysClass` adjusted-base identities — already patched

Canonical source: `Code/wwphys/phys.cpp:462-472,496-517,546-591`.

The three fields identify adjusted multiple-inheritance addresses:

- `CullableClass *`;
- `WidgetUserClass *`;
- `EditableClass *`.

They are format tokens, not object members. All three saves and loads must be
four bytes, followed by the original registrations against the corresponding
adjusted base of the new object. The active patch does exactly that and keeps
the original registrations intact. This path is reached by the 687 M00 static
physics objects.

### `PathfindPortalClass` and action-portal links — patch required

Canonical source: `Code/wwphys/PathfindPortal.cpp`.

- Base portal self token: save lines 97-98; load lines 142-170.
- Action portal exit token: save line 199; load line 259 and remap lines
  281-282.
- Action portal enter token: save line 200; load line 260 and remap lines
  277-278.

The base old pointer and both action-portal references are 32-bit remap tokens.
Use one `uint32` local for the base self token, and separate initialized
`uint32` locals for enter/exit tokens. After reading, convert those two tokens
back into pointer-shaped values in `m_EnterPortal` and `m_ExitPortal` before
preserving the existing non-ref-counted remap requests.

Do **not** patch `m_DestSector1` or `m_DestSector2`: despite their names they
are explicit `uint16` sector indices (`pathfindportal.h:138-139`), not
pointers. Do not patch `m_EntranceSector`; it is not serialized here and is
derived by normal pathfinding resolution.

This file is on `PhysStaticDataSaveSystemClass -> PathfindClass::Load`, so its
serialized branches are part of the M00 static-data frontier.

### `WaypointClass` — patch required

Canonical source: `Code/wwphys/waypoint.cpp:143-152,188-210`.

`VARID_OLD_PTR` is the waypoint self-identity token. Save it through a
four-byte local. Load a four-byte local, convert it to a pointer-shaped key,
then preserve `Register_Pointer(old_ptr, this)`. The canonical host load asks
for `sizeof(old_ptr)` at line 208 and is therefore currently eight bytes.

### `WaypathClass` — patch required

Canonical source: `Code/wwphys/waypath.cpp:203-220,257-301`.

Two token categories exist:

- one `VARID_OLD_PTR` self token (save line 209; load lines 280-288);
- one repeated `VARID_WAYPOINT_PTR` token per waypoint (save lines 217-219;
  load lines 268-276), followed by the original remap requests at lines
  296-300.

Every repeated waypoint token must be read as four bytes, widened to a
pointer-shaped `WaypointClass *`, and added in original order. The dynamic
vector itself remains a native vector of native pointers.

This pair is not a harmless missed diagnostic on LP64. Canonical
`WaypointClass::Load` initializes each failed old-pointer read to null and
registers that null key, while `WaypathClass::Load` appends one null value for
each failed waypoint-token read and later requests all of them be remapped.
The remapper therefore sees duplicate zero-valued registrations/requests and
can attach waypaths to the wrong waypoint rather than simply reporting a
clean failure.

Waypaths and waypoints are loaded by the genuine Pathfind static-data path.

### `PhysicsSceneClass` static-object-state identity — patch required and
high priority

Canonical source: `Code/wwphys/pscene_saveload.cpp:646-685`.

`PSCENE_DD_CHUNK_STATIC_OLD_PTR` associates a dynamic-state record with an
already loaded static object selected by stable object ID. Canonical save lines
657-660 write `sizeof(void *)`; canonical load lines 681-685 read
`sizeof(void *)` and register it.

Use an explicit four-byte token in this whole child chunk on both save and
load. This is especially important on LP64 because canonical `old_ptr` at line
683 is uninitialized; a rejected eight-byte read is followed immediately by a
registration of indeterminate data. This path is reached when the M00 LDD
restores state for doors, elevators, damageable objects, and other static
objects with dynamic state.

### Combat reference graph — patch required before authoritative object-state
loading

Canonical sources:

- `Code/Combat/reflist.cpp:44-76` (`ReferencerClass` target token);
- `Code/Combat/reflist.h:154-178` (`ReferenceableClass<T>` self token).

Both are genuine four-byte graph identities:

- `ReferencerClass::Save` must serialize `ReferenceTarget` through a `uint32`;
  Load must read a `uint32`, widen it into `ReferenceTarget`, and preserve the
  existing pointer-remap request and post-load callback.
- `ReferenceableClass<T>::Save` must serialize `this` through a `uint32`;
  Load must initialize/read a `uint32`, widen it into `old_ptr`, and preserve
  the existing registration.

The template load is a high-risk host bug: canonical `old_ptr` is
uninitialized, the eight-byte read fails, and line 177 registers the
indeterminate value unconditionally. `ElevatorPhysClass` uses the referencer
path for its conditional current-AI-rider state. The same classes become
pervasive as the original dynamic Combat object graph is enabled.

## Additional original WWPhys runtime token sites

These are genuine format issues in the integrated 93-TU WWPhys module. They
are not required to construct M00's initial static object set in every run,
but must be fixed before host save-game/gameplay validation can be considered
authoritative.

### `PathClass`

Canonical source: `Code/wwphys/Path.cpp:1481-1482,1541-1589`.

`VARID_OLD_PTR` is a 32-bit self token. Replace the pointer-sized macro
save/load with the established `uint32` conversion pattern and retain the
registration. `m_PathObject` at lines 1475/1563 is a value object containing
no pointers; `PATH_NODE` at lines 1487-1489/1570-1577 contains only scalar,
enum, bool, and `Vector3` fields. Neither should be changed by this audit.

### `PathSolveClass`

Canonical source: `Code/wwphys/pathsolve.cpp:1847-1862,1915-1941`.

- `VARID_OLD_PTR` is the ordinary 32-bit self token and must be fixed on save
  and load.
- `VARID_START_SECTOR` and `VARID_DEST_SECTOR` at lines 1856-1857 are raw
  pointer tokens written by the original format. The loader deliberately has
  no cases for these IDs and resets both members to null at lines 1918-1919;
  `On_Post_Load` recomputes pathfinding. Preserve that behavior, but make the
  save-side microchunks four bytes so a host-generated save remains format
  compatible. Do not add new load/remap behavior not present upstream.
- `VARID_PATH_OBJECT` is a pointer-free value object and must remain unchanged.

### `MoveablePhysClass`

Canonical source: `Code/wwphys/movephys.cpp:408-485`.

`Controller` and `Carrier` are nullable persisted references written at lines
418-422, read at lines 465-466, and remapped at lines 480-485. Use separate
four-byte tokens, widen into the native members after loading, then preserve
the original requests. These are dynamic/gameplay references, not part of the
687 static-object core.

### `RigidBodyClass`

Canonical source: `Code/wwphys/rbody.cpp:2094-2154`.

`RBODY_VARIABLE_ODESYSTEM_PTR` stores the adjusted `ODESystemClass *` identity
for the same multiple-inheritance reason as `PhysClass`. Save/load it through
a `uint32` token and preserve registration against `(ODESystemClass *)this`.
M00 has no rigid-body definitions or rigid-body objects in the already derived
static-object fingerprint, so this is a later dynamic/runtime branch.

## Deliberate non-fixes

- `Code/wwphys/PathfindSector.cpp:145-201` declares `old_ptr`, but no old-pointer
  field is serialized or read in that class. It stays null, so the final
  registration branch is dead. Do not invent a disk field.
- `PathfindPortalClass::m_DestSector1/2` are `uint16` indices.
- `PathClass::m_PathObject`, `PathSolveClass::m_PathObject`, and
  `PathClass::PATH_NODE` are pointer-free value records.
- AAB-tree object linkage stores a `uint32` node index
  (`Code/WWMath/aabtreecull.cpp:856-880`), not a pointer.
- Definition IDs, persist factory IDs, chunk IDs, path mechanism IDs, object
  IDs, visibility IDs, and archive offsets are numeric file-format values and
  must not be converted to `uintptr_t`.
- `DynTexProjectClass::LightSourceID` is a runtime address identity/cache key,
  not serialized data. Its active `uintptr_t` host fix is correct and unrelated
  to these four-byte disk tokens.

## Audit coverage

The audit enumerated all of the following in WWSaveLoad, the complete WWPhys
runtime source set, and the current M00 Combat closure:

- `SaveLoadSystemClass::Register_Pointer` calls;
- `REQUEST_POINTER_REMAP` and `REQUEST_REF_COUNTED_POINTER_REMAP` calls;
- pointer-valued `WRITE_MICRO_CHUNK` / `READ_MICRO_CHUNK` calls;
- direct `ChunkSaveClass::Write` / `ChunkLoadClass::Read` calls using pointer
  sizes;
- raw value structures adjacent to the flagged pathfinding fields.

No other disk-facing pointer token was found in current WWSaveLoad/WWPhys or
the current static-world Combat source closure. Broader Combat dynamic object
types have additional remap sites and must receive the same source-directed
audit as those translation units enter the A3.0 link closure; this report does
not claim that the not-yet-integrated complete dynamic Combat graph is clean.

## Independent patch validation

The prepared patches were applied to an isolated copy of the stable staged
source closure after the 93-TU WWPhys and 11-TU WWSaveLoad frontier owner
reported quiescence. The eight changed WWPhys translation units compiled
successfully with the exact active frontier flags under both host GCC (LP64)
and `arm-vita-eabi-g++` (ILP32):

- `Path.cpp`;
- `PathfindPortal.cpp`;
- `movephys.cpp`;
- `pathsolve.cpp`;
- `pscene_saveload.cpp`;
- `rbody.cpp`;
- `waypath.cpp`;
- `waypoint.cpp`.

`reflist.cpp` and the patched template in `reflist.h` also compile under both
toolchains. That isolated compile predefines the `SCRIPTABLEGAMEOBJ_H` guard:
the token classes themselves require only the forward declaration, while the
canonical `scriptablegameobj.h -> basegameobj.h -> networkobject.h ->
winsock.h` chain crosses the separate, not-yet-integrated WWNet platform
boundary. This is a scoped syntax/ABI validation of the Combat patch, not a
claim that the full dynamic Combat/WWNet closure is compiled.

The patches were subsequently activated and clean-restaged. The complete
aggregate frontier passed for both targets: 93/93 original WWPhys and 11/11
original WWSaveLoad translation units on host, and the same 93/93 + 11/11 on
Vita ARM. The active staged files are byte-identical to the independent patch
replay; canonical upstream remains pristine; no `.orig`/`.rej` exists.

Preserved validation logs:

- `../../logs/a30-20260807-pointer-tokens-clean-stage.log`;
- `../../logs/a30-20260807-pointer-tokens-host-build.log`;
- `../../logs/a30-20260807-pointer-tokens-vita-build.log`;
- `../../logs/a30-20260807-pointer-tokens-validation.log`.

## Remaining semantic runtime validation

Clean staging and compile validation are complete. The next runtime owner must:

1. Load original M00 pathfinding and static-object-state data on host.
2. Record pointer-pair registrations, remap requests, successful remaps, and
   failures; require zero remap failures.
3. Assert loaded waypath/waypoint/portal counts and link integrity from the
   original runtime rather than inventing expected values.
4. Preserve every A2.0/A2.1/A2.2 regression.

Do not accept an LP64 host world-load result as semantic evidence until the
immediate M00 token paths above are fixed. Vita ILP32 happens to match the
retail token width, but the host is the fast diagnostic environment and must
not silently validate a different format contract.
