# Dev100 prior-work audit

Date: 2026-09-08. Source authority: active bash checkout, resumed at
`f28578a`. Review scope: Dev87 physical failures, Dev88-Dev99 attempted
repairs, and the subsequent unbuilt performance preparation. Model attribution
is not part of the retained evidence; this audit assesses source and results.

The user requires substantial local progress before physical testing and a
60 FPS or better target. No device access is authorized by this work unit.
Fast and canonical ARM builds run in the background while independent audit,
tests, and reporting continue. Physical acceptance remains open.

## Findings and disposition

| Area | Prior work and remaining cause | Dev100 disposition | Evidence boundary |
| --- | --- | --- | --- |
| EA_WW.BIK and R_INTRO.BIK audio/video | Uploads dominated the measured Dev86 movie cost. Dev87-Dev98 reduced upload size and increased audio reserve, but a future pending video frame still stopped demuxing the following audio packets. Audio pressure could also discard a video frame before its PTS. | Bounded compressed-video read-ahead lets audio fill its reserve while video waits. Original video packet order and frontend-thread decoding are preserved. Future frames are not dropped merely for low audio. Audio output waits for decoder drain, not just demux EOF. | Deterministic production scheduler tests pass; real codec execution, audible pacing, and physical visuals remain open. |
| Missing menu, subtitle, and loading glyphs | Previous fixes cover missing native texture allocation, atlas width/height and UVs, short-WCHAR calls/formatting, glyph measurement, and presentation scopes. Indexed submission still applied its final ShaderClass before TextureClass replay, whose device SetTexture path can overwrite combiner state. | Final original indexed ShaderClass now applies after texture binding/sampler replay, before geometry. | Host ordering regression plus ARM closure required; no claim that all missing-text symptoms share this cause. |
| Loading progress | Save/load chunk counts were promoted into Combat's seven-stage milestone value. Repeated status notifications could drive unnecessary rendering and make large loads reach 100 percent early. Static last-progress state also survived new LoadingScreen instances, leaving a later instance's clamp uninitialized. | Keep counters separate; status-only callbacks use -1 and are throttled to 50 ms. Explicit milestone callbacks remain immediate. Guard redraw reentry. Initialize the clamp and store progress history per loading-screen instance. | Deterministic staging and source contracts; executable repeated-load coverage remains pending. This does not make a long synchronous operation without callbacks continuously animated. |
| NPC target boxes | Dev89 changed coordinates; Dev90 reverted the overcorrection; Dev93/95/98 align update/render/init scopes. Current target projection converts camera clip X/Y into the same 960x544 range used to construct TargetBoxRenderer. | No additional guessed offset. Retain the original box, camera, and physics owners. | Source consistency is not physical alignment. Capture the same target, camera, viewport, and box diagnostic before deciding a further correction. |
| Texture sampler cache | Per-stage sampler memos could survive another stage mutating the same native texture. Failed GL sampler writes were cached as success. Sampler setup also rebound an already bound texture. | Invalidate shared-object sampler memos before writes; commit cache state only after success; restore a changed binding; suppress redundant binds. | Actual production functions tested against object-state GL fake, including ASan/UBSan. A 600-frame synthetic replay reduces native binds 2400 to 1200 with identical state fingerprint E61BC335 and 4800 parameter calls. This is not an FPS benchmark. |
| Performance comparisons | Earlier parsing mixed ms/us and memory units, accepted non-finite values, and accepted a log whose final identity hid a mid-run camera/content/configuration change. | Schema 2 normalizes explicit units, preserves raw value and provenance, rejects ambiguous units and conflicting run identities, and excludes non-finite values. | Executable parser regressions. Aggregate log summaries remain descriptive, not a replacement for raw fixed-route frame samples. |

## Preparation and 60+ FPS work

Already present: deterministic host staging, ccache, incremental ARM builds,
unchanged retail MIX lookup/index caches, startup file touches, lazy original
font/glyph caches, texture-loader service calls, a VitaGL shader-cache directory,
one loading-screen warm frame, and 60 M00 render-only warm frames. These have
different effects; an archive read is not a decoded texture, a generated glyph,
or a compiled shader. The former pre-cache terminology overstates what file
touches alone can guarantee. TextureLoader::Update currently services network
work, not asynchronous texture decoding; scene rendering performs actual
first-use resource creation. Dev100 removes M01-only startup indexing/touches
from the M00 demo instead of warming content that cannot be played.

Dev100 adopts only the demonstrated redundant-bind removal and cache
correctness repair. It does not change traversal, material ordering, physics,
animation, simulation, retail formats, render resolution, or quality to report
a gain. The exact `gpt-5.3-codex-spark` model is unavailable in this session;
work is coordinator-owned without model substitution.

Next optimization candidates, pending evidence:

1. Replace fixed scene warm-frame counts with bounded convergence on new
   uploads, resident bytes, backend errors, and observed shader compilations.
   This targets startup/stutter; it cannot establish sustained 60+ FPS.
2. Check whether the installed VitaGL archive actually enables persistent
   shader caching. Calling the cache-path API alone does not prove disk hits.
3. Profile original mesh submission versus present, simulation, indexed HUD,
   texture upload, and resource work using one fixed route and matching content.
   The immediate-mode path and CPU material evaluation are audit leads, not
   approved speculative rewrites.
4. Pre-generate only reusable original-owned resources that appear in measured
   first-use stalls. Preserve asset keys, lifetime/eviction, memory budgets,
   and transparent draw order. Avoid bulk asset duplication or a new format.
5. Retain 16.667/20/33.333/50 ms bands, but judge the user's goal against the
   16.667 ms budget. 50/30/20 FPS are diagnostic bands, not target acceptance.

Before any performance adoption: matching route/content/configuration/build,
raw frame samples and p50/p95/p99/worst, CPU stages, upload/bind/cache counters,
memory low-water/high-water, and physical visual/correctness evidence.
Prewarm can reduce first-use stalls; steady-state FPS needs measured hot-path
cost reduction. No 60+ FPS result is claimed.

## Validation and limitations

The focused sampler/scheduler/ledger set passes 27 tests. The ten sampler
cases pass ASan/UBSan. Matching baseline/current synthetic replay executables,
source snapshot, staging logs, sanitizer logs, and build logs are retained in
`build/dev100-host-evidence/`. Canonical closure and final evidence will be
recorded after the background build completes.

The default host retail path was absent, but the existing Vita3K VFS contains
shared archives, M00 and both intro movies. These files remain unchanged.
Host FFmpeg CLI exists; development libraries are not exposed through
pkg-config. A separate bounded host decode is being retained for the actual
movies. Both completed with exit 0: EA_WW is 15.333333 seconds with 44100 Hz
stereo audio; R_Intro is 31.666667 seconds with 48000 Hz stereo audio. Both
are 800x600, authored at 15 FPS. The scheduler test itself uses synthetic packet/audio timing and
does not claim real-codec or audible pacing evidence. Existing host mission
evidence must be labelled retained if the canonical build reuses it.

The current VitaGL texture-object ownership assumption is corroborated by
the upstream [texture implementation](https://github.com/Rinnegatamante/vitaGL/blob/master/source/textures.c).
No external sampler implementation was copied into the port. A pinned vitaGL
source archive was fetched into ignored build dependency storage and built
locally with splash disabled, persistent shader caching and Vita3K support
enabled, without upstream global fast-math. Build options and archive/library
hashes are retained in `build/deps/vitagl-demo/provenance.txt`. Actual shader
cache hits and physical performance remain separate follow-ups.

## Demo scope

`docs/DEMO_CREDITS.md` records M00-only behavior and release gates. Original
Combat success now starts a three-second fade, ten-second exact thank-you
message, and twenty-second credits scene using original Render2D/Sentence
owners. Simulation stops after success; rendering/audio remain serviced in
the existing runtime until normal teardown. Failure/death never triggers a
thank-you. Unsupported map requests are consumed rather than falling through
to original desktop launch code. No retail or logo artwork is packaged.

Vita3K setup/runner changes preserve title backups and receipts, translate
Windows argument paths, and stop reporting process exit zero as gameplay
success. Full tutorial completion and both PS Vita/PSTV acceptance are open.

Latest closure: the executable demo policy and all 123 fast-build contracts
pass. ARM compilation fails on a remaining `kM01CacheIndex` startup check at
`port/platform/vita/a31_vita_runtime.cpp:2211`, left behind by the M00-only
change. Correction awaits user direction. No build remains running, canonical
closure has not started, and no Dev100 emulator/hardware launch is claimed.
