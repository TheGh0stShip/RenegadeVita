#include "a31_capture_telemetry.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

namespace {

bool Exists(const char *directory, const char *name)
{
	char path[512];
	snprintf(path, sizeof(path), "%s/bundle/%s", directory, name);
	struct stat status = {};
	return stat(path, &status) == 0 && status.st_size > 0;
}

bool Root_Exists(const char *directory, const char *name)
{
	char path[512];
	snprintf(path, sizeof(path), "%s/%s", directory, name);
	struct stat status = {};
	return stat(path, &status) == 0 && status.st_size > 0;
}

bool Summary_Contains(const char *directory, const char *needle)
{
	char path[512];
	snprintf(path, sizeof(path), "%s/bundle/summary.txt", directory);
	FILE *file = fopen(path, "rb");
	if (file == NULL) return false;
	char buffer[4096] = {};
	const size_t bytes = fread(buffer, 1U, sizeof(buffer) - 1U, file);
	fclose(file);
	buffer[bytes] = 0;
	return strstr(buffer, needle) != NULL;
}

bool State_Contains(const char *directory, const char *needle)
{
	char path[512];
	snprintf(path, sizeof(path), "%s/bundle/state.json", directory);
	FILE *file = fopen(path, "rb");
	if (file == NULL) return false;
	char buffer[4096] = {};
	const size_t bytes = fread(buffer, 1U, sizeof(buffer) - 1U, file);
	fclose(file);
	buffer[bytes] = 0;
	return strstr(buffer, needle) != NULL;
}

bool Bundle_File_Contains(const char *directory, const char *bundle,
	const char *name, const char *needle)
{
	char path[512];
	snprintf(path, sizeof(path), "%s/%s/%s", directory, bundle, name);
	FILE *file = fopen(path, "rb");
	if (file == NULL) return false;
	char buffer[4096] = {};
	const size_t bytes = fread(buffer, 1U, sizeof(buffer) - 1U, file);
	fclose(file);
	buffer[bytes] = 0;
	return strstr(buffer, needle) != NULL;
}

void Check(bool condition, const char *name, unsigned &checks,
	unsigned &failures)
{
	++checks;
	if (!condition) {
		++failures;
		fprintf(stderr, "capture telemetry check failed: %s\n", name);
	}
}

} // namespace

int main()
{
	unsigned checks = 0U;
	unsigned failures = 0U;
	char directory[] = "/tmp/renegade-a31-capture-XXXXXX";
	Check(mkdtemp(directory) != NULL, "temporary capture root", checks, failures);

	A31FrameHistory history;
	A31FrameTelemetry first = {};
	first.frame_index = 1U;
	first.frame_time_us = 17000U;
	first.ordinary_frame_time_us = 16000U;
	first.stages.capture_readback_us = 1000U;
	first.renderer.draw_calls = 2U;
	first.renderer.triangles = 4U;
	history.Push(first);
	A31FrameTelemetry second = first;
	second.frame_index = 2U;
	second.ordinary_frame_time_us = 15000U;
	history.Push(second);
	Check(history.Count() == 2U && history.Oldest(0).frame_index == 1U &&
		history.Oldest(1).frame_index == 2U, "ordered frame history", checks, failures);

	uint8_t pixels[4U * 4U * 4U];
	for (unsigned index = 0U; index < sizeof(pixels); index += 4U) {
		pixels[index + 0U] = static_cast<uint8_t>(index);
		pixels[index + 1U] = 80U;
		pixels[index + 2U] = 160U;
		pixels[index + 3U] = 255U;
	}
	A31CaptureBundleInput input = {};
	input.base_directory = directory;
	input.bundle_label = "bundle";
	input.resolved_rgba_bottom_up = pixels;
	input.framebuffer_width = 4U;
	input.framebuffer_height = 4U;
	input.write_annotated_screenshot = true;
	input.state.schema_version = A31_CAPTURE_SCHEMA_VERSION;
	snprintf(input.state.milestone, sizeof(input.state.milestone), "A3.5-host");
	snprintf(input.state.build_label, sizeof(input.state.build_label),
		"Renegade Vita A3.5-host");
	snprintf(input.state.capture_overlay_label, sizeof(input.state.capture_overlay_label),
		"A3.5-host CAPTURE");
	snprintf(input.state.runtime_log_path, sizeof(input.state.runtime_log_path),
		"ux0:data/renegade/user/logs/a35-host-runtime.log");
	snprintf(input.state.reason, sizeof(input.state.reason), "host-selftest");
	snprintf(input.state.phase, sizeof(input.state.phase), "host-fixture");
	snprintf(input.state.benchmark_route, sizeof(input.state.benchmark_route),
		"M00-fixed-camera-v1");
	input.state.capture_frame = 2U;
	input.state.world.definition_count = 2157U;
	input.state.renderer = second.renderer;
	input.state.memory.available = true;
	input.state.memory.sample_count = 3U;
	input.state.memory.system_user_free = 120U;
	input.state.memory.system_user_free_low_water = 100U;
	input.state.memory.vitagl_ram_free_low_water = 80U;
	input.state.loading_visual_gate.active = true;
	input.state.loading_visual_gate.framebuffer_width = 960U;
	input.state.loading_visual_gate.framebuffer_height = 544U;
	input.state.loading_visual_gate.original_logical_width = 640U;
	input.state.loading_visual_gate.original_logical_height = 480U;
	input.state.loading_visual_gate.native_display_width = 960U;
	input.state.loading_visual_gate.native_display_height = 544U;
	input.state.loading_visual_gate.logical_to_native_fullscreen = true;
	input.state.loading_visual_gate.original_loading_screen_owner = true;
	input.state.loading_visual_gate.direct_vitagl_overlay_disabled = true;
	input.state.loading_visual_gate.loading_texture_v_flip_enabled = true;
	input.state.loading_visual_gate.gameplay_texture_v_unchanged = true;
	input.history = &history;
	const A31CaptureBundleResult result = A31_Write_Capture_Bundle(input);
	if (!result.passed) {
		fprintf(stderr,
			"capture result: screenshot/annotated/state/history/summary/marker=%d/%d/%d/%d/%d/%d error=%d:%s\n",
			result.screenshot_written ? 1 : 0,
			result.annotated_screenshot_written ? 1 : 0,
			result.state_written ? 1 : 0, result.history_written ? 1 : 0,
			result.summary_written ? 1 : 0, result.failure_marker_written ? 1 : 0,
			result.first_error_code, result.first_error);
	}
	Check(result.passed, "correlated capture bundle", checks, failures);
	Check(Exists(directory, "frame.bmp"), "clean screenshot", checks, failures);
	Check(Exists(directory, "frame-annotated.bmp"), "annotated screenshot", checks, failures);
	Check(Exists(directory, "state.json"), "JSON state", checks, failures);
	Check(Exists(directory, "frames.csv"), "CSV history", checks, failures);
	Check(Exists(directory, "summary.txt"), "text summary", checks, failures);
	Check(Summary_Contains(directory, "min/p50/p95/p99/mean/max"),
		"summary percentiles", checks, failures);
	Check(Summary_Contains(directory, "sampled low-water"),
		"summary memory low-water", checks, failures);
	Check(State_Contains(directory, "\"schema_version\":4") &&
		State_Contains(directory, "\"system_user_free_low_water\":100"),
		"schema four low-water state", checks, failures);
	Check(State_Contains(directory, "\"loading_visual_gate\"") &&
		State_Contains(directory, "\"original_logical_width\":640") &&
		State_Contains(directory, "\"native_display_width\":960") &&
		State_Contains(directory, "\"logical_to_native_fullscreen\":true") &&
		State_Contains(directory, "\"direct_vitagl_overlay_disabled\":true") &&
		State_Contains(directory, "\"loading_texture_v_flip_enabled\":true") &&
		Summary_Contains(directory, "Loading visual gate: active=1 logical=640x480 native=960x544 framebuffer=960x544 fullscreen=1"),
		"loading visual gate state and summary", checks, failures);
	Check(State_Contains(directory, "\"phase\":\"host-fixture\"") &&
		State_Contains(directory, "\"runtime_log_path\":\"ux0:data/renegade/user/logs/a35-host-runtime.log\""),
		"capture identity and phase state", checks, failures);

	A31CaptureBundleInput interactive_input = input;
	interactive_input.bundle_label = "interactive-fixture";
	snprintf(interactive_input.state.reason, sizeof(interactive_input.state.reason),
		"first-interactive-player-frame");
	snprintf(interactive_input.state.phase, sizeof(interactive_input.state.phase),
		"interactive-player-owned");
	interactive_input.state.player.present = true;
	interactive_input.state.player.object_id = 73U;
	interactive_input.state.camera.player_owned = true;
	interactive_input.state.game_update_count = 1U;
	interactive_input.state.physics_update_count = 1U;
	interactive_input.state.input_action_count = 1U;
	const A31CaptureBundleResult interactive_result =
		A31_Write_Capture_Bundle(interactive_input);
	Check(interactive_result.passed, "simulated interactive capture bundle", checks, failures);
	Check(Bundle_File_Contains(directory, "interactive-fixture", "state.json",
		"\"phase\":\"interactive-player-owned\"") &&
		Bundle_File_Contains(directory, "interactive-fixture", "state.json",
			"\"present\":true") &&
		Bundle_File_Contains(directory, "interactive-fixture", "frame-annotated.bmp", "BM"),
		"simulated interactive player capture metadata and BMP", checks, failures);

	char overlay[256] = {};
	A31StateSnapshot overlay_state = input.state;
	overlay_state.capture_frame = 0U;
	overlay_state.renderer.draw_calls = 0U;
	overlay_state.renderer.triangles = 0U;
	Check(A31_Format_Capture_Overlay(overlay, sizeof(overlay), overlay_state, history) &&
		strstr(overlay, "FRAME 0") != NULL && strstr(overlay, "DRAW 0") != NULL,
		"overlay formats zero telemetry", checks, failures);
	overlay_state.capture_frame = UINT64_MAX;
	overlay_state.renderer.draw_calls = 634U;
	overlay_state.renderer.triangles = UINT64_MAX;
	Check(A31_Format_Capture_Overlay(overlay, sizeof(overlay), overlay_state, history) &&
		strstr(overlay, "DRAW 634") != NULL &&
		strstr(overlay, "TRI 18446744073709551615") != NULL,
		"overlay formats ordinary and maximum fixed-width telemetry", checks, failures);

	A31CaptureBundleInput failed_input = input;
	failed_input.bundle_label = "missing-parent/bundle";
	const A31CaptureBundleResult failed_bundle = A31_Write_Capture_Bundle(failed_input);
	Check(!failed_bundle.passed && failed_bundle.failure_marker_written,
		"capture failure writes a marker outside incomplete bundle", checks, failures);
	Check(Root_Exists(directory, "capture-write-failure.txt"),
		"capture failure marker is nonempty", checks, failures);

	A31M00BenchmarkRoute route;
	route.Start(10U);
	Check(route.Is_Active() && route.Point_Index(10U) == 0U,
		"benchmark starts at point zero", checks, failures);
	Check(route.Is_Capture_Frame(100U), "first fixed capture point", checks, failures);
	Check(route.Point_Index(130U) == 1U, "second fixed camera point", checks, failures);
	Check(route.Is_Capture_Frame(220U), "second fixed capture point", checks, failures);
	Check(route.Is_Complete(490U), "fixed route completion", checks, failures);
	route.Stop();
	Check(!route.Is_Active(), "benchmark stop", checks, failures);

	printf("A3.1 capture telemetry host self-test: %s (%u checks, %u failures)\n",
		failures == 0U ? "PASS" : "FAIL", checks, failures);
	return failures == 0U ? 0 : 1;
}
