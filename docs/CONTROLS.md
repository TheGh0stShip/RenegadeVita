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
| Front touch | Original WWUI cursor plus left-click/tap |
| Rear touch | First-person / third-person camera toggle |
| Select | Next UI focus group in menus; not a system screenshot control |
| Select + Square | Original quicksave; fresh creation and original reload passed on Dev116 in Vita3K; existing-slot overwrite remains problematic |
| Start | Open original EVA pause menu; readable menu observed on Dev116; full pause/resume stability remains under test |

Notes:

- Front touch is reserved for original mouse cursor and left-click WWUI/terminal interaction.
- D-pad navigates the original WWUI focus in the frontend and remains weapon/zoom input in gameplay.
- D-pad gameplay input must not leak into camera turning.
- Circle or the original Back control leaves EVA through original Continue_Game. Start no longer requests immediate application exit in the original-frontend route.
- The native EVA menu keeps unavailable Help, save and load entries visible but disabled. Confirming Exit Demo requests orderly outer-loop teardown.
- Development checkpoint startup is a separate opt-in build feature; public builds default to leaving it disabled. Save files are never packaged with the demo.
- Rear touch pad remains the gameplay first-person / third-person camera toggle.
- The MP4 recorder's L+Start finalize gesture is separate from normal game input and is unsafe as a capture workaround until Start lifecycle behavior is accepted.
- Vita3K development input uses the native opt-in command sender without requiring focus. Visible capture uses `tools/capture_vita3k_visible_windows.ps1`, which requests no activation and restores window order. Its receipt records whether foreground actually changed during capture. Do not use PrintWindow on the current Qt emulator build; the isolated comparison implicated that capture path.
- Dev116 Vita3K observations confirm Left/Right weapon cycling and readable health, armor and ammo digits. The pending Dev118 source batch replaces 13 English PC-key tutorial hints with Vita wording; other languages retain original translations. Focused tests and affected ARM compilation pass; packaged visual validation remains pending.
