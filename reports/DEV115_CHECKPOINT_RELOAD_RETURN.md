# Dev115 original checkpoint reload

Evidence class: Vita3K only. Full tutorial completion remains unproven.

The matching Dev115 run at
`D:/Vita3K/RenegadeEvidence/Dev115-checkpoint-20260909T1513Z`
reached original gameplay from `save/dev112-post-sydney.sav`.
Runtime lines 1120-1123 show the original inactive player reactivated,
the saved star preserved, and the saved first-person camera reused.
Line 1498 records the original player/session ready.

`window-151.png` visibly shows the loaded tutorial room, objective indicator,
radar and weapon HUD. Numeric HUD rendering remains incorrect in this package.
The capture does not establish mission completion or physical performance.

Dev116 canonical build was launched with explicit candidate label and
development checkpoint enabled. `CCACHE_NODIRECT=1` prevents direct-mode
cache reuse across the newly staged TGA header; default full staging is used.
Build output: `build/dev116-canonical.log`. Completion is not yet assessed.

Next: assess original EVA pause/resume, validate Dev116 HUD correction,
then continue original tutorial scripts to the demo ending.

## Original EVA visual return

Native Start input was accepted and released without foreground focus:
`build/dev115-pause-input.json`.
`step-20260909T151703145Z.png` visibly shows the original EVA Objectives
screen, seven labeled tabs, objective rows, description and bottom buttons.
Locate Advanced Guard Tower is accomplished; Locate Infantry Barracks is
pending, with original text directing the player to Gunner for weapon basics.
This establishes pause entry and visible original UI on this checkpoint.
It does not establish every tab or pause exit. Dev115 still exposes Options;
the integrated Dev116 policy disables that unsupported demo action.

Subsequent Circle input (`build/dev115-resume-input.json`) was accepted and
released. `step-20260909T151717741Z.png` shows gameplay restored, establishing
one original pause/resume cycle without a crash in this Vita3K run.
