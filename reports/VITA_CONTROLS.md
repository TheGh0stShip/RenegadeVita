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
| Circle | DIK_LCONTROL | Crouch |
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
