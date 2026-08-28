# Vita open-source reference insights

Updated: 2026-08-25. Source material was fetched only into
`/tmp/renegade-vita-reference-cache`; no external implementation was imported
into the port.

## Confirmed useful patterns

- Vita3K CLI: `vita3k/config/src/config.cpp` at
  `496939b602703951277263c7b3e60a9ae36879c1` confirms positional
  `content-path` VPK/folder run, `--console`, `--app-args`,
  `--installed-path`, `--recompile-shader`, `--archive-log`, and `--log-level`.
  `tools/run_vita3k_candidate.py` now wraps only the VPK/console path and
  labels the result as emulator-only.
- vitaGL: `README.md`, `source/vgl.c`, `source/shared.h`,
  `source/textures.c`, `source/framebuffers.c`, `source/draw.c`, and
  `source/shaders.h` at `6440cf0e0c6573d7b3de6521462d8cbecd8fb4c1` confirm
  practical diagnostic flags for the current visual blockers:
  `LOG_ERRORS`, `HAVE_PROFILING`, `DEBUG_GLSL_TRANSLATOR`, `SAFE_DRAW`,
  `SAFE_UNIFORMS`, `HAVE_TEXTURE_CACHE`, `HAVE_UNFLIPPED_FBOS`,
  `HAVE_SHADER_CACHE`, and `NO_TILE_CLIPPER`. `TEXTURES_SPEEDHACK` conflicts
  with `HAVE_TEXTURE_CACHE`, so do not combine them in one A/B build.
- Sokol audio: `sokol_audio.h` at
  `7cee0ba17c358985e4744fe8ac20b6829d328229` still documents and implements
  a Vita backend selected by `PSP2_SDK_VERSION` and linked to `SceAudio`. It is
  suitable as an independent SceAudio smoke oracle if dev48 still has silent
  dialogue despite nonzero WWAudio/provider counters.
- vita-crashdump: `README.md` and `src/lib.rs` at
  `86ef3ee05a02d08bb2daf039ee4161264b14ff67` confirm desirable parser
  features for retained dumps: gzip/raw PSP2DMP handling, module/segment
  address resolution, THREAD_INFO/THREAD_REG_INFO/STACK_INFO use, DFAR/IFAR
  fault address reporting, persistent addr2line, objdump context, and
  `.ARM.exidx`/`.ARM.extab` unwind before heuristic stack scan. Its license is
  not asserted, so this is requirements input only.
- libvcp: `lib/include`, `lib/src`, and `cli/jsondump` at
  `950c98f55c995d56bed9ab6c0485a9be68cc0f4f` are MIT and can be compared when
  extending `tools/parse_psp2_core.py`, but matching candidate artifacts remain
  mandatory.

## Study-only findings

- Vita3K, DaedalusX64-vitaGL, and SRB2Kart Vita are GPL-2.0-only in GitHub
  metadata. Use them only for behavior, CLI, or diagnostic ideas.
- vita-crashdump, vita-parse-core, Alisa-Vita, and psp2spvc have no asserted
  license from GitHub metadata. Treat them as study-only until license status
  is resolved.
- Vita Recorder is GPL-3.0 and useful only as a diagnostic capture reference.
  It is not a release-path dependency.

## Next implementation targets

1. Renderer/loading: create candidate-specific A/B builds around vitaGL
   diagnostics only when tied to a fixed loading capture or replay. Start with
   `LOG_ERRORS`/`HAVE_PROFILING`, then isolate `SAFE_DRAW`, `SAFE_UNIFORMS`,
   shader cache, texture cache, and FBO orientation separately.
2. Crash tooling: when a new PSP2DMP arrives, compare the in-tree parser
   output against the fetched libvcp/vita-crashdump behavior, then implement
   any missing parser fields independently or from MIT-compatible libvcp
   patterns with a ledger entry.
3. Audio: do not import Sokol into WWAudio. Use a minimal SceAudio smoke test
   only if physical dev48 logs prove stream creation/start and category volume
   but dialogue remains inaudible.
4. Build overhead: retain the existing ccache and fast-candidate flow. Use
   VitaSDK/Vita3K build references for diagnostics, not a broad unity/LTO or
   fast-math rewrite.
