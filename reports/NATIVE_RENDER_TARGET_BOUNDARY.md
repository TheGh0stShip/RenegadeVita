# Native render-target boundary

Status: source implementation present but uncompiled and unvalidated. No build,
runtime test or physical acceptance is claimed.

## Former ownership gap

Original `PhysicsSceneClass` obtains projector textures from
`DX8Wrapper::Create_Render_Target`, binds a `TextureClass` or its level-zero
`IDirect3DSurface8`, renders the projector camera, then restores the default
target with a null surface. Before the source implementation below, the Vita
boundary broke that ownership at three separate points:

- `port/renderer/vita/ww3d_dx8_boundary.cpp` returned null from
  `Create_Render_Target`.
- `port/platform/a31_gameplay_boundary.cpp` rejected both non-default
  `Set_Render_Target` overloads.
- `port/renderer/vita/d3d8.h` stored a native texture name but had no framebuffer,
  depth attachment, render-target flag or target-lifetime fields.

The adjacent `../d3dvita-demo` tree has the same deferred non-default target
boundary and supplies no proven FBO implementation to reuse. The installed
vitaGL API does expose framebuffer, texture attachment, renderbuffer and status
calls, but API presence is not lifecycle or hardware evidence.

## Implemented source boundary

1. The process-local DX8-shaped texture owner now has explicit render-target
   identity plus framebuffer/depth attachment handles. These fields remain
   outside serialized engine structures.
2. `_Create_DX8_Texture(..., rendertarget=true)` allocates one uncompressed
   level, attaches its existing native texture to a framebuffer, allocates the
   matching depth surface, verifies completeness, and restores the previously
   bound framebuffer on every success/failure path.
3. The final `IDirect3DBaseTexture8::Release` deletes framebuffer and depth
   resources before the native texture. Partial construction unwinds without
   changing ordinary texture destruction.
4. `Create_Render_Target` restores power-of-two square sizing and resolves
   `WW3D_FORMAT_UNKNOWN` to a supported display-compatible color format.
5. A surface has a read-only route to its owning texture/level. Binding rejects
   detached CPU surfaces and nonzero mip levels as render targets.
6. Both gameplay stubs now use one shared binder. It retains/releases both the
   current surface and its raw owning texture, binds the FBO, sets target-sized viewport state,
   invalidates texture/render caches affected by direct GL state, and sets
   `IsRenderToTexture` only after a complete bind.
7. A null target restores vitaGL's default framebuffer and the original logical
   display viewport, releases the retained custom target, invalidates the same
   caches, and clears `IsRenderToTexture` without inventing a desktop back buffer.
8. `Get_Render_Target_Resolution` reports active target dimensions while
   offscreen and the logical device dimensions otherwise. Camera projection and
   clear operations depend on this distinction.
9. `WW3D::Begin_Render` now carries the original `clear` and `clearz` requests
   into the native frame boundary. The renderer builds the GL clear mask from
   those independent requests, so an offscreen pass can preserve either color
   or depth exactly as its original caller requests instead of clearing both
   attachments unconditionally.
10. Original projector scene traversal, culling, material-pass queues, camera
   rendering and texture sampling remain owners. The platform boundary owns
   only target allocation, binding and restoration.
11. Render-target surface locks and `CopyRects` synchronize the GPU color image
    into the existing CPU surface, convert it back to the declared DX8 format,
    and flip OpenGL's bottom-up rows into the original top-down surface layout.
    This retains the original static-projector capability test rather than
    bypassing it with a forced success.
12. The retained active surface and texture now have an explicit logical
    renderer-shutdown release route. Shutdown first requests the default target,
    then releases both retained references and clears render-to-texture state
    even if the native default-framebuffer bind reports failure. A later WW3D
    logical session therefore cannot inherit an interrupted projector pass.

## Required evidence

- Host/source contracts: format fallback, POT sizing, target/surface ownership,
  partial-allocation unwind, reference balance, nested/repeated bind rejection,
  default restoration and active resolution.
- ARM: `arm-vita-eabi` compile/link, ELF attributes confirming ARMv7-A ILP32
  hard-float consistency, retained framebuffer symbols and package identity.
- Vita3K: install-only artifact identity first; any later runtime result remains
  emulator evidence.
- Physical Vita/PSTV: target completeness, projected pixels, correct orientation,
  depth behavior, viewport restoration, repeated level transitions, memory
  high-water, frame-time distribution and soak cleanup. Renegade hardware
  evidence is required separately on Vita and PSTV.

Until those gates pass, generated shadow maps remain unaccepted. Authored
projectors with existing textures and generated targets now have source routes,
but neither constitutes working native pixels without the listed evidence.
