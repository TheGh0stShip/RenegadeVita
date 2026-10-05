# Original LAN server preset wiring

The released LAN host screen exposes a Save/Load control for named server
settings. The Vita frontend previously displayed that control disabled because
`dlgserversaveload.cpp` was omitted with the retired slave-server path.

The full profile now links the original dialog and preserves its game-owned
behavior:

- host-option tabs apply changes before the preset dialog opens;
- `cGameData::Is_Valid_Settings` remains the save admission owner;
- the released list, display names, empty slot, overwrite message, numbered
  filenames, load, save and delete behavior remain;
- the immutable shipped default remains available through retail fallback;
- custom default and numbered presets read and write under `user/` through
  the established server-config/file-factory boundary.

The platform adaptation is limited to three boundaries. Retired
`SlaveServerDialogClass` references are excluded from the LAN profile.
Pointers stored in WWUI's 32-bit list data use
`Renegade_Ui_Pointer_To_Token`, `From_Token` and `Take_Pointer_Token`, so
Vita ILP32 semantics remain explicit without truncating LP64 host pointers.
Desktop `data\\` probes, creation and deletion are replaced by validated
logical filenames and user-rooted file-factory operations.

Canonical resource `IDD_MENU_SERVER_SETTINGS_SAVELOAD` (250) is selected
with required checks for its edit, list, back, delete, save and load controls.
The host dialog also requires `IDC_SAVELOAD_BUTTON`. Canonical and fast
artifact checks require `ServerSaveLoadMenuClass::On_Init_Dialog`.

Deterministic staging passes with 495 ordered patches and inventory SHA-256
`6392bf3f224d18bc8798f067b327436c00df124b58f6f8ed9d9ac2aa9d37c826`.
No compilation, tests, emulator, physical device, GitHub, or GitHub Actions
runner were used. ARM link, rendered dialog, input focus, persistence,
read-only default behavior, delete behavior and repeated lifetime remain open.
Failed filesystem deletion leaves the row present. Server-config writes now
accumulate status across original base/derived serialization, inspect final
close/atomic-replace failure and keep the dialog open with the released storage
error when persistence fails. Hardware validation must still measure the cost
of scanning up to 498 numbered preset names.
