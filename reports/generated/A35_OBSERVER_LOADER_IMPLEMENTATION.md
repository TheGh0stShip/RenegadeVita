# A35 Observer Loader Implementation (v3.5-dev3 focused repair step)

## Scope

- Implemented one deterministic patch and one focused host contract to add
  bounded observer-loader diagnostics and root/child validation around
  `PersistentGameObjObserverManager::Load`.
- No VPK build, physical Vita deploy, or gameplay/rendering/audio/network changes in
  this step.

## Changed files

- `port/patches/combat-a35-observer-load-diagnostics.patch`
- `port/patches/wwlib-a35-chunkio-open-chunk-breadcrumbs.patch`
- `port/validation/persistent_observer_loader_contract.cpp`
- `tools/stage_sources.sh`
- `tools/host_a30_definitions/CMakeLists.txt`
- `staging/combat/persistentgameobjobserver.cpp` (materialized by staging)
- `staging/wwlib/chunkio.cpp` (materialized by staging)

## Deterministic patch details

- New patch introduces:
  - entry breadcrumb (`Debug_Say`),
  - required root open failure breadcrumb and explicit `false` return,
  - wrong-root breadcrumb plus root-close preservation (`return false`),
  - per-child open breadcrumb with id/length/depth,
  - factory-found/unknown-child breadcrumb,
  - per-child close breadcrumb,
  - child-exhaustion breadcrumb,
  - final root close and function exit breadcrumbs.
- The staged combat source now returns `false` if `Open_Chunk()` fails on
  initial root open.

## Required-root behavior before/after

- Before: `PersistentGameObjObserverManager::Load` immediately called
  `cload.Open_Chunk()` then asserted chunk id with `WWASSERT`, and had no
  explicit failure breadcrumbs.
- After: required root open and root-id are now validated in code, both paths
  return `false` on failure, preserving root close balance when possible and
  emitting bounded debug breadcrumbs for all expected branches.

## Host contract route

- New target: `a35_persistent_observer_loader_contract_selftest`
  in `tools/host_a30_definitions/CMakeLists.txt`.
- Source: `port/validation/persistent_observer_loader_contract.cpp`.
- Target shares existing WWLib sources (`${RV_WWLIB_SOURCES}`) and reuse pattern with
  existing host contract include/compile/link settings.

## Contract test coverage

The contract now directly invokes `PersistentGameObjObserverManager::Load` on the
deterministic fixtures, with a narrow `PersistFactoryClass` hook to observe known
child behavior.

The contract verifies with synthetic fixtures:

- valid container with no children,
- valid container with known+unknown children,
- missing/truncated required root header,
- wrong root ID,
- truncated child header,
- repeated independent invocations.
- chunk depth/close balance after each case (`depth_after_root_close == 0` where
  expected).
`PersistentGameObjObserverManager::Load` is directly invoked in this target and the
translation unit under test is compiled into the executable as part of the focused
contract closure.

## Commands run (exit status)

1. `bash tools/stage_sources.sh`  
   Exit: `0`

2. `cmake -S tools/host_a30_definitions -B build/host-a30-definitions -G Ninja -DCMAKE_BUILD_TYPE=RelWithDebInfo -DRENEGADE_USE_CCACHE=ON`  
   Exit: `0`

3. `cmake --build build/host-a30-definitions --target a35_persistent_observer_loader_contract_selftest --parallel 4`  
   Exit: `0`

4. `build/host-a30-definitions/a35_persistent_observer_loader_contract_selftest`  
   Exit: `0`  
   Output summary: `A3.5 observer loader contract: root/child checks 46, failures 0`

5. `cmake --build build/host-a30-definitions --target a36_file_factory_telemetry_contract_selftest --parallel 4 && build/host-a30-definitions/a36_file_factory_telemetry_contract_selftest`  
   Exit: `0`  
   Output summary: `A3.6 rooted file-factory telemetry contract: 13 checks, 0 failures; ...`

6. ASan variant:
   `cmake -S tools/host_a30_definitions -B build/host-a35-asan -G Ninja -DCMAKE_BUILD_TYPE=RelWithDebInfo -DRENEGADE_USE_CCACHE=ON -DCMAKE_C_FLAGS='-O1 -g -fsanitize=address' -DCMAKE_CXX_FLAGS='-O1 -g -fsanitize=address' -DCMAKE_EXE_LINKER_FLAGS='-fsanitize=address'`  
   `cmake --build build/host-a35-asan --target a35_persistent_observer_loader_contract_selftest --parallel 4`  
   `ASAN_OPTIONS='abort_on_error=1:detect_leaks=0:halt_on_error=1' build/host-a35-asan/a35_persistent_observer_loader_contract_selftest`  
   All exit `0`, summary `root/child checks 46, 0 failures`.

7. UBSan variant:
   `cmake -S tools/host_a30_definitions -B build/host-a35-ubsan-visible -G Ninja -DCMAKE_BUILD_TYPE=RelWithDebInfo -DRENEGADE_USE_CCACHE=ON -DCMAKE_CXX_FLAGS='-O1 -g -fsanitize=undefined -fno-sanitize-recover=all' -DCMAKE_EXE_LINKER_FLAGS='-fsanitize=undefined -fno-sanitize-recover=all'`  
   `cmake --build build/host-a35-ubsan-visible --target a35_persistent_observer_loader_contract_selftest --parallel 4`  
   `UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1' build/host-a35-ubsan-visible/a35_persistent_observer_loader_contract_selftest`  
   All exit `0`, summary `root/child checks 46, 0 failures`.

8. Review validation after implementation:
   `patch --batch --forward --fuzz=0 --dry-run` against a fresh copy of the
   upstream Combat source, followed by application and a diff against staged
   output: exit `0`.

9. `cmake --build build/host-a30-definitions --target a31_gameplay_seed_runtime --parallel 4`
   Exit: `0`. This compiled the actual staged
   `combat/persistentgameobjobserver.cpp` translation unit. It emitted only
   pre-existing legacy-source warnings; no error was reported.

## Current evidence and uncertainties

- No `.rej` / `.orig` files remain after restaging.
- Stage log shows patch application and explicit `Applied:` entries for the new patch.
- Direct `PersistentGameObjObserverManager::Load` is invoked in host for:
  valid/empty, valid/mixed known+unknown, wrong root, missing header,
  truncated child, and repeated-load cases; each keeps chunk depth balanced.
- `ChunkLoadClass::Open_Chunk` null pointer, missing required-root header,
  parent-container exhaustion, and repeated-open balance paths are now covered
  in `Run_Chunk_Open_*` loaders and assertions.
- This step does **not** prove the physical crash root cause.
- No VPK was built in this step.

## Next narrow evidence needed from physical Vita

- One physical capture around the failing `0x810EAFBE` load path with exact required-root/child breadcrumbs
  enabled and a matching `dev3` artifact set, to separate:
  - file-open failure at required root,
  - malformed root/child header path,
  - versus chunk data/serialization content entering normal loop path.
