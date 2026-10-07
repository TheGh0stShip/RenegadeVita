# FPS round 4 — SHADER_PRECOMPILE (vitaGL FFP program cache / pre-warm)

Nothing here is measured on hardware. Every gain below is an estimate.

## Hypothesis
Each vitaGL fixed-function (FFP) shader variant is first used inside a gameplay
frame. If its GXP is not on disk, libshacccg compiles it. If it is on disk, the
GXP is still read through sceIoOpen/lseek/read on ux0. Loading every previously
seen variant on a loading screen moves both costs out of gameplay. Per-draw
program selection is already cheap, so it is instrumented rather than changed.

## Evidence (pinned vitaGL 6e7fe40 + the six existing Renegade patches)
- Keys: `reload_ffp_shaders` (ffp.c:447) builds a 32-bit `shader_mask`
  (ffp.c:203-224) and a 64-bit `combiner_mask`. The vertex key is
  `mask & VERTEX_SHADER_MASK`. The fragment key is `mask & FRAGMENT_SHADER_MASK`
  plus the combiner.
- Per-draw lookup: there is already a last-key memo (ffp.c:608). Only a key
  change triggers a linear scan of the RAM caches (ffp.c:614-645), at most 256
  entries each, comparing a u32 (and a u64 for fragments). That cost is small
  next to the measured 24-29 ms mesh-boundary CPU, so it is unchanged. Its rate
  is now logged.
- Re-patching: a key or blend change calls
  `sceGxmShaderPatcherCreateFragmentProgram` again (ffp.c:1016-1020,
  shared.h:480). A vertex-layout change calls `...CreateVertexProgram`
  (ffp.c:863). vitaGL has no patched-program cache of its own; it relies on the
  GXM patcher's internal dedup and never releases. The counts are now logged.
- Compiles: on a RAM miss vitaGL reads `.../{v,f}/<key>.gxp`. If that file is
  missing, it calls `shark_compile_shader_extended` (ffp.c:668-697 and 887-981)
  and writes the GXP. libshacccg is loaded once (gxm.c:303-316) and never
  released. There are no precompiled FFP GXPs.
- Cache path defect: `HAVE_SHADER_CACHE` is on, but the FFP path is hard-coded
  to `ux0:data/shader_cache/v28` (vgl.c:175-185, ffp.c:664/879). The port's
  `vglSetShaderCachePath("ux0:data/renegade/cache/vitagl-shader-cache")`
  (ww3d_vita_renderer.cpp:2941) moves only the custom-GLSL cache. So FFP GXPs
  were written outside the Renegade tree, into a directory shared with all
  vitaGL homebrew. That directory is keyed only by magic 28, which was not
  bumped when vitagl-projective-immediate.patch changed ffp_v.h/ffp_f.h.
- Only M00 has a hidden-scene pre-warm. Campaign levels compile or disk-load on
  first use during play.
- Latent upstream bug: the RAM-cache counts are `uint8_t` (ffp.c:270-271) but
  the capacity is 256. On the 256th variant the count wraps to 0: no eviction,
  the cache leaks, and the scan sees nothing.

## Change made
1. New `port/renderer/vita/dependency-patches/vitagl-ffp-program-cache.patch`
   (ffp.c, vgl.c). It is applied last by tools/build_vitagl_demo.sh, which now
   also re-extracts vgl.c from the archive, adds the patch to the build identity
   and provenance, and passes `-DRENEGADE_VGL_FFP_CACHE_DIGEST`. That digest is
   12 hex characters of sha256 over the patched ffp.c, ffp_v.h, ffp_f.h and
   texture_combiners/*.h.
   - (a) If the app sets a cache root before vglInit, the FFP cache moves to
     `<root>/ffp-6e7fe40-m28-w0-p<digest>/{v,f}`, created at runtime. Without a
     root, the path stays as upstream.
   - The first-use read now validates the file: size between 1 byte and
     256 KiB, a full read, `sceGxmProgramCheck`, and a header size no larger
     than the file. An invalid file is recompiled and rewritten, where before a
     truncated GXP was registered.
   - The RAM-cache counts are now `uint16_t`. Behaviour is identical below 256
     variants; at 256 the intended eviction now works.
   - (d) `vglRenegadeGetFfpStats` exports counters: compiles, compile µs
     (sum and max), disk loads and µs, rejects, key changes, vertex/fragment
     re-patches, pre-warm counts and bytes, and resident sizes.
   - (c) `vglRenegadeGetFfpKeys` exports the resident keys.
     `vglRenegadePrewarmFfpPrograms` loads, registers and inserts each listed
     key that is not resident, using the same file and steps as first use. It
     never compiles, never wraps or evicts the ring, and restores the active
     program globals.
2. Port side (default on):
   - `ww3d_vita_ffp_program_keys.h` holds the pure logic: a tagged, versioned
     text record bounded at 128 vertex and 192 fragment keys, plus merge,
     serialize and a strict whole-file parser.
   - `ww3d_vita_ffp_program_warm.{h,cpp}` is the Vita glue:
     - `Prewarm_From_Record` runs right after vglInit (boot loading).
     - `Record_Resident_Keys` runs at the start of
       Prepare_Original_Level_Loading_Resources and at renderer Shutdown. It
       writes `<ffp dir>/program-keys.txt` through a .tmp file and a rename, and
       only when the record grew.
     - `Sample_Window` runs every 120 presented frames (End_Frame).
   - Breadcrumbs under `ffp-program-cache`: `prewarm:`, `record:` and
     `window:`. A `window:` line appears whenever a window had a compile or disk
     load, and on every 10th window; at most 600 lines.
   - Off switch: `ux0:data/renegade/user/config/ffp-prewarm-v1.flag`
     containing `RVFP1 0\n` disables pre-warm. Recording and telemetry stay on.
   - CMakeLists.txt adds the new TU.
- Path note: the brief said `user/cache/`. AGENTS.md defines the cache root as
  `ux0:data/renegade/cache/` (a sibling of `user/`), and the port already uses
  `.../cache/vitagl-shader-cache` (vita_platform.cpp:231 creates it). This
  change follows that. Switching to `user/cache` is a one-line edit of
  `shader_cache_path` in Initialize.

## Risk and invalidation argument
- Program selection is unchanged: the RAM cache is still keyed by the exact
  masks and combiner, and the memo and scan are untouched. A pre-warmed entry for
  key K holds the bytes of `<dir>/{v,f}/K.gxp`, the same file and the same
  loader that first use would hit. Within a process that file is written only
  when K is absent from both RAM and disk, so it cannot change between pre-warm
  and first use. Uniform and attribute indices come from the same program
  through the same functions. Only the ring order differs, and that matters
  only for eviction after 256 variants (performance only).
- Invalidation: the directory tag covers the revision, FFP magic, WVP mode, and
  the digest of every FFP shader-text source. The record carries the same tag
  and is ignored on any mismatch. As upstream, compiler options are not part of
  the key, and the port never changes them.
- One-time cost: the first launch after this change starts from an empty
  versioned directory. Each variant compiles once, as on a fresh install. The
  old unversioned, shared `ux0:data/shader_cache/v28` is deliberately not
  reused. Measure on the second launch.
- Memory: every recorded GXP and its uniform buffer come from the vitaGL RAM
  pool at boot: at most 320 programs, typically about 2-6 KiB each. The actual
  figure is the `bytes=` field of `prewarm:`.
- Per-draw overhead: one counter increment per key change and per re-patch.

## Tests run
- `RENEGADE_VITAGL_TARBALL=<main>/build/deps/vitagl-demo/source.tar.gz python3 -m unittest tools.test_vita_ffp_program_cache -v`
  passes 6/6:
  - zero-fuzz application after the six existing patches; every active FFP
    path redirected; validating loader; vglInit mkdirs and tag;
  - a mock GXM/IO harness under ASan/UBSan (tools/vitagl_ffp_prewarm_test.c)
    over the extracted patched code: exact bytes inserted, padded GXP accepted,
    truncated and bad-magic GXPs rejected, resident and out-of-mask keys
    skipped, a registration failure frees, no ring wrap, globals restored, key
    order, stats and bytes (this harness found the uint8_t bug);
  - stat-enum parity between the patch and the port header; build-script
    order, identity, re-extract and digest; renderer and runtime wiring;
  - an ASan/UBSan harness (tools/vita_ffp_program_keys_test.cpp) for the
    record: round trip, dedupe, bounds, and rejection of a stale tag, wrong
    version, truncation, trailer mismatch, duplicates, bad hex, CRLF and trailing
    data.
- Related tests, using a temporary symlink to the main tree's tarball (since
  removed): test_vitagl_full_upload, test_vita_projective_coordinates,
  test_vita_static_mesh_cache and test_vitagl_compact_vertices PASS.
  test_vitagl_dds_chain ERRORS with `Probed_Upload_DXT_Chain` undeclared; that
  is pre-existing, as none of its inputs are touched here.
- VitaSDK compile of the patched ffp.c and vgl.c with the exact build flags:
  OK. The only extra output is `-Wall`-only format-truncation notes, and the
  real build does not use `-Wall`.
- ARM TUs (arm_tu_check.sh): ww3d_vita_ffp_program_warm.cpp OK with
  `-Wall -Wextra -Werror=format`, no warnings. a31_vita_runtime.cpp OK.
  ww3d_vita_renderer.cpp OK.

## Expected gain (unmeasured estimate)
From the second launch on, recorded variants cost 0 ms at first use in
gameplay. Today each costs an ux0 disk load (about 1-5 ms) or, if its GXP is
missing, a compile (about 20-200 ms). That cost moves to boot. This removes
hitches; average FPS is not expected to change.

## Hardware measurement (second launch after install)
1. `ffp-program-cache prewarm:` should show `record=valid`, `loaded` close to
   `keys`, `rejects=0`, plus `bytes` and `elapsed_us` (the boot cost).
2. During campaign play, `window:` lines should show `compiles=0/0` and
   `disk_loads=0/0` except for variants new to this run. Compare frame-vblank
   `max_delta` with a run that has `ffp-prewarm-v1.flag` set to `RVFP1 0`.
3. Steady-state `window:` lines give `mask_changes` and `repatches` per 120
   frames. If re-patches reach the hundreds per frame, do (b) next: a vitaGL
   patched-fragment memo keyed by (program id, vertex program, blend), flushed
   on ring eviction.
4. On the first launch, `total_compiles` and `max_compile_ms` give the real
   libshacccg cost.
