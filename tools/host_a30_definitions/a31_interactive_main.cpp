// Host proof for the A3.1 original interactive path.  This intentionally
// enters the original Combat manager's scene, level, control and think
// ordering; the only local implementation is the offline transport contract
// required below CombatManager's existing network-handler seam.

#include "renegade_file_factory.h"
#if defined(RENEGADE_A35_ORIGINAL_WWAUDIO)
#include "assets.h"
#include "renegade_miles_test.h"
#include "renegade_miles_runtime_stats.h"
#include "audio_release_probe.h"
#endif
#include "renegade_find_files.h"
#include "renegade_mission_ranks.h"
#include "renegade_vita_options.h"
#include "a31_interactive_runtime_policy.h"
#include "a4_frontend_lifecycle_boundary.h"

#include "assetmgr.h"
#include "_globals.h"
#include "campaign.h"
#include "scorescreen.h"
#include "encyclopediamgr.h"
#include "chunkio.h"
#include "combat.h"
#include "combatgmode.h"
#include "conversationmgr.h"
#include "pscene.h"
#include "cnetwork.h"
#include "definitionfactorymgr.h"
#include "definitionmgr.h"
#include "definition.h"
#include "damage.h"
#include "damageablegameobj.h"
#include "physicalgameobj.h"
#include "humanphys.h"
#include "soldier.h"
#include "explosion.h"
#include "directinput.h"
#include "hud_bitmap_atlas_probe.h"
#include "m13_runtime_inventory.h"
#include "mission_rank_probe.h"
#include "wwnet_packet_probe.h"
#include "local_session_probe.h"
#include "ttfs_factory_probe.h"
#include "direct_client_probe.h"
#include "tt_soldier_probe.h"
#include "tt_vehicle_probe.h"
#include <memory>
#include <atomic>
#include "purchase_probe.h"
#include "tt_purchase_probe.h"
#include "tt_c4_probe.h"
#include "state_machine_probe.h"
#include "m13_cinematic_probe.h"
#if defined(RENEGADE_ORIGINAL_SORTING) && defined(RENEGADE_HOST_ABI_TEST)
#include "sorting_renderer_probe.h"
#endif
#include "dinput.h"
#include "networkobjectmgr.h"
#include "ffactory.h"
#include "ffactorylist.h"
#include "font3d.h"
#include "gamedata.h"
#include "gameinitmgr.h"
#include "gameobjmanager.h"
#include "gamemode.h"
#include "gdsingleplayer.h"
#include "gdskirmish.h"
#include "hanim.h"
#include "gametype.h"
#include "god.h"
#include "hud.h"
#include "input.h"
#include "mixfile.h"
#include "mapmgr.h"
#include "texture.h"
#include "netinterface.h"
#include "pathmgr.h"
#include "Path.h"
#include "playermanager.h"
#include "radar.h"
#include "renegadedialogmgr.h"
#include "renegadecheatmgr.h"
#include "rendobj.h"
#include "render2dsentence.h"
#include "serverfps.h"
#include "singlepl.h"
#include "scriptablegameobj.h"
#include "stylemgr.h"
#include "teammanager.h"
#include "timemgr.h"
#include "timeddecophys.h"
#include "twiddler.h"
#include "ww3d.h"
#include "ww3d_vita_renderer.h"
#include "wwaudio.h"
#include "wwfile.h"
#include "wwmath.h"
#include "wwphys.h"
#include "saveload.h"
#include "translatedb.h"
#include "wwsaveload.h"

#include "a31_console_stub.h"
#include "dialogmgr.h"
#include "dialogcontrol.h"
#include "dialogtests.h"
#include "dialogresource.h"
#include "dlgmainmenu.h"
#include "dlgtechoptions.h"
#include "dlgmessagebox.h"
#include "dlgconfigaudiotab.h"
#include "dlgconfigperformancetab.h"
#include "childdialog.h"
#include "sliderctrl.h"
#include "listctrl.h"
#include "tabctrl.h"
#include "gamemenu.h"
#include "movie.h"

#include <stdio.h>
#include <stdarg.h>
#include <chrono>
#if __has_include(<valgrind/callgrind.h>)
#include <valgrind/callgrind.h>
#else
#define CALLGRIND_START_INSTRUMENTATION ((void)0)
#define CALLGRIND_STOP_INSTRUMENTATION ((void)0)
#define CALLGRIND_ZERO_STATS ((void)0)
#define CALLGRIND_DUMP_STATS_AT(label) ((void)0)
#endif
#include <stdlib.h>
#include <string.h>
#include <vector>
#include "movephys.h"

static unsigned HostReplayFrameMilliseconds = 16U;
#if defined(RENEGADE_A35_ORIGINAL_WWAUDIO)
// Same basename adapter as the native Commando/WWAudio boundary.
class HostAudioFileFactory final : public SimpleFileFactoryClass {
public:
	explicit HostAudioFileFactory(FileFactoryClass *base) : Base(base) {}
	FileClass *Get_File(const char *name) override {
		if (name == NULL || Base == NULL) return NULL;
		StringClass stripped(true);
		Strip_Path_From_Filename(stripped, name);
		return Base->Get_File(stripped);
	}
private:
	FileFactoryClass *Base;
};
#endif
#ifndef __vita__
static bool HostFixedSimulationClock = false;
#if defined(RENEGADE_A35_ORIGINAL_WWAUDIO)
static std::atomic<uint32_t> HostAudioClockMilliseconds{1U};
extern "C" int Renegade_Host_Audio_Clock(DWORD *milliseconds)
{
	if (!HostFixedSimulationClock) return 0;
	*milliseconds = HostAudioClockMilliseconds.load(std::memory_order_relaxed);
	return 1;
}
#endif
extern "C" float __real__ZN4WW3D28Get_Movie_Capture_Frame_RateEv();
extern "C" float __wrap__ZN4WW3D28Get_Movie_Capture_Frame_RateEv()
{
	return HostFixedSimulationClock ? 1000.0F / HostReplayFrameMilliseconds :
		__real__ZN4WW3D28Get_Movie_Capture_Frame_RateEv();
}

// Preserve campaign diagnostic messages through the host's output boundary.
void A30_Vita_Log(const char *format, ...)
{
	va_list args;
	va_start(args, format);
	vfprintf(stderr, format, args);
	va_end(args);
	fputc('\n', stderr);
}
#endif

// The host fixture exercises campaign initialization, not the score screen.
// The Vita target links the original scorescreen.cpp implementation.
void ScoreScreenGameModeClass::Save_Stats(void) {}

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

class SettingsDialogProbe : public TechOptionsMenuClass
{
public:
	ChildDialogClass *Find_Tab(int id)
	{
		for (int i = 0; i < ChildDialogList.Count(); ++i)
			if (ChildDialogList[i]->Get_Dlg_ID() == id) return ChildDialogList[i];
		return NULL;
	}
};

class ConfirmationChoiceProbe : public Observer<DlgMsgBoxEvent>
{
public:
	DlgMsgBoxEvent::EventID choice = DlgMsgBoxEvent::None;
	void HandleNotification(DlgMsgBoxEvent &event)
	{
		if (event.Event() == DlgMsgBoxEvent::Yes || event.Event() == DlgMsgBoxEvent::No)
			choice = event.Event();
	}
};

bool Validate_Original_Confirmation_Controller()
{
	ConfirmationChoiceProbe observer;
	if (!DlgMsgBox::DoDialog(L"Controller test", L"Select No", DlgMsgBox::YesNo, &observer)) return false;
	DialogBaseClass *dialog = DialogMgrClass::Get_Active_Dialog();
	if (dialog == NULL) return false;
	dialog->Add_Ref();
	DialogControlClass *yes = dialog->Get_Dlg_Item(IDYES);
	DialogControlClass *no = dialog->Get_Dlg_Item(IDNO);
	bool valid = yes && no;
	auto press = [](int key) {
		A4_Frontend_Set_Test_WWUI_Key_State(key, true);
		A4_Frontend_Pump_WWUI_Key_Transitions();
		A4_Frontend_Set_Test_WWUI_Key_State(key, false);
		A4_Frontend_Pump_WWUI_Key_Transitions();
	};
	if (valid) {
		DialogMgrClass::Set_Focus(yes);
		press(VK_RIGHT); valid = (DialogMgrClass::Get_Focus() == no) && valid;
		press(VK_RIGHT); valid = (DialogMgrClass::Get_Focus() == yes) && valid;
		press(VK_LEFT); valid = (DialogMgrClass::Get_Focus() == no) && valid;
		press(VK_UP); valid = (DialogMgrClass::Get_Focus() == yes) && valid;
		press(VK_DOWN); valid = (DialogMgrClass::Get_Focus() == no) && valid;
		yes->Enable(false);
		valid = (dialog->Find_Next_Control(no) == no) && valid;
		yes->Enable(true); no->Show(false);
		valid = (dialog->Find_Next_Control(yes) == yes) && valid;
		no->Show(true); yes->Enable(false); no->Enable(false);
		valid = (dialog->Find_Next_Control(no) == NULL) && valid;
		yes->Enable(true); no->Enable(true);
		DialogMgrClass::Set_Focus(yes);
		press(VK_RIGHT); press(VK_RETURN);
		valid = observer.choice == DlgMsgBoxEvent::No && valid;
	}
	dialog->End_Dialog();
	REF_PTR_RELEASE(dialog);
	return valid;
}

bool Validate_Original_Native_Settings()
{
	char scratch[] = "/tmp/renegade-options-ui-XXXXXX";
	if (mkdtemp(scratch) == NULL) return false;
	char settings_path[256];
	snprintf(settings_path, sizeof(settings_path), "%s/options.cfg", scratch);
	if (!RenegadeVitaUserSettings::Configure(settings_path)) return false;
	ConsoleBox.Set_Exclusive(false);
	A4_Frontend_Begin_Pause_Loop();
	RenegadeDialogMgrClass::Initialize();
	MenuGameModeClass2 menu_mode;
	GameModeManager::Add(&menu_mode);
	int old_static = 0, old_dynamic = 0;
	const bool confirmation_valid = Validate_Original_Confirmation_Controller();
	COMBAT_SCENE->Get_Polygon_Budgets(&old_static, &old_dynamic);
	// A non-preset budget exposes unwanted rounding when merely closing Options.
	COMBAT_SCENE->Set_Polygon_Budgets(12345, 6789);
	const int texture_reduction = WW3D::Get_Texture_Reduction();
	const SurfaceEffectsManager::MODE old_surface = SurfaceEffectsManager::Get_Mode();
	const float old_volume = WWAudioClass::Get_Instance()->Get_Sound_Effects_Volume();
	SettingsDialogProbe *dialog = new SettingsDialogProbe;
	dialog->Start_Dialog();
	TabCtrlClass *tabs = static_cast<TabCtrlClass *>(dialog->Get_Dlg_Item(IDC_TABCTRL));
	DlgConfigAudioTabClass *audio = static_cast<DlgConfigAudioTabClass *>(dialog->Find_Tab(IDD_CONFIG_AUDIO));
	DlgConfigPerformanceTabClass *performance = static_cast<DlgConfigPerformanceTabClass *>(dialog->Find_Tab(IDD_CONFIG_PERFORMANCE));
	ChildDialogClass *video = dialog->Find_Tab(IDD_CONFIG_VIDEO);
	bool valid = confirmation_valid && tabs && tabs->Get_Tab_Count() == 3 && audio && performance && video;
	if (valid) {
		valid = !audio->Is_Dlg_Item_Enabled(IDC_RATE_COMBO) &&
			!video->Is_Dlg_Item_Enabled(IDC_GAMMA_SLIDER) &&
			!performance->Is_Dlg_Item_Enabled(IDC_CHAR_SHADOWS_SLIDER) &&
			!performance->Is_Dlg_Item_Enabled(IDC_TERRAIN_SHADOW_CHECK) && performance->On_Apply();
		SliderCtrlClass *volume = static_cast<SliderCtrlClass *>(audio->Get_Dlg_Item(IDC_SOUND_EFFECTS_SLIDER));
		valid = valid && volume != NULL;
		if (volume) {
			volume->Set_Pos(37);
			valid = valid && audio->On_Apply() &&
				WWMath::Fabs(WWAudioClass::Get_Instance()->Get_Sound_Effects_Volume() - 0.37F) < 0.001F;
		}
		for (int i = 0; i < 3; ++i) tabs->Set_Curr_Tab(i);
		SliderCtrlClass *surface = static_cast<SliderCtrlClass *>(performance->Get_Dlg_Item(IDC_SURFACE_DETAIL_SLIDER));
		if (surface) {
			surface->Set_Pos(old_surface == SurfaceEffectsManager::MODE_FULL ? 1 : 2);
			valid = performance->On_Apply() && valid;
		} else valid = false;
	}
	dialog->End_Dialog();
	REF_PTR_RELEASE(dialog);
	int after_static = 0, after_dynamic = 0;
	COMBAT_SCENE->Get_Polygon_Budgets(&after_static, &after_dynamic);
	valid = valid && after_static == 12345 && after_dynamic == 6789 &&
		WW3D::Get_Texture_Reduction() == texture_reduction;
	// Discard all process-local preference state and mutate the live owners,
	// then restore through the same boundary used by a native session reload.
	valid = RenegadeVitaUserSettings::Configure(settings_path) && valid;
	COMBAT_SCENE->Set_Polygon_Budgets(111, 222);
	WWAudioClass::Get_Instance()->Set_Sound_Effects_Volume(1.0F);
	RenegadeVitaOptions::Apply_Audio(*WWAudioClass::Get_Instance());
	RenegadeVitaOptions::Apply_Performance(*COMBAT_SCENE);
	COMBAT_SCENE->Get_Polygon_Budgets(&after_static, &after_dynamic);
	valid = valid && after_static == 12345 && after_dynamic == 6789 &&
		WWMath::Fabs(WWAudioClass::Get_Instance()->Get_Sound_Effects_Volume() - 0.37F) < 0.001F;
	COMBAT_SCENE->Set_Polygon_Budgets(old_static, old_dynamic);
	SurfaceEffectsManager::Set_Mode(old_surface);
	WWAudioClass::Get_Instance()->Set_Sound_Effects_Volume(old_volume);
	RenegadeVitaUserSettings::Configure(NULL);
	remove(settings_path);
	rmdir(scratch);
	menu_mode.Deactivate();
	GameModeManager::Safely_Deactivate();
	GameModeManager::Remove(&menu_mode);
	RenegadeDialogMgrClass::Shutdown();
	A4_Frontend_End_Menu_Loop();
	ConsoleBox.Set_Exclusive(true);
	return valid;
}

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

bool Validate_Frontend_Campaign_First_Latch()
{
	if (!g_a4_host_harness_combat_mode.Is_Inactive()) {
		g_a4_host_harness_combat_mode.Deactivate();
		GameModeManager::Safely_Deactivate();
	}
	A4_Frontend_Reset_Trace();
	A4_Frontend_Begin_Menu_Loop();
	MovieGameModeClass movie_mode;
	class ScoreMode final : public GameModeClass {
	public:
		const char *Name(void) override { return "ScoreScreen"; }
		void Init(void) override {}
		void Shutdown(void) override {}
		void Render(void) override {}
		void Think(void) override {}
	} score_mode;
	GameModeManager::Add(&movie_mode);
	GameModeManager::Add(&score_mode);
	GameInitMgrClass::Initialize_SP();
	CampaignManager::Start_Campaign(1);
	const A4FrontendTrace trace = A4_Frontend_Get_Trace();
	const bool valid = trace.tutorial_start_latched &&
		::strcmp(trace.tutorial_map, "M13.mix") == 0 &&
		PTheGameData != NULL;
	GameModeManager::Remove(&score_mode);
	GameModeManager::Remove(&movie_mode);
	GameInitMgrClass::Shutdown();
	CampaignManager::Reset();
	A4_Frontend_End_Menu_Loop();
	return valid;
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

	unsigned Wide_Text_Length(const WCHAR *text)
	{
		// This harness uses -fshort-wchar, but host libc/ASan wide-string
		// interceptors use four-byte wchar_t. Keep the engine's UTF-16 ABI.
		return text != NULL ? static_cast<unsigned>(rv_utf16_length(text)) : 0U;
	}

	bool Is_Valid_Translated_Text(const WCHAR *text)
	{
		return text != NULL &&
			Wide_Text_Length(text) > 0U &&
			rv_utf16_compare(text, STRING_NOT_FOUND) != 0 &&
			rv_utf16_strstr(text, L"IDS_") == NULL;
	}

	bool Text_Has_Renderable_Glyphs(FontCharsClass *font, const WCHAR *text,
		unsigned *covered_glyphs_out, unsigned *advance_out)
	{
		if (covered_glyphs_out != NULL) *covered_glyphs_out = 0U;
		if (advance_out != NULL) *advance_out = 0U;
		if (font == NULL || text == NULL) return false;
		unsigned covered_glyphs = 0U;
		unsigned advance = 0U;
		for (const WCHAR *cursor = text; *cursor != 0; ++cursor) {
			if (*cursor <= L' ') continue;
			const int width = font->Get_Char_Width(*cursor);
			const int spacing = font->Get_Char_Spacing(*cursor);
			if (width > 0) ++covered_glyphs;
			if (spacing > 0) advance += static_cast<unsigned>(spacing);
		}
		if (covered_glyphs_out != NULL) *covered_glyphs_out = covered_glyphs;
		if (advance_out != NULL) *advance_out = advance;
		return covered_glyphs > 0U && advance > 0U;
	}

	bool Load_Original_Strings_Database(FileFactoryClass &factory,
		unsigned *object_count_out, unsigned *version_out)
	{
		if (object_count_out != NULL) *object_count_out = 0U;
		if (version_out != NULL) *version_out = 0U;
		TranslateDBClass::Initialize();
		FileClass *file = factory.Get_File("STRINGS.TDB");
		if (file == NULL) return false;

		bool loaded = false;
		if (file->Open(FileClass::READ)) {
			if (file->Is_Available()) {
				ChunkLoadClass cload(file);
				loaded = SaveLoadSystemClass::Load(cload);
			}
			file->Close();
		}
		factory.Return_File(file);
		if (object_count_out != NULL) {
			*object_count_out = static_cast<unsigned>(TranslateDBClass::Get_Object_Count());
		}
		if (version_out != NULL) {
			*version_out = static_cast<unsigned>(TranslateDBClass::Get_Version_Number());
		}
		return loaded && TranslateDBClass::Is_Loaded();
	}

	struct MainMenuTextProbe {
		int control_id;
		const char *desc;
	};

	const MainMenuTextProbe kMainMenuTextProbes[] = {
		{ IDC_MENU_START_SP_GAME_BUTTON, "IDS_MENU_TEXT073" },
		{ IDC_MENU_MP_INTERNET_GAME_BUTTON, "IDS_MENU_TEXT276" },
		{ IDC_MENU_MP_LAN_GAME_BUTTON, "IDS_MENU_TEXT277" },
		{ IDC_MENU_START_PRACTICE_GAME_BUTTON, "IDS_MENU_TEXT513" },
		{ IDC_MENU_OPTIONS_BUTTON, "IDS_MENU_TEXT076" },
		{ IDC_MENU_QUIT_BUTTON, "IDS_MENU_TEXT077" },
	};

	bool Validate_Main_Menu_Translation_Table(unsigned *valid_count_out)
	{
		if (valid_count_out != NULL) *valid_count_out = 0U;
		unsigned valid_count = 0U;
		for (unsigned index = 0U;
			index < sizeof(kMainMenuTextProbes) / sizeof(kMainMenuTextProbes[0]);
			++index) {
			const MainMenuTextProbe &probe = kMainMenuTextProbes[index];
			TDBObjClass *object = TranslateDBClass::Find_Object(probe.desc);
			const WCHAR *text = TranslateDBClass::Get_String(probe.desc);
			const bool valid = object != NULL && Is_Valid_Translated_Text(text);
			printf("a31.frontend_mainmenu_translation_%s=%s,len=%u\n",
				probe.desc, valid ? "valid" : "invalid", Wide_Text_Length(text));
			fflush(stdout);
			if (valid) ++valid_count;
		}
		if (valid_count_out != NULL) *valid_count_out = valid_count;
		return valid_count ==
			sizeof(kMainMenuTextProbes) / sizeof(kMainMenuTextProbes[0]);
	}

	bool Validate_Main_Menu_Control_Text(MainMenuDialogClass *menu,
		unsigned *valid_count_out, unsigned *renderable_count_out)
	{
		if (valid_count_out != NULL) *valid_count_out = 0U;
		if (renderable_count_out != NULL) *renderable_count_out = 0U;
		if (menu == NULL) return false;
		FontCharsClass *font = StyleMgrClass::Get_Font(StyleMgrClass::FONT_MENU);
		if (font == NULL) return false;

		unsigned valid_count = 0U;
		unsigned renderable_count = 0U;
		for (unsigned index = 0U;
			index < sizeof(kMainMenuTextProbes) / sizeof(kMainMenuTextProbes[0]);
			++index) {
			const MainMenuTextProbe &probe = kMainMenuTextProbes[index];
			DialogControlClass *control = menu->Get_Dlg_Item(probe.control_id);
			const WCHAR *text = control != NULL ? control->Get_Text() : NULL;
			unsigned covered_glyphs = 0U;
			unsigned advance = 0U;
			const bool valid = Is_Valid_Translated_Text(text);
			const bool renderable = Text_Has_Renderable_Glyphs(font, text,
				&covered_glyphs, &advance);
			printf("a31.frontend_mainmenu_control_%s=%s,renderable=%s,len=%u,glyphs=%u,advance=%u\n",
				probe.desc, valid ? "valid" : "invalid",
				renderable ? "true" : "false", Wide_Text_Length(text),
				covered_glyphs, advance);
			fflush(stdout);
			if (valid) ++valid_count;
			if (renderable) ++renderable_count;
		}
		REF_PTR_RELEASE(font);
		if (valid_count_out != NULL) *valid_count_out = valid_count;
		if (renderable_count_out != NULL) *renderable_count_out = renderable_count;
		const unsigned expected =
			sizeof(kMainMenuTextProbes) / sizeof(kMainMenuTextProbes[0]);
		return valid_count == expected && renderable_count == expected;
	}

	void Stage(const char *name)
	{
	fprintf(stderr, "a31.stage=%s\n", name);
	fflush(stderr);
}

bool Client_Connection_Present(const char *stage)
{
	const bool present = cNetwork::PClientConnection != NULL;
	if (!present) {
		fprintf(stderr, "a31.network_client_connection.%s=missing\n", stage);
		fflush(stderr);
	}
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
			unsigned *render_frames_out, bool *mode_lifecycle_out,
			unsigned *valid_label_count_out, unsigned *renderable_label_count_out)
	{
		if (control_count_out != NULL) *control_count_out = 0;
		if (render_frames_out != NULL) *render_frames_out = 0;
		if (mode_lifecycle_out != NULL) *mode_lifecycle_out = false;
		if (valid_label_count_out != NULL) *valid_label_count_out = 0U;
		if (renderable_label_count_out != NULL) *renderable_label_count_out = 0U;

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
		unsigned valid_label_count = 0U;
		unsigned renderable_label_count = 0U;
		const bool menu_labels_valid = Validate_Main_Menu_Control_Text(menu,
			&valid_label_count, &renderable_label_count);
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
	// Exercise the original auto-link command after every manager re-entry.
	// Directly constructing Load would conceal factories deleted at shutdown.
	const int dialogs_before_load = DialogMgrClass::Get_Dialog_Count();
	if (menu != NULL) menu->On_Command(IDC_MENU_LOAD_SP_GAME_BUTTON, BN_CLICKED, 0);
	const bool load_factory_created_dialog =
		DialogMgrClass::Get_Dialog_Count() == dialogs_before_load + 1;
	Print("frontend_load_factory_after_reinitialize", load_factory_created_dialog);
	bool load_focus_valid = true;
	if (::getenv("RENEGADE_HOST_LOAD_FOCUS_FIXTURE") != NULL) {
		// Optional private original-save fixture; never required by public builds.
		for (unsigned frame = 0; frame < 180U; ++frame) {
			WW3D::Sync(WW3D::Get_Sync_Time() + 16U);
			DialogMgrClass::On_Frame_Update();
			DialogMgrClass::Render();
		}
		DialogBaseClass *load = DialogMgrClass::Get_Active_Dialog();
		load_focus_valid = load != NULL && load->Get_Dlg_ID() == IDD_MENU_LOAD_SP_GAME;
		if (load_focus_valid) {
			ListCtrlClass *list = static_cast<ListCtrlClass *>(load->Get_Dlg_Item(IDC_LOAD_GAME_LIST_CTRL));
			DialogControlClass *remove = load->Get_Dlg_Item(IDC_DELETE_GAME_BUTTON);
			load_focus_valid = list != NULL && remove != NULL;
			if (load_focus_valid) {
				for (int row = 0; row < list->Get_Entry_Count(); ++row) {
					list->Set_Curr_Sel(row);
					if (remove->Is_Enabled()) break;
				}
				load_focus_valid = remove->Is_Enabled() && remove->Is_Visible();
				A4_Frontend_Reset_Trace();
				A4_Frontend_Begin_Menu_Loop();
				DialogMgrClass::Set_Focus(list);
				bool reached_delete = false;
				for (unsigned step = 0; step < 4U; ++step) {
					A4_Frontend_Set_Test_WWUI_Key_State(VK_TAB, true);
					A4_Frontend_Pump_WWUI_Key_Transitions();
					A4_Frontend_Set_Test_WWUI_Key_State(VK_TAB, false);
					A4_Frontend_Pump_WWUI_Key_Transitions();
					DialogControlClass *focus = DialogMgrClass::Get_Focus();
					printf("a31.load_focus_step=%u id=%d delete=%d\n", step + 1,
						focus != NULL ? focus->Get_ID() : -1, IDC_DELETE_GAME_BUTTON);
					reached_delete = reached_delete || focus == remove;
					DialogMgrClass::On_Frame_Update();
				}
				A4_Frontend_End_Menu_Loop();
				load_focus_valid = load_focus_valid && reached_delete;
			}
		}
		Print("frontend_load_list_to_delete_controller_focus", load_focus_valid);
	}
	menu_mode.Deactivate();
	GameModeManager::Safely_Deactivate();
	const bool mode_shutdown = menu_mode.Is_Inactive();
		GameModeManager::Remove(&menu_mode);
		const bool valid = menu != NULL && controls > 0U &&
			initial_dialog_count > 0U && rendered_frames == 3U &&
			mode_active && mode_shutdown && menu_labels_valid && load_factory_created_dialog && load_focus_valid;
		RenegadeDialogMgrClass::Shutdown();
		ConsoleBox.Set_Exclusive(true);

		if (control_count_out != NULL) *control_count_out = controls;
		if (render_frames_out != NULL) *render_frames_out = rendered_frames;
		if (valid_label_count_out != NULL) *valid_label_count_out = valid_label_count;
		if (renderable_label_count_out != NULL) *renderable_label_count_out =
			renderable_label_count;
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
		for (unsigned pump_index = 0; pump_index < 180U &&
				(DialogMgrClass::Get_Active_Dialog() == NULL ||
				 DialogMgrClass::Get_Focus() == NULL);
			 ++pump_index) {
			WW3D::Sync(WW3D::Get_Sync_Time() + 16U);
			DialogMgrClass::On_Frame_Update();
			DialogMgrClass::Render();
		}

		MainMenuDialogClass *const menu = MainMenuDialogClass::Get_Instance();
		DialogControlClass *const initial_focus = DialogMgrClass::Get_Focus();
		if (control_count_out != NULL && menu != NULL) {
			*control_count_out = static_cast<unsigned>(menu->Get_Control_Count());
		}

		A4_Frontend_Reset_Trace();
		A4_Frontend_Begin_Menu_Loop();
		A4_Frontend_Set_Test_WWUI_Key_State(VK_DOWN, true);
		A4_Frontend_Pump_WWUI_Key_Transitions();
		DialogMgrClass::On_Frame_Update();
		DialogControlClass *const after_down_focus = DialogMgrClass::Get_Focus();
		A4_Frontend_Set_Test_WWUI_Key_State(VK_DOWN, false);
		A4_Frontend_Pump_WWUI_Key_Transitions();
		DialogMgrClass::On_Frame_Update();
		A4_Frontend_Set_Test_WWUI_Key_State(VK_UP, true);
		A4_Frontend_Pump_WWUI_Key_Transitions();
		DialogMgrClass::On_Frame_Update();
		DialogControlClass *const after_up_focus = DialogMgrClass::Get_Focus();
		A4_Frontend_Set_Test_WWUI_Key_State(VK_UP, false);
		A4_Frontend_Pump_WWUI_Key_Transitions();
		DialogMgrClass::On_Frame_Update();
		A4_Frontend_End_Menu_Loop();

		if (DialogMgrClass::Get_Active_Dialog() != NULL) {
			DialogMgrClass::Set_Active_Dialog(NULL);
			for (unsigned pump_index = 0; pump_index < 180U &&
					DialogMgrClass::Get_Active_Dialog() != NULL;
				 ++pump_index) {
				WW3D::Sync(WW3D::Get_Sync_Time() + 16U);
				DialogMgrClass::Render();
			}
		}

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
			GameModeManager::Find("Combat") != NULL && !trace.reload_requested;
		// A load from pause remains a request until the outer session owner
		// has destroyed menu references and completed the original teardown.
		A4_Frontend_Begin_Pause_Loop();
		GameInitMgrClass::Start_Game("M00_Tutorial.mix", -1, 0);
		const A4FrontendTrace reload = A4_Frontend_Get_Trace();
		A4_Frontend_End_Menu_Loop();
		const bool deferred_reload = reload.reload_requested &&
			A4_Frontend_Get_Trace().reload_requested &&
			::strcmp(reload.tutorial_map, "M00_Tutorial.mix") == 0;
		A4_Frontend_Begin_Menu_Loop();
		const bool fresh_menu_clears_request = !A4_Frontend_Get_Trace().reload_requested;

		menu_mode.Deactivate();
		GameModeManager::Safely_Deactivate();
		GameModeManager::Remove(&menu_mode);
		RenegadeDialogMgrClass::Shutdown();
		GameInitMgrClass::Shutdown();
		A4_Frontend_End_Menu_Loop();
		ConsoleBox.Set_Exclusive(true);
		return valid && deferred_reload && fresh_menu_clears_request;
	}


	bool Prepare_Explosion_Choice_For_Smoke(DefinitionClass *definition,
		const char *name, unsigned depth)
	{
		if (definition == NULL || depth >= 4U) {
			printf("a31.m13_sam_prewarm=%s missing_or_deep=%u\n", name, depth);
			return false;
		}
		if (definition->Get_Class_ID() == CLASSID_TWIDDLERS) {
			const TwiddlerClass *twiddler = (const TwiddlerClass *)definition;
			const int count = twiddler->Get_Referenced_Definition_Count();
			bool all_ready = count > 0;
			printf("a31.m13_sam_prewarm_twiddler=%s choices=%d\n", name, count);
			for (int index = 0; index < count; ++index) {
				DefinitionClass *choice = DefinitionMgrClass::Find_Definition(
					twiddler->Get_Referenced_Definition_ID(index), false);
				if (!Prepare_Explosion_Choice_For_Smoke(choice, name, depth + 1U)) {
					all_ready = false;
				}
			}
			return all_ready;
		}
		if (definition->Get_Class_ID() != CLASSID_DEF_EXPLOSION) {
			printf("a31.m13_sam_prewarm=%s unexpected_class=%u\n", name,
				static_cast<unsigned>(definition->Get_Class_ID()));
			return false;
		}
		ExplosionDefinitionClass *explosion =
			(ExplosionDefinitionClass *)definition;
		PhysDefClass *phys_def = static_cast<PhysDefClass *>(
			DefinitionMgrClass::Find_Definition(explosion->PhysDefID));
		TimedDecorationPhysClass *phys = phys_def != NULL &&
			phys_def->Is_Type("TimedDecorationPhysDef") ?
			static_cast<TimedDecorationPhysClass *>(phys_def->Create()) : NULL;
		const bool ready = phys != NULL && phys->Peek_Model() != NULL;
		printf("a31.m13_sam_prewarm=%s variant=%s ready=%d\n", name,
			explosion->Get_Name(), ready ? 1 : 0);
		if (phys != NULL) phys->Release_Ref();
		return ready;
	}

	} // namespace

int main(int argc, char **argv)
{
#if defined(RENEGADE_ORIGINAL_SORTING) && defined(RENEGADE_HOST_ABI_TEST)
	if (argc == 3 && strcmp(argv[1], "--sorting-selftest") == 0) {
		WWMath::Init();
		if (WW3D::Init(NULL, NULL, true) != WW3D_ERROR_OK) return 1;
		bool passed = false;
		if (strcmp(argv[2], "basic") == 0) passed = Check_Original_Sorting_Renderer();
		if (strcmp(argv[2], "strip") == 0) passed = Check_Native_Strip_Renderer();
		if (strcmp(argv[2], "statistics") == 0) passed = Check_Original_Frame_Statistics();
		if (strcmp(argv[2], "nodes") == 0) passed = Check_Original_Sorting_Capacity(4097, 3, 1);
		if (strcmp(argv[2], "vertices") == 0) passed = Check_Original_Sorting_Capacity(3000, 24, 1);
		if (strcmp(argv[2], "indices") == 0) passed = Check_Original_Sorting_Capacity(2, 3, 11000);
		if (strcmp(argv[2], "zero") == 0) passed = Check_Original_Sorting_Capacity(1, 3, 0);
		if (strcmp(argv[2], "index-limit") == 0) passed = Check_Original_Sorting_Capacity(1, 3, 21845);
		if (strcmp(argv[2], "vertex-limit") == 0) passed = Check_Original_Sorting_Capacity(1, 65535, 1);
		if (strcmp(argv[2], "interleaved") == 0) passed = Check_Original_Sorting_Capacity(1000, 72, 2, true);
		WW3D::Shutdown();
		return passed ? 0 : 1;
	}
#endif
    if (argc == 2 && strcmp(argv[1], "--state-machine-selftest") == 0)
        return OriginalStateMachineProbe::Run();
    if (argc >= 3 && argc <= 258 && strcmp(argv[1], "--persist-factories") == 0) {
        for (int i = 2; i < argc; ++i) {
            char *end = NULL;
            const unsigned long id = strtoul(argv[i], &end, 10);
            if (!*argv[i] || *end || id > 0xffffffffUL) return 2;
            printf("persist_factory.%lu=%d\n", id,
                SaveLoadSystemClass::Find_Persist_Factory(static_cast<uint32>(id)) != NULL);
        }
        return 0;
    }
	if ((argc == 3 || argc == 4) && strcmp(argv[1], "--export-resource-options") == 0)
		return DirectClientProbe::Export_Resource_Options(argv[2], argc == 4 ? argv[3] : "C&C_ResourceFixture.mix");
	if (argc == 2 && strcmp(argv[1], "--direct-client-selftest") == 0)
		return DirectClientProbe::Run();
	if (argc == 4 && strcmp(argv[1], "--options-wire-probe") == 0)
		return DirectClientProbe::Replay_Options(argv[2], argv[3]);
	if (argc == 2 && strcmp(argv[1], "--tt-server-info-selftest") == 0)
		return DirectClientProbe::TT_Server_Info_Test();
	if (argc == 2 && strcmp(argv[1], "--tt-client-greeting-selftest") == 0)
		return DirectClientProbe::TT_Client_Greeting_Test();
	if (argc == 2 && strcmp(argv[1], "--missing-network-preset-selftest") == 0)
		return DirectClientProbe::Run_Missing_Preset();
	if (argc == 2 && strcmp(argv[1], "--building-factory-selftest") == 0)
		return DirectClientProbe::Building_Factory_Test();
	if (argc == 2 && strcmp(argv[1], "--announcement-selftest") == 0)
		return DirectClientProbe::Announcement_Test();
	if (argc == 2 && strcmp(argv[1], "--connection-timeout-selftest") == 0)
		return DirectClientProbe::Run_Timeout();
	if (argc == 2 && strcmp(argv[1], "--client-options-selftest") == 0)
		return DirectClientProbe::Run_Options();
	if (argc == 2 && strcmp(argv[1], "--tt-physical-rare-selftest") == 0)
		return DirectClientProbe::Physical_Rare_Test();
	if (argc == 2 && strcmp(argv[1], "--tt-soldier-rare-selftest") == 0)
		return Validate_TT_Soldier_Rare();
	if (argc == 2 && strcmp(argv[1], "--tt-smart-frequent-selftest") == 0)
		return Validate_TT_Smart_Frequent();
	if (argc == 2 && strcmp(argv[1], "--tt-soldier-frequent-selftest") == 0)
		return Validate_TT_Soldier_Frequent();
	if (argc == 2 && strcmp(argv[1], "--tt-vehicle-selftest") == 0)
		return Validate_TT_Vehicle_Vectors();
	if (argc == 2 && strcmp(argv[1], "--tt-purchase-catalog-selftest") == 0)
		return Validate_TT_Purchase_Catalogs();
	if (argc == 2 && strcmp(argv[1], "--tt-c4-selftest") == 0)
		return Validate_TT_C4_Vectors();
	if (argc == 2 && strcmp(argv[1], "--tt-defense-selftest") == 0)
		return Validate_TT_Defense();
	static unsigned interactive_cycle = 0;
	if (argc == 2 && strcmp(argv[1], "--network-selftest") == 0)
		return Validate_Original_WWNet_Packets();
#if defined(RENEGADE_A35_ORIGINAL_WWAUDIO)
	if (argc == 2 && strcmp(argv[1], "--audio-release-selftest") == 0)
		return AudioReleaseProbe::Run();
	if (argc == 2 && strcmp(argv[1], "--audio-flush-enqueue-selftest") == 0)
		return AudioReleaseProbe::Run_Flush_Enqueue();
	if (argc == 2 && strcmp(argv[1], "--audio-logical-removal-selftest") == 0)
		return AudioReleaseProbe::Run_Logical_Removal();
	if (argc == 2 && strcmp(argv[1], "--audio-audible-removal-selftest") == 0)
		return AudioReleaseProbe::Run_Audible_Removal();
	if (argc == 2 && strcmp(argv[1], "--audio-completed-sounds-selftest") == 0)
		return AudioReleaseProbe::Run_Completed_Sounds();
	if (argc == 2 && strcmp(argv[1], "--audio-continuous-removal-selftest") == 0)
		return AudioReleaseProbe::Run_Continuous_Removal();
#endif
	if (argc == 2 && strcmp(argv[1], "--local-session-selftest") == 0)
		return Validate_Local_Session_Boundaries();
	if (argc == 2 && strcmp(argv[1], "--mission-ranks-selftest") == 0)
		return MissionRankProbe::Run();
	if (argc == 3 && strcmp(argv[1], "--ttfs-cache-selftest") == 0)
		return Validate_TTFS_Fixture_Factory(argv[2]);
	const unsigned cycle = ++interactive_cycle;
	if (argc != 5 && argc != 6 && argc != 7 && argc != 8) {
		fprintf(stderr, "usage: %s RETAIL_ROOT USER_ROOT CACHE_ROOT MODS_ROOT [LEVEL_MIX] [M13_INVENTORY|M13_INTRO_SMOKE|M13_SAM_DAMAGE_SMOKE|M13_SAM_PREWARM_SMOKE|SKIRMISH_SMOKE]\n", argv[0]);
		return 2;
	}
	const char *level_mix = argc >= 6 ? argv[5] : "M00_Tutorial.mix";
	std::string negotiated_map;
	const bool remote_purchase = argc == 8 && (strcmp(argv[6], "REMOTE_SERVER_PURCHASE_SMOKE") == 0 ||
		strcmp(argv[6], "REMOTE_CLIENT_PURCHASE_SMOKE") == 0);
	const bool remote_server = argc == 8 && (strcmp(argv[6], "REMOTE_SERVER_SMOKE") == 0 ||
		strcmp(argv[6], "REMOTE_SERVER_PURCHASE_SMOKE") == 0);
	const bool tt_admission = argc == 8 && strcmp(argv[6], "TT_ADMISSION_PROBE") == 0;
	const bool tt_soak = argc == 8 && strcmp(argv[6], "TT_WORLD_SOAK") == 0;
	bool tt_world = tt_soak || (argc == 8 && strcmp(argv[6], "TT_WORLD_PROBE") == 0);
	const bool resource_fixture = argc == 8 && strcmp(argv[6], "RESOURCE_ADMISSION_FIXTURE") == 0;
	const bool remote_admission = tt_admission || resource_fixture ||
		(argc == 8 && strcmp(argv[6], "REMOTE_ADMISSION_PROBE") == 0);
	const bool remote_client = tt_world || remote_admission || (argc == 8 && (strcmp(argv[6], "REMOTE_CLIENT_SMOKE") == 0 ||
		strcmp(argv[6], "REMOTE_CLIENT_PURCHASE_SMOKE") == 0));
	const bool remote_smoke = remote_server || remote_client;
	const bool harvester_lifetime = argc == 7 && strcmp(argv[6], "HARVESTER_LIFETIME_SMOKE") == 0;
	const bool tt_soldier_smoke = argc == 7 && strcmp(argv[6], "TT_SOLDIER_STATE_SMOKE") == 0;
	const bool tt_vehicle_smoke = argc == 7 && strcmp(argv[6], "TT_VEHICLE_STATE_SMOKE") == 0;
	unsigned remote_port = 0;
	bool tt_client_request = false;
	if (remote_purchase && strchr(argv[7], ':')) return 2; // Isolated loopback experiment only.
	RenegadeNetworkProvider::Endpoint remote_endpoint;
	remote_endpoint.Address = INADDR_LOOPBACK;
	if (remote_admission || (remote_client && strchr(argv[7], ':') != NULL)) {
		if (!RenegadeNetworkProvider::Parse_Client_Request(argv[7], 0, remote_endpoint, tt_client_request)) return 2;
		remote_port = remote_endpoint.PortNumber;
		if (tt_client_request && remote_client && !remote_admission) tt_world = true;
	} else if (remote_smoke) {
		char *end = nullptr;
		unsigned long port = strtoul(argv[7], &end, 10);
		if (!*argv[7] || *end || port < 1024 || port > 65535) return 2;
		remote_port = port;
	}
	const bool m13_sam_prewarm_smoke = argc == 7 &&
		strcmp(level_mix, "M13.mix") == 0 &&
		strcmp(argv[6], "M13_SAM_PREWARM_SMOKE") == 0;
	const bool m13_sam_damage_smoke = argc == 7 &&
		strcmp(level_mix, "M13.mix") == 0 &&
		(strcmp(argv[6], "M13_SAM_DAMAGE_SMOKE") == 0 ||
			m13_sam_prewarm_smoke);
	const bool m13_inventory = argc == 7 &&
		strcmp(level_mix, "M13.mix") == 0 &&
		strcmp(argv[6], "M13_INVENTORY") == 0;
	const bool m13_intro_smoke = argc == 7 &&
		strcmp(level_mix, "M13.mix") == 0 &&
		strcmp(argv[6], "M13_INTRO_SMOKE") == 0;
	const bool m13_save_replay = argc == 7 &&
		strcmp(level_mix, "M13.mix") == 0 &&
		strcmp(argv[6], "M13_SAVE_REPLAY") == 0;
	const bool m01_intro_smoke = argc == 7 &&
		strcmp(level_mix, "M01.mix") == 0 &&
		strcmp(argv[6], "M01_INTRO_SMOKE") == 0;
	const bool m01_save_replay = argc == 7 &&
		strcmp(level_mix, "M01.mix") == 0 &&
		strcmp(argv[6], "M01_SAVE_REPLAY") == 0;
	char skirmish_archive[96];
	const bool purchase_smoke = argc == 7 && strcmp(argv[6], "PURCHASE_SMOKE") == 0;
	const bool skirmish_smoke = argc == 7 && (strcmp(argv[6], "SKIRMISH_SMOKE") == 0 || purchase_smoke) &&
		A4_Frontend_Resolve_Skirmish_Archive(level_mix, skirmish_archive, sizeof(skirmish_archive));
	if (argc >= 7 && !remote_smoke && !harvester_lifetime && !tt_soldier_smoke && !tt_vehicle_smoke && !m13_sam_damage_smoke && !m13_inventory && !m13_intro_smoke && !m13_save_replay && !m01_intro_smoke && !m01_save_replay && !skirmish_smoke) return 2;
#ifndef __vita__
	HostFixedSimulationClock = m13_inventory || m13_intro_smoke || m13_save_replay || m01_intro_smoke || m01_save_replay;
	const char *replay_frame_ms = getenv("A31_HOST_REPLAY_FRAME_MS");
	if (replay_frame_ms != NULL) {
		char *end = NULL;
		const unsigned long value = strtoul(replay_frame_ms, &end, 10);
		if (!HostFixedSimulationClock || replay_frame_ms[0] == '\0' ||
			*end != '\0' || value < 1UL || value > 200UL) {
			fprintf(stderr, "A31_HOST_REPLAY_FRAME_MS requires a replay mode and 1..200 milliseconds\n");
			return 2;
		}
		HostReplayFrameMilliseconds = static_cast<unsigned>(value);
	}
	if (HostFixedSimulationClock)
		printf("a31.host_replay_frame_ms=%u native_timing_changed=0\n", HostReplayFrameMilliseconds);
#else
	if (m13_intro_smoke || m01_intro_smoke) return 2;
#endif
	char level_archive[96] = {};
	char level_ldd_name[96] = {};
	snprintf(level_archive, sizeof(level_archive), "Data\\%s", level_mix);
	snprintf(level_ldd_name, sizeof(level_ldd_name), "%s", level_mix);
	char *extension = strrchr(level_ldd_name, '.');
	if (extension == NULL) { fprintf(stderr, "invalid level archive name: %s\n", level_mix); return 2; }
	snprintf(extension, sizeof(level_ldd_name) - static_cast<size_t>(extension - level_ldd_name), ".ldd");
	Print_Number("hardware_equivalent_cycle", cycle);

	const RenegadePathRoots roots = { argv[1], argv[2], argv[3], argv[4] };
	const RenegadeResolvedPath ranks_path = Renegade_Resolve_Path(
		roots, "user/config/mission-ranks-v1.cfg", RENEGADE_PATH_WRITE);
	const char *ranks_key = Build_Registry_Location_String(
		const_cast<char *>(APP_SUB_KEY), NULL, const_cast<char *>("Ranks"));
	const bool ranks_loaded = RenegadeMissionRanks::Configure(
		ranks_path.success ? ranks_path.physical : NULL, ranks_key);
	const RenegadeMissionRanks::Status ranks_status = RenegadeMissionRanks::Get_Status();
	printf("a31.mission_ranks_loaded=%s,count=%u,error=%d\n",
		ranks_loaded ? "true" : "false", ranks_status.count, ranks_status.error);
	Renegade_Set_Find_Roots(roots);
	RenegadeRootedFileFactoryClass root_factory(roots);
	MixFileFactoryClass always2_factory(kAlways2Archive, &root_factory);
	MixFileFactoryClass always_dbs_factory(kAlwaysDbsArchive, &root_factory);
	MixFileFactoryClass always_factory(kAlwaysArchive, &root_factory);
	MixFileFactoryClass m00_factory(level_archive, &root_factory);
	std::unique_ptr<MixFileFactoryClass> negotiated_factory;
	FileFactoryListClass factory_list;
	factory_list.Add_FileFactory(&root_factory, "");
	factory_list.Add_FileFactory(&always2_factory, "Always2.dat");
	factory_list.Add_FileFactory(&always_dbs_factory, "Always.dbs");
	factory_list.Add_FileFactory(&always_factory, "Always.dat");
	if (!tt_world) factory_list.Add_FileFactory(&m00_factory, level_mix);

	FileFactoryClass *previous_read_factory = _TheFileFactory;
	FileFactoryClass *previous_write_factory = _TheWritingFileFactory;
	_TheFileFactory = &factory_list;
	_TheWritingFileFactory = &root_factory;

	bool passed = always2_factory.Is_Valid() && always_dbs_factory.Is_Valid() &&
		always_factory.Is_Valid() && (tt_world || m00_factory.Is_Valid());
	bool math_initialized = false;
	bool path_manager_initialized = false;
	bool ww3d_initialized = false;
	bool wwphys_initialized = false;
	bool wwsaveload_initialized = false;
	bool input_initialized = false;
	bool combat_initialized = false;
	bool radar_initialized = false;
		bool stylemgr_initialized = false;
		bool translatedb_initialized = false;
		bool global_conversations_initialized = false;
		bool campaign_initialized = false;
	bool session_initialized = false;
	bool single_player_transport_initialized = false;
	bool level_loaded = false;
	A31ClientConnect remote_join;
	cConnection *accepted_connection = nullptr;
	WW3DAssetManager *asset_manager = NULL;
	{
		Stage("audio_construct");
#if defined(RENEGADE_A35_ORIGINAL_WWAUDIO)
		Renegade_Miles_Reset_Runtime_Stats();
		HostAudioFileFactory audio_factory(&factory_list);
		WWAudioClass audio(false);
		audio.Initialize();
		audio.Set_File_Factory(&audio_factory);
		const bool audio_ready = audio.Get_Sound_Scene() != NULL &&
			audio.Get_2D_Driver() != NULL && audio.Get_3D_Driver() != 0;
		Print("host_original_audio_scene_and_drivers", audio_ready);
		passed = passed && audio_ready;
		std::vector<int16_t> audio_mix(HostReplayFrameMilliseconds * 48U * 2U);
#else
		WWAudioClass audio(true);
#endif
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
			{
				const Vector3 point(12.0f, -4.0f, 2.0f);
				PathClass zero_path;
				zero_path.Initialize(point, point);
				Vector3 next;
				const bool zero_path_valid = zero_path.Evaluate_Next_Point(point, next) &&
					zero_path.Get_State() == PathClass::STATE_PATH_COMPLETE &&
					next.Is_Valid() && next.X == point.X && next.Y == point.Y && next.Z == point.Z;
				Print("zero_length_original_path_completes", zero_path_valid);
				if (!zero_path_valid) { passed = false; break; }
			}
			asset_manager = new WW3DAssetManager;
			asset_manager->Set_WW3D_Load_On_Demand(true);
			asset_manager->Set_Activate_Fog_On_Load(true);
			Stage("ww3d_init");
			ww3d_initialized = WW3D::Init(NULL, NULL, true) == WW3D_ERROR_OK;
			if (!ww3d_initialized) { passed = false; break; }
#if defined(RENEGADE_ORIGINAL_SORTING) && defined(RENEGADE_HOST_ABI_TEST)
			const bool sorting_ready = Check_Original_Sorting_Renderer();
			Print("original_sorting_queue_draw_cleanup", sorting_ready);
			if (!sorting_ready) { passed = false; break; }
#endif
			Stage("wwphys_init");
			WWPhys::Init();
			wwphys_initialized = true;
				WWSaveLoad::Init();
				wwsaveload_initialized = true;
				Stage("strings_database_load");
				unsigned translatedb_objects = 0U;
				unsigned translatedb_version = 0U;
				const bool translatedb_loaded = Load_Original_Strings_Database(
					factory_list, &translatedb_objects, &translatedb_version);
				Print("strings_database_loaded", translatedb_loaded);
				Print_Number("strings_database_objects", translatedb_objects);
				Print_Number("strings_database_version", translatedb_version);
				if (!translatedb_loaded) { passed = false; break; }
				translatedb_initialized = true;
				Stage("global_conversation_database_load");
				uint32_t global_conversation_count = 0U;
				global_conversations_initialized = A31_Interactive_Load_Global_Conversations(
					factory_list, &global_conversation_count);
				Print("global_conversation_database_loaded", global_conversations_initialized);
				Print_Number("global_conversation_database_records", global_conversation_count);
				if (!global_conversations_initialized) { passed = false; break; }
				unsigned main_menu_translation_count = 0U;
				const bool main_menu_translations =
					Validate_Main_Menu_Translation_Table(&main_menu_translation_count);
				Print("frontend_mainmenu_translations_resolved",
					main_menu_translations);
				Print_Number("frontend_mainmenu_translation_labels",
					main_menu_translation_count);
				if (!main_menu_translations) { passed = false; break; }

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
					Input::Get_Primary_Key_For_Function(INPUT_FUNCTION_CYCLE_POG) == DIK_BACK &&
					Input::Get_Secondary_Key_For_Function(INPUT_FUNCTION_CYCLE_POG) == 0 &&
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
			EncyclopediaMgrClass::Initialize();
			campaign_initialized = CampaignFlowDescriptions.Count() > 0;
			Print_Number("campaign_flow_entries",
				static_cast<unsigned>(CampaignFlowDescriptions.Count()));
			Print("campaign_catalog_loaded", campaign_initialized);
			if (!campaign_initialized) { passed = false; break; }
			if (getenv("RENEGADE_TRACE_CAMPAIGN_FLOW") != nullptr) {
				for (int index = 0; index < CampaignFlowDescriptions.Count(); ++index) {
					printf("campaign_flow[%d]=%s\n", index,
						CampaignFlowDescriptions[index].Peek_Buffer());
				}
			}
			Stage("frontend_mainmenu_lifecycle");
			Register_A4_Host_Harness_Combat_Mode();
			const bool campaign_first_latch = Validate_Frontend_Campaign_First_Latch();
			Print("frontend_campaign_first_latched", campaign_first_latch);
			if (!campaign_first_latch) { passed = false; break; }
				unsigned main_menu_control_count = 0;
				unsigned main_menu_render_frames = 0;
				unsigned main_menu_valid_labels = 0U;
				unsigned main_menu_renderable_labels = 0U;
				bool original_menu_mode_lifecycle = false;
				const bool authentic_main_menu_lifecycle =
					Validate_Authentic_Main_Menu_Lifecycle(&main_menu_control_count,
						&main_menu_render_frames, &original_menu_mode_lifecycle,
						&main_menu_valid_labels, &main_menu_renderable_labels);
					Print("frontend_dialog_manager_initialized", authentic_main_menu_lifecycle);
					Print("frontend_original_menu_mode_lifecycle", original_menu_mode_lifecycle);
					Print_Number("frontend_mainmenu_original_controls", main_menu_control_count);
					Print_Number("frontend_mainmenu_original_render_frames", main_menu_render_frames);
					Print_Number("frontend_mainmenu_valid_labels", main_menu_valid_labels);
					Print_Number("frontend_mainmenu_renderable_labels",
						main_menu_renderable_labels);
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
			if (!remote_client) cServerFps::Create_Instance();
			Stage(skirmish_smoke ? "gameinit_skirmish" : "gameinit_sp");
			/* Preserve the original single-player session owner rather than
			 * reproducing its cSinglePlayerData/nickname/game-data setup in the
			 * direct M00 development harness.  The level-loader remains below this
			 * boundary until the full desktop mode graph is portable. */
			if (remote_smoke) {
				if (!GameInitMgrClass::Initialize_Direct_IP(remote_server)) { passed = false; break; }
			} else if (skirmish_smoke) GameInitMgrClass::Initialize_Skirmish();
			else GameInitMgrClass::Initialize_SP();
			single_player_transport_initialized = cSinglePlayerData::Is_Single_Player();
			Print(skirmish_smoke ? "original_gameinit_skirmish_initialized" : "original_gameinit_sp_initialized",
				single_player_transport_initialized && PTheGameData != NULL &&
				cGameType::Get_Game_Type() == (skirmish_smoke ? GAMETYPE_SKIRMISH : GAMETYPE_MISSION));
			if ((!remote_smoke && !single_player_transport_initialized) ||
				(remote_smoke && single_player_transport_initialized) || PTheGameData == NULL) {
				passed = false;
				break;
			}
			if (PTheGameData == NULL) { passed = false; break; }
			GameModeClass *combat_mode = GameModeManager::Find("Combat");
			if (combat_mode == NULL) { passed = false; break; }
			combat_mode->Activate();
			if (skirmish_smoke || remote_smoke) combat_mode->Suspend();
			StringClass map_name(level_mix, true);
			The_Game()->Set_Map_Name(map_name);
			if (remote_smoke) {
				The_Game()->Set_Ip_Address(htonl(remote_endpoint.Address));
				The_Game()->Set_Port(remote_port);
				// Original one-slot C&C games permit play without an opposing human.
				The_Game()->Set_Max_Players(1);
				The_Game()->Set_Map_Cycle(0, map_name);
			}
			_Force_Link_Soldier();
			// Own the local authoritative session through the original cNetwork
			// lifecycle.  This follows GameInitMgrClass::Start_Client_Server:
			// server first, then client, then service the original single-player
			// in-memory packet queues until the client has its negotiated ID.
			// Never manufacture connection pointers or player IDs for gameplay.
			Stage("network_onetime_init");
			cNetwork::Onetime_Init();
			Stage("network_server_init");
			if (!remote_client) cNetwork::Init_Server();
			Stage("network_client_init");
			if (tt_admission || tt_world || tt_client_request) Renegade_Arm_TT_Greeting_Probe();
			if (!remote_server) cNetwork::Init_Client();
			if (remote_client && !remote_join.Begin()) { passed = false; break; }
			if (remote_client) remote_join.Configure_Resources((std::string(argv[3]) + "/ttfs").c_str());
			PacketManager.Set_Is_Server(!remote_client);
			if (!remote_server && !Client_Connection_Present("after_init")) { passed = false; break; }
			session_initialized = true;
			if (remote_admission) {
				Print_Text("direct_admission_endpoint", argv[7]);
				passed = DirectClientProbe::Admission(remote_join, resource_fixture);
				break;
			}
			Stage("combat_scene_init");
			CombatManager::Scene_Init();
			if (!remote_server && !Client_Connection_Present("after_scene_init")) { passed = false; break; }
			/* Exercise the original Font3D asset route before Combat owns the HUD:
			 * FileFactory -> Targa -> CPU SurfaceClass -> TextureClass -> Vita edge. */
			Stage("font3d_render_capability");
			Font3DInstanceClass *large_font = asset_manager->Get_Font3DInstance("FONT12x16.TGA");
			Font3DInstanceClass *small_font = asset_manager->Get_Font3DInstance("FONT6x8.TGA");
			Print("font3d_large_available", large_font != NULL);
			Print("font3d_small_available", small_font != NULL);
			if (large_font == NULL || small_font == NULL) { passed = false; break; }
			const bool large_digits = Probe_Original_HUD_Digit_Atlas(large_font, "FONT12x16.TGA");
			const bool small_digits = Probe_Original_HUD_Digit_Atlas(small_font, "FONT6x8.TGA");
			Print("font3d_large_digits_match_source", large_digits);
			Print("font3d_small_digits_match_source", small_digits);
			REF_PTR_RELEASE(large_font);
			REF_PTR_RELEASE(small_font);
			if (!large_digits || !small_digits) { passed = false; break; }
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
			if (!remote_server && !Client_Connection_Present("after_combat_init")) { passed = false; break; }
			Stage("network_handshake");
			for (unsigned update_count = 0; !remote_server && update_count < (remote_client ? 30000U : 120U); ++update_count) {
				if (!Client_Connection_Present("before_update")) { passed = false; break; }
				if (remote_client && remote_join.Poll() == A31ClientConnect::WaitingResources)
					remote_join.Prepare_Resources();
				if (remote_client && remote_join.Poll() != A31ClientConnect::WaitingOptions &&
					remote_join.Poll() != A31ClientConnect::WaitingResources) break;
				if (cNetwork::PClientConnection->Is_Established() &&
					(!remote_client || remote_join.Poll() == A31ClientConnect::Ready)) break;
				cNetwork::Update();
				if (remote_client) { PacketManager.Flush(true); usleep(1000); }
				if (!Client_Connection_Present("after_update")) { passed = false; break; }
			}
			const bool transport_established = remote_server || (cNetwork::PClientConnection != NULL &&
				cNetwork::PClientConnection->Is_Established());
			Print("original_singleplayer_transport_established", transport_established);
			if (!transport_established) {
				passed = false;
				break;
			}
			if (remote_client) {
				if (tt_world) {
					char archive[96];
					if (remote_join.Poll() != A31ClientConnect::Ready ||
						!A4_Frontend_Resolve_Skirmish_Archive(The_Game()->Get_Map_Name(), archive, sizeof(archive))) {
						passed = false; break;
					}
					negotiated_map = archive;
					level_mix = negotiated_map.c_str();
					std::string retail_archive = std::string("Data\\") + negotiated_map;
					negotiated_factory.reset(new MixFileFactoryClass(retail_archive.c_str(), &root_factory));
					if (negotiated_factory->Is_Valid())
						factory_list.Add_FileFactory(negotiated_factory.get(), level_mix);
					else if (!A31ClientConnect::Is_Prepared_Map(level_mix)) { passed = false; break; }
					snprintf(level_ldd_name, sizeof(level_ldd_name), "%s", level_mix);
					strcpy(strrchr(level_ldd_name, '.'), ".ldd");
					Print_Text("remote_negotiated_world", level_mix);
				}
				A4_Frontend_Begin_Menu_Loop();
				bool start = remote_join.Request_Start(1, 0);
				A4_Frontend_End_Menu_Loop();
				if (!start || !remote_join.Begin_World_Load() ||
					stricmp(The_Game()->Get_Map_Name(), level_mix) != 0) { passed = false; break; }
				accepted_connection = cNetwork::PClientConnection;
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
			if (remote_smoke) CombatGameModeClass::Vita_Begin_Level_Load(nullptr, true);
			CombatManager::Pre_Load_Level(false);
			NetworkObjectMgrClass::Set_Is_Level_Loading(true);
			Stage("combat_load");
			CombatManager::Load_Level_Threaded(m13_save_replay ? "save\\savegame05.sav" :
				m01_save_replay ? "save\\savegame04.sav" : level_mix, false);
			while (!CombatManager::Is_Load_Level_Complete()) {
				if (remote_smoke) { cNetwork::Update(); usleep(1000); }
			}
			Stage("post_load_processing");
			SaveLoadSystemClass::Post_Load_Processing(remote_smoke ? &cNetwork::Update : NULL);
			NetworkObjectMgrClass::Set_Is_Level_Loading(false);
			Stage("combat_postload");
			CombatManager::Post_Load_Level();
			if (remote_smoke) {
				CombatGameModeClass::Vita_Finalize_Loaded_Level(nullptr, true);
				radar_initialized = true;
				combat_mode->Resume();
				level_loaded = true;
			}
			if (skirmish_smoke) {
				The_Game()->Reset_Game(true);
				GameObjManager::Init_Buildings();
				The_Game()->On_Game_Begin();
				combat_mode->Resume();
				Print("original_skirmish_game_started", IS_SKIRMISH);
			}
			if (strcmp(level_mix, "M13.mix") == 0) {
				ScriptableGameObj *controller =
					GameObjManager::Find_ScriptableGameObj(1500017);
				bool area4_script = false;
				if (controller != NULL) {
					const GameObjObserverList &observers = controller->Get_Observers();
					for (int index = 0; index < observers.Count(); ++index) {
						GameObjObserverClass *observer = observers[index];
						if (observer != NULL && observer->Get_Name() != NULL &&
							strcmp(observer->Get_Name(), "MX0_Area4_Controller_DLS") == 0) {
							area4_script = true;
						}
					}
				}
				Print("m13_area4_controller_script_registered", area4_script);
				if (!area4_script) { passed = false; break; }
			}
			if (strcmp(level_mix, "M00_Tutorial.mix") == 0) {
				StringClass map_name;
				MapMgrClass::Get_Map_Texture_Filename(map_name);
				TextureClass *map = asset_manager->Get_Texture(map_name, TextureClass::MIP_LEVELS_1);
				// Do not initialize here: the original map owner must already
				// have dimensions before Combat starts revealing explored cells.
				// The retail M00 map is 512x512. A positive-size check also
				// accepted the 2x2 diagnostic fallback after failed DDS parsing.
				const bool map_ready = map != NULL && map->Get_Width() == 512 && map->Get_Height() == 512;
				Print("eva_map_dimensions_ready_before_first_frame", map_ready);
				REF_PTR_RELEASE(map);
				if (!map_ready) { passed = false; break; }
			}
			level_loaded = CombatManager::Get_Scene() != NULL;
			A31_Interactive_Apply_Render_Capabilities();
			/* CombatGameModeClass owns radar creation after the original level
			 * post-load sequence.  This direct M00 development route retains that
			 * ownership ordering whenever the real render HUD is enabled; without
			 * it HUDClass::Think legitimately has no RadarManager renderer. */
			if (A31_Interactive_Render_HUD_Available() && !radar_initialized) {
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
			if (!DirectClientProbe::Weapon_Definition_Test()) { passed = false; break; }
			if (harvester_lifetime) {
				passed = DirectClientProbe::Harvester_Lifetime_Test() == 0;
				break;
			}
			if (remote_smoke) {
				if (remote_client && (accepted_connection != cNetwork::PClientConnection ||
					!cNetwork::I_Am_Only_Client() || cPlayerManager::Count() != 0 ||
					!remote_join.Complete_World_Load(1, 0))) { passed = false; break; }
				Print(remote_server ? "remote_server_ready" : "remote_client_world_loaded", true);
				const unsigned required_frames = tt_soak ? 3600U : 60U;
				const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(tt_soak ? 180 : 60);
				bool received_player = false;
				unsigned verified_frames = 0;
				RemotePurchaseProbe purchase_probe;
				while (std::chrono::steady_clock::now() < deadline) {
					A31_Interactive_Run_Simulation_Frame();
					if (remote_purchase) purchase_probe.Tick(remote_server);
					PacketManager.Flush(true);
					if (remote_client) {
						received_player = remote_join.Poll() == A31ClientConnect::InGame;
						if (received_player && ++verified_frames >= required_frames &&
							(!remote_purchase || purchase_probe.Passed())) break;
						if (remote_join.Poll() == A31ClientConnect::ConnectionLost ||
							remote_join.Poll() == A31ClientConnect::ProtocolMismatch) break;
					} else {
						cPlayer *player = cPlayerManager::Find_Player(L"PS Vita");
						if (player && player->Get_GameObj()) received_player = true;
						if (received_player && cPlayerManager::Count() == 0) break;
					}
					usleep(16000);
				}
				passed = received_player && (remote_server ? cPlayerManager::Count() == 0 :
					verified_frames >= required_frames) && (!remote_purchase || purchase_probe.Passed());
				if (remote_client) Print_Number("remote_verified_simulation_frames", verified_frames);
				if (remote_server) Print("remote_server_observed_disconnect", passed);
				Print(remote_server ? "remote_server_created_player" : "remote_client_replicated_star", passed);
				break;
			}
			WideStringClass local_player_name;
			local_player_name.Convert_From(skirmish_smoke ? "PS Vita" : "Renegade");
			Stage("player_create");
			cPlayer *local_player = cGod::Create_Player(cNetwork::Get_My_Id(),
				local_player_name, skirmish_smoke ? 1 : -1, 0);
			Print("original_session_player_created", local_player != NULL);
			Print("original_session_player_registered", cPlayerManager::Count() == 1);
			const bool eva_player_ready = local_player != NULL &&
				cNetwork::Get_My_Player_Object() == local_player;
			Print("eva_statistics_original_player_available", eva_player_ready);
			if (!eva_player_ready) { passed = false; break; }
			Stage("god_think");
			cGod::Think();
			Print("original_god_created_commando", CombatManager::Get_The_Star() != NULL);
			if (m01_intro_smoke) {
				HumanPhysClass *phys = CombatManager::Get_The_Star() != NULL ?
					CombatManager::Get_The_Star()->Peek_Human_Phys() : NULL;
				Vector3 before, after;
				if (phys != NULL) {
					phys->Get_Velocity(&before);
					phys->Jump_To_Point(phys->Get_Transform().Get_Translation());
					phys->Get_Velocity(&after);
				}
				const bool finite_jump = phys != NULL &&
					WWMath::Is_Valid_Float(after.X) && WWMath::Is_Valid_Float(after.Y) &&
					WWMath::Is_Valid_Float(after.Z) &&
					before.X == after.X && before.Y == after.Y && before.Z == after.Z;
				Print("m01_zero_distance_jump_preserves_velocity", finite_jump);
				if (!finite_jump) { passed = false; break; }
			}
			if (tt_soldier_smoke || tt_vehicle_smoke) {
				A31_Interactive_Run_Simulation_Frame();
				passed = CombatManager::Get_The_Star() &&
					(tt_vehicle_smoke ? Validate_TT_Vehicle_Runtime(CombatManager::Get_The_Star()->Get_Definition()) :
					Validate_TT_Soldier_Runtime(CombatManager::Get_The_Star()->Get_Definition()));
                if (tt_soldier_smoke) passed = Validate_TT_C4_Runtime(*CombatManager::Get_The_Star()) && passed;
				break;
			}
			if (purchase_smoke) {
				A31_Interactive_Run_Simulation_Frame();
				passed = Validate_Original_Purchases();
				break;
			}
			const bool starting_weapon_revealed = EncyclopediaMgrClass::Is_Object_Revealed(
				EncyclopediaMgrClass::TYPE_WEAPON, 14);
			Print("fresh_m00_original_script_weapon_discovery", starting_weapon_revealed);
			if (strcmp(level_mix, "M00_Tutorial.mix") == 0 && !starting_weapon_revealed) {
				passed = false; break;
			}

			Stage("hardware_equivalent_120_frame_loop");
			M13CinematicProbe cinematic_probe;
			const unsigned target_frames = m13_intro_smoke ? 5000U :
				m13_save_replay ? 600U :
				m01_save_replay ? 1800U :
				m01_intro_smoke ? 1800U : 120U;
			/* Make each cycle's first-frame geometry a per-cycle measurement,
			** matching the Vita adapter's reset immediately before its loop. */
			RenegadeVitaRenderer::Reset_Statistics();
			unsigned complete_frames = 0;
			bool first_frame_geometry = false;
			for (; complete_frames < target_frames; ++complete_frames) {
#if defined(RENEGADE_A35_ORIGINAL_WWAUDIO)
				HostAudioClockMilliseconds += HostReplayFrameMilliseconds;
#endif
				if (!m13_inventory && !m13_intro_smoke && !m01_intro_smoke)
					WW3D::Sync((complete_frames + 1U) * HostReplayFrameMilliseconds);
				A31_Interactive_Run_Simulation_Frame();
#if defined(RENEGADE_A35_ORIGINAL_WWAUDIO)
				audio.On_Frame_Update(HostReplayFrameMilliseconds);
				bool mixed = true;
				// Match the provider's bounded output blocks, including long replay steps.
				for (size_t offset = 0; offset < audio_mix.size() / 2U; ) {
					const size_t frames = std::min<size_t>(1024U, audio_mix.size() / 2U - offset);
					if (!Renegade_Miles_Mix_For_Test(audio_mix.data() + offset * 2U, frames)) {
						mixed = false;
						break;
					}
					offset += frames;
				}
				if (!mixed) {
					Print("host_original_audio_mix", false);
					passed = false;
					break;
				}
#endif
				if (m13_save_replay || m13_intro_smoke || m01_save_replay || m01_intro_smoke) {
					unsigned checked = 0;
					for (SLNode<BaseGameObj> *node = GameObjManager::Get_Game_Obj_List()->Head();
						node != NULL; node = node->Next()) {
						PhysicalGameObj *object = node->Data()->As_PhysicalGameObj();
						PhysClass *phys = object != NULL ? object->Peek_Physical_Object() : NULL;
						if (phys == NULL) continue;
						const Matrix3D &transform = phys->Get_Transform();
						Vector3 velocity(0.0f, 0.0f, 0.0f);
						MoveablePhysClass *moving = phys->As_MoveablePhysClass();
						if (moving != NULL) moving->Get_Velocity(&velocity);
						bool valid = velocity.Is_Valid();
						for (int row = 0; row < 3; ++row)
							for (int column = 0; column < 4; ++column)
								valid = valid && WWMath::Is_Valid_Float(transform[row][column]);
						if (!valid) {
							printf("a31.invalid_mission_physics map=%s frame=%u id=%d preset=%s\n",
								level_mix, complete_frames + 1U, object->Get_ID(), object->Get_Definition().Get_Name());
							passed = false;
							break;
						}
						++checked;
					}
					if (!passed) break;
					if (complete_frames + 1U == target_frames)
						printf("a31.mission_physics_finite map=%s frames=%u final_objects=%u\n",
							level_mix, target_frames, checked);
				}
				if (m13_save_replay) {
					for (int id : {1500000055, 1500000059}) {
						ScriptableGameObj *obj = GameObjManager::Find_ScriptableGameObj(id);
						SoldierGameObj *soldier = obj != NULL ? obj->As_SoldierGameObj() : NULL;
						if (soldier == NULL || soldier->Peek_Human_Phys() == NULL) {
							printf("a31.m13_missing_engineer frame=%u id=%d\n", complete_frames + 1U, id);
							passed = false;
							break;
						}
						HumanPhysClass *phys = soldier->Peek_Human_Phys();
						Vector3 velocity;
						phys->Get_Velocity(&velocity);
						const Vector3 position = phys->Get_Position();
						if (!position.Is_Valid() || !velocity.Is_Valid()) {
							printf("a31.m13_first_invalid_engineer frame=%u id=%d pos=%.6f,%.6f,%.6f vel=%.6f,%.6f,%.6f\n",
								complete_frames + 1U, id, position.X, position.Y, position.Z,
								velocity.X, velocity.Y, velocity.Z);
							passed = false;
							break;
						}
						if (complete_frames + 1U == target_frames)
							printf("a31.m13_engineer_final id=%d pos=%.6f,%.6f,%.6f vel=%.6f,%.6f,%.6f\n",
								id, position.X, position.Y, position.Z,
								velocity.X, velocity.Y, velocity.Z);
					}
					if (!passed) break;
				}
				const A31InteractiveRenderTrace render_trace =
					A31_Interactive_Run_Render_Frame();
				if (m13_intro_smoke) cinematic_probe.Observe(complete_frames);
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
#if defined(RENEGADE_A35_ORIGINAL_WWAUDIO)
			RenegadeMilesRuntimeStats audio_stats = {};
			Renegade_Miles_Get_Runtime_Stats(&audio_stats);
			printf("a31.host_audio starts=%u mixed_nonzero=%llu decode_failures=%u active_samples=%u manual_clock=%d\n",
				audio_stats.sample_start_successes,
				static_cast<unsigned long long>(audio_stats.mixed_nonzero_buffers),
				audio_stats.sample_file_load_failures + audio_stats.sample_3d_file_load_failures,
				audio_stats.active_samples, HostFixedSimulationClock ? 1 : 0);
			if (m13_intro_smoke || m13_save_replay || m01_intro_smoke || m01_save_replay)
				passed = passed && audio_stats.sample_start_successes > 0 && audio_stats.mixed_nonzero_buffers > 0;
#endif
			Print("hardware_equivalent_render_frame", complete_frames == target_frames);
			Print("interactive_first_frame_geometry", first_frame_geometry);
			passed = passed && complete_frames == target_frames && first_frame_geometry &&
				CombatManager::Get_Scene() != NULL &&
				CombatManager::Get_Camera() != NULL &&
				CombatManager::Get_The_Star() != NULL;
			if (m13_intro_smoke) {
				const bool intro_passed = cinematic_probe.Validate();
				Print("m13_intro_scripted_actor_contract", intro_passed);
				passed = passed && intro_passed;
			}
			if (passed && m13_inventory) {
				Dump_M13_Linked_Scripts();
				Dump_M13_Runtime_Inventory();
				const bool presets_ready = Dump_M13_Cinematic_Preset_Definitions();
				const bool w3d_ready = Dump_M13_W3D_Dependencies(m00_factory);
				passed = presets_ready && w3d_ready;
			}
			if (passed && m13_sam_damage_smoke) {
				if (m13_sam_prewarm_smoke) {
					struct WorldExplosionUse { int id; unsigned count; } uses[64] = {};
					unsigned use_count = 0;
					for (SLNode<BaseGameObj> *node =
						GameObjManager::Get_Game_Obj_List()->Head(); node != NULL;
						node = node->Next()) {
						PhysicalGameObj *physical =
							node->Data()->As_PhysicalGameObj();
						if (physical == NULL) continue;
						const int id = physical->Get_Definition().Get_Killed_Explosion_ID();
						if (id <= 0) continue;
						unsigned index = 0;
						for (; index < use_count && uses[index].id != id; ++index) {}
						if (index == use_count) {
							if (use_count == 64U) { passed = false; break; }
							uses[use_count++] = {id, 0U};
							DefinitionClass *explosion =
								DefinitionMgrClass::Find_Definition(id, false);
							printf("a31.m13_world_explosion_id=%d preset=%s explosion=%s\n",
								id, physical->Get_Definition().Get_Name(),
								explosion != NULL ? explosion->Get_Name() : "(missing)");
						}
						++uses[index].count;
					}
					printf("a31.m13_world_explosion_unique=%u\n", use_count);
					for (unsigned index = 0; index < use_count; ++index) {
						printf("a31.m13_world_explosion_count_id=%d count=%u\n",
							uses[index].id, uses[index].count);
						DefinitionClass *definition = DefinitionMgrClass::Find_Definition(
							uses[index].id, false);
						const bool ready = Prepare_Explosion_Choice_For_Smoke(
							definition, definition != NULL ? definition->Get_Name() :
								"(missing)", 0U);
						printf("a31.m13_world_explosion_ready_id=%d ready=%d\n",
							uses[index].id, ready ? 1 : 0);
						if (!ready) passed = false;
					}
					const char *const names[] = {
						"Explosion_SAM_Site",
						"Rocket Launcher Explosion Twiddler",
						"Ground Explosions Twiddler",
						"Air Explosions Twiddler"
					};
					bool all_prepared = true;
					for (const char *name : names) {
						if (!Prepare_Explosion_Choice_For_Smoke(
							DefinitionMgrClass::Find_Named_Definition(name, false),
							name, 0U)) all_prepared = false;
					}
					passed = passed && all_prepared;
					const char *const intro_models[] = {
						"X00_MTank_traj", "X00_Humvee_Traj", "X00_apc_Traj",
						"X00_GDI_Troops", "X00_Havoc_Traj", "X00_Trnspt_traj",
						"X00_Rope", "X00_Ltank_traj", "X00_NOD_Troops",
						"X00_Scorpion", "X00_ROC2_traj", "X00_ENG1_traj",
						"X00_ENG2_traj"
					};
					for (const char *name : intro_models) {
						RenderObjClass *object = WW3DAssetManager::Get_Instance()->Create_Render_Obj(name);
						printf("a31.m13_intro_model=%s ready=%d\n", name, object != NULL ? 1 : 0);
						if (object != NULL) object->Release_Ref();
						else passed = false;
					}
					const char *const intro_animations[] = {
						"X00_MTank_traj.X00_MTank_traj",
						"v_gdi_medtnk.x00_Mtank_anim",
						"X00_Humvee_Traj.X00_Humvee_Traj",
						"X00_apc_Traj.X00_apc_Traj",
						"X00_GDI_Troops.X00_GDI_Troops",
						"S_A_Human.H_A_x00_walk_01",
						"S_A_Human.H_A_X00_WALK_04",
						"S_A_Human.H_A_X00_Walk_02",
						"X00_Havoc_Traj.X00_Havoc_Traj",
						"S_A_Human.H_A_X00_Havoc",
						"X00_Trnspt_traj.X00_Trnspt_traj",
						"V_GDI_Trnspt.X00_Trnspt_anim",
						"X00_Rope.X00_Rope",
						"X00_Ltank_traj.X00_Ltank_traj",
						"V_Nod_Ltank.X00_Ltank_Anim",
						"X00_NOD_Troops.X00_NOD_Troops",
						"X00_Scorpion.X00_Scorpion",
						"X00_ROC2_traj.X00_ROC2_traj",
						"S_A_Human.H_A_X00_ROC2",
						"X00_ENG1_traj.X00_ENG1_traj",
						"S_A_Human.H_A_X00_ENG1",
						"X00_ENG2_traj.X00_ENG2_traj",
						"S_A_Human.H_A_X00_ENG2"
					};
					for (const char *name : intro_animations) {
						HAnimClass *animation = WW3DAssetManager::Get_Instance()->Get_HAnim(name);
						const int frames = animation != NULL ? animation->Get_Num_Frames() : 0;
						printf("a31.m13_intro_animation=%s frames=%d\n", name, frames);
						if (animation != NULL) animation->Release_Ref();
						if (frames <= 0) passed = false;
					}
					struct IntroAttachment {
						const char *model;
						const char *bone;
					};
					const IntroAttachment attachments[] = {
						{"X00_Havoc_Traj", "BN_Havoc"},
						{"X00_ENG1_traj", "BN_ENGINEER_1"},
						{"X00_ENG2_traj", "BN_ENGINEER_2"}
					};
					for (const IntroAttachment &attachment : attachments) {
						RenderObjClass *object = WW3DAssetManager::Get_Instance()->Create_Render_Obj(attachment.model);
						const int bone = object != NULL ? object->Get_Bone_Index(attachment.bone) : -1;
						printf("a31.m13_intro_attachment=%s bone=%s index=%d\n",
							attachment.model, attachment.bone, bone);
						if (object != NULL) object->Release_Ref();
						if (bone < 0) passed = false;
					}
					RenderObjClass *trajectory = WW3DAssetManager::Get_Instance()->Create_Render_Obj("X00_Havoc_Traj");
					HAnimClass *rappel = WW3DAssetManager::Get_Instance()->Get_HAnim("X00_Havoc_Traj.X00_Havoc_Traj");
					if (trajectory != NULL && rappel != NULL) {
						trajectory->Set_Animation(rappel, 0.0f);
						const Vector3 start = trajectory->Get_Bone_Transform("BN_Havoc").Get_Translation();
						trajectory->Set_Animation(rappel, 200.0f);
						const Vector3 end = trajectory->Get_Bone_Transform("BN_Havoc").Get_Translation();
						const float movement = (end - start).Length();
						printf("a31.m13_havoc_rappel_bone_movement=%.3f start_z=%.3f end_z=%.3f\n",
							movement, start.Z, end.Z);
						if (movement <= 0.1f) passed = false;
					} else {
						passed = false;
					}
					if (rappel != NULL) rappel->Release_Ref();
					if (trajectory != NULL) trajectory->Release_Ref();
				}
				if (!passed) break;
				const WarheadType steel = ArmorWarheadManager::Get_Warhead_Type("STEEL");
				for (int sam_id = 1500015; sam_id <= 1500016; ++sam_id) {
					ScriptableGameObj *object =
						GameObjManager::Find_ScriptableGameObj(sam_id);
					DamageableGameObj *sam = object != NULL ?
						object->As_DamageableGameObj() : NULL;
					if (sam == NULL) { passed = false; break; }
					printf("a31.m13_sam_damage_smoke_id=%d health_before=%.1f\n",
						sam_id, sam->Get_Defense_Object()->Get_Health());
					fflush(stdout);
					// Retail SAM bindings exempt player damage but protect against
					// unattributed/non-player damage until the controller disables
					// their modifier. Exercise the player destruction path here.
					SoldierGameObj *attacker = CombatManager::Get_The_Star();
					if (attacker == NULL) { passed = false; break; }
					OffenseObjectClass damage(50000.0f, steel, attacker);
					const bool profile_sam = cycle == 1U && sam_id ==
						(m13_sam_prewarm_smoke ? 1500015 : 1500016);
					if (profile_sam) {
						CALLGRIND_ZERO_STATS;
						CALLGRIND_START_INSTRUMENTATION;
					}
					const auto damage_start = std::chrono::steady_clock::now();
					sam->Apply_Damage(damage);
					const auto damage_end = std::chrono::steady_clock::now();
					if (profile_sam) {
						CALLGRIND_STOP_INSTRUMENTATION;
						CALLGRIND_DUMP_STATS_AT(m13_sam_prewarm_smoke ?
							"m13_first_sam_damage" : "m13_second_sam_damage");
					}
					printf("a31.m13_sam_damage_us_id=%d elapsed=%lld\n", sam_id,
						static_cast<long long>(std::chrono::duration_cast<
							std::chrono::microseconds>(damage_end - damage_start).count()));
					fflush(stdout);
					for (unsigned settle = 0U; settle < 2U; ++settle) {
						A31_Interactive_Run_Simulation_Frame();
						A31_Interactive_Run_Render_Frame();
					}
					object = GameObjManager::Find_ScriptableGameObj(sam_id);
					sam = object != NULL ? object->As_DamageableGameObj() : NULL;
					float remaining_health = sam != NULL ?
						sam->Get_Defense_Object()->Get_Health() : 0.0f;
					// The second retail SAM scales player damage to 10 percent
					// and accumulates damage across callbacks. One lethal offense
					// therefore does not destroy it. Keep a bounded player route
					// through those callbacks rather than bypassing the modifier.
					unsigned hits = 1U;
					while (remaining_health > 0.0f && hits < 16U) {
						sam->Apply_Damage(damage);
						++hits;
						for (unsigned settle = 0U; settle < 2U; ++settle) {
							A31_Interactive_Run_Simulation_Frame();
							A31_Interactive_Run_Render_Frame();
						}
						object = GameObjManager::Find_ScriptableGameObj(sam_id);
						sam = object != NULL ? object->As_DamageableGameObj() : NULL;
						remaining_health = sam != NULL ?
							sam->Get_Defense_Object()->Get_Health() : 0.0f;
					}
					printf("a31.m13_sam_damage_smoke_id=%d player_hits=%u\n", sam_id, hits);
					printf("a31.m13_sam_damage_smoke_id=%d health_after=%.1f\n",
						sam_id, remaining_health);
					if (remaining_health > 0.0f) { passed = false; break; }
				}
				Print("m13_sam_damage_smoke_completed", passed);
			}
		} while (false);

		Print("factory_chain_ready", always2_factory.Is_Valid() &&
			always_dbs_factory.Is_Valid() && always_factory.Is_Valid() &&
			m00_factory.Is_Valid());
		Print("combat_scene_owned", CombatManager::Get_Scene() != NULL);
		Print("original_camera_owned", CombatManager::Get_Camera() != NULL);
		Print("original_star_restored", CombatManager::Get_The_Star() != NULL);
		if (!remote_admission) Print("one_original_control_think_frame", passed);

			if (passed && combat_initialized) {
				Stage("original_native_settings");
				if (stylemgr_initialized) StyleMgrClass::Shutdown();
				stylemgr_initialized = false;
				const bool settings_valid = Validate_Original_Native_Settings();
				Print("original_settings_volume_and_unchanged_budgets", settings_valid);
				passed = passed && settings_valid;
			}
			Stage("teardown");
			/* Preserve the original Core_Shutdown dependency order for the direct
			 * M00 route: stop player respawn, free level-owned objects/assets, then
			 * release radar before Combat's process-level state. */
			if (level_loaded) {
				cGod::Exit();
				if (skirmish_smoke || remote_smoke) The_Game()->On_Game_End();
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
					EncyclopediaMgrClass::Shutdown();
					Print("campaign_catalog_shutdown",
						CampaignFlowDescriptions.Count() == 0);
				}
				if (translatedb_initialized) {
					if (global_conversations_initialized && !combat_initialized) {
						ConversationMgrClass::Shutdown();
					}
					global_conversations_initialized = false;
					TranslateDBClass::Shutdown();
					translatedb_initialized = false;
				}
		if (session_initialized) {
			/* GameInitMgr owns the matching SP data/transport shutdown.  Network
			 * one-time shutdown remains at the outer application lifecycle, as in
			 * the original shutdown ordering. */
			GameInitMgrClass::Shutdown();
			cNetwork::Onetime_Shutdown();
		}
		if (session_initialized && cServerFps::Get_Instance()) cServerFps::Destroy_Instance();
		if (input_initialized) Input::Shutdown();
	}

#if defined(RENEGADE_A35_ORIGINAL_WWAUDIO)
	RenegadeMilesRuntimeStats teardown_audio = {};
	Renegade_Miles_Get_Runtime_Stats(&teardown_audio);
	const bool audio_released = teardown_audio.allocated_samples == 0 && teardown_audio.active_streams == 0;
	Print("host_original_audio_handles_released", audio_released);
	passed = passed && audio_released;
#endif
	if (asset_manager != NULL) WW3DAssetManager::Delete_This();
	if (path_manager_initialized) PathMgrClass::Shutdown();
	if (math_initialized) WWMath::Shutdown();
	if (wwsaveload_initialized) WWSaveLoad::Shutdown();
	if (ww3d_initialized) WW3D::Shutdown();
	if (wwphys_initialized) WWPhys::Shutdown();
	_TheFileFactory = previous_read_factory;
	_TheWritingFileFactory = previous_write_factory;

	if (remote_smoke) {
		printf("A3.1 original remote %s: %s\n", remote_admission ? "admission probe (not gameplay)" :
			remote_server ? "server runtime" : "client runtime", passed ? "PASS" : "FAIL");
		return passed ? 0 : 1;
	}
	if (passed && cycle < 2U) {
		Stage("start_equivalent_exit_and_second_cycle");
		return main(argc, argv);
	}
	printf("A3.1 original %s interactive runtime: %s (two in-process cycles)\n",
		level_mix, passed && cycle == 2U ? "PASS" : "FAIL");
	return passed && cycle == 2U ? 0 : 1;
}
