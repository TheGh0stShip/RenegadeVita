# Current Status

Updated: 2026-08-28

## Accepted Baseline

**A3.1.4** is the latest accepted physical baseline. It proves native Vita
startup, original file/archive access, visible original M00 world/session
lifecycle, interactive player/camera ownership, and clean exit.

## Current Candidate

**A3.5-dev82** is the active M00 gameplay source/build line. This
`feature/a35-dev82-retail-frontend` branch is a focused source/build candidate
for the original Commando frontend on top of that line. It does not supersede
the accepted A3.1.4 physical baseline and it does not claim physical menu or
movie acceptance.

The frontend branch admits the original `MovieGameModeClass`,
`MenuGameModeClass2`, `RenegadeDialogMgrClass`, `MainMenuDialogClass`,
single-player start/load/options dialog surfaces, and WWUI control stack behind
`RENEGADE_A4_ORIGINAL_FRONTEND`. It adds a Vita frontend lifecycle boundary for
controller-to-WWUI key transitions, menu exit/tutorial latching, and traceable
movie requests.

Intro movie requests still go through the original movie owner. The Bink/RAD
provider is fail-closed for this pass: it logs the requested movie, records the
skip, does not import proprietary RAD code, and does not package retail movie
files. That keeps the menu flow moving while preserving the future provider
boundary for legal decoder work.

Tutorial selection from the original Start SP menu latches the original
`GameInitMgrClass::Start_Game("M00_Tutorial.mix")` request and then reuses the
existing dev82 direct M00 loading route. This avoids a second gameplay loader,
HUD owner, input owner, or loading progress bar until full menu-to-combat
equivalence is proven.

## What This Branch Targets

- Original startup movie/menu ownership where practical:
  `MovieGameModeClass` enters the EA/Westwood logo request and Renegade intro
  request before the main menu.
- Retail main-menu path with original WWUI focus, text/layout/resource
  templates, menu mode lifecycle, and single-player entry surfaces.
- Vita controller navigation through the existing DirectInput/WWUI boundary:
  D-pad focus only during the frontend loop, Cross confirm, Circle back, and
  Select tab/next focus.
- Compatibility with dev82 gameplay fixes after handoff: loading screen,
  HUD/dialogue text, D-pad weapon/zoom mapping, Triangle use, Square reload,
  shoulders unchanged, texture orientation, CombatGameMode finalization, and
  VitaGL shader cache/prewarm.

## Still Open Until Physical Evidence Returns

- Whether the frontend renders and focuses correctly on physical Vita.
- Whether the intro movie fail-closed path advances to the main menu on device.
- Whether the main menu buttons, back/quit behavior, options surfaces, and
  supported load-game surfaces behave like retail under physical controls.
- Whether tutorial selection reaches the same stable M00 route on hardware.
- Whether current dev82 M00 fixes remain intact after menu handoff.

## Useful Evidence To Return

- Runtime log from `ux0:data/renegade/user/logs/a35-dev82-runtime.log`.
- Any screenshots showing intro/menu, loading screen, Logan text, NPC/Havoc
  materials, HUD, gate state, and freeze point.
- Any `psp2core-*.psp2dmp` if the app crashes or the system captures a dump.
- Whether D-pad moves WWUI focus in the menu, Cross/Circle activate/back, and
  after tutorial handoff D-pad weapon/zoom, Triangle use, Square reload, and
  shoulder behavior remain unchanged.
