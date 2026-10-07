# Campaign text and conversation closure M13, M01-M11

Evidence class: host Python scan of the unchanged retail Data (read-only) plus staged-source
inspection of the Vita build input (`staging/`, `port/`). No build, link, VPK, emulator or Vita
action. Nothing here proves rendering, layout, audio playback or physical behavior. No retail
text or audio is reproduced (IDs, names and counts only). Complements
`OBJECTIVE_TEXT_READINESS.md` (M01-M11 script string IDs) and `CONVERSATION_COMPLETION.md`
(`Action_Complete` delivery).

## Verdict

- Every string ID a campaign script passes to `Set_HUD_Help_Text`, `Add_Objective`,
  `Set_Objective_HUD_Info(_Position)` or `Display_Text` resolves in both `strings.tdb`
  candidates. M01-M11 was already 0 missing; M13 was added here (5 IDs, all
  `Set_HUD_Help_Text`, 0 missing, 0 unresolved expressions). Scripts never call
  `Get_String`; the only string-ID surface is those four commands plus
  `Create_Conversation` names and `Reveal_Encyclopedia_*` (covered in the other report).
- Every conversation remark text ID reachable from script-referenced conversation names resolves in
  both `strings.tdb` candidates (0 absent, 0 rows with no translation, 0 empty English strings),
  and every remark's orator index is in range (0 errors). All text IDs of the 12 maps are covered.
- Every voiced remark's sound definition resolves to a retail file except **one**: text ID 1905
  (global conversation `M05_CON059`, used by M05) names sound definition 163845379, which exists in
  no `objects.ddb` or mission `.ddb` that is mounted. Runtime handles it (see trace).
- **Four script-referenced conversation names do not exist** in any level or global conversation
  database: `MX0_ENGINEER1_048` (M13), `M02_HIDDEN_02_FINISH` (M02), `M03CON068` (M10),
  `M01_TurretBeach_TurnOverTank_Conversation` (M01, from a script outside the bound closure).
  `Create_Conversation` returns -1 and every later conversation command is a no-op. None of the four
  is a progression dependency (details below). This is retail behavior, not a port defect.
- Vita code paths: no reachable NULL dereference or NULL wide-string format was found for these
  data. Three latent NULL/zero-ID hazards exist in retail-original code but no M01-M11/M13 script,
  level or definition data reaches them. No patch was needed or made; no upstream, staging or
  `PATCH_INVENTORY.json` change.
- Wide characters: `WCHAR` is 2 bytes everywhere in the Vita build (`-fshort-wchar` on compile and
  link, `static_assert(sizeof(WCHAR) == 2)`), and the wide libc surface used by HUD, objective and
  conversation text is replaced by 16-bit-safe code. One non-campaign `swscanf` use and one
  benign uninitialized read are recorded below.

## Inputs

| Input | Identity |
|---|---|
| Retail Data | read-only Vita3K tree `.../ux0/data/renegade/retail/Data` (always.dat, always.dbs, Always2.dat, M01-M11.mix, M13.mix) |
| strings.tdb candidates | always.dat: 11,655 IDs, 5 or 7 translations per ID; always.dbs: 11,678 IDs, 1 per ID (same hashes as `OBJECTIVE_TEXT_READINESS.md`) |
| Global conversations | `conv10.cdb`, only in always.dbs: 3,606 conversations |
| Runtime strings source | `STRINGS.TDB` through `_TheFileFactory`, mounted Always2.dat, Always.dbs, Always.dat, then the mission archive; only the two always archives contain it, so both candidates were checked |
| Tools | `tools/audit_mission_conversations.py` (per-map receipts), `tools/audit_objective_text_readiness.py` (M13), new `tools/audit_text_conversation_closure.py` |

## Per-map conversation closure

Names are the lower-cased conversation names found by the existing conversation audit in each
map's script-closure source scan (literal `Create_Conversation`, known-name string leads and exact
parameter tokens). "Level" means the map's `.ldd`/`.lsd`; "global" means `conv10.cdb`.

| Map | Names | Level | Global | Missing | Remarks | Text IDs | TDB absent | Voiced | No voice | Sound def absent |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| M13 | 105 | 104 | 0 | 1 | 120 | 114 | 0 | 114 | 0 | 0 |
| M01 | 81 | 80 | 0 | 1 | 135 | 125 | 0 | 112 | 13 | 0 |
| M02 | 60 | 59 | 0 | 1 | 79 | 79 | 0 | 79 | 0 | 0 |
| M03 | 36 | 36 | 0 | 0 | 54 | 52 | 0 | 50 | 2 | 0 |
| M04 | 29 | 29 | 0 | 0 | 45 | 45 | 0 | 43 | 2 | 0 |
| M05 | 78 | 42 | 36 | 0 | 107 | 106 | 0 | 102 | 4 | 1 (text 1905) |
| M06 | 60 | 60 | 0 | 0 | 112 | 110 | 0 | 108 | 2 | 0 |
| M07 | 29 | 29 | 0 | 0 | 54 | 54 | 0 | 53 | 1 | 0 |
| M08 | 40 | 40 | 0 | 0 | 48 | 47 | 0 | 47 | 0 | 0 |
| M09 | 10 | 10 | 0 | 0 | 27 | 27 | 0 | 27 | 0 | 0 |
| M10 | 53 | 52 | 0 | 1 | 86 | 84 | 0 | 82 | 2 | 0 |
| M11 | 29 | 25 | 4 | 0 | 55 | 54 | 0 | 54 | 0 | 0 |

"Voiced" is a positive translation sound ID; "no voice" is an absent, zero or negative sound ID
(the original treats `sound_def_id > 0` as the only playable case). Counts are identical for both
`strings.tdb` candidates.

Names assigned to a variable before `Create_Conversation(variable, ...)` (19 variables across
`Code/Scripts/*.cpp`, 378 literal assignments, no `sprintf`/`strcpy` construction found) were checked
separately against the union of all 12 maps' level and global conversation names. Every assigned
literal in `Mission01`-`Mission11` and `MissionX0` exists. The only literals absent from that union
are in `Mission00.cpp` (M00 tutorial and `MSK_MP_*` skirmish names, a map outside this task) and in
`Test_DLS/DME/RAD.cpp` (unbound test scripts). The existing audit's exact-name leads cannot flag a
misspelled variable-assigned name, which is why this extra pass was needed.

The 499 global-database sound-definition gaps reported by `audit_mission_conversations.py` and the
four sound-file gaps belong to global conversations no M01-M11/M13 script references (their
`referenced_by_authored_level` flag is false); they are not part of any map's closure above except
text 1905.

## The four missing conversation names

| Map | Script, line | Name | Dependency on the conversation |
|---|---|---|---|
| M13 | `MX0_MissionStart_DME` (MissionX0.cpp:97) | `MX0_ENGINEER1_048` | `Start_Conversation(id, 100048)` and `Monitor_Conversation`; nothing handles action 100048. No stall. |
| M02 | `M02_Respawn_Controller` (Mission02.cpp:3244) | `M02_HIDDEN_02_FINISH` | Fired after the objective custom event; no monitor, no action handler. No stall. |
| M10 | `M10_Radar_Scramble` (Mission10.cpp:4359) | `M03CON068` | `Monitor_Conversation`; no handler for 100068. A second call at :4462 uses the same name. No stall. |
| M01 | `M01_TurretBeach_GDI_Guy_01_JDG` (Mission01.cpp:8069) | `M01_TurretBeach_TurnOverTank_Conversation` | Script is not in the map's bound closure (not attached by level data). If it ever ran, only its post-conversation walk would be skipped. |

Telemetry signature on Vita: `A35_Script_Lookup_Record(A35_LOOKUP_CONVERSATION, name, 0, found=0)`
for these names (`Create_Conversation`, scriptcommands.cpp:2456-2492). Seeing found=0 for them is
expected and not a defect.

## Script string-ID arguments

`tools/audit_text_conversation_closure.py` scans every `Code/Scripts/*.cpp` call to the four
string-ID commands (568 calls, comments stripped):

- Literal `0` or `NULL` passed as a string ID: **0**.
- `Add_Objective` calls that omit the long-description ID (defaults to 0, so `TRANSLATE(0)` is
  NULL): 33 calls, none live in campaign data:
  - `Mission06.cpp:190`, objective 610 (hidden, short ID 1000). Objective 610 is created hidden
    and nothing in Mission06.cpp ever changes its status, so the EVA objectives list (which skips
    hidden entries) never shows it.
  - `Toolkit_Objectives.cpp` (27 calls): designer toolkit script. Its name does not occur in any
    `.ldd`/`.lsd` of M01-M11 or M13.
  - `Test_BMG.cpp` (5 calls): test script, not bound to missions.
- `Display_Text`, `Display_Int`, `Display_Float`: no mission script calls them.
- `Get_String` of the translation database: not used by any script (`Text_File_Get_String` reads
  cinematic control files, narrow text).
- Cinematics: control files carry preset names (`Play_Audio` calls `Create_2D_Sound` by preset
  name) and no text or string IDs. Cinematic text closure therefore reduces to the preset-name audio
  audits, not to `strings.tdb`.

## Vita code-path trace for missing strings and conversations

Staged sources are the build input (`staging/`); the quoted behavior is original except where the
port block is named.

| Situation | Path | Result |
|---|---|---|
| `Get_String(0)` | translatedb.h:250 | NULL by design |
| `Get_String(id)` unknown, not loaded, or id < 1000 | translatedb.h:257-290 (`WWASSERT` then range test) | non-NULL placeholder wide string `TDBER` |
| `Find_Object(id)` unknown | translatedb.h:388 | NULL |
| `Set_HUD_Help_Text(0)` | scriptcommands.cpp:3306 | clears with an empty string |
| `Set_HUD_Help_Text(unknown)` | scriptcommands.cpp:3315-3328 | shows `TDBER`; Vita tutorial caption override only for known IDs in language 0 (ASCII) |
| `Display_Text(unknown)` | scriptcommands.cpp:1566 | no-op |
| `Say_Dynamic_Dialogue(unknown text)` | soldier.cpp:3575 | skips body, returns 2.0 s; conversation advances |
| Sound def absent (text 1905) | `WWAudioClass::Create_Sound` -> `Find_Definition` NULL | NULL sound; duration stays 2.0 s; `speaker->CurrentSpeech = NULL`; text still shown (Vita forces `display_text = true`) |
| Empty text string | soldier.cpp:3620 guard `string[0] != 0` | no message |
| `Create_Conversation(unknown)` | scriptcommands.cpp:2456 | returns -1 |
| `Join/Start/Stop/Monitor_Conversation(-1)` | `Find_Active_Conversation(-1)` | NULL, each command no-op |
| Beacon, base controller, building announcements | beacongameobj.cpp:1210, basecontroller.cpp:1148, building.cpp:821 | guarded `if (translate_obj)` |
| Weapon, powerup and vehicle names with ID 0 | hud.cpp:1030/3297, vehicle.cpp:2568 | `WideStringClass` ctor and `operator=` accept NULL; vehicle has an explicit fallback ID; hud target name guarded by `!= 0` |
| `Add_Objective` with short ID 0 | objectives.cpp:511 | `Format` receives an empty wide string; no deref |

Latent hazards (retail-original code, unreachable with the data above, not patched):

1. `ObjectivesViewerClass::Compare` (objectivesviewer.cpp:330-332) passes
   `TranslateDBClass::Get_String(ShortDescriptionID)` to `wcsicmp`; a short ID of 0 is a NULL
   dereference. No script passes a zero short ID.
2. `dlgevaobjectivestab.cpp:162` calls `Set_Dlg_Item_Text(IDC_DESCRIPTION_EDIT, TRANSLATE(LongDescriptionID))`.
   A visible objective added without a long ID reaches `Set_Text(NULL)`; if that control is an
   `EditCtrlClass`, `rv_utf16_length(NULL)` dereferences NULL (`MultiLineTextCtrlClass` would accept
   it). Only the hidden M06 objective 610 and the unused toolkit/test scripts lack a long ID.
3. `TDBObjClass::Get_String(lang)` (translateobj.cpp:418) falls back to index 0 without checking
   `Count() > 0`; a string object with no translation chunks would index past the array. Every retail
   row has at least one translation (histogram: always.dat 5 or 7, always.dbs 1).

Corrupt-save conversation hazard is unchanged and already recorded in `CONVERSATION_COMPLETION.md`
(open item 2).

No patch was made: none of these is reachable from the campaign data, and a speculative guard
would add SHA-anchored staging patches, stage-script entries and an inventory regeneration for
behavior that cannot occur. If the objective data is ever extended (Toolkit objectives, new
HIDDEN-to-PENDING transitions), hardening 1 and 2 should be applied with a deterministic patch.

## Wide-character assumptions

- `WCHAR` is `wchar_t`, compiled with `-fshort-wchar` (CMakeLists.txt compile options and link
  options, `RENEGADE_SHORT_WCHAR_ABI=1`), so literals and stored strings are UTF-16 as under Win32.
  `win32_compat.h` asserts `sizeof(WCHAR) == 2` on Vita and in host ABI builds.
- libc wide functions are built for a 4-byte `wchar_t`; the port replaces the ones in use:
  `wcslen, wcscmp, wcsncmp, wcscpy, wcsncpy, wcschr, wcsrchr, wcsstr` as `extern "C"` 16-bit
  versions (`port/platform/a31_miscutil_boundary.cpp`), `_wcsicmp/_wcsnicmp/wcsicmp/_wcsupr/_wtoi`
  and `CompareStringW` to `rv_utf16_*`, and `WideStringClass` storage to `rv_utf16_length/compare`.
- `WideStringClass::Format` uses `_vsnwprintf` mapped to `rv_utf16_vsnprintf`: `%s` and `%ls`
  wide, `%S`/`%hs` narrow, `%c`, integer and float conversions, `%I64`, `%n`, a NULL `%s`
  argument prints `(null)` instead of faulting. The only conversion specs present in the retail
  English strings are `%s %d %lu %S %u %.2f %.01f %-8d %.02d %.2d %.01d %.3u %tS`; all are
  handled (`%tS`, one multiplayer string, is parsed as a `t` length with a narrow-string spec).
  No English string holds a surrogate pair.
- Persistence: `chunkio.h` writes wide strings with an explicit `* 2` byte count and `savegame.cpp`
  validates `length % sizeof(WCHAR)`; both agree with 2-byte `WCHAR`.
- `MultiByteToWideChar` and `WideCharToMultiByte` are Latin-1 byte copies (values above 0xFF map to
  `?`). English strings are ASCII plus U+000A, so this is exact for the supported language.
- Remaining items, none on the campaign path:
  - `DialogBaseClass::Get_Dlg_Item_Float` (wwui/dialogbase.cpp:633) calls libc `swscanf` on 2-byte
    text. Only the developer tuning dialogs in `commando/dialogtests.cpp` call it. If those dialogs
    are ever exposed, replace it with a 16-bit parser.
  - `StringClass::Copy_Wide` (wwlib/wwstring.cpp:326) returns `!unmapped` where `unmapped` is
    uninitialized: the compat `WideCharToMultiByte` (port/compatibility/include/win.h:120) returns
    before writing `*used_default_character` on a size query. Its callers
    (`WideStringClass::Convert_To`, used for the English-string copy at load) ignore the result.
  - Non-English languages need CJK glyphs the font set lacks (see `OBJECTIVE_TEXT_READINESS.md`);
    English is the runtime language.

## Reproduce

```sh
python3 -m tools.audit_mission_conversations --data /path/to/retail/Data \
  --output-directory build/conv $(for m in M13 M01 M02 M03 M04 M05 M06 M07 M08 M09 M10 M11; do echo --map $m.mix; done)
python3 -m tools.audit_text_conversation_closure --data /path/to/retail/Data \
  --receipts build/conv --output build/closure/closure.json
python3 -m tools.audit_objective_text_readiness --data /path/to/retail/Data --font-dir <dir> \
  --map M13.mix --owner-scan --output-directory build/objtext13
python3 -m unittest tools.test_audit_text_conversation_closure
```

The first command takes several minutes on `/mnt/c`; the second needs the staged `upstream/`
checkout for the script scan. Detailed JSON stays under ignored `build/`.

## Physical validation signatures

- M05 `M05_CON059` (text 1905): conversation transitions advance with a 2.0 s remark duration, no
  sound-created record for the remark, text visible in the message window, `Action_Complete`
  delivered at the end.
- `A35_LOOKUP_CONVERSATION` found=0 for the four names above, and no fault afterward.
- No `TDBER` in HUD help, objective or conversation text during M01-M11/M13 play (a `TDBER`
  string would mean an ID outside the loaded database).

## Limits

Source and data scan only. Names built dynamically, runtime-mounted overrides, mod data, saves,
subtitles layout, font rendering, lip-sync and audio playback are not covered. The two candidate
databases agree for every referenced ID; the exact mount-order winner was not re-derived because
it does not change any result.
