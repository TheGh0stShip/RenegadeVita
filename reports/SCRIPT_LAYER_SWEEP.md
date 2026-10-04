# S5 script layer — complete slot/unit denominator in progress

## Selected script warning closure — 2026-10-04

The current optimized compile inventory covers all45 Scripts.dsp units:44
selected units compile and DLLmain is deliberately replaced by the static
provider. The two remaining live warnings belonged to `RMV_Engineer_Wander`,
which has two persisted bindings in M03 with payload `Custom_Param_1=1`.
Original code converted that integer to a pointer and back into the saved
`int_anim` field, later reconstructed a pointer, then overwrote it with the
literal `s_a_human.h_a_con2` before animation playback. The zero-fuzz correction
assigns the integer directly and initializes the same literal directly. It
retains field type, save slot5, action IDs, callback order and animation.

Actual original and corrected registrations pass the bounded host callback
fixture for INT_MIN,0 and INT_MAX payloads; both produce the same literal
animation. The warning-route ledger classifies both live bindings as
`original_patched`. Dev225 passes491 fast contracts, a clean315-patch restage
and all634 ARM compile/link actions.

The only optimized warning left is `PDS_Test_Inventory`'s pointer-return
receiver. Across27 retained maps it has zero bindings; its sole attaching
`PDS_Test_Controller` also has zero bindings, and the selected script set has
no sender for `CUSTOM_HAS_MEDKIT`. The original source remains compiled and is
classified `excluded_with_proof`, avoiding an invented host token path for an
unreached designer test. Computed external attachments and omitted maps remain
an explicit limit. Native M03 execution and the wchar_t ABI warning remain open.

## Mission08/Mission10 Apache controller bounds — 2026-10-04

The two copied three-slot Apache controllers had the same unchecked routes.
Non-exit events accepted `-1` and indexed three-element arrays; timer IDs3..9
also indexed those arrays. A child reload event used the controller's current
area, which can already be `-1` after the player exits, instead of the child's
validated Area parameter. Their decimal attachment buffers were one byte short
for the full signed 32-bit range. The zero-fuzz patch bounds non-exit events and
spawn timers to0..2, retains only the authored type3000 `-1` exit sentinel,
uses the sender area for reload/timer10..12, and uses a 12-byte int buffer.

The actual registered original callbacks reproduce eight UBSan failures across
M08 and M10: negative destroy, inactive-area reload, gap timer9 and negative
timer. Corrected callbacks pass those cases plus valid slots0..2, sentinel exit,
sender-area reload and high timers13/INT_MAX. High reload IDs are harmless in
the original branch because it indexes only when `timer_id-10` equals the
already bounded active area. DeepSeek V4 Pro raised that counterexample and a
broader negative-sentinel concern; source inspection and the added cases reject
both as remaining defects. This was advisory review, not execution evidence.

The all-map binding surface covers27 maps. It retains one authored
M10_Apache_Controller binding, no M08 controller/child binding in this metadata
surface, and two RMV_Engineer_Wander bindings; computed and serialized runtime
attachments remain open. Dev224 passes491 focused contracts outside the
ptrace-conflicted sandbox and all634 ARM build/link actions. The ELF, map and
symbols validate. The current45-unit optimized compiler inventory has only
three review warnings, all retained pointer casts in Test_PDS and
Test_RMV_Toolkit; both Apache format warnings are gone. The mixed wchar_t linker
warning and native M08/M10 behavior remain open.

See [warning routes](generated/sweeps/script_warning_routes.json) and
[compiler diagnostics](generated/sweeps/script_compiler_diagnostics.json).

## Mission09 camera bounds correction — 2026-10-04

The original registered M09_Camera_Activate callback reads past camera[5] on
its first entry;UBSan reproduces index five. The zero-fuzz patch changes only
the loop bound to the array's element count. Five parameter names, save fields,
zero-slot skips, attachment payload and repeated-entry latch stay unchanged.
Four actual callback cases pass ASan/UBSan with exact fixture callback types.
The fixture uses synthetic transport/opaque objects and does not render cameras.

The all-map binding inventory retains27 maps:15 persisted M09 instances each
have five parameter fields;the other26 maps have zero retained matches. Dynamic
attachments and mounting/activation remain open. Public metadata excludes raw
retail parameters. Dev223 host617/ARM634 actions and485 fast contracts pass;
four additional tests are added to future fast gates.48 focused checks pass.
ELF32 little-endian ARMv7 hard-float inspection passes;wchar_t warnings remain.
All44 selected script units recompile and the camera diagnostic disappears;
two parameter-buffer and three pointer-cast warnings remain.313 patches apply.
The consolidated register retains53,166 overlapping records with52,885 unknowns.
See [fix receipt](generated/sweeps/m09_camera_bounds_fix.json) and
[binding inventory](generated/sweeps/m09_camera_bindings.json).

## Optimized compiler diagnostic denominator — 2026-10-04

All44 selected DSP units compile with actual host target flags plus optimized
uninitialized/return diagnostics. DLLmain remains unselected; all45 behavioral
statuses remain unknown. Six review warnings include a source-confirmed M09
camera array overrun, two parameter-buffer range leads and three pointer-cast
leads. Seven tooling tests pass; no runtime source or native artifact changed.
See [diagnostic ledger](SCRIPT_COMPILER_DIAGNOSTICS.md).

## Mission03 host pointer-exchange compatibility — 2026-10-04

The three verified Mission03 synchronous out-parameter events now use scoped
32-bit tokens under `RENEGADE_HOST_ABI_TEST`. Their receivers resolve full-width
host pointers; each sender removes its token when the inline call returns.
The original Vita branches, integer event ABI, command table and mission
decisions are preserved. Tokens are process-local and cannot be retained by
delayed events or serialized. No other integer event is reinterpreted.

The actual registered Mission03 classes pass ASan/UBSan:three escort results
0/1/-1, two area/target queries, all three real sender exchanges, nested token
isolation and release/stale lookup. Opaque objects and synthetic command
transport bound the fixture; real world/observer lifetime and complete M03
gameplay remain open. Every fixture callback now has an exact compile-time
function-pointer type check. Initial fixture setup failures and the permissive
callback mismatch are corrected; the qualified retained run is the evidence.

Host runtime rebuild/link passes, including133 initial and two final actions.
Dev222 ARM compile/link passes six actions and485 fast contract tests. Native
Mission03 preprocessing matches the pre-fix staged source byte-for-byte under
the retained flags. This is compile/source evidence, not native dispatch or
physical acceptance. Existing ARM wchar_t linker warnings remain open.

The new patch is in the312-entry zero-fuzz stage registry. S1 is refreshed to
3,597 records:51 stubs, one patched, two boundaries, six disabled guards and
3,537 unknown. Its previously stale scriptcommands review hash is reconciled
only after verifying that the sole difference is the already-tested Load_Data
capacity guard; audio and other caller bodies are unchanged. Dependent command
joins, portability metadata and the53,087-record gap register reconcile.

The [cluster receipt](generated/sweeps/m03_pointer_exchange_fix.json) pins
matching source, probe, host runtime, ELF, map and registry hashes. Retained
artifacts and logs are under `build/procedural-renderer-dependencies/` with
the `m03-pointer-` prefix; native artifacts are in `local-builder/dist/`.
The regression is in the fast-build gate. No packaging, emulator launch,
physical-device operation or adjacent D3D project change occurred.

## Original custom-event timing contract — 2026-10-04

The original and staged `Send_Custom_Event` bodies match exactly. Its default
delay is0; delay<=0 iterates the target's observers and invokes `Custom` inline.
Positive delay calls `Start_Custom_Timer`; original timer expiry later iterates
observers in `ScriptableGameObj::Post_Think`. Thus Mission03's three default-delay
pointer exchanges rely on synchronous delivery and stack writes before return.
Their host LP64 pointer conversions remain unresolved.

The extracted original command passes host ASan/UBSan for nine contracts:
inline observer order, nested/reentrant order, stack mutation, negative delay,
null sender, positive-delay queue arguments, null target, empty observer list
and signed32-bit extremes. The fixture's callback list/timer queue are bounded
seams; actual mission callbacks, observer mutation/lifetime and timer expiry
are not executed. Trace logging is omitted; the original null-target guard and
assert predicate remain. No original command-table layout or event width changes.

The same fixture compiles to an ELF32 little-endian ARMv7 object with VFP-register
arguments. This is object compilation, not native execution or a linked game
candidate. Matching host executable, ARM object, compile/runtime/attribute logs
and receipt are retained in
`build/procedural-renderer-dependencies/custom-event-delivery/`. Public metadata:
[delivery receipt](generated/sweeps/host_custom_event_delivery.json).

Reproduce host checks with `python3 -m unittest tools.test_custom_event_delivery`.
Set `RENEGADE_CUSTOM_EVENT_PROBE_DIRECTORY` to retain artifacts and
`RENEGADE_CUSTOM_EVENT_ARM_COMPILER` to the installed Vita compiler for the
optional ARM object gate. Production runtime and Dev221 artifacts are unchanged.

## Whole script compiler-assumption surface — 2026-10-04

`python3 -m tools.audit_script_portability` inventories every original DSP unit
and directory header:45 units plus45 headers, all90 with staged counterparts.
Original/staged hashes and lexical candidates retain lines, offsets and preceding
script declaration candidates. The source and category partitions reconcile in
the full gap register. Candidates remain unknown; they are not defect verdicts.
Thirty-four focused tests pass; both inventories regenerate identically. The
consolidated register retains53,066 overlapping records, including52,785 unknown.

| Syntax category | Original | Staged |
| --- | ---: | ---: |
| Address to integer cast | 3 | 3 |
| Bare scalar declaration | 2,231 | 2,224 |
| Case-insensitive lookup | 89 | 99 |
| Dereference order comparison | 4 | 4 |
| Integer cast | 24 | 22 |
| Loop-local declaration | 38 | 38 |
| Plain-char declaration | 691 | 696 |
| Scalar-pointer cast | 16 | 15 |
| Size expression | 41 | 43 |

Source inspection links all three address casts to Mission03 custom events:
`M03_Chinook_Spawned_Soldier_GDI::Poked` sends `&has_escort` as type3000;
`M03_Commando_Script::Custom` casts its integer parameter back to `int*`.
`M03_Area_Troop_Counter::Custom` sends `&area` and `&target_count` as types5000
and6300; `M03_Reinforce_Area::Custom` casts them back to pointers. The staged
casts are unchanged. This is a host LP64 width risk, not evidence of an ARM
mission defect. Callback timing, runtime reachability and a host compatibility
boundary still need verification before a change; no pointer truncation fix
or raw pointer token is being introduced here.

Installed compiler macros confirm ARMv7-A, little endian, int/long/pointer4
and VFP calling convention; host int4/long8/pointer8. Default plain char is
signed in both queried compilers; actual per-unit flags and execution remain
separate requirements. Existing aliases in `msvc_compat.h` cover stricmp and
strnicmp names, without proving locale-equivalent results. The four separated
dereference comparisons occur in the cinematic parser; its signed-char edge
fixture is separate host evidence.

Bare declarations can be members or assigned before use; loop declarations do
not prove post-loop use. Templates, compact comparisons, indirect macros,
transitive headers, type flow and stack initialization require additional
compiler/dataflow evidence. Directory-header presence does not establish DSP
include reachability. The JSON records these limits explicitly. Production
runtime and Dev221 artifacts are unchanged; native acceptance remains open.

## Cinematic alternative and failure execution — 2026-10-04

The original dispatch sanitizer fixture now also passes 25 cases: five
alternative/failure routes, 18 guarded no-effect routes and two slot-preservation
checks. These cover bone-positioned 3D sound, bone detachment, standalone real
object creation, failed decoration/real creation, empty or explicitly guarded
invalid slots, absent custom targets and same-slot/invalid-destination moves.
Failed creation retains an occupied destination slot, matching the original
handler. No production code changes were needed.

The retained executable, logs and metadata receipt live under
`build/procedural-renderer-dependencies/cinematic-dispatch-alternatives/`.
The public dispatch receipt matches that retained receipt exactly. Host
ASan/UBSan passes; real object lifetime, callbacks, exhaustive input coverage,
ARM dispatch and native effects remain open. Dev221 runtime artifacts are unchanged.

## Command and dispatch register reconciliation — 2026-10-04

The full gap register now retains 202 command bodies, 202 lexical dependency
joins, 202 initialized host-table entries and 18 cinematic dispatch branches.
Nested port candidates remain overlapping evidence records. Parent hashes,
status totals, candidate totals, initialization partitions and unique dispatch
commands are checked. Twenty-two consolidation tests pass, including stale-parent
rejection.

The register contains 46,695 records: 46,414 unknown, 160 missing, 68 stubbed/no-op,
46 boundary replacements, six disabled guards and one patched record. These
counts are not unique defects. Host checks retain unknown native acceptance;
execution fixtures without status inventories remain linked evidence in this
ledger. Runtime source and Dev221 artifacts are unchanged. Real objects,
alternative dispatch routes and native effects still require execution evidence.

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

## Direct port dependency candidates — 2026-10-04

All 202 command-body records are joined to the hash-pinned port-function and
function-like macro inventory. Forty-seven commands have candidates across 76
matched call names. Both overload bodies contribute discovery calls until a
signature-aware source join selects one. Candidates retain guard row identity,
file, line, scope, status and body hash; unmatched calls remain explicit.

Distinct diagnostic, text-file pointer-token and tutorial HUD owners are visible,
alongside sound creation/playback candidates. Generic names such as Read, Play,
Next and Release_Ref can collide across classes. This is a review queue, not a
call graph or a verdict that 47 commands are defective. Equal command bodies
do not establish original downstream behavior, and no match proves absence of
port changes. Staged original methods, virtual/transitive dispatch and active
preprocessor branches remain the next coverage denominator.

Nine focused tests pass; independent regeneration matches exactly. Parent hashes
pin both inventories, whose current source identity needs revalidation before
fixing a candidate. Runtime code and Dev221 artifacts are unchanged.
See [dependency candidates](generated/sweeps/script_command_port_dependencies.json).

## Original text-file boundary execution — 2026-10-04

The three staged original text-file command bodies execute against a synthetic
FileClass/factory seam and the real host pointer-token implementation under
ASan/UBSan. Missing/unavailable files, CRLF, multiple lines, final unterminated
lines, EOF, truncation while consuming the remainder, zero capacity, invalid
host handles and repeated close pass. Retained executable, logs and source hashes
are available locally; the public [receipt](generated/sweeps/host_script_text_file_boundary.json)
contains no retail payloads.

The original size argument is maximum characters, excluding final NUL. The
shipped cinematic caller allocates 200 bytes and passes 199. Zero capacity
consumes a line and returns false; this original behavior is preserved rather
than changed as a guessed port defect. Host tokens avoid LP64 pointer truncation
and are removed on close. Native ILP32 uses original pointer handles, so invalid
native handle behavior is not established by this host test.

This closes a focused boundary contract, not MIX/file-factory integration,
cinematic playback or physical I/O. Runtime source and Dev221 artifacts are
unchanged; the test compiles the actual three staged method bodies.

## Shared retail MIX text transport — 2026-10-04

The retained host runtime stops after its original rooted factory and MIX
factory-list setup. Original Text_File_Open/Get_String/Close read all 283 unique
.txt member names across always.dat, Always2.dat and always.dbs. There are 284
archive occurrences; the shared duplicate is retained as an expected-payload
alternative. Every returned line-sequence hash/count matches an archive candidate.
No payload text is printed or published. The public
[receipt](generated/sweeps/host_mix_text_commands.json) pins binary, probe and
archive identities and retains only names, hashes and counts.

Four reference/boundary tests pass. The initial debugger attempt failed solely
at a missing return-type cast for free; its private log is retained, and the
corrected bounded run succeeds. This executes the real host FileFactory/MIX
transport, beyond the synthetic seam, without cinematic command dispatch.
Per-map members, always3.dat, ordinary startup sequencing, world/playback and
physical I/O remain outside this evidence. Leak checking is disabled for GDB.
Runtime sources and Dev221 compiled artifacts remain unchanged.

## All-map local text transport — 2026-10-04

All 27 retail .mix map archives are inventoried. Eleven contain 142 local .txt
member names; original host text commands through each map's actual factory
stack match all 142 line hashes/counts. This includes campaign maps M01–M06,
M08/M09/M11/M13 and multiplayer C&C_Glacier_Flying. The other 16 archives have
zero local text members; they are inventoried, not runtime-tested here.

The reproducible all-map driver retains archive/binary/probe identities and
individual map receipts. Explicit reuse requires matching binary, probe,
archive, level selection and successful totals; it does not infer execution
from a lock or state label. Independent summary regeneration is byte-identical.
Four focused boundary/reference tests pass. The current always3.dat index also
contains zero text members; no transport claim is inferred from that absence.

See [all-map metadata](generated/sweeps/host_all_map_text_commands.json).
Shared transport remains a separate historical receipt. These are archive-member
denominators, not a complete cinematic-reference/dispatch or playback proof.
Runtime source and Dev221 artifacts are unchanged; no emulator/device action.

## All-archive original cinematic scheduling — 2026-10-04

The original Test_Cinematic::Load_Control_File and Add_Control_Line execute
under ASan/UBSan over all 426 .txt archive occurrences in the 31-archive install.
All 10,955 scheduled records match reference timestamp float bits, stable order
and command-byte fingerprints. Not every .txt is a cinematic: credits.txt is
included deliberately as a member-level coverage case, not a playback claim.
The fixture supplies original-compatible line transport; real MIX transport has
separate shared/all-map evidence. Effects and callbacks are not dispatched.

An initial 425/426 comparison exposed a reference defect on credits.txt. Original
signed-char comparisons treat high-bit bytes as whitespace at trim/token edges;
the reference now preserves this behavior. This is not a retail asset correction.
Failed attempt logs remain private and the final run succeeds. Three reference
tests and the existing cinematic sanitizer regression pass. Source, binary and
archive identities are retained in the public
[scheduling receipt](generated/sweeps/host_retail_cinematic_parser.json), with no
command payloads. Native char/compiler behavior and real playback remain open.

The new fixture compiles original script/framework code using the existing
isolated MSVC-default compatibility flags. Production runtime source and Dev221
ARM artifacts remain unchanged; no device or emulator action occurred.

## Cinematic dispatch dependency denominator — 2026-10-04

All 18 original Parse_Command title branches are enumerated with their handler
body hashes, source lines and direct ScriptCommands calls. They depend on 32
distinct engine commands. The title sequence agrees with the existing retail
control vocabulary; missing or duplicate dispatch extraction fails explicitly.
Commented branches/calls are excluded. Every behavior row remains unknown.

Thirty-three focused inventory/control tests pass and regeneration is
byte-identical. This connects the parsed schedule to a complete direct dispatch
dependency set before executing branches. Prefix/case matching, parameter and
slot validity, object lifetime, platform selection and effects remain separate
execution requirements. Runtime source and Dev221 artifacts are unchanged.
See [dispatch dependencies](generated/sweeps/cinematic_dispatch_dependencies.json).

## Original cinematic dispatch execution — 2026-10-04

All 18 original Parse_Command title branches execute through bounded synthetic
callbacks under ASan/UBSan. Assertions verify routed arguments for animation,
explosion, scripted attachment, custom-event slot references, sniper/shake,
shadow, letterbox and fades, plus object-slot creation/move state. Primary
attachment handles MyID=2147483647 through its previously repaired buffer.
Camera release calls restore camera/input/HUD in original order. Original
case-insensitive title-prefix behavior is retained; unknown titles invoke no
callback. Seven focused tests pass.

The [execution receipt](generated/sweeps/host_cinematic_dispatch.json) pins the
retained executable and original/fixture sources. Opaque object identity is
never dereferenced as an engine object. This verifies dispatch and conversion
contracts, not actual creation, rendering, animation/audio playback or callbacks
from live objects. One success route per title leaves alternative/failure and
lifetime paths open. Native-only branches, ARM dispatch and physical acceptance
remain unverified. Production runtime and Dev221 artifacts are unchanged.
