# Stealth unit rendering (M07 park, M08 stealth tank, M09, M10, M11 Petrova soldiers)

Evidence class: source inspection of the staged ww3d2/wwphys/combat tree and the
Vita renderer boundary on 2026-10-07. No build, host test, Vita3K run or
physical run was performed for this review, and no pixel, frame-cost or visual
correctness claim is made. Every "supported" below means "the source path is
present and consistent with the original DX8 contract", not "observed".

## 1. What the original stealth effect needs

`StealthEffectClass` (`staging/wwphys/stealtheffect.cpp`, unmodified upstream
logic) is a `MaterialEffectClass` attached to the object's `PhysClass` by
`SmartGameObj::Alloc_Stealth_Effect` / `Add_Effect_To_Me`. The first-person
"hands" physics object shares the player's effect (`weaponview.cpp:521`).

Per frame:

- `Timestep` (driven by `PhysicsSceneClass::Update` ->
  `MaterialEffectClass::Timestep_All_Effects`, pscene.cpp:407) moves
  `CurrentFraction` toward `TargetFraction` at 0.5/s and derives
  `IntensityScale = 1 - 2*|CurrentFraction - 0.5|`, a UV scroll offset, and
  `RenderBaseMaterial = (CurrentFraction < 0.5)`.
- Target fractions: hostile 1.0, friendly 0.75, broken (<25% health) 0.25,
  disabled 0.0.
- `Render_Push` (called from `PhysClass::Render` -> `Push_Effects`) adds up to
  +0.40 intensity when the camera is inside `FadeDistance` (defaults: 15 m human,
  25 m vehicle; `globalsettings.cpp`, retail database may override), then, if
  `IntensityScale > 0`, writes emissive = intensity and a texture-transform
  offset into the shared `MaterialPassClass` and calls
  `rinfo.Push_Material_Pass`. If `RenderBaseMaterial` is false it also pushes
  `RINFO_OVERRIDE_ADDITIONAL_PASSES_ONLY`, which suppresses the base geometry.
- By design a hostile, undamaged, fully cloaked unit (fraction 1.0) at
  distance > FadeDistance has intensity 0: no base pass and no stealth pass, i.e.
  genuinely invisible on the original PC. A friendly one (0.75) shows at
  intensity 0.5. This is gameplay, not a port defect.
- `Is_Stealthed()` is `CurrentFraction > 0.5` and independently drives
  targeting suppression (`ccamera.cpp:1104`) and vehicle emitter suppression
  (`vehicle.cpp:1784`). Those are logic paths and do not depend on the renderer.

The procedural pass (built once in the constructor):

| Item | Value |
| --- | --- |
| Texture | stage 0 only, `stealth_effect.tga` (retail member `stealth_effect.dds` in always.dat: DXT1, 128x128, 8 mips; `reports/generated/sweeps/dds_formats.json`) |
| Shader | `ShaderClass::_PresetAdditiveShader`: depth LEQUAL, depth write off, colour write on, src ONE / dst ONE, no fog, primary gradient MODULATE, texturing on, alpha test off, back-face cull on. (The constructor's local `shader` with `GRADIENT_ADD` is never applied in the original either; preserved as-is.) |
| Vertex material | lighting on, ambient/diffuse/specular 0, emissive = intensity, opacity 1, all colour sources MATERIAL |
| Texture coordinates | `MatrixMapperClass` stage 0, `ORTHO_PROJECTION`. `Apply` sets `D3DTS_TEXTURE0` to `ViewToPixel`, `TEXCOORDINDEX = D3DTSS_TCI_CAMERASPACEPOSITION`, `TEXTURETRANSFORMFLAGS = D3DTTFF_COUNT2` |
| Other | `Enable_On_Translucent_Meshes(false)`; null cull volume (no per-polygon APT) |

Resulting pixel colour is `texture * emissive` added to the framebuffer. UVs are
`s = k*(x + 1 + offU)`, `t = k*(1 - y + offV)` of the camera-space vertex
position (k = 0.5*62/64), so the shimmer is a view-aligned orthographic
projection that scrolls with `UVOffset`; it does not use mesh UVs.

What it does NOT need: no render target, no framebuffer copy/refraction, no
bump-env map, no second texture stage, no vertex/pixel shader, no projective
divide (`D3DTTFF_PROJECTED` is not set), no stencil.

## 2. Vita path, stage by stage

| Requirement | Vita implementation | Status (source) |
| --- | --- | --- |
| Additional pass reaches the renderer | `PhysClass::Render` -> `MeshClass::Render` Vita branch (`staging/ww3d2/mesh.cpp` ~738-775, patch `port/patches/ww3d2-a36-native-material-pass-queue.patch`) iterates `rinfo.Additional_Pass_Count()`, honours `Is_Translucent` / `Is_Enabled_On_Translucent_Meshes`, and calls `TheDX8MeshRenderer.Queue_Material_Pass(pass, mesh, skin, delayed)` | Present |
| Base suppression | Same branch skips `Submit_Mesh` when `ADDITIONAL_PASSES_ONLY` is active (shadow-rendering alpha exception preserved) | Present, original semantics |
| Retained pass lifetime and order | `port/renderer/vita/ww3d_dx8_boundary.cpp`: refcounted FIFO tasks (`NativeMaterialPassTask` holds pass + mesh refs), rigid queue, skin queue, delayed rigid queue; `Flush` drains rigid, skin, decals, delayed rigid. `WW3D::Flush` (Vita branch) sets camera then flushes, then static-sort lists | Present |
| Draw with pass material/shader/texture | `RenegadeVitaRenderer::Submit_Material_Pass` -> `Submit_Mesh_Internal(..., &pass)` (`ww3d_vita_renderer.cpp:3722-4246`): `texture_for/shader_for/material_for` redirect to the pass, one draw pass, mesh pass-0 UV/DCG streams, static cache bypassed, textured-skin white passthrough disabled | Present |
| Skinned (stealth soldiers) | `Get_Deformed_Vertices` deformed copy, identity world, queued in the ordinary skin queue (matches the original skin container delegating delayed work to its ordinary queue) | Present |
| Rigid (stealth tanks) | Base suppressed -> delayed rigid queue, drawn after decals | Present |
| Additive blend, depth LEQUAL / no depth write, cull | `Apply_Original_Shader_State` translates `ShaderClass` bits (blend, depth func/mask, colour mask, cull, GRADIENT_MODULATE) | Present |
| Lit emissive colour | `Evaluate_Original_Material_Vertex_Color`: `ambient*ambientLight + emissive + sum(diffuse*N.L)`; with ambient 0 and diffuse 0 this reduces to emissive = intensity. Per-pass colour cache generation is bumped per mesh pass (`Begin_Material_Color_Pass`), so the per-frame emissive change is not served stale; the constant-colour cache is lighting-off only | Present |
| Mapper / texture transform | `Apply_Original_Texture_Coordinate_State(material)` calls `mapper->Apply`; the DX8 boundary stores `D3DTS_TEXTURE0` and stage state; `Capture_Original_Texture_Coordinate_State` reads them back and `Emit_Original_Texture_Coordinate` generates `CAMERASPACEPOSITION` coordinates on the CPU per vertex (`Compute_Camera_Space_Position` with the same view matrix WW3D uses) and applies `Apply_DX8_Texture_Transform` (row-vector convention, count 2, not projected). Stage state is reset to pass-through at the end of every submission, so it cannot leak into later draws | Present |
| Texture wrap | `TextureClass::Apply_For_Platform_Boundary` owns address mode; default (no clamp flag) is repeat, which the scrolling UVs require | Present (not independently verified on device) |
| Texture format | DXT1 is in `Texture_Format_Is_Supported` | Present |
| Render target use | None required | n/a |

The earlier note in `PROCEDURAL_MATERIAL_OWNER_REVIEW.md` that native
`MeshClass` rejected additional passes describes the state before the
2026-10-05 retained queue; the current tree has the queue. The generated gap
rows in `FULL_PORT_GAP_REGISTER.md` (port_guards 3362/3536/3537) predate it.

## 3. Behaviour when a stage is unsupported or fails

Because the base is suppressed whenever fraction >= 0.5, the failure direction
depends on which stage fails. For stealth the dangerous direction is
"invisible", not "fully visible".

| Failure | Effect on the unit | Gameplay impact |
| --- | --- | --- |
| `Queue_Material_Pass` returns false (null, or task allocation failure) | `Submit_Unsupported(mesh)` increments `unsupported_submissions` and logs one breadcrumb; base already suppressed -> unit fully INVISIBLE, no shimmer | Unit cannot be seen at any range even inside FadeDistance. Only reachable on out-of-memory |
| Skin scratch allocation failure in `Submit_Mesh_Internal` | Returns before drawing; `skin_deformation_failures` and `backend_errors` increment -> INVISIBLE | Same |
| `Flush` with no camera | Queues drained without drawing -> INVISIBLE | Not reachable from the Vita `WW3D::Flush`, which sets the camera first |
| Texture NULL / load failure | Pass still drawn, stage 0 unbound with texturing enabled: additive flat silhouette of colour = intensity (white, scaled) | VISIBLE, brighter and un-animated; a diagnostic checkerboard texture would show as an additive checker |
| Texture transform / stage state ignored | Static (non-scrolling) texture projected in view space | Visible shimmer, no animation |
| `IntensityScale <= 0` (hostile, fraction 1.0, beyond FadeDistance) | No pass queued by design | INVISIBLE, same as PC |
| Translucent sub-mesh (glass/lights) of a stealth object | Pass disabled on translucent meshes by original flag, base suppressed | Those sub-meshes vanish, same as PC |

There is no fallback that forces base geometry visible, deliberately: the
repository rule is not to introduce forced visibility, and a visible fallback
would also change the original gameplay (stealth units are meant to be hard to
see).

## 4. Defects and risks found

No clear code defect was found in the stealth path, so no source was changed.
The remaining risks are evidence gaps, in priority order:

1. The retained material-pass queue and the stealth pass have no physical,
   emulator or ARM-run evidence in the reports; the queue lives in
   `ww3d_dx8_boundary.cpp` and the `mesh.cpp` patch only. Stealth pixels, wrap
   mode, UV scale and cost are unobserved.
2. Failure is silent for gameplay: an OOM in the queue yields invisible enemies
   with a single one-shot breadcrumb. Statistics `unsupported_submissions` and
   `backend_errors` must be zero in a stealth mission log.
3. Pass state is shared and mutable (`Render_Push` rewrites emissive and the
   texture transform on one `MaterialPassClass`; draws occur later at flush).
   The player's first-person hands share the effect, so `Render_Push` runs more
   than once per frame and the last write wins for every queued task. The
   original deferred FVF queue has the same property; do not "fix" it.
4. Draw order: stealth passes draw at `Flush` after all direct base draws and
   before the sorted/translucent lists. Additive, no-depth-write passes are
   order independent among themselves; interleaving with desktop FVF categories
   is not reproduced (already documented in the owner review).
5. Frame cost of stealth units (extra immediate-mode draw per mesh, skin
   deformation still performed) is unmeasured; M11 Petrova reinforcements and
   M10 stealth groups are the likely worst cases.

## 5. Evidence to collect on the next physical candidate (M08)

From the runtime log, in a mission with an active stealth unit in view:

- `unsupported_submissions` = 0 and no `unsupported-submit` breadcrumb naming a
  stealth tank / soldier mesh; no `material-pass` "invalid rigid APT" breadcrumb
  (should not occur, cull volume is null).
- `material_passes` / `mesh_submissions` growth consistent with stealth meshes
  being drawn.
- The existing one-shot breadcrumb `first generated texture coordinates:
  stage=0 mode=00020000 flags=00000002` (`D3DTSS_TCI_CAMERASPACEPOSITION`,
  `D3DTTFF_COUNT2`) confirms the generated-coordinate route executed; the
  `first original VertexMaterial mapper` breadcrumb confirms mapper dispatch.
  Either can fire first for other content, so match the stage/flags and mission.
- A capture or user observation (not a log) of a hostile stealth tank inside
  and outside FadeDistance; visual fidelity cannot be inferred from the log.

## 6. Source map

- `staging/wwphys/stealtheffect.{h,cpp}`, `materialeffect.{h,cpp}`, `phys.cpp`
  (Push/Pop_Effects), `pscene.cpp` (effect timestep), `physresourcemgr.cpp`
  (stealth texture).
- `staging/combat/smartgameobj.cpp` (alloc, friendly/broken/damage, powerup and
  firing timers), `vehicle.cpp:1623`, `weaponview.cpp:521`, `ccamera.cpp:1104`.
- `staging/ww3d2/mesh.cpp`, `matrixmapper.cpp`, `rinfo.cpp`, `shader.cpp`,
  `vertmaterial.cpp`, `ww3d.cpp` (Flush).
- `port/renderer/vita/ww3d_dx8_boundary.cpp` (queue, texture transform state),
  `port/renderer/vita/ww3d_vita_renderer.cpp` (`Submit_Mesh_Internal`,
  texture coordinate generation, shader/colour evaluation).
- Missions using stealth units: M07 (parked stealth tank), M08 (player and Nod
  stealth tanks, stealth trap), M09 (stationary stealth tank), M10 (stealth
  drop/attack scripts), M11 (Petrova stealth soldiers); see the per-mission
  readiness reports and `CAMPAIGN_VEHICLES.md`.
