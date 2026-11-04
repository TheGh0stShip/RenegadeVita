# Remaining full-port inventory

## Active constraint — 2026-11-04

The user requires completion of the remainder of the port, including a complete
inventory of potentially missing items needing correction or relinking, before
any play tests. No emulator or hardware gameplay launches are permitted during
this work. Compilation, static audits and packaging validation may continue.
This supersedes the earlier plan to proceed directly to candidate play tests.

## Inventory completion criteria

This inventory is OPEN, not a claim of exhaustive closure. Reconcile every
released project translation unit against selected sources and final linked
symbols. Classify exclusions as obsolete/tool-only, replaced platform boundary,
profile-specific, or missing engine functionality, with evidence for each.
Check weak/no-op compatibility owners as well as undefined symbols: successful
linking alone cannot establish functional completeness.

Track each finding with its original owner, current selection/reachability,
required correction, compile/link evidence and unresolved acceptance gate.
Cover all campaign missions and scripts; persistence and progression; renderer
and resource lifetime; frontend/HUD/input; audio/video; networking/provider
boundaries; filesystem/platform lifecycle; packaging and diagnostics. Retail
metadata audits must cover asset, definition, script, conversation and resource
references without redistributing retail data.

## Existing evidence to reconcile

### Configured native source selection

The dev246 CMake compile database selects 632 original translation units for
RenegadeVitaA31 out of 1,490 released units. The inventory tool now accepts
`--compile-commands` and exact `--target` arguments and records matching object
outputs plus the database hash. Other targets and manifest comments cannot
establish selection. Final compilation, symbol retention and functional owner
classification remain separate open steps. Generated local inventory:
reports/generated/remaining_original_sources.json.

### Triangle-fan submission correction

Native Draw_Sorting_IB_VB previously counted fan indices but submitted them as
a strip. It now expands fans into lists, validates the source window separately
from expanded output capacity, and preserves anchor/winding and rebasing.
Production-block sanitizer checks cover translation, invalid ranges and every
16-bit polygon count's capacity decision. The changed production boundary
compiles for ARMv7 with VFP-register arguments; full ARM linking remains in
progress. Existing callers use list/strip; no visual acceptance claim.
See research round 27 for the original source/caller evidence.

### Installed dependency identity

FFmpeg's installed-prefix shortcut checks configuration stamp and archive
existence before computing the optional full cache key. Toolchain/SDK drift
can therefore reuse old files under the same stamp. Retain and compare complete
recipe/toolchain identity on that path; research round 20 records the evidence.

### Canonical host harness closure

dev246 stopped at A22 host linking. Native manifests select PointGroup,
AnimatedSoundMgr and statistics owners; the render-target cleanup owner is in
a31_gameplay_boundary.cpp. The retained A22 graph now links the three original
owners, with an isolated host audio-device boundary that aborts playback and a
host offscreen-target cleanup boundary. Host link and headless asset checks
PASS; broader canonical host graph closure remains open. This failure was
host-only evidence, not proof those engine units were absent from the Vita
target. See research round 9.

### Audio effects coverage

Research round 3 additionally confirms empty `AIL_set_3D_orientation` and
`AIL_set_3D_velocity_vector` implementations with original Sound3D/Listener
callers. Audit provider capability, listener orientation ownership and Doppler
units before implementing; positional attenuation alone is not full 3D closure.
Round 4 refines this: original Sound3D already supplies listener-space positions
and Listener initializes a fixed basis. Do not classify the ignored fixed basis
alone as broken camera-relative stereo or add a duplicate camera rotation.

`port/audio/vita/renegade_miles_provider.cpp` implements
`AIL_set_3D_sample_effects_level(H3DSAMPLE, F32)` as an empty function. Original
caller/provider selection and required room/effect behavior need tracing; the
presence of the symbol does not close its semantic contract. Research round 2
found an analogous gap in the alternative browser port, not a proven solution.

### Confirmed dependency finding — FFmpeg transform enum

dev246 dependency compiler output reports `libavutil/tx.c:323` converting
`TX_TYPE_ANY` (2147483647) into `enum AVTXType` as 255; comparisons at lines
436, 578 and 758 become constant. Pinned FFmpeg `libavutil/tx_priv.h` defines
the wildcard outside the enum as INT32_MAX. This is a demonstrated arithmetic
defect under the installed target compiler, not a gameplay observation.
Open action: determine a consistent enum ABI for FFmpeg and every caller,
check public structure layouts and archive ELF attributes, then rebuild the
dependency with an invalidated configuration stamp. Do not change flags in
the middle of the currently live build or infer physical audio correctness.

- `tools/check_excluded_original_sources.py`: excluded-source symbol comparison.
- `tools/verify_source_inventory.py`: manifest/report identity checks.
- `reports/generated/compile_closure.json`: prior compile closure findings.
- `reports/generated/sweeps/`: campaign script, persist, definition and missing
  caller findings; regenerate or qualify stale evidence against current main.
- `reports/KNOWN_GAPS.md` and `reports/CAPABILITY_MATRIX.md`: reconcile historical
  source/build/runtime claims without promoting them to current acceptance.

## Execution order

Current audit findings: all 1,490 released C/C++ units are enumerated in
`generated/remaining_original_sources.json` with original project membership.
Known CMake script-root prefixes are normalized so selected mission files do
not appear absent merely because their paths use a variable. This is lexical
evidence only; selected-target evidence remains pending canonical configure.

`Combat/statemachine.cpp` is a reviewed exclusion: its only code is the include
of `statemachine.h`; boss objects use the header's template implementation.
Adding this empty translation unit would restore no missing out-of-line owner.
Other unmentioned sources remain unclassified rather than presumed unnecessary.

1. Finish observing the live dev246 canonical build (session 17626); preserve
   its actual outcome. Do not restart while it remains live.
2. Establish the full original-source and linked-owner inventory, including
   stubs and intentionally excluded subsystems.
3. Resolve missing/replaced-owner findings in dependency order and retain
   focused compile/static evidence for each correction.
4. Reconcile all remaining full-port gaps and package closure before lifting
   the play-test hold. Runtime and physical acceptance remain unproven during
   the hold; source completion cannot itself establish those gates.
