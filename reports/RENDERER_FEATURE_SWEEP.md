# S2 renderer features — inventory in progress

This source denominator is incomplete as a feature matrix. Of 2,052 records,
15 direct state mappings are reviewed as `missing`, 15 as `boundary_replaced`,
and 2,022 remain `unknown`.
Syntax discovery does not prove selection, linking, native
submission, feature support or physical rendering. S1 classification continues.

| Kind | Records |
| --- | ---: |
| Class/struct definitions | 467 |
| Parse uncertainties | 391 |
| Draw-state token references | 990 |
| Required feature cross-checks | 28 |
| Per-symbol state mappings | 176 |

The references contain 176 distinct D3D render-state, texture-stage, sampler,
FVF, format and transform symbols. Comments and literals are excluded while
source positions are retained. References include declarations and queries;
they are not automatically calls that set a state. All source files and the
generator/parser inputs have SHA-256 identity. Rows have unique location IDs.

Initial state mapping: `D3DRS_ZBIAS` is missing natively. Decal flush requests
bias 8 and resets to 0. Original DX8Wrapper forwards to the native device;
its render-state handler has no ZBIAS case in fog/ambient or draw-state handling,
then logs an unsupported state and returns success without applying it. The
review pins all four source inputs. A changed input invalidates the mapping.
Original pseudo-ZBias projection handling is a separate route; it does not
make this direct decal state request work. Per-map instances and physical
z-fighting are unverified. No renderer repair is included in this batch.

The next direct-state review covers the complete inspected handler cases:

| Source path present | Translation |
| --- | --- |
| Blend enable, source/destination factors | GL blend state and factor translation |
| Alpha enable, reference, comparison | GL alpha test, 8-bit reference and comparison |
| Depth comparison and write enable | GL depth function and mask |
| Cull and fill modes | GL cull side and polygon mode |
| Fog enable, color, start and end | Retained values applied as linear GL fog |
| Ambient color | Packed RGB to GL light-model ambient |

These 15 rows are `boundary_replaced`, not feature acceptance. Legal value
domains, default factor/comparison fallbacks, initialization, cache coherence,
shader-state overlap and physical combinations remain open.

Fourteen further direct mappings are `missing`: fog density, table/vertex mode,
range fog; stencil enable/fail/function/mask/pass/reference/write-mask/Z-fail;
clipping and clip-plane enable. The inspected handler returns success without
applying them. This proves a gap in this entry point, not absence of all clipping,
fog or stencil behavior through independent renderer routes. Exact active
setters, retail requests and per-map effects remain unverified. Together with
ZBIAS, 15 state rows are missing; no behavior changes are included here.

Candidate ancestry identifies 25 render-object definitions, 14 prototype-loader
definitions and 14 prototype definitions. These counts include the base classes.
The graph follows transitive/multiple inheritance but does not resolve namespaces,
aliases, template substitutions, preprocessing or duplicate names. Each definition
retains its bases, scope, byte positions, definition hash and syntax-error flag.
Every parsed class is retained so helpers outside these ancestries remain visible.
Twenty-eight explicit required-feature rows cross-check discovery seeds against
the class definitions. They include skin/decal, point/line groups, shatter,
projectors, Render2D/sentence and other helpers even without RenderObj ancestry.
These rows remain unknown until ownership, native submission and support are
reviewed. Snapshot is state/macro evidence rather than a parsed class; no StreakClass
definition was discovered. Neither observation proves a missing retail feature.

Dx8Wrapper.h and dx8wrapper.h are identical case-alias paths. Their source
records remain separate provenance, including 131 parse uncertainties each.
Counts are source locations, not unique semantic types or distinct parser bugs.

Render-object candidates include mesh and dynamic meshes, HLOD, collections,
composite/animated bases, bitmap, Dazzle, distance LOD, line/segmented line,
particle buffer/emitter, sphere, ring, axis-aligned/oriented boxes, sound,
text, camera, light and null objects. Loader candidates include aggregate,
collection, mesh/HModel, HLOD, Dazzle, particle emitter, distance LOD, sphere,
ring, boxes, sound and null objects. Skin/decal, point/line groups, streak,
shatter, projectors, snapshot and Render2D/sentence helpers still require explicit
owner/feature mapping; their absence from an ancestry list is not an exclusion.

Thirteen upstream source/header files lack staged counterparts. They include
hueshift, skeleton and sorttest paths plus intersec.inl. This list is discovery,
not editor-only proof. Project membership, retail references and runtime callers
must be checked before assigning `excluded_with_proof`.

Reproduce after deterministic source staging using the pinned parser environment:

```sh
build/sweep-parser-venv/bin/python -m unittest discover -s tools -p test_audit_sweep_renderer.py
build/sweep-parser-venv/bin/python tools/audit_sweep_renderer.py --output reports/generated/sweeps/renderer.json
```

Six focused tests pass with the pinned parser. They cover transitive/multiple
inheritance, cycles, namespace/template preservation, malformed syntax and
comment/literal masking. General Python without the parser skips two AST tests;
the explicit CI parser step installs the dependency and runs all six. State
aggregation and stale review invalidation are covered. CI retains
the partial S2 JSON independently of the S1 artifact.

Coverage question: what can exist outside this denominator? Open risks are
macro-generated classes, sources outside the scanned WW3D/renderer trees,
unresolved syntax, scoped/aliased inheritance, numeric/computed states, dynamic
FVF and state combinations. Active graph/link selection, native draw mapping,
all-map asset effects and Vita/PSTV visual evidence are required to close S2.
Fog, alpha/stencil/clip behavior, multitexture operations, environment/bump/cube
maps, specular, point sprites, depth bias and render targets remain mapping work.

Machine inventory: [renderer.json](generated/sweeps/renderer.json).
