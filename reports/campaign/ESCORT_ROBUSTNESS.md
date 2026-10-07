# Escort robustness: elevator entry timeout and arrival checks (2026-10-07)

Evidence class: source change plus static review. The patch passed
`arm-vita-eabi-g++ -fsyntax-only` (candidate compile flags with
`-Wall`; `pathaction.cpp`, `action.cpp` and `transition.cpp` all exit 0, and the
new code adds no warnings). `bash tools/stage_sources.sh` exits 0 with zero
fuzz and 544 ordered patches, and the related host tests pass (27/27). Nothing
was built, packaged or run on Vita3K or hardware. Nothing here shows that an
escort completes on hardware.

Follows `ESCORT_PATHING_REVIEW.md` risk 5 and `ELEVATORS.md`.

## 1. Change: AI elevator ENTERING timeout

Patch: `port/patches/combat-a37-pathaction-elevator-entry-timeout.patch`. It is
registered last in `tools/stage_sources.sh`, with sha256 anchors on
`pathaction.{h,cpp}` before and after it.

| Location (staged) | Change |
|---|---|
| `staging/combat/pathaction.h:142-144` | private `Vita_Elevator_Entry_Timed_Out (ElevatorPhysClass *)` |
| `staging/combat/pathaction.h:192-195` | members `VitaEntrySeconds`, `VitaEntryLogMask` |
| `staging/combat/pathaction.cpp:46-58` | `colmath.h`, `a30_vita_runtime.h` (only on Vita and outside the M00 demo), `VITA_ELEVATOR_ENTRY_TIMEOUT = 5.0F` |
| `staging/combat/pathaction.cpp:111-114` | constructor zeroes both members |
| `staging/combat/pathaction.cpp:362-365` | the WAITING to ENTERING transition resets both members |
| `staging/combat/pathaction.cpp:414-418` | `else if (Has_Arrived () \|\| Vita_Elevator_Entry_Timed_Out (elevator))` |
| `staging/combat/pathaction.cpp:594-657` | the helper |
| `staging/combat/pathaction.cpp:724-730` | `Load_Variables` resets both members; the save format is unchanged |

All of it is inside `#if defined(RENEGADE_VITA_PORT)`. The `#else` branch
keeps the original condition word for word.

### Behaviour

- The helper runs only when the original code would test arrival and fail:
  the elevator is at rest (`Is_Moving()==false`) and the rider is not within
  0.15 m of the inside point. `||` short-circuits, so a rider that arrives
  normally never reaches the helper on that frame.
- It adds `TimeManager::Get_Frame_Seconds()` to an accumulator, so it measures
  simulation time: pause adds 0, and one frame adds at most 0.2 s. This matches
  the original EXITING and door timers.
- Before 5 s the helper returns false, so the original behaviour is unchanged.
- At or after 5 s it returns true only if the rider's position is INSIDE the
  inside-zone OBB for the elevator's current floor
  (`CollisionMath::Overlap_Test(zone_box, pos) == INSIDE`).
  `ElevatorPhysClass::Triggered` uses this same test to send the lift for a
  player standing in the car (`elevator.cpp` ~653). The caller then runs the
  original "arrived" branch: face `FacePos`, `State = STATE_WAITING`, and
  `Request_Elevator(GameObj)`.
- `Request_Elevator` only sets trigger bits for zones the rider's model box
  intersects, and the lift leaves `STATE_DOWN`/`STATE_UP` only for the inside
  zone or the opposite call zone (`elevator.cpp` Update_State). A rider standing
  inside the zone therefore sends the lift through the original 0.5 s check
  and 1 s call timer. No new path can move a lift.
- If the rider is outside the zone after 5 s (for example blocked in the
  doorway), the helper returns false and the original steering continues. It
  rechecks every frame, so a rider that drifts into the zone triggers then.
- A save made during ENTERING reloads with a fresh 5 s window, because the
  members are not saved and `Load_Variables` resets them.

### Breadcrumb

`A4 elevator entry timeout v1: obj=<id> def=<name> elevator=<phys id> floor=<0|1> entry_seconds=<s> dist=<m> inside=<0|1> action=<request_elevator|keep_steering>`

This is written through `A30_Vita_Log`, only on Vita and outside the M00 demo.
Each entry episode writes at most one record per outcome (expired while
outside, fired while inside), with a cap of 32 records per run.

### Scope: which escorts use this path

- **M11 Sydney**: yes. Her passenger lifts are ElevatorPhys objects
  (`WAR_ELEV01`, `L11_ELVMUT` x2), so her route goes through
  `PathActionClass::Handle_Elevator`.
- **M09 Mobius**: no. M09 has no ElevatorPhys objects (`ELEVATORS.md` §2). Its
  lifts are StaticAnimPhys objects driven by the `M09_Elevator_*` scripts
  (`Mission09.cpp:3254-3520`). `ESCORT_PATHING_REVIEW.md` risk 5 says M09
  depends on the ENTERING state; that statement is wrong. On M09 Mobius rides
  scripted lifts as an ordinary carrier rider, and the risk there is whether
  the scripts admit him by zone. This patch does not touch that path.
- Every other AI that pathfinds through an ElevatorPhys lift in M00-M04, M07,
  M08 or M10 gets the same fallback.

## 2. Review: frame-rate dependence of other arrival checks

| Primitive | Arrival test | Frame-rate dependent? | Action |
|---|---|---|---|
| Soldier `Move_To_Absolute` (Goto, Follow, waypaths, PathAction legs) `action.cpp:656-750` | `remaining_path + range <= MoveArrivedDistance` (0.05 m for PathAction legs) | **No.** `Clamped_Units` (`action.cpp:611-621`) divides the offset by `Get_Max_Speed()*speed*dt`. `Get_Max_Speed()` is the physics `NormSpeed` (`soldier.cpp:1730`), and `Phys3`/`HumanPhys` set velocity to `NormSpeed*move` with no acceleration (`phys3.cpp:1360-1366`). Inside one frame's reach the step is therefore offset × (walk/crouch factor ≤ 1), whatever dt is: a deadbeat controller that cannot overshoot because of a long frame. The only error that grows with dt is the heading change during the frame. It is bounded by the bearing gate (moves only when bearing < 40° or facing is done), so each step contracts the distance by at least 2·sin(20°) ≈ 0.68. | none |
| Follow (`MoveFollow`) `action.cpp` Update_Move_Location | re-path when target moved > 2 m and ratio > 0.1 | No (positions, not time). Arrival keeps the action running. | none |
| PathAction door states | 0.15 m or 5 s timer | No; already time-bounded. | none |
| PathAction elevator EXITING | 0.15 m or 5 s timer | No; already time-bounded. | none |
| PathAction elevator ENTERING | 0.15 m, no timer | No for step size (see the first row). It could still stall forever if the point is unreachable: the player or another body standing at the zone centre, or car or door geometry in the way. | **fixed above** |
| PathAction ladder CLIMBING | \|ΔZ\| < 0.25 m window; sign-only climb command | Theoretically. Climb speed is `0.3 × NormSpeed`-scaled analog (`soldier.cpp:1853-1874`). The 0.5 m window would need more than about 2.5 m/s of vertical speed at the 5 FPS clamp; a soldier's climb speed is far below that. LADDER WAITING and GETTING_ON have no timer, but both wait on occupancy or input, not on arrival. | none; residual |
| Jump | landing state | No (`wwphys-a35-human-jump-finite`). | none |
| VehicleDriver `vehicledriver.cpp:340-348,555-563` | `dist <= m_ArrivedDist` (default 1.0) | Weakly. Braking aims for about 0.5 m/s at the goal, so one frame at the 5 FPS clamp moves about 0.1 m. Overshoot needs an arrive distance under roughly 0.2 m on a vehicle. | none; residual |
| Script arrive distances (`staging/scripts`) | 0.0 to 30 m | 11 sites use 0.0, 2 use 0.05, 6 use 0.1 (M01, M03, M09:1778, M10:1399-1458, MissionX0). With the deadbeat soldier controller, whether these complete does not depend on frame rate; a 0.0 radius is original behaviour, such as an attack-move that is never meant to "arrive". | none |

`Innate` enable/disable and `Modify_Action` only change parameters
(`action.cpp:2025-2047`). They contain no time-based arrival logic.

## 3. Residual risk

1. A rider that cannot get its position inside the inside zone (stuck in the
   doorway or behind the closed car door) still stalls in ENTERING, exactly as
   upstream does. The breadcrumb records `inside=0 action=keep_steering` once,
   which identifies the case on hardware.
2. After the fallback the rider stands wherever it stopped inside the zone,
   not at the zone centre. When the lift moves, the rider is carried only if it
   is grounded on the car (`Link_To_Carrier`). A rider standing on the
   threshold could be pushed, or could revert the lift
   (`Revert_Animation_State`). The point-inside test makes this less likely than
   a box-overlap test would, but it is not proven on hardware. Zone sizes were
   not extracted from the definitions database.
3. While the timer has not expired, the rider holds the lift
   (`CurrentAIRider`). A player who rides it away triggers the original
   RIDING/EXITING sequence for an AI that is not on board. This is unchanged.
4. The pre-existing risk 6 of `ESCORT_PATHING_REVIEW.md` remains (spline
   look-ahead tuned for 30 FPS).
5. Required evidence: a physical M11 run through Sydney's lift legs, then grep
   the log for `A4 elevator entry timeout`. No record means the fallback never
   fired. `inside=1` means it fired. Only the physical result can confirm that
   the lift carried her.
