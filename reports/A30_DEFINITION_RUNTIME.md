# A3.0 Original Definition Runtime

Date: 2026-08-07  
Canonical upstream revision:
`3e00c3a1b97381bb28be89a35b856375e0629a08`

## Objective and architecture

This host runtime proves the real definition-database path needed by the M00
world loader. It does not parse DDB records itself and does not construct a
replacement definition table:

```text
RenegadeRootedFileFactoryClass
  -> original FileFactoryListClass
  -> original MixFileFactoryClass for Data/always.dbs
  -> original biased FileClass for Objects.DDB
  -> original ChunkLoadClass
  -> original SaveLoadSystemClass
  -> original DefinitionMgrClass
  -> original PersistFactoryClass registrations
  -> original concrete DefinitionClass instances
```

The source is under `tools/host_a30_definitions/`. The narrow executable first
proved the same path with the original Twiddler factory: `Objects.DDB` was
opened at 5,157,396 bytes, 260 Twiddlers were instantiated, the absent optional
`m00_tutorial.ddb` remained a successful no-data operation, and 13/13 checks
passed. Evidence: `../../logs/a30-20260807-definition-runtime-minimal.log`.

## Full original WWPhys closure

The full target `a30_wwphys_definition_runtime` links the explicit 209-TU A3
manifest, the remaining 14 original WWMath runtime TUs, and the original
WW3D/wwlib closure exposed by the complete WWPhys module:

- `wwlib`: GCD/LCM and LZO implementation;
- `ww3d2`: DynamicMesh, Light/LightEnvironment, particle emitter/buffer/loader,
  PointGroup, LineGroup, SegLineRenderer, and ShatterSystem.

The compiler/linker frontier identified five more original implementation
TUs rather than substitutes: `gcd_lcm.cpp`, `dynamesh.cpp`, `linegrp.cpp`,
`pointgr.cpp`, and `seglinerenderer.cpp`. The final executable contains 237
original translation units and six target/port translation units. All 243
source objects compile and link. Original `dx8fvf.cpp`,
`dx8vertexbuffer.cpp`, and `dx8indexbuffer.cpp` provide the real engine buffer
implementations; the production Vita boundary provides their platform bind and
draw edge.

## Definition-only graphics boundary

`tools/host_a30_definitions/wwphys_definition_dx8_boundary.cpp` is linked only
into this host definition target. Original `dx8fvf.cpp`,
`dx8vertexbuffer.cpp`, and `dx8indexbuffer.cpp` now remain the sole engine
implementations of the generic buffer classes, while the production Vita
boundary owns the buffer bind/draw and DX8 diagnostic functions. The host-only
definition boundary covers only the still-unavailable render-target,
render-resolution, light-environment, and sorting-submission calls; each logs
its exact operation and aborts. The runtime must finish with
`definition_runtime.unsupported_gpu_calls=0`; therefore it cannot pass by
silently simulating graphics. This file is not linked into the Vita runtime
and does not replace the production renderer.

The non-MSVC branch of the original `dx8wrapper.h` defines `Convert_Color` but
omits the declared `Convert_Color_Clamp`. The target-scoped boundary supplies
the same scalar clamp-and-pack operation because it is a deterministic CPU
utility, not a graphics submission.

## Compatibility work

`port/patches/ww3d2-a30-gcc15.patch` is an exact patch against the pinned
source. It contains only the modern-GCC corrections exposed by this closure:

- two missing explicit `float` declarations in `lightenvironment.cpp`;
- six VC6 post-loop index lifetime fixes in `part_buf.cpp`;
- one `LPCTSTR` spelling changed to `const char *` in `part_ldr.cpp`;
- three old integer-null arguments changed to `nullptr` in `pointgr.cpp`;
- two VC6 post-loop `found` lifetime fixes in `dynamesh.cpp`.

Patch SHA-256:
`f42d55fcbcce74cbbd09dd7442f6dfe16e3334d626b374ea39e2c124ab04bb8c`.
It replayed with `--fuzz=0`; clean staging contained no `.orig` or `.rej`, and
canonical upstream remained pristine.

## Validated runtime fingerprint

The unchanged retail `Objects.DDB` was loaded through the original biased
`FileClass`, `ChunkLoadClass`, `SaveLoadSystemClass`, registered persist
factories, and `DefinitionMgrClass`. The final run passed 34/34 checks and did
not enter the fail-fast graphics boundary:

- file size: 5,157,396 bytes;
- definitions: 1,411 total = 260 Twiddlers + 1,151 core WWPhys;
- core factories: 17/17 registered;
- class counts: decoration 405, human 219, motorcycle 8, motor vehicle 0,
  Phys3 97, projectile 5, rigid body 0, static 44, wheeled vehicle 23,
  static animation 101, timed decoration 102, vehicle 0, tracked vehicle 47,
  VTOL vehicle 26, dynamic animation 49, shakeable static 0, accessible 25;
- absent `m00_tutorial.ddb`: original successful no-op, definition table
  unchanged;
- unsupported graphics calls: 0;
- original definition ownership teardown: clean.

Complete evidence:

- build: `../../logs/a30-20260807-definition-wwphys-final-build.log`;
- asserted runtime: `../../logs/a30-20260807-definition-wwphys-runtime-final.log`;
- immutable working evidence: `build/a30-definition-runtime-34of34/`.

SHA-256:

- executable: `916de72c56bfdbc2fa0eae70358e44614e6d5e2b5be0f9e759396e23b414ad22`;
- build log: `d319416db5053ce52829b2d0df3635c9817b10509b9f6fc4504b4bfcdb83de02`;
- runtime log: `6b77a47f41cabd11eba221ab77805e6852585dfa99be9009f251061f7f8dfe52`.

## Continuation into the original M00 world

The accepted definition executable is preserved. Its cached successor links
the separate nine-TU original Combat world-factory slice and calls
`Run_A30_World_Runtime` from `port/validation/a30_world_runtime.cpp`. That
validation layer does not parse retail formats: it initializes the original
file/MIX, WWMath, WW3DAssetManager, WW3D, WWPhys, WWSaveLoad,
PhysicsSceneClass and ArmorWarheadManager owners, loads `Objects.DDB` and
`M00_Tutorial.lsd` through original SaveLoad, performs original post-load
processing, and fingerprints the live PhysicsScene/RenderObj graph. The next
coherent runtime now links and passes its exact 35/35 semantic fingerprint;
full evidence is in `reports/A30_M00_WORLD_RUNTIME.md`. Active continuation is
the callback over that still-live world using original CameraClass,
PhysicsScene pre/post processing and WW3D frame traversal.
