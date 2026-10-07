# FPS round 4: derived-data cache (DERIVED_DATA_CACHE)

Status: report only. No runtime code changed. Nothing here was measured on
hardware. Cycle and I/O figures are estimates from ARM codegen, retail MIX
metadata and dev238 log counts.

## Hypothesis

Some deterministic derived data could be computed once and reused from the
user-owned cache (`ux0:data/renegade/cache/`, created at
`port/platform/vita/main.cpp:127`) without changing the bytes the engine sees.
That cache would use source identity, a format version, atomic writes, an LRU
budget, recompute on mismatch and an `RVDC1 0` kill switch.

**Verdict: no candidate justifies a cache, so nothing was implemented.** For
the two largest candidates the cached bytes are as large as the source (DXT
swizzle) or twice as large (TGA16 to RGBA8888). On the memory card, reading the
cached product costs about as much as recomputing it. An exact, cache-free
rewrite of each hot loop saves more, with no I/O, no card space and no
invalidation risk. Both rewrites are listed below as follow-ups outside this
slug.

## Evidence

- dev238 physical logs (main tree, read-only, `build/device-evidence/A3.5-dev238-20261004/`):
  startup pre-cache `elapsed_ms=2882` incl. 1000 ms visible minimum, 4 archives,
  15,429 names, 594 KB touched (startup.log:62); M13 dependency preload (original
  W3D loader) `elapsed_ms=10488` (startup.log:561); M13 texture prepare
  `prepared=199`, resident +8.16 MB, all native DXT (observation-3.log:1034; every
  logged load `source=dds compressed=1`, no TGA in M13); first frame 2.53 s
  (observation-3.log:1057); first-use preset creates 0.22-0.59 s (prototype loads,
  already targeted by the cinematic warm-up).
- Retail MIX metadata (read-only, counts only, `local-builder/retail-host/Data`):
  always.dat 15,161 entries, 182 KB index, 377 KB names table, 1,563 DXT files;
  M08.mix 209 .tga + 16 .dds; M09.mix 130 .tga; M13.mix 48 .dds, 0 .tga. Matches
  `reports/campaign/MISSION_MEMORY_ESTIMATES.md` (256x256 A1R5G5B5, 128 KiB each).
- ARM codegen: `arm-vita-eabi-g++` 15.2 -O2/-O3 on a verbatim scratch copy of the
  conversion loop and the vitaGL swizzle (not committed).

## Ranking (estimates, Cortex-A9 @ 444 MHz)

| # | Candidate | Where | Work per load (est.) | Derived/source bytes | Verdict |
|---|---|---|---|---|---|
| 1 | TGA16 to RGBA8888 + FNV checksum | `ww3d_dx8_boundary.cpp:1152-1185`, via `Load_Targa_Texture` :1713 | M08 13.7 Mpx: 0.77-1.23 s. M09 8.5 Mpx: 0.48-0.77 s. M13: about 0. | 2x | Reject (A) |
| 2 | DXT Morton swizzle in `vglRenegadeUploadDXTChain` | `dependency-patches/vitagl-dds-chain.patch` | M13, about 0.7-0.9 M blocks: 0.23-0.51 s | 1x | Reject (B) |
| 3 | always.dat name list at startup | `a31_vita_runtime.cpp:962` calling `Build_Filename_List` | 15,161 names, 30 k reads, about 128 k string alloc/copy: 0.1-0.2 s | 1x | Reject (C) |
| 4 | MIX index parse | `staging/wwlib/mixfile.cpp:68-160` | one 182 KB read plus `is_sorted`: under 10 ms | 1x | Too cheap |
| 5 | `mpg123_scan` on MP3 open | `renegade_wave_decoder.cpp:806` | in-memory header walk, tens of ms per track | tiny | No exact way to inject the result |
| 6 | FreeType glyph raster | `renegade_freetype_font_provider.cpp:195-205` | lazy, unmeasured | small | No evidence; per-session cache exists |
| 7 | W3D / TDB / CDB / pathfind | original loaders | M13 10.5 s | n/a | Forbidden: it would replace original loaders |
| 8 | Shader compile, dir listing | vitaGL shader cache, `renegade_paths` | n/a | n/a | Already cached |

### (A) TGA16 conversion

- At -O3, GCC inlines and unswitches the loop to about 25-35 instructions per
  pixel (3 `umull`, 4 `strb`, one FNV `mul`). That is about 25-40 cycles per
  pixel.
- A cache would read 256 KiB instead of 128 KiB per TGA:
  - M08 reads 26 MiB more, which takes 0.65-1.3 s at an assumed 20-40 MB/s.
  - The first visit also writes 53 MiB for M08 and 33 MiB for M09.
  - Net effect is between -0.5 s and +0.6 s, depending on the card.
- **Exact follow-up:** a dedicated A1R5G5B5 loop using a 32-entry
  `floor(v*255/31)` table. It produces identical bytes and checksum at about
  10-14 cycles per pixel. Estimated saving: 0.5-0.9 s on M08 and 0.3-0.5 s on
  M09, with zero I/O.

### (B) DXT swizzle

- Each block costs about 150-250 cycles:
  - a `log2(tile)` bit loop (6 x 14 instructions for 256 px);
  - an `__aeabi_uidiv` call (the A9 has no hardware divide);
  - an out-of-line `memcpy`.
- A pre-swizzled cache would remove only this CPU time. It would need a new
  vitaGL entry point, the same I/O, and card space equal to the DXT bytes
  (59 MB for always.dat alone).
- **Exact follow-up:** shift by the power-of-two tile, use a bit-spread
  Morton, and copy fixed 8/16-byte words. That is about 15-25 cycles per block,
  saving an estimated 0.2-0.45 s per M13 load.

### (C) Filename list

- The list only feeds the pre-cache pass gate (`archives_valid`, line 972) and
  counters (lines 1155 and 1315).
- A cache would still construct every string.
- **Exact follow-up:** keep the gate but presize the list
  (`Set_Growth_Step(1000)` causes about 15 regrowth copies), or count names
  without building strings. This affects startup only, not FPS.

## Change made

None to runtime code, patches, staging, tests or the inventory. The only commit
is this report.

## Risk and invalidation argument

There is no change, so there is no risk. If a cache is reconsidered (for
example, for a future CPU mip-chain generation added for DX8 fidelity, where
compute is heavy relative to bytes), use:
- Key: archive logical name, size and mtime, the member's CRC, offset and
  size, FNV-1a of the member bytes, and the `RVDC1` and converter versions.
- Store `PixelChecksum` and recompute on any mismatch.
- Write `.pending`, then rename.
- Keep an LRU budget.
- Never write retail data.

## Tests run

- `python3 <scratchpad>/ddc/mix_metrics.py local-builder/retail-host/Data always.dat
  Always2.dat M13.mix M08.mix M09.mix M01.mix` (read-only; numbers above): PASS.
- `arm-vita-eabi-g++ -O2|-O3 -fno-exceptions -fno-rtti -fno-strict-aliasing -S` on
  the harness (instruction counts above). No ARM TU check or host test: no TU changed.

## Expected gain

Zero from this slug. Unmeasured follow-up estimates: TGA table loop M08 -0.5 to
-0.9 s, M09 -0.3 to -0.5 s; swizzle rewrite -0.2 to -0.45 s per DXT-heavy load.
No steady-state FPS effect; both shorten first-use hitches for textures not
prepared during loading. No switch added (`derived-cache-v1.flag` unused).

## Hardware measurement to take

Accumulate `sceKernelGetProcessTimeWide` deltas, logged once per level on the
`referenced textures: prepared=` line: `tga_read_us` (Targa Open+Load),
`tga_convert_us` (RGBA + checksum), `tga_upload_us` (glTexImage2D),
`dxt_upload_us` (`Probed_Upload_DXT_Chain`), prepare `elapsed_us`; also time
`Startup_Index_Mix_Archive` for always.dat. Run cold boot, then M13, then M08/M09.
Adopt the TGA table loop if `tga_convert_us` >= 0.3 s on M08; adopt the swizzle
rewrite if `dxt_upload_us` >= 0.15 s on M13; revisit a disk cache only if the card
reads 2x the bytes faster than the CPU converts them.
