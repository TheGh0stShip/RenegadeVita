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
| Left shoulder | Original joystick button 0, currently primary-fire path |
| Right shoulder | Original joystick button 1, currently secondary-fire path |
| Start | Clean exit/menu escape path, sampled early for LiveArea return |
| Select | Debug/capture path only |
| Front touch | First-person / third-person camera toggle |
| Rear touch pad | Unmapped |

Notes:

- D-pad navigates the original WWUI focus while the frontend menu loop is
  active; during gameplay it remains bound to weapon switching and sniper zoom.
- Square and Circle are no longer both reload. Circle is crouch/back; Square
  is reload.
- D-pad Left/Right must not emit gameplay camera turn while changing weapons.
- D-pad Up/Down are reserved for sniper zoom so shoulder buttons remain
  available to the original weapon behaviors.
