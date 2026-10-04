# Original animation clock ownership

## Physical observation and source diagnosis

During dev230 tutorial testing, the user observed a light rotating around the
power-plant smoke stack occasionally restarting before completing a cycle.
Gameplay remained usable. This observation is retained separately from the
earlier particle-table crash, which was corrected in dev230.

The native gameplay loop in `port/platform/vita/a31_vita_runtime.cpp` wrote
`WW3D::Sync` from a session-relative wall clock before calling
`A31_Interactive_Run_Simulation_Frame`. That original frame boundary calls
`TimeManager::Update`, whose original `staging/combat/timemgr.cpp` advances
the same WW3D clock by `FrameTicks`. The pause dialog also used both writers.
Original `staging/ww3d2/animobj.cpp` subtracts the previous synchronization
token from the current unsigned token and converts the result to a float.
Backward time therefore becomes a large positive animation delta. Its original
loop recovery resets the frame to zero when it remains outside the period.

For example, a40 ms frame followed by a10 ms frame changes the old effective
clock from wall+40 to wall+10, a20 ms backward movement. This is a demonstrated
wrapper defect. It is a plausible cause of the observed light restart;
specific light ownership and corrected physical behavior are not yet verified.

## Minimal boundary correction

Dev231 removes the wall-clock writes from gameplay and pause. Original
TimeManager remains the owner of frame clamping, time scale, pause ticks and
WW3D synchronization. The simulation call order, original animation method,
physics, scripts and networking remain unchanged. Preloading/validation paths
that do not run the original simulation retain their separate existing clocks.
The unused session-relative origin and pause-function argument are removed.

## Focused evidence and remaining gates

`tools/test_vita_animation_clock.py` extracts and compiles the actual original
`Compute_Current_Frame` method under ASan/UBSan. Its fixture uses explicit
32-bit clock tokens and signed32-bit LastSyncTime, matching the target boundary
instead of host LP64 arithmetic. Across4,096 irregular frames, the old two-writer
schedule produces1,536 backward events and1,536 resets. The single original
owner matches independent frame expectations and passes zero-tick/pause and
unsigned millisecond rollover checks. No original long-frame recovery is changed.

A source boundary check fails against the old wrapper and passes after the
correction. It verifies the actual gameplay and pause wrappers have no second
WW3D writer and the original TimeManager advancement remains. Both tests are
included in the canonical and fast build gates. Two focused tests pass.

Dev231 passes 499 focused host tests, five ARM compile/link actions and seven
package actions. Vita3K installation hashes match; it was not launched.
The current physical Vita
continues running dev230; it has not been replaced or relaunched for this fix.
Physical identification of the affected light, full-cycle continuity under
uneven frame costs, pause/resume, menu transitions, repeated loads and soak
remain required. A successful host or ARM check cannot establish that the
reported smoke-stack light is fixed. No PSTV result is claimed.
