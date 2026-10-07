# Fix-ledger integrity audit — 2026-10-07

Scope: "no missing fixes" audit of the active staging-patch registry, the fixes that
reports claim as adopted, the candidate/deferred fixes still listed in reports, and the
host Python test suite. Evidence class: host source/text inspection and host unit tests
only. No cmake, ninja, ARM link, VPK, Vita3K or Vita action was taken. For the test run
the empty `upstream/CnC_Renegade` gitlink was temporarily replaced by a symlink to the
active tree's pristine upstream and restored before commit; upstream was never edited.

## 1. Patch registry (port/patches vs tools/stage_sources.sh)

| Check | Result |
| --- | --- |
| Files in `port/patches/` | 530 at start (532 now) |
| Registered `patch ... < port/patches/X` commands in `tools/stage_sources.sh` | 525 at start (527 now), one per distinct patch, all with `--batch --forward --fuzz=0 --no-backup-if-mismatch -p1` |
| Duplicate registrations | 0 |
| Registered but missing file | 0 |
| Unregistered patch files | 5 (all in the `RETIRED` set of `tools/renegade_patch_inventory.py`, which the tool enforces) |
| Non-`.patch` debris (`.orig`, `.rej`) in `port/patches/` or `staging/` | 0 |
| `bash tools/stage_sources.sh` against pristine upstream | exit 0, every hunk at fuzz 0 (offsets only), and the regenerated `staging/` was byte-identical to the committed tree before this unit's changes |
| `renegade_patch_inventory.py` | PASS (receipt matches) |

The five unregistered patches are intentional evidence-only retirements, not lost fixes:

| Patch | Why it is not applied | Evidence |
| --- | --- | --- |
| `wwnet-a31-network-posix.patch` | historical A3.1 investigation; networking provider replaced it | `reports/DECISION_LOG.md` (2026-08-15), `wwnet-a35-vita-libc-receive.patch` |
| `combat-a35-weaponview-reload-motion.patch`, `combat-a35-weaponview-reload-visible-fallback.patch` | superseded by `combat-a35-weaponview-reload-latch.patch`; `tools/test_stage_sources_incremental_contract.py` asserts the fallback stays unregistered | test + inventory |
| `wwphys-a31-vita-material-effect-boundary.patch`, `wwphys-a31-vita-material-effect-close.patch` | they made `TransitionEffectClass::Render_Push/Pop` return immediately; retired in 17d6d5f when the native adapter restored transition Push/Pop ownership | `reports/KNOWN_GAPS.md` ("restores transition Push/Pop ownership"); `staging/wwphys/transitioneffect.cpp` has no port guard |

Note: `reports/PROCEDURAL_MATERIAL_OWNER_REVIEW.md` and `reports/PORT_GUARD_SWEEP.md` still
describe the transition guard as live; they predate that retirement (historical, not a missing fix).

Cosmetic only: 327 of 527 registered commands have no matching `echo "Applied: ..."` line in
`stage_sources.sh`. The echo lines are a console log, not a registry, so this is harmless.

### Did a later patch silently undo an earlier fix?

For every registered patch the significant added lines (>= 12 characters, non-comment) were
checked against the final staged file. 49 patches have at least one added line that is
absent from the final tree. All but one are explained by a later registered patch that
deletes that exact line (diagnostic traces replaced by later patches, hunks re-expressed by
status-propagation patches, and so on); the remaining one
(`commando-a36-multiplayer-frontend-gcc15.patch`, `dlgserversaveload.cpp`) is reverted by
a later hunk of the same patch. No fix is accidentally reverted. Largest supersessions, all
confirmed intentional: `ww3d2-a35-create-depth-timing` (22/25 lines), `scripts-a35-m13-slot19-phases`
(9/13), `ww3d2-a35-m13-aggregate-template` (16/32), `scripts-a35-cinematic-time-budget-only` (1/1).
`combat-a35-hud-target-box-nan-guard` (2/3) is superseded by the equivalent `__vita__` guard in
`staging/combat/hud.cpp:1901`.

## 2. Reports that claim a fix

Method: (a) every `*.patch` name mentioned in any `reports/**/*.md`, `docs/` or top-level
markdown (249 distinct names) was resolved against `port/patches/`; (b) backticked symbols,
functions, log strings and file names in `reports/campaign/*.md` and `reports/*.md` were
resolved against `port/`, `staging/`, `tools/`, `cmake/` and upstream; (c) distinctive lines of
the 2026-10-07 claims were grepped.

* 234 of 249 names resolve. The other 15 are not missing fixes: 7 are glob/shorthand fragments
  (`admission.patch`, `save-status.patch`, `status.patch`, `route.patch`, `save-variable-ids.patch`,
  `contract.patch`, `generator.patch`); `DEV103_CURSOR_CLAMP.patch` exists as
  `reports/DEV103_CURSOR_CLAMP.patch`, is byte-identical (ignoring a/b prefixes) to the registered
  `wwui-a35-vita-cursor-clamp.patch`; `host-validation-entrypoints.patch` (experiments/hud-font-atlas)
  is already applied (`tools/run_a30_host.sh:44` builds `a31_interactive_runtime`;
  `tools/validate_a4_dialog_resources.sh:22` passes `--dialog-resource-h`);
  `vitagl-attribute-invalidation.patch`, `vitagl-projective-immediate.patch` live in
  `port/renderer/vita/dependency-patches/`; `ww3d2-render2d-texture-readiness` and
  `wwui-loading-animation-evidence` (DEV109/DEV110 "prepared" names) are registered as
  `ww3d2-a35-render2d-texture-readiness.patch` and `wwui-a35-loading-animation-evidence.patch`;
  the DEV110 `font-surface-conversion` and `native-quicksave-dispatch` proposals are integrated in
  port source (`port/renderer/vita/surface_boundary.cpp:206` ARGB-to-A4R4G4B4 copy;
  `port/platform/a31_gameplay_boundary.cpp:768` `CombatGameModeClass::Quick_Save()` dispatch).
* Spot verification of adopted/fixed claims (all present): `timeGetTime` on `CLOCK_MONOTONIC`
  (`port/compatibility/include/mmsystem.h:31`); unconsumed-autosave clear
  (`a31_vita_runtime.cpp:7117`); `TimeManager::Set_Time_Scale(1.0F)` at session start (`:4657`);
  `combat-a36-boss-waypath-release-guard.patch` log `waypath 3000100 unusable`
  (`staging/combat/mendozabossgameobj.cpp`); boss load-status void-call collapse; M01 save-variable
  IDs (`SAVE_VARIABLE(playerSeen, 3)`, `prayerSound, 2` in `staging/scripts/Mission01.cpp`);
  `scripts-a36-m01-intro-command-breadcrumbs.patch`, `scripts-a36-m05-apc-deploy-param-buffer`,
  `scripts-a36-m08-mobile-vehicle-attack-slot`, `combat-a36-raveshaw-arc-effect-null-guards`,
  `scripts-a35-apache-controller-bounds` (all registered); M13 and M01 retained-preparation,
  pause, and 17d6d5f breadcrumbs. The one stale doc claim is the retired transition guard above.
* No patch referenced by a report as "applied/adopted/fixed" is missing from staging.

## 3. Candidate / deferred / recommended items still open

"Safe" means a clearly minimal, behavior-preserving crash guard that can be applied without
building. Applied in this unit: items marked **APPLIED**.

| # | Item | Source report | Owner file | Safe/simple? | Disposition |
| --- | --- | --- | --- | --- | --- |
| 1 | `Static_Anim_Phys_Goto_Last_Frame` dereferences `Peek_Animation()` with no null check; a lift whose `.w3d` fails to resolve crashes instead of skipping | campaign/ELEVATORS.md s6.1 | `staging/combat/scriptcommands.cpp` (original `scriptcommands.cpp:2279`) | Yes | **APPLIED** (merged as part of `combat-a36-scriptcommands-null-guards.patch`) |
| 2 | `Set_Screen_Overlay_Opacity` is the only unclamped overlay setter (float-to-color overflow outside 0..1; retail uses 0 and 1) | campaign/CINEMATIC_PRESENTATION.md residual risks | `staging/combat/screenfademanager.cpp` | Yes | **APPLIED**: `combat-a37-screen-overlay-opacity-clamp.patch` (same `WWMath::Clamp` as the color setters) |
| 3 | Unresolved conversation (`Conversation == NULL`) dereferenced on corrupt/foreign saves (`Stop_Conversation`, `Say_Next_Remark`, `Is_Audience_In_Place`, `conversationmgr.cpp:1116`) | campaign/CONVERSATION_COMPLETION.md item 2 | `staging/combat/activeconversation.cpp`, `conversationmgr.cpp` | Not minimal (four call sites, end-state choice UNABLE_TO_INIT) | Deferred; no valid path reaches it. Needs a design choice and an ASan corrupt-save test |
| 4 | Monitor registered after the conversation already ended (M10 ordering) | CONVERSATION_COMPLETION.md item 1 | `activeconversation.cpp` | No: departs from retail | Leave; runtime evidence only |
| 5 | Elevator ENTERING state has no timeout (low-FPS escort orbit) | campaign/ESCORT_PATHING_REVIEW.md risk 5 | `staging/combat/pathaction.cpp` | No: changes AI semantics | Deferred until a physical repro |
| 6 | Spline look-ahead tuned for 30 FPS | ESCORT_PATHING_REVIEW.md risk 6 | `staging/wwphys/Path.cpp` | No | Measure first; no code change |
| 7 | Vehicle `VEHICLE_TOGGLE_GUNNER` has no Vita input; aircraft strafe shares `DIK_LCONTROL` with crouch | campaign/CAMPAIGN_VEHICLES.md s6 | `port/platform/renegade_directinput.cpp` | No: input profile/rebinding impact | Deferred to MP/flying maps |
| 8 | `Set_Max_3D_Sound_Buffer(600000)` for 56 oversized 3D definitions; azimuth pan for spatial samples (`Mix_Locked` centers them) | campaign/LEVEL_AUDIO_READINESS.md obs. 1, 2 | `port/audio/vita/renegade_miles_provider.cpp` | No: memory + listening check | Deferred |
| 9 | M01/M13 prepared render objects are not re-prepared after a failure-restart | campaign/MISSION_FAILURE_PATHS.md 1 | `port/platform/vita/a31_vita_runtime.cpp` | No: refactor + frame-time comparison | Deferred |
| 10 | No exit guard if the failure popup is never created | MISSION_FAILURE_PATHS.md 2 | `combatgmode.cpp` | No: timing unprovable without a run | Deferred |
| 11 | `Peek_Map_Name` failure would leave a `save/xxx.sav` rank key | campaign/SCORE_AND_RANKS.md 1 | `staging/commando/scorescreen.cpp` (new patch) | Not minimal; no known path | Recorded |
| 12 | M08/M09 TGA closure: 16-bit upload or no retained CPU copy | campaign/MISSION_MEMORY_ESTIMATES.md | `port/renderer/vita/*` | No: visual/perf trade-off, unevaluated | Deferred |
| 13 | Weather first-frame priming stall (M02/M04); lower `maxparticlecount` | campaign/WEATHER_BY_MISSION.md | `staging/combat/WeatherMgr.cpp` | No: measure first | Deferred |
| 14 | Level-load tiny retained buffers (`thread_local` RGBA scratch, 2 KiB path arrays, ...) | campaign/LEVEL_LOAD_MEMORY.md | `port/renderer`, `port/filesystem` | No: gain under 10 KiB or per-frame allocation change | Not applied (stated) |
| 15 | Relax first-load mask for `MICROCHUNKID_CHEAT_HISTORY` only if a Vita log shows an admission failure | campaign/DIFFICULTY_CHAIN.md risk 1 | `combat-a36-combat-manager-admission.patch` | Conditional | Only on evidence |
| 16 | M05 `Cathedral_Apache` does not save `fire_loc`; `Cathedral_Artillery` duplicate save ID 1 (same as PC) | campaign/M05_READINESS.md | `staging/scripts/Mission05.cpp` | Parity with PC; could mirror the `*-save-variable-ids` series | Deferred (completion unaffected) |
| 17 | `Remove_Pog(805/806)` clears wrong IDs; `M09_Nod_Damage_Mod_1` undeclared | M08/M09 readiness | `Mission08.cpp`, `Mission09.cpp` | Original bugs, kept for parity | Leave |
| 18 | Retail M11 fodder-guy scripts absent | KNOWN_GAPS (2026-10-05/06) | none (graceful) | n/a | Leave |
| 19 | Staging-guard policy statement; retail `campaign.ini` duplicate-backdrop check for first-match change | KNOWN_GAPS | `commando-a36-campaign-backdrop-selection.patch` | Documentation/audit | Open |
| 20 | `experiments/material-loader-bounds/ww3d2-material-chunk-bounds.patch` (name-chunk bounds, NUL-terminated mapper args, unsigned-arithmetic guard, cleanup on early return) | experiments README | `staging/ww3d2/vertmaterial.cpp` (`VertexMaterialClass::Load_W3D` still has the unbounded `cload.Read(&name, ...)` and `new char[len]` + `sprintf("%s")`) | Beneficial but changes failure behavior on malformed chunks and needs sanitizer runs on retail materials | **Unapplied, unregistered by its own README**; left as is. Highest-value remaining defensive patch |
| 21 | `experiments/diagnostic-sampling`, `experiments/canonical-cache-identity` | experiment READMEs | `port/developer`, build flags | No (needs measurement) | Not integrated, as documented |
| 22 | `DisableCameraShake` decoded but not applied (TT protocol) | KNOWN_GAPS | network provider | No | Open feature |
| 23 | Full ARM build of the 2026-10-05 a36 status-patch batch | campaign/BOSS_CLASS_SUPPORT.md | build | Build gate | The three boss TUs were already found broken by this class of gap; an ARM full build is the only closure |

## 4. Host test suite

Command shape: `python3 -m unittest discover -s tools -p <file> -v`, one file per process,
4 files in parallel, each under `setarch x86_64 -R` (see "TSan"), with the upstream symlink in
place and an empty `build/` directory present (it is git-ignored; no build ran in it).
`test_renegade_script_dsp_cmake.py` was skipped on purpose because it invokes `cmake`.

| Run | Files pass | Files fail | Skipped | Test cases executed | Cases failing |
| --- | --- | --- | --- | --- | --- |
| Before fixes (plain `unittest`, TSan broken by kernel ASLR) | 185 | 37 | 1 | 1,047 | 36 (27 errors, 9 failures) |
| After fixes (this unit) | 200 | 22 | 1 | 1,064 | 21 (19 errors, 2 failures) in 16 files |

All 22 remaining file-level failures are classified below. None is a regression in
shipped code; the real defect that the suite found (dialog generator) is fixed.

### Triage of every initial failure

| Test file | Class | Cause | Action |
| --- | --- | --- | --- |
| test_wwui_resource_styles | **Real defect (fixed)** | `tools/generate_wwui_dialog_templates.py` had no `ES_CENTER`, `ES_PASSWORD`, `ES_NUMBER`, `ES_OEMCONVERT` or `CBS_SORT`, so unknown style names silently resolved to 0 in the generated resources (original WWUI reads `ES_PASSWORD` at `editctrl.cpp:339`, `ES_CENTER` at `multilinetextctrl.cpp:164`, `ES_NUMBER|ES_OEMCONVERT` at `editctrl.cpp:1295`). It also mis-joined a statement wrapped as `NOT` / `WS_GROUP`, leaving WS_GROUP set. The test had been failing at the llvm-rc parse step (the 2026-10-06 triage called this a toolchain issue), which hid the second defect | Flags added, `NOT` continuation fixed. Now all 58 dialogs / 728 controls equal independent llvm-rc output. Effect on generated templates: dialogs 172 (credits) and 174, 177, 180, 181, 188, 246 (multiplayer) change; the 22-dialog M00 set is byte-identical. **This changes generated VPK resources on the next build: password/credits edit styling and WS_GROUP on a few statics. It matches the original RC, but needs a Vita3K/physical look at those dialogs.** |
| test_mission_conversation_diagnostics_contract | stale test | Triangle/Square/D-pad key gates now read `(ordinary_gameplay_input \|\| dialog_navigation)` plus chord exclusions (17d6d5f radio/chord routing) instead of `gameplay_input_active` | Tokens updated to the current whitespace-normalized lines, now bound per key (`DIK_E`=Triangle, `DIK_R`=Square, arrows=D-pad, `DIK_F`=rear touch). **Review note:** the `\|\| dialog_navigation` clause also lets those buttons set keyboard keys while a dialog has focus; that is existing 17d6d5f behavior, not changed here |
| test_vita_m13_cinematic_preparation | stale test | Fixed 48 MiB texture-prepare budget became the minimum of a headroom-scaled budget (6522ab2, today) | Test now pins `base_budget = 48 MiB`, the `Select_Campaign_Texture_Prepare_Budget` call and the `budget < base_budget` floor |
| test_vita_skin_submission_contract | stale test | Predicate hoisted to `batch_skin_color_passthrough` (d375dd1) | Regex retargeted to the hoisted assignment (same expression) |
| test_m09_camera | stale test | Asserted whole staged `Mission09.cpp` equals upstream plus the camera-loop bound; later registered patches legitimately touch other M09 scripts | Compares only the `M09_Camera_Activate` declaration body; sanitizer compile/run of original vs bounded is unchanged (passes, ~130 s) |
| test_logical_stimulus_telemetry | stale test | Asserted no `offset` in `patch` output; later patches shift lines by 2. The 2026-10-06 note called this a zero-fuzz violation; it is not (`--fuzz=0` still applies) | Now rejects `fuzz` and `FAILED`; ordering assertions unchanged |
| test_script_load_capacity | stale harness | `Load_Data` now calls `Report_Error()` | Seam gained `Report_Error`; asserts each rejected case reports exactly one error |
| test_vita_bink_scheduler | stale harness | `BINKMovie::Update` calls `sceKernelPowerTick` | Stubs added to the harness |
| test_vita_index_preparation | stale harness | Extracted block now spans the render-target size query and `RENEGADE_FRAME_PROFILE` | Stubs added (`g_active_render_target_*`, profile macro) |
| test_vita_sampler_cache | stale harness | Extraction end markers moved (`Bind_Offscreen_Render_Target`, `Submit_Mesh_Internal`) | Markers updated |
| test_renegade_async_log, test_a35_flight_background_flush, test_renegade_paths_cache, test_renegade_file_factory_availability | environment | `FATAL: ThreadSanitizer: unexpected memory mapping` on the WSL 6.18 kernel; a 3-line TSan probe fails the same way | Pass under `setarch x86_64 -R` (ASLR off) |
| test_script_lookup_telemetry | environment | needs a `build/` directory | Passes once `build/` exists |
| test_campaign_flight_recorder_contract, test_vita3k_runner_launch_proof, test_win32_time_compat | script-style tests | no `unittest` cases; discovery reports "NO TESTS RAN" | Pass (exit 0) when run as `python3 tools/<file>` |

### Remaining failures (22 files), none a regression

| Test file(s) | Class | Detail |
| --- | --- | --- |
| test_action_observer_miss_telemetry | stale sha pin (report only) | `tools/original_owner_source_replay.py` pins `action.cpp` input `a8cc3e71...`; the live staging anchor `tools/stage_sources.sh:1054` is `9e630666...` and staging succeeds, so the helper pin lags a legitimately re-anchored chain. Not changed (anchor rule) |
| test_original_dazzle_lifecycle, test_original_decal_submission | stale sha pin (report only) | `tools/original_effect_source_replay.py` pins `ww3d.cpp` `32fdca66...`; replay actually produces `e213b455...`, identical to the live anchor `stage_sources.sh:1097`. Not changed |
| test_cinematic_filename_diagnostics | stale sha pin (report only) | test pins match the live anchors (`4196cdba...`, `32e962cf...`, `stage_sources.sh:1064,1075`) but its own replay of the owner chain yields `207680a0...` / `487d94fd...`: the replay input is stale, not staging. Not changed |
| test_vita_mesh_batch, test_vita_static_mesh_equivalence | stale harness (not fixed) | The mesh submission loop was restructured (`draw_pass_count`, `material_for`/`texture_for`/`shader_for` lambdas, `submitted_triangle_count`, batch hoists, 17d6d5f and d375dd1). The extraction anchors and the harness stubs both need a rework; partial edits were reverted rather than left half-fixed |
| test_tt_c4, test_tt_client_greeting, test_tt_physical_rare, test_tt_purchase_catalog, test_tt_soldier_rare, test_tt_vehicle | needs build artifact | require `build/host-a31-asan/a31_m00_interactive_runtime` (a cmake host build) |
| test_vita_projective_coordinates, test_vitagl_compact_vertices, test_vitagl_dds_chain, test_vitagl_full_upload | needs build artifact | require `build/deps/vitagl-demo/source.tar.gz` |
| test_remote_world, test_tt_client_control, test_tt_resource_preparation | CLI tools named `test_*` | argparse drivers needing `--binary/--retail/--output` or a log; not unit tests |

Not executed: `test_renegade_script_dsp_cmake.py` (invokes `cmake -P` / configure).

## 5. Changes made in this unit

* Null guard in `Static_Anim_Phys_Goto_Last_Frame`: proposed here as a separate patch; on merge it
  was dropped as a duplicate of the same guard in `combat-a36-scriptcommands-null-guards.patch`.
* `port/patches/combat-a37-screen-overlay-opacity-clamp.patch` (new, registered last):
  `WWMath::Clamp(opacity)` in `ScreenFadeManager::Set_Screen_Overlay_Opacity`.
* `staging/` regenerated with `bash tools/stage_sources.sh` against pristine upstream: exit 0,
  zero fuzz, 527 ordered patches, `staging/PATCH_INVENTORY.json` updated; only
  `combat/scriptcommands.cpp` and `combat/screenfademanager.cpp` changed. Existing sha256
  anchors in `stage_sources.sh` and the tests were not changed.
* `tools/generate_wwui_dialog_templates.py`: missing Win32 style flags and the `NOT` wrap fix.
* Stale tests/harnesses updated as listed above (intent preserved; no sha pins touched).
* Report notes: `campaign/ELEVATORS.md`, `campaign/CINEMATIC_PRESENTATION.md`,
  `HOST_TEST_TRIAGE_2026-10-06.md`.
* Both new patches are source-only. They were not compiled for ARM (no building was allowed);
  the guard code is plain C++ using symbols already present in the same translation unit
  (`HAnimClass`, `Debug_Say`, `WWMath::Clamp`). An ARM `-fsyntax-only` of those two files
  belongs in the next canonical build.

## 6. Recommendations

1. Next candidate build: confirm the generated dialog templates (credits centering, password
   masking in the Direct-IP/LAN join dialog, numeric edit IME gating) in Vita3K, since they
   change with the generator fix.
2. Decide whether to land `experiments/material-loader-bounds/ww3d2-material-chunk-bounds.patch`
   (the only unapplied defensive patch of value) after an ASan run over the retail materials.
3. Re-pin the three replay helpers (`original_owner_source_replay.py`,
   `original_effect_source_replay.py`) and `test_cinematic_filename_diagnostics.py` to the live
   `stage_sources.sh` anchors in an explicitly authorized change; they are the only red tests that
   are plainly stale rather than environmental.
4. Rework the mesh-batch and static-mesh equivalence harnesses against the restructured submission loop.
5. Make the suite runnable by one command: add a small runner that skips CLI-style `test_*`
   files, runs script-style tests directly and wraps TSan cases in `setarch -R`.
