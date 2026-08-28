# Controls

Current A3.5-dev82 retail-frontend source/build candidate mapping.

## Original Frontend Menus

| Vita input | Current function |
| --- | --- |
| D-pad | Navigates the original WWUI focus while the frontend menu loop is active |
| Cross | Confirm / activate the focused WWUI control |
| Circle | Back / cancel through the original WWUI escape path |
| Select | Next focus through the original WWUI tab path |
| Start | Clean exit path sampled by the Vita runtime |
| Left stick | No frontend focus owner yet |
| Right stick | No frontend pointer owner yet |
| Touch | No frontend pointer owner yet |

The D-pad navigates the original WWUI focus only while
`A4_Frontend_Is_Menu_Loop_Active()` is true. The same physical D-pad still
emits the original gameplay keys after the menu hands off to M00.

## M00 Gameplay

| Vita input | Current function |
| --- | --- |
| Left stick | Original movement sliders: forward/back and strafe |
| Right stick | Original camera/look sliders |
| Cross | Jump |
| Circle | Crouch |
| Square | Reload |
| Triangle | Action/use/interact |
| D-pad Left | Previous weapon |
| D-pad Right | Next weapon |
| D-pad Up | Sniper zoom in |
| D-pad Down | Sniper zoom out |
| Left shoulder | Original joystick button 0 |
| Right shoulder | Original joystick button 1 |
| Start | Clean exit/menu escape path, sampled early for LiveArea return |
| Select | Debug/capture path |
| Select + L + R | Fixed-camera benchmark path |
| Front touch | First-person / third-person camera toggle |
| Rear touch pad | Unmapped |

Notes:

- The frontend path does not add a second input owner. Vita buttons feed the
  existing DirectInput/WWUI boundary.
- Tutorial selection from the original menu reuses the existing direct M00
  route. D-pad weapon/zoom, Triangle use, Square reload, and shoulder behavior
  remain the dev82 gameplay controls after the handoff.
