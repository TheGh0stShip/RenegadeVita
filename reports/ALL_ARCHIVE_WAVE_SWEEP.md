# All-archive WAV metadata sweep

The read-only archive inventory counts every WAV index entry across all 31
supplied MIX/DAT/DBS archives, including duplicate names and uppercase suffixes.
The reproducible public receipt is `generated/sweeps/wave_headers.json`;
full member metadata remains privately under `build/`.

There are 10,241 entries: 10,100 in always.dat, 53 in M03.mix, nine in M06.mix,
56 in M07.mix and 23 in always3.dat. Other archives have explicit zero rows.
All 31 archive rows remain `unknown` for runtime acceptance.

Strict checks identify 265 entries in always.dat: 264 RIFF declared lengths
outside the source bounds and one chunk extending beyond its RIFF bounds.
No block findings were reported among entries eligible for block inspection.
Malformed headers can prevent block inspection and format identification;
zero block findings does not establish that every compressed block is valid.
These findings extend beyond the known eleven M01 voice candidates.

The existing original-provider metadata parser is reused without changes.
No audio is decoded, exported, converted or altered. Names, archive/member
hashes, index positions and metadata findings provide investigation leads;
mount precedence, active references, decoder fallback, duration and audible
behavior remain unverified. Loose WAVs, music and movie streams need separate
denominators. Host metadata does not establish Vita playback correctness.

Validation: 28 focused/parser counterexample tests pass, including duplicate
entries, unidentified format accounting, malformed chunks and empty archives.
Reproduce with:

```sh
python3 -m tools.audit_all_wave_headers --data "$RENEGADE_RETAIL_ROOT" --output reports/generated/sweeps/wave_headers.json
python3 -m unittest tools.test_audit_all_wave_headers tools.test_mission_wave_headers
```

The consolidated register now retains these 31 archive rows and 265 nested
findings. It reconciles archive status counts, WAV format partitions and both
finding partitions; inconsistent receipts fail generation. The register totals
39,994 overlapping evidence records, including 39,814 unknown records. This is
not a count of unique defects.

Current provider review: `Inspect_Wave` in
`port/audio/vita/renegade_wave_decoder.cpp` rejects oversized RIFF declarations
by default. `Decode_Wave_With_Info` uses that strict default. Duration-only
inspection can explicitly allow truncated data; it does not decode PCM.
The compiled `tools.test_vita_audio_provider` regression passes with ASan,
LeakSanitizer and UBSan, including strict truncated-payload rejection and the
bounded 3D oversized-RIFF case. The 34 focused inventory/parser/register tests
also pass. No provider behavior was changed.

These authored regressions prove the current rejection boundary, not retail
compatibility. Next: classify the 265 original files by actual chunk bounds,
trace their active callers and compare documented retail behavior before
considering any compatibility change. Keep malformed data bounded throughout.
