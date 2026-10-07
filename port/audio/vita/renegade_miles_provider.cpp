#include "mss.h"

#include "renegade_miles_runtime_stats.h"
#include "renegade_miles_test.h"
#include "renegade_wave_decoder.h"
#include "renegade_audio_output_buffers.h"

#include <algorithm>
#include <atomic>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <limits>
#include <new>
#include <pthread.h>
#include <time.h>
#include <vector>

#if defined(__vita__)
#include <psp2/audioout.h>
#include <psp2/kernel/cpu.h>
#include <psp2/kernel/threadmgr.h>
#endif

using RenegadeVitaAudio::DecodedWave;
using RenegadeVitaAudio::WaveInfo;

// One decoded PCM image. Every voice that plays the same source image shares
// it, and a bounded cache keeps recently used images, so replaying a sound
// does not decode its whole file again. References are guarded by the
// provider mutex.
struct RenegadeMilesPcm {
	DecodedWave wave;
	size_t frames = 0;
	U32 encoded_data_bytes = 0;
	uint64_t source_hash = 0;
	size_t source_bytes = 0;
	uint64_t last_use = 0;
	uint32_t references = 0;
	bool cached = false;
};

struct RenegadeMilesSample {
	// Format metadata of the current image; its PCM lives in pcm.
	DecodedWave wave;
	RenegadeMilesPcm *pcm = nullptr;
	std::unique_ptr<RenegadeVitaAudio::MpegPlayback> mpeg;
	U32 encoded_data_bytes = 0;
	double cursor = 0.0;
	S32 playback_rate = 0;
	S32 volume = 127;
	S32 pan = 64;
	U32 loop_count = 1;
	U32 loops_remaining = 1;
	AIL_USER_DATA user_data[8] = {};
	F32 position[3] = {};
	F32 maximum_distance = 100.0F;
	F32 minimum_distance = 1.0F;
	bool spatial = false;
	bool streaming = false;
	bool playing = false;
	bool paused = false;

	~RenegadeMilesSample();
};

struct RenegadeMilesStream {
	RenegadeMilesSample *sample = nullptr;
	bool owns_sample = false;
};

struct RenegadeMilesMixSummary {
	uint32_t stream_active = 0U;
	uint32_t stream_frames = 0U;
	uint32_t stream_nonzero = 0U;
	uint32_t stream_peak_abs = 0U;
};

struct RenegadeMilesPreparedSource {
	DecodedWave wave;
	WaveInfo info;
	std::unique_ptr<RenegadeVitaAudio::MpegPlayback> mpeg;
	uint64_t source_hash = 0U;
	size_t source_bytes = 0U;
	const char *error = nullptr;
	bool is_mpeg = false;
	bool cacheable = false;
};

namespace {

constexpr size_t kOutputFrames = 1024U;
constexpr S32 kOutputRate = 48000;
constexpr size_t kMaximumWaveBytes = 64U * 1024U * 1024U;
constexpr HPROVIDER kNative3DProvider = 1U;
// Idle decoded images retained for replay. Images still playing are never
// evicted; an image larger than a quarter of the budget is not retained.
constexpr size_t kPcmCacheSlots = 128U;
constexpr size_t kPcmCacheBudgetBytes = 4U * 1024U * 1024U;
constexpr size_t kPcmCacheMaximumSourceBytes = 1024U * 1024U;

pthread_once_t g_mutex_once = PTHREAD_ONCE_INIT;
pthread_mutex_t g_mutex;
std::atomic<uint32_t> g_output_lock_starvation_buffers{0U};
#if !defined(RENEGADE_MILES_MANUAL_MIX)
pthread_t g_output_thread;
bool g_output_thread_running = false;
std::atomic<bool> g_output_stop{false};
#if defined(__vita__)
int g_audio_port = -1;
#endif
#endif
RenegadeMilesDriver g_driver = {};
RenegadeMilesSample g_listener;
// Ordered sample registry with non-throwing growth. This TU is built with
// -fno-exceptions, where std::vector growth failure aborts the process; keep
// insertion order identical so mixing iteration stays bit-exact.
class SampleRegistry {
	RenegadeMilesSample **items = nullptr;
	size_t count = 0, capacity = 0;
public:
	RenegadeMilesSample **begin() const { return items; }
	RenegadeMilesSample **end() const { return items + count; }
	size_t size() const { return count; }
	bool push_back(RenegadeMilesSample *sample)
	{
		if (count == capacity) {
			const size_t grown = capacity == 0 ? 16U : capacity * 2U;
			void *resized = std::realloc(items, grown * sizeof(*items));
			if (resized == nullptr) return false;
			items = static_cast<RenegadeMilesSample **>(resized);
			capacity = grown;
		}
		items[count++] = sample;
		return true;
	}
	void erase(RenegadeMilesSample **entry)
	{
		std::memmove(entry, entry + 1,
			static_cast<size_t>(end() - (entry + 1)) * sizeof(*items));
		--count;
	}
	void clear() { count = 0; }
};
SampleRegistry g_samples;
char g_last_error[160] = "no error";
RenegadeMilesRuntimeStats g_stats = {};
AIL_FILE_OPEN_CALLBACK g_file_open = nullptr;
AIL_FILE_CLOSE_CALLBACK g_file_close = nullptr;
AIL_FILE_SEEK_CALLBACK g_file_seek = nullptr;
AIL_FILE_READ_CALLBACK g_file_read = nullptr;
RenegadeMilesPcm *g_pcm_cache[kPcmCacheSlots] = {};
size_t g_pcm_cache_bytes = 0U;
uint64_t g_pcm_cache_clock = 0U;
// Decoded PCM held by live images (cached and uncached). Guarded by g_mutex.
size_t g_pcm_live_bytes = 0U;
size_t g_pcm_live_high_water_bytes = 0U;
size_t g_pcm_largest_image_bytes = 0U;

void Initialize_Mutex()
{
	pthread_mutexattr_t attributes;
	pthread_mutexattr_init(&attributes);
	pthread_mutexattr_settype(&attributes, PTHREAD_MUTEX_RECURSIVE);
	pthread_mutex_init(&g_mutex, &attributes);
	pthread_mutexattr_destroy(&attributes);
}

void Ensure_Mutex()
{
	pthread_once(&g_mutex_once, Initialize_Mutex);
}

void Set_Error(const char *message)
{
	std::snprintf(g_last_error, sizeof(g_last_error), "%s",
		message != nullptr ? message : "unknown error");
	std::snprintf(g_stats.last_error, sizeof(g_stats.last_error), "%s",
		g_last_error);
}

uint32_t Read_U32(const uint8_t *data)
{
	return static_cast<uint32_t>(data[0]) |
		(static_cast<uint32_t>(data[1]) << 8U) |
		(static_cast<uint32_t>(data[2]) << 16U) |
		(static_cast<uint32_t>(data[3]) << 24U);
}

size_t Declared_Wave_Bytes(const void *image)
{
	if (image == nullptr) return 0;
	const uint8_t *data = static_cast<const uint8_t *>(image);
	if (Read_U32(data) != UINT32_C(0x46464952) ||
		Read_U32(data + 8U) != UINT32_C(0x45564157)) return 0;
	const uint64_t declared = static_cast<uint64_t>(Read_U32(data + 4U)) + 8U;
	return declared >= 12U && declared <= kMaximumWaveBytes
		? static_cast<size_t>(declared) : 0;
}

// 64-bit content hash of a source image, eight bytes per step. Decoding is
// a pure function of the image bytes, so an equal hash and length select the
// same decoded PCM.
uint64_t Hash_Image(const uint8_t *data, size_t bytes)
{
	uint64_t hash = UINT64_C(0x9e3779b97f4a7c15) ^
		(static_cast<uint64_t>(bytes) * UINT64_C(0xc2b2ae3d27d4eb4f));
	size_t offset = 0U;
	for (; offset + 8U <= bytes; offset += 8U) {
		uint64_t word = 0U;
		std::memcpy(&word, data + offset, sizeof(word));
		hash = (hash ^ word) * UINT64_C(0xff51afd7ed558ccd);
		hash ^= hash >> 29U;
	}
	uint64_t tail = 0U;
	std::memcpy(&tail, data + offset, bytes - offset);
	hash = (hash ^ tail ^ (static_cast<uint64_t>(bytes - offset) << 56U)) *
		UINT64_C(0xc4ceb9fe1a85ec53);
	return hash ^ (hash >> 32U);
}

size_t Pcm_Bytes(const RenegadeMilesPcm *pcm)
{
	return sizeof(*pcm) + pcm->wave.samples.capacity() * sizeof(int16_t);
}

void Release_Pcm(RenegadeMilesPcm *pcm)
{
	if (pcm != nullptr && --pcm->references == 0U) {
		g_pcm_live_bytes -= Pcm_Bytes(pcm);
		delete pcm;
	}
}

// Called once per new image after its PCM is moved in; capacity is fixed
// thereafter so Release_Pcm subtracts the same amount.
void Track_New_Pcm(const RenegadeMilesPcm *pcm)
{
	const size_t bytes = Pcm_Bytes(pcm);
	g_pcm_live_bytes += bytes;
	if (g_pcm_live_bytes > g_pcm_live_high_water_bytes)
		g_pcm_live_high_water_bytes = g_pcm_live_bytes;
	if (bytes > g_pcm_largest_image_bytes) g_pcm_largest_image_bytes = bytes;
}

void Set_Sample_Pcm(RenegadeMilesSample *sample, RenegadeMilesPcm *pcm)
{
	if (pcm != nullptr) ++pcm->references;
	Release_Pcm(sample->pcm);
	sample->pcm = pcm;
}

void Remove_Cached_Pcm(size_t slot)
{
	RenegadeMilesPcm *pcm = g_pcm_cache[slot];
	g_pcm_cache[slot] = nullptr;
	g_pcm_cache_bytes -= Pcm_Bytes(pcm);
	pcm->cached = false;
	Release_Pcm(pcm);
}

void Clear_Pcm_Cache()
{
	for (size_t slot = 0U; slot < kPcmCacheSlots; ++slot) {
		if (g_pcm_cache[slot] != nullptr) Remove_Cached_Pcm(slot);
	}
}

RenegadeMilesPcm *Find_Cached_Pcm(uint64_t hash, size_t bytes)
{
	for (RenegadeMilesPcm *pcm : g_pcm_cache) {
		if (pcm != nullptr && pcm->source_hash == hash && pcm->source_bytes == bytes)
			return pcm;
	}
	return nullptr;
}

// Evicts least recently used idle images (referenced only by the cache) until
// `bytes` more fit the budget and a slot is free. Images that voices still
// play are never evicted; if they fill the budget, nothing new is retained.
bool Make_Pcm_Cache_Room(size_t bytes)
{
	for (;;) {
		size_t free_slot = kPcmCacheSlots;
		size_t victim = kPcmCacheSlots;
		for (size_t slot = 0U; slot < kPcmCacheSlots; ++slot) {
			const RenegadeMilesPcm *pcm = g_pcm_cache[slot];
			if (pcm == nullptr) {
				if (free_slot == kPcmCacheSlots) free_slot = slot;
			} else if (pcm->references == 1U && (victim == kPcmCacheSlots ||
				pcm->last_use < g_pcm_cache[victim]->last_use)) {
				victim = slot;
			}
		}
		if (free_slot != kPcmCacheSlots && g_pcm_cache_bytes + bytes <= kPcmCacheBudgetBytes)
			return true;
		if (victim == kPcmCacheSlots) return false;
		Remove_Cached_Pcm(victim);
		++g_stats.pcm_cache_evictions;
	}
}

void Cache_Pcm(RenegadeMilesPcm *pcm)
{
	const size_t bytes = Pcm_Bytes(pcm);
	if (bytes > kPcmCacheBudgetBytes / 4U || !Make_Pcm_Cache_Room(bytes)) return;
	for (RenegadeMilesPcm *&slot : g_pcm_cache) {
		if (slot != nullptr) continue;
		slot = pcm;
		++pcm->references;
		pcm->cached = true;
		g_pcm_cache_bytes += bytes;
		return;
	}
}

DecodedWave Wave_Metadata(const DecodedWave &wave)
{
	DecodedWave metadata;
	metadata.channels = wave.channels;
	metadata.sample_rate = wave.sample_rate;
	metadata.fact_sample_frames = wave.fact_sample_frames;
	metadata.estimated_sample_frames = wave.estimated_sample_frames;
	metadata.untrimmed_sample_frames = wave.untrimmed_sample_frames;
	metadata.trimmed_sample_frames = wave.trimmed_sample_frames;
	return metadata;
}

bool Decode_Into_Sample(RenegadeMilesSample *sample, const void *data,
	size_t bytes)
{
	if (sample == nullptr || data == nullptr || bytes < 12U ||
		bytes > kMaximumWaveBytes) {
		Set_Error("invalid or oversized WAVE image");
		return false;
	}
	const uint8_t *image = static_cast<const uint8_t *>(data);
	const char *error = nullptr;
	if (RenegadeVitaAudio::Is_Mpeg_Media(image, bytes)) {
		auto playback = RenegadeVitaAudio::Open_Mpeg_Playback(image, bytes, &error);
		if (!playback) { Set_Error(error); return false; }
		Set_Sample_Pcm(sample, nullptr);
		sample->wave = {};
		sample->wave.channels = playback->Channels();
		sample->wave.sample_rate = playback->Sample_Rate();
		sample->wave.estimated_sample_frames = sample->wave.untrimmed_sample_frames =
			static_cast<uint32_t>(playback->Frame_Count());
		sample->mpeg = std::move(playback);
		sample->encoded_data_bytes = static_cast<U32>(bytes);
		sample->cursor = 0.0;
		sample->playback_rate = static_cast<S32>(sample->wave.sample_rate);
		sample->playing = sample->paused = false;
		return true;
	}
	const bool cacheable = bytes <= kPcmCacheMaximumSourceBytes;
	const uint64_t hash = cacheable ? Hash_Image(image, bytes) : 0U;
	RenegadeMilesPcm *pcm = cacheable ? Find_Cached_Pcm(hash, bytes) : nullptr;
	if (pcm != nullptr) {
		++g_stats.pcm_cache_hits;
	} else {
		DecodedWave decoded;
		WaveInfo info;
		if (!RenegadeVitaAudio::Decode_Wave_With_Info(image, bytes, &decoded, &info, &error)) {
			Set_Error(error);
			return false;
		}
		pcm = new (std::nothrow) RenegadeMilesPcm;
		if (pcm == nullptr) {
			Set_Error("decoded PCM allocation failed");
			return false;
		}
		pcm->frames = decoded.Frame_Count();
		pcm->wave = std::move(decoded);
		pcm->encoded_data_bytes = info.data_bytes;
		pcm->source_hash = hash;
		pcm->source_bytes = bytes;
		Track_New_Pcm(pcm);
		++g_stats.pcm_decodes;
		if (cacheable) Cache_Pcm(pcm);
	}
	pcm->last_use = ++g_pcm_cache_clock;
	Set_Sample_Pcm(sample, pcm);
	sample->wave = Wave_Metadata(pcm->wave);
	sample->mpeg.reset();
	sample->encoded_data_bytes = pcm->encoded_data_bytes;
	sample->cursor = 0.0;
	sample->playback_rate = static_cast<S32>(sample->wave.sample_rate);
	sample->playing = false;
	sample->paused = false;
	return true;
}

bool Prepare_Stream_Source(const void *data, size_t bytes,
	RenegadeMilesPreparedSource *prepared)
{
	if (prepared == nullptr || data == nullptr || bytes < 12U ||
		bytes > kMaximumWaveBytes) {
		if (prepared != nullptr) prepared->error = "invalid or oversized WAVE image";
		return false;
	}
	const uint8_t *image = static_cast<const uint8_t *>(data);
	prepared->source_bytes = bytes;
	prepared->is_mpeg = RenegadeVitaAudio::Is_Mpeg_Media(image, bytes);
	if (prepared->is_mpeg) {
		prepared->mpeg = RenegadeVitaAudio::Open_Mpeg_Playback(image, bytes,
			&prepared->error);
		return prepared->mpeg != nullptr;
	}
	prepared->cacheable = bytes <= kPcmCacheMaximumSourceBytes;
	prepared->source_hash = prepared->cacheable ? Hash_Image(image, bytes) : 0U;
	return RenegadeVitaAudio::Decode_Wave_With_Info(image, bytes,
		&prepared->wave, &prepared->info, &prepared->error);
}

bool Publish_Stream_Source_Locked(RenegadeMilesSample *sample,
	RenegadeMilesPreparedSource *prepared)
{
	if (sample == nullptr || prepared == nullptr) return false;
	if (prepared->is_mpeg) {
		Set_Sample_Pcm(sample, nullptr);
		sample->wave = {};
		sample->wave.channels = prepared->mpeg->Channels();
		sample->wave.sample_rate = prepared->mpeg->Sample_Rate();
		sample->wave.estimated_sample_frames =
			sample->wave.untrimmed_sample_frames = static_cast<uint32_t>(
				std::min<size_t>(prepared->mpeg->Frame_Count(),
					std::numeric_limits<uint32_t>::max()));
		sample->mpeg = std::move(prepared->mpeg);
		sample->encoded_data_bytes = static_cast<U32>(prepared->source_bytes);
	} else {
		// Preparation already performed the decode outside the mixer lock. A
		// concurrently retained cache entry can still win publication here.
		++g_stats.pcm_decodes;
		RenegadeMilesPcm *pcm = prepared->cacheable
			? Find_Cached_Pcm(prepared->source_hash, prepared->source_bytes) : nullptr;
		if (pcm != nullptr) {
			++g_stats.pcm_cache_hits;
		} else {
			pcm = new (std::nothrow) RenegadeMilesPcm;
			if (pcm == nullptr) {
				Set_Error("decoded PCM allocation failed");
				return false;
			}
			pcm->frames = prepared->wave.Frame_Count();
			pcm->wave = std::move(prepared->wave);
			pcm->encoded_data_bytes = prepared->info.data_bytes;
			pcm->source_hash = prepared->source_hash;
			pcm->source_bytes = prepared->source_bytes;
			Track_New_Pcm(pcm);
			if (prepared->cacheable) Cache_Pcm(pcm);
		}
		pcm->last_use = ++g_pcm_cache_clock;
		Set_Sample_Pcm(sample, pcm);
		sample->wave = Wave_Metadata(pcm->wave);
		sample->mpeg.reset();
		sample->encoded_data_bytes = pcm->encoded_data_bytes;
	}
	sample->cursor = 0.0;
	sample->playback_rate = static_cast<S32>(sample->wave.sample_rate);
	sample->playing = false;
	sample->paused = false;
	return true;
}

void Reset_Sample(RenegadeMilesSample *sample)
{
	if (sample == nullptr) return;
	Set_Sample_Pcm(sample, nullptr);
	sample->mpeg.reset();
	sample->wave = {};
	sample->encoded_data_bytes = 0;
	sample->cursor = 0.0;
	sample->playback_rate = 0;
	sample->volume = 127;
	sample->pan = 64;
	sample->loop_count = 1;
	sample->loops_remaining = 1;
	std::fill(std::begin(sample->user_data), std::end(sample->user_data), 0U);
	std::fill(std::begin(sample->position), std::end(sample->position), 0.0F);
	sample->maximum_distance = 100.0F;
	sample->minimum_distance = 1.0F;
	sample->spatial = false;
	sample->streaming = false;
	sample->playing = false;
	sample->paused = false;
}

size_t Sample_Frame_Count(const RenegadeMilesSample *sample)
{
	return sample->mpeg ? sample->mpeg->Frame_Count() :
		sample->pcm != nullptr ? sample->pcm->frames : 0U;
}

bool Advance_Loop(RenegadeMilesSample *sample)
{
	if (sample->loop_count == 0U) {
		sample->cursor = 0.0;
		return true;
	}
	if (sample->loops_remaining > 1U) {
		--sample->loops_remaining;
		sample->cursor = 0.0;
		return true;
	}
	sample->loops_remaining = 0U;
	sample->playing = false;
	sample->paused = false;
	return false;
}

bool Start_Sample_Locked(RenegadeMilesSample *sample)
{
	if (sample == nullptr || Sample_Frame_Count(sample) == 0) return false;
	const size_t frames = Sample_Frame_Count(sample);
	if (sample->cursor >= static_cast<double>(frames)) sample->cursor = 0.0;
	sample->playing = true;
	sample->paused = false;
	sample->loops_remaining = sample->loop_count;
	return true;
}

void Count_Sample_Start_Locked(bool started)
{
	++g_stats.sample_start_attempts;
	if (started) ++g_stats.sample_start_successes;
	else ++g_stats.sample_start_silent;
}

void Capture_Last_Stream_Locked(const RenegadeMilesSample *sample)
{
	if (sample == nullptr) return;
	g_stats.last_stream_frames = static_cast<uint32_t>(
		std::min<size_t>(Sample_Frame_Count(sample),
			std::numeric_limits<uint32_t>::max()));
	g_stats.last_stream_fact_frames = sample->wave.fact_sample_frames;
	g_stats.last_stream_estimated_frames = sample->wave.estimated_sample_frames;
	g_stats.last_stream_untrimmed_frames = sample->wave.untrimmed_sample_frames;
	g_stats.last_stream_trimmed_frames = sample->wave.trimmed_sample_frames;
	g_stats.last_stream_rate = static_cast<uint32_t>(
		std::max<S32>(0, sample->playback_rate));
	g_stats.last_stream_volume = static_cast<uint32_t>(
		std::max<S32>(0, sample->volume));
	g_stats.last_stream_pan = static_cast<uint32_t>(
		std::max<S32>(0, sample->pan));
}

uint32_t Saturate_Size_To_U32(size_t value)
{
	return static_cast<uint32_t>(
		std::min<size_t>(value, std::numeric_limits<uint32_t>::max()));
}

uint32_t Saturate_Double_To_U32(double value)
{
	if (value <= 0.0) return 0U;
	return static_cast<uint32_t>(
		std::min<double>(value, std::numeric_limits<uint32_t>::max()));
}

uint32_t Frame_Position_To_MS(double frame, uint32_t rate)
{
	if (rate == 0U) return 0U;
	return Saturate_Double_To_U32(frame * 1000.0 / static_cast<double>(rate));
}

void Capture_Active_Stream_Locked(RenegadeMilesRuntimeStats *stats,
	const RenegadeMilesSample *sample)
{
	if (stats == nullptr || sample == nullptr) return;
	const size_t total_frames = Sample_Frame_Count(sample);
	const double cursor = std::max(0.0,
		std::min(sample->cursor, static_cast<double>(total_frames)));
	const uint32_t rate = static_cast<uint32_t>(
		std::max<S32>(0, sample->playback_rate > 0
			? sample->playback_rate : static_cast<S32>(sample->wave.sample_rate)));
	stats->active_stream_position_ms = Frame_Position_To_MS(cursor, rate);
	stats->active_stream_length_ms = Frame_Position_To_MS(
		static_cast<double>(total_frames), rate);
	stats->active_stream_cursor_frame = Saturate_Double_To_U32(cursor);
	stats->active_stream_total_frames = Saturate_Size_To_U32(total_frames);
	stats->active_stream_loop_count = sample->loops_remaining;
	stats->active_stream_volume = static_cast<uint32_t>(
		std::max<S32>(0, sample->volume));
	stats->active_stream_pan = static_cast<uint32_t>(
		std::max<S32>(0, sample->pan));
}

#if !defined(RENEGADE_MILES_MANUAL_MIX) && defined(__vita__)
void Record_Output_Stream_Submit_Locked(const RenegadeMilesMixSummary &summary)
{
	g_stats.last_output_stream_active = summary.stream_active;
	g_stats.last_output_stream_frames = summary.stream_frames;
	g_stats.last_output_stream_nonzero = summary.stream_nonzero;
	g_stats.last_output_stream_peak_abs = summary.stream_peak_abs;
	if (summary.stream_active != 0U) {
		++g_stats.output_stream_buffers_written;
		g_stats.output_stream_frames_written += summary.stream_frames;
		if (summary.stream_nonzero != 0U) {
			++g_stats.output_stream_nonzero_buffers_written;
		}
		g_stats.output_stream_peak_abs =
			std::max(g_stats.output_stream_peak_abs, summary.stream_peak_abs);
	}
}
#endif

// The per-voice loops below reproduce the original per-frame mixer exactly
// (same double cursor sequence, loop handling, float interpolation and
// truncation) with the per-frame calls, divisions and branches hoisted out.

// Reloads a voice that reached its end; returns false when it stopped.
bool Wrap_Voice(RenegadeMilesSample *sample, double &cursor, double end)
{
	sample->cursor = cursor;
	while (sample->cursor >= end) {
		if (!Advance_Loop(sample)) break;
	}
	cursor = sample->cursor;
	return sample->playing;
}

// A voice whose gains are both zero contributes exactly zero; only its cursor
// and loop state advance.
void Advance_Silent_Voice(RenegadeMilesSample *sample, size_t source_frames,
	double step, size_t frames)
{
	const double end = static_cast<double>(source_frames);
	double cursor = sample->cursor;
	for (size_t output_frame = 0; output_frame < frames; ++output_frame) {
		if (cursor >= end && !Wrap_Voice(sample, cursor, end)) return;
		cursor += step;
	}
	sample->cursor = cursor;
}

template <bool Mono, bool Stream>
void Mix_Pcm_Voice(RenegadeMilesSample *sample, const int16_t *pcm,
	size_t source_frames, size_t stride, double step, const float gains[2],
	int32_t *accumulator, int32_t *stream_accumulator, size_t frames)
{
	const double end = static_cast<double>(source_frames);
	const size_t last = source_frames - 1U;
	const float left_gain = gains[0];
	const float right_gain = gains[1];
	double cursor = sample->cursor;
	for (size_t output_frame = 0; output_frame < frames; ++output_frame) {
		if (cursor >= end && !Wrap_Voice(sample, cursor, end)) return;
		const size_t first = static_cast<size_t>(cursor);
		const size_t second = std::min(first + 1U, last);
		const float fraction = static_cast<float>(cursor - first);
		int32_t left = 0;
		int32_t right = 0;
		if (Mono) {
			const float start = pcm[first];
			const float finish = pcm[second];
			const float interpolated = start + (finish - start) * fraction;
			left = static_cast<int32_t>(interpolated * left_gain);
			right = static_cast<int32_t>(interpolated * right_gain);
		} else {
			const int16_t *a = pcm + first * stride;
			const int16_t *b = pcm + second * stride;
			const float left_start = a[0];
			const float left_finish = b[0];
			const float left_value = left_start + (left_finish - left_start) * fraction;
			left = static_cast<int32_t>(left_value * left_gain);
			const float right_start = a[1];
			const float right_finish = b[1];
			const float right_value = right_start + (right_finish - right_start) * fraction;
			right = static_cast<int32_t>(right_value * right_gain);
		}
		accumulator[output_frame * 2U] += left;
		accumulator[output_frame * 2U + 1U] += right;
		if (Stream) {
			stream_accumulator[output_frame * 2U] += left;
			stream_accumulator[output_frame * 2U + 1U] += right;
		}
		cursor += step;
	}
	sample->cursor = cursor;
}

template <bool Stream>
void Mix_Mpeg_Voice(RenegadeMilesSample *sample, size_t source_frames,
	double step, const float gains[2], int32_t *accumulator,
	int32_t *stream_accumulator, size_t frames)
{
	RenegadeVitaAudio::MpegPlayback &mpeg = *sample->mpeg;
	const double end = static_cast<double>(source_frames);
	const size_t last = source_frames - 1U;
	const uint16_t channels = sample->wave.channels;
	const uint16_t right_channel = channels == 1 ? 0U :
		std::min<uint16_t>(1U, static_cast<uint16_t>(channels - 1U));
	double cursor = sample->cursor;
	for (size_t output_frame = 0; output_frame < frames; ++output_frame) {
		if (cursor >= end && !Wrap_Voice(sample, cursor, end)) return;
		const size_t first = static_cast<size_t>(cursor);
		const size_t second = std::min(first + 1U, last);
		const float fraction = static_cast<float>(cursor - first);
		// Same decode request order as the original mixer: the playback
		// keeps a window cache whose refills depend on it.
		for (uint16_t channel = 0; channel < 2; ++channel) {
			const uint16_t source_channel = channel == 0 ? 0U : right_channel;
			const float start = mpeg.Sample(first, source_channel);
			const float finish = mpeg.Sample(second, source_channel);
			const float interpolated = start + (finish - start) * fraction;
			const int32_t contribution =
				static_cast<int32_t>(interpolated * gains[channel]);
			accumulator[output_frame * 2U + channel] += contribution;
			if (Stream) stream_accumulator[output_frame * 2U + channel] += contribution;
		}
		cursor += step;
	}
	sample->cursor = cursor;
}

// Miles/DS3D inverse-distance rolloff: unity inside minimum, held at the
// maximum-distance gain beyond it (WWAudio already edge-fades and culls).
inline float Inverse_Distance_Gain(float minimum_distance, float maximum_distance,
	float distance)
{
	const float minimum = std::max(1.0e-3F, std::min(minimum_distance, maximum_distance));
	const float maximum = std::max(minimum, maximum_distance);
	return minimum / std::max(minimum, std::min(distance, maximum));
}

void Mix_Locked(int16_t *output, size_t frames,
	RenegadeMilesMixSummary *summary = nullptr)
{
	if (frames > kOutputFrames) return;
	if (summary != nullptr) *summary = {};
	int32_t accumulator[kOutputFrames * 2U] = {};
	int32_t stream_accumulator[kOutputFrames * 2U];
	bool stream_mix_attempted = false;
	uint32_t stream_mix_peak_abs = 0U;
	for (RenegadeMilesSample *sample : g_samples) {
		if (sample == nullptr || !sample->playing || sample->paused) continue;
		const size_t source_frames = Sample_Frame_Count(sample);
		if (source_frames == 0) continue;
		const bool is_stream = sample->streaming;
		if (is_stream && !stream_mix_attempted) {
			std::fill(stream_accumulator, stream_accumulator + frames * 2U, 0);
			stream_mix_attempted = true;
		}
		const double step = static_cast<double>(
			sample->playback_rate > 0 ? sample->playback_rate :
			static_cast<S32>(sample->wave.sample_rate)) / kOutputRate;
		// Miles ignores 2D pan on 3D (spatial) samples; use center pan.
		const S32 effective_pan = sample->spatial ? 64 : sample->pan;
		const float left_pan_gain = effective_pan <= 64 ? 1.0F :
			static_cast<float>(127 - effective_pan) / 63.0F;
		const float right_pan_gain = effective_pan >= 64 ? 1.0F :
			static_cast<float>(effective_pan) / 64.0F;
		const float volume = std::max(0.0F, std::min(1.0F,
			static_cast<float>(sample->volume) / 127.0F));
		float distance_gain = 1.0F;
		if (sample->spatial) {
			const float distance = std::sqrt(
				sample->position[0] * sample->position[0] +
				sample->position[1] * sample->position[1] +
				sample->position[2] * sample->position[2]);
			distance_gain = Inverse_Distance_Gain(
				sample->minimum_distance, sample->maximum_distance, distance);
		}
		const float gains[2] = {
			volume * distance_gain * left_pan_gain,
			volume * distance_gain * right_pan_gain
		};
		if (sample->mpeg) {
			if (is_stream) {
				Mix_Mpeg_Voice<true>(sample, source_frames, step, gains,
					accumulator, stream_accumulator, frames);
			} else {
				Mix_Mpeg_Voice<false>(sample, source_frames, step, gains,
					accumulator, stream_accumulator, frames);
			}
			continue;
		}
		if (gains[0] == 0.0F && gains[1] == 0.0F) {
			Advance_Silent_Voice(sample, source_frames, step, frames);
			continue;
		}
		const int16_t *pcm = sample->pcm->wave.samples.data();
		const size_t stride = sample->wave.channels;
		if (stride == 1U) {
			if (is_stream) {
				Mix_Pcm_Voice<true, true>(sample, pcm, source_frames, stride, step,
					gains, accumulator, stream_accumulator, frames);
			} else {
				Mix_Pcm_Voice<true, false>(sample, pcm, source_frames, stride, step,
					gains, accumulator, stream_accumulator, frames);
			}
		} else if (is_stream) {
			Mix_Pcm_Voice<false, true>(sample, pcm, source_frames, stride, step,
				gains, accumulator, stream_accumulator, frames);
		} else {
			Mix_Pcm_Voice<false, false>(sample, pcm, source_frames, stride, step,
				gains, accumulator, stream_accumulator, frames);
		}
	}
	uint32_t mixed_peak_abs = 0U;
	bool mixed_nonzero = false;
	for (size_t index = 0; index < frames * 2U; ++index) {
		const int32_t clamped = std::max<int32_t>(-32768,
			std::min<int32_t>(32767, accumulator[index]));
		const uint32_t magnitude = static_cast<uint32_t>(
			clamped < 0 ? -clamped : clamped);
		mixed_peak_abs = std::max(mixed_peak_abs, magnitude);
		mixed_nonzero = mixed_nonzero || magnitude != 0U;
		output[index] = static_cast<int16_t>(clamped);
	}
	g_stats.mixed_peak_abs = std::max(g_stats.mixed_peak_abs, mixed_peak_abs);
	++g_stats.mixed_buffers;
	g_stats.mixed_frames += frames;
	if (mixed_nonzero) ++g_stats.mixed_nonzero_buffers;
	if (stream_mix_attempted) {
		++g_stats.stream_mixed_buffers;
		g_stats.stream_mixed_frames += frames;
		bool stream_nonzero = false;
		for (size_t index = 0; index < frames * 2U; ++index) {
			const int32_t clamped = std::max<int32_t>(-32768,
				std::min<int32_t>(32767, stream_accumulator[index]));
			const uint32_t magnitude = static_cast<uint32_t>(
				clamped < 0 ? -clamped : clamped);
			if (magnitude != 0U) {
				stream_nonzero = true;
				stream_mix_peak_abs =
					std::max(stream_mix_peak_abs, magnitude);
				g_stats.stream_mixed_peak_abs =
					std::max(g_stats.stream_mixed_peak_abs, magnitude);
			}
		}
		if (stream_nonzero) ++g_stats.stream_mixed_nonzero_buffers;
		g_stats.last_stream_mix_active = 1U;
		g_stats.last_stream_mix_frames = Saturate_Size_To_U32(frames);
		g_stats.last_stream_mix_nonzero = stream_nonzero ? 1U : 0U;
		g_stats.last_stream_mix_peak_abs = stream_mix_peak_abs;
		if (summary != nullptr) {
			summary->stream_active = 1U;
			summary->stream_frames = Saturate_Size_To_U32(frames);
			summary->stream_nonzero = stream_nonzero ? 1U : 0U;
			summary->stream_peak_abs = stream_mix_peak_abs;
		}
	} else {
		g_stats.last_stream_mix_active = 0U;
		g_stats.last_stream_mix_frames = 0U;
		g_stats.last_stream_mix_nonzero = 0U;
		g_stats.last_stream_mix_peak_abs = 0U;
	}
}

#if !defined(RENEGADE_MILES_MANUAL_MIX)
void *Output_Thread(void *)
{
#if defined(__vita__)
	// The game thread owns user core 0; mixing runs beside it on core 1.
	(void)sceKernelChangeThreadCpuAffinityMask(SCE_KERNEL_THREAD_ID_SELF,
		SCE_KERNEL_CPU_MASK_USER_1);
#endif
	RenegadeAudioOutputBuffers<kOutputFrames * 2U> buffers;
	for (;;) {
		RenegadeMilesMixSummary mix_summary = {};
		if (g_output_stop.load(std::memory_order_acquire)) break;
		auto &output = buffers.Next();
		if (pthread_mutex_trylock(&g_mutex) != 0) {
			// The hardware deadline still needs a buffer while the game thread is
			// preparing a stream under the legacy recursive Miles lock. Silence is
			// deterministic and prevents the previous hardware buffer from repeating.
			std::fill(output.begin(), output.end(), 0);
			g_output_lock_starvation_buffers.fetch_add(1U, std::memory_order_relaxed);
		} else {
			Mix_Locked(output.data(), kOutputFrames, &mix_summary);
			pthread_mutex_unlock(&g_mutex);
		}
#if defined(__vita__)
		if (g_audio_port >= 0) {
			const int result = sceAudioOutOutput(g_audio_port, output.data());
			if (pthread_mutex_trylock(&g_mutex) == 0) {
				if (result < 0) {
					Set_Error("sceAudioOutOutput failed");
					++g_stats.output_write_failures;
				} else {
					++g_stats.output_buffers_written;
					Record_Output_Stream_Submit_Locked(mix_summary);
				}
				pthread_mutex_unlock(&g_mutex);
			}
		}
#else
		struct timespec duration = { 0, 21333333L };
		nanosleep(&duration, nullptr);
#endif
	}
	// The final native pointer must remain valid until playback has drained.
#if defined(__vita__)
	if (g_audio_port >= 0) sceAudioOutOutput(g_audio_port, nullptr);
#endif
	return nullptr;
}
#endif

bool Start_Output()
{
#if defined(RENEGADE_MILES_MANUAL_MIX)
	++g_stats.output_start_attempts;
	++g_stats.output_start_successes;
	return true;
#else
	if (g_output_thread_running) return true;
	++g_stats.output_start_attempts;
#if defined(__vita__)
	g_audio_port = sceAudioOutOpenPort(SCE_AUDIO_OUT_PORT_TYPE_BGM,
		static_cast<int>(kOutputFrames), kOutputRate, SCE_AUDIO_OUT_MODE_STEREO);
	if (g_audio_port < 0) {
		Set_Error("sceAudioOutOpenPort failed");
		++g_stats.output_start_failures;
		return false;
	}
#endif
	g_output_stop.store(false, std::memory_order_release);
	if (pthread_create(&g_output_thread, nullptr, Output_Thread, nullptr) != 0) {
		Set_Error("audio output thread creation failed");
		++g_stats.output_start_failures;
#if defined(__vita__)
		sceAudioOutReleasePort(g_audio_port);
		g_audio_port = -1;
#endif
		return false;
	}
	g_output_thread_running = true;
	++g_stats.output_start_successes;
	return true;
#endif
}

void Stop_Output()
{
#if !defined(RENEGADE_MILES_MANUAL_MIX)
	if (g_output_thread_running) {
		g_output_stop.store(true, std::memory_order_release);
		pthread_join(g_output_thread, nullptr);
		g_output_thread_running = false;
	}
#if defined(__vita__)
	if (g_audio_port >= 0) {
		sceAudioOutOutput(g_audio_port, nullptr);
		sceAudioOutReleasePort(g_audio_port);
		g_audio_port = -1;
	}
#endif
#endif
}

RenegadeMilesSample *Allocate_Sample()
{
	RenegadeMilesSample *sample = new (std::nothrow) RenegadeMilesSample;
	if (sample == nullptr) {
		Set_Error("sample allocation failed");
	} else if (!g_samples.push_back(sample)) {
		delete sample;
		sample = nullptr;
		Set_Error("sample registry allocation failed");
	}
	return sample;
}

void Release_Sample(RenegadeMilesSample *sample)
{
	if (sample == nullptr) return;
	auto entry = std::find(g_samples.begin(), g_samples.end(), sample);
	if (entry != g_samples.end()) g_samples.erase(entry);
	delete sample;
}

bool Read_Stream_Image(const char *name, AIL_FILE_OPEN_CALLBACK file_open,
	AIL_FILE_CLOSE_CALLBACK file_close, AIL_FILE_SEEK_CALLBACK file_seek,
	AIL_FILE_READ_CALLBACK file_read, std::unique_ptr<uint8_t[]> *image,
	size_t *image_bytes, const char **error)
{
	if (name == nullptr || image == nullptr || image_bytes == nullptr || file_open == nullptr ||
		file_close == nullptr || file_seek == nullptr || file_read == nullptr) {
		if (error != nullptr) *error = "stream file callbacks are unavailable";
		return false;
	}
	AIL_FILE_HANDLE handle = 0;
	if (file_open(name, &handle) == 0U) {
		if (error != nullptr) *error = "stream source open failed";
		return false;
	}
	const S32 file_size = file_seek(handle, 0, AIL_FILE_SEEK_END);
	if (file_size <= 0 || static_cast<size_t>(file_size) > kMaximumWaveBytes ||
		file_seek(handle, 0, AIL_FILE_SEEK_BEGIN) < 0) {
		file_close(handle);
		if (error != nullptr) *error = "stream source size is invalid";
		return false;
	}
	std::unique_ptr<uint8_t[]> pending(new (std::nothrow) uint8_t[static_cast<size_t>(file_size)]);
	if (!pending) {
		file_close(handle);
		if (error != nullptr) *error = "stream image allocation failed";
		return false;
	}
	const U32 read = file_read(handle, pending.get(), static_cast<U32>(file_size));
	file_close(handle);
	if (read != static_cast<U32>(file_size)) {
		if (error != nullptr) *error = "stream source read was incomplete";
		return false;
	}
	*image = std::move(pending);
	*image_bytes = static_cast<size_t>(file_size);
	return true;
}

RenegadeMilesSample *Stream_Sample(HSTREAM stream)
{
	return stream != nullptr ? stream->sample : nullptr;
}

} // namespace

RenegadeMilesSample::~RenegadeMilesSample()
{
	Release_Pcm(pcm);
}

void AIL_startup(void)
{
	Ensure_Mutex();
}

void AIL_shutdown(void)
{
	AIL_lock();
	Stop_Output();
	for (RenegadeMilesSample *sample : g_samples) delete sample;
	g_samples.clear();
	Clear_Pcm_Cache();
	AIL_unlock();
}

void AIL_lock(void)
{
	Ensure_Mutex();
	pthread_mutex_lock(&g_mutex);
}

void AIL_unlock(void)
{
	pthread_mutex_unlock(&g_mutex);
}

char *AIL_last_error(void)
{
	return g_last_error;
}

S32 AIL_set_preference(S32, S32)
{
	return AIL_NO_ERROR;
}

S32 AIL_waveOutOpen(HDIGDRIVER *driver, void *, U32, LPWAVEFORMAT format)
{
	AIL_lock();
	if (driver == nullptr || format == nullptr || format->nChannels == 0 ||
		format->nSamplesPerSec == 0) {
		Set_Error("invalid output format");
		AIL_unlock();
		return 1;
	}
	g_driver.emulated_ds = 0;
	*driver = &g_driver;
	const bool started = Start_Output();
	AIL_unlock();
	return started ? AIL_NO_ERROR : 1;
}

void AIL_waveOutClose(HDIGDRIVER)
{
	AIL_lock();
	Stop_Output();
	AIL_unlock();
}

HSAMPLE AIL_allocate_sample_handle(HDIGDRIVER)
{
	AIL_lock();
	RenegadeMilesSample *sample = Allocate_Sample();
	AIL_unlock();
	return sample;
}

void AIL_release_sample_handle(HSAMPLE sample)
{
	AIL_lock();
	Release_Sample(sample);
	AIL_unlock();
}

void AIL_init_sample(HSAMPLE sample)
{
	AIL_lock();
	Reset_Sample(sample);
	AIL_unlock();
}

S32 AIL_set_named_sample_file(HSAMPLE sample, char *, const void *data,
	U32 bytes, S32)
{
	AIL_lock();
	++g_stats.sample_file_load_attempts;
	const bool decoded = Decode_Into_Sample(sample, data, bytes);
	if (decoded) ++g_stats.sample_file_load_successes;
	else ++g_stats.sample_file_load_failures;
	AIL_unlock();
	return decoded ? 1 : 0;
}

void AIL_start_sample(HSAMPLE sample)
{
	AIL_lock();
	Count_Sample_Start_Locked(Start_Sample_Locked(sample));
	AIL_unlock();
}

void AIL_stop_sample(HSAMPLE sample)
{
	AIL_lock();
	if (sample != nullptr) {
		sample->playing = false;
		sample->paused = true;
	}
	AIL_unlock();
}

void AIL_resume_sample(HSAMPLE sample)
{
	AIL_lock();
	if (sample != nullptr && Sample_Frame_Count(sample) != 0) {
		sample->playing = true;
		sample->paused = false;
	}
	AIL_unlock();
}

void AIL_end_sample(HSAMPLE sample)
{
	AIL_lock();
	if (sample != nullptr) {
		sample->playing = false;
		sample->paused = false;
		sample->cursor = 0.0;
	}
	AIL_unlock();
}

void AIL_set_sample_pan(HSAMPLE sample, S32 pan)
{
	AIL_lock();
	if (sample != nullptr) sample->pan = std::max<S32>(0, std::min<S32>(127, pan));
	AIL_unlock();
}

S32 AIL_sample_pan(HSAMPLE sample)
{
	AIL_lock();
	const S32 value = sample != nullptr ? sample->pan : 64;
	AIL_unlock();
	return value;
}

void AIL_set_sample_volume(HSAMPLE sample, S32 volume)
{
	AIL_lock();
	if (sample != nullptr) sample->volume = std::max<S32>(0, std::min<S32>(127, volume));
	AIL_unlock();
}

S32 AIL_sample_volume(HSAMPLE sample)
{
	AIL_lock();
	const S32 value = sample != nullptr ? sample->volume : 0;
	AIL_unlock();
	return value;
}

void AIL_set_sample_loop_count(HSAMPLE sample, U32 count)
{
	AIL_lock();
	if (sample != nullptr) {
		sample->loop_count = count;
		sample->loops_remaining = count;
	}
	AIL_unlock();
}

U32 AIL_sample_loop_count(HSAMPLE sample)
{
	AIL_lock();
	const U32 value = sample != nullptr ? sample->loops_remaining : 0U;
	AIL_unlock();
	return value;
}

void AIL_set_sample_ms_position(HSAMPLE sample, U32 milliseconds)
{
	AIL_lock();
	if (sample != nullptr && sample->wave.sample_rate != 0) {
		sample->cursor = std::min<double>(Sample_Frame_Count(sample),
			static_cast<double>(milliseconds) * sample->wave.sample_rate / 1000.0);
	}
	AIL_unlock();
}

void AIL_sample_ms_position(HSAMPLE sample, S32 *length, S32 *position)
{
	AIL_lock();
	if (sample != nullptr && sample->wave.sample_rate != 0) {
		if (length != nullptr) *length = static_cast<S32>(std::min<uint64_t>(
			std::numeric_limits<S32>::max(),
			static_cast<uint64_t>(Sample_Frame_Count(sample)) * 1000U /
				sample->wave.sample_rate));
		if (position != nullptr) *position = static_cast<S32>(
			sample->cursor * 1000.0 / sample->wave.sample_rate);
	} else {
		if (length != nullptr) *length = 0;
		if (position != nullptr) *position = 0;
	}
	AIL_unlock();
}

void AIL_set_sample_user_data(HSAMPLE sample, S32 index, AIL_USER_DATA value)
{
	AIL_lock();
	if (sample != nullptr && index >= 0 && index < 8) sample->user_data[index] = value;
	AIL_unlock();
}

AIL_USER_DATA AIL_sample_user_data(HSAMPLE sample, S32 index)
{
	AIL_lock();
	const AIL_USER_DATA value = sample != nullptr && index >= 0 && index < 8
		? sample->user_data[index] : 0U;
	AIL_unlock();
	return value;
}

S32 AIL_sample_playback_rate(HSAMPLE sample)
{
	AIL_lock();
	const S32 value = sample != nullptr ? sample->playback_rate : 0;
	AIL_unlock();
	return value;
}

void AIL_set_sample_playback_rate(HSAMPLE sample, S32 rate)
{
	AIL_lock();
	if (sample != nullptr && rate > 0) sample->playback_rate = rate;
	AIL_unlock();
}

S32 AIL_enumerate_3D_providers(HPROENUM *next, HPROVIDER *provider, char **name)
{
	static char native_name[] = "Vita Native Stereo";
	if (next == nullptr || provider == nullptr || name == nullptr || *next != HPROENUM_FIRST) {
		return 0;
	}
	*provider = kNative3DProvider;
	*name = native_name;
	*next = 1;
	return 1;
}

S32 AIL_open_3D_provider(HPROVIDER provider)
{
	return provider == kNative3DProvider ? M3D_NOERR : 1;
}

void AIL_close_3D_provider(HPROVIDER)
{
}

H3DPOBJECT AIL_3D_open_listener(HPROVIDER)
{
	return &g_listener;
}

void AIL_set_3D_speaker_type(HPROVIDER, S32)
{
}

H3DSAMPLE AIL_allocate_3D_sample_handle(HPROVIDER)
{
	H3DSAMPLE sample = AIL_allocate_sample_handle(&g_driver);
	AIL_lock();
	if (sample != nullptr) sample->spatial = true;
	AIL_unlock();
	return sample;
}

void AIL_release_3D_sample_handle(H3DSAMPLE sample)
{
	AIL_release_sample_handle(sample);
}

U32 AIL_set_3D_sample_file(H3DSAMPLE sample, const void *data)
{
	return AIL_set_3D_sample_file_bounded(sample, data, Declared_Wave_Bytes(data));
}

U32 AIL_set_3D_sample_file_bounded(H3DSAMPLE sample, const void *data, size_t bytes)
{
	AIL_lock();
	++g_stats.sample_3d_file_load_attempts;
	const bool decoded = bytes != 0 && Decode_Into_Sample(sample, data, bytes);
	if (decoded) ++g_stats.sample_3d_file_load_successes;
	else ++g_stats.sample_3d_file_load_failures;
	AIL_unlock();
	return decoded ? 1U : 0U;
}

void AIL_start_3D_sample(H3DSAMPLE sample) { AIL_start_sample(sample); }
void AIL_stop_3D_sample(H3DSAMPLE sample) { AIL_stop_sample(sample); }
void AIL_resume_3D_sample(H3DSAMPLE sample) { AIL_resume_sample(sample); }
void AIL_end_3D_sample(H3DSAMPLE sample) { AIL_end_sample(sample); }
void AIL_set_3D_sample_volume(H3DSAMPLE sample, S32 volume) { AIL_set_sample_volume(sample, volume); }
S32 AIL_3D_sample_volume(H3DSAMPLE sample) { return AIL_sample_volume(sample); }
void AIL_set_3D_sample_loop_count(H3DSAMPLE sample, U32 count) { AIL_set_sample_loop_count(sample, count); }
U32 AIL_3D_sample_loop_count(H3DSAMPLE sample) { return AIL_sample_loop_count(sample); }

void AIL_set_3D_sample_offset(H3DSAMPLE sample, U32 bytes)
{
	AIL_lock();
	if (sample != nullptr && sample->encoded_data_bytes != 0U) {
		const double fraction = std::min<double>(1.0,
			static_cast<double>(bytes) / sample->encoded_data_bytes);
		sample->cursor = fraction * Sample_Frame_Count(sample);
	}
	AIL_unlock();
}

U32 AIL_3D_sample_offset(H3DSAMPLE sample)
{
	AIL_lock();
	const U32 value = sample != nullptr && Sample_Frame_Count(sample) != 0U
		? static_cast<U32>(std::min<double>(sample->encoded_data_bytes,
			sample->cursor * sample->encoded_data_bytes / Sample_Frame_Count(sample)))
		: 0U;
	AIL_unlock();
	return value;
}

U32 AIL_3D_sample_length(H3DSAMPLE sample)
{
	AIL_lock();
	const U32 value = sample != nullptr ? sample->encoded_data_bytes : 0U;
	AIL_unlock();
	return value;
}

void AIL_set_3D_object_user_data(H3DSAMPLE sample, S32 index, AIL_USER_DATA value) { AIL_set_sample_user_data(sample, index, value); }
AIL_USER_DATA AIL_3D_object_user_data(H3DSAMPLE sample, S32 index) { return AIL_sample_user_data(sample, index); }
S32 AIL_3D_sample_playback_rate(H3DSAMPLE sample) { return AIL_sample_playback_rate(sample); }
void AIL_set_3D_sample_playback_rate(H3DSAMPLE sample, S32 rate) { AIL_set_sample_playback_rate(sample, rate); }

void AIL_set_3D_position(H3DSAMPLE sample, F32 x, F32 y, F32 z)
{
	AIL_lock();
	if (sample != nullptr) {
		sample->position[0] = x;
		sample->position[1] = y;
		sample->position[2] = z;
		const F32 scale = std::max(1.0F, sample->maximum_distance);
		const F32 normalized = std::max(-1.0F, std::min(1.0F, x / scale));
		sample->pan = static_cast<S32>(std::lround((normalized + 1.0F) * 63.5F));
	}
	AIL_unlock();
}

void AIL_set_3D_orientation(H3DSAMPLE, F32, F32, F32, F32, F32, F32) {}
void AIL_set_3D_velocity_vector(H3DSAMPLE, F32, F32, F32) {}

void AIL_set_3D_sample_distances(H3DSAMPLE sample, F32 maximum, F32 minimum)
{
	AIL_lock();
	if (sample != nullptr) {
		sample->maximum_distance = std::max(0.0F, maximum);
		sample->minimum_distance = std::max(0.0F,
			std::min(minimum, sample->maximum_distance));
	}
	AIL_unlock();
}

void AIL_set_3D_sample_effects_level(H3DSAMPLE, F32) {}

HSTREAM AIL_open_stream_by_sample(HDIGDRIVER, HSAMPLE sample,
	const char *name, S32)
{
	AIL_FILE_OPEN_CALLBACK file_open = nullptr;
	AIL_FILE_CLOSE_CALLBACK file_close = nullptr;
	AIL_FILE_SEEK_CALLBACK file_seek = nullptr;
	AIL_FILE_READ_CALLBACK file_read = nullptr;
	AIL_lock();
	++g_stats.stream_open_attempts;
	std::snprintf(g_stats.last_stream_name, sizeof(g_stats.last_stream_name), "%s",
		name != nullptr ? name : "");
	file_open = g_file_open;
	file_close = g_file_close;
	file_seek = g_file_seek;
	file_read = g_file_read;
	// Stream handles are pooled by WWAudio. Detach the preceding stream before
	// the blocking file callbacks so the mixer cannot observe or replay it and
	// repeated playback does not retain two complete sources.
	Reset_Sample(sample);
	AIL_unlock();

	std::unique_ptr<uint8_t[]> image;
	size_t image_bytes = 0U;
	const char *read_error = sample != nullptr ? nullptr : "invalid stream sample";
	const bool image_loaded = sample != nullptr && Read_Stream_Image(name,
		file_open, file_close, file_seek, file_read, &image, &image_bytes,
		&read_error);
	RenegadeMilesPreparedSource prepared;
	const bool source_prepared = image_loaded && Prepare_Stream_Source(
		image.get(), image_bytes, &prepared);

	AIL_lock();
	RenegadeMilesStream *stream = nullptr;
	if (!image_loaded) {
		Set_Error(read_error);
	} else {
		g_stats.stream_bytes_read += image_bytes;
		if (!source_prepared) Set_Error(prepared.error);
	}
	if (source_prepared && Publish_Stream_Source_Locked(sample, &prepared)) {
		stream = new (std::nothrow) RenegadeMilesStream;
		if (stream != nullptr) {
			stream->sample = sample;
			sample->streaming = true;
			g_stats.stream_decoded_frames += Sample_Frame_Count(sample);
			Capture_Last_Stream_Locked(sample);
		}
	}
	if (stream != nullptr) ++g_stats.stream_open_successes;
	else ++g_stats.stream_open_failures;
	AIL_unlock();
	return stream;
}

HSTREAM AIL_open_stream(HDIGDRIVER driver, const char *name, S32 stream_mem)
{
	HSAMPLE sample = AIL_allocate_sample_handle(driver);
	HSTREAM stream = AIL_open_stream_by_sample(driver, sample, name, stream_mem);
	if (stream != nullptr) stream->owns_sample = true;
	else AIL_release_sample_handle(sample);
	return stream;
}

void AIL_close_stream(HSTREAM stream)
{
	if (stream == nullptr) return;
	AIL_lock();
	AIL_end_sample(stream->sample);
	if (stream->owns_sample) {
		Release_Sample(stream->sample);
	} else {
		// Borrowed 2D samples outlive the stream. Drop MPEG storage now; the next
		// open has no use for the previous file image or decoder state.
		Reset_Sample(stream->sample);
	}
	delete stream;
	AIL_unlock();
}

void AIL_start_stream(HSTREAM stream)
{
	AIL_lock();
	++g_stats.stream_start_attempts;
	RenegadeMilesSample *sample = Stream_Sample(stream);
	if (sample != nullptr) {
		Capture_Last_Stream_Locked(sample);
	}
	const bool started = Start_Sample_Locked(sample);
	Count_Sample_Start_Locked(started);
	if (started) {
		++g_stats.stream_start_successes;
		if (sample->volume <= 0) ++g_stats.stream_start_zero_volume;
	} else {
		++g_stats.stream_start_silent;
	}
	AIL_unlock();
}

void AIL_pause_stream(HSTREAM stream, S32 pause)
{
	if (pause != 0) AIL_stop_sample(Stream_Sample(stream));
	else AIL_resume_sample(Stream_Sample(stream));
}

void AIL_set_stream_pan(HSTREAM stream, S32 pan) { AIL_set_sample_pan(Stream_Sample(stream), pan); }
S32 AIL_stream_pan(HSTREAM stream) { return AIL_sample_pan(Stream_Sample(stream)); }
void AIL_set_stream_volume(HSTREAM stream, S32 volume) { AIL_set_sample_volume(Stream_Sample(stream), volume); }
S32 AIL_stream_volume(HSTREAM stream) { return AIL_sample_volume(Stream_Sample(stream)); }
void AIL_set_stream_loop_block(HSTREAM, S32, S32) {}
void AIL_set_stream_loop_count(HSTREAM stream, U32 count) { AIL_set_sample_loop_count(Stream_Sample(stream), count); }
U32 AIL_stream_loop_count(HSTREAM stream) { return AIL_sample_loop_count(Stream_Sample(stream)); }
void AIL_set_stream_ms_position(HSTREAM stream, U32 milliseconds) { AIL_set_sample_ms_position(Stream_Sample(stream), milliseconds); }
void AIL_stream_ms_position(HSTREAM stream, S32 *length, S32 *position) { AIL_sample_ms_position(Stream_Sample(stream), length, position); }
S32 AIL_stream_playback_rate(HSTREAM stream) { return AIL_sample_playback_rate(Stream_Sample(stream)); }
void AIL_set_stream_playback_rate(HSTREAM stream, S32 rate) { AIL_set_sample_playback_rate(Stream_Sample(stream), rate); }

S32 AIL_WAV_info_bounded(const void *data, size_t bytes, AILSOUNDINFO *info)
{
	if (data == nullptr || info == nullptr || bytes < 12U ||
		bytes > kMaximumWaveBytes) return 0;
	WaveInfo wave;
	const char *error = nullptr;
	if (!RenegadeVitaAudio::Inspect_Wave(
		static_cast<const uint8_t *>(data), bytes, &wave, &error, true, true)) {
		Set_Error(error);
		return 0;
	}
	std::memset(info, 0, sizeof(*info));
	info->format = static_cast<S32>(wave.encoding);
	info->data_ptr = static_cast<const uint8_t *>(data) + wave.data_offset;
	info->data_len = wave.data_bytes;
	info->rate = wave.sample_rate;
	info->bits = wave.bits_per_sample;
	info->channels = wave.channels;
	info->samples = wave.sample_frames;
	info->block_size = wave.block_align;
	info->initial_ptr = data;
	return 1;
}

S32 AIL_WAV_info(const void *data, AILSOUNDINFO *info)
{
	const size_t bytes = Declared_Wave_Bytes(data);
	return bytes != 0 ? AIL_WAV_info_bounded(data, bytes, info) : 0;
}

S32 AIL_enumerate_filters(HPROENUM *, HPROVIDER *, char **) { return 0; }
void AIL_set_sample_processor(HSAMPLE, S32, HPROVIDER) {}
S32 AIL_set_filter_sample_preference(HSAMPLE, const char *, const void *) { return 0; }

void AIL_set_file_callbacks(AIL_FILE_OPEN_CALLBACK open_callback,
	AIL_FILE_CLOSE_CALLBACK close_callback, AIL_FILE_SEEK_CALLBACK seek_callback,
	AIL_FILE_READ_CALLBACK read_callback)
{
	AIL_lock();
	g_file_open = open_callback;
	g_file_close = close_callback;
	g_file_seek = seek_callback;
	g_file_read = read_callback;
	AIL_unlock();
}

void AIL_stop_timer(HTIMER) {}
void AIL_release_timer_handle(HTIMER) {}

bool Renegade_Miles_Mix_For_Test(int16_t *stereo_output, size_t frames)
{
	if (stereo_output == nullptr || frames == 0 || frames > kOutputFrames) return false;
	AIL_lock();
	Mix_Locked(stereo_output, frames);
	AIL_unlock();
	return true;
}

void Renegade_Miles_Reset_Runtime_Stats()
{
	AIL_lock();
	g_stats = {};
	g_pcm_live_high_water_bytes = g_pcm_live_bytes;
	g_output_lock_starvation_buffers.store(0U, std::memory_order_relaxed);
	std::snprintf(g_stats.last_error, sizeof(g_stats.last_error), "%s",
		g_last_error);
	AIL_unlock();
}

void Renegade_Miles_Get_Runtime_Stats(RenegadeMilesRuntimeStats *stats)
{
	if (stats == nullptr) return;
	AIL_lock();
	*stats = g_stats;
	stats->output_lock_starvation_buffers =
		g_output_lock_starvation_buffers.load(std::memory_order_relaxed);
	stats->allocated_samples = static_cast<uint32_t>(g_samples.size());
	stats->pcm_cache_entries = 0U;
	for (const RenegadeMilesPcm *pcm : g_pcm_cache) {
		if (pcm != nullptr) ++stats->pcm_cache_entries;
	}
	stats->pcm_cache_bytes = Saturate_Size_To_U32(g_pcm_cache_bytes);
	stats->pcm_live_bytes = Saturate_Size_To_U32(g_pcm_live_bytes);
	stats->pcm_live_high_water_bytes =
		Saturate_Size_To_U32(g_pcm_live_high_water_bytes);
	stats->pcm_largest_image_bytes =
		Saturate_Size_To_U32(g_pcm_largest_image_bytes);
	stats->active_samples = 0U;
	stats->active_streams = 0U;
	stats->active_stream_position_ms = 0U;
	stats->active_stream_length_ms = 0U;
	stats->active_stream_cursor_frame = 0U;
	stats->active_stream_total_frames = 0U;
	stats->active_stream_loop_count = 0U;
	stats->active_stream_volume = 0U;
	stats->active_stream_pan = 0U;
	bool captured_active_stream = false;
	for (RenegadeMilesSample *sample : g_samples) {
		if (sample != nullptr && sample->playing && !sample->paused) {
			++stats->active_samples;
			if (sample->streaming) {
				++stats->active_streams;
				if (!captured_active_stream) {
					Capture_Active_Stream_Locked(stats, sample);
					captured_active_stream = true;
				}
			}
		}
	}
	std::snprintf(stats->last_error, sizeof(stats->last_error), "%s",
		g_last_error);
	AIL_unlock();
}
