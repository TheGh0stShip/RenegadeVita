# Render-target path audit — candidate/render-target-flip (a3730e0)

Static source audit only (no build, no Vita run). Candidate negates clip Y in
`Build_Indexed_Transform_Matrices` while `g_active_render_target_width/height`
are non-zero, sets `glFrontFace(GL_CW)` on `Bind_Offscreen_Render_Target`,
restores `GL_CCW` on `Restore_Default_Render_Target`, maps offscreen viewport
Y directly (`viewport.y = d3d_y`), and drops the readback row flip.

| Path that can draw/affect pixels while a target is bound | Covered? | Notes |
|---|---|---|
| MeshClass submit (`ww3d_vita_renderer.cpp` ~3781, loads proj at 3789) | Yes | Uses Build_Indexed_Transform_Matrices. |
| Static mesh cache replay (`Submit_Static_Mesh_Cache` at 3815 → `Replay_Static_Mesh_Entry`) | Yes | Called after the 3789 projection load; no own matrix load. |
| Generic indexed / DX8 boundary draws, incl. Render2D/ortho, shadow/projector scene (`Submit_Indexed_Triangles` ~4316, load at 4366) | Yes | All original Set_Transform projections (ortho included) go through the same builder. No glOrtho in port. |
| TexProjectClass::Compute_Texture render (`staging/ww3d2/texproject.cpp` 1123–1142) and `staging/wwphys/pscene_projectors.cpp` shadows | Yes | Set_Render_Target → WW3D::Begin_Render/Render/End_Render → paths above. |
| Projector texgen / texture-stage matrix (`ww3d_dx8_boundary.cpp` `Apply_Texture_Stage_Transform`, glLoadMatrixf on GL_TEXTURE) | N/A (correct) | Affects sampling, not clip space; now consistent because FBO rows match D3D top-down UVs. |
| Clears (`Begin_Frame` glClear; `DX8Wrapper::Clear` → full-target Clear) | N/A | Full-target clears only; orientation-independent. Begin_Frame resets projection to identity, no draw with it. |
| Identity-baseline resets after submissions (4082, 4456, 3050) | N/A | No draws issued under identity; next draw rebuilds via builder. |
| Viewport (`Apply_Viewport` offscreen branch) | Yes | `y = d3d_y` is correct under negated clip Y (NDC −1 → FBO row 0 = D3D top). Full-target viewport set at bind. |
| Scissor | N/A | No glScissor / GL_SCISSOR_TEST use in port/renderer/vita. |
| Pre-transformed XYZRHW vertices | N/A | No XYZRHW path in renderer/boundary. |
| Culling (D3DRS_CULLMODE → glCullFace; line ~1017 culling_inverted) | Yes | glFrontFace(GL_CW) compensates mirrored winding; no other glFrontFace writes exist. |
| Render-target readback (`Readback_Render_Target_Surface`) | Yes | Row flip removed consistently. |
| Display capture glReadPixels (~4543) | N/A | Default framebuffer only, unaffected. |

## Conclusion

Every draw reachable while an offscreen target is bound loads its projection
through `Build_Indexed_Transform_Matrices`, so the flip covers all paths; clears
and scissor are orientation-neutral/unused. **Safe to merge from a code-path
standpoint**, subject to residual risks:

1. `Restore_Default_Render_Target` restores CCW only when width != 0; any
   future path binding an FBO without `Bind_Offscreen_Render_Target` would skip
   both the flip and front-face swap.
2. vitaGL native-state caches: confirm `Invalidate_Native_State_Cache` does not
   cache front-face state (it currently does not set it).
3. Physical/Vita3K visual check of projector shadows (upright, correct cull)
   is still required; this audit is not visual evidence.
