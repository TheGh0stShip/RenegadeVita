#include "a31_vita_runtime.h"

#include "a30_vita_runtime.h"
#include "a31_interactive_runtime_policy.h"
#include "renegade_cache_health.h"
#include "renegade_file_factory.h"
#include "renegade_vita_input_telemetry.h"
#include "ww3d_vita_renderer.h"

#include "assetmgr.h"
#include "combat.h"
#include "cnetwork.h"
#include "definitionfactorymgr.h"
#include "ffactory.h"
#include "ffactorylist.h"
#include "gamedata.h"
#include "gameinitmgr.h"
#include "gamemode.h"
#include "gdsingleplayer.h"
#include "gametype.h"
#include "god.h"
#include "input.h"
#include "mixfile.h"
#include "netinterface.h"
#include "networkobjectmgr.h"
#include "pathmgr.h"
#include "playermanager.h"
#include "radar.h"
#include "renegadecheatmgr.h"
#include "serverfps.h"
#include "singlepl.h"
#include "teammanager.h"
#include "timemgr.h"
#include "ww3d.h"
#include "wwaudio.h"
#include "wwmath.h"
#include "wwphys.h"
#include "wwsaveload.h"

#include <psp2/ctrl.h>
#include <psp2/kernel/processmgr.h>
#include <psp2/kernel/threadmgr.h>

extern void _Force_Link_Soldier(void);

namespace {

const RenegadePathRoots kVitaRoots = {
	"ux0:data/renegade/retail",
	"ux0:data/renegade/user",
	"ux0:data/renegade/cache",
	"ux0:data/renegade/mods"
};

const char *const kAlways2Archive = "Data\\Always2.dat";
const char *const kAlwaysDbsArchive = "Data\\always.dbs";
const char *const kAlwaysArchive = "Data\\Always.dat";
const char *const kM00Archive = "Data\\M00_Tutorial.mix";
const char *const kM01CacheIndex = "cache/m01-mix-index-v1.txt";
const uint32_t kTimingWindowFrames = 120U;

// Fixed-capacity timing aggregation keeps the physical candidate decisive
// without adding allocator churn or per-object logging to a release frame.
// All values are process-clock microseconds and therefore are available on a
// retail Vita without a development-only profiler.
struct InteractiveTiming
{
	uint32_t frame_us[kTimingWindowFrames];
	uint32_t sample_count;
	uint32_t sample_cursor;
	uint64_t total_frame_us;
	uint64_t total_sync_us;
	uint64_t total_simulation_us;
	uint64_t total_render_us;
	uint32_t total_frames;
	uint32_t minimum_frame_us;
	uint32_t slow_frame_count;
	uint32_t worst_frame_us;

	void Add(uint32_t sync_us, uint32_t simulation_us, uint32_t render_us,
		uint32_t frame_duration_us)
	{
		frame_us[sample_cursor] = frame_duration_us;
		sample_cursor = (sample_cursor + 1U) % kTimingWindowFrames;
		if (sample_count < kTimingWindowFrames) ++sample_count;
		total_sync_us += sync_us;
		total_simulation_us += simulation_us;
		total_render_us += render_us;
		total_frame_us += frame_duration_us;
		++total_frames;
		if (minimum_frame_us == 0U || frame_duration_us < minimum_frame_us) {
			minimum_frame_us = frame_duration_us;
		}
		if (frame_duration_us > 33333U) ++slow_frame_count;
		if (frame_duration_us > worst_frame_us) worst_frame_us = frame_duration_us;
	}

	uint32_t Percentile(unsigned percentile) const
	{
		if (sample_count == 0U) return 0U;
		uint32_t ordered[kTimingWindowFrames];
		for (uint32_t index = 0U; index < sample_count; ++index) {
			ordered[index] = frame_us[index];
		}
		for (uint32_t index = 1U; index < sample_count; ++index) {
			const uint32_t value = ordered[index];
			uint32_t cursor = index;
			while (cursor > 0U && ordered[cursor - 1U] > value) {
				ordered[cursor] = ordered[cursor - 1U];
				--cursor;
			}
			ordered[cursor] = value;
		}
		const uint32_t rank = (sample_count - 1U) * percentile / 100U;
		return ordered[rank];
	}

	uint32_t Average(uint64_t total) const
	{
		return total_frames == 0U ? 0U : static_cast<uint32_t>(total / total_frames);
	}

	uint32_t Average_FPS_Milli() const
	{
		return total_frame_us == 0U ? 0U : static_cast<uint32_t>(
			static_cast<uint64_t>(total_frames) * 1000000000ULL / total_frame_us);
	}
};

void Copy_Timing_Statistics(A31VitaInteractiveResult &result,
	const InteractiveTiming &timing)
{
	result.average_fps_milli = timing.Average_FPS_Milli();
	result.median_frame_us = timing.Percentile(50U);
	result.p95_frame_us = timing.Percentile(95U);
	result.worst_frame_us = timing.worst_frame_us;
	result.average_sync_us = timing.Average(timing.total_sync_us);
	result.average_simulation_us = timing.Average(timing.total_simulation_us);
	result.average_render_us = timing.Average(timing.total_render_us);
}

void Log_Timing_Statistics(const InteractiveTiming &timing,
	const RenegadeVitaRenderer::Statistics &renderer)
{
	if (timing.sample_count == 0U) return;
	A30_Vita_Log("A3.5 perf: frames=%u rolling_samples=%u avg_fps=%.3f frame_us min/p50/p95/max=%u/%u/%u/%u slow_over_33ms=%u stage_us sync/sim/render=%u/%u/%u draws meshes=%u triangles=%u textures req/decode/upload/bind/missing=%llu/%llu/%llu/%llu/%llu source/invalid/unsupported/decode/upload_fail/checker=%llu/%llu/%llu/%llu/%llu/%llu state_changes=%llu backend_errors=%llu\n",
		timing.total_frames, timing.sample_count,
		static_cast<double>(timing.Average_FPS_Milli()) / 1000.0,
		timing.minimum_frame_us, timing.Percentile(50U), timing.Percentile(95U),
		timing.worst_frame_us, timing.slow_frame_count,
		timing.Average(timing.total_sync_us), timing.Average(timing.total_simulation_us),
		timing.Average(timing.total_render_us), renderer.mesh_submissions,
		renderer.triangle_submissions,
		static_cast<unsigned long long>(renderer.texture_requests),
		static_cast<unsigned long long>(renderer.texture_decodes),
		static_cast<unsigned long long>(renderer.texture_uploads),
		static_cast<unsigned long long>(renderer.texture_binds),
		static_cast<unsigned long long>(renderer.texture_missing),
		static_cast<unsigned long long>(renderer.texture_source_missing),
		static_cast<unsigned long long>(renderer.texture_invalid_data),
		static_cast<unsigned long long>(renderer.texture_unsupported_formats),
		static_cast<unsigned long long>(renderer.texture_decode_failures),
		static_cast<unsigned long long>(renderer.texture_upload_failures),
		static_cast<unsigned long long>(renderer.texture_checkerboard_fallbacks),
		static_cast<unsigned long long>(renderer.state_changes),
		static_cast<unsigned long long>(renderer.backend_errors));
}

void Log_Input_Telemetry()
{
	const RenegadeVitaInputTelemetry &input = Renegade_Vita_Last_Input_Telemetry();
	A30_Vita_Log("A3.5 input: samples=%llu raw lx/ly/rx/ry=%u/%u/%u/%u normalized=%.3f/%.3f/%.3f/%.3f logical=%ld/%ld/%ld/%ld mouse_delta=%ld/%ld dt=%.4f buttons=%08X\n",
		static_cast<unsigned long long>(input.sample_count),
		static_cast<unsigned>(input.lx), static_cast<unsigned>(input.ly),
		static_cast<unsigned>(input.rx), static_cast<unsigned>(input.ry),
		static_cast<double>(input.normalized_lx),
		static_cast<double>(input.normalized_ly),
		static_cast<double>(input.normalized_rx),
		static_cast<double>(input.normalized_ry),
		static_cast<long>(input.logical_lx), static_cast<long>(input.logical_ly),
		static_cast<long>(input.logical_rx), static_cast<long>(input.logical_ry),
		static_cast<long>(input.mouse_dx), static_cast<long>(input.mouse_dy),
		static_cast<double>(input.frame_seconds), input.buttons);
}

void Log_File_Factory_Statistics()
{
	const RenegadeFileFactoryStatistics statistics =
		Renegade_File_Factory_Get_Statistics();
	A30_Vita_Log("A3.6 resources: factory get/return=%u/%u resolve read/write/total/fail/cache_hit=%u/%u/%u/%u/%u open=%u fail=%u available=%u fail=%u create=%u fail=%u delete=%u fail=%u io read=%u/%uB write=%u/%uB; original MIX route unchanged\n",
		statistics.get_file_calls, statistics.return_file_calls,
		statistics.read_resolution_attempts, statistics.write_resolution_attempts,
		statistics.resolution_attempts, statistics.resolution_failures,
		statistics.resolution_cache_hits, statistics.open_attempts,
		statistics.open_failures, statistics.availability_attempts,
		statistics.availability_failures, statistics.create_attempts,
		statistics.create_failures, statistics.delete_attempts,
		statistics.delete_failures, statistics.read_calls, statistics.read_bytes,
		statistics.write_calls, statistics.write_bytes);
}

void Copy_Render_Statistics(A31VitaInteractiveResult &result)
{
	const RenegadeVitaRenderer::Statistics &statistics =
		RenegadeVitaRenderer::Get_Statistics();
	result.mesh_submissions = statistics.mesh_submissions;
	result.vertex_submissions = statistics.vertex_submissions;
	result.triangle_submissions = statistics.triangle_submissions;
}

bool Is_Start_Pressed()
{
	SceCtrlData controller = {};
	return sceCtrlPeekBufferPositive(0, &controller, 1) > 0 &&
		(controller.buttons & SCE_CTRL_START) != 0U;
}

} // namespace

A31VitaInteractiveResult A31_Vita_Run_Interactive_Runtime()
{
	A31VitaInteractiveResult result = {};
	result.attempted = true;
	Renegade_File_Factory_Reset_Statistics();

	RenegadeRootedFileFactoryClass root_factory(kVitaRoots);
	MixFileFactoryClass always2_factory(kAlways2Archive, &root_factory);
	MixFileFactoryClass always_dbs_factory(kAlwaysDbsArchive, &root_factory);
	MixFileFactoryClass always_factory(kAlwaysArchive, &root_factory);
	MixFileFactoryClass m00_factory(kM00Archive, &root_factory);
	FileFactoryListClass factory_list;
	factory_list.Add_FileFactory(&root_factory, "");
	factory_list.Add_FileFactory(&always2_factory, "Always2.dat");
	factory_list.Add_FileFactory(&always_dbs_factory, "Always.dbs");
	factory_list.Add_FileFactory(&always_factory, "Always.dat");
	factory_list.Add_FileFactory(&m00_factory, "M00_Tutorial.mix");

	FileFactoryClass *previous_read_factory = _TheFileFactory;
	FileFactoryClass *previous_write_factory = _TheWritingFileFactory;
	_TheFileFactory = &factory_list;
	_TheWritingFileFactory = &root_factory;

	bool math_initialized = false;
	bool path_manager_initialized = false;
	bool ww3d_initialized = false;
	bool wwphys_initialized = false;
	bool wwsaveload_initialized = false;
	bool input_initialized = false;
	bool combat_initialized = false;
	bool radar_initialized = false;
	bool session_initialized = false;
	bool single_player_transport_initialized = false;
	WW3DAssetManager *asset_manager = NULL;

	A30_Vita_Log("A3.1 interactive: begin original Commando/Combat session\n");
	const RenegadeCacheHealth cache_health = Renegade_Inspect_Mix_Index_Cache(
		kVitaRoots, "M01.mix", kM01CacheIndex);
	A30_Vita_Log("A3.6 cache health: state=%s archive=%s entries=%u detail=%s path=%s; original MIX route unchanged\n",
		Renegade_Cache_Health_Name(cache_health.state), cache_health.archive,
		cache_health.entry_count, cache_health.detail, cache_health.physical_path);
	WWAudioClass *audio = WWAudioClass::Get_Instance();
	if (audio == NULL) {
		A30_Vita_Log("A3.1 interactive: FAIL missing application-owned WWAudio boundary\n");
		Log_File_Factory_Statistics();
		_TheFileFactory = previous_read_factory;
		_TheWritingFileFactory = previous_write_factory;
		return result;
	}
	A30_Vita_Log("A3.1 breadcrumb: audio/session construction singleton=%p sound_scene=%p\n",
		static_cast<void *>(audio), static_cast<void *>(audio->Get_Sound_Scene()));
	{
		RenegadeCheatMgrClass cheat_manager;
		do {
			if (!always2_factory.Is_Valid() || !always_dbs_factory.Is_Valid() ||
				!always_factory.Is_Valid() || !m00_factory.Is_Valid()) {
				A30_Vita_Log("A3.1 interactive: retail factory chain FAIL\n");
				break;
			}

			WWMath::Init();
			math_initialized = true;
			/* Preserve original Commando ordering: the process-wide path-solver
			 * pool begins after WWMath and is destroyed after the asset manager. */
			PathMgrClass::Initialize();
			path_manager_initialized = true;
			asset_manager = new WW3DAssetManager;
			asset_manager->Set_WW3D_Load_On_Demand(true);
			asset_manager->Set_Activate_Fog_On_Load(true);
			ww3d_initialized = WW3D::Init(NULL, NULL, true) == WW3D_ERROR_OK;
			if (!ww3d_initialized) {
				A30_Vita_Log("A3.1 interactive: WW3D init FAIL\n");
				break;
			}
			A30_Vita_Log("A3.1 breadcrumb: WW3D asset manager ready\n");
			/* Font3D now follows the original FileFactory/Targa/Surface/texture
			 * chain. HUD promotion remains a separately tested A4 decision, so log
			 * the selected original Combat mode rather than claiming a capability
			 * is absent. */
			WWPhys::Init();
			wwphys_initialized = true;
			WWSaveLoad::Init();
			wwsaveload_initialized = true;

			Input::Init(true);
			Input::Load_Configuration("DEFAULT_INPUT.CFG");
			A31_Interactive_Configure_Vita_Controls();
			input_initialized = true;
			cServerFps::Create_Instance();
			A30_Vita_Log("A4 breadcrumb: original GameInitMgr SP initialization entry\n");
			GameInitMgrClass::Initialize_SP();
			single_player_transport_initialized = cSinglePlayerData::Is_Single_Player();
			A30_Vita_Log("A4 breadcrumb: original GameInitMgr SP initialized=%d data=%p\n",
				single_player_transport_initialized ? 1 : 0,
				static_cast<void *>(PTheGameData));
			GameModeClass *combat_mode = GameModeManager::Find("Combat");
			if (!single_player_transport_initialized || PTheGameData == NULL || combat_mode == NULL) {
				A30_Vita_Log("A3.1 interactive: game-data/mode FAIL\n");
				break;
			}
			combat_mode->Activate();
			StringClass map_name("M00_Tutorial.mix", true);
			The_Game()->Set_Map_Name(map_name);
			_Force_Link_Soldier();
			cNetwork::Onetime_Init();
			cNetwork::Init_Server();
			cNetwork::Init_Client();
			/*
			 * The original local single-player lane owns this connection.  Keep
			 * the invariant explicit at the platform boundary: a failure here is
			 * an initialization failure, not a reason to dereference a missing
			 * client connection while polling the original handshake.
			 */
			if (cNetwork::PClientConnection == NULL) {
				A30_Vita_Log("A3.1 interactive: original client connection unavailable\n");
				break;
			}
			session_initialized = true;
			CombatManager::Scene_Init();
			const bool render_hud = A31_Interactive_Render_HUD_Available();
			A30_Vita_Log("A3.1 breadcrumb: CombatManager::Init entry render_hud=%d\n",
				render_hud ? 1 : 0);
			CombatManager::Init(render_hud);
			combat_initialized = true;
			A30_Vita_Log("A3.1 breadcrumb: Combat initialized render_hud=%d\n",
				render_hud ? 1 : 0);

			for (unsigned updates = 0U; updates < 120U &&
				!cNetwork::PClientConnection->Is_Established(); ++updates) {
				cNetwork::Update();
			}
			result.transport_established =
				cNetwork::PClientConnection->Is_Established();
			if (!result.transport_established) {
				A30_Vita_Log("A3.1 interactive: original local transport FAIL\n");
				break;
			}
			A30_Vita_Log("A3.1 breadcrumb: original local transport established\n");

			CombatManager::Pre_Load_Level(false);
			NetworkObjectMgrClass::Set_Is_Level_Loading(true);
			CombatManager::Load_Level_Threaded("M00_Tutorial.mix", false);
			while (!CombatManager::Is_Load_Level_Complete()) {
				/* Original ThreadClass performs the level work; this preserves the
				** established CombatManager polling contract. */
			}
			SaveLoadSystemClass::Post_Load_Processing(NULL);
			NetworkObjectMgrClass::Set_Is_Level_Loading(false);
			CombatManager::Post_Load_Level();
			A31_Interactive_Apply_Render_Capabilities();
			if (render_hud) {
				/* Match CombatGameModeClass::Load_Level: RadarManager owns its
				 * Render2D resources after level post-load and before HUD Think. */
				RadarManager::Init();
				RadarManager::Set_Radar_Mode(The_Game()->Get_Radar_Mode());
				radar_initialized = true;
				A30_Vita_Log("A4 breadcrumb: original RadarManager initialized for HUD\n");
			}
			const A31InteractiveHUDState post_load_hud =
				A31_Interactive_Get_HUD_State();
			A30_Vita_Log("A3.1 breadcrumb: post-load HUD serialized=%d resources=%d effective=%d\n",
				post_load_hud.serialized_enabled ? 1 : 0,
				post_load_hud.render_resources_available ? 1 : 0,
				post_load_hud.effectively_displayable ? 1 : 0);
			result.level_loaded = CombatManager::Get_Scene() != NULL;
			if (!result.level_loaded) {
				A30_Vita_Log("A3.1 interactive: original level load FAIL\n");
				break;
			}
			A30_Vita_Log("A3.1 breadcrumb: original M00 level loaded\n");

			WideStringClass local_player_name;
			local_player_name.Convert_From("Renegade");
			cPlayer *local_player = cGod::Create_Player(cNetwork::Get_My_Id(),
				local_player_name, -1, 0);
			result.player_created = local_player != NULL;
			result.player_registered = cPlayerManager::Count() == 1;
			A30_Vita_Log("A3.1 breadcrumb: original player created=%d registered=%d\n",
				result.player_created ? 1 : 0, result.player_registered ? 1 : 0);
			cGod::Think();
			result.commando_created = CombatManager::Get_The_Star() != NULL;
			if (!result.player_created || !result.player_registered ||
				!result.commando_created) {
				A30_Vita_Log("A3.1 interactive: original player creation FAIL player=%d registered=%d commando=%d\n",
					result.player_created ? 1 : 0, result.player_registered ? 1 : 0,
					result.commando_created ? 1 : 0);
				break;
			}

			result.initialized = true;
			A30_Vita_Log("A3.1 breadcrumb: original player/session ready; START exits\n");
			RenegadeVitaRenderer::Reset_Statistics();
			InteractiveTiming timing = {};
			const uint64_t sync_origin = sceKernelGetProcessTimeWide() / 1000ULL;
			while (!Is_Start_Pressed()) {
				const uint64_t frame_begin = sceKernelGetProcessTimeWide();
				WW3D::Sync(static_cast<uint32_t>(
					sceKernelGetProcessTimeWide() / 1000ULL - sync_origin));
				const uint64_t simulation_begin = sceKernelGetProcessTimeWide();
				if (result.frames == 0U) {
					A30_Vita_Log("A3.1 breadcrumb: first original input frame\n");
				}
				A31_Interactive_Run_Simulation_Frame();
				const uint64_t render_begin = sceKernelGetProcessTimeWide();
				if (result.frames == 0U) {
					A30_Vita_Log("A3.1 breadcrumb: first original Combat update\n");
				}

				const A31InteractiveRenderTrace render_trace =
					A31_Interactive_Run_Render_Frame();
				const uint64_t frame_end = sceKernelGetProcessTimeWide();
				timing.Add(static_cast<uint32_t>(simulation_begin - frame_begin),
					static_cast<uint32_t>(render_begin - simulation_begin),
					static_cast<uint32_t>(frame_end - render_begin),
					static_cast<uint32_t>(frame_end - frame_begin));
				if (result.frames == 0U) {
					A30_Vita_Log("A3.1 breadcrumb: interactive render state scene=%p camera=%p star=%p static/dynamic/lights=%u/%u/%u vis=%u/%u camera=(%.3f,%.3f,%.3f) player=(%.3f,%.3f,%.3f) clip=%.3f..%.3f\n",
						reinterpret_cast<void *>(render_trace.scene_pointer),
						reinterpret_cast<void *>(render_trace.camera_pointer),
						reinterpret_cast<void *>(render_trace.star_pointer),
						render_trace.static_object_count,
						render_trace.dynamic_object_count,
						render_trace.static_light_count,
						render_trace.visibility_table_size,
						render_trace.visibility_table_count,
						render_trace.camera_x, render_trace.camera_y, render_trace.camera_z,
						render_trace.player_x, render_trace.player_y, render_trace.player_z,
						render_trace.near_clip, render_trace.far_clip);
					A30_Vita_Log("A3.1 breadcrumb: first render closure scene/camera/star/pre/begin/combat/end/post=%d/%d/%d/%d/%d/%d/%d/%d meshes=%llu vertices=%llu triangles=%llu rejected=%llu unsupported=%llu\n",
						render_trace.scene_available ? 1 : 0,
						render_trace.camera_available ? 1 : 0,
						render_trace.star_available ? 1 : 0,
						render_trace.pre_render_completed ? 1 : 0,
						render_trace.begin_render_completed ? 1 : 0,
						render_trace.combat_render_called ? 1 : 0,
						render_trace.end_render_completed ? 1 : 0,
						render_trace.post_render_completed ? 1 : 0,
						static_cast<unsigned long long>(render_trace.mesh_submissions),
						static_cast<unsigned long long>(render_trace.vertex_submissions),
						static_cast<unsigned long long>(render_trace.triangle_submissions),
						static_cast<unsigned long long>(render_trace.rejected_submissions),
						static_cast<unsigned long long>(render_trace.unsupported_submissions));
				}
				if (!render_trace.end_render_completed ||
					!render_trace.post_render_completed) {
					result.render_error = true;
					A30_Vita_Log("A3.1 interactive: render closure FAIL frame=%u scene/camera/pre/begin/combat/end/post=%d/%d/%d/%d/%d/%d/%d\n",
						result.frames, render_trace.scene_available ? 1 : 0,
						render_trace.camera_available ? 1 : 0,
						render_trace.pre_render_completed ? 1 : 0,
						render_trace.begin_render_completed ? 1 : 0,
						render_trace.combat_render_called ? 1 : 0,
						render_trace.end_render_completed ? 1 : 0,
						render_trace.post_render_completed ? 1 : 0);
					break;
				}
				if (result.frames == 0U &&
					(render_trace.mesh_submissions == 0U ||
						render_trace.vertex_submissions == 0U ||
						render_trace.triangle_submissions == 0U ||
						render_trace.rejected_submissions != 0U ||
						render_trace.unsupported_submissions != 0U)) {
					result.render_error = true;
					A30_Vita_Log("A3.1 interactive: first visible-frame gate FAIL meshes=%llu vertices=%llu triangles=%llu rejected=%llu unsupported=%llu\n",
						static_cast<unsigned long long>(render_trace.mesh_submissions),
						static_cast<unsigned long long>(render_trace.vertex_submissions),
						static_cast<unsigned long long>(render_trace.triangle_submissions),
						static_cast<unsigned long long>(render_trace.rejected_submissions),
						static_cast<unsigned long long>(render_trace.unsupported_submissions));
					break;
				}
				++result.frames;
				Copy_Render_Statistics(result);
				if (!result.first_frame_completed) {
					result.first_frame_completed = true;
					result.first_frame_geometry = true;
					A30_Vita_Log("A3.1 breadcrumb: first original render frame PASS meshes=%u vertices=%u triangles=%u\n",
						result.mesh_submissions, result.vertex_submissions,
						result.triangle_submissions);
				}
		if ((result.frames % kTimingWindowFrames) == 0U) {
			A30_Vita_Log("A3.5 breadcrumb: %u-frame checkpoint PASS\n",
				result.frames);
					Log_Timing_Statistics(timing,
						RenegadeVitaRenderer::Get_Statistics());
					Log_Input_Telemetry();
				}
			}
			Copy_Timing_Statistics(result, timing);
			Log_Timing_Statistics(timing, RenegadeVitaRenderer::Get_Statistics());
			result.clean_exit_requested = !result.render_error;
			if (result.clean_exit_requested) {
				A30_Vita_Log("A3.1 breadcrumb: START exit request detected\n");
			}
		} while (false);

			/* Match CombatGameModeClass::Core_Shutdown for the direct M00 route:
			 * cGod leaves before the level frees static network wrappers, game
			 * objects, and load-on-demand assets. This precedes Radar/Combat
			 * shutdown and keeps the original ownership hierarchy intact. */
			if (result.level_loaded) {
				A30_Vita_Log("A4 breadcrumb: original Combat level unload entry\n");
				cGod::Exit();
				CombatManager::Unload_Level();
				A30_Vita_Log("A4 breadcrumb: original Combat level unload complete\n");
			}
			if (radar_initialized) {
				RadarManager::Shutdown();
				A30_Vita_Log("A4 breadcrumb: original RadarManager shutdown complete\n");
			}
		if (session_initialized) {
			/* Preserve GameInitMgrClass's original session shutdown ordering:
			 * client-goodbye events are drained by NetworkObjectMgr, then the
			 * original server teams and player objects leave before a reload. */
			A30_Vita_Log("A4 breadcrumb: original session teardown entry\n");
			cNetwork::Flush();
			cNetwork::Cleanup_Client();
			cNetwork::Cleanup_Server();
			cPlayerManager::Remove_All();
			cTeamManager::Remove_All();
			NetworkObjectMgrClass::Set_All_Delete_Pending();
			NetworkObjectMgrClass::Delete_Pending();
			cGod::Reset();
			A30_Vita_Log("A4 breadcrumb: original session teardown complete\n");
		}
		if (combat_initialized) {
			A30_Vita_Log("A3.1 breadcrumb: Combat shutdown entry\n");
			CombatManager::Shutdown();
			A30_Vita_Log("A3.1 breadcrumb: Combat shutdown complete\n");
		}
		if (session_initialized) {
			GameInitMgrClass::Shutdown();
			A30_Vita_Log("A4 breadcrumb: original GameInitMgr SP shutdown complete\n");
			cNetwork::Onetime_Shutdown();
			A30_Vita_Log("A3.1 breadcrumb: network shutdown complete\n");
		}
		if (session_initialized) cServerFps::Destroy_Instance();
		if (input_initialized) Input::Shutdown();
	}

	if (asset_manager != NULL) WW3DAssetManager::Delete_This();
	if (path_manager_initialized) PathMgrClass::Shutdown();
	if (math_initialized) WWMath::Shutdown();
	if (wwsaveload_initialized) WWSaveLoad::Shutdown();
	if (ww3d_initialized) {
		WW3D::Shutdown();
		A30_Vita_Log("A3.1 breadcrumb: renderer shutdown complete\n");
	}
	if (wwphys_initialized) WWPhys::Shutdown();
	Log_File_Factory_Statistics();
	_TheFileFactory = previous_read_factory;
	_TheWritingFileFactory = previous_write_factory;
	result.teardown_completed = !result.render_error &&
		WW3DAssetManager::Get_Instance() == NULL && !WW3D::Is_Initted();
	A30_Vita_Log("A3.1 interactive: complete ready=%d transport=%d level=%d player=%d commando=%d frames=%u exit=%d render_error=%d teardown=%d perf_fps=%.3f p50/p95/worst_us=%u/%u/%u\n",
		result.initialized ? 1 : 0, result.transport_established ? 1 : 0,
		result.level_loaded ? 1 : 0, result.player_created ? 1 : 0,
		result.commando_created ? 1 : 0, result.frames,
		result.clean_exit_requested ? 1 : 0, result.render_error ? 1 : 0,
		result.teardown_completed ? 1 : 0,
		static_cast<double>(result.average_fps_milli) / 1000.0,
		result.median_frame_us, result.p95_frame_us, result.worst_frame_us);
	return result;
}
