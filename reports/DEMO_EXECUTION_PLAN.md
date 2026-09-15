# Active M00 demo execution plan

Current override (Dev127): complete the user's reported native crash, movie,
controls-caption and EVA fixes plus further indexed-renderer/movie-transfer
optimizations. Physical testing is held. Current plan and route decisions are in
DEV127_FIX_AND_OPTIMIZATION_PLAN.md and DEV127_OPTIMIZATION_AUDIT.md. The older
Dev108-116 emulator sequence and build-approval language below are historical;
they are not current instructions. No new persistent goal was created on resume.

Persistent goal created 2026-09-09 UTC in the current Codex thread. The full
Renegade Vita port remains the durable program; the M00-only demo is interim.

## Ordered completion gates

1. Preserve canonical Dev108 closure and matching artifact identities; its r3
   completed. Dev109 canonical was explicitly superseded, not passed. Dev110
   fast package is installed but not launched; never substitute fast evidence
   for canonical acceptance of a later consolidated candidate.
2. Reliable background input with observed original-game consumption and released
   controls. Queued window messages and cursor movement are insufficient proof.
3. Create a real original M00 quicksave, retain an immutable checkpoint and load
   it through original SaveGameManager without replacing the restored player.
4. Complete the entire original M00 tutorial; retain progression evidence and
   checkpoint proven segments instead of repeating complete fresh runs.
5. Observe original mission-success fade, exact requested thank-you, dependency
   credits and safe exit without M01 or the VitaGL spinning splash.
6. Retain candidate-scoped package, source/patch identities, ELF/map/symbols,
   emulator evidence and installation instructions without retail data/saves.
7. Assess remaining presentation and measured performance gaps honestly against
   the 60 FPS+ target; no log-only visual correctness or emulator-to-hardware
   acceptance inference. Physical PS Vita/PSTV tests stay on hold until major
   progress and user direction.

## Current action: substantial renderer/performance and save/resume batch

The current coherent source optimization batch is implemented and ready for
consolidated review/validation, which remains held by the user. Do not prolong
the source pass with speculative edits merely to avoid reporting this boundary.
Request approval for one consolidated build and host/Vita3K validation cycle;
no action on physical devices. This does not mean the renderer is fully optimized
or the demo is complete. Validation may reveal necessary fixes and further
measurable costs. Full save/load, tutorial, presentation and ending gates remain.

Consolidated authoritative status is source_optimization_batch in BUILD_STATE.json.
The timer boundary already has a constant performance frequency and one monotonic
clock read. Leave its clock domain, elapsed-time units and update cadence intact;
do not manufacture a timing optimization or alter gameplay rates to claim FPS.
The implemented source batch has no staging/build/runtime acceptance. Completing
this source pass does not close save/load, tutorial, visual, ending or device gates.

The user prohibits further builds for small steps. No build is running or
requested. Dev110's already-built correctness batch contains original quicksave
dispatch, numeric-font format conversion, icon readiness and loading-animation
diagnostics. Its install returned INSTALLED_NOT_LAUNCHED. Dev109 was closed by
owned-window request, without forced termination; retain its evidence.

Source tracing confirms redundant material evaluation per triangle corner and
four native sampler writes per individual parameter transition. Implement
bounded per-pass reuse and texture-object parameter caching, initially opt-in
for same-SELF A/B comparisons. See RENDER_WORK_REUSE_BATCH.md. Do not call these
measured gains or include them in descriptions of the existing Dev110 binary.

Added a third opt-in path: completed original text atlases seed TextureClass
directly instead of blank texture creation followed by a replacement upload.
It preserves original sentence layout and lifetime and is registered as a
zero-fuzz patch. Modes 0..7 isolate each optimization in one future binary.
No build or test has been run for this source batch.

The material-reuse mode now also prepares original normalized light directions
once per mesh pass, rather than per vertex, with operation-count telemetry.
This remains unbuilt source, not a measured gain or lighting acceptance result.

User explicitly declined Dev110 tests and further builds/tests during this
optimization pass, and clarified: implement source-identifiable improvements
now, get measurements afterward. Do not repeat requests or treat continuation
as approval. Added an unexecuted fixed-window CSV
comparison tool with identity, workload and contamination checks; no benchmark
result or new acceptance gate follows from creating that tool.

Added combined indexed bounds/checksum preparation as mode bit 8, with original
checks and checksum ordering retained. Selector is now hexadecimal 0..F.
Next source work should prioritize submission/UV preparation and resource churn,
not additional benchmark infrastructure. No build or test was run.

Material reuse now includes meshes larger than 8192 vertices without increasing
the entry limit: bounded direct mapping with exact vertex/material keys replaces
the former large-mesh fallback. This is source-only optimization; retain the
build/test hold and obtain measurements after the consolidated pass.

Per-pass material-cache invalidation now uses generation tags instead of clearing
every entry each pass. Initialization and generation wrap remain explicit; no
runtime or performance acceptance follows from this source change.

Texture-object sampler invalidation also uses generation tags, avoiding full
table clears during repeated procedural texture updates. Upload, deletion,
external GL and backend reset still invalidate state; wrap clears explicitly.
All optimization work remains source-only under the build/test hold.

FreeType preparation now shares successful glyph rasterization between measure
and draw, skips repeated size selection and deduplicates identical retail font
aliases. Size/style/character changes and failures invalidate the face-local
glyph memo. Layout and raster-output equivalence remain untested under the hold.

Original MIX failure paths now return file objects on unavailable archives and
failed filename-list opens, avoiding unbalanced factory ownership. Registered
source patch only; no repeated-load test or memory-result claim.

Texture wrapper construction now balances its temporary GetSurfaceLevel reference
after metadata extraction, retaining its separate texture-owner reference.
Registered source patch; repeated-lifecycle memory evidence remains deferred.

Original dynamic vertex/index and sorting buffers now share a native-only capped
growth policy, reducing repeated reallocations as larger draw batches arrive.
The original buffer owners, 16-bit limits, locks, offsets and draw counts remain.
Registered ww3d2-a35-dynamic-buffer-growth.patch; not staged/built/tested.

Skin scratch allocation now grows geometrically for normal mesh sizes, bounded
at 16384 entries before reverting to exact-size growth for larger requests.
This reduces repeated growth allocations without dropping deformation or meshes.
Memory tradeoff and encounter-time impact remain to be measured afterward.

DDS preparation now combines original pixel decode/checksum/RGBA storage and
retained CPU-surface population into one traversal, preserving existing helpers
and mip upload semantics. No pixel-equivalence or timing test has been run.

Aligned DXT1/DXT5 levels now additionally use original 4x4 block decompression,
with the retained CPU surface as a four-row cache. No new decoder, asset format
or scratch-image allocation; checksum/output row order remains unchanged by
design. Pixel equivalence remains deferred under the explicit test hold.

The original DXT block decoder now precomputes its color palette once per block,
retaining Combine_Colors rounding and original alpha behavior. Registered patch;
not staged, built or tested during this pass.

Audio load preparation now avoids duplicate RIFF/WAVE parsing and pre-reserves
bounded ADPCM output capacity. Existing Decode_Wave callers keep their API;
the Miles boundary receives metadata from the decoder's own validated parse.
See AUDIO_DECODE_PREPARATION_BATCH.md. No tests, builds or runtime changes run.

IMA ADPCM now precomputes fixed step/nibble transitions once, with bounded static
tables and the same individual-shift rounding and predictor saturation. Source
optimization only; later audio-byte equivalence and timing remain open.

Filesystem source pass: original MIX requests already binary-search a resident
CRC index; no redundant replacement cache added. Registered offset/count bounds
hardening at original MIX construction to prevent invalid count-derived allocation
and empty-index access. See MIX_LOOKUP_SOURCE_PASS.md; no FPS or crash-cause claim.

Next: consolidate remaining submission/UV/upload work against evidence, establish
a fixed original M00 route/checkpoint, and compare baseline versus each cache
mode with matching content/camera/input. Original save/load, loading animation,
HUD visual acceptance and complete tutorial/ending remain open. No emulator fork,
new builds for diagnostics alone, or physical device access.

## Working rule

When a substantial batch warrants a build, keep it detached and progress on independent runtime work; check build status
only at useful boundaries. Update this plan after material evidence, gate closure
or blocker changes. Do not mark the persistent goal complete before the required
demo work is actually evidenced, or blocked before its required recurrence audit.
