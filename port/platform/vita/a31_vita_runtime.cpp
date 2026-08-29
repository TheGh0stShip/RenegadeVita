#include "a31_vita_runtime.h"

#include "a30_vita_runtime.h"
#include "a31_interactive_runtime_policy.h"
#include "a31_capture_telemetry.h"
#if defined(RENEGADE_A4_ORIGINAL_FRONTEND)
#include "a4_frontend_lifecycle_boundary.h"
#endif
#include "renegade_cache_health.h"
#include "renegade_file_factory.h"
#include "renegade_miles_runtime_stats.h"
#include "renegade_vita_input_telemetry.h"
#include "renegade_build_identity.h"
#include "ww3d_vita_renderer.h"

#include "assetmgr.h"
#include "assets.h"
#include "campaign.h"
#include "chunkio.h"
#include "combat.h"
#include "combatgmode.h"
#include "cnetwork.h"
#include "d3d8.h"
#include "datasafe.h"
#include "debug.h"
#include "definitionfactorymgr.h"
#include "ffactory.h"
#include "ffactorylist.h"
#include "gamedata.h"
#include "gameinitmgr.h"
#include "gamemode.h"
#if defined(RENEGADE_A4_ORIGINAL_FRONTEND)
#include "dialogmgr.h"
#include "gamemenu.h"
#include "movie.h"
#include "renegadedialogmgr.h"
#endif
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
#include "render2d.h"
#include "render2dsentence.h"
#include "saveload.h"
#include "saveloadstatus.h"
#include "serverfps.h"
#include "singlepl.h"
#include "scripts.h"
#include "scene.h"
#include "stylemgr.h"
#include "teammanager.h"
#include "textdisplay.h"
#include "textwindow.h"
#include "timemgr.h"
#include "textureloader.h"
#include "menubackdrop.h"
#include "translatedb.h"
#include "ww3d.h"
#include "wwaudio.h"
#include "wwmath.h"
#include "wwphys.h"
#include "wwsaveload.h"

#include <psp2/ctrl.h>
#include <psp2/kernel/processmgr.h>
#include <psp2/kernel/threadmgr.h>

#include <debugScreen.h>

#include <new>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

extern void _Force_Link_Soldier(void);
extern void *Commando_Create_Original_Loading_Screen(void);
extern void Commando_Render_Original_Loading_Screen(void *screen, bool update_network);
extern bool Commando_Original_Loading_Screen_Has_Backdrop_Model(void *screen);
extern void Commando_Destroy_Original_Loading_Screen(void *screen);

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
const char *const kStringsDatabase = "STRINGS.TDB";
const char *const kStyleManagerIni = "stylemgr.ini";
const char *const kM01CacheIndex = "cache/m01-mix-index-v1.txt";
const uint32_t kTimingWindowFrames = 120U;
const uint32_t kCaptureWidth = RenegadeVitaRenderer::DISPLAY_WIDTH;
const uint32_t kCaptureHeight = RenegadeVitaRenderer::DISPLAY_HEIGHT;
const uint32_t kCaptureBytes = kCaptureWidth * kCaptureHeight * 4U;
const unsigned kAutomaticCaptureAttempts = 3U;
const unsigned kStartupPrecacheVisibleSteps = 5U;
const uint64_t kStartupPrecacheMinimumVisibleUs = 5000000ULL;
const unsigned kLoadingPrewarmFrames = 8U;
const unsigned kM00ScenePrewarmFrames = 60U;
const int kCncMultiplayerLoadBackdropNumber = 94;
const float kOriginalLoadingLogicalWidth = 640.0f;
const float kOriginalLoadingLogicalHeight = 480.0f;
const float kOriginalHUDLogicalWidth = 640.0f;
const float kOriginalHUDLogicalHeight = 480.0f;

struct A31StartupPrecacheResult
{
	bool passed;
	unsigned archives_valid;
	unsigned archives_total;
	unsigned entries_indexed;
	unsigned files_touched;
	unsigned files_opened;
	unsigned movie_files_touched;
	unsigned movie_files_opened;
	uint64_t bytes_read;
};

/* Original Commando gives WWAudio a path-stripping factory over the active
** retail/MIX chain. Keep the same semantic boundary here so authoring paths
** such as always\\sound\\... resolve to the basename stored in the archives.
** This adapter and WWAudio are declared after the chain, so audio teardown
** returns every file before the stack-local factories are destroyed. */
class A31AudioFileFactoryClass final : public SimpleFileFactoryClass
{
public:
	explicit A31AudioFileFactoryClass(FileFactoryClass *base_factory) :
		BaseFactory(base_factory)
	{
	}

	FileClass *Get_File(char const *filename) override
	{
		if (BaseFactory == NULL || filename == NULL) return NULL;
		StringClass stripped(true);
		Strip_Path_From_Filename(stripped, filename);
		return BaseFactory->Get_File(stripped);
	}

private:
	FileFactoryClass *BaseFactory;
};

bool Load_Strings_Database_For_Loading_Screen()
{
	TranslateDBClass::Initialize();
	FileClass *file = _TheFileFactory != NULL ? _TheFileFactory->Get_File(kStringsDatabase) : NULL;
	if (file == NULL) {
		A30_Vita_Log("A3.5 loading screen: FAIL strings database file unavailable name=%s\n",
			kStringsDatabase);
		return false;
	}

	bool loaded = false;
	if (file->Open(FileClass::READ)) {
		if (file->Is_Available()) {
			ChunkLoadClass cload(file);
			loaded = SaveLoadSystemClass::Load(cload);
		}
		file->Close();
	}
	_TheFileFactory->Return_File(file);
	A30_Vita_Log("A3.5 loading screen: strings database load=%d name=%s version=%lu\n",
		loaded ? 1 : 0, kStringsDatabase,
		static_cast<unsigned long>(TranslateDBClass::Get_Version_Number()));
	return loaded;
}

void Draw_Startup_Precache_Screen(int startup_screen_result, const char *phase,
	unsigned step, unsigned percent, const A31StartupPrecacheResult &state,
	const char *detail)
{
	if (startup_screen_result < 0) return;
	if (percent > 100U) percent = 100U;
	psvDebugScreenClear(0x102030);
	psvDebugScreenSetFgColor(0xFFFFFF);
	psvDebugScreenPrintf("%s\n", RENEGADE_BUILD_DISPLAY_LABEL);
	psvDebugScreenPrintf("Pre-cache / pre-warm / pre-compute\n\n");
	psvDebugScreenPrintf("Phase %u/%u: %s\n", step,
		kStartupPrecacheVisibleSteps, phase != NULL ? phase : "unknown");
	psvDebugScreenPrintf("[");
	const unsigned filled = percent / 5U;
	for (unsigned index = 0U; index < 20U; ++index) {
		psvDebugScreenPrintf(index < filled ? "#" : ".");
	}
	psvDebugScreenPrintf("] %u%%\n\n", percent);
	psvDebugScreenPrintf("Original MIX archives: %u/%u\n",
		state.archives_valid, state.archives_total);
	psvDebugScreenPrintf("Indexed entries:       %u\n", state.entries_indexed);
	psvDebugScreenPrintf("Startup files:         %u/%u\n",
		state.files_opened, state.files_touched);
	psvDebugScreenPrintf("Movie files:           %u/%u\n",
		state.movie_files_opened, state.movie_files_touched);
	psvDebugScreenPrintf("Bytes touched:         %llu\n",
		static_cast<unsigned long long>(state.bytes_read));
	if (detail != NULL && detail[0] != 0) {
		psvDebugScreenPrintf("Now:                   %s\n", detail);
	}
	psvDebugScreenPrintf("\nThis runs before intro movies, menus, and M00 input.\n");
	psvDebugScreenPrintf("Log: %s\n", RENEGADE_BUILD_RUNTIME_LOG_PATH);
}

bool Startup_Index_Mix_Archive(const char *name, MixFileFactoryClass &factory,
	A31StartupPrecacheResult &state)
{
	++state.archives_total;
	DynamicVectorClass<StringClass> names;
	names.Set_Growth_Step(1000);
	const bool listed = factory.Is_Valid() && factory.Build_Filename_List(names);
	const unsigned count = listed && names.Count() > 0 ?
		static_cast<unsigned>(names.Count()) : 0U;
	if (count != 0U) {
		++state.archives_valid;
		state.entries_indexed += count;
	}
	A30_Vita_Log("A3.5 prewarm: startup-precache archive=%s valid=%d listed=%d entries=%u retained_factory=1 original_mix_owner=1\n",
		name != NULL ? name : "unknown", factory.Is_Valid() ? 1 : 0,
		listed ? 1 : 0, count);
	return count != 0U;
}

void Startup_Touch_File(FileFactoryClass &factory, const char *name,
	A31StartupPrecacheResult &state)
{
	++state.files_touched;
	const bool movie_file = name != NULL && ::strstr(name, "MOVIES") != NULL;
	if (movie_file) {
		++state.movie_files_touched;
	}
	unsigned read_bytes = 0U;
	bool opened = false;
	FileClass *file = factory.Get_File(name);
	if (file != NULL && file->Open(FileClass::READ)) {
		opened = true;
		char buffer[512];
		for (unsigned remaining = 2048U; remaining != 0U;) {
			const unsigned request = remaining < sizeof(buffer) ?
				remaining : static_cast<unsigned>(sizeof(buffer));
			const int received = file->Read(buffer, request);
			if (received <= 0) break;
			read_bytes += static_cast<unsigned>(received);
			remaining -= static_cast<unsigned>(received);
			if (static_cast<unsigned>(received) != request) break;
		}
		file->Close();
	}
	if (file != NULL) {
		factory.Return_File(file);
	}
	if (opened) {
		++state.files_opened;
		state.bytes_read += read_bytes;
		if (movie_file) {
			++state.movie_files_opened;
		}
	}
	A30_Vita_Log("A3.5 prewarm: startup-precache touch name=%s opened=%d read_bytes=%u original_file_factory=1\n",
		name != NULL ? name : "unknown", opened ? 1 : 0, read_bytes);
}

bool Run_Visible_Startup_Precache_Phase(int startup_screen_result,
	FileFactoryClass &factory, MixFileFactoryClass &always2_factory,
	MixFileFactoryClass &always_dbs_factory, MixFileFactoryClass &always_factory,
	MixFileFactoryClass &m00_factory)
{
	A31StartupPrecacheResult state = {};
	const uint64_t started_us = sceKernelGetProcessTimeWide();
	A30_Vita_Log("A3.5 prewarm: startup-precache begin visible=%d before_frontend=1 before_movies=1 before_gameplay=1 input_enabled=0\n",
		startup_screen_result >= 0 ? 1 : 0);
	Draw_Startup_Precache_Screen(startup_screen_result,
		"Indexing original retail MIX archives", 1U, 5U, state,
		"Always/Always2/always.dbs/M00");
	sceKernelDelayThread(300000);

	bool archives_ok = true;
	archives_ok = Startup_Index_Mix_Archive(kAlways2Archive, always2_factory,
		state) && archives_ok;
	Draw_Startup_Precache_Screen(startup_screen_result,
		"Indexing original retail MIX archives", 2U, 25U, state,
		kAlways2Archive);
	sceKernelDelayThread(250000);
	archives_ok = Startup_Index_Mix_Archive(kAlwaysDbsArchive,
		always_dbs_factory, state) && archives_ok;
	archives_ok = Startup_Index_Mix_Archive(kAlwaysArchive, always_factory,
		state) && archives_ok;
	Draw_Startup_Precache_Screen(startup_screen_result,
		"Precomputing archive name tables", 3U, 50U, state,
		kAlwaysArchive);
	sceKernelDelayThread(250000);
	archives_ok = Startup_Index_Mix_Archive(kM00Archive, m00_factory, state) &&
		archives_ok;

	const char *const required_files[] = {
		kStringsDatabase,
		kStyleManagerIni,
		"DEFAULT_INPUT.CFG",
		"if_lvl94load.w3d",
		"IF_BACK01.W3D",
		"IF_RENLOGO.W3D",
		"IF_EVAGIZMO.W3D",
		"M00_Tutorial.lsd",
		"M00_Tutorial.ldd",
		"m00_tutorial.dep",
		"DATA\\MOVIES\\EA_WW.BIK",
		"DATA\\MOVIES\\R_INTRO.BIK"
	};
	for (unsigned index = 0U;
		index < sizeof(required_files) / sizeof(required_files[0]); ++index) {
		Startup_Touch_File(factory, required_files[index], state);
		if ((index % 3U) == 2U || index + 1U ==
			sizeof(required_files) / sizeof(required_files[0])) {
			char detail[96];
			snprintf(detail, sizeof(detail), "%s", required_files[index]);
			Draw_Startup_Precache_Screen(startup_screen_result,
				"Touching startup menu, movie, loading, and M00 files",
				4U, 55U + ((index + 1U) * 35U) /
					(sizeof(required_files) / sizeof(required_files[0])),
				state, detail);
			sceKernelDelayThread(180000);
		}
	}
	state.passed = archives_ok && state.archives_valid == state.archives_total &&
		state.files_opened >= 8U;
	Draw_Startup_Precache_Screen(startup_screen_result,
		state.passed ? "Startup pre-cache complete" :
			"Startup pre-cache incomplete", 5U, 100U, state,
		state.passed ? "starting original intro/menu" :
			"continuing only if required archives are present");
	const uint64_t after_work_us = sceKernelGetProcessTimeWide();
	if (startup_screen_result >= 0 &&
		after_work_us - started_us < kStartupPrecacheMinimumVisibleUs) {
		const uint64_t hold_us =
			kStartupPrecacheMinimumVisibleUs - (after_work_us - started_us);
		A30_Vita_Log("A3.5 prewarm: startup-precache visible hold remaining_ms=%llu minimum_ms=%llu\n",
			static_cast<unsigned long long>(hold_us / 1000ULL),
			static_cast<unsigned long long>(
				kStartupPrecacheMinimumVisibleUs / 1000ULL));
		sceKernelDelayThread(static_cast<unsigned int>(hold_us));
	} else {
		sceKernelDelayThread(450000);
	}
	A30_Vita_Log("A3.5 prewarm: startup-precache complete pass=%d archives=%u/%u entries=%u files=%u/%u movie_files=%u/%u bytes=%llu elapsed_ms=%llu visible_minimum_ms=%llu before_frontend=1 before_movies=1 before_gameplay=1 original_mix_owner=1\n",
		state.passed ? 1 : 0, state.archives_valid, state.archives_total,
		state.entries_indexed, state.files_opened, state.files_touched,
		state.movie_files_opened, state.movie_files_touched,
		static_cast<unsigned long long>(state.bytes_read),
		static_cast<unsigned long long>(
			(sceKernelGetProcessTimeWide() - started_us) / 1000ULL),
		static_cast<unsigned long long>(
			kStartupPrecacheMinimumVisibleUs / 1000ULL));
	return state.passed;
}

class A31VitaScopedLoadingRenderResolution
{
public:
	A31VitaScopedLoadingRenderResolution() :
		PreviousWidth(0),
		PreviousHeight(0),
		PreviousBits(0),
		PreviousWindowed(false),
		Applied(false)
	{
		WW3D::Get_Device_Resolution(PreviousWidth, PreviousHeight,
			PreviousBits, PreviousWindowed);
		Applied = WW3D::Set_Device_Resolution(
			static_cast<int>(kOriginalLoadingLogicalWidth),
			static_cast<int>(kOriginalLoadingLogicalHeight), -1, -1,
			false) == WW3D_ERROR_OK;
		A30_Vita_Log("A3.5 loading screen: original logical WW3D/DX8/Render2D resolution %.0fx%.0f over Vita display %ux%u applied=%d previous=%dx%d\n",
			kOriginalLoadingLogicalWidth, kOriginalLoadingLogicalHeight,
			kCaptureWidth, kCaptureHeight, Applied ? 1 : 0,
			PreviousWidth, PreviousHeight);
	}

	~A31VitaScopedLoadingRenderResolution()
	{
		if (Applied) {
			const int previous_windowed = PreviousWindowed ? 1 : 0;
			WW3D::Set_Device_Resolution(PreviousWidth, PreviousHeight,
				PreviousBits, previous_windowed, false);
		}
		A30_Vita_Log("A3.5 loading screen: restored Vita WW3D/DX8/Render2D resolution %dx%d applied=%d\n",
			PreviousWidth, PreviousHeight, Applied ? 1 : 0);
	}

	A31VitaScopedLoadingRenderResolution(const A31VitaScopedLoadingRenderResolution &) = delete;
	A31VitaScopedLoadingRenderResolution &operator=(const A31VitaScopedLoadingRenderResolution &) = delete;

private:
	int PreviousWidth;
	int PreviousHeight;
	int PreviousBits;
	bool PreviousWindowed;
	bool Applied;
};

class A31VitaScopedOriginalHUDRender2DResolution
{
public:
	explicit A31VitaScopedOriginalHUDRender2DResolution(const char *reason) :
		Previous(Render2DClass::Get_Screen_Resolution()),
		Reason(reason != NULL ? reason : "unknown")
	{
		Render2DClass::Set_Screen_Resolution(RectClass(0, 0,
			kOriginalHUDLogicalWidth, kOriginalHUDLogicalHeight));
		A30_Vita_Log("A3.5 HUD: original logical Render2D resolution %.0fx%.0f reason=%s previous=%.0fx%.0f\n",
			kOriginalHUDLogicalWidth, kOriginalHUDLogicalHeight, Reason,
			Previous.Width(), Previous.Height());
	}

	~A31VitaScopedOriginalHUDRender2DResolution()
	{
		Render2DClass::Set_Screen_Resolution(Previous);
		A30_Vita_Log("A3.5 HUD: restored Render2D resolution %.0fx%.0f reason=%s\n",
			Previous.Width(), Previous.Height(), Reason);
	}

	A31VitaScopedOriginalHUDRender2DResolution(
		const A31VitaScopedOriginalHUDRender2DResolution &) = delete;
	A31VitaScopedOriginalHUDRender2DResolution &operator=(
		const A31VitaScopedOriginalHUDRender2DResolution &) = delete;

private:
	RectClass Previous;
	const char *Reason;
};

void Copy_Renderer_Statistics(A31RendererTelemetry &telemetry)
{
	const RenegadeVitaRenderer::Statistics &statistics =
		RenegadeVitaRenderer::Get_Statistics();
	telemetry.draw_calls = static_cast<uint64_t>(statistics.mesh_submissions) +
		static_cast<uint64_t>(statistics.indexed_submissions);
	telemetry.mesh_submissions = statistics.mesh_submissions;
	telemetry.vertices = statistics.vertex_submissions;
	telemetry.triangles = statistics.triangle_submissions;
	telemetry.indexed_draw_calls = statistics.indexed_submissions;
	telemetry.indexed_vertex_references = statistics.indexed_vertex_references;
	telemetry.indexed_triangles = statistics.indexed_triangle_submissions;
	telemetry.material_passes = statistics.material_passes;
	telemetry.textures_resident = statistics.texture_resident;
	telemetry.texture_bytes_resident = statistics.texture_bytes_resident;
	telemetry.texture_uploads = statistics.texture_uploads;
	telemetry.texture_binds = statistics.texture_binds;
	telemetry.texture_requests = statistics.texture_requests;
	telemetry.texture_decodes = statistics.texture_decodes;
	telemetry.texture_dds_loads = statistics.texture_dds_loads;
	telemetry.texture_tga_loads = statistics.texture_tga_loads;
	telemetry.texture_missing = statistics.texture_missing;
	telemetry.texture_source_missing = statistics.texture_source_missing;
	telemetry.texture_invalid_data = statistics.texture_invalid_data;
	telemetry.texture_unsupported_formats = statistics.texture_unsupported_formats;
	telemetry.texture_decode_failures = statistics.texture_decode_failures;
	telemetry.texture_upload_failures = statistics.texture_upload_failures;
	telemetry.texture_checkerboard_fallbacks = statistics.texture_checkerboard_fallbacks;
	telemetry.texture_checkerboard_binds = statistics.texture_checkerboard_binds;
	telemetry.texture_invalid_binds = statistics.texture_invalid_binds;
	telemetry.state_changes = statistics.state_changes;
	telemetry.rejected_submissions = statistics.rejected_indexed_submissions;
	telemetry.unsupported_submissions = statistics.unsupported_submissions;
	telemetry.backend_errors = statistics.backend_errors;
	telemetry.geometry_checksum = statistics.geometry_checksum;
	telemetry.indexed_geometry_checksum = statistics.indexed_geometry_checksum;
}

class A31VitaLoadingPresenter
{
public:
	A31VitaLoadingPresenter() :
		Screen(NULL),
		BackdropReady(false),
		LastMirroredLoadProgress(-1)
	{
	}

	~A31VitaLoadingPresenter()
	{
		Commando_Destroy_Original_Loading_Screen(Screen);
		Screen = NULL;
	}

	bool Initialize()
	{
		CampaignManager::Select_Backdrop_Number(kCncMultiplayerLoadBackdropNumber);
		const int description_count = CampaignManager::Get_Backdrop_Description_Count();
		StringClass selected_model(0, true);
		for (int index = 0; index < description_count; ++index) {
			StringClass desc = CampaignManager::Get_Backdrop_Description(index);
			while (desc.Get_Length() != 0 && desc[0] <= ' ') desc.Erase(0, 1);
			while (desc.Get_Length() != 0 && desc[desc.Get_Length() - 1] <= ' ') {
				desc.Erase(desc.Get_Length() - 1, 1);
			}
			if (::strnicmp("Model", desc, 5) == 0) {
				desc.Erase(0, 5);
				while (desc.Get_Length() != 0 && desc[0] <= ' ') desc.Erase(0, 1);
				selected_model = desc;
			}
		}
		Screen = Commando_Create_Original_Loading_Screen();
		BackdropReady =
			Commando_Original_Loading_Screen_Has_Backdrop_Model(Screen);
		A30_Vita_Log("A3.5 loading screen: original class state=%d descriptions=%d model=%s ready=%d direct_vitagl_tiles=0 progress_owner=original_LoadingScreenClass\n",
			kCncMultiplayerLoadBackdropNumber, description_count,
			selected_model.Get_Length() != 0 ?
				static_cast<const char *>(selected_model) : "none",
			BackdropReady ? 1 : 0);
		return Screen != NULL && BackdropReady;
	}

	void *Peek_Screen() const
	{
		return Screen;
	}

	void Render_Original_Progress(const char *phase, bool update_network = true,
		int minimum_progress = -1)
	{
		StringClass load_status;
		StringClass load_sub_status;
		SaveLoadStatus::Get_Status_Text(load_status, 0);
		SaveLoadStatus::Get_Status_Text(load_sub_status, 1);
		const int status_count = SaveLoadStatus::Get_Status_Count();
		const int current_progress = CombatManager::Get_Load_Progress();
		int mirrored_progress = current_progress;
		if (status_count > mirrored_progress) mirrored_progress = status_count;
		if (minimum_progress > mirrored_progress) mirrored_progress = minimum_progress;
		if (mirrored_progress > current_progress) {
			CombatManager::Set_Load_Progress(mirrored_progress);
		}
		Commando_Render_Original_Loading_Screen(Screen, update_network);
		if (LastMirroredLoadProgress != mirrored_progress ||
			phase == NULL ||
			::strstr(phase, "complete") != NULL ||
			::strstr(phase, "ready") != NULL ||
			::strstr(phase, "prewarm") != NULL) {
			LastMirroredLoadProgress = mirrored_progress;
		}
		A30_Vita_Log("A3.5 loading screen: phase=%s original_class=1 original_backdrop=%d progress=%d status_count=%d status=%s sub_status=%s\n",
			phase != NULL ? phase : "unknown", BackdropReady ? 1 : 0,
			CombatManager::Get_Load_Progress(), status_count,
			static_cast<const char *>(load_status),
			static_cast<const char *>(load_sub_status));
	}

private:
	void *Screen;
	bool BackdropReady;
	int LastMirroredLoadProgress;
};

	A31StateSnapshot Make_Interactive_Capture_State(const A31InteractiveRenderTrace &trace,
		uint64_t frame, uint64_t monotonic_us, const char *reason)
	{
	A31StateSnapshot state = {};
	state.schema_version = A31_CAPTURE_SCHEMA_VERSION;
	snprintf(state.milestone, sizeof(state.milestone), "%s", RENEGADE_BUILD_CANDIDATE_LABEL);
	snprintf(state.build_label, sizeof(state.build_label), "%s", RENEGADE_BUILD_DISPLAY_LABEL);
	snprintf(state.capture_overlay_label, sizeof(state.capture_overlay_label), "%s", RENEGADE_BUILD_CAPTURE_OVERLAY);
	snprintf(state.runtime_log_path, sizeof(state.runtime_log_path), "%s", RENEGADE_BUILD_RUNTIME_LOG_PATH);
	snprintf(state.reason, sizeof(state.reason), "%s", reason);
	snprintf(state.phase, sizeof(state.phase), "%s", "interactive-player-owned");
	state.capture_monotonic_us = monotonic_us;
	state.capture_frame = frame;
	state.world.loaded = trace.scene_available;
	state.world.static_object_count = trace.static_object_count;
	state.world.dynamic_object_count = trace.dynamic_object_count;
	state.world.light_count = trace.static_light_count;
	state.world.vis_sector_count = trace.visibility_table_count;
	state.camera.present = trace.camera_available;
	state.camera.original_camera_class = trace.camera_available;
	state.camera.player_owned = trace.camera_available && trace.star_available;
	state.camera.position[0] = trace.camera_x;
	state.camera.position[1] = trace.camera_y;
	state.camera.position[2] = trace.camera_z;
	state.camera.near_clip = trace.near_clip;
	state.camera.far_clip = trace.far_clip;
	state.player.present = trace.star_available;
	state.player.object_id = trace.player_object_id;
	snprintf(state.player.definition, sizeof(state.player.definition), "%s",
		trace.player_definition);
	snprintf(state.player.type, sizeof(state.player.type), "%s", "SoldierGameObj");
	state.player.position[0] = trace.player_x;
	state.player.position[1] = trace.player_y;
	state.player.position[2] = trace.player_z;
	for (unsigned index = 0U; index < 4U; ++index) {
		state.player.orientation[index] = trace.player_orientation[index];
	}
	for (unsigned index = 0U; index < 3U; ++index) {
		state.player.velocity[index] = trace.player_velocity[index];
	}
	state.player.health = trace.player_health;
	state.player.physics_registered = trace.player_physics_registered;
	state.player.grounded = trace.player_grounded;
	Copy_Renderer_Statistics(state.renderer);
	if (state.renderer.draw_calls == 0U) {
		state.renderer.draw_calls = trace.mesh_submissions;
		state.renderer.mesh_submissions = trace.mesh_submissions;
		state.renderer.vertices = trace.vertex_submissions;
		state.renderer.triangles = trace.triangle_submissions;
		state.renderer.rejected_submissions = trace.rejected_submissions;
		state.renderer.unsupported_submissions = trace.unsupported_submissions;
	}
	state.game_update_count = frame;
	state.physics_update_count = frame;
	state.input_action_count = Renegade_Vita_Last_Input_Telemetry().sample_count;
	state.scripts_active = ScriptManager::Is_Provider_Active()
		&& ScriptManager::Get_Active_Script_Count() > 0;
	return state;
}

A31StateSnapshot Make_Loading_Capture_State(uint64_t monotonic_us, const char *reason)
{
	A31StateSnapshot state = {};
	state.schema_version = A31_CAPTURE_SCHEMA_VERSION;
	snprintf(state.milestone, sizeof(state.milestone), "%s", RENEGADE_BUILD_CANDIDATE_LABEL);
	snprintf(state.build_label, sizeof(state.build_label), "%s", RENEGADE_BUILD_DISPLAY_LABEL);
	snprintf(state.capture_overlay_label, sizeof(state.capture_overlay_label), "%s", RENEGADE_BUILD_CAPTURE_OVERLAY);
	snprintf(state.runtime_log_path, sizeof(state.runtime_log_path), "%s", RENEGADE_BUILD_RUNTIME_LOG_PATH);
	snprintf(state.reason, sizeof(state.reason), "%s", reason != NULL ? reason : "unknown");
	snprintf(state.phase, sizeof(state.phase), "%s", "original-loading-screen");
	state.capture_monotonic_us = monotonic_us;
	state.world.loaded = CombatManager::Get_Scene() != NULL;
	Copy_Renderer_Statistics(state.renderer);
	state.loading_visual_gate.active = true;
	state.loading_visual_gate.framebuffer_width = kCaptureWidth;
	state.loading_visual_gate.framebuffer_height = kCaptureHeight;
	state.loading_visual_gate.original_logical_width =
		static_cast<uint32_t>(kOriginalLoadingLogicalWidth);
	state.loading_visual_gate.original_logical_height =
		static_cast<uint32_t>(kOriginalLoadingLogicalHeight);
	state.loading_visual_gate.native_display_width = RenegadeVitaRenderer::DISPLAY_WIDTH;
	state.loading_visual_gate.native_display_height = RenegadeVitaRenderer::DISPLAY_HEIGHT;
	state.loading_visual_gate.logical_to_native_fullscreen = true;
	state.loading_visual_gate.original_loading_screen_owner = true;
	state.loading_visual_gate.direct_vitagl_overlay_disabled = true;
	state.loading_visual_gate.loading_texture_v_flip_enabled = true;
	state.loading_visual_gate.gameplay_texture_v_unchanged = true;
	state.scripts_active = ScriptManager::Is_Provider_Active()
		&& ScriptManager::Get_Active_Script_Count() > 0;
	return state;
}

bool Apply_Original_Gameplay_Render_Resolution(const char *reason = "startup",
	bool log_state = true)
{
	const bool applied = WW3D::Set_Device_Resolution(
		static_cast<int>(RenegadeVitaRenderer::DISPLAY_WIDTH),
		static_cast<int>(RenegadeVitaRenderer::DISPLAY_HEIGHT), -1, -1, false) == WW3D_ERROR_OK;
	int width = 0;
	int height = 0;
	int bits = 0;
	bool windowed = false;
	WW3D::Get_Device_Resolution(width, height, bits, windowed);
	if (log_state) {
		A30_Vita_Log("A3.5 HUD: native Vita gameplay/HUD render resolution reason=%s requested=%ux%u current=%dx%d bits=%d windowed=%d applied=%d\n",
			reason != NULL ? reason : "unknown",
			RenegadeVitaRenderer::DISPLAY_WIDTH,
			RenegadeVitaRenderer::DISPLAY_HEIGHT, width, height, bits,
			windowed ? 1 : 0, applied ? 1 : 0);
	}
	return applied && width == static_cast<int>(RenegadeVitaRenderer::DISPLAY_WIDTH) &&
		height == static_cast<int>(RenegadeVitaRenderer::DISPLAY_HEIGHT);
}

bool Apply_Original_Loading_Render_Resolution_For_Prewarm(unsigned frame,
	bool log_state)
{
	const bool applied = WW3D::Set_Device_Resolution(
		static_cast<int>(kOriginalLoadingLogicalWidth),
		static_cast<int>(kOriginalLoadingLogicalHeight), -1, -1, false) == WW3D_ERROR_OK;
	int width = 0;
	int height = 0;
	int bits = 0;
	bool windowed = false;
	WW3D::Get_Device_Resolution(width, height, bits, windowed);
	if (log_state) {
		A30_Vita_Log("A3.5 prewarm: loading presenter overlay resolution frame=%u requested=%.0fx%.0f current=%dx%d bits=%d windowed=%d native=%ux%u applied=%d\n",
			frame, kOriginalLoadingLogicalWidth,
			kOriginalLoadingLogicalHeight, width, height, bits,
			windowed ? 1 : 0, RenegadeVitaRenderer::DISPLAY_WIDTH,
			RenegadeVitaRenderer::DISPLAY_HEIGHT, applied ? 1 : 0);
	}
	return applied && width == static_cast<int>(kOriginalLoadingLogicalWidth) &&
		height == static_cast<int>(kOriginalLoadingLogicalHeight);
}

void Warm_Original_M00_Presentation_Cache(A31VitaLoadingPresenter &loading_presenter)
{
	SaveLoadStatus::Set_Status_Text("Prewarming loading cache", 0);
	CombatManager::Set_Load_Progress(7);
	for (unsigned frame = 0U; frame < kLoadingPrewarmFrames; ++frame) {
		TextureLoader::Update(IS_SOLOPLAY ? NULL : &cNetwork::Update);
		A31_Interactive_Apply_Render_Capabilities();
		loading_presenter.Render_Original_Progress("prewarm_renderer_cache",
			true, 7);
		sceKernelDelayThread(16666);
	}
	const RenegadeVitaRenderer::Statistics &statistics =
		RenegadeVitaRenderer::Get_Statistics();
	A30_Vita_Log("A3.5 prewarm: loading-screen-owned frames=%u textures=%u uploads=%u binds=%u shader_cache=ux0:data/renegade/cache/vitagl-shader-cache state_changes=%u backend_errors=%u\n",
		kLoadingPrewarmFrames,
		statistics.texture_resident, statistics.texture_uploads,
		statistics.texture_binds, statistics.state_changes,
		statistics.backend_errors);
}

bool Warm_Original_M00_Interactive_Presentation_Cache(
	A31VitaLoadingPresenter &loading_presenter, WWAudioClass *audio)
{
	SaveLoadStatus::Set_Status_Text("Prewarming M00 scene cache", 0);
	CombatManager::Set_Load_Progress(7);
	const uint64_t prewarm_started_us = sceKernelGetProcessTimeWide();
	A30_Vita_Log("A3.5 prewarm: m00-scene start frames=%u input_enabled=0 simulation_frames=0 status=%s\n",
		kM00ScenePrewarmFrames, "Prewarming M00 scene cache");

	A31InteractiveRenderTrace last_trace = {};
	bool rendered_scene = false;
	for (unsigned frame = 0U; frame < kM00ScenePrewarmFrames; ++frame) {
		TextureLoader::Update(IS_SOLOPLAY ? NULL : &cNetwork::Update);
		if (!Apply_Original_Gameplay_Render_Resolution("prewarm_m00_scene",
			frame == 0U)) {
			A30_Vita_Log("A3.5 prewarm: FAIL native gameplay resolution before scene frame=%u\n",
				frame);
			return false;
		}
		WW3D::Sync(static_cast<uint32_t>(
			(sceKernelGetProcessTimeWide() - prewarm_started_us) / 1000ULL));
		A31_Interactive_Apply_Render_Capabilities();
		last_trace = A31_Interactive_Run_Render_Frame();
		rendered_scene = rendered_scene ||
			(last_trace.begin_render_completed &&
			 last_trace.combat_render_called &&
			 last_trace.end_render_completed);
		if (audio != NULL) audio->On_Frame_Update(0);
		if (!Apply_Original_Loading_Render_Resolution_For_Prewarm(frame,
			frame == 0U || frame + 1U == kM00ScenePrewarmFrames)) {
			A30_Vita_Log("A3.5 prewarm: FAIL loading overlay resolution after scene frame=%u\n",
				frame);
			return false;
		}
		loading_presenter.Render_Original_Progress("prewarm_m00_scene",
			true, 7);
		if (frame == 0U || frame + 1U == kM00ScenePrewarmFrames ||
			((frame + 1U) % 15U) == 0U) {
			A30_Vita_Log("A3.5 prewarm: m00-scene frame=%u/%u scene=%d camera=%d star=%d begin/combat/end=%d/%d/%d meshes=%llu vertices=%llu triangles=%llu rejected=%llu unsupported=%llu\n",
				frame + 1U, kM00ScenePrewarmFrames,
				last_trace.scene_available ? 1 : 0,
				last_trace.camera_available ? 1 : 0,
				last_trace.star_available ? 1 : 0,
				last_trace.begin_render_completed ? 1 : 0,
				last_trace.combat_render_called ? 1 : 0,
				last_trace.end_render_completed ? 1 : 0,
				static_cast<unsigned long long>(last_trace.mesh_submissions),
				static_cast<unsigned long long>(last_trace.vertex_submissions),
				static_cast<unsigned long long>(last_trace.triangle_submissions),
				static_cast<unsigned long long>(last_trace.rejected_submissions),
				static_cast<unsigned long long>(last_trace.unsupported_submissions));
		}
		sceKernelDelayThread(16667);
	}
	if (!Apply_Original_Gameplay_Render_Resolution("prewarm_m00_scene_complete",
		true)) {
		A30_Vita_Log("A3.5 prewarm: FAIL native gameplay resolution after scene prewarm\n");
		return false;
	}
	const RenegadeVitaRenderer::Statistics &statistics =
		RenegadeVitaRenderer::Get_Statistics();
	A30_Vita_Log("A3.5 prewarm: m00-scene complete rendered=%d frames=%u elapsed_ms=%llu textures=%u uploads=%u binds=%u state_changes=%u shader_cache=ux0:data/renegade/cache/vitagl-shader-cache backend_errors=%u\n",
		rendered_scene ? 1 : 0, kM00ScenePrewarmFrames,
		static_cast<unsigned long long>(
			(sceKernelGetProcessTimeWide() - prewarm_started_us) / 1000ULL),
		statistics.texture_resident, statistics.texture_uploads,
		statistics.texture_binds, statistics.state_changes,
		statistics.backend_errors);
	return rendered_scene;
}

void Log_Interactive_Player_Effects(const A31InteractiveRenderTrace &trace,
	uint32_t frame, const char *reason)
{
	A30_Vita_Log("A3.5 effects: reason=%s frame=%u player=%u definition=%s state=%s position=(%.3f,%.3f,%.3f) velocity=(%.3f,%.3f,%.3f) health=%.3f physics=%d grounded=%d first_person=%d weapon=%s/%u rounds=%d/%d fired_total=%u weapon_state=%d triggered/fired=%d/%d action_count/active/busy=%u/%d/%d control action/reload=%d/%d input action/reload/use/camera/prev/next/zoom/objectives=%d/%d/%d/%d/%d/%d/%d/%d/%d physical square/triangle/select/circle/cross/l/r/front/dpad_udlr=%d/%d/%d/%d/%d/%d/%d/%d/%d/%d/%d/%d key action/reload/camera/prev/next/zoom/objectives=%u/%u/%u/%u/%u/%u/%u/%u buttons=%08X\n",
		reason, frame, trace.player_object_id, trace.player_definition,
		trace.player_state, trace.player_x, trace.player_y, trace.player_z,
		trace.player_velocity[0], trace.player_velocity[1],
		trace.player_velocity[2], trace.player_health,
		trace.player_physics_registered ? 1 : 0,
		trace.player_grounded ? 1 : 0,
		trace.first_person_active ? 1 : 0,
		trace.weapon_present ? trace.weapon_definition : "none",
		trace.weapon_definition_id, trace.weapon_total_rounds,
		trace.weapon_clip_rounds, trace.weapon_total_rounds_fired,
		trace.weapon_state, trace.weapon_triggered ? 1 : 0,
		trace.weapon_fired_this_frame ? 1 : 0, trace.action_act_count,
		trace.action_active ? 1 : 0, trace.action_busy ? 1 : 0,
		trace.control_action_active ? 1 : 0,
		trace.control_reload_active ? 1 : 0,
		trace.input_action_active ? 1 : 0,
		trace.input_reload_active ? 1 : 0,
		trace.input_use_weapon_active ? 1 : 0,
			trace.input_first_person_toggle_active ? 1 : 0,
			trace.input_previous_weapon_active ? 1 : 0,
			trace.input_next_weapon_active ? 1 : 0,
			trace.input_zoom_in_active ? 1 : 0,
			trace.input_zoom_out_active ? 1 : 0,
			trace.input_objectives_toggle_active ? 1 : 0,
			trace.input_square_down ? 1 : 0,
		trace.input_triangle_down ? 1 : 0,
		trace.input_select_down ? 1 : 0,
		trace.input_circle_down ? 1 : 0,
		trace.input_cross_down ? 1 : 0,
		trace.input_left_shoulder_down ? 1 : 0,
		trace.input_right_shoulder_down ? 1 : 0,
		trace.input_front_touch_down ? 1 : 0,
		trace.input_dpad_up_down ? 1 : 0,
		trace.input_dpad_down_down ? 1 : 0,
		trace.input_dpad_left_down ? 1 : 0,
		trace.input_dpad_right_down ? 1 : 0,
		trace.input_action_key_state, trace.input_reload_key_state,
			trace.input_camera_toggle_key_state,
			trace.input_previous_weapon_key_state,
			trace.input_next_weapon_key_state,
			trace.input_zoom_in_key_state,
			trace.input_zoom_out_key_state,
			trace.input_objectives_toggle_key_state,
			trace.input_buttons);
}

bool Mission_Progress_Changed(const A31MissionProgressState &left,
	const A31MissionProgressState &right)
{
	if (left.star_available != right.star_available ||
		left.player_control_enabled != right.player_control_enabled ||
		left.objective_count != right.objective_count ||
		left.active_conversation_count != right.active_conversation_count ||
		left.active_conversation_id != right.active_conversation_id ||
		left.active_conversation_state != right.active_conversation_state ||
		left.active_conversation_action_id != right.active_conversation_action_id ||
		left.active_conversation_current_remark !=
			right.active_conversation_current_remark ||
		left.active_conversation_remark_count !=
			right.active_conversation_remark_count ||
		left.active_conversation_text_id !=
			right.active_conversation_text_id ||
		left.active_conversation_sound_id !=
			right.active_conversation_sound_id ||
		left.active_conversation_string_available !=
			right.active_conversation_string_available ||
		left.active_conversation_sound_definition_available !=
			right.active_conversation_sound_definition_available ||
		left.active_conversation_speech_source !=
			right.active_conversation_speech_source ||
		left.active_conversation_speech_class_id !=
			right.active_conversation_speech_class_id ||
		left.active_conversation_speech_type !=
			right.active_conversation_speech_type ||
		left.active_conversation_speech_state !=
			right.active_conversation_speech_state ||
		left.active_conversation_speech_duration_ms !=
			right.active_conversation_speech_duration_ms ||
		left.active_conversation_speaker_available !=
			right.active_conversation_speaker_available ||
		left.active_conversation_speech_available !=
			right.active_conversation_speech_available ||
		left.active_conversation_speech_in_scene !=
			right.active_conversation_speech_in_scene ||
		left.active_conversation_speech_culled !=
			right.active_conversation_speech_culled ||
		left.active_conversation_speech_playing !=
			right.active_conversation_speech_playing ||
		strcmp(left.active_conversation_name,
			right.active_conversation_name) != 0) {
		return true;
	}
	for (unsigned index = 0U; index < 6U; ++index) {
		if (left.objective_status[index] != right.objective_status[index]) {
			return true;
		}
	}
	return false;
}

void Log_Mission_Progress(const A31MissionProgressState &progress,
	const A31InteractiveRenderTrace &trace, uint32_t frame)
{
	A30_Vita_Log("A3.5 mission progress: frame=%u star/control=%d/%d objectives=%u status_1_6=%d/%d/%d/%d/%d/%d active_conversations=%u active=%s id/state/action/remark/count=%d/%d/%d/%d/%d text/sound/str/def=%d/%d/%d/%d next_seconds=%.3f speech=speaker:%d src:%d present/scene/culled/playing=%d/%d/%d/%d class/type/state=%d/%d/%d dur/dropoff/dist=%u/%.3f/%.3f player=(%.3f,%.3f,%.3f)\n",
		frame, progress.star_available ? 1 : 0,
		progress.player_control_enabled ? 1 : 0, progress.objective_count,
		progress.objective_status[0], progress.objective_status[1],
		progress.objective_status[2], progress.objective_status[3],
		progress.objective_status[4], progress.objective_status[5],
		progress.active_conversation_count,
		progress.active_conversation_name[0] != '\0' ?
			progress.active_conversation_name : "none",
		progress.active_conversation_id, progress.active_conversation_state,
		progress.active_conversation_action_id,
		progress.active_conversation_current_remark,
		progress.active_conversation_remark_count,
		progress.active_conversation_text_id,
		progress.active_conversation_sound_id,
		progress.active_conversation_string_available ? 1 : 0,
		progress.active_conversation_sound_definition_available ? 1 : 0,
		progress.active_conversation_next_remark_seconds,
		progress.active_conversation_speaker_available ? 1 : 0,
		progress.active_conversation_speech_source,
		progress.active_conversation_speech_available ? 1 : 0,
		progress.active_conversation_speech_in_scene ? 1 : 0,
		progress.active_conversation_speech_culled ? 1 : 0,
		progress.active_conversation_speech_playing ? 1 : 0,
		progress.active_conversation_speech_class_id,
		progress.active_conversation_speech_type,
		progress.active_conversation_speech_state,
		progress.active_conversation_speech_duration_ms,
		progress.active_conversation_speech_dropoff_radius,
		progress.active_conversation_speech_listener_distance,
		trace.player_x, trace.player_y, trace.player_z);
}

	A31CaptureBundleResult Capture_Interactive_Frame(const A31StateSnapshot &state,
		const A31FrameHistory &history, const uint8_t *pixels, const char *label)
	{
	A31CaptureBundleInput input = {};
	input.base_directory = RENEGADE_BUILD_CAPTURE_ROOT;
	input.bundle_label = label;
	input.resolved_rgba_bottom_up = pixels;
	input.framebuffer_width = kCaptureWidth;
	input.framebuffer_height = kCaptureHeight;
	input.write_annotated_screenshot = pixels != NULL;
	input.state = state;
	input.history = &history;
	return A31_Write_Capture_Bundle(input);
}

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
	A30_Vita_Log("A3.5 perf: frames=%u rolling_samples=%u avg_fps=%.3f frame_us min/p50/p95/max=%u/%u/%u/%u slow_over_33ms=%u stage_us sync/sim/render=%u/%u/%u draws meshes=%u triangles=%u textures req/decode/upload/bind/missing=%llu/%llu/%llu/%llu/%llu loaded_dds/tga=%llu/%llu source/invalid/unsupported/decode/upload_fail/checker/checker_bind/invalid_bind=%llu/%llu/%llu/%llu/%llu/%llu/%llu/%llu state_changes=%llu backend_errors=%llu\n",
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
		static_cast<unsigned long long>(renderer.texture_dds_loads),
		static_cast<unsigned long long>(renderer.texture_tga_loads),
		static_cast<unsigned long long>(renderer.texture_source_missing),
		static_cast<unsigned long long>(renderer.texture_invalid_data),
		static_cast<unsigned long long>(renderer.texture_unsupported_formats),
		static_cast<unsigned long long>(renderer.texture_decode_failures),
		static_cast<unsigned long long>(renderer.texture_upload_failures),
		static_cast<unsigned long long>(renderer.texture_checkerboard_fallbacks),
		static_cast<unsigned long long>(renderer.texture_checkerboard_binds),
		static_cast<unsigned long long>(renderer.texture_invalid_binds),
		static_cast<unsigned long long>(renderer.state_changes),
		static_cast<unsigned long long>(renderer.backend_errors));
	A30_Vita_Log("A3.5 skin: submissions=%u deformed_vertices=%u deformation_failures=%u\n",
		renderer.skinned_mesh_submissions, renderer.deformed_skin_vertices,
		renderer.skin_deformation_failures);
	A30_Vita_Log("A3.5 indexed: submissions=%u triangles=%u state_applications=%llu rejected=%u\n",
		renderer.indexed_submissions, renderer.indexed_triangle_submissions,
		static_cast<unsigned long long>(renderer.indexed_state_applications),
		renderer.rejected_indexed_submissions);
}

void Log_Input_Telemetry()
{
	const RenegadeVitaInputTelemetry &input = Renegade_Vita_Last_Input_Telemetry();
	A30_Vita_Log("A3.5 input: samples=%llu raw lx/ly/rx/ry=%u/%u/%u/%u normalized=%.3f/%.3f/%.3f/%.3f logical=%ld/%ld/%ld/%ld mouse_delta=%ld/%ld dt=%.4f buttons=%08X physical square/triangle/select/circle/cross/l/r/front/dpad_udlr=%u/%u/%u/%u/%u/%u/%u/%u/%u/%u/%u/%u key action/reload/camera/prev/next/zoom/objectives=%u/%u/%u/%u/%u/%u/%u/%u route_mode/active/index/count/truncated=%u/%u/%u/%u/%u\n",
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
		static_cast<double>(input.frame_seconds), input.buttons,
		input.square_down, input.triangle_down, input.select_down,
		input.circle_down, input.cross_down, input.left_shoulder_down,
		input.right_shoulder_down, input.front_touch_down,
		input.dpad_up_down, input.dpad_down_down,
		input.dpad_left_down, input.dpad_right_down,
		input.action_key_state, input.reload_key_state,
		input.camera_toggle_key_state, input.previous_weapon_key_state,
		input.next_weapon_key_state, input.zoom_in_key_state,
		input.zoom_out_key_state, input.objectives_toggle_key_state,
		input.route_mode, input.route_gameplay_active,
		input.route_sample_index, input.route_sample_count,
		input.route_truncated);
	}

void Log_Audio_Runtime_Statistics(const char *reason, uint32_t frame)
{
	RenegadeMilesRuntimeStats stats = {};
	Renegade_Miles_Get_Runtime_Stats(&stats);
	WWAudioClass *audio = WWAudioClass::Get_Instance();
	const float dialog_volume = audio != NULL ? audio->Get_Dialog_Volume() : -1.0F;
	const float cinematic_volume = audio != NULL ? audio->Get_Cinematic_Volume() : -1.0F;
	A30_Vita_Log("A3.5 audio: reason=%s frame=%u output_start=%u/%u/%u output_written/fail=%u/%u output_stream=buffers:%llu frames:%llu nonzero:%llu peak:%u last_output_stream=active/frames/nonzero/peak:%u/%u/%u/%u sample_file=%u/%u/%u sample_3d=%u/%u/%u stream=%u/%u/%u stream_start=%u/%u/%u/%u stream_bytes/frames=%llu/%llu stream_mix=buffers:%llu frames:%llu nonzero:%llu peak:%u last_stream_mix=active/frames/nonzero/peak:%u/%u/%u/%u last_stream=%s frames/fact/estimate/untrimmed/trimmed/rate/vol/pan=%u/%u/%u/%u/%u/%u/%u/%u starts=%u/%u/%u mix=buffers:%llu frames:%llu nonzero:%llu peak:%u allocated/active/streams=%u/%u/%u active_stream=pos/len/cursor/frames/loops/vol/pan=%u/%u/%u/%u/%u/%u/%u volumes_dialog/cinematic=%.3f/%.3f last_error=%s\n",
		reason != NULL ? reason : "unknown", frame,
		stats.output_start_attempts, stats.output_start_successes,
		stats.output_start_failures, stats.output_buffers_written,
		stats.output_write_failures,
		static_cast<unsigned long long>(stats.output_stream_buffers_written),
		static_cast<unsigned long long>(stats.output_stream_frames_written),
		static_cast<unsigned long long>(stats.output_stream_nonzero_buffers_written),
		stats.output_stream_peak_abs,
		stats.last_output_stream_active, stats.last_output_stream_frames,
		stats.last_output_stream_nonzero, stats.last_output_stream_peak_abs,
		stats.sample_file_load_attempts, stats.sample_file_load_successes,
		stats.sample_file_load_failures,
		stats.sample_3d_file_load_attempts,
		stats.sample_3d_file_load_successes,
		stats.sample_3d_file_load_failures,
		stats.stream_open_attempts, stats.stream_open_successes,
		stats.stream_open_failures,
		stats.stream_start_attempts, stats.stream_start_successes,
		stats.stream_start_silent, stats.stream_start_zero_volume,
		static_cast<unsigned long long>(stats.stream_bytes_read),
		static_cast<unsigned long long>(stats.stream_decoded_frames),
		static_cast<unsigned long long>(stats.stream_mixed_buffers),
		static_cast<unsigned long long>(stats.stream_mixed_frames),
		static_cast<unsigned long long>(stats.stream_mixed_nonzero_buffers),
		stats.stream_mixed_peak_abs,
		stats.last_stream_mix_active, stats.last_stream_mix_frames,
		stats.last_stream_mix_nonzero, stats.last_stream_mix_peak_abs,
		stats.last_stream_name[0] != '\0' ? stats.last_stream_name : "none",
		stats.last_stream_frames, stats.last_stream_fact_frames,
		stats.last_stream_estimated_frames,
		stats.last_stream_untrimmed_frames,
		stats.last_stream_trimmed_frames, stats.last_stream_rate,
		stats.last_stream_volume, stats.last_stream_pan,
		stats.sample_start_attempts, stats.sample_start_successes,
		stats.sample_start_silent,
		static_cast<unsigned long long>(stats.mixed_buffers),
		static_cast<unsigned long long>(stats.mixed_frames),
		static_cast<unsigned long long>(stats.mixed_nonzero_buffers),
		stats.mixed_peak_abs,
		stats.allocated_samples, stats.active_samples, stats.active_streams,
		stats.active_stream_position_ms, stats.active_stream_length_ms,
		stats.active_stream_cursor_frame, stats.active_stream_total_frames,
		stats.active_stream_loop_count, stats.active_stream_volume,
		stats.active_stream_pan,
		static_cast<double>(dialog_volume),
		static_cast<double>(cinematic_volume),
		stats.last_error[0] != '\0' ? stats.last_error : "none");
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
	return (sceCtrlPeekBufferPositive(0, &controller, 1) > 0 &&
			(controller.buttons & SCE_CTRL_START) != 0U) ||
		Renegade_Vita_Input_Route_Replay_Exit_Requested();
}

#if defined(RENEGADE_A4_ORIGINAL_FRONTEND)
bool Run_Original_Frontend_Intro_And_Menu(MenuGameModeClass2 &menu_mode,
	MovieGameModeClass &movie_mode, WWAudioClass *audio)
{
	A4_Frontend_Reset_Trace();
	A4_Frontend_Begin_Menu_Loop();
	Input::Menu_Enable(true);
	RenegadeDialogMgrClass::Initialize();
	GameModeManager::Add(&menu_mode);
	GameModeManager::Add(&movie_mode);
	movie_mode.Activate();
	movie_mode.Startup_Movies();
	A30_Vita_Log("A4 frontend: original MovieGameMode startup sequence entered; Bink provider owns decode or per-movie fail-closed skip\n");

	unsigned frontend_frame = 0U;
	while (!A4_Frontend_Exit_Requested() &&
		!A4_Frontend_Get_Trace().tutorial_start_latched) {
		if (frontend_frame == 0U) A30_Vita_Log("A4 frontend: first menu loop frame entry\n");
		TimeManager::Update();
		if (frontend_frame == 0U) A30_Vita_Log("A4 frontend: first menu loop after TimeManager::Update\n");
		Input::Update();
		if (frontend_frame == 0U) A30_Vita_Log("A4 frontend: first menu loop after Input::Update\n");
		A4_Frontend_Pump_WWUI_Key_Transitions();
		if (frontend_frame == 0U) A30_Vita_Log("A4 frontend: first menu loop after WWUI key pump\n");
		GameModeManager::Think();
		if (frontend_frame == 0U) A30_Vita_Log("A4 frontend: first menu loop after GameModeManager::Think\n");
		GameInitMgrClass::Think();
		if (frontend_frame == 0U) A30_Vita_Log("A4 frontend: first menu loop after GameInitMgrClass::Think\n");
		DialogMgrClass::On_Frame_Update();
		if (frontend_frame == 0U) A30_Vita_Log("A4 frontend: first menu loop after DialogMgrClass::On_Frame_Update\n");
		GameModeManager::Render();
		if (frontend_frame == 0U) A30_Vita_Log("A4 frontend: first menu loop after GameModeManager::Render\n");
		if (audio != NULL) audio->On_Frame_Update(0);
		if (frontend_frame == 0U) A30_Vita_Log("A4 frontend: first menu loop after WWAudio On_Frame_Update\n");
		++frontend_frame;
		sceKernelDelayThread(16667);
	}

	const A4FrontendTrace trace = A4_Frontend_Get_Trace();
	const bool tutorial_selected = trace.tutorial_start_latched &&
		stricmp(trace.tutorial_map, "M00_Tutorial.mix") == 0;
	A30_Vita_Log("A4 frontend: menu loop exit latched=%d map=%s movie_play/skip=%u/%u last_movie=%s exit=%d code=%d\n",
		trace.tutorial_start_latched ? 1 : 0,
		trace.tutorial_map[0] != '\0' ? trace.tutorial_map : "none",
		trace.movie_play_requests, trace.movie_skip_requests,
		trace.last_movie[0] != '\0' ? trace.last_movie : "none",
		trace.exit_requested ? 1 : 0, trace.exit_code);

	if (!movie_mode.Is_Inactive()) {
		movie_mode.Deactivate();
	}
	if (!menu_mode.Is_Inactive()) {
		menu_mode.Deactivate();
	}
	GameModeManager::Safely_Deactivate();
	GameModeManager::Remove(&movie_mode);
	if (tutorial_selected) {
		A30_Vita_Log("A4 frontend: retained original Menu mode through Combat handoff\n");
	} else {
		GameModeManager::Remove(&menu_mode);
	}
	RenegadeDialogMgrClass::Shutdown();
	Input::Menu_Enable(false);
	A4_Frontend_End_Menu_Loop();
	return tutorial_selected;
}
#endif

} // namespace

A31VitaInteractiveResult A31_Vita_Run_Interactive_Runtime(
	int startup_screen_result)
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
	const bool startup_precache_ok = Run_Visible_Startup_Precache_Phase(
		startup_screen_result, factory_list, always2_factory,
		always_dbs_factory, always_factory, m00_factory);
	if (startup_screen_result >= 0) {
		psvDebugScreenFinish();
	}
	if (!startup_precache_ok) {
		A30_Vita_Log("A3.5 prewarm: FAIL startup precache/precompute phase before frontend\n");
		result.render_error = true;
		Log_File_Factory_Statistics();
		_TheFileFactory = previous_read_factory;
		_TheWritingFileFactory = previous_write_factory;
		return result;
	}

	bool math_initialized = false;
	bool path_manager_initialized = false;
	bool ww3d_initialized = false;
	bool wwphys_initialized = false;
	bool wwsaveload_initialized = false;
	bool translatedb_initialized = false;
	bool stylemgr_initialized = false;
		bool input_initialized = false;
			bool combat_initialized = false;
			bool campaign_initialized = false;
			bool mission_completion_observer_installed = false;
			bool text_display_initialized = false;
			bool text_window_scene_initialized = false;
		bool radar_initialized = false;
		bool session_initialized = false;
		bool single_player_transport_initialized = false;
		bool audio_teardown_completed = false;
			WW3DAssetManager *asset_manager = NULL;
			TextDebugDisplayHandlerClass text_display_handler;
			TextDisplayGameModeClass text_display_mode;
#if defined(RENEGADE_A4_ORIGINAL_FRONTEND)
			CombatGameModeClass frontend_combat_mode;
			bool frontend_combat_mode_registered = false;
			MenuGameModeClass2 frontend_menu_mode;
			MovieGameModeClass frontend_movie_mode;
			bool frontend_menu_mode_registered_for_handoff = false;
#endif

	{
		/* Match original Commando ownership.  WWAudio must see the installed
		** retail/MIX chain and must be destroyed after the Combat session but
		** before asset, renderer, physics, and factory teardown. */
		A31AudioFileFactoryClass audio_file_factory(&factory_list);
		A30_Vita_Log("A3.1 breadcrumb: application audio construction entry singleton=%p\n",
			static_cast<void *>(WWAudioClass::Get_Instance()));
		Renegade_Miles_Reset_Runtime_Stats();
		WWAudioClass application_audio(false);
		application_audio.Initialize();
		application_audio.Set_File_Factory(&audio_file_factory);
		WWAudioClass *audio = &application_audio;
		A30_Vita_Log("Alpha direct M00: original audio initialized over path-stripped Vita retail provider; entering original tutorial runtime\n");

		A30_Vita_Log("A3.1 interactive: begin original Commando/Combat session\n");
		const RenegadeCacheHealth cache_health = Renegade_Inspect_Mix_Index_Cache(
			kVitaRoots, "M01.mix", kM01CacheIndex);
		A30_Vita_Log("A3.6 cache health: state=%s archive=%s entries=%u detail=%s path=%s; original MIX route unchanged\n",
			Renegade_Cache_Health_Name(cache_health.state), cache_health.archive,
			cache_health.entry_count, cache_health.detail, cache_health.physical_path);
		if (WWAudioClass::Get_Instance() != audio || audio->Get_Sound_Scene() == NULL ||
			audio->Get_2D_Driver() == NULL || audio->Get_3D_Driver() == 0U) {
			A30_Vita_Log("A3.5 interactive: FAIL original WWAudio/Vita provider unavailable singleton=%p sound_scene=%p driver2d=%p driver3d=%lu\n",
				static_cast<void *>(audio),
				audio != NULL ? static_cast<void *>(audio->Get_Sound_Scene()) : NULL,
				audio != NULL ? static_cast<void *>(audio->Get_2D_Driver()) : NULL,
				audio != NULL ? static_cast<unsigned long>(audio->Get_3D_Driver()) : 0UL);
			Log_File_Factory_Statistics();
			_TheFileFactory = previous_read_factory;
			_TheWritingFileFactory = previous_write_factory;
			return result;
		}
		A30_Vita_Log("A3.1 breadcrumb: audio/session construction singleton=%p sound_scene=%p\n",
			static_cast<void *>(audio), static_cast<void *>(audio->Get_Sound_Scene()));
		Log_Audio_Runtime_Statistics("post-initialize", 0U);
		{
		RenegadeCheatMgrClass cheat_manager;
		A31FrameHistory *capture_history = new (std::nothrow) A31FrameHistory;
		uint8_t *capture_pixels = NULL;
		bool first_interactive_capture_pending = true;
		unsigned first_interactive_capture_attempts = 0U;
		uint32_t current_pause_input_frames = 0U;
		bool select_was_pressed = false;
		A31InteractiveRenderTrace last_render_trace = {};
		A31MissionProgressState last_mission_progress = {};
		bool mission_progress_recorded = false;
		bool tutorial_control_ready_observed = false;
		do {
			if (capture_history == NULL) {
				A30_Vita_Log("A3.5 capture: FAIL frame history heap allocation unavailable\n");
				break;
			}
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
			if (!Apply_Original_Gameplay_Render_Resolution()) {
				A30_Vita_Log("A3.5 HUD: FAIL native gameplay/HUD render resolution unavailable\n");
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
			if (!Load_Strings_Database_For_Loading_Screen()) {
				A30_Vita_Log("A3.5 loading screen: FAIL original strings database initialization\n");
				break;
			}
			translatedb_initialized = true;
			StyleMgrClass::Initialize_From_INI(kStyleManagerIni);
			stylemgr_initialized = true;
			if (StyleMgrClass::Peek_Font(StyleMgrClass::FONT_INGAME_TXT) == NULL ||
				StyleMgrClass::Peek_Font(StyleMgrClass::FONT_INGAME_BIG_TXT) == NULL) {
				A30_Vita_Log("A3.5 loading screen: FAIL original StyleMgr in-game fonts unavailable ini=%s normal=%p big=%p\n",
					kStyleManagerIni,
					static_cast<void *>(StyleMgrClass::Peek_Font(StyleMgrClass::FONT_INGAME_TXT)),
					static_cast<void *>(StyleMgrClass::Peek_Font(StyleMgrClass::FONT_INGAME_BIG_TXT)));
				break;
			}
				A30_Vita_Log("A3.5 loading screen: original StyleMgr initialized ini=%s normal_font=%p big_font=%p\n",
					kStyleManagerIni,
					static_cast<void *>(StyleMgrClass::Peek_Font(StyleMgrClass::FONT_INGAME_TXT)),
					static_cast<void *>(StyleMgrClass::Peek_Font(StyleMgrClass::FONT_INGAME_BIG_TXT)));
				Input::Init(true);
				Input::Load_Configuration("DEFAULT_INPUT.CFG");
				A31_Interactive_Configure_Vita_Controls();
				input_initialized = true;
					CampaignManager::Init();
					campaign_initialized = true;
					A30_Vita_Log("A3.5 loading screen: original CampaignManager catalog initialized\n");
#if defined(RENEGADE_A4_ORIGINAL_FRONTEND)
					if (GameModeManager::Find("Combat") == NULL) {
						GameModeManager::Add(&frontend_combat_mode);
						frontend_combat_mode_registered = true;
						A30_Vita_Log("A4 frontend: registered original CombatGameMode owner for menu/direct M00 route\n");
					}
					{
						const bool frontend_tutorial_selected =
							Run_Original_Frontend_Intro_And_Menu(frontend_menu_mode,
								frontend_movie_mode, audio);
						frontend_menu_mode_registered_for_handoff =
							frontend_tutorial_selected &&
							GameModeManager::Find("Menu") == &frontend_menu_mode;
						stylemgr_initialized = false;
						if (!frontend_tutorial_selected) {
							result.clean_exit_requested = A4_Frontend_Exit_Requested();
							A30_Vita_Log("A4 frontend: menu exited without supported tutorial selection; direct M00 route not entered\n");
							break;
						}
						StyleMgrClass::Initialize_From_INI(kStyleManagerIni);
						stylemgr_initialized = true;
						A30_Vita_Log("A4 frontend: original StyleMgr reinitialized for direct M00 loading screen after menu shutdown\n");
						if (StyleMgrClass::Peek_Font(StyleMgrClass::FONT_INGAME_TXT) == NULL ||
							StyleMgrClass::Peek_Font(StyleMgrClass::FONT_INGAME_BIG_TXT) == NULL) {
							A30_Vita_Log("A4 frontend: FAIL StyleMgr fonts unavailable after menu handoff normal=%p big=%p\n",
								static_cast<void *>(StyleMgrClass::Peek_Font(StyleMgrClass::FONT_INGAME_TXT)),
								static_cast<void *>(StyleMgrClass::Peek_Font(StyleMgrClass::FONT_INGAME_BIG_TXT)));
							break;
						}
					}
#endif
				{
					A31VitaScopedOriginalHUDRender2DResolution text_display_resolution(
						"TextDisplayGameModeClass::Init");
					text_display_mode.Init();
				}
				text_display_initialized =
					TextDisplayGameModeClass::Get_Instance() == &text_display_mode;
				if (text_display_initialized) {
					DebugManager::Set_Display_Handler(&text_display_handler);
				}
				A30_Vita_Log("A3.5 text display: original TextDisplayGameMode init after final StyleMgr=%d handler=%d\n",
					text_display_initialized ? 1 : 0,
					text_display_initialized ? 1 : 0);
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
				{
					A31VitaScopedOriginalHUDRender2DResolution hud_init_resolution(
						"CombatManager::Init");
					CombatManager::Init(render_hud);
				}
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

			/* Match CombatGameModeClass::Load_Level at the existing misc-handler
			** seam. The adapter observes only callbacks generated by original
				** Combat/Mission00 code. */
				A31_Interactive_Begin_Mission_Completion_Observation();
				mission_completion_observer_installed = true;
				CombatManager::Set_Load_Progress(0);
				A31VitaScopedLoadingRenderResolution loading_render_resolution;
				A31VitaLoadingPresenter loading_presenter;
			if (!loading_presenter.Initialize()) {
				result.render_error = true;
				A30_Vita_Log("A3.5 loading screen: FAIL original MenuBackDrop model unavailable\n");
				break;
			}
			loading_presenter.Render_Original_Progress("before_pre_load");
			CombatGameModeClass::Vita_Begin_Level_Load(
				loading_presenter.Peek_Screen(), true);
			loading_presenter.Render_Original_Progress("after_combatgmode_begin_load");
			/* The direct Vita runtime has a real WW3D presentation backend even
			** while the full HUD remains independently gated.  Passing false here
			** prevented the original BackgroundMgr from constructing SkyClass and
			** its Haze/Starfield/CloudLayer/SkyObject children, so no indexed sky
			** draw could ever reach the platform boundary.  Match the original
			** non-exclusive CombatGameMode load contract for world rendering. */
			CombatManager::Pre_Load_Level(true);
			loading_presenter.Render_Original_Progress("after_pre_load");
			A30_Vita_Log("A3.5 background: original render_available=1\n");
			NetworkObjectMgrClass::Set_Is_Level_Loading(true);
			TextureLoader::Suspend_Texture_Load();
			A30_Vita_Log("A3.5 texture loader: suspended during threaded M00 load\n");
			CombatManager::Load_Level_Threaded("M00_Tutorial.mix", false);
			int last_load_progress = -1;
			int last_load_status_count = -1;
			StringClass last_load_sub_status;
			const uint64_t load_started_us = sceKernelGetProcessTimeWide();
			uint64_t last_load_log_us = load_started_us;
			while (!CombatManager::Is_Load_Level_Complete()) {
				/* Original ThreadClass performs the level work; this preserves the
				** established CombatManager polling contract. Report only progress
				** changes or one heartbeat per ten seconds. */
				const int load_progress = CombatManager::Get_Load_Progress();
				const uint64_t now_us = sceKernelGetProcessTimeWide();
				StringClass load_sub_status;
				SaveLoadStatus::Get_Status_Text(load_sub_status, 1);
				const int load_status_count = SaveLoadStatus::Get_Status_Count();
				loading_presenter.Render_Original_Progress("threaded_load");
				if (load_progress != last_load_progress ||
					load_status_count != last_load_status_count ||
					load_sub_status != static_cast<const char *>(last_load_sub_status) ||
					now_us - last_load_log_us >= 10000000ULL) {
					StringClass load_status;
					SaveLoadStatus::Get_Status_Text(load_status, 0);
					A30_Vita_Log("A3.1 M00 load: progress=%d status=%s sub_status=%s chunks=%d elapsed_ms=%llu\n",
						load_progress, static_cast<const char *>(load_status),
						static_cast<const char *>(load_sub_status), load_status_count,
						static_cast<unsigned long long>((now_us - load_started_us) / 1000ULL));
					last_load_progress = load_progress;
					last_load_status_count = load_status_count;
					last_load_sub_status = load_sub_status;
					last_load_log_us = now_us;
				}
				sceKernelDelayThread(50000);
			}
			loading_presenter.Render_Original_Progress("threaded_load_complete");
			A30_Vita_Log("A3.1 M00 load: threaded load complete progress=%d elapsed_ms=%llu\n",
				CombatManager::Get_Load_Progress(),
				static_cast<unsigned long long>(
					(sceKernelGetProcessTimeWide() - load_started_us) / 1000ULL));
			GenericDataSafeClass::Set_Preferred_Thread(GetCurrentThreadId());
			TextureLoader::Continue_Texture_Load();
			loading_presenter.Render_Original_Progress("texture_load_continued");
			A30_Vita_Log("A3.5 texture loader: continued before post-load processing\n");
			loading_presenter.Render_Original_Progress("post_load_processing");
			SaveLoadSystemClass::Post_Load_Processing(NULL);
				NetworkObjectMgrClass::Set_Is_Level_Loading(false);
				loading_presenter.Render_Original_Progress("post_load_level");
				CombatManager::Post_Load_Level();
				{
					A31VitaScopedOriginalHUDRender2DResolution hud_finalize_resolution(
						"CombatGameModeClass::Vita_Finalize_Loaded_Level");
					CombatGameModeClass::Vita_Finalize_Loaded_Level(
						loading_presenter.Peek_Screen(), true);
				}
				radar_initialized = true;
				A30_Vita_Log("A3.5 CombatGameMode: original post-load finalization complete radar_initialized=1\n");
				Warm_Original_M00_Presentation_Cache(loading_presenter);
				loading_presenter.Render_Original_Progress("level_ready", true, 7);
				if (capture_pixels == NULL) {
					capture_pixels = static_cast<uint8_t *>(malloc(kCaptureBytes));
				}
				const uint64_t loading_capture_us = sceKernelGetProcessTimeWide();
				const bool loading_readback = capture_pixels != NULL &&
					RenegadeVitaRenderer::Capture_Resolved_Frame_RGBA(capture_pixels, kCaptureBytes);
				A31FrameTelemetry loading_capture_frame = {};
				loading_capture_frame.frame_index = 0U;
				loading_capture_frame.monotonic_us = loading_capture_us;
				Copy_Renderer_Statistics(loading_capture_frame.renderer);
				capture_history->Reset();
				capture_history->Push(loading_capture_frame);
				char loading_capture_label[96];
				snprintf(loading_capture_label, sizeof(loading_capture_label),
					"original-loading-screen-level-ready-t%llu",
					static_cast<unsigned long long>(loading_capture_us));
				const A31StateSnapshot loading_capture_state =
					Make_Loading_Capture_State(loading_capture_us, "level-ready");
				const A31CaptureBundleResult loading_capture = Capture_Interactive_Frame(
					loading_capture_state, *capture_history,
					loading_readback ? capture_pixels : NULL, loading_capture_label);
				A30_Vita_Log("Capture: %s candidate=%s phase=original-loading-screen reason=level-ready path=%s screenshot/state/csv/summary=%d/%d/%d/%d error_code=%d\n",
					loading_capture.passed ? "PASS" : "FAIL",
					RENEGADE_BUILD_CANDIDATE_LABEL, loading_capture.bundle_path,
					loading_capture.screenshot_written ? 1 : 0,
					loading_capture.state_written ? 1 : 0,
					loading_capture.history_written ? 1 : 0,
					loading_capture.summary_written ? 1 : 0,
					loading_capture.first_error_code);
				capture_history->Reset();
				if (!Apply_Original_Gameplay_Render_Resolution(
					"post-loading-capture", true)) {
					result.render_error = true;
					A30_Vita_Log("A3.5 HUD: FAIL native gameplay/HUD resolution after loading capture\n");
					break;
				}
				A31_Interactive_Apply_Render_Capabilities();
				if (render_hud && CombatManager::Get_Background_Scene() != NULL) {
					TextWindowClass::Initialize(CombatManager::Get_Background_Scene());
					text_window_scene_initialized = true;
					A30_Vita_Log("A3.5 text window: original scene binding initialized for message/objective HUD scene=%p\n",
						static_cast<void *>(CombatManager::Get_Background_Scene()));
				}
				A30_Vita_Log("A3.5 scripts: provider_active=%d registered=%d active=%d\n",
					ScriptManager::Is_Provider_Active() ? 1 : 0,
					Get_Script_Count(), ScriptManager::Get_Active_Script_Count());
			A30_Vita_Log("A4 breadcrumb: original RadarManager initialized by CombatGameMode finalization for HUD=%d\n",
				render_hud ? 1 : 0);
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
			CombatManager::Set_First_Person_Default(true);
			CombatManager::Set_First_Person(true);
			A30_Vita_Log("A3.5 camera: original first-person default restored for direct M00 route first_person=%d\n",
				CombatManager::Is_First_Person() ? 1 : 0);
			if (!Warm_Original_M00_Interactive_Presentation_Cache(
				loading_presenter, audio)) {
				result.render_error = true;
				A30_Vita_Log("A3.5 prewarm: FAIL M00 interactive scene warmup before first input\n");
				break;
			}

				result.initialized = true;
				A30_Vita_Log("A3.1 breadcrumb: original player/session ready; original mission completion or START exits\n");
				RenegadeVitaRenderer::Reset_Statistics();
				InteractiveTiming timing = {};
				if (capture_pixels == NULL) {
					capture_pixels = static_cast<uint8_t *>(malloc(kCaptureBytes));
				}
				const uint64_t sync_origin = sceKernelGetProcessTimeWide() / 1000ULL;
			while (true) {
				if (Is_Start_Pressed()) {
					result.start_exit_requested = true;
					break;
				}
				const uint64_t frame_begin = sceKernelGetProcessTimeWide();
				WW3D::Sync(static_cast<uint32_t>(
					sceKernelGetProcessTimeWide() / 1000ULL - sync_origin));
				const uint64_t simulation_begin = sceKernelGetProcessTimeWide();
				if (result.frames == 0U) {
					A30_Vita_Log("A3.1 breadcrumb: first original input frame\n");
				}
				const bool was_suspended = combat_mode->Is_Suspended();
				A31_Interactive_Run_Simulation_Frame();
				const A31MissionCompletionState mission_state =
					A31_Interactive_Get_Mission_Completion_State();
				result.star_killed_observed = mission_state.star_killed_observed;
				if (mission_state.completion_observed) {
					result.mission_completion_observed = true;
					result.mission_succeeded = mission_state.mission_succeeded;
					A30_Vita_Log("A3.5 mission completion: original Combat event observed success=%d frame=%u\n",
						result.mission_succeeded ? 1 : 0, result.frames);
					break;
				}
				if (mission_state.star_killed_observed) {
					A30_Vita_Log("A3.5 mission completion: original Combat star-killed event observed frame=%u\n",
						result.frames);
					break;
				}
				const bool is_suspended = combat_mode->Is_Suspended();
				if (!was_suspended && is_suspended) {
					result.pause_observed = true;
					current_pause_input_frames = 0U;
					A30_Vita_Log("A3.5 pause: original Combat suspended frame=%u player=(%.3f,%.3f,%.3f)\n",
						result.frames, last_render_trace.player_x,
						last_render_trace.player_y, last_render_trace.player_z);
				}
				if (was_suspended && !is_suspended) {
					result.resume_observed = true;
					A30_Vita_Log("A3.5 pause: original Combat resumed frame=%u paused_input_frames=%u player=(%.3f,%.3f,%.3f)\n",
						result.frames, current_pause_input_frames,
						last_render_trace.player_x, last_render_trace.player_y,
						last_render_trace.player_z);
					current_pause_input_frames = 0U;
				}
				if (is_suspended) {
					++current_pause_input_frames;
					++result.paused_input_frames;
					/* Preserve the last original Combat frame while the absent desktop
					** menu presenter is deferred. Input, TimeManager, and the local
					** network lane were serviced above, so resume has no accumulated
					** simulation delta. */
					audio->On_Frame_Update(0);
					sceKernelDelayThread(16667);
					continue;
				}
				const uint64_t render_begin = sceKernelGetProcessTimeWide();
				if (result.frames == 0U) {
					A30_Vita_Log("A3.1 breadcrumb: first original Combat update\n");
				}

				const A31InteractiveRenderTrace render_trace =
					A31_Interactive_Run_Render_Frame();
				/* Preserve original mainloop ownership and ordering: WWAudio advances
				** once after the game render. This services playback completion,
				** looping, and original sound-ended events; conversation remark timing
				** remains owned by ActiveConversationClass and TimeManager. */
				audio->On_Frame_Update(0);
				last_render_trace = render_trace;
				const A31MissionProgressState mission_progress =
					A31_Interactive_Get_Mission_Progress_State();
				if (!mission_progress_recorded ||
					Mission_Progress_Changed(last_mission_progress, mission_progress)) {
					Log_Mission_Progress(mission_progress, render_trace, result.frames);
					last_mission_progress = mission_progress;
					mission_progress_recorded = true;
				}
					/* Do not begin record/replay merely because the first frame rendered:
					** Mission00 owns the dialogue/control handoff. Physical M00 evidence
					** can report pre-completed objective status while original player
					** control is already valid, so the route gate follows the original
					** control flag rather than one objective slot. */
					if (!tutorial_control_ready_observed &&
						mission_progress.player_control_enabled) {
						tutorial_control_ready_observed = true;
						Renegade_Vita_Input_Route_Set_Gameplay_Active(true,
							result.frames);
						A30_Vita_Log("A3.5 mission progress: original player control available for route activation frame=%u objectives=%u status_1=%d\n",
							result.frames, mission_progress.objective_count,
							mission_progress.objective_status[0]);
					}
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
					A30_Vita_Log("A3.1 breadcrumb: first render closure scene/camera/star/pre/begin/combat/message/end/post=%d/%d/%d/%d/%d/%d/%d/%d/%d meshes=%llu vertices=%llu triangles=%llu rejected=%llu unsupported=%llu\n",
						render_trace.scene_available ? 1 : 0,
						render_trace.camera_available ? 1 : 0,
						render_trace.star_available ? 1 : 0,
						render_trace.pre_render_completed ? 1 : 0,
						render_trace.begin_render_completed ? 1 : 0,
						render_trace.combat_render_called ? 1 : 0,
						render_trace.message_window_render_called ? 1 : 0,
						render_trace.end_render_completed ? 1 : 0,
						render_trace.post_render_completed ? 1 : 0,
						static_cast<unsigned long long>(render_trace.mesh_submissions),
						static_cast<unsigned long long>(render_trace.vertex_submissions),
						static_cast<unsigned long long>(render_trace.triangle_submissions),
						static_cast<unsigned long long>(render_trace.rejected_submissions),
						static_cast<unsigned long long>(render_trace.unsupported_submissions));
					Log_Interactive_Player_Effects(render_trace, result.frames,
						"first-visible-frame");
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
				A31FrameTelemetry capture_frame = {};
				capture_frame.frame_index = result.frames;
				capture_frame.monotonic_us = frame_end;
				capture_frame.frame_time_us = frame_end - frame_begin;
				capture_frame.ordinary_frame_time_us = capture_frame.frame_time_us;
				capture_frame.stages.input_us = simulation_begin - frame_begin;
				capture_frame.stages.game_update_us = render_begin - simulation_begin;
				capture_frame.stages.render_us = frame_end - render_begin;
				Copy_Renderer_Statistics(capture_frame.renderer);
				if (capture_frame.renderer.draw_calls == 0U) {
					capture_frame.renderer.draw_calls = render_trace.mesh_submissions;
					capture_frame.renderer.mesh_submissions = render_trace.mesh_submissions;
					capture_frame.renderer.vertices = render_trace.vertex_submissions;
					capture_frame.renderer.triangles = render_trace.triangle_submissions;
					capture_frame.renderer.rejected_submissions =
						render_trace.rejected_submissions;
					capture_frame.renderer.unsupported_submissions =
						render_trace.unsupported_submissions;
				}
				capture_frame.game_update_count = result.frames;
				capture_frame.physics_update_count = result.frames;
				const RenegadeVitaInputTelemetry &input_telemetry =
					Renegade_Vita_Last_Input_Telemetry();
				capture_frame.input_action_count = input_telemetry.sample_count;
				capture_history->Push(capture_frame);
				if (first_interactive_capture_pending && render_trace.star_available &&
					render_trace.camera_available &&
					first_interactive_capture_attempts < kAutomaticCaptureAttempts) {
					++first_interactive_capture_attempts;
					const bool readback = capture_pixels != NULL &&
						RenegadeVitaRenderer::Capture_Resolved_Frame_RGBA(capture_pixels, kCaptureBytes);
					char label[96];
					snprintf(label, sizeof(label), "first-interactive-player-frame-f%u-t%llu",
						result.frames, static_cast<unsigned long long>(frame_end));
					const A31StateSnapshot state = Make_Interactive_Capture_State(render_trace,
						result.frames, frame_end, "first-interactive-player-frame");
					const A31CaptureBundleResult capture = Capture_Interactive_Frame(state,
						*capture_history, readback ? capture_pixels : NULL, label);
					A30_Vita_Log("Capture: %s candidate=%s phase=interactive-player-owned reason=first-interactive-player-frame path=%s screenshot/state/csv/summary=%d/%d/%d/%d error_code=%d\n",
						capture.passed ? "PASS" : "FAIL", RENEGADE_BUILD_CANDIDATE_LABEL,
						capture.bundle_path, capture.screenshot_written ? 1 : 0,
						capture.state_written ? 1 : 0, capture.history_written ? 1 : 0,
						capture.summary_written ? 1 : 0, capture.first_error_code);
					first_interactive_capture_pending = !capture.passed;
				}
				const bool select_pressed =
					(input_telemetry.buttons & SCE_CTRL_SELECT) != 0U;
				if (select_pressed && !select_was_pressed && render_trace.star_available &&
					render_trace.camera_available) {
					const bool readback = capture_pixels != NULL &&
						RenegadeVitaRenderer::Capture_Resolved_Frame_RGBA(capture_pixels, kCaptureBytes);
					char label[96];
					snprintf(label, sizeof(label), "manual-select-interactive-f%u-t%llu",
						result.frames, static_cast<unsigned long long>(frame_end));
					const A31StateSnapshot state = Make_Interactive_Capture_State(render_trace,
						result.frames, frame_end, "manual-select");
					const A31CaptureBundleResult capture = Capture_Interactive_Frame(state,
						*capture_history, readback ? capture_pixels : NULL, label);
					A30_Vita_Log("Capture: %s candidate=%s phase=interactive-player-owned reason=manual-select path=%s screenshot/state/csv/summary=%d/%d/%d/%d error_code=%d\n",
						capture.passed ? "PASS" : "FAIL", RENEGADE_BUILD_CANDIDATE_LABEL,
						capture.bundle_path, capture.screenshot_written ? 1 : 0,
						capture.state_written ? 1 : 0, capture.history_written ? 1 : 0,
						capture.summary_written ? 1 : 0, capture.first_error_code);
				}
				select_was_pressed = select_pressed;
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
					Log_Interactive_Player_Effects(render_trace, result.frames,
						"checkpoint");
					Log_Timing_Statistics(timing,
						RenegadeVitaRenderer::Get_Statistics());
					Log_Input_Telemetry();
					Log_Audio_Runtime_Statistics("checkpoint", result.frames);
				}
			}
				result.clean_exit_requested = !result.render_error &&
					(result.start_exit_requested ||
						(result.mission_completion_observed && result.mission_succeeded));
				if (result.clean_exit_requested && capture_history->Count() != 0U &&
					last_render_trace.star_available && last_render_trace.camera_available) {
					char label[96];
					const uint64_t exit_us = sceKernelGetProcessTimeWide();
					snprintf(label, sizeof(label), "pre-clean-exit-f%u-t%llu", result.frames,
						static_cast<unsigned long long>(exit_us));
					const A31StateSnapshot state = Make_Interactive_Capture_State(last_render_trace,
						result.frames, exit_us, "pre-clean-exit");
					const A31CaptureBundleResult capture = Capture_Interactive_Frame(state,
						*capture_history, NULL, label);
					A30_Vita_Log("Capture flush: %s candidate=%s phase=interactive-player-owned reason=pre-clean-exit path=%s state/csv/summary=%d/%d/%d error_code=%d\n",
						capture.passed ? "PASS" : "FAIL", RENEGADE_BUILD_CANDIDATE_LABEL,
						capture.bundle_path, capture.state_written ? 1 : 0,
						capture.history_written ? 1 : 0, capture.summary_written ? 1 : 0,
						capture.first_error_code);
				} else if (result.render_error && capture_history->Count() != 0U) {
					char label[96];
					const uint64_t fatal_us = sceKernelGetProcessTimeWide();
					snprintf(label, sizeof(label), "fatal-snapshot-f%u-t%llu", result.frames,
						static_cast<unsigned long long>(fatal_us));
					const A31StateSnapshot state = Make_Interactive_Capture_State(last_render_trace,
						result.frames, fatal_us, "best-effort-fatal-snapshot");
					const A31CaptureBundleResult capture = Capture_Interactive_Frame(state,
						*capture_history, NULL, label);
					A30_Vita_Log("Capture flush: %s candidate=%s phase=interactive-player-owned reason=best-effort-fatal-snapshot path=%s state/csv/summary=%d/%d/%d error_code=%d\n",
						capture.passed ? "PASS" : "FAIL", RENEGADE_BUILD_CANDIDATE_LABEL,
						capture.bundle_path, capture.state_written ? 1 : 0,
						capture.history_written ? 1 : 0, capture.summary_written ? 1 : 0,
						capture.first_error_code);
				}
				Copy_Timing_Statistics(result, timing);
				Log_Timing_Statistics(timing, RenegadeVitaRenderer::Get_Statistics());
				Log_Audio_Runtime_Statistics("final", result.frames);
			if (result.start_exit_requested && result.clean_exit_requested) {
				A30_Vita_Log("A3.1 breadcrumb: START exit request detected\n");
			} else if (result.mission_completion_observed && result.mission_succeeded &&
				result.clean_exit_requested) {
				A30_Vita_Log("A3.5 breadcrumb: original mission success transition detected\n");
			} else if (result.mission_completion_observed || result.star_killed_observed) {
				A30_Vita_Log("A3.5 breadcrumb: original mission failure transition detected\n");
			}
			} while (false);
			free(capture_pixels);
			delete capture_history;
			capture_history = NULL;
				if (mission_completion_observer_installed) {
					A31_Interactive_End_Mission_Completion_Observation();
					mission_completion_observer_installed = false;
				}

#if defined(RENEGADE_A4_ORIGINAL_FRONTEND)
				if (frontend_combat_mode_registered) {
					if (!frontend_combat_mode.Is_Inactive()) {
						frontend_combat_mode.Deactivate();
						GameModeManager::Safely_Deactivate();
						result.level_loaded = false;
						radar_initialized = false;
						A30_Vita_Log("A4 frontend: original CombatGameMode shutdown consumed level/radar teardown\n");
					}
					GameModeManager::Remove(&frontend_combat_mode);
					frontend_combat_mode_registered = false;
				}
				if (frontend_menu_mode_registered_for_handoff) {
					if (!frontend_menu_mode.Is_Inactive()) {
						frontend_menu_mode.Deactivate();
					}
					GameModeManager::Safely_Deactivate();
					GameModeManager::Remove(&frontend_menu_mode);
					frontend_menu_mode_registered_for_handoff = false;
					A30_Vita_Log("A4 frontend: removed retained Menu mode after Combat handoff\n");
				}
#endif

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
			if (campaign_initialized) {
				CampaignManager::Shutdown();
				campaign_initialized = false;
				A30_Vita_Log("A3.5 loading screen: original CampaignManager catalog shutdown complete\n");
			}
				if (combat_initialized) {
					A30_Vita_Log("A3.1 breadcrumb: Combat shutdown entry\n");
					if (text_window_scene_initialized) {
						TextWindowClass::Shutdown();
						text_window_scene_initialized = false;
						A30_Vita_Log("A3.5 text window: original scene binding shutdown complete\n");
					}
					CombatManager::Shutdown();
					A30_Vita_Log("A3.1 breadcrumb: Combat shutdown complete\n");
				}
				if (text_display_initialized) {
					DebugManager::Set_Display_Handler(NULL);
					TextDisplayGameModeClass::Get_Instance()->Shutdown();
					text_display_initialized = false;
					A30_Vita_Log("A3.5 text display: original TextDisplayGameMode shutdown complete\n");
				}
				if (stylemgr_initialized) {
				StyleMgrClass::Shutdown();
				stylemgr_initialized = false;
				A30_Vita_Log("A3.5 loading screen: original StyleMgr shutdown complete\n");
			}
			if (translatedb_initialized) {
				TranslateDBClass::Shutdown();
				translatedb_initialized = false;
				A30_Vita_Log("A3.5 loading screen: original TranslateDB shutdown complete\n");
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
		A30_Vita_Log("A3.1 breadcrumb: application audio teardown entry singleton=%p\n",
			static_cast<void *>(WWAudioClass::Get_Instance()));
	}
	audio_teardown_completed = WWAudioClass::Get_Instance() == NULL;
	A30_Vita_Log("A3.1 breadcrumb: application audio teardown complete singleton=%p\n",
		static_cast<void *>(WWAudioClass::Get_Instance()));

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
	result.teardown_completed = !result.render_error && audio_teardown_completed &&
		WW3DAssetManager::Get_Instance() == NULL && !WW3D::Is_Initted();
	A30_Vita_Log("A3.1 interactive: complete ready=%d transport=%d level=%d player=%d commando=%d frames=%u exit=%d render_error=%d teardown=%d pause/resume=%d/%d paused_input_frames=%u start_exit=%d mission_complete/success/star=%d/%d/%d perf_fps=%.3f p50/p95/worst_us=%u/%u/%u\n",
		result.initialized ? 1 : 0, result.transport_established ? 1 : 0,
		result.level_loaded ? 1 : 0, result.player_created ? 1 : 0,
		result.commando_created ? 1 : 0, result.frames,
		result.clean_exit_requested ? 1 : 0, result.render_error ? 1 : 0,
		result.teardown_completed ? 1 : 0, result.pause_observed ? 1 : 0,
		result.resume_observed ? 1 : 0, result.paused_input_frames,
		result.start_exit_requested ? 1 : 0,
		result.mission_completion_observed ? 1 : 0,
		result.mission_succeeded ? 1 : 0,
		result.star_killed_observed ? 1 : 0,
		static_cast<double>(result.average_fps_milli) / 1000.0,
		result.median_frame_us, result.p95_frame_us, result.worst_frame_us);
	return result;
}
