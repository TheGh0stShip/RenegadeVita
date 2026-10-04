# M13 development normal-preparation candidate

## Physical cost and hypothesis

Dev236 physical log SHA-256
`20dbb1446f16dbac8d8758da21d0b77055753543362571e5930731d8862fd429`
records severe M13 combat cost: at frame3840 cumulative average15.052 FPS,
rolling frame p50/p95/p99=191.016/301.962/490.461 ms, worst2.539 s.
Cumulative simulation/render averages are19.419/47.012 ms. The preceding
120-frame mesh sample window estimates5.707232 s in mesh submission and
0.445616 s in draw completion (47.560/3.713 ms per frame). These are stride16
CPU estimates, not exact profiling or GPU timestamps. Route/input differ
from earlier playthroughs; do not claim a comparative FPS gain.

Current lighting submission reconstructs the same world-space normal
cofactors and determinant per lit vertex. The original world transform is
fixed for the mesh pass, and the existing pass-local lighting preparation is
already scoped to that lifetime. Preparing the normal transform at that
boundary removes redundant arithmetic without caching across frames,
deformation, loads or changing original engine traversal.

## Dev238 change and correctness

`port/renderer/vita/normal_transform.h` separates preparation and application.
Application retains original multiply/add order and division by determinant;
there is no reciprocal approximation, fast-math, normalization omission or
scale/shear assumption. The existing convenience function still prepares
and applies for callers without reuse. Singular transforms retain failure.

`port/renderer/vita/ww3d_vita_renderer.cpp` prepares world normals alongside
light directions once per cached mesh pass. The existing cache mode2 switch
controls it; uncached mode keeps the prior path. Skin identity transforms,
light limits, source colors, opacity and original shader/draw ordering remain
the same. Storage is fixed pass-local floats and a flag, not scene residency.

The actual production material fixture compares a frozen pre-change arithmetic
oracle bit-for-bit across1,000 scale/shear/reflection transforms, checks normal
perpendicularity and singular output preservation, and checks192,000 material
comparisons including changed world transforms across passes. AddressSanitizer/
UndefinedBehaviorSanitizer pass on the focused normal/material checks; the
final singular preservation assertion passes in the final sanitized fixture.
The first full run exposed an outdated mesh-batch fixture stub accepting only
two preparation arguments. Its interface now accepts the world transform;
production mesh batch ordering/equivalence tests pass without weaker assertions.

An initial optimized host fixture reports isolated normal preparation
median/p95/p99/worst in microseconds4090.3/5616.8/6345.7/6345.7 before and
3266.6/3895.8/4172.9/4172.9 prepared. It ran alongside sanitizer work and is
only a directional host result. Sanitized timings are not performance evidence.
Retain the quiet full-build fixture measurements separately. None establishes
physical Vita improvement, pixels, memory high-water or combat playability.

The first full suite's isolated optimized fixture (no concurrent sanitizer)
reports4166.9/4538.0/4865.1/4865.1 microseconds before and
3600.8/4113.6/4137.5/4137.5 prepared: a13.6% host median reduction. That full
run failed only the outdated fixture interface above. The successful repeat
reports4480.5/5141.2/5642.1/5642.1 before and
3759.4/4279.6/4747.2/4747.2 prepared:16.1% lower median. This remains a host
result, not an FPS prediction.

## Gates and fixed hardware comparison

Dev238 passes all502 host checks and13 ARM/package build actions, plus11
DDSFileClass and13 original ShaderClass executable checks. Vita3K installed
hashes match without launch. Physical acceptance is pending.
Only VitaShell was running before physical replacement. Dev236 rollback SELF
was retained locally and the installed old hash verified. Dev238 replacement
used both hash guards and independent installed SELF readback verification.
No synthetic input or unrelated title/retail modification was performed.
Matching VPK was stored in the Renegade user directory. Launch is confirmed
as process153561863. The user has been asked for an untouched scripted opening
and first-fight observation. This is launch evidence, not gameplay or visual
acceptance. Future candidate pulls must use `a35-dev238-runtime.log`.
SELF SHA-256: `613e92c849f0a42e7c6a36f45b56b2e450eebd2351df2292e27fff178635d62b`.
ELF: `32d261345313e0e3aa343203aaa97038a5e3ba260e2421f0505814727a69d21e`.
VPK: `bc415eaac5f9e99aa318cf2ea5f90e2566c985bdb430ff9f495ae4b97a6c077f`.
Decision: development candidate, not adopted as a
verified physical performance improvement. Severe M13 playability remains open.

For a before/after hardware comparison use the same M13 difficulty, start,
camera, content and input segment. Prefer an early verified original save
once saving works, then a retained combat checkpoint. Record rolling
median/p95/p99/worst, sampled mesh/draw costs, CPU/GPU memory high-water,
visible lighting and controls, and audio behavior. Quicksave/crash/reload
costs are separate from ordinary frame statistics. Keep all original combat,
AI, physics, animation, scripts and level content; do not shorten the mission
or disable effects/actors to obtain a better number.
