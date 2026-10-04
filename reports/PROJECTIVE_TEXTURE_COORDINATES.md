# Projective texture coordinates

## Original ownership and correction

Original WW3D mappers, material/state traversal, texture ownership and geometry
submission remain the owners. Original `ww3d2/mapper.cpp` supplies camera-space
position with `D3DTTFF_PROJECTED | D3DTTFF_COUNT3`. The Vita boundary previously
divided S/T per vertex, then discarded the divisor when emitting float2 UVs.
That interpolates vertex ratios instead of projecting interpolated coordinates.

`Apply_DX8_Texture_Transform` now returns S/T/divisor without division. COUNT2
projected coordinates use the second component as divisor and retain a zero T;
COUNT3 and COUNT4 use their third/fourth components. Nonprojected coordinates
retain divisor one. A pass-through two-component UV source is extended with
homogeneous third coordinate one for transformed coordinates. Zero and negative
endpoint divisors are retained; singular fragment behavior is not redefined.

Direct and indexed native draw batches select the same opt-in projective begin
boundary when their original captured state requests projection. Their emitters
send the three components through the pinned vitaGL extension. Existing texture
matrix reset, sampler/combiner ownership, geometry W and original material
state are retained. No alternate scene renderer or effect replacement is added.

## Pinned dependency

`vitagl-projective-immediate.patch` applies after the retained compact/indexed
patches to vitaGL revision `6e7fe40292e8f1d10f9a94ff2cd2f4fb1ba452a5`.
The build script restores all affected files from the pinned archive, applies
zero-fuzz patches and includes patch/source/compiler identities in provenance.

Ordinary immediate and client-array paths retain their prior layout and shader
keys. Projective immediate vertices add one float per active texture stage.
Copied attribute descriptors use three-component UVs and matching material
offsets/strides; the original descriptors are not modified. Both expanded and
indexed draws use this storage. A bounds check rejects an entire projective
primitive with an allocation error before a short vertex write; no partial
indexed draw or float2 fallback hides the failure.
The pool-end value is maintained even with the pinned error-checking-disable
flag, and null allocations retain a null end pointer for rejection before
writing. An initial ARM attempt exposed the formerly conditional declaration;
that failed log is retained rather than treated as a successful dependency build.

The unused high bit of the pinned two-stage shader key distinguishes the new
vertex and fragment variants, including persistent caches. Projective shaders
retain float3 S/T/divisor varyings and perform division in the fragment stage.
Nonprojected stages in a projective batch use divisor one. Fixed-array flags
cannot leak into the explicit float projective layout, and the fast/half
interpolation hint is disabled for this variant. Begin/end boundaries reset
extension state; two-component coordinate calls reset their stage's divisor.
The patch explicitly requires the existing pinned two-stage configuration;
the dependency's optional high-texture-unit profile is outside this build.

vitaGL is LGPLv3-or-later, as stated in its `source/ffp.c` header and
`COPYING.LESSER`. The patch and deterministic rebuild recipe are retained source
modifications; existing dependency licensing and source/relinking obligations
remain applicable. No SDK implementation, retail content or external port
source is copied.

## Retained validation

- The previous production transform fails the retained zero-endpoint divisor
  assertion through a signature-only observation adapter. The previous function
  body is unchanged in that reproduction.
- The current production transform passes 1,000 interpolation/reference cases
  under ASan/UBSan. The old per-vertex division disagrees in 985 cases.
  Disabled, COUNT1/2/3/4, UV translation, zero/negative endpoint divisors and
  either texture stage's projective begin selection are checked.
- Actual patched vitaGL emit/end bodies pass 24 lit/unlit, single/dual-stage,
  mixed projective/nonprojective and expanded/indexed cases under sanitizers.
  Attribute offsets, copied GPU indices, state reset and short-pool failure
  and null-allocation failure are observed. Ordinary baseline/compact/indexed
  checks remain retained.
- Forty-eight pinned shader-source variants preprocess with matching float2
  or float3 vertex/fragment interfaces, fragment division and template bounds.
  This is source validation, not GPU shader compilation. The dependency's
  shader compiler runs on Vita and has not been exercised for these variants.

Native shader compilation, projected pixels, original effect/mapper execution,
frame time, memory high-water and physical Vita/PSTV acceptance remain open.
Projector render targets and additional procedural material passes are separate
unresolved boundaries; this change does not establish their execution.

## Dev229 build evidence

The final fast gate passes 494 tests, the original DDS and render-state
executables pass 11/13 checks, and all six incremental ARM compile/link actions
pass. The rebuilt vitaGL archive has 30 members with ARMv7 and VFP-register
attributes. The final ELF is ELF32 little-endian ARMv7/EABI5 with VFP arguments;
both projective entry points are linked. Symbol retention is not runtime proof.
Existing mixed wchar_t warnings remain unresolved. No SELF/VPK packaging,
emulator launch or physical device action occurred.

| Artifact | SHA-256 |
|---|---|
| Dev229 ELF | `d20f154a7531010bac465b4d6caf834eb0a8f741b9233ceb6928f13913dc4e1d` |
| Dev229 map | `2566226fda99bdde7f310ddeab6ed4767926e420b3082de5ce08d5b13a294a0b` |
| vitaGL archive | `26992c253486e1eeaac0b9ef6f3ee7062e161491d07ca4465a60c075fe3f83b9` |
| Projective patch | `4733d1c7881302fd3b80c718895f169907fce8337e09dbb858f6228c0cdc91f3` |

Successful managed log:
`local-builder/logs/a35-dev229-fast-20261004-131043-build.log`.
Retained failed attempt:
`local-builder/logs/a35-dev229-fast-20261004-130853-build.log`.

Next acceptance needs actual Vita shader compilation for affected variants,
fixed-scene projected textures with varying geometry W/divisor, both stages,
ordinary/projective draw alternation, skin/rigid routes and original mapper
consumers. Compare pixels, memory high-water and frame-time tails on Vita and
PSTV. A native link or host preprocessor check cannot close those gates.
