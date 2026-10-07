# Audio stream memory (WAV streams, Vita Miles provider)

Scope: `port/audio/vita/renegade_miles_provider.cpp`, static analysis only (no build, no hardware measurement).

## Code path
- `AIL_open_stream_by_sample` (~L1350-1386): resets the sample (drops previous PCM, L1353), then calls `Read_Stream_Image` and `Prepare_Stream_Source` outside the mixer lock.
- `Read_Stream_Image` (L912-948): allocates one buffer of the full file size (cap `kMaximumWaveBytes` = 64 MiB, L94) and reads it whole.
- `Prepare_Stream_Source` (L344-364): for non-MPEG, `Decode_Wave_With_Info` decodes the full file to PCM16 into `prepared->wave`.
- `Publish_Stream_Source_Locked` (L366-410): moves the PCM into a `RenegadeMilesPcm`; cached if source <= 1 MiB (`kPcmCacheMaximumSourceBytes`, L100; cache budget 4 MiB / 128 slots, L98-99).

## Is the source image freed?
Yes. `image` is a local `std::unique_ptr<uint8_t[]>` (L1356) and is released when `AIL_open_stream_by_sample` returns (L1386). The image is not retained per stream. The overlap is only transient: image + full PCM exist together during decode/publish.

## Estimate (22,050 Hz mono IMA ADPCM, 4 bits/sample -> PCM16, about 4x)
- ADPCM is about 11 KB/s on disk; PCM16 is 44.1 KB/s resident.
- 30 s dialog line: about 330 KB image + 1.32 MB PCM = **about 1.65 MB peak**, then **1.32 MB steady** per stream.
- 2 min ambient loop: about 1.3 MB image + 5.3 MB PCM = **about 6.6 MB peak**, then **5.3 MB steady**.
- Stereo doubles all figures. Decoder scratch inside `Decode_Wave_With_Info` (and any vector growth) is extra and not measured here.
- Sources over 1 MiB (about 95 s or more of mono ADPCM) bypass the PCM cache, so each open decodes again and the memory stays held until close/reset.

With several dialog streams plus one or two ambient loops playing at once, the steady state can easily reach 10-15 MB of PCM. That is significant against Vita main-heap budgets.

## Recommendation
1. Short term: add a stat for per-stream PCM bytes and their high-water mark (beside `stream_bytes_read`), then measure M13 on hardware before changing anything.
2. If the measured high-water mark is material: switch WAV streams to incremental decoding. Keep the encoded image (or a file handle plus a ring buffer of encoded blocks) and decode ADPCM blocks on demand in the mixer, as MPEG already does through `Open_Mpeg_Playback`. Resident memory then drops to about the encoded size (roughly 4x less) or to a small fixed ring buffer.
3. Keep full-decode for small sources (<= 1 MiB, cacheable), where reuse through the cache pays off.
