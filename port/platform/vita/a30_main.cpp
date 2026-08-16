#include "a21_filesystem_selftest.h"
#include "a22_w3d_selftest.h"
#include "a30_vita_runtime.h"
#include "a30_world_runtime.h"
#include "a31_vita_runtime.h"
#include "renegade_build_identity.h"
#include "vita_platform.h"
#include "ww3d_vita_renderer.h"
#include "wwbitpack_selftest.h"
#include "wwaudio.h"

#include <psp2/ctrl.h>
#include <psp2/kernel/processmgr.h>
#include <psp2/kernel/threadmgr.h>

#include <debugScreen.h>

namespace {

const RenegadePathRoots kVitaRoots = {
	"ux0:data/renegade/retail",
	"ux0:data/renegade/user",
	"ux0:data/renegade/cache",
	"ux0:data/renegade/mods"
};

void Print_Startup(const VitaBootstrapStatus &status,
	const WestwoodSelfTestResult &bitpack,
	const A21FilesystemSelfTestResult &filesystem, int screen_result)
{
	psvDebugScreenClear(0x102030);
	psvDebugScreenSetFgColor(0xFFFFFF);
	psvDebugScreenPrintf("%s\nCorrectness and Diagnostics Development Build\n\n",
		RENEGADE_BUILD_DISPLAY_LABEL);
	psvDebugScreenPrintf("A2.0 regression: %s (%u/19)\n",
		Vita_Pass_Fail(bitpack.passed), bitpack.checks);
	psvDebugScreenPrintf("Framebuffer:     %s (%08X)\n",
		Vita_Pass_Fail(screen_result >= 0),
		static_cast<unsigned>(screen_result));
	psvDebugScreenPrintf("Retail/Data:     %s/%s\n",
		Vita_Pass_Fail(status.retail_root_found),
		Vita_Pass_Fail(status.data_directory_found));
	psvDebugScreenPrintf("A2 files/log:    %s/%s/%s/%s\n",
		Vita_Pass_Fail(status.always_dat_found),
		Vita_Pass_Fail(status.always2_dat_found),
		Vita_Pass_Fail(status.always_dbs_found),
		Vita_Pass_Fail(status.log_result >= 0));
	psvDebugScreenPrintf("A2.1 MIX:        %s (%u/10)\n",
		Vita_Pass_Fail(filesystem.passed), filesystem.checks);
	psvDebugScreenPrintf("always.dat:      %u entries\n",
		filesystem.archive_entries);
	psvDebugScreenPrintf("dsp_o2tank:      %u/%u/%08X\n\n",
		filesystem.known_entry_size, filesystem.known_entry_bytes_read,
		filesystem.known_entry_prefix);
	psvDebugScreenPrintf("Next: preserved A2.2/A3.0 regressions, then\n");
	psvDebugScreenPrintf("original M00 Combat/session/player runtime.\n");
	psvDebugScreenPrintf("Controls pass through original Input/Combat:\n");
	psvDebugScreenPrintf("  D-pad/left stick = movement mappings\n");
	psvDebugScreenPrintf("  right stick = look mappings\n");
	psvDebugScreenPrintf("  CROSS/CIRCLE/L/R = original action mappings\n");
	psvDebugScreenPrintf("  START        = clean exit\n\n");
	psvDebugScreenPrintf("START exits cleanly after original runtime begins\n");
	psvDebugScreenPrintf("Log: %s\n", RENEGADE_BUILD_RUNTIME_LOG_PATH);
}

void A30_World_Stage_Breadcrumb(void *, const char *stage)
{
	WWAudioClass *audio = WWAudioClass::Get_Instance();
	SoundSceneClass *scene = audio != NULL ? audio->Get_Sound_Scene() : NULL;
	A30_Vita_Log("A3.1 breadcrumb: %s singleton=%p sound_scene=%p\n", stage,
		static_cast<void *>(audio), static_cast<void *>(scene));
}

} // namespace

int main()
{
	const int screen_result = psvDebugScreenInit();
	const WestwoodSelfTestResult bitpack =
		Run_Westwood_Bitpack_Self_Test();
	VitaBootstrapStatus status = Vita_Initialize_Filesystem();
	const int log_reset_result = A30_Vita_Log_Reset();
	status.log_result = log_reset_result;
	A30_Vita_Log("Runtime identity: candidate=%s display=%s path=%s\n",
		RENEGADE_BUILD_CANDIDATE_LABEL, RENEGADE_BUILD_DISPLAY_LABEL,
		RENEGADE_BUILD_RUNTIME_LOG_PATH);
	const A21FilesystemSelfTestResult filesystem =
		Run_A21_Filesystem_Self_Test(kVitaRoots);
	const bool a20_passed = screen_result >= 0 && bitpack.passed &&
		status.user_tree_ready && status.retail_root_found &&
		status.data_directory_found && status.always_dat_found &&
		status.always2_dat_found && status.always_dbs_found &&
		status.log_result >= 0;
	A30_Vita_Log(
		"A2.0 regression: %s (%u checks, %u failures) framebuffer=%08X retail/data=%d/%d always/always2/dbs=%d/%d/%d writable/log=%d/%d log_rc=%08X\n",
		a20_passed ? "PASS" : "FAIL", bitpack.checks,
		bitpack.failures, static_cast<unsigned>(screen_result),
		status.retail_root_found ? 1 : 0,
		status.data_directory_found ? 1 : 0,
		status.always_dat_found ? 1 : 0,
		status.always2_dat_found ? 1 : 0,
		status.always_dbs_found ? 1 : 0,
		status.user_tree_ready ? 1 : 0,
		status.log_result >= 0 ? 1 : 0,
		static_cast<unsigned>(status.log_result));
	A30_Vita_Log(
		"A2.1 regression: %s (%u checks, %u failures) entries=%u known=%u/%u/%08X\n",
		filesystem.passed ? "PASS" : "FAIL", filesystem.checks,
		filesystem.failures, filesystem.archive_entries,
		filesystem.known_entry_size, filesystem.known_entry_bytes_read,
		filesystem.known_entry_prefix);
	A30_Vita_Log("A3 log reset result: %08X\n",
		static_cast<unsigned>(log_reset_result));

	if (screen_result >= 0) {
		Print_Startup(status, bitpack, filesystem, screen_result);
		sceKernelDelayThread(1400 * 1000);
		psvDebugScreenFinish();
	}

	sceCtrlSetSamplingMode(SCE_CTRL_MODE_ANALOG);
	/* Original Commando constructs WWAudio before later engine/world setup. The
	** Vita implementation is deliberately no-output, but it is still the sole
	** owner required by the original StaticAudioSaveLoadClass. Keep it alive
	** across both the preserved A3.0 regression and A3.1 interactive session. */
	A30_Vita_Log("A3.1 breadcrumb: application audio construction entry singleton=%p\n",
		static_cast<void *>(WWAudioClass::Get_Instance()));
	{
		WWAudioClass application_audio(true);
		A30_World_Stage_Breadcrumb(NULL,
			"application audio ready before A3.0 world validation");
	const A22W3DRenderOptions a22_options = {
		true,
		1U,
		NULL,
		NULL
	};
	const A22W3DSelfTestResult a22 =
		Run_A22_W3D_Self_Test(kVitaRoots, &a22_options);
	A30_Vita_Log(
		"A2.2 regression: %s (%u checks, %u failures) object=%s class=%d meshes=%u vertices=%u polygons=%u materials=%u textures=%u pivots=%u frame=%u/%u/%u/%u unsupported=%u checksum=%08X\n",
		a22.passed ? "PASS" : "FAIL", a22.checks, a22.failures,
		a22.render_object_name, a22.render_object_class_id, a22.mesh_count,
		a22.vertex_count, a22.polygon_count, a22.material_count,
		a22.texture_count, a22.render_hierarchy_pivots,
		a22.rendered_frames, a22.rendered_meshes, a22.rendered_vertices,
		a22.rendered_triangles, a22.unsupported_render_objects,
		a22.rendered_geometry_checksum);
	const RenegadeVitaRenderer::BackendLifecycleStatistics &after_a22 =
		RenegadeVitaRenderer::Get_Backend_Lifecycle_Statistics();
	A30_Vita_Log(
		"Renderer lifecycle after A2.2: native_attempted/ready/calls=%d/%d/%u logical_active/sessions/shutdowns=%d/%u/%u\n",
		after_a22.native_initialization_attempted ? 1 : 0,
		after_a22.native_backend_ready ? 1 : 0,
		after_a22.native_initialization_calls,
		after_a22.logical_session_active ? 1 : 0,
		after_a22.logical_sessions, after_a22.logical_shutdowns);

	A30VitaWorldRenderResult render_result = {};
	const A30WorldRuntimeOptions world_options = {
		&A30_Vita_Render_Loaded_World,
		&render_result,
		&A30_World_Stage_Breadcrumb,
		NULL
	};
	A30_World_Stage_Breadcrumb(NULL, "A3.0 world validation entry");
	const A30WorldRuntimeResult world_result =
		Run_A30_World_Runtime(kVitaRoots, &world_options);
	A30_Vita_Log_World_Result(world_result, render_result);
	A30_World_Stage_Breadcrumb(NULL, "A3.0 world validation complete");
	const RenegadeVitaRenderer::BackendLifecycleStatistics &after_world =
		RenegadeVitaRenderer::Get_Backend_Lifecycle_Statistics();
	A30_Vita_Log(
		"Renderer lifecycle after A3 world: native_attempted/ready/calls=%d/%d/%u logical_active/sessions/shutdowns=%d/%u/%u\n",
		after_world.native_initialization_attempted ? 1 : 0,
		after_world.native_backend_ready ? 1 : 0,
		after_world.native_initialization_calls,
		after_world.logical_session_active ? 1 : 0,
		after_world.logical_sessions, after_world.logical_shutdowns);

	const A31VitaInteractiveResult interactive =
		A31_Vita_Run_Interactive_Runtime();
	A30_Vita_Log(
		"A3.1 original interactive: attempted/ready/transport/level/player/registered/commando/first_frame/geometry/exit/render_error/teardown=%d/%d/%d/%d/%d/%d/%d/%d/%d/%d/%d/%d frames=%u meshes=%u vertices=%u triangles=%u perf_fps=%.3f p50/p95/worst_us=%u/%u/%u stage_us sync/sim/render=%u/%u/%u\n",
		interactive.attempted ? 1 : 0, interactive.initialized ? 1 : 0,
		interactive.transport_established ? 1 : 0, interactive.level_loaded ? 1 : 0,
		interactive.player_created ? 1 : 0, interactive.player_registered ? 1 : 0,
		interactive.commando_created ? 1 : 0,
		interactive.first_frame_completed ? 1 : 0,
		interactive.first_frame_geometry ? 1 : 0,
		interactive.clean_exit_requested ? 1 : 0,
		interactive.render_error ? 1 : 0,
		interactive.teardown_completed ? 1 : 0, interactive.frames,
		interactive.mesh_submissions, interactive.vertex_submissions,
		interactive.triangle_submissions,
		static_cast<double>(interactive.average_fps_milli) / 1000.0,
		interactive.median_frame_us, interactive.p95_frame_us,
		interactive.worst_frame_us, interactive.average_sync_us,
		interactive.average_simulation_us, interactive.average_render_us);
	}
	A30_Vita_Log("A3.1 breadcrumb: application audio teardown singleton=%p\n",
		static_cast<void *>(WWAudioClass::Get_Instance()));
	A30_Vita_Log("A3.1 breadcrumb: clean teardown complete\n");
	A30_Vita_Log("[LIFECYCLE] END status=clean candidate=%s\n",
		RENEGADE_BUILD_CANDIDATE_LABEL);

	/* The native app reaches this only after START or a durable diagnosed
	** failure. Never touch or deploy retail data during shutdown. */
	sceKernelExitProcess(0);
	return 0;
}
