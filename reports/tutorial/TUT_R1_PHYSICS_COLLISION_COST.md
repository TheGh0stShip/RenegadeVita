# TUT-R1-05: physics and collision cost in the tutorial (PHYSICS_COLLISION_COST)

Base: `45c6cf5`, which is `tutorial-r1/base` (main plus the FPS round-4
dev240 candidate). The worktree was created from main at `cde0b86`, so
`git merge --ff-only tutorial-r1/base` could not fast-forward. Branch
`tut-r1/physics-collision-cost` was created at `45c6cf5` instead.

Nothing in this report was compiled, run on Vita3K or run on hardware.

## Result

**This work found no runtime change worth making, so no runtime code changed.**

- The port adds **no per-frame physics-scene collision or visibility query**.
- Every per-frame `Cast_Ray`, `Cast_AABox` and `Cast_OBBox` in the tutorial comes
  from the original Combat, WWPhys or WW3D code.
- Each original query that was checked already avoids repeating identical
  work (see the table below).
- Hibernation runs as originally designed. The tutorial's soldier scripts turn
  it off on purpose.

The deliverable is therefore developer-loop tooling:

- a static audit that keeps the port free of unregistered queries;
- a log analyzer that converts the existing telemetry into windowed physics
  and Combat cost for hardware A/B runs on the tutorial route.

Flag prefix `RVPH1` (`physics-cost-v1.flag`) is **reserved but not used**. No
code reads it. Under the new audit policy, any future per-frame diagnostic
query added by the port must sit behind this flag.

## Findings (file:line, worktree staging)

### Port-added queries (audit: `tools/audit_physics_scene_queries.py`)

The audit scanned:

- every port-owned C/C++ file under `port/`;
- all 14,570 added lines of the 3,261 hunks in `port/patches/*.patch`.

It found exactly **one** query:

- **Location:** `port/platform/a31_gameplay_boundary.cpp:908`, call
  `scene.Get_Vis_Table_For_Rendering(camera)`, inside the A3.6 vis-census.
- **Cadence:** it runs on every 120th render frame, for at most 1,024 samples
  (guard at :904).
- **Duplicate work:** it repeats the PVS lookup that `Pre_Render_Processing`
  made at :1096 for the same camera. That lookup is
  `StaticAABTreeCullClass::Find_Vis_Tile`, which casts one AABox and one ray
  against the static tree (`staticaabtreecull.cpp:483-505`), followed by a
  cached table fetch (`vistablemgr.cpp:301`).
- **Other census work:** it also runs about 531 frustum overlap tests. Static
  and dynamic objects number 495/36 in the tutorial.
- **Verdict:** it only feeds diagnostics, and it is sampled. Its average cost
  is negligible, and it logs its own `census_us`. No change is justified until
  hardware shows `census_us` above 1 ms.

Other port diagnostics named in the brief contain no collision queries:

| Diagnostic | Evidence | Per-frame cost |
| --- | --- | --- |
| Scene cast counters | `pscene_collision.cpp:144/198/251`, one increment per cast; snapshot at `a31_gameplay_boundary.cpp:801/838` | one global increment per cast |
| Vehicle proximity (dev91) | `vehicle.cpp:2259/2270`; timing and star distance compiled out (`RENEGADE_VITA_DETAILED_TIMING` undefined); init and transition logs capped at 64/96 | none |
| Target-box projection (dev92) | `hud.cpp:1548-1559` returns after 64 logs | one call plus compare per target box |
| M13 nearby-actor snapshot | `a31_vita_runtime.cpp:7254`; M13 only, every 120-frame checkpoint, distance math only | none in the tutorial |
| Render trace object census | `a31_gameplay_boundary.cpp:976-986`, every 120 frames | none |
| Input/aim boundary | No port aim assist or crosshair raycast exists; targeting rays are original (`ccamera.cpp:1057`, `weapons.cpp:1776`) | n/a |

Commit `a707f39` (another worktree branch, not in this base) adds a
call-site guard for the target-box diagnostic. In this base the function
still returns early after its log budget, so nothing casts.

### Original per-frame queries in the tutorial (not duplicated)

| Query | Site | Existing reuse or limit |
| --- | --- | --- |
| Camera sweep | `ccamera.cpp:889` `Cast_OBBox` (retries at :897 only on StartBad while interpolating) | once per frame; `combat.cpp:776/786` updates the camera once |
| Camera targeting | `ccamera.cpp:1057` `Cast_Ray` | once per frame |
| Weapon help | `ccamera.cpp:1246`, about 2 Hz (:1153) | Easy difficulty only (:1164) |
| Reticle target | `weapons.cpp:1776` `Display_Targeting` | once per frame |
| First-person hands pullback | `weaponview.cpp:702` | once per frame (`combat.cpp:818`) |
| Ambient sound | `SoundEnvironment.cpp:148` | once per frame, only while used |
| Lens flares | `combatdazzle.cpp:93`, called from `dazzle.cpp:968` | one ray per facing, unblinked dazzle; render phase |
| Soldier ground probe | `phys3.cpp:1259-1265`, `Check_Ground` | cached until `GroundState.IsDirty` |
| Soldier sleep | `phys3.cpp:1167` | asleep, uncontrolled bodies skip the timestep |
| Vehicle wheels | `wheel.cpp:307-329`, `Intersect_Spring` | skipped when the spring endpoints are bit-identical (:320); midpoint integration needs two different states per step |
| Dynamic vis ID | `dynamicphys.cpp:137-150` | at most 4 Hz per object (:63) |
| PVS lookups | `pscene_vis.cpp:242-255` (render) and `messages.cpp:1236/1355` (hibernation) | two different sample points (camera near plane vs player head); not reusable |
| Physics substeps | `pscene.cpp:138` (`MAX_TIMESTEP = 1/15`) | one step per frame unless the frame takes more than 66.7 ms |

`UpdateOnlyVisibleObjects` (`pscene.cpp:218/365`) would skip vehicles that are
not visible. It is an original console toggle and is off. Enabling it
changes simulation, so it is out of bounds.

### Hibernation

- The original single-player rule (`messages.cpp:1355-1440`) wakes every
  object that is both in the player's PVS and within 300 m.
- An object then sleeps 30 s after its last wake (`physicalgameobj.cpp:76-77`,
  :759-765, :974-984).
- Sleeping objects skip Think, Post_Think and Generate_Control
  (`gameobjmanager.cpp:395/432/475`). Their physics timestep still runs
  (`pscene.cpp:358-370`).
- In the tutorial, **`MTU_Tutorial_Instructor::Created` (`Mission00.cpp:1269`)
  and `MTU_GDI_Soldier::Created` (`Mission00.cpp:3238`) call
  `Enable_Hibernation(false)`**. Instructors and GDI soldiers therefore never
  sleep, by original design. The save path stores `HibernationEnable`.
- The FPS round-4 counter
  `A4 combat casts ... soldiers_awake/hibernating_per_frame` should therefore
  show almost all soldiers awake in the tutorial. That is not a Vita defect.
  There is no hibernation gain available without changing semantics.
- Tutorial PVS data exists: the dev230 log reports a vis table of 1684/347.

### What device evidence already shows (dev230 tutorial run, derived figures only)

Produced by `tools/analyze_physics_cost.py` from the private log. No log
contents are committed.

- **Frame time:** the median is about 30.2 ms. Render dominates: the
  cumulative render stage averages 22–28 ms, against 3.3–4.6 ms for sim.
- **Combat stage, per 120-frame window:** median 3.2 ms, p90 7.5 ms,
  maximum 22.7 ms. The median is about 11 % of the frame.
- **Bursts:** 12 windows reached 8 ms or more. They cluster in the Gunner-range
  weapon segment (frames 12,360–17,000) and in a late firefight
  (frames 27,478–27,958).
- **Network stage:** median 0.30 ms. This includes `Hibernation_Think`.
- **For comparison, M13 (dev238):** Combat median 9.7 ms, about 19 % of a
  51.6 ms frame.

The physics share inside these bursts is **not yet attributed**. Candidate
sources are bullets and instant-hit rays, explosion victim rays, vehicle
wheels on range vehicles, and AI. dev230 predates the live engine profiler
scopes and the cast counters.

## Changes

| File | Purpose |
| --- | --- |
| `tools/audit_physics_scene_queries.py` | Static audit described below |
| `tools/analyze_physics_cost.py` | Log analyzer described below |
| `tools/test_physics_cost_tooling.py` | 13 pure-Python tests |
| `reports/tutorial/TUT_R1_PHYSICS_COLLISION_COST.md` | This report |

The audit (`tools/audit_physics_scene_queries.py`):

- strips comments and string literals;
- ignores pure `CollisionMath::` helpers and argument-less accessors;
- scans port sources and only the added lines of port patches, reporting
  new-file line numbers;
- requires each query to be registered with its count and cadence;
- fails on unregistered, stale or miscounted entries;
- fails on any per-frame diagnostic query that has no flag.

The analyzer (`tools/analyze_physics_cost.py`):

- turns cumulative `A4 campaign pacing` lines into windows, and detects
  restarts;
- uses the exact `A4 combat casts` `combat_avg_us` whenever a checkpoint
  matches;
- reads cast counts and awake/hibernating counts per frame;
- reads `A3.5 perf` percentiles, dropping the line the runtime prints twice;
- reads `A3.6 vis-census`, and physics scopes from the `A3.6 frame-profile`
  line;
- merges adjacent burst windows;
- compares two runs with `--compare`.

Its tests:

- render the runtime's own printf format strings from
  `a31_vita_runtime.cpp`, `a31_gameplay_boundary.cpp` and
  `renegade_vita_frame_profile.cpp`;
- parse the rendered lines, so a format change breaks the test.

No staging, patch, `stage_sources.sh`, CMake or runtime source was changed.

## Hypothesis ledger entry (for the coordinator to transcribe)

| ID | Hypothesis | Evidence | Decision |
| --- | --- | --- | --- |
| TUT1-PH1 | Port-added per-frame raycasts inflate tutorial Combat cost | Audit finds one port query, sampled at 1/120 (vis-census) | **Rejected** (source). No change. |
| TUT1-PH2 | Hibernation is inactive on Vita, so extra soldiers stay awake | Original rule active; tutorial scripts disable it (`Mission00.cpp:1269/3238`) | **Rejected as a port defect.** Expected behavior. |
| TUT1-PH3 | Identical same-frame original queries can be reused | Camera, targeting, ground, wheel, vis-ID and PVS paths checked; each already caches or uses different inputs | **No provable duplicate**. Deferred. |
| TUT1-PH4 | Tutorial burst windows (8–23 ms Combat) come from weapons fire and range vehicles, not steady physics | dev230 windows plus player state; attribution unmeasured | **Open.** Measure with dev240 telemetry. |

- **Risk:** none. There is no runtime change.
- **Estimated in-game gain:** 0 ms.
- **Developer-loop gain:** one command produces windowed physics cost and an
  A/B comparison. Previously this took manual log arithmetic.

## Verified vs unverified

Verified on the host. All of this is pure Python, with no compiler:

- `python3 -m unittest tools.test_physics_cost_tooling`: 13 tests, OK.
- `python3 tools/audit_physics_scene_queries.py`: PASS (hits=1, registered=1).
- The analyzer parses the existing dev230 and dev238 device logs locally.
  The figures above come from those runs. No contents were committed.

Unverified:

- All runtime behavior and the burst attribution.
- Whether the frame-profile top 16 includes physics scopes in tutorial
  frames. Render scopes may crowd them out.
- `tools/test_sim_hotpaths_contract.py` was not run, because it invokes
  `g++ -E`.

## Hardware A/B steps (tutorial route, dev240 or the integrated tutorial candidate)

1. Use a fixed route:
   - Logan, then Sydney;
   - the Gunner range: fire pistol, rifle, sniper, rocket and beacon;
   - Mobius;
   - enter and drive the HMVV;
   - the base buildings.
2. Pull `ux0:data/renegade/user/logs/a35-dev240-runtime.log` (or the
   candidate's own log), then run:
   `python3 tools/analyze_physics_cost.py <log> --windows`
3. Read these fields:
   - `combat_us` median/p90/max, and the bursts;
   - casts per frame (`ray_cull`, `aabox_cull`, `obbox_cull`);
   - soldiers awake/hibernating (expect awake to be about the soldier count);
   - `vis-census` `sector_missing_fraction` and `census_us`;
   - the physics scopes `Scene`, `PhysicsScene::Update`, `Phys3::Timestep`,
     `VehiclePhysClass::*`, `Dazzle::Render`, `Bullets`, `Cast_Ray`.
4. Profiler A/B: write `RVFP1 0` to
   `ux0:data/renegade/user/config/frame-profile-v1.flag`, repeat the route,
   then run `--compare <default.log>`. This separates profiler overhead from
   physics in burst windows.
5. Decide the next step from the results:

   | Observation | Next step |
   | --- | --- |
   | `ray_cull` in bursts is far above quiet windows, and `VehiclePhysClass::Compute_Force_And_Torque` leads | Study static AABTree ray traversal (results must stay identical) |
   | `Dazzle::Render` is large | Dazzle occlusion rays are the next target (original visuals must be preserved) |
   | `census_us` exceeds 1000 | Gate the vis-census under `RVPH1` |

## Shared files touched

None. All four files are new. The only possible conflict is another agent
adding a file with the same name under `reports/tutorial/`.
