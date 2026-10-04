# S5 script layer — complete slot/unit denominator in progress

## Named parameter-read inventory — 2026-10-04

The 1,636 live original script bodies contain 1,201 lexically identified
parameter reads: 1,146 literal names match their hash-verified descriptor,
35 use literal integer indices, and 20 literal names are absent. No computed
argument or unresolved call parse was found within this body denominator;
helper/inherited/macro paths remain an explicit coverage risk.

The 20 absent-name call sites belong to eight scripts. Five call sites have
direct authored bindings in the 27-map receipts: three M05_Park_Controller
artillery names, M00_Damage_Modifier_DME's Killable_ByNotStar spelling and
M00_Play_Sound_Object_Bone_DAY's Offset. The damage script occurs directly in
M03 and M13; the sound script occurs directly in M01–M11 and M13. Other absent
names occur in toolkit action/trigger scripts and GTH test scripts without
direct authored occurrences located by this join. An empty map set does not
prove runtime attachments or editor references cannot reach them.

These are original-source mismatch leads, including original description
truncation/name quirks, not authorizations to change behavior. Original
Get_Parameter_Index compares names without case but preserves underscores,
uses only 511 descriptor bytes and returns -1 when no name matches. Literal
indices still need supplied-value bounds and original overload/conversion
checks; no callback execution is claimed.

`python3 -m tools.audit_script_parameter_reads` reproduces source line, method,
literal name/index and direct authored map sets from the verified live registry.
Receipt: `reports/generated/sweeps/script_parameter_reads.json`. Twenty focused
tests pass, including comments/strings, adjacent literals, case/underscores,
computed nested arguments, index retention and consolidation partition checks.
The register retains 44,620 overlapping records, with 44,356 unknowns. All new
rows remain unknown behavior. Original owners, source hashes and parent receipt
identities are retained; no runtime source or compiled artifact changed.

## Live parameter descriptors and all-map positions — 2026-10-04

All 1,636 live registry parameter-description hashes match the literal original
source descriptions. All 27 map receipts match the retained archive/database
identities. The 8,314 authored bindings partition into 3,287 equal positional
counts, 5,017 excess-value leads, one fewer-value lead, six unrecorded startup
parameter strings and three unregistered names already identified in M11.
Extra values frequently occur on scripts declaring an empty descriptor;
this is not evidence of thousands of broken scripts.

The original name parser uses a 511-byte description prefix and does not visit
a final empty comma field. Independent source inspection corrected seven
apparent M07_Custom_Activate shortages: its description ends with a comma,
but it names only three parameters. A regression case preserves that behavior.
No normalization of misspelled names or underscores is introduced.

The remaining shorter binding is M03_Killed_Sound on definition 82050391: one
serialized value for Officer and Location. Its original Killed callback reads
both values and sends LOCATION/TROOP_KILLED events to object 2018061. Original
Get_Parameter returns empty text outside supplied positions. Callback activation,
integer conversion and mission impact require runtime evidence; no default or
retail data correction is invented.

`python3 -m tools.audit_live_script_parameters` reproduces the receipt from
private all-map bindings, public retail/live registry receipts and pristine
source declarations. Public JSON is `reports/generated/sweeps/live_script_parameters.json`;
it preserves shape/provenance, not authored parameter values. Nineteen focused
tests pass, including byte bounds, comma semantics and partition rejection.
The gap register includes 43,419 overlapping records, with 43,155 unknowns.
All parameter-map rows remain unknown behavior. Type coercion, named callback
lookups, computed attachments and native execution remain open. Runtime source
and compiled artifacts are unchanged; no emulator or device action occurred.

Live host index lookup verifies 1,636 script factories. Across27 hash-matched map
receipts,8,311/8,314 authored bindings match those factories. Three M11 spawner
names remain unmatched; their source declarations are absent from the supplied
EA Scripts tree. Retail DLL behavior and spawner activation remain open.
The49 selected-unit source candidates absent from the live registry are inside
original constant-disabled branches. None of this accepts script creation,
parameter semantics, callbacks or ARM/physical execution. Seventeen focused
tests pass. See [live registration evidence](LINK_REGISTRATION_SWEEP.md).

ARM symbol reconciliation finds retained function candidates for all 202
staged command-slot assignments. Each row carries demangled symbol, address
and symbol-type metadata; the input symbol file is hash-pinned. Matching uses
exact unqualified function-name prefixes and retains overload alternatives.
Data symbols and qualified member functions do not satisfy this comparison.
Eight authored slot/table tests pass. This closes the missing-function-symbol
question for these lexical assignments only; signature/ABI compatibility,
active platform branches, stub bodies and runtime initialization remain open.

The inventory contains every original ScriptCommands function-pointer slot:
202 rows, each with original/staged assignment candidates and direct shipped
script-owner candidates. All 202 have exactly one lexical staged assignment.
Direct declared bodies in Scripts.dsp use 179 of these commands. None of
these counts proves non-stub behavior, active platform branches, correct ABI
layout or initialized function pointers at runtime; all statuses remain unknown.

All 45 Scripts.dsp C++ units are enumerated against the retained ARM target.
44 are selected; DLLmain.cpp is unselected. The native static-registration
path requires separate initialization/link evidence rather than blindly
including the Windows DLL entry unit or declaring it irrelevant.

Seven authored slot/table tests pass. The slot extractor confines discovery
to the ScriptCommands structure, ignores comments and rejects a missing
structure explicitly. Rows retain source lines, identities, input hashes and
parent build-inventory identity. Repeated generation reproduces exactly.

Run `python3 -m tools.audit_sweep_scripts --symbols <matching-symbol-file> --link-inventory
reports/generated/sweeps/link.json --output <inventory.json>`.

Next: complete command body/guard classification, default-argument CI checks,
retail parameter matching across every map, original misspellings and MSVC
semantic dependencies. Indirect/helper/global calls remain open coverage risks.
The 179-command count is broader than campaign-only counts and does not
contradict them. Full S5 and native mission acceptance remain incomplete.
