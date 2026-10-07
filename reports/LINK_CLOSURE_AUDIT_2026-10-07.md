# Link-closure audit without linking — 2026-10-07

Evidence class: host static analysis only. No CMake/ninja build, no link, no
VPK, no Vita3K, no physical Vita. This report does not prove that the next
ARM link succeeds; it lists every gap the analysis could see and fixes the one
confirmed defect.

## Baseline and scope

- Last full ARM link: `build/vita-fast-candidate/RenegadeVitaA31`, A3.5-dev238,
  2026-10-04 17:46 -0500 (ELF sha256 `32d26134…d21e`). The source state matches
  commit `d0f993b` (committed 5 minutes after the link). 185 commits since.
- Baseline symbols: `arm-vita-eabi-nm` over all 653 dev238 objects on the
  link line, plus the 50 link-line archives and the toolchain spec's default
  libraries (`SceKernelThreadMgr_stub`, `SceProcessmgr_stub`,
  `SceKernelModulemgr_stub`, ...).
- Current symbols: libclang 18 (`--target=armv7a-none-eabihf`, Vita GCC
  include paths, `-fshort-enums -fshort-wchar`, plus the four new
  `RENEGADE_VITA_*` defines) over all 680 current Vita TUs: the 650 dev238
  TUs (every one depends on a changed forced-include header) and the 30 new
  ones. It recorded definitions and odr-used function/variable references in
  each main file and in the 104 staging/port headers changed since dev238. It
  compared Itanium mangled names with the GCC/nm sets. Clang and GCC predefine
  identical `__INT32/SIZE/WCHAR_TYPE__` types on this target.
- The patched TU was rechecked with `arm-vita-eabi-g++ -fsyntax-only` (rc 0).

## Source lists (task item 2)

| Check | Result |
|---|---|
| New `.cpp` under `port/` since dev238 | 2: `renegade_vita_frame_profile.cpp` (in `RENEGADE_A30_PORT_SOURCES`) and `renegade_vita_direct_ip_dialog.cpp` (in the `RENEGADE_A4_ORIGINAL_FRONTEND` list, which is ON). Both are listed. |
| New staged TUs added to CMake | 28 (17 frontend + 5 interactive + 7 multiplayer, two of the 30 new entries are the port files). All exist and none was already listed. |
| Listed sources that no longer exist | none |
| Tracked `port/**/*.cpp` not in any CMake list | 9, all host/validation or retired files last changed 2026-09-26 or earlier (`main.cpp`, `a30_static_world_boundary.cpp`, `port/validation/*`). None is new, and none is referenced by the Vita target. |

## Defects

| # | Location | Severity | Evidence | Status |
|---|---|---|---|---|
| 1 | `port/patches/commando-a36-lan-team-selection.patch` → `staging/commando/DlgMPTeamSelect.cpp:598-1071` (pre-fix) | **High: link failure** | With `RENEGADE_VITA_LAN_FRONTEND=1`, one `#if !defined(RENEGADE_VITA_LAN_FRONTEND)` block ran from `RequestWOLGameInfo` to the end of the WOL handlers. That also compiled out `DlgMPTeamSelect::ShowTimeRemaining(float)` and `FindPlayerInListCtrl(const WCHAR*, ListCtrlClass*&, int&)`. The patched header still declares both for the LAN build. Active code still calls them: the virtual `On_Frame_Update` (line 422) and `RemoveLANPlayerInfo` (line 1210). The vtable is emitted with the class, so `--gc-sections` cannot drop `On_Frame_Update`. Neither symbol is defined in any dev238 object or any current TU. | **Fixed.** The guard is now split so it covers only `RequestWOLGameInfo` and the WOL notification/processing block. Both shared helpers are compiled again; their dependencies are already defined: `cMiscUtil::Seconds_To_Hms` (`a31_miscutil_boundary.cpp`), `ListCtrlClass::Find_Entry` (`listctrl.cpp`) and `DialogBaseClass::Set_Dlg_Item_Text` (`dialogbase.cpp`). The patch applies with zero fuzz and `stage_sources.sh` exits 0 (525 ordered patches). Staged diff: +2 preprocessor lines. |

No other unresolved reference was confirmed. Every remaining candidate is
triaged below.

## Unresolved-reference triage (task items 1 and 5)

| Candidate | Classification |
|---|---|
| `vglRenegadeInvalidateVertexAttributes` (`ww3d_vita_renderer.cpp:68,2313,2384`) | Resolves at the next build, but it is a **build-order requirement**. The `libvitaGL.a` currently on disk under `build/deps/vitagl-demo` does not define it. `port/renderer/vita/dependency-patches/vitagl-attribute-invalidation.patch` adds it as a C function in `ffp.c`, matching the `extern "C"` declaration. A scratch apply of all six vitaGL patches to the pinned `6e7fe40` sources succeeded with fuzz 0. `tools/build_vitagl_demo.sh` puts this patch in its identity hash, and both `build.sh` and `build_fast_candidate.sh` run it before linking. A manual link against the stale archive would fail. |
| `sceKernelChangeThreadCpuAffinityMask`, `sceKernelCreateCallback`, `sceKernelDelayThreadCB`, `sceKernelPowerTick` (new calls in `a31_vita_runtime.cpp`, `vita_platform.cpp`, `renegade_miles_provider.cpp`, `a35_campaign_flight_recorder.cpp`, `a4_binkmovie_boundary.cpp`) | Resolved by the `arm-vita-eabi-gcc` spec default libraries `libSceKernelThreadMgr_stub.a` and `libSceProcessmgr_stub.a`. The dev238 map already pulls `sceKernelDelayThread` from the same archive. |
| `DX8FVFCategoryContainer::Add_Visible_Material_Pass` (11 TUs, via `dx8renderer.h:287`) | False positive. It is only referenced by the inline virtual `DX8SkinFVFCategoryContainer::Add_Delayed_Visible_Material_Pass`. That class's key function lives in `dx8renderer.cpp`, which is not in the Vita target, so GCC never emits the vtable or the inline body. The `mesh.cpp:843` call is preprocessor-inactive. |
| `RenegadeResolvedPath()`, `StaticMeshEntry()` constructors | False positive: implicit inline constructors of aggregate structs. |
| `std::move<…>` instantiations, `__builtin_*` | False positive: templates and builtins. |
| `__real_shark_init` | Pre-existing; satisfied by `-Wl,--wrap=shark_init`. |
| `DX8Wrapper::*Render_Device*`, `*Swap_Interval`, `Toggle_Windowed`, `Flip_To_Primary` (`ww3d.cpp`), `FindResourceEx` (`renegadedialogmgr.cpp`), `WWDebug_Printf` (`wwprofile.cpp`), `TextFileClass::Read_Line` (`hmorphanim.cpp`), `MissingTexture::_Get_Missing_Texture` (`texture.cpp`), `PKey::*` (`ini.cpp`) | Pre-existing: these were already undefined in the same dev238 objects, and that link succeeded because `--gc-sections` drops the unreachable callers. The analysis confirms no new caller. |

## Changed/removed definitions (task item 3, signature drift)

Strong dev238 definitions that clang no longer saw under the same mangled
name. I checked each one against current callers. No reference to an old
mangled name remains in any active TU.

| Old dev238 definition | Current state |
|---|---|
| `A31_Vita_Run_Interactive_Runtime(int,bool,const char*,const char*,const unsigned char*,unsigned)` | Signature extended to `(int,bool,bool,const char*,const char*,const unsigned char*,unsigned,int,const char*,bool)`. The only caller, `a30_main.cpp:236`, matches. |
| `RenegadeVitaRenderer::Begin_Frame(float,float,float)` | Now `Begin_Frame(bool,bool,float,float,float)`; callers updated. |
| `CombatGameModeClass::Core_Restart()` | Now `Core_Restart(bool(*)(void*),void*)` plus `Process_Core_Restart_Request`; callers updated. |
| `SaveGameManager::Load_Definitions(const char*)` | Now `(const char*, bool)`; callers updated. |
| `SaveLoadSystemClass::Load(ChunkLoadClass&, bool)` | Now `(ChunkLoadClass&, bool, bool)`; callers updated. |
| 17 `DX8Wrapper` statistics members (`Begin/End/Reset_Statistics`, `Get_Last_Frame_*`, `*_changes`) | Unchanged: they are defined in `port/renderer/vita/original_dx8_statistics.inc`, which `ww3d_dx8_boundary.cpp:2070` includes. This is a tool blind spot because unchanged `.inc` files were not traversed. |
| `DX8Wrapper::Set_Light_Environment` | Unchanged: `original_dx8_light_environment.inc`, included by `a31_gameplay_boundary.cpp:1671` (same blind spot). |
| `Destroy_Script`, `Set_Script_Commands`, `Set_Request_Destroy_Func` | Unchanged since dev238 (`renegade_script_static_provider.cpp:21,44`); clang partially failed on the GCC-only default arguments in `scriptcommands.h`. |
| `Objective_Radar_Locations` | Unchanged header-defined array (`staging/scripts/mission2.h`). |

## Duplicate definitions and linkage (task items 3 and 4)

- Duplicate strong external definitions across current TUs: **none**. Only
  non-inline definitions in main files and changed headers were compared.
- Port overrides of libc symbols: `wcslen`, `wcscmp`, `wcsncmp`, `wcscpy`,
  `wcsncpy`, `wcschr`, `wcsrchr`, `wcsstr` in `a31_miscutil_boundary.cpp`.
  These predate dev238 and are unchanged. Each newlib archive member defines
  one function, so the object definitions win without a clash, as in dev238.
- `_newlib_heap_size_user`: a strong `extern "C"` definition in
  `port/platform/vita/a30_main.cpp:27-29` (192 MiB). newlib `sbrk.o` and
  `ww3d_vita_renderer.cpp:44` both hold weak undefined references (`w`). The
  types agree (`unsigned int`) and the renderer guards the address. This is
  correct, with no C/C++ linkage mismatch.
- `ww3d_vita_renderer.cpp:47-48` declares two weak C++ functions,
  `RenegadeVita_Release_DX8_Bound_Textures` and `RenegadeVita_Release_DX8_Render_Target`.
  These are unchanged.
- Patch-added `extern` declarations since dev238 are `bool g_is_loading`
  (defined in `gamemenu.cpp`) and `void Stop_Main_Loop(int)` (defined in
  `a4_frontend_lifecycle_boundary.cpp`). Both resolve.
- Virtual methods declared in the classes of the 28 new staged TUs' headers:
  no non-pure, non-inline virtual without a definition, by heuristic header
  scan.

## Deferred / limits

- Implicit destructor calls, vtable/typeinfo emission and thunks are not
  modelled. Only explicit calls, constructor expressions, member references
  and variable references are.
- Unchanged headers and `.inc` files were not traversed. Definitions that live
  only there come from the dev238 nm baseline, which covers them unless they
  were removed.
- `--gc-sections` reachability was not modelled. A reported pre-existing
  undefined reference stays harmless only while its caller is unreachable.
- 48 TUs had clang-only diagnostics: the 47 script TUs and
  `combat/scripts.cpp` (default arguments on function-pointer members), and
  `persistfactory.cpp` (one incomplete-type use). References inside the
  affected declarations may be missed. Those TUs changed only through
  forced-include headers.
- The final gate is still a real ARM link. The next fast candidate should
  confirm defect 1 is closed and that `build_vitagl_demo.sh` rebuilt vitaGL
  (its identity hash includes `vitagl-attribute-invalidation.patch`).

## New external symbols since dev238 → defining TU

418 symbols in 59 TUs. These are strong, non-inline definitions that are new
or have a new signature, compared with every dev238 object, from the libclang
scan. A few entries in TUs with clang diagnostics can be mangling artefacts.
| Defining TU | New external symbols (demangled) |
|---|---|
| `port/audio/vita/renegade_wave_decoder.cpp` (3) | `RenegadeVitaAudio::Adpcm_Block_Max_Frames(RenegadeVitaAudio::WaveInfo const&, unsigned int)`<br>`RenegadeVitaAudio::Decode_Ima_Block(unsigned char const*, unsigned int, RenegadeVitaAudio::WaveInfo const&, short*, unsigned int, unsigned int*, char const**)`<br>`RenegadeVitaAudio::Decode_Ms_Block(unsigned char const*, unsigned int, RenegadeVitaAudio::WaveInfo const&, short*, unsigned int, unsigned int*, char const**)` |
| `port/developer/a35_campaign_flight_recorder.cpp` (2) | `A35_Campaign_Flight_Set_Background_Flush(bool)`<br>`A35_Campaign_Flight_Wait_For_Background_Flush()` |
| `port/filesystem/renegade_file_factory.cpp` (9) | `RenegadeRootedFileClass::Close()`<br>`RenegadeRootedFileClass::Error(int, int, char const*)`<br>`RenegadeRootedFileClass::Flush_Staged_Writes()`<br>`RenegadeRootedFileClass::Seek(int, int)`<br>`RenegadeRootedFileClass::Size()`<br>`RenegadeRootedFileClass::Stage_Write(void const*, int)`<br>`Renegade_File_Factory_Set_Atomic_Write_Report_Hook(void (*)(char const*, int, unsigned long long, bool))`<br>`Renegade_Recover_Interrupted_Replace(char const*)`<br>`Renegade_Replace_File(char const*, char const*)` |
| `port/filesystem/renegade_registry.cpp` (1) | `RegistryClass::Set_String_Checked(char const*, char const*)` |
| `port/platform/a31_client_connect_boundary.cpp` (8) | `A31ClientConnect::Abort_Pending_Round()`<br>`A31ClientConnect::Commit_Round_Resources_After_Core_Shutdown()`<br>`A31ClientConnect::Complete_Round_Load()`<br>`A31ClientConnect::Observe_Round_Identity(cGameData*, unsigned int, unsigned int, int, bool, bool, char const*, StringClass&)`<br>`A31ClientConnect::Prepare_Round_Resources(bool, RenegadeTTFS::Progress const&)`<br>`A31ClientConnect::Resolve_Round_Source()`<br>`A31ClientConnect::Round_Map_Validity(char const*, bool&)`<br>`A31ClientConnect::Round_Resource_Group_Matches() const` |
| `port/platform/a31_gameplay_boundary.cpp` (2) | `A31_Interactive_Restart_Mission_Completion_Observation()`<br>`RenegadeVita_Release_DX8_Render_Target()` |
| `port/platform/a4_frontend_lifecycle_boundary.cpp` (4) | `A4_Frontend_Latch_Direct_IP(char const*)`<br>`A4_Frontend_Latch_Replay_Level(char const*, int)`<br>`A4_Frontend_Mark_Next_Start_Game_As_Campaign_Level()`<br>`A4_Frontend_Record_Direct_IP_Failure()` |
| `port/platform/renegade_script_static_provider.cpp` (3) | `Destroy_Script(int*)`<br>`Set_Request_Destroy_Func`<br>`Set_Script_Commands(int*)` |
| `port/platform/vita/a30_main.cpp` (1) | `_newlib_heap_size_user` |
| `port/platform/vita/a31_vita_runtime.cpp` (3) | `A31VitaScopedOriginalLoadingScreenCallback::A31VitaScopedOriginalLoadingScreenCallback(void*)`<br>`A31VitaScopedOriginalLoadingScreenCallback::~A31VitaScopedOriginalLoadingScreenCallback()`<br>`A31_Vita_Run_Interactive_Runtime(int, bool, bool, char const*, char const*, unsigned char const*, unsigned int, int, char const*, bool)` |
| `port/platform/vita/renegade_vita_direct_ip_dialog.cpp` (3) | `RenegadeVitaDirectIPDialog::DoDialog()`<br>`RenegadeVitaDirectIPDialog::Finish_Connection()`<br>`RenegadeVitaDirectIPDialog::Take_Cancel_Request()` |
| `port/platform/vita/renegade_vita_frame_profile.cpp` (6) | `Renegade_Frame_Profile_Begin()`<br>`Renegade_Frame_Profile_Begin_Frame()`<br>`Renegade_Frame_Profile_Configure()`<br>`Renegade_Frame_Profile_End(char const*, unsigned long long)`<br>`Renegade_Frame_Profile_End_Frame(unsigned int)`<br>`g_renegade_frame_profile_active` |
| `port/platform/vita/vita_platform.cpp` (2) | `Renegade_Runtime_Log_Enqueue(char const*, unsigned int)`<br>`Renegade_Runtime_Log_Flush()` |
| `port/renderer/vita/ww3d_dx8_boundary.cpp` (5) | `DX8MeshRendererClass::Init()`<br>`DX8MeshRendererClass::Queue_Material_Pass(MaterialPassClass*, MeshClass*, bool, bool)`<br>`DX8MeshRendererClass::Shutdown()`<br>`DX8Wrapper::Draw_Sorting_IB_VB(unsigned int, unsigned short, unsigned short, unsigned short, unsigned short)`<br>`Readback_Render_Target_Surface(IDirect3DSurface8*)` |
| `port/renderer/vita/ww3d_vita_renderer.cpp` (8) | `RenegadeVitaRenderer::Begin_Frame(bool, bool, float, float, float)`<br>`RenegadeVitaRenderer::Bind_Offscreen_Render_Target(unsigned int, unsigned int, unsigned int)`<br>`RenegadeVitaRenderer::Forget_Static_Mesh_Model(void const*)`<br>`RenegadeVitaRenderer::Forget_Static_Mesh_User_Lighting(void const*, void const*)`<br>`RenegadeVitaRenderer::Get_Active_Render_Target_Size(unsigned int*, unsigned int*)`<br>`RenegadeVitaRenderer::Invalidate_Static_Mesh_Cache()`<br>`RenegadeVitaRenderer::Restore_Default_Render_Target()`<br>`RenegadeVitaRenderer::Submit_Material_Pass(MeshClass&, MaterialPassClass&, RenderInfoClass&)` |
| `staging/combat/CNCModeSettings.cpp` (1) | `CNCModeSettingsDef::On_Load_Rejected()` |
| `staging/combat/beacongameobj.cpp` (3) | `BeaconGameObj::On_Post_Load()`<br>`BeaconGameObj::Restore_Weapon_Definition()`<br>`BeaconGameObj::Start_Armed_Sound()` |
| `staging/combat/characterclasssettings.cpp` (1) | `CharacterClassSettingsDefClass::On_Load_Rejected()` |
| `staging/combat/evasettings.cpp` (2) | `EvaSettingsDefClass::On_Load_Rejected()`<br>`EvaSettingsDefClass::On_Post_Load()` |
| `staging/combat/globalsettings.cpp` (2) | `GlobalSettingsDef::On_Load_Rejected()`<br>`HUDGlobalSettingsDef::On_Load_Rejected()` |
| `staging/combat/purchasesettings.cpp` (1) | `PurchaseSettingsDefClass::On_Load_Rejected()` |
| `staging/combat/savegame.cpp` (2) | `SaveGameManager::LastSaveWriteSucceeded`<br>`SaveGameManager::Load_Definitions(char const*, bool)` |
| `staging/combat/teampurchasesettings.cpp` (1) | `TeamPurchaseSettingsDefClass::On_Load_Rejected()` |
| `staging/commando/DlgMPConnect.cpp` (7) | `DlgMPConnect::Connected(cGameData*)`<br>`DlgMPConnect::DlgMPConnect(int, unsigned long)`<br>`DlgMPConnect::DoDialog(int, unsigned long)`<br>`DlgMPConnect::Failed_To_Connect()`<br>`DlgMPConnect::On_Command(int, int, unsigned long)`<br>`DlgMPConnect::On_Periodic()`<br>`DlgMPConnect::~DlgMPConnect()` |
| `staging/commando/DlgMPConnectionRefused.cpp` (5) | `DlgMPConnectionRefused::DlgMPConnectionRefused(wchar_t const*, bool)`<br>`DlgMPConnectionRefused::DoDialog(wchar_t const*, bool)`<br>`DlgMPConnectionRefused::On_Command(int, int, unsigned long)`<br>`DlgMPConnectionRefused::On_Init_Dialog()`<br>`DlgMPConnectionRefused::~DlgMPConnectionRefused()` |
| `staging/commando/DlgMPTeamSelect.cpp` (15) | `DlgMPTeamSelect::AddLANPlayerInfo(cPlayer*)`<br>`DlgMPTeamSelect::DlgMPTeamSelect()`<br>`DlgMPTeamSelect::DoDialog(Signaler<TypedEventPair<bool, int> >&)`<br>`DlgMPTeamSelect::FinalizeCreate()`<br>`DlgMPTeamSelect::GetSideChoice()`<br>`DlgMPTeamSelect::HandleNotification(TypedActionPtr<PLAYERMGR_ACTION, cPlayer>&)`<br>`DlgMPTeamSelect::InitSideChoice(int)`<br>`DlgMPTeamSelect::On_Command(int, int, unsigned long)`<br>`DlgMPTeamSelect::On_Frame_Update()`<br>`DlgMPTeamSelect::On_Init_Dialog()`<br>`DlgMPTeamSelect::On_Last_Menu_Ending()`<br>`DlgMPTeamSelect::PopulateWithLANPlayers()`<br>`DlgMPTeamSelect::RemoveLANPlayerInfo(cPlayer*)`<br>`DlgMPTeamSelect::SelectSideChoice(int)`<br>`DlgMPTeamSelect::~DlgMPTeamSelect()` |
| `staging/commando/DlgPasswordPrompt.cpp` (8) | `DlgPasswordPrompt::DlgPasswordPrompt()`<br>`DlgPasswordPrompt::DoDialog(Signaler<DlgPasswordPrompt>*)`<br>`DlgPasswordPrompt::GetPassword() const`<br>`DlgPasswordPrompt::On_Command(int, int, unsigned long)`<br>`DlgPasswordPrompt::On_EditCtrl_Change(EditCtrlClass*, int)`<br>`DlgPasswordPrompt::On_EditCtrl_Enter_Pressed(EditCtrlClass*, int)`<br>`DlgPasswordPrompt::On_Init_Dialog()`<br>`DlgPasswordPrompt::~DlgPasswordPrompt()` |
| `staging/commando/campaign.cpp` (3) | `CampaignManager::Current_Level_Matches_Archive(char const*)`<br>`CampaignManager::Is_Catalog_Ready()`<br>`CampaignManager::Loaded_Save_State_Matches_Archive(char const*)` |
| `staging/commando/combatgmode.cpp` (10) | `CombatGameModeClass::Core_Restart(bool (*)(void*), void*)`<br>`CombatGameModeClass::Process_Autosave_Request()`<br>`CombatGameModeClass::Process_Chat_Input()`<br>`CombatGameModeClass::Process_Core_Restart_Request(bool (*)(void*), void*)`<br>`CombatGameModeClass::Process_Multiplayer_Info_Input()`<br>`CombatGameModeClass::Process_Overlay_Update()`<br>`CombatGameModeClass::Process_Player_List_Input()`<br>`CombatGameModeClass::Process_Radio_Command_Input()`<br>`CombatGameModeClass::Render_Overlays()`<br>`CombatGameModeClass::Vita_Abort_Level_Load()` |
| `staging/commando/dialogtests.cpp` (4) | `DeathOptionsPopupClass::On_Command(int, int, unsigned long)`<br>`DeathOptionsPopupClass::On_Init_Dialog()`<br>`FailedOptionsPopupClass::On_Command(int, int, unsigned long)`<br>`FailedOptionsPopupClass::On_Init_Dialog()` |
| `staging/commando/dlgcncbattleinfo.cpp` (8) | `CNCBattleInfoDialogClass::Build_Player_Display_Name(cPlayer const*, WideStringClass&)`<br>`CNCBattleInfoDialogClass::CNCBattleInfoDialogClass()`<br>`CNCBattleInfoDialogClass::Configure_Icons()`<br>`CNCBattleInfoDialogClass::ListSortCallback(ListCtrlClass*, int, int, unsigned int)`<br>`CNCBattleInfoDialogClass::On_Frame_Update()`<br>`CNCBattleInfoDialogClass::On_Init_Dialog()`<br>`CNCBattleInfoDialogClass::Populate_Player_List(ListCtrlClass*, int)`<br>`CNCBattleInfoDialogClass::~CNCBattleInfoDialogClass()` |
| `staging/commando/dlgcncreference.cpp` (14) | `CnCReferenceMenuClass::CnCReferenceMenuClass()`<br>`CnCReferenceMenuClass::Display()`<br>`CnCReferenceMenuClass::Exit_Game()`<br>`CnCReferenceMenuClass::HandleNotification(DlgMsgBoxEvent&)`<br>`CnCReferenceMenuClass::LastChangeTeamTimeMs`<br>`CnCReferenceMenuClass::LastSuicideTimeMs`<br>`CnCReferenceMenuClass::On_Command(int, int, unsigned long)`<br>`CnCReferenceMenuClass::On_Destroy()`<br>`CnCReferenceMenuClass::On_Frame_Update()`<br>`CnCReferenceMenuClass::On_Init_Dialog()`<br>`CnCReferenceMenuClass::On_Menu_Activate(bool)`<br>`CnCReferenceMenuClass::Prompt_User()`<br>`CnCReferenceMenuClass::_TheInstance`<br>`CnCReferenceMenuClass::~CnCReferenceMenuClass()` |
| `staging/commando/dlgcncserverinfo.cpp` (4) | `CNCServerInfoDialogClass::CNCServerInfoDialogClass()`<br>`CNCServerInfoDialogClass::On_Frame_Update()`<br>`CNCServerInfoDialogClass::On_Init_Dialog()`<br>`CNCServerInfoDialogClass::~CNCServerInfoDialogClass()` |
| `staging/commando/dlgcncteaminfo.cpp` (8) | `CNCTeamInfoDialogClass::Build_Player_Display_Name(cPlayer const*, WideStringClass&)`<br>`CNCTeamInfoDialogClass::CNCTeamInfoDialogClass()`<br>`CNCTeamInfoDialogClass::Configure_Icons()`<br>`CNCTeamInfoDialogClass::ListSortCallback(ListCtrlClass*, int, int, unsigned int)`<br>`CNCTeamInfoDialogClass::On_Frame_Update()`<br>`CNCTeamInfoDialogClass::On_Init_Dialog()`<br>`CNCTeamInfoDialogClass::Populate_Player_List()`<br>`CNCTeamInfoDialogClass::~CNCTeamInfoDialogClass()` |
| `staging/commando/dlgcncwinscreen.cpp` (14) | `CNCWinScreenMenuClass::Build_Player_Display_Name(cPlayer const*, WideStringClass&)`<br>`CNCWinScreenMenuClass::CNCWinScreenMenuClass()`<br>`CNCWinScreenMenuClass::Close_Dialog()`<br>`CNCWinScreenMenuClass::ListSortCallback(void const*, void const*)`<br>`CNCWinScreenMenuClass::On_Command(int, int, unsigned long)`<br>`CNCWinScreenMenuClass::On_Destroy()`<br>`CNCWinScreenMenuClass::On_Frame_Update()`<br>`CNCWinScreenMenuClass::On_Init_Dialog()`<br>`CNCWinScreenMenuClass::On_Menu_Activate(bool)`<br>`CNCWinScreenMenuClass::Populate_Player_Lists(int, int)`<br>`CNCWinScreenMenuClass::Render()`<br>`CNCWinScreenMenuClass::UpdateIntervalS`<br>`CNCWinScreenMenuClass::_TheInstance`<br>`CNCWinScreenMenuClass::~CNCWinScreenMenuClass()` |
| `staging/commando/dlgcontrols.cpp` (7) | `ControlsMenuClass::Apply_Changes()`<br>`ControlsMenuClass::ControlsMenuClass()`<br>`ControlsMenuClass::On_Command(int, int, unsigned long)`<br>`ControlsMenuClass::On_Init_Dialog()`<br>`ControlsMenuClass::Reload()`<br>`ControlsMenuClass::_TheInstance`<br>`ControlsMenuClass::~ControlsMenuClass()` |
| `staging/commando/dlgcontrolsaveload.cpp` (12) | `ControlSaveLoadMenuClass::ControlSaveLoadMenuClass()`<br>`ControlSaveLoadMenuClass::Delete_Config()`<br>`ControlSaveLoadMenuClass::HandleNotification(DlgMsgBoxEvent&)`<br>`ControlSaveLoadMenuClass::Insert_Configuration(InputConfigClass const&)`<br>`ControlSaveLoadMenuClass::ListSortCallback(ListCtrlClass*, int, int, unsigned int)`<br>`ControlSaveLoadMenuClass::Load_Config()`<br>`ControlSaveLoadMenuClass::On_Command(int, int, unsigned long)`<br>`ControlSaveLoadMenuClass::On_EditCtrl_Enter_Pressed(EditCtrlClass*, int)`<br>`ControlSaveLoadMenuClass::On_Init_Dialog()`<br>`ControlSaveLoadMenuClass::On_ListCtrl_Delete_Entry(ListCtrlClass*, int, int)`<br>`ControlSaveLoadMenuClass::On_ListCtrl_Sel_Change(ListCtrlClass*, int, int, int)`<br>`ControlSaveLoadMenuClass::Save_Config(bool)` |
| `staging/commando/dlgcontrolslisttab.cpp` (12) | `ControlsListTabClass::Add_Function(int, int, int)`<br>`ControlsListTabClass::Clear_Key(int, bool)`<br>`ControlsListTabClass::ControlsListTabClass(int)`<br>`ControlsListTabClass::Find_Function_By_Key(int, int)`<br>`ControlsListTabClass::Get_Function_Name(int)`<br>`ControlsListTabClass::HandleNotification(DlgMsgBoxEvent&)`<br>`ControlsListTabClass::Load_Key_Mappings()`<br>`ControlsListTabClass::On_Init_Dialog()`<br>`ControlsListTabClass::On_InputCtrl_Get_Key_Info(InputCtrlClass*, int, int, WideStringClass&, int*)`<br>`ControlsListTabClass::On_Reload()`<br>`ControlsListTabClass::Prompt_User()`<br>`ControlsListTabClass::Remap_Key(int, int, int)` |
| `staging/commando/dlgcontroltabs.cpp` (13) | `ControlsAttackTabClass::ControlsAttackTabClass()`<br>`ControlsAttackTabClass::Load_Controls()`<br>`ControlsAttackTabClass::On_Apply()`<br>`ControlsAttackTabClass::On_Init_Dialog()`<br>`ControlsAttackTabClass::On_Reload()`<br>`ControlsBasicMvmtTabClass::ControlsBasicMvmtTabClass()`<br>`ControlsLookTabClass::ControlsLookTabClass()`<br>`ControlsLookTabClass::Load_Controls()`<br>`ControlsLookTabClass::On_Apply()`<br>`ControlsLookTabClass::On_Init_Dialog()`<br>`ControlsLookTabClass::On_Reload()`<br>`ControlsMultiPlayTabClass::ControlsMultiPlayTabClass()`<br>`ControlsWeaponsTabClass::ControlsWeaponsTabClass()` |
| `staging/commando/dlgcredits.cpp` (3) | `CreditsMenuClass::CreditsMenuClass()`<br>`CreditsMenuClass::On_Command(int, int, unsigned long)`<br>`CreditsMenuClass::On_Init_Dialog()` |
| `staging/commando/dlgmovieoptions.cpp` (12) | `MovieOptionsMenuClass::Begin_Play_Movie()`<br>`MovieOptionsMenuClass::HandleNotification(CDVerifyEvent&)`<br>`MovieOptionsMenuClass::MovieOptionsMenuClass()`<br>`MovieOptionsMenuClass::On_Command(int, int, unsigned long)`<br>`MovieOptionsMenuClass::On_Frame_Update()`<br>`MovieOptionsMenuClass::On_Init_Dialog()`<br>`MovieOptionsMenuClass::On_Key_Down(unsigned int, unsigned int)`<br>`MovieOptionsMenuClass::On_ListCtrl_DblClk(ListCtrlClass*, int, int)`<br>`MovieOptionsMenuClass::On_ListCtrl_Delete_Entry(ListCtrlClass*, int, int)`<br>`MovieOptionsMenuClass::Play_Movie(char const*)`<br>`MovieOptionsMenuClass::Render()`<br>`MovieOptionsMenuClass::~MovieOptionsMenuClass()` |
| `staging/commando/dlgmpchangelannickname.cpp` (8) | `DlgMpChangeLanNickname::DialogCount`<br>`DlgMpChangeLanNickname::DlgMpChangeLanNickname()`<br>`DlgMpChangeLanNickname::DoDialog()`<br>`DlgMpChangeLanNickname::On_Command(int, int, unsigned long)`<br>`DlgMpChangeLanNickname::On_EditCtrl_Change(EditCtrlClass*, int)`<br>`DlgMpChangeLanNickname::On_EditCtrl_Enter_Pressed(EditCtrlClass*, int)`<br>`DlgMpChangeLanNickname::On_Init_Dialog()`<br>`DlgMpChangeLanNickname::~DlgMpChangeLanNickname()` |
| `staging/commando/dlgmplangamelist.cpp` (18) | `MPLanGameListMenuClass::Connect_To_Server()`<br>`MPLanGameListMenuClass::Display()`<br>`MPLanGameListMenuClass::Join_Game()`<br>`MPLanGameListMenuClass::MPLanGameListMenuClass()`<br>`MPLanGameListMenuClass::On_Command(int, int, unsigned long)`<br>`MPLanGameListMenuClass::On_Destroy()`<br>`MPLanGameListMenuClass::On_EditCtrl_Change(EditCtrlClass*, int)`<br>`MPLanGameListMenuClass::On_Frame_Update()`<br>`MPLanGameListMenuClass::On_Init_Dialog()`<br>`MPLanGameListMenuClass::On_Key_Down(unsigned int, unsigned int)`<br>`MPLanGameListMenuClass::On_Last_Menu_Ending()`<br>`MPLanGameListMenuClass::On_ListCtrl_DblClk(ListCtrlClass*, int, int)`<br>`MPLanGameListMenuClass::On_ListCtrl_Delete_Entry(ListCtrlClass*, int, int)`<br>`MPLanGameListMenuClass::ReceiveSignal(DlgPasswordPrompt&)`<br>`MPLanGameListMenuClass::UpdateNickname`<br>`MPLanGameListMenuClass::Update_Game_List()`<br>`MPLanGameListMenuClass::_TheInstance`<br>`MPLanGameListMenuClass::~MPLanGameListMenuClass()` |
| `staging/commando/dlgmplanhostoptions.cpp` (46) | `List_Contains(DynamicVectorClass<WideStringClass>&, WideStringClass&)`<br>`MPLanHostAdvancedOptionsTabClass::ConfigureWOLControls()`<br>`MPLanHostAdvancedOptionsTabClass::HandleNotification(DlgMsgBoxEvent&)`<br>`MPLanHostAdvancedOptionsTabClass::IsHostAClanMember() const`<br>`MPLanHostAdvancedOptionsTabClass::MPLanHostAdvancedOptionsTabClass()`<br>`MPLanHostAdvancedOptionsTabClass::On_Apply()`<br>`MPLanHostAdvancedOptionsTabClass::On_Command(int, int, unsigned long)`<br>`MPLanHostAdvancedOptionsTabClass::On_Init_Dialog()`<br>`MPLanHostAdvancedOptionsTabClass::ReceiveSignal(bool&)`<br>`MPLanHostBasicOptionsTabClass::BandTestMaxPlayers`<br>`MPLanHostBasicOptionsTabClass::Get_Instance()`<br>`MPLanHostBasicOptionsTabClass::InitSideChoiceCombo(int)`<br>`MPLanHostBasicOptionsTabClass::MPLanHostBasicOptionsTabClass()`<br>`MPLanHostBasicOptionsTabClass::On_Apply()`<br>`MPLanHostBasicOptionsTabClass::On_EditCtrl_Change(EditCtrlClass*, int)`<br>`MPLanHostBasicOptionsTabClass::On_Init_Dialog()`<br>`MPLanHostBasicOptionsTabClass::_mInstance`<br>`MPLanHostBasicOptionsTabClass::~MPLanHostBasicOptionsTabClass()`<br>`MPLanHostCnCOptionsTabClass::On_Apply()`<br>`MPLanHostCnCOptionsTabClass::On_Init_Dialog()`<br>`MPLanHostMapCycleOptionsTabClass::Add_Map()`<br>`MPLanHostMapCycleOptionsTabClass::Build_Map_List()`<br>`MPLanHostMapCycleOptionsTabClass::Build_Map_List(ModPackageClass const*)`<br>`MPLanHostMapCycleOptionsTabClass::Build_Mod_Package_List()`<br>`MPLanHostMapCycleOptionsTabClass::Enable_Mod_Selection(bool)`<br>`MPLanHostMapCycleOptionsTabClass::Fill_Map_Ctrls()`<br>`MPLanHostMapCycleOptionsTabClass::MPLanHostMapCycleOptionsTabClass()`<br>`MPLanHostMapCycleOptionsTabClass::On_Apply()`<br>`MPLanHostMapCycleOptionsTabClass::On_ComboBoxCtrl_Sel_Change(ComboBoxCtrlClass*, int, int, int)`<br>`MPLanHostMapCycleOptionsTabClass::On_Command(int, int, unsigned long)`<br>`MPLanHostMapCycleOptionsTabClass::On_Init_Dialog()`<br>`MPLanHostMapCycleOptionsTabClass::On_ListCtrl_DblClk(ListCtrlClass*, int, int)`<br>`MPLanHostMapCycleOptionsTabClass::Populate_Map_List_Ctrl()`<br>`MPLanHostMapCycleOptionsTabClass::Remove_Map()`<br>`MPLanHostOptionsMenuClass::Enable_Mod_Selection(bool)`<br>`MPLanHostOptionsMenuClass::MPLanHostOptionsMenuClass()`<br>`MPLanHostOptionsMenuClass::On_Command(int, int, unsigned long)`<br>`MPLanHostOptionsMenuClass::On_Init_Dialog()`<br>`MPLanHostOptionsMenuClass::On_Periodic()`<br>`MPLanHostOptionsMenuClass::Start_Game(cGameData*)`<br>`MPLanHostOptionsMenuClass::~MPLanHostOptionsMenuClass()`<br>`MPLanHostVictoryOptionsTabClass::MPLanHostVictoryOptionsTabClass()`<br>`MPLanHostVictoryOptionsTabClass::On_Apply()`<br>`MPLanHostVictoryOptionsTabClass::On_Command(int, int, unsigned long)`<br>`MPLanHostVictoryOptionsTabClass::On_Init_Dialog()`<br>`MPLanHostVictoryOptionsTabClass::Update_Enable_State()` |
| `staging/commando/dlgserversaveload.cpp` (26) | `DEFAULT_SERVER_SETTINGS_FILE_NAME`<br>`ServerSaveLoadMenuClass::Delete_Config()`<br>`ServerSaveLoadMenuClass::FromSlaveConfig`<br>`ServerSaveLoadMenuClass::HandleNotification(DlgMsgBoxEvent&)`<br>`ServerSaveLoadMenuClass::Insert_Configuration(ServerSettingsClass*)`<br>`ServerSaveLoadMenuClass::ListSortCallback(ListCtrlClass*, int, int, unsigned int)`<br>`ServerSaveLoadMenuClass::Load_Config()`<br>`ServerSaveLoadMenuClass::Next_Dialog()`<br>`ServerSaveLoadMenuClass::On_Command(int, int, unsigned long)`<br>`ServerSaveLoadMenuClass::On_EditCtrl_Enter_Pressed(EditCtrlClass*, int)`<br>`ServerSaveLoadMenuClass::On_Init_Dialog()`<br>`ServerSaveLoadMenuClass::On_ListCtrl_Delete_Entry(ListCtrlClass*, int, int)`<br>`ServerSaveLoadMenuClass::On_ListCtrl_Sel_Change(ListCtrlClass*, int, int, int)`<br>`ServerSaveLoadMenuClass::Save_Config(bool)`<br>`ServerSaveLoadMenuClass::Save_Now()`<br>`ServerSaveLoadMenuClass::ServerSaveLoadMenuClass()`<br>`ServerSettingsClass::ServerSettingsClass(ServerSettingsClass*)`<br>`ServerSettingsClass::ServerSettingsClass(char*, wchar_t*, int)`<br>`ServerSettingsManagerClass::Add_Configuration(WideStringClass*)`<br>`ServerSettingsManagerClass::Clear_Settings_List()`<br>`ServerSettingsManagerClass::Delete_Configuration(ServerSettingsClass*)`<br>`ServerSettingsManagerClass::Get_Settings(int)`<br>`ServerSettingsManagerClass::Load_Settings(ServerSettingsClass*)`<br>`ServerSettingsManagerClass::Save_Configuration(ServerSettingsClass*)`<br>`ServerSettingsManagerClass::Scan()`<br>`ServerSettingsManagerClass::ServerSettingsList` |
| `staging/commando/gamechanlist.cpp` (5) | `cGameChannelList::Add_Channel(cGameData*)`<br>`cGameChannelList::ChanList`<br>`cGameChannelList::Find_Channel(WideStringClass const&)`<br>`cGameChannelList::Remove_All()`<br>`cGameChannelList::Remove_Channel(WideStringClass const&)` |
| `staging/commando/gamechannel.cpp` (2) | `cGameChannel::cGameChannel(cGameData*)`<br>`cGameChannel::~cGameChannel()` |
| `staging/commando/god.cpp` (3) | `cGod::Can_Save_Current_State()`<br>`cGod::Has_Pending_Restart()`<br>`cGod::Request_Restart()` |
| `staging/commando/inputconfig.cpp` (4) | `InputConfigClass::Load(ChunkLoadClass&)`<br>`InputConfigClass::Load_Variables(ChunkLoadClass&)`<br>`InputConfigClass::Save(ChunkSaveClass&)`<br>`InputConfigClass::operator=(InputConfigClass const&)` |
| `staging/commando/inputconfigmgr.cpp` (23) | `InputConfigMgrClass::Add_Configuration(wchar_t const*)`<br>`InputConfigMgrClass::ConfigList`<br>`InputConfigMgrClass::CurrentConfigIndex`<br>`InputConfigMgrClass::Current_Configuration_Is_Custom()`<br>`InputConfigMgrClass::Delete_Configuration(char const*)`<br>`InputConfigMgrClass::Delete_Configuration(int)`<br>`InputConfigMgrClass::Find_Configuration(char const*)`<br>`InputConfigMgrClass::Get_Config_Path(StringClass&)`<br>`InputConfigMgrClass::Get_Current_Configuration(InputConfigClass&)`<br>`InputConfigMgrClass::Get_Unique_Config_Filename(StringClass&)`<br>`InputConfigMgrClass::Initialize()`<br>`InputConfigMgrClass::Load()`<br>`InputConfigMgrClass::Load_Config_List(ChunkLoadClass&)`<br>`InputConfigMgrClass::Load_Configuration(InputConfigClass const&)`<br>`InputConfigMgrClass::Load_Current_Configuration()`<br>`InputConfigMgrClass::Load_Default_Configuration()`<br>`InputConfigMgrClass::Load_Variables(ChunkLoadClass&)`<br>`InputConfigMgrClass::Save()`<br>`InputConfigMgrClass::Save_Config_List(ChunkSaveClass&)`<br>`InputConfigMgrClass::Save_Configuration(InputConfigClass const&)`<br>`InputConfigMgrClass::Save_Current_Configuration()`<br>`InputConfigMgrClass::Save_Variables(ChunkSaveClass&)`<br>`InputConfigMgrClass::Shutdown()` |
| `staging/commando/lanchat.cpp` (14) | `cLanChat::Accept_Actions()`<br>`cLanChat::Go_To_Location(ChatLocationEnum)`<br>`cLanChat::Init_Lan_Protocol_And_Socket()`<br>`cLanChat::LAN_BROADCAST_INTERVAL_MS`<br>`cLanChat::LAN_PORT`<br>`cLanChat::Lan_Packet_Handler(cPacket&)`<br>`cLanChat::Load_Lan_Registry_Keys()`<br>`cLanChat::Process_Position_Broadcast(cPacket&)`<br>`cLanChat::Refusal_Actions()`<br>`cLanChat::Save_Lan_Registry_Keys()`<br>`cLanChat::Send_Position_Broadcast()`<br>`cLanChat::Think()`<br>`cLanChat::cLanChat()`<br>`cLanChat::~cLanChat()` |
| `staging/commando/langmode.cpp` (5) | `LanGameModeClass::Get_Lan_Interface()`<br>`LanGameModeClass::Init()`<br>`LanGameModeClass::PLanChat`<br>`LanGameModeClass::Shutdown()`<br>`LanGameModeClass::Think()` |
| `staging/commando/movie.cpp` (1) | `MovieGameModeClass::Stop_Current_Movie()` |
| `staging/commando/nicenum.cpp` (6) | `cNicEnum::Enumerate_Nics(unsigned long*, unsigned long)`<br>`cNicEnum::GSNicList`<br>`cNicEnum::Init()`<br>`cNicEnum::NicList`<br>`cNicEnum::NumGSNics`<br>`cNicEnum::NumNics` |
| `staging/commando/radiocommanddisplay.cpp` (9) | `RadioCommandDisplayClass::Check_Keys()`<br>`RadioCommandDisplayClass::Display(bool, RadioCommandDisplayClass::DISPLAY_TYPE)`<br>`RadioCommandDisplayClass::DisplayTimer`<br>`RadioCommandDisplayClass::Initialize()`<br>`RadioCommandDisplayClass::IsDisplayed`<br>`RadioCommandDisplayClass::Render()`<br>`RadioCommandDisplayClass::Shutdown()`<br>`RadioCommandDisplayClass::TextWindow`<br>`RadioCommandDisplayClass::Update(RadioCommandDisplayClass::DISPLAY_TYPE)` |
| `staging/commando/scorescreen.cpp` (2) | `ScoreScreenDialogClass::ForcedTeardown`<br>`ScoreScreenDialogClass::Set_Forced_Teardown(bool)` |
| `staging/commando/suicideevent.cpp` (6) | `cSuicideEvent::Act()`<br>`cSuicideEvent::Export_Creation(BitStreamClass&)`<br>`cSuicideEvent::Import_Creation(BitStreamClass&)`<br>`cSuicideEvent::Init()`<br>`cSuicideEvent::cSuicideEvent()`<br>`cSuicideEventFactory` |
| `staging/ww3d2/meshmdl.cpp` (1) | `MeshModelClass::Vita_Invalidate_Static_Cache()` |
| `staging/wwsaveload/saveload.cpp` (7) | `SaveLoadSystemClass::Discard_Post_Load_Callbacks()`<br>`SaveLoadSystemClass::Has_Reported_Load_Failure()`<br>`SaveLoadSystemClass::Load(ChunkLoadClass&, bool, bool)`<br>`SaveLoadSystemClass::RejectedLoadList`<br>`SaveLoadSystemClass::Report_Load_Failure()`<br>`SaveLoadSystemClass::ReportedLoadFailure`<br>`SaveLoadSystemClass::Retain_Rejected_Object_Until_Next_Load(PersistClass*)` |
