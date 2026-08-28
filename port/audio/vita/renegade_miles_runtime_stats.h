#pragma once

#include <stdint.h>

struct RenegadeMilesRuntimeStats {
	uint32_t output_start_attempts;
	uint32_t output_start_successes;
	uint32_t output_start_failures;
	uint32_t output_buffers_written;
	uint32_t output_write_failures;
	uint32_t sample_file_load_attempts;
	uint32_t sample_file_load_successes;
	uint32_t sample_file_load_failures;
	uint32_t sample_3d_file_load_attempts;
	uint32_t sample_3d_file_load_successes;
	uint32_t sample_3d_file_load_failures;
	uint32_t stream_open_attempts;
	uint32_t stream_open_successes;
	uint32_t stream_open_failures;
	uint32_t stream_start_attempts;
	uint32_t stream_start_successes;
	uint32_t stream_start_silent;
	uint32_t stream_start_zero_volume;
	uint64_t stream_bytes_read;
	uint64_t stream_decoded_frames;
	uint32_t last_stream_frames;
	uint32_t last_stream_rate;
	uint32_t last_stream_volume;
	uint32_t last_stream_pan;
	uint32_t sample_start_attempts;
	uint32_t sample_start_successes;
	uint32_t sample_start_silent;
	uint64_t mixed_buffers;
	uint64_t mixed_frames;
	uint64_t mixed_nonzero_buffers;
	uint32_t mixed_peak_abs;
	uint32_t allocated_samples;
	uint32_t active_samples;
	char last_stream_name[96];
	char last_error[160];
};

void Renegade_Miles_Reset_Runtime_Stats();
void Renegade_Miles_Get_Runtime_Stats(RenegadeMilesRuntimeStats *stats);
