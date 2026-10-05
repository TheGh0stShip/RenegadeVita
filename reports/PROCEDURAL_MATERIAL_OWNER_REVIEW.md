# Required procedural material paths

Source review on 2026-10-03 confirms unfinished native additional material-pass
support beyond the separately restored dazzle and decal paths.

TransitionEffectClass native Render_Push and Render_Pop return immediately.
Original CombatMaterialEffectManager supplies transition effects for physical
object spawning, corpse/powerup death, soldier healing and electrocution.
Textures are REN_spawn, REN_death, REN_repair and REN_shock. These effects are
original gameplay presentation consumers, not merely designer debug overlays.
Per-mission runtime instances and texture loading remain unverified.

StealthEffectClass retains original material-pass push/pop and can select
ADDITIONAL_PASSES_ONLY when its base material is suppressed. Native MeshClass
still rejects additional passes. Thus the inspected source path can omit both
base and stealth presentation; no observed physical disappearance is claimed.
Grid and generic material effects, and texture projectors, also push passes.
Physics visibility/backface debugging shares the interface but does not define
the gameplay requirement.

Original mesh traversal filters passes on translucent meshes, queues ordinary
passes and delays passes when base rendering is suppressed. Original rendering
installs pass material/shader/textures, retains skin deformation, and supports
per-polygon cull volumes through generated APT index lists. It consumes original
polygon renderers/category buffers. Native base submission bypasses that
registration. Removing the transition guard or calling Render_Material_Pass
alone therefore does not close the path.

The correction must retain original MaterialPass/RenderInfo/effect ownership,
texture mapper and material evaluation, translucent filtering, deferred order,
skin geometry, cull-volume polygon selection and state/lifetime handling while
using the established native buffer/draw boundary. It must not replace effects
with opaque base meshes or a separate scene renderer. Compare actual tutorial,
M13 and M01 effect instances and matching native captures before acceptance.

Further queue/lifetime trace: original MatPassTaskClass adds references to both
MaterialPass and Mesh on construction and releases both on deletion after the
draw. Visible procedural tasks append FIFO within their FVF category. Rigid
suppressed-base tasks append to a separate delayed FIFO; its flush binds the
category vertex/index buffers, draws and clears head/tail. The skin container's
delayed entry point delegates to its ordinary queue. Skin rendering deforms
vertices, fills both UV sets and diffuse colors, sets each mesh's base offset,
binds the dynamic buffer, draws categories and procedural tasks, then clears
visible skin state. Native Submit_Mesh instead reads only model base passes.
Do not replace these rules with borrowed pointers, one global delayed queue,
or an unregistered polygon-renderer call.

Evidence is source inspection only. No correction or native acceptance is
claimed in this review, and no build or launch was performed.

## 2026-10-05 rejected direct-queue approach

A first implementation attempted to register only meshes carrying additional
passes and reuse the released FVF/material queues. Link-graph inspection then
showed that native targets select `port/renderer/vita/ww3d_dx8_boundary.cpp`,
whose reduced `DX8MeshRendererClass` implements only the native decal lifecycle.
The desktop `dx8renderer.cpp` definitions for `Register_Mesh_Type`, FVF
containers, material queues and visible skins are excluded. The approach would
therefore produce unresolved native symbols; its source and staging selection
were removed, and the existing transition-effect guard was restored.

The viable choices remain a native material-pass task layer that retains the
original queue and draw semantics, or replacing the reduced mesh boundary with
the complete original renderer while resolving duplicate definitions and
proving its buffer path. No fallback base rendering or forced visibility was
introduced. Projector render-target creation remains separate. No staging,
build, test or runtime operation was performed.
## Native retained-pass implementation

The current local source now factors `Submit_Mesh` through an internal optional
`MaterialPassClass` override while existing base callers still pass null. The
override selects its uniform material, shader and textures, draws one pass,
reuses model pass-zero UV/DCG streams, bypasses the static base cache, and keeps
the textured-skin white passthrough disabled so animated emissive intensity is
not erased.

The reduced native `DX8MeshRendererClass` now owns refcounted FIFO tasks for
ordinary rigid, ordinary skinned and delayed rigid passes. It reconstructs a
short-lived RenderInfo from the renderer camera and the retained Mesh's original
lighting environment, drains ordinary rigid then skinned work, renders decals,
then drains delayed rigid work. Invalidation, shutdown and a flush without a
camera release every retained owner. Static-sort levels install their camera and
flush their own queued passes. `TransitionEffectClass` again uses the original
Push/Pop owner, so transition and stealth passes with null cull volumes reach the
native emitter.

This remains source-only and unvalidated. The native queues preserve the
original broad class ordering, but they do not reproduce desktop FVF-category
interleaving because the native base renderer submits geometry directly. Rigid
passes with a non-null cull volume now reproduce the original orthogonal inverse
world-to-model box transform, view-direction derivation, cull-tree or backface
APT generation, and returned triangle order. Skinned procedural passes continue
to draw the complete deformed mesh, matching the original branch that precedes
per-polygon culling. Projector pixels, texture mapper state and repeat lifecycle
still require compile and runtime evidence before generic projector effects can
be claimed.

The native emitter now includes the `SimpleDynVecClass` declaration explicitly
and validates the complete generated rigid APT before drawing. An out-of-range
polygon ID rejects the procedural submission, increments the backend error
count, and emits one bounded native breadcrumb. It is no longer silently
deleted from the list, which could turn corrupt culling output into a plausible
but incorrect partial effect. This remains source-inspection evidence only.

The native DX8 boundary also restores the released sorting-buffer conversion:
when both retained buffers are sorting buffers, it copies the declared vertex
window and rebased indices into the original dynamic DX8-shaped buffers before
calling the established indexed submitter. Range validation rejects malformed
indices rather than underflowing during rebasing. `SortingRendererClass` keeps
ownership of insertion, global depth order and flush timing; the boundary only
replaces the released Direct3D upload/draw edge. This is uncompiled source
evidence and does not establish transparent rendering correctness.

## Original projector enablement ownership

The full native gameplay boundary previously disabled both static and dynamic
projectors and forced `SHADOW_MODE_NONE` on every scene after original settings
had initialized it. That removed authored projectors with existing textures as
well as render-target shadows, even though the retained material-pass queue can
now submit the former. The blanket override is removed. Original scene and
system-setting state again decide whether each projector list runs, while the
still-unsupported render-target allocation fails explicitly through
`DX8Wrapper::Create_Render_Target` and the original null/fallback handling.

This does not claim generated shadow-map support. Static/dynamic authored
projectors, culling, projected UVs, null render-target fallback, frame cost and
repeat lifecycle remain uncompiled and physically unverified.

The complete allocation/bind/restore ownership requirements and the finding
that the adjacent D3D Vita tree also defers this boundary are recorded in
`NATIVE_RENDER_TARGET_BOUNDARY.md`.
