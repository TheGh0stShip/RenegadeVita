# TUT-R1-20: host test runner (developer-loop performance)

Tutorial Round 1, item HOST_TEST_RUNNER. Base: `tutorial-r1/base` at 45c6cf5
(main plus the unmerged FPS round-4 candidate, dev240). Evidence class: host
only. Nothing was built for this item. Only the pure lane was executed.

## What changed

| File | Purpose |
| --- | --- |
| `tools/run_host_tests.py` | Static classifier, change-impact selector, parallel runner (stdlib only) |
| `tools/host_test_manifest.json` | Committed classification of every `tools/**/test_*.py` module |
| `tools/host_test_known_failures.json` | Curated pre-existing failures (reported as KNOWN, never hidden) |
| `tools/test_host_test_manifest.py` | Pure test: the committed manifest matches a fresh classification |
| `tools/test_run_host_tests.py` | Pure tests for the classifier, mapping, parsing, sharding and execution, on temporary fixture trees |

## How host tests ran before this item

- `tools/build.sh` runs about 60 hand-listed modules in one `python3 -m unittest`
  process, plus three more after staging. There is no lane split and no selection.
- CI (`compile-and-probes.yml`) runs `tools/run_python_contracts.py`, which loads
  every module into one process, sequentially, after the compiled probes.
- Recent fix-ledger work ran `python3 -m unittest discover -s tools -p <file>` per
  file, by hand, 4 in parallel.
- No record said which modules compile, need sanitizers, retail data, build
  outputs or a device, so agents that may not build could not tell what was
  safe to run.

## Classification (255 modules at this commit)

Static only: the runner parses each module and the local helpers it reaches
with `ast`. It never imports them. A module's lane is the heaviest one that applies:

| Lane | Modules | Meaning |
| --- | ---: | --- |
| pure | 157 (154 runnable, 3 argparse drivers excluded) | stdlib Python, patch/git/bash -n or python subprocesses only |
| retail | 0 | Python that locates the retail install (the one retail reader also compiles; see sanitizer) |
| artifact | 6 | needs `build/host-a31-asan/a31_m00_interactive_runtime` (the `test_tt_*` probes) |
| compiled | 37 | runs g++/c++/cmake/llvm-rc or the Vita cross compiler |
| sanitizer | 55 | compiles with `-fsanitize` unconditionally |
| device | 0 | every device-related test uses fixtures, mocks or `--dry-run` |

Tags (one module can carry several): `compiles-host-c++` 92, `compiles-vita-arm` 6,
`sanitizer-optional` 11 (behind an env switch), `tsan` 4 (`test_renegade_async_log`,
`test_renegade_paths_cache`, `test_a35_flight_background_flush`,
`test_renegade_file_factory_availability`, matching the fix ledger), `needs-upstream` 35,
`needs-build-artifact` 10 (the 6 artifact-lane modules plus 4 that need the
vitaGL source tarball), `optional-build-artifact` 3, `needs-retail-data` 1
(`test_cinematic_low_fps`, sanitizer lane), `needs-module:yaml` 1. Kinds: 247 unittest,
2 pytest-style function modules, 1 script, 3 argparse drivers. 20 modules
import sibling tools without the `tools.` prefix and run via `unittest discover`.

Main rules, in order of importance:

- A compile is a compiler token (`g++`, `c++`, `cmake`, `ninja`, `llvm-rc`,
  `arm-vita-eabi-g++`, ...) and a subprocess call in the same call closure. The
  closure follows local helpers function by function. A helper's `__main__`
  block and module-level argparse defaults are not reached by importing it, so
  `from tools.audit_m13_level_owners import chunks` stays pure.
- Paths are evaluated (`ROOT / "a" / "b"`, `Path(__file__).parents[1]`,
  `with_name`, `os.environ.get(..., default)`). A script counts as executed
  only when its path reaches a subprocess call's arguments. A script that is
  only read (most tests read `tools/stage_sources.sh`) does not count.
  Executed scripts are scanned in turn.
- `ninja -t` alone is a query of an existing build (artifact). Reads under
  `build/` without a skip guard are artifact. With a skip guard they are tagged
  `optional-build-artifact` and the lane is left alone.
- Three overrides, each with its reason recorded in the manifest:
  `test_vita_open_source_references` (runs the Vita3K runner only with
  `--dry-run`, which returns before launching), and the runner's own two tests,
  whose imported tables name compilers and devices as data.

## Pure lane timing (measured, this worktree)

Hardware: i5-1145G7, 4 cores / 8 threads, WSL2. Other agents in this round were
running at the same time (load average 1.3 to 3.4), so expect a few seconds of noise.

| Mode | Workers | Wall | Sum of module time |
| --- | ---: | ---: | ---: |
| runner, sequential (`--jobs 1`) | 1 | 62.2 s, 66.8 s | 62.0 s, 66.6 s |
| runner, parallel | 4 | 28.5 s | 113.4 s |
| runner, parallel (default `--jobs` = nproc) | 8 | 27.7 s, 29.4 s, 24.6 s, 28.1 s | 159 to 199 s |
| runner, parallel, with `--split-over 6` sharding | 8 | 28.2 s | 222.6 s |
| old style: one `python3 -m unittest` process, only the 133 modules importable by dotted name | 1 | 36.5 s | n/a |

All runs covered 154 modules and 1,012 to 1,015 test cases (the runner's own
tests grew during the work). Each produced the same 5 known problems listed
below and nothing else.

- Parallel is 2.3x to 2.7x faster than the sequential per-module run, and about
  1.4x faster than the old single-process style. The single-process figure also
  leaves out the 21 modules that need discover-style or function-style
  execution.
- The critical path is `tools.test_mission_event_routes`: two test cases of about
  5.5 s each, 10.9 s alone, but 23 to 29 s once all cores are busy and turbo drops.
  Sharding it by recorded per-test time spread the cases over workers but did not
  shorten the wall time on this laptop, so `--split-over` is off by default
  (rejected as default, kept as an option). Making those two cases cheaper is the
  next real gain for the pure lane.
- Classification costs about 4 to 5 s cold. It is cached in
  `build/host-test-manifest-cache.json`, keyed by the stat fingerprint of every
  `tools/` source, and takes 0.2 s warm. `--changed` mapping adds about 4 to 6 s.
  An agent loop on this item's own change (`--changed HEAD --pure-only`) took
  6.0 s end to end: 5 modules, 54 cases.

## Selective mode (`--changed`)

`--changed A..B` or `A...B` diffs commits. `--changed REV` diffs REV against the
work tree and includes untracked files. Each changed path selects:

- the test module itself, and every test that imports it, directly or through
  another test module;
- tests whose evaluated paths, globs, string-named files, or harness `#include`
  closure (compiled tests only) contain the path. A top-level directory alone
  (`port`, `tools`) is treated as a join root or `-I` path, not as a dependency on
  everything under it;
- for `port/patches/*.patch`, the staged files the patch rewrites, using the
  `-d "$rv_stage/<pool>" -pN` registration in `stage_sources.sh`;
- every test, for `CMakeLists.txt`, `cmake/*`, `tools/build.sh` and
  `tools/build_fast_candidate.sh`, and for `tools/stage_sources.sh` unless the
  only changed lines register patches. Those lines map to the named patches;
- unmapped files are listed. `--unmapped-fallback compiled` (the default)
  selects every compiled/sanitizer test for an unmapped C/C++ or
  port/staging/upstream file. `none` and `all` are also available.

Sample selections (all lanes): 4f29b2d (M10 patch + `stage_sources.sh`
registration) selects 64 modules, 27 of them because they read
`stage_sources.sh`. bdd853b (renderer vertex arrays) selects 32. 2ff842c (new
audit tool + test) selects 1. 6528a8e (LIVE_PROGRESS only) selects 0.

## How to run

Agents that may not build:

    python3 tools/run_host_tests.py --pure-only                   # all pure tests
    python3 tools/run_host_tests.py --changed main...HEAD --pure-only
    python3 tools/run_host_tests.py --changed HEAD --list --explain   # what and why

Coordinator, compiled lanes (not executed for this item; unverified here):

    python3 tools/run_host_tests.py --lanes compiled,sanitizer --jobs 8 --heavy-jobs 4
    python3 tools/run_host_tests.py --lanes artifact      # after tools/run_a30_host.sh
    python3 tools/run_host_tests.py --changed main...HEAD --lanes compiled,sanitizer,artifact

Prerequisites for those lanes:

- the `upstream/CnC_Renegade` submodule must be populated (35 modules read
  it; fresh worktrees have it empty);
- g++, cmake, ninja and llvm-rc must be on PATH. The VitaSDK cross compiler is
  needed for `compiles-vita-arm`;
- `build/host-a31-asan` must come from `tools/run_a30_host.sh`, or set
  `RENEGADE_HOST_RUNTIME`;
- `build/deps/vitagl-demo/source.tar.gz` must come from `tools/build_vitagl_demo.sh`.

TSan modules run under `setarch <arch> -R` automatically, because this WSL
kernel's ASLR breaks TSan. `--no-aslr-wrap` disables that. `--heavy-jobs` caps
concurrent compiled, sanitizer and device modules (default jobs // 2), so ASan
links do not exhaust memory. `--timeout` (default 900 s) applies per module and
kills the module's process group.

Each module runs in its own process with a private `TMPDIR`. Logs go to
`build/host-test-logs/<time>/`, the JSON summary to `build/host-test-summary.json`
(`--summary`), and duration history to `build/host-test-durations.json`. The
duration history drives longest-first scheduling. Pytest-style modules run
through `--run-function-tests`, without pytest. Argparse drivers named `test_*`
are excluded unless `--include-cli-drivers` is given. Modules whose third-party
import is missing are reported as unavailable, or fail with `--strict`.

Exit codes: 0 when every selected module passed, or nothing was selected. 1 when
a test failed, errored, timed out or ran no tests. 2 for usage or environment
errors. 3 when the manifest is stale (`--check-manifest`). 130 when interrupted.
With `--allow-known-failures`, the run exits 0 only if every problem is listed in
`tools/host_test_known_failures.json`.

After adding, renaming or reclassifying a test, run
`python3 tools/run_host_tests.py --write-manifest`.
`tools/test_host_test_manifest.py` fails with that command in its message when
the manifest is stale. If parallel branches each add tests, regenerate after
merging. The JSON is deterministic, so a conflict is resolved by regenerating it.

## Known and pre-existing failures

Reproduced in every pure-lane run at 45c6cf5 (none caused by this item):

- `test_action_observer_miss_telemetry`: stale `action.cpp` pin in
  `original_owner_source_replay.py`.
- `test_original_dazzle_lifecycle`, `test_original_decal_submission`: stale
  `ww3d.cpp` pin in `original_effect_source_replay.py`.
- `test_cinematic_filename_diagnostics` (2 cases): stale replay input. All of the
  above are as described in `FIX_LEDGER_INTEGRITY_2026-10-07.md` section 4.
- New finding: `test_campaign_flight_recorder_contract`
  `::test_campaign_flight_checkpoints_append_deltas_not_full_snapshots`.
  This pytest-style module was never executed before, because `python3 file`
  only defines its functions. Its first real run shows the token
  `persisted_frame_sequence / kFlightFrameCapacity` is gone from the flush code.

Reported by the coordinator:

- `test_vita_m13_cinematic_preparation` `.test_m01_referenced_textures_prepare_before_first_world_frame`:
  compiled lane, not run here, unverified.
- `test_vita_skin_submission_contract` `.test_vita_boundary_uses_original_material_color_with_textured_skin_passthrough`:
  pure lane, passed in every run here. It may be fixed at this base, or
  intermittent.

From the fix ledger, still expected in lanes I did not run:

- `test_vita_mesh_batch` and `test_vita_static_mesh_equivalence` (stale
  harnesses). This may have changed after FPS round 4's harness alignment.
- the six `test_tt_*` artifact probes, and the four vitaGL-tarball tests, when
  their inputs are absent.

## Other findings

- 17 pure modules (`test_renegade_asset_cache_*`, `test_probe_host_*_registry`,
  several `test_audit_*`, the sweep tests) fail with ModuleNotFoundError when
  run alone as `python3 -m unittest tools.<module>`, because they import
  siblings without the `tools.` prefix. In `run_python_contracts.py`'s single
  process they pass only when a module loaded earlier has already put `tools/`
  on `sys.path`. `tools/diagnostics/definition_factory_audit.py` and
  `tools/test_verify_repo_hygiene.py` do that at import. That is a hidden order
  dependency. The runner runs these modules with
  `unittest discover -s tools -p <file>`, which works on its own.
- In a fresh worktree the `upstream/CnC_Renegade` submodule is an empty
  directory. For the measurements I pointed it at the main checkout's populated
  copy. That local change was not committed, and the worktree was restored afterwards.

## Limits of the static scan

- It is conservative. A compiler name and an unrelated subprocess call in the
  same closure count as a compile.
- Commands built from function parameters are followed only through local
  helpers.
- A basename names a dependency only when at most 8 tracked files share it.
- Generated or inherited tests are never sharded.
- When a new pattern defeats the scan, add an `OVERRIDES` entry with a reason.
  The manifest shows it.
