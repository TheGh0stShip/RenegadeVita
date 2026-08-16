# A4 frontend link inventory

The frozen A3.2-dev1 ELF is intentionally unchanged. The selected authentic
frontend/campaign control set compiles as 52 Vita ARM objects. Comparing its
unresolved symbols against both those definitions and the frozen ELF leaves 91
symbols.

The next original owners are:

The resolved owners now include `ww3d2/render2d.cpp`, `render2dsentence.cpp`,
`wwui/stylemgr.cpp`, popup/cursor/IME owners, and Commando's main-menu
transition, GameMode, Campaign, GameInitMgr, and SaveGame. The remaining
references are dominated by real renderer, texture, audio, packet, Combat-mode,
and system-service owners; they must be selected from their original units,
not locally stubbed to force a menu.

The entry sequence is original: `GameInitMgrClass` returns to
`RenegadeDialogMgrClass::Goto_Location(LOC_MAIN_MENU)`, which calls
`MainMenuDialogClass::Display`; Start-SP reaches `Initialize_SP` then
`Start_Game`. No alternative menu or gameplay loop is proposed.

Reproduce the inventory after staging with:

```text
find build/vita-a4-frontend-syntax/CMakeFiles/a4_wwui_frontend_probe.dir -name '*.obj'
arm-vita-eabi-nm -u / -g --defined-only on those objects and the frozen A3.2 ELF
```

The standalone Vita UTF-16 contract executable emits the same wchar-size linker
warning as the accepted A3.2 ELF because the VitaSDK C++ runtime contributes a
4-byte-wchar ABI tag. It is a diagnostic executable only; the frontend is
validated as 16-bit-WCHAR objects and no warning is suppressed.
