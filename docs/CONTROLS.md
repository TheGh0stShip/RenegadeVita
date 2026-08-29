# Controls

Current A3.5-dev82 mapping:

| Vita input | Current function |
| --- | --- |
| Left stick | Original movement sliders: forward/back and strafe |
| Right stick | Original camera/look sliders |
| Cross | Jump / confirm |
| Circle | Crouch / back in UI contexts |
| Square | Reload |
| Triangle | Action/use/interact |
| D-pad Left | Previous weapon |
| D-pad Right | Next weapon |
| D-pad Up | Sniper zoom in |
| D-pad Down | Sniper zoom out |
| Left shoulder | Original joystick button 0, currently secondary-fire/use-weapon path |
| Right shoulder | Original joystick button 1, currently primary-fire path |
| Start | Clean exit/menu escape path, sampled early for LiveArea return |
| Select | Debug/capture path only |
| Front touch | Original mouse cursor positioning plus left-click/tap |
| Rear touch pad | First-person / third-person camera toggle |

Notes:

- D-pad navigates the original WWUI focus while the frontend menu loop is
  active; during gameplay it remains bound to weapon switching and sniper zoom.
- Square and Circle are no longer both reload. Circle is crouch/back; Square
  is reload.
- D-pad Left/Right must not emit gameplay camera turn while changing weapons.
- D-pad Up/Down are reserved for sniper zoom so shoulder buttons remain
  available to the original weapon behaviors.
- Front touch maps to original 640x480 UI cursor coordinates and left mouse
  button state for WWUI menus, options, save/load screens, and in-game
  terminals.
- Rear touch owns the first-person / third-person camera toggle so front touch
  remains available for mouse-driven UI.
