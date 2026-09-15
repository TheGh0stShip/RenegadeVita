# Audio decode preparation optimization

Status: source implemented, unbuilt and untested, part of the consolidated
source-first optimization pass. No emulator, hardware or benchmark claim.

## Source-identified costs

Decode_Into_Sample in the native Miles provider previously called Inspect_Wave
and then Decode_Wave, which called Inspect_Wave again. Both scans checked RIFF
chunks and built the Microsoft ADPCM coefficient vector. The provider needed
only the resulting encoded data-byte count in addition to decoded samples.

PCM decoding already reserves its final vector capacity. ADPCM decoding did not:
Append_Frame repeatedly grew the vector while decoding every block, potentially
copying prior PCM output during growth. These costs occur at sound loading, not
necessarily during every steady-state audio callback. The output thread's output
vector is already allocated outside its loop; it was not changed.

## Changes

- IMA ADPCM's 89 step indices and 16 nibble transitions are prepared once into
  fixed difference/next-index arrays (7120 bytes of table payload, no heap).
  Decoding uses lookups instead of repeated shifts, sign branches and step-index
  clamping. Preparation preserves each individual shift and signed difference;
  predictor saturation remains in the original sample loop. Difference entries
  use 32 bits because their pre-clamp range exceeds signed 16-bit samples.
- Decode_Wave_With_Info performs the existing validated parse once and returns
  metadata only after successful decoding. It accepts source bytes, not externally
  prepared metadata that could bypass validation. Decode_Wave retains its original
  signature as a wrapper, and failure leaves caller outputs uncommitted.
- The Miles boundary uses the combined entry point instead of parsing twice.
- ADPCM output reserves the smallest of the format-derived frame estimate times
  channel count, encoded-byte nibble capacity, and the existing 16M-sample ceiling.
  The RIFF fact count is not trusted for allocation sizing. This changes capacity,
  not vector length, decoding order, sample arithmetic or final trimming.
- Per-frame append ceilings and block/predictor validation remain. An imperfect
  partial-block estimate can still grow through the existing vector behavior;
  valid content is not rejected solely because it exceeded a reservation hint.

## Later evidence

After the user lifts the build/test hold, compare decoded PCM bytes and metadata
for mono/stereo PCM, IMA and Microsoft ADPCM, partial blocks, fact trimming and
malformed/truncated inputs. Retain load-time and peak-memory measurements with
real tutorial dialogue/effects. No sample-rate reduction, voice dropping, mixer
replacement, retail modification or full-port scope restriction is introduced.
IMA comparison must cover all step-index/nibble combinations, odd-step rounding,
predictor saturation and initial-index rejection. These checks are deferred,
not reported as passed from inspection alone.
