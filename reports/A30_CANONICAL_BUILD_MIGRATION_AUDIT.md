# A3.0 Canonical Build Migration Audit

Date: 2026-08-07  
Canonical upstream revision:
`3e00c3a1b97381bb28be89a35b856375e0629a08`

## Scope and snapshot

This is a read-only migration audit of the canonical root `CMakeLists.txt`,
`tools/build.sh`, and `tools/generate_integration_report.py` against the
isolated `tools/vita_a30/CMakeLists.txt` target. The isolated target is an
active work in progress; its first 248-original-TU ARM build was still
compiling when this audit began. Its current source count and link contract
must therefore be rechecked after that target reaches a clean link/SELF/VPK.

No staging tree, canonical source, build target, or release artifact was
changed by this audit.

## Current canonical mismatch

The root workflow is still an A2.2 release workflow:

- root project/version: `RenegadeVitaA2` / `2.2.0`;
- original manifest: `cmake/A22OriginalSources.cmake`, 105 TUs;
- entry point: `port/platform/vita/main.cpp`;
- output: `RenegadeVita-A2.2.*`, title ID `RNEGA2001`, app version `02.02`;
- runtime log: `ux0:data/renegade/user/logs/a22-runtime.log`;
- host gate: only `tools/run_a22_host.sh`;
- report generator: A2.2-only, 105 original TUs, nine port TUs, six patches,
  51 unique patched upstream files;
- linked-symbol, linker-map, build-report, dist-copy, and checksum assertions:
  all A2.2-specific.

The staging script now applies 22 exact zero-fuzz patches touching 109 unique
canonical upstream files. Consequently the current A2.2 report generator's
exact-patch-set assertion is stale and `bash ./tools/build.sh` will reject the
current project state even before configuring an ARM target. This is not an A3
compiler failure; it is a release-metadata mismatch.

The isolated A3 target currently specifies:

- project/version: `RenegadeVitaA30` / `3.0.0`;
- VPK: `RenegadeVita-A3.0.vpk`;
- title ID: `RNEGA3001`;
- app version: `03.00`;
- name: `Renegade Vita A3.0`;
- map: `RenegadeVita-A3.0.map`;
- runtime log: `ux0:data/renegade/user/logs/a30-runtime.log`;
- 248 direct-linked original EA/Westwood TUs;
- 13 project-owned platform/renderer/validation TUs plus VitaSDK's
  `debugScreen.c`;
- the same currently audited Vita graphics/system libraries as A2.2.

## Exact current A3 source closure

At this snapshot the 248 original TUs are:

| Original module | TUs |
| --- | ---: |
| `wwbitpack` | 4 |
| `wwutil` | 1 |
| `wwlib` | 27 |
| `WWMath` | 35 |
| `wwsaveload` | 11 |
| `ww3d2` | 65 |
| `WWPhys` | 93 |
| `Combat` | 11 |
| `Commando` | 1 |
| **Total** | **248** |

The effective closure is currently split across
`cmake/A30OriginalSources.cmake` (220 TUs) and two lists local to both the host
and isolated Vita targets (14 extra WWMath TUs and 14 extra wwlib/ww3d2 link
dependencies). Before canonicalization, move the final
`RENEGADE_A30_WORLD_ORIGINAL_SOURCES` list and its exact `248` assertion into a
shared CMake manifest. Root Vita, host world validation, and source-report
generation must consume that single list. Do not retain three independently
maintained copies.

The current 13 project-owned Vita TUs are:

1. `port/filesystem/renegade_paths.cpp`
2. `port/filesystem/renegade_file_factory.cpp`
3. `port/platform/renegade_optional_services.cpp`
4. `port/renderer/vita/ww3d_vita_renderer.cpp`
5. `port/renderer/vita/ww3d_dx8_boundary.cpp`
6. `port/validation/wwbitpack_selftest.cpp`
7. `port/validation/a21_filesystem_selftest.cpp`
8. `port/validation/a22_w3d_selftest.cpp`
9. `port/validation/a30_world_runtime.cpp`
10. `port/platform/vita/vita_platform.cpp`
11. `port/platform/vita/a30_vita_runtime.cpp`
12. `port/platform/vita/a30_static_world_boundary.cpp`
13. `port/platform/vita/a30_main.cpp`

`debugScreen.c` is one SDK helper and must be reported separately, as it was
for A2.2.

### Static registration linkage requirement

The 248 original TUs must remain direct executable objects or an object
library whose objects are all placed on the final link line. Do not simply put
the expanded list into A2.2's ordinary `westwood_original` static archive.
Numerous WWSaveLoad/WWPhys/Combat persist and definition factories register
through translation-unit static objects; an ordinary archive member with no
otherwise referenced symbol is not extracted, so its initializer would never
run. The proven host fingerprint requires 3/3 SaveLoad subsystems and 33/33
persist factories. A direct source list, CMake `OBJECT` library, or an audited
whole-archive arrangement is acceptable.

## CMake migration checklist

1. Wait for the isolated A3 target to finish its current atomic build and
   renderer-lifecycle work. Re-read its CMake file and source count afterward.
2. Make the shared 248-TU world closure authoritative in `cmake/`; keep the
   exact count assertion. If the dynamic `.ldd`/GameObj slice lands first,
   replace 248 with the newly derived count and report the delta rather than
   silently retaining 248.
3. Change the root project to `RenegadeVitaA30` version `3.0.0` and use the A3
   entry point/runtime/boundary files listed above.
4. Preserve compile definitions:
   `NDEBUG=1`, `_UNIX=1`, `UMBRASUPPORT=0`,
   `RENEGADE_RUNTIME_READ_ONLY=1`, `RENEGADE_VITA_PORT=1`,
   `RENEGADE_VITA_A30=1`, `RENEGADE_A30_FULL_WWPHYS=1`,
   `RENEGADE_VITA_A22_ORIGINAL_SOURCES=105`,
   `RENEGADE_VITA_A22_PORT_SOURCES=9`, and the exact current
   `RENEGADE_VITA_A30_ORIGINAL_SOURCES` value. Add an explicit A3 port-TU count
   (`13` at this snapshot) rather than misusing the retained A2.2 count.
5. Preserve `-fno-strict-aliasing`, `-fno-exceptions`, `-fno-rtti`, function
   and data sections, GCC-15 warning accommodations, and forced inclusion of
   `msvc_compat.h`.
6. Preserve `--gc-sections`, `--wrap=shark_init`, and the A3 map filename.
7. Preserve these current link libraries unless the completed isolated link
   proves an additional requirement:
   `vitaGL`, `stdc++`, `SceLibKernel_stub`, `SceAppMgr_stub`,
   `SceAppUtil_stub`, `mathneon`, `c`, `SceCommonDialog_stub`, `m`,
   `SceGxm_stub`, `SceDisplay_stub`, `SceSysmem_stub`, `SceSysmodule_stub`,
   `zip`, `z`, `vitashark`, `SceShaccCgExt`, `taihen_stub`,
   `SceShaccCg_stub`, `SceKernelDmacMgr_stub`, `SceCtrl_stub`,
   `SceIofilemgr_stub`, and `pthread`.
8. Emit `RenegadeVita-A3.0.vpk`, `RenegadeVita-A3.0.map`, title ID
   `RNEGA3001`, app version `03.00`, and app name `Renegade Vita A3.0`.
9. Do not make the production target depend on
   `tools/host_a30_definitions/include`. Its lowercase `audiosaveload.h` and
   `winsock.h` are filename/declaration compatibility shims currently shared
   by accident. Move their function into the centralized port compatibility
   layer or use an exact staged source patch, then make both host and Vita
   consume that production-owned compatibility path.
10. Keep `a30_static_world_boundary.cpp` explicitly classified as a temporary
    static-world link boundary. Its definitions of
    `CombatManager::IAmServer`, `CombatManager::TheStar`,
    `GameObjManager::StarGameObjList`,
    `SmartGameObj::Is_Human_Controlled`, `VehicleGameObj::Get_Driver`, and
    `DiagLogClass::Log_Timed` are engine-owned and must be retired when the
    original owner TUs enter the dynamic/GameObj target. The WWAudio no-audio
    methods and DX8/Vita methods are legitimate external/platform boundaries.

## Required renderer lifecycle gate

The A3 process invokes two WW3D sessions:

1. the one-frame A2.2 regression calls `WW3D::Init` and `WW3D::Shutdown`;
2. `Run_A30_World_Runtime` calls `WW3D::Init` again for M00.

The audited vitaGL library has process-lifetime initialization and no matching
shutdown API. At the start of this audit, renderer `Shutdown()` cleared the
only `initialized` flag, causing the second `Initialize()` to call `vglInit`
again. Canonical migration is blocked until the isolated target has a separate
process-lifetime native-backend flag, a logical per-WW3D-session flag, a
host-testable two-session lifecycle proof, and a successful ARM compile/link.
The release symbol audit should retain `vglInit` but the physical/runtime log
must prove it is entered only on the first session.

## Canonical host validation

Create one A3 host runner (for example `tools/run_a30_host.sh`) that performs a
single strict restage, then runs the retained A2 host regression and the exact
M00 world target. Do not make two runners race by cleaning staging while an ARM
build is active.

The existing M00 host command shape is:

```bash
cmake -S tools/host_a30_definitions -B build/host-a30-definitions -G Ninja \
  -DCMAKE_BUILD_TYPE=RelWithDebInfo
cmake --build build/host-a30-definitions --parallel \
  --target a30_wwphys_definition_runtime
build/host-a30-definitions/a30_m00_world_runtime \
  "$RENEGADE_RETAIL_ROOT" \
  build/host-a30-definitions-runtime/user \
  build/host-a30-definitions-runtime/cache \
  build/host-a30-definitions-runtime/mods
```

The canonical host log must first retain these exact A2 semantic gates:

- A2.0: 19 checks, 0 failures;
- A2.1: 10 checks, 0 failures, `15161/32081/32/00000100`;
- A2.2: 14 checks, 0 failures;
- A2.2 Scene/Camera: one frame, 8 meshes, 357 vertices, 324 triangles,
  unsupported 0, checksum `5704AB7D`;
- A2.2 host integration final PASS.

Then require at least these exact A3 lines from the unchanged-retail host run:

```text
runtime.checks=45
runtime.failures=0
runtime.first_failure=none
world.required_subsystem_count=3
world.registered_subsystem_count=3
world.required_persist_factory_count=33
world.registered_persist_factory_count=33
world.definition_count=2157
world.definition_checksum=90DB91BE
world.static_object_count=495
world.static_light_count=192
world.render_object_node_count=1615
world.mesh_count=1288
world.mesh_vertex_count=38158
world.mesh_polygon_count=21537
world.loaded_prototype_count=1177
world.object_identity_checksum=4A930F8A
world.render_graph_checksum=BFA9C255
world.prototype_checksum=E835A45F
world.vis_object_count=1684
world.vis_sector_count=347
world.render.frames=1
world.render.mesh_submissions=652
world.render.vertex_submissions=30603
world.render.triangle_submissions=16939
world.render.geometry_checksum=34FFAD42
world.render.rejected_indexed_submissions=0
world.render.unsupported_submissions=0
world.default_render_target_resets=1
world.unsupported_gpu_calls=0
world.teardown_completed=true
A3.0 original M00 world runtime: PASS
```

Also preserve the exact world bounds
`(-109.983284,-109.420731,-18.072906)` to
`(121.511314,118.983627,39.252510)`, dynamic object count zero for this static
`.lsd` slice, and the original optional `m00_tutorial.ddb` missing/no-op result.
Do not infer a Vita runtime fingerprint from this host output. The Vita A3
callback currently runs continuously until START; physical A3 values remain
pending hardware evidence.

## Integration-report migration

`tools/generate_integration_report.py` cannot be reused unchanged. Its current
exact six-patch assertion fails against the current 22-patch project. Migrate
or parameterize it so the A3 report asserts:

- milestone `A3.0` and the pinned revision;
- the single shared effective original source manifest;
- 248 original TUs at this snapshot, with the module table above;
- 13 project-owned Vita TUs plus one SDK helper;
- 22 exact patch files, all applied only to generated staging with
  `--batch --forward --fuzz=0 --no-backup-if-mismatch`;
- 109 unique upstream files touched by the patch set (59 are compiled `.cpp`
  TUs in the current 248-TU closure; the remainder are dependency headers or
  staged sources for the next coherent closure);
- zero in-place upstream edits, `.orig`, or `.rej` files;
- explicit temporary static-world link boundaries rather than the stale
  `runtime_stubs_linked: 0` claim;
- complete runtime WWPhys (93 TUs), release-mode WWSaveLoad definition closure
  (11), partial Combat (11), DataSafe Commando (1), and partial WW3D (65);
- original MIX, W3D, DefinitionMgr, SaveLoad, PhysicsScene, Camera, and render
  traversal; no custom MIX/W3D/world parser, scene graph, physics, or asset
  format;
- no retail assets packaged and no deployment.

The generated report itself must be parsed as JSON and exact numeric fields
must be asserted by the canonical build. Simple greps for stale A2 strings are
not sufficient.

## ARM/link/release assertions

After the completed isolated target is green and migrated, `tools/build.sh`
must validate all of the following before touching active dist reports:

1. ELF is ELF32, little-endian ARM EABI.
2. The final link contains the exact current original-object closure. Because
   A3 direct-links objects, remove the stale `libwestwood_original.a` linker-map
   requirement. Audit the direct object list/count and representative map
   entries from every original module instead.
3. Retain all A2 symbol checks and add exact A3 symbols, including:
   `Run_A30_World_Runtime`, `WWSaveLoad::Init`,
   `SaveLoadSystemClass::Load`,
   `SaveLoadSystemClass::Post_Load_Processing`,
   `DefinitionMgrClass::Load`, `ArmorWarheadManager::Init`,
   `PhysicsSceneClass::Load_Level_Static_Data`,
   `PhysicsSceneClass::Pre_Render_Processing`,
   `PhysicsSceneClass::Post_Render_Processing`, `WW3D::Render`,
   `A30_Vita_Render_Loaded_World`, `A30_Vita_Log`, and the Vita renderer
   entry/submission functions.
4. Retain the vitaGL/vitaShaRK header/archive SHA audit and the linked
   `__wrap_shark_init` call-target audit.
5. Require the linker map to contain `libvitaGL.a`, `libvitashark.a`,
   `libSceShaccCgExt.a`, and the system archives needed by the completed link.
6. Require successful ELF -> VELF -> SELF -> VPK production.
7. Require the VPK to contain exactly `sce_sys/param.sfo` and `eboot.bin`.
8. Reject any `retail`, `Data`, `.dat`, `.dbs`, `.mix`, `.w3d`, `.rva`, or
   converted/custom asset payload.
9. Recheck canonical upstream is pristine and staging contains no `.orig` or
   `.rej` after host and ARM builds.
10. Never connect to, copy to, install on, or launch the Vita.

## Build report and artifact migration

Remove stale A2.2 release prose such as candidate-1 renderer failure,
"A2.2 hardware re-test pending", and A2.2 as the active output. The A3 build
report should state:

- A2.0/A2.1/A2.2 are accepted physical baselines;
- A3.0 host world load/render is 45/45 PASS;
- A3.0 physical world validation is pending manual Vita testing;
- 248 original TUs and 13 project-owned Vita TUs at this snapshot;
- the exact M00 host fingerprints above;
- the temporary direct call into the original M00 load path and temporary
  development Camera/SceCtrl bridge, without claiming full Commando startup;
- runtime log `ux0:data/renegade/user/logs/a30-runtime.log`;
- original unchanged Vita retail tree is used in place;
- retail/custom assets packaged: zero;
- automatic deployment: disabled.

Produce and checksum at minimum:

- `RenegadeVita-A3.0.vpk`
- `RenegadeVita-A3.0.elf`
- `RenegadeVita-A3.0.map`
- `RenegadeVita-A3.0.symbols.txt`
- `RenegadeVita-A3.0.elf-header.txt`
- `RenegadeVita-A3.0.vpk-contents.txt`
- `BUILD_REPORT.txt`
- `SOURCE_INTEGRATION_REPORT.json`
- `COMPILER_LOG.txt`
- `SHA256SUMS.txt`

A dedicated host-validation log in `dist` is useful, although the complete
outer compiler log already captures nested host output. Generate all files and
validate them before replacing generic active reports in `dist`; immutable
`baselines/A2.0`, `A2.1`, and `A2.2` must remain untouched.

The existing small `RenegadeVita_BUILD.ps1` remains suitable because it only
invokes `./tools/build.sh`. Do not regenerate an embedded PowerShell payload.

## Release blockers at this snapshot

1. The first isolated 248-TU ARM build/link/SELF/VPK has not yet completed.
2. The process-lifetime vitaGL/two-WW3D-session correction and its dual-session
   validation have not yet been folded into a completed A3 ARM artifact.
3. Root CMake, canonical host runner, report generator, build report, symbol
   audit, artifact names, and dist/checksum list are still A2.2.
4. The production Vita target still consumes two headers from a host-tool
   include directory.
5. The engine-owned temporary static-world symbol closures must remain clearly
   documented and must be retired, not normalized into permanent platform
   architecture, as the original dynamic/GameObj owner TUs arrive.

Once these are resolved and the canonical clean-restage build reproduces A2
regressions, A3 45/45 host evidence, the ARM link, SELF, VPK, symbol/map audit,
two-entry no-retail VPK, and checksum verification, the resulting A3 VPK is
ready for the next manual physical Vita world-render test.
