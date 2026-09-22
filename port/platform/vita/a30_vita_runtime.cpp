#include "a30_vita_runtime.h"

#include "a31_capture_telemetry.h"
#include "renegade_build_identity.h"

#include "camera.h"
#include "matrix3d.h"
#include "pscene.h"
#include "ww3d.h"
#include "ww3d_vita_renderer.h"

#include <psp2/ctrl.h>
#include <psp2/io/fcntl.h>
#include <psp2/kernel/processmgr.h>
#include <psp2/kernel/threadmgr.h>

#include <math.h>
#include <stdarg.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>

namespace {

const char *const kA30RuntimeLog = RENEGADE_BUILD_RUNTIME_LOG_PATH;
const char *const kA31CaptureRoot = RENEGADE_BUILD_CAPTURE_ROOT;
const size_t kResolvedFrameBytes =
	static_cast<size_t>(RenegadeVitaRenderer::DISPLAY_WIDTH) *
	static_cast<size_t>(RenegadeVitaRenderer::DISPLAY_HEIGHT) * 4U;

uint32_t gA35StaticTraceObjectIndex = 0U;
uint32_t gA35StaticTraceFactoryId = 0U;
bool gA35StaticTraceSummary = false;
bool gA35StaticTraceDeep = false;
SceUID gA30RuntimeLogFile = -1;

int Ensure_Runtime_Log_File()
{
	if (gA30RuntimeLogFile >= 0) return gA30RuntimeLogFile;
	gA30RuntimeLogFile = sceIoOpen(kA30RuntimeLog,
		SCE_O_WRONLY | SCE_O_CREAT | SCE_O_APPEND, 0666);
	return gA30RuntimeLogFile;
}

int Write_Runtime_Log_Line(const char *line, unsigned length)
{
	const SceUID file = Ensure_Runtime_Log_File();
	if (file < 0) return file;
	unsigned offset = 0;
	int result = 0;
	while (offset < length) {
		const int written = sceIoWrite(file, line + offset, length - offset);
		if (written <= 0) {
			result = written < 0 ? written : -2;
			break;
		}
		offset += static_cast<unsigned>(written);
	}
	const int sync_result = sceIoSyncByFd(file, 0);
	if (result >= 0 && sync_result < 0) result = sync_result;
	return result;
}

float Analog_Axis(unsigned char value)
{
	const int offset = static_cast<int>(value) - 128;
	if (offset > -18 && offset < 18) {
		return 0.0f;
	}
	return static_cast<float>(offset) /
		(offset < 0 ? 128.0f : 127.0f);
}

void Copy_Vector(float output[3], const Vector3 &value)
{
	output[0] = value.X;
	output[1] = value.Y;
	output[2] = value.Z;
}

void Copy_Statistics(A30VitaWorldRenderResult &result)
{
	const RenegadeVitaRenderer::Statistics &statistics =
		RenegadeVitaRenderer::Get_Statistics();
	result.frames = statistics.frames;
	result.mesh_submissions = statistics.mesh_submissions;
	result.vertex_submissions = statistics.vertex_submissions;
	result.triangle_submissions = statistics.triangle_submissions;
	result.geometry_checksum = statistics.geometry_checksum;
	result.indexed_submissions = statistics.indexed_submissions;
	result.indexed_vertex_references = statistics.indexed_vertex_references;
	result.indexed_triangle_submissions =
		statistics.indexed_triangle_submissions;
	result.indexed_geometry_checksum = statistics.indexed_geometry_checksum;
	result.rejected_indexed_submissions =
		statistics.rejected_indexed_submissions;
	result.unsupported_submissions = statistics.unsupported_submissions;
}

uint64_t Delta_U64(uint64_t current, uint64_t previous)
{
	return current >= previous ? current - previous : current;
}

uint32_t Delta_U32(uint32_t current, uint32_t previous)
{
	return current >= previous ? current - previous : current;
}

void Copy_World_State(A31WorldTelemetry &output,
	const A30WorldRuntimeFingerprint &world)
{
	output.loaded = world.m00_static_world_loaded && world.post_load_completed;
	output.definition_count = world.definition_count;
	output.static_object_count = world.static_object_count;
	output.dynamic_object_count = world.dynamic_object_count;
	output.light_count = world.static_light_count;
	output.render_object_nodes = world.render_object_node_count;
	output.semantic_meshes = world.mesh_count;
	output.semantic_vertices = world.mesh_vertex_count;
	output.semantic_polygons = world.mesh_polygon_count;
	output.prototype_count = world.loaded_prototype_count;
	output.vis_object_count = world.vis_object_count;
	output.vis_sector_count = world.vis_sector_count;
	output.definition_checksum = world.definition_checksum;
	output.object_checksum = world.object_identity_checksum;
	output.render_checksum = world.render_graph_checksum;
	output.prototype_checksum = world.prototype_checksum;
	memcpy(output.bounds_min, world.level_min, sizeof(output.bounds_min));
	memcpy(output.bounds_max, world.level_max, sizeof(output.bounds_max));
}

void Copy_Camera_State(A31CameraTelemetry &output,
	const Matrix3D &transform, const Vector3 &position, const Vector3 &target,
	float near_clip, float far_clip)
{
	output.present = true;
	output.original_camera_class = true;
	output.player_owned = false;
	for (unsigned row = 0U; row < 3U; ++row) {
		for (unsigned column = 0U; column < 4U; ++column) {
			output.transform[row * 4U + column] = transform[row][column];
		}
	}
	Copy_Vector(output.position, position);
	Copy_Vector(output.target, target);
	output.near_clip = near_clip;
	output.far_clip = far_clip;
}

void Query_Memory(A31MemoryTelemetry &output)
{
	RenegadeVitaRenderer::BackendMemoryStatistics memory = {};
	if (!RenegadeVitaRenderer::Query_Backend_Memory(memory)) {
		return;
	}
	output.available = true;
	output.system_user_free = memory.system_user_free;
	output.system_cdram_free = memory.system_cdram_free;
	output.system_phycont_free = memory.system_phycont_free;
	output.vitagl_ram_total = memory.ram_total;
	output.vitagl_ram_free = memory.ram_free;
	output.vitagl_vram_total = memory.vram_total;
	output.vitagl_vram_free = memory.vram_free;
	output.vitagl_slow_total = memory.slow_total;
	output.vitagl_slow_free = memory.slow_free;
	output.vitagl_all_total = memory.all_total;
	output.vitagl_all_free = memory.all_free;
}

void Initialize_Memory_Low_Water(A31MemoryTelemetry &aggregate,
	const A31MemoryTelemetry &sample)
{
	aggregate = sample;
	if (!sample.available) return;
	aggregate.sample_count = 1U;
	aggregate.system_user_free_low_water = sample.system_user_free;
	aggregate.system_cdram_free_low_water = sample.system_cdram_free;
	aggregate.system_phycont_free_low_water = sample.system_phycont_free;
	aggregate.vitagl_ram_free_low_water = sample.vitagl_ram_free;
	aggregate.vitagl_vram_free_low_water = sample.vitagl_vram_free;
	aggregate.vitagl_slow_free_low_water = sample.vitagl_slow_free;
	aggregate.vitagl_all_free_low_water = sample.vitagl_all_free;
}

void Update_Memory_Low_Water(A31MemoryTelemetry &aggregate,
	const A31MemoryTelemetry &sample)
{
	if (!sample.available) return;
	if (!aggregate.available) {
		Initialize_Memory_Low_Water(aggregate, sample);
		return;
	}
	/* Preserve current free values and totals with the lowest periodic sample.
	** This stays bounded and must not be mistaken for allocator attribution. */
	const uint32_t prior_samples = aggregate.sample_count;
	const int64_t user_low = aggregate.system_user_free_low_water;
	const int64_t cdram_low = aggregate.system_cdram_free_low_water;
	const int64_t phycont_low = aggregate.system_phycont_free_low_water;
	const uint64_t ram_low = aggregate.vitagl_ram_free_low_water;
	const uint64_t vram_low = aggregate.vitagl_vram_free_low_water;
	const uint64_t slow_low = aggregate.vitagl_slow_free_low_water;
	const uint64_t all_low = aggregate.vitagl_all_free_low_water;
	aggregate = sample;
	aggregate.sample_count = prior_samples + 1U;
	aggregate.system_user_free_low_water =
		sample.system_user_free < user_low ? sample.system_user_free : user_low;
	aggregate.system_cdram_free_low_water =
		sample.system_cdram_free < cdram_low ? sample.system_cdram_free : cdram_low;
	aggregate.system_phycont_free_low_water =
		sample.system_phycont_free < phycont_low ? sample.system_phycont_free : phycont_low;
	aggregate.vitagl_ram_free_low_water =
		sample.vitagl_ram_free < ram_low ? sample.vitagl_ram_free : ram_low;
	aggregate.vitagl_vram_free_low_water =
		sample.vitagl_vram_free < vram_low ? sample.vitagl_vram_free : vram_low;
	aggregate.vitagl_slow_free_low_water =
		sample.vitagl_slow_free < slow_low ? sample.vitagl_slow_free : slow_low;
	aggregate.vitagl_all_free_low_water =
		sample.vitagl_all_free < all_low ? sample.vitagl_all_free : all_low;
}

A31RendererTelemetry Frame_Renderer_Telemetry(
	const A30WorldRuntimeFingerprint &world,
	const RenegadeVitaRenderer::Statistics &before,
	const RenegadeVitaRenderer::Statistics &after,
	uint64_t textures_resident, uint64_t texture_bytes_resident)
{
	A31RendererTelemetry output = {};
	output.render_objects = world.render_object_node_count;
	output.mesh_candidates = world.mesh_count;
	output.mesh_submissions = Delta_U32(after.mesh_submissions,
		before.mesh_submissions);
	output.lod_selections = output.mesh_submissions;
	output.indexed_draw_calls = Delta_U32(after.indexed_submissions,
		before.indexed_submissions);
	output.draw_calls = output.mesh_submissions + output.indexed_draw_calls;
	output.vertices = Delta_U32(after.vertex_submissions,
		before.vertex_submissions);
	output.triangles = Delta_U32(after.triangle_submissions,
		before.triangle_submissions);
	output.indexed_vertex_references = Delta_U32(
		after.indexed_vertex_references, before.indexed_vertex_references);
	output.indexed_triangles = Delta_U32(after.indexed_triangle_submissions,
		before.indexed_triangle_submissions);
	output.material_passes = Delta_U64(after.material_passes,
		before.material_passes);
	output.textures_resident = after.texture_resident;
	output.texture_bytes_resident = after.texture_bytes_resident;
	output.texture_uploads = Delta_U64(after.texture_uploads,
		before.texture_uploads);
	output.texture_binds = Delta_U64(after.texture_binds,
		before.texture_binds);
	output.texture_bind_skips = Delta_U64(after.texture_bind_skips,
		before.texture_bind_skips);
	output.texture_requests = Delta_U64(after.texture_requests,
		before.texture_requests);
	output.texture_decodes = Delta_U64(after.texture_decodes,
		before.texture_decodes);
	output.texture_missing = Delta_U64(after.texture_missing,
		before.texture_missing);
	output.texture_source_missing = Delta_U64(after.texture_source_missing,
		before.texture_source_missing);
	output.texture_invalid_data = Delta_U64(after.texture_invalid_data,
		before.texture_invalid_data);
	output.texture_unsupported_formats = Delta_U64(
		after.texture_unsupported_formats, before.texture_unsupported_formats);
	output.texture_decode_failures = Delta_U64(after.texture_decode_failures,
		before.texture_decode_failures);
	output.texture_upload_failures = Delta_U64(after.texture_upload_failures,
		before.texture_upload_failures);
	output.texture_checkerboard_fallbacks = Delta_U64(
		after.texture_checkerboard_fallbacks,
		before.texture_checkerboard_fallbacks);
	output.texture_invalid_binds = Delta_U64(after.texture_invalid_binds,
		before.texture_invalid_binds);
	output.texture_sampler_updates = Delta_U64(after.texture_sampler_updates,
		before.texture_sampler_updates);
	output.texture_sampler_skips = Delta_U64(after.texture_sampler_skips,
		before.texture_sampler_skips);
	output.texture_stage_enable_skips = Delta_U64(after.texture_stage_enable_skips,
		before.texture_stage_enable_skips);
	output.texture_combiner_skips = Delta_U64(after.texture_combiner_skips,
		before.texture_combiner_skips);
	output.texture_unsupported_stages = Delta_U64(after.texture_unsupported_stages,
		before.texture_unsupported_stages);
	output.state_changes = Delta_U64(after.state_changes,
		before.state_changes);
	output.render_state_skips = Delta_U64(after.render_state_skips,
		before.render_state_skips);
	output.rejected_submissions = Delta_U32(after.rejected_indexed_submissions,
		before.rejected_indexed_submissions);
	output.unsupported_submissions = Delta_U32(after.unsupported_submissions,
		before.unsupported_submissions);
	output.backend_errors = Delta_U64(after.backend_errors,
		before.backend_errors);
	output.geometry_checksum = after.geometry_checksum;
	output.indexed_geometry_checksum = after.indexed_geometry_checksum;
	output.visible_object_count = world.vis_object_count;
	output.visibility_sector_count = world.vis_sector_count;
	output.mesh_candidates_not_submitted =
		output.mesh_submissions < world.mesh_count ?
			world.mesh_count - static_cast<uint32_t>(output.mesh_submissions) : 0U;
	/* Original scene traversal exposes candidate and submitted sets here, but
	** not a one-to-one cull-reason counter. Keep the derived value explicit. */
	output.culling_count_exact = false;
	return output;
}

A31StateSnapshot Make_State_Snapshot(const A30WorldRuntimeFingerprint &world,
	const A31FrameTelemetry *frame, const A31CameraTelemetry *camera,
	const char *reason, const char *phase, uint64_t monotonic_us)
{
	A31StateSnapshot state = {};
	state.schema_version = A31_CAPTURE_SCHEMA_VERSION;
	snprintf(state.milestone, sizeof(state.milestone), "%s",
		RENEGADE_BUILD_CANDIDATE_LABEL);
	snprintf(state.build_label, sizeof(state.build_label), "%s",
		RENEGADE_BUILD_DISPLAY_LABEL);
	snprintf(state.capture_overlay_label, sizeof(state.capture_overlay_label), "%s",
		RENEGADE_BUILD_CAPTURE_OVERLAY);
	snprintf(state.runtime_log_path, sizeof(state.runtime_log_path), "%s",
		RENEGADE_BUILD_RUNTIME_LOG_PATH);
	snprintf(state.reason, sizeof(state.reason), "%s", reason);
	snprintf(state.phase, sizeof(state.phase), "%s", phase);
	snprintf(state.benchmark_route, sizeof(state.benchmark_route),
		"M00-fixed-camera-v1");
	state.capture_monotonic_us = monotonic_us;
	Copy_World_State(state.world, world);
	if (camera != NULL) state.camera = *camera;
	if (frame != NULL) {
		state.capture_frame = frame->frame_index;
		state.renderer = frame->renderer;
		state.memory = frame->memory;
		state.game_update_count = frame->game_update_count;
		state.physics_update_count = frame->physics_update_count;
		state.input_action_count = frame->input_action_count;
		state.benchmark_active = frame->benchmark_active;
		state.benchmark_point = frame->benchmark_point;
	}
	/* No original player or mission script instance exists in the accepted
	** static-world runtime yet. These become populated by the A3.1 Combat path. */
	state.player.present = false;
	state.scripts_active = false;
	state.sensors.available = false;
	return state;
}

A31CaptureBundleResult Write_Bundle(const char *label, const char *reason,
	const char *phase,
	const uint8_t *pixels, const A31FrameHistory &history,
	const A30WorldRuntimeFingerprint &world, const A31FrameTelemetry *frame,
	const A31CameraTelemetry *camera, uint64_t monotonic_us,
	uint64_t capture_readback_us)
{
	A31CaptureBundleInput input = {};
	input.base_directory = kA31CaptureRoot;
	input.bundle_label = label;
	input.resolved_rgba_bottom_up = pixels;
	input.framebuffer_width = RenegadeVitaRenderer::DISPLAY_WIDTH;
	input.framebuffer_height = RenegadeVitaRenderer::DISPLAY_HEIGHT;
	input.write_annotated_screenshot = pixels != NULL;
	input.state = Make_State_Snapshot(world, frame, camera, reason, phase,
		monotonic_us);
	input.state.capture_stall_us = capture_readback_us;
	input.history = &history;
	return A31_Write_Capture_Bundle(input);
}

} // namespace

int A30_Vita_Log_Reset()
{
	if (gA30RuntimeLogFile >= 0) {
		sceIoSyncByFd(gA30RuntimeLogFile, 0);
		sceIoClose(gA30RuntimeLogFile);
		gA30RuntimeLogFile = -1;
	}
	const int open_flags = SCE_O_WRONLY | SCE_O_CREAT | SCE_O_APPEND;
	gA30RuntimeLogFile = sceIoOpen(kA30RuntimeLog, open_flags, 0666);
	if (gA30RuntimeLogFile < 0) return gA30RuntimeLogFile;
	char header[320];
	const int header_count = snprintf(header, sizeof(header),
		"[LIFECYCLE] START status=begin mode=append candidate=%s log_path=%s\n",
		RENEGADE_BUILD_CANDIDATE_LABEL, RENEGADE_BUILD_RUNTIME_LOG_PATH);
	const int result = header_count > 0 ? Write_Runtime_Log_Line(header,
		static_cast<unsigned>(header_count)) : -1;
	const int sync_result = sceIoSyncByFd(gA30RuntimeLogFile, 0);
	return result >= 0 && sync_result < 0 ? sync_result : result;
}

int A30_Vita_Log(const char *format, ...)
{
	char line[768];
	va_list arguments;
	va_start(arguments, format);
	const int count = vsnprintf(line, sizeof(line), format, arguments);
	va_end(arguments);
	if (count <= 0) {
		return -1;
	}

	const unsigned length = static_cast<unsigned>(
		count < static_cast<int>(sizeof(line)) ? count :
		static_cast<int>(sizeof(line) - 1U));
	return Write_Runtime_Log_Line(line, length);
}

void A35_Vita_Static_Load_Trace_Begin(uint32_t object_index,
	uint32_t factory_id)
{
	gA35StaticTraceObjectIndex = object_index;
	gA35StaticTraceFactoryId = factory_id;
	gA35StaticTraceSummary = object_index == 0U ||
		(object_index % 25U) == 0U ||
		(object_index >= 108U && object_index <= 124U);
	gA35StaticTraceDeep = object_index == 116U;
	if (gA35StaticTraceSummary) {
		RenegadeVitaRenderer::BackendMemoryStatistics memory = {};
		if (RenegadeVitaRenderer::Query_Backend_Memory(memory)) {
			A30_Vita_Log(
				"A3.5 static direct: index=%u factory=%u phase=factory-load-entry memory_user=%lld memory_cdram=%lld memory_phycont=%lld vitagl_ram_free=%llu vitagl_vram_free=%llu vitagl_slow_free=%llu vitagl_all_free=%llu\n",
				static_cast<unsigned>(object_index),
				static_cast<unsigned>(factory_id),
				static_cast<long long>(memory.system_user_free),
				static_cast<long long>(memory.system_cdram_free),
				static_cast<long long>(memory.system_phycont_free),
				static_cast<unsigned long long>(memory.ram_free),
				static_cast<unsigned long long>(memory.vram_free),
				static_cast<unsigned long long>(memory.slow_free),
				static_cast<unsigned long long>(memory.all_free));
		} else {
			A30_Vita_Log(
				"A3.5 static direct: index=%u factory=%u phase=factory-load-entry memory=unavailable\n",
				static_cast<unsigned>(object_index),
				static_cast<unsigned>(factory_id));
		}
	}
}

void A35_Vita_Static_Load_Trace_Step(const char *phase, uint32_t detail_id)
{
	if (!gA35StaticTraceDeep) {
		return;
	}
	A30_Vita_Log(
		"A3.5 static direct: index=%u factory=%u phase=%s detail=%08X\n",
		static_cast<unsigned>(gA35StaticTraceObjectIndex),
		static_cast<unsigned>(gA35StaticTraceFactoryId), phase,
		static_cast<unsigned>(detail_id));
}

void A35_Vita_Static_Load_Trace_Name(const char *phase, const char *name)
{
	if (!gA35StaticTraceDeep) {
		return;
	}
	A30_Vita_Log(
		"A3.5 static direct: index=%u factory=%u phase=%s name=%.96s\n",
		static_cast<unsigned>(gA35StaticTraceObjectIndex),
		static_cast<unsigned>(gA35StaticTraceFactoryId), phase,
		name != NULL ? name : "(null)");
}

void A35_Vita_Static_Load_Trace_End()
{
	if (gA35StaticTraceSummary) {
		A30_Vita_Log(
			"A3.5 static direct: index=%u factory=%u phase=factory-load-return\n",
			static_cast<unsigned>(gA35StaticTraceObjectIndex),
			static_cast<unsigned>(gA35StaticTraceFactoryId));
	}
	gA35StaticTraceSummary = false;
	gA35StaticTraceDeep = false;
}

bool A30_Vita_Render_Loaded_World(void *context, PhysicsSceneClass &scene,
	WW3DAssetManager &asset_manager, const A30WorldRuntimeFingerprint &world)
{
	(void)asset_manager;
	A30VitaWorldRenderResult *result =
		static_cast<A30VitaWorldRenderResult *>(context);
	if (result == NULL) {
		return false;
	}
	*result = {};
	result->attempted = true;
	A30_Vita_Log("Stage: loaded-world callback entry\n");
	const RenegadeVitaRenderer::BackendLifecycleStatistics &active_lifecycle =
		RenegadeVitaRenderer::Get_Backend_Lifecycle_Statistics();
	A30_Vita_Log(
		"Renderer lifecycle at world entry: native_attempted/ready/calls=%d/%d/%u logical_active/sessions/shutdowns=%d/%u/%u\n",
		active_lifecycle.native_initialization_attempted ? 1 : 0,
		active_lifecycle.native_backend_ready ? 1 : 0,
		active_lifecycle.native_initialization_calls,
		active_lifecycle.logical_session_active ? 1 : 0,
		active_lifecycle.logical_sessions,
		active_lifecycle.logical_shutdowns);

	Vector3 level_min;
	Vector3 level_max;
	scene.Get_Level_Extents(level_min, level_max);
	Vector3 target = (level_min + level_max) * 0.5f;
	const Vector3 span = level_max - level_min;
	const float largest_span =
		span.X > span.Y ? (span.X > span.Z ? span.X : span.Z) :
		(span.Y > span.Z ? span.Y : span.Z);
	float yaw = 0.0f;
	float pitch = 0.30f;
	float distance = largest_span * 0.78f;
	result->near_clip = 0.5f;
	result->far_clip = largest_span * 4.0f;

	CameraClass *camera = new CameraClass;
	if (camera == NULL) {
		result->render_error = true;
		A30_Vita_Log("CameraClass allocation: FAIL\n");
		return false;
	}
	camera->Set_Aspect_Ratio(960.0f / 544.0f);
	camera->Set_Clip_Planes(result->near_clip, result->far_clip);
	result->camera_initialized = true;
	A30_Vita_Log(
		"Original CameraClass: PASS extents=(%.6f,%.6f,%.6f)..(%.6f,%.6f,%.6f) clip=%.3f..%.3f\n",
		level_min.X, level_min.Y, level_min.Z, level_max.X, level_max.Y,
		level_max.Z, result->near_clip, result->far_clip);

	RenegadeVitaRenderer::Reset_Statistics();
	const uint64_t start_us = sceKernelGetProcessTimeWide();
	uint64_t previous_us = start_us;
	/* WW3D::Shutdown deliberately retains the original static SyncTime.  The
	** A2.2 regression has therefore already advanced it before this second
	** logical WW3D session.  Continue from that value so Get_Frame_Time never
	** observes unsigned underflow on the first live-world frame. */
	const uint32_t sync_origin = WW3D::Get_Sync_Time();
	A30_Vita_Log("WW3D monotonic sync continuation: origin=%u\n", sync_origin);
	uint32_t local_frames = 0U;
	uint32_t previous_buttons = 0U;
	uint64_t excluded_capture_us = 0U;
	uint64_t input_action_count = 0U;
	A31FrameHistory frame_history;
	A31M00BenchmarkRoute benchmark;
	bool first_static_capture_pending = true;
	A31MemoryTelemetry sampled_memory = {};
	A31MemoryTelemetry memory_low_water = {};
	/* The accepted A3.0 backend does not upload or bind texture resources yet.
	** Report native residency as zero instead of invoking WW3D's Direct3D
	** surface-accounting path, which describes a backend that is intentionally
	** absent on Vita. The renderer counters will become authoritative when the
	** native texture boundary is implemented. */
	uint64_t sampled_texture_count = 0U;
	uint64_t sampled_texture_bytes = 0U;
	A31CameraTelemetry camera_state = {};
	uint8_t *resolved_frame = static_cast<uint8_t *>(malloc(kResolvedFrameBytes));
	A30_Vita_Log(
		"A3.1 capture telemetry: ring=%u frames resolved_bytes=%u buffer=%s SELECT=capture SELECT+L+R=benchmark route=M00-fixed-camera-v1\n",
		A31_FRAME_HISTORY_CAPACITY, static_cast<unsigned>(kResolvedFrameBytes),
		resolved_frame != NULL ? "ready" : "unavailable");
	Query_Memory(sampled_memory);
	Initialize_Memory_Low_Water(memory_low_water, sampled_memory);
	bool continue_rendering = true;
	while (continue_rendering) {
		const uint64_t frame_start_us = sceKernelGetProcessTimeWide();
		const uint64_t now_us = frame_start_us;
		float elapsed_seconds =
			static_cast<float>(now_us - previous_us) * (1.0f / 1000000.0f);
		previous_us = now_us;
		if (elapsed_seconds < 0.0f) {
			elapsed_seconds = 0.0f;
		} else if (elapsed_seconds > 0.1f) {
			elapsed_seconds = 0.1f;
		}

		A31FrameTelemetry frame = {};
		frame.frame_index = static_cast<uint64_t>(local_frames) + 1U;
		frame.monotonic_us = now_us;
		const RenegadeVitaRenderer::Statistics statistics_before =
			RenegadeVitaRenderer::Get_Statistics();
		const uint64_t input_start_us = sceKernelGetProcessTimeWide();
		SceCtrlData controller = {};
		bool capture_requested = first_static_capture_pending;
		if (sceCtrlPeekBufferPositive(0, &controller, 1) > 0) {
			if ((controller.buttons & SCE_CTRL_START) != 0U) {
				result->clean_exit_requested = true;
				break;
			}
			const bool select_pressed =
				(controller.buttons & SCE_CTRL_SELECT) != 0U &&
				(previous_buttons & SCE_CTRL_SELECT) == 0U;
			const bool benchmark_chord =
				(controller.buttons & (SCE_CTRL_LTRIGGER | SCE_CTRL_RTRIGGER)) ==
					(SCE_CTRL_LTRIGGER | SCE_CTRL_RTRIGGER);
			if (select_pressed && benchmark_chord) {
				benchmark.Start(local_frames);
				A30_Vita_Log(
					"A3.1 deterministic benchmark started: route=M00-fixed-camera-v1 frame=%u points=4 duration=480\n",
					local_frames);
			} else if (select_pressed) {
				capture_requested = true;
			}

			if (!benchmark.Is_Active()) {
				const float look_scale = elapsed_seconds * 1.8f;
				yaw += Analog_Axis(controller.rx) * look_scale;
				pitch -= Analog_Axis(controller.ry) * look_scale;
				if (pitch > 1.25f) {
					pitch = 1.25f;
				} else if (pitch < -1.25f) {
					pitch = -1.25f;
				}

				const float move_scale = elapsed_seconds * largest_span * 0.28f;
				const float strafe = Analog_Axis(controller.lx) * move_scale;
				const float forward = -Analog_Axis(controller.ly) * move_scale;
				target.X += cosf(yaw) * strafe + sinf(yaw) * forward;
				target.Y += sinf(yaw) * strafe - cosf(yaw) * forward;
				if ((controller.buttons & SCE_CTRL_LTRIGGER) != 0U) distance += move_scale;
				if ((controller.buttons & SCE_CTRL_RTRIGGER) != 0U) distance -= move_scale;
				const float minimum_distance = largest_span * 0.05f;
				const float maximum_distance = largest_span * 2.5f;
				if (distance < minimum_distance) distance = minimum_distance;
				else if (distance > maximum_distance) distance = maximum_distance;
			}
			previous_buttons = controller.buttons;
		}
		frame.stages.input_us = sceKernelGetProcessTimeWide() - input_start_us;

		if (benchmark.Is_Active() && benchmark.Is_Capture_Frame(local_frames)) {
			capture_requested = true;
		}

		const uint64_t camera_start_us = sceKernelGetProcessTimeWide();
		Vector3 frame_target = target;
		Vector3 camera_position;
		if (benchmark.Is_Active()) {
			const A31BenchmarkPoint &point = benchmark.Point(local_frames);
			camera_position.Set(point.camera_position[0], point.camera_position[1],
				point.camera_position[2]);
			frame_target.Set(point.camera_target[0], point.camera_target[1],
				point.camera_target[2]);
			frame.benchmark_active = true;
			frame.benchmark_point = benchmark.Point_Index(local_frames);
		} else {
			const float horizontal_distance = distance * cosf(pitch);
			camera_position.Set(
				target.X + horizontal_distance * sinf(yaw),
				target.Y - horizontal_distance * cosf(yaw),
				target.Z + distance * sinf(pitch));
		}
		Matrix3D camera_transform(1);
		camera_transform.Look_At(camera_position, frame_target, 0.0f);
		camera->Set_Transform(camera_transform);
		Copy_Vector(result->camera_position, camera_position);
		Copy_Vector(result->camera_target, frame_target);
		Copy_Camera_State(camera_state, camera_transform, camera_position,
			frame_target, result->near_clip, result->far_clip);
		frame.stages.camera_us = sceKernelGetProcessTimeWide() - camera_start_us;

		const uint32_t elapsed_ms = static_cast<uint32_t>(
			(now_us - start_us - excluded_capture_us) / 1000ULL);
		WW3D::Sync(sync_origin + elapsed_ms);
		const uint64_t visibility_start_us = sceKernelGetProcessTimeWide();
		scene.Pre_Render_Processing(*camera);
		frame.stages.visibility_us =
			sceKernelGetProcessTimeWide() - visibility_start_us;
		const uint64_t render_start_us = sceKernelGetProcessTimeWide();
		const bool began = WW3D::Begin_Render(true, true,
			Vector3(0.035f, 0.055f, 0.085f)) == WW3D_ERROR_OK;
		const bool rendered = began &&
			WW3D::Render(&scene, camera) == WW3D_ERROR_OK;
		frame.stages.render_us = sceKernelGetProcessTimeWide() - render_start_us;
		bool capture_readback_ok = false;
		if (capture_requested && resolved_frame != NULL && rendered) {
			const uint64_t readback_start_us = sceKernelGetProcessTimeWide();
			capture_readback_ok = RenegadeVitaRenderer::Capture_Resolved_Frame_RGBA(
				resolved_frame, kResolvedFrameBytes);
			frame.stages.capture_readback_us =
				sceKernelGetProcessTimeWide() - readback_start_us;
		}
		const uint64_t present_start_us = sceKernelGetProcessTimeWide();
		const bool ended = rendered &&
			WW3D::End_Render(true) == WW3D_ERROR_OK;
		frame.stages.present_us = sceKernelGetProcessTimeWide() - present_start_us;
		const uint64_t housekeeping_start_us = sceKernelGetProcessTimeWide();
		scene.Post_Render_Processing();
		frame.stages.housekeeping_us =
			sceKernelGetProcessTimeWide() - housekeeping_start_us;
		if (!(began && rendered && ended)) {
			result->render_error = true;
			A30_Vita_Log(
				"Original world frame: FAIL frame=%u begin=%d render=%d end=%d\n",
				local_frames, began ? 1 : 0, rendered ? 1 : 0,
				ended ? 1 : 0);
			break;
		}

		++local_frames;
		if ((local_frames % 60U) == 0U || capture_requested) {
			Query_Memory(sampled_memory);
			Update_Memory_Low_Water(memory_low_water, sampled_memory);
		}
		const RenegadeVitaRenderer::Statistics statistics_after =
			RenegadeVitaRenderer::Get_Statistics();
		frame.renderer = Frame_Renderer_Telemetry(world, statistics_before,
			statistics_after, sampled_texture_count, sampled_texture_bytes);
		frame.memory = memory_low_water;
		frame.input_action_count = input_action_count;
		frame.frame_time_us = sceKernelGetProcessTimeWide() - frame_start_us;
		frame.ordinary_frame_time_us =
			frame.frame_time_us >= frame.stages.capture_readback_us ?
				frame.frame_time_us - frame.stages.capture_readback_us : 0U;
		frame_history.Push(frame);
		Copy_Statistics(*result);
		if (!result->first_frame_completed) {
			result->first_frame_completed = true;
			A30_Vita_Log(
				"First original M00 frame: PASS meshes=%u vertices=%u triangles=%u indexed=%u indexed_triangles=%u unsupported=%u checksum=%08X/%08X\n",
				result->mesh_submissions, result->vertex_submissions,
				result->triangle_submissions, result->indexed_submissions,
				result->indexed_triangle_submissions,
				result->unsupported_submissions, result->geometry_checksum,
				result->indexed_geometry_checksum);
		} else if ((local_frames % 120U) == 0U) {
			A30_Vita_Log(
				"World frame=%u meshes=%u vertices=%u triangles=%u indexed=%u rejected=%u unsupported=%u checksum=%08X/%08X\n",
				result->frames, result->mesh_submissions,
				result->vertex_submissions, result->triangle_submissions,
				result->indexed_submissions,
				result->rejected_indexed_submissions,
				result->unsupported_submissions, result->geometry_checksum,
				result->indexed_geometry_checksum);
		}

		if (capture_requested) {
			char label[96];
			const char *reason = first_static_capture_pending ?
				"first-static-world-frame" : (benchmark.Is_Active() ?
					"benchmark-capture" : "select-capture");
			snprintf(label, sizeof(label), "%s-p%u-f%llu-t%llu", reason,
				frame.benchmark_point, (unsigned long long)frame.frame_index,
				(unsigned long long)frame.monotonic_us);
			const A31CaptureBundleResult capture = Write_Bundle(label, reason,
				"static-world",
				capture_readback_ok ? resolved_frame : NULL, frame_history, world,
				&frame, &camera_state, frame.monotonic_us,
				frame.stages.capture_readback_us);
			const uint64_t capture_stall = frame.stages.capture_readback_us +
				capture.write_stall_us;
			excluded_capture_us += capture_stall;
			previous_us = sceKernelGetProcessTimeWide();
			if (first_static_capture_pending && capture.passed) {
				first_static_capture_pending = false;
			}
			A30_Vita_Log(
				"Capture: %s candidate=%s phase=static-world reason=%s path=%s screenshot/annotated/state/csv/summary/failure_marker=%d/%d/%d/%d/%d/%d error_code=%d stall_us=%llu excluded_from_timing=1 first_error=%s\n",
				capture.passed ? "PASS" : "FAIL", RENEGADE_BUILD_CANDIDATE_LABEL,
				reason, capture.bundle_path,
				capture.screenshot_written ? 1 : 0,
				capture.annotated_screenshot_written ? 1 : 0,
				capture.state_written ? 1 : 0, capture.history_written ? 1 : 0,
				capture.summary_written ? 1 : 0,
				capture.failure_marker_written ? 1 : 0, capture.first_error_code,
				(unsigned long long)capture_stall,
				capture.first_error[0] != 0 ? capture.first_error : "none");
		}

		if (benchmark.Is_Complete(local_frames)) {
			benchmark.Stop();
			frame.benchmark_active = false;
			char label[96];
			snprintf(label, sizeof(label), "benchmark-complete-f%u-t%llu",
				local_frames, (unsigned long long)sceKernelGetProcessTimeWide());
			const A31CaptureBundleResult completion = Write_Bundle(label,
				"benchmark-complete", "static-world", NULL, frame_history, world, &frame,
				&camera_state, sceKernelGetProcessTimeWide(), 0U);
			excluded_capture_us += completion.write_stall_us;
			previous_us = sceKernelGetProcessTimeWide();
			A30_Vita_Log(
				"A3.1 deterministic benchmark complete: %s path=%s frames=480 write_stall_us=%llu excluded_from_timing=1\n",
				completion.passed ? "PASS" : "FAIL", completion.bundle_path,
				(unsigned long long)completion.write_stall_us);
		}
	}
	const A31FrameTelemetry *last_frame = frame_history.Count() != 0U ?
		&frame_history.Oldest(frame_history.Count() - 1U) : NULL;
	char flush_label[96];
	const char *flush_reason = result->render_error ? "render-error" :
		(result->clean_exit_requested ? "orderly-exit" : "runtime-exit");
	const uint64_t flush_us = sceKernelGetProcessTimeWide();
	snprintf(flush_label, sizeof(flush_label), "%s-f%u-t%llu", flush_reason,
		local_frames, (unsigned long long)flush_us);
	const A31CaptureBundleResult flush = Write_Bundle(flush_label, flush_reason,
		"static-world", NULL, frame_history, world, last_frame, &camera_state, flush_us, 0U);
	A30_Vita_Log(
		"Capture flush: %s candidate=%s phase=static-world reason=%s path=%s state/csv/summary/failure_marker=%d/%d/%d/%d error_code=%d frames=%u stall_us=%llu first_error=%s\n",
		flush.passed ? "PASS" : "FAIL", RENEGADE_BUILD_CANDIDATE_LABEL,
		flush_reason, flush.bundle_path,
		flush.state_written ? 1 : 0, flush.history_written ? 1 : 0,
		flush.summary_written ? 1 : 0,
		flush.failure_marker_written ? 1 : 0, flush.first_error_code,
		static_cast<unsigned>(frame_history.Count()),
		(unsigned long long)flush.write_stall_us,
		flush.first_error[0] != 0 ? flush.first_error : "none");
	free(resolved_frame);

	Copy_Statistics(*result);
	A30_Vita_Log(
		"Loaded-world callback exit: first_frame=%d START=%d render_error=%d frames=%u meshes=%u vertices=%u triangles=%u indexed=%u rejected=%u unsupported=%u checksum=%08X/%08X\n",
		result->first_frame_completed ? 1 : 0,
		result->clean_exit_requested ? 1 : 0,
		result->render_error ? 1 : 0, result->frames,
		result->mesh_submissions, result->vertex_submissions,
		result->triangle_submissions, result->indexed_submissions,
		result->rejected_indexed_submissions,
		result->unsupported_submissions, result->geometry_checksum,
		result->indexed_geometry_checksum);
	camera->Release_Ref();
	return result->first_frame_completed && result->clean_exit_requested &&
		!result->render_error;
}

void A30_Vita_Log_World_Result(const A30WorldRuntimeResult &world_result,
	const A30VitaWorldRenderResult &render_result)
{
	const A30WorldRuntimeFingerprint &world = world_result.world;
	A30_Vita_Log("\nA3.0 ORIGINAL M00 WORLD RUNTIME\n");
	A30_Vita_Log("Overall: %s (%u checks, %u failures; first=%s)\n",
		world_result.passed ? "PASS" : "FAIL", world_result.checks,
		world_result.failures, world_result.first_failure);
	A30_Vita_Log(
		"Initialization: file_factory=%d subsystems=%u/%u factories=%u/%u WW3D=%d WWPhys=%d WWSaveLoad=%d armor=%d scene=%d\n",
		world.factory_chain_ready ? 1 : 0,
		world.registered_subsystem_count, world.required_subsystem_count,
		world.registered_persist_factory_count,
		world.required_persist_factory_count,
		world.ww3d_initialized ? 1 : 0, world.wwphys_initialized ? 1 : 0,
		world.wwsaveload_initialized ? 1 : 0,
		world.armor_warhead_initialized ? 1 : 0,
		world.physics_scene_initialized ? 1 : 0);
	A30_Vita_Log(
		"Definitions: count=%u twiddlers=%u armor=%u warheads=%u checksum=%08X optional_ddb_missing/noop=%d/%d\n",
		world.definition_count, world.twiddler_definition_count,
		world.armor_type_count, world.warhead_type_count,
		world.definition_checksum, world.optional_level_ddb_missing ? 1 : 0,
		world.optional_level_ddb_noop ? 1 : 0);
	A30_Vita_Log(
		"World: loaded/post/pathfind=%d/%d/%d objects=%u lights=%u nodes=%u meshes=%u vertices=%llu polygons=%llu prototypes=%u vis=%u/%u\n",
		world.m00_static_world_loaded ? 1 : 0,
		world.post_load_completed ? 1 : 0,
		world.pathfind_data_loaded ? 1 : 0, world.static_object_count,
		world.static_light_count, world.render_object_node_count,
		world.mesh_count,
		static_cast<unsigned long long>(world.mesh_vertex_count),
		static_cast<unsigned long long>(world.mesh_polygon_count),
		world.loaded_prototype_count, world.vis_object_count,
		world.vis_sector_count);
	A30_Vita_Log(
		"World fingerprints: definition=%08X object=%08X render=%08X prototype=%08X extents=(%.6f,%.6f,%.6f)..(%.6f,%.6f,%.6f)\n",
		world.definition_checksum, world.object_identity_checksum,
		world.render_graph_checksum, world.prototype_checksum,
		world.level_min[0], world.level_min[1], world.level_min[2],
		world.level_max[0], world.level_max[1], world.level_max[2]);
	A30_Vita_Log(
		"Render: attempted/camera/first/START/error=%d/%d/%d/%d/%d frames=%u meshes=%u vertices=%u triangles=%u indexed=%u rejected=%u unsupported=%u checksum=%08X/%08X\n",
		render_result.attempted ? 1 : 0,
		render_result.camera_initialized ? 1 : 0,
		render_result.first_frame_completed ? 1 : 0,
		render_result.clean_exit_requested ? 1 : 0,
		render_result.render_error ? 1 : 0, render_result.frames,
		render_result.mesh_submissions, render_result.vertex_submissions,
		render_result.triangle_submissions, render_result.indexed_submissions,
		render_result.rejected_indexed_submissions,
		render_result.unsupported_submissions,
		render_result.geometry_checksum,
		render_result.indexed_geometry_checksum);
	A30_Vita_Log("Teardown: %s\n",
		world.teardown_completed ? "PASS" : "FAIL");
}
