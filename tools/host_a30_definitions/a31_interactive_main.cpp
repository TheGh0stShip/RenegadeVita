// Host proof for the A3.1 original interactive path.  This intentionally
// enters the original Combat manager's scene, level, control and think
// ordering; the only local implementation is the offline transport contract
// required below CombatManager's existing network-handler seam.

#include "renegade_file_factory.h"
#include "a31_interactive_runtime_policy.h"
#include "a4_frontend_lifecycle_boundary.h"

#include "assetmgr.h"
#include "campaign.h"
#include "combat.h"
#include "cnetwork.h"
#include "definitionfactorymgr.h"
#include "definitionmgr.h"
#include "definition.h"
#include "directinput.h"
#include "dinput.h"
#include "networkobjectmgr.h"
#include "ffactory.h"
#include "ffactorylist.h"
#include "font3d.h"
#include "gamedata.h"
#include "gameinitmgr.h"
#include "gamemode.h"
#include "gdsingleplayer.h"
#include "gametype.h"
#include "god.h"
#include "hud.h"
#include "input.h"
#include "mixfile.h"
#include "netinterface.h"
#include "pathmgr.h"
#include "playermanager.h"
#include "radar.h"
#include "renegadedialogmgr.h"
#include "renegadecheatmgr.h"
#include "rendobj.h"
#include "render2dsentence.h"
#include "serverfps.h"
#include "singlepl.h"
#include "stylemgr.h"
#include "teammanager.h"
#include "timemgr.h"
#include "ww3d.h"
#include "ww3d_vita_renderer.h"
#include "wwaudio.h"
#include "wwfile.h"
#include "wwmath.h"
#include "wwphys.h"
#include "saveload.h"
#include "wwsaveload.h"

#include "a31_console_stub.h"
#include "dialogmgr.h"
#include "dialogtests.h"
#include "dialogresource.h"
#include "dlgmainmenu.h"
#include "gamemenu.h"
#include "movie.h"

#include <stdio.h>
#include <string.h>
#include <vector>

// The original source uses this deliberate linker anchor to retain the
// Soldier definition/persist factories when the game is linked from static
// source pools.  It is not a replacement definition or a custom player.
extern void _Force_Link_Soldier(void);

/* This is the original campaign.cpp-owned retail flow table.  The narrow host
 * contract observes it only to prove that CampaignManager consumed
 * campaign.ini through the original FileFactory/MIX route; it does not invent
 * a campaign sequence or bypass GameInitMgrClass::Start_Game. */
extern DynamicVectorClass<StringClass> CampaignFlowDescriptions;

namespace {

const char *const kAlways2Archive = "Data\\Always2.dat";
const char *const kAlwaysDbsArchive = "Data\\always.dbs";
const char *const kAlwaysArchive = "Data\\Always.dat";
const char *const kM00Archive = "Data\\M00_Tutorial.mix";

// The direct M00 host harness owns the original CombatManager lifecycle below
// GameModeManager. This inert registry entry preserves cGameData's existing
// query contract without pretending to be the Vita frontend implementation.
class A4HostHarnessCombatMode final : public GameModeClass {
public:
	const char *Name(void) override { return "Combat"; }
	void Init(void) override {}
	void Shutdown(void) override {}
	void Render(void) override {}
	void Think(void) override {}
};

A4HostHarnessCombatMode g_a4_host_harness_combat_mode;
bool g_a4_host_harness_combat_registered = false;

void Register_A4_Host_Harness_Combat_Mode()
{
	if (!g_a4_host_harness_combat_registered &&
		GameModeManager::Find("Combat") == NULL) {
		GameModeManager::Add(&g_a4_host_harness_combat_mode);
		g_a4_host_harness_combat_registered = true;
	}
}

void Print(const char *name, bool value)
{
	printf("a31.%s=%s\n", name, value ? "true" : "false");
	fflush(stdout);
}

unsigned Count_Definitions(uint32 class_id)
{
	unsigned count = 0;
	for (DefinitionClass *definition = DefinitionMgrClass::Get_First();
		definition != NULL;
		definition = DefinitionMgrClass::Get_Next(definition)) {
		if (class_id == 0 || definition->Get_Class_ID() == class_id) {
			++count;
		}
	}
	return count;
}

	void Print_Number(const char *name, unsigned value)
	{
		printf("a31.%s=%u\n", name, value);
		fflush(stdout);
	}

	void Print_Text(const char *name, const char *value)
	{
		printf("a31.%s=%s\n", name, value != NULL ? value : "");
		fflush(stdout);
	}

void Stage(const char *name)
{
	fprintf(stderr, "a31.stage=%s\n", name);
	fflush(stderr);
}

bool Client_Connection_Present(const char *stage)
{
	const bool present = cNetwork::PClientConnection != NULL;
	fprintf(stderr, "a31.network_client_connection.%s=%s\n", stage,
		present ? "present" : "missing");
	fflush(stderr);
	return present;
}

bool Validate_Frontend_Render_Object(WW3DAssetManager *asset_manager,
	const char *name)
{
	if (asset_manager == NULL || name == NULL) return false;
	RenderObjClass *object = asset_manager->Create_Render_Obj(name);
	const bool available = object != NULL;
	REF_PTR_RELEASE(object);
	return available;
}

bool Validate_Frontend_Font_File(FileFactoryClass &factory, const char *name,
	unsigned *byte_count)
{
	if (byte_count != NULL) *byte_count = 0;
	FileClass *file = factory.Get_File(name);
	if (file == NULL || !file->Is_Available()) {
		if (file != NULL) factory.Return_File(file);
		return false;
	}
	const int size = file->Size();
	unsigned char signature[4] = {};
	const bool opened = file->Open(FileClass::READ) != 0;
	const int read = opened ? file->Read(signature, sizeof(signature)) : 0;
	if (opened) file->Close();
	factory.Return_File(file);
	if (byte_count != NULL && size > 0) *byte_count = static_cast<unsigned>(size);
	/* TrueType/OpenType containers accepted by FreeType.  This proves the real
	** retail font is reachable through Renegade's factory/MIX path, without
	** treating a generic blob as a usable frontend font. */
	const bool recognized =
		(signature[0] == 0x00 && signature[1] == 0x01 &&
		 signature[2] == 0x00 && signature[3] == 0x00) ||
		(signature[0] == 'O' && signature[1] == 'T' &&
		 signature[2] == 'T' && signature[3] == 'O') ||
		(signature[0] == 't' && signature[1] == 'r' &&
		 signature[2] == 'u' && signature[3] == 'e');
	return size > 4 && read == static_cast<int>(sizeof(signature)) && recognized;
}

bool Validate_Frontend_Font_Glyph(WW3DAssetManager *asset_manager,
	const char *family, WCHAR glyph, unsigned *width_out, unsigned *height_out,
	unsigned *covered_pixels_out)
{
	if (width_out != NULL) *width_out = 0;
	if (height_out != NULL) *height_out = 0;
	if (covered_pixels_out != NULL) *covered_pixels_out = 0;
	if (asset_manager == NULL) return false;
	FontCharsClass *font = asset_manager->Get_FontChars(family, 12, false);
	if (font == NULL) return false;
	const int width = font->Get_Char_Width(glyph);
	const int height = font->Get_Char_Height();
	bool valid = width > 0 && height > 0 && width <= 128 && height <= 128;
	unsigned covered_pixels = 0;
	if (valid) {
		std::vector<uint16> pixels(static_cast<size_t>(width) * static_cast<size_t>(height));
		font->Blit_Char(glyph, pixels.data(), width * static_cast<int>(sizeof(uint16)), 0, 0);
		for (uint16 pixel : pixels) {
			if ((pixel & 0xF000U) != 0) ++covered_pixels;
		}
		valid = covered_pixels != 0;
	}
	REF_PTR_RELEASE(font);
	if (width_out != NULL && width > 0) *width_out = static_cast<unsigned>(width);
	if (height_out != NULL && height > 0) *height_out = static_cast<unsigned>(height);
	if (covered_pixels_out != NULL) *covered_pixels_out = covered_pixels;
	return valid;
}

/*
** Exercise the actual single-player frontend owner before the direct M00
** development route begins.  The Vita console boundary intentionally has no
** desktop console window, but it must not suppress the original WWUI setup:
** RenegadeDialogMgrClass owns StyleMgr, MenuDialog, input installation, and
** the dialog resource route.  This deliberately uses Goto_Location rather
** than a locally constructed presenter, and restores the former console
** state before gameplay setup continues.
*/
	bool Validate_Authentic_Main_Menu_Lifecycle(unsigned *control_count_out,
		unsigned *render_frames_out, bool *mode_lifecycle_out)
{
	if (control_count_out != NULL) *control_count_out = 0;
	if (render_frames_out != NULL) *render_frames_out = 0;
	if (mode_lifecycle_out != NULL) *mode_lifecycle_out = false;

	ConsoleBox.Set_Exclusive(false);
	RenegadeDialogMgrClass::Initialize();
	/* The original menu owner is deliberately registered for this bounded
	 * lifecycle rather than represented by a headless mode.  Combat is already
	 * registered as the direct M00 route's query owner, so MenuGameMode's
	 * GameInitMgr check preserves original single-player semantics. */
	MenuGameModeClass2 menu_mode;
	GameModeManager::Add(&menu_mode);
	/* Goto_Location owns MainMenuDialog construction and, in the released
	 * frontend, activates the already-registered Menu mode.  Keep that exact
	 * ordering here: direct Activate would conceal a missing manager owner. */
	RenegadeDialogMgrClass::Goto_Location(RenegadeDialogMgrClass::LOC_MAIN_MENU);

	MainMenuDialogClass *const menu = MainMenuDialogClass::Get_Instance();
	const unsigned controls = menu != NULL && menu->Get_Control_Count() > 0
		? static_cast<unsigned>(menu->Get_Control_Count()) : 0U;
	const unsigned initial_dialog_count =
		static_cast<unsigned>(DialogMgrClass::Get_Dialog_Count());
	unsigned rendered_frames = 0;
	for (unsigned frame = 0; menu != NULL && frame < 3U; ++frame) {
		GameModeManager::Think();
		DialogMgrClass::On_Frame_Update();
		DialogMgrClass::Render();
		++rendered_frames;
	}

	const bool mode_active = menu_mode.Is_Active() &&
		GameModeManager::Find("Menu") == &menu_mode;
	menu_mode.Deactivate();
	GameModeManager::Safely_Deactivate();
	const bool mode_shutdown = menu_mode.Is_Inactive();
	GameModeManager::Remove(&menu_mode);
	const bool valid = menu != NULL && controls > 0U &&
		initial_dialog_count > 0U && rendered_frames == 3U &&
		mode_active && mode_shutdown;
	RenegadeDialogMgrClass::Shutdown();
	ConsoleBox.Set_Exclusive(true);

	if (control_count_out != NULL) *control_count_out = controls;
	if (render_frames_out != NULL) *render_frames_out = rendered_frames;
		if (mode_lifecycle_out != NULL) *mode_lifecycle_out =
			mode_active && mode_shutdown;
		return valid;
	}

	bool Validate_Frontend_Controller_Navigation(unsigned *control_count_out)
	{
		if (control_count_out != NULL) *control_count_out = 0;
		ConsoleBox.Set_Exclusive(false);
		RenegadeDialogMgrClass::Initialize();
		MenuGameModeClass2 menu_mode;
		GameModeManager::Add(&menu_mode);
		RenegadeDialogMgrClass::Goto_Location(RenegadeDialogMgrClass::LOC_MAIN_MENU);

		MainMenuDialogClass *const menu = MainMenuDialogClass::Get_Instance();
		DialogControlClass *const initial_focus = DialogMgrClass::Get_Focus();
		if (control_count_out != NULL && menu != NULL) {
			*control_count_out = static_cast<unsigned>(menu->Get_Control_Count());
		}

		A4_Frontend_Reset_Trace();
		A4_Frontend_Begin_Menu_Loop();
		A4_Frontend_Set_Test_WWUI_Key_State(VK_DOWN, true);
		A4_Frontend_Pump_WWUI_Key_Transitions();
		DialogControlClass *const after_down_focus = DialogMgrClass::Get_Focus();
		A4_Frontend_Set_Test_WWUI_Key_State(VK_DOWN, false);
		A4_Frontend_Pump_WWUI_Key_Transitions();
		A4_Frontend_Set_Test_WWUI_Key_State(VK_UP, true);
		A4_Frontend_Pump_WWUI_Key_Transitions();
		DialogControlClass *const after_up_focus = DialogMgrClass::Get_Focus();
		A4_Frontend_Set_Test_WWUI_Key_State(VK_UP, false);
		A4_Frontend_Pump_WWUI_Key_Transitions();
		A4_Frontend_End_Menu_Loop();

		menu_mode.Deactivate();
		GameModeManager::Safely_Deactivate();
		GameModeManager::Remove(&menu_mode);
		RenegadeDialogMgrClass::Shutdown();
		ConsoleBox.Set_Exclusive(true);

		return menu != NULL && initial_focus != NULL &&
			after_down_focus != NULL && after_down_focus != initial_focus &&
			after_up_focus == initial_focus;
	}

	bool Validate_Frontend_Movie_Provider_Route(unsigned *play_requests_out,
		unsigned *skip_requests_out, char *last_movie_out, unsigned last_movie_size)
	{
		if (play_requests_out != NULL) *play_requests_out = 0;
		if (skip_requests_out != NULL) *skip_requests_out = 0;
		if (last_movie_out != NULL && last_movie_size != 0U) last_movie_out[0] = '\0';

		ConsoleBox.Set_Exclusive(false);
		A4_Frontend_Reset_Trace();
		A4_Frontend_Begin_Menu_Loop();
		RenegadeDialogMgrClass::Initialize();
		MenuGameModeClass2 menu_mode;
		MovieGameModeClass movie_mode;
		GameModeManager::Add(&menu_mode);
		GameModeManager::Add(&movie_mode);
		movie_mode.Activate();
		movie_mode.Startup_Movies();

		for (unsigned frame = 0; frame < 4U; ++frame) {
			GameModeManager::Think();
			DialogMgrClass::On_Frame_Update();
		}
		const A4FrontendTrace trace = A4_Frontend_Get_Trace();
		if (play_requests_out != NULL) *play_requests_out = trace.movie_play_requests;
		if (skip_requests_out != NULL) *skip_requests_out = trace.movie_skip_requests;
		if (last_movie_out != NULL && last_movie_size != 0U) {
			::strncpy(last_movie_out, trace.last_movie, last_movie_size - 1U);
			last_movie_out[last_movie_size - 1U] = '\0';
		}

		const bool valid = trace.movie_play_requests >= 2U &&
			trace.movie_skip_requests >= 2U &&
			::strstr(trace.last_movie, "R_INTRO.BIK") != NULL &&
			MainMenuDialogClass::Get_Instance() != NULL &&
			DialogMgrClass::Get_Dialog_Count() > 0;

		menu_mode.Deactivate();
		movie_mode.Deactivate();
		GameModeManager::Safely_Deactivate();
		GameModeManager::Remove(&movie_mode);
		GameModeManager::Remove(&menu_mode);
		RenegadeDialogMgrClass::Shutdown();
		A4_Frontend_End_Menu_Loop();
		ConsoleBox.Set_Exclusive(true);
		return valid;
	}

	bool Validate_Frontend_Tutorial_Start_Latch(char *map_out, unsigned map_size)
	{
		if (map_out != NULL && map_size != 0U) map_out[0] = '\0';
		ConsoleBox.Set_Exclusive(false);
		A4_Frontend_Reset_Trace();
		A4_Frontend_Begin_Menu_Loop();
		RenegadeDialogMgrClass::Initialize();
		MenuGameModeClass2 menu_mode;
		GameModeManager::Add(&menu_mode);

		StartSPGameDialogClass *dialog = new StartSPGameDialogClass;
		dialog->Start_Dialog();
		dialog->On_Command(IDC_MENU_START_TUTORIAL_BUTTON, BN_CLICKED, 0);
		REF_PTR_RELEASE(dialog);

		const A4FrontendTrace trace = A4_Frontend_Get_Trace();
		if (map_out != NULL && map_size != 0U) {
			::strncpy(map_out, trace.tutorial_map, map_size - 1U);
			map_out[map_size - 1U] = '\0';
		}
		const bool valid = trace.tutorial_start_latched &&
			::strcmp(trace.tutorial_map, "M00_Tutorial.mix") == 0 &&
			trace.tutorial_team_choice == -1 &&
			GameModeManager::Find("Combat") != NULL;

		menu_mode.Deactivate();
		GameModeManager::Safely_Deactivate();
		GameModeManager::Remove(&menu_mode);
		RenegadeDialogMgrClass::Shutdown();
		GameInitMgrClass::Shutdown();
		A4_Frontend_End_Menu_Loop();
		ConsoleBox.Set_Exclusive(true);
		return valid;
	}


	} // namespace

int main(int argc, char **argv)
{
	static unsigned interactive_cycle = 0;
	const unsigned cycle = ++interactive_cycle;
	if (argc != 5 && argc != 6) {
		fprintf(stderr, "usage: %s RETAIL_ROOT USER_ROOT CACHE_ROOT MODS_ROOT [LEVEL_MIX]\n", argv[0]);
		return 2;
	}
	const char *const level_mix = argc == 6 ? argv[5] : "M00_Tutorial.mix";
	char level_archive[96] = {};
	char level_ldd_name[96] = {};
	snprintf(level_archive, sizeof(level_archive), "Data\\%s", level_mix);
	snprintf(level_ldd_name, sizeof(level_ldd_name), "%s", level_mix);
	char *extension = strrchr(level_ldd_name, '.');
	if (extension == NULL) { fprintf(stderr, "invalid level archive name: %s\n", level_mix); return 2; }
	snprintf(extension, sizeof(level_ldd_name) - static_cast<size_t>(extension - level_ldd_name), ".ldd");
	Print_Number("hardware_equivalent_cycle", cycle);

	const RenegadePathRoots roots = { argv[1], argv[2], argv[3], argv[4] };
	RenegadeRootedFileFactoryClass root_factory(roots);
	MixFileFactoryClass always2_factory(kAlways2Archive, &root_factory);
	MixFileFactoryClass always_dbs_factory(kAlwaysDbsArchive, &root_factory);
	MixFileFactoryClass always_factory(kAlwaysArchive, &root_factory);
	MixFileFactoryClass m00_factory(level_archive, &root_factory);
	FileFactoryListClass factory_list;
	factory_list.Add_FileFactory(&root_factory, "");
	factory_list.Add_FileFactory(&always2_factory, "Always2.dat");
	factory_list.Add_FileFactory(&always_dbs_factory, "Always.dbs");
	factory_list.Add_FileFactory(&always_factory, "Always.dat");
	factory_list.Add_FileFactory(&m00_factory, level_mix);

	FileFactoryClass *previous_read_factory = _TheFileFactory;
	FileFactoryClass *previous_write_factory = _TheWritingFileFactory;
	_TheFileFactory = &factory_list;
	_TheWritingFileFactory = &root_factory;

	bool passed = always2_factory.Is_Valid() && always_dbs_factory.Is_Valid() &&
		always_factory.Is_Valid() && m00_factory.Is_Valid();
	bool math_initialized = false;
	bool path_manager_initialized = false;
	bool ww3d_initialized = false;
	bool wwphys_initialized = false;
	bool wwsaveload_initialized = false;
	bool input_initialized = false;
	bool combat_initialized = false;
	bool radar_initialized = false;
	bool stylemgr_initialized = false;
	bool campaign_initialized = false;
	bool session_initialized = false;
	bool single_player_transport_initialized = false;
	bool level_loaded = false;
	WW3DAssetManager *asset_manager = NULL;
	{
		Stage("audio_construct");
		WWAudioClass audio(true);
		// The original campaign loader persists its own cheat history.  Keep the
		// original manager alive for that serialized lifecycle.
		RenegadeCheatMgrClass cheat_manager;
		do {
			if (!passed) break;
			Stage("wwmath_init");
			WWMath::Init();
			math_initialized = true;
			/* Match original Commando lifecycle: the global solver pool begins
			 * after WWMath and must be released after the asset manager rather
			 * than surviving a load/play/exit harness cycle. */
			PathMgrClass::Initialize();
			path_manager_initialized = true;
			asset_manager = new WW3DAssetManager;
			asset_manager->Set_WW3D_Load_On_Demand(true);
			asset_manager->Set_Activate_Fog_On_Load(true);
			Stage("ww3d_init");
			ww3d_initialized = WW3D::Init(NULL, NULL, true) == WW3D_ERROR_OK;
			if (!ww3d_initialized) { passed = false; break; }
			Stage("wwphys_init");
			WWPhys::Init();
			wwphys_initialized = true;
			WWSaveLoad::Init();
			wwsaveload_initialized = true;

			Stage("input_init");
			Input::Init(true);
			A31_Interactive_Configure_Vita_Controls();
			const bool vita_control_bindings =
				Input::Get_Primary_Key_For_Function(INPUT_FUNCTION_MOVE_FORWARD) == Input::SLIDER_JOYSTICK_UP &&
				Input::Get_Primary_Key_For_Function(INPUT_FUNCTION_MOVE_BACKWARD) == Input::SLIDER_JOYSTICK_DOWN &&
				Input::Get_Primary_Key_For_Function(INPUT_FUNCTION_MOVE_LEFT) == Input::SLIDER_JOYSTICK_LEFT &&
				Input::Get_Primary_Key_For_Function(INPUT_FUNCTION_MOVE_RIGHT) == Input::SLIDER_JOYSTICK_RIGHT &&
					Input::Get_Secondary_Key_For_Function(INPUT_FUNCTION_MOVE_FORWARD) == 0 &&
					Input::Get_Secondary_Key_For_Function(INPUT_FUNCTION_MOVE_BACKWARD) == 0 &&
					Input::Get_Secondary_Key_For_Function(INPUT_FUNCTION_MOVE_LEFT) == 0 &&
					Input::Get_Secondary_Key_For_Function(INPUT_FUNCTION_MOVE_RIGHT) == 0 &&
					Input::Get_Primary_Key_For_Function(INPUT_FUNCTION_WEAPON_LEFT) == Input::SLIDER_MOUSE_LEFT &&
					Input::Get_Primary_Key_For_Function(INPUT_FUNCTION_WEAPON_RIGHT) == Input::SLIDER_MOUSE_RIGHT &&
					Input::Get_Primary_Key_For_Function(INPUT_FUNCTION_WEAPON_UP) == Input::SLIDER_MOUSE_UP &&
					Input::Get_Primary_Key_For_Function(INPUT_FUNCTION_WEAPON_DOWN) == Input::SLIDER_MOUSE_DOWN &&
					Input::Get_Secondary_Key_For_Function(INPUT_FUNCTION_WEAPON_LEFT) == 0 &&
					Input::Get_Secondary_Key_For_Function(INPUT_FUNCTION_WEAPON_RIGHT) == 0 &&
					Input::Get_Secondary_Key_For_Function(INPUT_FUNCTION_WEAPON_UP) == 0 &&
					Input::Get_Secondary_Key_For_Function(INPUT_FUNCTION_WEAPON_DOWN) == 0 &&
					Input::Get_Primary_Key_For_Function(INPUT_FUNCTION_TURN_LEFT) == 0 &&
					Input::Get_Secondary_Key_For_Function(INPUT_FUNCTION_TURN_LEFT) == 0 &&
					Input::Get_Primary_Key_For_Function(INPUT_FUNCTION_TURN_RIGHT) == 0 &&
					Input::Get_Secondary_Key_For_Function(INPUT_FUNCTION_TURN_RIGHT) == 0 &&
					Input::Get_Primary_Key_For_Function(INPUT_FUNCTION_VEHICLE_TURN_LEFT) == 0 &&
					Input::Get_Secondary_Key_For_Function(INPUT_FUNCTION_VEHICLE_TURN_LEFT) == 0 &&
					Input::Get_Primary_Key_For_Function(INPUT_FUNCTION_VEHICLE_TURN_RIGHT) == 0 &&
					Input::Get_Secondary_Key_For_Function(INPUT_FUNCTION_VEHICLE_TURN_RIGHT) == 0 &&
					Input::Get_Primary_Key_For_Function(INPUT_FUNCTION_ACTION) == DIK_E &&
					Input::Get_Secondary_Key_For_Function(INPUT_FUNCTION_ACTION) == 0 &&
					Input::Get_Primary_Key_For_Function(INPUT_FUNCTION_RELOAD_WEAPON) == DIK_R &&
					Input::Get_Secondary_Key_For_Function(INPUT_FUNCTION_RELOAD_WEAPON) == 0 &&
					Input::Get_Primary_Key_For_Function(INPUT_FUNCTION_FIRST_PERSON_TOGGLE) == DIK_F &&
					Input::Get_Secondary_Key_For_Function(INPUT_FUNCTION_FIRST_PERSON_TOGGLE) == 0 &&
					Input::Get_Primary_Key_For_Function(INPUT_FUNCTION_PREV_WEAPON) == DIK_LEFT &&
					Input::Get_Secondary_Key_For_Function(INPUT_FUNCTION_PREV_WEAPON) == 0 &&
					Input::Get_Primary_Key_For_Function(INPUT_FUNCTION_NEXT_WEAPON) == DIK_RIGHT &&
					Input::Get_Secondary_Key_For_Function(INPUT_FUNCTION_NEXT_WEAPON) == 0 &&
					Input::Get_Primary_Key_For_Function(INPUT_FUNCTION_ZOOM_IN) == DIK_UP &&
					Input::Get_Secondary_Key_For_Function(INPUT_FUNCTION_ZOOM_IN) == 0 &&
					Input::Get_Primary_Key_For_Function(INPUT_FUNCTION_ZOOM_OUT) == DIK_DOWN &&
					Input::Get_Secondary_Key_For_Function(INPUT_FUNCTION_ZOOM_OUT) == 0 &&
					Input::Get_Primary_Key_For_Function(
						INPUT_FUNCTION_EVA_MISSION_OBJECTIVES_TOGGLE) == 0 &&
						Input::Get_Secondary_Key_For_Function(
							INPUT_FUNCTION_EVA_MISSION_OBJECTIVES_TOGGLE) == 0 &&
						Input::Get_Primary_Key_For_Function(INPUT_FUNCTION_USE_WEAPON) == DIK_E &&
						Input::Get_Secondary_Key_For_Function(INPUT_FUNCTION_USE_WEAPON) == 0;
			Print("vita_controls_use_original_action_sliders", vita_control_bindings);
			if (!vita_control_bindings) { passed = false; break; }
			input_initialized = true;
			Stage("campaign_catalog_init");
			CampaignManager::Init();
			campaign_initialized = CampaignFlowDescriptions.Count() > 0;
			Print_Number("campaign_flow_entries",
				static_cast<unsigned>(CampaignFlowDescriptions.Count()));
			Print("campaign_catalog_loaded", campaign_initialized);
			if (!campaign_initialized) { passed = false; break; }
			Stage("frontend_mainmenu_lifecycle");
			Register_A4_Host_Harness_Combat_Mode();
			unsigned main_menu_control_count = 0;
			unsigned main_menu_render_frames = 0;
			bool original_menu_mode_lifecycle = false;
			const bool authentic_main_menu_lifecycle =
				Validate_Authentic_Main_Menu_Lifecycle(&main_menu_control_count,
					&main_menu_render_frames, &original_menu_mode_lifecycle);
				Print("frontend_dialog_manager_initialized", authentic_main_menu_lifecycle);
				Print("frontend_original_menu_mode_lifecycle", original_menu_mode_lifecycle);
				Print_Number("frontend_mainmenu_original_controls", main_menu_control_count);
				Print_Number("frontend_mainmenu_original_render_frames", main_menu_render_frames);
				if (!authentic_main_menu_lifecycle) { passed = false; break; }
				Stage("frontend_controller_navigation");
				unsigned frontend_navigation_controls = 0;
				const bool frontend_controller_navigation =
					Validate_Frontend_Controller_Navigation(&frontend_navigation_controls);
				Print("frontend_controller_navigation_mapping", frontend_controller_navigation);
				Print_Number("frontend_controller_navigation_controls",
					frontend_navigation_controls);
				if (!frontend_controller_navigation) { passed = false; break; }
				Stage("frontend_movie_provider_route");
				unsigned frontend_movie_play_requests = 0;
				unsigned frontend_movie_skip_requests = 0;
				char frontend_last_movie[160] = {};
				const bool frontend_movie_route = Validate_Frontend_Movie_Provider_Route(
					&frontend_movie_play_requests, &frontend_movie_skip_requests,
					frontend_last_movie, sizeof(frontend_last_movie));
				Print("frontend_movie_provider_fail_closed", frontend_movie_route);
				Print_Number("frontend_movie_play_requests",
					frontend_movie_play_requests);
				Print_Number("frontend_movie_skip_requests",
					frontend_movie_skip_requests);
				Print_Text("frontend_movie_last_request", frontend_last_movie);
				if (!frontend_movie_route) { passed = false; break; }
				Stage("frontend_tutorial_start_latch");
				char frontend_tutorial_map[96] = {};
				const bool frontend_tutorial_latch =
					Validate_Frontend_Tutorial_Start_Latch(frontend_tutorial_map,
						sizeof(frontend_tutorial_map));
				Print("frontend_tutorial_start_latched", frontend_tutorial_latch);
				Print_Text("frontend_tutorial_latched_map", frontend_tutorial_map);
				if (!frontend_tutorial_latch) { passed = false; break; }
				Stage("gamedata_create");
			// The original local session owns both WWNet endpoints.  Rendering/UI
			// one-time setup remains under the existing Vita presentation path.
			cServerFps::Create_Instance();
			Stage("gameinit_sp");
			/* Preserve the original single-player session owner rather than
			 * reproducing its cSinglePlayerData/nickname/game-data setup in the
			 * direct M00 development harness.  The level-loader remains below this
			 * boundary until the full desktop mode graph is portable. */
			GameInitMgrClass::Initialize_SP();
			single_player_transport_initialized = cSinglePlayerData::Is_Single_Player();
			Print("original_gameinit_sp_initialized",
				single_player_transport_initialized && PTheGameData != NULL &&
				cGameType::Get_Game_Type() == GAMETYPE_MISSION);
			if (!single_player_transport_initialized || PTheGameData == NULL) {
				passed = false;
				break;
			}
			if (PTheGameData == NULL) { passed = false; break; }
			GameModeClass *combat_mode = GameModeManager::Find("Combat");
			if (combat_mode == NULL) { passed = false; break; }
			combat_mode->Activate();
			StringClass map_name(level_mix, true);
			The_Game()->Set_Map_Name(map_name);
			_Force_Link_Soldier();
			// Own the local authoritative session through the original cNetwork
			// lifecycle.  This follows GameInitMgrClass::Start_Client_Server:
			// server first, then client, then service the original single-player
			// in-memory packet queues until the client has its negotiated ID.
			// Never manufacture connection pointers or player IDs for gameplay.
			Stage("network_onetime_init");
			cNetwork::Onetime_Init();
			Stage("network_server_init");
			cNetwork::Init_Server();
			Stage("network_client_init");
			cNetwork::Init_Client();
			if (!Client_Connection_Present("after_init")) { passed = false; break; }
			session_initialized = true;
			Stage("combat_scene_init");
			CombatManager::Scene_Init();
			if (!Client_Connection_Present("after_scene_init")) { passed = false; break; }
			/* Exercise the original Font3D asset route before Combat owns the HUD:
			 * FileFactory -> Targa -> CPU SurfaceClass -> TextureClass -> Vita edge. */
			Stage("font3d_render_capability");
			Font3DInstanceClass *large_font = asset_manager->Get_Font3DInstance("FONT12x16.TGA");
			Font3DInstanceClass *small_font = asset_manager->Get_Font3DInstance("FONT6x8.TGA");
			Print("font3d_large_available", large_font != NULL);
			Print("font3d_small_available", small_font != NULL);
			if (large_font == NULL || small_font == NULL) { passed = false; break; }
			REF_PTR_RELEASE(large_font);
			REF_PTR_RELEASE(small_font);
			/* These are the original main-menu backdrop/logo/gizmo render-object
			 * names owned by MenuGameModeClass2/MainMenuDialogClass.  Probe the
			 * actual retail factory path without substituting a menu presenter. */
			Stage("frontend_asset_probe");
			const bool menu_backdrop_available =
				Validate_Frontend_Render_Object(asset_manager, "IF_BACK01");
			const bool menu_logo_available =
				Validate_Frontend_Render_Object(asset_manager, "IF_RENLOGO");
			const bool menu_gizmo_available =
				Validate_Frontend_Render_Object(asset_manager, "IF_EVAGIZMO");
			Print("frontend_menu_backdrop_available", menu_backdrop_available);
			Print("frontend_menu_logo_available", menu_logo_available);
			Print("frontend_menu_gizmo_available", menu_gizmo_available);
			unsigned regatta_font_bytes = 0;
			unsigned arial_font_bytes = 0;
			const bool regatta_font_available = Validate_Frontend_Font_File(
				factory_list, "54251___.TTF", &regatta_font_bytes);
			const bool arial_font_available = Validate_Frontend_Font_File(
				factory_list, "ARI_____.TTF", &arial_font_bytes);
			Print("frontend_regatta_font_available", regatta_font_available);
			Print("frontend_arial_font_available", arial_font_available);
			Print_Number("frontend_regatta_font_bytes", regatta_font_bytes);
			Print_Number("frontend_arial_font_bytes", arial_font_bytes);
			unsigned regatta_glyph_width = 0;
			unsigned regatta_glyph_height = 0;
			unsigned regatta_glyph_coverage = 0;
			unsigned arial_glyph_width = 0;
			unsigned arial_glyph_height = 0;
			unsigned arial_glyph_coverage = 0;
			const bool regatta_glyph_rasterized = Validate_Frontend_Font_Glyph(
				asset_manager, "Regatta Condensed LET", static_cast<WCHAR>('R'),
				&regatta_glyph_width, &regatta_glyph_height, &regatta_glyph_coverage);
			const bool arial_glyph_rasterized = Validate_Frontend_Font_Glyph(
				asset_manager, "Arial MT", static_cast<WCHAR>('A'),
				&arial_glyph_width, &arial_glyph_height, &arial_glyph_coverage);
			Print("frontend_regatta_glyph_rasterized", regatta_glyph_rasterized);
			Print("frontend_arial_glyph_rasterized", arial_glyph_rasterized);
			Print_Number("frontend_regatta_glyph_width", regatta_glyph_width);
			Print_Number("frontend_regatta_glyph_height", regatta_glyph_height);
			Print_Number("frontend_regatta_glyph_covered_pixels", regatta_glyph_coverage);
			Print_Number("frontend_arial_glyph_width", arial_glyph_width);
			Print_Number("frontend_arial_glyph_height", arial_glyph_height);
			Print_Number("frontend_arial_glyph_covered_pixels", arial_glyph_coverage);
			if (!menu_backdrop_available || !menu_logo_available ||
				!menu_gizmo_available || !regatta_font_available || !arial_font_available ||
				!regatta_glyph_rasterized || !arial_glyph_rasterized) { passed = false; break; }
			Stage("frontend_stylemgr_init");
			StyleMgrClass::Initialize_From_INI("stylemgr.ini");
			stylemgr_initialized = true;
			FontCharsClass *menu_font = StyleMgrClass::Get_Font(StyleMgrClass::FONT_MENU);
			FontCharsClass *ingame_font = StyleMgrClass::Get_Font(StyleMgrClass::FONT_INGAME_TXT);
			const bool stylemgr_font_contract = menu_font != NULL && ingame_font != NULL;
			Print("frontend_stylemgr_initialized", stylemgr_font_contract);
			REF_PTR_RELEASE(menu_font);
			REF_PTR_RELEASE(ingame_font);
			if (!stylemgr_font_contract) { passed = false; break; }
			Stage("combat_init_shared_hud_policy");
			CombatManager::Init(A31_Interactive_Render_HUD_Available());
			combat_initialized = true;
			if (!Client_Connection_Present("after_combat_init")) { passed = false; break; }
			Stage("network_handshake");
			for (unsigned update_count = 0; update_count < 120; ++update_count) {
				if (!Client_Connection_Present("before_update")) { passed = false; break; }
				if (cNetwork::PClientConnection->Is_Established()) break;
				cNetwork::Update();
				if (!Client_Connection_Present("after_update")) { passed = false; break; }
			}
			const bool transport_established = cNetwork::PClientConnection != NULL &&
				cNetwork::PClientConnection->Is_Established();
			Print("original_singleplayer_transport_established", transport_established);
			if (!transport_established) {
				passed = false;
				break;
			}
			FileClass *objects_ddb = factory_list.Get_File("Objects.DDB");
			Print("objects_ddb_visible_before_load",
				objects_ddb != NULL && objects_ddb->Is_Available());
			if (objects_ddb != NULL) {
				factory_list.Return_File(objects_ddb);
			}
			FileClass *level_ldd = factory_list.Get_File(level_ldd_name);
			Print("level_ldd_visible_before_load",
				level_ldd != NULL && level_ldd->Is_Available());
			if (level_ldd != NULL) {
				factory_list.Return_File(level_ldd);
			}
			Stage("combat_preload");
			CombatManager::Pre_Load_Level(false);
			NetworkObjectMgrClass::Set_Is_Level_Loading(true);
			Stage("combat_load");
			CombatManager::Load_Level_Threaded(level_mix, false);
			while (!CombatManager::Is_Load_Level_Complete()) {}
			Stage("post_load_processing");
			SaveLoadSystemClass::Post_Load_Processing(NULL);
			NetworkObjectMgrClass::Set_Is_Level_Loading(false);
			Stage("combat_postload");
			CombatManager::Post_Load_Level();
			level_loaded = CombatManager::Get_Scene() != NULL;
			A31_Interactive_Apply_Render_Capabilities();
			/* CombatGameModeClass owns radar creation after the original level
			 * post-load sequence.  This direct M00 development route retains that
			 * ownership ordering whenever the real render HUD is enabled; without
			 * it HUDClass::Think legitimately has no RadarManager renderer. */
			if (A31_Interactive_Render_HUD_Available()) {
				Stage("combat_mode_radar_init");
				RadarManager::Init();
				RadarManager::Set_Radar_Mode(The_Game()->Get_Radar_Mode());
				radar_initialized = true;
			}
			const A31InteractiveHUDState post_load_hud =
				A31_Interactive_Get_HUD_State();
			Print("postload_hud_serialized_enabled", post_load_hud.serialized_enabled);
			Print("postload_hud_resources_available", post_load_hud.render_resources_available);
			Print("postload_hud_effectively_displayable", post_load_hud.effectively_displayable);
			Print("soldier_definition_factory_registered",
				DefinitionFactoryMgrClass::Find_Factory("Soldier") != NULL);
			Print_Number("definitions_total", Count_Definitions(0));
			Print_Number("soldier_definitions_loaded",
				Count_Definitions(CLASSID_GAME_OBJECT_DEF_SOLDIER));
			Print("commando_definition_loaded",
				DefinitionMgrClass::Find_Typed_Definition("Commando", CLASSID_GAME_OBJECTS) != NULL);
			WideStringClass local_player_name;
			local_player_name.Convert_From("Renegade");
			Stage("player_create");
			cPlayer *local_player = cGod::Create_Player(cNetwork::Get_My_Id(),
				local_player_name, -1, 0);
			Print("original_session_player_created", local_player != NULL);
			Print("original_session_player_registered", cPlayerManager::Count() == 1);
			Stage("god_think");
			cGod::Think();
			Print("original_god_created_commando", CombatManager::Get_The_Star() != NULL);

			Stage("hardware_equivalent_120_frame_loop");
			/* Make each cycle's first-frame geometry a per-cycle measurement,
			** matching the Vita adapter's reset immediately before its loop. */
			RenegadeVitaRenderer::Reset_Statistics();
			unsigned complete_frames = 0;
			bool first_frame_geometry = false;
			for (; complete_frames < 120U; ++complete_frames) {
				WW3D::Sync((complete_frames + 1U) * 16U);
				A31_Interactive_Run_Simulation_Frame();
				const A31InteractiveRenderTrace render_trace =
					A31_Interactive_Run_Render_Frame();
				if (complete_frames == 0U) {
					Print("interactive_scene_available", render_trace.scene_available);
					Print("interactive_camera_available", render_trace.camera_available);
					Print("interactive_star_available", render_trace.star_available);
					Print("interactive_pre_render_completed", render_trace.pre_render_completed);
					Print("interactive_combat_render_called", render_trace.combat_render_called);
					Print("interactive_post_render_completed", render_trace.post_render_completed);
					Print_Number("interactive_first_frame_meshes",
						static_cast<unsigned>(render_trace.mesh_submissions));
					Print_Number("interactive_first_frame_vertices",
						static_cast<unsigned>(render_trace.vertex_submissions));
					Print_Number("interactive_first_frame_triangles",
						static_cast<unsigned>(render_trace.triangle_submissions));
					Print_Number("interactive_first_frame_rejected",
						static_cast<unsigned>(render_trace.rejected_submissions));
					Print_Number("interactive_first_frame_unsupported",
						static_cast<unsigned>(render_trace.unsupported_submissions));
					Print_Number("interactive_static_objects",
						render_trace.static_object_count);
					Print_Number("interactive_dynamic_objects",
						render_trace.dynamic_object_count);
					Print_Number("interactive_static_lights",
						render_trace.static_light_count);
					Print_Number("interactive_visibility_table_size",
						render_trace.visibility_table_size);
					Print_Number("interactive_visibility_table_count",
						render_trace.visibility_table_count);
					first_frame_geometry = render_trace.mesh_submissions > 0U &&
						render_trace.vertex_submissions > 0U &&
						render_trace.triangle_submissions > 0U &&
						render_trace.rejected_submissions == 0U &&
						render_trace.unsupported_submissions == 0U;
				}
				if (!render_trace.end_render_completed ||
					!render_trace.post_render_completed) {
					Print("hardware_equivalent_render_frame", false);
					passed = false;
					break;
				}
			}
			Print_Number("hardware_equivalent_complete_frames", complete_frames);
			Print("hardware_equivalent_render_frame", complete_frames == 120U);
			Print("interactive_first_frame_geometry", first_frame_geometry);
			passed = passed && complete_frames == 120U && first_frame_geometry &&
				CombatManager::Get_Scene() != NULL &&
				CombatManager::Get_Camera() != NULL &&
				CombatManager::Get_The_Star() != NULL;
		} while (false);

		Print("factory_chain_ready", always2_factory.Is_Valid() &&
			always_dbs_factory.Is_Valid() && always_factory.Is_Valid() &&
			m00_factory.Is_Valid());
		Print("combat_scene_owned", CombatManager::Get_Scene() != NULL);
		Print("original_camera_owned", CombatManager::Get_Camera() != NULL);
		Print("original_star_restored", CombatManager::Get_The_Star() != NULL);
		Print("one_original_control_think_frame", passed);

			Stage("teardown");
			/* Preserve the original Core_Shutdown dependency order for the direct
			 * M00 route: stop player respawn, free level-owned objects/assets, then
			 * release radar before Combat's process-level state. */
			if (level_loaded) {
				cGod::Exit();
				CombatManager::Unload_Level();
				level_loaded = false;
			}
			if (radar_initialized) RadarManager::Shutdown();
			if (session_initialized) {
				/* This is the original GameInitMgrClass shutdown order.  In
				 * particular, the client-goodbye event must be registered before
				 * NetworkObjectMgr drains pending objects, and server-owned teams
				 * must leave before the next in-process campaign cycle. */
				cNetwork::Flush();
				cNetwork::Cleanup_Client();
				cNetwork::Cleanup_Server();
				cPlayerManager::Remove_All();
				cTeamManager::Remove_All();
				NetworkObjectMgrClass::Set_All_Delete_Pending();
				NetworkObjectMgrClass::Delete_Pending();
				cGod::Reset();
			}
			if (combat_initialized) CombatManager::Shutdown();
			if (stylemgr_initialized) StyleMgrClass::Shutdown();
			if (campaign_initialized) {
				CampaignManager::Shutdown();
				Print("campaign_catalog_shutdown",
					CampaignFlowDescriptions.Count() == 0);
			}
		if (session_initialized) {
			/* GameInitMgr owns the matching SP data/transport shutdown.  Network
			 * one-time shutdown remains at the outer application lifecycle, as in
			 * the original shutdown ordering. */
			GameInitMgrClass::Shutdown();
			cNetwork::Onetime_Shutdown();
		}
		if (session_initialized) cServerFps::Destroy_Instance();
		if (input_initialized) Input::Shutdown();
	}

	if (asset_manager != NULL) WW3DAssetManager::Delete_This();
	if (path_manager_initialized) PathMgrClass::Shutdown();
	if (math_initialized) WWMath::Shutdown();
	if (wwsaveload_initialized) WWSaveLoad::Shutdown();
	if (ww3d_initialized) WW3D::Shutdown();
	if (wwphys_initialized) WWPhys::Shutdown();
	_TheFileFactory = previous_read_factory;
	_TheWritingFileFactory = previous_write_factory;

	if (passed && cycle < 2U) {
		Stage("start_equivalent_exit_and_second_cycle");
		return main(argc, argv);
	}
	printf("A3.1 original %s interactive runtime: %s (two in-process cycles)\n",
		level_mix, passed && cycle == 2U ? "PASS" : "FAIL");
	return passed && cycle == 2U ? 0 : 1;
}
