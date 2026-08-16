# Crash symbolication index

| Candidate | Physical finding | Exact evidence location |
|---|---|---|
| A3.1 | null WWAudio singleton during static-audio save/load | historical reports and dist artifacts |
| A3.1.1 | null Font3D release in render-enabled HUD initialization | historical reports and dist artifacts |
| A3.1.2 | uninitialized no-HUD resources reached by HUD Think | historical reports and dist artifacts |
| A3.1.3 | lifecycle passed but zero interactive geometry | `reports/milestones/A3.1.3-HARDWARE-INTERACTIVE-LIFECYCLE-VALIDATION.md` |
| A3.1.4 | no crash; physical texture/input fidelity gaps | `../../baselines/A3.1.4/` raw log and observation |
| A3.2-dev1 | physical C2-12828-1; matching dump/ELF/map place PC `0x810DACB6` in `HumanStateClass::Update_Animation`; the original `_weapon_style_names` initializer had a missing Beacon/EMPTY comma, leaving the final legal style null | private evidence archive, matching candidate symbols, and `port/patches/combat-a35-humanstate-weapon-style-table.patch` |

Always record module load bias and use the exact candidate ELF/map/symbols for
addresses from a returned `psp2core` dump.

`tools/symbolicate_vita_dump.sh` accepts a gzip-wrapped Vita `.psp2dmp`, the
matching ELF/map/symbol list, and an output report path. It records SHA-256
provenance, safely decompresses only to a temporary file, and asks host GDB for
the thread backtraces and registers. It does not guess a candidate identity:
never run an A3.2 dump against an A3.1 ELF (or vice versa).

The wrapper also writes a bounded `.core-notes.json` inventory using
`tools/parse_psp2_core.py`. It parses ELF note headers and the observed
`THREAD_INFO` v4 record envelope, including verified thread IDs, names, and PCs,
without emitting raw notes. `THREAD_REG_INFO` fields remain explicitly
unavailable until their private Sony layout is independently verified; the parser
records this with an explicit `thread_reg_info.status` marker.

`tools/parse_psp2_core.py` now emits parser metadata and deterministic input
identity for reproducibility:
`schema`, `parser_version`, `input_identity.{sha256,byte_count}` for the
gzip-wrapped dump, `payload_identity.{sha256,byte_count}` for the decompressed
ELF payload, and `notes_inventory` with `count` and `types`. Synthetic fixtures in
`tools/fixtures/psp2_core/` cover malformed input, truncated headers, unknown
note owners, multi-note inventory order, and byte-stable repeated runs.
