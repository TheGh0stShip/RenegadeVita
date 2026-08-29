# A3.5-dev82 minimum deliverables audit

Updated: 2026-08-28.

Authoritative workspace:
`/home/steve/projects/RenegadeVitaBuilder/workspace/active`.
Do not use the E: mirror as source authority; it is only a copied backup of
this bash workspace after validation.

## Gate conclusion

All source/build/artifact minimum deliverables for the dev82 physical-test
candidate are met by the compiled source state at commit `4bb767e` and the
canonical build `logs/a35-dev82-20260828-182910-build.log`. Later audit/report
commits are documentation-only unless they change code or rebuild artifacts.

This is not a physical acceptance claim. The Vita still must prove the movie,
menu, M00, controls, HUD, texture, FPS, gate, freeze/crash, and clean-exit
behavior with returned `a35-dev82-runtime.log`, captures/screenshots, and any
matching `psp2core` dump.

## Canonical artifact set

| Deliverable | Status | Evidence |
|---|---|---|
| Canonical release gate uses `tools/build.sh` | PASS | `logs/a35-dev82-20260828-182910-build.log` ends with `A3.5-dev82 BUILD SUCCESS` and `No Vita filesystem was accessed and no deployment was attempted.` |
| VPK exists and is current | PASS | `dist/RenegadeVita-A3.5-dev82.vpk` SHA-256 `3be156223c7ace92e10d42eabc0e39a1ca90a6920c1491678559be061f50c4ea` |
| ELF/map/symbols exist and match manifest | PASS | ELF `cbc3fef1023a8d35b0507a12e7e4bb160232907ef1dacfe31c89cceaa7272851`; map `eab1dc1f66541f4b9e81c28947dd404face11b8e40666842af5488466551434b`; symbols `e177183e073ea03e588e9bf98c05e73e09178167e7a2df3ee1cc79b60fc1cb13` |
| Diagnostics bundle exists | PASS | `dist/A3.5-dev82-BUILD-DIAGNOSTICS-20260828-182910.zip` SHA-256 `80ea9e3a3356c42a2a72bbb075594d538cb8f5f7642e773c7035d6bb36547f32` |
| Retail exclusion | PASS | `dist/RenegadeVita-A3.5-dev82.vpk-contents.txt` contains only `sce_sys/param.sfo` and `eboot.bin`; no retail assets, saves, credentials, dumps, or user files are packaged |
| No automatic device mutation | PASS | canonical log records no Vita filesystem access or deployment; latest frontend/Bink/viewport candidate has not been uploaded |

## Source and staging deliverables

| Deliverable | Status | Evidence |
|---|---|---|
| Upstream remains pristine; deterministic staging is used | PASS | `reports/SOURCE_INTEGRATION_REPORT.json` records upstream revision `3e00c3a1b97381bb28be89a35b856375e0629a08`, `patch_count: 134`, and `custom_asset_formats: 0` |
| Original source ownership is preserved | PASS | source report records 506 original Westwood translation units plus 1 staged original-owner extraction and 26 Vita platform/renderer/validation/developer files |
| Deterministic patch count is guarded | PASS | `tools/generate_integration_report.py` and `tools/build.sh` expect `patch_count=134`; `tools/stage_sources.sh` applies patches with zero fuzz |
| Render2D viewport restore is durable | PASS | `port/patches/ww3d2-a35-render2d-viewport-restore.patch` and `staging/ww3d2/render2d.cpp` save the active DX8 viewport before the fullscreen 2D pass and restore it after drawing |
| Render2D HUD/loading/scope vertex data is initialized | PASS | `port/patches/ww3d2-a35-render2d-dynamic-fvf-init.patch` initializes normal and UV1 data used by dynamic FVF 2D draws |
| Texture orientation fixes are staged | PASS | texture-surface/provenance contracts cover top-down gameplay DDS uploads and passthrough texture-V correction after original DX8 texture transforms |
| DX8 render-state bridge remains selected | PASS | canonical build retains `RenegadeVitaRenderer::Apply_DX8_Render_State` and render-state contract 13/13 passes |

## Frontend, intro, and menu deliverables

| Deliverable | Status | Evidence |
|---|---|---|
| External frontend worker is reconciled into active | PASS | `reports/BUILD_STATE.json` records `feature/a35-dev82-retail-frontend` commit `e7a7fa82fa90981e160035a81ff029169f3412cc` as integrated and superseded by active |
| Original frontend owners are linked | PASS | final symbols include `MovieGameModeClass::Startup_Movies`, `MenuGameModeClass2::Think`, `RenegadeDialogMgrClass::Goto_Location`, and `GameInitMgrClass::Start_Game` |
| Main menu source routing is selected | PASS | `CMakeLists.txt` selects original WWUI/dialog/menu sources plus `a4_frontend_lifecycle_boundary.cpp`; `tools/test_a4_original_frontend_contract.py` validates the selection |
| Tutorial selection uses original GameInit path | PASS | staged `dialogtests.cpp` calls `GameInitMgrClass::Start_Game("M00_Tutorial.mix", -1, 0)` and the Vita runtime latches that into the existing direct M00 route |
| Menu input does not leak into gameplay bindings | PASS | `port/platform/renegade_directinput.cpp` gates WWUI D-pad/key navigation with `A4_Frontend_Is_Menu_Loop_Active()` and disables gameplay sticks/buttons while the menu is active |
| Retail intro movies are wired through the original movie owner | PASS | staged `movie.cpp` requests `DATA\\MOVIES\\EA_WW.BIK` and `DATA\\MOVIES\\R_INTRO.BIK` through `MovieGameModeClass`/`BINKMovie` |
| Vita Bink provider is real, not a RAD/proprietary import | PASS | `tools/build_ffmpeg_bink_vita.sh` pins FFmpeg 9.0.1 with Bink demuxer, Bink video, Bink DCT/RDFT audio, swscale, and swresample only |
| Vita ELF retains Bink decode symbols | PASS | `dist/RenegadeVita-A3.5-dev82.symbols.txt` contains `BINKMovie::Play`, `BINKMovie::Update`, `BINKMovie::Render`, `avformat_open_input`, `ff_bink_decoder`, `ff_binkaudio_dct_decoder`, `ff_binkaudio_rdft_decoder`, `swr_convert`, and `sws_scale` |
| Missing/invalid movies fail closed | PASS | `port/platform/a4_binkmovie_boundary.cpp` logs failed movie open/decoder setup and marks playback complete so the original menu route can continue |

## M00 physical-test deliverables

| Deliverable | Source/build status | Physical status |
|---|---|---|
| Original CombatGameMode post-load finalization, building/radar init, texture-loader update, and `On_Game_Begin` | PASS | PENDING |
| Loading screen coverage, text, progress, and loading/prewarm progress stream | PASS | PENDING |
| HUD/TextDisplay/subtitle path and final StyleMgr/TextDisplay initialization order | PASS | PENDING |
| Audible dialogue boundary and streamed-audio diagnostics | PASS | PENDING |
| Normal camera Y and gameplay input map | PASS | PENDING |
| Triangle action/use, Square reload, D-pad weapon-only switching, D-pad sniper zoom, front-touch camera toggle | PASS | PENDING |
| First-person reload animation fallback while original weapon state is reload | PASS | PENDING |
| Sniper scope/icon placement and zoom behavior | PASS | PENDING |
| NPC/Havoc/door/powerup/objective texture orientation and material correctness | PASS | PENDING |
| Bounding-box placement and random rectangle/shadow behavior | PASS | PENDING |
| FPS regression observation | instrumented/build-ready | PENDING |
| Gate interaction and freeze/crash after pistol/gate interaction | instrumented/build-ready | PENDING |
| Clean Start exit/LiveArea return | retained historical physical evidence plus current source/build support | PENDING for this candidate |

## Validation run

- `python3 -m unittest tools.test_vita_loading_screen_contract tools.test_stage_sources_incremental_contract tools.test_vita_indexed_state_contract tools.test_mission_conversation_diagnostics_contract tools.test_a4_original_frontend_contract tools.test_vita_camera_input_contract tools.test_vita_texture_surface_contract tools.test_vita_texture_provenance_contract tools.test_compare_capture_bundles tools.test_validate_vita_loading_capture`
  passed 73/73.
- `git diff --check` passed.
- `jq empty reports/BUILD_STATE.json reports/SOURCE_INTEGRATION_REPORT.json`
  passed.
- `bash ./tools/build.sh` passed in
  `logs/a35-dev82-20260828-182910-build.log`.

## Not dev82 minimum deliverables

These remain future milestones and must not block this dev82 physical-test
candidate: v3.6 multi-scene/resource-memory acceptance, v3.7 measured renderer
performance acceptance, v3.9 campaign representative RC/soak, public networking
providers, and W3DHub/TT compatibility.
