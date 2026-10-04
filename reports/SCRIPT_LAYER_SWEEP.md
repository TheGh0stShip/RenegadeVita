# S5 script layer — complete slot/unit denominator in progress

## Shared save-data boundary and destinations — 2026-10-04

All 45 shipped script units contain eight explicit Commands->Load_Data call
sites; all eight argument lists parse completely. They are retained separately
from cinematic round-trip evidence. `Combat/scriptcommands.cpp::Load_Data`
reads Cur_Micro_Chunk_Length bytes into the supplied destination; the size
relationship is checked by WWASSERT, with no explicit runtime rejection before
the read. Assertion configuration and original chunk transport need independent
verification before claiming malformed fields are bounded.

The cinematic saved-command caller tests len < 200, without requiring positive
length, initializes neither its local character buffer nor explicit termination,
then passes it to Add_Control_Line/strdup. A shared boundary fix must validate
destination capacity, while the caller must handle length and string termination.
The current sanitizer fixture validates normal round trips and parser strings;
it does not exercise malformed saved fields or the real shared Load_Data owner.

`python3 -m tools.audit_script_load_destinations` reproduces the eight source
locations, size/destination expressions and parser/source/shared-owner hashes.
Public receipt: `reports/generated/sweeps/script_load_destinations.json`.
Twenty-two focused parser/consolidation tests pass. The register now contains
45,927 overlapping records, with 45,663 unknowns. Runtime source/artifacts are
unchanged; no malformed save, device or emulator execution occurred.

Next fix cluster: original shared boundary rejection plus deterministic cinematic
command-buffer handling, focused malformed-field host regressions, retained
sanitizers and matching ARM compile/link. Valid disk chunk widths and original
save ordering must remain unchanged. Broader indirect/auto-variable load routes
remain outside the eight explicit script-call denominator.

## Original cinematic parser sanitizer fixture — 2026-10-04

The original Test_Cinematic implementation now passes seven mutable-input
parameter cases under ASan/UBSan: empty input, surrounding whitespace, a quoted
comma, empty comma fields, an unterminated quote, repeated end-of-input reads,
and a 600-character parameter. Two simultaneous script instances also retain
independent parameter cursors. Constructor, parser and destructor run directly;
the tests do not replace the parser with a reimplementation.

The combined fixture also passes the existing original save/load camera, clock,
slot and control-command checks, plus pending audio executing once after
save/load. Chunk transport and playback callbacks are synthetic fixture seams.
This bounded test does not establish arbitrary malformed-save handling, full
command dispatch, retail movie/audio synchronization or cinematic presentation.

Reproduce with `python3 -m unittest tools.test_cinematic_save`. Set
RENEGADE_CINEMATIC_PROBE_DIRECTORY to a private build directory to retain the
matching executable, compiler/runtime logs and receipt. The public sanitized
receipt is `reports/generated/sweeps/host_cinematic_parser.json`; it binds the
host executable and seven source hashes. Host LP64 behavior is distinct from
ARM ILP32 serialization, alignment and physical acceptance.

Only the host fixture/harness changed. Original runtime source and the Dev220
ARM candidate are unchanged. No device, emulator or adjacent D3D modification
occurred; native acceptance remains open.

## Parameter syntax beyond live bodies — 2026-10-04

All 45 Scripts.dsp translation units and all 45 supplied Scripts headers now
have a separate lexical parameter-method denominator. It contains 1,285 syntax
candidates: 1,201 reconcile with the prior live-body inventory and 84 fall
outside it. Fourteen are definition candidates; the remaining 1,271 include
calls and declarations and must not all be claimed as executable calls.

The 84 additional candidates include 51 in Test_Cinematic.cpp: 29 next-parameter,
19 first-parameter and three command-parameter expressions, including parser
definitions. The other 33 are shared scripts.cpp/parser or header syntax.
Get_Command_Parameter and its first/next wrappers consume cinematic commands,
not ScriptImpClass's named descriptor arguments. Their runtime bounds and
semantics remain a separate requirement even when script descriptors match.

`python3 -m tools.audit_script_parameter_surface` reproduces this denominator
from pristine source and the pinned read inventory. Public receipt:
`reports/generated/sweeps/script_parameter_surface.json`. It retains file,
line, column, method, syntax category, source/header kind and body attribution;
parent/source/project hashes bind the evidence. Twenty-one focused tests pass.
The consolidated register contains 45,919 overlapping records, with 45,655
unknowns. Overlapping body rows are evidence records, not new distinct defects.

Headers are scanned independently; actual include selection, macro expansion,
nonconstant conditional branches and overloads remain open. Source-line/method
attribution is lexical, not AST proof. No parser runtime, retail cinematic,
callback, native or visual acceptance is claimed. Runtime source and retained
compiled artifacts are unchanged; no emulator/device/adjacent D3D action.

## Original parameter API execution — 2026-10-04

Fourteen synthetic cases pass through the retained original host APIs after
creating three scripts with ScriptRegistrar::CreateScript. No Created, Killed,
timer or other mission callback is invoked; no gameplay object or retail data
is loaded. Results distinguish executable parser behavior from prior lexical
and authored metadata inventories.

M00_Damage_Modifier_DME resolves the correctly underscored declared name at
index four, including case-insensitive spelling. The original Killable_ByNotStar
read resolves to -1 and integer zero. Its float value converts as expected.
M03_Killed_Sound returns empty text and integer zero for an absent Location;
setting an empty string retains the prior Officer argument. A trailing comma
creates an empty second argument. Nonnumeric integer text becomes zero and
numeric-prefix text becomes its leading integer. M06_Hedgemaze_Patrol returns
the supplied vector, while nonnumeric vector text yields zero components.

These tests preserve original behavior. They do not prove M03's authored binding
callback activates, mission completion, damage scaling, save/load or native ABI
correctness. Numeric overflow, locale, long descriptions and embedded NUL remain
open. Three bounded allocations live until debugger process exit; destruction
and leak freedom are not claimed and debugger leak checking is disabled.

Reproduce using `tools/probe_host_script_parameters.py`; receipt is
`reports/generated/sweeps/host_script_parameters.json`. It binds the retained
host ELF, probe and seven original parser/factory/script owner source hashes.
All 14 receipt rows retain unknown full-game behavior. Seventeen consolidation
tests pass. The register contains 44,634 overlapping records, with 44,370
unknowns. Runtime source and compiled artifacts are unchanged. No emulator
launch, physical-device action or adjacent D3D modification occurred.

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

## Save-load bounds cluster — 2026-10-04

The eight-call destination inventory exposed a shared capacity check that
previously depended on assertions. Original Load_Data now rejects negative
capacity and oversized microchunks before reading. Cinematic command restore
initializes its buffer and requires a positive, bounded length and final NUL.
Original chunk formats and valid command behavior remain unchanged.

Six shared-boundary cases pass with assertions disabled under ASan/UBSan;
four malformed cinematic cases, seven parser cases, cursor independence and
saved pending-audio replay pass. Host runtime rebuild and light smoke pass.
A3.5-dev221 ARM compile/link and artifact checks pass. The fast-build gate now
includes both regressions. Two stale renderer extraction fixtures were repaired
without changing the production renderer; sanitized batching equivalence passes.
See [matching receipt](generated/sweeps/script_load_bounds_fix.json).

Real save transport error propagation, other malformed fields and physical
save/load remain open. Native mission acceptance stays 0/10. Earlier inventories
and parser receipts retain their historical source/artifact identities.

## Command body denominator — 2026-10-04

Every original ScriptCommands slot now has original/staged body candidates:
202 rows, all unknown. There are 191 equal bodies, eight changed bodies and
three unresolved extraction cases. Changes cover lookup/logical-sound telemetry,
shared load capacity, conversation lookup, text-file host token boundaries and
native HUD prompt routing. Create_Object, Enable_Enemy_Seen and Add_Radar_Marker
remain ambiguous and require overload-aware extraction rather than guessing.

The inventory retains body hashes, lines, preprocessor directives, lexical calls
and return signals. None establishes an active branch, stub verdict or runtime
behavior. Equal bodies can still invoke replaced downstream owners or macros.
This is the main remaining coverage question: downstream command dependencies
must be joined to the guard inventory before declaring behavior preserved.

Six focused tests pass and independent regeneration is byte-identical.
Runtime source and compiled Dev221 artifacts are unchanged. No device action.
Run `python3 -m tools.audit_script_command_bodies --output <receipt.json>`.
See [body records](generated/sweeps/script_command_bodies.json).

### Definition identity correction

The extractor now requires an exact unqualified function token. The earlier
Enable_Enemy_Seen ambiguity was a suffix match against
Innate_Soldier_Enable_Enemy_Seen, not an engine defect. Current totals are 192
equal bodies, eight changed and two unresolved assigned-overload selections.
Create_Object and Add_Radar_Marker each retain both definition candidates,
including parameter spelling, line, body hash, directives and lexical calls.
This prevents ambiguous selection from discarding downstream review evidence.
Seven tests pass; regeneration is byte-identical. Runtime source and Dev221
artifacts remain unchanged. Selecting overloads from the command signature and
evaluating downstream platform branches remain open.

## Initialized command table — 2026-10-04

A bounded debugger call to original Get_Script_Commands in the retained host
runtime initializes all 202 slots. Every pointer is non-null and resolves to
its lexically assigned function name. The selected overloaded functions are
Create_Object(char const*, Vector3 const&) and
Add_Radar_Marker(int, Vector3 const&, int, int), agreeing with original slot
types. All 202 exact host-selected function signatures are retained as function
symbols in the hash-pinned Dev221 ARM symbol list.

The public [table receipt](generated/sweeps/host_script_command_table.json)
retains binary/probe/source identities and selected signatures; the debugger
log remains private. No callbacks, gameplay or authored retail data execute.
Initialization is invoked at main by the debugger, so ordinary startup ordering
and ARM initialization remain unproven. Leak checking is disabled for debugger
operation. Behavior statuses remain unknown. Runtime source is unchanged.
