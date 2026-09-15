# Dev127 fixes and pre-hardware optimization audit

Latest user steering: compare similar native Vita ports and continue toward
60 FPS. Physical testing remains held. Six pinned projects are compared in
DEV127_UPSTREAM_60FPS_COMPARISON.md; native-resolution sustained 60 FPS is not
assumed from their headline claims. Indexed mesh/generic draws and movie upload
reductions pass local production-function equivalence checks. Canonical rebuild
is running after correcting its obsolete symbol requirement and sampler-test
extraction boundary. Native compressed textures and persistent GPU geometry remain
open routes with documented ownership/lifetime prerequisites; the audit is not
exhausted. No physical access occurred. Further code changes need matching builds.

User requires fixes followed by a full build/FPS optimization inspection before
any further physical test. Do not deploy another candidate during this work.
Original engine owners, retail semantics and measured correctness remain gates.

1. Resolve physical Mobius/START crash: mapped _kill_r trap and heuristic stack
   identify abort/terminate/operator-new/Decode_Mpeg vector growth. Replace native
   whole-track PCM expansion with bounded MPEG decoding; validate seek, loop,
   sample identity, failure and cleanup behavior using generated fixtures.
2. Fix ladder control presentation and inspect missing EVA datalinks.
3. Resolve movie conversion/upload cost and missing audible output based on
   returned native measurements. Preserve original Bink assets.
4. Audit applicable FPS routes: build flags/CPU instructions; renderer state,
   per-vertex transforms/material/lighting, batching and allocation; texture
   transfers and cache; simulation/path budgets; resource I/O; audio decode/mix;
   synchronization/frame pacing; instrumentation overhead and memory lifetime.
   Record each route as adopted with checks, rejected with evidence, or blocked
   on a precisely identified physical measurement. No speculative semantics cuts.
5. Consolidated ARM/package/identity/artifact audit, then physical candidate only
   after this audit is exhausted. The latest user steering keeps physical testing
   held while further indexed-renderer and movie-transfer optimizations close.
   No 60 FPS claim from host or build results.

Physical Dev126: runtime b48c47198585da3ce9532c6e8f87141a440d94af99edd2e1cc9ecc3138089fe4;
dump 72f954e8805c8cdfe42d27c9bbaeed9cab8e66426527ab9ea6b01216a2770407.
Matching installed SELF verified. Dump module base 0x8105b000, ELF base
0x81000000, main PC 0x813e794a maps to 0x8138c94a (_kill_r). Stack candidates
are heuristic, not an unwound backtrace; inline addr2line of saved return minus
instruction offset resolves vector insert in Decode_Mpeg line399.

Late gameplay cumulative average 13.1 FPS with render59.7ms/simulation16.5ms.
First intro: 115 uploads/115 drops over20.632s; receive/scale8.473s, send4.131s,
upload1.349s, draw0.059s. Draw submission itself is not the dominant movie cost.
Audio output counters do not prove audibility. User reports movie silence.

Dev126 Logan float-priority diagnostic format is incorrect (Priority is int).
Do not interpret its shifted fields as corrupt game state; correct before reuse.

## Current local work (unpackaged, no new physical test)

- Bounded MPEG player replaces native whole-track PCM expansion. Generated music
  matches every decoded sample across window boundaries, seeks and mixer loops;
  focused audio/HUD tests pass and decoder/provider ARM objects compile.
- Original EncyclopediaMgr initialization/shutdown restored around campaign
  lifetime. Tutorial input strings now cover original conversation caption IDs,
  including the ladder instruction, through in-memory English TDB presentation.
- Deferred Bink colour conversion avoids converting frames discarded as late.
  Seven production scheduler cases pass ASan/UBSan. FFmpeg speed dependency built
  successfully: CONFIG_SMALL disabled, final -O3, Cortex-A9/NEON retained.
- Production material-cache comparison: 192,000 exact result comparisons pass;
  light/material/source changes, pass reset, generation wrap, direct-map collisions
  and missing inputs included. Ten native sampler-cache cases also pass ASan/UBSan.
  Fixed host material fixture (40 repeats of 65,536 corners): uncached vs cached
  median 11818/1500us, p95 16743/7213us, p99/worst 23377/12742us. Concurrent build
  load affects host timings; operation counts are decisive: evaluations
  2621440 -> 163840, normalizations 10485760 -> 160. Scratch capped at 655360B
  on this host ABI. These are CPU fixture results, not native FPS/visual acceptance.
- Audio output lifetime correction in progress: aligned alternating blocks in
  movie and Miles threads; drain before block destruction. Movie PCM peak/nonzero
  counters added because prior API-success counts cannot establish audibility.
  Reference-only inspection: SDL Vita backend uses aligned rotating buffers
  (https://raw.githubusercontent.com/libsdl-org/SDL/main/src/audio/vita/SDL_vitaaudio.c).
  No SDL source copied. User's local EA_WW.BIK decodes on host with mean -18.5dB,
  peak -3.9dB; retail data unchanged and excluded from artifacts.
- Audit found vitaGL's convenience initializer selects 4x MSAA. No silent quality
  reduction adopted. Main gameplay has no unconditional 16.7ms sleep; those delays
  belong to suspended/frontend/ending paths. CPU/GPU clock selection is absent and
  needs an explicit native platform policy/measurement. Original simulation and
  pathfinding budgets remain correctness owners.

## Consolidated validation update

First fast package passed 138 focused checks and ARM/ELF/SELF/VPK identity. It is
superseded locally (never deployed): expanded MPEG tests found insufficient default
seek pre-roll on 22050Hz mono, corrected with bounded 16-frame mpg123 pre-roll.
ASan/UBSan now passes mono/stereo 22050/44100/48000Hz, up to 30 seconds, sequential
and interpolated reads, arbitrary seeks, loops and stop/release. Stereo fixtures
match exactly; mono has six one-LSB feeder/reader quantization differences. This
is explicitly bounded to one signed-16 LSB, not claimed bit-identical for mono.
MPEG duration inspection now scans headers instead of decoding the full track.

Native output lifetime test retains SDK pointers until the next submission and
checks alignment, wrap at four offsets, sample order, final padding and drain.
It passes ASan/UBSan. Native indexed preparation equivalence passes 30 cases,
including invalid bounds/overflow/layout/transforms without checksum commits.
Sampler/material/direct-atlas/indexed reuse enabled for this candidate (mode15);
RVRC1 0 remains a baseline override for a later matching physical comparison.
Direct atlas uses the completed original A4R4G4B4 surface and the same pixel
converter; removes empty texture allocation/upload/copy. Original TextureClass
owns the completed texture and source atlas is no longer mutated after creation.

Native userland clock requests added with before/result/actual readback:
CPU444/BUS222/GPU222/XBAR166MHz. No plugin/kernel override. Reference for supported
native requests: https://github.com/Rinnegatamante/Vita-Recorder/blob/main/main.c
(API pattern only, no source copied). Physical power-policy results remain unknown.

Canonical build now running with -Wformat enabled so attributed native logs are
actually checked; fix attributable format defects before finalizing artifacts.
No deployment or physical acceptance. Continue the remaining optimization audit.

## Additional dependency/layout finding

Pinned vitaGL immediate vertices reserve 22/24/26 floats for zero/one/two textures
even when lighting is disabled and only 7/9/11 floats are written. Candidate
dependency patch compacts only unlit strides; lit bytes/attributes remain intact.
GPU stream stride and emitted pool advancement change together. Production
glVertex3f/glEnd bodies tested against a recording GXM sink, pristine and patched:
48 draws each, all attributes equal including lighting/texture transitions;
ASan/UBSan pass. Single-texture unlit reservation 96 -> 36 bytes. Combined fixture
(half lit) reservation 456192 -> 313632 bytes. No measured GPU/FPS/visual claim.
Patch lives outside EA staging under port/renderer/vita/dependency-patches and
is reapplied with zero fuzz from the pinned archive by build_vitagl_demo.sh;
dependency provenance includes patch and resulting source hashes. Archive rebuild
and final canonical validation still required after the current baseline build.

Compiler format audit found vehicle TypeName (StringClass) passed through varargs
as %s. Vehicle diagnostics now use Peek_Buffer; passenger entering/exiting animation
names use bounded snprintf with explicit buffers. Changes remain in the existing
zero-fuzz vehicle patch. Current running canonical build predates this staging
change and must be refreshed; do not deploy its intermediate result.
