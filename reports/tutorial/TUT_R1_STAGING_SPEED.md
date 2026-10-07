# TUT-R1-18 — Staging speed (build/dev-loop performance)

Scope: `tools/stage_sources.sh` cost on every build. Base: `tutorial-r1/base`
(45c6cf5, 577 registered patches, 15 managed staging directories, 1,948
staged files / 28.7 MB). The worktree was created from `main`. Because `main`
had moved past the round base, `git merge --ff-only tutorial-r1/base` failed.
The clean worktree branch was therefore pointed at 45c6cf5 before any work
began.

Evidence class: host only (WSL2 Ubuntu, GNU patch 2.7.6, bash 5, Python
3.14/3.12). No compiler or CMake was run, and neither was the real
`tools/stage_sources.sh` against the worktree. Byte-identity was proven by
sandboxed copies of the script, described in the equivalence section.

## What staging does (and where the time went)

1. It resets the 15 managed directories, then copies upstream pools with 13
   `find … -exec cp {} DIR/ \;` commands (about 1,770 files) plus a few
   explicit `cp` commands.
2. It applies 577 ordered `patch --batch --forward --fuzz=0` commands, one
   process each. Twelve of these are root-level (`-d "$rv_stage"`) and span
   modules. They are interleaved with 64 sha256 anchors (44 `test` lines,
   plus 20 assignment/`[[ ]]` blocks), one Python heredoc, the
   `restore_postthink_sampler.py` call and explicit alias refreshes.
3. A lower-case header alias pass runs mid-script over about 940 headers.
   Each header used `$(dirname)`, `$(basename)` and `$(printf | tr)`. Later
   patches intentionally leave some aliases stale, so this pass's position
   is semantic.
4. It runs a wwaudio `.H` alias loop with `$(basename … .h)` and a `touch`.
   In incremental mode it then syncs through a temporary tree.
5. It writes the `PATCH_INVENTORY.json` receipt. `renegade_patch_inventory.py`
   also runs as a `--count` preflight.

Phase breakdown from xtrace with `$EPOCHREALTIME` timestamps (one run each;
tracing inflates absolute values):

| Phase | Original | Candidate |
|---|---:|---:|
| Lower-case alias pass (~940 headers × ~5 forks) | 12.45 s | 0.09 s |
| Upstream pool copy (one `cp` per file) | 4.09 s | 0.13 s |
| 577 `patch` processes | 4.86 s | 2.29 s (same work; load noise) |
| Explicit/alias `cp` (193) | 0.54 s | 0.51 s |
| sha256 anchors | 0.45 s | 0.26 s |
| Python (inventory ×2, heredoc, sampler, fingerprint begin/record) | ~0.5 s | ~1.0 s |
| **Traced total** | **22.9 s** | **~4.7 s** |

Isolated measurements:

- **Pool copy:** 1,765 files took 3.98 s, 5.18 s and 6.72 s with one cp per
  file, against 0.13 s, 0.20 s and 0.28 s with `-exec cp -t DIR -- {} +`.
  Output bytes and modes were identical.
- **Alias-name derivation alone (1,057 headers):** 10.11 s down to 0.13 s.
  WSL2 forks of bash cost about 3 ms each.
- **Patch work:** 577 patches took about 1.6–2.1 s, including about 0.9 ms
  of spawn time per patch.
- **Hashing:** hashing the upstream pools (28 MB) takes about 0.06 s;
  hashing the staged tree takes about 0.08 s warm.

## Changes

1. **Batched pool copies.** In `stage_sources.sh` the 13 commands
   `-exec cp {} "$rv_stage/X/" \;` become `-exec cp -t "$rv_stage/X/" -- {} +`.
   The find predicates are unchanged.
2. **Fork-free alias pass.** `${p%/*}`, `${p##*/}` and `${name,,}` replace the
   subprocesses. A name containing any non-ASCII character still uses the
   original `tr` pipeline. The wwaudio loop now uses `${x##*/}` followed by
   `%.h`.
3. **`tools/staging_fingerprint.py` (new).** It provides `check`, `begin`,
   `record`, `plan` and `invalidate`, and writes only
   `build/staging-stamp.json` (gitignored).
   - **Inputs** cover the script bytes and the ordered patch identities. They
     also cover every upstream path the script names (`$rv_upstream/...`,
     directories hashed recursively without `.git`) and every repository
     file it names (`$rv_root/...`, such as `restore_postthink_sampler.py`,
     `bittype.h`, the inventory tool and this helper). Finally they include
     the GNU `patch` version. The Python version is deliberately left out:
     the Python steps do not depend on it, and including it would thrash
     the stamp between login and non-login WSL shells that resolve
     `python3` differently.
   - **Outputs** are a manifest of mode plus sha256 for every file in the
     managed directories, plus the receipt.
   - **Skip rule:** `check` exits 0 only if the inputs AND every staged byte
     match the stamp. The skip is therefore self-validating: tampering with
     the tree, switching branches or editing a staged file forces a restage.
   - **Race guard:** `begin` deletes the stamp and stores the inputs as
     pending. `record` refuses to write a stamp if the inputs changed while
     staging ran.
4. **Wiring.**
   - `stage_sources.sh` calls `begin` near the top and `record` after the
     receipt; both are non-fatal and only warn on failure. There is a new
     opt-in, `RENEGADE_STAGE_IF_CHANGED=1`, which skips staging when `check`
     passes. The default (used by canonical `tools/build.sh`) always does a
     full restage.
   - `build_fast_candidate.sh` previously skipped staging based on the
     receipt alone. It now also requires `staging_fingerprint.py check`;
     `RENEGADE_FAST_RESTAGE=1` remains the force override. This closes
     gaps the receipt never covered: changes to upstream content, helper
     scripts or `bittype.h`, and drift in the staged tree.
   - Tests: `tools/test_staging_fingerprint.py` (19 tests) and two new
     contract tests in `test_stage_sources_incremental_contract.py`. Both
     are registered in the test lists of `build.sh` and
     `build_fast_candidate.sh`.

## Measured results (sandbox, same machine, alternating runs)

| Scenario | Before | After |
|---|---:|---:|
| Canonical full staging (6 runs each) | 14.5–27.2 s (last batch median 16.5 s) | 5.3–6.6 s (last batch median 5.9 s) |
| Fast build, nothing changed | receipt check ~0.15 s | receipt check ~0.15 s + fingerprint check ~0.4 s |
| `RENEGADE_STAGE_IF_CHANGED=1`, nothing changed | n/a (full) | 0.56–0.62 s wall |
| Restage after a patch/script change (incremental) | ≈ full staging + sync (estimated 15–27 s) | 5.1 s measured; sync copied 0 unchanged files |

The canonical build saves about 10–15 s of staging per build (about −65%).
A fresh worktree with no stamp restages once on its first fast build. That
takes about 5 s and preserves mtimes, so Ninja does not rebuild anything.

## Per-module fingerprints and why execution stays whole-tree

The helper splits the script into units: a command, an `if`/`for`/`while`/`case`
block, or a command with its here-document. It then attributes each unit:

- Each managed directory owns its ordered patch applications. Root-level
  patches are attributed by their `---`/`+++` paths.
- A directory also owns the units that name only it: copies, anchors, the
  `if [[ "$rv_x_sha" … ]]` blocks that read its anchor variable, and helper
  calls together with their file inputs.
- Literal `echo` and comment lines are inert.
- Everything else is global: the skeleton, the alias pass, the incremental
  sync, the receipt and the tool versions.
- A `cp A/x B/y` adds the edge A→B; any other multi-module unit couples its
  modules.

`plan`/`check` report the closure of dirty modules with reasons, for
example: "scripts: patch changed …; combat/ww3d2/wwphys: reads scripts".
On the real script, every registered patch is attributed to a managed
module, all anchor blocks are module-scoped, and 18 units are global. The
edges are wwlib→wwaudio, wwmath→wwaudio and wwmath→combat, plus the coupling
of combat, scripts, ww3d2 and wwphys created by the trailing-blank-line
heredoc.

Partial (per-module) execution was deliberately not wired up:

- Anchors use `if [[ … ]]` keyword blocks, which cannot be shadowed. A
  module-filtered replay would therefore need a shell slicer or a second
  interpreter of the staging language. Either would be a second source of
  truth that the coordinator cannot verify cheaply.
- Cross-module data flow exists: 3 cp edges, 12 root-level patches and the
  4-module heredoc. The mid-script alias pass's deliberately stale aliases
  also make ordering semantic.
- After the changes above, the best case is bounded by the clean modules'
  patch time, about 1–2 s of a 5–6 s run.

Running independent modules in parallel was rejected for the same reasons.
Patch runs are separated by barriers (anchors and cross-module operations),
and only about 1.5 s could be saved. If this is wanted later, the safe path
is a declarative per-module operation registry iterated by the bash script.
The helper's per-scope ordered entries and edges already model that
registry. The "append one patch line" workflow stays unchanged either way.

Remaining cost, not changed here:

- The 577 patch processes are inherent to per-patch zero-fuzz attribution.
- About 190 alias `cp` processes cost about 0.5 s. Their positions are
  semantic.
- Anchors cost about 0.3 s. Editing the 64 copy-pasted anchor lines would
  invite merge conflicts.

## Equivalence argument

- **Copy:** the same predicates select the same files. With GNU `cp -t DIR`
  the bytes and modes match the per-file form (umask-masked source mode).
  The order of copies is irrelevant because each target is a distinct name
  in a flat directory. The only behavioral difference is on failure:
  `find -exec … +` exits non-zero when cp fails, so staging now stops
  instead of silently missing a file.
- **Alias pass:** paths printed by `find "$rv_stage"` are absolute and have
  no trailing slash, so `%/*` and `##*/` equal `dirname` and `basename`.
  For ASCII names, `${name,,}` equals GNU `tr '[:upper:]' '[:lower:]'`,
  checked over all 1,104 staged `.h` names under C.UTF-8 with 0
  mismatches. Non-ASCII names keep `tr`; upstream has none. The find
  iteration order and the `! -e` guard are unchanged, and there are no
  case-collision groups.
- **Fingerprint:** it writes only under `build/`, and its failures never
  fail staging.
- **Sandbox proof:** both the committed script and the candidate script were
  run in fake roots under `build/stagebench/` (copied tools and patches,
  with upstream symlinked read-only).
  - The committed script reproduced the tracked `staging/` byte-for-byte,
    receipt included, which validates the harness.
  - The candidate produced 1,947/1,947 source files with identical bytes and
    modes, and 0 `.orig`/`.rej` files.
  - Its receipt differs only in `stage_script_sha256`/`registry_sha256`. The
    patch list, order, hashes and count of 577 are identical.
  - An incremental candidate run synced 0 copied / 1,947 unchanged files.
  - Skip, tamper, patch-edit and restore cycles behaved as designed.

## Coordinator verification on integration

The receipt in this branch is deliberately not regenerated. Because the
script bytes changed, `--check-staging` reports a stale receipt until the
usual refresh.

1. Merge only this branch onto the base. Run
   `bash tools/stage_sources.sh`. Then:
   - `git status --porcelain -- staging ':!staging/PATCH_INVENTORY.json'`
     must be empty.
   - `git diff staging/PATCH_INVENTORY.json` must show only
     `stage_script_sha256` and `registry_sha256`.
   - `find staging \( -name '*.orig' -o -name '*.rej' \)` must print
     nothing.
2. Run `RENEGADE_INCREMENTAL_STAGE=1 bash tools/stage_sources.sh`. The sync
   JSON totals must show `"copied": 0`.
3. Run `RENEGADE_STAGE_IF_CHANGED=1 bash tools/stage_sources.sh`. It should
   print `Staging fingerprint FRESH` and then `Staging skipped`, in under
   1 s. Append a byte to any staged file and run it again: it should
   restage, reporting `STALE_OUTPUTS`.
4. Run `python3 -m unittest tools.test_staging_fingerprint tools.test_stage_sources_incremental_contract tools.test_sync_staged_tree tools.test_fast_candidate_build_contract`.
5. Optional A/B timing: `time bash tools/stage_sources.sh` before and after
   the merge.

## Conflict risk

- **`tools/stage_sources.sh`:** this branch adds a 12-line block after the
  environment parsing, edits the 13 `find` copy lines, the alias loop and
  the wwaudio loop, and appends 2 lines after the receipt line. Appended
  patch lines from other agents go before the sync/receipt block, so the
  hunks do not touch. The receipt needs the normal refresh.
- **`tools/build_fast_candidate.sh`:** one condition line, one echo line and
  one test-list line. TUT-R1-17 (ccache) may edit this file elsewhere, so
  the risk is low.
- **`tools/build.sh`:** one test-list line.
- **New files:** `tools/staging_fingerprint.py`,
  `tools/test_staging_fingerprint.py` and this report.
