# Remaining full-port inventory

Archive-route correction: original all-top-level retail MIX availability is
implemented; actual-owner non-play sanitizer fixtures cover temp/network/M09
priority and teardown. Redundant selected/supplement indices, 161 duplicate CRC
provider groups and always3.dat provider/version semantics still need review.
See RETAIL_ARCHIVE_ROUTE_AUDIT.md. Full content/runtime acceptance stays OPEN.

## Active constraint — 2026-11-04

The user requires completion of the remainder of the port, including a complete
inventory of potentially missing items needing correction or relinking, before
any play tests. No emulator or hardware gameplay launches are permitted during
this work. Compilation, static audits and packaging validation may continue.
This supersedes the earlier plan to proceed directly to candidate play tests.

## Inventory completion criteria

Primary requirement: complete retail gameplay/content parity, as defined in
RETAIL_CONTENT_PARITY_CONTRACT.md. The translation-unit inventory below is
only a supporting technical track. Its completion cannot establish that battles,
interactions, scripted handoffs, objectives, presentation or other retail game
content survived the port. Establish the independent retail feature/sequence
catalogue and audit all existing readiness claims before claiming completeness.

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

### Retail-derived content discovery and asset admission

See RETAIL_CONTENT_BASELINE.md. Raw retail campaign flow and every indexed
entry are collected independently of port selection; unknown bindings, verbs,
structural paths and unparsed formats remain visible. Fifty manual-derived
feature seeds are tracked separately, all OPEN. The complete sequence/feature
catalogue and shared semantic admission gate are still unfinished.

A real required M09 archive is absent from the Steam-linked data root. A
matching reference has it; all 30 common archive hashes match. General manifest
and repair validation now default to campaign requirements derived from retail
campaign.ini, and reject missing maps/movies before repair copies. The explicit
demo helper retains its tutorial-only profile and disclaims campaign validation.
This closes one concrete file-availability blind spot, not content parity.

### Configured native source selection

The dev246 CMake compile database selects 632 original translation units for
RenegadeVitaA31 out of 1,490 released units. The inventory tool now accepts
`--compile-commands` and exact `--target` arguments and records matching object
outputs plus the database hash. It also retains hashes of the actual staged
inputs and refuses ambiguous case-folded matches. The current tree has zero
original case collisions; 336 selected units differ from their released bytes
through staging. One additional staged source, commando/loadingscreen.cpp, is
explicitly traced to LoadingScreenClass extracted from Commando/combatgmode.cpp
by the shared-loadingscreen patch. No staged input remains unmapped in this
target. Other targets and manifest comments cannot establish selection.
Full direct ARM compilation/linking now passes, with selected-owner symbol
retention in DEV246_NATIVE_LINK_CLOSURE.md. Complete symbol/functional-owner
classification remains open. Generated local inventory:
reports/generated/remaining_original_sources.json.

### Triangle-fan submission correction

Native Draw_Sorting_IB_VB previously counted fan indices but submitted them as
a strip. It now expands fans into lists, validates the source window separately
from expanded output capacity, and preserves anchor/winding and rebasing.
Production-block sanitizer checks cover translation, invalid ranges and every
16-bit polygon count's capacity decision. The changed production boundary
compiles for ARMv7 with VFP-register arguments, and its sorting submission is
retained in the successfully linked native ELF. Existing callers use list/strip;
no visual acceptance claim.
See research round 27 for the original source/caller evidence.

### Installed dependency identity

The earlier FFmpeg shortcut could reuse archives after compiler/SDK changes.
The fix computes mandatory recipe/toolchain/SDK identity before local
reuse, verifies installed content hashes, and extracts a fresh verified source
archive for each rebuild. Shared cache use remains optional. Source tests pass;
the revised dependency rebuild and unchanged installed reuse now pass. Its five
archive hashes match the successful native link. Receipt covers 173 files and
actual input identity is retained. Research round
20 records the original defect; independent review is retained separately.

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
Corrected: FFmpeg and its Bink caller use scoped int-sized enums; the dependency
was rebuilt with the v4-int-enums stamp, transform sentinel checks pass, and
the actual Bink consumer compiled for ARM. Engine enum ABI remains unchanged.
Archive attributes and exact hashes are retained in research round 20. This
does not establish physical A/V correctness or restore missing subtitles.

### Subtitle owner restoration and enum seam

The FFmpeg-facing Bink TU is compiled with int-sized enums. Its current engine
calls use opaque pointers/plain scalar APIs. Do not include or construct the
original SubTitleManagerClass/Render2DSentenceClass directly there: those engine
classes must retain the engine's short-enum layout. Restore the three original
subtitle owners through a separately compiled engine-ABI adapter exposing only
opaque manager handles, FontCharsClass pointers and explicit 32-bit tick values.
Keep Create/Process/Render/destruction ownership, original 60-Hz timing and rooted
read paths. Parser EOF/malformed time handling also needs review before linkage;
the released Get_Sub_Titles loop does not break when Get_Next_Line returns NULL.

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
not appear absent merely because their paths use a variable. Configured-target
evidence now comes from the dev246 compile database; linking/functional owner
classification remains open.

`Combat/statemachine.cpp` is a reviewed exclusion: its only code is the include
of `statemachine.h`; boss objects use the header's template implementation.
Adding this empty translation unit would restore no missing out-of-line owner.
Other unmentioned sources remain unclassified rather than presumed unnecessary.

1. Preserve failed canonical dev246 (session 17626) and successful direct native
   session 54511 as separate evidence. Revised FFmpeg session 45286 and verified
   unchanged reuse session 7212 are terminal PASS; retain their exact identities.
2. Establish the full original-source and linked-owner inventory, including
   stubs and intentionally excluded subsystems.
3. Resolve missing/replaced-owner findings in dependency order and retain
   focused compile/static evidence for each correction.
4. Reconcile all remaining full-port gaps and package closure before lifting
   the play-test hold. Runtime and physical acceptance remain unproven during
   the hold; source completion cannot itself establish those gates.
