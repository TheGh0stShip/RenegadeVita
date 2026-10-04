# Surface normal transforms and projective texture boundary

## Corrected normal transformations

The direct native mesh lighting path previously multiplied a normal by the
world's linear transform and normalized it. Generated camera-space normal and
reflection coordinates did the same in both direct and indexed submissions.
With nonuniform scale or shear this fails to keep the normal perpendicular to
the transformed surface. Original geometry, material and mapper ownership are
unchanged by the correction.

`port/renderer/vita/normal_transform.h` computes the inverse transpose of a
column-vector 3x3 transform. Direct submissions extract the original Matrix3D
linear rows; indexed submissions transpose DX8's row-vector matrix explicitly.
Camera-space normals apply the world and view normal transforms in order.
Translation is excluded. Existing unit normalization and +Z fallback policy
are retained; singular transforms use that fallback. The separate indexed
primary-lighting evaluator already computes an inverse transpose and is not
changed by this correction. Its normalization switch remains independent.

The existing production-body material regression gains a nonuniform-scale
case. It failed before the correction and passes afterward. It now executes
the actual direct/world/indexed-camera functions for 1,000 reflected,
nonuniformly scaled, sheared and rotated transforms, checking perpendicularity
to transformed tangents and parity between both matrix conventions. A singular
case checks the fallback. Translation is present in indexed matrices and must
not affect normals. Existing 192,000 material-cache comparisons and 15,360
submitted-skin alpha comparisons remain in the same retained fixture.
The focused 21 tests pass with ASan/UBSan enabled for this production fixture.

These are correctness changes, not performance adoption. Host fixture timings
are not Vita frame-time evidence. Native lighting, generated-coordinate pixels,
skin routes and physical stability remain unverified.

Dev228 passes all 492 focused contracts and six incremental ARM compile/link
actions. ELF inspection confirms ELF32 little-endian ARMv7/EABI5 and VFP
register arguments. Existing mixed wchar_t ABI warnings remain unresolved.
No SELF/VPK packaging, emulator launch or physical action occurred.

| Artifact | SHA-256 |
|---|---|
| Dev228 ELF | `6a14599c7348c0f17d57606d45c29c3f8f7f116af4ade31900334b92ebcfa47c` |
| Dev228 map | `d34b2c8fa147d936db50450bae7150ec5828da221a4404e0ff43f4fc0b5e8b61` |
| Normal helper | `9f27793b4a1b4758d73b1e5e8f0536dbd9e3717d67fb10d97d04f97aca2b1f9b` |

Retained log: `local-builder/logs/a35-dev228-fast-20261004-125126-build.log`.

## Projective interpolation remains open

Original `upstream/CnC_Renegade/Code/ww3d2/mapper.cpp` sends camera-space position
with `D3DTTFF_PROJECTED | D3DTTFF_COUNT3` and constructs its texture transform
to use the projection divisor. The native renderer's
`Apply_DX8_Texture_Transform` currently divides the coordinates at each vertex
and emits only `glMultiTexCoord2f`. That loses the divisor before rasterization;
variable-divisor projective interpolation is not preserved.

The pinned vitaGL revision is
`6e7fe40292e8f1d10f9a94ff2cd2f4fb1ba452a5`. Inspected source boundaries:

- `build/deps/vitagl-demo/source/source/vitaGL.h`: only two-component immediate
  texture-coordinate entry points are declared.
- `source/ffp.c` in that dependency: immediate vertex state stores two-component
  UVs, and `glMultiTexCoord2f` writes their X/Y components.
- `source/shaders/ffp_v.h` and `ffp_f.h`: texture varyings are float2; the vertex
  transform retains only XY. A four-component application call alone cannot
  fix this shader/storage boundary.

Read-only comparison of the adjacent D3DVita project's `docs/ROADMAP.md` retains
generated/projected texture coordinates as unfinished. No backend switch,
dependency import, or modification to that project occurred.

Required follow-up: preserve S/T/divisor through the existing vitaGL immediate
storage, indexed/compact paths and shader interface, perform division after
perspective interpolation, preserve nonprojected behavior and sampler/combiner
ownership, and add variable-W/divisor reference tests. Stage any dependency
patch deterministically from its pinned archive with provenance and archive
ABI checks. Compile every affected shader variant and inspect native images
before claiming support. Zero-divisor behavior, multiple texture stages,
shader-cache invalidation and memory/stride changes require explicit tests.
This remains a full-game rendering requirement, not an optional cosmetic effect.
