# Campaign boss game-object class support (Vita build)

Date: 2026-10-07. Evidence class: source/staging inspection, symbol inspection of
the last packaged ARM build (A3.5-dev238, 2026-10-04), and ARM `-fsyntax-only`
checks of the current staging using the recorded Vita compile flags. Not built,
not run on Vita3K or hardware.

## Classes in scope

| Class (staging/combat) | Def class ID | Object / Def chunk IDs | Base |
|---|---|---|---|
| `SakuraBossGameObj` / `SakuraBossGameObjDef` | `CLASSID_GAME_OBJECT_DEF_SAKURA_BOSS` | `CHUNKID_GAME_OBJECT_SAKURA_BOSS` / `..._DEF_SAKURA_BOSS` | `VehicleGameObj` |
| `MendozaBossGameObjClass` / `...DefClass` | `CLASSID_GAME_OBJECT_DEF_MENDOZA_BOSS` | `CHUNKID_GAME_OBJECT_MENDOZA_BOSS` / `..._DEF_MENDOZA_BOSS` | `SoldierGameObj` |
| `RaveshawBossGameObjClass` / `...DefClass` | `CLASSID_GAME_OBJECT_DEF_RAVESHAW_BOSS` | `CHUNKID_GAME_OBJECT_RAVESHAW_BOSS` / `..._DEF_RAVESHAW_BOSS` | `SoldierGameObj` |

`staging/combat/combatchunkid.h` and `CombatChunkID.h` are byte-identical to
upstream, so the enum values that retail `.ddb` definitions and saves depend on
are unchanged.

## Findings

1. **The sources are in the build.** `sakurabossgameobj.cpp`,
   `mendozabossgameobj.cpp` and `raveshawbossgameobj.cpp` are listed in
   `cmake/A35MultiplayerBuildingSources.cmake`. `CMakeLists.txt` appends that
   list when `RENEGADE_VITA_M00_DEMO` is OFF. That is the default, and
   `tools/build.sh` uses `RENEGADE_M00_DEMO=0`. Campaign scripts that drive the
   bosses are compiled through the 13-file campaign script inventory: M02
   `M02_Nod_Sakura`/`M02_Mendoza`, M03 `Sakura_Killed`, M05 `M05_Mendoza*`,
   M06 `M06_Mendoza`, and M08 `M08_Raveshaw`/`M08_Sakura*`.

2. **The factories are registered and not stripped.** Each TU defines its
   original `SimplePersistFactoryClass` for the object and the definition, plus
   `DECLARE_DEFINITION_FACTORY`. Both are also referenced by the original
   `FORCE_LINK(SakuraBoss|MendozaBoss|RaveshawBoss)` in `objlibrary.cpp`. The
   TUs go to the linker as objects, not as archive members, so
   `--gc-sections` cannot drop their `.init_array` constructors. The dev238
   symbol list contains `_GLOBAL__sub_I__Z22_Force_Link_SakuraBossv` and the
   Mendoza and Raveshaw equivalents. It also contains all nine factory globals,
   such as `_SakuraBossGameObjDefDefFactory`,
   `_SakuraBossGameObjPersistFactory` and `_SakuraBossGameObjDefPersistFactory`.

3. **Save and load chunks are handled with original layouts.** The only
   staging deltas are four patches:
   - `combat-a35-original-owner-cpp.patch`: GCC requires
     `&Class::member` for the Mendoza camera state-machine pointers.
   - `combat-a36-boss-save-status.patch`: propagates the status of child
     `Save`.
   - `combat-a36-boss-load-status.patch`: propagates the status of child
     `Load`.
   - `combat-a36-definition-hierarchy-load-status.patch`: propagates the
     status of definition `Load`.

   The chunk IDs, chunk order and variable micro-chunks are unchanged.
   `On_Post_Load` and `Register_Post_Load_Callback` are unchanged.

4. **The boss paths have no Win32 or DX8 dependency.** The 360 undefined
   symbols of the three dev238-era ARM objects resolve as follows:
   - 340 resolve to original `staging/` objects in combat, wwphys, wwmath,
     wwlib, wwsaveload, wwaudio, wwnet, ww3d2, wwtranslatedb and commando. Zero
     resolve to `port/` objects.
   - The other 20 are libc, libm or libstdc++ symbols, such as `sinf`,
     `atan2f`, `qsort` and `operator new`.

   The only platform crossing is `timeGetTime()` (`port/compatibility/include/mmsystem.h`,
   `gettimeofday`), reached through original `TimeManager`/`SysTime` headers.
   It is the timing boundary, not a stub.

5. **No port stub replaces boss behaviour.** In `port/`, boss names appear only
   in `a31_vita_runtime.cpp`'s script-spawn preset preparation lists, such as
   `"Mendoza Boss"`, `"Raveshaw"` and `"Sakura Crash Controller"`. These lists
   only preload models before the original `Create_Real_Object` path runs.
   Think, AI state machines, animation, weapons and damage all stay in the
   original Combat code.

## Defect found and fixed

`combat-a36-boss-load-status.patch` was added in 17d6d5f on 2026-10-05, after
dev238 was built. It wrapped several `Load` calls in boolean checks such as
`if (!X.Load(cload)) loaded = false;`. Those members return `void`:

- `StateMachineClass<T>::Load`: 14 Mendoza calls and 9 Raveshaw calls.
- `PilotClass::Load` and `PathClass::Load`: Sakura.

All three boss translation units therefore failed to compile with the Vita
toolchain (`could not convert ... from 'void' to 'bool'`). No ARM or host
object for these TUs has been built since that commit, so the current tree
could not link a full-port candidate.

The fix collapses those 25 void-returning calls back to the original
statements inside the patch. Status propagation still works through
`!cload.Has_Error()` and the bool-returning children (the parent class,
rocket defense objects, references, `StealthSoldier`, `TiberiumEffect` and
`CameraSpline`). Hunk line counts are unchanged, so the later
`definition-hierarchy-load-status` patch still applies with zero fuzz.

Validation:
- Regenerated staging with `tools/stage_sources.sh` against a temporary
  upstream symlink, then restored the symlink. Only the three boss `.cpp`
  files changed. No `.orig` or `.rej` files were left behind.
- `renegade_patch_inventory.py --check-staging` passes: 506 patches, registry
  sha256 `0ce6dd9e…5d07bd`.
- ARM `-fsyntax-only` passes for all three boss TUs and `objlibrary.cpp`.

## Remaining gaps and next gates

- Every staged Combat TU should go through a full ARM build. The 2026-10-05
  status-patch batch has not been compiled in any build directory yet.
- A save/load round-trip in each boss mission (M02/M03 Sakura, M05/M06 Mendoza,
  M08 Raveshaw) still needs Vita3K evidence, then physical evidence.
- The fight behaviour (AI states, animations, weapons, camera) has not been
  validated in a runtime yet. Nothing here proves it is correct.
