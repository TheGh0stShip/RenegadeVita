# AI path following at low frame rates (2026-10-07)

Evidence class: static source review plus a host simulation of the original
math. Nothing was built, packaged or run on Vita3K or hardware. This report
follows up `ESCORT_PATHING_REVIEW.md` risk 6 ("spline look-ahead tuned for
30 FPS", `Path.cpp:103`).

Simulation: `tools/sim_path_follow_low_fps.py` (pure Python, about 3.5 min;
`--json` for machine output). It is transcribed from the staged originals:

- `Path.cpp`: `Initialize_Human_Spline` and `Initialize_Spline`
  (`:1151`, `:1399-1404`), and `Evaluate_Next_Point` (`:611-760`).
- `cardinalspline.cpp`: `Update_Tangents`.
- `hermitespline.cpp`: `Evaluate`.
- `action.cpp`: `Traverse_Path`, `Move_To_Absolute`,
  `Human_Move_To_Relative` and `Clamped_Units` (`:611-750`, `:1227-1290`).
- `soldier.cpp`: the AI turn limit in `Set_Targeting` (`:3362-3391`).
- `phys3.cpp`: `User_Move` (`:1357-1369`).
- `timemgr.cpp`: the 0.2 s clamp.

Collision is not modelled. The script measures the commanded trajectory
against wall points with a 0.3 m body radius.

## How the original follower works

- **The carrot moves by distance, not by time.** `Evaluate_Next_Point` moves
  the target ("carrot") forward by one fixed spline step, and only when the
  actor is within `m_LookAheadDist + m_MovementRadius` of the carrot. It moves
  at most one step per call, and `Traverse_Path` calls it once per frame
  (`SmartGameObj::Generate_Control` → `Action.Act`). `dt` plays no part in
  the advance decision.
- **Human constants.** One step is `8 / approx_frames` of spline time, which
  is about 0.667 m of spline distance. The gate is 0.333 m + 0.1 m. Both are
  fixed when the path is built, from `ASSUMED_FPS = 30` and 2.5 m/s.
- **The steering cannot overshoot.** `Clamped_Units` divides the offset by
  `NormSpeed*MoveSpeed*dt`. `Set_Targeting` applies the new heading
  immediately (`Phys3Class::Set_Heading`), and `User_Move` rotates the move
  vector by that same heading. So the actor moves either exactly onto the
  carrot or by `V*dt` toward it. A long frame cannot carry it past the
  carrot, and its heading cannot skew the step.

## Results (V = NormSpeed × MoveSpeed in m/s; the 10 m/s case equals `DEFAULT_NORMALIZED_SPEED`)

| scenario | V | 60 fps | 30 fps | 15 fps | 15 jitter (50/100 ms) | 10 fps | 5 fps |
|---|---|---|---|---|---|---|---|
| tight 90° corner: slowdown | 6 | 1.02 | 1.03 | 1.07 | 1.12 | 1.10 | 1.90 |
| tight 90° corner: slowdown | 10 | 1.03 | 1.06 | 1.11 | 1.17 | 1.58 | 3.17 |
| tight corner: max deviation from spline (m) | 6 | 0.117 | 0.118 | 0.103 | 0.070 | 0.111 | 0.028 |
| tight corner: inner-corner clearance (m; spline itself 1.114) | 6 | 1.001 | 1.001 | 1.033 | 1.046 | 1.009 | 1.092 |
| 1.2 m doorway S-bend: slowdown | 6 | 0.99 | 1.00 | 1.04 | 1.02 | 1.08 | 1.92 |
| doorway: jamb clearance (m; spline itself 0.247) | 6 | 0.240 | 0.243 | 0.260 | 0.269 | 0.271 | 0.278 |
| doorway: max deviation (m) | 10 | 0.104 | 0.103 | 0.104 | 0.104 | 0.055 | 0.055 |
| elevator approach (tightened action node): slowdown | 6 | 0.99 | 1.02 | 1.05 | 1.15 | 1.09 | 1.96 |
| elevator: actor-to-node distance when the action fires (m) | 6 | 0.239 | 0.140 | 0.036 | 0.112 | 0.088 | 0.135 |
| elevator: jamb clearance (m; spline itself 0.450) | 6 | 0.457 | 0.467 | 0.494 | 0.469 | 0.486 | 0.446 |

Slowdown is completion time divided by `spline length / V`. Values just
below 1.00 are the end-of-path arrival radius (0.5 m).

The following hold for all 54 profile runs, covering 3 scenarios, V of 3, 6
and 10, and the 6 frame-time profiles:

- Every run completed.
- No run backtracked. A backtrack is a move with a negative dot product
  against the previous move.
- The sequence of carrot spline times visited was **identical** in every
  run. Action nodes (ladder, door, elevator) therefore fire at the same spline
  point at every frame rate, and the follower cannot skip a waypoint or a
  corner.

**Single 200 ms frame:** the sweep inserts one 200 ms frame at every frame
index of a 30 fps run, for each scenario and speed. Worst-case results:

- Maximum deviation rises by at most +0.045 m (tight corner at V = 10,
  0.067 → 0.112).
- Clearance falls by at most 0.046 m against the 30 fps run (elevator jamb at
  V = 10, 0.492 → 0.446). No spike run is more than 0.011 m below the 60 fps
  run of the same case.
- The run takes at most 0.067 s longer than the base run plus the extra
  frame time.
- Every run completes.

The lead between the actor and the carrot (up to about 1.1 m) absorbs the
long frame.

## Findings

1. **No geometric defect at low frame rates.** A long frame cannot skip a
   waypoint or corner, cannot cut through geometry, and cannot oscillate. At
   low fps the actor stops exactly on each carrot, which lies on the
   portal-clipped spline. As a result, deviation falls as fps falls (5 fps
   corner deviation is 0.028 m against 0.117 m at 60 fps), and clearance is
   never more than 0.011 m below the 60 fps run. The clearance figures assume
   no collision, as in all runs.
2. **There is one frame-rate-dependent effect: a throughput cap.** Path speed
   is limited to one 0.667 m step per frame: 40 m/s at 60 fps, 20 at 30, 10
   at 15, 6.7 at 10 and 3.3 at 5. A run is slowed only when
   `V > 0.667 × fps`.
   - At a steady 15 fps the slowdown is at most 7 % for V ≤ 6 m/s and at most
     15 % for V = 10.
   - At 10 fps it is at most 1.10× for V = 6 but 1.6–1.7× for V = 10.
   - At 5 fps it is 1.9–2.0× for V = 6 and 3.1–3.2× for V = 10.

   The effect makes the escort slower. It does not stall: every run
   completed. Upstream PC has the same behaviour at the same frame rates.
3. **The steering is independent of frame rate within a frame.** The
   deadbeat clamp, the immediate heading update and the 40° bearing gate
   (`gated` is 0–3 frames per run, highest at 60 fps) give no frame-rate
   dependent overshoot or heading skew.
4. **Vehicles (analytical only, not simulated).**
   - **Constants:** each step is `LookAheadTime/5`, about 2.13 m of spline
     distance. The carrot snaps to `VehicleCurveClass` arc in and out points,
     and `m_SplineTime` is set to `Get_Last_Eval_Time`
     (`vehiclecurve.cpp:449-575`, `Path.cpp:755`). The gate is 5.33 m + 0.1 m.
   - **No frame-rate dependence in the carrot:** the advance is still gated
     by position and limited to one step per frame, so the carrot sequence is
     the same at every frame rate.
   - **Overrun bound:** a vehicle passes a carrot that has not advanced only
     if it covers more than 5.43 m in one frame. At the 5 fps clamp that
     needs more than about 27 m/s (98 km/h); at 15 fps it needs more than
     81 m/s.
   - **Not covered:** the low-fps response of `VehicleDriverClass::Drive_*`
     (proportional steering and speed control) depends on the vehicle
     physics. This simulation does not cover it, so it remains a residual
     risk for convoys.

## Fix decision: no code change

I tested the smallest candidate fix: when `dt > 1/30`, take up to
`ceil(dt*30)` carrot steps that the actor can reach this frame. It is inert at
30 fps or faster. Speed recovers (5 fps slowdown 1.2–1.45× instead of
1.9–3.2×), but geometry gets worse:

- Corner deviation at 5 fps rises from 0.028 m to 0.26 m.
- Inner-corner clearance falls from 1.09 m to 0.89 m.
- Doorway clearance at 10 fps falls from 0.271 m to 0.225 m.
- Elevator-approach deviation rises to 0.435 m.

The fix would trade the original follower's protection against clipping for
speed. That speed only matters below about 10 fps, which is outside the
supported frame-rate target. It would also change original AI semantics. No
patch was added.

Related guards that already exist:

- the 5 fps `TimeManager` clamp;
- the elevator ENTERING timeout (`ESCORT_ROBUSTNESS.md`);
- the M11 1 s retry and the M09 FOLLOW retry.

These cover the stall cases that a slower escort could otherwise expose.

## Residual risk and hardware check

- Soldier `NormSpeed` values from the retail definitions database were not
  extracted. The sweep (3, 6 and 10 m/s) brackets them. At a steady 15 fps
  only V > 10 m/s would be capped.
- Escort segments that run below about 10 fps will be visibly slower. Scripts
  that race an escort against a timer could then fire their timeout branch
  earlier, relative to escort progress, than on PC at 30 fps. Check
  frame-stage telemetry (`real_us` / `simulated_us`,
  `a31_gameplay_boundary.cpp:839-848`) on the M09 and M11 escort legs. If
  FPS stays at or above 15, the cap costs at most about 15 %, even at
  10 m/s.
- Vehicle-driver dynamics at low fps (convoys) are not covered here.
