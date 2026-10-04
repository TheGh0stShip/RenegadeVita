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

## Translation and authored conversation chains

The reference pass inspects both strings.tdb alternatives and all 55 supplied
LDD/LSD/CDB index entries. Their member hashes, index identities, record totals
and matched translation totals remain in the public receipt. No dialogue text
or audio is exported. Unsupported translation schema fails the pass.

207 flagged WAVs have direct numeric translation sound references, totaling
414 candidates across the two database alternatives. Thirty-six flagged WAVs
also have authored conversation remarks, totaling 38 remark occurrences.
Those occurrences appear in M01 (13), M04 (3), M05 (4), M06 (5), M08 (2),
M09 (5), M10 (3), M11 (1) and the global always.dbs conversation database (2).
These are overlapping reference occurrences, not a runtime play count.

The receipt retains conversation IDs/names, remark ordinals/offsets and text
IDs without copying spoken text. A translation candidate does not prove the
selected database, and an authored remark does not prove its conversation is
triggered. Direct scripted/cinematic audio and indirect twiddler references
remain separate coverage risks. Thirty-nine focused tests pass. The next
compatibility step is original playback-caller and retail post-data handling
review; physical audio and progression remain unaccepted.

## Compiled all-archive decode evidence

The current C++ provider decoder was compiled with GCC 13.3.0 C++17, `-O2`,
`-fsanitize=address,undefined`, `-fno-omit-frame-pointer` and strict warnings.
The host-only framed probe feeds actual archive bytes directly through a pipe;
it emits decode verdicts and frame totals, never PCM. Source lengths are
explicit little-endian uint32, allocation is bounded and malformed probe
frames fail. Each decoded sample vector is released before the next record.

Across all 10,241 WAV entries, 9,975 decode and 266 are rejected. The rejected
set contains the previously identified 264 oversized RIFF declarations and
one trailing chunk failure, plus `wind4r.wav`, whose decoded output is empty.
The run exits successfully with no ASan/LSan/UBSan stderr. Decoding success
does not establish waveform agreement with retail, audible timing, mixing,
memory performance or Vita playback. The rejected audio remains unchanged.

The new probe also compiles as an ARMv7 object; ELF attributes report Thumb-2
and VFP register arguments. This is compilation evidence only, not an ARM
decode run or a packaged candidate. The game runtime and Dev209 artifacts are
unchanged. No emulator or physical device was launched.

Receipt: `generated/sweeps/wave_decode.json`, bound to the WAV inventory hash,
archive hashes, decoder/probe source hashes and exact executable hash. The
consolidated register checks decoded/rejected partitions and parent identity.
All 43 focused probe/parser/register tests pass. Installed compiler macros
confirm host LP64 versus target little-endian ARMv7 ILP32 and VFP argument ABI.
Reproduce the host build/run with:

```sh
g++ -std=c++17 -O2 -fsanitize=address,undefined -fno-omit-frame-pointer -Wall -Wextra -Werror -Iport/audio/vita tools/host_wave_archive_probe.cpp port/audio/vita/renegade_wave_decoder.cpp -o build/host-wave-archive-probe
python3 -m tools.audit_wave_decoder_runtime --data "$RENEGADE_RETAIL_ROOT" --probe build/host-wave-archive-probe --output reports/generated/sweeps/wave_decode.json --stderr build/wave-decoder-sanitizers.log
```

## Original provider contract comparison

The supplied Mss32.dll is SHA-256 pinned; all four retained installation backup
copies have the same hash. Ghidra identifies the WAV-info export at 0x2110d170
delegating to 0x21115230, and 3D sample loading at 0x2110eb20 reaching
0x211283f0 and WAV inspection. Original SoundBuffer.cpp:133 calls WAV-info;
sound3dhandle.cpp uses the raw buffer, while sound2dhandle.cpp:88 uses named
sample loading with its original source length. These are different contracts.

A 32-bit Windows host probe invokes the original WAV-info export on eight
authored fixtures: valid PCM/IMA, outer size seven bytes too large, invalid
trailing content, and both conditions. All eight are accepted with payload
offsets/lengths within the authored source and unchanged sample counts. The
current native decoder accepts the two valid fixtures and rejects the other
six under ASan/LSan/UBSan. This proves a concrete provider compatibility
difference without assuming that malformed trailing content is audio data.

Receipt: `generated/retail_wave_contract.json`. The probe creates its own
PCM/IMA fixtures and exports no retail audio. Windows pointers remain 32-bit;
the stdcall signature and 36-byte output layout are explicit. Guard storage
does not establish memory safety of the legacy DLL. No game, mixer or audio
device is launched. The DLL and all decompiled output remain private; no
proprietary implementation is copied into the port. This DLL identity does
not establish a retail game.exe version.

Next: preserve bounded format/data validation while reproducing this proven
inspection behavior, with separate regression cases for truncated payloads,
duplicate chunks and fact ordering. Validate both metadata and decode paths
before a new ARM candidate. Physical audio acceptance remains open.

## Bounded provider compatibility correction

The provider now accepts an oversized outer RIFF declaration and malformed
opaque trailing content after a bounded format and complete data payload.
Strict inspection remains the default; playback explicitly selects retail
compatibility. Truncated format/data chunks, duplicate chunks and malformed
content before the validated payload still fail. Valid fact chunks after data
retain their sample-count trimming. Duration-only inspection retains its
separate metadata contract and is not permission to decode truncated audio.

The updated all-archive C++ sanitizer run decodes 10,230 of 10,241 entries,
recovering 255 of the previous 266 rejections. Ten files now reach IMA decoding
and fail on short final blocks; wind4r.wav still produces empty output. These
eleven remain open compatibility leads. No retail file was changed. The strict
metadata inventory still reports 265 header anomalies; tolerating those
declarations does not repair their on-disk metadata.

Independent payload inspection shows that all ten short-block failures are
mono IMA with 512-byte alignment and final tails of one to three bytes, shorter
than the four-byte predictor header. The empty WAV has a zero-byte PCM data
chunk. These explain the current rejection paths; original decode behavior
must be established before discarding tails or accepting empty samples.

All eight authored original-provider inspection vectors now decode through the
host provider. Forty-five focused tests pass, including truncated-payload,
duplicate-chunk, pre-data-malformation and post-data-fact counterexamples.
ASan/LSan/UBSan report no findings in the all-archive run. Fast ARM compile/link
passes all 635 actions; canonical Dev210 also passes all 661 ARM actions,
host validation, package checks and Vita3K install-only verification. Native
playback, waveform agreement and audio timing remain unverified.

The regenerated receipts supersede the pre-correction decode totals above;
the original-provider comparison receipt remains frozen baseline evidence.
The consolidated register reconciles 40,025 overlapping evidence records:
39,845 unknown, 92 missing, 43 replaced boundaries, 39 stubs and six disabled
guards. These are not unique defects or completed native acceptance gates.

The original ADPCM export at preferred VA 0x2110d0c0 delegates to 0x21125880.
A separate authored 32-bit probe now exercises one full eight-byte mono block
with zero to three trailing bytes, fixed or extended fact counts, and two
guard-byte patterns. All sixteen inspect and decode successfully. Output WAV
size follows the fact count (62 bytes at nine frames; 66/70/74 at 11/13/15).
All returned payload bytes are zero for these zero-valued fixtures, independent
of guard pattern. Receipt: `generated/retail_adpcm_contract.json`.

This proves another compatibility difference, not the correct retail waveform
or safety of the original unbounded API. The ten 512-byte retail block cases
remain unresolved. The native decoder is unchanged by this reference probe.

Dev210 identity: ELF `07603eefcdfebf042ebc69674273136cfcea800c78313ecd87b2851b35aaa177`,
SELF `c9b1bbd8aa1eebc2e965957fff6967938de85818d10680a97d12987f29f3c87a`,
VPK `12f6a244c46673fd21cb68c8a103fe12569e013dfe73890a47fcf6fc5353efbd`.
All seven packaged files match the installed title. Retail data is unchanged;
no emulator launch, physical deployment or native acceptance occurred.

## Mono IMA final-block correction

The ten remaining compressed files now decode with complete PCM SHA-256 and
frame counts matching the supplied original Miles DLL. The comparison covers
every returned sample, including the last predictor and fact-count padding;
audio payloads remain private. Provenance and scoped verdicts are retained in
`generated/retail_ima_tail_contract.json`.

The bounded decoder admits a final one-to-three-byte mono predictor only after
a complete block and with a fact count. A one-byte predictor requires its
second byte to exist in the physical source image (the RIFF pad in the supplied
files). It never decodes absent nibbles. Remaining declared frames are zero-
filled within the existing 16-million-sample ceiling. Smaller fact counts still
trim. Standalone partial blocks, stereo partial headers, missing padding and
oversized fact counts retain explicit rejection tests.

Five focused compiled-provider/probe tests pass. The full C++ archive run now
decodes 10,240 of 10,241 entries with zero sanitizer stderr. Only wind4r.wav's
zero-byte PCM payload remains rejected; its runtime meaning remains open.
Strict metadata still reports 265 header anomalies, and no retail file changed.
Dev211 passes all 634 fast ARM compile/link actions and artifact checks.
Canonical package validation is running. Native playback and timing remain
unverified; the Dev210 package described above predates this correction.
