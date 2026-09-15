# Patch inventory: single authority, no manually maintained counts

The executable, ordered zero-fuzz application commands in tools/stage_sources.sh
are the only active registry. Add/remove/reorder patches there; do not update
numeric expectations in other files. The retained historical network experiment
is explicitly excluded in tools/renegade_patch_inventory.py.

Application discovery uses shell-argument tokenization, not formatting-sensitive
regular expressions. Leading tabs/spaces, argument spacing, LF/CRLF input,
quoted paths, trailing comments, single-line commands and backslash continuations
are handled independently of the required options. Option order is immaterial;
duplicates, unknown arguments, shell chaining and unsafe paths are rejected.
This is a constrained command parser, not an arbitrary Bash evaluator.

Both canonical and fast builds preflight the registry before dependencies,
staging or compilation. Missing files, duplicates, unregistered patch files,
retired patch activation, unrecognized application commands and reintroduced
hardcoded patch counts are rejected early.

Successful staging writes staging/PATCH_INVENTORY.json with ordered paths,
application directories, patch SHA-256 hashes and staging-script identity.
The receipt is written only after the set -e staging script completes.
Fast builds automatically restage when that receipt is missing or stale.
The integration report consumes the same inventory and must match the successful
staging receipt by identity and order, not merely by count. The canonical build
summary derives its displayed count from preflight.

This removes the previously independent 145/146 numeric expectations. It does
not remove zero-fuzz patch application or allow an arbitrary directory count
to stand in for registered/applied patches. Native source and Dev108 runtime
behavior are unchanged by this build-pipeline correction.

Validation status: canonical r3 passed whitespace-independent preflight and
successful staging for all 147 registered patches. The retained registry identity
is 198f15f44372490536ad71905f301f00c2b578637460493665d8f21d6fcd8202.
This is staging evidence, not full canonical or demo acceptance. The prior
layout-matching parser rejected 11 valid indented commands; that failure remains
in canonical-build-r2.log.

Maintenance rule: never repair registry discovery by normalizing source
indentation, adding layout-specific command patterns, weakening zero-fuzz flags,
or incrementing a second expected count. Parse supported shell arguments and
derive the inventory from the single staging registry. Unsupported shell syntax
must fail in preflight, before expensive compilation, with the strict contract
preserved. This addresses the recurring formatting/count failure class; it does
not promise that unrelated build errors cannot occur.
