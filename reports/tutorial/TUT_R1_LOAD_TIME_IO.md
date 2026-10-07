# TUT-R1-10 LOAD_TIME_IO: tutorial load-path file I/O (RVIO1)

Agent TUT-R1-10, Tutorial Round 1. Branch `tut-r1-10-load-io`, created from
`tutorial-r1/base` (45c6cf5). The requested `git merge --ff-only` failed
because this worktree was created from a newer `main` (cde0b86). The branch
therefore starts at 45c6cf5 itself.

**Nothing in this change has been compiled, built, packaged or run.** Every
gain below is a hypothesis until a Vita A/B run measures it.

## Scope

This covers the load from Single Player → Tutorial (Start_Game
`M00_Tutorial.mix`) to the first gameplay frame. It includes the file I/O on
ux0, the MIX/factory route, the read layering, and the synchronous loading
presenter.

## Findings (file:line, worktree state)

### 1. Factory route: the tutorial never re-opens or re-indexes a MIX

- `port/platform/vita/a31_vita_runtime.cpp:5096-5141` builds the MIX factories
  once at startup and adds them to `FileFactoryListClass` in this order: root
  (loose retail), `Data` (loose), `Always2.dat`, `always.dbs`, `Always.dat`,
  `M00_Tutorial.mix`.
- `:5641` builds a per-load mission factory only for archives other than the
  tutorial. The tutorial already has its index (84 entries) from startup, so
  the "avoid re-index" option cannot help this route. For M01 and later, each
  load reads one index, which is small next to the preload.
- `staging/combat/ffactorylist.cpp:136-189`: for each asset name the two loose
  factories are tried first. The existing `confirmed_missing` cache already
  answers those misses without native I/O
  (`port/filesystem/renegade_file_factory.cpp` Open and Is_Available). After
  that, each MIX is binary-searched.

### 2. Every MIX member costs two native opens

- `staging/wwlib/mixfile.cpp:269-271`: `MixFileFactoryClass::Get_File` calls
  `Factory->Get_File(MixFilename)` and then `file->Bias(offset, size)`.
- `staging/wwlib/rawfile.cpp:1105-1120`: `RawFileClass::Bias` calls
  `RawFileClass::Size()`.
- `rawfile.cpp:844-902`: on a closed file, `Size()` opens the archive, runs
  `ftell/fseek END/ftell/fseek`, and closes it again.
- The loader then opens the same archive a second time for the real read.
- The availability check in between is already cached, so it adds no native
  I/O.
- Device telemetry agrees. At the first gameplay timing window, the A3.6
  resource counters showed 1,924 opens for about 950 asset fetches.

### 3. VitaSDK newlib splits every read into 1 KiB `sceIoRead` calls

These facts come from disassembling `/usr/local/vitasdk/arm-vita-eabi/lib/libc.a`
with `llvm-objdump`. No compiler was involved.

- **Buffer size.** `__smakebuf_r` sets the buffer to `mov.w r1,#0x400` (1024
  bytes) and adds flag `#0x800` (`__SNPT`) after a successful `fstat`.
  HAVE_BLKSIZE is unset, and `scestat_to_stat` zeroes 0x28 bytes without
  setting `st_blksize`.
- **fread.** `_fread_r` goes straight to the destination only for unbuffered
  streams (`lsls r3,#0x1e; bpl` tests `__SNBF`). On a buffered stream it calls
  `__srefill_r` once per 1 KiB block. So one 16 KiB `BufferedFileClass` refill
  becomes 16 `sceIoRead` calls, and a 300 KiB mesh chunk becomes about 300.
- **fseek.** `_fseeko_r` calls `_fflush_r` first for `SEEK_CUR`. Flags mask
  `0x81a` (`__SNPT|__SNBF|...`) forces a plain lseek. The optimised path sets
  `_blksize = 0x400` and refills 1 KiB.
- **fflush.** `__sflush_r` on a read stream sets `__SNPT`. If it still holds
  unread bytes it seeks back and drops them, so they are read again later.
- **lseek.** `_lseek_r` maps to `sceIoLseek32`.
- **Why this matters.** `RawFileClass::Read` (`rawfile.cpp:616-680`) calls
  `Seek(0)` (an `fseek`) before every biased read. As a result the 1 KiB stdio
  buffer saves no reads at all and only adds re-reads.
  `BufferedFileClass` (`staging/wwlib/bufffile.cpp:42,109-168`) already
  buffers small reads at 16 KiB.

### 4. Chunk read pattern

- `staging/wwlib/chunkio.cpp:454-473`: each top-level `Open_Chunk` calls
  `Tell` and `Size` and reads an 8-byte header.
- `:788-813`: a skip runs `Tell` + `Seek(n, SEEK_CUR)`.
- `BufferedFileClass::Seek` (`bufffile.cpp:220-248`) always calls through to
  `RawFileClass::Seek`, so every Tell costs one lseek. `SEEK_SET` and negative
  relative seeks free the 16 KiB buffer.

### 5. Loading presenter

- `a31_vita_runtime.cpp:1617-1662`: each call renders the full original
  `LoadingScreenClass` (`WW3D::Begin/End_Render`, i.e. a present). VSync is on
  by default (`port/renderer/vita/ww3d_vita_renderer.cpp:3890`).
- On a progress change it adds `kLoadingProgressCatchupFrames = 3`
  (`:380`) extra frames, each preceded by `sceDisplayWaitVblankStart`.
- Sub-status callbacks fire from `INIT_SUB_STATUS` once per dependency W3D
  (`staging/combat/assetdep.cpp:293`). They are rate-limited to 50 ms
  (`a31_vita_runtime.cpp:5023`, previously a constant).

### 6. The existing load timer does not measure the level load

`staging/combat/combat.cpp:492-500` runs `LoadThreadClass` synchronously on
Vita. The existing `threaded load complete elapsed_ms` (about 53 ms on
device) only measures the polling loop after the load has already finished.

### Device time split

Sources: aggregate figures from the private dev229/dev230 tutorial logs.
Contents are not reproduced, and log lines carry no timestamps.

| Phase | Evidence | Value |
| --- | --- | --- |
| M00 dependency preload (`Load_Level_Assets`) | logged elapsed | **≈9.3 s** |
| Presenter renders during preload | phase lines | 123, no catch-up |
| Synchronous LDD/level load | not timed before this change | 32 renders, 6 with 3 catch-up frames |
| Post-load + m00-scene prewarm | logged | 60 frames ≈ 2.7 s, 104 presenter lines |
| First gameplay frame | logged slow frame | ≈1.0 s |
| Cumulative reads at first timing window | A3.6 resources | 48.3 MB in 2.32 M logical reads, 1,924 opens |
| M01 preload, for scale | logged | ≈37.8 s |

## Model evidence (pure Python, no compiler)

`tools/model_vita_load_io.py` reproduces the newlib paths above,
`RawFileClass` (bias and `Bias` via `Size`), the staged `BufferedFileClass`,
and the ChunkLoad/DDS read sequences. It runs them against the real retail
tutorial dependency list (`m00_tutorial.dep`: 280 names, 226 distinct, 219
resolved, 12.3 MB) plus the 44 tutorial lightmap DDS members (1.9 MB).

| Model, 263 members | sceIoRead | bytes read | sceIoLseek | fstat | opens |
| --- | --- | --- | --- | --- | --- |
| Original (buffered stdio, Bias probe) | 15,293 | 15.66 MB | 12,795 | 1,008 | 526 |
| RVIO1 bit 0 | 963 | 13.97 MB | 11,265 | 0 | 526 |
| RVIO1 bit 1 (opens only) | — | — | — | — | 266 |

- The read and Tell traces are byte-identical between the two stdio modes for
  every member.
- Original mode reads 12 % more bytes than direct mode because flushes drop
  buffered bytes that are read again later.
- Leaf skips use a synthetic one-in-seven policy, which inflates lseek
  counts. With no skips the counts are 6,295 → 5,410 lseeks and 15,353 → 1,011
  reads.

## Change (flag `ux0:data/renegade/user/config/load-io-v1.flag`, `RVIO1 <0-7>\n`, default **0 = all off**)

| Bit | Behaviour | Where |
| --- | --- | --- |
| 1 | Direct reads: a read-only retail stream opened by `RenegadeRootedFileClass` gets `setvbuf(_IONBF)` before its first stdio operation. This happens after `fopen`, or inside the `Seek` that `RawFileClass::Open` issues for biased files. Writable namespaces, write/RW opens and forced probes are unchanged. | `port/filesystem/renegade_file_factory.cpp` `Open` / `Seek` / `Apply_Direct_Reads` |
| 2 | Archive size reuse: a `Bias` override applies `RawFileClass::Bias`'s exact arithmetic (`BiasStart = start; BiasLength = max(min(S, length), 0)`) without the extra open. It only applies when the archive object is fresh, closed, immutable retail, and its whole-file size S was recorded by an earlier original probe (via `Size()`). All other cases call the original `Bias`. | same file, `Bias` / `Size` |
| 4 | Presenter cadence: sub-status repaints are spaced 250 ms instead of 50 ms. Milestone repaints (`minimum_progress >= 0`) and catch-up frames are unchanged. | `a31_vita_runtime.cpp:5023` via `renegade_load_io.h` |

New telemetry is always on, and these lines are log-only:

- `A3.6 load-io: version=1 mask=…` at startup.
- `A3.6 load-io: level load sync_ms=… since_begin_ms=…`, the real synchronous
  loader time.
- `A3.6 load-io: level load begin_to_first_frame_ms=…`.
- `A3.6 load-io: frame=… direct_read_streams=… archive_size reuse/probe=…`
  next to the existing A3.6 resources lines.

### Why default off

Bytes, positions, short-read/EOF results and `BiasStart`/`BiasLength` are
identical by construction, and identical in the model. Bit 0 changes only the
syscall split, and every large-read destination inspected is ordinary heap
(`ddsfile.cpp:215 new unsigned char[size]`).

This is still the first hardware exposure of a change that touches every
retail read, so it stays opt-in for the A/B. If the A/B is clean, consider
`RENEGADE_LOAD_IO_DEFAULT = 3U`. A malformed flag file already falls back to
the default, and `RVIO1 0` would still force everything off. Bit 4 is visual
only (the backdrop bar lerps per rendered frame) and should stay a choice.

## Hypothesis-ledger entry (proposed; shared ledger not edited)

- **Hypothesis.** Tutorial load time is inflated by about 15× more
  `sceIoRead` calls than needed (newlib's 1 KiB buffer), by a second
  open/close per MIX member, and by presenter frames every 50 ms during the
  9.3 s preload.
- **Risk.**
  - Bit 0: low. Byte-identical; `_fwalk(lflush)` before each unbuffered read
    is a lock-free scan.
  - Bit 1: low. Retail is already treated as immutable, as in the existing
    availability cache.
  - Bit 4: visual only. The progress bar animates in fewer steps.
- **Estimated gain, unmeasured.**
  - Bit 0 removes about 14 of every 15 data `sceIoRead` calls: roughly 50 k
    fewer calls for 48 MB through the first gameplay window. That is about
    1–4 s at an *assumed* 25–80 µs fixed cost per call.
  - Bit 1 removes about 950 open/close pairs: about 0.2–1 s.
  - Bit 4 saves about 0.5–2 s of the preload, depending on per-frame render
    cost, which is unknown (VSync on).
- **Measure on the tutorial route.** Cold launch → Single Player → Tutorial,
  same card, three runs per setting. Read these from the runtime log:
  - `campaign preload … elapsed_ms`
  - `A3.6 load-io: level load sync_ms`
  - `prewarm: m00-scene complete … elapsed_ms`
  - `A3.6 load-io: level load begin_to_first_frame_ms`
  - `startup-precache … elapsed_ms`
  - the A3.6 resources/load-io lines

## Verified vs unverified

- **Verified (host, pure Python):**
  - `python3 -m unittest tools.test_vita_load_io` passes 11 tests: flag
    parser vs header, source gates, byte identity (synthetic and retail
    tutorial), random seek/read/tell positions, Bias arithmetic and open
    halving, and presenter cadence keeping every milestone.
  - Text-only regressions still pass: `tools.test_campaign_autosave_chain`,
    `tools.test_runtime_log_contract` and
    `tools.test_vita_loading_screen_contract`.
  - The newlib behaviour comes from the disassembly of the installed libc.a.
- **Unverified:**
  - The code has not been compiled. `tools/file_factory_stub/bufffile.h`
    gained `Bias`/`BiasStart`/`BiasLength`/`Get_File_Handle` so the
    compiler-based host tests (`test_renegade_file_factory_*`) should still
    build, but they were not run.
  - All timings and gains, the device per-call costs, and the visual effect of
    bit 4.

## Hardware A/B

1. Use the same build and no flag file (baseline, mask 0). Cold boot → SP →
   Tutorial → first control, three times. Keep the logs.
2. Run `RVIO1 1`, `RVIO1 3`, `RVIO1 7` the same way. Write the flag as exactly
   8 bytes, `RVIO1 3` plus a newline.
3. Compare preload, sync, prewarm and first-frame times, plus the startup
   precache. Expect `direct_read_streams` > 0 for masks 1/3/7. Expect
   `archive_size reuse` ≈ the number of member fetches and `probe` ≈ the
   number of archives (≤ 6) for masks 3/7.
4. Check the tutorial plays identically: Logan intro, Gunner range, HMVV.
   With bit 4, confirm the loading text and bar still advance.

## Follow-ups (not done)

- **Tell cache.** A logical-position cache in `RenegadeRootedFileClass` would
  remove the remaining ~5–11 k lseeks for the dependency set alone (one per
  Tell/refill).
- **Read counters.** `RenegadeRootedFileClass::Read` makes two atomic RMWs per
  logical read: 2.32 M reads ≈ 0.1–0.3 s on Cortex-A9 (estimate).
- **Read-ahead size.** A `BufferedFileClass` read-ahead of 64 KiB through the
  protected `Set_Desired_Buffer_Size` needs SEEK_SET-reset measurements first.
- **M01 preload.** M01 (37.8 s preload) should benefit more; re-measure there.
