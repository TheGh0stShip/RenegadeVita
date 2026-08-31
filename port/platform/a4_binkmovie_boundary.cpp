#include "binkmovie.h"
#include "a4_frontend_lifecycle_boundary.h"

#if defined(__vita__) && defined(RENEGADE_A4_BINK_FFMPEG)

#include "renegade_paths.h"
#include "ww3d_vita_renderer.h"
#include "vita/a30_vita_runtime.h"

#include <algorithm>
#include <atomic>
#include <errno.h>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <vector>

#include <psp2/audioout.h>
#include <psp2/ctrl.h>
#include <psp2/kernel/processmgr.h>
#include <psp2/kernel/threadmgr.h>
#include <vitaGL.h>

extern "C" {
#include <libavcodec/avcodec.h>
#include <libavformat/avformat.h>
#include <libavutil/channel_layout.h>
#include <libavutil/error.h>
#include <libavutil/mathematics.h>
#include <libswresample/swresample.h>
#include <libswscale/swscale.h>
}

namespace {

constexpr int kAudioRate = 48000;
constexpr int kAudioChannels = 2;
constexpr int kAudioFramesPerBuffer = 1024;
constexpr size_t kAudioRingFrames = 2U * kAudioRate;
constexpr int64_t kPresentationToleranceUs = 2000;
constexpr int64_t kUpdateBudgetUs = 12000;
constexpr uint32_t kSkipButtonMask =
	SCE_CTRL_START | SCE_CTRL_CROSS | SCE_CTRL_CIRCLE | SCE_CTRL_TRIANGLE;

const RenegadePathRoots kVitaRoots = {
	"ux0:data/renegade/retail",
	"ux0:data/renegade/user",
	"ux0:data/renegade/cache",
	"ux0:data/renegade/mods"
};

bool g_initialized = false;
bool g_active = false;
bool g_complete = true;
std::atomic<bool> g_demux_eof(false);
bool g_decoders_flushed = false;
char g_movie_name[160] = {};

AVFormatContext *g_format = NULL;
AVCodecContext *g_video_decoder = NULL;
AVCodecContext *g_audio_decoder = NULL;
AVFrame *g_video_frame = NULL;
AVFrame *g_audio_frame = NULL;
AVPacket *g_packet = NULL;
bool g_packet_pending = false;
SwsContext *g_scaler = NULL;
SwrContext *g_resampler = NULL;
int g_video_stream = -1;
int g_audio_stream = -1;
int g_video_width = 0;
int g_video_height = 0;
int64_t g_start_us = 0;
int64_t g_first_video_pts_us = AV_NOPTS_VALUE;
int64_t g_frame_duration_us = 33333;
uint64_t g_decoded_video_frames = 0U;

GLuint g_video_texture = 0U;
bool g_texture_allocated = false;
int g_texture_width = 0;
int g_texture_height = 0;
bool g_pending_video = false;
int64_t g_pending_video_pts_us = 0;
std::vector<uint8_t> g_pending_rgba;

pthread_mutex_t g_audio_mutex = PTHREAD_MUTEX_INITIALIZER;
pthread_t g_audio_thread;
bool g_audio_thread_running = false;
int g_audio_port = -1;
std::atomic<bool> g_audio_stop(false);
std::atomic<bool> g_audio_drained(true);
std::vector<int16_t> g_audio_ring;
size_t g_audio_read = 0U;
size_t g_audio_write = 0U;
size_t g_audio_count = 0U;
bool g_audio_enabled = false;
bool g_audio_drop_logged = false;
SceAudioOutPortType g_audio_port_type = SCE_AUDIO_OUT_PORT_TYPE_MAIN;
uint32_t g_last_skip_buttons = 0U;
bool g_update_budget_logged = false;
bool g_update_entry_logged = false;
bool g_render_entry_logged = false;
bool g_demux_read_entry_logged = false;
bool g_audio_thread_entry_logged = false;
bool g_audio_first_output_logged = false;
bool g_audio_first_frame_logged = false;
bool g_video_first_frame_logged = false;
bool g_video_first_upload_logged = false;
bool g_playback_statistics_logged = false;

struct BinkStageTiming
{
	uint64_t calls;
	uint64_t total_us;
	uint64_t worst_us;
};

BinkStageTiming g_audio_decode_timing = {};
BinkStageTiming g_video_decode_timing = {};
BinkStageTiming g_video_upload_timing = {};
std::atomic<uint64_t> g_audio_wait_count(0U);
std::atomic<uint64_t> g_audio_output_buffers(0U);
std::atomic<uint64_t> g_audio_output_samples(0U);
std::atomic<uint64_t> g_audio_partial_output_buffers(0U);
std::atomic<uint64_t> g_audio_high_water_samples(0U);

void Record_Bink_Stage(BinkStageTiming &timing, uint64_t elapsed_us)
{
	++timing.calls;
	timing.total_us += elapsed_us;
	if (elapsed_us > timing.worst_us) timing.worst_us = elapsed_us;
}

class BinkStageTimer
{
public:
	explicit BinkStageTimer(BinkStageTiming &timing) :
		Timing(timing), StartedUs(sceKernelGetProcessTimeWide())
	{
	}

	~BinkStageTimer()
	{
		Record_Bink_Stage(Timing,
			sceKernelGetProcessTimeWide() - StartedUs);
	}

private:
	BinkStageTiming &Timing;
	uint64_t StartedUs;
};

int Next_Power_Of_Two(int value)
{
	int result = 1;
	while (result < value && result < 4096) result <<= 1;
	return result;
}

void Log_FFmpeg_Error(const char *operation, int error)
{
	char message[AV_ERROR_MAX_STRING_SIZE] = {};
	av_strerror(error, message, sizeof(message));
	A30_Vita_Log("A4 Bink: %s failed code=%d error=%s movie=%s\n",
		operation, error, message,
		g_movie_name[0] != '\0' ? g_movie_name : "none");
}

void Copy_Movie_Name(const char *filename)
{
	if (filename == NULL) filename = "";
	strncpy(g_movie_name, filename, sizeof(g_movie_name) - 1U);
	g_movie_name[sizeof(g_movie_name) - 1U] = '\0';
}

const char *Audio_Port_Name(SceAudioOutPortType port_type)
{
	switch (port_type) {
		case SCE_AUDIO_OUT_PORT_TYPE_MAIN: return "main";
		case SCE_AUDIO_OUT_PORT_TYPE_BGM: return "bgm";
		case SCE_AUDIO_OUT_PORT_TYPE_VOICE: return "voice";
		default: return "unknown";
	}
}

const char *Build_FFmpeg_File_URL(const RenegadeResolvedPath &resolved,
	char *url, size_t capacity)
{
	if (strncmp(resolved.physical, "file:", 5) == 0) return resolved.physical;
	if (strchr(resolved.physical, ':') == NULL) return resolved.physical;
	if (snprintf(url, capacity, "file:%s", resolved.physical) <= 0) {
		return resolved.physical;
	}
	url[capacity - 1U] = '\0';
	return url;
}

uint32_t Read_Skip_Buttons()
{
	SceCtrlData controller = {};
	if (sceCtrlPeekBufferPositive(0, &controller, 1) <= 0) return 0U;
	return controller.buttons & kSkipButtonMask;
}

void Prime_Skip_Button_Latch()
{
	g_last_skip_buttons = Read_Skip_Buttons();
}

bool Check_Skip_Request()
{
	const uint32_t buttons = Read_Skip_Buttons();
	const uint32_t newly_pressed = buttons & ~g_last_skip_buttons;
	g_last_skip_buttons = buttons;
	if (newly_pressed == 0U) return false;
	A30_Vita_Log("A4 Bink: skip requested buttons=%08X movie=%s\n",
		static_cast<unsigned>(newly_pressed),
		g_movie_name[0] != '\0' ? g_movie_name : "none");
	A4_Frontend_Record_Bink_Skip(g_movie_name);
	g_complete = true;
	return true;
}

void Reset_Audio_Ring()
{
	pthread_mutex_lock(&g_audio_mutex);
	g_audio_ring.assign(kAudioRingFrames * kAudioChannels, 0);
	g_audio_read = 0U;
	g_audio_write = 0U;
	g_audio_count = 0U;
	pthread_mutex_unlock(&g_audio_mutex);
	g_audio_drained.store(false, std::memory_order_release);
	g_audio_drop_logged = false;
}

void Queue_Audio(const int16_t *samples, size_t sample_count)
{
	if (!g_audio_enabled || samples == NULL || sample_count == 0U) return;
	pthread_mutex_lock(&g_audio_mutex);
	const size_t capacity = g_audio_ring.size();
	if (capacity == 0U || g_audio_count >= capacity) {
		pthread_mutex_unlock(&g_audio_mutex);
		if (!g_audio_drop_logged) {
			A30_Vita_Log("A4 Bink: audio ring unavailable/full capacity=%u count=%u samples=%u movie=%s\n",
				static_cast<unsigned>(capacity),
				static_cast<unsigned>(g_audio_count),
				static_cast<unsigned>(sample_count), g_movie_name);
			g_audio_drop_logged = true;
		}
		return;
	}
	const size_t available = capacity - g_audio_count;
	const size_t accepted = std::min(sample_count, available);
	for (size_t index = 0U; index < accepted; ++index) {
		g_audio_ring[g_audio_write] = samples[index];
		g_audio_write = (g_audio_write + 1U) % capacity;
	}
	g_audio_count += accepted;
	uint64_t high_water = g_audio_high_water_samples.load(std::memory_order_relaxed);
	while (g_audio_count > high_water &&
		!g_audio_high_water_samples.compare_exchange_weak(high_water,
			g_audio_count, std::memory_order_relaxed)) {
	}
	pthread_mutex_unlock(&g_audio_mutex);
	if (accepted != sample_count && !g_audio_drop_logged) {
		A30_Vita_Log("A4 Bink: audio ring full; dropped=%u samples movie=%s\n",
			static_cast<unsigned>(sample_count - accepted), g_movie_name);
		g_audio_drop_logged = true;
	}
}

void *Audio_Output_Thread(void *)
{
	if (!g_audio_thread_entry_logged) {
		A30_Vita_Log("A4 Bink: audio output thread entry port=%d ring_samples=%u\n",
			g_audio_port, static_cast<unsigned>(g_audio_ring.size()));
		g_audio_thread_entry_logged = true;
	}
	std::vector<int16_t> output(kAudioFramesPerBuffer * kAudioChannels, 0);
	while (!g_audio_stop.load(std::memory_order_acquire)) {
		std::fill(output.begin(), output.end(), 0);
		pthread_mutex_lock(&g_audio_mutex);
		const size_t capacity = g_audio_ring.size();
		const bool drained_before_output = g_demux_eof.load(std::memory_order_acquire) &&
			g_audio_count == 0U;
		const bool full_output_ready = capacity > 0U &&
			g_audio_count >= output.size();
		if (drained_before_output) {
			pthread_mutex_unlock(&g_audio_mutex);
			g_audio_drained.store(true, std::memory_order_release);
			break;
		}
		/* Never submit a zero-filled startup/starvation buffer.  A BINK decode
		** may occupy the frontend thread for longer than one hardware buffer;
		** wait for real samples and record the wait instead of turning that
		** decoder latency into audible buzz. */
		if (!full_output_ready &&
			!g_demux_eof.load(std::memory_order_acquire)) {
			pthread_mutex_unlock(&g_audio_mutex);
			g_audio_wait_count.fetch_add(1U, std::memory_order_relaxed);
			sceKernelDelayThread(1000U);
			continue;
		}
		const size_t copied = capacity > 0U ? std::min(output.size(), g_audio_count) : 0U;
		for (size_t index = 0U; index < copied; ++index) {
			output[index] = g_audio_ring[g_audio_read];
			g_audio_read = (g_audio_read + 1U) % capacity;
		}
		g_audio_count -= copied;
		const bool drained = g_demux_eof.load(std::memory_order_acquire) &&
			g_audio_count == 0U;
		pthread_mutex_unlock(&g_audio_mutex);
		if (drained) g_audio_drained.store(true, std::memory_order_release);
		if (g_audio_port >= 0) {
			if (!g_audio_first_output_logged) {
				A30_Vita_Log("A4 Bink: audio output first buffer port=%d copied=%u drained=%d waits=%llu movie=%s\n",
					g_audio_port, static_cast<unsigned>(copied),
					drained ? 1 : 0,
					static_cast<unsigned long long>(g_audio_wait_count.load(
						std::memory_order_relaxed)), g_movie_name);
				g_audio_first_output_logged = true;
			}
			const int result = sceAudioOutOutput(g_audio_port, output.data());
			if (result < 0) {
				A30_Vita_Log("A4 Bink: sceAudioOutOutput failed code=%08X\n",
					static_cast<unsigned>(result));
				break;
			}
			g_audio_output_buffers.fetch_add(1U, std::memory_order_relaxed);
			g_audio_output_samples.fetch_add(copied, std::memory_order_relaxed);
			if (copied != output.size()) {
				g_audio_partial_output_buffers.fetch_add(1U,
					std::memory_order_relaxed);
			}
		}
	}
	g_audio_drained.store(true, std::memory_order_release);
	return NULL;
}

void Stop_Audio_Output()
{
	if (g_audio_thread_running) {
		g_audio_stop.store(true, std::memory_order_release);
		pthread_join(g_audio_thread, NULL);
		g_audio_thread_running = false;
	}
	if (g_audio_port >= 0) {
		sceAudioOutReleasePort(g_audio_port);
		g_audio_port = -1;
	}
	g_audio_enabled = false;
	g_audio_drained.store(true, std::memory_order_release);
}

bool Start_Audio_Output()
{
	Reset_Audio_Ring();
	const SceAudioOutPortType port_types[] = {
		SCE_AUDIO_OUT_PORT_TYPE_MAIN,
		SCE_AUDIO_OUT_PORT_TYPE_VOICE,
		SCE_AUDIO_OUT_PORT_TYPE_BGM
	};
	for (size_t index = 0U; index < sizeof(port_types) / sizeof(port_types[0]);
		++index) {
		g_audio_port_type = port_types[index];
		g_audio_port = sceAudioOutOpenPort(g_audio_port_type,
			kAudioFramesPerBuffer, kAudioRate, SCE_AUDIO_OUT_MODE_STEREO);
		if (g_audio_port >= 0) {
			A30_Vita_Log("A4 Bink: audio output port opened type=%s handle=%d\n",
				Audio_Port_Name(g_audio_port_type), g_audio_port);
			break;
		}
		A30_Vita_Log("A4 Bink: sceAudioOutOpenPort type=%s failed code=%08X%s\n",
			Audio_Port_Name(g_audio_port_type),
			static_cast<unsigned>(g_audio_port),
			static_cast<unsigned>(g_audio_port) ==
				static_cast<unsigned>(SCE_AUDIO_OUT_ERROR_PORT_FULL) ?
				" port_full" : "");
	}
	if (g_audio_port < 0) {
		A30_Vita_Log("A4 Bink: all audio output ports unavailable last_code=%08X; video continues\n",
			static_cast<unsigned>(g_audio_port));
		g_audio_drained.store(true, std::memory_order_release);
		return false;
	}
	g_audio_stop.store(false, std::memory_order_release);
	if (pthread_create(&g_audio_thread, NULL, Audio_Output_Thread, NULL) != 0) {
		A30_Vita_Log("A4 Bink: audio output thread creation failed; video continues\n");
		sceAudioOutReleasePort(g_audio_port);
		g_audio_port = -1;
		g_audio_drained.store(true, std::memory_order_release);
		return false;
	}
	g_audio_thread_running = true;
	g_audio_enabled = true;
	return true;
}

void Release_Decoder_State()
{
	Stop_Audio_Output();
	if (g_video_texture != 0U) glDeleteTextures(1, &g_video_texture);
	g_video_texture = 0U;
	g_texture_allocated = false;
	g_texture_width = 0;
	g_texture_height = 0;
	g_pending_video = false;
	g_pending_rgba.clear();
	g_audio_ring.clear();
	if (g_resampler != NULL) swr_free(&g_resampler);
	if (g_scaler != NULL) sws_freeContext(g_scaler);
	g_scaler = NULL;
	av_frame_free(&g_video_frame);
	av_frame_free(&g_audio_frame);
	if (g_packet != NULL) {
		av_packet_unref(g_packet);
	}
	av_packet_free(&g_packet);
	g_packet_pending = false;
	avcodec_free_context(&g_video_decoder);
	avcodec_free_context(&g_audio_decoder);
	if (g_format != NULL) avformat_close_input(&g_format);
	g_video_stream = -1;
	g_audio_stream = -1;
	g_video_width = 0;
	g_video_height = 0;
	g_demux_eof.store(false, std::memory_order_release);
	g_decoders_flushed = false;
	g_first_video_pts_us = AV_NOPTS_VALUE;
	g_decoded_video_frames = 0U;
	g_last_skip_buttons = 0U;
	g_update_budget_logged = false;
	g_update_entry_logged = false;
	g_render_entry_logged = false;
	g_demux_read_entry_logged = false;
	g_audio_thread_entry_logged = false;
	g_audio_first_output_logged = false;
	g_audio_first_frame_logged = false;
	g_video_first_frame_logged = false;
	g_video_first_upload_logged = false;
}

bool Open_Decoder(AVCodecContext **context, AVStream *stream)
{
	const AVCodec *codec = avcodec_find_decoder(stream->codecpar->codec_id);
	if (codec == NULL) return false;
	AVCodecContext *decoder = avcodec_alloc_context3(codec);
	if (decoder == NULL) return false;
	int result = avcodec_parameters_to_context(decoder, stream->codecpar);
	if (result >= 0) {
		decoder->thread_count = 1;
		result = avcodec_open2(decoder, codec, NULL);
	}
	if (result < 0) {
		Log_FFmpeg_Error("avcodec_open2", result);
		avcodec_free_context(&decoder);
		return false;
	}
	*context = decoder;
	return true;
}

bool Configure_Audio()
{
	if (g_audio_stream < 0 || g_audio_decoder == NULL) return false;
	AVChannelLayout output_layout;
	av_channel_layout_default(&output_layout, kAudioChannels);
	const int result = swr_alloc_set_opts2(&g_resampler, &output_layout,
		AV_SAMPLE_FMT_S16, kAudioRate, &g_audio_decoder->ch_layout,
		g_audio_decoder->sample_fmt, g_audio_decoder->sample_rate, 0, NULL);
	av_channel_layout_uninit(&output_layout);
	if (result < 0 || g_resampler == NULL || swr_init(g_resampler) < 0) {
		A30_Vita_Log("A4 Bink: audio resampler unavailable; video continues\n");
		if (g_resampler != NULL) swr_free(&g_resampler);
		return false;
	}
	return Start_Audio_Output();
}

void Decode_Audio_Frames()
{
	BinkStageTimer timing(g_audio_decode_timing);
	if (g_audio_decoder == NULL || g_audio_frame == NULL || g_resampler == NULL) return;
	for (;;) {
		const int result = avcodec_receive_frame(g_audio_decoder, g_audio_frame);
		if (result == AVERROR(EAGAIN) || result == AVERROR_EOF) break;
		if (result < 0) {
			Log_FFmpeg_Error("audio receive", result);
			break;
		}
		const int input_rate = std::max(1, g_audio_decoder->sample_rate);
		const int output_frames = static_cast<int>(av_rescale_rnd(
			swr_get_delay(g_resampler, input_rate) + g_audio_frame->nb_samples,
			kAudioRate, input_rate, AV_ROUND_UP));
		std::vector<int16_t> converted(
			static_cast<size_t>(output_frames) * kAudioChannels);
		uint8_t *output[] = { reinterpret_cast<uint8_t *>(converted.data()) };
		const int frames = swr_convert(g_resampler, output, output_frames,
			reinterpret_cast<const uint8_t *const *>(g_audio_frame->extended_data),
			g_audio_frame->nb_samples);
			if (frames > 0) {
				if (!g_audio_first_frame_logged) {
					A30_Vita_Log("A4 Bink: first decoded audio frame input_samples=%d output_frames=%d movie=%s\n",
						g_audio_frame->nb_samples, frames, g_movie_name);
					g_audio_first_frame_logged = true;
				}
				Queue_Audio(converted.data(), static_cast<size_t>(frames) * kAudioChannels);
			}
			av_frame_unref(g_audio_frame);
		}
}

bool Receive_Video_Frame()
{
	BinkStageTimer timing(g_video_decode_timing);
	if (g_video_decoder == NULL || g_video_frame == NULL || g_pending_video) return false;
	const int result = avcodec_receive_frame(g_video_decoder, g_video_frame);
	if (result == AVERROR(EAGAIN) || result == AVERROR_EOF) return false;
	if (result < 0) {
		Log_FFmpeg_Error("video receive", result);
		return false;
	}

	g_scaler = sws_getCachedContext(g_scaler, g_video_frame->width,
		g_video_frame->height, static_cast<AVPixelFormat>(g_video_frame->format),
		g_video_width, g_video_height, AV_PIX_FMT_RGBA, SWS_BILINEAR,
		NULL, NULL, NULL);
	if (g_scaler == NULL) {
		A30_Vita_Log("A4 Bink: sws_getCachedContext failed\n");
		av_frame_unref(g_video_frame);
		return false;
	}
	g_pending_rgba.resize(static_cast<size_t>(g_video_width) * g_video_height * 4U);
	uint8_t *destination[] = { g_pending_rgba.data() };
	int destination_stride[] = { g_video_width * 4 };
	sws_scale(g_scaler, g_video_frame->data, g_video_frame->linesize, 0,
		g_video_frame->height, destination, destination_stride);

	int64_t pts_us = AV_NOPTS_VALUE;
	if (g_video_frame->best_effort_timestamp != AV_NOPTS_VALUE) {
		pts_us = av_rescale_q(g_video_frame->best_effort_timestamp,
			g_format->streams[g_video_stream]->time_base, AVRational{1, 1000000});
		if (g_first_video_pts_us == AV_NOPTS_VALUE) g_first_video_pts_us = pts_us;
		pts_us -= g_first_video_pts_us;
	}
	if (pts_us == AV_NOPTS_VALUE || pts_us < 0) {
		pts_us = static_cast<int64_t>(g_decoded_video_frames) * g_frame_duration_us;
	}
	g_pending_video_pts_us = pts_us;
	g_pending_video = true;
	++g_decoded_video_frames;
	if (!g_video_first_frame_logged) {
		A30_Vita_Log("A4 Bink: first decoded video frame source=%dx%d output=%dx%d pts_us=%lld movie=%s\n",
			g_video_frame->width, g_video_frame->height, g_video_width,
			g_video_height, static_cast<long long>(pts_us), g_movie_name);
		g_video_first_frame_logged = true;
	}
	av_frame_unref(g_video_frame);
	return true;
}

bool Upload_Pending_Video()
{
	BinkStageTimer timing(g_video_upload_timing);
	if (!g_pending_video || g_pending_rgba.empty()) return false;
	if (g_video_texture == 0U) glGenTextures(1, &g_video_texture);
	if (g_video_texture == 0U) return false;
	GLenum stale_error = GL_NO_ERROR;
	for (unsigned index = 0U; index < 8U; ++index) {
		const GLenum error = glGetError();
		if (error == GL_NO_ERROR) break;
		stale_error = error;
	}
	GLint previous_active_texture = GL_TEXTURE0;
	GLint previous_texture = 0;
	glGetIntegerv(GL_ACTIVE_TEXTURE, &previous_active_texture);
	glActiveTexture(GL_TEXTURE0);
	glGetIntegerv(GL_TEXTURE_BINDING_2D, &previous_texture);
	const int intended_texture_width = g_texture_allocated ?
		g_texture_width : Next_Power_Of_Two(g_video_width);
	const int intended_texture_height = g_texture_allocated ?
		g_texture_height : Next_Power_Of_Two(g_video_height);
	glBindTexture(GL_TEXTURE_2D, g_video_texture);
	RenegadeVitaRenderer::Invalidate_Texture_State_Cache();
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);
	const GLenum setup_error = glGetError();
	if (setup_error != GL_NO_ERROR) {
		glBindTexture(GL_TEXTURE_2D, static_cast<GLuint>(previous_texture));
		glActiveTexture(static_cast<GLenum>(previous_active_texture));
		A30_Vita_Log("A4 Bink: texture setup failed error=%08X stale_error=%08X video=%dx%d storage=%dx%d texture=%u movie=%s\n",
			static_cast<unsigned>(setup_error), static_cast<unsigned>(stale_error),
			g_video_width, g_video_height, intended_texture_width, intended_texture_height,
			static_cast<unsigned>(g_video_texture), g_movie_name);
		return false;
	}
	if (!g_texture_allocated) {
		g_texture_width = Next_Power_Of_Two(g_video_width);
		g_texture_height = Next_Power_Of_Two(g_video_height);
		std::vector<uint8_t> padded(
			static_cast<size_t>(g_texture_width) * g_texture_height * 4U, 0U);
		for (int y = 0; y < g_video_height; ++y) {
			memcpy(padded.data() + static_cast<size_t>(y) * g_texture_width * 4U,
				g_pending_rgba.data() + static_cast<size_t>(y) * g_video_width * 4U,
				static_cast<size_t>(g_video_width) * 4U);
		}
		glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, g_texture_width, g_texture_height,
			0, GL_RGBA, GL_UNSIGNED_BYTE, padded.data());
	} else {
		glTexSubImage2D(GL_TEXTURE_2D, 0, 0, 0, g_video_width, g_video_height,
			GL_RGBA, GL_UNSIGNED_BYTE, g_pending_rgba.data());
	}
	const GLenum upload_error = glGetError();
	glBindTexture(GL_TEXTURE_2D, static_cast<GLuint>(previous_texture));
	glActiveTexture(static_cast<GLenum>(previous_active_texture));
	RenegadeVitaRenderer::Invalidate_Texture_State_Cache();
	if (upload_error != GL_NO_ERROR) {
		const int attempted_texture_width = g_texture_width;
		const int attempted_texture_height = g_texture_height;
		if (!g_texture_allocated && g_video_texture != 0U) {
			glDeleteTextures(1, &g_video_texture);
			g_video_texture = 0U;
		}
		g_texture_allocated = false;
		g_texture_width = 0;
		g_texture_height = 0;
		A30_Vita_Log("A4 Bink: texture upload failed error=%08X stale_error=%08X video=%dx%d storage=%dx%d movie=%s\n",
			static_cast<unsigned>(upload_error), static_cast<unsigned>(stale_error),
			g_video_width, g_video_height, attempted_texture_width, attempted_texture_height,
			g_movie_name);
		return false;
	}
	g_texture_allocated = true;
	if (!g_video_first_upload_logged) {
		A30_Vita_Log("A4 Bink: first video texture upload complete texture=%u video=%dx%d storage=%dx%d movie=%s\n",
			static_cast<unsigned>(g_video_texture), g_video_width, g_video_height,
			g_texture_width, g_texture_height, g_movie_name);
		g_video_first_upload_logged = true;
	}
	g_pending_video = false;
	return true;
}

bool Submit_Video_Packet()
{
	if (g_video_decoder == NULL || g_packet == NULL) return true;
	for (unsigned attempt = 0U; attempt < 2U; ++attempt) {
		const int result = avcodec_send_packet(g_video_decoder, g_packet);
		if (result == AVERROR(EAGAIN)) {
			Receive_Video_Frame();
			if (g_pending_video) return false;
			continue;
		}
		if (result < 0) {
			Log_FFmpeg_Error("video send", result);
		}
		Receive_Video_Frame();
		return true;
	}
	return false;
}

bool Submit_Audio_Packet()
{
	if (g_audio_decoder == NULL || g_packet == NULL || !g_audio_enabled) return true;
	for (unsigned attempt = 0U; attempt < 2U; ++attempt) {
		const int result = avcodec_send_packet(g_audio_decoder, g_packet);
		if (result == AVERROR(EAGAIN)) {
			Decode_Audio_Frames();
			continue;
		}
		if (result < 0) {
			Log_FFmpeg_Error("audio send", result);
		}
		Decode_Audio_Frames();
		return true;
	}
	return false;
}

void Flush_Decoders()
{
	if (g_decoders_flushed) return;
	g_decoders_flushed = true;
	if (g_video_decoder != NULL) avcodec_send_packet(g_video_decoder, NULL);
	if (g_audio_decoder != NULL) {
		avcodec_send_packet(g_audio_decoder, NULL);
		Decode_Audio_Frames();
	}
}

void Reset_Playback_Statistics()
{
	g_audio_decode_timing = {};
	g_video_decode_timing = {};
	g_video_upload_timing = {};
	g_audio_wait_count.store(0U, std::memory_order_relaxed);
	g_audio_output_buffers.store(0U, std::memory_order_relaxed);
	g_audio_output_samples.store(0U, std::memory_order_relaxed);
	g_audio_partial_output_buffers.store(0U, std::memory_order_relaxed);
	g_audio_high_water_samples.store(0U, std::memory_order_relaxed);
	g_playback_statistics_logged = false;
}

void Log_Playback_Statistics(const char *reason)
{
	if (g_playback_statistics_logged) return;
	g_playback_statistics_logged = true;
	const uint64_t wall_us = g_start_us > 0 ?
		sceKernelGetProcessTimeWide() - static_cast<uint64_t>(g_start_us) : 0U;
	A30_Vita_Log("A4 Bink: playback stats reason=%s movie=%s wall_ms=%llu frames=%llu audio_waits=%llu output_buffers/samples/partial=%llu/%llu/%llu audio_high_water_samples=%llu audio_decode_calls/total/worst_us=%llu/%llu/%llu video_decode_calls/total/worst_us=%llu/%llu/%llu video_upload_calls/total/worst_us=%llu/%llu/%llu\n",
		reason != NULL ? reason : "unknown", g_movie_name,
		static_cast<unsigned long long>(wall_us / 1000U),
		static_cast<unsigned long long>(g_decoded_video_frames),
		static_cast<unsigned long long>(g_audio_wait_count.load(std::memory_order_relaxed)),
		static_cast<unsigned long long>(g_audio_output_buffers.load(std::memory_order_relaxed)),
		static_cast<unsigned long long>(g_audio_output_samples.load(std::memory_order_relaxed)),
		static_cast<unsigned long long>(g_audio_partial_output_buffers.load(std::memory_order_relaxed)),
		static_cast<unsigned long long>(g_audio_high_water_samples.load(std::memory_order_relaxed)),
		static_cast<unsigned long long>(g_audio_decode_timing.calls),
		static_cast<unsigned long long>(g_audio_decode_timing.total_us),
		static_cast<unsigned long long>(g_audio_decode_timing.worst_us),
		static_cast<unsigned long long>(g_video_decode_timing.calls),
		static_cast<unsigned long long>(g_video_decode_timing.total_us),
		static_cast<unsigned long long>(g_video_decode_timing.worst_us),
		static_cast<unsigned long long>(g_video_upload_timing.calls),
		static_cast<unsigned long long>(g_video_upload_timing.total_us),
		static_cast<unsigned long long>(g_video_upload_timing.worst_us));
}

void Mark_Failed(const char *reason)
{
	Log_Playback_Statistics(reason);
	A30_Vita_Log("A4 Bink: playback skipped reason=%s movie=%s; original menu route continues\n",
		reason, g_movie_name[0] != '\0' ? g_movie_name : "unnamed");
	A4_Frontend_Record_Bink_Skip(g_movie_name);
	/* A failure belongs to this movie.  Closing the original provider boundary
	** safely permits the next startup movie to run; it must not silently turn
	** a failed EA movie upload into a forced skip of the Renegade intro. */
	Release_Decoder_State();
	g_active = false;
	g_complete = true;
}

} // namespace

void BINKMovie::Init()
{
	g_initialized = true;
	av_log_set_level(AV_LOG_ERROR);
	A4_Frontend_Record_Bink_Init(true);
}

void BINKMovie::Shutdown()
{
	Stop();
	g_initialized = false;
	A4_Frontend_Record_Bink_Init(false);
}

void BINKMovie::Play(const char *filename, const char *, FontCharsClass *)
{
	Stop();
	Copy_Movie_Name(filename);
	Reset_Playback_Statistics();
	A4_Frontend_Record_Bink_Play(filename);
	g_complete = false;
	if (!g_initialized || filename == NULL) {
		Mark_Failed("provider not initialized or filename missing");
		return;
	}
	const RenegadeResolvedPath resolved = Renegade_Resolve_Path(kVitaRoots,
		filename, RENEGADE_PATH_READ);
	if (!resolved.success || !resolved.existing_case_matched) {
		Mark_Failed("retail movie path unavailable");
		return;
	}
	char ffmpeg_url[sizeof(resolved.physical) + 6U] = {};
	const char *open_url = Build_FFmpeg_File_URL(resolved, ffmpeg_url,
		sizeof(ffmpeg_url));
	int result = avformat_open_input(&g_format, open_url, NULL, NULL);
	if (result < 0) {
		Log_FFmpeg_Error("avformat_open_input", result);
		A30_Vita_Log("A4 Bink: movie open path logical=%s physical=%s url=%s\n",
			resolved.normalized_logical, resolved.physical, open_url);
		Mark_Failed("movie open failed");
		return;
	}
	result = avformat_find_stream_info(g_format, NULL);
	if (result < 0) {
		Log_FFmpeg_Error("avformat_find_stream_info", result);
		Mark_Failed("stream discovery failed");
		return;
	}
	g_video_stream = av_find_best_stream(g_format, AVMEDIA_TYPE_VIDEO,
		-1, -1, NULL, 0);
	g_audio_stream = av_find_best_stream(g_format, AVMEDIA_TYPE_AUDIO,
		-1, -1, NULL, 0);
	if (g_video_stream < 0 || !Open_Decoder(&g_video_decoder,
			g_format->streams[g_video_stream])) {
		Mark_Failed("Bink video decoder unavailable");
		return;
	}
	g_video_width = g_video_decoder->width;
	g_video_height = g_video_decoder->height;
	if (g_video_width <= 0 || g_video_height <= 0) {
		Mark_Failed("invalid movie dimensions");
		return;
	}
	const AVRational rate = av_guess_frame_rate(g_format,
		g_format->streams[g_video_stream], NULL);
	if (rate.num > 0 && rate.den > 0) {
		g_frame_duration_us = av_rescale_q(1, av_inv_q(rate),
			AVRational{1, 1000000});
	}
	g_video_frame = av_frame_alloc();
	g_audio_frame = av_frame_alloc();
	g_packet = av_packet_alloc();
	g_packet_pending = false;
	if (g_video_frame == NULL || g_audio_frame == NULL || g_packet == NULL) {
		Mark_Failed("decoder allocation failed");
		return;
	}

	bool audio_ready = false;
	if (g_audio_stream >= 0 && Open_Decoder(&g_audio_decoder,
			g_format->streams[g_audio_stream])) {
		audio_ready = Configure_Audio();
	}
	if (!audio_ready) {
		g_audio_enabled = false;
		g_audio_drained.store(true, std::memory_order_release);
	}
	g_start_us = static_cast<int64_t>(sceKernelGetProcessTimeWide());
	Prime_Skip_Button_Latch();
	g_active = true;
	g_complete = false;
	A30_Vita_Log("A4 Bink: playback started movie=%s path=%s video=%dx%d frame_us=%lld audio=%d\n",
		g_movie_name, resolved.physical, g_video_width, g_video_height,
		static_cast<long long>(g_frame_duration_us), audio_ready ? 1 : 0);
}

void BINKMovie::Stop()
{
	const bool skipped = g_active && !g_complete;
	if (skipped) A4_Frontend_Record_Bink_Skip(g_movie_name);
	if (g_active) Log_Playback_Statistics(skipped ? "skip-or-stop" : "complete");
	Release_Decoder_State();
	g_active = false;
	g_complete = true;
	if (skipped) A30_Vita_Log("A4 Bink: playback stopped early movie=%s\n", g_movie_name);
}

void BINKMovie::Update()
{
	if (!g_active || g_complete || g_format == NULL) return;
	if (!g_update_entry_logged) {
		A30_Vita_Log("A4 Bink: update entry movie=%s audio=%d pending_packet=%d pending_video=%d texture=%d\n",
			g_movie_name, g_audio_enabled ? 1 : 0,
			g_packet_pending ? 1 : 0, g_pending_video ? 1 : 0,
			g_texture_allocated ? 1 : 0);
		g_update_entry_logged = true;
	}
	if (Check_Skip_Request()) return;
	const int64_t elapsed_us = static_cast<int64_t>(sceKernelGetProcessTimeWide()) - g_start_us;
	const int64_t update_start_us = static_cast<int64_t>(sceKernelGetProcessTimeWide());
	for (unsigned iteration = 0U; iteration < 16U; ++iteration) {
		if (iteration != 0U) {
			if (Check_Skip_Request()) return;
			const int64_t update_elapsed_us =
				static_cast<int64_t>(sceKernelGetProcessTimeWide()) - update_start_us;
			if (update_elapsed_us >= kUpdateBudgetUs) {
				if (!g_update_budget_logged) {
					A30_Vita_Log("A4 Bink: update budget yield after %u iterations elapsed_us=%lld movie=%s\n",
						iteration, static_cast<long long>(update_elapsed_us),
						g_movie_name[0] != '\0' ? g_movie_name : "none");
					g_update_budget_logged = true;
				}
				break;
			}
		}
		if (g_pending_video) {
			if (g_pending_video_pts_us > elapsed_us + kPresentationToleranceUs &&
				g_texture_allocated) break;
			if (!Upload_Pending_Video()) {
				Mark_Failed("video texture upload failed");
				return;
			}
			continue;
		}
		if (g_demux_eof.load(std::memory_order_acquire)) {
			Flush_Decoders();
			if (Receive_Video_Frame()) continue;
			const bool audio_done = !g_audio_enabled ||
				g_audio_drained.load(std::memory_order_acquire);
			if (audio_done) {
				g_complete = true;
				A30_Vita_Log("A4 Bink: playback complete movie=%s frames=%llu\n",
					g_movie_name, static_cast<unsigned long long>(g_decoded_video_frames));
			}
			break;
		}

			if (!g_packet_pending) {
				if (!g_demux_read_entry_logged) {
					A30_Vita_Log("A4 Bink: first av_read_frame entry movie=%s\n", g_movie_name);
					g_demux_read_entry_logged = true;
				}
				const int read_result = av_read_frame(g_format, g_packet);
				if (read_result < 0) {
					g_demux_eof.store(true, std::memory_order_release);
					continue;
			}
			g_packet_pending = true;
		}
		bool packet_consumed = true;
		if (g_packet->stream_index == g_video_stream) {
			packet_consumed = Submit_Video_Packet();
		} else if (g_packet->stream_index == g_audio_stream &&
			g_audio_decoder != NULL && g_audio_enabled) {
			packet_consumed = Submit_Audio_Packet();
		}
		if (!packet_consumed) {
			break;
		}
		av_packet_unref(g_packet);
		g_packet_pending = false;
	}
}

void BINKMovie::Render()
{
	if (g_active && !g_render_entry_logged) {
		A30_Vita_Log("A4 Bink: render entry movie=%s texture=%d pending_video=%d\n",
			g_movie_name, g_texture_allocated ? 1 : 0,
			g_pending_video ? 1 : 0);
		g_render_entry_logged = true;
	}
	if (!g_active || !g_texture_allocated || g_video_texture == 0U) return;
	const GLfloat max_u = g_texture_width > 0 ?
		static_cast<GLfloat>(g_video_width) / static_cast<GLfloat>(g_texture_width) : 1.0F;
	const GLfloat max_v = g_texture_height > 0 ?
		static_cast<GLfloat>(g_video_height) / static_cast<GLfloat>(g_texture_height) : 1.0F;
	const GLfloat scale = std::min(960.0F / static_cast<GLfloat>(g_video_width),
		544.0F / static_cast<GLfloat>(g_video_height));
	const GLfloat draw_width = static_cast<GLfloat>(g_video_width) * scale;
	const GLfloat draw_height = static_cast<GLfloat>(g_video_height) * scale;
	const GLfloat draw_x = (960.0F - draw_width) * 0.5F;
	const GLfloat draw_y = (544.0F - draw_height) * 0.5F;
	GLint previous_viewport[4] = {};
	GLint previous_matrix_mode = GL_MODELVIEW;
	GLint previous_active_texture = GL_TEXTURE0;
	GLint previous_texture = 0;
	GLboolean texture0_enabled = GL_FALSE;
	GLfloat previous_color[4] = {1.0F, 1.0F, 1.0F, 1.0F};
	glGetIntegerv(GL_VIEWPORT, previous_viewport);
	glGetIntegerv(GL_MATRIX_MODE, &previous_matrix_mode);
	glGetIntegerv(GL_ACTIVE_TEXTURE, &previous_active_texture);
	glGetFloatv(GL_CURRENT_COLOR, previous_color);
	const GLboolean depth_enabled = glIsEnabled(GL_DEPTH_TEST);
	const GLboolean cull_enabled = glIsEnabled(GL_CULL_FACE);
	const GLboolean blend_enabled = glIsEnabled(GL_BLEND);
	glViewport(0, 0, 960, 544);
	glDisable(GL_DEPTH_TEST);
	glDisable(GL_CULL_FACE);
	glDisable(GL_BLEND);
	glActiveTexture(GL_TEXTURE0);
	texture0_enabled = glIsEnabled(GL_TEXTURE_2D);
	glGetIntegerv(GL_TEXTURE_BINDING_2D, &previous_texture);
	glEnable(GL_TEXTURE_2D);
	glBindTexture(GL_TEXTURE_2D, g_video_texture);
	RenegadeVitaRenderer::Invalidate_Texture_State_Cache();
	glMatrixMode(GL_PROJECTION);
	glPushMatrix();
	glLoadIdentity();
	glOrtho(0.0, 960.0, 544.0, 0.0, -1.0, 1.0);
	glMatrixMode(GL_MODELVIEW);
	glPushMatrix();
	glLoadIdentity();
	glColor4ub(255, 255, 255, 255);
	glBegin(GL_TRIANGLE_STRIP);
	glTexCoord2f(0.0F, 0.0F); glVertex3f(draw_x, draw_y, 0.0F);
	glTexCoord2f(max_u, 0.0F); glVertex3f(draw_x + draw_width, draw_y, 0.0F);
	glTexCoord2f(0.0F, max_v); glVertex3f(draw_x, draw_y + draw_height, 0.0F);
	glTexCoord2f(max_u, max_v); glVertex3f(draw_x + draw_width, draw_y + draw_height, 0.0F);
	glEnd();
	glPopMatrix();
	glMatrixMode(GL_PROJECTION);
	glPopMatrix();
	glColor4f(previous_color[0], previous_color[1], previous_color[2], previous_color[3]);
	glBindTexture(GL_TEXTURE_2D, static_cast<GLuint>(previous_texture));
	if (texture0_enabled) {
		glEnable(GL_TEXTURE_2D);
	} else {
		glDisable(GL_TEXTURE_2D);
	}
	glActiveTexture(static_cast<GLenum>(previous_active_texture));
	RenegadeVitaRenderer::Invalidate_Texture_State_Cache();
	glMatrixMode(static_cast<GLenum>(previous_matrix_mode));
	if (depth_enabled) glEnable(GL_DEPTH_TEST);
	if (cull_enabled) glEnable(GL_CULL_FACE);
	if (blend_enabled) glEnable(GL_BLEND);
	glViewport(previous_viewport[0], previous_viewport[1],
		previous_viewport[2], previous_viewport[3]);
}

bool BINKMovie::Is_Complete()
{
	return g_complete;
}

#else

#if defined(RENEGADE_HOST_ABI_TEST)
#include <stdio.h>
#else
#include "vita/a30_vita_runtime.h"
#endif

namespace {
bool g_initialized = false;

void Log_Unsupported_Playback(const char *filename)
{
#if defined(RENEGADE_HOST_ABI_TEST)
	fprintf(stderr,
		"A4 Bink boundary: playback skipped (%s); decoder provider unavailable; original menu route continues\n",
		filename != NULL ? filename : "unnamed");
#else
	A30_Vita_Log(
		"A4 Bink boundary: playback skipped (%s); decoder provider unavailable; original menu route continues\n",
		filename != NULL ? filename : "unnamed");
#endif
}
} // namespace

void BINKMovie::Init()
{
	g_initialized = true;
	A4_Frontend_Record_Bink_Init(true);
}

void BINKMovie::Shutdown()
{
	g_initialized = false;
	A4_Frontend_Record_Bink_Init(false);
}

void BINKMovie::Play(const char *filename, const char *, FontCharsClass *)
{
	A4_Frontend_Record_Bink_Play(filename);
	Log_Unsupported_Playback(filename);
	A4_Frontend_Record_Bink_Skip(filename);
}

void BINKMovie::Stop() {}
void BINKMovie::Update() {}
void BINKMovie::Render() {}
bool BINKMovie::Is_Complete() { return true; }

#endif
