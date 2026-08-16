# Capability matrix

| Capability | Status | Evidence / boundary |
|---|---|---|
| Native bootstrap, retail root, clean exit | physically validated | A2.0 |
| Original MIX/file-factory chain | physically validated | A2.1 |
| Original WW3D visible asset pipeline | physically validated | A2.2 |
| Original M00 static world | physically validated | A3.0 |
| Original interactive M00 session/player/camera/lifecycle | physically validated | A3.1.4 |
| Vita DirectInput logical ±1000 axis contract | host-tested | A3.5 contract 22/22; pending physical Vita observation |
| Original DDS lookup/decode/native upload/bind | built for Vita | A3.2 staging/host closure in progress; not yet physical |
| Original texture/material alpha/multistage coverage | mapped | pending coverage matrix and validation |
| Automatic evidence ZIP | host/ARM validated | dev5 capture schema 3 verifies nonempty BMP/state/CSV/summary artifacts, external failure marker, canonical identity/phase, and correct fixed-width overlay formatting; physical return pending |
| HUD Font3D / original Render2D | host-validated | original factory-backed Regatta/Arial FontChars FreeType provider plus Targa/Surface/Texture/RadarManager; optimized + ASan memory-safety two-cycle M00 runs; pending Vita |
| Original WWUI StyleMgr font/layout initialization | host-validated + ARM-linked | retail `stylemgr.ini` initializes menu and in-game original FontChars slots twice; DialogMgr and controls remain unselected |
| Original WWUI parser/resource/manager/MainMenu/Start-SP/Load-SP control frontier | host + ASan/UBSan + ARM compilation | 52 units now compile: the full selected control stack plus original Render2D/StyleMgr, `RenegadeDialogMgr`, MainMenu, GameMode, Campaign, SaveGame, and GameInitMgr. Four focused contracts pass: enumeration 11/11, pointer tokens 5/5, ListCtrl UTF-16/tag/modifier semantics 10/10, dialog resources. The isolated no-video Bink endpoint completes rather than fabricating playback; WOL/GameSpy/server-control endpoints are inactive beneath the original single-player branch. The fresh ARM symbol audit leaves 91 references beyond the frozen A3.2 ELF and selected definitions. |
| A4 original lifecycle/frontend source closure | host + Vita ARM linked; ASan/LSan/UBSan runtime | The 495-action target selects original GameMode, `MenuGameModeClass2`, CombatGameMode, campaign, dialog, WWUI, GameInitMgr and supporting owners; normal, ASan/LeakSanitizer, and UBSan host builds complete two 120-frame M00 cycles. The direct route uses original `Initialize_SP` and matching `Shutdown`, executes the authentic level/session unload order, and is leak-free in the current LSan run. The same selection links as an ARMv7 Vita ELF against the production renderer/platform library closure. `RenegadeDialogMgr` instantiates, updates/renders three frames, and tears down real `MainMenuDialog` (nine controls); when Menu is registered first, the original `Goto_Location(LOC_MAIN_MENU)` route activates `MenuGameModeClass2`, after which `GameModeManager` dispatches three Think frames and safely deactivates/removes it. Generated `chat.rc` aliases are contract-checked against the six IDs used by `MainMenuTransitionClass`. The full menu/CombatGameMode virtual graph is intentionally not activated yet. |
| Original WWUI frontend source pool | staged | 90 source/header files staged deterministically; StyleMgr and the single-player parser/manager/control-construction frontier are selected separately |
| Essential audio | deferred | silent lifecycle boundary retained |
| Campaign catalog / launch path | catalog host-validated + ARM-linked; launch source-traced | original `CampaignManager::Init` loads 36 retail `campaign.ini` flow records and matching Shutdown clears them across two normal and ASan/LeakSanitizer M00 cycles. `CampaignManager::Start_Campaign` calls `GameInitMgrClass::Start_Game`, whose original branch calls `CombatGameModeClass::Load_Level`; device activation awaits the A3.2 gate and full ownership closure |
| Multiplayer | deferred | original local route preserved; no public-service work |
