# Cross-system deep content/owner audit — 2026-09-27

**Coverage is incomplete.** This source/data audit found shared startup and UI
omissions as well as missing scripts. It does not restore them or establish
runtime acceptance. No C++ compilation, game execution, server contact,
installation, device access or retail/save modification occurred.

## Source-only follow-up — 2026-10-02

The five additional original script owners and three W3D object owners listed
below have since been added to the native and host source graphs. The Vita
startup now registers the original particle-emitter, sphere, ring and
sound-render-object loaders and restores the original particle lifetime and
17 LOD defaults. A fresh static sweep of Tutorial, Practice, M13, M01 and 13
installed C&C maps reports no unselected required script or persistence-
factory owners in the configured native source graph. This closes source
selection findings only; the source has not been compiled or runtime-tested.

The same sweep retains two M01 content leads: `X01_ConYardDrop.txt` is attached
by `M01_ConDropZone_JDG` but absent from the inspected retail archives/loose
files, while the HONEscort text member's three unresolved script names have no
proved attachment path. Do not implement or alias the latter without reachability
evidence. Remaining UI/options, save/load and multiplayer gaps below are open.

The original `IDD_MENU_OPTIONS` template and its Tech Options route have now
been added to the Vita single-player frontend source path. The Vita page hides
Controls, Movies, Credits and Multiplayer Options because their original
owners/routes are still unavailable. Static tests verify the generated
template controls and route. This source change remains uncompiled; it does not
close the Controls/Movies/Credits or broader frontend findings below.

This supersedes the narrower scope/counts in the preceding M00/M13 audits.
Those earlier persistence-factory checks did not cover WW3D prototype loader
registration, dialog resources, network events or all global cinematics.

## Highest-priority confirmed findings

### 1. Four original WW3D bootstrap registrations are missing

Original `Commando/init.cpp:813` registers particle-emitter, sphere, ring and
sound-render-object loaders. Native `port/platform/vita/a31_vita_runtime.cpp:3573`
creates WW3DAssetManager, enables load-on-demand and fog, but omits these
registrations. The base asset-manager constructor registers nine other types.
The configured-source census finds no direct registration of these four.

| Original owner | Source selection / existing ARM ELF | Consequence |
| --- | --- | --- |
| `ww3d2/part_ldr.cpp` | Selected; `_ParticleEmitterLoader` defined; not registered | Linked code alone cannot make this emitter loader discoverable by the asset manager. |
| `ww3d2/sphereobj.cpp` | Unselected; loader global absent | Original sphere prototype owner missing. |
| `ww3d2/ringobj.cpp` | Unselected; loader global absent | Original ring prototype owner missing. |
| `ww3d2/soundrobj.cpp` | Unselected; loader global absent | Original embedded sound-render-object owner missing. |

Bounded root-chunk parsing of **3,330 W3D archive entries** found **429 entries**
requiring these loaders: 414 emitters, five spheres, three rings and seven
sound objects. No malformed W3D member was found. Three sound objects are in
M01.mix: sfx_gdi_orca.w3d, sfx_nod_apache.w3d, sfx_nod_heli.w3d. The remaining
hits are in global archives. These counts describe available content, not
proof that every asset appears on every route. Restoring a loader still
requires correct original rendering/audio behavior and native validation.

### 2. Five original script files were absent from the audited baseline

The following are historical baseline findings. The source-only follow-up
above has selected these owners; current compile/link/runtime status is not
established.

| Requested area | Unselected required script owners |
| --- | --- |
| Tutorial | `Test_DAK.cpp` |
| Multiplayer Practice | `Test_DAK.cpp`, `Toolkit_Sounds.cpp` |
| Scorpion Hunters / M13 | `Mission03.cpp`, `Test_RMV_Toolkit.cpp`, `Toolkit_Sounds.cpp` |
| M01 | `Mission03.cpp`, `Mission11.cpp`, `Test_DAK.cpp`, `Test_RMV_Toolkit.cpp` |

`Mission11.cpp` is **newly confirmed for M01**: M01.ldd saves
M11_Temple_Hologram_01_JDG at offset 762075 on object 157978, definition
81960071. Mission11.cpp:5826 starts the looping DSP_HOLO_BIG animation.
This is different from the unconfirmed soldier-table lead in earlier audits.

The five units selected in the earlier video correction remain unbuilt:
Test_RAD.cpp, Toolkit.cpp, Toolkit_Objects.cpp, Test_DAY.cpp and mission08.cpp.
Across all 17 inspected maps, the unchanged Dev207 ARM executable lacks
**39 distinct required script factory methods**. Practice lacks 13, including
guard-tower/Obelisk/base-defense helpers, terminal poke indication, building
sound controllers, and pickup/transition helpers. Thus the omissions extend
well beyond cosmetic tutorial camera shake.

### 3. M01 has source/data dependencies that adding .cpp files cannot resolve

- M01.ldd places M01_ConDropZone_JDG on object **119825**, definition 519.
  Mission01.cpp:17994 attaches Test_Cinematic with **X01_ConYardDrop.txt**.
  This name is absent from the inspected map/global archives, all other
  installed archive indexes, and loose files in the inspected retail root.
  Do not invent or silently alias the missing sequence.
- M01.mix/xg_m01_honescort_evacanim.txt references
  **M01_HONescort_Air_Evac_Waypath_JDG** (line 37),
  **M01_HONescort_Air_Evac_Chopper_JDG** (45), and
  **M01_HONescort_Air_Evac_Rope_JDG** (52). No declaration or occurrence of
  these names exists in the released Scripts source. The text exists, but
  this audit has not proved its runtime trigger/reachability. These remain
  unresolved source/data contract findings, not invented missing filenames.

### 4. Main-menu Options exposed a resource and routing gap

The audited baseline showed `OptionsMenuClass` requesting
**IDD_MENU_OPTIONS (135)**, absent from both the full-port template selection
and generated templates. Source now selects that original template, routes its
Tech button to the supported `TechOptionsMenuClass`, and hides the four
unavailable routes. These changes remain uncompiled. The full-port defines
RENEGADE_VITA_FRONTEND_SINGLEPLAYER; its reduced
renegadedialogmgr.cpp FactoryArray still leaves Controls, Movies, Credits and
other original routes null. The supported Tech Options route now opens
directly from the Options page. This flag remains enabled even when
RENEGADE_VITA_M00_DEMO=0.

The relevant omitted original owners include dlgcontrols.cpp,
dlgcontrolslisttab.cpp, dlgcontroltabs.cpp, dlgcontrolsaveload.cpp,
inputconfig.cpp, inputconfigmgr.cpp, dlgmovieoptions.cpp and dlgcredits.cpp.
Restoration must preserve Vita input/platform boundaries rather than import
DirectInput or Windows process ownership.

The pause menu **does** open TechOptionsMenuClass directly. Its audio/video/
performance owners and templates are present. Audio and supported performance
settings have explicit native Save/Apply paths; the process-local registry
stub is not evidence those native settings are lost. However,
SystemSettings::Apply_All is an empty boundary substitute, and
TechOptionsMenuClass::On_Destroy ignores Apply_Changes_On_Tabs' failure result.
This is a generic-settings/error-feedback gap, not proof that all options fail.

### 5. Death/failure and some load routing remain stubbed

Configured god.cpp includes a31_god_ui_stub.h, a31_gameinit_stub.h and
a31_dialogmgr_stub.h unconditionally. Star_Killed/Mission_Failed allocate
substitute popups whose Start_Dialog does nothing. cGod::Load_Game calls
substitute End_Game/Goto_Location methods which do nothing.

The real death/failure handlers in dialogtests.cpp are excluded by
RENEGADE_VITA_FRONTEND_SINGLEPLAYER. Their templates 196/197 are present;
template presence alone does not restore behavior. The normal single-player
pause EVA, main load dialog, pause save dialog and deferred-load path are
selected and were separately traced. This is not a claim all loading is absent.

### 6. Save failures are not propagated to the save dialog

Original `combat/savegame.cpp:99` calls FileClass::Open(WRITE) without checking
its result, does not aggregate serialization/write success, and returns void.
`commando/dlgsavegame.cpp:330` then closes the dialog after calling Save_Game.
The disk-space check does not prove the file opened or completed successfully.
This is a confirmed error-reporting/integrity gap, **not a demonstrated cause
of the user's or reporter's specific save failure**. Save bytes were untouched.

### 7. Multiplayer UI, events and lifecycle coverage remain partial

- Original C&C pause/reference, team/battle/server-info and win-screen owners
  are unselected: dlgcncreference.cpp, dlgcncteaminfo.cpp,
  dlgcncbattleinfo.cpp, dlgcncserverinfo.cpp, dlgcncwinscreen.cpp.
- Team-selection, connection/refusal and local server-message call sites still
  use no-op dialog substitutes. Original LAN lobby/host/settings owners and
  radiocommanddisplay.cpp are excluded. Existing direct-IP/TT provider,
  purchase dialogs, replicated chat and native connection path are distinct
  implemented capabilities; their presence does not close these gaps.
- Native remote-client START explicitly disconnects and returns to the menu
  until original multiplayer menu/round flow is connected
  (a31_vita_runtime.cpp near 4393). It does **not** enter the SP pause loop.
- The original network-factory macro census finds **39 classes, 11 absent
  owners/vtables**: clientbboevent.cpp, consolecommandevent.cpp,
  csconsolecommandevent.cpp, donateevent.cpp, godmodeevent.cpp, moneyevent.cpp,
  requestkillevent.cpp, scoreevent.cpp, suicideevent.cpp, vipmodeevent.cpp,
  warpevent.cpp. Suicide/donation and bandwidth-event behavior must be
  distinguished from optional console/developer/cheat events. This does not
  prove live servers require all eleven; the macro census excludes manual
  factories and is not a full protocol-compatibility test.
- Legacy WOL/GameSpy web/auth/master services remain provider-policy
  exclusions, not requirements to revive obsolete services.

## All requested areas and data coverage

| Area | Reviewed presets | Required scripts | Missing old-ELF factories | Persist types / source-bound callbacks |
| --- | ---: | ---: | ---: | --- |
| Tutorial | 323 | 27 | 3 | 53 / 97 |
| Practice | 305 | 19 | 13 | 50 / 54 |
| Scorpion Hunters (M13) | 415 | 75 | 25 | 44 / 102 |
| M01 | 555 | 308 | 14 | 55 / 128 |

The script sets conservatively include every mission-prefix registration,
even diagnostic branches. Broader token discovery covers 593/629/1161/907
possible presets respectively; these are leads, not proven execution.
Literal shared cinematic references now resolve across map and global
archives: one tutorial text, 18 M13 archive/member entries, 148 M01 entries.
Collision candidates are retained; exact runtime archive precedence is not
asserted by this audit.

All **13 installed retail C&C maps** were swept: Canyon, City, City_Flying,
Complex, Field, Glacier_Flying, Hourglass, Islands, Mesa, Under, Volcano,
Walls and Walls_Flying. Glacier's **seven map-local DDB definitions** are
merged and traversed; it reaches 242 presets and 50 persist types. No other
inspected map contains a DDB overlay. These maps need the shared script
corrections; no additional mapped persistence-factory owner/Load-method gap
was found. Across 17 maps, 69 unique reached persistence-factory types have
their original source owners and existing ELF Load methods.

Main menu/options, load/save, pause and multiplayer were additionally checked
against original routing, full-port preprocessor guards, selected source,
generated resources, compatibility headers and retained symbols. Of 31
reviewed UI resource IDs, **22 are absent**; the generated set has 30 templates.

The source census inventories **609 configured translation units**, 630
original units in eight relevant modules, 158 unselected original units,
78 substitute-header include edges and 90 constant/empty port methods.
Those last three counts are **review candidates, not 158+ missing features**.
Examples rejected as false positives: header-only statemachine.cpp, host-only
WWAudio/TextDisplay substitutes, the inactive Bink fallback, and Windows
DirectInput/IME/DX8 interfaces replaced by native providers.

Conversation decoding covers 65 tutorial, 24 Practice, 570 M13 and 89 M01
records (748 total). **17 local save files / 10 distinct hashes** decode;
two files use the one-byte category format already supported by the staged
loader. Save scripts still expose two old-ELF missing helpers. A save can only
contain scripts successfully instantiated when written; a clean save census
cannot establish complete level coverage.

## Validation, receipts and next work

77 asset-free Python checks pass. The new coverage gate deliberately returns
**INCOMPLETE (exit 1)** with 73 categorized entries, including duplicated map
manifestations; this is not a count of 73 distinct bugs. It is a standalone
audit guard, not yet wired into build scripts, and it cannot validate runtime.
Existing 62-script M13 gate is insufficient for these broader findings.

Receipts under build/: dev208-deep-content/{summary,*-typed,*-discovery}.json,
dev208-cross-system-owners.json, dev208-frontend-resources.json,
dev208-w3d-loader-coverage.json, dev208-deep-saved-content.json,
dev208-deep-coverage-gate.json and dev208-deep-audit-tests.log. They contain
metadata, IDs, hashes and dependency edges, not redistributed assets/saves.
Reproduction commands are in `tools/DEEP_AUDIT.md`.

Existing ELF SHA-256 remains
`187cfec06117cd0549a8fbb3df387bc5f90908bbb25fe650b84bb6630f95db9d`.
It is ELF32 little-endian ARMv7/Thumb-2, hard-float. Existing savegame.o and
all 30 inspected vitaGL objects agree on VFP-register arguments. savegame.o
uses two-byte wchar_t; vitaGL objects use four-byte wchar_t. Merged ELF
attributes do not override explicit original 32-bit serialization/UTF-16
boundary checks. No new ARM compilation was performed.

Restoration order: original WW3D registrations/three owners; five script
owners and expanded registry gates; death/load/save feedback and Options
resource/routing; multiplayer menu/round/event ownership. Then validate full
normal routes, save round trips, repeated sessions and native rendering/audio.

This is deep **static discovery**, not proof no further defects exist. Remaining
uncertainty includes computed/parameter-driven names, unresolved typed IDs,
full C++ control flow, every nested W3D/model reference and asset override,
server-provided mods/manual network factories, real save writes, runtime
registration, menu interaction, visuals, audio and physical-device behavior.
No native acceptance gate was closed; build/launch hold remains active.
