# FPS round 4: HUD_TEXT_PRERENDER

Branch `worktree-agent-a60e3d89159c6be68`. This continues `fps-r3/hud-render2d-text`
(c3cdeec). Nothing here was measured on hardware.

## Hypothesis

The steady M13 "surface-backed texture upload" comes from original
Render2DSentenceClass atlases. Each `Reset` + `Build_Sentence` + `Render` makes a
fresh A4R4G4B4 surface, a new TextureClass and a GL upload, and frees the old
texture. HUD code that rebuilds an unchanged sentence every frame pays for this
every frame for nothing.

## Evidence

- dev238 physical log (`build/device-evidence/A3.5-dev238-20261004/runtime-observation-3.log`).
  Surface-backed creations are `upload - req` in the `A3.5 perf` lines. Over M13
  frames 1800->3240 they went from 114 to 198. `render-work-cache
  direct_atlas_requests`, which counts `Render2DSentenceClass::Build_Textures`
  atlases (ww3d_vita_renderer.cpp `Use_Direct_Text_Atlas_Upload`), went from 114
  to 198 over the same frames. They match exactly, so these uploads are text
  atlases. There was a burst of +112 in 120 frames (1680->1800), about 1 per
  frame. Steady play adds about 1.5 per 120 frames from real range or name changes.
- `UnlockRect` -> `Upload_Texture_Level_From_Surface` re-uploads
  (ww3d_dx8_boundary.cpp) are not counted in `texture_uploads`. No gameplay HUD
  path locks a texture-owned surface: the sentence surface is a standalone
  `SurfaceClass`.
- Per-frame rebuild owners in staging/combat/hud.cpp:
  1. Help text. `PowerUpGameObj` Think calls `Grant` every frame while the player
     overlaps a powerup he cannot take. powerup.cpp:470
     `Set_HUD_Help_Text(no_grant_message)` sets the dirty flag, so
     `HUD_Help_Text_Render` does Reset + Build + a new atlas every frame
     ("Health full" while standing on a pickup).
  2. Objective text. While any HUD objective is younger than `POG_FLY_TIME` (2 s),
     `dont_clear` keeps `Are_HUD_Objectives_Changed()` true. `Objective_Update`
     then rebuilds the pogs and resets the text cache every frame, so the
     message+range atlas is rebuilt every frame for 2+ s after each objective
     add or update. This fits the +112 burst.
- Already change-driven, so left alone: target name, weapon/vehicle name, weapon
  chart, radar compass, message/conversation TextWindow (dirty flag), powerup
  labels (combat-a36-powerup-text-once). Ammo, health and score use
  Render2DTextClass with a fixed Font3D texture, so they make quads and no
  uploads. MultiHUD names rebuild every frame but are multiplayer only.

## Change

1. `port/patches/combat-a36-hud-text-build-once.patch`. The same change is in
   `staging/combat/hud.cpp`. The patch is registered in `tools/stage_sources.sh`
   right after `combat-a36-hud-load-admission.patch`, the last patch that
   touches hud.cpp. All of it is under `RENEGADE_VITA_PORT`, with the original
   code under `#else`.
   - Help text: when the dirty text equals the current build, and the 2D
     resolution and screen UV bias are unchanged, keep the build. Only the
     original state/timer reset runs (`DISPLAYING`, timer 2 s). Every other case
     runs the original Reset/Build. The built flag is cleared at every Reset and
     at Init and Shutdown.
   - Objective text: `Objective_Update_Text` replaces the text block. It runs
     under the identical condition (`CachedObjectiveIndex != CurrentObjectiveIndex
     || irange != CachedRange`) and computes the strings and positions exactly
     as the original does. It keeps the build when message, range string, both
     positions, resolution and UV bias are all equal. Otherwise it rebuilds in
     the original order. The pog-rebuild branch no longer resets the text. That
     is safe because the branch always sets `CachedObjectiveIndex = -1`, so the
     text block always runs in the same frame.
2. HUD glyph prewarm: `Warm_Original_HUD_Font_Glyphs` in
   `port/platform/vita/a31_vita_runtime.cpp`, called at the end of
   `Prepare_Original_Level_Loading_Resources` (loading screen, every level and
   reload). For FONT_INGAME_TXT/_BIG_TXT/_SUBTITLE_TXT/_HEADER_TXT it calls
   `Get_Char_Width` for NUL and 0x20..0x7E, so `FontCharsClass::Store_GDI_Char`
   (FreeType measure + rasterize) runs before gameplay. It logs `A4 <level> HUD
   font glyph preparation: fonts= visible= elapsed_us=`.
3. vitaGL, the DX8 draw path and surface_boundary.cpp are unchanged. Sub-rect
   upload is not needed because the redundant uploads are whole new textures,
   and the fix is not to create them.

## Risk and invalidation argument

- A sentence build (atlas pixels, chunk layout, UVs) is a pure function of the
  string, the renderer's font (fixed at Init), TextureSizeHint (unset) and the
  deterministic per-glyph data. Quads also depend on Location, the coordinate
  range (`Get_Screen_Resolution()` when the renderer is created) and
  `WW3D::Is_Screen_UV_Biased()` (Update_Bias). The shader is the class default and
  never changes. Every input is either fixed or in the key, so a kept build
  equals a rebuild. The help path keeps the original per-frame `Reset_Polys` /
  `Draw_Sentence` / `Force_Alpha`, which is exactly the original non-dirty frame.
- If DX8 is not initted, `Build_Sentence` is a no-op, so the build is not marked
  kept and the next request rebuilds. If `Render` bails (device lost), the
  pending surfaces stay pending and are converted later, as in the original.
- Glyph prewarm: a glyph's width and pixels do not depend on storage order. Only
  its slot in the font's 64 KiB buffers changes. Memory is bounded at 4 x 96 small
  glyphs, an estimated well under 200 KiB. Non-ASCII glyphs (non-English
  languages) still rasterize on first use.

## Tests

- `python3 -m unittest tools.test_hud_text_build_once tools.test_hud_powerup_text_once`:
  5 tests, OK. The new test extracts the real staged `HUD_Help_Text_*` and
  `Objective_*` code. It builds it twice with g++ ASan/UBSan, as the original and
  with `-DRENEGADE_VITA_PORT`, against one model of the original Render2DSentence
  semantics. It then runs 400 frames: help text repeated every frame, text
  changes, objective adds and fly-ins, cycling, a same-width message change,
  clear and re-add, width changes, a height-only resolution change during a
  fly-in, UV-bias toggles and DX8-not-initted frames. Rendered quads (converted
  vertices, UVs, colour/alpha) and sampled texture content are identical in every
  frame. Text textures created: original 337, port 99. I also ran a mutation check
  by hand with a scratch script that is not in the repo. Dropping any one of help
  string, help resolution, objective resolution, objective UV bias, message or
  range makes the frames differ. Dropping help UV bias or the positions does
  not: `Reset_Polys` already refreshes the help bias every frame, and positions
  follow from strings and resolution. Those two keys are redundant but harmless.
- `tools.test_vita_text_readiness`, `test_vita_loading_screen_contract` and
  `test_vita_m13_cinematic_preparation`: 1 error, which was already there.
  `test_m01_referenced_textures_prepare_before_first_world_frame` looks for
  `stricmp(selected_archive, "M01.mix") == 0`, and that text is absent at base
  95c4976 too (1b9e887 refactor).
- `patch -p1 -F0 --dry-run` against the pre-change staged hud.cpp (95c4976)
  applies cleanly, and the result is byte-identical to the committed staging file.
- ARM TU (VitaSDK, current flags): OK for `staging/combat/hud.cpp` and
  `port/platform/vita/a31_vita_runtime.cpp`. There are no new warnings; the
  hud.cpp:3013 typedef warning was already there.

## Expected gain (unmeasured estimate)

- Each avoided rebuild saves a surface allocation and clear, the glyph blits, a
  TextureClass and GL texture create/free in the vitaGL pools, the
  A4R4G4B4->RGBA conversion and the upload. These atlases are usually 64x64 to
  128x128. Estimate: about 0.2-0.5 ms CPU per affected frame, plus less
  texture-pool churn. The affected frames are the 2+ s after every objective
  change and all frames spent standing on an unusable powerup. Other
  steady-state frames are unchanged.
- Glyph prewarm takes first-use FreeType work (roughly 50-300 us per glyph) out
  of early gameplay frames such as the first objective, help or target text. It
  adds an estimated tens of ms to loading; see `elapsed_us` in the log.

## Switches

Default-on in Vita port builds. There is no runtime switch.

## Hardware measurement to take

Run M13 from mission start through the first objectives, then stand on a health
pickup at full health for about 5 s. Compare against dev238: the per-120-frame
delta of `render-work-cache direct_atlas_requests` and of the `A3.5 perf`
`upload - req` counter should fall. It should be about zero while on the pickup,
with no per-frame rise during pog fly-ins. Also record p50/p95/p99 frame time in
those windows and `A4 M13 HUD font glyph preparation ... elapsed_us`, and check
visually that help, objective and range text and the pog fly-in are unchanged.
