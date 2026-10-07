# TUT-R1-17: ARM/host compile time (BUILD_COMPILE_TIME)

Round: Tutorial Round 1, base `45c6cf5` (main + FPS round-4 dev240).
Scope: wall-clock compile time of the Renegade sources. Separate agents own
`tools/stage_sources.sh` speed (TUT-R1-18) and third-party dependency
caching (TUT-R1-19).

Nothing was built for this report. The evidence comes from existing
`.ninja_log` files, `build.ninja` files, one read-only `ninja -t deps` dump of
the main checkout's `build/vita-fast-candidate`, `local-builder/logs`, read-only
`ccache --show-stats`, the installed ccache manual
(`/usr/share/doc/ccache/MANUAL.adoc.gz`) and the ccache binary's option table.

Host: i5-1145G7 (4 cores / 8 threads), 15 GiB RAM, ninja 1.11.1, ccache
4.9.1, VitaSDK GCC 15.2. Builds use 8 jobs, so logged durations include
hyper-threading contention and any concurrent sessions. Read the numbers as
estimates and compare like with like.

## Findings

### A. Canonical ARM builds never hit ccache (cause: `-g` plus a new directory)

`tools/build.sh` configures a new `build/vita-<stem>-candidate-<timestamp>`
directory for every build. The Vita target is `RelWithDebInfo` (`-O2 -g`).
With `-g`, ccache hashes the working directory by default (`hash_dir`)
because GCC writes it to `DW_AT_comp_dir`. Every canonical build therefore
misses every ARM object. The retained experiment
`experiments/canonical-cache-identity` reproduced this with the real ARM
compiler: two sibling directories gave two misses, and a debug prefix map gave
one miss then one direct hit, with byte-identical objects and identical `.text`.

| Evidence (all canonical Vita dirs, 2026-08-24 to 2026-10-03) | Value |
|---|---|
| Full canonical ARM builds (more than 400 compiles) | 138 |
| Compile edges | 71,490 |
| Sub-second compile edges (likely hits) | 3,022 (4.2%) |
| Mean ARM stage wall time | 543 s |
| dev209 / dev210 / dev211 ARM stage wall time | 1,333 / 903 / 1,775 s |
| dev209–211: sub-second compiles out of 652 | 1 each |

The canonical logs report about 81% ccache hits overall (dev210: 2,554 / 3,149).
Those hits come from the host builds, which use stable directories.

### B. 63 translation units always bypass ccache (backslash include)

`staging/commando/gamedata.h:51,53` contain `#include <WWLib\Notify.h>` and
`<WWLib\Signaler.h>`. GCC finds these through the literal backslash alias
files in `port/compatibility/include/`. In the `ninja -t deps` dump, 597 TUs
have the relative header paths that ccache's `base_dir` rewriting produces.
The other 63 TUs have absolute paths, which means ccache gave up and ran the
original command. All 63, and only those 63, include `WWLib\Notify.h`
(62 also include `WWLib\Signaler.h`). No cached TU includes either file.

This group contains 60 `staging/commando` TUs, `a31_vita_runtime.cpp`,
`a31_gameplay_boundary.cpp` and `a31_client_connect_boundary.cpp`. It matches
ccache's "Could not read or parse input file" counter: 1,112 cumulative in the
main cache, and 83 of 685 calls in the fps-r4 worktree build.

Likely mechanism (inferred, not traced): GCC escapes `\` as `\\` in
preprocessor linemarkers. ccache 4.9 takes that path verbatim, `stat` fails,
and ccache reports `bad_input_file` and compiles without caching.

| Build | Bypassed TUs | Their compile serial | LPT on 8 jobs | Share of compile serial |
|---|---|---|---|---|
| dev210 canonical | 63 | 960 s | 125 s | 14% |
| dev211 canonical | 63 | 1,512 s | 195 s | 11% |
| fps-r4 worktree, last session | 62 | 1,091 s | 138 s | 41% |
| main fast dir, latest per TU | 63 | ~1,040 s (`staging/commando`) | — | 71% |

These TUs recompile whenever Ninja reruns them, including in every new build
directory and every new worktree, even when the cache is warm.

### C. Integration worktrees start with an empty cache

`CCACHE_DIR=$rv_root/build/ccache` is per tree. The dev240 build in
`.claude/worktrees/fps-r4-integration` reported 0 / 602 hits, with a 0.1 GiB
cache against ccache's default 5 GiB limit. The main cache holds 11.1 GiB
(`max_size = 16G`).

A shared directory alone would not fix this. `-g` hashes the working
directory, and that path differs in every worktree. Sharing therefore needs
change A2 below as well. `CCACHE_BASEDIR` is already the tree root. The deps
dump confirms that ccache 4.9.1 rewrites the concatenated
`-include/abs/.../msvc_compat.h` form to a relative path (its option table
marks `-include` as taking a concatenated path argument), so command lines
already match across trees.

### D. Unused target-wide definitions rewrite every compile command

`RENEGADE_VITA_A31_ORIGINAL_SOURCES` and `RENEGADE_VITA_A30_PORT_SOURCES` are
list lengths passed to all 681 TUs. No source in `port/` or `staging/` reads
them. They changed from 602 / 36 at dev211 to 632 / 38 at dev240, as sources
were added. Each change rewrites every compile command, so Ninja reruns all
681 edges and ccache's direct mode misses each one. At best it falls back to
a preprocessor-mode hit, which still costs one `cpp` run per TU. The 63 TUs
from finding B fully recompile.

### E. Build identity is already isolated

`generated/renegade_build_identity.h` reaches 4 TUs: `a31_vita_runtime.cpp`
(22 uses), `a30_vita_runtime.cpp`, `a30_main.cpp` and `vita_platform.cpp`.
The candidate label does not appear in any compile flag; it is only in the
link map path and the packaging steps. No `__DATE__`, `__TIME__` or
`__TIMESTAMP__` appears in `port/` or `staging/`.

The dev238 fast build is a label bump plus one renderer edit. It recompiled
exactly those 4 TUs plus `ww3d_vita_renderer.cpp` in 41.4 s wall. Of that,
`a31_vita_runtime.cpp` took 23.4 s, then link 8.3 s, velf 1.7 s and
`eboot.bin.out` 6.7 s. No change is needed here; see recommendation R6.

### F. The critical path and scheduling

Cold builds are limited by throughput, not by dependencies:

- Parallel efficiency is 0.95 (dev210/211) and 0.89 (fps-r4).
- The dependency critical path is the slowest TU plus the link chain. In
  dev210 that is `Mission01.cpp` 164 s + link 8 s + velf 5 s + SELF 7.5 s,
  187 s in total. In dev211 it is 297 s.
- Ninja 1.11 starts edges in manifest (source-list) order, so the mission
  scripts, which come late in the list, start last. Scheduling longest-first
  (LPT) would finish in 335 s instead of the observed 375 s for fps-r4 (−11%),
  and in 1,686 s instead of 1,775 s for dev211 (−5%).

Slowest TUs in dev211 (8-way contended):

| TU | Time |
|---|---|
| `Mission01.cpp` | 231.6 s |
| `Mission04.cpp` | 135.9 s |
| `raveshawbossgameobj.cpp` | 132.9 s |
| `Mission11.cpp` | 126.4 s |
| `Mission05.cpp` / `Mission07.cpp` | 98 s each |
| `mission08.cpp` | 88.1 s |
| `hud.cpp` | 83.3 s |
| `a31_vita_runtime.cpp` | 63.7 s |

Compile time by directory in dev211:

| Directory | Time | TUs |
|---|---|---|
| `staging/combat` | 3,255 s | 125 |
| `staging/ww3d2` | 2,170 s | 80 |
| `staging/commando` | 1,960 s | 92 |
| `staging/scripts` | 1,757 s | 44 |
| `staging/wwphys` | 1,671 s | 93 |

## Changes on this branch

All changes are opt-in. With none of the new environment variables set, the
compile commands, launcher, cache location and objects are the same as on
the base.

1. **`RENEGADE_CCACHE_DIR=<absolute path>`** (environment; read by
   `cmake/RenegadeCcache.cmake`, and by `tools/build.sh`,
   `tools/build_fast_candidate.sh` and `tools/run_a30_host.sh` for the
   exported `CCACHE_DIR` and the `build.ninja` check).
   - It moves the cache to a shared directory.
   - In shared mode only, the launcher adds `CCACHE_SLOPPINESS=locale`.
     This is output-neutral: LANG only changes the language of diagnostic text.
   - No other sloppiness is used. `hash_dir`, `time_macros`,
     `include_file_mtime` / `include_file_ctime` and `system_headers` stay at
     their safe defaults, and a contract test enforces this.
2. **`RENEGADE_CCACHE_RELOCATABLE_DEBUG=1`** (environment, or the CMake option
   of the same name).
   - It adds `-fdebug-prefix-map=<binary dir>=/renegade-vita/<parent>/obj`.
     The pseudo path has the same depth as the build directory, so the
     relative names `../../staging/...` resolve below `/renegade-vita`.
   - Only `DW_AT_comp_dir` in the debug sections changes. `-ffile-prefix-map`
     is deliberately not used, so `__FILE__` and `.rodata` are untouched.
   - To find sources in gdb, run `set substitute-path /renegade-vita <tree>`.
3. **`RENEGADE_OMIT_SOURCE_COUNT_DEFINES=1`** (environment, or the CMake
   option). It drops the two unused definitions from finding D. With the
   option off (the default), CMake's sorted `DEFINES` string is unchanged.
4. **`tools/ninja_log_report.py`** (read-only, pure Python). It reports:
   - per-session or latest-per-output summaries and the slowest edges;
   - per-directory totals and maximum concurrency;
   - the observed critical chain and the LPT estimate;
   - with `--build-ninja`, the real dependency critical path;
   - with `--deps-dump`/`--base-dir`, the ccache-bypassed TUs (absolute
     depfiles) and the headers they share.

   Tests: `tools/test_ninja_log_report.py` (13 tests on a synthetic log,
   manifest and deps dump).
5. **`tools/test_build_cache_opt_in_contract.py`** (6 text contracts). They
   check that the defaults keep today's launcher, defines and script checks;
   that the prefix map exists only under the opt-in; that no correctness
   sloppiness is set; and that no TU reads the count definitions.

Usage for integration worktrees:

```
export RENEGADE_CCACHE_DIR=/home/steve/projects/RenegadeVitaBuilder/ccache-shared
export RENEGADE_CCACHE_RELOCATABLE_DEBUG=1
ccache -d "$RENEGADE_CCACHE_DIR" -M 20G        # one-time size limit
RENEGADE_FAST_TESTS=none bash tools/build_fast_candidate.sh
python3 tools/ninja_log_report.py build/vita-fast-candidate --build-ninja build/vita-fast-candidate/build.ninja
```

Note: `tools/build.sh` still runs `ccache --zero-stats`. In shared mode, this
resets the shared counters for every user of that cache.

## Verification status

Verified:

- The unit and contract tests pass (`python3 -m unittest
  tools.test_ninja_log_report tools.test_build_cache_opt_in_contract
  tools.test_fast_candidate_build_contract tools.test_canonical_retry_directory`).
- The three edited scripts pass `bash -n`.
- Every evidence number above was produced by the new tool or by read-only
  queries.

Unverified, because no configure or build was allowed:

- CMake has not configured the edited module or `CMakeLists.txt`.
- The real hit rates with the new options are not measured.
- Object identity for option 3, and for option 2 beyond the earlier
  single-fixture experiment, is not checked.
- The inferred ccache mechanism in finding B is not traced.

Coordinator check, one build pair each:

1. Option 2: run two consecutive canonical (or fast, new-directory) builds
   with `RENEGADE_CCACHE_RELOCATABLE_DEBUG=1`.
   - Expect about 618 / 681 ARM hits on the second build. The 63 TUs from
     finding B still miss.
   - Compare the ELF `.text` and `.data` (`arm-vita-eabi-objcopy -O binary
     --only-section=...`) and the `eboot.bin` hash against a default build of
     the same source.
   - `readelf --debug-dump=info` should show
     `DW_AT_comp_dir: /renegade-vita/build/obj`.
2. Option 3: build the same directory with and without
   `RENEGADE_OMIT_SOURCE_COUNT_DEFINES=1` and run `cmp` on every `.obj`.
   They are expected to be identical, because GCC leaves `-D` out of
   `DW_AT_producer` and emits no macro info at `-g`.
3. Option 1: with both variables set, build worktree A and then worktree B.
   B should hit for every TU that is not affected by finding B.

## Recommendations (estimates)

| # | Action | Estimated effect | Artifact impact |
|---|---|---|---|
| R1 | Staging patch for `commando/gamedata.h` lines 51 and 53: `<WWLib\Notify.h>` → `"notify.h"`, `<WWLib\Signaler.h>` → `"signaler.h"`. These resolve through the same `-I` chain to `staging/wwlib/notify.h` and `signaler.h`, exactly as the alias's own `#include "notify.h"` does: neither `port/compatibility/include/` nor `staging/commando/` contains a `notify.h` or `signaler.h` (`staging/wwlib` holds both case variants). It needs the normal patch-inventory process, which this agent may not edit. The other 11 backslash alias headers probably cause the host-build "errors" too (238–242 per canonical run). | −125 to −195 s on every new-directory or worktree ARM build; makes `a31_vita_runtime.cpp` cacheable | No code change expected (the alias headers contain no code) |
| R2 | After the option 2 check passes, make relocatable debug the default. | Canonical ARM stage: 543 s mean → about 150–250 s today, about 30–90 s with R1. Over the last 138 canonical builds that would have saved about 13 h of wall time, or about 17–19 h with R1. This assumes most TUs are unchanged between consecutive candidates; the stable fast directory hits 86%. | DWARF `comp_dir` only |
| R3 | Shared cache for integration and agent worktrees (options 1 and 2). | A new worktree's first ARM build drops from a cold 6–15 min to about 1–3 min | None |
| R4 | After the `cmp` check, make option 3 the default. | Adding a source no longer reruns about 680 compile edges in stable directories. Estimated 2–4 min saved per source-list change. | None expected |
| R5 | Ninja ≥ 1.12, whose critical-path scheduling uses `.ninja_log` history. It cannot be installed in this round. Reordering CMake sources instead would change link order and the ELF, so do not. | 5–11% on cold builds in stable directories | None |
| R6 | Split `a31_vita_runtime.cpp` (7.6k lines; edited in 85 of 612 commits since 2026-09-15) into 3–4 TUs, keeping the identity macros in one small TU. Not done, per instructions. | Incremental fast-build critical path −12 to −16 s (23.4 s TU → about 6–8 s) | Code moves; needs normal validation |
| R7 | PCH for `msvc_compat.h`, `win32_compat.h` and the core wwlib headers (195 headers per TU on average; the smallest TUs take 3–5 s against a 20 s average under contention). | About 15–25% of cold compile time; nothing on cache hits. GCC PCH with ccache needs `pch_defines,time_macros` sloppiness and `-fpch-preprocess`. | Low priority after R1/R2 |
| R8 | Unity builds: not recommended. | About 20–35% on cold builds | Changes codegen through cross-TU inlining, risks name clashes between file-statics in the original Westwood code, and makes every edit invalidate a whole chunk. |
| R9 | Profile the mission scripts (`Mission01.cpp`, 22k lines, 164–232 s) with `-ftime-report`. If debug var-tracking dominates, try an opt-in `-fno-var-tracking-assignments` for `staging/scripts` (debug info only). | Unmeasured | Debug info only |
| R10 | Use `CCACHE_STATSLOG=<build>/ccache-stats.log` with `ccache --show-log-stats` to get per-build hit rates instead of cumulative or zeroed counters. | Diagnostic only | None |

Measured per-step tail after the compiles: link 8–30 s, velf 2–6 s,
`eboot.bin.out` (vita-make-fself) 7–24 s. These can't be shortened without
changing artifacts.
