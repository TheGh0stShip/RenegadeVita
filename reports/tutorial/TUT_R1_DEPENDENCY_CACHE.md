# TUT-R1-19: content-addressed dependency cache

Status: implemented and host-tested with synthetic inputs. **Nothing was
built.** No ARM build, Vita3K run or device test was done. The cache is
**opt-in**. With no environment variable set, all three dependency scripts
take their existing path.

Base: `tutorial-r1/base` (45c6cf5). Branch: `tutorial-r1/tut-r1-19-dependency-cache`.

## 1. Facts (read-only inspection of the main checkout and the `fps-r4-integration` worktree)

| | vitaGL | FFmpeg (Bink) | curl + Mbed TLS (TTFS HTTPS) |
| --- | --- | --- | --- |
| Script | `tools/build_vitagl_demo.sh` | `tools/build_ffmpeg_bink_vita.sh` | `tools/build_ttfs_https_vita.sh` (skipped when `RENEGADE_M00_DEMO=1`) |
| Called by | `build.sh`, `build_fast_candidate.sh`, every candidate | same | same |
| Pinned source | codeload tarball of commit `6e7fe402…`, **no pinned SHA-256**, stored in `build/deps/vitagl-demo/source.tar.gz` (9.6 MB, per tree) | `ffmpeg-9.0.1.tar.xz`, SHA-256 pinned in the script, in source-cache | `mbedtls-3.6.5.tar.bz2`, `curl-8.22.0.tar.xz`, both SHA-256 pinned, in source-cache |
| Patches / flags | 8 ordered zero-fuzz patches from `port/renderer/vita/dependency-patches/`; explicit `CFLAGS` (`-O3`, no fast-math) plus the FFP digest define; `make -B -j${RENEGADE_BUILD_JOBS:-8}` | configure line in the script (Bink only, `-O3`) | `config.py` option edits; CMake/Ninja, `-j${RENEGADE_DEPENDENCY_JOBS:-2}` |
| Output used by CMake | `build/deps/vitagl-demo/libvitaGL.a` (6.3 MB) and the patched `source/source/` include directory (`vitaGL.h`) | `build/deps/ffmpeg-bink-vita/{include,lib,share}` (5.0 MB) | `build/deps/ttfs-https-vita/{bin,include,lib,share}` (5.4 MB) plus a 93–96 MB work directory |
| Linked into the game ELF | yes | yes | **no**. Used only by the `EXCLUDE_FROM_ALL` probe targets and the host ARM closure. |
| Existing in-tree reuse check | `build.identity` = hash of `sha256sum` lines (these include **absolute paths**) plus `gcc --version` and flags | stamp text equals `ffmpeg-9.0.1-…-v3-speed` and 5 libraries exist. It does **not** cover flags, script or toolchain. | `inputs()` `sha256sum` lines (include **absolute paths**) plus the library hashes |
| Measured cold build | **63 s** (main, 2026-10-04 13:10:43→13:11:46); **~105 s** (fps-r4-integration, 2026-10-07 06:46:21→06:48:05) | **161 s** (configure 21 s + make/install 139 s; object mtimes, 2026-09-14) | **316 s** (fps-r4-integration log 06:49:11→06:54:27, `-j2`) |

These are not built: `mpg123`, `freetype`, `png`, `bz2`, `zip`, `z`,
`vitashark`, `SceShaccCgExt` and `mathneon` are VitaSDK packages.
`build_renegade_demo_recorder_plugin.sh` is not called by the candidate
builds.

**Does each worktree rebuild them?** Yes. `build/deps` is in the tree, and
each tree has only one slot per dependency.
`fps-r4-integration` was seeded by copying the main checkout's `build/deps`.
Its first build on 2026-10-07 went like this:

- It downloaded the FFmpeg, Mbed TLS and curl archives again into
  `.claude/source-cache`. In a worktree, `$rv_root/../..` resolves to
  `.claude/`, not to the managed source-cache.
- It rebuilt vitaGL. The patches had changed, and the identity also includes
  paths.
- It **failed** in the HTTPS step. The copied `ttfs-https-vita-build/*/CMakeCache.txt`
  still pointed at the main tree (log `a35-dev240-fast-20261007-064618`).
- After those build dirs were removed, it rebuilt HTTPS in 316 s. Every input
  content hash was identical to main's (`.https-inputs.sha256` differs only in
  paths). The rebuild happened only because the identity includes absolute
  paths.

**What "full ARM build (vitaGL rebuild)" in `LIVE_PROGRESS.md` implies:**

- The main checkout's `libvitaGL.a` dates from 2026-10-04 13:11 and has 5
  patches.
- Main's script has applied 6 patches since e336772, and round 4 brings 8.
  Each change of patch set pays a cold vitaGL build.
- Moving one tree back and forth between patch sets (main ↔ integration) pays
  it again on every move, because the single slot is overwritten.

### Pre-existing gaps found (not changed, so artifacts stay identical)

1. **Two VitaSDKs are in use, and the existing checks cannot tell them apart.**
   - Main's FFmpeg was configured with
     `--cross-prefix=/home/steve/.local/vitasdk/bin/…`. Main's `libvitaGL.a`
     has DWARF include paths under `/home/steve/.local/vitasdk`. That SDK was
     built 2026-08-25 with different newlib, vita-headers and toolchain
     commits.
   - The fps-r4 worktree built against `/usr/local/vitasdk` (built
     2026-05-24).
   - Both produce byte-identical `gcc --version` text, and their gcc drivers
     differ (`0295…` vs `76be…`).
   - The FFmpeg stamp ignores the toolchain completely.
2. Copying `build/deps` between trees cannot work. The path-bearing identities
   force rebuilds, and the copied CMake caches break the HTTPS build.
3. **vitaGL revision-bump hazard.** If `revision=` changes, the old
   `source.tar.gz` and the old `source/` extraction are reused. Only the 7
   re-extracted files come from the archive, and that archive is also the old
   one. The cache key is not affected, because it hashes the compiled tree.
4. The vitaGL archive has no pinned SHA-256.
5. HTTPS defaults to `-j2`. HTTPS is built for every campaign candidate but is
   not linked into the game.

## 2. Design

- **`tools/dependency_cache.py`** (stdlib only) has four subcommands:
  - `key` hashes ordered, typed inputs by **content only**:
    `--source`, `--patch` (order matters), `--script`, `--file LABEL=PATH`,
    `--value LABEL=VALUE`, `--flags=VALUE` and `--tree LABEL=DIR` with
    `--tree-exclude`. It returns SHA-256 of a canonical JSON document, so the
    same inputs in any worktree give the same key. `--explain-out` writes that
    document.
  - `store` copies the outputs into `<cache>/<name>/.tmp-*`. It hashes every
    file before and after the copy, then writes `manifest.json` with the
    path, SHA-256, size and mode of each file, the directories, the outputs,
    the producer root and the key document. The entry is published by atomic
    rename. If an existing entry is valid, store is a no-op. If it is corrupt,
    store replaces it. `--require-complete` refuses to store a prefix that has
    top-level entries the restore would drop.
  - `restore` verifies the schema, name, key, output list, exact file and
    directory set, sizes and hashes. It also checks that the recorded key
    document hashes to the key. Then it copies into a staging directory,
    re-hashes every copy, and swaps the copies into place
    (`--replace-dest` swaps the whole prefix). Exit codes: 0 verified hit,
    3 miss, 4 rejected. The destination is untouched on a miss or a rejection.
    Restored files get **fresh mtimes**, so ninja relinks against a restored
    library.
  - `verify` re-checks one entry or all entries.
- **`tools/dependency_cache.sh`** is a small sourced library. It is enabled
  only by `RENEGADE_DEPENDENCY_CACHE=1` or by `RENEGADE_DEPENDENCY_CACHE_DIR`.
  `RENEGADE_DEPENDENCY_CACHE=0` forces it off. Every lookup in the scripts is
  guarded by `rv_depcache_enabled &&`, so a disabled run expands no key
  arguments and runs no Python. The default location is
  `build/dependency-cache` (git-ignored). Any key, verification or copy
  failure falls back to the existing build. A failure to store never fails a
  build.
- **Integration.** The cache is consulted only where the script would
  otherwise build:

| Script | Lookup point | Key inputs | Cached outputs |
| --- | --- | --- | --- |
| vitaGL | after re-extracting and patching, just before `make` | script, revision, `source.tar.gz`, 8 patches in application order, **digest of the compiled tree** (`source/` without `*.o`/`*.a`), SDK realpath, gcc driver SHA-256, `version_info.txt`, `gcc --version`, flags, FFP digest | `libvitaGL.a`. Provenance and identity are written as normal, and a hit adds one `dependency_cache=restored key=…` line to `provenance.txt`. |
| vitaGL archive | only when `source.tar.gz` is missing | revision | `source.tar.gz`, which removes the codeload download in a fresh worktree |
| FFmpeg | after the stamp check, before configure | script (which covers the pinned archive hash and every flag), archive, config id, SDK realpath, gcc driver, `version_info.txt`, `gcc --version` | `include lib share` (prefix replaced). The stamp is rewritten. |
| HTTPS | after the `inputs()` check, **before the downloads** | the same files as `inputs()`, hashed by content, plus `version_info.txt` and the SDK realpath | `bin include lib share` (prefix replaced). The stamps are rewritten through the new `record_stamps`. |

`build.sh` and `build_fast_candidate.sh` are **not modified**. The variables
pass through the environment.

### Artifact identity

- A hit restores exactly the bytes that a real build with the same key
  produced. This is verified twice.
- **Same tree:** a rebuild would produce the same objects. Today `libvitaGL.a`
  and the curl/Mbed TLS archives already differ between rebuilds in their ar
  member mtimes. FFmpeg's archives are deterministic. The linker does not copy
  ar headers into the ELF, so a hit is expected to give the same
  ELF/SELF/VPK. This is unverified.
- **Shared across trees:** a hit carries some producer-tree path text:
  - vitaGL DWARF `DW_AT_comp_dir`;
  - FFmpeg's `--prefix` configuration string;
  - the `.pc` and `curl-config` text.

  The ELF debug sections can then name the producer tree. Each tree's own
  Renegade objects already embed its path, so ELF bytes already differ
  between worktrees. These strings are expected not to reach `eboot.bin`
  (unverified).
- The key does not cover the host `make`, `patch` or `cmake` versions, or
  unmanaged edits to the VitaSDK sysroot (`arm-vita-eabi/include` and `lib`)
  that leave `version_info.txt`, the gcc driver and the hashed libraries
  unchanged. The key is still a strict superset of what today's in-tree checks
  trust. Because it does not provably cover every input, **the cache stays
  off by default**.

## 3. Estimated savings (not measured end to end; no build was run)

| Situation | Today | With a warm cache |
| --- | --- | --- |
| Same tree, inputs unchanged | 0 s (in-tree checks skip) | 0 s (the cache is not consulted) |
| Same tree, moving back to an earlier vitaGL patch set (main ↔ integration) | 63–105 s per move | ~0.7 s (real-input vitaGL key 0.45 s + restore) |
| New worktree with a shared cache | ~9–10 min serial (vitaGL 63–105 s + FFmpeg 161 s + HTTPS 316 s) + 3–4 downloads; seeding by copy fails or rebuilds HTTPS | a few seconds: archive extract and patching (~1–2 s), keys (~0.5 s each) and restores (measured on the real 5.4 MB HTTPS prefix: store 0.30 s, restore 0.23 s). FFmpeg still verifies its archive from source-cache. |
| 20-worktree round, each building once | up to ~3 h cumulative dependency build time | one cold build per distinct key |

## 4. Verification steps for the coordinator

1. Host tests (pure Python plus bash, no compiler):
   `python3 -m unittest tools.test_dependency_cache` gives 23 OK. The existing
   script-parsing tests still pass:
   - `test_vita_indexed_vertex_records…test_build_script_applies_records_patch_last`
   - `test_vita_ffp_program_cache…test_build_script_applies_versions_and_reextracts`
   - `test_vita_static_mesh_cache…test_array_and_immediate_layout_transitions_repatch`
   - `test_a4_original_frontend_contract…test_intro_movie_provider…`

   Consider adding `tools.test_dependency_cache` to the focused lists in
   `build.sh` and `build_fast_candidate.sh` during integration. It was left
   out here to avoid conflicts.
2. **Default is unchanged:** build a candidate with no `RENEGADE_DEPENDENCY_CACHE*`
   variables. The log must contain no `Dependency cache:` lines, and the
   ELF/VPK hashes must match a build of the same tree without this branch.
3. **Prime the cache:** in a fresh integration worktree, set
   `RENEGADE_DEPENDENCY_CACHE_DIR=/home/steve/projects/RenegadeVitaBuilder/dependency-cache`
   (and preferably
   `RENEGADE_SOURCE_CACHE=/home/steve/projects/RenegadeVitaBuilder/source-cache`),
   then build without copying `build/deps`. All three dependencies build and
   log `Dependency cache: stored …`.
4. **Hit:** in a second fresh worktree, use the same variables. Expect
   `verified hit` for vitagl-demo, ffmpeg-bink-vita and ttfs-https-vita, and
   the dependency phase should take seconds.
   - In the **same** tree, remove `build/deps/vitagl-demo/build.identity` and
     rebuild. `eboot.bin` and the VPK must hash identically to the previous
     build. This is the decisive identity check.
   - Across trees, compare `eboot.bin` too, after accounting for each tree's
     own path-bearing objects.
5. **Rejection:** flip a byte in an entry's `payload/libvitaGL.a`. The next
   lookup must log `rejected`, rebuild, and log `replaced`. Run
   `python3 tools/dependency_cache.py verify --cache-dir <dir>` and expect all
   entries `ok`.
6. Clean up with `rm -rf <dir>/<name>/<key>`. There is no automatic eviction.
   One full set is about 26 MB (vitaGL 6.3 MB + its archive 9.6 MB + FFmpeg 5.0 MB + HTTPS 5.4 MB).

## 5. Files and conflict risk

- New files:
  - `tools/dependency_cache.py`
  - `tools/dependency_cache.sh`
  - `tools/test_dependency_cache.py`
  - this report
- Edited:
  - the three dependency scripts (delimited blocks)
  - one paragraph in `docs/BUILDING.md`
- **Conflict risk:**
  - **Low** with TUT-R1-17 and TUT-R1-18: `build.sh`, `build_fast_candidate.sh`
    and `stage_sources.sh` are untouched.
  - **Medium** for any branch that adds a vitaGL patch. It must also add
    `--patch "$new_patch"` to the key block. `test_dependency_cache` fails if
    the keyed order differs from the applied order.
