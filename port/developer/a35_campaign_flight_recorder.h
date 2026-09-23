#pragma once

#include "a31_capture_telemetry.h"

#include <stdint.h>

enum : uint32_t {
	A35_CAMPAIGN_FLIGHT_SCHEMA_VERSION = 1U
};

struct A35CampaignFlightMissionState
{
	uint32_t frame;
	const char *archive;
	const char *load_source;
	bool star_available;
	bool player_control_enabled;
	uint32_t objective_count;
	int objective_status[6];
	uint32_t active_conversation_count;
	const char *active_conversation_name;
	int active_conversation_id;
	int active_conversation_state;
	int active_conversation_action_id;
	int active_conversation_current_remark;
	int active_conversation_remark_count;
	int active_conversation_text_id;
	int active_conversation_sound_id;
	bool active_conversation_string_available;
	bool active_conversation_sound_definition_available;
	float active_conversation_next_remark_seconds;
	bool active_conversation_speaker_available;
	int active_conversation_speech_source;
	bool active_conversation_speech_available;
	bool active_conversation_speech_in_scene;
	bool active_conversation_speech_culled;
	bool active_conversation_speech_playing;
	int active_conversation_speech_class_id;
	int active_conversation_speech_type;
	int active_conversation_speech_state;
	uint32_t active_conversation_speech_duration_ms;
	float active_conversation_speech_dropoff_radius;
	float active_conversation_speech_listener_distance;
	float player_x;
	float player_y;
	float player_z;
};

struct A35CampaignFlightRenderState
{
	bool scene_available;
	bool camera_available;
	bool star_available;
	bool pre_render_completed;
	bool begin_render_completed;
	bool combat_render_called;
	bool message_window_render_called;
	bool end_render_completed;
	bool post_render_completed;
	uint64_t mesh_submissions;
	uint64_t vertex_submissions;
	uint64_t triangle_submissions;
	uint64_t rejected_submissions;
	uint64_t unsupported_submissions;
	float camera_x;
	float camera_y;
	float camera_z;
	float player_x;
	float player_y;
	float player_z;
};

struct A35CampaignFlightAudioState
{
	uint32_t active_samples;
	uint32_t active_streams;
	uint32_t active_stream_position_ms;
	uint32_t active_stream_length_ms;
	uint32_t active_stream_cursor_frame;
	uint32_t active_stream_total_frames;
	uint32_t output_write_failures;
	uint32_t stream_open_failures;
	uint32_t stream_start_silent;
	uint32_t mixed_peak_abs;
	const char *last_stream_name;
	const char *last_error;
	float dialog_volume;
	float cinematic_volume;
};

void A35_Campaign_Flight_Reset(const char *candidate, const char *capture_root,
	const char *runtime_log_path, const char *archive, const char *load_source);
void A35_Campaign_Flight_Shutdown(void);
void A35_Campaign_Flight_Record_Log_Line(const char *line, unsigned length);
void A35_Campaign_Flight_Record_Event(const char *category, const char *name,
	uint32_t frame, uint64_t monotonic_us, const char *detail);
void A35_Campaign_Flight_Record_Frame(const A31FrameTelemetry &frame,
	const A35CampaignFlightRenderState &render,
	const A35CampaignFlightAudioState &audio);
void A35_Campaign_Flight_Record_Mission(
	const A35CampaignFlightMissionState &state);
void A35_Campaign_Flight_Record_Resource_Snapshot(uint32_t frame,
	uint32_t open_attempts, uint32_t open_failures, uint32_t available_attempts,
	uint32_t availability_failures, uint32_t read_calls, uint32_t read_bytes,
	uint32_t write_calls, uint32_t write_bytes);
bool A35_Campaign_Flight_Flush(const char *reason);
