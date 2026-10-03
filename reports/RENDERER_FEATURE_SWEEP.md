# S2 renderer features — inventory in progress

This source denominator is incomplete as a feature matrix. All 1,848 records
remain `unknown`; syntax discovery does not prove selection, linking, native
submission, feature support or physical rendering. S1 classification continues.

| Kind | Records |
| --- | ---: |
| Class/struct definitions | 467 |
| Parse uncertainties | 391 |
| Draw-state token references | 990 |

The references contain 176 distinct D3D render-state, texture-stage, sampler,
FVF, format and transform symbols. Comments and literals are excluded while
source positions are retained. References include declarations and queries;
they are not automatically calls that set a state. All source files and the
generator/parser inputs have SHA-256 identity. Rows have unique location IDs.

Candidate ancestry identifies 25 render-object definitions, 14 prototype-loader
definitions and 14 prototype definitions. These counts include the base classes.
The graph follows transitive/multiple inheritance but does not resolve namespaces,
aliases, template substitutions, preprocessing or duplicate names. Each definition
retains its bases, scope, byte positions, definition hash and syntax-error flag.
Every parsed class is retained so helpers outside these ancestries remain visible.

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

Four focused tests pass with the pinned parser. They cover transitive/multiple
inheritance, cycles, namespace/template preservation, malformed syntax and
comment/literal masking. General Python without the parser skips two AST tests;
the explicit CI parser step installs the dependency and runs all four. CI retains
the partial S2 JSON independently of the S1 artifact.

Coverage question: what can exist outside this denominator? Open risks are
macro-generated classes, sources outside the scanned WW3D/renderer trees,
unresolved syntax, scoped/aliased inheritance, numeric/computed states, dynamic
FVF and state combinations. Active graph/link selection, native draw mapping,
all-map asset effects and Vita/PSTV visual evidence are required to close S2.
Fog, alpha/stencil/clip behavior, multitexture operations, environment/bump/cube
maps, specular, point sprites, depth bias and render targets remain mapping work.

Machine inventory: [renderer.json](generated/sweeps/renderer.json).
