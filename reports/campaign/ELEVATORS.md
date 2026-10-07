# Campaign elevators and moving collision — 2026-10-07

Evidence class: source review plus host parsing of retail level files from the
Vita3K `Data/` copy (M09.mix SHA-256 prefix `059fc7de`, identical to the
identity recorded in `M09_READINESS.md`; other mixes were not hashed against
the physical Vita). Nothing was built, run, or tested on Vita3K or hardware.
One header syntax check was compiled (see "Fix applied"). This report cannot
prove any physical behavior.

## 1. Two different elevator mechanisms

Retail missions use two unrelated mechanisms. Both are original Combat/WWPhys
code; neither is replaced by the port.

| Mechanism | Owner | Driven by | Saved as |
|---|---|---|---|
| `ElevatorPhysClass` (call-zone elevator) | `staging/combat/elevator.cpp` | Own state machine: call zones, 1 s call timer, 0.5 s state check; AI uses `PathActionClass::Handle_Elevator` (`pathaction.cpp:327`) | dynamic-object chunk `0x00020A01` |
| `StaticAnimPhysClass` driven by script | `staging/wwphys/staticanimphys.cpp` + `AnimCollisionManagerClass` | `Commands->Static_Anim_Phys_Goto_Frame / _Goto_Last_Frame` (`scriptcommands.cpp:2249-2282`) | static-object state |

Doors are the same split: `DoorPhysClass` (`doors.cpp`, chunk `0x00020A00`)
plus script-driven anim doors.

## 2. Inventory per mission (retail `.lsd`, host chunk walk)

Counts are persisted object chunks `0x00020A01` (ElevatorPhys) and
`0x00020A00` (DoorPhys) found anywhere in each mission's `.lsd`
(`PHYSICS_CHUNKID_*` in `staging/wwphys/wwphysids.h`). The M00 count of 4
ElevatorPhys agrees with the independent `A30_DEFINITION_TRACE.md:512`
(`m00.elevator_objects = 4`). Model names are the first identifier string in
each object chunk, so they are a name inference, not a parsed property.

| Mission | ElevatorPhys | ElevatorPhys models | DoorPhys | Script-driven lifts |
|---|---|---|---|---|
| M00 Tutorial | 4 | MNHND_ELEV01 x4 | 10 | none |
| M01 | 6 | HND_ELEV01-03, COM_LIFT, COM_RLIFT | 31 | 1 `Static_Anim_Phys` call site in `Mission01.cpp` (target not inspected) |
| M02 | 15 | HND_ELEV01-03, DAM_ELEV01 x4, PWR/OBL/ATR lifts, ag_coreshower | 41 | none |
| M03 | 7 | REF_LIFT, AG_REFRNDOOR, PWR/COM lifts, ag_coreshower | 21 | `cave_lift` (obj 1300881, `Mission03.cpp:6945/7004`; `cave_lift.w3d` is in M03.mix) |
| M04 | 7 | SHP_LIFT1-7 | 41 | 2 call sites in `Mission04.cpp` (targets not inspected) |
| M05 | 0 | - | 2 | none |
| M06 | 0 | - | 50 | 6 call sites in `Mission06.cpp` (targets not inspected) |
| M07 | 3 | OBL_ELEV01, OBL_ELEV, OBL_PRSN_LIFT | 8 | none |
| M08 | 8 | RES_ELEV11, LAB_SPN_DOOR08, CENT_ELEV01, ELEV01, RES_ELEV04, BIG_ELEV, BIG2_ELEV, RES_ELEV05 | 82 | `M08_Elevator_Movement_Zone` (`mission08.cpp:6902`) |
| M09 | **0** | - | 20 | **7 lift models** (below) |
| M10 | 16 | HND/PWR/OBL/COM/REF/ATR lifts, ag_coreshower | 61 | 6 call sites in `Mission10.cpp` (targets not inspected) |
| M11 | 4 | WAR_ELEV01, L11_ELVMUT x2, ag_coreshower | 39 | MISS_ELEV1-4 missile lifts; 2 `SHP_DOORP01` door calls |
| M13 | 0 | - | 0 | none |

There is no `M12.mix` in the Vita3K copy (not scanned).

### M09 (the question was about elevators; M09 has no ElevatorPhys)

M09's lifts are `StaticAnimPhys` objects moved by
`M09_Elevator_Movement_Zone`, `M09_Elevator_All_Zone` and
`M09_Elevator_All_Controller` (`Mission09.cpp:3254-3520`, nine-entry
`elevators[]` table). Level-data model names found: ELEV01, L09_BIG_ELEV,
L09_BIG2_ELEV, L09_RES_ELEV05, L09_RES_ELEV06, RES_ELEV04, RES_ELEV11. The
`.w3d` for each indexed name, with animation header frames/rate:

| `Anim_num` | Name | Source archive | Frames @ fps |
|---|---|---|---|
| 0 | l09_res_elev06 | M09.mix | 52 @ 15 |
| 1 | elev01 | always.dat | 66 @ 30 |
| 2 | res_elev04 | always.dat | 21 @ 15 |
| 3 | l09_res_elev05 | M09.mix | 71 @ 15 |
| 4 | res_elev11 | always.dat | 21 @ 15 |
| 5 | l09_big_elev | M09.mix | 111 @ 30 |
| 6 | l09_big2_elev | M09.mix | 81 @ 30 |
| 7 | cent_elev01 | **not in M09.mix, always.dat or Always2.dat** | - |
| 8 | lab_spn_door08 | always.dat | 15 @ 15 |

`M09_READINESS.md` records that retail data only passes `Anim_num` 0,1,3,5,6,8,
so the missing `cent_elev01` is unused. The lookup is
`WW3DAssetManager::Get_HAnim` (`assetmgr.cpp:920`): it splits at the `.`,
loads `<name>.w3d` on demand through the original file factory, and
registers a name as known-missing on failure. No Vita patch alters that path.

### M11

Passenger lifts are four ElevatorPhys objects, so Sydney's escort goes through
`PathActionClass::Handle_Elevator`, not through scripted frame jumps. The
`M11_Missile_Lift_*` scripts (`Mission11.cpp` 8641-10851) drive MISS_ELEV1-4
(46 frames @ 15 fps, in M11.mix) with `Static_Anim_Phys_Goto_Frame` only; they
are silo lifts, not passenger lifts. `WAR_ELEV01` (41 @ 15) and `L11_ELVMUT`
(46 @ 15) are in M11.mix.

## 3. Port patches touching this code

Diffed staged vs upstream (`upstream/CnC_Renegade/Code`, CRLF-normalized):

| File | Difference from upstream |
|---|---|
| `combat/elevator.cpp`, `combat/doors.cpp` | include-case fixes; `Load`/`Save` now propagate child status (`loaded`, `csave.Report_Error`). No timer, state, zone, or sound logic changed. |
| `wwphys/accessiblephys.cpp`, `dynamicphys.cpp`, `dynamicanimphys.cpp` | same save/load status propagation only |
| `wwphys/staticanimphys.cpp` | status propagation + Vita static-load trace calls (`A35_Vita_Static_Load_Trace_Step`) |
| `wwphys/movephys.cpp` | `Controller`/`Carrier` saved as 32-bit tokens through `uintptr_t` (`wwphys-a30-pointer-tokens`); remap requests unchanged; Timestep untouched |
| `wwphys/animcollisionmanager.cpp` | one line: `REF_PTR_RELEASE(anim)` after the prev-animation load (`wwphys-a35-prev-animation-load-ref`), fixes a leaked reference. `Timestep`, `Check_Collision`, `Push_Collided_Object`, `Revert_Animation_State` are unmodified. |
| `wwphys/phys3.cpp`, `humanphys.cpp` | status propagation, network helpers, a loop-scope fix, finite-float guards on `Jump_To_Point`. Ground check, `Link_To_Carrier`, snap-down and `Move_Riders` are unmodified. |
| `wwphys/ridermanager.cpp`, `combat/timemgr.cpp`, `wwlib/systimer.cpp` | **no difference from upstream** |
| `combat/pathaction.cpp` | `REQUEST_REF_COUNTED_POINTER_REMAP` -> `REQUEST_POINTER_REMAP` for `Mechanism` and `Path` (`combat-a35-pathaction-borrowed-remap`). I checked that `PathActionClass` never `Add_Ref`s either pointer (`pathaction.cpp:129`, `Initialize`) nor releases them, so the patch removes an unmatched extra reference rather than creating a dangling one. |

Nothing in the patch set changes elevator or door collision, riding, or
timing. No `port/patches/scripts-*.patch` or scriptcommands patch mentions
`Elevator`, `Static_Anim_Phys` or `Goto_Last_Frame` (grep). The M09 script
patches are `scripts-a35-m09-camera-bounds` and
`scripts-a36-m09-keycard-mobius-refetch`.

## 4. Timing review: simulated time vs real time

Every elevator/door/anim path takes its step from the simulated frame time:

- `ElevatorPhysClass::Timestep(dt)`: `CheckTimer -= dt` (0.5 s) and
  `CallTimer -= dt` (1 s). `DoorPhysClass::Update_State(dt)`: `Timer -= dt`,
  `CheckTimer -= dt` (0.3 s).
- `AnimCollisionManagerClass::Timestep(dt)`: `CurFrame += frame_rate * dt`,
  snapping exactly to `TargetFrame` on overshoot, so the `== 0` and
  `== Num_Frames-1` end tests in `Update_State` are exact float compares of
  an assigned value. ARM hard-float VFP has no extended precision, and the
  build uses `-fno-strict-aliasing` with no fast-math (`CMakeLists.txt:126,609`).
- AI exit timer: `Timer -= TimeManager::Get_Frame_Seconds()`
  (`pathaction.cpp:~400`).
- `dt` comes from `COMBAT_SCENE->Update(TimeManager::Get_Frame_Seconds(), 0)`
  (`combat.cpp:767`); `TimeManager` caps a step at 200 ms (`SLOWEST_FPS 5`) and
  advances the WW3D clock by the same `FrameTicks`.
  `ANIMATION_CLOCK_OWNERSHIP.md` (dev231) already removed the second WW3D
  clock writer from gameplay. Remaining `WW3D::Sync` calls in the port are
  in the renderer self-test, the A30 demo path, and the M00 scene-prewarm loop
  (`a31_vita_runtime.cpp:2014`), which runs with simulation frames = 0.

Consequences at low frame rates:

- At the original clamp a 5 fps frame advances a 30 fps lift animation by 6
  frames (0.2 s); the 0.5 s state check and 1 s call timer take 3-5 frames
  instead of 30. Lift travel time is unchanged in sim time. Frames longer than
  200 ms lose sim time (slow motion) but never desynchronize lift animation,
  its sound frames, or its timers from each other. This matches
  `SLOWDOWN_TIMING_EFFECTS.md`.
- `ElevatorPhysClass::Update_Sound_Effects` detects "frame crossed" with
  `Has_Frame_Occured(prev, curr, target)` (both directions), so a larger step
  cannot skip a door/motor sound frame. It runs in `Timestep` before
  `PrevFrame` is updated; unmodified original logic.
- The audio side of lifts (`Create_Instant_Sound`, `Create_Continuous_Sound`
  on bone `ELESOUND`) plays in real time. A long hitch can leave a door sound
  slightly ahead of the animation; no ownership problem.

### Defect found at the timing boundary (fixed)

`TimeManager::SystemTicks()` is `TIMEGETTIME` = `SystemTime.Get` =
`timeGetTime()`, and the port's `timeGetTime` (`port/compatibility/include/
mmsystem.h`) used `gettimeofday`. Disassembly of the installed VitaSDK
`libc.a` shows `clock_gettime(CLOCK_REALTIME)` reads the RTC
(`sceRtcGetCurrentClock`) and `CLOCK_MONOTONIC` (id 4) reads
`sceKernelGetProcessTimeWide`; `gettimeofday` is the RTC path (`_gettimeofday_r`).
Win32 `timeGetTime` is monotonic, and `TimeManager::Update_Frame_Time` only
clamps the upper bound (`MIN(FrameTicks, 200 ms)`). A backward RTC step (manual
clock change or network time sync) would produce one hugely negative
`FrameTicks`, and every sim timer would then gain that time:
`CheckTimer`/`CallTimer`/door `Timer` could jump by the size of the step and a
lift or door would stop re-evaluating until it elapsed, while lift animation
targets would run backward for that frame. `win32_compat.h:408` and
`A30_COMMANDO_NEXT_RUNTIME.md:484` already state the intent that simulation
timing is monotonic; the code did not implement it.

I have no evidence that this occurred on hardware. It is a latent boundary
defect, not an explanation for any observed symptom.

Fix: on `__vita__`, `timeGetTime` reads `CLOCK_MONOTONIC` (falls back to
`gettimeofday` if the call fails). Host and test builds are unchanged. The
epoch is not used anywhere else: the only consumers are `SysTimeClass`
(subtracts its own start time), the texture-loader and profile deltas.
`port/compatibility/include/mmsystem.h` is the only file changed.
Validation: `arm-vita-eabi-g++ -fsyntax-only` and host `g++ -fsyntax-only` on
a two-line translation unit including the header both pass. The Vita branch
was compiled (`__vita__` is predefined by the toolchain). No ARM project
build or host test suite was run. Required follow-up: the next candidate build
and a hardware check that the frame timer, lift timing and TTFS/telemetry
timestamps are still sane.

## 5. Riders and moving-platform collision

Mechanism (all original, unmodified by the port):

1. `Phys3Class::Check_Ground` and the snap-down path call
   `Link_To_Carrier(CollidedPhysObj, CollidedRenderObj)` when the soldier
   stands on a physics object (`phys3.cpp:1325, 1962`); it clears the link when
   airborne (`1223, 1982`).
2. The lift's `AnimCollisionManagerClass::Timestep` caches the collision mesh
   start/end transform, and `Check_Collision` computes
   `delta = end * inverse(start)` and calls `RiderManager.Move_Riders(delta,...)`
   (`animcollisionmanager.cpp` ~1230-1245). Riders are therefore moved by the
   exact geometric delta of that step; the amount does not depend on `dt` or on
   the rider's own gravity step.
3. Non-rider dynamic objects that overlap are pushed
   (`Push_Collided_Object` -> `MoveablePhysClass::Push`); if the push fails the
   whole animation step reverts (`Revert_Animation_State`) and the lift stays
   at `PrevFrame` until the obstruction clears. A rider overlapping its own
   carrier mesh also reverts (the squish code is commented out in retail).

Assessment for Vita:

- No fall-through mechanism that depends on frame rate was found. A larger step
  moves the rider by the same delta in a single `Move_Riders`, so a 200 ms
  frame cannot leave a rider behind the car; the rider is only unlinked if its
  ground cast fails, which is the same condition as on PC.
- The collision tests themselves (`Intersect_Scene`, `Cast_AABox`) are the
  original CPU paths; the port has no collision patches. Float behavior differs
  only by ARM VFP versus x87, which has no extended precision. WWPhys compiles
  at `-O3` (`RENEGADE_VITA_HOT_PATH_O3`, `CMakeLists.txt:42,672`); that is a
  compiler-risk class to watch, not an observed fault.
- A blocked or reverted lift is possible at any frame rate and is original
  behavior. If a lift stalls, the cause is an overlapping object or a rider the
  `RiderManager` marks as colliding with the car's own mesh.
- Save/load: `MoveablePhysClass::Carrier` is saved as a 32-bit token and
  remapped after load, so a rider's link depends on the post-load pointer
  remap. `ElevatorPhysClass::Load` ends by setting `ANIMATE_TARGET` with target
  frame 0 while `State` is restored from the save. That is original code
  (diff shows only status propagation); I did not examine whether a save made
  mid-travel or at the opposite floor resumes consistently in retail, and no
  host or Vita test exercises it.
- Physical evidence: the user rode both M00 elevators on Vita3K (dev111/dev118
  captures) and reported rendering artifacts on the car, not fall-through
  (`DEV111_ELEVATOR_RENDERING_FOLLOWUP.md`, `DEV118_VISUAL_DEFECTS.md`). That is
  indirect, emulator-only evidence. No M09 or M11 lift has been run.

## 6. Residual risks (not source-closable here)

1. `Static_Anim_Phys_Goto_Last_Frame` dereferences
   `Get_Animation_Manager().Peek_Animation()` without a null check
   (`scriptcommands.cpp:2279`, original). For every retail name that M09
   (indices 0,1,3,5,6,8), M03 (`cave_lift`) and M11 (MISS_ELEV*) pass, the
   `.w3d` exists in the archive that mission searches, so the on-demand load
   should resolve. If a lift `.w3d` failed to open on Vita (case, archive
   order, memory), the script would crash instead of skipping. A null guard
   would be a safe hardening but is a behavior change in original script
   plumbing, so none was added without evidence.
   Update 2026-10-07: the null guard is now applied as
   `port/patches/combat-a36-scriptcommands-null-guards.patch` (skips the
   command and logs via `Debug_Say` when `Peek_Animation()` is NULL; unchanged
   behavior otherwise). Source-only: not built or run.
2. The first call of each scripted lift loads a `.w3d` on demand during
   gameplay; a hitch on first use is expected.
3. M11 Sydney escort over ElevatorPhys relies on `Can_Object_Enter`,
   `Request_Elevator`, `Can_Object_Exit` and the `CheckTimer` cadence; the
   0.5 s evaluation and 1 s call timer are sim-time and frame-rate independent.
   The existing note in `M11_READINESS.md` stands: a stall there is the most
   likely physical failure and would come from pathfind data, not timing.
4. `Can_Object_Enter` indexes `CallZones[STATE_DOWN]` and `CallZones[STATE_UP]`
   with state constants (0 and 2), which coincide with
   `ZONE_LOWER_CALL`/`ZONE_UPPER_CALL`. This is an original quirk that works
   by coincidence; left alone.
5. The visual intrusion in M00 lifts (`DEV111_ELEVATOR_RENDERING_FOLLOWUP.md`)
   remains open and is independent of this timing and collision review.

## 7. Suggested physical test route (hardware only)

1. M00: ride each lift up and down twice, including a manual call from the
   upper floor; confirm door open/close sounds and no stall.
2. M09: from a fresh load, enter each scripted lift zone; confirm each
   `Static_Anim_Phys_Goto_*` call moves the car (log should show no "cannot
   find animation" lines), escort Mobius through the lifts, and confirm the car
   carries the player down and up without dropping them.
3. M11: ride WAR_ELEV01 and the two L11_ELVMUT cars; let Sydney use them;
   watch the missile lifts after the nuke objective.
4. Repeat one lift ride during a deliberately heavy scene or a slow load frame
   to cover the 200 ms clamp, and once after a save made mid-ride.
5. Pull the log: check frame real vs sim seconds (`a31_gameplay_boundary.cpp`
   telemetry) around each ride, and confirm the clock still advances after the
   `timeGetTime` change.
