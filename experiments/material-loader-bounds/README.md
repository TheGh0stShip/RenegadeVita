# Material loader bounds proposal

Unapplied, unregistered patch against the currently staged original material
loader. No canonical source or retail asset changes. Not compiled or tested.

The proposal checks material-name chunk bounds and a serialized terminator,
requires material-info presence, terminates mapper argument buffers explicitly,
guards unsigned prefix-allocation arithmetic, and cleans mapper allocations on
duplicate chunks and early returns. It retains original chunk parsing, INI
construction and mapper creation rather than introducing an asset format.

Prefix copying replaces sprintf but retains the existing first-NUL text length
used by BufferStraw. Allocation policy remains original; this is not a total
memory budget or protection from all very large valid allocations.

Before integration: confirm original writer name termination, exercise valid
retail material cases plus malformed/duplicate/short chunks under sanitizers,
and inspect callers' chunk-unwind behavior. Compare resulting original mapper
state. Do not infer a crash fix or FPS improvement from this proposal.

Dev111 remains the frozen validation candidate. Apply only in a later coherent
correction batch after its result, not during compilation.
