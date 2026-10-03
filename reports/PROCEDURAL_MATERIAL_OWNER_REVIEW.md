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
