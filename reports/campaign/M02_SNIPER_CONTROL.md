# M02 midtro: Sniper_Control trace and hand-off audit

Source audit only. Nothing was built, run on the host, or run on a Vita. All
statements about on-screen result are unverified until a physical test.

## Call chain (all original code except where marked)

1. `Test_Cinematic::Command_Sniper_Control` (`staging/scripts/Test_Cinematic.cpp:890`)
   parses `ENABLED, ZOOM` and calls `Commands->Cinematic_Sniper_Control`.
2. `Cinematic_Sniper_Control` (`staging/combat/scriptcommands.cpp:3081`) forwards
   to `COMBAT_CAMERA->Cinematic_Sniper_Control`.
3. `CCameraClass::Cinematic_Sniper_Control` (`ccamera.cpp:~1600`) only stores
   `CinematicSnipingEnabled` and `CinematicSnipingDesiredZoom`.
4. Each frame `CCameraClass::Update()` calls `Handle_Input()` before the
   host-model early return. When `CinematicSnipingEnabled` is set, `Handle_Input`
   moves `SniperZoom` toward the desired zoom at 1.0 per second
   (`zoom_change` clamped to the frame time) and calls
   `CurrentProfile->Set_Zoom(SniperZoom)`. That sets `CurrentProfile->FOV`.
5. `Use_Host_Model()` keeps `FOV` from the profile while
   `CinematicSnipingEnabled` is set (otherwise it forces 75 degrees) and calls
   `Set_View_Plane`. The camera transform comes from the host's `CAMERA` bone.
6. `CCameraClass::Draw_Sniper()` returns `CinematicSnipingEnabled` while a host
   model is active, otherwise `IsStarSniping`.
7. `HUDClass::Think` calls `SniperHUDClass::Update` and `HUDClass::Render` calls
   `SniperHUDClass::Render` whenever `Draw_Sniper()` is true. Both run before
   the `Is_HUD_Displayed()` check, so `Enable_HUD(0)` from `Control_Camera`
   hides the normal HUD but not the scope, as in the original.

Rate note: 21 steps over a ~39 s cinematic is slow enough that the 1.0/s zoom
slew keeps up with each step, so the zoom follows the script without clamping
to a stall.

## Sniper overlay rendering path on the Vita (KNOWN_GAPS open item)

The overlay is the original `SniperHUDClass` (`staging/combat/sniper.cpp`) on
`Render2DClass` with texture `hud_sniper.tga`.

- Retail ships it as `hud_sniper.dds` (DXT5, 128x128, 8 mips,
  `reports/generated/sweeps/dds_formats.json`). The Vita backend
  (`port/renderer/vita/ww3d_dx8_boundary.cpp`) has DXT1/DXT5 upload paths, so
  the format is supported in principle. That DDS row is still `status: unknown`.
- Coordinate space is consistent for all three phases: `HUDClass::Init`
  (covers `SniperHUDClass::Init` and `Build_Base`), `HUDClass::Think` (covers
  `SniperHUDClass::Update`) and `CombatManager::Render` (wraps
  `HUDClass::Render`) all run inside `A31_Vita_Begin/End_Original_HUD_Render`.
  `Build_Base` is built once at Init, so it uses the 960x544 logical HUD space
  only if Init happens inside that scope; it does.
- The existing Vita-only change in `Build_Base` (`combat-a35-m00-ui-hud-subtitles.patch`)
  stretches the scope view to the full screen instead of the original
  646x700 per-mille box. Whether the reticle lines, zoom marker and DXT5 alpha
  look right at 16:9 cannot be judged from source. This stays a physical
  visual gate.
- The scope overlay is drawn inside the HUD pass, after the world and before
  `ScreenFadeManager::Render`, so fades and the letterbox still go over it.

## Input while the cinematic owns the camera

Timeline (original `Mission02.cpp:843-851`, `:1840`): zone 400193 calls
`Control_Enable(STAR, false)`, starts timer 9 (1 s) and attaches
`Test_Cinematic X2K_Midtro.txt`. `Control_Camera` in the cinematic also disables
star control and the HUD. Timer 9 then teleports the star and calls
`Control_Enable(STAR, true)` while the midtro still owns the camera.
`Control_Camera -1` at the end re-enables control and the HUD again.

Findings:

- **Star movement and fire: no leak.** The star has `EnableCinematicFreeze`
  defaulted to true; only the camera host disables it. While
  `Activate_Cinematic_Freeze(true)` is on (set by `Set_Host_Model`),
  `GameObjManager::Generate_Control` skips the star and `GameObjManager::Think`
  calls `Reset_Controller()` and `Weapon->Deselect()` every frame. The D-pad
  weapon switch, fire and action inputs therefore reach nothing.
- **Sniper zoom input: no leak.** `Handle_Input` only reads
  `INPUT_FUNCTION_ZOOM_IN/OUT` when `!Is_Using_Host_Model() && Is_Star_Sniping()`.
  D-pad Up/Down are bound to those functions
  (`a31_gameplay_boundary.cpp:584-587`).
- **Look stick: leak (fixed).** `Handle_Input` returns early only when star
  control is disabled. With control re-enabled at 1 s, `Tilt` and `Heading`
  accumulated from the right stick for the rest of the midtro even though the
  host camera ignores them. `Heading` is forced back to the star's facing when
  the host is dropped, but `Tilt` was not, so the player could leave the
  midtro with a pitched camera (clamped to +/-80 degrees). The original PC
  code has the same ordering; a mouse is rarely moved for 39 s, a held stick is.

## Sniper state after the cinematic

`Set_Host_Model(NULL)` restored the camera profile but never cleared
`CinematicSnipingEnabled`; only acquiring a host cleared it. Consequences when a
cinematic ends without `Sniper_Control 0`, or when the level unloads while the
midtro is active (`combat-a36-level-cinematic-camera-release.patch` now calls
`Set_Host_Model(NULL)` from `Unload_Level`):

- `Handle_Input` kept forcing `Set_Zoom` on the player's profile every frame,
  so the FOV stayed zoomed.
- `MainCamera` outlives the level, so the latch could carry into M03.
- `SniperZoom` kept the cinematic's last value, so the star's next sniper
  session started from it.

I could not read the retail `X2K_Midtro.txt` here (the Steam install is not
mounted in this WSL), so I could not confirm whether the retail script ends with
`Sniper_Control 0`. The fix is correct either way.

## Changes

New staging patch `port/patches/combat-a47-ccamera-cinematic-sniper-handoff.patch`
(registered in `tools/stage_sources.sh` after `commando-credits-short-read`, applied
to `staging/combat/ccamera.cpp`; receipt refreshed, 514 patches, inventory
check passes; the patch applies zero-fuzz to the pre-change staged file and
reproduces the staged result byte for byte):

1. `CCameraClass::Set_Host_Model`: when a host is dropped, clear
   `CinematicSnipingEnabled` and `CinematicSnipingDesiredZoom`, and restore
   `SniperZoom` to the value saved when the host was acquired. Not gated; it
   only changes the case where the flag would otherwise stay latched.
2. `CCameraClass::Handle_Input`: under `RENEGADE_VITA_PORT`, return before the
   Tilt/Heading accumulation while `Is_Using_Host_Model()`. The cinematic zoom
   step above it and the star-sniping zoom block are unchanged.

Not changed: the scope geometry, the `Mission02.cpp` ordering (original
behavior), star freeze handling, and the HUD/overlay presentation scopes.

## Physical checks for the midtro (additions to the M02 route)

- Scope overlay appears with the midtro, zooms smoothly across the 21 steps and
  disappears when the midtro ends. Compare lines/zoom marker against the 16:9
  stretch; check DXT5 alpha on the scope texture.
- Hold the right stick and the D-pad for the whole midtro. The camera must not
  respond, the star must not fire or switch weapon, and after release the
  camera must be at the pre-cinematic pitch and normal FOV (no residual zoom).
- After the midtro, raise the sniper rifle and confirm the first zoom level is
  the one used before the midtro.
- Complete M02 and enter M03; the first M03 frames must be at normal FOV.
- Grep the log for `A4 slow campaign cinematic command: file=X2` for hitches
  around the zoom steps.
