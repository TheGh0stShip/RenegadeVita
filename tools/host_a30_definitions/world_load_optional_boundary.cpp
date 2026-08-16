// Target-scoped boundary for code retained by complete Door/Elevator vtables
// but not entered by the original static M00 SaveLoad path.
//
// The world harness deliberately has no gameplay update, audio device,
// networking, or render submission. Pulling the full implementations of these
// methods would expand a static-world loader into unrelated player/network/
// middleware systems. Callable operations therefore fail loudly. The few
// process globals use the same neutral pre-Combat initialization values as the
// original definitions.

#include "combat.h"
#include "diaglog.h"
#include "dx8wrapper.h"
#include "gameobjmanager.h"
#include "smartgameobj.h"
#include "vehicle.h"
#include "WWAudio.h"

#include <stdio.h>
#include <stdlib.h>

namespace {

[[noreturn]] void Unsupported_World_Load_Call(const char *operation)
{
	fprintf(stderr,
		"A3.0 static-world host boundary entered unexpectedly: %s\n",
		operation);
	fflush(stderr);
	abort();
}

} // namespace

// Original CombatManager/GameObjManager definitions live in high-fanout game
// runtime TUs. Static-world loading only needs their canonical empty state.
bool CombatManager::IAmServer = false;
GameObjReference CombatManager::TheStar;
SList<SoldierGameObj> GameObjManager::StarGameObjList;

void DiagLogClass::Log_Timed(const char *, const char *, ...)
{
	Unsupported_World_Load_Call("DiagLogClass::Log_Timed");
}

bool SmartGameObj::Is_Human_Controlled()
{
	Unsupported_World_Load_Call("SmartGameObj::Is_Human_Controlled");
}

SoldierGameObj *VehicleGameObj::Get_Driver()
{
	Unsupported_World_Load_Call("VehicleGameObj::Get_Driver");
}

// No WWAudio instance exists in this no-audio host process. If a retained
// update/effect method tries to cross the audio edge, its method body reports
// the exact unexpected operation before terminating.
WWAudioClass *WWAudioClass::_theInstance = NULL;

int WWAudioClass::Create_Instant_Sound(int, const Matrix3D &, RefCountClass *,
	uint32, int)
{
	Unsupported_World_Load_Call("WWAudioClass::Create_Instant_Sound");
}

AudibleSoundClass *WWAudioClass::Create_Continuous_Sound(int,
	RefCountClass *, uint32, int)
{
	Unsupported_World_Load_Call("WWAudioClass::Create_Continuous_Sound");
}

// PhysicsSceneClass retains Customized_Render even though this executable
// never renders. Keep its D3D8-shaped edge explicit and unenterable.
unsigned DX8Wrapper::RenderStates[256] = {};
unsigned DX8Wrapper::render_state_changes = 0;

void DX8Wrapper::Get_DX8_Render_State_Value_Name(StringClass &,
	D3DRENDERSTATETYPE, unsigned)
{
	Unsupported_World_Load_Call(
		"DX8Wrapper::Get_DX8_Render_State_Value_Name");
}

HRESULT IDirect3DDevice8::SetRenderState(D3DRENDERSTATETYPE, DWORD)
{
	Unsupported_World_Load_Call("IDirect3DDevice8::SetRenderState");
}
