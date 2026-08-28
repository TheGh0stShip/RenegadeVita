// Vita lifecycle edges reached by original frontend owners.
//
// The native runtime, rather than Commando's Win32 `mainloop.cpp`, owns the
// process loop. Keep the shared functions below at that one boundary so menu
// controls do not pull a second desktop message loop into the port.

#include "a4_frontend_lifecycle_boundary.h"

#include "IMEManager.h"
#include "dx8renderer.h"
#include "dialogmgr.h"
#include "dialogtests.h"
#include "renegadedialogmgr.h"
#include "resource.h"
#include "consolefunction.h"
#include "init.h"
#include "movie.h"
#include "scorescreen.h"
#include "systemsettings.h"
#include "textureloader.h"
#include "wwuiinput.h"

#include <string.h>

namespace {

A4FrontendTrace g_frontend_trace = {};
bool g_frontend_previous_keys[256] = {};

class A4FrontendKeyDispatchInput final : public WWUIInputClass
{
public:
	A4FrontendKeyDispatchInput() : MousePosition(0, 0, 0) {}
	const Vector3 &Get_Mouse_Pos(void) const override { return MousePosition; }
	void Set_Mouse_Pos(const Vector3 &pos) override { MousePosition = pos; }
	bool Is_Button_Down(int) override { return false; }

private:
	Vector3 MousePosition;
};

A4FrontendKeyDispatchInput g_frontend_key_dispatcher;

void Copy_Text(char *dest, unsigned dest_size, const char *source)
{
	if (dest == NULL || dest_size == 0U) return;
	if (source == NULL) source = "";
	::strncpy(dest, source, dest_size - 1U);
	dest[dest_size - 1U] = '\0';
}

bool Is_Pressed_Key(int virtual_key)
{
	return virtual_key >= 0 && virtual_key < 256 &&
		(RenegadeVitaWWUIKeyState[virtual_key] & 0x80U) != 0U;
}

void Dispatch_Key_Message(UINT message, int virtual_key)
{
	LRESULT result = 0;
	g_frontend_key_dispatcher.ProcessMessage(NULL, message,
		static_cast<WPARAM>(virtual_key), 0, result);
}

} // namespace

namespace IME {

void IMEManager::Activate(void) {}
void IMEManager::Deactivate(void) {}
void IMEManager::Disable(void) {}
void IMEManager::Enable(void) {}
void IMEManager::GetTargetClause(unsigned long &start, unsigned long &end)
{
	start = 0;
	end = 0;
}

} // namespace IME

// Native WW3D owns mesh submission. This compatibility object supplies the
// one GameInitMgr invalidation call without constructing a Direct3D renderer.
DX8MeshRendererClass TheDX8MeshRenderer;

DX8MeshRendererClass::DX8MeshRendererClass() {}
DX8MeshRendererClass::~DX8MeshRendererClass() {}
void DX8MeshRendererClass::Invalidate() {}

void Get_Version_Number(unsigned long *major, unsigned long *minor)
{
	// The released source intentionally removed public version metadata.
	if (major != NULL) *major = 0;
	if (minor != NULL) *minor = 0;
}

void Stop_Main_Loop(int exit_code)
{
	// The Vita host loop consumes this request when it owns menu presentation.
	g_frontend_trace.exit_requested = true;
	g_frontend_trace.exit_code = exit_code;
}

// Vita has no Win32 message queue. CombatGameMode calls this while synchronously
// loading; retaining the call boundary keeps its original load ordering intact.
void Windows_Message_Handler(void) {}

// Full developer-console parsing and the score/movie presenters depend on
// desktop-only UI/media owners. These are explicit temporary single-player
// adapters; campaign difficulty is already applied by CombatManager before
// Parse_Input is reached, and Bink skip behavior remains logged by its boundary.
void ConsoleFunctionManager::Parse_Input(const char *) {}
void ScoreScreenGameModeClass::Save_Stats(void) {}
#if !defined(RENEGADE_A4_ORIGINAL_MOVIE_OWNER)
void MovieGameModeClass::Start_Movie(const char *) {}
#endif
void SystemSettings::Apply_All(void) {}

bool CDVerifyClass::Get_CD_Path(StringClass &drive_path)
{
	drive_path = "";
	return false;
}

void CDVerifyClass::Display_UI(Observer<CDVerifyEvent> *observer)
{
	if (observer == NULL) return;
	AddObserver(*observer);
	CDVerifyEvent event(CDVerifyEvent::NOT_VERIFIED, this);
	NotifyObservers(event);
}

// The current Vita renderer performs texture decoding/upload synchronously at
// its DX8 boundary. Keep the original loader's scheduling contract explicit:
// these calls must not create a second desktop D3DX worker/queue.
bool TextureLoader::TextureLoadSuspended = false;
void TextureLoader::Init(void) {}
void TextureLoader::Deinit(void) {}
void TextureLoader::Validate_Texture_Size(unsigned &, unsigned &) {}
IDirect3DTexture8 *TextureLoader::Load_Thumbnail(const StringClass &) { return NULL; }
IDirect3DSurface8 *TextureLoader::Load_Surface_Immediate(const StringClass &, WW3DFormat, bool)
{
	return NULL;
}
void TextureLoader::Request_Thumbnail(TextureClass *) {}
void TextureLoader::Request_Background_Loading(TextureClass *) {}
void TextureLoader::Request_Foreground_Loading(TextureClass *) {}
void TextureLoader::Flush_Pending_Load_Tasks(void) {}
void TextureLoader::Update(void (*network_callback)(void))
{
	if (network_callback != NULL) network_callback();
}
bool TextureLoader::Is_DX8_Thread(void) { return true; }
void TextureLoader::Suspend_Texture_Load(void) { TextureLoadSuspended = true; }
void TextureLoader::Continue_Texture_Load(void) { TextureLoadSuspended = false; }

// The native bootstrap owns the rooted retail-data factories. This distinct
// original global is required only for optional MOD-package enumeration.
SimpleFileFactoryClass RenegadeBaseFileFactory;

// The desktop splash presenters are intentionally outside the Vita's
// single-player startup route.  Keep the original dialog types and factory
// ABI, but transition immediately into the genuine main-menu dialog instead
// of playing a Windows-era splash/video presentation.
SplashIntroMenuDialogClass::SplashIntroMenuDialogClass()
	: Timer(0.0F), MenuDialogClass(IDD_MENU_SPLASH1)
{
}

SplashIntroMenuDialogClass::~SplashIntroMenuDialogClass() = default;

void SplashIntroMenuDialogClass::On_Init_Dialog()
{
	MenuDialogClass::On_Init_Dialog();
	RenegadeDialogMgrClass::Goto_Location(RenegadeDialogMgrClass::LOC_MAIN_MENU);
	End_Dialog();
}

void SplashIntroMenuDialogClass::On_Frame_Update() {}
void SplashIntroMenuDialogClass::On_Command(int, int, DWORD) {}

SplashOutroMenuDialogClass::SplashOutroMenuDialogClass()
	: Timer(0.0F), MenuDialogClass(IDD_MENU_SPLASH2)
{
}

SplashOutroMenuDialogClass::~SplashOutroMenuDialogClass() = default;

void SplashOutroMenuDialogClass::On_Init_Dialog()
{
	MenuDialogClass::On_Init_Dialog();
	Stop_Main_Loop(0);
	End_Dialog();
}

void SplashOutroMenuDialogClass::On_Frame_Update() {}
void SplashOutroMenuDialogClass::On_Command(int, int, DWORD) {}

void A4_Frontend_Reset_Trace(void)
{
	::memset(&g_frontend_trace, 0, sizeof(g_frontend_trace));
	::memset(g_frontend_previous_keys, 0, sizeof(g_frontend_previous_keys));
}

void A4_Frontend_Begin_Menu_Loop(void)
{
	g_frontend_trace.menu_loop_active = true;
	g_frontend_trace.exit_requested = false;
	g_frontend_trace.exit_code = 0;
	g_frontend_trace.tutorial_start_latched = false;
	g_frontend_trace.tutorial_map[0] = '\0';
	g_frontend_trace.tutorial_team_choice = 0;
	g_frontend_trace.tutorial_clan_id = 0;
	::memset(g_frontend_previous_keys, 0, sizeof(g_frontend_previous_keys));
}

void A4_Frontend_End_Menu_Loop(void)
{
	g_frontend_trace.menu_loop_active = false;
	::memset(g_frontend_previous_keys, 0, sizeof(g_frontend_previous_keys));
}

bool A4_Frontend_Is_Menu_Loop_Active(void)
{
	return g_frontend_trace.menu_loop_active;
}

bool A4_Frontend_Exit_Requested(void)
{
	return g_frontend_trace.exit_requested;
}

int A4_Frontend_Exit_Code(void)
{
	return g_frontend_trace.exit_code;
}

bool A4_Frontend_Latch_Start_Game(const char *map_name, int teamChoice,
	unsigned long clanID)
{
	if (!g_frontend_trace.menu_loop_active || map_name == NULL) return false;
	g_frontend_trace.tutorial_start_latched = true;
	Copy_Text(g_frontend_trace.tutorial_map,
		sizeof(g_frontend_trace.tutorial_map), map_name);
	g_frontend_trace.tutorial_team_choice = teamChoice;
	g_frontend_trace.tutorial_clan_id = clanID;
	return true;
}

A4FrontendTrace A4_Frontend_Get_Trace(void)
{
	return g_frontend_trace;
}

void A4_Frontend_Record_Bink_Init(bool initialized)
{
	g_frontend_trace.bink_initialized = initialized;
}

void A4_Frontend_Record_Bink_Play(const char *filename)
{
	++g_frontend_trace.movie_play_requests;
	Copy_Text(g_frontend_trace.last_movie, sizeof(g_frontend_trace.last_movie),
		filename);
}

void A4_Frontend_Record_Bink_Skip(const char *filename)
{
	++g_frontend_trace.movie_skip_requests;
	Copy_Text(g_frontend_trace.last_movie, sizeof(g_frontend_trace.last_movie),
		filename);
}

void A4_Frontend_Pump_WWUI_Key_Transitions(void)
{
	static const int keys[] = {
		VK_UP, VK_DOWN, VK_LEFT, VK_RIGHT, VK_RETURN, VK_SPACE,
		VK_ESCAPE, VK_TAB
	};

	for (unsigned index = 0U; index < sizeof(keys) / sizeof(keys[0]); ++index) {
		const int key = keys[index];
		const bool pressed = Is_Pressed_Key(key);
		if (pressed && !g_frontend_previous_keys[key]) {
			Dispatch_Key_Message(WM_KEYDOWN, key);
		} else if (!pressed && g_frontend_previous_keys[key]) {
			Dispatch_Key_Message(WM_KEYUP, key);
		}
		g_frontend_previous_keys[key] = pressed;
	}
}

void A4_Frontend_Set_Test_WWUI_Key_State(int virtual_key, bool pressed)
{
	if (virtual_key < 0 || virtual_key >= 256) return;
	RenegadeVitaWWUIKeyState[virtual_key] = pressed ? 0x80U : 0U;
}
