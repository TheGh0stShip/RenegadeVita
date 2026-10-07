# Range (radial) fog analysis

## Original behavior
`staging/ww3d2/dx8wrapper.cpp:355` (`Set_Default_Global_Render_States`) turns on
`D3DRS_RANGEFOGENABLE` when the device reports `D3DPRASTERCAPS_FOGRANGE`, and
uses `D3DFOG_LINEAR` vertex fog. The fog factor therefore comes from eye-space
radial distance `|P_eye|`, not planar depth.

## vitaGL used by this repo
Source: `build/deps/vitagl-demo/source`. I found no vitaGL fog patches in
`dependency-patches/` or `tools/`.

- Nothing in the tree supports `GL_FOG_DISTANCE_MODE_NV`, `GL_EYE_RADIAL_NV` or
  `GL_FOG_COORD`.
- The FFP fragment shaders (`source/shaders/ffp_f.h:190`, `ffp_ext_f.h:186`)
  compute `fog_dist = coords.z / coords.w` (planar depth) for
  LINEAR, EXP and EXP2. Fog is planar only, with no radial mode.
- The Vita backend sets fog with `glFog*` in
  `port/renderer/vita/ww3d_vita_renderer.cpp`.

## Visual impact
At the same Z, planar fog is lighter at the screen edges than radial fog. The
gap scales with 1/cos(theta) from the view axis, which is roughly 15-30% at the
edges for typical Renegade FOVs. Fog density on an object can also change as the
camera rotates. This is expected from the math and has not been checked on
hardware.

## Options
1. Keep planar fog (current behavior). This costs nothing but is a small fidelity
   deviation. Record it in KNOWN_GAPS.
2. Add a vitaGL dependency patch: pass the eye-space position to the FFP
   fragment shader and use `length(eyePos)` as `fog_dist`. Gate it behind
   `GL_FOG_DISTANCE_MODE_NV` / `GL_EYE_RADIAL_NV` state, which needs a new
   shader-cache key bit. Faithful, moderate effort, and the shader variants
   must be regenerated.
3. Write a custom shader path for W3D passes in the Vita backend. Faithful, but
   it bypasses FFP and costs more to maintain.
4. Scale fog start/end by the mean cos(theta) for the FOV. Cheap, but wrong at
   screen center. Not recommended.

Recommendation: use option 1 for now. Take option 2 during the v3.7 renderer
work, once a fixed-camera benchmark exists for comparing physical captures.
