# S2 renderer features — inventory in progress

Compound DX8_FVF_* discovery adds 11 symbols and 29 references; one symbol
is the header guard, not a vertex layout. Ten original named layouts are now
reviewed against the indexed native gate, which accepts only 0x152/stride36
and 0x252/stride44 (XYZNDUV1/2). Eight other named layouts are rejected there.
This does not establish missing whole render objects: alternate mesh, immediate
and sorting submission routes and actual callers remain open. Dynamic FVF
combinations still require enumeration. Eleven tests/reproduction pass.
Current totals: 3,119 rows; 86 missing, 38 replaced, 2,995 unknown.

Five two-byte formats have size handling but lack CPU RGBA conversion:
X1R5G5B5, A8R3G3B2, X4R4G4B4, A8P8 and A8L8. Pixel converters and
capability gates reject them; filtered copies, surface-to-RGBA conversion and
dimension-based texture allocation therefore lack these paths. Alternate file
loaders and actual retail requests remain unverified. This is scoped missing
conversion support, not proof that every use of these formats fails.
Current totals: 78 missing, 36 replaced, 2,965 unknown across 3,079 rows.

CPU surface conversion review covers eight formats: A8R8G8B8, X8R8G8B8,
R8G8B8, A4R4G4B4, A1R5G5B5, R5G6B5, A8 and L8. Decode/encode helpers
and capability gates accept these formats; packed 16-bit reads assemble bytes
explicitly in little-endian order. These rows describe CPU conversion paths,
not complete texture/GPU support. Channel order, quantization, alpha thresholds,
luminance weighting, pitch/mip bounds and upload semantics still need validation.
Totals: 73 missing, 36 boundary-replaced, 2,970 unknown across 3,079 rows.
Ten inventory tests and repeated generation pass; no C++ behavior changed.

Engine-format discovery now includes WW3D_FORMAT_* alongside DirectX format
tokens. It adds 26 symbols and 461 references, including bump formats and
UNKNOWN/COUNT sentinels; this is not a count of supported texture formats.
Original format conversion, CPU surface conversion, compressed uploads and
fallback paths require separate review. Current totals: 3,079 rows comprising
467 classes, 391 parse uncertainties, 1,900 references, 28 required features and
293 aggregated symbols; 73 missing, 28 boundary-replaced and 2,978 unknown.
Ten tests pass and regenerated output matches byte-for-byte.

Texture-stage selector closure adds four missing direct mappings: COLORARG0,
ALPHAARG0, RESULTARG and MAXMIPLEVEL. Their references do not yet prove active
retail requests. Aggregated symbols now distinguish state selectors from values
and layout tokens: D3DTSS_TCI_* are TEXCOORDINDEX values, not additional states.
A regression test protects that distinction. Current totals: 73 missing,
28 boundary-replaced and 2,491 unknown across 2,592 rows. Nine tests and
byte-for-byte regeneration pass. Coordinate generation values remain unknown
pending value-specific verification, even though their parent state has a path.

Direct-render-state handler review now covers the remaining 44 discovered
render-state symbols: lighting/material sources, specular, point sprites/size/
scale, color writes, blend operation, depth enable, wrapping, vertex blending,
multisample and other legacy/debug states. None has a case in the direct native
handler or its fog/ambient helpers. Before initialization it returns success;
after initialization it logs the first unsupported request and returns success.
These are missing direct mappings, not proof of missing whole features: original
shader, CPU lighting, geometry and color-mask routes require separate comparison.
References may be debug names rather than active setters. Current totals are
69 missing, 28 boundary-replaced and 2,495 unknown across 2,592 rows. Eight
tests and repeated generation pass. Latest publication CI remains queued.

Value-domain expansion adds texture operations, arguments and modifiers,
transform flags, addressing/filter values, blend/comparison/cull/fill/fog and
stencil-operation constants. This exposes 91 additional distinct symbols and
449 references previously omitted by the state-name-only token pattern.
All new rows remain unknown; declarations and references do not prove active
requests or defects. Current denominator is 2,592 rows: 467 class definitions,
391 parse uncertainties, 1,439 token references, 28 required features and 267
aggregated symbols. Statuses reconcile at 25 missing, 28 boundary-replaced and
2,539 unknown. Eight tests pass and generation reproduces byte-for-byte.
Numeric/dynamic values and cross-state combinations remain open coverage risks.

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

Texture-stage follow-up identifies ten direct requests accepted without value
application by `SetTextureStageState` (native boundary lines 2225–2274):
`BUMPENVMAT00/01/10/11`, `BUMPENVLSCALE/LOFFSET`, `MAXANISOTROPY`,
`MIPMAPLODBIAS`, `ADDRESSW` and `BORDERCOLOR`. Original bump mapper setters
are at `mapper.cpp:970–973`, initialization at `dx8wrapper.cpp:361–366`, and
anisotropy selection at `texture.cpp:944`. Other references include debug and
validation cases; those alone do not prove active runtime requests. These ten
requests now have source-pinned JSON classifications; independent-route review
and per-map material closure remain open. They do not establish physical visual
symptoms. Totals are 25 missing, 15 boundary-replaced and 2,012 unknown across
2,052 rows. Duplicate symbol reviews are rejected rather than silently allowing
the last review to overwrite an earlier classification. Seven tests pass.

Eleven combiner/sampler rows now have partial native mappings recorded:
color/alpha operation and two arguments each; U/V addressing and min/mag/mip
filters. Sampler translation recognizes clamp value 3 and repeats other address
values, maps point to nearest and other min/mag values to linear. Mip values
1 and 2/3 choose nearest/linear mip interpolation. This does not preserve mirror,
border or anisotropic semantics. Combiner arguments recognize exact texture,
diffuse and current values; modifiers are not decoded and other arguments become
previous. Unsupported RGB operations pass through previous. These are
`boundary_replaced` with explicitly partial value domains, not feature acceptance.
Source references, retail value reachability, independent routes and pixels
remain open. Current totals: 25 missing, 26 boundary-replaced, 2,001 unknown.

Texture-coordinate index and transform flags have source-reviewed emulation
paths. Mesh/indexed submissions capture retained DX8 state, reset GL texture
matrices and emit CPU-generated pass-through, camera normal/position or reflection
coordinates. CPU row transforms handle count/projected flags with a near-zero
divisor guard and emit 2D output. Indexed UV selection uses UV1 only for source
1 and otherwise UV0. Direct boundary matrix loading is also present; route
ownership, count/value domains, nonuniform-scale normals and double-transform
avoidance remain verification tasks. These two rows are boundary-replaced,
not accepted environment/projector behavior. Totals: 25 missing, 28 replaced,
1,999 unknown.

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
