#pragma once

#include <stddef.h>
#include <stdint.h>

enum : uint32_t {
	/* Schema v3 adds canonical candidate/log identity and explicit phase labels.
	** Memory values remain sampled rather than ownership accounting. */
	A31_CAPTURE_SCHEMA_VERSION = 3U,
	A31_FRAME_HISTORY_CAPACITY = 240U,
	A31_CAPTURE_PATH_CAPACITY = 320U
};

struct A31StageTimings
{
	uint64_t input_us;
	uint64_t game_update_us;
	uint64_t physics_us;
	uint64_t camera_us;
	uint64_t visibility_us;
	uint64_t render_us;
	uint64_t present_us;
	uint64_t housekeeping_us;
	uint64_t capture_readback_us;
};

struct A31RendererTelemetry
{
	uint64_t render_objects;
	uint64_t mesh_candidates;
	uint64_t lod_selections;
	uint64_t draw_calls;
	uint64_t mesh_submissions;
	uint64_t vertices;
	uint64_t triangles;
	uint64_t indexed_draw_calls;
	uint64_t indexed_vertex_references;
	uint64_t indexed_triangles;
	uint64_t material_passes;
	uint64_t textures_resident;
	uint64_t texture_bytes_resident;
	uint64_t texture_uploads;
	uint64_t texture_binds;
	uint64_t texture_requests;
	uint64_t texture_decodes;
	uint64_t texture_missing;
	uint64_t texture_source_missing;
	uint64_t texture_invalid_data;
	uint64_t texture_unsupported_formats;
	uint64_t texture_decode_failures;
	uint64_t texture_upload_failures;
	uint64_t texture_checkerboard_fallbacks;
	uint64_t texture_invalid_binds;
	uint64_t state_changes;
	uint64_t rejected_submissions;
	uint64_t unsupported_submissions;
	uint64_t backend_errors;
	uint32_t geometry_checksum;
	uint32_t indexed_geometry_checksum;
	uint32_t visible_object_count;
	uint32_t visibility_sector_count;
	uint32_t mesh_candidates_not_submitted;
	bool culling_count_exact;
};

struct A31MemoryTelemetry
{
	bool available;
	uint32_t sample_count;
	int64_t system_user_free;
	int64_t system_cdram_free;
	int64_t system_phycont_free;
	uint64_t vitagl_ram_total;
	uint64_t vitagl_ram_free;
	uint64_t vitagl_vram_total;
	uint64_t vitagl_vram_free;
	uint64_t vitagl_slow_total;
	uint64_t vitagl_slow_free;
	uint64_t vitagl_all_total;
	uint64_t vitagl_all_free;
	int64_t system_user_free_low_water;
	int64_t system_cdram_free_low_water;
	int64_t system_phycont_free_low_water;
	uint64_t vitagl_ram_free_low_water;
	uint64_t vitagl_vram_free_low_water;
	uint64_t vitagl_slow_free_low_water;
	uint64_t vitagl_all_free_low_water;
};

struct A31PlayerTelemetry
{
	bool present;
	uint32_t object_id;
	char definition[96];
	char type[64];
	float position[3];
	float orientation[4];
	float velocity[3];
	float health;
	bool physics_registered;
	bool grounded;
};

struct A31WorldTelemetry
{
	bool loaded;
	uint32_t definition_count;
	uint32_t static_object_count;
	uint32_t dynamic_object_count;
	uint32_t light_count;
	uint32_t render_object_nodes;
	uint32_t semantic_meshes;
	uint64_t semantic_vertices;
	uint64_t semantic_polygons;
	uint32_t prototype_count;
	uint32_t vis_object_count;
	uint32_t vis_sector_count;
	uint32_t definition_checksum;
	uint32_t object_checksum;
	uint32_t render_checksum;
	uint32_t prototype_checksum;
	float bounds_min[3];
	float bounds_max[3];
};

struct A31CameraTelemetry
{
	bool present;
	bool original_camera_class;
	bool player_owned;
	float transform[12];
	float position[3];
	float target[3];
	float near_clip;
	float far_clip;
};

struct A31SensorTelemetry
{
	bool available;
	float battery_percent;
	float battery_temperature_c;
};

struct A31FrameTelemetry
{
	uint64_t frame_index;
	uint64_t monotonic_us;
	uint64_t frame_time_us;
	uint64_t ordinary_frame_time_us;
	A31StageTimings stages;
	A31RendererTelemetry renderer;
	A31MemoryTelemetry memory;
	bool benchmark_active;
	uint32_t benchmark_point;
	uint64_t game_update_count;
	uint64_t physics_update_count;
	uint64_t input_action_count;
};

struct A31StateSnapshot
{
	uint32_t schema_version;
	char milestone[16];
	char build_label[64];
	char capture_overlay_label[64];
	char runtime_log_path[A31_CAPTURE_PATH_CAPACITY];
	char reason[48];
	char phase[48];
	char benchmark_route[48];
	uint64_t capture_monotonic_us;
	uint64_t capture_frame;
	uint64_t capture_stall_us;
	A31WorldTelemetry world;
	A31CameraTelemetry camera;
	A31PlayerTelemetry player;
	A31RendererTelemetry renderer;
	A31MemoryTelemetry memory;
	A31SensorTelemetry sensors;
	uint64_t game_update_count;
	uint64_t physics_update_count;
	uint64_t input_action_count;
	bool scripts_active;
	bool benchmark_active;
	uint32_t benchmark_point;
};

class A31FrameHistory
{
public:
	A31FrameHistory();
	void Reset();
	void Push(const A31FrameTelemetry &frame);
	size_t Count() const;
	const A31FrameTelemetry &Oldest(size_t index) const;

private:
	A31FrameTelemetry Frames[A31_FRAME_HISTORY_CAPACITY];
	size_t Next;
	size_t Used;
};

struct A31CaptureBundleInput
{
	const char *base_directory;
	const char *bundle_label;
	const uint8_t *resolved_rgba_bottom_up;
	uint32_t framebuffer_width;
	uint32_t framebuffer_height;
	bool write_annotated_screenshot;
	A31StateSnapshot state;
	const A31FrameHistory *history;
};

struct A31CaptureBundleResult
{
	bool passed;
	bool screenshot_written;
	bool annotated_screenshot_written;
	bool state_written;
	bool history_written;
	bool summary_written;
	bool failure_marker_written;
	int first_error_code;
	uint64_t write_stall_us;
	char bundle_path[A31_CAPTURE_PATH_CAPACITY];
	char first_error[128];
};

A31CaptureBundleResult A31_Write_Capture_Bundle(
	const A31CaptureBundleInput &input);

/* Formats the exact annotation used in captured BMPs.  Keeping this bounded,
 * fixed-width interface lets host tests cover zero, ordinary, and UINT64_MAX
 * telemetry without depending on a framebuffer. */
bool A31_Format_Capture_Overlay(char *output, size_t capacity,
	const A31StateSnapshot &state, const A31FrameHistory &history);

struct A31BenchmarkPoint
{
	float camera_position[3];
	float camera_target[3];
	uint32_t duration_frames;
	uint32_t capture_frame;
};

class A31M00BenchmarkRoute
{
public:
	A31M00BenchmarkRoute();
	void Start(uint64_t starting_frame);
	void Stop();
	bool Is_Active() const;
	bool Is_Complete(uint64_t frame) const;
	uint32_t Point_Index(uint64_t frame) const;
	bool Is_Capture_Frame(uint64_t frame) const;
	const A31BenchmarkPoint &Point(uint64_t frame) const;
	uint64_t Starting_Frame() const;

private:
	uint64_t StartFrame;
	bool Active;
};
