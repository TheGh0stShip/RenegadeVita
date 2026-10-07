# Escort pathing review (M09 Mobius, M11 Sydney)

Static review only: no build, no Vita run, upstream untouched. The staged
sources (`staging/`, which are the patched copies) were compared file by file
with `upstream/CnC_Renegade/Code` (CRLF-normalised diff). Evidence class:
source inspection. None of this is a runtime or hardware result.

## Scope covered

wwphys: `pathmgr`, `pathsolve`, `Path`, `Pathfind`, `PathfindPortal`,
`PathfindSector`, `waypath`, `waypoint`, `humanphys`, `phys3`, `movephys`,
`staticanimphys`, `animcollisionmanager`, `accessiblephys`, `physcon`.
Combat: `action`, `pathaction`, `elevator`, `doors`, `smartgameobj`,
`soldier`, `humanstate`, `transition*`, `timemgr` (no changes).
Frame driver: `port/platform/a31_gameplay_boundary.cpp`.
Scripts: the only M09 script patches are camera bounds and the keycard Mobius
re-fetch. No M11 script patch exists.

All files not listed under Findings differ from upstream only in save/load
status propagation, 32-bit pointer tokens, for-scope or include-case fixes,
TT network-client paths (`Import_*`, gated on TT replication), or logging.
None of these changes affect single-player movement.

## Verdict

No clear port-introduced defect was found that would stall an escort, so no
code was changed. Four port patches change behaviour on the escort path. All
four fail toward progress, not toward a stall. The real stall exposure comes
from upstream code running at Vita frame rates (risks 5 and 6).

## Port-introduced behaviour changes

1. **Path solve timeslice early break** (low risk).
   `staging/wwphys/pathmgr.cpp:369-374`
   (`port/patches/wwphys-a36-path-timeslice-underflow.patch`).
   Upstream calculates `uint32((end_time - Get_Time())/TicksPerMilliSec)`. Once
   the 5 ms budget (`pathmgr.h:80`) is overrun by at least 1 ms, that value
   wraps to about 4e9 ms and the solver runs unbounded. The port breaks instead
   and keeps `ActivePath` for the next frame. The solver cannot starve: an
   activated path always gets `Timestep` on the next frame, and
   `PathSolveClass::Resolve_Path` is a do-while, so it processes at least one
   node per call (`pathsolve.cpp:346-392`). Effect: up to one frame of extra
   latency per overrun. The budget is wall-clock, not frame-based. At low FPS a
   solve therefore takes more frames, but the same wall time. Queue age
   priority (`pathmgr.cpp` Activate_New_Priority_Path, `+1 per 5 s`) and
   distance-to-camera priority favour an escort near the player.
   Timer source: `win32_compat.h:507-528` (QPC on CLOCK_MONOTONIC, ns). If
   `clock_gettime` failed, the counter would stay at 0 and solves would run
   unbounded (a hitch, not a stall).
   Mitigation: none needed. Verify with the existing `path_us` stage counter
   (`a31_gameplay_boundary.cpp:839`): a sustained average near 5000 µs/frame
   during M09/M11 escorts means the solve queue is saturated.

2. **Zero-length path early-out** (low risk).
   `staging/wwphys/Path.cpp:624-637` (`wwphys-a35-zero-length-path.patch`).
   When `m_TotalDist <= WWMATH_EPSILON`, upstream divides 0/0 in
   `Initialize_Human_Spline` (`Path.cpp:1174`) and `approx_frames`
   (`Path.cpp:1402`), giving a NaN or Inf target. The port instead snaps the
   target to `m_DestPos` and steps through any pending action, one per call,
   before setting `STATE_PATH_COMPLETE`. This can only trigger when every node
   coincides. It cannot trigger on an elevator, door or ladder route, because
   those include different entrance and exit node positions
   (`Path.cpp:250-300`), or on a normal looping patrol. It can trigger on a
   single-point waypath (`start_pt == end_pt`) or a Goto to the actor's
   current position. In those cases the path now reports complete, where
   upstream returned NaN. Mitigation: none.

3. **Play_Animation stall watchdog** (low stall risk, moderate semantic change).
   `staging/combat/action.cpp:458-488` (`a35-dev190-staging-preserve.patch`,
   then `combat-a36-action-stall-logical-time.patch`). If a non-looping
   animation's frame stops advancing for 5 s of game time (cinematic freeze
   excluded, pause gives 0 s), it is forced to `ACTION_COMPLETE_NORMAL`.
   Upstream would wait indefinitely. The watchdog resolves stalls; it cannot
   cause one. The M11 pass requires Sydney's switch animation to complete, and
   the watchdog guarantees that it eventually does.
   Residual risk: a script could receive the completion of an animation that
   is visually unfinished, for example an animation that is not updated while
   its actor is culled. Mitigation: grep hardware logs for
   `A4 animation action forced complete` with the Mobius (2000010) or Sydney
   object IDs. Any hit is a separate animation-update bug and should be fixed
   at its source, not by changing the threshold.

4. **AI jump finite guard** (low risk).
   `staging/wwphys/humanphys.cpp:626-631,695`
   (`wwphys-a35-human-jump-finite.patch`). A zero-displacement or no-solution
   jump returns early instead of setting a NaN velocity. The consumer
   `PathActionClass::Handle_Jump` (`pathaction.cpp:308-313`) then sees
   `Has_Just_Jumped()==false` and `UPRIGHT`, so it finishes immediately and
   the path continues. No stall.
   Residual risk: an over-high jump target leaves the actor below the ledge and
   walking into it. Upstream would have produced a NaN velocity in that case.

## Port-introduced save/load-only changes (affect mid-escort reloads only)

- `pathaction.cpp:664,671` (`combat-a35-pathaction-borrowed-remap.patch`):
  `Mechanism` and `Path` are borrowed pointers. They are assigned at
  `pathaction.cpp:129-130`, cleared at 753, and never released. Remapping
  them without adding a ref is correct, and removes an upstream reference
  leak.
- `pathsolve.cpp:1877-1987` and `pathmgr.cpp:300-318`
  (`wwphys-a36-physics-path-load-admission.patch`): an in-flight path solve
  must now contain all 7 micro-chunks at exact sizes, or it is dropped and the
  load reports failure. The port's own `Save` always writes all 7, so only a
  corrupt save is rejected. The result is a rejected load, not a frozen
  escort.
- `elevator.cpp:192-241` and `doors.cpp:144-188`: definition loads now
  propagate parent failures. If the original definition admission ever
  rejected an elevator or door definition, `Find_Static_Object` would return
  NULL at `action.cpp:1335-1337`. No `PathAction` would be set up, and the
  actor would walk the spline into the shaft. Mitigation: check the
  definition-rejection breadcrumbs from the M09 and M11 level loads. There is
  no evidence that this happens.
- `scripts-a36-m09-keycard-mobius-refetch.patch` (`Mission09.cpp:4417`):
  refreshes the unsaved `mobius` pointer by ID. This is behaviour-identical
  while the pointer is valid.

## Upstream behaviour exposed by Vita frame rate (not port-introduced)

5. **Elevator ENTERING has no timeout** (medium risk at low FPS).
   `pathaction.cpp:385-405`. After the elevator admits the rider, the actor
   must reach the inside-zone point within 0.15 m horizontally (`Has_Arrived`,
   `pathaction.cpp:525`) before `Request_Elevator` runs. EXITING has a 5 s
   timer (`pathaction.cpp:409-420`); ENTERING does not. The steering in
   `Move_To_Absolute` (`action.cpp:656-750`, `ignore_arrived_dist` = 0.05 m)
   moves about `speed * dt` per frame. At the 5 FPS game-time clamp
   (`timemgr.cpp:71`) or sustained low FPS, an escort can orbit the 0.3 m
   window and never request the lift. Both M09 (`M09_Elevator_All_Controller`)
   and M11 (Sydney's four `GOING_TO_ELEVATOR0n` legs) depend on this state.
   Proposed minimal mitigation, deferred until hardware shows it: a
   port-guarded ENTERING timer that mirrors the original EXITING `Timer`
   pattern (for example 5 s, then `Request_Elevator`). It must not be added
   without a physical repro, because it changes original AI semantics.

6. **Spline look-ahead tuned for 30 FPS** (low to medium risk).
   `Path.cpp:103` (`ASSUMED_FPS = 30`) and `Path.cpp:1401-1404`. The target
   advances one 8-frame step per evaluate. At 15 FPS the actor covers 2/30 s of
   path per frame against an 8/30 s look-ahead, so it keeps up. Below about
   8 FPS the steps become coarse, and corner and portal clipping
   (`Clip_Spline_To_Pathfind_Data`) can leave the actor rubbing walls near lab
   doors. That produces upstream `ACTION_COMPLETE_PATH_BAD_*` and retry
   behaviour (M11 `Mission11.cpp:9831-9870` retries every 1 s; M09 FOLLOW
   retry `Mission09.cpp:563`).
   Mitigation: no code change. Measure escort-segment FPS on hardware first.

## Recommended hardware checks (M09 steps 2–5, M11 steps 4–7)

1. Use frame-stage telemetry (`path_us`, `real_us`) to confirm that the solver
   budget is not saturated and that FPS stays above about 10 through the
   elevator legs.
2. Check logs for `A4 animation action forced complete` and the action
   observer-miss flight-recorder events on Mobius (2000010) and Sydney.
3. If an escort freezes beside an elevator, capture whether the elevator was
   requested. A rider that is admitted but never reaches the inside point is
   risk 5, and the ENTERING timer is the minimal fix.
