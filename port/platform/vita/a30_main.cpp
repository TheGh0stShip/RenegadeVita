#include "a30_vita_runtime.h"
#include "a31_vita_runtime.h"
#include "renegade_build_identity.h"
#include "vita_platform.h"
#include "wwaudio.h"

#include <psp2/ctrl.h>
#include <psp2/display.h>
#include <psp2/kernel/cpu.h>
#include <psp2/kernel/processmgr.h>
#include <psp2/kernel/threadmgr.h>
#include <psp2/io/fcntl.h>
#include <psp2/power.h>

#include <debugScreen.h>

#include <stdint.h>
#include <string.h>

namespace {

// Raw Vita I/O is deliberately independent of newlib, the display, and the
// original engine. A failed launch must leave a boundary marker even when
// the normal runtime log has not been initialized yet.
void Write_Boot_Trace(const char *phase, unsigned result, bool reset = false)
{
	const int flags = SCE_O_WRONLY | SCE_O_CREAT |
		(reset ? SCE_O_TRUNC : SCE_O_APPEND);
	const SceUID file = sceIoOpen(
		"ux0:data/renegade/user/logs/" RENEGADE_BUILD_CANDIDATE_LABEL "-boot-v1.log",
		flags, 0666);
	if (file < 0) return;
	char line[128];
	unsigned length = 0;
	while (*phase && length < sizeof(line) - 12U) line[length++] = *phase++;
	line[length++] = ' ';
	const char hex[] = "0123456789ABCDEF";
	for (int shift = 28; shift >= 0; shift -= 4)
		line[length++] = hex[(result >> shift) & 15U];
	line[length++] = '\n';
	unsigned offset = 0;
	while (offset < length) {
		const SceSSize wrote = sceIoWrite(file, line + offset, length - offset);
		if (wrote <= 0 || static_cast<unsigned>(wrote) > length - offset) break;
		offset += static_cast<unsigned>(wrote);
	}
	sceIoSyncByFd(file, 0);
	sceIoClose(file);
}

__attribute__((constructor(101))) void Record_Early_Native_Startup()
{
	Write_Boot_Trace("native-constructor-entry", 1U, true);
}

void Flush_Bootstrap_Display(unsigned frames)
{
	for (unsigned index = 0; index < frames; ++index) {
		sceDisplayWaitVblankStart();
	}
}

void Hold_Bootstrap_Display(unsigned milliseconds)
{
	const unsigned frames = (milliseconds * 60U + 999U) / 1000U;
	Flush_Bootstrap_Display(frames > 0U ? frames : 1U);
}

void Print_Bootstrap_Progress(int screen_result)
{
	if (screen_result < 0) return;
	psvDebugScreenClear(0x102030);
	psvDebugScreenSetFgColor(0xFFFFFF);
	psvDebugScreenPrintf("%s\nFirst-mission alpha development build\n\n",
		RENEGADE_BUILD_DISPLAY_LABEL);
	psvDebugScreenPrintf("Starting native Vita runtime...\n");
	psvDebugScreenPrintf("Now: initializing the writable user tree\n");
	psvDebugScreenPrintf("Then: checking the user-supplied retail Data files\n");
	psvDebugScreenPrintf("Next: visible pre-cache / pre-warm / pre-compute\n\n");
	psvDebugScreenPrintf("This status remains visible while startup work begins.\n");
	Hold_Bootstrap_Display(750U);
}

void Print_Startup(const VitaBootstrapStatus &status, int screen_result)
{
	psvDebugScreenClear(0x102030);
	psvDebugScreenSetFgColor(0xFFFFFF);
	psvDebugScreenPrintf("%s\nFirst-mission alpha development build\n\n",
		RENEGADE_BUILD_DISPLAY_LABEL);
	psvDebugScreenPrintf("Framebuffer:     %s (%08X)\n",
		Vita_Pass_Fail(screen_result >= 0),
		static_cast<unsigned>(screen_result));
	psvDebugScreenPrintf("Retail/Data:     %s/%s\n",
		Vita_Pass_Fail(status.retail_root_found),
		Vita_Pass_Fail(status.data_directory_found));
	psvDebugScreenPrintf("Mission data:    %s/%s/%s\n",
		Vita_Pass_Fail(status.always_dat_found),
		Vita_Pass_Fail(status.always2_dat_found),
		Vita_Pass_Fail(status.always_dbs_found));
	psvDebugScreenPrintf("Persistent log:  %s\n\n",
		Vita_Pass_Fail(status.log_result >= 0));
	psvDebugScreenPrintf("Next: visible pre-cache/pre-warm/pre-compute.\n");
	psvDebugScreenPrintf("Then original intro movies, menu, and M00 tutorial.\n");
	psvDebugScreenPrintf("Controls pass through original Input/Combat:\n");
	psvDebugScreenPrintf("  left stick = movement mappings\n");
	psvDebugScreenPrintf("  right stick = look mappings\n");
	psvDebugScreenPrintf("  D-pad = weapons/sniper zoom in gameplay, WWUI focus in menu\n");
	psvDebugScreenPrintf("  X/O/Triangle/Square/L/R = original action mappings\n");
	psvDebugScreenPrintf("  touch = mouse cursor/click, rear touch = camera toggle\n");
	psvDebugScreenPrintf("  START        = runtime exit poll only\n\n");
	psvDebugScreenPrintf("Avoid START during gameplay unless exit evidence is requested\n");
	psvDebugScreenPrintf("Log: %s\n", RENEGADE_BUILD_RUNTIME_LOG_PATH);
	Hold_Bootstrap_Display(750U);
}

} // namespace

int main()
{
	Write_Boot_Trace("main-entry", 1U);
	const uint64_t startup_started_us = sceKernelGetProcessTimeWide();
	Write_Boot_Trace("display-init-enter", 0U);
	const int screen_result = psvDebugScreenInit();
	Write_Boot_Trace("display-init-return", static_cast<unsigned>(screen_result));
	Print_Bootstrap_Progress(screen_result);
	Write_Boot_Trace("bootstrap-print-return", 0U);
	Hold_Bootstrap_Display(250U);
	Write_Boot_Trace("bootstrap-vblank-return", 0U);
	const uint64_t filesystem_started_us = sceKernelGetProcessTimeWide();
	VitaBootstrapStatus status = Vita_Initialize_Filesystem();
	Write_Boot_Trace("filesystem-init-return", 0U);
	const uint64_t filesystem_completed_us = sceKernelGetProcessTimeWide();
	const int log_reset_result = A30_Vita_Log_Reset();
	Write_Boot_Trace("runtime-log-reset-return", static_cast<unsigned>(log_reset_result));
	status.log_result = log_reset_result;
	A30_Vita_Log("Runtime identity: candidate=%s display=%s path=%s\n",
		RENEGADE_BUILD_CANDIDATE_LABEL, RENEGADE_BUILD_DISPLAY_LABEL,
		RENEGADE_BUILD_RUNTIME_LOG_PATH);
	// Select the native userland performance clocks explicitly. No plugin or
	// kernel override is needed; record failures and actual frequencies rather
	// than assuming the requests were honored by the device power policy.
	const int old_cpu = scePowerGetArmClockFrequency();
	const int old_bus = scePowerGetBusClockFrequency();
	const int old_gpu = scePowerGetGpuClockFrequency();
	const int old_xbar = scePowerGetGpuXbarClockFrequency();
	const int cpu_result = scePowerSetArmClockFrequency(444);
	const int bus_result = scePowerSetBusClockFrequency(222);
	const int gpu_result = scePowerSetGpuClockFrequency(222);
	const int xbar_result = scePowerSetGpuXbarClockFrequency(166);
	A30_Vita_Log("A3.5 native clocks MHz cpu/bus/gpu/xbar before=%d/%d/%d/%d requested=444/222/222/166 result=%d/%d/%d/%d actual=%d/%d/%d/%d\n",
		old_cpu, old_bus, old_gpu, old_xbar,
		cpu_result, bus_result, gpu_result, xbar_result,
		scePowerGetArmClockFrequency(), scePowerGetBusClockFrequency(),
		scePowerGetGpuClockFrequency(), scePowerGetGpuXbarClockFrequency());
	// Pin the game thread to user core 0. The audio mixer runs on core 1;
	// log, flight-recorder and vitaGL garbage-collector threads on core 2.
	const int affinity_result = sceKernelChangeThreadCpuAffinityMask(
		SCE_KERNEL_THREAD_ID_SELF, SCE_KERNEL_CPU_MASK_USER_0);
	A30_Vita_Log("A3.6 thread placement: game=user0 audio=user1 io/gc=user2 result=%08X\n",
		static_cast<unsigned>(affinity_result));
	A30_Vita_Log("A3.5 startup: bootstrap display=%d startup_ms=%llu filesystem_ms=%llu; visible bootstrap status precedes retail pre-cache\n",
		screen_result >= 0 ? 1 : 0,
		static_cast<unsigned long long>((filesystem_completed_us - startup_started_us) / 1000U),
		static_cast<unsigned long long>((filesystem_completed_us - filesystem_started_us) / 1000U));
	const bool mission_data_ready = status.user_tree_ready && status.retail_root_found &&
		status.data_directory_found && status.always_dat_found &&
		status.always2_dat_found && status.always_dbs_found &&
		status.log_result >= 0;
	A30_Vita_Log(
		"Alpha direct M00 preflight: %s framebuffer=%08X retail/data=%d/%d always/always2/dbs=%d/%d/%d writable/log=%d/%d log_rc=%08X\n",
		mission_data_ready ? "PASS" : "FAIL", static_cast<unsigned>(screen_result),
		status.retail_root_found ? 1 : 0,
		status.data_directory_found ? 1 : 0,
		status.always_dat_found ? 1 : 0,
		status.always2_dat_found ? 1 : 0,
		status.always_dbs_found ? 1 : 0,
		status.user_tree_ready ? 1 : 0,
		status.log_result >= 0 ? 1 : 0,
		static_cast<unsigned>(status.log_result));

	if (screen_result >= 0) {
		Print_Startup(status, screen_result);
		Flush_Bootstrap_Display(2U);
		sceKernelDelayThread(250 * 1000);
	}
	if (!mission_data_ready) {
		A30_Vita_Log("[LIFECYCLE] END status=controlled-failure phase=retail-preflight candidate=%s\n",
			RENEGADE_BUILD_CANDIDATE_LABEL);
		if (screen_result >= 0) {
			psvDebugScreenFinish();
		}
		A30_Vita_Log_Flush();
		sceKernelExitProcess(1);
		return 1;
	}

	sceCtrlSetSamplingMode(SCE_CTRL_MODE_ANALOG);
	/* The direct runtime owns the retail MIX chain and therefore constructs
	** WWAudio there, after the chain exists but before engine/world setup. */
	A31VitaInteractiveResult interactive = {};
	bool start_at_main_menu = false;
	bool start_at_lan_menu = false;
	char pending_reload[96] = {};
	int pending_replay_difficulty = -1;
	char pending_campaign_source[96] = {};
	uint8_t pending_campaign_state[64] = {};
	uint32_t pending_campaign_state_size = 0;
	char pending_frontend_source[96] = {};
	bool pending_frontend_skirmish = false;
	bool runtime_ok = false;
	unsigned recovered_load_failures = 0U;
	// Re-enter the original frontend only after the prior engine session has
	// completed its owned cleanup. No world, player or save state is reused.
	for (;;) {
	interactive = A31_Vita_Run_Interactive_Runtime(screen_result, start_at_main_menu,
		start_at_lan_menu,
		pending_reload[0] != '\0' ? pending_reload : nullptr,
		pending_campaign_source[0] != '\0' ? pending_campaign_source : nullptr,
		pending_campaign_state_size != 0 ? pending_campaign_state : nullptr,
		pending_campaign_state_size, pending_replay_difficulty,
		pending_frontend_source[0] != '\0' ? pending_frontend_source : nullptr,
		pending_frontend_skirmish);
	pending_reload[0] = '\0';
	pending_replay_difficulty = -1;
	pending_campaign_source[0] = '\0';
	pending_campaign_state_size = 0;
	pending_frontend_source[0] = '\0';
	pending_frontend_skirmish = false;
	const bool audio_teardown_completed = WWAudioClass::Get_Instance() == NULL;
	A30_Vita_Log("A3.1 breadcrumb: application audio teardown singleton=%p\n",
		static_cast<void *>(WWAudioClass::Get_Instance()));
	A30_Vita_Log(
		"A3.1 original interactive: attempted/ready/transport/level/player/registered/commando/first_frame/geometry/exit/render_error/teardown=%d/%d/%d/%d/%d/%d/%d/%d/%d/%d/%d/%d frames=%u start_exit=%d mission_complete/success/star=%d/%d/%d meshes=%u vertices=%u triangles=%u perf_fps=%.3f p50/p95/worst_us=%u/%u/%u stage_us sync/sim/render=%u/%u/%u\n",
		interactive.attempted ? 1 : 0, interactive.initialized ? 1 : 0,
		interactive.transport_established ? 1 : 0, interactive.level_loaded ? 1 : 0,
		interactive.player_created ? 1 : 0, interactive.player_registered ? 1 : 0,
		interactive.commando_created ? 1 : 0,
		interactive.first_frame_completed ? 1 : 0,
		interactive.first_frame_geometry ? 1 : 0,
		interactive.clean_exit_requested ? 1 : 0,
		interactive.render_error ? 1 : 0,
		interactive.teardown_completed ? 1 : 0, interactive.frames,
		interactive.start_exit_requested ? 1 : 0,
		interactive.mission_completion_observed ? 1 : 0,
		interactive.mission_succeeded ? 1 : 0,
		interactive.star_killed_observed ? 1 : 0,
		interactive.mesh_submissions, interactive.vertex_submissions,
		interactive.triangle_submissions,
		static_cast<double>(interactive.average_fps_milli) / 1000.0,
		interactive.median_frame_us, interactive.p95_frame_us,
		interactive.worst_frame_us, interactive.average_sync_us,
		interactive.average_simulation_us, interactive.average_render_us);
	A30_Vita_Log("A4 world generations: started/bound/rendered=%u/%u/%u\n",
		interactive.world_generations_started, interactive.world_generations_bound,
		interactive.world_generations_rendered);
	A30_Vita_Log("A3.5 original Combat pause: suspend/resume=%d/%d paused_input_frames=%u\n",
		interactive.pause_observed ? 1 : 0,
		interactive.resume_observed ? 1 : 0,
		interactive.paused_input_frames);
	if (interactive.campaign_handoff_failure != A31_CAMPAIGN_HANDOFF_NO_FAILURE) {
		A30_Vita_Log("A4 campaign: controlled handoff recovery code=%u return_to_menu=%d\n",
			interactive.campaign_handoff_failure,
			interactive.return_to_menu_requested ? 1 : 0);
	}
	const bool gameplay_ok = interactive.attempted && interactive.initialized &&
		interactive.transport_established && interactive.level_loaded &&
		interactive.player_created && interactive.player_registered &&
		interactive.commando_created && interactive.first_frame_completed &&
		interactive.first_frame_geometry && interactive.clean_exit_requested &&
		interactive.world_generations_started != 0U &&
		interactive.world_generations_started == interactive.world_generations_bound &&
		interactive.world_generations_started == interactive.world_generations_rendered &&
		!interactive.render_error && interactive.level_load_failure == 0U &&
		interactive.campaign_handoff_failure == A31_CAMPAIGN_HANDOFF_NO_FAILURE &&
		interactive.teardown_completed &&
		audio_teardown_completed;
	runtime_ok = gameplay_ok || (interactive.frontend_exit_requested &&
		interactive.clean_exit_requested && !interactive.render_error &&
		interactive.level_load_failure == 0U &&
		interactive.campaign_handoff_failure == A31_CAMPAIGN_HANDOFF_NO_FAILURE &&
		interactive.teardown_completed &&
		audio_teardown_completed);
	const bool load_recovery_ready = interactive.level_load_failure != 0U &&
		interactive.load_failure_cleanup_completed && interactive.clean_exit_requested &&
		interactive.return_to_menu_requested && !interactive.frontend_exit_requested &&
		!interactive.render_error && interactive.teardown_completed && audio_teardown_completed;
	const bool campaign_recovery_ready =
		interactive.campaign_handoff_failure != A31_CAMPAIGN_HANDOFF_NO_FAILURE &&
		interactive.campaign_handoff_cleanup_completed && interactive.clean_exit_requested &&
		interactive.return_to_menu_requested && !interactive.frontend_exit_requested &&
		!interactive.render_error && interactive.teardown_completed && audio_teardown_completed;
	A30_Vita_Log("A3.1 breadcrumb: runtime teardown complete result=%s\n",
		runtime_ok ? "PASS" : (load_recovery_ready ? "LOAD_FAILURE_RECOVERY" :
			(campaign_recovery_ready ? "CAMPAIGN_HANDOFF_RECOVERY" : "FAIL")));
	if (load_recovery_ready) {
		++recovered_load_failures;
		start_at_lan_menu = interactive.return_to_lan_menu_requested;
		start_at_main_menu = !start_at_lan_menu;
		A30_Vita_Log("A4 completion: failed level code=%u cleanup complete; reopening original %s menu recovery=%u\n",
			interactive.level_load_failure, start_at_lan_menu ? "LAN" : "main",
			recovered_load_failures);
		continue;
	}
	if (campaign_recovery_ready) {
		start_at_lan_menu = false;
		start_at_main_menu = true;
		A30_Vita_Log("A4 campaign: failed handoff code=%u cleanup complete; reopening original main menu\n",
			interactive.campaign_handoff_failure);
		continue;
	}
	if (runtime_ok && interactive.reload_source[0] != '\0') {
		memcpy(pending_reload, interactive.reload_source, sizeof(pending_reload));
		pending_replay_difficulty = interactive.reload_is_replay
			? interactive.reload_replay_difficulty : -1;
		A30_Vita_Log("A4 load: clean session released; entering original source=%s replay_difficulty=%d\n",
			pending_reload, pending_replay_difficulty);
		start_at_main_menu = true;
		start_at_lan_menu = false;
		continue;
	}
	if (runtime_ok && interactive.frontend_selection_deferred &&
		interactive.frontend_next_source[0] != '\0') {
		memcpy(pending_frontend_source, interactive.frontend_next_source,
			sizeof(pending_frontend_source));
		pending_frontend_skirmish = interactive.frontend_next_skirmish;
		start_at_main_menu = false;
		start_at_lan_menu = false;
		A30_Vita_Log("A4 frontend: clean session released; resuming deferred %s source=%s\n",
			pending_frontend_skirmish ? "Practice" : "single-player",
			pending_frontend_source);
		continue;
	}
#if !RENEGADE_VITA_M00_DEMO
	if (runtime_ok && interactive.campaign_handoff_completed &&
		interactive.campaign_next_source[0] != '\0' &&
		interactive.campaign_state_size <= sizeof(pending_campaign_state)) {
		memcpy(pending_campaign_source, interactive.campaign_next_source,
			sizeof(pending_campaign_source));
		memcpy(pending_campaign_state, interactive.campaign_state,
			interactive.campaign_state_size);
		pending_campaign_state_size = interactive.campaign_state_size;
		A30_Vita_Log("A4 campaign: clean session released; entering original next source=%s state_bytes=%u\n",
			pending_campaign_source, pending_campaign_state_size);
		start_at_main_menu = false;
		start_at_lan_menu = false;
		continue;
	}
#endif
	if (runtime_ok && interactive.return_to_menu_requested) {
		start_at_lan_menu = interactive.return_to_lan_menu_requested;
		start_at_main_menu = !start_at_lan_menu;
		A30_Vita_Log("A4 frontend: clean session released; reopening original %s menu\n",
			start_at_lan_menu ? "LAN" : "main");
		continue;
	}
	break;
	}
	if (runtime_ok) {
		A30_Vita_Log("[LIFECYCLE] END status=%s candidate=%s recovered_load_failures=%u\n",
			recovered_load_failures == 0U ? "clean" : "clean-with-recovered-load-failure",
			RENEGADE_BUILD_CANDIDATE_LABEL, recovered_load_failures);
	} else {
		A30_Vita_Log("[LIFECYCLE] END status=controlled-failure phase=interactive-runtime candidate=%s\n",
			RENEGADE_BUILD_CANDIDATE_LABEL);
	}

	/* The native app reaches this only after START or a durable diagnosed
	** failure. Never touch or deploy retail data during shutdown. */
	const int exit_code = runtime_ok ? 0 : 1;
	// Drain the background log writer before the process ends.
	A30_Vita_Log_Flush();
	sceKernelExitProcess(exit_code);
	return exit_code;
}
