#pragma once

#include <stddef.h>
#include <stdint.h>

struct RenegadeMilesRuntimeStats {
	uint32_t output_start_attempts;
	uint32_t output_start_successes;
	uint32_t output_start_failures;
	uint32_t output_buffers_written;
	uint32_t output_write_failures;
	uint32_t output_lock_starvation_buffers;
	uint64_t output_stream_buffers_written;
	uint64_t output_stream_frames_written;
	uint64_t output_stream_nonzero_buffers_written;
	uint32_t output_stream_peak_abs;
	uint32_t last_output_stream_active;
	uint32_t last_output_stream_frames;
	uint32_t last_output_stream_nonzero;
	uint32_t last_output_stream_peak_abs;
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
	uint64_t stream_mixed_buffers;
	uint64_t stream_mixed_frames;
	uint64_t stream_mixed_nonzero_buffers;
	uint32_t stream_mixed_peak_abs;
	uint32_t last_stream_mix_active;
	uint32_t last_stream_mix_frames;
	uint32_t last_stream_mix_nonzero;
	uint32_t last_stream_mix_peak_abs;
	uint32_t last_stream_frames;
	uint32_t last_stream_fact_frames;
	uint32_t last_stream_estimated_frames;
	uint32_t last_stream_untrimmed_frames;
	uint32_t last_stream_trimmed_frames;
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
	uint32_t pcm_decodes;
	uint32_t pcm_cache_hits;
	uint32_t pcm_cache_evictions;
	uint32_t pcm_cache_entries;
	uint32_t pcm_cache_bytes;
	uint32_t pcm_live_bytes;
	uint32_t pcm_live_high_water_bytes;
	uint32_t pcm_largest_image_bytes;
	uint32_t allocated_samples;
	uint32_t active_samples;
	uint32_t active_streams;
	uint32_t active_stream_position_ms;
	uint32_t active_stream_length_ms;
	uint32_t active_stream_cursor_frame;
	uint32_t active_stream_total_frames;
	uint32_t active_stream_loop_count;
	uint32_t active_stream_volume;
	uint32_t active_stream_pan;
	char last_stream_name[96];
	char last_error[160];
};

void Renegade_Miles_Reset_Runtime_Stats();
void Renegade_Miles_Get_Runtime_Stats(RenegadeMilesRuntimeStats *stats);

// Loading-screen pre-warm of the decoded-PCM cache. Decodes one complete
// WAVE file image (the same bytes WWAudio later passes to
// AIL_set_*sample_file) and retains it only when it fits the cache's free
// budget and a free slot without evicting anything. Returns
// RENEGADE_MILES_PREWARM_CACHED (newly retained), _PRESENT (already cached),
// _FULL (would need eviction; caller should stop) or _SKIPPED (MPEG, too
// large, or not decodable). *retained_bytes receives the retained size.
enum {
	RENEGADE_MILES_PREWARM_SKIPPED = 0,
	RENEGADE_MILES_PREWARM_CACHED = 1,
	RENEGADE_MILES_PREWARM_PRESENT = 2,
	RENEGADE_MILES_PREWARM_FULL = 3
};
int Renegade_Miles_Prewarm_Pcm(const void *data, size_t bytes, size_t *retained_bytes);

// RVAU1 audio cost switches (audio-cost-v1.flag; bits in renegade_audio_cost.h).
// The Vita provider reads the flag in AIL_startup; tests may set the mask.
// Counters are cumulative since startup.
struct RenegadeMilesAudioCostStats {
	uint32_t mode;
	uint32_t stream_probe_hits;      // stream opens that reused a cached decode
	uint32_t stream_probe_misses;
	uint32_t stream_pcm_deferred;    // first opens kept out of the PCM cache
	uint32_t stream_pcm_admitted;    // repeat opens admitted to the PCM cache
	uint32_t image_pool_hits;        // stream images read into a slab
	uint32_t image_pool_oversize;    // larger than a slab: heap path
	uint32_t image_pool_busy;        // every slab claimed: heap path
	uint32_t image_pool_allocation_failures;
	uint32_t image_pool_resident_bytes;
	uint32_t exact_reserve_raises;   // decodes whose reserve bit 0 enlarged
};
void Renegade_Miles_Set_Audio_Cost_Mode(unsigned mode);
unsigned Renegade_Miles_Get_Audio_Cost_Mode();
void Renegade_Miles_Get_Audio_Cost_Stats(RenegadeMilesAudioCostStats *stats);
