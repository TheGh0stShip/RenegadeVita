#include "a35_campaign_flight_recorder.h"

#include <errno.h>
#include <inttypes.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <time.h>

#if defined(__vita__)
#include <psp2/io/stat.h>
#endif

namespace {

enum : uint32_t {
	kFlightFrameCapacity = 4096U,
	kFlightEventCapacity = 768U,
	kFlightLogCapacity = 768U,
	kFlightLogLineCapacity = 320U,
	kFlightPathCapacity = 384U
};

struct FlightFrameSample
{
	uint64_t frame;
	uint64_t monotonic_us;
	uint64_t frame_time_us;
	uint64_t sync_us;
	uint64_t simulation_us;
	uint64_t render_us;
	uint64_t draw_calls;
	uint64_t mesh_submissions;
	uint64_t vertices;
	uint64_t triangles;
	uint64_t texture_requests;
	uint64_t texture_decodes;
	uint64_t texture_uploads;
	uint64_t texture_binds;
	uint64_t texture_missing;
	uint64_t backend_errors;
	int64_t system_user_free;
	int64_t system_cdram_free;
	int64_t system_phycont_free;
	uint64_t vitagl_all_free;
	uint32_t active_samples;
	uint32_t active_streams;
	uint32_t stream_position_ms;
	uint32_t stream_length_ms;
	uint32_t stream_cursor_frame;
	uint32_t stream_total_frames;
	uint32_t output_write_failures;
	uint32_t stream_open_failures;
	uint32_t stream_start_silent;
	uint32_t mixed_peak_abs;
	float player_x;
	float player_y;
	float player_z;
	float camera_x;
	float camera_y;
	float camera_z;
	uint8_t scene_available;
	uint8_t camera_available;
	uint8_t star_available;
	uint8_t render_closed;
	uint8_t render_incomplete;
};

struct FlightEvent
{
	uint32_t frame;
	uint64_t monotonic_us;
	char category[32];
	char name[64];
	char detail[224];
};

struct FlightMissionState
{
	A35CampaignFlightMissionState state;
	char archive[64];
	char load_source[96];
	char conversation[96];
};

struct FlightLogLine
{
	char line[kFlightLogLineCapacity];
};

struct FlightRecorder
{
	bool active;
	bool flushed_once;
	char candidate[64];
	char capture_root[kFlightPathCapacity];
	char runtime_log_path[kFlightPathCapacity];
	char archive[64];
	char load_source[96];
	FlightFrameSample frames[kFlightFrameCapacity];
	uint32_t frame_cursor;
	uint32_t frame_count;
	FlightEvent events[kFlightEventCapacity];
	uint32_t event_cursor;
	uint32_t event_count;
	FlightLogLine logs[kFlightLogCapacity];
	uint32_t log_cursor;
	uint32_t log_count;
	FlightMissionState mission;
	bool mission_available;
	uint64_t worst_frame_us;
	uint64_t worst_frame_index;
	uint64_t slow_over_16_7ms;
	uint64_t slow_over_33_3ms;
	uint64_t slow_over_50ms;
	uint64_t slow_over_100ms;
	uint64_t slow_over_250ms;
	uint64_t slow_over_500ms;
	uint32_t resource_snapshots;
	uint32_t last_open_attempts;
	uint32_t last_open_failures;
	uint32_t last_available_attempts;
	uint32_t last_availability_failures;
	uint32_t last_read_calls;
	uint32_t last_read_bytes;
	uint32_t last_write_calls;
	uint32_t last_write_bytes;
};

FlightRecorder gRecorder;

uint64_t Monotonic_Us()
{
	struct timespec now = {};
	if (clock_gettime(CLOCK_MONOTONIC, &now) != 0) return 0U;
	return static_cast<uint64_t>(now.tv_sec) * 1000000ULL +
		static_cast<uint64_t>(now.tv_nsec) / 1000ULL;
}

void Copy_String(char *output, size_t capacity, const char *input)
{
	if (capacity == 0U) return;
	if (input == NULL) input = "";
	snprintf(output, capacity, "%s", input);
}

bool Make_Directory(const char *path)
{
#if defined(__vita__)
	const int result = sceIoMkdir(path, 0777);
	if (result < 0) {
		SceIoStat status = {};
		return sceIoGetstat(path, &status) >= 0;
	}
	return true;
#else
	const int result = mkdir(path, 0777);
	return result == 0 || errno == EEXIST;
#endif
}

bool Build_Path(char *output, size_t capacity, const char *name)
{
	const int count = snprintf(output, capacity, "%s/%s",
		gRecorder.capture_root[0] != '\0' ? gRecorder.capture_root : ".",
		name != NULL ? name : "campaign-flight-invalid.txt");
	return count > 0 && static_cast<size_t>(count) < capacity;
}

void Json_String(FILE *file, const char *text)
{
	fputc('"', file);
	if (text != NULL) {
		for (const unsigned char *cursor =
			reinterpret_cast<const unsigned char *>(text); *cursor != 0; ++cursor) {
			switch (*cursor) {
			case '\\': fputs("\\\\", file); break;
			case '"': fputs("\\\"", file); break;
			case '\n': fputs("\\n", file); break;
			case '\r': fputs("\\r", file); break;
			case '\t': fputs("\\t", file); break;
			default:
				if (*cursor < 32U) {
					fprintf(file, "\\u%04x", static_cast<unsigned>(*cursor));
				} else {
					fputc(*cursor, file);
				}
				break;
			}
		}
	}
	fputc('"', file);
}

uint32_t Ring_Start(uint32_t cursor, uint32_t count, uint32_t capacity)
{
	return count < capacity ? 0U : cursor;
}

void Push_Event(const char *category, const char *name, uint32_t frame,
	uint64_t monotonic_us, const char *detail)
{
	FlightEvent &event = gRecorder.events[gRecorder.event_cursor];
	event.frame = frame;
	event.monotonic_us = monotonic_us != 0U ? monotonic_us : Monotonic_Us();
	Copy_String(event.category, sizeof(event.category), category);
	Copy_String(event.name, sizeof(event.name), name);
	Copy_String(event.detail, sizeof(event.detail), detail);
	gRecorder.event_cursor =
		(gRecorder.event_cursor + 1U) % kFlightEventCapacity;
	if (gRecorder.event_count < kFlightEventCapacity) ++gRecorder.event_count;
}

void Write_Events(FILE *file)
{
	const uint32_t start = Ring_Start(gRecorder.event_cursor,
		gRecorder.event_count, kFlightEventCapacity);
	for (uint32_t index = 0U; index < gRecorder.event_count; ++index) {
		const FlightEvent &event =
			gRecorder.events[(start + index) % kFlightEventCapacity];
		fprintf(file,
			"{\"schema\":%u,\"candidate\":",
			A35_CAMPAIGN_FLIGHT_SCHEMA_VERSION);
		Json_String(file, gRecorder.candidate);
		fprintf(file, ",\"archive\":");
		Json_String(file, gRecorder.archive);
		fprintf(file, ",\"load_source\":");
		Json_String(file, gRecorder.load_source);
		fprintf(file,
			",\"frame\":%u,\"monotonic_us\":%" PRIu64 ",\"category\":",
			event.frame, event.monotonic_us);
		Json_String(file, event.category);
		fprintf(file, ",\"name\":");
		Json_String(file, event.name);
		fprintf(file, ",\"detail\":");
		Json_String(file, event.detail);
		fputs("}\n", file);
	}
}

void Write_Frames(FILE *file)
{
	fputs("schema,candidate,archive,load_source,frame,monotonic_us,frame_us,"
		"sync_us,simulation_us,render_us,draw_calls,meshes,vertices,triangles,"
		"texture_requests,texture_decodes,texture_uploads,texture_binds,"
		"texture_missing,backend_errors,system_user_free,system_cdram_free,"
		"system_phycont_free,vitagl_all_free,active_samples,active_streams,"
		"stream_pos_ms,stream_len_ms,stream_cursor_frame,stream_total_frames,"
		"output_write_failures,stream_open_failures,stream_start_silent,"
		"mixed_peak_abs,player_x,player_y,player_z,camera_x,camera_y,camera_z,"
		"scene,camera,star,render_closed,render_incomplete\n", file);
	const uint32_t start = Ring_Start(gRecorder.frame_cursor,
		gRecorder.frame_count, kFlightFrameCapacity);
	for (uint32_t index = 0U; index < gRecorder.frame_count; ++index) {
		const FlightFrameSample &frame =
			gRecorder.frames[(start + index) % kFlightFrameCapacity];
		fprintf(file,
			"%u,%s,%s,%s,%" PRIu64 ",%" PRIu64 ",%" PRIu64
			",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64
			",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64
			",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64
			",%" PRIu64 ",%" PRId64 ",%" PRId64 ",%" PRId64
			",%" PRIu64 ",%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,"
			"%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,%u,%u,%u,%u,%u\n",
			A35_CAMPAIGN_FLIGHT_SCHEMA_VERSION,
			gRecorder.candidate, gRecorder.archive, gRecorder.load_source,
			frame.frame, frame.monotonic_us, frame.frame_time_us,
			frame.sync_us, frame.simulation_us, frame.render_us,
			frame.draw_calls, frame.mesh_submissions, frame.vertices,
			frame.triangles, frame.texture_requests, frame.texture_decodes,
			frame.texture_uploads, frame.texture_binds, frame.texture_missing,
			frame.backend_errors, frame.system_user_free, frame.system_cdram_free,
			frame.system_phycont_free, frame.vitagl_all_free,
			frame.active_samples, frame.active_streams,
			frame.stream_position_ms, frame.stream_length_ms,
			frame.stream_cursor_frame, frame.stream_total_frames,
			frame.output_write_failures, frame.stream_open_failures,
			frame.stream_start_silent, frame.mixed_peak_abs,
			static_cast<double>(frame.player_x),
			static_cast<double>(frame.player_y),
			static_cast<double>(frame.player_z),
			static_cast<double>(frame.camera_x),
			static_cast<double>(frame.camera_y),
			static_cast<double>(frame.camera_z),
			frame.scene_available, frame.camera_available, frame.star_available,
			frame.render_closed, frame.render_incomplete);
	}
}

void Write_Log_Tail(FILE *file)
{
	const uint32_t start = Ring_Start(gRecorder.log_cursor,
		gRecorder.log_count, kFlightLogCapacity);
	for (uint32_t index = 0U; index < gRecorder.log_count; ++index) {
		const FlightLogLine &line =
			gRecorder.logs[(start + index) % kFlightLogCapacity];
		fputs(line.line, file);
		if (line.line[0] != '\0' &&
			line.line[strlen(line.line) - 1U] != '\n') {
			fputc('\n', file);
		}
	}
}

void Write_Mission(FILE *file)
{
	if (!gRecorder.mission_available) {
		fputs("\"mission\":null", file);
		return;
	}
	const A35CampaignFlightMissionState &state = gRecorder.mission.state;
	fputs("\"mission\":{\"archive\":", file);
	Json_String(file, gRecorder.mission.archive);
	fprintf(file, ",\"load_source\":");
	Json_String(file, gRecorder.mission.load_source);
	fprintf(file,
		",\"frame\":%u,\"star_available\":%d,\"player_control_enabled\":%d,"
		"\"objective_count\":%u,\"objective_status\":[%d,%d,%d,%d,%d,%d],"
		"\"active_conversation_count\":%u,\"conversation\":",
		state.frame, state.star_available ? 1 : 0,
		state.player_control_enabled ? 1 : 0, state.objective_count,
		state.objective_status[0], state.objective_status[1],
		state.objective_status[2], state.objective_status[3],
		state.objective_status[4], state.objective_status[5],
		state.active_conversation_count);
	Json_String(file, gRecorder.mission.conversation);
	fprintf(file,
		",\"conversation_id\":%d,\"conversation_state\":%d,"
		"\"conversation_action_id\":%d,\"remark\":%d,\"remark_count\":%d,"
		"\"text_id\":%d,\"sound_id\":%d,\"string_available\":%d,"
		"\"sound_definition_available\":%d,\"next_remark_seconds\":%.3f,"
		"\"speaker_available\":%d,\"speech_source\":%d,"
		"\"speech_available\":%d,\"speech_in_scene\":%d,"
		"\"speech_culled\":%d,\"speech_playing\":%d,"
		"\"speech_class_id\":%d,\"speech_type\":%d,\"speech_state\":%d,"
		"\"speech_duration_ms\":%u,\"speech_dropoff_radius\":%.3f,"
		"\"speech_listener_distance\":%.3f,\"player\":[%.3f,%.3f,%.3f]}",
		state.active_conversation_id, state.active_conversation_state,
		state.active_conversation_action_id,
		state.active_conversation_current_remark,
		state.active_conversation_remark_count,
		state.active_conversation_text_id,
		state.active_conversation_sound_id,
		state.active_conversation_string_available ? 1 : 0,
		state.active_conversation_sound_definition_available ? 1 : 0,
		static_cast<double>(state.active_conversation_next_remark_seconds),
		state.active_conversation_speaker_available ? 1 : 0,
		state.active_conversation_speech_source,
		state.active_conversation_speech_available ? 1 : 0,
		state.active_conversation_speech_in_scene ? 1 : 0,
		state.active_conversation_speech_culled ? 1 : 0,
		state.active_conversation_speech_playing ? 1 : 0,
		state.active_conversation_speech_class_id,
		state.active_conversation_speech_type,
		state.active_conversation_speech_state,
		state.active_conversation_speech_duration_ms,
		static_cast<double>(state.active_conversation_speech_dropoff_radius),
		static_cast<double>(state.active_conversation_speech_listener_distance),
		static_cast<double>(state.player_x),
		static_cast<double>(state.player_y),
		static_cast<double>(state.player_z));
}

} // namespace

void A35_Campaign_Flight_Reset(const char *candidate, const char *capture_root,
	const char *runtime_log_path, const char *archive, const char *load_source)
{
	memset(&gRecorder, 0, sizeof(gRecorder));
	gRecorder.active = true;
	Copy_String(gRecorder.candidate, sizeof(gRecorder.candidate), candidate);
	Copy_String(gRecorder.capture_root, sizeof(gRecorder.capture_root),
		capture_root);
	Copy_String(gRecorder.runtime_log_path, sizeof(gRecorder.runtime_log_path),
		runtime_log_path);
	Copy_String(gRecorder.archive, sizeof(gRecorder.archive), archive);
	Copy_String(gRecorder.load_source, sizeof(gRecorder.load_source),
		load_source);
	Make_Directory(gRecorder.capture_root);
	Push_Event("lifecycle", "reset", 0U, Monotonic_Us(),
		"campaign flight recorder reset");
}

void A35_Campaign_Flight_Shutdown(void)
{
	if (gRecorder.active) {
		A35_Campaign_Flight_Flush("shutdown");
	}
	gRecorder.active = false;
}

void A35_Campaign_Flight_Record_Log_Line(const char *line, unsigned length)
{
	if (!gRecorder.active || line == NULL || length == 0U) return;
	FlightLogLine &slot = gRecorder.logs[gRecorder.log_cursor];
	const unsigned copy_length =
		length < (kFlightLogLineCapacity - 1U) ? length :
		(kFlightLogLineCapacity - 1U);
	memcpy(slot.line, line, copy_length);
	slot.line[copy_length] = '\0';
	gRecorder.log_cursor = (gRecorder.log_cursor + 1U) % kFlightLogCapacity;
	if (gRecorder.log_count < kFlightLogCapacity) ++gRecorder.log_count;
}

void A35_Campaign_Flight_Record_Event(const char *category, const char *name,
	uint32_t frame, uint64_t monotonic_us, const char *detail)
{
	if (!gRecorder.active) return;
	Push_Event(category, name, frame, monotonic_us, detail);
}

void A35_Campaign_Flight_Record_Frame(const A31FrameTelemetry &frame,
	const A35CampaignFlightRenderState &render,
	const A35CampaignFlightAudioState &audio)
{
	if (!gRecorder.active) return;
	FlightFrameSample &sample = gRecorder.frames[gRecorder.frame_cursor];
	memset(&sample, 0, sizeof(sample));
	sample.frame = frame.frame_index;
	sample.monotonic_us = frame.monotonic_us;
	sample.frame_time_us = frame.frame_time_us;
	sample.sync_us = frame.stages.input_us;
	sample.simulation_us = frame.stages.game_update_us;
	sample.render_us = frame.stages.render_us;
	sample.draw_calls = frame.renderer.draw_calls;
	sample.mesh_submissions = frame.renderer.mesh_submissions;
	sample.vertices = frame.renderer.vertices;
	sample.triangles = frame.renderer.triangles;
	sample.texture_requests = frame.renderer.texture_requests;
	sample.texture_decodes = frame.renderer.texture_decodes;
	sample.texture_uploads = frame.renderer.texture_uploads;
	sample.texture_binds = frame.renderer.texture_binds;
	sample.texture_missing = frame.renderer.texture_missing;
	sample.backend_errors = frame.renderer.backend_errors;
	sample.system_user_free = frame.memory.system_user_free;
	sample.system_cdram_free = frame.memory.system_cdram_free;
	sample.system_phycont_free = frame.memory.system_phycont_free;
	sample.vitagl_all_free = frame.memory.vitagl_all_free;
	sample.active_samples = audio.active_samples;
	sample.active_streams = audio.active_streams;
	sample.stream_position_ms = audio.active_stream_position_ms;
	sample.stream_length_ms = audio.active_stream_length_ms;
	sample.stream_cursor_frame = audio.active_stream_cursor_frame;
	sample.stream_total_frames = audio.active_stream_total_frames;
	sample.output_write_failures = audio.output_write_failures;
	sample.stream_open_failures = audio.stream_open_failures;
	sample.stream_start_silent = audio.stream_start_silent;
	sample.mixed_peak_abs = audio.mixed_peak_abs;
	sample.player_x = render.player_x;
	sample.player_y = render.player_y;
	sample.player_z = render.player_z;
	sample.camera_x = render.camera_x;
	sample.camera_y = render.camera_y;
	sample.camera_z = render.camera_z;
	sample.scene_available = render.scene_available ? 1U : 0U;
	sample.camera_available = render.camera_available ? 1U : 0U;
	sample.star_available = render.star_available ? 1U : 0U;
	sample.render_closed = render.end_render_completed &&
		render.post_render_completed ? 1U : 0U;
	sample.render_incomplete = !render.pre_render_completed ||
		!render.begin_render_completed || !render.combat_render_called ||
		!render.end_render_completed || !render.post_render_completed ? 1U : 0U;
	gRecorder.frame_cursor =
		(gRecorder.frame_cursor + 1U) % kFlightFrameCapacity;
	if (gRecorder.frame_count < kFlightFrameCapacity) ++gRecorder.frame_count;
	if (frame.frame_time_us > gRecorder.worst_frame_us) {
		gRecorder.worst_frame_us = frame.frame_time_us;
		gRecorder.worst_frame_index = frame.frame_index;
	}
	if (frame.frame_time_us > 16667U) ++gRecorder.slow_over_16_7ms;
	if (frame.frame_time_us > 33333U) ++gRecorder.slow_over_33_3ms;
	if (frame.frame_time_us > 50000U) ++gRecorder.slow_over_50ms;
	if (frame.frame_time_us > 100000U) ++gRecorder.slow_over_100ms;
	if (frame.frame_time_us > 250000U) ++gRecorder.slow_over_250ms;
	if (frame.frame_time_us > 500000U) ++gRecorder.slow_over_500ms;
	if (frame.frame_time_us > 250000U) {
		char detail[192];
		snprintf(detail, sizeof(detail),
			"frame_us=%" PRIu64 " sync_us=%" PRIu64
			" simulation_us=%" PRIu64 " render_us=%" PRIu64
			" stream=%s audio_pos=%u/%u",
			frame.frame_time_us, frame.stages.input_us,
			frame.stages.game_update_us, frame.stages.render_us,
			audio.last_stream_name != NULL ? audio.last_stream_name : "none",
			audio.active_stream_position_ms, audio.active_stream_length_ms);
		Push_Event("performance", "slow_frame_over_250ms",
			static_cast<uint32_t>(frame.frame_index), frame.monotonic_us, detail);
	}
}

void A35_Campaign_Flight_Record_Mission(
	const A35CampaignFlightMissionState &state)
{
	if (!gRecorder.active) return;
	gRecorder.mission.state = state;
	Copy_String(gRecorder.mission.archive, sizeof(gRecorder.mission.archive),
		state.archive);
	Copy_String(gRecorder.mission.load_source,
		sizeof(gRecorder.mission.load_source), state.load_source);
	Copy_String(gRecorder.mission.conversation,
		sizeof(gRecorder.mission.conversation), state.active_conversation_name);
	gRecorder.mission.state.archive = gRecorder.mission.archive;
	gRecorder.mission.state.load_source = gRecorder.mission.load_source;
	gRecorder.mission.state.active_conversation_name =
		gRecorder.mission.conversation;
	gRecorder.mission_available = true;
	char detail[224];
	snprintf(detail, sizeof(detail),
		"control=%d objectives=%u status=%d/%d/%d/%d/%d/%d conversation=%s state=%d speech_playing=%d",
		state.player_control_enabled ? 1 : 0, state.objective_count,
		state.objective_status[0], state.objective_status[1],
		state.objective_status[2], state.objective_status[3],
		state.objective_status[4], state.objective_status[5],
		state.active_conversation_name != NULL &&
			state.active_conversation_name[0] != '\0' ?
			state.active_conversation_name : "none",
		state.active_conversation_state,
		state.active_conversation_speech_playing ? 1 : 0);
	Push_Event("mission", "progress_changed", state.frame, Monotonic_Us(),
		detail);
}

void A35_Campaign_Flight_Record_Resource_Snapshot(uint32_t frame,
	uint32_t open_attempts, uint32_t open_failures, uint32_t available_attempts,
	uint32_t availability_failures, uint32_t read_calls, uint32_t read_bytes,
	uint32_t write_calls, uint32_t write_bytes)
{
	if (!gRecorder.active) return;
	++gRecorder.resource_snapshots;
	gRecorder.last_open_attempts = open_attempts;
	gRecorder.last_open_failures = open_failures;
	gRecorder.last_available_attempts = available_attempts;
	gRecorder.last_availability_failures = availability_failures;
	gRecorder.last_read_calls = read_calls;
	gRecorder.last_read_bytes = read_bytes;
	gRecorder.last_write_calls = write_calls;
	gRecorder.last_write_bytes = write_bytes;
	char detail[192];
	snprintf(detail, sizeof(detail),
		"open=%u fail=%u available=%u fail=%u read=%u/%uB write=%u/%uB",
		open_attempts, open_failures, available_attempts,
		availability_failures, read_calls, read_bytes, write_calls,
		write_bytes);
	Push_Event("resources", "factory_snapshot", frame, Monotonic_Us(), detail);
}

bool A35_Campaign_Flight_Flush(const char *reason)
{
	if (!gRecorder.active) return false;
	Make_Directory(gRecorder.capture_root);
	char path[kFlightPathCapacity];
	bool ok = true;
	if (Build_Path(path, sizeof(path), "campaign-flight-events.jsonl")) {
		FILE *file = fopen(path, "wb");
		if (file != NULL) {
			Write_Events(file);
			ok = fclose(file) == 0 && ok;
		} else {
			ok = false;
		}
	}
	if (Build_Path(path, sizeof(path), "campaign-flight-frames.csv")) {
		FILE *file = fopen(path, "wb");
		if (file != NULL) {
			Write_Frames(file);
			ok = fclose(file) == 0 && ok;
		} else {
			ok = false;
		}
	}
	if (Build_Path(path, sizeof(path), "campaign-flight-log-tail.txt")) {
		FILE *file = fopen(path, "wb");
		if (file != NULL) {
			Write_Log_Tail(file);
			ok = fclose(file) == 0 && ok;
		} else {
			ok = false;
		}
	}
	if (Build_Path(path, sizeof(path), "campaign-flight-summary.json")) {
		FILE *file = fopen(path, "wb");
		if (file != NULL) {
			fprintf(file,
				"{\n  \"schema\":%u,\n  \"candidate\":",
				A35_CAMPAIGN_FLIGHT_SCHEMA_VERSION);
			Json_String(file, gRecorder.candidate);
			fprintf(file, ",\n  \"reason\":");
			Json_String(file, reason != NULL ? reason : "unknown");
			fprintf(file, ",\n  \"archive\":");
			Json_String(file, gRecorder.archive);
			fprintf(file, ",\n  \"load_source\":");
			Json_String(file, gRecorder.load_source);
			fprintf(file, ",\n  \"runtime_log_path\":");
			Json_String(file, gRecorder.runtime_log_path);
			fprintf(file,
				",\n  \"frames_recorded\":%u,\n  \"events_recorded\":%u,"
				"\n  \"log_lines_recorded\":%u,\n  \"worst_frame\":{"
				"\"frame\":%" PRIu64 ",\"us\":%" PRIu64 "},"
				"\n  \"slow_counts\":{\"over_16_7ms\":%" PRIu64
				",\"over_33_3ms\":%" PRIu64 ",\"over_50ms\":%" PRIu64
				",\"over_100ms\":%" PRIu64 ",\"over_250ms\":%" PRIu64
				",\"over_500ms\":%" PRIu64 "},"
				"\n  \"resources\":{\"snapshots\":%u,\"open_attempts\":%u,"
				"\"open_failures\":%u,\"available_attempts\":%u,"
				"\"availability_failures\":%u,\"read_calls\":%u,"
				"\"read_bytes\":%u,\"write_calls\":%u,\"write_bytes\":%u},\n  ",
				gRecorder.frame_count, gRecorder.event_count, gRecorder.log_count,
				gRecorder.worst_frame_index, gRecorder.worst_frame_us,
				gRecorder.slow_over_16_7ms, gRecorder.slow_over_33_3ms,
				gRecorder.slow_over_50ms, gRecorder.slow_over_100ms,
				gRecorder.slow_over_250ms, gRecorder.slow_over_500ms,
				gRecorder.resource_snapshots, gRecorder.last_open_attempts,
				gRecorder.last_open_failures, gRecorder.last_available_attempts,
				gRecorder.last_availability_failures, gRecorder.last_read_calls,
				gRecorder.last_read_bytes, gRecorder.last_write_calls,
				gRecorder.last_write_bytes);
			Write_Mission(file);
			fputs("\n}\n", file);
			ok = fclose(file) == 0 && ok;
		} else {
			ok = false;
		}
	}
	gRecorder.flushed_once = true;
	return ok;
}
