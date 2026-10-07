# FPS round 4: LOD_TRIANGLE_BUDGET (original detail options and Vita defaults)

Status: source and host-tested only. Nothing here was measured on a Vita or in Vita3K.

## Hypothesis
Renegade already has its own way to scale detail: per-object HLOD levels picked by
`PredictiveLODOptimizerClass` against a static and a dynamic polygon budget, particle
decimation through the same optimizer, plus texture reduction, surface-effect and shadow
options. A Vita that has no saved Performance record never went through WWConfig, so it
runs with engine compile-time budgets (4000/4000). That value is not one the original
options UI or WWConfig would ever write. If the Vita starts from the value the original
picks for its slowest supported PC, the original optimizer cuts character, vehicle,
weapon and particle work. The user can still raise it from the original Performance tab.

## Evidence (file:line)
- The LOD optimizer is live on Vita every frame. `a31_gameplay_boundary.cpp:1008` calls
  `Pre_Render_Processing`, and that reaches `pscene.cpp:1145` `Optimize_LODs`.
  `pscene.cpp:1203-1233` gives the dynamic list `DynamicPolyBudget` and the static and
  world-space lists `StaticPolyBudget`. `hlod.cpp:2879-2925` adds multi-LOD HLODs (and,
  recursively, the head and weapon aggregates). `part_buf.cpp:1219-1262` adds particle
  buffers. HLODs are not forced to LOD 0.
- The Vita budget today is `pscene.cpp:144-145` `DEFAULT_{DYNAMIC,STATIC}_LOD_BUDGET = 4000`.
  The original desktop never ran at that value, because `SystemSettings::Init`
  (`systemsettings.cpp`) always overrides it. On the Vita, `SystemSettings` is not compiled
  and `a4_frontend_lifecycle_boundary.cpp:117` stubs `Apply_All`. The only Vita owner is
  `RenegadeVitaOptions::Apply_Performance`, which runs every frame from
  `a31_gameplay_boundary.cpp:493-503,828`. Before this change it returned early when no
  Performance record had been saved.
- The original slow-PC choice comes from WWConfig `AutoConfigSettings`
  (`Tools/WWConfig/PerformanceConfigDialog.cpp:904-988`):
  - Budgets: 10000 with hardware T&L, 5000 for an SSE or Athlon CPU, otherwise **0**.
  - Texture_Resolution: 0 with DXTC.
  - Shadow mode: 3/2 with render-to-texture (RTT), else 1/0.
  - Surface effects: 2/1/**0**.
  - Particle detail: 2/1/**0**.

  The in-game tab presets (`dlgconfigperformancetab.cpp:73-119`) put Geometry detail at
  Low (`MAX_LOD_LOW=0`, line 131-133) for both lower presets.
- Retail data (scratch scan of always.dat, Always2.dat and M13.mix HLOD chunks):
  - 204 of 1470 HLODs have more than one LOD: 115 characters (`c_`), about 63 vehicles,
    24 weapons (`w_`).
  - Triangles: sum at top LOD 135,446, sum at lowest LOD 28,310.
  - Sub-meshes: top LOD 2632, lowest LOD 1007. For example, `v_nod_buggy` has
    22 meshes / 1038 tris at top and 7–13 meshes / 91–571 below. `c_nod_mg_` has
    21 meshes / 1112 tris at top and 1 mesh / 136–484 below.
  - 123 of the 204 have artist `MaxScreenSize` limits. Those keep large on-screen bodies
    at a high LOD even with budget 0, through the minlod clamp in
    `hlod.cpp` `Calculate_Cost_Value_Arrays`.
  - 81 have no such limit: heads such as `c_havoc_head` (28/91/160/248 tris), weapons
    (`w_rifl` 59/78/178) and a few vehicles. With budget 0 these always drop to LOD 0.
- Particle detail: the original registry value is read only by sysinfo logging
  (`Commando/shutdown.cpp:120,237`), so it has no runtime effect on the PC or the Vita.
  Real particle LOD is the optimizer plus the 17-entry screen-size table. The Vita copies
  that table exactly (`a31_vita_runtime.cpp:4856-4865` = `init.cpp:159-178`).
- Texture detail is not honored on Vita. `texture.cpp:438-452` (Vita `Init`) calls
  `_Create_DX8_Texture(path, mips)` (`ww3d_dx8_boundary.cpp:2225`) with no reduction
  argument, and `TextureClass::Get_Reduction` (`texture.cpp:632`) is never consulted.
  Changing the slider still runs `WW3D::Set_Texture_Reduction`, which calls
  `_Invalidate_Textures()` (`ww3d.cpp:1758-1763`). The result is a full texture reload at
  the same size: cost and no benefit.
- Render-to-texture does exist (`ww3d_dx8_boundary.cpp:2923`). Shadows still stay at the
  `pscene.cpp:202-204` defaults (mode None, projectors off): Vita disables the shadow
  controls in the dialog (`dlgconfigperformancetab.cpp:333-336`) and nothing else sets them.
- Static sort lists: the original client enables them (`init.cpp:856`). The Vita gameplay
  path never does, so they are on only inside `dialogmgr.cpp:458-527`. This affects
  fidelity (sort-level and alpha order), not throughput, and needs separate visual review.

## Knob table
| Knob | Original range | Original default (no registry / dialog fallback / WWConfig slow PC) | Current Vita | Recommended (applied) | Expected impact (unmeasured) |
|---|---|---|---|---|---|
| Dynamic LOD budget | 100..100000 console; dialog writes 0/5000/10000 | 10000 / 3000 / **0** | 4000 (engine constant) | **0** (Low) | All dynamic HLODs and particle buffers drop to their minimum allowed LOD. In a sparse view (player + 3 soldiers + 1 vehicle) roughly 5k down to 2–3k tris, plus fewer sub-meshes for vehicles and some characters. Crowded views were already near minlod at 4000. Less CPU skinning and vertex emission, fewer particles drawn |
| Static LOD budget | 100..10000; dialog 0/5000/10000 | 3000 / 3000 / **0** | 4000 | **0** | Small. Static multi-LOD objects are rare (world meshes have one LOD) |
| Texture reduction | 0..7 (dialog 0..2) | 0 / 0 / 0 (DXTC) | 0 | 0 (unchanged) | None. Not honored by the Vita loader (see gap) |
| Surface effect detail | 0 Off, 1 No Emitters, 2 Full | Full (engine) / 1 / **0** | 2 | 2 (unchanged; override macro) | Off would also remove footstep, impact and tread sounds and decals. Measure 1 on hardware |
| Shadow mode + projectors | 0..3; on/off | None / Blobs+ / 2 with RTT on non-T&L | None, off | None (unchanged) | Already the cheapest. Mode 2 would add RTT passes |
| Particle detail | 0..2 | 1 / 1 / 0 | n/a | n/a | No runtime consumer in original code |
| Prelit / filter / NPatches | fixed | MT / bilinear / off | fixed (read-only on Vita) | unchanged | n/a |

## Change made
- New `port/platform/renegade_vita_performance_defaults.h` (engine-independent):
  - `Original_Auto_Config`: a branch-for-branch transcription of `AutoConfigSettings`.
  - `Vita_Auto_Config_Inputs`: the Vita classified as DXTC yes, RTT yes, hardware T&L no,
    SSE-class CPU no. The evidence for "no T&L-class headroom" is the CPU-bound mesh/skin
    boundary (dev238: 24–29 ms mesh CPU at about 5k tris).
  - `Vita_Default`: budgets from the original table (0/0) and texture reduction 0.
    Surface mode stays at the engine's MODE_FULL.
  - `Effective(record)`: a saved Performance record wins exactly; otherwise defaults apply.
- `renegade_vita_options.h` `Apply_Performance` now applies `Effective(...)` instead of
  returning early. The original Performance tab on Vita reads the live scene budget and
  shows 0 as Geometry "Low" (`Load_Values` `< 1000`). Any user change is persisted by the
  existing `Save_Performance` and overrides the defaults from then on.
- Build-time switches, limited to original option values:
  - `RENEGADE_VITA_DEFAULT_GEOMETRY_DETAIL=0|1|2` selects budget 0/5000/10000.
  - `RENEGADE_VITA_DEFAULT_SURFACE_EFFECT_DETAIL=0|1|2`.

  Out-of-range values fail with `static_assert`. Undefined (the default) means the
  original auto-config budgets and Full surface effects.
- No upstream or staging source changed. No patch was needed.

## Risk and invalidation argument
- Default-on only for users with no saved Performance record; saved RVOPT1 records
  (`value[0]&2`) apply exactly as before (host-tested). Defaults are never written, so a
  later build can change them; audio-only saves do not set the Performance bit.
- Visual risk is the original "Low geometry" look: bodies with artist screen-size limits
  stay detailed up close, but heads/third-person weapons/a few vehicles without limits use
  LOD 0 at every distance (Havoc head 28 vs 248 tris; visible in close-up cinematics).
  Fallback: `RENEGADE_VITA_DEFAULT_GEOMETRY_DETAIL=1` (original Medium) or raise Geometry
  detail in Options. Distant particles decimate to their screen-size minimum (original Low).
- No simulation effect: LOD only swaps render sub-objects (`Notify_Added/Removed`).
- Applies to every configuration calling `A31_Interactive_Apply_Render_Capabilities`,
  including the M00 demo: new runs log fewer dynamic meshes/triangles than frozen A3.x
  baselines (expected, not a regression). Per-frame re-apply is a few integer stores.

## Tests run
- `RENEGADE_UPSTREAM_CODE=<main>/upstream/CnC_Renegade/Code python3 -m unittest tools.test_vita_performance_defaults -v`
  passes 4/4. It checks the C++ table against an independent Python transcription for all
  16 input combinations, the Vita default `0 0 0 2`, saved-record precedence, audio-only
  records, `Valid()` storage, the override macros and their rejection, and that the
  upstream constants are unchanged. Built with ASan and UBSan.
- `python3 -m unittest tools.test_vita_user_settings` (same environment variable) passes 2/2.
- ARM TU OK (VitaSDK, current flags): `a31_gameplay_boundary.cpp`, `dlgconfigperformancetab.cpp`,
  `dlgconfigaudiotab.cpp`, `vita/a31_vita_runtime.cpp` (all include `renegade_vita_options.h`).
- `python3 -m unittest tools.test_a4_original_frontend_contract`: 21/21 pass.
- Not run: `host_a30_definitions/a31_interactive_main.cpp` (needs full host build); its
  options check saves a record before `Apply_Performance`, so its expectation is unchanged.

## Expected gain (estimate, unmeasured)
- Frames with several characters or vehicles close to the camera, where the 4000 budget
  was not yet binding: roughly 1–3k fewer skinned and vertex-emitted triangles per frame,
  and up to about 10–20 fewer sub-mesh submissions per nearby vehicle or 21-mesh
  character. A guess at a share of render CPU: 1–4 ms in those scenes.
- Crowded views (M13 ambush) were already close to minlod at 4000. The expected gain
  there is small: about 0–1 ms, mostly from particles.
- World meshes, the dominant per-mesh cost in dev238, are single-LOD and unaffected.

## Follow-ups (not done here)
1. Honor `TextureClass::Get_Reduction()` in the Vita DDS loader by skipping the top mip
   levels, as `DDSFileClass` does. That would make Texture detail save vitaGL memory and
   upload time. Until then it is a reload-only cost, so consider disabling the slider.
2. Enable original static sort lists on the gameplay path, per `init.cpp:856` (a fidelity
   issue, needs visual review).
3. A/B surface effects at 1 (No Emitters) in an M13 firefight.

## Hardware measurement
On a fresh options file (delete or rename `ux0:data/renegade/user/config/options-v1.cfg`),
run the fixed M13 ambush replay, then repeat with Geometry detail set to High in Options:
1. Compare frame p50/p95/p99 and the "Vita Render" profile scopes (mesh boundary and skin
   path).
2. Compare per-frame mesh, triangle and particle counts.
3. Visually check close-up cinematics: heads and weapons.
