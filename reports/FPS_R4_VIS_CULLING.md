# FPS round 4: VIS_CULLING, original precomputed visibility on Vita

Status: audit complete. One diagnostic-only change (a sampled census). Nothing
here has been measured on hardware.

## Hypothesis

The port might have disabled or bypassed the original PVS / vis-sector tables
or the static AABTree culling, so the Vita would submit objects that the
original PC game rejects.

## Verdict: the original VIS and culling are active and unmodified

- **Defaults are original.** `VisEnabled(true)`, `VisInverted(false)`,
  `VisResetNeeded(false)`, `VisSectorFallbackEnabled(true)`
  (`staging/wwphys/pscene.cpp:188-196`). Hierarchical vis is `true`
  (`staging/wwphys/physaabtreecull.cpp:48`). `UMBRASUPPORT 0` is the upstream
  value (`staging/wwphys/umbrasupport.h:42`).
- **Sources are pristine.** These are byte-identical to upstream after CR
  stripping (test-enforced): `pscene_vis.cpp`, `staticaabtreecull.{cpp,h}`,
  `dynamicaabtreecull.cpp`, `physaabtreecull.{cpp,h}`, `physgridcull.cpp`,
  `vistable.{cpp,h}`, `vistablemgr.{cpp,h}`. `pscene.cpp` differs only in a
  camera-shake guard. `pscene_saveload.cpp` differs only in status text and
  dynamic-load error returns; the vis chunk handling is unchanged.
- **Nothing turns vis off.** The only `Enable_Vis`, `Invert_Vis` and
  `Lock_Vis_Sample_Point` callers are the original console commands
  (`staging/commando/consolefunction.cpp:495,511,609`). No added patch line or
  port source calls a vis toggle (test-enforced).
- **Load.** `Load_Level_Static_Data` clears `VisResetNeeded` and loads
  `PSCENE_SD_CHUNK_VISIBILITY_DATA` into `VisTableManager`
  (`pscene_saveload.cpp:208-245`). Decompression uses the original LZO
  (`vistable.cpp:432`, `cmake/A30OriginalSources.cmake:238-240`). The static
  AABTree `Add_Object` keeps upstream's commented-out `Reset_Vis`, so loading
  static objects does not invalidate vis.
- **Per frame.** `A31_Interactive_Run_Render_Frame`
  (`port/platform/vita/a31_vita_runtime.cpp:6474`) mirrors
  `GameModeManager::Render` and calls `Pre_Render_Processing`. That calls:
  - `Get_Vis_Table_For_Rendering(camera)`, which finds the vis sector by a
    ray/box cast below the near plane;
  - the static hierarchical PVS+frustum and dynamic grid PVS+frustum
    `Collect_Visible_Objects`;
  - `Optimize_LODs` (`pscene.cpp:1123-1145`).
- **Per mesh.** `MeshClass::Render` keeps the original frustum `Overlap_Test`
  before the Vita submit (`staging/ww3d2/mesh.cpp:733-736`).

**Physical dev238 evidence (read-only).**
- `runtime-observation-3.log:1058` shows M13 loaded with
  `static/dynamic/lights=423/167/42 vis=2682/198`: 2682 vis object ids and 198
  sectors from retail data.
- Gameplay submits about 65 meshes and 5.7k triangles per frame
  (`meshes=7775`/120 frames at line 1092).
- That fits active culling, but no breadcrumb proved a non-NULL PVS on any
  frame. The change below closes that gap.

## Change made (diagnostic only; culling behaviour unchanged)

- `port/platform/a31_gameplay_boundary.cpp` adds
  `Sample_Original_Visibility_Census`, compiled only with
  `__vita__ && !RENEGADE_VITA_M00_DEMO`.
- It runs every 120 render frames, right after `Pre_Render_Processing` and
  before `Begin_Render` / `CombatManager::Render` (which applies camera
  shakes). It is capped at 1024 lines, about 340 KB.
- It logs: `A3.6 vis-census: frame vis_enabled inverted sector missing fallback pvs_true=N/bits static total/ws/in_frustum/pvs_hidden/vis_saved/collected dynamic total/in_frustum/pvs_hidden/vis_saved/collected census_us`.
- `vis_saved` counts objects in the frustum that the PVS rejects, i.e. the
  over-draw VIS removes compared with frustum-only culling.
- `tools/test_vis_culling_contract.py` (new, 5 cases) checks:
  - the original defaults;
  - that the PVS is passed to both culling systems;
  - that no patch or port source toggles vis;
  - that the census is read-only and runs before the camera is changed;
  - that the vis sources match upstream (skipped without upstream).

## Risk and invalidation argument

- `Get_Vis_Table_For_Rendering` is idempotent for an unchanged camera. It
  gives the same sector and writes the same `LastValidVisId` /
  `VisSectorMissing` the render call just wrote.
- The table lookup is a cache hit (add-ref, then release). LRU timestamps
  never advance because the original never calls `Notify_Frame_Ended`.
- The census avoids `Get_Vis_Table_Size/Count`, which run
  `Internal_Vis_Reset()`.
- The visible lists are already built, so rendering is unaffected.
- Cost: one box cast and one ray cast plus about 590 frustum/AABox tests per
  sample. Estimate: under 0.3 ms per sample, about 2 µs per frame amortized;
  `census_us` reports the real figure.

## Pre-existing observation (not changed)

The trace block in `A31_Interactive_Run_Render_Frame` calls
`scene->Get_Vis_Table_Size()` and `Get_Vis_Table_Count()` on every frame. Both
run `Internal_Vis_Reset()`. This matters only if `VisResetNeeded` is true,
which happens only for a level with the obsolete LZHL vis chunk
(`vistable.cpp:429`):
- the original game would skip vis for that level;
- the port would reset it (drop tables, re-partition static trees, reassign
  ids).
Both end up frustum-only. No retail evidence of that chunk exists, so this is
low risk. Optional fix: read those counts once per scene in the existing
120-frame census block.

## Remaining over-draw sources (not VIS-cullable by design)

- **Sky/background:** `WW3D::Render(BackgroundScene, ...)` at
  `staging/combat/combat.cpp:844`, a separate SimpleScene with no PVS.
- **Dazzles** (`combat.cpp:856`) and **weather** (`combat.cpp:814`).
- **Static translucent sort lists:** `mesh.cpp:716`.
- **Shadows/projectors:** off by default on Vita. Scene defaults are
  `SHADOW_MODE_NONE` with projectors disabled (`pscene.cpp:202-204`), and the
  Vita `SystemSettings::Apply_All` is a no-op
  (`port/platform/a4_frontend_lifecycle_boundary.cpp:117`). The PC default
  BLOBS_PLUS therefore never applies.
- **LOD budgets:** default 4000/4000 (`pscene.cpp:144-145`); the PC registry
  default for dynamic is 3000 (`staging/commando/shutdown.cpp:109`). The
  original lever `Set_Polygon_Budgets` is persisted by
  `RenegadeVitaOptions::Apply_Performance`. At about 5.7k triangles per frame
  the budgets are rarely binding.
- **Terrain chunks** (world-space meshes such as `L00.AR01_ROAD`) are already
  PVS- and frustum-culled. Their cost is per-mesh CPU submission, which the
  renderer agents own.

## Expected gain

None from culling (unmeasured): VIS is already original and active. The
bottleneck stays the renderer's per-mesh CPU cost, not the object count. The
census supplies the missing hardware proof and measures how much over-draw VIS
saves.

## Tests run

- `python3 -m unittest tools.test_vis_culling_contract`: 5 OK. The upstream
  identity case ran with a temporary upstream symlink, since removed.
- `python3 -m unittest tools.test_vis_culling_contract tools.test_npc_path_frame tools.test_a4_original_frontend_contract`:
  27 OK.
- `tools.test_mission_conversation_diagnostics_contract`: one failure,
  `test_direct_vita_action_and_reload_are_not_the_same_button`. It asserts on
  `directinput.cpp`, which this change does not touch, so it is pre-existing.
- ARM TU build of `port/platform/a31_gameplay_boundary.cpp` (VitaSDK g++ 15.2,
  recorded fast-candidate flags, `-Werror=format`): no diagnostics in the
  changed lines. It was run as a direct command because the sandbox refused
  the wrapper script.

## Hardware measurement to take

1. Run M13 (and M01) for at least 2 minutes, then
   `grep "A3.6 vis-census"` the runtime log.
2. Expect `vis_enabled=1`, `sector` ≥ 0 and `missing=0` on most lines,
   `pvs_true` well below `bits`, static `vis_saved` > 0 when looking along
   streets or into buildings, and `census_us` < 500.
3. Long stretches of `sector=-1` or `missing=1` would be a real finding:
   vis-sector casts (COLLISION_TYPE_VIS meshes) would be failing, leaving only
   the stale-sector fallback or frustum-only culling.
