# Real time across Vita suspend/resume (2026-10-07)

Scope: what `TimeManager` real frame time (`RealFrameTicks` /
`Get_Frame_Real_Seconds`), the 200 ms simulation cap, WWAudio and port timers
do across a system suspend (power button / standby) or a LiveArea round trip
(PS button), and the Vita power callback
(`a31_vita_runtime.cpp` `Power_Event_Callback` / `Consume_Power_Resume`).
Also the cinematic slow-command record read flagged in
`reports/campaign/CINEMATIC_LOW_FPS.md` finding 3.

Evidence class: static source audit, a host model (ASan/UBSan), patch
application at fuzz 0 on the committed staged files, and
`arm-vita-eabi-g++ -fsyntax-only` with the `vita-fast-candidate` compile
database. Nothing was built, linked or packaged, and nothing ran in Vita3K or
on a Vita.

## Verdict

- The engine clock is `timeGetTime` → `CLOCK_MONOTONIC` →
  `sceKernelGetProcessTimeWide` (`port/compatibility/include/mmsystem.h:31`,
  through `SysTimeClass::Get`). **Whether that clock advances while the title
  is suspended is not established.** No retained log contains an
  `A3.6 power: resume observed` line. The port now handles both outcomes, and
  a new bounded resume record measures which one hardware shows.
- Before this change, if the clock advanced, the first `TimeManager` update
  after resume had `FrameTicks` capped at 200 ms, so simulation was safe. But
  `RealFrameTicks` carried the whole suspended interval to every
  real-time consumer (table below).
- Now the first `Update_Frame_Time` after an observed resume caps the pending
  real step at the original simulated cap, 200 ms (`1000/SLOWEST_FPS`).
  Simulation stepping is unchanged. Ordinary long frames keep original
  semantics, because only the first update after a resume notification is
  touched.
- The cinematic slow-command record now copies the command text before
  dispatch. It can no longer read a control line that a re-entrant primary
  kill freed.

## Power notifications a user application can receive

The VitaSDK header (`psp2common/power.h`) gives
`SCE_POWER_CB_VALID_MASK_NON_SYSTEM = 0x00361180`. That mask has
`SYSTEM_RESUMING`, `SYSTEM_RESUME`, `APP_RESUME` (0x00200000), `0x00100000`,
`POWER_ONLINE`, `BATTERY_ONLINE` and `AFTER_SYSTEM_RESUME`. It does **not**
have `SYSTEM_SUSPEND`, `THERMAL_SUSPEND`, `LOW_BATTERY_SUSPEND` or
`APP_SUSPEND`. So the existing `suspends=` counters in the resume log are
expected to stay 0 on hardware, and a resume notification is the only usable
signal. Several flags are marked "TODO: confirm" in the SDK.
`Power_Event_Callback` now also counts `SCE_POWER_CB_APP_RESUME`. That count is
used only by the frame clock. EVA pause routing still triggers on
`SCE_POWER_CB_SYSTEM_RESUME` only, as before.

## Who reads real time

Simulated time is already capped at 200 ms per frame and needed no change.
Its consumers are script and custom timers, `CombatManager::SyncTime`,
`Test_Cinematic`, conversations, objectives, physics, `WW3D::Sync` and
`TotalSeconds`.

These consumers read `Get_Frame_Real_Seconds` and are now capped after a
resume:

| Consumer | Effect of an uncapped resume step |
| --- | --- |
| `mendozabossgameobj.cpp` (7 sites; death camera, pack explosion) | State timers expire at once and `CAMERA_STATE_WAYPATH_FOLLOW` is skipped. |
| `input.cpp:957` axis acceleration, `:800` mouse scale | Axis value jumps to its limit for one frame; mouse delta scaled toward 0. |
| `directinput.cpp:726` | One-frame input time delta spike. |
| `weaponview.cpp:634` recoil bob | Bob snaps to rest (cosmetic). |
| `gamedata.cpp:1971/1977`, `DlgMPTeamSelect.cpp:421` | Multiplayer intermission and time-limit counters lose the suspended time. |
| `ccamera.cpp:1354/1704`, `TimeManager::Update` slow-frame warning | Debug or snapshot paths only. |
| `TimeManager::AveragedFPS` | One distorted 10 s average. |

These consumers read the clock directly and were not changed:

- `AudibleSound.cpp:557/1166` tracks play position by `TIMEGETTIME` for
  handle-less (virtual or culled) sounds. If the clock advances, such a
  one-shot completes on the first update after resume. Handle-backed samples
  are paced by the Vita Miles provider's sample consumption, and
  `port/audio/vita` has no wall clock, so they resume where they stopped.
  `Threads.cpp:193/295` (delayed release) and `Sound3D.cpp:210` (velocity
  from position change) see one long interval, which is benign. This matches
  PC behaviour after a sleep.
- `dialogmgr.cpp:380` UI time.
- Port diagnostics: the frame profile, flight recorder and per-stage timing
  use `sceKernelGetProcessTimeWide` deltas. A suspend inside a frame shows up
  as one long sample. The gameplay loop has no absolute-deadline pacing; it is
  paced by vsync and fixed 16.667 ms delays, so it cannot try to catch up.

## Fixes

1. **`port/patches/combat-a38-timemgr-resume-real-step-cap.patch`.**
   - Staged `combat/timemgr.cpp:171-182`. Inside
     `#if defined(__vita__) && defined(RENEGADE_VITA_PORT)`, after the
     first-time sync and before `FrameTicks = ticks - LastTicks`, it calls
     `LastTicks = Renegade_Vita_Resume_Frame_Clock_Rebase(ticks, LastTicks,
     RealFrameTicks, TICKS_PER_SECOND / SLOWEST_FPS)`.
   - Registered at the end of `tools/stage_sources.sh` with a pre-anchor on
     the original `timemgr.cpp` (`16db8b1e…`). No earlier patch touches that
     file.
2. **`port/platform/vita/a31_vita_runtime.cpp`.**
   - `g_power_app_resume_events` (`:2497-2499`) is counted in
     `Power_Event_Callback` (`:2520-2521`). The callback still uses atomics
     only, with no logging or locks.
   - `Renegade_Vita_Resume_Frame_Clock_Rebase` is defined at global scope
     (`:4562-4598`). When the system plus application resume count has changed
     since its last call and the pending step is over 200 ms, it returns
     `ticks - 200`. That frame then gets `RealFrameTicks = FrameTicks = 200`.
     Otherwise it returns `LastTicks` unchanged.
   - Every caller of `Update_Frame_Time` goes through this hook: the gameplay
     simulation frame, the EVA pause loop, the frontend loops, the loading
     screen and `combatgmode`. Whichever update runs first after the resume
     takes the cap.
   - A bounded record (at most 32 lines per process):
     `A3.6 power: resume frame clock pending_real_ms=… cap_ms=200
     action=capped|unchanged recent_max_real_ms=… system_resumes=…
     app_resumes=…`.
3. **`port/patches/scripts-a38-cinematic-slow-command-text-copy.patch`.**
   - Staged `scripts/Test_Cinematic.cpp:990-995`. `Parse_Command` copies the
     command into `char vita_original_command[161]` before dispatch, using
     `strncpy` bounded to 160 characters plus a NUL. The
     `A4 slow campaign cinematic command` record (`:1055`) prints that copy.
   - Before, it printed a pointer into a control line that a re-entrant
     primary kill had already freed (`Custom` → `Parse_Commands` →
     `Remove_Head_Control_Line` → `free`).
   - Side effect: the record now shows the whole command. Before, it showed
     text cut short by the handlers' parameter tokenising.
   - The change is Vita-only and diagnostic; dispatch is unchanged.
   - Anchored after the last Test_Cinematic patch, on the then-final file
     (`b7a05ce2…`). No earlier anchor moved.

## Reading the resume record on hardware

| Record | Meaning |
| --- | --- |
| `pending_real_ms` ≈ time suspended, `action=capped` | Process time advances across suspend; the cap was applied. |
| `pending_real_ms` ≈ one frame, `action=unchanged`, `recent_max_real_ms` ≤ 200 | Process time froze; nothing needed capping. |
| `action=unchanged` with `recent_max_real_ms` far above 200 | The notification arrived after the main thread had already consumed the gap (the race below). |
| `app_resumes` stays 0 across PS-button round trips | `APP_RESUME` is not delivered for LiveArea returns. |

## Evidence

- `tools/test_suspend_resume_frame_clock.py` has 4 tests and runs under
  ASan/UBSan. It is registered in `tools/build.sh`.
  - It compiles the staged `Update_Frame_Time` delta lines, including the hook
    call, together with the real hook body.
  - It drives a fake process clock through these cases: steady frames; a
    2.5 s frame with no resume, which keeps its real step; a 30 s advancing
    suspend, which gets one 200 ms step and then normal frames; a frozen
    clock, which is unchanged; a coalesced system plus application resume,
    which gets one cap; a late notification, which the record flags; and the
    32-line log bound.
  - Text checks cover the hook's order relative to the original deltas, the
    callback counting `APP_RESUME` without logging, and the cinematic copy
    being made before the first `Title_Match`.
  - A mutant hook that never caps is caught.
  - `tools.test_vita_animation_clock` still passes.
- `arm-vita-eabi-g++ -fsyntax-only` exits 0, with no diagnostics on changed
  lines, for the staged `timemgr.cpp`, the staged `Test_Cinematic.cpp` and
  `a31_vita_runtime.cpp`.
- Both patches dry-run and apply at `--fuzz=0` to the committed staged files.
  - Resulting `timemgr.cpp`: `20ffbb86…`.
  - Resulting `Test_Cinematic.cpp`: `b2ab14e6…`.
  - `staging/PATCH_INVENTORY.json`: 572 ordered patches, `0094ae91…`.
- **Not run:**
  - A full `tools/stage_sources.sh` pass. Symlinking the shared upstream into
    this worktree was refused by the session's permission policy. Run it from
    a tree that has upstream before relying on the staging receipt.
    `tools/build.sh` re-stages on every build anyway.
  - `tools.test_cinematic_low_fps`, which cannot compile here because
    `upstream/` is empty. The new cinematic code sits inside a `__vita__`
    block, so that host harness never compiles it.

## Residual risk

- **Callback race.** Resume notifications arrive on the power callback
  thread. If the main thread runs an `Update_Frame_Time` before the callback
  increments the counter, that one frame still carries the full gap, as it
  did before this change. The record flags it. If hardware shows it, detect
  the resume on the main thread before `TimeManager::Update`, for example by
  polling `sceAppMgrReceiveSystemEvent`, or by creating the callback on the
  main thread and calling `sceKernelCheckCallback`.
- `APP_RESUME` delivery for LiveArea round trips is unverified on hardware.
- WWAudio virtual-sound positions and `Sound3D` velocity read `TIMEGETTIME`
  directly and are not covered. A virtual one-shot can end at resume.
- Real frames over 200 ms that are not caused by a suspend (hitches) still
  pass their full real step to the Mendoza timers. That is original
  behaviour. The `mendozabossgameobj.cpp`-local per-frame clamp proposed in
  `reports/campaign/SCRIPT_TIMER_LOW_FPS.md` is no longer needed for suspend,
  and remains an owner decision for hitches.
- A LiveArea round trip does not open the EVA pause menu, which is unchanged.
  PC focus-loss parity would suggest it should; that is an owner decision.
- Physical gate: a suspend/resume during gameplay, in the pause menu and in
  the Mendoza death sequence, plus a PS-button round trip. Then read the
  `resume frame clock` and `resume observed` records.
