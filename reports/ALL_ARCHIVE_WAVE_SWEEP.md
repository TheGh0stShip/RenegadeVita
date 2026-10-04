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
compatibility.

## Actual source-bound follow-up

An independent, bounded metadata walk ignores the outer RIFF length solely to
inspect physical chunk placement. All 265 flagged files contain one format and
one data chunk; every declared data payload fits within the actual source.
Each walk subsequently reaches trailing bytes that fail chunk bounds. There
are 12–3,312 bytes after the data payload. Of the 264 oversized outer lengths,
141 exceed the source by seven bytes and 123 by eight. One file has an exact
outer length but still fails the trailing chunk check. No file was repaired,
decoded or modified.

Filename prefixes span m00 (178), m01 (16), m04 (3), m05 (15), m06 (8), m08 (2),
m09 (2), m10 (3), m11 (1), mxx (36) and cor (1). These are naming evidence,
not established mission usage. In particular, m00 includes shared voices and
does not prove that all 178 files are tutorial dependencies.

The staged original `SoundBufferClass::Load_From_File` reads the actual file
size and calls `Determine_Stats`; its patched bounded statistics provider can
also encounter the trailing-chunk failure. The original 3D handle passes the
actual allocation length to the bounded sample-file provider. Thus duration
and playback both require compatibility investigation; the duration truncation
flag alone does not solve this trailing-content case.

Thirty-seven inventory/parser/register tests pass, including intact data with
an oversized outer length, truncated data, short trailing headers and final
odd padding. Next: reconcile definition/conversation references to these exact
files and establish retail handling of post-data content before changing the
provider. Physical playback and audio timing remain open.

## Sound-definition reference reconciliation

Every archive index entry named objects.ddb was inspected independently. The
supplied archive set contains one such database in always.dbs: 15,146 total
definitions, including 9,509 nonempty sound filename definitions. Of the 265
flagged WAVs, 215 have one filename-basename candidate each; 50 have none.
All database alternatives are retained rather than merged into assumed mount
precedence. Case-insensitive basename matches are explicitly distinguished
from exact filename matches. Authored directory strings remain private;
public provenance retains their hashes and definition IDs/names/offsets.

This establishes authored references for 215 files, not executed playback or
per-mission usage. Unmatched filenames may still occur in direct cinematic,
script or other data paths; they are not classified as unused. Definition
duplicates are retained, and the matcher does not choose a winning provider.
Thirty-eight focused tests pass. The exact retail post-data handling and
conversation/caller chains remain the next compatibility evidence requirements.
