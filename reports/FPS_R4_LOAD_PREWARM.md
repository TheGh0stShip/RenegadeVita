# FPS round 4: LOAD_PREWARM (loading-screen pre-warm and load ordering)

Status: implemented, host-tested (audio) and ARM-compiled; nothing measured on
hardware. All three new warm-ups default ON, gated by `preload-v1.flag`.

## Hypothesis
First-use work still lands in gameplay frames after the existing preparation
(cinematic preset models/HAnims, script-spawn supplements, killed explosions,
48 MiB referenced textures): (1) the static mesh cache builds+uploads each
rigid world mesh on its first draw, (2) every sound effect is WAVE-decoded on
its first play, (3) soldier locomotion/wound HAnims (`S_A_HUMAN.H_A_*`) load
(or fail-probe every archive) when a soldier first enters a state. Moving these
to the loading screen removes those hitches without changing semantics.

## Evidence (dev238 physical log, read-only; build/device-evidence/A3.5-dev238-20261004)
- runtime-observation-3.log:561 `original mission dependency list ... elapsed_ms=10488`
  is the only large timed load phase; `loading screen: phase=` lines carry no
  timestamps, so the other phases cannot be ranked from this log.
- :1051/:1260/:1418/:1421 first-use soldier creation 221-588 ms
  (GDI_ENGINEER_0 233 ms first, 1.5 ms second at :2068). The model part is now
  covered by the post-dev238 cinematic preset warm-up (1b9e887); animations,
  sounds and world geometry are not.
- :1057 `slow frame: frame=1 total_us=2527879 ... render_us=1027447`.
- humanstate.cpp:748-798 (on-demand H_A names), :1347-1361 (wound table);
  assetmgr.cpp:920-955 (Get_HAnim: load or Register_Missing after two failed
  Load_3D_Assets probes); renegade_miles_provider.cpp Decode_Into_Sample
  (content-hash keyed PCM cache, 4 MiB, 128 slots).
- Load ordering (retail data, `scratchpad/dep_order.py`): M13.dep resolves 291
  files/15.1 MB (202 in always.dat, 86 in M13.mix, 24 missing); dep order sums
  25.5 GB of intra-archive seek distance with 13 archive switches vs 0.56 GB/2
  sorted by (archive, offset). M01: 952 files/37.9 MB, 45.1 GB vs 0.55 GB.
  But 15 MB in 10.5 s is ~1.4 MB/s, far below memory-card throughput, so the
  phase is dominated by W3D parse/prototype creation, not seeks. Flash media has
  no mechanical seek. **No reordering implemented**: it would change the
  original AssetDependencyManager load order for an unmeasured, likely small
  gain. Next step is a sampled per-file elapsed log inside `Load_Assets`.

## Change made
`port/platform/vita/a31_vita_runtime.cpp` (`Prepare_Original_Level_Loading_Resources`,
after killed explosions; geometry after textures):
- `Warm_Level_Soldier_Animations`: hold styles from the level's soldiers'
  primary/secondary weapons (`WeaponDefinitionClass::Style`); names built with
  the humanstate.cpp rules for legs A0/A1/B1, the 13 wound anims, then
  A2-A6/C0/C1 (aiming styles load tilt variants 1-3). Loaded via
  `WW3DAssetManager::Get_HAnim`, released; bounds 160 names, 2.5 s, 24 MiB
  vitaGL floor. Log: `A4 <lvl> soldier animation preparation: ...`.
- `Warm_Level_Sound_Pcm`: fire/continuous (weight 4), ammo+killed explosion
  (2/1), reload/empty (1) sound defs of level objects, most-referenced first;
  file read through `_TheFileFactory` (path stripped as in `Create_Sound`) and
  handed to new `Renegade_Miles_Prewarm_Pcm`. Bounds 96 sounds, 1.5 s, stops
  at first "would evict". Log: `A4 <lvl> sound PCM preparation: ...`.
- `Prebuild_Level_Static_Geometry`: static physics objects sorted by distance
  to the star (scene order if none), meshes found by sub-object recursion,
  each passed to new `RenegadeVitaRenderer::Prebuild_Static_Mesh`. Bounds
  3 s, 24 MiB floor (every 16 objects), 3/4 of the 24 MiB cache budget.
  Log: `A4 <lvl> static geometry preparation: ...`.
- `Read_Level_Preload_Mode`: `ux0:data/renegade/user/config/preload-v1.flag`
  exactly `"RVPL1 <d>\n"`, d=0..7 mask (1 anims, 2 sounds, 4 geometry); default
  7; `RVPL1 0` disables all three. Logged once per level (`round-4 preload:`).
  Existing cinematic/explosion/texture warm-ups are not gated by it.

`port/renderer/vita/ww3d_vita_renderer.{h,cpp}`: `Prebuild_Static_Mesh`
(after `Forget_Static_Mesh_User_Lighting`) reuses `Build_Static_Mesh_Streams` and
`Upload_Static_Mesh_Entry`; skips skins, already-known (model, user_lighting)
keys, ineligible and lit results (nothing recorded), never evicts (stops at
3/4 budget), and restores default texture-coordinate stage state afterwards.
`Submit_Static_Mesh_Cache` is untouched. If the cache keying changes, only the
`Find`/`Insert` pair in this function needs to follow.

`port/audio/vita/renegade_miles_{provider.cpp,runtime_stats.h}`:
`Renegade_Miles_Prewarm_Pcm` hashes and decodes outside the mixer lock with the
same `Hash_Image`/`Decode_Wave_With_Info`, retains only into a free slot within
budget (no eviction), reports CACHED/PRESENT/FULL/SKIPPED.

## Risk and invalidation argument
- PCM: cache key is (content hash, length) of the exact bytes; decode is a pure
  function of them, so a hit is identical to a cold decode (host test proves
  sample-exact output). WWAudio buffers, randomisation and playback untouched.
- HAnims: same `Get_HAnim` call first use would make; HAnimManager owns the
  result or the missing mark until the original Free_Assets. Cost: heap
  (~12 KB/anim file, <=160 anims, ~2 MB est.) and loading time.
- Geometry: unlit colours depend only on model arrays, user lighting array and
  material state; the first draw still runs `Static_Mesh_Entry_Current`
  (counts, alternate materials, material snapshots), so any change rebuilds as
  before. Staged-but-undrawn entries are oldest in LRU and evicted first. Risk:
  up to ~18 MiB vitaGL memory consumed earlier (24 MiB all_free floor kept);
  the build touches DX8 texture-stage state outside a draw (reset afterwards).
- Not gated: none of these change game objects, scripts, timing or RNG
  (`AudibleSoundDefinitionClass::Create_Sound` avoided: it calls rand()).

## Tests
- `python3 -m unittest tools.test_vita_audio_provider` equivalent run directly
  (ASan/UBSan build of tools/vita_audio_provider_test.cpp + provider): PASS,
  including the new prewarm block (CACHED, PRESENT, SKIPPED, accounting,
  first sample load = cache hit with 0 decodes, mixed output == cold decode).
- `python3 -m unittest tools.test_vita_m13_cinematic_preparation
  tools.test_vita_static_mesh_cache`: 12/13 pass; the one error
  (`test_m01_referenced_textures_prepare_before_first_world_frame`, anchor
  `stricmp(selected_archive, "M01.mix")`) is pre-existing: the anchor is absent
  from base commit 95c4976 since the 1b9e887 refactor.
- ARM TU (VitaSDK, current flags): a31_vita_runtime.cpp OK,
  ww3d_vita_renderer.cpp OK, renegade_miles_provider.cpp OK.
- No host test for the runtime/renderer warmers (need WW3D/WWPhys host scene).

## Expected gain (unmeasured estimates)
Removes first-play WAVE decodes for the level's weapon/explosion sounds
(~1-10 ms each), first-state HAnim loads/probes (~2-20 ms each, several per new
soldier type) and first-draw static mesh build+upload bursts on camera turns
(up to several ms per mesh). Adds ~1-6 s loading time worst case (bounded).

## Hardware measurement to take
Same M13 (and M01) route with `preload-v1.flag` absent vs `RVPL1 0`: compare
`A4 slow frame` count/worst, p95/p99 frame time over the first 600 frames,
`static-mesh-cache` builds after frame 1, `pcm_cache_hits`/`pcm_decodes`,
the three new preparation log lines (counts/bytes/ms) and total
`A4 level preparation: complete ... elapsed_us`, plus vitaGL all_free after load.
