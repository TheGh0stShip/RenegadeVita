#include "mss.h"

#include "renegade_miles_runtime_stats.h"
#include "renegade_miles_test.h"
#include "renegade_wave_decoder.h"

#include <algorithm>
#include <atomic>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <limits>
#include <new>
#include <pthread.h>
#include <time.h>
#include <vector>

#if defined(__vita__)
#include <psp2/audioout.h>
#endif

using RenegadeVitaAudio::DecodedWave;
using RenegadeVitaAudio::WaveInfo;

struct RenegadeMilesSample {
	DecodedWave wave;
	U32 encoded_data_bytes = 0;
	double cursor = 0.0;
	S32 playback_rate = 0;
	S32 volume = 127;
	S32 pan = 64;
	U32 loop_count = 1;
	U32 loops_remaining = 1;
	U32 user_data[8] = {};
	F32 position[3] = {};
	F32 maximum_distance = 100.0F;
	F32 minimum_distance = 1.0F;
	bool spatial = false;
	bool streaming = false;
	bool playing = false;
	bool paused = false;
};

struct RenegadeMilesStream {
	RenegadeMilesSample *sample = nullptr;
	bool owns_sample = false;
};

namespace {

constexpr size_t kOutputFrames = 1024U;
constexpr S32 kOutputRate = 48000;
constexpr size_t kMaximumWaveBytes = 64U * 1024U * 1024U;
constexpr HPROVIDER kNative3DProvider = 1U;

pthread_once_t g_mutex_once = PTHREAD_ONCE_INIT;
pthread_mutex_t g_mutex;
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
std::vector<RenegadeMilesSample *> g_samples;
char g_last_error[160] = "no error";
RenegadeMilesRuntimeStats g_stats = {};
AIL_FILE_OPEN_CALLBACK g_file_open = nullptr;
AIL_FILE_CLOSE_CALLBACK g_file_close = nullptr;
AIL_FILE_SEEK_CALLBACK g_file_seek = nullptr;
AIL_FILE_READ_CALLBACK g_file_read = nullptr;

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

bool Decode_Into_Sample(RenegadeMilesSample *sample, const void *data,
	size_t bytes)
{
	if (sample == nullptr || data == nullptr || bytes < 12U ||
		bytes > kMaximumWaveBytes) {
		Set_Error("invalid or oversized WAVE image");
		return false;
	}
	DecodedWave decoded;
	WaveInfo info;
	const char *error = nullptr;
	if (!RenegadeVitaAudio::Inspect_Wave(
		static_cast<const uint8_t *>(data), bytes, &info, &error)) {
		Set_Error(error);
		return false;
	}
	if (!RenegadeVitaAudio::Decode_Wave(
		static_cast<const uint8_t *>(data), bytes, &decoded, &error)) {
		Set_Error(error);
		return false;
	}
	sample->wave = std::move(decoded);
	sample->encoded_data_bytes = info.data_bytes;
	sample->cursor = 0.0;
	sample->playback_rate = static_cast<S32>(sample->wave.sample_rate);
	sample->playing = false;
	sample->paused = false;
	return true;
}

void Reset_Sample(RenegadeMilesSample *sample)
{
	if (sample == nullptr) return;
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

int16_t Source_Sample(const RenegadeMilesSample *sample, size_t frame,
	uint16_t output_channel)
{
	const size_t frames = sample->wave.Frame_Count();
	if (frames == 0) return 0;
	frame = std::min(frame, frames - 1U);
	const uint16_t source_channel = sample->wave.channels == 1
		? 0 : std::min<uint16_t>(output_channel, sample->wave.channels - 1U);
	return sample->wave.samples[frame * sample->wave.channels + source_channel];
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
	sample->playing = false;
	sample->paused = false;
	return false;
}

bool Start_Sample_Locked(RenegadeMilesSample *sample)
{
	if (sample == nullptr || sample->wave.Frame_Count() == 0) return false;
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

void Mix_Locked(int16_t *output, size_t frames)
{
	if (frames > kOutputFrames) return;
	std::fill(output, output + frames * 2U, 0);
	int32_t accumulator[kOutputFrames * 2U] = {};
	int32_t stream_accumulator[kOutputFrames * 2U] = {};
	bool stream_mix_attempted = false;
	for (RenegadeMilesSample *sample : g_samples) {
		if (sample == nullptr || !sample->playing || sample->paused ||
			sample->wave.Frame_Count() == 0) continue;
		const bool is_stream = sample->streaming;
		if (is_stream) stream_mix_attempted = true;
		const double step = static_cast<double>(
			sample->playback_rate > 0 ? sample->playback_rate :
			static_cast<S32>(sample->wave.sample_rate)) / kOutputRate;
		const float left_pan_gain = sample->pan <= 64 ? 1.0F :
			static_cast<float>(127 - sample->pan) / 63.0F;
		const float right_pan_gain = sample->pan >= 64 ? 1.0F :
			static_cast<float>(sample->pan) / 64.0F;
		const float volume = std::max(0.0F, std::min(1.0F,
			static_cast<float>(sample->volume) / 127.0F));
		float distance_gain = 1.0F;
		if (sample->spatial) {
			const float distance = std::sqrt(
				sample->position[0] * sample->position[0] +
				sample->position[1] * sample->position[1] +
				sample->position[2] * sample->position[2]);
			const float minimum = std::max(0.0F, std::min(
				sample->minimum_distance, sample->maximum_distance));
			const float maximum = std::max(minimum, sample->maximum_distance);
			if (distance >= maximum) distance_gain = 0.0F;
			else if (distance > minimum && maximum > minimum) {
				distance_gain = (maximum - distance) / (maximum - minimum);
			}
		}
		const float gains[2] = {
			volume * distance_gain * left_pan_gain,
			volume * distance_gain * right_pan_gain
		};
		for (size_t output_frame = 0; output_frame < frames; ++output_frame) {
			const size_t source_frames = sample->wave.Frame_Count();
			while (sample->cursor >= source_frames) {
				if (!Advance_Loop(sample)) break;
			}
			if (!sample->playing) break;
			const size_t first = static_cast<size_t>(sample->cursor);
			const size_t second = std::min(first + 1U, source_frames - 1U);
			const float fraction = static_cast<float>(sample->cursor - first);
			for (uint16_t channel = 0; channel < 2; ++channel) {
				const float start = Source_Sample(sample, first, channel);
				const float end = Source_Sample(sample, second, channel);
				const float interpolated = start + (end - start) * fraction;
				const int32_t contribution =
					static_cast<int32_t>(interpolated * gains[channel]);
				accumulator[output_frame * 2U + channel] += contribution;
				if (is_stream) {
					stream_accumulator[output_frame * 2U + channel] += contribution;
				}
			}
			sample->cursor += step;
		}
	}
	for (size_t index = 0; index < frames * 2U; ++index) {
		const int32_t clamped = std::max<int32_t>(-32768,
			std::min<int32_t>(32767, accumulator[index]));
		const uint32_t magnitude = static_cast<uint32_t>(
			clamped < 0 ? -clamped : clamped);
		if (magnitude != 0U) {
			g_stats.mixed_peak_abs = std::max(g_stats.mixed_peak_abs, magnitude);
		}
		output[index] = static_cast<int16_t>(clamped);
	}
	++g_stats.mixed_buffers;
	g_stats.mixed_frames += frames;
	for (size_t index = 0; index < frames * 2U; ++index) {
		if (output[index] != 0) {
			++g_stats.mixed_nonzero_buffers;
			break;
		}
	}
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
				g_stats.stream_mixed_peak_abs =
					std::max(g_stats.stream_mixed_peak_abs, magnitude);
			}
		}
		if (stream_nonzero) ++g_stats.stream_mixed_nonzero_buffers;
	}
}

#if !defined(RENEGADE_MILES_MANUAL_MIX)
void *Output_Thread(void *)
{
	std::vector<int16_t> output(kOutputFrames * 2U, 0);
	for (;;) {
		if (g_output_stop.load(std::memory_order_acquire)) break;
		if (pthread_mutex_trylock(&g_mutex) != 0) {
			struct timespec retry = { 0, 1000000L };
			nanosleep(&retry, nullptr);
			continue;
		}
		Mix_Locked(output.data(), kOutputFrames);
		pthread_mutex_unlock(&g_mutex);
#if defined(__vita__)
		if (g_audio_port >= 0) {
			const int result = sceAudioOutOutput(g_audio_port, output.data());
			if (pthread_mutex_trylock(&g_mutex) == 0) {
				if (result < 0) {
					Set_Error("sceAudioOutOutput failed");
					++g_stats.output_write_failures;
				} else {
					++g_stats.output_buffers_written;
				}
				pthread_mutex_unlock(&g_mutex);
			}
		}
#else
		struct timespec duration = { 0, 21333333L };
		nanosleep(&duration, nullptr);
#endif
	}
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
	if (sample != nullptr) g_samples.push_back(sample);
	else Set_Error("sample allocation failed");
	return sample;
}

void Release_Sample(RenegadeMilesSample *sample)
{
	if (sample == nullptr) return;
	auto entry = std::find(g_samples.begin(), g_samples.end(), sample);
	if (entry != g_samples.end()) g_samples.erase(entry);
	delete sample;
}

bool Read_Stream_Image(const char *name, std::vector<uint8_t> *image)
{
	if (name == nullptr || image == nullptr || g_file_open == nullptr ||
		g_file_close == nullptr || g_file_seek == nullptr || g_file_read == nullptr) {
		Set_Error("stream file callbacks are unavailable");
		return false;
	}
	U32 handle = 0;
	if (g_file_open(name, &handle) == 0U) {
		Set_Error("stream source open failed");
		return false;
	}
	const S32 file_size = g_file_seek(handle, 0, AIL_FILE_SEEK_END);
	if (file_size <= 0 || static_cast<size_t>(file_size) > kMaximumWaveBytes ||
		g_file_seek(handle, 0, AIL_FILE_SEEK_BEGIN) < 0) {
		g_file_close(handle);
		Set_Error("stream source size is invalid");
		return false;
	}
	image->resize(static_cast<size_t>(file_size));
	const U32 read = g_file_read(handle, image->data(), static_cast<U32>(image->size()));
	g_file_close(handle);
	if (read != image->size()) {
		image->clear();
		Set_Error("stream source read was incomplete");
		return false;
	}
	g_stats.stream_bytes_read += read;
	return true;
}

RenegadeMilesSample *Stream_Sample(HSTREAM stream)
{
	return stream != nullptr ? stream->sample : nullptr;
}

} // namespace

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
	if (sample != nullptr && sample->wave.Frame_Count() != 0) {
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
		sample->cursor = std::min<double>(sample->wave.Frame_Count(),
			static_cast<double>(milliseconds) * sample->wave.sample_rate / 1000.0);
	}
	AIL_unlock();
}

void AIL_sample_ms_position(HSAMPLE sample, S32 *length, S32 *position)
{
	AIL_lock();
	if (sample != nullptr && sample->wave.sample_rate != 0) {
		if (length != nullptr) *length = static_cast<S32>(
			sample->wave.Frame_Count() * 1000U / sample->wave.sample_rate);
		if (position != nullptr) *position = static_cast<S32>(
			sample->cursor * 1000.0 / sample->wave.sample_rate);
	} else {
		if (length != nullptr) *length = 0;
		if (position != nullptr) *position = 0;
	}
	AIL_unlock();
}

void AIL_set_sample_user_data(HSAMPLE sample, S32 index, U32 value)
{
	AIL_lock();
	if (sample != nullptr && index >= 0 && index < 8) sample->user_data[index] = value;
	AIL_unlock();
}

U32 AIL_sample_user_data(HSAMPLE sample, S32 index)
{
	AIL_lock();
	const U32 value = sample != nullptr && index >= 0 && index < 8
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
	const size_t bytes = Declared_Wave_Bytes(data);
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
		sample->cursor = fraction * sample->wave.Frame_Count();
	}
	AIL_unlock();
}

U32 AIL_3D_sample_offset(H3DSAMPLE sample)
{
	AIL_lock();
	const U32 value = sample != nullptr && sample->wave.Frame_Count() != 0U
		? static_cast<U32>(std::min<double>(sample->encoded_data_bytes,
			sample->cursor * sample->encoded_data_bytes / sample->wave.Frame_Count()))
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

void AIL_set_3D_object_user_data(H3DSAMPLE sample, S32 index, U32 value) { AIL_set_sample_user_data(sample, index, value); }
U32 AIL_3D_object_user_data(H3DSAMPLE sample, S32 index) { return AIL_sample_user_data(sample, index); }
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
	AIL_lock();
	++g_stats.stream_open_attempts;
	std::snprintf(g_stats.last_stream_name, sizeof(g_stats.last_stream_name), "%s",
		name != nullptr ? name : "");
	std::vector<uint8_t> image;
	RenegadeMilesStream *stream = nullptr;
	if (sample != nullptr && Read_Stream_Image(name, &image) &&
		Decode_Into_Sample(sample, image.data(), image.size())) {
		stream = new (std::nothrow) RenegadeMilesStream;
		if (stream != nullptr) {
			stream->sample = sample;
			sample->streaming = true;
			g_stats.stream_decoded_frames += sample->wave.Frame_Count();
			g_stats.last_stream_frames = static_cast<uint32_t>(
				std::min<size_t>(sample->wave.Frame_Count(),
					std::numeric_limits<uint32_t>::max()));
			g_stats.last_stream_rate = static_cast<uint32_t>(
				std::max<S32>(0, sample->playback_rate));
			g_stats.last_stream_volume = static_cast<uint32_t>(
				std::max<S32>(0, sample->volume));
			g_stats.last_stream_pan = static_cast<uint32_t>(
				std::max<S32>(0, sample->pan));
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
	if (stream->sample != nullptr) stream->sample->streaming = false;
	if (stream->owns_sample) Release_Sample(stream->sample);
	delete stream;
	AIL_unlock();
}

void AIL_start_stream(HSTREAM stream)
{
	AIL_lock();
	++g_stats.stream_start_attempts;
	RenegadeMilesSample *sample = Stream_Sample(stream);
	if (sample != nullptr) {
		g_stats.last_stream_frames = static_cast<uint32_t>(
			std::min<size_t>(sample->wave.Frame_Count(),
				std::numeric_limits<uint32_t>::max()));
		g_stats.last_stream_rate = static_cast<uint32_t>(
			std::max<S32>(0, sample->playback_rate));
		g_stats.last_stream_volume = static_cast<uint32_t>(
			std::max<S32>(0, sample->volume));
		g_stats.last_stream_pan = static_cast<uint32_t>(
			std::max<S32>(0, sample->pan));
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
		static_cast<const uint8_t *>(data), bytes, &wave, &error, true)) {
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
	std::snprintf(g_stats.last_error, sizeof(g_stats.last_error), "%s",
		g_last_error);
	AIL_unlock();
}

void Renegade_Miles_Get_Runtime_Stats(RenegadeMilesRuntimeStats *stats)
{
	if (stats == nullptr) return;
	AIL_lock();
	*stats = g_stats;
	stats->allocated_samples = static_cast<uint32_t>(g_samples.size());
	stats->active_samples = 0U;
	stats->active_streams = 0U;
	for (RenegadeMilesSample *sample : g_samples) {
		if (sample != nullptr && sample->playing && !sample->paused) {
			++stats->active_samples;
			if (sample->streaming) ++stats->active_streams;
		}
	}
	std::snprintf(stats->last_error, sizeof(stats->last_error), "%s",
		g_last_error);
	AIL_unlock();
}
