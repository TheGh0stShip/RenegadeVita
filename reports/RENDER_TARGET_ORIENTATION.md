# Render-target orientation (D3D top-down vs GL bottom-up)

Status: analysis only, unverified on hardware. No code changed.

## Evidence
- Upstream projector UVs assume D3D top-down texture space:
  `upstream/CnC_Renegade/Code/ww3d2/matrixmapper.cpp:132-135`
  (`s = (x/w+1)*0.5*K`, `t = (1 - y/w)*0.5*K`, i.e. v = 0.5 - 0.5y).
- Projectors render into offscreen targets via
  `texproject.cpp:1123` (`DX8Wrapper::Set_Render_Target(rtarget)`) and restore at `:1142`.
- Upstream sets/clears `IsRenderToTexture` at `dx8wrapper.cpp:2541,2569,2663`.
- Vita boundary defines it (`port/renderer/vita/ww3d_dx8_boundary.cpp:45`) but no
  renderer code reads it (grep of `port/renderer/vita` finds only the definition).
- FBO creation attaches the texture with no orientation handling:
  `ww3d_dx8_boundary.cpp:1032-1056`.
- The port already knows GL storage is bottom-up: readback flips rows
  (`ww3d_dx8_boundary.cpp:2374-2385`, source row `Height-1-y`). Sampling paths do not.
- Cull mapping assumes a fixed winding: `ww3d_vita_renderer.cpp:3500-3510`.

Consequence: geometry rendered into an FBO lands with GL row 0 at the bottom;
sampling with D3D v (v=0 top) reads it vertically mirrored. Projected textures /
shadow blobs from render targets appear upside down (static file textures are
unaffected because upload writes row 0 at v=0).

## Fix design (preferred: flip at render time)
While an offscreen target is bound (`IsRenderToTexture` true, or the bound FBO != 0):
1. Post-multiply projection by `diag(1,-1,1,1)` (negate clip Y) in the
   transform upload path, so row 0 of the FBO holds the top of the image.
2. Swap winding: `glFrontFace(GL_CW)` while bound (or invert the
   `D3DCULL_CW/CCW -> GL_BACK/GL_FRONT` choice at `ww3d_vita_renderer.cpp:3509`).
3. Flip viewport/scissor Y for the FBO (`y' = H - y - h`) when D3D viewports
   are sub-rect.
4. Remove the row flip in readback (`ww3d_dx8_boundary.cpp:2381`) for FBO-backed
   textures, since storage now matches D3D order.
Re-apply 1-3 on every Set_Render_Target transition (state is cached; mark
transform/cull/viewport dirty).

Alternative: flip at sample time (v' = 1 - v via texture matrix) for stages
bound to render-target textures. Smaller blast radius for 3D, but every
consumer (2D blits, readback, TexProject mappers) needs to know the texture's
origin, so it is more error-prone.

## Validation
Host: render a known asymmetric quad to RT, read back, assert top row colour.
Vita: compare a projector/shadow scene with PC reference capture.
