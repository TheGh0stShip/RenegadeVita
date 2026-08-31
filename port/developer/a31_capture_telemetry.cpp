#include "a31_capture_telemetry.h"

#include <errno.h>
#include <inttypes.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <time.h>

#if defined(__vita__)
#include <psp2/io/fcntl.h>
#include <psp2/io/stat.h>
#endif

namespace {

bool Open_Path(char *output, size_t capacity, const char *directory,
	const char *name);

uint64_t Monotonic_Us()
{
	struct timespec now = {};
	if (clock_gettime(CLOCK_MONOTONIC, &now) != 0) {
		return 0U;
	}
	return static_cast<uint64_t>(now.tv_sec) * 1000000ULL +
		static_cast<uint64_t>(now.tv_nsec) / 1000ULL;
}

bool Make_Directory(const char *path)
{
#if defined(__vita__)
	const int result = sceIoMkdir(path, 0777);
	if (result < 0) {
		SceIoStat status = {};
		return sceIoGetstat(path, &status) >= 0;
	}
#else
	const int result = mkdir(path, 0777);
#endif
	return result >= 0 || errno == EEXIST;
}

void Set_Error(A31CaptureBundleResult &result, const char *message,
	int error_code = 0)
{
	if (result.first_error[0] == 0) {
		snprintf(result.first_error, sizeof(result.first_error), "%s", message);
		result.first_error_code = error_code;
	}
}

bool Verify_Artifact(const char *path, const char *prefix, int &error_code)
{
	if (path == NULL || prefix == NULL) {
		error_code = EINVAL;
		return false;
	}
#if defined(__vita__)
	SceIoStat status = {};
	const int stat_result = sceIoGetstat(path, &status);
	if (stat_result < 0 || status.st_size == 0U) {
		error_code = stat_result < 0 ? stat_result : EIO;
		return false;
	}
#else
	struct stat status = {};
	if (stat(path, &status) != 0 || status.st_size <= 0) {
		error_code = errno != 0 ? errno : EIO;
		return false;
	}
#endif
	FILE *file = fopen(path, "rb");
	if (file == NULL) {
		error_code = errno != 0 ? errno : EIO;
		return false;
	}
	char actual[256] = {};
	const size_t wanted = strlen(prefix);
	const bool content_valid = wanted < sizeof(actual) &&
		fread(actual, 1U, wanted, file) == wanted &&
		memcmp(actual, prefix, wanted) == 0;
	const bool close_valid = fclose(file) == 0;
	const bool valid = content_valid && close_valid;
	if (!valid) {
		error_code = EIO;
	}
	return valid;
}

bool Write_Failure_Marker(const A31CaptureBundleInput &input,
	const A31CaptureBundleResult &result)
{
	char path[A31_CAPTURE_PATH_CAPACITY];
	if (!Open_Path(path, sizeof(path), input.base_directory,
		"capture-write-failure.txt")) {
		return false;
	}
	FILE *file = fopen(path, "wb");
	if (file == NULL) return false;
	fprintf(file, "candidate=%s\nphase=%s\nreason=%s\nerror=%s\nerror_code=%d\n",
		input.state.milestone, input.state.phase, input.state.reason,
		result.first_error, result.first_error_code);
	const bool flushed = fflush(file) == 0;
	const bool closed = fclose(file) == 0;
	return flushed && closed;
}

bool Open_Path(char *output, size_t capacity, const char *directory,
	const char *name)
{
	const int count = snprintf(output, capacity, "%s/%s", directory, name);
	return count > 0 && static_cast<size_t>(count) < capacity;
}

void Write_U16(FILE *file, uint16_t value)
{
	const unsigned char bytes[2] = {
		static_cast<unsigned char>(value),
		static_cast<unsigned char>(value >> 8U)
	};
	fwrite(bytes, 1U, sizeof(bytes), file);
}

void Write_U32(FILE *file, uint32_t value)
{
	const unsigned char bytes[4] = {
		static_cast<unsigned char>(value),
		static_cast<unsigned char>(value >> 8U),
		static_cast<unsigned char>(value >> 16U),
		static_cast<unsigned char>(value >> 24U)
	};
	fwrite(bytes, 1U, sizeof(bytes), file);
}

uint8_t Glyph_Row(char character, unsigned row)
{
	static const char glyph_characters[] =
		" 0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ.-:/_";
	static const uint8_t glyph_rows[][7] = {
		{0,0,0,0,0,0,0}, {14,17,19,21,25,17,14},
		{4,12,4,4,4,4,14}, {14,17,1,2,4,8,31},
		{30,1,1,14,1,1,30}, {2,6,10,18,31,2,2},
		{31,16,16,30,1,1,30}, {14,16,16,30,17,17,14},
		{31,1,2,4,8,8,8}, {14,17,17,14,17,17,14},
		{14,17,17,15,1,1,14}, {14,17,17,31,17,17,17},
		{30,17,17,30,17,17,30}, {14,17,16,16,16,17,14},
		{30,17,17,17,17,17,30}, {31,16,16,30,16,16,31},
		{31,16,16,30,16,16,16}, {14,17,16,23,17,17,15},
		{17,17,17,31,17,17,17}, {14,4,4,4,4,4,14},
		{7,2,2,2,2,18,12}, {17,18,20,24,20,18,17},
		{16,16,16,16,16,16,31}, {17,27,21,21,17,17,17},
		{17,25,21,19,17,17,17}, {14,17,17,17,17,17,14},
		{30,17,17,30,16,16,16}, {14,17,17,17,21,18,13},
		{30,17,17,30,20,18,17}, {15,16,16,14,1,1,30},
		{31,4,4,4,4,4,4}, {17,17,17,17,17,17,14},
		{17,17,17,17,17,10,4}, {17,17,17,21,21,21,10},
		{17,17,10,4,10,17,17}, {17,17,10,4,4,4,4},
		{31,1,2,4,8,16,31}, {0,0,0,0,0,0,4},
		{0,0,0,31,0,0,0}, {1,2,4,8,16,0,0},
		{0,4,0,0,4,0,0}, {0,0,0,0,0,0,31}
	};
	for (size_t index = 0; index + 1U < sizeof(glyph_characters); ++index) {
		if (glyph_characters[index] == character) {
			return glyph_rows[index][row < 7U ? row : 0U];
		}
	}
	return 0U;
}

bool Annotation_Pixel(const char *text, uint32_t x, uint32_t y)
{
	if (y < 7U || y >= 63U || x < 8U) {
		return false;
	}
	const unsigned line = (y - 7U) / 10U;
	const unsigned glyph_row = (y - 7U) % 10U;
	if (line >= 6U || glyph_row >= 7U) {
		return false;
	}
	const unsigned column = (x - 8U) / 6U;
	const unsigned glyph_column = (x - 8U) % 6U;
	if (glyph_column >= 5U) {
		return false;
	}
	const char *cursor = text;
	for (unsigned current_line = 0U; current_line < line; ++current_line) {
		cursor = strchr(cursor, '\n');
		if (cursor == NULL) {
			return false;
		}
		++cursor;
	}
	const char *line_end = strchr(cursor, '\n');
	const size_t line_length = line_end != NULL ?
		static_cast<size_t>(line_end - cursor) : strlen(cursor);
	if (column >= line_length) {
		return false;
	}
	const uint8_t row_bits = Glyph_Row(cursor[column], glyph_row);
	return (row_bits & (1U << (4U - glyph_column))) != 0U;
}

bool Write_Bmp(const char *path, const uint8_t *rgba, uint32_t width,
	uint32_t height, const char *annotation)
{
	if (rgba == NULL || width == 0U || height == 0U) {
		return false;
	}
	FILE *file = fopen(path, "wb");
	if (file == NULL) {
		return false;
	}
	const uint32_t row_bytes = (width * 3U + 3U) & ~3U;
	const uint32_t image_bytes = row_bytes * height;
	fwrite("BM", 1U, 2U, file);
	Write_U32(file, 54U + image_bytes);
	Write_U16(file, 0U); Write_U16(file, 0U); Write_U32(file, 54U);
	Write_U32(file, 40U); Write_U32(file, width); Write_U32(file, height);
	Write_U16(file, 1U); Write_U16(file, 24U); Write_U32(file, 0U);
	Write_U32(file, image_bytes); Write_U32(file, 2835U); Write_U32(file, 2835U);
	Write_U32(file, 0U); Write_U32(file, 0U);
	unsigned char row[4096U * 3U + 4U];
	if (width > 4096U) {
		fclose(file);
		return false;
	}
	for (uint32_t y = 0U; y < height; ++y) {
		for (uint32_t x = 0U; x < width; ++x) {
			const uint8_t *source = rgba + (static_cast<size_t>(y) * width + x) * 4U;
			uint8_t red = source[0];
			uint8_t green = source[1];
			uint8_t blue = source[2];
			const uint32_t annotation_y = height - 1U - y;
			if (annotation != NULL && annotation_y < 70U) {
				if (Annotation_Pixel(annotation, x, annotation_y)) {
					red = 255U; green = 255U; blue = 255U;
				} else if (x < 520U) {
					red = static_cast<uint8_t>(red / 4U);
					green = static_cast<uint8_t>(green / 4U);
					blue = static_cast<uint8_t>(blue / 4U);
				}
			}
			row[x * 3U + 0U] = blue;
			row[x * 3U + 1U] = green;
			row[x * 3U + 2U] = red;
		}
		memset(row + width * 3U, 0, row_bytes - width * 3U);
		if (fwrite(row, 1U, row_bytes, file) != row_bytes) {
			fclose(file);
			return false;
		}
	}
	return fflush(file) == 0 && fclose(file) == 0;
}

void Json_String(FILE *file, const char *value)
{
	fputc('"', file);
	for (const unsigned char *cursor =
		reinterpret_cast<const unsigned char *>(value != NULL ? value : "");
		*cursor != 0U; ++cursor) {
		if (*cursor == '"' || *cursor == '\\') {
			fputc('\\', file);
			fputc(*cursor, file);
		} else if (*cursor >= 0x20U) {
			fputc(*cursor, file);
		}
	}
	fputc('"', file);
}

void Json_Float_Array(FILE *file, const float *values, unsigned count)
{
	fputc('[', file);
	for (unsigned index = 0U; index < count; ++index) {
		fprintf(file, "%s%.9g", index == 0U ? "" : ",", values[index]);
	}
	fputc(']', file);
}

bool Write_State(const char *path, const A31StateSnapshot &state)
{
	FILE *file = fopen(path, "wb");
	if (file == NULL) return false;
	fprintf(file, "{\n  \"schema_version\":%u,\n  \"milestone\":", state.schema_version);
	Json_String(file, state.milestone);
	fprintf(file, ",\n  \"build_label\":"); Json_String(file, state.build_label);
	fprintf(file, ",\n  \"capture_overlay_label\":"); Json_String(file, state.capture_overlay_label);
	fprintf(file, ",\n  \"runtime_log_path\":"); Json_String(file, state.runtime_log_path);
	fprintf(file, ",\n  \"reason\":"); Json_String(file, state.reason);
	fprintf(file, ",\n  \"phase\":"); Json_String(file, state.phase);
	fprintf(file, ",\n  \"capture\":{\"monotonic_us\":%llu,\"frame\":%llu,\"stall_us\":%llu},",
		static_cast<unsigned long long>(state.capture_monotonic_us),
		static_cast<unsigned long long>(state.capture_frame),
		static_cast<unsigned long long>(state.capture_stall_us));
	const A31LoadingVisualGateTelemetry &visual = state.loading_visual_gate;
	fprintf(file, "\n  \"loading_visual_gate\":{\"active\":%s,\"framebuffer_width\":%u,\"framebuffer_height\":%u,\"original_logical_width\":%u,\"original_logical_height\":%u,\"native_display_width\":%u,\"native_display_height\":%u,\"native_presentation_x\":%u,\"native_presentation_y\":%u,\"native_presentation_width\":%u,\"native_presentation_height\":%u,\"logical_to_native_fullscreen\":%s,\"aspect_preserved\":%s,\"original_loading_screen_owner\":%s,\"direct_vitagl_overlay_disabled\":%s,\"loading_texture_v_flip_enabled\":%s,\"gameplay_texture_v_unchanged\":%s},",
		visual.active ? "true" : "false",
		visual.framebuffer_width, visual.framebuffer_height,
		visual.original_logical_width, visual.original_logical_height,
		visual.native_display_width, visual.native_display_height,
		visual.native_presentation_x, visual.native_presentation_y,
		visual.native_presentation_width,
		visual.native_presentation_height,
		visual.logical_to_native_fullscreen ? "true" : "false",
		visual.aspect_preserved ? "true" : "false",
		visual.original_loading_screen_owner ? "true" : "false",
		visual.direct_vitagl_overlay_disabled ? "true" : "false",
		visual.loading_texture_v_flip_enabled ? "true" : "false",
		visual.gameplay_texture_v_unchanged ? "true" : "false");
	fprintf(file, "\n  \"world\":{\"loaded\":%s,\"definitions\":%u,\"static_objects\":%u,\"dynamic_objects\":%u,\"lights\":%u,\"render_object_nodes\":%u,\"meshes\":%u,\"vertices\":%llu,\"polygons\":%llu,\"prototypes\":%u,\"visibility_objects\":%u,\"visibility_sectors\":%u,\"definition_checksum\":\"%08X\",\"object_checksum\":\"%08X\",\"render_checksum\":\"%08X\",\"prototype_checksum\":\"%08X\",\"bounds_min\":",
		state.world.loaded ? "true" : "false", state.world.definition_count,
		state.world.static_object_count, state.world.dynamic_object_count,
		state.world.light_count, state.world.render_object_nodes,
		state.world.semantic_meshes,
		static_cast<unsigned long long>(state.world.semantic_vertices),
		static_cast<unsigned long long>(state.world.semantic_polygons),
		state.world.prototype_count, state.world.vis_object_count,
		state.world.vis_sector_count, state.world.definition_checksum,
		state.world.object_checksum, state.world.render_checksum,
		state.world.prototype_checksum);
	Json_Float_Array(file, state.world.bounds_min, 3U);
	fprintf(file, ",\"bounds_max\":"); Json_Float_Array(file, state.world.bounds_max, 3U);
	fprintf(file, "},\n  \"camera\":{\"present\":%s,\"original_class\":%s,\"player_owned\":%s,\"transform\":",
		state.camera.present ? "true" : "false",
		state.camera.original_camera_class ? "true" : "false",
		state.camera.player_owned ? "true" : "false");
	Json_Float_Array(file, state.camera.transform, 12U);
	fprintf(file, ",\"position\":"); Json_Float_Array(file, state.camera.position, 3U);
	fprintf(file, ",\"target\":"); Json_Float_Array(file, state.camera.target, 3U);
	fprintf(file, ",\"near_clip\":%.9g,\"far_clip\":%.9g},",
		state.camera.near_clip, state.camera.far_clip);
	fprintf(file, "\n  \"player\":{\"present\":%s,\"object_id\":%u,\"definition\":",
		state.player.present ? "true" : "false", state.player.object_id);
	Json_String(file, state.player.definition); fprintf(file, ",\"type\":");
	Json_String(file, state.player.type); fprintf(file, ",\"position\":");
	Json_Float_Array(file, state.player.position, 3U); fprintf(file, ",\"orientation\":");
	Json_Float_Array(file, state.player.orientation, 4U); fprintf(file, ",\"velocity\":");
	Json_Float_Array(file, state.player.velocity, 3U);
	fprintf(file, ",\"health\":%.9g,\"physics_registered\":%s,\"grounded\":%s},",
		state.player.health, state.player.physics_registered ? "true" : "false",
		state.player.grounded ? "true" : "false");
	const A31RendererTelemetry &r = state.renderer;
	fprintf(file,
		"\n  \"renderer\":{\"render_objects\":%llu,\"mesh_candidates\":%llu,\"lod_selections\":%llu,\"draw_calls\":%llu,\"mesh_submissions\":%llu,\"vertices\":%llu,\"triangles\":%llu,\"indexed_draw_calls\":%llu,\"indexed_vertex_references\":%llu,\"indexed_triangles\":%llu,\"material_passes\":%llu,\"textures_resident\":%llu,\"texture_bytes_resident\":%llu,\"texture_uploads\":%llu,\"texture_binds\":%llu,\"texture_bind_skips\":%llu,\"texture_requests\":%llu,\"texture_decodes\":%llu,\"texture_dds_loads\":%llu,\"texture_tga_loads\":%llu,\"texture_missing\":%llu,\"texture_source_missing\":%llu,\"texture_invalid_data\":%llu,\"texture_unsupported_formats\":%llu,\"texture_decode_failures\":%llu,\"texture_upload_failures\":%llu,\"texture_checkerboard_fallbacks\":%llu,\"texture_checkerboard_binds\":%llu,\"texture_invalid_binds\":%llu,\"texture_sampler_updates\":%llu,\"texture_sampler_skips\":%llu,\"texture_stage_enable_skips\":%llu,\"texture_combiner_skips\":%llu,\"texture_unsupported_stages\":%llu,\"state_changes\":%llu,\"render_state_skips\":%llu,\"rejected\":%llu,\"unsupported\":%llu,\"backend_errors\":%llu,\"geometry_checksum\":\"%08X\",\"indexed_checksum\":\"%08X\",\"visible_objects\":%u,\"visibility_sectors\":%u,\"mesh_candidates_not_submitted\":%u,\"culling_count_exact\":%s},",
		(unsigned long long)r.render_objects, (unsigned long long)r.mesh_candidates,
		(unsigned long long)r.lod_selections, (unsigned long long)r.draw_calls,
		(unsigned long long)r.mesh_submissions, (unsigned long long)r.vertices,
		(unsigned long long)r.triangles, (unsigned long long)r.indexed_draw_calls,
		(unsigned long long)r.indexed_vertex_references,
		(unsigned long long)r.indexed_triangles, (unsigned long long)r.material_passes,
		(unsigned long long)r.textures_resident,
		(unsigned long long)r.texture_bytes_resident,
		(unsigned long long)r.texture_uploads, (unsigned long long)r.texture_binds,
		(unsigned long long)r.texture_bind_skips,
		(unsigned long long)r.texture_requests, (unsigned long long)r.texture_decodes,
		(unsigned long long)r.texture_dds_loads,
		(unsigned long long)r.texture_tga_loads,
		(unsigned long long)r.texture_missing,
		(unsigned long long)r.texture_source_missing,
		(unsigned long long)r.texture_invalid_data,
		(unsigned long long)r.texture_unsupported_formats,
		(unsigned long long)r.texture_decode_failures,
		(unsigned long long)r.texture_upload_failures,
		(unsigned long long)r.texture_checkerboard_fallbacks,
		(unsigned long long)r.texture_checkerboard_binds,
		(unsigned long long)r.texture_invalid_binds,
		(unsigned long long)r.texture_sampler_updates,
		(unsigned long long)r.texture_sampler_skips,
		(unsigned long long)r.texture_stage_enable_skips,
		(unsigned long long)r.texture_combiner_skips,
		(unsigned long long)r.texture_unsupported_stages,
		(unsigned long long)r.state_changes,
		(unsigned long long)r.render_state_skips,
		(unsigned long long)r.rejected_submissions,
		(unsigned long long)r.unsupported_submissions,
		(unsigned long long)r.backend_errors, r.geometry_checksum,
		r.indexed_geometry_checksum, r.visible_object_count,
		r.visibility_sector_count, r.mesh_candidates_not_submitted,
		r.culling_count_exact ? "true" : "false");
	const A31MemoryTelemetry &m = state.memory;
	fprintf(file, "\n  \"memory\":{\"available\":%s,\"sample_count\":%u,\"system_user_free\":%lld,\"system_cdram_free\":%lld,\"system_phycont_free\":%lld,\"vitagl_ram_total\":%llu,\"vitagl_ram_free\":%llu,\"vitagl_vram_total\":%llu,\"vitagl_vram_free\":%llu,\"vitagl_slow_total\":%llu,\"vitagl_slow_free\":%llu,\"vitagl_all_total\":%llu,\"vitagl_all_free\":%llu,\"system_user_free_low_water\":%lld,\"system_cdram_free_low_water\":%lld,\"system_phycont_free_low_water\":%lld,\"vitagl_ram_free_low_water\":%llu,\"vitagl_vram_free_low_water\":%llu,\"vitagl_slow_free_low_water\":%llu,\"vitagl_all_free_low_water\":%llu},",
		m.available ? "true" : "false", m.sample_count, (long long)m.system_user_free,
		(long long)m.system_cdram_free, (long long)m.system_phycont_free,
		(unsigned long long)m.vitagl_ram_total, (unsigned long long)m.vitagl_ram_free,
		(unsigned long long)m.vitagl_vram_total, (unsigned long long)m.vitagl_vram_free,
		(unsigned long long)m.vitagl_slow_total, (unsigned long long)m.vitagl_slow_free,
		(unsigned long long)m.vitagl_all_total, (unsigned long long)m.vitagl_all_free,
		(long long)m.system_user_free_low_water,
		(long long)m.system_cdram_free_low_water,
		(long long)m.system_phycont_free_low_water,
		(unsigned long long)m.vitagl_ram_free_low_water,
		(unsigned long long)m.vitagl_vram_free_low_water,
		(unsigned long long)m.vitagl_slow_free_low_water,
		(unsigned long long)m.vitagl_all_free_low_water);
	fprintf(file, "\n  \"runtime\":{\"game_updates\":%llu,\"physics_updates\":%llu,\"input_actions\":%llu,\"scripts_active\":%s},",
		(unsigned long long)state.game_update_count,
		(unsigned long long)state.physics_update_count,
		(unsigned long long)state.input_action_count,
		state.scripts_active ? "true" : "false");
	fprintf(file, "\n  \"benchmark\":{\"active\":%s,\"route\":",
		state.benchmark_active ? "true" : "false");
	Json_String(file, state.benchmark_route);
	fprintf(file, ",\"point\":%u},\n  \"sensors\":{\"available\":%s,\"battery_percent\":%.9g,\"battery_temperature_c\":%.9g}\n}\n",
		state.benchmark_point, state.sensors.available ? "true" : "false",
		state.sensors.battery_percent, state.sensors.battery_temperature_c);
	return fflush(file) == 0 && fclose(file) == 0;
}

bool Write_History(const char *path, const A31FrameHistory &history)
{
	FILE *file = fopen(path, "wb");
	if (file == NULL) return false;
	fprintf(file, "frame,monotonic_us,frame_us,ordinary_frame_us,input_us,game_update_us,physics_us,camera_us,visibility_us,render_us,present_us,housekeeping_us,capture_readback_us,draw_calls,meshes,vertices,triangles,indexed_draws,indexed_triangles,material_passes,textures_resident,texture_bytes,texture_uploads,texture_binds,texture_bind_skips,texture_sampler_updates,texture_sampler_skips,texture_stage_enable_skips,texture_combiner_skips,texture_unsupported_stages,state_changes,render_state_skips,rejected,unsupported,backend_errors,user_free,cdram_free,phycont_free,user_free_low_water,cdram_free_low_water,phycont_free_low_water,vitagl_ram_free_low_water,vitagl_vram_free_low_water,vitagl_slow_free_low_water,vitagl_all_free_low_water,memory_samples,benchmark_active,benchmark_point,game_updates,physics_updates,input_actions\n");
	for (size_t index = 0; index < history.Count(); ++index) {
		const A31FrameTelemetry &f = history.Oldest(index);
		const A31RendererTelemetry &r = f.renderer;
		fprintf(file, "%llu,%llu,%llu,%llu,%llu,%llu,%llu,%llu,%llu,%llu,%llu,%llu,%llu,%llu,%llu,%llu,%llu,%llu,%llu,%llu,%llu,%llu,%llu,%llu,%llu,%llu,%llu,%llu,%llu,%llu,%llu,%llu,%llu,%llu,%llu,%lld,%lld,%lld,%lld,%lld,%lld,%llu,%llu,%llu,%llu,%u,%d,%u,%llu,%llu,%llu\n",
			(unsigned long long)f.frame_index, (unsigned long long)f.monotonic_us,
			(unsigned long long)f.frame_time_us,
			(unsigned long long)f.ordinary_frame_time_us,
			(unsigned long long)f.stages.input_us,
			(unsigned long long)f.stages.game_update_us,
			(unsigned long long)f.stages.physics_us,
			(unsigned long long)f.stages.camera_us,
			(unsigned long long)f.stages.visibility_us,
			(unsigned long long)f.stages.render_us,
			(unsigned long long)f.stages.present_us,
			(unsigned long long)f.stages.housekeeping_us,
			(unsigned long long)f.stages.capture_readback_us,
			(unsigned long long)r.draw_calls, (unsigned long long)r.mesh_submissions,
			(unsigned long long)r.vertices, (unsigned long long)r.triangles,
			(unsigned long long)r.indexed_draw_calls,
			(unsigned long long)r.indexed_triangles,
			(unsigned long long)r.material_passes,
			(unsigned long long)r.textures_resident,
			(unsigned long long)r.texture_bytes_resident,
			(unsigned long long)r.texture_uploads, (unsigned long long)r.texture_binds,
			(unsigned long long)r.texture_bind_skips,
			(unsigned long long)r.texture_sampler_updates,
			(unsigned long long)r.texture_sampler_skips,
			(unsigned long long)r.texture_stage_enable_skips,
			(unsigned long long)r.texture_combiner_skips,
			(unsigned long long)r.texture_unsupported_stages,
			(unsigned long long)r.state_changes,
			(unsigned long long)r.render_state_skips,
			(unsigned long long)r.rejected_submissions,
			(unsigned long long)r.unsupported_submissions,
			(unsigned long long)r.backend_errors,
			(long long)f.memory.system_user_free, (long long)f.memory.system_cdram_free,
			(long long)f.memory.system_phycont_free,
			(long long)f.memory.system_user_free_low_water,
			(long long)f.memory.system_cdram_free_low_water,
			(long long)f.memory.system_phycont_free_low_water,
			(unsigned long long)f.memory.vitagl_ram_free_low_water,
			(unsigned long long)f.memory.vitagl_vram_free_low_water,
			(unsigned long long)f.memory.vitagl_slow_free_low_water,
			(unsigned long long)f.memory.vitagl_all_free_low_water,
			f.memory.sample_count, f.benchmark_active ? 1 : 0,
			f.benchmark_point, (unsigned long long)f.game_update_count,
			(unsigned long long)f.physics_update_count,
			(unsigned long long)f.input_action_count);
	}
	return fflush(file) == 0 && fclose(file) == 0;
}

uint64_t Ordinary_Frame_Percentile(const A31FrameHistory &history,
	uint32_t percentile)
{
	if (history.Count() == 0U) return 0U;
	uint64_t ordered[A31_FRAME_HISTORY_CAPACITY];
	for (size_t index = 0U; index < history.Count(); ++index) {
		ordered[index] = history.Oldest(index).ordinary_frame_time_us;
	}
	// This runs only while writing a user-requested capture bundle. Keeping the
	// fixed 240-sample insertion sort avoids allocations and any frame-time cost.
	for (size_t index = 1U; index < history.Count(); ++index) {
		const uint64_t value = ordered[index];
		size_t cursor = index;
		while (cursor > 0U && ordered[cursor - 1U] > value) {
			ordered[cursor] = ordered[cursor - 1U];
			--cursor;
		}
		ordered[cursor] = value;
	}
	const size_t rank = (static_cast<size_t>(percentile) * history.Count() + 99U) /
		100U;
	return ordered[rank == 0U ? 0U : rank - 1U];
}

bool Write_Summary(const char *path, const A31StateSnapshot &state,
	const A31FrameHistory &history)
{
	FILE *file = fopen(path, "wb");
	if (file == NULL) return false;
	uint64_t ordinary_total = 0U;
	uint64_t ordinary_min = 0U;
	uint64_t ordinary_max = 0U;
	for (size_t index = 0; index < history.Count(); ++index) {
		const uint64_t value = history.Oldest(index).ordinary_frame_time_us;
		ordinary_total += value;
		if (index == 0U || value < ordinary_min) ordinary_min = value;
		if (value > ordinary_max) ordinary_max = value;
	}
	fprintf(file,
			"%s developer capture\nCandidate: %s\nRuntime log: %s\nPhase: %s\nReason: %s\nFrame: %llu\nHistory frames: %u\nOrdinary frame min/p50/p95/p99/mean/max: %.3f / %.3f / %.3f / %.3f / %.3f / %.3f ms\nCapture stall excluded: %.3f ms\nLoading visual gate: active=%d logical=%ux%u native=%ux%u presentation=%u,%u %ux%u framebuffer=%ux%u fullscreen=%d aspect=%d original_owner=%d overlay_disabled=%d loadscreen_vflip=%d gameplay_uv=%d\nWorld: %u static, %u dynamic, %u semantic meshes\nCamera: %s (%s)\nPlayer: %s id=%u type=%s\nRenderer: %llu draws, %llu vertices, %llu triangles, %llu material passes\nTextures: %llu resident, %llu bytes, %llu uploads, %llu binds, %llu bind skips\nTexture state: %llu sampler updates, %llu sampler skips, %llu stage-enable skips, %llu combiner skips, %llu unsupported stages\nBackend: %llu state changes, %llu render-state skips, %llu errors, %llu rejected, %llu unsupported\nMemory samples: %u\nMemory user/cdram/phycont free: %lld / %lld / %lld\nMemory user/cdram/phycont sampled low-water: %lld / %lld / %lld\nMemory VitaGL RAM/VRAM/SLOW/ALL sampled low-water: %llu / %llu / %llu / %llu\nBenchmark: %s route=%s point=%u\n",
		state.build_label, state.milestone, state.runtime_log_path, state.phase,
		state.reason, (unsigned long long)state.capture_frame,
		static_cast<unsigned>(history.Count()),
		ordinary_min / 1000.0,
		Ordinary_Frame_Percentile(history, 50U) / 1000.0,
		Ordinary_Frame_Percentile(history, 95U) / 1000.0,
		Ordinary_Frame_Percentile(history, 99U) / 1000.0,
		history.Count() != 0U ? ordinary_total / 1000.0 / history.Count() : 0.0,
		ordinary_max / 1000.0, state.capture_stall_us / 1000.0,
		state.loading_visual_gate.active ? 1 : 0,
		state.loading_visual_gate.original_logical_width,
		state.loading_visual_gate.original_logical_height,
			state.loading_visual_gate.native_display_width,
			state.loading_visual_gate.native_display_height,
			state.loading_visual_gate.native_presentation_x,
			state.loading_visual_gate.native_presentation_y,
			state.loading_visual_gate.native_presentation_width,
			state.loading_visual_gate.native_presentation_height,
			state.loading_visual_gate.framebuffer_width,
			state.loading_visual_gate.framebuffer_height,
			state.loading_visual_gate.logical_to_native_fullscreen ? 1 : 0,
			state.loading_visual_gate.aspect_preserved ? 1 : 0,
			state.loading_visual_gate.original_loading_screen_owner ? 1 : 0,
		state.loading_visual_gate.direct_vitagl_overlay_disabled ? 1 : 0,
		state.loading_visual_gate.loading_texture_v_flip_enabled ? 1 : 0,
		state.loading_visual_gate.gameplay_texture_v_unchanged ? 1 : 0,
		state.world.static_object_count, state.world.dynamic_object_count,
		state.world.semantic_meshes, state.camera.present ? "present" : "absent",
		state.camera.player_owned ? "player-owned" : "developer-owned",
		state.player.present ? "present" : "absent", state.player.object_id,
		state.player.type, (unsigned long long)state.renderer.draw_calls,
		(unsigned long long)state.renderer.vertices,
		(unsigned long long)state.renderer.triangles,
		(unsigned long long)state.renderer.material_passes,
		(unsigned long long)state.renderer.textures_resident,
		(unsigned long long)state.renderer.texture_bytes_resident,
		(unsigned long long)state.renderer.texture_uploads,
		(unsigned long long)state.renderer.texture_binds,
		(unsigned long long)state.renderer.texture_bind_skips,
		(unsigned long long)state.renderer.texture_sampler_updates,
		(unsigned long long)state.renderer.texture_sampler_skips,
		(unsigned long long)state.renderer.texture_stage_enable_skips,
		(unsigned long long)state.renderer.texture_combiner_skips,
		(unsigned long long)state.renderer.texture_unsupported_stages,
		(unsigned long long)state.renderer.state_changes,
		(unsigned long long)state.renderer.render_state_skips,
		(unsigned long long)state.renderer.backend_errors,
		(unsigned long long)state.renderer.rejected_submissions,
		(unsigned long long)state.renderer.unsupported_submissions,
		state.memory.sample_count,
		(long long)state.memory.system_user_free,
		(long long)state.memory.system_cdram_free,
		(long long)state.memory.system_phycont_free,
		(long long)state.memory.system_user_free_low_water,
		(long long)state.memory.system_cdram_free_low_water,
		(long long)state.memory.system_phycont_free_low_water,
		(unsigned long long)state.memory.vitagl_ram_free_low_water,
		(unsigned long long)state.memory.vitagl_vram_free_low_water,
		(unsigned long long)state.memory.vitagl_slow_free_low_water,
		(unsigned long long)state.memory.vitagl_all_free_low_water,
		state.benchmark_active ? "active" : "inactive", state.benchmark_route,
		state.benchmark_point);
	return fflush(file) == 0 && fclose(file) == 0;
}

const A31BenchmarkPoint kM00Route[] = {
	{{5.764015f,-176.000000f,64.000000f},{5.764015f,4.781448f,10.589802f},120U,90U},
	{{104.000000f,-82.000000f,34.000000f},{18.000000f,8.000000f,7.000000f},120U,90U},
	{{-91.000000f,83.000000f,28.000000f},{-5.000000f,5.000000f,5.000000f},120U,90U},
	{{74.000000f,102.000000f,42.000000f},{8.000000f,0.000000f,8.000000f},120U,90U}
};

uint64_t Route_Length()
{
	uint64_t length = 0U;
	for (size_t index = 0; index < sizeof(kM00Route) / sizeof(kM00Route[0]); ++index)
		length += kM00Route[index].duration_frames;
	return length;
}

} // namespace

A31FrameHistory::A31FrameHistory() : Next(0U), Used(0U) { memset(Frames, 0, sizeof(Frames)); }
void A31FrameHistory::Reset() { Next = 0U; Used = 0U; memset(Frames, 0, sizeof(Frames)); }
void A31FrameHistory::Push(const A31FrameTelemetry &frame) { Frames[Next] = frame; Next = (Next + 1U) % A31_FRAME_HISTORY_CAPACITY; if (Used < A31_FRAME_HISTORY_CAPACITY) ++Used; }
size_t A31FrameHistory::Count() const { return Used; }
const A31FrameTelemetry &A31FrameHistory::Oldest(size_t index) const { const size_t first = Used == A31_FRAME_HISTORY_CAPACITY ? Next : 0U; return Frames[(first + index) % A31_FRAME_HISTORY_CAPACITY]; }

bool A31_Format_Capture_Overlay(char *output, size_t capacity,
	const A31StateSnapshot &state, const A31FrameHistory &history)
{
	if (output == NULL || capacity == 0U) return false;
	const double frame_ms = history.Count() != 0U ?
		static_cast<double>(history.Oldest(history.Count() - 1U).ordinary_frame_time_us) /
		1000.0 : 0.0;
	const int count = snprintf(output, capacity,
		"%s\nFRAME %" PRIu64 "\n%.2f MS\nDRAW %" PRIu64 "\nTRI %" PRIu64 "\nPOINT %" PRIu32,
		state.capture_overlay_label[0] != '\0' ? state.capture_overlay_label : state.milestone,
		state.capture_frame, frame_ms,
		state.renderer.draw_calls, state.renderer.triangles,
		state.benchmark_point);
	return count > 0 && static_cast<size_t>(count) < capacity;
}

A31CaptureBundleResult A31_Write_Capture_Bundle(const A31CaptureBundleInput &input)
{
	A31CaptureBundleResult result = {};
	const uint64_t start_us = Monotonic_Us();
	if (input.base_directory == NULL || input.bundle_label == NULL ||
		input.history == NULL || !Make_Directory(input.base_directory)) {
		Set_Error(result, "capture base directory unavailable"); return result;
	}
	if (snprintf(result.bundle_path, sizeof(result.bundle_path), "%s/%s",
		input.base_directory, input.bundle_label) <= 0 ||
		!Make_Directory(result.bundle_path)) {
		Set_Error(result, "capture bundle directory unavailable");
		result.failure_marker_written = Write_Failure_Marker(input, result);
		return result;
	}
	char path[A31_CAPTURE_PATH_CAPACITY];
	int history_error = 0;
	int state_error = 0;
	int summary_error = 0;
	if (input.resolved_rgba_bottom_up != NULL &&
		Open_Path(path, sizeof(path), result.bundle_path, "frame.bmp")) {
		result.screenshot_written = Write_Bmp(path, input.resolved_rgba_bottom_up,
			input.framebuffer_width, input.framebuffer_height, NULL);
		int error_code = 0;
		result.screenshot_written = result.screenshot_written &&
			Verify_Artifact(path, "BM", error_code);
		if (!result.screenshot_written)
			Set_Error(result, "clean screenshot write/verify failed", error_code);
	}
		if (input.write_annotated_screenshot && input.resolved_rgba_bottom_up != NULL &&
			Open_Path(path, sizeof(path), result.bundle_path, "frame-annotated.bmp")) {
			char annotation[256];
			result.annotated_screenshot_written =
				A31_Format_Capture_Overlay(annotation, sizeof(annotation), input.state,
					*input.history) && Write_Bmp(path,
				input.resolved_rgba_bottom_up, input.framebuffer_width,
				input.framebuffer_height, annotation);
			int error_code = 0;
			result.annotated_screenshot_written = result.annotated_screenshot_written &&
				Verify_Artifact(path, "BM", error_code);
			if (!result.annotated_screenshot_written)
				Set_Error(result, "annotated screenshot write/verify failed", error_code);
	}
	if (Open_Path(path, sizeof(path), result.bundle_path, "frames.csv")) {
		result.history_written = Write_History(path, *input.history);
		result.history_written = result.history_written &&
			Verify_Artifact(path, "frame,", history_error);
	}
	if (!result.history_written)
		Set_Error(result, "frame history write/verify failed", history_error != 0 ? history_error : errno);
	A31StateSnapshot final_state = input.state;
	final_state.capture_stall_us += Monotonic_Us() - start_us;
	if (Open_Path(path, sizeof(path), result.bundle_path, "state.json")) {
		result.state_written = Write_State(path, final_state);
		result.state_written = result.state_written && Verify_Artifact(path, "{", state_error);
	}
	if (!result.state_written)
		Set_Error(result, "state snapshot write/verify failed", state_error != 0 ? state_error : errno);
	if (Open_Path(path, sizeof(path), result.bundle_path, "summary.txt")) {
		result.summary_written = Write_Summary(path, final_state, *input.history);
		result.summary_written = result.summary_written && Verify_Artifact(path,
			final_state.build_label, summary_error);
	}
	if (!result.summary_written)
		Set_Error(result, "summary write/verify failed", summary_error != 0 ? summary_error : errno);
	result.write_stall_us = Monotonic_Us() - start_us;
	const bool screenshot_required = input.resolved_rgba_bottom_up != NULL;
	result.passed = (!screenshot_required || result.screenshot_written) && result.state_written &&
		result.history_written && result.summary_written &&
		(!input.write_annotated_screenshot || result.annotated_screenshot_written);
	if (!result.passed) {
		result.failure_marker_written = Write_Failure_Marker(input, result);
	}
	return result;
}

A31M00BenchmarkRoute::A31M00BenchmarkRoute() : StartFrame(0U), Active(false) {}
void A31M00BenchmarkRoute::Start(uint64_t starting_frame) { StartFrame = starting_frame; Active = true; }
void A31M00BenchmarkRoute::Stop() { Active = false; }
bool A31M00BenchmarkRoute::Is_Active() const { return Active; }
bool A31M00BenchmarkRoute::Is_Complete(uint64_t frame) const { return Active && frame >= StartFrame + Route_Length(); }
uint32_t A31M00BenchmarkRoute::Point_Index(uint64_t frame) const { uint64_t offset = frame > StartFrame ? frame - StartFrame : 0U; for (uint32_t index = 0U; index < sizeof(kM00Route) / sizeof(kM00Route[0]); ++index) { if (offset < kM00Route[index].duration_frames) return index; offset -= kM00Route[index].duration_frames; } return static_cast<uint32_t>(sizeof(kM00Route) / sizeof(kM00Route[0]) - 1U); }
bool A31M00BenchmarkRoute::Is_Capture_Frame(uint64_t frame) const { if (!Active || Is_Complete(frame)) return false; uint64_t offset = frame - StartFrame; const uint32_t point = Point_Index(frame); for (uint32_t index = 0U; index < point; ++index) offset -= kM00Route[index].duration_frames; return offset == kM00Route[point].capture_frame; }
const A31BenchmarkPoint &A31M00BenchmarkRoute::Point(uint64_t frame) const { return kM00Route[Point_Index(frame)]; }
uint64_t A31M00BenchmarkRoute::Starting_Frame() const { return StartFrame; }
