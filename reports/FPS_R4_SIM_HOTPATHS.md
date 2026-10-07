# FPS round 4: SIM_HOTPATHS (Combat + WWPhys simulation cost)

Scope: physical M13 ambush in dev238.

- Combat costs about 13.3 ms/frame (`A4 campaign pacing ... combat=`).
- cNetwork costs about 0.5 ms and control about 0.3 ms.
- Port logging and telemetry were already audited (ledger, 2026-10-06), so
  this report does not repeat that.
- Nothing here was measured on hardware.

## Key finding: the A3.6 frame profiler never saw an engine scope

Commit cbd42ab routes `WWPROFILE` to the Vita profiler by patching
`staging/wwdebug/wwprofile.h`. But `staging/wwdebug` is not in
`target_include_directories` (CMakeLists.txt:526-565); only
`${RENEGADE_UPSTREAM}/Code/wwdebug` is.

So every engine TU (combat, wwphys, ww3d2, wwaudio, commando) resolves the
pristine header, where `WWPROFILE` is empty because `WWDEBUG` is not defined.

Evidence:

- An ARM `wheel.o` built with `-DRENEGADE_VITA_FRAME_PROFILE=1` has no
  `Renegade_Frame_Profile_*` or `g_renegade_frame_profile_active` references.
- Its size (238888 B) is identical to the build with the scopes compiled out.

Consequences:

- A3.6 logs could only have shown the native `Vita Sim *` and render scopes.
  They would not include `Game Obj Think`, `Scene`, `Soldier Think`, or
  `VehiclePhysClass::*`.
- The ledger's "microsecond-scale profiler" holds only because the profiler
  was inactive.

## Changes (diagnostic-only; no engine-read value changes)

1. **Include fix (CMakeLists.txt).** Insert `${RENEGADE_STAGE}/wwdebug` just
   before upstream wwdebug.
   - Only `wwprofile.h` differs between the two directories. wwdebug.h,
     wwhack.h and wwmemlog.h are identical, and those names are unique across
     the include directories.
   - All engine `WWPROFILE` scopes go live, as cbd42ab intended.
   - Cost per scope when enabled: two `sceKernelGetProcessTimeWide` calls plus
     one `sceKernelGetThreadId` call. `sceKernelGetProcessTimeWide` is a
     SceLibKernel wrapper over the SceProcessmgr syscall
     `sceKernelGetProcessTimeWideCore`.
   - Cost per scope with `RVFP1 0`: one load and one branch.
2. **Per-wheel opt-out.**
   - The new `wwdebug-a36-frame-profile-tu-opt-out.patch` makes
     `RENEGADE_VITA_FRAME_PROFILE_SKIP_TU` compile a TU's scopes to nothing.
   - CMake sets the macro for `staging/wwphys/wheel.cpp` only.
   - Why: wheel.cpp opens up to 5 scopes per wheel per force evaluation
     (wheel.cpp:689,703,785,824,903/1071/1218). `Midpoint_Integrate`
     evaluates forces twice per step (rbody.cpp:1172; ode.cpp:142,155).
   - One awake tank with ~10 contacting wheels would cost ~100 scopes, about
     200 syscalls per frame. That is more than the work being timed.
   - `VehiclePhysClass::Compute_Force_And_Torque` (vehiclephys.cpp:308) still
     times the whole loop.
3. **Combat cast counters.**
   - `wwphys-a36-scene-cast-counters.patch` adds a Vita-only increment at the
     top of `PhysicsSceneClass::Cast_Ray/Cast_AABox/Cast_OBBox`, split into
     culled and collision-region.
   - `a31_gameplay_boundary.cpp` accumulates the deltas across the Combat
     stage.
   - The 120-frame checkpoint logs a windowed line:
     `A4 combat casts: frames= window= combat_avg_us= soldiers_awake/hibernating_per_frame= per_frame ray_cull/ray_region/aabox_cull/aabox_region/obbox_cull/obbox_region=`.
   - Awake and hibernating counts come from the original
     `_AwakeSoldiers/_HibernatingSoldiers` tallies (gameobjmanager.cpp:404),
     which were console-only on PC.

## Risk

- The include fix adds a scope object wherever `WWPROFILE` appears. Two
  scopes in one C++ scope would be a compile error (on PC that could only
  happen in WWDEBUG builds). The ARM sweep below found none.
- With the profiler on by default, timings now include the profiler's own
  overhead. Read `scopes_per_frame`, and use `RVFP1 0` for A/B comparisons.
- The counters write to globals that nothing in the engine reads.

## Tests

- `python3 -m unittest tools.test_sim_hotpaths_contract`: 6/6 OK. It covers:
  - `SKIP_TU` macro selection, checked through the preprocessor.
  - wheel.cpp is the only TU that opts out, and the parent scope still wraps
    the wheel loop.
  - The staged include comes before upstream, and the staged header set is
    as expected.
  - Each cast is counted once, before any return.
  - The cast snapshot is taken before `CombatManager::Think` and accumulated
    after `combat_end_us`.
  - Both patches are registered once and reverse-apply with `-F0`.
- `python3 -m unittest tools.test_npc_path_frame`: OK.
- `patch -p1 -F0 --dry-run` of both patches on the pre-change staged files:
  clean.
- ARM TU builds: `wheel.cpp`, `vehiclephys.cpp`, `pscene_collision.cpp`,
  `a31_gameplay_boundary.cpp` and `a31_vita_runtime.cpp` all OK.
- ARM `-fsyntax-only` of all 87 `WWPROFILE` TUs with the staged wwdebug
  directory first (`-iquote`): 80 OK, 0 failed. The other 7 are not in the
  build graph (mainloop, wolgmode, dx8wrapper, console, langmode, overlay,
  dx8renderer).
- nm/objdump with routing on:
  - `vehiclephys.o` references `Renegade_Frame_Profile_Begin/End`.
  - `wheel.o` without `SKIP_TU`: 7 Begin call sites, 249356 B.
  - `wheel.o` with `SKIP_TU`: 0 call sites, 238888 B.

## Coordinator leads (checked; no change)

- **DataSafe.** `DataSafeClass<T>::Get/Set` call `Shuffle()` and
  `Security_Check()` on every access. Both return after a static call counter
  until 100000 calls have passed (datasafe.h:229, datasafe.cpp:990-995,
  datasafe.h:1097-1102). So each reads `TIMEGETTIME` at most once per 100000
  accesses.
  - `THREAD_SAFE_DATA_SAFE` is off (datasafe.h:187), so `ThreadLockClass` is
    empty and takes no mutex.
  - Not a per-frame cost. Main bc88fcb (`CLOCK_MONOTONIC` via the
    process-time syscall plus two 64-bit divides) is fine at a few calls per
    frame.
  - This branch predates bc88fcb and does not touch `mmsystem.h`.
- **HumanAnimControlClass::Update.** `StringClass::Format` runs only when
  `_Monitor == this`. `_Monitor` is set only by `Get_Information`, and its
  game caller is gated by a local `InfoDebug = false` (hud.cpp:1494). The
  function takes no mutex.
  - Real, original cost: with more than two blended animations (a
    cross-fade), each update deletes the old `HAnimComboDataClass` objects and
    allocates new ones, with the malloc lock, per soldier per frame
    (animcontrol.cpp:886-893; hanim.cpp:260).
  - *Correction (2026-10-07, tutorial round 1):* `HAnimComboDataClass` is an
    `AutoPoolClass<HAnimComboDataClass,256>` (`hanim.h:176`), so this churn uses the
    pool free list, not the malloc lock. See
    [frame allocations](tutorial/TUT_R1_FRAME_ALLOCATIONS.md).
  - Deferred: reusing these objects needs an `Is_Shared`/ownership proof.
    Measure via `Soldier PostThink` first.

## Ranked hotspots (source analysis; confirm with the now-live scopes)

| # | Suspect | Port? | Confirm on HW |
|---|---|---|---|
| 1 | Vehicle step: 2 force evaluations per step, one full static-AABTree + dynamic `Cast_Ray` per wheel each time (wheel.cpp:329, no collision region). Skipped only if the spring endpoints are bit-identical. | No | `VehiclePhysClass::Timestep`, `...::Compute_Force_And_Torque`, `RigidBody::Timestep`; `ray_cull` |
| 2 | Frame-profiler overhead once live | Yes | `scopes_per_frame`; `combat=` with `RVFP1 1` vs `0` |
| 3 | Soldier Phys3 moves (box sweeps in the collision region) | No | `Phys3::Timestep`, `HumanPhys::Timestep`, `Phys3::Collide_Move`; `aabox_region`/`obbox_region` |
| 4 | Soldier logic and animation | No | `Soldier Think`, `Soldier PostThink`, `Human Animation/State`, `Post Think` |
| 5 | Vision: one ray per enemy pair, but each observer only every 0.5-1 s (`MovingSoundTimer`, smartgameobj.cpp:744-772) | No | `See`, `Cast Ray` calls/frame |
| 6 | Bullets and instant-hit rays | No | `Bullets`, `Bullet Think`, `Cast_Ray` |
| 7 | cNetwork in SP: `Server_Update_Dynamic_Objects` returns early on `IS_SOLOPLAY` (comnetrcvinst.cpp:137), so nothing is serialised. The remainder is God Think, `End_Game_Test`, `Hibernation_Think` (PVS merge + object walk, messages.cpp:1355) and loopback service. | No | `cNetwork::Update`, `Shared CS Think`, `Server_Think`, `Client_Think` |
| 8 | Vehicle PostThink: `sprintf("SEAT%d")` + linear `Get_Bone_Index` per occupied seat per frame (vehicle.cpp:1639-1652). A cache would need a model-swap invalidation proof. | No | `Vehicle PostThink` |
| 9 | More soldiers awake than on PC (for example, missing PVS data) | Maybe | awake/hibernating per frame |

Checked and not issues:

- `#pragma pack` in win32_compat.h:106-125 is balanced and covers dialog
  templates only.
- `WWASSERT` and `WWDEBUG_SAY` compile out.
- The WWPhys port patches add no per-frame work:
  - `History` stays NULL in SP.
  - The track tokens are matched at model set only.
  - The path guard is a single compare.
- Paths cost 5-44 us/frame.
- `UpdateOnlyVisibleObjects` is an original console toggle, off by default;
  left as is.

## Expected gain (unmeasured) and hardware measurement

- No sim speedup compared with dev238, where the profiler was inactive.
- The opt-out avoids roughly 0.5-2 ms/frame of per-wheel profiler overhead
  while vehicles are awake. The include fix would otherwise add that cost.
- The counters cost under 1 us/frame.
- The main value is that the 13.3 ms can now be attributed.

Hardware measurement, on the fixed M13 ambush route:

1. Run with `RVFP1 1` and record the `A3.6 frame-profile` and `-worst`
   lines plus `A4 combat casts`.
2. Repeat with `RVFP1 0` and compare `combat=` and p50.

What to do next depends on the result:

- If `VehiclePhysClass::Compute_Force_And_Torque` and `ray_cull` dominate,
  look at the static AABTree ray path for result-identical savings.
- If almost all soldiers stay awake, audit hibernation and the vis data.
- If `scopes_per_frame` is above about 1000, opt out more inner-loop TUs or
  use a cheaper time source.
