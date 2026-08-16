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
	snprintf(input.state.milestone, sizeof(input.state.milestone), "A3.1");
	snprintf(input.state.reason, sizeof(input.state.reason), "host-selftest");
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
	input.history = &history;
	const A31CaptureBundleResult result = A31_Write_Capture_Bundle(input);
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
	Check(State_Contains(directory, "\"schema_version\":2") &&
		State_Contains(directory, "\"system_user_free_low_water\":100"),
		"schema two low-water state", checks, failures);

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
