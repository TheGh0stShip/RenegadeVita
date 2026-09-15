# Dev111 follow-up: original culling inversion

The user reported intermittent black geometry intruding into the view in both
M00 elevators. No matching capture yet establishes the root cause.

Source inspection found a definite state-translation omission in
`port/renderer/vita/ww3d_vita_renderer.cpp`:

- `Apply_Original_Shader_State` always used `GL_BACK` when culling was enabled.
- Its reuse key contained only `ShaderClass::Get_Bits()`.
- The original engine exposes global inversion separately through
  `ShaderClass::Is_Backface_Culling_Inverted()`.

The native shader path now selects `GL_FRONT` when that original flag is set
and includes the flag in cache identity. Normal culling and disabled culling
are unchanged. This complements the earlier direct `D3DRS_CULLMODE` mapping
correction; it does not change geometry, camera clipping, or asset data.

Status: source correction only, not part of the installed dev111 package.
ARM compilation and matching elevator captures remain required. Do not claim
the elevator artifact or unrelated HUD/font defects are resolved by this edit.

Next runtime check: replay both elevators, inspect nearby surfaces while the
camera moves, and compare against the same candidate's retained source identity.
