# Controls

Current A3.5-dev79 mapping:

| Vita input | Current function |
| --- | --- |
| Left stick | Original movement sliders: forward/back and strafe |
| Right stick | Original camera/look sliders |
| Cross | Jump / confirm |
| Circle | Crouch / back in UI contexts |
| Square | Reload |
| Triangle | Action/use/interact |
| D-pad Down | First-person / third-person camera toggle |
| D-pad Left | Previous weapon |
| D-pad Right | Next weapon |
| D-pad Up | EVA/objectives viewer toggle path |
| Left shoulder | Original joystick button 0, currently primary-fire path |
| Right shoulder | Original joystick button 1, currently secondary-fire path |
| Start | Clean exit/menu escape path, sampled early for LiveArea return |
| Select | Debug/capture path only |
| Front touch | Unmapped |
| Rear touch pad | Unmapped |

Notes:

- D-pad buttons still emit virtual keys for UI navigation, but no longer drive
  gameplay movement.
- Square and Circle are no longer both reload. Circle is crouch/back; Square
  is reload.
- D-pad Up is reserved for the original EVA/objectives path because that is
  useful during tutorial progression without competing with movement.
