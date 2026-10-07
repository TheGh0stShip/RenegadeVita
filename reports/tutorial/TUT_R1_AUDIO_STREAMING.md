# Tutorial round 1: AUDIO_STREAMING (RVAU1)

Scope: tutorial audio cost and heap churn in the Vita Miles replacement
(`port/audio/vita`). Base: `45c6cf5` (main + FPS round-4 dev240 candidate).
Only source reading, retail header analysis (read only, nothing copied) and
pure-Python tests were done. **Nothing was compiled or run on a Vita or in
Vita3K. Every gain below is an estimate.**

## Summary

- **Switch:** `ux0:data/renegade/user/config/audio-cost-v1.flag`, exactly
  `RVAU1 <hex>\n`. Default is **0, all off** (`RENEGADE_VITA_AUDIO_COST_DEFAULT`).
  `RVAU1 F` turns on all four bits.
- **Bit 0, exact ADPCM reserve.** Fixes a real defect. 264 `always.dat` voice
  files (178 of them `m00*` generic soldier chatter) make the decoder's PCM
  vector regrow to about twice its size and keep that capacity.
- **Bit 1, stream cache probe.** A stream replay used to decode the whole file
  and then throw the result away when the PCM cache already held it. It now
  looks in the cache first.
- **Bit 2, second-open admission.** One-shot dialogue streams no longer fill
  the 4 MiB PCM cache and evict effect PCM, including the RVPL1 loading
  pre-warm.
- **Bit 3, image slab.** Stream file images are read into a bounded, reusable
  128 KiB slab. When an image does not fit or every slab is busy, the existing
  heap path is used.
- Under every bit the mixer reads the same PCM bytes, and the cursor, loop and
  gain arithmetic is unchanged. The source contract pins that the mixer has no
  RVAU1 code. The new C++ host test, which mixes under every mask and compares
  each mask to mask 0, has **not been run**.

## Findings (line numbers are base `45c6cf5` unless marked "new")

### F1. Which tutorial sounds are streamed, and what they cost

- Any 2D sound file larger than 20,000 bytes is streamed
  (`DEF_MAX_2D_BUFFER_SIZE`, staging/wwaudio/WWAudio.h:99; WWAudio.cpp:704).
- 3D sound files are held in memory up to 200,000 bytes (WWAudio.h:100 ×2 at
  WWAudio.cpp:215).
- Each start of a stream calls `AIL_open_stream_by_sample`
  (soundstreamhandle.cpp:80). That call reads the whole file and then decodes
  all of it to PCM:
  - `Read_Stream_Image` (provider:1115, allocation at :1137)
  - `Prepare_Stream_Source` → `Decode_Wave_With_Info` (provider:511)
  - `Publish_Stream_Source_Locked` (provider:533)
- The M00 level conversations have 228 remarks, which resolve to 221 voice
  files in `always.dat`:
  - 213 are IMA mono at 22.05 kHz; 8 are PCM16.
  - Image size: median 39.5 KB, p90 71.7 KB, max 512.8 KB.
  - 197 are larger than 20,000 bytes, so they are streamed. Their decoded PCM
    is median 164 KB, mean 189 KB, max 2.03 MB (`m00ccnc_dsgn0004i1ccnc_snd.wav`).
    It totals about 37 MB.
  - 2 of these lines decode to more than 1 MiB of PCM and are never cached.
- The newest private tutorial run (dev230,
  `build/device-evidence/A3.5-dev230-20261004/`) has these aggregate counters:
  about 1.4k 2D sample-file loads, 0.17k 3D loads, about 200 stream opens,
  16 MB read and 29 M frames decoded by streams (about 58 MB of PCM16
  allocated). The run is dominated by dialogue streams.

### F2. A stream replay always decodes again

`Prepare_Stream_Source` always decodes. `Publish_Stream_Source_Locked` looks in
the cache only afterwards (provider:550-556). On a cache hit it throws the new
decode away, but still counts it in `pcm_decodes` (:551).

So caching a stream saves no decode time on a replay. It only shares memory.
Each replay still allocates a transient copy of the whole PCM (about 4× the
image size for IMA) and spends the decode CPU.

### F3. One-shot dialogue streams churn the PCM cache

- Each stream decode of 1 MiB or less is admitted to the cache
  (provider:568 → `Cache_Pcm`/`Make_Pcm_Cache_Room` :367-401). The cache
  evicts least-recently-used idle entries to make room.
- About 25 median dialogue lines fill the 4 MiB budget. After that, every new
  line evicts idle effect PCM.
- The idle effect PCM includes what RVPL1 pre-warmed while loading
  (a31_vita_runtime.cpp:4220). The pre-warm never evicts and stops when the
  budget is reached, so its entries are the oldest in the LRU order.
- The tutorial runs Logan's and Sydney's dialogue before the Gunner range.
  This plausibly evicts the pre-warmed fire and explosion PCM before the first
  shot, which brings back the first-use decodes that RVPL1 was meant to remove.
  This is inferred from the source, not measured.

### F4. ADPCM decodes regrow to about twice their size (real defect)

- `Decode_Wave_With_Info` reserves `min(estimate, 2 × data_bytes)` samples
  (decoder:687).
- Two cases overflow that reserve:
  - Mono IMA output is padded to the fact count (`resize(fact)`, :716).
  - A final block no larger than its header still produces 1–2 frames
    (`push_back` :56, `insert` :269). The estimate counts it as zero.
- On overflow, libstdc++ grows the vector to `size + max(size, n)`, which is
  about 2× its size. Peak use is then about 3× the decoded size (old buffer
  plus new). The 2× capacity is kept, and the cache budget is charged for it,
  because `Pcm_Bytes` uses `capacity()`.
- A Python model of the decoder's allocation sequence (see Tests) swept all
  8,915 ADPCM headers in `always.dat`. 264 files regrow:
  - 178 are `m00*` generic soldier chatter (`m00gnod_kill*`, `_hesx*`,
    `_secx*`, `_gcon*`), which AI soldiers say in combat, including at the
    tutorial range. That they play there is inferred, not traced.
  - 36 are `mxx*`; the rest belong to M01–M11 lines.
  - None of the 221 M00 conversation lines regrow.
- Example, `m00gnod_kill0007r2nomg_snd.wav`, which decodes to 145 KB:
  - Old: peak about 433 KB, keeps 289 KB.
  - Bit 0: peak and kept size both 145 KB.

### F5. Per-open heap allocations

Each stream open allocates the following:

| Allocation | Lifetime | Size |
|---|---|---|
| File image | transient | median 42 KB, variable |
| Decode scratch vector | transient | about 2 KB (decoder:278/396) |
| PCM vector | long-lived (cache or line) | median 164 KB, variable |
| `RenegadeMilesPcm` | long-lived | about 100 B |
| `RenegadeMilesStream` | stream | 8 B |

The image is allocated, then the long-lived PCM, then the image is freed. That
order leaves a hole below each long-lived block, a classic fragmentation
pattern.

### F6. Voices and mixer

- WWAudio allocates 16 2D handles and 16 3D handles (WWAudio.h:91-92), so 32
  voices at most. Streams borrow 2D handles. The logs show 32 handles
  allocated, up to 18 active in campaign logs and 12 at the end of the
  tutorial.
- The output is 48 kHz stereo in 1024-frame blocks (provider:97, :1051), a
  21.3 ms deadline.
- Work in each callback:
  - Clearing an 8 KB accumulator (:872).
  - For each voice: gains, one `sqrt` for spatial voices, and a linear
    resample with a double cursor.
  - Voices with zero gain only advance their cursor (:918).
  - Two clamp and statistics passes.
- Locking: `trylock`; if the lock is held, the callback outputs silence
  (:1003).
- Worst case is about 33k voice-frames per callback, roughly 1–2 ms on the
  Cortex-A9 (estimate). **No mixer change is justified.**
- MPEG voices still decode while their gain is zero (:907). FPS round 4 kept
  this on purpose: skipping the decode would move mpg123 to a seek path that
  cannot be proven bit-identical. Left as is.

## Changes

| File | Change |
|---|---|
| `port/audio/vita/renegade_audio_cost.h` (new) | Mode bits, the `RVAU1` parser, and `RenegadeAudioImagePool<SlabBytes,Slabs>`: atomic claims, slab allocated on first claim, returns no lease when the image is too large, all slabs are busy or allocation fails, plus `Free_Idle` |
| `renegade_wave_decoder.{h,cpp}` | `Exact_Adpcm_Reserve` (new :460), used only when `g_exact_decode_reserve` is set (new :719). Adds `Set_Exact_Decode_Reserve` and `Exact_Decode_Reserve_Raises` |
| `renegade_miles_provider.cpp` | See the list below this table |
| `renegade_miles_runtime_stats.h` | `RenegadeMilesAudioCostStats`, set/get mode, stats query |
| `port/platform/vita/a31_vita_runtime.cpp` | One `A3.5 audio-cost:` line after the existing audio checkpoint line (new :2908) |
| `tools/test_vita_audio_cost_contract.py` (new) | Pure-Python contract and decoder allocation model |
| `tools/vita_audio_cost_equivalence_test.cpp` and `tools/test_vita_audio_cost_equivalence.py` (new) | g++ host equivalence test, ASan/UBSan. **Not run** (compiling was not allowed) |

Changes in `renegade_miles_provider.cpp`:

- The flag is read in `AIL_startup`, on Vita only (new :1308).
- With all stream bits off, `AIL_open_stream_by_sample` runs the original
  sequence unchanged. The OOM test's allocation order is preserved.
- `Load_Stream_Source_Costed` (new :1234), in order:
  1. Read the image into a slab or onto the heap.
  2. MPEG images, and images under 12 bytes, are copied to the heap and take
     the original path.
  3. Hash the image.
  4. Bit 1: under the lock, look in the cache and take a pin reference.
  5. Decode, unless the cache supplied the PCM.
  6. Release the slab or image before the publish lock is taken.
- `Publish_Stream_Source_Locked` gains a pinned branch (new :603). It matches
  the cache-hit branch and does not count a decode.
- Bit 2 admission is checked in `Admit_Stream_Pcm_Locked` (new :565), using a
  64-entry ring.
- A defensive pin release runs before the final unlock. `AIL_shutdown` frees
  idle slabs and clears the ring.

Bits:

| Bit | Name | What it does |
|---|---|---|
| 0 | exact reserve | Reserves the final ADPCM size once (header-only final block, mono IMA fact padding) |
| 1 | stream cache probe | Reuses a cached decode of identical bytes (same hash and length key as publication). The pin keeps it from being evicted until publication |
| 2 | second-open admission | Stream PCM is cached only if the same bytes were opened among the last 64 first-time opens |
| 3 | image slab | 2 × 128 KiB slabs at most. Usually only one is ever allocated, because opens are serial under WWAudio's `MMSLockClass`. One slab holds 188 of the 197 tutorial stream images |

Why the output stays sample-identical:

- Decoding is a pure function of the image bytes.
- The cache key (64-bit content hash and length) is the one publication
  already trusts.
- Reserving capacity does not change the samples written.
- Admission changes only whether PCM is kept after a stream closes.
- A pinned entry has two or more references, so `Make_Pcm_Cache_Room`
  (which evicts only `references == 1`) cannot evict it.
- The slab holds the same bytes the heap buffer would.

Sample-file and pre-warm decodes (`Decode_Into_Sample`,
`Renegade_Miles_Prewarm_Pcm`) are untouched apart from bit 0.

## Hypothesis ledger entry (proposed; shared ledger not edited)

**Hypothesis.** The tutorial's audio heap churn comes mostly from
dialogue-stream decodes passing through the PCM cache, plus regrowth of
fact-padded chatter. With RVAU1 on:

- Fewer large variable-size allocations.
- Effect PCM, including the pre-warm, survives the dialogue segments.
- Replays and fact-padded chatter no longer have a 2–3× transient.

The audio output is unchanged.

**Risk.** Low, and default off.

- Bit 2 makes a stream replayed exactly twice decode twice. Today it already
  decodes on every replay (F2).
- Bit 3 keeps 128 KiB resident and copies short MPEG images.
- Bit 0, on a corrupt mono IMA file with a large fact count, can fail on
  allocation earlier. The error message differs; it is a failure either way.

**Estimated effect.** All figures are estimates; nothing was measured.

- **Live/cached PCM in the conversation segments (bit 2):** between 0 and
  about 4 MiB lower `pcm_cache_bytes` / `pcm_live` high-water. It depends on
  how full the effect PCM and RVPL1 pre-warm leave the cache. If the pre-warm
  already fills 4 MiB the high-water does not change, and the gain is the hit
  rate instead: no mid-tutorial re-decodes of fire/explosion sounds.
- **Transient peak per event:**
  - Stream replay (bit 1): minus the full decoded PCM (tutorial median
    164 KB) and about 1–4 ms of decode.
  - Fact-padded chatter (bit 0): minus about 2× the decoded size.
  - Dialogue first plays (bits 0/1): unchanged. Their PCM decode is required.
    The 2.03 MB line still needs a 2 MB contiguous block.
- **Fragmentation (bit 3):** removes one variable-size transient allocation
  per stream open, and the short-lived allocation pattern that sits around the
  long-lived PCM block. It costs +128 KiB resident. The net high-water effect
  is roughly neutral.
- **Frame time:** fewer decode spikes (bits 0 and 1), and fewer first-shot
  re-decode hitches at the range (bit 2).

**How to measure on the tutorial route.** Read the `A3.5 heap`
(in_use/free/top_free), `A3.5 audio` (`pcm=decodes/hits/evictions/entries/bytes`,
`pcm_live=bytes/high/largest`) and new `A3.5 audio-cost` lines at these
checkpoints:

- after Logan
- after Sydney
- at the Gunner range
- after Mobius
- after HMVV
- end gate

Also note `A4 M00 sound PCM preparation: retained_bytes` and the frame-time
p95/p99 during range gunfire.

**Decision.** Deferred until hardware A/B.

## Tests

- **`python3 -m unittest tools.test_vita_audio_cost_contract`: 14 tests OK,
  about 6 s.** It runs no compiler, game or device action. It covers:
  - Flag format and default off.
  - The default stream path is textually the original sequence.
  - Mixer, sample-file and pre-warm functions contain no RVAU1 code.
  - The pool is bounded, falls back to the heap, copies MPEG out of the slab
    and releases the slab before publication.
  - Probe ordering: hash → lock → find → pin → unlock → skip decode.
  - The pinned publish matches the hit branch.
  - Admission ring bound and telemetry line.
  - A Python model of the decoder's ADPCM block counts, its reserve and
    libstdc++ growth:
    - More than 500 synthetic header cases (both codecs, mono and stereo,
      odd tails, overstated and understated samples-per-block, fact ±).
    - The model proves bit 0 never regrows, never costs more capacity or peak,
      and keeps capacity identical wherever the old path did not regrow.
      The one exception is overstated-samples-per-block headers: at most
      2 frames more.
  - When retail data is present, it also sweeps all 8,915 `always.dat` ADPCM
    headers (264 regrow today; 0 with bit 0).
  - The model caught and pinned that overstated-samples-per-block exception.
- **Existing source-only tests still pass:**
  - `test_bounded_3d_audio_contract`: 2 of 3 pass. The third needs `upstream/`,
    which this worktree does not have; the failure is about the environment,
    not this change.
  - `test_mission_conversation_diagnostics_contract`: all pass.
  - `test_renegade_async_log.test_game_thread_paths_enqueue_instead_of_syncing`:
    passes.
- **Not run (it compiles):** `tools.test_vita_audio_cost_equivalence`.
  - It mixes, with ASan/UBSan, a stream sequence of IMA with fact padding and
    a predictor tail, PCM16, and a 153 KB IMA file larger than a slab, with
    overlapping handles, plus a 3D sample.
  - It does this under all 16 masks and requires the output to equal mask 0
    byte for byte.
  - It also requires each bit's counters to fire exactly when that bit is set,
    the slabs to be freed at shutdown, and checks the pool unit cases.
- Also not run: the existing compiled audio tests
  (`test_vita_audio_provider`, `test_vita_audio_mixer_equivalence`,
  `test_vita_audio_deferred_position`, `test_adpcm_block_decoder`). They must
  be re-run on the integrated tree.

## Hardware A/B steps

1. Build the integrated candidate. Run the four existing compiled audio tests
   plus `tools.test_vita_audio_cost_equivalence`. The build scripts' focused
   test lists were left untouched; consider adding the two new modules.
2. **Run A:** no `audio-cost-v1.flag`. Boot, start the Tutorial on Recruit,
   and play the fixed route Logan → Sydney → Gunner range → Mobius → HMVV →
   base buildings → end gate. Pull `a35-*-runtime.log`.
3. **Run B:** write `RVAU1 F` plus a newline (8 bytes) to
   `ux0:data/renegade/user/config/audio-cost-v1.flag`. Cold boot and play the
   same route.
4. **Confirm the flag took effect:** every `A3.5 audio-cost:` line shows
   `mode=F`. `probe=hits` should be above 0 if any stream replayed,
   `stream_pcm=deferred` about the number of dialogue lines, `image_pool=hits`
   about the number of stream opens, and `resident:131072`.
5. Compare A against B at each checkpoint: `pcm_cache_bytes`,
   `pcm_live high`, `pcm decodes/evictions`, heap `in_use`/`top_free`,
   frame-time p95/p99 at the range.
6. **Listen.** Dialogue, effects and music must sound the same, with no
   clipped lines.
7. If B regresses, bisect one bit at a time with `RVAU1 1`, `2`, `4` and `8`.

## Not done, and why

- **Incremental ADPCM streaming** (`reports/ADPCM_STREAMING_DESIGN.md`) is the
  only change that removes the 2 MB contiguous PCM allocation and the
  first-play decode for dialogue. It is too large to land unverified in this
  round. It is the recommended next step if hardware shows the long lines at
  the heap high-water.
- **Skipping the file read on a replay**, keyed by file name, was rejected.
  Name-to-content mapping can change with level MIX overlays; the content hash
  is the only proven key.
- **Skipping MPEG decode for silent voices:** see F6.
- **WWAudio's unbounded raw-buffer cache** (original `Cache_Buffer`, eviction
  commented out upstream, flushed on level change at combat.cpp:600) is
  original engine behaviour, outside this boundary.
