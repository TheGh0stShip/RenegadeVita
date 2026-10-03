# Host and ARM compile closure

The restored engine graph now compiles on GCC and links on ARM. The fixes
restore ScriptCommands call defaults per translation unit, original GCC scope
and template semantics, audio probe access, host FreeType discovery, retained
probe dependencies, and original audio selection in canonical configurations.
Original random arithmetic uses translation-unit-scoped wrap semantics with
32 regression vectors. PR/push CI now includes host and ARM compilation,
Python contracts, strict script-call auditing and sanitizer probes.

Verified local evidence: 31 host binaries compiled; 60 retail-free ASan/UBSan
invocations passed; five threading/diagnostic probes passed TSan with per-process
ASLR disabled; 793 Python tests across 149 modules passed with one optional skip.
The skipped original-engine TTFS fixture passed separately in the sanitizer
suite. All 45 original script-project units pass strict default-call auditing.
Fast ARM compilation/link passed, with 652 matching source/object hash pairs.
Original Dazzle initialization, rendering and cleanup are retained in the ELF.
Seventeen current build-state fields now reflect actual compilation evidence.
See [machine-readable evidence](generated/compile_closure.json).

Original textureloader.cpp is compiled separately on host and ARM; its missing
D3DX header alias is restored. Runtime integration remains open because the
current graph selects the native texture boundary. Compilation does not prove
link selection, runtime behavior or pixels.

Canonical packaging stopped on an ASan overlapping-copy finding in the shared
script parameter-name trim helper. All three original trim bodies were inspected:
Scripts narrow trim and WWLib wide trim now use overlap-safe moves; WWLib narrow
trim already had that correction. Whitespace predicates and underscore lookup
quirks remain unchanged. The original-owner regression and all 60 retail-free
ASan/UBSan cases pass again. Host and ARM rebuild/link pass; the current ELF is
recorded in the generated ledger. The M13 damage smoke passes two in-process
cycles using bounded player-attributed hits through the retail damage modifiers.
The old fixture used unattributed damage and incorrectly expected one hit to
destroy both differently configured SAMs. Prewarmed repeat is still running.
These fixtures prove damage/teardown paths, not natural mission completion.

Outputs now use the ignored WSL `local-builder/` folder.
The first clean-checkout CI passed TSan, but Python
contracts failed on missing prerequisites: the host runtime, native SDK,
pinned renderer archive and LLVM resource compiler. ARM preflight also stopped
on the LLVM compiler and a workstation-specific MPEG header path. The runner now prepares
those inputs and builds the runtime before contracts; MPEG checks use VITASDK.
The corrected main run passed host ASan/UBSan, TSan, all 793 Python tests and
the excluded texture-worker compile. ARM preflight still required Clang for
LLVM resource preprocessing; both CI dependency lists now install it. Eleven
focused script/probe/install checks and seven RC checks pass locally.
Canonical packaging and the next remote ARM run remain pending.
Phase 0 is still open. Native/runtime acceptance remains 0/10; complete mission progression,
all-map inventories, projector targets, decal depth bias, procedural material
passes and visual Dazzle acceptance remain open.

Future build and diagnostic output defaults use `local-builder/`. The complete
Windows builder archive was independently checksum-verified before deletion;
no migrated retail data, saves, credentials or artifacts are committed.
