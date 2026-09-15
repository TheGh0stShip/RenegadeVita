# Dev111 elevator rendering follow-up

User observation after the retained Vita3K run: intermittent black artifacts
intruded into the player's field of view in both elevators. This remains an
open demo correctness defect. Do not label it emulator-only or fixed from
backend error counters.

## Source evidence and narrow correction

The native `D3DRS_CULLMODE` handler mapped both `D3DCULL_CW` and
`D3DCULL_CCW` to `glCullFace(GL_BACK)`. Under the native counterclockwise-front
baseline, that discards clockwise faces for both DX8 modes. The handler now
selects GL_FRONT for D3DCULL_CCW, retaining GL_BACK for the normal CW mode and
disabled culling for D3DCULL_NONE. Existing render-state/shader-cache overlap
invalidation is unchanged.

Original `ShaderClass::Invert_Backface_Culling` switches `_PolygonCullMode`
between D3DCULL_CCW and D3DCULL_CW. Original ShaderClass::Apply passes that
mode through D3DRS_CULLMODE. The direct Vita mesh shader path separately
selects GL_BACK from a boolean culling flag; its handling of global inversion
and shader-cache identity still requires closure. This narrow correction is
not a claim that every shader culling path has been repaired.

The inspected mesh and indexed submission paths retain homogeneous projection
through vitaGL rather than CPU-dividing vertices to NDC. The inspected depth
conversion is `z_GL = 2*z_D3D - w`. No speculative near-plane change, camera
offset, elevator collision change, or triangle suppression was applied.

## Validation boundary and next proof

The direct-mode correction is source-only, not in the retained Dev111 package.
Its connection to the reported elevator artifacts is unproven. Required next
evidence is a fixed elevator entry/travel/exit route with matching captures,
camera/player/elevator transforms and cull-state transitions. Compare black
intrusions against camera contact and moving geometry before attributing cause.
Include this correction in the coherent HUD/pause/checkpoint follow-up rather
than producing a separate candidate just for this change.
