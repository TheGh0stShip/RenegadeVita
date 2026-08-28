# Vita open-source reuse plan

Updated: 2026-08-25. This is a tooling and provenance plan for the active
A3.5 correctness work. It does not import external source trees, retail data,
proprietary SDK material, or emulator evidence into the port.

## Pulled reference set

`tools/vita_open_source_references.yml` pins the external projects that are
useful to the current broad blockers: loading-screen correctness, black or
wrong textures, skinned-material regressions, crash-dump analysis, build
iteration cost, SceAudio smoke testing, and optional Vita3K regression loops.
The 2026-08-25 fetch materialized 14/14 references and recorded the exact
external cache paths in
`reports/generated/vita_open_source_reference_fetch.json`.

Run:

```bash
python3 tools/fetch_vita_open_source_references.py
```

The default cache is `/tmp/renegade-vita-reference-cache`; override it with
`RENEGADE_VITA_REFERENCE_CACHE` or `--cache`. The generated fetch report is
`reports/generated/vita_open_source_reference_fetch.json`.

## Integration rules

- Direct implementation remains owned by the EA/Westwood engine plus narrow
  Vita platform boundaries.
- GPL-2.0-only and unknown-license projects are study-only and cannot
  contribute copied source.
- Vita3K is emulator-only. It may shorten compile/run iteration, but cannot
  accept physical Vita gates.
- vitaGL references inform diagnostics, flags, cache behavior, and state
  boundaries. They do not replace WW3D traversal or Renegade resource owners.
- Crash-parser references are cross-checks for retained dumps; matching ELF,
  map, symbols, and candidate hashes remain mandatory.

## Immediate uses

1. Use the fetched vitaGL/Daedalus/SRB2Kart/Alisa references to define
   renderer A/B diagnostics for texture upload, shader cache, texture cache,
   FBO orientation, and loading-screen logical-to-native scaling.
2. Use the Vita3K CLI reference and `tools/run_vita3k_candidate.py` only for
   emulator smoke loops when a Vita3K executable is supplied.
3. Use vita-crashdump, vita-parse-core, and libvcp references to improve the
   in-tree PSP2 dump parser only after comparing their output on a retained
   candidate-matched dump.
4. Use VitaSDK buildscripts/toolchain references to keep fast builds pinned and
   to improve ccache/Ninja diagnostics without changing canonical acceptance.
5. Use Sokol/VitaSDK audio references only as an independent SceAudio smoke
   oracle if dev48 still proves inaudible dialogue with nonzero stream and
   category-volume counters.

## Tested tooling

- `python3 -m unittest tools.test_vita_open_source_references -v` passes.
- `python3 tools/fetch_vita_open_source_references.py` fetched every pinned
  reference into `/tmp/renegade-vita-reference-cache`.
- `python3 tools/run_vita3k_candidate.py --dry-run ...` produced a dev48
  emulator-only receipt with `physical_acceptance=false`.
