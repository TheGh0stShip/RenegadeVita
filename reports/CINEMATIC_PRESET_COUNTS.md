# Cinematic preset counts (retail MIX scan)

Source: `tools/renegade_cinematic_dependency_scan.py` `MixArchive` over the
Vita3K retail Data copy. Counts all `.txt` entries per mission MIX; presets are
unique (case-insensitive) `Create_Real_Object` names, `;` comment lines excluded.
Host scan only; no build, no Vita evidence.

| Mission | .txt files | .txt bytes | Unique presets |
|---|---:|---:|---:|
| M00_Tutorial | 0 | 0 | 0 |
| M01 | 18 | 50067 | 16 |
| M02 | 54 | 175829 | 21 |
| M03 | 12 | 14373 | 2 |
| M04 | 1 | 4648 | 4 |
| M05 | 5 | 14860 | 6 |
| M06 | 2 | 14450 | 7 |
| M07 | 0 | 0 | 0 |
| M08 | 10 | 23999 | 9 |
| M09 | 9 | 16606 | 2 |
| M10 | 0 | 0 | 0 |
| M11 | 8 | 19671 | 3 |
| M13 | 22 | 80443 | 27 |

## Warm-up cost flags

- M02: largest by far (54 files, ~172 KiB text, 21 presets).
- M13: most unique presets (27), second-largest text (~79 KiB).
- M01: 16 presets, ~49 KiB text.
- M00, M07, M10: no cinematic `.txt` in their MIX.
