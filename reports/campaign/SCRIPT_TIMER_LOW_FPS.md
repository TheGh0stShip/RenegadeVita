# Script timers at low frame rate (2026-10-07)

Scope: the observer/custom timer machinery in `ScriptableGameObj`, the
original `TimeManager` frame clock and its 200 ms cap, the clocks used by
cinematics, conversations and innate AI, the Vita time boundary, and every
`Start_Timer` call in `staging/scripts/*.cpp`.

Evidence class: static source audit, a host Python model of the exact timer
arithmetic, deterministic staging (`tools/stage_sources.sh`, exit 0, fuzz 0)
and an `arm-vita-eabi-g++ -fsyntax-only` check of `staging/combat/action.cpp`
using the `vita-fast-candidate` compile database. Nothing was built, linked or
packaged, and nothing ran in Vita3K or on a Vita. No mission script was
edited.

## Verdict

- Script timers run on simulated time. They fire at most once per frame and do
  not catch up. When a timer re-arms itself, the overshoot is dropped. So at
  15–30 fps every timer link runs late by less than one frame, plus at most one
  more frame from float32 rounding. Original behaviour is kept and nothing is
  patched here.
- A zero or near-zero duration cannot busy-loop inside one frame. A timer that
  re-arms itself becomes a once-per-frame poll at most. No campaign script
  re-arms with a duration under 1 s. All 0.0–0.1 s calls are one-shot "next
  frame" deferrals.
- The Vita clock boundary is monotonic. Pause and Combat suspend freeze every
  script clock. One engine timer was wall-clock and stored an absolute,
  per-process stamp in saves. That timer is fixed: see "Engine fix". The
  intentional real-time Mendoza boss timers are the only other real-time
  gameplay consumer. They have one conditional suspend/resume hazard, which is
  recorded below and not patched.
- The 200 ms cap only ever makes simulated time slower than real time. Mission
  countdowns run slower than authored, never faster. Speech advances on
  simulated time but plays on real time. So a hitch over 200 ms opens a gap
  between lines and never overlaps or truncates them. The only drift between
  audio and visuals is inside a cinematic `Play_Audio` wave that is playing
  during a hitch over 200 ms. That drift is bounded by the hitch length minus
  200 ms, and the next cinematic command re-anchors it.

## 1. How `Start_Timer` timers fire

- `Commands->Start_Timer` (`scriptcommands.cpp:602`) calls
  `ScriptableGameObj::Start_Observer_Timer`, which appends a one-shot
  `GameObjObserverTimerClass` (`scriptablegameobj.cpp:687-690`). There is no
  periodic timer and no stop command.
- `Update()` subtracts `TimeManager::Get_Frame_Seconds()` and fires when the
  remainder is <= 0 (`scriptablegameobj.cpp:161`). Custom-event delays use the
  same code (`:238`).
- `Post_Think` walks the list from `Count()-1` down to 0
  (`scriptablegameobj.cpp:724`, `:772`). If a handler re-arms, the new timer is
  appended above the cursor. It is first decremented next frame and its
  overshoot is discarded. **A repeating timer fires once per frame at most and
  never catches up.** Its period is the authored duration rounded up to whole
  frames.
- Two timers on the same object that expire in the same frame fire in reverse
  insertion order (LIFO). Timers on different objects fire in `GameObjList`
  order. Hibernating or cinematic-frozen objects skip `Post_Think`
  (`gameobjmanager.cpp:475`), so their timers stop counting. That is original
  behaviour and does not depend on the frame rate.
- `Post_Think` runs only inside `CombatManager::Think` (`combat.cpp:781`).

Modelled period of a timer that re-arms itself. The host model uses a
constant-rate monotonic millisecond clock, `FrameTicks = min(delta_ms, 200)`,
a float32 `RemainingTime -= ticks/1000` until <= 0, and a re-arm whose first
decrement comes the next frame. The model is not committed; it is about 30
lines and is fully specified by those four rules.

| fps | 0.0 s | 0.1 s | 0.5 s | 1.0 s | 2.0 s | M07 nuke chain (120 s) | 60 × 1 s pulses |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 60 | 0.017 | 0.101 | 0.517 | 1.000 | 2.017 | 120.02 | 60.0 |
| 30 | 0.033 | 0.101 | 0.501 | 1.033 | 2.000 | 120.20 | 62.0 |
| 24 | 0.042 | 0.125 | 0.542 | 1.042 | 2.000 | 120.42 | 62.5 |
| 20 | 0.050 | 0.150 | 0.500 | 1.000 | 2.050 | 120.10 | 60.0 |
| 15 | 0.067 | 0.133 | 0.533 | 1.067 | 2.000 | 120.47 | 64.0 |
| 5 (cap) | 0.200 | 0.200 | 0.600 | 1.200 | 2.000 | 121.60 | 72.0 |

The extra frame at 30/15 fps on 1.0 s is float32 rounding. For example,
0.033+0.033+0.034 subtracted thirty times leaves a tiny positive remainder.

### Logic that counts timer pulses

- Engine innate AI: `SoldierObserverClass` re-arms a 1 s `THINK_ID` timer
  (`soldierobserver.cpp:374-375`). It counts state and action time in pulses:
  `StateTimer += 1` (`:905`) and `ActionTimer -= 1` (`:927`). The innate AI
  reacts about 3% slower at 30 fps and about 7% slower at 15 fps. The
  durations are randomised ranges, so this is benign and kept as original.
- Campaign scripts: an automated scan looked at every `Timer_Expired` body
  that re-arms and also increments and compares a member counter. It found
  only cyclic selectors and retry limits on pulses of 10 s or more. Examples
  are `Mission02.cpp:5152`, `Mission03.cpp:3516-3532`, `Mission10.cpp:2954`,
  `Mission11.cpp:6848` and `Test_RAD.cpp:895-964` / `:1222`. None of them
  turns a pulse count into mission time that matters for an outcome.

### Ordering between two timers

At 15 fps, same-object timers whose gap is under 67 ms can fall into the same
frame, and then they fire in LIFO order. The scan looked for timers started
together on the same object with distinct durations less than 0.21 s apart.
It found only the C-130 paradrop pattern. That pattern stays safe at every
frame rate (see the hotspots below).

## 2. Zero and very short durations

Every literal duration of 0.1 s or less is a one-shot deferral. None re-arms
itself at that length, so none becomes a per-frame loop:

- 0.0 s: `Mission05.cpp:2570` (then 12 s), `Mission05.cpp:5445`,
  `Mission06.cpp:1417`, `Mission06.cpp:3398` (then 8 s), `Mission07.cpp:3796`
  (then 30 s), `Mission09.cpp:1189`, `Test_DLS.cpp:2160`.
- 0.1 s: `Mission00.cpp:3398/3403/4121/4125`, `Mission02.cpp:758/946`,
  `Mission03.cpp:1425`, `Mission09.cpp:292`, `Mission10.cpp:2389`
  (then 5 s), `Test_RAD.cpp:1558/2024/2035/2046/2057/2068` (then the
  randomised basic-move period), `Toolkit_Broadcaster.cpp:79`.
- `1.0f/30.0f`: `Test_DLS.cpp:511-566` (`DLS_Filing_Cabinet`) steps one
  animation frame per timer. At 15 fps it advances one step per frame, so the
  locker break plays at half the authored speed. This is cosmetic.

Durations taken from level data, such as the `Toolkit_Sounds.cpp:751`
frequency or the `Toolkit_Powerup` and `Toolkit_Triggers` timer lengths, would
still poll once per frame even if they were 0. Each poll costs only its
handler.

## 3. Real time and simulated time

- **Port clock.** `timeGetTime` uses `CLOCK_MONOTONIC` (process time) on Vita
  (`port/compatibility/include/mmsystem.h:31`). RTC changes cannot make a
  frame step negative.
- **Pause and EVA menu.** The pause loop calls `TimeManager::Update` but not
  `CombatManager::Think` (`a31_vita_runtime.cpp:2972`). Observer and custom
  timers, `CombatManager::SyncTime` (`combat.cpp:736`, the clock behind
  `Commands->Get_Sync_Time` and `Test_Cinematic`), conversations and
  objectives therefore all freeze. `TotalSeconds` and WW3D sync time keep
  running for UI animation, as the original desktop main loop does.
- **Power resume.** The first frame after resume is capped at a 200 ms
  simulated step. Auto-pause is skipped while a cinematic camera is active
  (`a31_vita_runtime.cpp:6231`), which matches the original focus-loss rule.
  The cinematic clock is `SyncTime`, so it does not jump.
- **Real-time gameplay consumers in the engine**:
  1. `FaceLocationActionCodeClass` (`action.cpp:2281`, `:2325`) used
     `TimeManager::Get_Seconds()`, a wall clock measured from process start,
     as an absolute end stamp, and saved that stamp. **Fixed**: see "Engine
     fix".
  2. `MendozaBossGameObjClass` deliberately uses
     `Get_Frame_Real_Seconds()` (`mendozabossgameobj.cpp:1234`, `:1242`,
     `:1298`, `:1335`, `:1425`, `:1558`, `:1595`), so its death camera ignores
     `Set_Time_Scale(0.5F)` (`:1579`). Conditional hazard: the real step is
     not capped. If Vita process time advances across a system suspend, the
     first frame after resume carries the whole suspend duration. In the
     pack-exploding or death-camera states that frame expires the state timers
     at once and skips `CAMERA_STATE_WAYPATH_FOLLOW`. The window is about 10
     seconds of one boss fight. **Mitigated in port code**: the first
     `TimeManager` update after an observed power or application resume
     now caps the real step at 200 ms
     (`combat-a38-timemgr-resume-real-step-cap.patch`; see
     `reports/SUSPEND_RESUME_TIMING.md`). Real hitches over 200 ms that are
     not suspends still pass through, as in the original.
  3. HUD blink (`hud.cpp:3374`), console, scoreboard and
     `weaponview.cpp:634` recoil are cosmetic.
- Diagnostic only: `Toolkit.cpp:96-135` uses `time(NULL)` for a debug log.

## 4. The 200 ms cap, countdowns, audio and cinematics

`TimeManager::Update_Frame_Time` clamps `FrameTicks` to 200 ms
(`timemgr.cpp:71`, `:176`). Every simulated clock reads that value:
script/custom timers, `SyncTime`, `ActiveConversation::NextRemarkTimer`
(`activeconversation.cpp:443`), `ObjectiveManager::Update` (`combat.cpp:758`),
physics (`combat.cpp:767`) and soldier look timers. The clocks therefore stay
consistent with each other.

- **Countdowns run slower than authored, and that is acceptable.** There is
  no HUD countdown command in the script API (`scriptcommands.h` has only
  `Start_Timer` and `Get_Sync_Time`). Timed sequences are chained
  `Start_Timer`, conversation and cinematic links. Each link can lose at most
  one frame, plus any hitch over 200 ms.
- **Speech never overlaps because of the cap.** The next remark is scheduled
  at the wave length in simulated time (`activeconversation.cpp:543`), while
  the wave plays in real time. A hitch can only add a gap.
- **Cinematics.** `Test_Cinematic` advances its timeline from `SyncTime`
  (`Test_Cinematic.cpp:1059`). It runs every command that is due in the same
  frame (`:1084`) and offsets `Play_Animation` by `FrameSync` (`:657`,
  `:1085`). `Play_Audio` (`:672`) has no offset. The risk class is
  lip-sync/animation offset during a long wave, when a hitch over 200 ms hits
  that wave (for example, a `Create_Object` model load). The offset is bounded
  by the hitch length minus 200 ms and lasts until the next command. Measure
  it per cinematic with the existing `A4 campaign pacing ...
  clock_real/sim/drift_ms` and `A4 slow campaign cinematic command`
  breadcrumbs. Mitigate by prewarming assets, not by changing the cap. Raising
  or removing the cap would change original physics stepping.
- **M13, M08 and M11.**
  - M13 (MissionX0, Test_DLS, Test_RAD and Test_DAY) has the paradrop timers
    and the 0.1 s deferrals listed above.
  - M08's long timers (`mission08.cpp:687-6709`, 30–60 s) are periodic
    re-checks.
  - M11's `delayTimer` values (`Mission11.cpp:845-1511`, `:7167`) are
    one-shot `Get_Random` ranges.
  - None of the three missions has a spoken countdown. The campaign's spoken
    countdown is M07, listed below.

## Engine fix

`port/patches/combat-a37-face-action-stale-end-time-clamp.patch` is
registered at the end of `tools/stage_sources.sh`. It is anchored to the final
`action.cpp` SHA-256 `f9076192…46edbb`, applies at fuzz 0, and the inventory
is now 544 patches. `FaceLocationActionCodeClass::Act` now limits `EndTime` to
`Get_Seconds() + MAX(FaceDuration, LookDuration)`.

- Within one session this never fires, because `Init` sets a stamp that is
  already inside the bound and the clock is monotonic.
- After a save made at uptime T1 is loaded in a fresh process at uptime
  T2 < T1, the restored action used to hold for about T1−T2. That could be
  minutes or hours, and it stalled any script waiting on its `Action_Complete`.
  It now lasts at most its authored duration.
- Innate AI starts 2 s face actions constantly (`soldierobserver.cpp:875`,
  `:1340`), so most saves contain some. Campaign scripts call
  `Action_Face_Location` 25 times: M01 ×7, M11 ×7, M06 ×5, mission08 ×3, and
  M04, M05 and M09 once each.
- The save format and the pause behaviour are unchanged. A pause still ends a
  face action early, as on PC.

## Mission-script hotspots for the mission owners

These are informational. None requires a change for 15–30 fps.

| Location | Pattern | Effect at 15 fps |
| --- | --- | --- |
| `Mission07.cpp:1420-1530` `M07_Cathedral_Controller` | Spoken nuke countdown chained 60/30/10/10/5/1/1/1/1/1 s. `XG_NukeStrike` starts at `FIVE` (about `:1478`); the impact is at `ONE`. | +0.47 s over 120 s. The impact lags the cinematic by up to 4 frames (about 0.27 s). |
| `Test_DLS.cpp:1002-1010`, the same pattern at `Mission03.cpp:4719-4727`, `Mission09.cpp:2331-2339` and `Mission10.cpp:1727-1735` | Paradrop timers (145–280)/30 s. The closest pair is timer 6 at 5.500 s and timer 1 at 5.633 s. | These stay in separate frames down to 7.5 fps. If they ever share a frame, LIFO runs 6 before 1, which is safe (`out >= 1` is set at 4.83 s). Parachutes and soldiers start at animation frame 0 with no compensation, so they can trail the C-130 by up to 1 frame. |
| `Test_DLS.cpp:511-566` `DLS_Filing_Cabinet` | Animation stepped by 1/30 s timers. | Plays at half speed (cosmetic). |
| `Toolkit_Sounds.cpp:727-731` | `Custom()` calls `Timer_Expired` directly, so every custom adds another re-arming chain. | This is an authored duplication and does not depend on fps. It is reported only. |
| `Mission09.cpp:612-645` (Mobius evac escort poll: re-arms every 3 s, then waits 1 s before `Mission_Complete`), `Mission02.cpp:2373` (respawn poll, 25−10×difficulty s) | Escort and respawn pollers. | Less than 1 frame per pulse. Arrival is checked by distance, not by counting pulses. |

## Residual and next evidence

- Cross-object ordering between two timers or delayed customs with distinct
  but close delays is not exhaustively scanned. At 15 fps, events less than
  67 ms apart can share a frame and then follow `GameObjList` order.
- On hardware, read the `A3.6 power: resume frame clock` record to learn
  whether `sceKernelGetProcessTimeWide` advances across a suspend, and
  whether the resume notification can arrive late
  (`reports/SUSPEND_RESUME_TIMING.md`).
- Record `clock_real/sim/drift_ms` per cinematic on hardware to size the
  audio drift that hitches cause.
