// Vita lifecycle edges reached by original frontend owners.
//
// The native runtime, rather than Commando's Win32 `mainloop.cpp`, owns the
// process loop. Keep the shared functions below at that one boundary so menu
// controls do not pull a second desktop message loop into the port.

#include "IMEManager.h"
#include "dx8renderer.h"
#include "dialogtests.h"
#include "renegadedialogmgr.h"
#include "resource.h"
#include "consolefunction.h"
#include "init.h"
#include "movie.h"
#include "scorescreen.h"
#include "systemsettings.h"
#include "textureloader.h"

namespace {

bool g_frontend_exit_requested = false;
int g_frontend_exit_code = 0;

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
	g_frontend_exit_requested = true;
	g_frontend_exit_code = exit_code;
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
void MovieGameModeClass::Start_Movie(const char *) {}
void SystemSettings::Apply_All(void) {}

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
