# ADPCM streaming design (incremental IMA / MS ADPCM stream playback)

Status: design only. Nothing here is built, host-tested or physically validated.
Scope: `port/audio/vita/renegade_miles_provider.cpp` stream path and
`port/audio/vita/renegade_wave_decoder.{h,cpp}`.

## 1. Current behaviour

`AIL_open_stream` reads the whole image (`Read_Stream_Image`), then, outside the
lock, calls `Prepare_Stream_Source`:

- MPEG (`Is_Mpeg_Media`) -> `Open_Mpeg_Playback`, a `MpegPlayback` with a fixed
  decode window plus a one-frame `previous` cache. PCM is never fully materialised.
- Everything else (PCM, IMA 0x0011, MS 0x0002) -> `Decode_Wave_With_Info`, a full
  PCM16 decode into `DecodedWave::samples`. `Publish_Stream_Source_Locked` then
  wraps it in a `RenegadeMilesPcm`, which is cached when
  `bytes <= kPcmCacheMaximumSourceBytes`.

So a long ADPCM music or dialog stream keeps about 4x its encoded size (for IMA)
as live PCM on the Vita, plus the transient image.

## 2. Every provider touch-point on a stream sample

All of these go through `RenegadeMilesSample` fields or `Sample_Frame_Count()`.
This is the complete list a new source kind must satisfy.

| Site | Uses |
|---|---|
| `Sample_Frame_Count` | `mpeg->Frame_Count()`, else `pcm->frames` (the source of truth for length) |
| `Publish_Stream_Source_Locked` | sets `wave.channels/sample_rate/estimated/untrimmed`, `encoded_data_bytes`, `cursor=0`, `playback_rate`, playing/paused |
| `Reset_Sample` | resets `mpeg`, `pcm`, cursor, loop_count/loops_remaining |
| `Start_Sample_Locked` | frame count, cursor clamp, `loops_remaining = loop_count` |
| `Advance_Loop` / `Wrap_Voice` | `loop_count` (0 = infinite), `loops_remaining`, `cursor = 0.0` on wrap |
| `Mix_Locked` | dispatches by kind; `step = playback_rate / 48000`; per-voice gains |
| `Mix_Mpeg_Voice` | `Sample(first,ch)` and `Sample(second,ch)` per output frame per channel; `last = frames-1` clamp |
| `Mix_Pcm_Voice<Mono,Stream>` | direct `pcm[]` indexing with identical interpolation |
| `AIL_set_sample_ms_position` / `AIL_sample_ms_position` (and so `AIL_stream_ms_position`) | `cursor`, frame count, `wave.sample_rate` |
| `AIL_set_3D_sample_offset` / `AIL_3D_sample_offset` | `encoded_data_bytes`, cursor, frame count (the byte offset is proportional, not block-exact) |
| `AIL_set_stream_loop_count` / `AIL_stream_loop_count` -> sample loop count | `loop_count`, `loops_remaining` |
| `AIL_stream_playback_rate` etc. | `playback_rate` |
| `Capture_Last_Stream_Locked`, runtime stats | frame count, `wave.fact/estimated/untrimmed/trimmed_sample_frames`, rate; `active_stream_cursor_frame`, `active_stream_position_ms`, `active_stream_loop_count` |
| `AIL_open_stream` stats | `stream_decoded_frames += Sample_Frame_Count`, PCM live/high-water accounting (`Track_New_Pcm`) |

No consumer needs random access to more than frames `first` and `first+1`. The
cursor only jumps on start, on loop wrap (to 0), and on an ms or offset seek.

## 3. Proposed design

### 3.1 Interface

Generalise the MPEG interface rather than adding a third path. Rename the
abstract base to `StreamPlayback`, keeping `using MpegPlayback = StreamPlayback;`
for compatibility, and add
`std::unique_ptr<StreamPlayback> Open_Adpcm_Playback(std::unique_ptr<uint8_t[]> image, size_t bytes, const char **error)`.
The provider field `sample->mpeg` becomes `sample->stream_source`, and
`Mix_Mpeg_Voice` becomes `Mix_Stream_Voice` with its body unchanged. The virtuals
stay the same: `Frame_Count`, `Sample_Rate`, `Channels`, `Sample(frame, ch)`,
`PCM_Storage_Bytes`. Add one non-virtual metadata accessor,
`const DecodedWave &Metadata()` (with no samples), so `Publish` fills
fact/estimated/untrimmed/trimmed exactly as it does today.

The ADPCM playback **owns the encoded image**. The image is moved out of
`AIL_open_stream`, which today frees its `image` unique_ptr after publishing.
Memory becomes the encoded bytes plus a small ring, instead of the encoded image
(transient) plus the full PCM.

### 3.2 Open (outside the mixer lock)

1. Call `Inspect_Wave(data, bytes, &info, err, false, true)`, the same validation
   `Decode_Wave_With_Info` uses. Reject non-ADPCM input: PCM keeps the existing
   path. PCM streams could later use a zero-decode view of the same class.
2. Build a **block index** in one pre-pass. For block `b`, record
   `first_frame[b]`: the cumulative frames that `Decode_Ima_Block` or
   `Decode_Ms_Block` emits up to that block. This must cover short final blocks
   and the mono-IMA "predictor-only tail" special case in `Decode_Ima`. Frames
   per block can be computed from `block_bytes`, `channels` and
   `samples_per_block` without decoding. To do that, factor the per-block loop
   bounds of the existing decoders out into `Ima_Block_Frames(bytes)` and
   `Ms_Block_Frames(bytes)`, which return exactly those bounds. Some validation
   happens during decode today (IMA step index > 88, MS predictor index). It must
   also run in this header-only pre-pass, so that open fails in exactly the cases
   where full decode failed. Nibbles themselves cannot fail.
3. Compute `untrimmed = sum(frames)` and apply the same post-processing as today.
   For mono IMA with `fact > untrimmed`, zero-pad logically up to `fact`. Then, if
   `sample_frames != 0 && frames > sample_frames`, trim. Store `frame_count`,
   `trimmed` and `untrimmed` exactly as `Decode_Wave_With_Info` does. Keep the
   same `kMaximumDecodedSamples` and IMA fact-ceiling errors.

### 3.3 Block-aligned ring

- The ring holds `R` decoded blocks (R = 4), each slot tagged with its block
  number. For IMA mono 1024-byte blocks (2041 frames each), R = 4 is about 16 KiB
  for stereo.
- `Sample(frame, ch)`:
  - If `frame >= frame_count`, return 0.
  - If `frame >= untrimmed` (the zero-pad region), return 0.
  - Otherwise, find the block in the index. Use the cached last block plus a
    linear step for the common sequential case, and a binary search on a miss.
  - Make sure that block is resident. If it is not, decode that single block
    into a slot with the refactored `Decode_*_Block` (writing into the slot
    instead of calling `Append_Frame` on a vector).
  - Return `slot[frame-first]`.
- ADPCM blocks are self-contained: each header carries the predictor and step
  index, or the coefficients and delta. So **any block can be decoded on its
  own**. A seek costs O(log blocks) plus one block decode, and a loop back to 0
  costs one block decode. Unlike MPEG, no decoder history is needed.
- Eviction is LRU among slots. Because R >= 2, when `first+1` crosses a block
  boundary both blocks stay resident.
- No prefetch in the mixer thread at first. One block decode is about 2k nibbles,
  well under a 1024-frame mix quantum. Measure before adding a worker.

### 3.4 Bit-exactness argument

The full decoder is a concatenation of independent per-block decodes followed by
zero-padding and trimming. Decoding block `b` on its own with the *same function
body* gives identical int16 values. Looking a frame up through the prefix-sum
index gives the same position as the offset into the vector.

Mixer arithmetic is also unchanged, provided the stream voice interpolates
exactly like `Mix_Pcm_Voice`:

- For mono, `Mix_Mpeg_Voice` sets `right_channel = 0` and computes each channel
  separately. That equals the `Mono` branch of `Mix_Pcm_Voice`
  (`interpolated * left_gain` and `interpolated * right_gain`).
- For stereo it matches the stereo branch exactly: same expression order, same
  float casts.

This must be verified, not assumed. The equivalence test must compare the
`Mix_Locked` output of (a) the current full-decode path and (b) the new playback
path for the same scenarios.

To keep a single source of decode logic, refactor `Decode_Ima_Block` and
`Decode_Ms_Block` to write into a sink (`int16_t *out, size_t cap`). The existing
full decoder then calls them through a vector sink. Do not duplicate the nibble
loops.

### 3.5 Cursor / position / loops

These do not change. The cursor stays a `double` in source frames on the sample.
`AIL_*ms_position`, `AIL_3D_sample_offset`, loop counting and `Wrap_Voice` do not
depend on the source kind. A seek only changes the cursor, and the ring simply
misses on the next `Sample`.

Runtime stats change only for PCM accounting. As with MPEG, the playback reports
`PCM_Storage_Bytes()` (the ring) and is tracked neither by `Track_New_Pcm` nor by
the PCM cache. `stream_decoded_frames` keeps meaning "logical frames". Add the
counters `stream_adpcm_block_decodes` and `stream_adpcm_ring_misses`.

### 3.6 Policy

- Streams only (`AIL_open_stream`). Short one-shot `AIL_set_sample_file` samples
  keep the full decode and cache: it is cheap, shared through the cache, and
  supports random access for 3D.
- Threshold: use incremental playback when the encoded image is larger than
  `kPcmCacheMaximumSourceBytes`. Those are exactly the streams that today get an
  uncacheable full decode. Smaller streams keep the cached path, so cache-hit
  behaviour is preserved. A compile-time switch, `RENEGADE_ADPCM_STREAMING`,
  gates the rollout.
- Threading: `Sample()` runs under the mixer lock, as MPEG does. Open and
  indexing run outside it in `Prepare_Stream_Source` (new `prepared->adpcm`).

## 4. Tests

1. Decoder unit test. Build synthetic cases: IMA mono and stereo, MS mono and
   stereo, a short last block, the mono-IMA predictor tail, fact > decoded
   (zero-pad), fact < decoded (trim), and an invalid step index or predictor
   (must give the same error). For each, assert `Sample(f,c) == full.samples[f*ch+c]`
   for every f, in sequential, random-seek and reverse order.
2. Extend `tools/vita_audio_mixer_equivalence_test.cpp` and
   `tools/test_vita_audio_mixer_equivalence.py` with scenarios covering ADPCM
   streams, rate changes, loop_count 0/1/N, and ms and 3D-offset seeks during
   playback. Byte-compare the mixed int16 output of the full-decode and
   incremental paths, and run under ASan/UBSan as the existing test does.
3. Memory test: assert that live stream PCM bytes equal the ring size, not
   `frame_count * ch * 2`.
4. Retail sweep on the host, using the user's own data (never committed): decode
   every ADPCM WAV in always.dat both ways and compare hashes.

## 5. Risks

- The pre-pass must reproduce every decode-time failure. Otherwise a stream that
  used to fail to open would play noise. Test 1 covers this.
- `AIL_3D_sample_offset` stays proportional, not block-exact. That is unchanged.
- The encoded image is held for the stream's lifetime. This is acceptable because
  it is smaller than the PCM it replaces.
- Underruns need physical Vita evidence. Host and Vita3K results do not prove it.
