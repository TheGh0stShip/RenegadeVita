# Cinematic scheduling at Vita frame rates

Status: source review plus host tests. Host evidence only: nothing was built for ARM, and nothing ran in Vita3K or on a Vita. Visual, audio and camera acceptance stay physical-only gates.

## Question

At 15–30 fps, with loading or first-spawn frames of 200–600 ms, does `Test_Cinematic` meet each of these?

- Executes every authored command and `Send_Custom` exactly once, in order.
- Fires the commands in the final batch: X0Z_Finale frame 440 `Send_Custom 1500017,445009,1`, x8a_midtro frame 1940 `Send_Custom 100002,8047`, X11N frame 494, and the x6b/x6c `6027` relocate customs at frames 2380/494.
- Keeps `Send_Custom` timing and camera animations in sync when `TimeManager` clamps a frame.
- Behaves correctly across pause and suspend.

**Answer: yes.** No low-fps scheduling defect was found, so no source change was made. The staged dispatch is the original code. The only differences from upstream are Vita trace/diagnostic logging, member initializers, the destructor, and the save/load bounds; dispatch-loop semantics are unchanged.

## What runs each frame (original order, unchanged by the port)

1. `TimeManager::Update_Frame_Time` (`staging/combat/timemgr.cpp`, identical to upstream):
   - `FrameTicks = min(real_ms, 1000/SLOWEST_FPS = 200)`.
   - `FrameTicks = 0` when `Is_Game_Paused` or in snapshot mode, then `TimeScale` is applied.
   - `WW3D::Sync(+FrameTicks)`.
   - The Vita `timeGetTime` is `CLOCK_MONOTONIC`, so the step cannot be negative.
2. `CombatManager::Think`: `SyncTime += (int)(FrameSeconds*1000+0.5)`. This is the same clamped ticks, so `Get_Sync_Time()` is simulation time, not wall time.
3. `GameObjManager::Think`, then `COMBAT_SCENE->Update(FrameSeconds)`. Cinematic `DynamicAnimPhys` and `AnimControl` animations advance here, by the same clamped `FrameSeconds`.
4. `GameObjManager::Post_Think` runs `ScriptableGameObj` observer timers:
   - The list is walked in reverse; each timer does `RemainingTime -= FrameSeconds`.
   - An expired timer calls `Test_Cinematic::Timer_Expired`, which calls `Parse_Commands`.
   - A timer started inside the callback is appended and is not visited until the next frame.
5. In host-model camera mode, the camera updates after `Post_Think`.

`Parse_Commands`:

- Advances `Time` by the whole `Get_Sync_Time` delta since the last callback.
- Runs `while (head->Time <= Time)` in list order. The list is sorted at load, and equal times keep authored order.
- For each line it sets `FrameSync = (Time - line.Time)*30` before dispatch, then removes the head.
- After the loop it either re-arms one timer for `next - Time` (always > 0) or destroys the controller.

So a long frame runs the whole due batch in one callback. The controller is only destroyed after that loop, in the same callback that consumed the last authored line. A final-frame `Send_Custom` cannot be skipped by animation end or looping, because dispatch never consults animation state. Lines at 1000000 (809 records, all `Destroy_Object`) are the primary-killed tail and correctly never run on the normal path.

## Clamp: is the cinematic slower than the animation it drives?

No. The cinematic clock (`SyncTime`), the observer timers, the physics and animation step, and `WW3D::Sync` all consume the same clamped `FrameTicks`. A 600 ms hitch therefore advances all of them by 200 ms. Camera bones, `Play_Animation` and `Send_Custom` stay mutually in sync.

A late line starts its animation at `FrameSync` frames of overshoot. That animation is first stepped in the next frame's scene update, which is the same delta the cinematic clock receives. The animation frame therefore equals `30*(cinematic time - line time)` from then on. The host test measured animation-versus-cinematic drift of at most 0.00011 frames over the 79 s x6b_midtro.

What does drift is wall-clock content: Play_Audio 2D/3D sounds, streamed music and dialogue. Every frame longer than 200 ms puts all simulation clocks behind real time by `real - 200` ms. Audio that started earlier therefore runs ahead of the camera and animations by the accumulated deficit. This is original PC behaviour. It matches `reports/SLOWDOWN_TIMING_EFFECTS.md` and is cosmetic: no cue is cut or skipped. At steady 15 fps (67 ms) nothing is clamped.

`reports/SLOWDOWN_TIMING_EFFECTS.md` still describes the removed 4 ms per-callback budget yield. That text is stale: `scripts-a35-cinematic-original-dispatch.patch` restored original dispatch.

## Pause and suspend

**EVA/pause menu** (`Run_Original_Gameplay_Pause_Menu`):

- Combat is `Suspend()`ed and `CombatManager::Think` does not run.
- `SyncTime`, cinematic timers and scene animation steps all stop together. The cinematic resumes exactly where it was, with no burst and no skipped line.
- `TimeManager::Update` keeps advancing `WW3D::Sync` during the menu. As on PC, render-object-managed animations keep running while paused: `Play_Animation` with a sub-object name sets the animation directly on the sub render object. Sounds are not paused by the original either.

**System suspend/resume:**

- The first frame after resume is one clamped 200 ms step for every clock.
- The power callback then routes to the same original EVA pause owner.
- Order and exactly-once execution are preserved. The host profile includes a 30 s gap.

**`Is_Game_Paused`:** `FrameTicks = 0` freezes every clock. The host test covers 60 such frames.

## Host evidence

`tools/host_cinematic_low_fps_test.cpp` and `tools/test_cinematic_low_fps.py` (ASan/UBSan, host only) compile the real staged `Test_Cinematic`. They exercise `Created`, `Load_Control_File`, `Timer_Expired`, `Custom`, `Parse_Commands` and all 18 handlers through the frame model above.

Each control file runs under these profiles, with creation either before or after the controller's own `Post_Think` in its first frame:

- a 1 ms reference;
- 30, 20 and 15 fps;
- a clamp-heavy 600/200/201/199/450 ms pattern;
- seeded 15–30 fps jitter with 200–600 ms spikes, including the first three frames;
- 15 fps with a 90-frame pause menu, a 30 s suspend gap and a 60-frame `Is_Game_Paused` window.

Each run must meet all of these:

- Consumes every authored line exactly once, in sorted authored order.
- Never runs a line before its time, and runs it at most one frame after the frame where it became due.
- Produces the reference's exact effect sequence: each create, model, animation, sound, camera, `Send_Custom`, attach and screen effect, with its arguments.
- Has `FrameSync` equal to the overshoot, and animation drift below 0.05 frames.
- Destroys the controller in the callback that consumed the final authored line.

Synthetic cases:

- A line every frame for 500 frames, with authored-out-of-order ties.
- A frame-440 final batch: `Send_Custom` plus destroys plus camera release.
- A time-0-only file.
- A re-entrant primary kill.

Retail: every `.txt` member of M01–M11, M13, `always.dat` and `Always2.dat` under the unchanged Vita3K Data tree. That is 425 members, streamed only to the local binary, with nothing copied.

- Run: `python3 -m unittest tools.test_cinematic_low_fps`. It took 113 s with 8 parallel streams. The retail part is skipped when the Data tree is absent.
- Result: 425/425 members and all 4 synthetic cases pass, with 0 failures.
- Vita-profile worst cases: lateness 199.3 ms, animation drift 0.00011 frames, `FrameSync` error 0.

Key members, worst case across all Vita profiles:

| Member | Lines | Final authored time | Worst lateness | Animation drift |
| --- | --- | --- | --- | --- |
| M13 x0z_finale | 73 | 14.667 s (frame 440) | 119 ms | 0.00002 frames |
| M08 x8a_midtro | 92 | 64.833 s (custom at frame 1940) | 197 ms | 0.00009 frames |
| M11 x11n_midtro | 35 | 16.500 s (custom at frame 494) | 188 ms | 0.00002 frames |
| M06 x6b_midtro | 144 | 79.400 s (custom at frame 2380) | 197 ms | 0.00011 frames |
| M06 x6c_midtro | 76 | 16.533 s (custom at frame 494) | 199 ms | 0.00002 frames |
| M13 x00_intro | 250 | 75.000 s | 195 ms | 0.00011 frames |

Lateness is always at most one clamped frame of 200 ms, and `FrameSync` absorbs it for animations.

## Findings that are original behaviour (documented, not changed)

1. **Float32 boundary hold.**
   - A line whose authored time is exactly a whole millisecond (frame multiples of 3: 0.1 s, 2.4 s, ...) can run one frame after it became due.
   - Cause: float `Time` accumulation lands an ulp below the float line time.
   - At 15 fps that is 67 ms, and at most one clamped frame.
   - Animations are compensated by `FrameSync`. Non-animated commands (`Send_Custom`, camera cut, fades, sounds) start one frame later.
   - It is the same on PC, but the absolute delay scales with frame time. Adding an epsilon would change original semantics, so it is not patched.
2. **Timer countdown rounding is worst at high fps, not low.**
   - Observer timers subtract `FrameSeconds` in float32. Over long gaps at 1 ms frames this holds lines by up to 33 ms in retail drop/flyover files.
   - At Vita frame rates there are 30–200x fewer subtractions, and every line stays within one frame.
3. **Re-entrant primary kill.**
   - Trigger: a command whose synchronous callee kills the primary, so that `Test_Cinematic_Primary_Killed` sends a 0-delay custom.
   - Effect: `Parse_Commands` re-enters from `Custom`. The inner call frees the executing head, runs only the >999000 tail, then destroys. The outer loop then sees an empty list.
   - Host test: no line runs twice, and `Destroy_Object` is called twice, which is harmless `Set_Delete_Pending`.
   - Port note: the Vita-only slow-command log in `Parse_Command` prints `vita_original_command` after the command returns. In this nested case, and only when that command took at least 100 ms, it reads freed text.
   - Reachability from retail data is unproven. **Fixed anyway**: `scripts-a38-cinematic-slow-command-text-copy.patch` copies the command into a 161-byte buffer before dispatch (`reports/SUSPEND_RESUME_TIMING.md`).
4. **Animation wrap and overshoot** (wwphys/combat, original).
   - `ANIMATE_TARGET` with `FrameSync` beyond the end frame snaps back to the end within a frame.
   - `ANIMATE_LOOP` and `ANIM_MODE_LOOP` subtract the loop length once per step. A loop shorter than one frame step (at most 6 frames at the clamp) can leave the frame past the loop end.
   - Retail loop lengths were not measured, so this remains a review lead.
5. **Camera cut pose** (unverified lead).
   - `Internal_Set_Animation` applies the new animation at the old `CurFrame` before `Set_Current_Frame(FrameSync)`.
   - The host-model camera updates after `Post_Think`, so a cut may show one frame of the start pose. That frame lasts 67–200 ms on Vita.
   - Needs physical capture to confirm.

## Remaining gates

- Physical Vita confirmation of camera cut timing.
- Audio-versus-animation drift after real hitches, using `Frame_Seconds` against `Frame_Real_Seconds` telemetry.
- Pause during an active camera cinematic.
