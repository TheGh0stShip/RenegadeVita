# Host and ARM compile closure

The restored engine graph now compiles on GCC and links on ARM. The fixes
restore ScriptCommands call defaults per translation unit, original GCC scope
and template semantics, audio probe access, host FreeType discovery, retained
probe dependencies, and original audio selection in canonical configurations.
Original random arithmetic uses translation-unit-scoped wrap semantics with
32 regression vectors. PR/push CI now includes host and ARM compilation,
Python contracts, strict script-call auditing and sanitizer probes.

Verified local evidence:31 host binaries compiled;60 retail-free ASan/UBSan
invocations passed;five threading/diagnostic probes passed TSan with per-process
ASLR disabled;793 Python tests across149 modules passed with one optional skip.
The skipped original-engine TTFS fixture passed separately in the sanitizer
suite. All45 original script-project units pass strict default-call auditing.
Fast ARM compilation/link passed, with652 matching source/object hash pairs.
Original Dazzle initialization, rendering and cleanup are retained in the ELF.
Seventeen current build-state fields now reflect actual compilation evidence.
See [machine-readable evidence](generated/compile_closure.json).

Original textureloader.cpp is compiled separately on host and ARM; its missing
D3DX header alias is restored. Runtime integration remains open because the
current graph selects the native texture boundary. Compilation does not prove
link selection, runtime behavior or pixels.

Canonical packaging is running after migration to the ignored WSL
`local-builder/` folder. Remote clean-checkout CI has not run. Phase0 is still
open. Native/runtime acceptance remains0/10; complete mission progression,
all-map inventories, projector targets, decal depth bias, procedural material
passes and visual Dazzle acceptance remain open.

Future build and diagnostic output defaults use `local-builder/`. The complete
Windows builder archive was independently checksum-verified before deletion;
no migrated retail data, saves, credentials or artifacts are committed.
