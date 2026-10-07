# TUT-R1-03 — Tutorial script-layer think cost (SCRIPT_THINK_COST)

Base: `tutorial-r1/base` (45c6cf5, dev240 candidate). Flag prefix **RVSC1**
(`ux0:data/renegade/user/config/script-cost-v1.flag`). Nothing was compiled
or run; all C++ is unverified until the coordinator builds it.

## Result

The evidence does **not** support a script-layer optimization for M00. The
tutorial's script layer is event-driven. Its per-frame work is small next to
the measured Combat think, and much smaller than render. No gameplay code
changed. This round adds the missing **measurement**: an RVSC1-gated
attribution line, plus a log summarizer. A tutorial run can then confirm or
refute this estimate on hardware.

## Physical baseline the estimate is checked against

Source: the dev230 physical tutorial run (`A3.5-dev230-20261004`, complete
route; pre-R4, so engine scopes were not yet profiled). Only aggregates are
quoted here.

| Item | Value |
| --- | --- |
| Level-load census | 74 objects: 70 scriptable, 22 smart (all soldiers), **31 script zones** (all sampled zones are `Script_Zone_Star` with 1 observer), 8 powerups, 81 observer refs, 60 active scripts |
| CombatManager::Think (`A4 campaign pacing` window deltas, 232 windows) | median **3.19 ms**, p95 9.5 ms, max 22.7 ms |
| Sim stage (`A3.5 perf`) | median 4.14 ms, p95 4.6 ms |
| Render stage (`A3.5 perf`) | median **26.5 ms**, p95 34.4 ms |

Reproduce: `python3 tools/tut1_script_cost_report.py <runtime.log>`. The
pacing line is cumulative and integer-truncated. Late windows therefore carry
up to ±frames/120 µs of error, and the medians are robust to it. dev240+
logs use the exact `A4 combat casts` window line instead.

## Findings (file:line in the tracked `staging/` tree unless noted)

1. **No per-frame script callback exists.**
   `combat/gameobjobserver.h:105-121` (identical to upstream) has only event
   callbacks. Scripts run per frame only when a timer expires.
2. **Mission00 timers are slow.**
   - Of the 34 `Start_Timer` calls in the 19 `MTU_*` scripts, every literal
     duration is ≥ 1.0 s except two 0.1 s one-shot camera timers
     (`scripts/Mission00.cpp:3398,3403`). Those are started from `Custom` and
     are never re-armed (`:3414`).
   - The flyover timer is 10–30 s (`:142,306`).
   - The four toolkit scripts attached in M00 (Test_DAK, Toolkit_Powerup,
     Toolkit_Objects, Toolkit) have no timers and no `Find_Object`.
   - `MSK_*` 0.1 s timers are skirmish-only and excluded by the M00 discovery.
3. **`Find_Object` is event-driven.**
   - Mission00 has 128 `Find_Object` call sites, all inside event callbacks.
   - Each call is one linear `GameObjList` scan (`combat/gameobjmanager.cpp:628`)
     plus the gated telemetry record (`combat/scriptcommands.cpp:444-452`).
   - No tutorial script uses an object-collection command:
     `Find_Random_Simple_Object`, `Get_A_Star`, `Find_Closest_Soldier` and
     `Find_Nearest_Building*` are all absent.
   - The only engine-side per-frame ID scans are small:
     - `ccamera.cpp:1279` scans the 22-entry smart list.
     - `activeconversation.cpp:1165` runs `Find_PhysicalGameObj` once per
       orator per frame, and only when a look-at id is > 0.
     - `clientcontrol.cpp:137` exports the local client's control.
4. **Per-frame script-layer work** (original code unless marked):
   - **31 star zones.**
     - Each frame, every star zone runs `ScriptZoneGameObj::Think`
       (`combat/scriptzone.cpp:349`): two profiler scopes, an inside-list
       walk, the one-star point test and the port's `Update_Sweep_Sample`
       (`:452`, one `Length()`).
     - Zones without observers return first (`:353`).
     - Trigger zones destroy themselves when used, so the count falls along
       the route.
   - **~70 `ScriptableGameObj::Post_Think` calls**
     (`combat/scriptablegameobj.cpp:712-790`).
     - Each one is a profiler scope plus a walk of its timer lists.
     - About 25–30 timers expire per second: the 22 innate-soldier THINK
       timers at 1 s (`combat/soldierobserver.cpp:58,331`) plus script
       timers.
     - The port adds two kernel clock reads per expiry (`:736,742`).
   - **Enemy_Seen scans.** Every 0.5–1.0 s, each enabled smart object walks
     the whole object list (`combat/smartgameobj.cpp:745-775`), about
     80 nodes per frame amortized. This is AI perception and is listed
     separately.
   - **Port boundary.**
     - Lookup telemetry is opt-in through `script-coverage.flag`
       (`port/platform/vita/a31_vita_runtime.cpp:5766-5779`).
     - Disabled hooks return before the mutex
       (`port/developer/a35_script_lookup_telemetry.cpp:66,79`), at a cost of
       one atomic load each.
     - `A31_Interactive_Get_Mission_Progress_State`
       (`port/platform/a31_gameplay_boundary.cpp:629`, polled at
       `a31_vita_runtime.cpp:7030`) does one `snprintf` and a few O(1) or
       O(log n) lookups per frame. That is a few µs.
     - Test_Cinematic's port diagnostics re-parse `ControlFilename` per
       command (`scripts/Test_Cinematic.cpp:998,1040`, each with a 512-byte
       `strncpy` at `scripts/scripts.cpp:541`). This cost is per cinematic
       command, not per frame.
5. **Static estimate:**
   - The script layer as defined here (zones + scriptable timers +
     conversations + objectives + spawners) costs about **30–150 µs per
     frame**.
   - That is ≲ 5 % of the measured Combat think and ≲ 0.5 % of the frame.
   - Removing all of it could not move tutorial FPS materially. The frame is
     dominated by render.

## Change (diagnostics only, default OFF)

Files:

- `port/compatibility/include/renegade_vita_script_cost.h` (new). It adds
  `RENEGADE_SCRIPT_COST_SCOPE`, a frame-profile scope that opens only when
  both RVSC1 and RVFP1 are on. Otherwise it costs one load and branch.
- `port/patches/combat-tut1-script-cost-scopes.patch`. It is registered last
  in the combat list in `tools/stage_sources.sh`, and the same edit is
  applied to `staging/combat/combat.cpp`. It wraps the three unscoped,
  script-driven once-per-frame calls in `CombatManager::Think`:
  - `ObjectiveManager::Update` as "Objective Update"
  - `ConversationMgrClass::Think` as "Conversation Think"
  - `SpawnManager::Update` as "Spawn Update"

  The call sequence is unchanged; the test proves it by reverse-applying the
  patch. Builds without `RENEGADE_VITA_PORT && RENEGADE_VITA_FRAME_PROFILE`
  compile the scopes out.
- `port/platform/vita/renegade_vita_frame_profile.cpp`:
  - `Configure` parses `RVSC1 0|1\n` with the same 8-byte grammar as RVFP1.
  - While RVSC1 is on, `Report_Window` adds an
    `A3.6 script-cost: version=1 …` line before the window reset. It lists 12
    scopes whatever their rank:
    - denominators: CombatManager Think, Game Obj Think, Post Think
    - RVSC1 scopes: Objective Update, Conversation Think, Spawn Update
    - original script scopes: ScriptZone Think, Star Enter, All Enter,
      Scriptable PostThink
    - perception: Smart Think, See
  - Scope Begin/End/End_Frame are untouched.
- `tools/tut1_script_cost_report.py` (new). Pure Python. It summarizes a
  runtime log into numbers only: census, Combat window, sim/render, the
  script-cost watch, and a rank bound when the watch is absent.
- `tools/test_tut1_script_think_cost.py` (new). 18 pure-Python tests pass.
  They pin:
  - the observer interface
  - the Mission00/toolkit timer cadence and object-collection-free scripts
  - `Find_Object` = one scan + gated record
  - the zone early-out
  - lockless disabled lookup hooks and the coverage-flag gating
  - RVSC1 parsing and default-off, untouched Begin/End, report-before-reset
  - watched names existing in staged sources
  - patch registration (once, last combat patch, reverse-applies) and an
    unchanged call order
  - analyzer math against the C++ format string

**Flag:** `script-cost-v1.flag` = `RVSC1 1\n` enables it. It is absent by
default. It needs RVFP1 on, which is the build default.

**Cost:**
- Off: three load+branch per frame and one branch per 120 frames.
- On: three exact scopes per frame (6 clock reads; see the `clock-cost`
  line), plus one log line and about 3k `strcmp` per 120 frames.

## Ledger entry

- **Hypothesis.** In M00, the script layer (ScriptZone Think + Scriptable
  PostThink + Conversation Think + Objective Update + Spawn Update) costs
  < 0.3 ms per frame median and < 2 % of the frame. Script-side
  optimization therefore cannot materially raise tutorial FPS. Effort
  belongs in render (26.5 ms median) and the Combat hot paths.
- **Risk.**
  - None to gameplay; this is diagnostics only.
  - With RVSC1 on, the profiler gains 3 scopes per frame.
  - Inclusive script scopes also contain nested profiler overhead.
  - Sub-µs scopes rely on µs-clock averaging.
- **Estimated gain.** None from this change, which is measurement only. A
  future script optimization is bounded at about ≤ 0.15 ms per frame.
- **Measure.** Run the tutorial route with RVSC1 on: Logan → Sydney → Gunner
  range → Mobius → HMVV/vehicles → base buildings. Read the median/p95 of
  `script_layer_us_per_frame`, `script_layer_share_of_frame` and
  `script_layer_share_of_combat`, plus per-scope calls per frame (for
  example, ScriptZone Think calls ≈ live zone count).
- **Decision rule.**
  - If the script layer is < 0.3 ms median and < 2 % → close (rejected as a
    target).
  - If Conversation Think or ScriptZone Think exceeds 0.5 ms in any route
    segment → follow up there. Example: an exact, flag-gated look-at lookup
    for `Control_Orator`, with invalidation proven against `GameObjManager`
    add/remove and network ID changes.

## Verified vs unverified

**Verified on host** (no compiler):
- 18 new pure-Python tests pass.
- The patch dry-run applies at fuzz 0 to the pre-change staged
  `combat.cpp` and reverse-applies to the tracked one.
- `renegade_patch_inventory.load_inventory` accepts the registry (578
  patches; the new patch is last).
- The analyzer reproduces the dev230 aggregates above.

**Unverified:**
- C++ compilation: the profiler change, the new header and the combat.cpp
  scopes. `tools/test_frame_profile.py` (host ASan/UBSan) should still pass
  because RVSC1 is off without the flag file. Not run, since it needs g++.
- ARM link.
- Any hardware number.
- `staging/PATCH_INVENTORY.json` was deliberately not regenerated; the
  coordinator's staging run must refresh it.

## Hardware A/B

1. Use a candidate built from this branch, with RVFP1 on (no
   `frame-profile-v1.flag`, or `RVFP1 1`).
2. **Run A:** no `script-cost-v1.flag`. Play the full tutorial route. Expect
   no `A3.6 script-cost` lines.
3. **Run B:** write `ux0:data/renegade/user/config/script-cost-v1.flag` with
   exactly `RVSC1 1` + LF (8 bytes). Play the same route.
   - Expect `A3.6 script-cost: configured enabled=1 collection=1 scopes=12`.
   - Expect one `A3.6 script-cost:` line per 120 profiled frames.
4. Run `python3 tools/tut1_script_cost_report.py runB.log` (and on `runA.log`).
   - Compare frame p50/p95 between A and B. The B−A difference bounds the
     RVSC1 overhead.
   - Apply the decision rule above.
5. Delete the flag file afterwards.
