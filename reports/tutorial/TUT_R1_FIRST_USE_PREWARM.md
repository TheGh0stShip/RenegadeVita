# Tutorial round 1: FIRST_USE_PREWARM (RVTP1)

Status: implemented on branch `tut-r1-02-first-use-prewarm` (base `45c6cf5`),
pure-Python tested, **not compiled** (round rule: no building), not run on
Vita3K or hardware. Every gain below is an unmeasured hypothesis. Flag
default **off**.

## Findings

1. **The Vita loader never loads `always.dep`.** The level load calls
   `CombatManager::Load_Level_Threaded(load_source, false)`
   (`port/platform/vita/a31_vita_runtime.cpp:5893`, log
   `preload_always=0` at :5891), so `_preload_assets` is false
   (`staging/combat/combat.cpp:446`) and only the mission list
   `m00_tutorial.dep` is preloaded (`Load_Level_Assets`, :5868). `always.dep` lists 1,521 W3D files (first-person
   `F_GA_*`/`F_HA_*` animations, `H_A_*` human animations, `e_*` emitters,
   `ag_*` explosion aggregates); on Vita each of them loads in the gameplay
   frame that first needs it.
2. **`m00_tutorial.dep` (241 names) already covers characters, vehicles,
   most power-up models and the X0I_Drop02 cinematic** (V_NOD_BUGGY,
   V_NOD_LTANK, V_GDI_HUMVEE, V_GDI_MEDTNK, V_GDI_ORCA, V_GDI_TRNSPT,
   V_NOD_TRNSPT, V_NOD_APACHE, C_* soldiers, P_* power-ups, XG_RT_*,
   H_A_troopDrop; only `XG_TransprtBone`, 364 bytes, is missing). It
   contains **no player weapon asset**: w_*.w3d, w_*_b.w3d, f_gm_*.w3d,
   f_cm_*.w3d, tracers (tracer_gold/red, o_tracer1gold, ag_rocketl,
   ag_grnshl) and the F_GA/F_HA sets are all in always.dat only. Retail
   read-only measurement for the nine tutorial player weapons: 1.17 MB of
   model W3D, 0.38 MB of first-person animation W3D, 30 textures /
   1.16 MB DDS. `tools/test_tutorial_prewarm_list.py` asserts the
   "in always.dat, absent from m00_tutorial.dep" premise per weapon.
3. **Hardware evidence (dev230 full tutorial run, private log
   `build/device-evidence/A3.5-dev230-20261004/runtime-tutorial-finished.log`):**
   every first weapon selection on the route is an `A4 slow frame`:
   pistol select (Mission00.cpp:2385) frame 3255 715 ms (sim 409 / render
   306); Gunner sniper frame 12724 549 ms (406/143); rocket frame 14882
   502 ms (350/152); remote C4 frame 15774 844 ms (597/247); ion beacon
   frame 16664 550 ms (10/540). ~3.2 s of single-frame stalls; sim-heavy
   (W3D + HAnim load) and render-heavy (texture decode) parts both appear.
   dev230 predates round 4, but nothing in round 4 covers player weapons
   (below).
4. **Existing prewarm coverage for M00** (campaign profile):
   - Cinematic preset warm (`Warm_Level_Cinematic_Preset_Models`) scans
     `.txt` members of the level archive; `M00_Tutorial.mix` has none
     (84 members: dds/w3d/wlt/dep/ldd/lsd) and `kScriptSpawnPresetSupplements`
     (:3607) has no M00 entry, so it warms nothing for the tutorial.
   - Killed-explosion warm runs only for M01-M13 (`if (campaign)`, :4555).
   - RVPL1 animations/sounds use objects placed at load (the star does not
     exist yet); the player's later weapon grants are not covered.
   - The M00 texture prewarm (:1900-1940) only initialises textures already
     referenced by loaded prototypes (`Num_Refs() > 1`, :1915), so textures
     of not-yet-loaded weapons are never reached. On device it attempted
     249 textures with `deferred=0` under its 32 MiB soft budget.
   - HUD glyph pre-rasterisation covers in-game ASCII text.
5. **Bug (report-only, not changed): the shared cinematic preset warm
   passes file-form names to `Create_Render_Obj`.** Physics model names in
   the data are paths (`vehicles\nod buggy\v_nod_buggy.w3d`, checked for all
   tutorial presets) and weapon `Model`/`BackModel` are paths too.
   `A35_Vita_Warm_Render_Obj(model.Peek_Buffer())` (:3802) and the weapon
   calls (:3813, :3815, :3832) hand those strings straight to
   `WW3DAssetManager::Create_Render_Obj`, whose `Find_Prototype` compares the
   full string (`staging/ww3d2/assetmgr.cpp:1595-1613`) and whose on-demand
   load asks the MIX factory for the CRC of the full path
   (`staging/wwlib/mixfile.cpp:246`). The original owners strip path and
   extension first (`PhysClass::Init`, `staging/wwphys/phys.cpp:162-170`;
   `Create_Render_Obj_From_Filename`, `staging/combat/assets.cpp:100`). By
   static reading these campaign warms return `created=0` after two failed
   probes and load nothing. Suggested follow-up (campaign owners): convert
   with `Get_Render_Obj_Name_From_Filename` exactly as RVTP1 does
   (`Add_Tutorial_Prewarm_Model_File`). Hardware check: count
   `A4 prepared render object: warmed=<path> created=0` lines on M13/M01.
6. **Open lead, not addressed:** the same dev230 run has 1.6-1.75 s
   render-only stalls at conversation starts (frames 4106 MTU_SYDNEY_START,
   8222 MTU_SYDNEY_LAST_TIME, 12297 MTU_GUNNER_RETICULE; sim 6-85 ms). Only
   the first coincides with a texture-decode jump (+73); the others do not,
   so they are not asset first-use. FFP shader compiles (RVPW1 helps from
   the second launch) are the leading unverified suspect.
7. Not prewarmed, by design: conversation voice clips (streamed, each plays
   once; prewarming only moves I/O and costs memory), the 364-byte
   XG_TransprtBone. Texture inactivation is stubbed on Vita
   (`TextureLoader::Update` in `port/platform/a4_frontend_lifecycle_boundary.cpp:149`;
   `WW3D::Begin_Render` returns before `staging/ww3d2/ww3d.cpp:867`), so
   textures prepared on the loading screen are not invalidated after 20 s.

## Change

- `port/platform/vita/a35_tutorial_prewarm.h` (new, data only): tutorial
  roots, each traceable to `staging/scripts/Mission00.cpp` (Create_Object /
  Give_PowerUp / Select_Weapon in the MTU_ scripts), the X0I_Drop02.txt
  cinematic, or `Toolkit_Powerup.cpp` (M00_Soldier_Powerup_Grant drops):
  1 player weapon, 13 player power-ups, 12 world presets, 3 grant sounds.
- `port/platform/vita/a35_tutorial_prewarm.inc` (new, included by
  `a31_vita_runtime.cpp:4265` inside its anonymous namespace, like
  `original_dx8_statistics.inc`): flag reader, a definition walk (no
  loading) and the bounded warm pass. Closure per root: physics model,
  killed explosion, weapons (twiddlers expanded); per weapon: third-person
  and back models, muzzle-flash and shell-eject phys models, projectile
  `ModelName`, continuous emitter, ammo explosion, fire/continuous/
  reload/empty sounds; for player weapons additionally the first-person
  `F_GM_` model, its `F_CM_` clip and the 3 `F_GA_` + 5 `F_HA_` animation
  names built exactly as `weaponview.cpp:786-860`, and the HUD icon
  texture created as `Render2DClass::Set_Texture` does (`MIP_LEVELS_1`,
  `Init`). Plus the global HUD help-text and EVA objective sounds
  (played on every `Set_HUD_Help_Text`, `scriptcommands.cpp:3380`).
  Everything goes through the original owners (`Create_Render_Obj`,
  `Get_HAnim`, `Prepare_Explosion_Choice`, the provider PCM cache); no game
  object, script, timing or RNG state is touched (twiddler lookups use
  `twiddle=false`; creation does not draw from the particle RNG).
- `a31_vita_runtime.cpp` (+98/-36): includes; `Prewarm_Level_Sound_Definition`
  extracted from `Warm_Level_Sound_Pcm` and shared (identical counters,
  order and break conditions); `Warm_Level_Soldier_Animations` takes an
  optional hold-style mask (0 = previous behaviour); in
  `Prepare_Original_Level_Loading_Resources` the M00-only flag read and
  log, the plan build before the RVPL1 animation step and the warm pass
  right after the RVPL1 sound step. Order inside the pass: first-person
  sets, weapon models, explosions, sounds, preset models. Bounds: 3 s,
  shared 24 MiB vitaGL free floor (every 4th vitaGL-backed step; sounds
  only time-bounded), 96 sounds, loading screen redrawn every 8 steps.
  Because the pass runs before `Warm_Original_M00_Referenced_Textures`, the
  textures of the newly loaded weapon models fall into that existing
  32 MiB prewarm (no new texture loader).
- `tools/test_tutorial_prewarm_list.py` (new, pure Python, 7 tests).

## Flag

`ux0:data/renegade/user/config/tutorial-prewarm-v1.flag`, exactly
`RVTP1 <hex>\n`, mask: `1` weapons (first-person sets, models, icons),
`2` preset models + explosions, `4` sounds, `8` tutorial hold styles added to
the RVPL1 soldier-animation set (needs RVPL1 bit 0). **Default 0 (off)**;
`RVTP1 F` = all. Only `M00_Tutorial.mix` reads it. With the flag absent the
runtime differs from the base only by one log line
(`A4 M00_Tutorial.mix RVTP1 tutorial prewarm: mode=0 ...`) and one `fopen`.
Default off because it moves ~3-4 MB heap and up to ~1.2 MB of compressed
textures earlier and adds loading time, which is not zero-risk.

## Hypothesis ledger entry

- **Hypothesis:** first selection of each tutorial weapon (and first
  range explosions, first fire/reload sounds) stalls one frame for
  0.5-0.85 s because the W3D models, F_GA/F_HA animations and their
  textures load on demand (Vita skips always.dep). Loading them on the
  M00 loading screen removes those frames.
- **Risk:** extra loading time (bounded 3 s; estimate 1-2.5 s); earlier heap
  residency (~2-4 MB parsed W3D + ~0.4 MB animations; at tutorial end the
  same assets would be resident anyway, except weapons the player never
  receives); texture prewarm budget shared with existing level textures
  (previously deferred=0 at 249 textures); missing clip models
  (F_CM_CHNG/ROCK/IONB do not exist) cost two failed probes each at load.
  Not compiled: a compile error is possible until the ARM build runs.
- **Estimated gain:** removal of five 0.5-0.85 s single-frame stalls on the
  Gunner range and pistol select (~3 s total), plus smaller first-explosion
  and first-sound hitches. Unmeasured.
- **Measure (tutorial route, same save/route, flag absent vs `RVTP1 F`):**
  `A4 slow frame` lines around pistol select (Logan) and each
  MTU_GUNNER_* weapon conversation, p95/p99/worst over the range section,
  `A4 M00_Tutorial.mix tutorial first-use preparation:` (counts,
  `memory_floor`, `time_limit`, `elapsed_us`), `A3.5 prewarm: original
  referenced textures attempted/deferred`, `A4 level preparation: complete
  elapsed_us`, vitaGL `all_free` and heap after load, `A3.5 weapon view`
  lines (no missing reload anims should newly appear).

## Verified vs unverified

Verified (host, no compiler): `python3 -m unittest
tools.test_tutorial_prewarm_list` 7/7 pass, including resolution of every
root against the M00 discovery receipt (`build/dev208-m00-aggressive-typed.json`)
and against read-only retail `always.dbs`/`always.dat`/`M00_Tutorial.mix`
(both found via parent directories; skipped when absent). Existing static
contract suites that read the runtime still pass
(`test_vita_loading_screen_contract`, `test_runtime_log_contract`,
`test_campaign_*`, `test_mission_conversations`, `test_vita_indexed_state_contract`,
`test_vita_texture_provenance_contract`, static functions of
`test_vita_m13_cinematic_preparation`); `test_original_dazzle_lifecycle`
errors only because `upstream/` is not checked out in the worktree.

Unverified: compilation (every API was checked against the staged headers:
`WeaponManager::Find_Weapon_Definition(const char*/int)`,
`PowerUpGameObjDef::Get_Grant_Weapon_ID`, `GlobalSettingsDef` sound IDs,
`TwiddlerClass` accessors, `PhysDefClass::Get_Model_Name`,
`Get_Render_Obj_Name_From_Filename`, `WW3DAssetManager::Get_Texture`),
runtime behaviour, timing, memory, and any gain.

## Hardware A/B

1. Build the candidate; launch twice (FFP cache) before measuring.
2. Run A: no `tutorial-prewarm-v1.flag`. Play Logan -> pistol select ->
   Sydney -> Gunner range through the ion beacon. Pull the runtime log.
3. Run B: write `RVTP1 F` + newline to the flag file, same route.
4. Compare the slow-frame list and the metrics above; then bisect with
   `RVTP1 1`, `RVTP1 2`, `RVTP1 4`, `RVTP1 9` if B helps but costs too much
   loading time or memory. Visual check: first-person weapon models, HUD
   weapon icons and range explosions look unchanged.
