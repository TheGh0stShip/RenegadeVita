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

Next: reconcile this supplemental denominator into the consolidated gap
register, then inspect original decoder behavior for malformed RIFF lengths
using authored regression cases before considering a provider change.
