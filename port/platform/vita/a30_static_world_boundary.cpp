// Explicit A3.0 boundaries retained by the original Door/Elevator vtables.
//
// The static M00 bring-up path does not yet instantiate gameplay objects,
// update doors/elevators, or initialize WWAudio.  Old VC6 vtables nevertheless
// retain references to a few methods/globals from those later coherent
// subsystems.  The scalar accessors below preserve their exact original
// algorithms and initial state; audio calls are isolated at the documented
// unavailable WWAudio/Miles boundary and produce durable diagnostics if a
// future frame begins to require them.

#include "a30_vita_runtime.h"

#include "combat.h"
#include "diaglog.h"
#include "dx8wrapper.h"
#include "gameobjmanager.h"
#include "smartgameobj.h"
#include "sortingrenderer.h"
#include "vehicle.h"
#include "WWAudio.h"
#include "ww3d_vita_renderer.h"

#include <stdarg.h>
#include <stdio.h>

bool CombatManager::IAmServer = false;
GameObjReference CombatManager::TheStar;
SList<SoldierGameObj> GameObjManager::StarGameObjList;

void DiagLogClass::Log_Timed(const char *type, const char *format, ...)
{
	char message[384];
	va_list arguments;
	va_start(arguments, format);
	vsnprintf(message, sizeof(message), format, arguments);
	va_end(arguments);
	A30_Vita_Log("Combat diagnostic [%s]: %s\n",
		type != NULL ? type : "(null)", message);
}

/* Exact original scalar predicates/accessors.  They are kept here only until
** the complete GameObj runtime TUs become part of A3.0; no gameplay state is
** manufactured by this target. */
bool SmartGameObj::Is_Human_Controlled()
{
	return ControlOwner >= 0;
}

SoldierGameObj *VehicleGameObj::Get_Driver()
{
	if (SeatOccupants.Length() > DRIVER_SEAT) {
		return SeatOccupants[DRIVER_SEAT];
	}
	return NULL;
}

WWAudioClass *WWAudioClass::_theInstance = NULL;

int WWAudioClass::Create_Instant_Sound(int definition_id, const Matrix3D &,
	RefCountClass *, uint32, int)
{
	static bool logged = false;
	if (!logged) {
		A30_Vita_Log(
			"Deferred WWAudio boundary entered: instant sound definition=%d (audio unavailable)\n",
			definition_id);
		logged = true;
	}
	return 0;
}

AudibleSoundClass *WWAudioClass::Create_Continuous_Sound(int definition_id,
	RefCountClass *, uint32, int)
{
	static bool logged = false;
	if (!logged) {
		A30_Vita_Log(
			"Deferred WWAudio boundary entered: continuous sound definition=%d (audio unavailable)\n",
			definition_id);
		logged = true;
	}
	return NULL;
}

/* These state-cache members belong to the DirectX implementation edge, not
** to world/game architecture.  The first production world renderer records
** state transitions while MeshClass remains on the already-validated Vita
** submission path. */
unsigned DX8Wrapper::RenderStates[256] = {};
unsigned DX8Wrapper::render_state_changes = 0;

void DX8Wrapper::Get_DX8_Render_State_Value_Name(StringClass &name,
	D3DRENDERSTATETYPE, unsigned)
{
	name = "VITA_BACKEND";
}

HRESULT IDirect3DDevice8::SetRenderState(D3DRENDERSTATETYPE state,
	DWORD value)
{
	/* DX8Wrapper::Set_Render_State owns and updates its protected cache before
	** crossing this device boundary.  The accepted Vita mesh path does not yet
	** need a second platform-side render-state cache; retain the successful
	** device result without violating that original ownership contract. */
	(void)state;
	(void)value;
	return D3D_OK;
}

unsigned int DX8Wrapper::Convert_Color_Clamp(const Vector4 &color)
{
	Vector4 clamped(color);
	for (unsigned component = 0; component < 4U; ++component) {
		if (clamped[component] < 0.0f) {
			clamped[component] = 0.0f;
		} else if (clamped[component] > 1.0f) {
			clamped[component] = 1.0f;
		}
	}
	return D3DCOLOR_COLORVALUE(clamped.X, clamped.Y, clamped.Z, clamped.W);
}

void DX8Wrapper::Set_Render_Target(TextureClass *texture)
{
	if (texture != NULL) {
		RenegadeVitaRenderer::Reject_Indexed_Submission(
			"non-default TextureClass render target is deferred", 0U);
	}
}

void DX8Wrapper::Set_Render_Target(IDirect3DSurface8 *surface, bool)
{
	if (surface != NULL) {
		RenegadeVitaRenderer::Reject_Indexed_Submission(
			"non-default surface render target is deferred", 0U);
	}
}

void DX8Wrapper::Set_Light_Environment(LightEnvironmentClass *)
{
	/* Original light ownership remains in RenderInfo/LightEnvironment.  The
	** accepted transitional MeshClass path visualizes normals and does not yet
	** consume the DX8 fixed-function light cache. */
}

void SortingRendererClass::Insert_Triangles(const SphereClass &,
	unsigned short, unsigned short, unsigned short, unsigned short)
{
	RenegadeVitaRenderer::Reject_Indexed_Submission(
		"sorted indexed submission is deferred", 0U);
}

void SortingRendererClass::Insert_Triangles(unsigned short, unsigned short,
	unsigned short, unsigned short)
{
	RenegadeVitaRenderer::Reject_Indexed_Submission(
		"sorted indexed submission is deferred", 0U);
}
