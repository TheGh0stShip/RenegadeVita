#include "binkmovie.h"
#include "a4_frontend_lifecycle_boundary.h"

#if defined(__vita__) && defined(RENEGADE_A4_BINK_FFMPEG)

#include "renegade_paths.h"
#include "vita/a30_vita_runtime.h"

#include <algorithm>
#include <atomic>
#include <errno.h>
#include <pthread.h>
#include <stdint.h>
#include <string.h>
#include <vector>

#include <psp2/audioout.h>
#include <psp2/kernel/processmgr.h>
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
	const size_t accepted = std::min(sample_count, capacity - g_audio_count);
	for (size_t index = 0U; index < accepted; ++index) {
		g_audio_ring[g_audio_write] = samples[index];
		g_audio_write = (g_audio_write + 1U) % capacity;
	}
	g_audio_count += accepted;
	pthread_mutex_unlock(&g_audio_mutex);
	if (accepted != sample_count && !g_audio_drop_logged) {
		A30_Vita_Log("A4 Bink: audio ring full; dropped=%u samples movie=%s\n",
			static_cast<unsigned>(sample_count - accepted), g_movie_name);
		g_audio_drop_logged = true;
	}
}

void *Audio_Output_Thread(void *)
{
	std::vector<int16_t> output(kAudioFramesPerBuffer * kAudioChannels, 0);
	while (!g_audio_stop.load(std::memory_order_acquire)) {
		std::fill(output.begin(), output.end(), 0);
		pthread_mutex_lock(&g_audio_mutex);
		const size_t copied = std::min(output.size(), g_audio_count);
		for (size_t index = 0U; index < copied; ++index) {
			output[index] = g_audio_ring[g_audio_read];
			g_audio_read = (g_audio_read + 1U) % g_audio_ring.size();
		}
		g_audio_count -= copied;
		const bool drained = g_demux_eof.load(std::memory_order_acquire) &&
			g_audio_count == 0U;
		pthread_mutex_unlock(&g_audio_mutex);
		if (drained) g_audio_drained.store(true, std::memory_order_release);
		if (g_audio_port >= 0) {
			const int result = sceAudioOutOutput(g_audio_port, output.data());
			if (result < 0) {
				A30_Vita_Log("A4 Bink: sceAudioOutOutput failed code=%08X\n",
					static_cast<unsigned>(result));
				break;
			}
		}
	}
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
	g_audio_port = sceAudioOutOpenPort(SCE_AUDIO_OUT_PORT_TYPE_BGM,
		kAudioFramesPerBuffer, kAudioRate, SCE_AUDIO_OUT_MODE_STEREO);
	if (g_audio_port < 0) {
		A30_Vita_Log("A4 Bink: sceAudioOutOpenPort failed code=%08X; video continues\n",
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
			Queue_Audio(converted.data(), static_cast<size_t>(frames) * kAudioChannels);
		}
		av_frame_unref(g_audio_frame);
	}
}

bool Receive_Video_Frame()
{
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
	av_frame_unref(g_video_frame);
	return true;
}

bool Upload_Pending_Video()
{
	if (!g_pending_video || g_pending_rgba.empty()) return false;
	if (g_video_texture == 0U) glGenTextures(1, &g_video_texture);
	if (g_video_texture == 0U) return false;
	GLint previous_active_texture = GL_TEXTURE0;
	GLint previous_texture = 0;
	GLint previous_unpack_alignment = 4;
	glGetIntegerv(GL_ACTIVE_TEXTURE, &previous_active_texture);
	glActiveTexture(GL_TEXTURE0);
	glGetIntegerv(GL_TEXTURE_BINDING_2D, &previous_texture);
	glGetIntegerv(GL_UNPACK_ALIGNMENT, &previous_unpack_alignment);
	glBindTexture(GL_TEXTURE_2D, g_video_texture);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);
	glPixelStorei(GL_UNPACK_ALIGNMENT, 1);
	if (!g_texture_allocated) {
		glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, g_video_width, g_video_height,
			0, GL_RGBA, GL_UNSIGNED_BYTE, g_pending_rgba.data());
		g_texture_allocated = true;
	} else {
		glTexSubImage2D(GL_TEXTURE_2D, 0, 0, 0, g_video_width, g_video_height,
			GL_RGBA, GL_UNSIGNED_BYTE, g_pending_rgba.data());
	}
	const GLenum upload_error = glGetError();
	glBindTexture(GL_TEXTURE_2D, static_cast<GLuint>(previous_texture));
	glPixelStorei(GL_UNPACK_ALIGNMENT, previous_unpack_alignment);
	glActiveTexture(static_cast<GLenum>(previous_active_texture));
	if (upload_error != GL_NO_ERROR) {
		A30_Vita_Log("A4 Bink: texture upload failed movie=%s\n", g_movie_name);
		return false;
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

void Mark_Failed(const char *reason)
{
	A30_Vita_Log("A4 Bink: playback skipped reason=%s movie=%s; original menu route continues\n",
		reason, g_movie_name[0] != '\0' ? g_movie_name : "unnamed");
	A4_Frontend_Record_Bink_Skip(g_movie_name);
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

	int result = avformat_open_input(&g_format, resolved.physical, NULL, NULL);
	if (result < 0) {
		Log_FFmpeg_Error("avformat_open_input", result);
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
	Release_Decoder_State();
	g_active = false;
	g_complete = true;
	if (skipped) A30_Vita_Log("A4 Bink: playback stopped early movie=%s\n", g_movie_name);
}

void BINKMovie::Update()
{
	if (!g_active || g_complete || g_format == NULL) return;
	const int64_t elapsed_us = static_cast<int64_t>(sceKernelGetProcessTimeWide()) - g_start_us;
	for (unsigned iteration = 0U; iteration < 64U; ++iteration) {
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
	if (!g_active || !g_texture_allocated || g_video_texture == 0U) return;
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
	glMatrixMode(GL_PROJECTION);
	glPushMatrix();
	glLoadIdentity();
	glOrtho(0.0, 960.0, 544.0, 0.0, -1.0, 1.0);
	glMatrixMode(GL_MODELVIEW);
	glPushMatrix();
	glLoadIdentity();
	glColor4ub(255, 255, 255, 255);
	glBegin(GL_TRIANGLE_STRIP);
	glTexCoord2f(0.0F, 0.0F); glVertex3f(0.0F, 0.0F, 0.0F);
	glTexCoord2f(1.0F, 0.0F); glVertex3f(960.0F, 0.0F, 0.0F);
	glTexCoord2f(0.0F, 1.0F); glVertex3f(0.0F, 544.0F, 0.0F);
	glTexCoord2f(1.0F, 1.0F); glVertex3f(960.0F, 544.0F, 0.0F);
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
