# Tutorial round 1: clocks, power and thread placement (TUT-R1-12)

Base: `tutorial-r1/base` 45c6cf5 (main plus FPS round 4, dev240). Branch:
`tut-r1-12-clocks-threads`. The worktree was created from a newer `main`, so
`git merge --ff-only tutorial-r1/base` was refused (the branches had
diverged). The task branch was created directly at 45c6cf5 instead.

**Nothing here was compiled or run on hardware.** The only evidence comes from
reading the source, decoding the VitaSDK libraries in pure Python, a pure-Python
static test, and summarized figures from existing device logs.

## Findings

### Clocks are already set at boot and re-checked during gameplay
- **Boot request.** `a30_main.cpp:160-175` requests 444/222/222/166 MHz
  (cpu/bus/gpu/xbar) and logs the readback. It runs once, unconditionally,
  after filesystem init and log reset. Earlier work (debug-screen init,
  250 ms bootstrap hold, filesystem init) runs at the default clocks; that
  costs well under 1 s and is not material.
- **Device evidence (dev229 to dev238, 43 boots).**
  - Readback before the request: 333/222/0/111. The GPU getter reads 0 until
    the game sets it.
  - Every request returned 0. Readback after: 444/222/222/166.
  - No log contains a clock re-application or a resume line. Either clocks
    never dropped, or no suspend/resume was exercised. The `A3.6 power` code
    (0ebc7b4, 2026-10-06) is newer than all of these logs.
- **Gameplay re-assertion.**
  - `Reassert_Performance_Clocks` (`a31_vita_runtime.cpp:2483`) re-requests the
    maxima only when a getter reads low.
  - It is called from `Consume_Power_Resume` (`:2589`) on a system resume, and
    from the 120-frame checkpoint (`:7304`, `kTimingWindowFrames` `:374`).
  - Both callers sit inside the gameplay loop (`:6699`).
- **Gap 1: phases outside gameplay are not covered.** A resume during the
  loading screen (including the M00 load), the frontend, the pause menu entry
  or a BINK movie leaves the clocks unchecked until gameplay runs again. The
  premise that a resume resets the clocks comes from a code comment
  (`:2480-2482`). There is no device evidence for it.
- **Gap 2: the suspend counters probably never fire.**
  - `SCE_POWER_CB_VALID_MASK_NON_SYSTEM` is `0x00361180`
    (`psp2common/power.h`). It contains these resume bits:
    `AFTER_SYSTEM_RESUME`, `SYSTEM_RESUMING`, `SYSTEM_RESUME`, `APP_RESUME`.
  - It does not contain `SYSTEM_SUSPEND`, `THERMAL_SUSPEND`,
    `LOW_BATTERY_SUSPEND`, `LOW_BATTERY` or `APP_SUSPEND`.
  - So the suspend and low-battery counters in `Power_Event_Callback` (`:2517`)
    are probably never delivered to a normal app. The SDK marks some of these
    bits "TODO: confirm", so this is unverified.
  - The resume path does not depend on these counters.
  - Returning from LiveArea (`APP_RESUME`) is not counted at all.

### Power tick and auto-suspend
- **Where it is already ticked.**
  - The loading screen ticks `SCE_KERNEL_POWER_TICK_DEFAULT` on each progress
    render (`a31:1638`).
  - BINK ticks `DISABLE_AUTO_SUSPEND` and `DISABLE_OLED_DIMMING` on every
    update (`a4_binkmovie_boundary.cpp:1218-1219`).
- **Gameplay never ticks.** Tutorial conversations and cinematics take no
  input, so the system dim and auto-suspend timers keep running while the
  player listens. The timers are user-configurable. Whether analog-only input
  resets them is unverified.
- **Original behaviour.** The original game blocked the Windows screen saver
  for its whole session (`upstream Commando/WINMAIN.CPP:620-625`,
  `SC_SCREENSAVE`).

### Thread inventory (tutorial-relevant)

Priorities are the Vita priorities passed to `sceKernelCreateThread`.

**What pthreads get by default** (decoded from VitaSDK `libpthread.a` in pure
Python):
- `vita_osal.o`: `pte_osThreadGetDefaultPriority` returns 160. Create and
  SetPriority map a pte priority to a Vita priority as `319 - pte`
  (`rsb #0x13E; adds #1`), so the default pthread priority is **159**.
- `vita_osal.o`: `pte_osThreadCreate` passes affinity 0 and attr 0.
- `create.o`: the default stack is 32 KiB (`mov.w #0x8000`), unless the app
  defines the weak symbol `_pthread_stack_default_user`. The port does not.

**Main thread.** The port defines no `sceUserMainThread*` symbol, so the main
thread uses the SDK default priority `0x10000100`. That is believed to resolve
to 160 for a game app, which would put pthreads one step **above** the game
thread. This is unverified; the dev240 `renderer-init game-thread:` line
(`ww3d_vita_renderer.cpp:2371`) will show the real value.

**Affinity 0.** `SCE_KERNEL_THREAD_CPU_AFFINITY_MASK_DEFAULT` (0) is
documented as "inherit calling thread affinity mask" in
`psp2common/kernel/threadmgr.h:140`. `psp2/kernel/threadmgr/thread.h` instead
says "of the calling process". Every creator below is the game thread, which
is pinned to user core 0 at `a30_main.cpp:178`.

| Thread | Created at | Priority | Affinity | Stack | Load |
|---|---|---|---|---|---|
| Game/main | process | 0x10000100 | pinned USER_0 (`a30_main.cpp:178`) | SDK default | all simulation, render, load |
| Miles mixer | `renegade_miles_provider.cpp:1060` | 159 | self-pins USER_1 (`:995`) | 32 KiB | real-time mix |
| WWAudio delayed release | `staging/wwaudio/Threads.cpp:101` | 159 | 0, never re-pinned | 32 KiB | wakes every 2.0-3.0 s (`:257-258`) |
| Async log writer | `vita_platform.cpp:139` | 159 | self-pins USER_2 (`:125`) | 32 KiB | I/O |
| Flight flusher | `a35_campaign_flight_recorder.cpp:803` | 159 | self-pins USER_2 (`:757`) | 32 KiB | I/O |
| vitaGL GC | `ww3d_vita_renderer.cpp:3861` (vitaGL `gxm.c:357`) | 0x10000100 | USER_2 | 64 KiB | deferred frees |
| Startup status repaint | `a31:880` | 0x10000100 | 0 | 16 KiB | full debug-screen redraw every 250 ms (`a31:384`), startup only |
| Power callback | `a31:2562` | 0x10000100 | 0 | 4 KiB | 1 Hz wake |
| BINK audio output | `a4_binkmovie_boundary.cpp:480` | 159 | 0, never re-pinned | 32 KiB | per audio buffer, movies only |
| BINK decode | none: ffmpeg `thread_count = 1` (`a4_binkmovie_boundary.cpp:632`) | - | game thread | - | - |
| Level loader / pre-warm | none: `Load_Level_Threaded` runs `Thread_Function()` synchronously on Vita (`staging/combat/combat.cpp:491-501`); RVPL1 pre-warm runs on the game thread | - | game thread | - | - |
| Texture loader | none: `TextureLoader::Init` is a no-op (`a4_frontend_lifecycle_boundary.cpp:137`) | - | - | - | - |

**Verdict on FPS round 4's "already sound".** It holds for every thread with
real load. The mixer is alone on core 1. I/O and GC run on core 2. Loading
and pre-warm stay on the game thread by design. The wording "no port worker
targets core 0" is accurate, but it misses inheritance:
- Four threads pass affinity 0 and so most likely run on core 0: startup
  status, power callback, BINK audio and WWAudio release. Round 4 did not
  list the WWAudio release thread.
- Three of those are pthreads at priority 159. If 0x10000100 resolves to 160,
  those three preempt the game thread whenever they are runnable.
- Their CPU use is tiny: microseconds per wake, 1 Hz or 0.4 Hz, or movie-only.
  The largest is the startup repaint, which redraws 960x544 at 4 Hz during
  startup only.
- None of them changes tutorial gameplay FPS in a measurable way.

## Changes (all behind `clocks-v1.flag`, prefix RVCK1, default OFF)

**Flag format.** The file holds exactly `RVCK1 <m>\n`, where `m` is a digit
0-7 used as a bit mask. Anything else selects 0.

**New `port/platform/vita/renegade_vita_clocks.h`.** It is header-only, so
CMake is unchanged. Its pure part (parser, target check, watchdog window,
cadence) has no Vita dependency. Its Vita part:
- reads the flag once, on the game thread, before any helper thread exists;
- requests 444/222/222/166 in the same order as the boot request;
- logs `RVCK1 clocks: armed ... readback` once;
- logs each re-application with before/after readback, capped at 32 lines.

**Mask 1: clock watchdog.**
- Every resume-type callback is counted: `AFTER_SYSTEM_RESUME`,
  `SYSTEM_RESUME` and `APP_RESUME` (`a31:2535`).
- After each 1 s `sceKernelDelayThreadCB` wake, the power thread calls
  `Power_Thread_Wake` (`a31:2545-2553`).
- After a resume event it re-reads the clocks on each wake for 8 wakes.
  Otherwise it re-reads them every 10 wakes.
- When any clock reads low, it requests the maxima again.
- This covers loading, frontend, movies and gameplay, and the PS-button
  return. The existing gameplay paths are unchanged.

**Mask 2: helper-thread placement.**
- The power-callback and startup-status threads are created on USER_2.
- The BINK audio worker pins itself to USER_1, next to the mixer.
- The WWAudio release thread is left alone. Moving it would need an
  original-code patch for a thread that wakes every 2-3 s.

**Mask 4: keep-awake.**
- Once per 30 distinct gameplay frames, `Tick_Presentation_Keep_Awake`
  (`a31:2597`, called at `:6698`) checks for an active cinematic camera
  (`COMBAT_CAMERA->Is_In_Cinematic()`) or an active conversation
  (`ConversationMgrClass::Get_Active_Conversation_Count() > 0`).
- If either is active, it ticks `DISABLE_AUTO_SUSPEND` and
  `DISABLE_OLED_DIMMING`, as BINK does for movies.
- It reads original state only. The pause menu and idle gameplay still dim
  normally.

**Default-off justification.** With no flag:
- the power thread keeps affinity 0 and its 4 KiB stack;
- `Power_Thread_Armed` and `Power_Thread_Wake` return after one load;
- no ticks and no extra clock requests are made.

The only always-on addition is one relaxed atomic increment in the callback
on resume events. Any bit enables logging, so it also raises the power thread
stack to 16 KiB. This matches the logging startup-status thread, because
`A30_Vita_Log` uses a 2 KiB buffer plus `vsnprintf`.

**Shared files touched.**
- `a31_vita_runtime.cpp`: +44/-3 lines, in the power block, the two thread
  creations and one line in the gameplay loop.
- `a4_binkmovie_boundary.cpp`: +4 lines.
- No staging, patch, CMake or `build.sh` change.

## Hypothesis-ledger entry
- **Hypothesis.**
  - (a) A suspend/resume or PS-button return outside gameplay can leave the
    SoC at boot defaults (333 MHz CPU, 111 MHz xbar, GPU unset) for the rest
    of a load or menu phase. Mask 1 restores the maxima within about 1 s.
  - (b) Helper threads that inherit core 0 steal small slices from the game
    thread. Mask 2 removes this.
  - (c) The screen dims or the system auto-suspends during long tutorial
    dialogue without input. Mask 4 prevents this.
- **Risk.**
  - Mask 1 could fight a deliberate system clock limit. This is mitigated:
    the existing checkpoint already re-requests the same values every 120
    frames, requests are made only when a clock reads low, and logging is
    capped.
  - Mask 4 could keep the device awake while ambient conversations repeat.
  - Mask 2: none known.
- **Estimated gain.**
  - Normal tutorial play: about 0 FPS.
  - After a resume during the M00 load: if clocks really reset, the rest of
    the load would otherwise run at about 75% CPU clock and lower bus/xbar
    clocks. The load would finish correspondingly faster, but this is
    unmeasured.
  - Mask 2: well under 0.1 ms per frame.
  - Mask 4: user experience only.
- **How to measure on the tutorial route.** Use the hardware A/B steps below.

## Verification
- **Verified.**
  - `python3 -m unittest tools.test_vita_clocks_threads` passes 9/9. It is pure
    Python and runs no compiler. It covers:
    - the unconditional boot maxima;
    - the gameplay resume path re-applying clocks;
    - the resume-type callback counting;
    - the watchdog running after every wake;
    - the re-request values and order;
    - strict, default-off parsing;
    - default affinity 0 and the 4 KiB stack;
    - thread wiring;
    - keep-awake gating;
    - no port clock request above the maxima.
  - A scratch mutation run killed 16/16 mutants.
  - The existing pure static tests that read the edited files pass, 76/76:
    `campaign_discovery_handoff`, `campaign_autosave_chain`,
    `runtime_log_contract`, `fail_and_retry_flow`,
    `explosion_effect_recycler_patch`, `vita_indexed_state_contract`,
    `vita_texture_provenance_contract`, `a4_original_frontend_contract`.
  - `git diff --check` is clean.
- **Unverified.**
  - ARM compilation, including `-Werror` format and conversion checks.
  - Whether a resume resets clocks at all.
  - The real main-thread priority.
  - Inherit-thread versus inherit-process affinity semantics.
  - The suspend-bit delivery mask.
  - Keep-awake behaviour on the device.

## Hardware A/B steps (tutorial route)
1. **Baseline: no flag.** Boot to M00 and play Logan, then Sydney, then the
   gunner range. Record:
   - `A3.5 native clocks`, `A3.6 thread placement` and
     `renderer-init game-thread:`. Note the real priority and affinity.
   - Press PS during the M00 loading screen, wait 10 s, then resume.
   - Note whether `A3.6 power: resume observed` appears when gameplay
     starts, and whether `A3.6 clocks: reapplied` shows lowered "before"
     values. This tests the reset premise.
   - Repeat with a full sleep (power button) and resume in mid-dialogue.
   - Stand still through Logan's dialogue and note whether the screen dims.
2. **`RVCK1 1\n`.** Repeat the PS-button and power-button resumes during the
   load and in the main menu. Expect:
   - `RVCK1 clocks: armed` at boot;
   - `RVCK1 clocks: reapplied trigger=resume` within about 1 s of a resume,
     only if the clocks really dropped.
   - Compare the load time after a resume against step 1.
3. **`RVCK1 2\n`.** `armed ... affinity=00040000` confirms core 2. Compare
   startup time to the main menu and intro-movie A/V sync against step 1.
4. **`RVCK1 4\n`.** Stand still through Logan's and Sydney's dialogue.
   Expect no dimming and one `RVCK1 keep-awake: first tick` line. Confirm
   that the pause menu still dims after the system timeout.
5. **`RVCK1 7\n`.** Run the whole tutorial route. Expect no regression in
   frame p50/p95/p99 against step 1, using the same fixed route.

**Adoption.** Make a mask the default only if step 2 shows real drops (mask
1) or step 4 shows dimming without the flag (mask 4). Keep mask 2 only if the
`game-thread:` priority confirms that 159 is above the game thread.
