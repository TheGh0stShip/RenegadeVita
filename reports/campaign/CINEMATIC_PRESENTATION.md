# Cinematic presentation: letterbox, screen fade, camera control

Scope: how original `ScreenFadeManager` letterbox/fade state reaches the Vita
renderer, whether it covers the 960x544 output including the native
presentation rect, and whether it resets between sessions.

Evidence class: static source trace plus a read-only scan of the user's local
retail `Data/` cinematic control scripts (no retail bytes copied). No build, no
Vita3K run, no physical Vita. Nothing here asserts visual correctness.

## Verdict

No clear coverage, ordering or reset defect was found, so no runtime source was
changed. One latent hazard (half-pixel UV bias) is currently inert and is now
pinned by a source-contract test. Residual risks are listed below.

## Path from script to pixels

1. Retail cinematic text (`Test_Cinematic` Parse_Command) calls
   `Commands->Enable_Letterbox / Set_Screen_Fade_Color / Set_Screen_Fade_Opacity`.
   `staging/combat/scriptcommands.cpp` forwards to
   `ScreenFadeManager::Enable_Letterbox / Set_Screen_Overlay_Color /
   Set_Screen_Overlay_Opacity` (original, unmodified routing).
2. `ScreenFadeManager` (original `screenfademanager.cpp`; only the A3.6
   save/load admission patch `combat-a36-screen-fade-admission.patch`
   differs) keeps five file-static `FloatInterpolatorClass` values (letterbox
   fraction, opacity, R, G, B). `Think()` advances them by
   `TimeManager::Get_Frame_Seconds()` and rebuilds one `Render2DClass`:
   - overlay quad `RectClass(-1,-1,1,1)` in a normalized 0..1 coordinate range
     (the second `Set_Coordinate_Range(0,0,1,1)` in `Init()` wins), which maps
     to NDC -3..1 / -1..3 and therefore over-covers the whole NDC square;
   - letterbox bars `(0,0,1,lsize)` and `(0,1-lsize,1,1)`, `lsize = fraction *
     0.125`, i.e. 12.5 percent of screen height each (68 px of 544 at full).
   Because geometry is normalized, it does not depend on the logical screen
   resolution that is current when `Think()` runs.
3. `CombatManager::Render()` calls `HUDClass::Render()` then
   `ScreenFadeManager::Render()` last, inside
   `A31_Vita_Begin/End_Original_HUD_Render()` (patch
   `combat-a35-vita-hud-presentation-boundary.patch`). Both the original
   `CombatGameModeClass` path and the native `a31_gameplay_boundary.cpp` frame
   path call `CombatManager::Render()`; overlays/radio/message window draw
   after it exactly as in the original game-mode order.
4. The scope (`A31GameplayHUDRenderPresentation`) sets the native presentation
   rect to `0,0,DISPLAY_WIDTH,DISPLAY_HEIGHT` (960x544) and Render2D screen
   resolution to 960x544, then restores both on exit.
5. `Render2DClass::Render()` (original) sets a viewport of
   `0,0,Get_Device_Resolution` (960x544 in gameplay), identity world/view/
   projection, `PRELIT_DIFFUSE`, default 2D shader (src-alpha/inv-src-alpha,
   depth always, no depth write, texturing off when no texture), then
   `DX8Wrapper::Draw_Triangles`. In the Vita boundary
   `IDirect3DDevice8::SetViewport` -> `RenegadeVitaRenderer::Apply_Viewport` ->
   `Build_Native_Viewport` scales through the presentation rect; with the full
   rect and logical == device it yields native viewport 0,0,960,544. The
   renderer contains no `glScissor`/`GL_SCISSOR_TEST`, and diffuse ARGB maps to
   `glColor4ub` with alpha from the top byte.

## Coverage conclusions

- Gameplay (including cinematics and the M13 finale): fades and bars cover the
  whole 960x544 framebuffer. The overlay over-covers; the bars are exactly the
  full width and top/bottom 12.5 percent.
- Loading (640x480) and frontend (800x600) use aspect-preserved presentation
  rects. `ScreenFadeManager::Render` is not called in those scopes, so the
  fade is not clipped to a 4:3 rect there. If a future caller drew the fade
  while one of those rects is active it would cover only that rect.
- Half-pixel bias hazard: on desktop, `ConsoleGameModeClass::Load_Registry_Keys`
  turns `WW3D::Set_Screen_UV_Bias` on (registry default 1). That shifts Render2D
  quads by -0.5 px, correct for D3D8 pixel centers but, under GL pixel centers,
  it would leave a 0.5 px sliver on the right edge and bottom edge of the
  letterbox bars. On Vita `console.cpp` is not built, `ConsoleGameModeClass` is
  stubbed in `a31_network_options_boundary.cpp`, nothing calls
  `Set_Screen_UV_Bias`, and `WW3D::IsScreenUVBiased` stays `false`, so quads are
  exact. Do not enable the bias at the Vita boundary without compensating.

## Session reset

- `CombatManager::Pre_Load_Level` (called by the original `combatgmode.cpp`
  load and by the native Vita loader) runs `Enable_Letterbox(0,0)` and
  `Set_Screen_Overlay_Opacity(0,0)`, plus `HUDClass::Enable(true)/Reset()`. So
  every new session starts with no bars and no overlay even if the previous one
  ended mid-cinematic (quit, death, mission-complete before the script cleared).
- `CombatManager::Unload_Level` (staged Vita fix) clears the camera host
  (`MainCamera->Set_Host_Model(NULL)`) and the cinematic freeze before objects
  are destroyed.
- Overlay color is not reset (original behavior). This is harmless: in the 12
  retail cinematic scripts present in the local install, every script issues
  `Set_Screen_Fade_Color` before the first non-zero opacity, and 11 end with an
  instant `Enable_Letterbox 0,0` and `Set_Screen_Fade_Opacity 0,0`. The twelfth
  (`x6b_midtro.txt`, M06) ends with a timed fade-out (0.5 s opacity, 1 s
  letterbox) that completes normally. Scripts from missions not in the local
  copy (for example M09, M12) were not scanned.
- `ScreenFadeManager::Shutdown` deletes the renderer but leaves the statics;
  `Think()`/`Render()` dereference `_Renderer` unguarded (original). They are
  only reached while Combat is initialized, so this is not a reachable defect
  today.
- Save/load: the five interpolators round-trip as the 15th Combat child chunk
  and the load is now strictly admitted (A3.6 patch); a restored fade state is
  intentional original behavior.

## M13 finale (`x0z_finale.txt`) as authored

Frame times are negative-prefixed frame counts (30 per second). In order:
letterbox on over 1 s; color white instant; opacity 1 instant (full white
flash) then to 0 over 3 s; at frame 410 color black instant and opacity to 1
over 1 s (fade to black); at frame 440 letterbox off and opacity 0, both
instant. The script only takes `Control_Camera` slot 0 and never releases it
(no -1), so the camera host and cinematic freeze rely on `Unload_Level`
cleanup plus `Pre_Load_Level` HUD re-enable at the next session. The Vita
paths exercised are instant/timed interpolation, ARGB diffuse alpha blending of
an untextured quad, and full-viewport coverage.

## Camera control

`Command_Control_Camera` sets the camera host, disables the star's controls and
HUD, and enters/leaves cinematic freeze; release (-1) restores them. This
report did not change it. Session-end release is covered above; mid-session
behavior was not re-traced.

## Residual risks (not fixed, no evidence of impact)

- `Set_Screen_Overlay_Opacity` is not clamped (color is). `FRGBA_TO_INT32`
  would wrap or hit float-to-unsigned UB for opacity outside 0..1. Retail
  scripts use 0 and 1 only.
  Update 2026-10-07: now clamped by
  `port/patches/combat-a37-screen-overlay-opacity-clamp.patch`, the same
  `WWMath::Clamp` the color setters use. Source-only: not built or run.
- Fade durations use `TimeManager::Get_Frame_Seconds`; cinematic event times
  use script frames. Relative pacing of the two under Vita frame times was not
  examined here.
- 960x544 is wider than the original 4:3, so a 12.5 percent bar is the same
  proportion of height but the framing differs from desktop.
- Earlier Vita3K evidence (Dev144) saw authored letterbox active during the M13
  intro; there is no recorded observation of the white flash or fade-to-black,
  and no physical Vita observation of either.

## Physical evidence to request

During the M13 finale (or any cinematic using fades): confirm bars reach all
four screen edges with no sliver, the white flash covers the HUD-free frame
fully and fades out, fade-to-black ends clear at the mission transition, and a
following mission starts with no residual bars or tint. Capture at the native
presentation size so edge slivers are visible.

## Guard

`tools/test_cinematic_presentation_contract.py` (8 asset-free checks, pass)
pins: fade drawn last inside the full-display HUD scope; full native rect;
normalized full-coverage quads; `Pre_Load_Level` reset; `Unload_Level` camera
release; UV bias not enabled and `console.cpp` not built; Render2D
full-device viewport with no scissor; script command routing.
