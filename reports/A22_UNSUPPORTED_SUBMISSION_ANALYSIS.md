# A2.2 One-Per-Frame Unsupported Submission Analysis

## Result

The accepted physical A2.2 run's `23 frames / 23 unsupported submissions` was
not a missing mesh, material, texture, or GPU state operation. It was a
diagnostic false-positive at the Vita boundary for the hidden collision-box
child of the tank HLOD:

- object: `DSP_O2TANK.BOUNDINGBOX`
- `Class_ID`: `27` (`RenderObjClass::CLASSID_OBBOX`)
- original entry point: `OBBoxRenderObjClass::Render`
- classification: collision/debug `RenderObj` variant
- mesh/material/pass: not applicable
- physical visual consequence: none with the default collision-box display mask

The accepted hardware evidence remains historical and unchanged. Its value of
one per frame accurately describes that build's counter behavior, while this
analysis explains why the count did not represent a draw that WW3D intended to
submit.

## Reproduction evidence

A clean-restaged host run with a one-shot identity breadcrumb reported:

```text
A2.2 first unsupported RenderObj: name=DSP_O2TANK.BOUNDINGBOX class_id=27
```

The complete reproduction log is:

```text
<managed-log-root>/a22-20260807-205744-host-asset.log
```

The same frame still traversed all eight genuine meshes and retained the
semantic fingerprint `357 vertices / 324 triangles / 5704AB7D`.

## Original control flow and cause

`HLodClass::Render` traverses the current LOD's children, including the
oriented box named `BOUNDINGBOX`. The original `OBBoxRenderObjClass::Render`
sets the D3D world transform and calls `BoxRenderObjClass::render_box`.
`render_box` then deliberately returns unless both of these conditions hold:

1. the box-render helper is initialized; and
2. `DisplayMask & Get_Collision_Type()` is nonzero.

`BoxRenderObjClass::DisplayMask` defaults to zero. Collision boxes therefore
remain hidden in normal rendering and are only visualized when an explicit
debug/display mask enables their collision type.

The prior Vita branch replaced the entire method body with an unconditional
`Submit_Unsupported(this)`. It incremented the counter before the original
display-mask decision, even though the original renderer would not have made a
box draw submission. That placement caused exactly one false-positive per
HLOD traversal and explains the physical `23 / 23` ratio.

This does not affect the box's original collision behavior. Ray casts, swept
AABox/OBBox tests, intersections, HLOD bounding-volume use, transforms, and
ownership remain in the original Westwood classes and were not changed.

## Correction

The Vita AABox and OBBox render boundaries now preserve the original
high-level display decision before reporting an unimplemented box draw:

```cpp
if (Get_Box_Display_Mask() & Get_Collision_Type()) {
    RenegadeVitaRenderer::Submit_Unsupported(this);
}
```

If collision-box visualization is deliberately enabled later, it will still
be identified as a real deferred backend operation. With the normal default
mask, the active host fingerprint is now `unsupported=0`; mesh totals and the
geometry checksum are unchanged.

The change is represented in the deterministic
`port/patches/ww3d2-a22-vita-boundaries.patch` patch and is applied with zero
fuzz. Canonical upstream remains pristine.

## A3.0 impact

This operation does not block Commando/Combat startup or real world rendering.
It is optional collision-box debug visualization, not the collision/physics
representation itself. A3.0 should proceed without implementing its visual
box draw. If a later developer explicitly enables collision-box display, the
one-shot unsupported breadcrumb records the object name and class for that
genuine request.
