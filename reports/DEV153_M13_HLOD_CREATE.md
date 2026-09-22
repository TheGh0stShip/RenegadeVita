# Dev153: M13 HLOD prototype construction

The original `WW3DAssetManager::Create_Render_Obj` is now timed by lookup,
on-demand load, and prototype creation, with bounded nested-call logging.
The M13 `X00_AG_Explode` model's prototype was already present. In isolated
Vita3K/OpenGL evidence, lookup took 4 us, the post-lookup phase 1 us, and
`proto->Create()` took 6,122,860 us. Its class ID 25 maps to the resulting
HLOD render object, not the prototype subclass. Dev154 subsequently identified
the prototype as an aggregate with 91 authored child objects.
No nested child create exceeded the trace's 100 ms threshold, so the slow
operation may be a constructor phase or many smaller child operations.

No performance fix, A/V alignment, actor-sequence correctness, or physical
Vita acceptance is claimed. The run timed out unassessed.

Evidence: managed AppData `campaign-dev153-assetdepth-m13-1/`; matching
SELF SHA-256
`d73dfcfcd3f25df0c3d889b5472382e49188631dba7f6ac21f363bb96d24e225`;
asset-free VPK SHA-256
`5397d1ab1a928cbf38629ddd67d720e9415d93def73f984e2726ddf74261b1cd`.
ARM SELF/VPK and 192 ordered patches pass.

Next: see `DEV154_M13_AGGREGATE_CHILDREN.md` for the child-create split and
retained-template experiment.
