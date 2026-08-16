# A3.0 Original M00 World Runtime

Date: 2026-08-07  
Canonical upstream revision:
`3e00c3a1b97381bb28be89a35b856375e0629a08`

## Result

The coherent original M00 static-world host runtime now passes 45/45
assertions against the unchanged retail installation. The first 35/35 proof
established original database/world loading; the succeeding proof retains that
live PhysicsScene and traverses one complete original Camera/WW3D frame. It is
not a level parser, replacement scene builder, or manual geometry renderer.
The tested ownership/call chain is:

```text
RenegadeRootedFileFactoryClass
  -> original FileFactoryListClass / MixFileFactoryClass
  -> original WWMath / WW3DAssetManager / WW3D / WWPhys / WWSaveLoad
  -> original PhysicsSceneClass
  -> original ArmorWarheadManager
  -> original SaveLoadSystemClass loads Objects.DDB
  -> original SaveLoadSystemClass loads M00_Tutorial.lsd
  -> original SaveLoadSystemClass::Post_Load_Processing
  -> original PhysicsScene iterators and RenderObj graph
  -> original CameraClass derived from loaded world extents
  -> original PhysicsSceneClass::Pre_Render_Processing
  -> original WW3D::Begin_Render / Render(scene,camera) / End_Render
  -> original PhysicsSceneClass::Post_Render_Processing
  -> original subsystem-order teardown
```

The target contains 248 original EA/Westwood translation units and ten
port/validation/host-boundary translation units. Retail files were read in
place; none were copied, converted, repacked, or modified.

## Exact semantic fingerprint

- checks: 35 passed, 0 failed;
- required SaveLoad subsystems: 3/3;
- required persist factories: 33/33;
- definitions: 2,157 total, 260 Twiddlers;
- definition checksum: `90DB91BE`;
- M00-required definitions: 916;
- armor types: 31; warhead types: 29;
- static objects: 495; static lights: 192; dynamic objects: 0;
- concrete objects: 424 StaticPhys, 5 StaticAnimPhys, 10 DoorPhys,
  4 ElevatorPhys, 5 DamageableStaticPhys, 47 BuildingAggregate;
- definition-backed objects: 93; valid definitionless objects: 594;
- render models: 687, all non-null;
- RenderObj nodes: 1,615;
- meshes: 1,288;
- mesh vertices: 38,158;
- mesh polygons: 21,537;
- loaded prototypes: 1,177;
- visibility objects: 1,684; visibility sectors: 347;
- pathfind data: loaded;
- object identity checksum: `4A930F8A`;
- RenderObj graph checksum: `BFA9C255`;
- prototype checksum: `E835A45F`;
- level minimum: `(-109.983284,-109.420731,-18.072906)`;
- level maximum: `(121.511314,118.983627,39.252510)`;
- optional absent `m00_tutorial.ddb`: original successful no-op;
- host optional/render boundary calls: 0;
- original ownership teardown: clean.

The first successful load run established these values. Only afterward were
they added as semantic assertions in `port/validation/a30_world_runtime.cpp`;
the asserted load rerun passed 35/35.

## Original live-world render fingerprint

The loaded-world continuation uses the borrowed original `PhysicsSceneClass`
and `WW3DAssetManager` while their normal ownership remains live. A temporary
development `CameraClass` derives its transform and clip range only from the
loaded original level extents. No objects are inserted, no mesh data is
extracted, and no parallel scene or render loop is constructed.

The first successful unasserted traversal produced:

- complete Pre_Render / Begin_Render / Render / End_Render / Post_Render;
- camera position: `(5.764015,-161.894669,84.668076)`;
- camera target: `(5.764015,4.781448,10.589802)`;
- clip planes: `(0.500000,925.978394)`;
- frames: 1;
- original `MeshClass` submissions: 652;
- submitted vertices: 30,603;
- submitted triangles: 16,939;
- geometry checksum: `34FFAD42`;
- indexed submissions/references/triangles: 0/0/0;
- rejected indexed submissions: 0;
- unsupported submissions: 0;
- unsupported host GPU calls: 0;
- default-render-target restores: 1.

Only after that observation were the exact frame, submission, checksum, and
boundary counts made assertions. Two subsequent unchanged-retail executions
passed 45/45 and produced byte-identical logs.

The one default-target restore is an original
`PhysicsSceneClass::Apply_Projectors` operation: it unconditionally calls
`DX8Wrapper::Set_Render_Target(NULL)` after the projector pass, including when
the projector lists are empty. The host boundary permits and counts only this
NULL/default restore. Any non-NULL render target and
`DX8Wrapper::Create_Render_Target` remain fail-fast. Their zero-call result is
therefore distinct from and does not inflate the unsupported-operation count.

## Link frontier and boundaries

The nine original Combat world-factory TUs register/restore the exact M00
object classes. Original `commando/datasafe.cpp` and `combat/crandom.cpp` plus
the shared optional-services boundary complete the authentic definition
decryption/random path.

The final linker frontier exposed 13 symbols retained by complete virtual
tables but not used by static SaveLoad: Door/Elevator gameplay checks and
audio effects, PhysicsScene customized rendering state, and empty pre-Combat
process globals. `tools/host_a30_definitions/world_load_optional_boundary.cpp`
defines neutral original startup state for the three globals and aborts with
the exact operation for every callable method. The passing runtime proves none
of those methods was entered. This host-only seam is not linked into the Vita
application and does not replace Combat, WWAudio, or the production renderer.

The target-local lowercase `audiosaveload.h` shim uses an explicit canonical
staged path. On the DrvFS workspace, an include differing only by case resolves
back to the shim itself; the explicit path prevents pragma-once self-inclusion.
The target-local `winsock.h` delegates to the centralized compatibility
definition for declaration-only WWNet types.

## Evidence

Preserved directory: `build/a30-m00-world-runtime-35of35/`

- executable SHA-256:
  `31f72c762ae7d005a22d161c5820eb224d16fe04f5c2b90095938d6d69ad7da5`;
- fingerprint build-log SHA-256:
  `448844a0e57eb4abc7b6cffafcfd6d45058287b5fb7365a194b7fc9cabcc50b5`;
- finite-link build-log SHA-256:
  `2284c256352d192e79770c4c8b02d2b265260fae48e6acb258a6cbe73a199196`;
- fingerprint runtime-log SHA-256:
  `ea741a92a7fa7e8c1368c8217f662012308cd67eb597103024563bbc86290275`.

`SHA256SUMS.txt` verifies all four preserved files.

Live-render evidence is independently preserved in
`build/a30-m00-world-render-45of45/`:

- exact 45/45 executable SHA-256:
  `10bf3ad0c025a29214a2e84d021dccf44e32d12fcd5465b29aa60e79f279e7c1`;
- pre-assertion first-success runtime-log SHA-256:
  `45629284f195d83aa941bca157497f3db63a8d2e49079bdb3981fb0952122b9e`;
- final fingerprint build-log SHA-256:
  `cb8c91297c6e7c89d2acc54e05ed150df44c655ba9c52d0bc239f141bfa9b23b`;
- two byte-identical asserted runtime logs, each SHA-256:
  `0780f12c69a7f956b303a3350934cfad5bb4b72e7c1bc10a65308761dfc566cb`;
- a SHA-256 manifest covering every preserved file.

## Continuation

The existing `A30WorldLoadedCallback` now proves the original frame sequence:

```text
PhysicsSceneClass::Pre_Render_Processing
  -> WW3D::Begin_Render
  -> WW3D::Render(PhysicsSceneClass, CameraClass)
  -> WW3D::End_Render
  -> PhysicsSceneClass::Post_Render_Processing
```

The next production step is to carry this exact world-load/traversal chain into
the Vita A3 runtime, then extend it into the original continuous Combat/game
update and input path. The current zero indexed-terrain count is an observed
property of this M00 static-world traversal, not a reason to manufacture
terrain submissions or bypass the original scene.
