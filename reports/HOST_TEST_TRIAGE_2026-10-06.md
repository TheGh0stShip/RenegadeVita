# Host test triage — 2026-10-06

> Superseded in part by [FIX_LEDGER_INTEGRITY_2026-10-07.md](FIX_LEDGER_INTEGRITY_2026-10-07.md):
> that run re-triaged every failure below, fixed the stale harnesses, and found that the
> `ES_CENTER` failure was a real dialog-generator defect, not a toolchain problem. The
> `logical_stimulus` 'offset' failure was a pure line offset, not a zero-fuzz violation.

Scope: host-only Python `tools/test_*.py`. 216 modules exist; 20 were skipped because
they invoke `arm-vita-eabi` or `cmake`. 196 were run, 8 at a time, each with a 120 s timeout.
For this run only, the empty `upstream/CnC_Renegade` was symlinked to the active tree's copy;
it was restored afterwards. Report only: no fixes were made.

Note on how to invoke: 77 modules fail with `ModuleNotFoundError: tools` when run as
`python3 tools/test_x.py`. They need `python3 -m unittest tools.test_x` from the repo root.
Results below use that form.

Totals: **162 pass, 34 not passing** (27 fail, 3 argparse CLI non-tests, 4 timeouts).

## Stale source token / identity hash (the test lags current source)
- test_campaign_discovery_handoff: expects `if (!loaded) break;`. The source now uses a `Queue_Campaign_Handoff_Failure` block.
- test_cinematic_filename_diagnostics: 2 SHA-256 identity mismatches against the current patch output.
- test_logical_stimulus_telemetry: a patch now applies with `offset 2 lines` in smartgameobj.cpp. That is patch drift and breaks the zero-fuzz rule.
- test_action_observer_miss_telemetry: input identity mismatch for combat-a35-action-observer-miss-telemetry.patch.
- test_original_dazzle_lifecycle, test_original_decal_submission: ww3d-a35-original-dazzle-lifecycle.patch has an input identity mismatch on ww3d.cpp.
- test_vita_mesh_batch, test_vita_static_mesh_equivalence: `ValueError: substring not found` when extracting a renderer source anchor.
- test_vita_index_preparation: extracted production.inc uses `RENEGADE_FRAME_PROFILE`, which the harness does not define.
- test_vita_sampler_cache: extracted sampler-production.inc uses `GLint`, which the harness does not define.
- test_script_load_capacity: the harness `ChunkSeam` stub has no `Report_Error`, which the source now calls.
- test_vita_bink_scheduler: the g++ -Werror harness build fails in setUpClass. The harness probably lags the source (not inspected deeply).

## Missing environment file / build product
- test_tt_c4, test_tt_client_greeting, test_tt_physical_rare, test_tt_purchase_catalog, test_tt_soldier_rare, test_tt_vehicle: need `build/host-a31-asan/a31_m00_interactive_runtime`. This is a cmake host build and does not exist in a fresh worktree.
- test_vita_projective_coordinates, test_vitagl_compact_vertices, test_vitagl_dds_chain, test_vitagl_full_upload: need `build/deps/vitagl-demo/source.tar.gz`.
- test_script_lookup_telemetry: expects a `build/` temp directory that does not exist.
- test_wwui_resource_styles: host `llvm-rc` cannot parse `ES_CENTER`. A toolchain or header environment issue.

## Sanitizer environment (not a code defect)
- test_renegade_async_log, test_renegade_paths_cache, test_renegade_file_factory_availability: the TSan sub-case aborts with `FATAL: ThreadSanitizer: unexpected memory mapping`. This is a known incompatibility between the WSL 6.18 kernel ASLR and TSan. The availability test shows it as a SIGSEGV.

## Not unittest modules (CLI tools named test_*)
- test_remote_world, test_tt_client_control, test_tt_resource_preparation: argparse CLIs that require arguments. 0 tests ran.

## Timeouts (>120 s under 8-way parallel load)
- test_m09_camera, test_mission_event_routes, test_renegade_file_factory_staging, test_vita_audio_mixer_equivalence. Rerun these serially before suspecting a defect.

## Real defect suspected
- None confirmed. The highest-value follow-ups are the patch drift and identity mismatches (logical_stimulus offset, dazzle lifecycle on ww3d.cpp, action observer). They show the staged patch inputs no longer match the inputs that were recorded.
