# Renegade Vita controls

Source of truth: `port/platform/renegade_directinput.cpp` (Vita buttons are
converted to the original DirectInput key/axis tables; original Combat `Input`
bindings still own the action) and `port/platform/renegade_vita_tutorial_help.h`
(in-memory English tutorial captions, applied in
`port/platform/vita/a31_vita_runtime.cpp`; retail strings are not changed).
**PSTV** marks DualShock-only inputs (L3/R3, read through Ext2).

## Gameplay (campaign and multiplayer, no dialog open)

| Vita input | Original key/axis | Renegade function |
|---|---|---|
| Left stick | Joystick X/Y slider | Move/strafe; ladder climb; vehicle drive |
| Right stick | Mouse X/Y delta | Look/aim/turn (CCamera) |
| R trigger | Joystick button 1 | Fire primary / place C4 |
| L trigger | Joystick button 0 | Secondary fire: sniper scope on/off, detonate C4 |
| Cross | DIK_SPACE | Jump |
| Circle (hold) | DIK_LCONTROL | Crouch while held (original) |
| Circle (quick solo tap) | DIK_LCONTROL latched | Crouch stays on until the next Circle press, Triangle/Action, or a menu/dialog |
| Triangle | DIK_E | Action/Use: enter vehicle, ladder, talk |
| Square | DIK_R | Reload |
| D-pad Left/Right | DIK_LEFT/RIGHT | Cycle weapons |
| D-pad Up/Down | DIK_UP/DOWN | Sniper zoom in/out |
| START | DIK_ESCAPE | Menu toggle (EVA/pause) |
| Select (tap alone) | DIK_BACK | CyclePog (cycle objectives) |
| Select + Square | DIK_F5 | Quicksave |
| Rear touch | DIK_F | First/third-person toggle |
| Select + Circle (campaign only) | DIK_F | First/third-person toggle (PSTV substitute for rear touch) |
| **PSTV** R3 | DIK_F | First/third-person toggle |
| **PSTV** L3 | DIK_LCONTROL | Crouch |
| Front touch | Mouse cursor + left button | Original cursor/click |

## Multiplayer / Practice chords (Select held; not in campaign missions)

| Vita input | Original key | Function |
|---|---|---|
| Select + Triangle | DIK_T | Public chat |
| Select + Circle | DIK_Y | Team chat |
| Select + Square | DIK_F7 | Team info |
| Select + Cross | DIK_F8 | Battle info |
| Select + D-pad Up | DIK_F9 | Server info |
| Select + L (+ command) | DIK_CONTROL/RCONTROL + 1-0 | Radio page 1 |
| Select + R (+ command) | DIK_ALT/RMENU + 1-0 | Radio page 2 |
| Select + L + R (+ command) | Ctrl+Alt + 1-0 | Radio page 3 |

Radio command buttons (while a radio page is held): D-pad Up/Down/Left/Right =
1/2/3/4, Triangle/Circle/Cross/Square = 5/6/7/8, left stick up = 9, left stick
down = 0. Ordinary gameplay input is suppressed while a chord or radio page is held.

## Menus and dialogs (frontend, EVA, DialogMgr)

| Vita input | Original key | Function |
|---|---|---|
| D-pad | VK_UP/DOWN/LEFT/RIGHT (+ DIK arrows) | Focus navigation |
| Cross | VK_RETURN (+ DIK_SPACE) | Accept/activate |
| Circle | VK_ESCAPE | Back/cancel (also dismisses connecting popup) |
| Square | VK_F6 | Dialog F6 action |
| Select | VK_TAB | Tab focus |
| START | DIK_ESCAPE (frontend) | Menu toggle |
| L / R triggers | Joystick buttons 0/1 | Bindable in controls dialog |
| Front touch | Mouse cursor + left click | Point and click |

In the key-binding dialog, fresh presses of Cross, Circle, Triangle, Square and
D-pad publish DIK_SPACE/LCONTROL/E/R/arrows as `LastKeyPressed`.

## Text entry

Save names, player names and chat fields (including the in-game chat popup)
open the Vita system IME dialog (`port/platform/vita/renegade_vita_text_entry.cpp`);
game input is blocked while it is open. Confirm/cancel follow the firmware IME.

## Campaign action coverage (2026-10-07, source audit)

Default bindings come from retail `DEFAULT_INPUT.CFG` (Always2.dat copy, a
keyboard/mouse map) with `A31_Interactive_Configure_Vita_Controls()`
(`port/platform/a31_gameplay_boundary.cpp`) applied on top whenever the
default profile is loaded. `tools/test_vita_campaign_control_coverage.py`
checks that each function below is bound to a key, slider or joystick button
that `renegade_directinput.cpp` actually produces. "Dialog" means a DialogMgr
dialog or the EVA/pause menu is open: gameplay keys, sticks and triggers are
then not gameplay input (single-player Combat is suspended), and Circle/Back
leaves the EVA. All functions are zeroed by the original `Input::Update`
during in-engine cinematics.

| Campaign action | Original function (type) | Retail PC | Vita | In vehicle |
|---|---|---|---|---|
| Move, strafe, climb ladder | MOVE_FORWARD/BACKWARD/LEFT/RIGHT (analog) | WASD | Left stick (0.15 radial dead zone) | Drive; X steers (VEHICLE_TURN copies MOVE_LEFT/RIGHT) |
| Look / aim | WEAPON_UP/DOWN/LEFT/RIGHT (mouse sliders) | Mouse | Right stick | Camera / turret |
| Poke PCT, MCT, console, switch | ACTION (hit); target under reticle within 2 m | E | Triangle | Exits vehicle |
| Enter vehicle, incl. passenger seat | ACTION via TransitionManager | E | Triangle | Triangle exits |
| Get on a ladder | ACTION in ladder zone; exits are automatic | E | Triangle, then left stick | n/a |
| Jump onto ledges | JUMP (hit) | Space | Cross | Aircraft up (not used in campaign) |
| Crouch | CROUCH (held) | C | Circle hold, or tap to latch; PSTV L3 | Not used |
| Crouch-jump | CROUCH held + JUMP (no extra height in original) | C+Space | Tap Circle, then Cross; or Circle+Cross together | n/a |
| Fire; place timed/proximity C4 | FIRE_WEAPON_PRIMARY (held) | LMB | R trigger | Fires vehicle weapon |
| Detonate remote C4 | USE_WEAPON (hit, copied from secondary fire), remote C4 selected | RMB | L trigger tap | n/a |
| Deploy ion/nuke beacon | FIRE_WEAPON_PRIMARY held through charge; must be upright | LMB hold | R trigger hold; stand up first | n/a |
| Cancel beacon arming | Any move, jump, weapon switch, reload, use or action while arming | Move | Left stick (ammo returned) | n/a |
| Sniper scope on/off | USE_WEAPON (hit) on a snipe weapon | RMB | L trigger tap | n/a |
| Sniper zoom in/out | ZOOM_IN/ZOOM_OUT (held, only while scoped) | Wheel, T/G | D-pad Up/Down | n/a |
| Pick weapon (C4, beacon, sniper) | NEXT/PREV_WEAPON (hit) | Wheel, Enter/' | D-pad Right/Left (cycle) | Single weapon |
| Reload | RELOAD_WEAPON (hit) | R | Square | n/a |
| First/third person | FIRST_PERSON_TOGGLE (hit) | F | Rear touch; Select+Circle; PSTV R3 | Works |
| Cycle objective marker | CYCLE_POG (hit) | Backspace | Select tap | Works |
| EVA / pause (objectives, map, data, save, load, options, quit) | MENU_TOGGLE (hit) | Esc | START; tabs by touch or D-pad+Cross; Circle leaves | Works |
| Quicksave | QUICKSAVE (hit) | F6 | Select+Square | Works |
| Load after death | Original death dialog | Mouse/keys | D-pad, Cross, Circle, touch | n/a |
| Skip movie | Bink owner | Esc | START, Cross, Circle or Triangle | n/a |

Not reachable from a Vita button, and not needed to finish the campaign:
SELECT_WEAPON_0-9 (number keys; cycle instead), EVA_OBJECTIVES_SCREEN (O) and
EVA_MAP_SCREEN (M) (use the EVA tabs), EVA_MISSION_OBJECTIVES_TOGGLE (Tab;
deliberately unbound and test-locked, so the in-game objectives overlay is
not shown; the EVA Objectives tab under START lists the same objectives),
HELP_SCREEN (F1; EVA Help button), WALK_MODE (Shift; the stick is analog),
TURN_AROUND (X), CURSOR_TARGETING (V) and VEHICLE_TOGGLE_GUNNER (Q; only
matters with a second occupant, which is a multiplayer case). DIVE and
DROP_FLAG are unbound in retail too. The original has no flashlight or
binocular function and cannot skip in-engine cinematics.

Fixes in this audit:

- Loading the default profile from the Controls Save/Load page, or deleting
  the current custom profile, reloaded the retail keyboard map without the
  Vita bindings. The left stick, triggers, crouch, weapon cycling and zoom
  then did nothing. `commando-a37-default-input-profile-vita-mapping.patch`
  reapplies the Vita mapping in `InputConfigMgrClass::Load_Configuration`
  whenever the loaded profile is the default one, before the Controls UI
  reloads.
- Crouch is hold-only in the original, and the right thumb cannot hold
  Circle while aiming with the right stick (handheld has no L3). A quick solo
  Circle tap (under 250 ms, without Cross, Square, Select or START) now
  latches the original crouch key. Holding Circle still works as before.
  Pressing Circle again, Triangle/Action (vehicle entry, ladder, poke), or
  opening any dialog, chord or IME releases the latch. A one-shot breadcrumb
  "Circle tap latched original crouch key DIK_LCONTROL" records first use.

Remaining risks (need hardware): the tap window and latch feel; beacons do
not fire while crouched (original rule), so a latched crouch must be released
first; a vehicle entered by script while crouch is latched gets the original
crouch-key throttle scaling until Circle is tapped; accidental rear-touch
camera toggles; Select+Square is a stretch for one thumb (the EVA Save button
is the alternative).
