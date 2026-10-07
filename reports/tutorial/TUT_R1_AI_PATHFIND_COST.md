# Tutorial round 1: AI_PATHFIND_COST (RVPF1)

Agent TUT-R1-04. Branch `tutorial-r1/ai-pathfind-cost`, cut from
`tutorial-r1/base` (45c6cf5). The worktree started on main, which is ahead of
the base, so `git merge --ff-only` could not run; the branch was created from
the base instead. Nothing here was compiled or run on a device. Every gain
below is an estimate.

## Bottom line

- In the tutorial, pathfinding costs almost nothing. The original AI
  time-slicing is intact and the port keeps its defaults.
- I found one redundant per-frame cost that grows with NPC count:
  `SoldierGameObj::Think` runs a dynamic-scene `Collect_Objects` probe for every
  awake soldier on every frame, then throws the answer away unless the soldier
  is ghosted.
- Fix: RVPF1 bit 0 skips the probe in exactly that case. This leaves engine
  state unchanged, so the bit defaults to on.
- Everything else in this report is report-only.

## Hardware evidence already on disk (physical Vita, dev230, M00 tutorial)

Source: the private `A3.5-dev230` `runtime-tutorial-finished.log`. It holds 233
cumulative `A4 campaign pacing` checkpoints over 27,958 frames (977 s real,
about 28.6 FPS). Windows were derived from consecutive checkpoints; integer
truncation gives about ±frames/120 µs of error per window.

| Stage | Whole-run average | 120-frame windows |
| --- | --- | --- |
| path (`PathMgrClass::Resolve_Paths`) | 6 µs/frame (about 0.17 s over the whole run) | flat 5 µs apart from one solve window |
| control (`Generate_Control` → `ActionClass::Act`) | 102 µs | p50 92, p90 168, max 794 µs |
| combat (`CombatManager::Think`: object Think, physics, scripts) | 4,139 µs | p50 3.2 ms, p90 7.3 ms, max 22.7 ms |

So path solving is about 0.02 % of the frame. The cost sits in the Combat
stage. FPS round 4 made the engine `WWPROFILE` scopes live, so dev240+ can
attribute it.

## Findings (file:line in tracked `staging/` unless noted)

### Path solving: already pooled and time-sliced (original)

- `PathMgrClass` pre-allocates 15 `PathSolveClass` objects
  (`wwphys/pathmgr.cpp:67`). Each has a 10,000-entry binary heap
  (`wwphys/pathsolve.cpp:211`), which accounts for most of the 80,256 bytes
  KNOWN_GAPS records per `PathSolveClass`.
  - `Request_Path_Object` reuses a pooled object, and `Return_Path_Object`
    resets it and puts it back.
  - A request allocates only when more than 15 solves are in flight. The new
    object then stays in the pool.
  - Per-request pooling is therefore already the original behaviour; there
    was nothing to add.
- A* nodes are `new PathNodeClass` (`pathsolve.cpp:1214`). Given the 6 µs
  average, pooling them is not justified.
- `Resolve_Paths(camera_pos, 5 ms)` (`pathmgr.cpp:342`):
  - The port calls it with the original default
    (`port/platform/a31_gameplay_boundary.cpp:781`), the same as desktop
    `commando/mainloop.cpp:97`.
  - Priority combines distance to the camera over 20 m, script priority, and
    age over 5 s (`pathmgr.cpp:420-422`).
  - The inner loop reads QPC once per A* expansion (`pathsolve.cpp:393`).
  - With no path in THINKING the call costs about 2 clock reads, which is the
    5 µs floor seen in the table.
  - Shrinking the 5 ms budget would delay path results, which changes AI
    timing. Report-only.
- Re-solving only happens when the goal really changes:
  - Goto initialises a solve once (`action.cpp:1145-1167`).
  - Follow mode (`MoveObject`) re-paths only when the target has moved more
    than 2 m and more than 10 % of the separation (`action.cpp:1570`).
  - Scripts that re-issue `Action_Goto` reset the action and solve again.
    That is an authored decision, so it is not changed.

### Vision, hearing and innate AI: already throttled (original)

- Enemy-seen scan:
  - Each observer scans every 0.5–1 s (`smartgameobj.cpp:751`).
  - A ray is cast only for an enemy inside sight range × `GlobalSightRangeScale`
    (1.0) and inside the sight arc (`smartgameobj.cpp:852-870`).
  - The scan walks the full object list in list order. Switching to
    `SmartGameObjList` would reorder `Enemy_Seen` callbacks, so it is not
    changed.
- Attack line-of-fire check runs every 2–3 s (`action.cpp:1956`).
- `SoldierObserverClass` innate think runs on a 1 s timer
  (`soldierobserver.cpp:58`).
- Logical sound processing is limited to 4 listeners per frame
  (`wwaudio/SoundScene.cpp:56`).
- Hibernation starts after 30 s (`physicalgameobj.cpp:76`).
- No O(n²) per-frame enemy scan exists. The per-observer cost is amortised
  over at least 0.5 s.

### Port-added diagnostics on AI paths: all bounded or compiled out

| Site | Cost | Decision |
| --- | --- | --- |
| Logan move/request/callback samples (`action.cpp:1584`, `combat-a35-logan-path-diagnostics.patch`) | One ID compare per `Goto Act`. At most 128 lines each, queued to the writer thread | keep (tutorial debugging value; negligible) |
| Action observer miss (`action.cpp` `Notify_Completed`) | Only on a miss, and only while the conversation queue is enabled | keep |
| Logical stimulus (`smartgameobj.cpp` `On_Logical_Heard`) | Returns early unless the type is M01 detention | keep |
| PostThink per-object timing (`gameobjmanager.cpp:458+`), vehicle transition timing (`vehicle.cpp:2259+`) | Compiled only with `RENEGADE_VITA_DETAILED_TIMING` | already off |
| Engine `WWPROFILE` scopes (about 15–20 per soldier per frame) | RVFP1 domain (FPS round 4) | not mine; A/B with `RVFP1 0` |

### The redundant probe (fixed)

The per-frame code is in `soldier.cpp:2466-2482` (`WWPROFILE("Coordination Zone")`):

```
if ( UnitCoordinationZoneMgr::Is_Unit_In_Zone( position ) ) Enable_Ghost_Collision( true );
else if ( Is_Safe_To_Disable_Ghost_Collision( position ) ) Enable_Ghost_Collision( false );
```

- **The probe** (`Is_Safe_To_Disable_Ghost_Collision`, `soldier.cpp:5244-5300`):
  - Builds a 3×3×2 m box.
  - Calls `PhysicsSceneClass::Collect_Objects(box, false, true, &list)`
    (`:5260`). That is a dynamic-grid query over 60 m cells
    (`wwphys/physgridcull.cpp:61-62`) with an overlap test per object in the
    cell.
  - Adds the hits to a pooled `NonRefPhysListClass`.
  - Makes four virtual casts per hit.
- **The answer is usually discarded.** `Enable_Ghost_Collision(false)`
  (`:5224`) returns at once when the soldier is not in
  `SOLDIER_GHOST_COLLISION_GROUP`.
- **Ghosting is rare in M00.** Coordination zones only cover the ladder and
  elevator entrances (`unitcoordinationzonemgr.cpp:188`), and M00 has two
  ladders. So almost every probe is wasted.

Why skipping the probe is state-identical (pinned by the tests):

1. **Exact condition.** The skip test is the same expression that
   `Enable_Ghost_Collision` uses to decide on its early return:
   `Peek_Physical_Object ()->Get_Collision_Group() == SOLDIER_GHOST_COLLISION_GROUP`.
   - `Get_Position` on the previous line already dereferences the physical
     object.
   - Both methods are non-virtual.
   - The probe has exactly one call site.
2. **No lasting effects.** The probe body only calls readers, constructs
   locals, and fills a scratch list that it frees.
3. **The collection list is transient.** The probe's one shared side effect
   is the `CullSystemClass` collection list (`wwmath/cullsys.cpp:140-150`).
   - `DynamicCullingSystem` is the single `PhysGridCullClass`
     (`wwphys/pscene.cpp:241`).
   - Every reader of its collection resets it first: scene collect helpers,
     projectors, grid casts and intersections, and
     `Re_Partition`/`Load` through `Collect_And_Unlink_All`.
4. **No debug statistics change.** `GRIDCULL_NODE_*` statistics exist only
   under `WWDEBUG`, which the build never defines.

## Change

| File | Change |
| --- | --- |
| `port/patches/combat-tut1-pathfind-cost.patch` | Vita-only (`__vita__`) ordered zero-fuzz patch to `soldier.cpp`. Includes the header and adds a skip branch before the original probe branch. Removes no original line. |
| `staging/combat/soldier.cpp` | Same edit applied to the tracked copy |
| `tools/stage_sources.sh` | One apply line after the last combat patch (face-action clamp). No sha anchor, so later integrations do not need to edit it. |
| `port/compatibility/include/renegade_vita_pathfind_cost.h` | New header-only flag reader, counters and bounded census. No CMake change. |
| `tools/test_pathfind_cost_contract.py` | 14 pure-Python tests |

Flag: `ux0:data/renegade/user/config/pathfind-cost-v1.flag`.

- Format: exactly `RVPF1 <hex>\n` (8 bytes, LF). The parser masks the value
  to the known bit 0.
- A missing or malformed file selects the default mask, 1.
- The flag is read once, at the first awake soldier Think.
- One line is logged when the flag is read:
  `A3.5 pathfind-cost: configured version=1 mask=… source=default|file|malformed …`.
- Census: `A3.5 pathfind-cost: census mask= zone_entries= probes= skipped=`.
  - One line per 16,384 evaluations, at most 128 lines.
  - Disabled in the M00 demo profile, whose log writes sync on the game thread.
- Default on: justified by the state-identity argument above.

## Ledger-style entry

| Field | Value |
| --- | --- |
| Hypothesis | Removing one dynamic-grid collect per awake, unghosted soldier per frame lowers Combat-stage time in proportion to the awake soldier count |
| Risk | No gameplay or physics semantics change (state-identical). Residual risk is limited to a compile error, since this was not compiled. |
| Estimated gain | About 3–15 µs per probe on Cortex-A9. With 10–25 awake soldiers that is about 0.03–0.4 ms/frame (≤ 10 % of the 4.1 ms Combat average). Unmeasured. |
| Measure | `A3.6 frame-profile` scope **`Coordination Zone`** (wraps exactly this code), `A4 campaign pacing` combat=, `A4 combat casts` soldiers awake, and the census `skipped/probes` ratio |
| Decision | Pending hardware A/B |

## Tutorial NPC/actor counts (Mission00.cpp and the dev208 LDD receipt)

**Placed at load.** `m00_tutorial.ldd` holds 74 objects, which agrees with the
dev230 load summary (22 soldiers, 0 vehicles):

- 22 soldiers:
  - Commando.
  - Instructors: Logan 400005, Sydney, Gunner (`GDI_RocketSoldier_2SF`),
    `GDI_Engineer_2SF`, Petrova, Mobius.
  - `GDI_Engineer_0`.
  - 4 `GDI_MiniGunner_0`; 3 of them run `MTU_GDI_Soldier`, with enemy-seen
    and innate disabled.
  - 10 `Nod_Minigunner_0`.
- 31 star trigger zones, 4 buildings, 4 gates, 2 ladders, and 8 power-ups.
- 9 spawners, including 3 × "M00 Basic Minigunner Infinite".

| Segment | Extra actors (Mission00.cpp) | Path work |
| --- | --- | --- |
| Throughout | One Orca or Chinook flyover every 10–30 s (:278-306) | waypath |
| Logan / Sydney escorts | Instructors only, mostly authored waypaths (27 `WaypathID` uses) plus 1 s wait timers | waypath or one solve per Goto |
| Gunner range, 9 rounds (:444-799) | At most 3 targets alive. Either 3 `Nod_Minigunner_0`, or a `Nod_Buggy` plus 1–2 minigunners (grenade/rocket/C4), or a `Nod_Light_Tank` plus 2 (ion). Innate is disabled (:3548); some walk waypaths 400105/400115/400129, and the "miss" ones attack the star. | waypath only |
| Vehicles (HMVV / medium tank) | Player vehicle (:967/:978) plus 6 innate-disabled squish minigunners (:999-1039) | none |
| Apache | `NOD_Apache` (:1814, :2495) | none |
| Finale / mock invasion | Lieutenant (:1112), 2 officers (:1148-1160), HMVV (:1162), and 3 spawned minigunners that follow the star and respawn on death (:1167-1192, `MTU_Nod_Soldier` :3772-3800) | **the only repeated dynamic solves** (follow re-path rule) |

Estimated peak concurrency is about 25–30 soldiers; hibernation removes the far
ones. dev240 logs the awake counts per window.

## Verified and unverified

Verified, with no compiler involved:

- `python3 -m unittest tools.test_pathfind_cost_contract`: 14/14 OK. The
  tests check:
  - the zero-fuzz reverse and forward round-trip of the tracked file;
  - registration;
  - the flag parser model;
  - the no-op condition;
  - the read-only probe body;
  - the reset-before-read scan;
  - an exhaustive control-flow model.
- `renegade_patch_inventory.py`: registry PASS with 578 patches. The staging
  receipt is now stale by design, and the coordinator regenerates it.
- The stage-sources, fast-candidate and mission-teardown contract tests pass.

Unverified:

- No ARM or host compile. The header and patch were reviewed by hand only.
- No runtime run.
- No measured gain.
- `Coordination Zone` share and awake counts on dev240+ are unknown.

## Hardware A/B (fixed tutorial route)

1. With no flag file, play the route: Logan → Sydney → range (handgun and
   autorifle rounds) → HMVV squish → mock invasion. Confirm that
   `pathfind-cost: configured … mask=1 source=default` appears, then keep the
   census lines, `A3.6 frame-profile` (`Coordination Zone` time and calls),
   `A4 campaign pacing`, and `A4 combat casts`.
2. Write the 8 bytes `RVPF1 0\n` to
   `ux0:data/renegade/user/config/pathfind-cost-v1.flag`, relaunch, and repeat
   the route. Expect `mask=0` and `skipped=0`.
3. Compare the `Coordination Zone` time per frame and Combat-stage p50 and p95.
   Behaviour check: soldiers still pass each other at ladder entrances,
   Logan's follow segments still work, and the invasion soldiers still chase
   the player.
