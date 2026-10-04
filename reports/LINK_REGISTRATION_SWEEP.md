# S3 link and registration closure — inventory in progress

## All-map level persistence reconciliation — 2026-10-03

The 27-map LSD/LDD metadata inventory contains 83,622 candidate simple-factory
envelopes using 33 persistence chunk IDs. Every ID has a retained Dev220 ARM
template Load symbol and a matching original host registry lookup. No missing
ARM symbol or host lookup was found in this scoped denominator. All 33 behavior
rows remain unknown. No runtime source or binary changed.

The detector requires sibling OBJPOINTER `0x00100100` and OBJDATA `0x00100101`
ancestries with equal counts and four-byte pointer-token payloads. Arbitrary
leaf chunk IDs are not treated as factory requests. Aggregated metadata cannot
prove sibling ordering within each instance. Six focused tests and two existing
chunk-parser tests pass; retained metadata parser hashes match current source,
and all 140 ARM/host template IDs agree. No malformed candidate envelope was
found in the supplied metadata.

Reproduce with `tools/audit_level_persist_closure.py`; evidence lives in
`reports/generated/sweeps/level_persist_closure.json`, including input hashes,
map/member provenance, counts and source classes. The remaining denominator
includes objects.ddb, saves, manual/non-template factories, opaque subsystem
payloads and definition class IDs. Actual Load/Save behavior and physical Vita
registration remain unverified. This receipt supplements the S3 ledger; it does
not change the consolidated ARM behavior classifications.

## Original host persistence lookup — 2026-10-03

The retained ASan/UBSan host runtime resolves all 140 template persistence
factory IDs through original `SaveLoadSystemClass::Find_Persist_Factory` after
static initialization. Each returned factory's virtual `Chunk_ID()` matches
the requested ID. An absent-ID control returns null. Two symbol-parser tests
pass. The reproducible driver and public count/class/ID receipt are
`tools/probe_host_persist_registry.py` and
`reports/generated/sweeps/host_persist_registry.json`.

The host ELF SHA-256 is
`bb685247f73b1e85377e9f209c55586d06a159d55c9021254873f5145c47b5a2`.
No runtime source changed; the existing compiled host and Dev220 ARM artifacts
remain unchanged. Debugger logs stay under the private build tree. Leak checking
is disabled for the debugger run; prior sanitizer tests are separate evidence.
This proves host ID lookup, not class identity, Load/Save behavior, other
registration forms, retail closure, or ARM/Vita execution. S3's ARM behavior
statuses remain unknown. Next: reconcile all-map retail chunk IDs and extend
execution evidence to other original registries.

## Header and installation discovery — 2026-10-03

Registration discovery now scans 2,150 source files: 1,947 staged files and
203 port files, including headers and fragments. The translation-unit
denominator remains 837 staged units. Dev220 selects 605, and its matching map
mentions all 605 objects. These observations do not prove section retention.

The inventory contains 2,215 registration candidates: 1,745 script declarations,
140 persist factories, 58 definition factories, 41 network declarations,
194 console installations, 17 prototype-loader installations, 10 allocated
game-mode installations, eight borrowed game-mode installations and two manual
factory-registration calls. There are 1,878 defined-symbol candidate matches.
Every registration candidate retains unknown behavior and unverified execution.

Header membership in a compiled target is unknown; it is no longer counted as
an unselected translation unit. One header script candidate is retained with
unknown membership. Macro declarations and inactive branches remain candidates,
not additional proven runtime registrations. Same-line candidates have distinct
column-based identities, avoiding accidental row collapse.

Four prototype installations are present both in unselected original init.cpp
and the selected native startup replacement. Borrowed game-mode installations
are also present in port startup. This establishes source routes, not executed
installation or complete equivalence. The adjacent D3D variant separately
selects the original DX8 renderer owners; it was inspected without modification.
Registration discovery applies to either graphics path.

Twenty-one focused discovery/consumer/consolidation tests pass. The W3D consumer
receipt was regenerated against the new link inventory, preserving its 98 chunk
rows and reviewed consumer evidence. Consolidation rejects stale dependent
identities. The gap register now contains 40,424 overlapping records, including
40,160 unknowns; these are not counts of distinct defects. Runtime source and
the retained Dev220 host/ARM binaries are unchanged by this tooling batch.

Remaining risks include computed arguments, alternate/template and expanded
macro forms, raw strings, header inclusion, active branches, discarded sections,
constructor execution and retail factory IDs. Next: probe live original factory
lookup on host, then reconcile numeric IDs across all retail maps. Host results
will remain separate from physical Vita/PSTV acceptance.

The retained ARM symbol inventory now includes 140 numeric persist Load
methods, with class, chunk ID, symbol/address/type evidence. This supports
all-map retail chunk-ID reconciliation without evaluating symbolic constants
from source or mistaking source declarations for linked methods. Function
presence still does not prove factory initialization or runtime registration.

Definition/network macro expansion adds 57 definition and 28 network object
symbol matches, bringing defined-symbol candidate matches to 1,861. The
unmatched ShakeableStaticPhys definition registration at source line 80 is
inside original `#if 0`; its persist factories have retained symbols.
Eleven unmatched network candidates are all in unselected Commando units:
clientbboevent, consolecommandevent, csconsolecommandevent, donateevent,
godmodeevent, moneyevent, requestkillevent, scoreevent, suicideevent,
vipmodeevent and warpevent. Runtime callers and mode/retail requirements remain
open; these are closure leads, not approved exclusions or compatibility proof.

Of 108 unmatched script candidates, 49 occur in selected units: 44 Test_BMG,
four Toolkit and one Test_GTH. Source inspection places them inside original
`#if 0` regions (Test_BMG 80–1156, Toolkit 151–301, Test_GTH 261–368).
The other 59 occur in unselected units. No port-induced script omission is
established by these selected-unit misses. Retail binding reconciliation is
still required; original disabled code is not blanket proof of irrelevance.
Five tests pass with custom definition-variable and network-macro name cases.

Retained Dev209 symbol evidence now matches 1,636 script registrar objects
and all 140 persist-factory candidates. Expected script names follow the
original REGISTER_SCRIPT macro (`_ClassRegistrant`); persist names come from
the declared variable. Of 1,744 script candidates, 108 lack these exact symbol
matches and require classification. Defined storage does not establish executed
initialization, registration success or gameplay. All statuses remain unknown.
Definition/network symbol expansion and discarded-section analysis remain open.
The symbols file is hash-pinned. Five tests pass, including undefined-symbol
rejection and preservation of uncertainty despite defined registrar storage.

The staged-source denominator contains 837 C/C++ translation units. The
retained Dev209 Ninja target selects 604; its link map mentions all 604 object
files. The remaining 233 units require classification, including potential
non-runtime sources. Selection and map mentions do not prove retained code,
static initialization, factory registration or functional behavior.

The upstream denominator now includes all 1,490 C/C++ units under Code,
including tools and editor code; 654 have no case-insensitive relative-path
staged counterpart. Case-insensitive matching retains all candidates rather
than silently resolving ambiguous names. These are unknowns, not exclusions.

Source discovery also retains 1,981 registration candidates: 1,744 scripts,
140 persist factories, 58 definition factories and 39 network factories.
Comments and ordinary string/character literals are masked with offsets
preserved. Inactive preprocessor branches remain candidates. Header/manual,
alternate/template registration forms, raw strings, console functions, game
modes and prototype registration still require discovery. Macro names and
symbolic IDs are not proof of retained initialization or numeric ID coverage.
Three authored tests pass, covering lexical masking and unstaged/case mapping
alongside the original target/map distinction test.

All staged, upstream and registration rows remain unknown. The generator retains source identities and the
map hash without publishing the raw map or private build paths. Current source
hashes do not establish that they match the original Dev209 build inputs.

Reproduce with `tools/audit_sweep_link.py --build <configured-build> --map
<matching-map> --symbols <matching-symbols> --target RenegadeVitaA31 --output <output.json>`. The authored
test separates target membership from map mentions, retains discarded-section
mentions as uncertain, and verifies deterministic rows and unique identities.

Next: classify upstream units absent from staging; expand static/manual
registrar discovery; distinguish discarded and retained sections using matching ARM
symbols and map; cross-check factory IDs against every retail map. This sweep
is incomplete and does not authorize exclusion of any original behavior.
