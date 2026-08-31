# Controls

The mapping below is the current source intent. Its complete physical behavior is still an A3.5 gate; do not infer acceptance from this table.

| Vita input | Intended function |
| --- | --- |
| Left stick | Original movement sliders: forward/back and strafe |
| Right stick | Original camera/look sliders |
| Cross | Jump / confirm |
| Circle | Crouch / back in UI contexts |
| Square | Reload |
| Triangle | Action/use/interact |
| D-pad Left / Right | Previous / next weapon in gameplay; WWUI focus navigation in frontend |
| D-pad Up / Down | Sniper zoom in / out in gameplay |
| Left shoulder | Original joystick button 0 / secondary-fire path |
| Right shoulder | Original joystick button 1 / primary-fire path |
| Front touch | Original 640×480 UI cursor plus left-click/tap |
| Rear touch | First-person / third-person camera toggle |
| Select | Diagnostic input only; it is not a system screenshot control |
| Start | Original pause/exit request; **not physically accepted** because the Dev87 return reported a crash after Start |

Notes:

- Front touch is reserved for original mouse cursor and left-click WWUI/terminal interaction.
- D-pad navigates the original WWUI focus in the frontend and remains weapon/zoom input in gameplay.
- D-pad gameplay input must not leak into camera turning.
- Rear touch pad remains the gameplay first-person / third-person camera toggle.
- The MP4 recorder's L+Start finalize gesture is separate from normal game input and is unsafe as a capture workaround until Start lifecycle behavior is accepted.
- Current capture work should use the future title-local VDB provider, not gameplay controls or arbitrary frame delays.
