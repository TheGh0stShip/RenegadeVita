# Original M00 pause owner restoration

Latest source progress: CMake now selects the original EVA owner, all seven
tabs and shared viewer (nine units). Registered staging changes fix the
message-box header case, exclude the unselected desktop Help presenter and
online-only SlaveMaster decision in the single-player selection, and replace
viewer list pointer payloads with bounds-checked original ObjectList indices.
No compilation or staging has run. Factory routing and native UI lifetime are
still deliberately inactive until their pause/resume/exit ownership is wired.
The existing Help control also needs visible disabled presentation at that point.

The original map click callback contains a player-warp operation. Its control
input admission must be traced before enabling the map tab in a public demo;
do not use it to manufacture tutorial progression or warmup coverage.

The dependency list below describes the pre-selection source trace; the nine
units are now selected in source, not demonstrated compile/link closure.

Status: source trace and preparation only; no build or test authorization.
Previous goal turn made progress through the loading/menu implementation batch.

## Original route

Combat_Keyboard routes the menu toggle to LOC_ENCYCLOPEDIA. The authentic
EVAEncyclopediaMenuClass owns the original pause screen, not MainMenuDialog.
It creates original objectives, map, data, characters, weapons, vehicles and
buildings tabs. Back/Cancel invokes GameInitMgrClass::Continue_Game; the main
menu command prompts the user before End_Game and Display_End_Game_Menu.

The active frontend source selection does not compile dlgevaencyclopedia.cpp
or its seven tab implementations. The single-player factory array omits EVA,
and the relevant Goto_Location cases are excluded. Native frontend shutdown
also destroys DialogMgr before M00; only StyleMgr is recreated afterward.
Restoring a key mapping alone cannot establish a working pause screen.

## Implemented preparation

- Registered an original EVA Exit_Game null guard for absent WOL/LAN modes.
  Existing providers retain the original dedicated/slave-server decision.
  This currently unselected source change is not a fix claim for the user's
  pause-entry crash, and no fault address has been established.
- Demo single-player submenu disables Campaign and Load while retaining their
  original controls/text. Direct commands are rejected as well. Tutorial and
  Back retain their original behavior. Full-port builds are unaffected.
- Developer checkpoint tooling remains separate from public menu selection;
  real original save/load compatibility is still unproven.

## Next implementation requirements

1. Select the original EVA owner and needed original tab implementations;
   isolate online-only dependencies without replacing the UI or game loop.
2. Restore factory/location routing and deliberate lifetime for DialogMgr,
   its input provider, StyleMgr, backdrop, menu mode and suspended Combat.
3. Pump original WWUI while paused and render in its original logical scope;
   preserve native HUD resolution when returning to gameplay.
4. Replace Start-to-exit only once original pause/resume ownership is wired.
   Preserve the development input emergency-release policy independently.
5. Route abandon-game through orderly native teardown rather than activating
   MainMenu while the native gameplay loop still holds level/player pointers.

All new staging patches are unexecuted. No tests, builds, emulator changes,
retail changes or physical access occurred. Full demo release remains 0/10.
