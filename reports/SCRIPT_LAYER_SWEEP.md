# S5 script layer — complete slot/unit denominator in progress

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

Run `python3 -m tools.audit_sweep_scripts --link-inventory
reports/generated/sweeps/link.json --output <inventory.json>`.

Next: complete command body/guard classification, default-argument CI checks,
retail parameter matching across every map, original misspellings and MSVC
semantic dependencies. Indirect/helper/global calls remain open coverage risks.
The 179-command count is broader than campaign-only counts and does not
contradict them. Full S5 and native mission acceptance remain incomplete.
