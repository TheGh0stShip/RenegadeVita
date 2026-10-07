# Tutorial round 1: PARTICLE_EMITTERS (RVPE1)

Status: source change, pure-Python tests and a static retail inventory only.
Nothing was compiled, staged by script, run in Vita3K or run on a Vita.
Every cost figure below is an estimate.

Base: `tutorial-r1/base` (45c6cf5, main + FPS round 4 / A3.5-dev240).
Line numbers refer to the staged `part_buf.cpp` before this patch unless
marked "patched".

## Findings

### 1. Particle LOD already follows the original Low tier; no new particle default is justified

- Original particle detail has no runtime effect. Commando stores
  `Particle_Detail` (`dlgconfigperformancetab.cpp:590,617`) and only logs it
  (`shutdown.cpp:120,237`). WWConfig auto-config writes 2/1/0
  (`Tools/WWConfig/PerformanceConfigDialog.cpp:979-988`), but nothing reads it.
  The Vita tab disables that slider (`staging/commando/dlgconfigperformancetab.cpp:333`).
- Real particle LOD works like this. Each buffer is a dynamic physics-scene
  object (`pscene.cpp:942-969`). It enters `Optimize_LODs` with the dynamic
  polygon budget (`pscene.cpp:1203-1233`) through `Prepare_LOD`
  (`part_buf.cpp:1219-1262`) and the 17 screen-size thresholds
  (`Calculate_Cost_Value_Arrays`, `1306-1369`).
- The port already restores the original Commando table and
  `Set_Default_Remove_On_Complete(false)`
  (`a31_vita_runtime.cpp:5328-5338` = `commando/init.cpp:157-178,873-877`).
  The startup gap in `DEEP_AUDIT_FOLLOWUP.md` is closed.
- FPS round 4 set the dynamic budget to 0 (original slow-PC Low). At budget 0
  `predlod.cpp:334-360` lowers every visible buffer to its screen-size
  minimum, so a buffer draws `lod/16` of its particles:
  - About 1 % of the screen: 3–4/16.
  - About 5 %: 5/16.
  - About 100 %: 11/16.

  `ProjectedArea` starts at 0 and is filtered by 0.9/0.1 per frame
  (`part_buf.cpp:1254-1255`). New short-lived effects (muzzle flashes,
  impacts) therefore start at 1–4/16 and climb over about 10–20 frames.
  This is the original Low behaviour, but it looks visibly thinner than
  dev238 (budget 4000).

  The only knobs are original ones. Geometry detail in Options raises the
  budget. Surface Effects (`surfaceeffects.cpp:535`: No Emitters suppresses
  impact/footstep emitters) stays active on Vita at Full. Neither needs a
  new flag.

### 2. Retail emitter inventory: buffers are small

Source: `tools/audit_tutorial_particle_emitters.py <retail Data>`. It reads
`M00_Tutorial.mix`, `always.dat`, `Always2.dat` and `always3.dat` read-only.

- 414 emitter definitions. All are tri (344) or quad (70); there are no
  line or line-group emitters.
- MaxNum is the original formula, `burst·rate·(life+1)` capped by max
  emissions (`part_emt.cpp:108-111`):
  - Median 9, p90 40.
  - Maximum 345 (`e_tib_bullet`), then `e_flamethrower` 195 and
    `e_rockettrail` 100.
- Continuous emitters allocate about 2.0× their steady-state live count
  (median).
- Ten emitter types are referenced by the M00 level. All are small:
  - `e_flame04` 21, `e_ref_fire` 20, `e_flame`/`e_smolder1` 12,
    `e_flame01` 10.
  - Sparks, flares and arcs: 2–4.
- 69 types are referenced from `always.dat` INIs (surface effects and so on):
  maximum 25, median 8.

Per-particle simulation is therefore cheap per buffer. The per-buffer fixed
costs dominate: Emit, Prepare_LOD, bounding box and the point-group draw
setup. Large buffers belong to weapons (rocket trail, flamethrower), which
the Gunner range and vehicle segments do exercise.

### 3. Wasted visual work under decimation

`Render` calls `Update_Visual_Particle_State` (`2475-2727`) for every live
particle whenever `DecimationThreshold < LodCount - 1` (`847`). However,
`Generate_APT` (`895,900`) and therefore `PointGroupClass::Render`
(`pointgr.cpp:779-822`) only read particles with
`PermutationArray[i & 15] >= DecimationThreshold`.

`Combine_Color_And_Alpha` copies and clamps all MaxNum slots
(`914-940`), live or not. Under budget 0, a buffer at LOD `k` reads `k/16`
of its slots, so `(16-k)/16` of the keyframe evaluation is never read.

### 4. Original defect: stale visual state for cloned small buffers

The two constructors set `LodCount` differently:

- Main constructor: `LodCount = 17` (`225`).
- Copy constructor: `LodCount = MIN(MaxNum, 17)` (`444`).

For a clone with MaxNum < 17 at its lowest LOD, `DecimationThreshold`
is `LodCount-1` (≤ 15). The visual update is skipped, yet the active point
table still draws `16-(LodCount-1)` of 16 slots with stale or never-written
(`new T[]`, uninitialized) colour, size and frame values.

Tutorial emitters are created from definitions (`part_ldr.cpp:1800-1802`),
so they use the main constructor and are not affected. Clones exist on the
HLOD/collection copy paths (`hlod.cpp:1299,1314`, `collect.cpp:236`) and in
the Vita M13 template caches (`hlod.cpp:268` `ag_fiery_ex06`,
`agg_def.cpp:252`). Budget 0 keeps those clones at minimum LOD.

The pointgroup lifecycle crash (`POINTGROUP_LIFECYCLE_CRASH.md`) is
unrelated: init and shutdown order are untouched.

## Change

`port/patches/ww3d2-tut1-particle-cost.patch` applies to the final
`part_buf.cpp`, registered in `tools/stage_sources.sh` after the last ww3d2
patch. The tracked staging file is updated to match. The new header
`port/compatibility/include/renegade_vita_particle_cost.h` holds the flag
grammar and reader.

Flag: `ux0:data/renegade/user/config/particle-cost-v1.flag` =
`"RVPE1 <hex>\n"`. The build default is `RENEGADE_VITA_PARTICLE_COST_DEFAULT`
= **5**.

| Bit | Default | Effect |
| --- | --- | --- |
| 0 (1) | **on** | Skips keyframe evaluation for particles the same render's active point table excludes. All seven keyframe cursors still advance (patched `2648-2668`), so the change stays exact even if particle ages are not in order. Combines colour and alpha only over live slots (patched `1011-1056`). |
| 1 (2) | off | Runs the visual update whenever a particle can be drawn (`DecimationThreshold < 16`, patched `923-932`). This makes no change when LodCount is 17; it fixes finding 4 for clones. |
| 2 (4) | on | Every 900 WW3D frames, logs one line: `A3.6 particle-cost: frames renders visual evaluated skipped drawn empty stale_lowest_lod corrected combine_saved mode`. The flag is read once, during emitter construction, and logged with the line `A3.6 particle-cost: version=1 mode=…`. |

Bit 0 is on by default because it is bit-identical for every value the point
group reads; the reference model proves this. It reads skipped slots only
through the active point table, which excludes them, or through the
small-clone stale path. Any slot that path reads has a permutation entry
≥ `LodCount-1`, which is above every threshold at which an update runs, so
both variants always wrote it.

Bit 1 changes pixels, so it is off by default. Emission, kinematics,
bounding boxes, LOD selection, sorting and submission are untouched.

## Hypothesis ledger entry

- **Hypothesis**: Under the budget-0 default, most keyframe evaluation and
  combine work in `ParticleBuffer::Render` is never read. Skipping it exactly
  lowers particle CPU time without changing any pixel.
- **Risk**: Very low. The patch is output-identical by construction, and the
  model and source contract pin it. The residual risk is a C++ transcription
  mistake, because nothing has been compiled. Bit 1 changes visuals for
  clones only.
- **Estimated gain (unmeasured)**: Small, because buffers are small.
  - Tutorial base fires, sparks and smoulder: < 0.05 ms per frame.
  - Gunner range rockets and other large trails (MaxNum 100–345) at
    mid-distance: about 0.05–0.3 ms in effect-heavy frames.

  The main value is evidence: the telemetry together with the existing
  `ParticleBuffer::Render` and `PartlicleEmitter::Emit` (sic) profiler scopes
  shows whether particles matter at all on this route.
- **Measure**: Same route, same seed. Compare:
  - p50/p95/p99 `ParticleBuffer::Render` and `PartlicleEmitter::Emit` scope
    time (RVFP1 profiler).
  - Frame time.
  - Telemetry `evaluated`/`skipped`/`drawn` per frame.
- **Adopt** if p95 `ParticleBuffer::Render` drops and the visuals match;
  otherwise keep the telemetry only.

## Verified vs unverified

Verified, host only:

- `python3 -m unittest tools.test_vita_particle_cost` passes 8 tests (about 15 s).
  - A reference model of the circular buffer, `Get_New_Particles`,
    `Kill_Old_Particles`, visual update, APT, aliased in-place clamp and
    point-group reads. It covers 120 seeds, 1–2 renders per frame, and both
    17-level and cloned LodCounts.
    - Bit 0 keeps every consumed value identical, including out-of-order ages.
    - Bit 1 changes only clone lowest-LOD renders, and only to fresh values.
  - Source contracts:
    - Skip-branch cursor walks mirror the evaluation walks in order.
    - The original test is retained.
    - Flag grammar and default are pinned.
    - The flag is read in the constructor.
    - The patch reverses and re-applies at `--fuzz=0` to the tracked staging
      file.
  - Mutation check (scratch): removing the cursor walks, using `<=`, or
    dropping the wrapped span fails 129, 337 and 309 of 400 scenarios.
- `tools.test_vita_particle_keyframe_guard` passes.
- `renegade_patch_inventory.py --count` reports 578 (the new patch parses).

Unverified:

- No ARM/host compile.
- `tools/stage_sources.sh` was not run, and `staging/PATCH_INVENTORY.json`
  was not refreshed. The coordinator must regenerate the receipt.
- No Vita3K or hardware run. There is no measured gain, and visual parity is
  unconfirmed.
- Two existing tests (`test_original_dazzle_lifecycle`,
  `test_requested_mission_owner_contract`) error in this worktree because
  `upstream/CnC_Renegade` is empty. This is environmental, not caused by
  this change.

## Hardware A/B (tutorial route: Logan → Sydney → Gunner range → Mobius → HMVV → base)

1. Run with the default (no flag file). Collect the `A3.6 particle-cost`
   lines and the `A3.6 frame-profile` lines for `ParticleBuffer::Render` and
   `PartlicleEmitter::Emit`. Expected: `stale_lowest_lod=0` on the tutorial,
   since it has no clones.
2. Run again with `RVPE1 4` (original evaluation, same telemetry) and compare
   scope p50/p95 at the Gunner range (rocket trails) and the burning base.
   Visuals must be identical.
3. Optional, for visuals: set Geometry detail to Medium or High and watch
   particle density and the `drawn/(evaluated+skipped)` ratio. Set Surface
   Effects to No Emitters during range fire to measure impact-emitter cost.
4. For the bit-1 fix, use `RVPE1 7` in M13 near `ag_fiery_ex06` explosions
   and expect `corrected>0`. Check visually for frozen or garbage
   small-effect particles with `5` versus `7`.
