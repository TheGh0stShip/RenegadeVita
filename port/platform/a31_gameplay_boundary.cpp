// A3.1 platform/middleware boundary for the original Combat ownership seed.
//
// The five temporary static-world gameplay definitions are intentionally not
// repeated here: CombatManager, GameObjManager, SmartGameObj, VehicleGameObj,
// and DiagLogClass are now supplied by their original owning translation units.
// Audio and the DX8 device edge remain explicit platform boundaries until the
// original WWAudio runtime is brought in as its own coherent closure.

#include "dx8wrapper.h"
#include "debug.h"
#include "cnetwork.h"
#include "gamemode.h"
#if defined(__vita__) && defined(RENEGADE_A4_ORIGINAL_FRONTEND) && !RENEGADE_VITA_M00_DEMO
#include "god.h"
#endif
#if defined(__vita__) && defined(RENEGADE_A4_ORIGINAL_GAMEMODE)
#include "combatgmode.h"
#include "gametype.h"
#include "vita_runtime_log.h"
#endif
#include "modpackagemgr.h"
#include "mpsettingsmgr.h"
#include "audiblesound.h"
#include "logicalsound.h"
#include "soundscene.h"
#include "textdisplay.h"
#include "stackdump.h"
#include "a31_audio_lifecycle.h"
#include "a31_interactive_runtime_policy.h"
#include "backgroundmgr.h"
#include "ccamera.h"
#include "combat.h"
#include "activeconversation.h"
#include "conversation.h"
#include "conversationmgr.h"
#include "conversationremark.h"
#include "definition.h"
#include "definitionmgr.h"
#include "hud.h"
#include "input.h"
#include "messagewindow.h"
#include "objectives.h"
#include "pathmgr.h"
#include "directinput.h"
#include "dinput.h"
#include "renegade_vita_input_contract.h"
#include "renegade_vita_input_telemetry.h"
#include "pscene.h"
#include "render2d.h"
#include "soldier.h"
#include "humanphys.h"
#include "quat.h"
#include "timemgr.h"
#include "translateobj.h"
#include "translatedb.h"
#include "weapons.h"
#include "wwaudio.h"
#include "ww3d.h"
#include "renegade_vita_options.h"
#include "ww3d_vita_renderer.h"
#include "a31_vita_hud_presentation.h"
#if defined(__vita__) && !RENEGADE_VITA_M00_DEMO
#include <psp2/kernel/processmgr.h>
static A31SimulationStageTotals g_campaign_simulation_stages = {};
#endif

#if defined(__vita__) && RENEGADE_VITA_M00_DEMO
extern void A31_Vita_Render_Demo_Ending_Overlay(void);
#endif

// Replaces the Win32 message-loop focus global for the native Vita lifecycle.
// The application starts foregrounded; original Input::Update retains its
// existing focus guard without changing action or control ownership.
bool GameInFocus = true;

// These legacy game-mode globals are observed by the original cNetwork
// broken-connection and packet-dispatch paths.  The original MenuGameMode
// owns g_is_loading once the authentic A4 mode graph is selected; retain this
// boundary-owned fallback only for the older direct gameplay targets.
#if !defined(RENEGADE_A4_ORIGINAL_GAMEMODE)
bool g_is_loading = false;
#endif
#if !defined(RENEGADE_A4_ORIGINAL_GAMEMODE) && !defined(RENEGADE_A35_ORIGINAL_COMBATGMODE)
bool g_client_quit = false;
// The full desktop CombatGameMode owns the restart presenter.  Replicated
// packet handling only observes this transition flag, so keep that isolated
// state at the same headless presentation boundary.
bool g_b_core_restart = false;
#endif

// The original desktop initializer creates a registry of game modes together
// with Win32 dialogs, movie playback, and WOL services.  Keep the original
// gameplay query contract without importing those desktop presenters: these
// headless lifecycle entries only report mode state.  Combat simulation,
// replication, player ownership, and frame ordering remain in original
// Commando/Combat owners.
A31AudioLifecycleTrace g_audio_lifecycle_trace = {};
#if !defined(RENEGADE_A4_ORIGINAL_GAMEMODE)
class A31HeadlessGameMode final : public GameModeClass {
public:
	explicit A31HeadlessGameMode(const char *name) : NameValue(name) {}
	virtual const char *Name() { return NameValue; }
	virtual void Init() {}
	virtual void Shutdown() {}
	virtual void Render() {}
	virtual void Think() {}

private:
	const char *NameValue;
};

namespace {

A31HeadlessGameMode g_combat_mode("Combat");
A31HeadlessGameMode g_lan_mode("LAN");
A31HeadlessGameMode g_wol_mode("WOL");
A31HeadlessGameMode g_menu_mode("Menu");
bool g_headless_game_modes_registered = false;
}

#if defined(RENEGADE_A35_ORIGINAL_GAMEMODE)
void A31_Interactive_Register_Headless_Game_Modes()
{
	if (g_headless_game_modes_registered) return;
	if (GameModeManager::Find("Combat") == NULL) {
		GameModeManager::Add(&g_combat_mode);
	}
	if (GameModeManager::Find("LAN") == NULL) {
		GameModeManager::Add(&g_lan_mode);
	}
	if (GameModeManager::Find("WOL") == NULL) {
		GameModeManager::Add(&g_wol_mode);
	}
	if (GameModeManager::Find("Menu") == NULL) {
		GameModeManager::Add(&g_menu_mode);
	}
	g_headless_game_modes_registered = true;
}
#else
void A31_Interactive_Register_Headless_Game_Modes()
{
}

GameModeClass *GameModeManager::Find(const char *name)
{
	if (name == NULL) return NULL;
	if (stricmp(name, g_combat_mode.Name()) == 0) return &g_combat_mode;
	if (stricmp(name, g_lan_mode.Name()) == 0) return &g_lan_mode;
	if (stricmp(name, g_wol_mode.Name()) == 0) return &g_wol_mode;
	if (stricmp(name, g_menu_mode.Name()) == 0) return &g_menu_mode;
	return NULL;
}

// These are the unmodified lifecycle state transitions from
// Commando/gamemode.cpp.  Their desktop manager owner is deliberately outside
// the native headless presentation boundary, but cGameData's original
// gameplay-permission query depends on the exact GameModeClass state machine.
void GameModeClass::Activate()
{
	if (State == GAME_MODE_INACTIVE) {
		Init();
		State = GAME_MODE_ACTIVE;
	}

	if (State == GAME_MODE_INACTIVE_PENDING) {
		State = GAME_MODE_ACTIVE;
	}
}

void GameModeClass::Deactivate()
{
	if (!Is_Inactive()) {
		State = GAME_MODE_INACTIVE_PENDING;
	}
}

void GameModeClass::Safely_Deactivate()
{
	if (State == GAME_MODE_INACTIVE_PENDING) {
		Shutdown();
		State = GAME_MODE_INACTIVE;
	}
}

void GameModeClass::Suspend()
{
	if (State == GAME_MODE_ACTIVE) {
		State = GAME_MODE_SUSPENDED;
	}
}

void GameModeClass::Resume()
{
	if (State == GAME_MODE_SUSPENDED) {
		State = GAME_MODE_ACTIVE;
	}
}
#endif // !RENEGADE_A35_ORIGINAL_GAMEMODE
#endif // !RENEGADE_A4_ORIGINAL_GAMEMODE

namespace {

/* The desktop CombatGameMode handler turns original Combat completion into a
** campaign/menu transition.  Those Win32 presenters are not part of the
** direct Vita route, so retain the same CombatMiscHandler ownership seam and
** latch only the event needed for a stable native application transition. */
A31MissionCompletionLatch g_mission_completion_latch;

enum
{
	A31_SPEECH_SOURCE_NONE = 0,
	A31_SPEECH_SOURCE_ORATOR = 1,
	A31_SPEECH_SOURCE_ACTIVE_CONVERSATION = 2
};

const float kA31GameplayHUDLogicalWidth =
	static_cast<float>(RenegadeVitaRenderer::DISPLAY_WIDTH);
const float kA31GameplayHUDLogicalHeight =
	static_cast<float>(RenegadeVitaRenderer::DISPLAY_HEIGHT);

struct A31NativeHUDPresentationRect
{
	uint32_t x;
	uint32_t y;
	uint32_t width;
	uint32_t height;
};

A31NativeHUDPresentationRect Build_A31_Gameplay_HUD_Presentation_Rect()
{
	/* Gameplay HUD/text and world-projected overlays must share one coordinate
	** space on Vita.  The Dev86/Dev87 physical returns showed target boxes and
	** HUD text drifting because initialization and render scopes forced 640x480
	** while the active Combat camera/projected coordinates were native Vita
	** display space.  Keep original Combat/HUD ownership, but present gameplay
	** overlays through the full native display coordinate range. */
	const A31NativeHUDPresentationRect rect = {
		0U,
		0U,
		RenegadeVitaRenderer::DISPLAY_WIDTH,
		RenegadeVitaRenderer::DISPLAY_HEIGHT
	};
	return rect;
}

bool Apply_A31_Gameplay_HUD_Presentation_Rect()
{
	const A31NativeHUDPresentationRect rect =
		Build_A31_Gameplay_HUD_Presentation_Rect();
	return RenegadeVitaRenderer::Set_Native_Presentation_Rect_Quiet(
		rect.x, rect.y, rect.width, rect.height);
}

class A31GameplayHUDRenderPresentation
{
public:
	A31GameplayHUDRenderPresentation() :
		Depth(0), Previous(0, 0, 0, 0), PresentationRectApplied(false)
	{
	}

	void Begin()
	{
		if (Depth++ != 0U) return;
		Previous = Render2DClass::Get_Screen_Resolution();
		PresentationRectApplied = Apply_A31_Gameplay_HUD_Presentation_Rect();
		Render2DClass::Set_Screen_Resolution(RectClass(0, 0,
			kA31GameplayHUDLogicalWidth, kA31GameplayHUDLogicalHeight));
	}

	void End()
	{
		if (Depth == 0U || --Depth != 0U) return;
		Render2DClass::Set_Screen_Resolution(Previous);
		if (PresentationRectApplied) {
			RenegadeVitaRenderer::Reset_Native_Presentation_Rect_Quiet();
			PresentationRectApplied = false;
		}
	}

private:
	unsigned Depth;
	RectClass Previous;
	bool PresentationRectApplied;
};

A31GameplayHUDRenderPresentation g_a31_gameplay_hud_render_presentation;

class A31ScopedGameplayHUDRender2DResolution
{
public:
	A31ScopedGameplayHUDRender2DResolution()
	{
		A31_Vita_Begin_Original_HUD_Render();
	}

	~A31ScopedGameplayHUDRender2DResolution()
	{
		A31_Vita_End_Original_HUD_Render();
	}

	A31ScopedGameplayHUDRender2DResolution(
		const A31ScopedGameplayHUDRender2DResolution &) = delete;
	A31ScopedGameplayHUDRender2DResolution &operator=(
		const A31ScopedGameplayHUDRender2DResolution &) = delete;
};

AudibleSoundClass *Find_Conversation_Speech_For_Diagnostics(
	ActiveConversationClass *active, A31MissionProgressState *state)
{
	if (active == NULL || state == NULL) {
		return NULL;
	}

	PhysicalGameObj *orator = active->Get_Current_Orator();
	SoldierGameObj *soldier = orator != NULL ? orator->As_SoldierGameObj() : NULL;
	state->active_conversation_speaker_available = orator != NULL;
	if (soldier != NULL) {
		AudibleSoundClass *speech =
			soldier->Peek_Current_Speech_For_Diagnostics();
		if (speech != NULL) {
			state->active_conversation_speech_source =
				A31_SPEECH_SOURCE_ORATOR;
			return speech;
		}
	}

	AudibleSoundClass *speech =
		active->Peek_Current_Sound_For_Diagnostics();
	if (speech != NULL) {
		state->active_conversation_speech_source =
			A31_SPEECH_SOURCE_ACTIVE_CONVERSATION;
		return speech;
	}

	return NULL;
}

void Fill_Conversation_Speech_Diagnostics(
	ActiveConversationClass *active, A31MissionProgressState *state)
{
	AudibleSoundClass *speech =
		Find_Conversation_Speech_For_Diagnostics(active, state);
	if (speech == NULL) {
		return;
	}

	state->active_conversation_speech_available = true;
	state->active_conversation_speech_in_scene = speech->Is_In_Scene();
	state->active_conversation_speech_culled = speech->Is_Sound_Culled();
	state->active_conversation_speech_playing = speech->Is_Playing();
	state->active_conversation_speech_class_id =
		static_cast<int32_t>(speech->Get_Class_ID());
	state->active_conversation_speech_type =
		static_cast<int32_t>(speech->Get_Type());
	state->active_conversation_speech_state =
		static_cast<int32_t>(speech->Get_State());
	state->active_conversation_speech_duration_ms =
		static_cast<uint32_t>(speech->Get_Duration());
	state->active_conversation_speech_dropoff_radius =
		speech->Get_DropOff_Radius();

	WWAudioClass *audio = WWAudioClass::Get_Instance();
	SoundSceneClass *sound_scene =
		audio != NULL ? audio->Get_Sound_Scene() : NULL;
	if (sound_scene != NULL) {
		const Vector3 listener_pos = sound_scene->Get_Listener_Position();
		const Vector3 speech_pos = speech->Get_Position();
		state->active_conversation_speech_listener_distance =
			(listener_pos - speech_pos).Quick_Length();
	}
}

class A31VitaCombatMiscHandler final : public CombatMiscHandlerClass {
public:
	virtual void Mission_Complete(bool success)
	{
		g_mission_completion_latch.Mission_Complete(success);
#if defined(__vita__) && defined(RENEGADE_A4_ORIGINAL_FRONTEND) && !RENEGADE_VITA_M00_DEMO
		if (!success) cGod::Mission_Failed();
#endif
	}

	virtual void Star_Killed()
	{
		g_mission_completion_latch.Star_Killed();
#if defined(__vita__) && defined(RENEGADE_A4_ORIGINAL_FRONTEND) && !RENEGADE_VITA_M00_DEMO
		cGod::Star_Killed();
#endif
	}
};

A31VitaCombatMiscHandler g_vita_combat_misc_handler;

}

// The original DebugManager implementation owns Windows-only symbol lookup.
// Keep the state observed by original Combat inline accessors at the platform
// boundary until native diagnostic UI replaces that desktop facility.
int DebugManager::VersionNumber = 0;
bool DebugManager::AllowCinematicKeys = false;
DebugDisplayHandlerClass *DebugManager::DisplayHandler = NULL;

// The original replicated update path reports high-volume diagnostics through
// this desktop debug sink.  Keep simulation and packet scheduling intact while
// routing the unavailable presentation endpoint to the Vita log boundary.
void DebugManager::Display_Network_Prolific(char const *, ...)
{
}

void DebugManager::Display_Text(const WideStringClass &, const Vector3 &)
{
	// The desktop debug display handler has no Vita presentation endpoint.
}

// SEH is a Win32-only failure-reporting mechanism.  ThreadClass' POSIX/Vita
// path never invokes this callback, but original Combat construction retains
// it in the ThreadClass contract.  Keep the unavailable behavior at this
// single platform boundary rather than altering Combat startup.
int Exception_Handler(int, struct _EXCEPTION_POINTERS *)
{
	return 0;
}

// Desktop stack-symbol lookup is unavailable on Vita. Preserve the original
// diagnostic call site while leaving collection to the native crash/log path.
void cStackDump::Print_Call_Stack(void)
{
}

/* Font3D now uses the same original FileFactory/Targa/SurfaceClass/
** TextureClass chain as the rest of WW3D, ending only at the Vita texture
** boundary.  Device builds now exercise the genuine Combat HUD so M00 can
** present Logan text, the weapon HUD, and original objective overlays. */
bool A31_Interactive_Render_HUD_Available()
{
	return true;
}

A31InteractiveHUDState A31_Interactive_Get_HUD_State()
{
	A31InteractiveHUDState state = {};
	state.serialized_enabled = HUDClass::Is_Enabled();
	state.render_resources_available = HUDClass::Are_Render_Resources_Available();
	state.effectively_displayable = state.serialized_enabled &&
		state.render_resources_available;
	return state;
}

void A31_Interactive_Apply_Render_Capabilities()
{
	PhysicsSceneClass *scene = CombatManager::Get_Scene();
	if (scene != NULL) {
		/* This is the original no-projector setting exposed by Commando's
		** performance controls, not a replacement renderer or scene. */
		scene->Enable_Static_Projectors(false);
		scene->Enable_Dynamic_Projectors(false);
		scene->Set_Shadow_Mode(PhysicsSceneClass::SHADOW_MODE_NONE);
		RenegadeVitaOptions::Apply_Performance(*scene);
	}
}

void A31_Interactive_Configure_Vita_Controls()
{
	// Use the original action map.  Analog sliders own movement/camera, while
	// physical D-pad buttons become original gameplay functions below the
	// DirectInput boundary.  The named sensitivity participates in original
	// Input::Update_Sliders and CCamera integration; it is not a Vita camera.
	Input::Set_Mouse_Sensitivity(RenegadeVitaInput::DEFAULT_CAMERA_SENSITIVITY);
	Input::Set_Primary_Key_For_Function(INPUT_FUNCTION_QUICKSAVE, DIK_F5);
	Input::Set_Secondary_Key_For_Function(INPUT_FUNCTION_QUICKSAVE, 0);
	Input::Set_Primary_Key_For_Function(INPUT_FUNCTION_CYCLE_POG, DIK_BACK);
	Input::Set_Secondary_Key_For_Function(INPUT_FUNCTION_CYCLE_POG, 0);
	Input::Set_Primary_Key_For_Function(INPUT_FUNCTION_MOVE_FORWARD,
		Input::SLIDER_JOYSTICK_UP);
	Input::Set_Primary_Key_For_Function(INPUT_FUNCTION_MOVE_BACKWARD,
		Input::SLIDER_JOYSTICK_DOWN);
	Input::Set_Primary_Key_For_Function(INPUT_FUNCTION_MOVE_LEFT,
		Input::SLIDER_JOYSTICK_LEFT);
	Input::Set_Primary_Key_For_Function(INPUT_FUNCTION_MOVE_RIGHT,
		Input::SLIDER_JOYSTICK_RIGHT);
	Input::Set_Secondary_Key_For_Function(INPUT_FUNCTION_MOVE_FORWARD, 0);
	Input::Set_Secondary_Key_For_Function(INPUT_FUNCTION_MOVE_BACKWARD, 0);
	Input::Set_Secondary_Key_For_Function(INPUT_FUNCTION_MOVE_LEFT, 0);
	Input::Set_Secondary_Key_For_Function(INPUT_FUNCTION_MOVE_RIGHT, 0);
	Input::Set_Primary_Key_For_Function(INPUT_FUNCTION_WEAPON_LEFT,
		Input::SLIDER_MOUSE_LEFT);
	Input::Set_Primary_Key_For_Function(INPUT_FUNCTION_WEAPON_RIGHT,
		Input::SLIDER_MOUSE_RIGHT);
	Input::Set_Primary_Key_For_Function(INPUT_FUNCTION_WEAPON_UP,
		Input::SLIDER_MOUSE_UP);
	Input::Set_Primary_Key_For_Function(INPUT_FUNCTION_WEAPON_DOWN,
		Input::SLIDER_MOUSE_DOWN);
	Input::Set_Secondary_Key_For_Function(INPUT_FUNCTION_WEAPON_LEFT, 0);
	Input::Set_Secondary_Key_For_Function(INPUT_FUNCTION_WEAPON_RIGHT, 0);
	Input::Set_Secondary_Key_For_Function(INPUT_FUNCTION_WEAPON_UP, 0);
	Input::Set_Secondary_Key_For_Function(INPUT_FUNCTION_WEAPON_DOWN, 0);
	Input::Set_Primary_Key_For_Function(INPUT_FUNCTION_TURN_LEFT, 0);
	Input::Set_Secondary_Key_For_Function(INPUT_FUNCTION_TURN_LEFT, 0);
	Input::Set_Primary_Key_For_Function(INPUT_FUNCTION_TURN_RIGHT, 0);
	Input::Set_Secondary_Key_For_Function(INPUT_FUNCTION_TURN_RIGHT, 0);
	Input::Set_Primary_Key_For_Function(INPUT_FUNCTION_VEHICLE_TURN_LEFT, 0);
	Input::Set_Secondary_Key_For_Function(INPUT_FUNCTION_VEHICLE_TURN_LEFT, 0);
	Input::Set_Primary_Key_For_Function(INPUT_FUNCTION_VEHICLE_TURN_RIGHT, 0);
	Input::Set_Secondary_Key_For_Function(INPUT_FUNCTION_VEHICLE_TURN_RIGHT, 0);
	Input::Set_Primary_Key_For_Function(INPUT_FUNCTION_JUMP, DIK_SPACE);
	Input::Set_Primary_Key_For_Function(INPUT_FUNCTION_CROUCH, DIK_LCONTROL);
	Input::Set_Primary_Key_For_Function(INPUT_FUNCTION_ACTION, DIK_E);
	Input::Set_Secondary_Key_For_Function(INPUT_FUNCTION_ACTION, 0);
	Input::Set_Primary_Key_For_Function(INPUT_FUNCTION_RELOAD_WEAPON, DIK_R);
	Input::Set_Secondary_Key_For_Function(INPUT_FUNCTION_RELOAD_WEAPON, 0);
	Input::Set_Primary_Key_For_Function(INPUT_FUNCTION_FIRST_PERSON_TOGGLE, DIK_F);
	Input::Set_Secondary_Key_For_Function(INPUT_FUNCTION_FIRST_PERSON_TOGGLE, 0);
	Input::Set_Primary_Key_For_Function(INPUT_FUNCTION_PREV_WEAPON, DIK_LEFT);
	Input::Set_Secondary_Key_For_Function(INPUT_FUNCTION_PREV_WEAPON, 0);
	Input::Set_Primary_Key_For_Function(INPUT_FUNCTION_NEXT_WEAPON, DIK_RIGHT);
	Input::Set_Secondary_Key_For_Function(INPUT_FUNCTION_NEXT_WEAPON, 0);
	Input::Set_Primary_Key_For_Function(INPUT_FUNCTION_ZOOM_IN, DIK_UP);
	Input::Set_Secondary_Key_For_Function(INPUT_FUNCTION_ZOOM_IN, 0);
	Input::Set_Primary_Key_For_Function(INPUT_FUNCTION_ZOOM_OUT, DIK_DOWN);
	Input::Set_Secondary_Key_For_Function(INPUT_FUNCTION_ZOOM_OUT, 0);
	Input::Set_Primary_Key_For_Function(
		INPUT_FUNCTION_EVA_MISSION_OBJECTIVES_TOGGLE, 0);
	Input::Set_Secondary_Key_For_Function(
		INPUT_FUNCTION_EVA_MISSION_OBJECTIVES_TOGGLE, 0);
	Input::Set_Primary_Key_For_Function(INPUT_FUNCTION_MENU_TOGGLE, DIK_ESCAPE);
	Input::Set_Primary_Key_For_Function(INPUT_FUNCTION_FIRE_WEAPON_PRIMARY,
		DirectInput::BUTTON_JOYSTICK_B);
	Input::Set_Primary_Key_For_Function(INPUT_FUNCTION_FIRE_WEAPON_SECONDARY,
		DirectInput::BUTTON_JOYSTICK_A);
	Input::Set_Primary_Key_For_Function(INPUT_FUNCTION_USE_WEAPON, DIK_E);
	Input::Set_Secondary_Key_For_Function(INPUT_FUNCTION_USE_WEAPON, 0);
}

void A31_Interactive_Begin_Mission_Completion_Observation()
{
	g_mission_completion_latch.Reset();
	CombatManager::Set_Combat_Misc_Handler(&g_vita_combat_misc_handler);
}

A31MissionCompletionState A31_Interactive_Get_Mission_Completion_State()
{
	return g_mission_completion_latch.State();
}

void A31_Interactive_End_Mission_Completion_Observation()
{
	CombatManager::Set_Combat_Misc_Handler(NULL);
}

A31MissionProgressState A31_Interactive_Get_Mission_Progress_State()
{
	A31MissionProgressState state = {};
	state.active_conversation_id = -1;
	state.active_conversation_state = -1;
	state.active_conversation_action_id = -1;
	state.active_conversation_current_remark = -1;
	state.active_conversation_remark_count = -1;
	state.active_conversation_text_id = -1;
	state.active_conversation_sound_id = -1;
	state.active_conversation_speech_source = A31_SPEECH_SOURCE_NONE;
	state.active_conversation_speech_class_id = -1;
	state.active_conversation_speech_type = -1;
	state.active_conversation_speech_state = -1;
	for (unsigned index = 0U; index < 6U; ++index) {
		state.objective_status[index] = -1;
	}
	SoldierGameObj *star = CombatManager::Get_The_Star();
	state.star_available = star != NULL;
	state.player_control_enabled = star != NULL && star->Is_Control_Enabled();
	const int objective_count = ObjectiveManager::Get_Objective_Count();
	state.objective_count = objective_count > 0 ?
		static_cast<uint32_t>(objective_count) : 0U;
	for (int index = 0; index < objective_count; ++index) {
		const Objective *objective = ObjectiveManager::Get_Objective(index);
		if (objective != NULL && objective->ID >= 1 && objective->ID <= 6) {
			state.objective_status[objective->ID - 1] = objective->Status;
		}
	}
	const int active_conversations = ConversationMgrClass::Get_Active_Conversation_Count();
	state.active_conversation_count = active_conversations > 0 ?
		static_cast<uint32_t>(active_conversations) : 0U;
	if (active_conversations > 0) {
		ActiveConversationClass *active =
			ConversationMgrClass::Peek_Active_Conversation_For_Diagnostics(0);
		if (active != NULL) {
			state.active_conversation_id = active->Get_ID();
			state.active_conversation_state = active->Get_State_For_Diagnostics();
			state.active_conversation_action_id =
				active->Get_Action_ID_For_Diagnostics();
			state.active_conversation_current_remark =
				active->Get_Current_Remark_For_Diagnostics();
			state.active_conversation_next_remark_seconds =
				active->Get_Next_Remark_Seconds_For_Diagnostics();
			ConversationClass *conversation = active->Peek_Conversation();
			if (conversation != NULL) {
				state.active_conversation_remark_count =
					conversation->Get_Remark_Count();
				snprintf(state.active_conversation_name,
					sizeof(state.active_conversation_name), "%s",
					conversation->Get_Name());
				const int current_remark =
					state.active_conversation_current_remark;
				if (current_remark >= 0 &&
					current_remark < conversation->Get_Remark_Count()) {
					ConversationRemarkClass remark;
					conversation->Get_Remark_Info(current_remark, remark);
					state.active_conversation_text_id = remark.Get_Text_ID();
					TDBObjClass *text = TranslateDBClass::Find_Object(
						state.active_conversation_text_id);
					state.active_conversation_string_available =
						text != NULL && text->Get_String() != NULL &&
						text->Get_String()[0] != 0;
					if (text != NULL) {
						state.active_conversation_sound_id =
							static_cast<int32_t>(text->Get_Sound_ID());
						if (state.active_conversation_sound_id > 0) {
							DefinitionClass *definition =
								DefinitionMgrClass::Find_Definition(
									state.active_conversation_sound_id, false);
							state.active_conversation_sound_definition_available =
								definition != NULL &&
								definition->Get_Class_ID() == CLASSID_SOUND;
						}
					}
				}
			}
			Fill_Conversation_Speech_Diagnostics(active, &state);
		}
	}
	return state;
}

void A31_Interactive_Run_Simulation_Frame()
{
#if defined(__vita__) && !RENEGADE_VITA_M00_DEMO
	const uint64_t frame_start_us = sceKernelGetProcessTimeWide();
#endif
	TimeManager::Update();
#if defined(__vita__) && !RENEGADE_VITA_M00_DEMO
	const uint64_t time_end_us = sceKernelGetProcessTimeWide();
#endif
	Input::Update();
#if defined(__vita__) && !RENEGADE_VITA_M00_DEMO
	const uint64_t input_end_us = sceKernelGetProcessTimeWide();
#endif
#if !defined(RENEGADE_A4_ORIGINAL_GAMEMODE)
	A31_Interactive_Register_Headless_Game_Modes();
#endif
	GameModeClass *combat_mode = GameModeManager::Find("Combat");
	if (combat_mode != NULL && Input::Get_State(INPUT_FUNCTION_MENU_TOGGLE)) {
#if defined(__vita__) && defined(RENEGADE_A4_ORIGINAL_FRONTEND)
		// The native outer loop presents original EVA after this frame returns.
		extern void A31_Vita_Request_Gameplay_Pause(void);
		if (combat_mode->Is_Active()) A31_Vita_Request_Gameplay_Pause();
		cNetwork::Update();
		return;
#else
		if (combat_mode->Is_Active()) {
			combat_mode->Suspend();
		} else if (combat_mode->Is_Suspended()) {
			combat_mode->Resume();
		}
#endif
	}
	/* Match the desktop main loop: suspended Combat returns before control and
	** simulation, while cNetwork still services the local session. The missing
	** desktop menu is presentation-only and does not become a second pause
	** owner at the Vita boundary. */
	if (combat_mode != NULL && !combat_mode->Is_Active()) {
		cNetwork::Update();
		return;
	}
#if defined(__vita__) && defined(RENEGADE_A4_ORIGINAL_GAMEMODE)
	if (IS_MISSION && Input::Get_State(INPUT_FUNCTION_QUICKSAVE)) {
		Vita_Append_A22_Runtime_Breadcrumb("save", "original quicksave requested; file and reload success unassessed");
		CombatGameModeClass::Quick_Save();
	}
#endif
	// Original Commando mainloop.cpp services queued paths before game-mode
	// control/Think. Without this, Goto actions wait forever in THINKING.
	if (COMBAT_CAMERA != NULL) {
		Vector3 camera_pos = COMBAT_CAMERA->Get_Position();
		PathMgrClass::Resolve_Paths(camera_pos);
	}
#if defined(__vita__) && !RENEGADE_VITA_M00_DEMO
	const uint64_t path_end_us = sceKernelGetProcessTimeWide();
#endif
	CombatManager::Generate_Control();
#if defined(__vita__) && !RENEGADE_VITA_M00_DEMO
	const uint64_t control_end_us = sceKernelGetProcessTimeWide();
#endif
	cNetwork::Update();
#if defined(__vita__) && !RENEGADE_VITA_M00_DEMO
	const uint64_t network_end_us = sceKernelGetProcessTimeWide();
#endif
	CombatManager::Think();
#if defined(__vita__) && !RENEGADE_VITA_M00_DEMO
	const uint64_t combat_end_us = sceKernelGetProcessTimeWide();
#endif
	A31_Interactive_Apply_Render_Capabilities();
#if !defined(RENEGADE_HOST_ABI_TEST)
	TextDisplayGameModeClass *text_display =
		TextDisplayGameModeClass::Get_Instance();
	if (text_display != NULL) text_display->Think();
#endif
#if defined(__vita__) && !RENEGADE_VITA_M00_DEMO
	const uint64_t frame_end_us = sceKernelGetProcessTimeWide();
	g_campaign_simulation_stages.frames++;
	g_campaign_simulation_stages.time_manager_us += time_end_us - frame_start_us;
	g_campaign_simulation_stages.input_us += input_end_us - time_end_us;
	g_campaign_simulation_stages.path_us += path_end_us - input_end_us;
	g_campaign_simulation_stages.control_us += control_end_us - path_end_us;
	g_campaign_simulation_stages.network_us += network_end_us - control_end_us;
	g_campaign_simulation_stages.combat_us += combat_end_us - network_end_us;
	g_campaign_simulation_stages.other_us += frame_end_us - combat_end_us;
	g_campaign_simulation_stages.simulated_us += static_cast<uint64_t>(
		TimeManager::Get_Frame_Seconds() * 1000000.0f);
	g_campaign_simulation_stages.real_us += static_cast<uint64_t>(
		TimeManager::Get_Frame_Real_Seconds() * 1000000.0f);
#endif
}

A31SimulationStageTotals A31_Interactive_Get_Simulation_Stage_Totals()
{
#if defined(__vita__) && !RENEGADE_VITA_M00_DEMO
	return g_campaign_simulation_stages;
#else
	return {};
#endif
}

uint32_t Count_Physics_Objects(RefPhysListIterator iterator)
{
	uint32_t count = 0;
	for (iterator.First(); !iterator.Is_Done(); iterator.Next()) {
		++count;
	}
	return count;
}

A31InteractiveRenderTrace A31_Interactive_Run_Render_Frame(bool present)
{
	A31InteractiveRenderTrace trace = {};
	PhysicsSceneClass *scene = CombatManager::Get_Scene();
	CCameraClass *camera = CombatManager::Get_Camera();
	SoldierGameObj *star = CombatManager::Get_The_Star();
	trace.scene_available = scene != NULL;
	trace.camera_available = camera != NULL;
	trace.star_available = star != NULL;
	trace.scene_pointer = reinterpret_cast<uintptr_t>(scene);
	trace.camera_pointer = reinterpret_cast<uintptr_t>(camera);
	trace.star_pointer = reinterpret_cast<uintptr_t>(star);
	if (scene == NULL || camera == NULL) {
		return trace;
	}

	trace.static_object_count = Count_Physics_Objects(
		scene->Get_Static_Object_Iterator());
	trace.dynamic_object_count = Count_Physics_Objects(
		scene->Get_Dynamic_Object_Iterator());
	trace.static_light_count = static_cast<uint32_t>(scene->Get_Static_Light_Count());
	trace.visibility_table_size = static_cast<uint32_t>(scene->Get_Vis_Table_Size());
	trace.visibility_table_count = static_cast<uint32_t>(scene->Get_Vis_Table_Count());
	const Vector3 camera_position = camera->Get_Position();
	camera->Get_Clip_Planes(trace.near_clip, trace.far_clip);
	trace.camera_x = camera_position.X;
	trace.camera_y = camera_position.Y;
	trace.camera_z = camera_position.Z;
	if (star != NULL) {
		Vector3 player_position;
		star->Get_Position(&player_position);
		trace.player_x = player_position.X;
		trace.player_y = player_position.Y;
		trace.player_z = player_position.Z;
		trace.player_object_id = static_cast<uint32_t>(star->Get_ID());
		snprintf(trace.player_definition, sizeof(trace.player_definition), "%s",
			star->Get_Definition().Get_Name());
		snprintf(trace.player_state, sizeof(trace.player_state), "%s",
			star->Get_State_Name());
		const Quaternion player_orientation = Build_Quaternion(star->Get_Transform());
		trace.player_orientation[0] = player_orientation.X;
		trace.player_orientation[1] = player_orientation.Y;
		trace.player_orientation[2] = player_orientation.Z;
		trace.player_orientation[3] = player_orientation.W;
		Vector3 player_velocity;
		star->Get_Velocity(player_velocity);
		trace.player_velocity[0] = player_velocity.X;
		trace.player_velocity[1] = player_velocity.Y;
		trace.player_velocity[2] = player_velocity.Z;
		trace.player_health = star->Get_Defense_Object()->Get_Health();
		trace.player_physics_registered = star->Peek_Physical_Object() != NULL;
		HumanPhysClass *human_phys = star->Peek_Human_Phys();
		trace.player_grounded = human_phys != NULL && human_phys->Is_In_Contact();
		trace.first_person_active = CombatManager::Is_First_Person();
		WeaponClass *weapon = star->Get_Weapon();
		if (weapon != NULL) {
			trace.weapon_present = true;
			trace.weapon_definition_id = static_cast<uint32_t>(weapon->Get_ID());
			snprintf(trace.weapon_definition, sizeof(trace.weapon_definition), "%s",
				weapon->Get_Name());
			trace.weapon_total_rounds = weapon->Get_Total_Rounds();
			trace.weapon_clip_rounds = weapon->Get_Clip_Rounds();
			trace.weapon_total_rounds_fired =
				static_cast<uint32_t>(weapon->Get_Total_Rounds_Fired());
			trace.weapon_state = static_cast<int32_t>(weapon->Get_State());
			trace.weapon_triggered = weapon->Is_Triggered();
			trace.weapon_fired_this_frame = weapon->Is_Firing();
		}
		ActionClass *action = star->Get_Action();
		if (action != NULL) {
			trace.action_act_count = action->Get_Act_Count();
			trace.action_active = action->Is_Active();
			trace.action_busy = action->Is_Busy();
		}
		ControlClass &control = star->Get_Control();
		trace.control_action_active =
			control.Get_Boolean(ControlClass::BOOLEAN_ACTION);
		trace.control_reload_active =
			control.Get_Boolean(ControlClass::BOOLEAN_WEAPON_RELOAD);
		trace.input_action_active = Input::Peek_State(INPUT_FUNCTION_ACTION);
		trace.input_reload_active =
			Input::Peek_State(INPUT_FUNCTION_RELOAD_WEAPON);
		trace.input_use_weapon_active =
			Input::Peek_State(INPUT_FUNCTION_USE_WEAPON);
		trace.input_first_person_toggle_active =
			Input::Peek_State(INPUT_FUNCTION_FIRST_PERSON_TOGGLE);
		trace.input_previous_weapon_active =
			Input::Peek_State(INPUT_FUNCTION_PREV_WEAPON);
			trace.input_next_weapon_active =
				Input::Peek_State(INPUT_FUNCTION_NEXT_WEAPON);
			trace.input_zoom_in_active =
				Input::Peek_State(INPUT_FUNCTION_ZOOM_IN);
			trace.input_zoom_out_active =
				Input::Peek_State(INPUT_FUNCTION_ZOOM_OUT);
			trace.input_objectives_toggle_active =
				Input::Peek_State(INPUT_FUNCTION_EVA_MISSION_OBJECTIVES_TOGGLE);
			const RenegadeVitaInputTelemetry &input =
				Renegade_Vita_Last_Input_Telemetry();
		trace.input_square_down = input.square_down != 0U;
		trace.input_triangle_down = input.triangle_down != 0U;
		trace.input_select_down = input.select_down != 0U;
		trace.input_circle_down = input.circle_down != 0U;
		trace.input_cross_down = input.cross_down != 0U;
		trace.input_left_shoulder_down = input.left_shoulder_down != 0U;
		trace.input_right_shoulder_down = input.right_shoulder_down != 0U;
		trace.input_front_touch_down = input.front_touch_down != 0U;
		trace.input_dpad_up_down = input.dpad_up_down != 0U;
		trace.input_dpad_down_down = input.dpad_down_down != 0U;
		trace.input_dpad_left_down = input.dpad_left_down != 0U;
		trace.input_dpad_right_down = input.dpad_right_down != 0U;
		trace.input_action_key_state = input.action_key_state;
		trace.input_reload_key_state = input.reload_key_state;
		trace.input_camera_toggle_key_state = input.camera_toggle_key_state;
		trace.input_previous_weapon_key_state =
			input.previous_weapon_key_state;
		trace.input_next_weapon_key_state = input.next_weapon_key_state;
		trace.input_zoom_in_key_state = input.zoom_in_key_state;
		trace.input_zoom_out_key_state = input.zoom_out_key_state;
			trace.input_objectives_toggle_key_state =
				input.objectives_toggle_key_state;
			trace.input_buttons = input.buttons;
		}

	/* Match the original GameModeManager::Render envelope.  PhysicsScene's
	** render method consumes its visible lists; without this pre-pass an intact
	** Combat frame can legally traverse zero objects. */
	scene->Pre_Render_Processing(*camera);
	trace.pre_render_completed = true;
	trace.begin_render_completed =
		WW3D::Begin_Render(true, true, BackgroundMgrClass::Get_Clear_Color()) ==
		WW3D_ERROR_OK;
	if (trace.begin_render_completed) {
		CombatManager::Render();
		trace.combat_render_called = true;
		A31ScopedGameplayHUDRender2DResolution hud_render_resolution;
		MessageWindowClass *message_window =
			CombatManager::Get_Message_Window();
		trace.message_window_available = message_window != NULL;
		if (message_window != NULL) {
			message_window->Render();
			trace.message_window_render_called = true;
		}
		ObjectiveManager::Render_Viewer();
		trace.objective_viewer_render_called = true;
#if !defined(RENEGADE_HOST_ABI_TEST)
		TextDisplayGameModeClass *text_display =
			TextDisplayGameModeClass::Get_Instance();
		trace.text_display_available = text_display != NULL;
		if (text_display != NULL) {
			text_display->Render();
			trace.text_display_render_called = true;
		}
#endif
#if defined(__vita__) && RENEGADE_VITA_M00_DEMO
		A31_Vita_Render_Demo_Ending_Overlay();
#endif
	}
	trace.end_render_completed = trace.begin_render_completed &&
		WW3D::End_Render(present) == WW3D_ERROR_OK;
	scene->Post_Render_Processing();
	trace.post_render_completed = true;

	const RenegadeVitaRenderer::Statistics &statistics =
		RenegadeVitaRenderer::Get_Statistics();
	trace.mesh_submissions = statistics.mesh_submissions;
	trace.vertex_submissions = statistics.vertex_submissions;
	trace.triangle_submissions = statistics.triangle_submissions;
	trace.rejected_submissions = statistics.rejected_indexed_submissions;
	trace.unsupported_submissions = statistics.unsupported_submissions;
	return trace;
}

#if defined(RENEGADE_HOST_ABI_TEST)
// Host closure targets do not link Commando's full text display owner.
// Device builds provide the original TextDisplayGameModeClass from textdisplay.cpp.
TextDisplayGameModeClass *TextDisplayGameModeClass::Instance = NULL;
void TextDisplayGameModeClass::Flush(void)
{
}
#endif

// MOD package enumeration was Win32-directory based. The normal retail
// campaign has no selected package; retain deterministic metadata queries
// until Vita mod discovery is implemented at this platform boundary.
#if !defined(RENEGADE_A4_ORIGINAL_GAMEMODE)
void ModPackageMgrClass::Set_Current_Package(const char *)
{
}
bool ModPackageMgrClass::Get_Mod_Map_Name_From_CRC(uint32, uint32,
	StringClass *, StringClass *)
{
	return false;
}
#endif // !RENEGADE_A4_ORIGINAL_GAMEMODE

// The local text filter starts with original defaults. WOL account preference
// persistence is intentionally outside the LAN/direct-IP baseline.
int MPSettingsMgrClass::OptionFlags = MPSettingsMgrClass::OPTION_DEFAULTS;
#include "sortingrenderer.h"
#include "texturethumbnail.h"
#include "WWAudio.h"
#include "LogicalListener.h"
#include "SoundScene.h"
#include "chunkio.h"
#include "cpudetect.h"
#include "stylemgr.h"

#if !defined(RENEGADE_HOST_ABI_TEST)
#include "a30_vita_runtime.h"
#include "ww3d_vita_renderer.h"
#endif

#include <stdarg.h>
#include <stdio.h>
#include <string.h>

namespace {

void Log_Deferred_Audio(const char *operation, int definition_id)
{
	/* A missing device must not turn an original per-frame retry into an I/O
	 * workload. Keep one bounded counter per boundary operation and preserve
	 * diagnostic visibility at exponentially spaced occurrences. */
	struct DeferredAudioCounter { const char *operation; unsigned count; };
	static DeferredAudioCounter counters[] = {
		{ "Create_Sound", 0U }, { "Create_Instant_Sound", 0U },
		{ "Create_Continuous_Sound", 0U }, { "Simple_Play_2D_Sound_Effect", 0U }
	};
	DeferredAudioCounter *counter = NULL;
	for (unsigned i = 0U; i < sizeof(counters) / sizeof(counters[0]); ++i) {
		if (strcmp(counters[i].operation, operation) == 0) { counter = &counters[i]; break; }
	}
	if (counter == NULL) return;
	++counter->count;
	const unsigned count = counter->count;
	if (count != 1U && (count & (count - 1U)) != 0U) return;
#if defined(RENEGADE_HOST_ABI_TEST)
	fprintf(stderr, "A3.5 deferred WWAudio boundary: %s definition=%d occurrence=%u\n",
		operation, definition_id, count);
#else
	A30_Vita_Log("A3.5 deferred WWAudio boundary: %s definition=%d occurrence=%u\n",
		operation, definition_id, count);
#endif
}

void Log_Audio_Lifecycle(const char *stage, WWAudioClass *audio,
	SoundSceneClass *scene)
{
#if defined(RENEGADE_HOST_ABI_TEST)
	fprintf(stderr,
		"A3.1 breadcrumb: %s singleton=%p sound_scene=%p\n",
		stage, static_cast<void *>(audio), static_cast<void *>(scene));
	fflush(stderr);
#else
	A30_Vita_Log("A3.1 breadcrumb: %s singleton=%p sound_scene=%p\n",
		stage, static_cast<void *>(audio), static_cast<void *>(scene));
#endif
}

} // namespace

void A31_Vita_Begin_Original_HUD_Render()
{
	g_a31_gameplay_hud_render_presentation.Begin();
}

void A31_Vita_End_Original_HUD_Render()
{
	g_a31_gameplay_hud_render_presentation.End();
}

void A31_Audio_Lifecycle_Reset_Trace()
{
	g_audio_lifecycle_trace = {};
}

A31AudioLifecycleTrace A31_Audio_Lifecycle_Get_Trace()
{
	return g_audio_lifecycle_trace;
}

void A31_Audio_Save_Load_Breadcrumb(const char *stage)
{
	WWAudioClass *audio = WWAudioClass::Get_Instance();
	SoundSceneClass *scene = audio != NULL ? audio->Get_Sound_Scene() : NULL;
	++g_audio_lifecycle_trace.static_audio_load_entries;
	g_audio_lifecycle_trace.singleton_present_at_static_load = audio != NULL;
	g_audio_lifecycle_trace.sound_scene_present_at_static_load = scene != NULL;
	Log_Audio_Lifecycle(stage, audio, scene);
}

// The retail SaveGameManager registers thumbnail databases while preparing a
// level. The established Vita texture path deliberately does not consume
// those DX8/GDI-generated databases, so retain this optional desktop
// preprocessing feature at its original subsystem boundary. This does not
// alter retail MIX access, definition loading, or world texture residency.
void ThumbnailManagerClass::Add_Thumbnail_Manager(const char *, const char *)
{
}

#if !defined(RENEGADE_A35_ORIGINAL_WWAUDIO)
WWAudioClass *WWAudioClass::_theInstance = NULL;

// This is the A3.1 no-output audio-device implementation.  It intentionally
// retains the original WWAudio object and original logical-listener ownership
// so Combat's SmartGameObj lifecycle is unchanged; only Miles/device playback
// is deferred below that interface.
WWAudioClass::WWAudioClass(bool lite)
	: m_PlaybackRate(44100),
	  m_PlaybackBits(16),
	  m_PlaybackStereo(true),
	  m_MusicVolume(DEF_MUSIC_VOL),
	  m_SoundVolume(DEF_SFX_VOL),
	  m_RealMusicVolume(DEF_MUSIC_VOL),
	  m_RealSoundVolume(DEF_SFX_VOL),
	  m_DialogVolume(DEF_DIALOG_VOL),
	  m_CinematicVolume(DEF_CINEMATIC_VOL),
	  m_Max2DSamples(DEF_2D_SAMPLE_COUNT),
	  m_Max3DSamples(DEF_3D_SAMPLE_COUNT),
	  m_Max2DBufferSize(DEF_MAX_2D_BUFFER_SIZE),
	  m_Max3DBufferSize(DEF_MAX_3D_BUFFER_SIZE),
	  m_UpdateTimer(-1),
	  m_IsMusicEnabled(true),
	  m_IsDialogEnabled(true),
	  m_IsCinematicSoundEnabled(true),
	  m_AreSoundEffectsEnabled(true),
	  m_AreNewSoundsEnabled(true),
	  m_FileFactory(NULL),
	  m_BackgroundMusic(NULL),
	  m_CachedIsMusicEnabled(true),
	  m_CachedIsDialogEnabled(true),
	  m_CachedIsCinematicSoundEnabled(true),
	  m_CachedAreSoundEffectsEnabled(true),
	  m_SoundScene(NULL),
	  m_CurrPage(PAGE_PRIMARY),
	  m_Driver2D(NULL),
	  m_Driver3D(NULL),
	  m_Driver3DPseudo(NULL),
	  m_ReverbFilter(NULL),
	  m_SpeakerType(0),
	  m_MaxCacheSize(DEF_CACHE_SIZE * 1024),
	  m_CurrentCacheSize(0),
	  m_EffectsLevel(0.0f),
	  m_ReverbRoomType(0),
	  m_NonDialogFadeTime(DEF_FADE_TIME),
	  m_FadeType(FADE_NONE),
	  m_FadeTimer(0.0f),
	  AudioIni(NULL),
	  m_ForceDisable(lite)
{
	_theInstance = this;
}

WWAudioClass::~WWAudioClass(void)
{
	_theInstance = NULL;
}

void WWAudioClass::Initialize(bool, int, int)
{
}

void WWAudioClass::Initialize(const char *)
{
}

void WWAudioClass::Shutdown(void)
{
}

void WWAudioClass::Add_Logical_Type(int id, LPCTSTR display_name)
{
	m_LogicalTypes.Add(LOGICAL_TYPE_STRUCT(id, display_name));
}

void WWAudioClass::Reset_Logical_Types(void)
{
	m_LogicalTypes.Delete_All();
}

void WWAudioClass::Set_Background_Music(const char *filename)
{
	// Music ownership remains below the silent-device boundary.  Preserve the
	// original visible state for retail dynamic-level restoration, but do not
	// synthesize a Miles sound object on Vita.
	m_BackgroundMusicName = filename;
}

void WWAudioClass::Fade_Background_Music(const char *filename, int, int)
{
	// Preserve the original requested-track state.  Audible fade and playback
	// remain below the deliberately silent Vita device boundary.
	m_BackgroundMusicName = filename;
}

void WWAudioClass::Flush_Cache(void)
{
	/* The A3.1 Vita audio boundary never creates Miles-backed cache entries, but
	 * CombatManager::Unload_Level still owns this call in the original level
	 * lifecycle.  Reset the same observable cache state so an unloaded level
	 * cannot retain stale accounting when a real device backend is added. */
	for (int hash_index = 0; hash_index < MAX_CACHE_HASH; ++hash_index) {
		m_CachedBuffers[hash_index].Delete_All();
	}
	m_CurrentCacheSize = 0;
}

// The original menu/game-init owners manipulate these WWAudio states even
// while Vita has no Miles output device.  Preserve their state and playlist
// lifecycle without constructing desktop sound objects.  This is deliberately
// narrower than an audio replacement: the original WWAudio graph remains the
// future owner once a Vita device backend is admitted.
void WWAudioClass::Allow_Sound_Effects(bool onoff)
{
	m_AreSoundEffectsEnabled = onoff;
}

void WWAudioClass::Allow_Music(bool onoff)
{
	m_IsMusicEnabled = onoff;
}

void WWAudioClass::Allow_Dialog(bool onoff)
{
	m_IsDialogEnabled = onoff;
}

void WWAudioClass::Allow_Cinematic_Sound(bool onoff)
{
	m_IsCinematicSoundEnabled = onoff;
}

// No-output host builds retain settings state for original UI contracts.
// Native candidates select WWAudio.cpp instead of this entire guarded block.
void WWAudioClass::Set_Sound_Effects_Volume(float volume)
{
	m_RealSoundVolume = m_SoundVolume = max(0.0F, min(1.0F, volume));
}
void WWAudioClass::Set_Music_Volume(float volume)
{
	m_RealMusicVolume = m_MusicVolume = max(0.0F, min(1.0F, volume));
}
void WWAudioClass::Set_Dialog_Volume(float volume)
{
	m_DialogVolume = max(0.0F, min(1.0F, volume));
}
void WWAudioClass::Set_Cinematic_Volume(float volume)
{
	m_CinematicVolume = max(0.0F, min(1.0F, volume));
}
int WWAudioClass::Get_Speaker_Type(void) const { return m_SpeakerType; }
void WWAudioClass::Set_Speaker_Type(int type) { m_SpeakerType = type; }
WWAudioClass::DRIVER_TYPE_2D WWAudioClass::Open_2D_Device(bool, int, int)
{
	return DRIVER2D_ERROR;
}
bool WWAudioClass::Select_3D_Device(const char *) { return false; }
bool WWAudioClass::Save_To_Registry(const char *, const StringClass &, bool,
	int, int, bool, bool, bool, bool, float, float, float, float, int)
{
	// This headless adapter has no durable audio settings provider.
	return false;
}
void WWAudioClass::Load_Default_Volume(int &music, int &sound, int &dialog, int &cinematic)
{
	// Same original fallbacks; retail INI consumption belongs to native WWAudio.
	music = 31; sound = 43; dialog = 50; cinematic = 100;
}

void WWAudioClass::Flush_Playlist(SOUND_PAGE page)
{
	// The no-output boundary never inserts audible sounds.  Delete only the
	// original pointer list entries; it owns no sound objects to release.
	m_Playlist[page].Delete_All();
}

void WWAudioClass::Flush_Playlist(void)
{
	Flush_Playlist(PAGE_PRIMARY);
	Flush_Playlist(PAGE_SECONDARY);
}

AudibleSoundClass *WWAudioClass::Create_Sound_Effect(const char *)
{
	/* MenuGameMode owns an optional looping music object.  The current Vita
	 * boundary has no Miles-compatible device or decoder, so report the same
	 * absence that the original method reports for an unavailable source; the
	 * original menu explicitly handles NULL and remains its own lifecycle
	 * owner.  Do not manufacture an audible object merely to advance the menu. */
	return NULL;
}

void WWAudioClass::Set_Active_Sound_Page(SOUND_PAGE page)
{
	/* No-output builds have no active audible objects to pause/resume, but the
	 * original page state is observed by MenuGameMode and later HUD/dialog
	 * owners.  Preserve that state transition exactly without introducing a
	 * replacement playlist or output backend. */
	if (page == PAGE_PRIMARY || page == PAGE_SECONDARY) {
		m_CurrPage = page;
	}
}

void WWAudioClass::Push_Active_Sound_Page(SOUND_PAGE page)
{
	m_PageStack.Add(m_CurrPage);
	Set_Active_Sound_Page(page);
}

void WWAudioClass::Pop_Active_Sound_Page(void)
{
	if (m_PageStack.Count() > 0) {
		const SOUND_PAGE previous = m_PageStack[m_PageStack.Count() - 1];
		m_PageStack.Delete(m_PageStack.Count() - 1);
		Set_Active_Sound_Page(previous);
	}
}

void WWAudioClass::Temp_Disable_Audio(bool onoff)
{
	if (onoff) {
		m_CachedIsMusicEnabled = m_IsMusicEnabled;
		m_CachedIsDialogEnabled = m_IsDialogEnabled;
		m_CachedIsCinematicSoundEnabled = m_IsCinematicSoundEnabled;
		m_CachedAreSoundEffectsEnabled = m_AreSoundEffectsEnabled;
		Allow_Sound_Effects(false);
		Allow_Music(false);
		Allow_Dialog(false);
		Allow_Cinematic_Sound(false);
	} else {
		Allow_Sound_Effects(m_CachedAreSoundEffectsEnabled);
		Allow_Music(m_CachedIsMusicEnabled);
		Allow_Dialog(m_CachedIsDialogEnabled);
		Allow_Cinematic_Sound(m_CachedIsCinematicSoundEnabled);
	}
}

void WWAudioClass::On_Frame_Update(unsigned int)
{
	// No Miles/device work is scheduled by this A3.1 boundary.  Keeping this
	// entry point avoids menu lifecycle drift without per-frame diagnostics.
}

bool WWAudioClass::Simple_Play_2D_Sound_Effect(const char *, float, float)
{
	static bool logged = false;
	if (!logged) {
		Log_Deferred_Audio("Simple_Play_2D_Sound_Effect", -1);
		logged = true;
	}
	return false;
}

bool SoundSceneClass::Save_Static(ChunkSaveClass &)
{
	return true;
}

bool SoundSceneClass::Load_Static(ChunkLoadClass &)
{
	return true;
}

bool SoundSceneClass::Save_Dynamic(ChunkSaveClass &)
{
	return true;
}

bool SoundSceneClass::Load_Dynamic(ChunkLoadClass &)
{
	return true;
}

LogicalListenerClass *WWAudioClass::Create_Logical_Listener(void)
{
	return new LogicalListenerClass;
}

LogicalSoundClass *WWAudioClass::Create_Logical_Sound(void)
{
	// Logical sounds drive original listener/AI behavior and therefore retain
	// their source-authentic object even while audible output is deferred.
	return new LogicalSoundClass;
}

SoundSceneObjClass *WWAudioClass::Find_Sound_Object(uint32 sound_obj_id)
{
	int index = 0;
	if (SoundSceneObjClass::Find_Sound_Object(sound_obj_id, &index)) {
		return SoundSceneObjClass::m_GlobalSoundList[index];
	}
	return NULL;
}

Sound3DClass *WWAudioClass::Create_3D_Sound(const char *, int)
{
	static bool logged = false;
	if (!logged) {
		Log_Deferred_Audio("Create_3D_Sound", -1);
		logged = true;
	}
	return NULL;
}

AudibleSoundClass *WWAudioClass::Create_Sound(int definition_id,
	RefCountClass *, uint32, int)
{
	Log_Deferred_Audio("Create_Sound", definition_id);
	return NULL;
}

AudibleSoundClass *WWAudioClass::Create_Sound(const char *, RefCountClass *,
	uint32, int)
{
	Log_Deferred_Audio("Create_Sound", -1);
	return NULL;
}

int WWAudioClass::Create_Instant_Sound(int definition_id, const Matrix3D &,
	RefCountClass *, uint32, int)
{
	static bool logged = false;
	if (!logged) {
		Log_Deferred_Audio("Create_Instant_Sound", definition_id);
		logged = true;
	}
	return 0;
}

AudibleSoundClass *WWAudioClass::Create_Continuous_Sound(int definition_id,
	RefCountClass *, uint32, int)
{
	static bool logged = false;
	if (!logged) {
		Log_Deferred_Audio("Create_Continuous_Sound", definition_id);
		logged = true;
	}
	return NULL;
}

int WWAudioClass::Create_Instant_Sound(const char *, const Matrix3D &,
	RefCountClass *, uint32, int)
{
	Log_Deferred_Audio("Create_Instant_Sound", -1);
	return 0;
}

AudibleSoundClass *WWAudioClass::Create_Continuous_Sound(const char *,
	RefCountClass *, uint32, int)
{
	Log_Deferred_Audio("Create_Continuous_Sound", -1);
	return NULL;
}
#endif // !RENEGADE_A35_ORIGINAL_WWAUDIO

// The headless input/scene closure provides this storage only while the real
// original StyleMgr owner is absent.  Once StyleMgr is selected, it owns its
// own FontChars cache and lifecycle.
#if !defined(RENEGADE_A4_REAL_STYLEMGR)
FontCharsClass *StyleMgrClass::Fonts[StyleMgrClass::FONT_MAX] = {};
#endif

#if !defined(RENEGADE_HOST_ABI_TEST)

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
	// The accepted transitional MeshClass renderer retains engine-owned light
	// state above this unimplemented fixed-function device edge.
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

#endif
/* The original profiler only needs the calibrated reciprocal.  CPU feature
 * probing is x86/Win32 assembly and stays behind the platform boundary. */
double CPUDetectClass::InvProcessorTicksPerSecond = 1.0e-9;
