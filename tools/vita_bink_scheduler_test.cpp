#include <algorithm>
#include <atomic>
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <deque>
#include <vector>

struct AVPacket { int stream_index, size; int64_t pts; };
struct BINKMovie { static void Update(); };
constexpr size_t kAudioStartupSamples = 12288;
constexpr size_t kMaxPrefetchedVideoPackets = 16;
constexpr size_t kMaxPrefetchedVideoBytes = 8 * 1024 * 1024;
constexpr unsigned kMaxBinkUpdateIterations = 4;
constexpr int64_t kUpdateBudgetUs = 6000, kPresentationToleranceUs = 2000;
constexpr int64_t kVideoDropLatenessUs = 25000;
bool g_active = true, g_complete = false, g_audio_enabled = true;
bool g_update_entry_logged = false, g_update_budget_logged = false;
bool g_demux_read_entry_logged = false, g_video_drop_logged = false;
bool g_pending_video = false, g_packet_pending = false, g_texture_allocated = false;
bool g_video_prefetch_failed = false, clone_failure = false, skip_requested = false;
bool g_audio_thread_running = false;
std::atomic<bool> g_demux_eof(false), g_audio_drained(false);
const char *g_movie_name = "synthetic-bink";
int dummy, *g_format = &dummy, *g_audio_decoder = &dummy;
int *g_video_frame = &dummy;
unsigned released_video_frames = 0;
void av_frame_unref(int *frame) { assert(frame == g_video_frame); ++released_video_frames; }
int g_video_stream = 0, g_audio_stream = 1;
AVPacket packet = {};
AVPacket *g_packet = &packet;
std::deque<AVPacket *> g_prefetched_video_packets;
std::deque<AVPacket> source_packets;
size_t g_prefetched_video_bytes = 0, g_prefetched_video_high_water = 0, queued_audio = 0;
int64_t g_pending_video_pts_us = 0, g_frame_duration_us = 33333;
int64_t g_last_video_upload_elapsed_us = 0;
int64_t clock_start = -1, now_us = 1;
uint64_t g_decoded_video_frames = 0, g_uploaded_video_frames = 0, g_dropped_video_frames = 0;
std::vector<unsigned char> g_pending_video_pixels;
std::vector<int64_t> decoded_pts;
unsigned read_calls = 0, first_upload_audio_samples = 0;
void A30_Vita_Log(const char *, ...) {}
uint64_t sceKernelGetProcessTimeWide() { return now_us; }
bool Check_Skip_Request() { if (skip_requested) g_complete = true; return skip_requested; }
size_t Queued_Audio_Samples() { return queued_audio; }
bool Audio_Output_Under_Pressure() { return g_audio_thread_running && queued_audio < 6144; }
int64_t Current_Movie_Elapsed_Us() { return clock_start < 0 ? 0 : now_us - clock_start; }
void Mark_Failed(const char *) { g_active = false; g_complete = true; }
int av_read_frame(int *, AVPacket *out) {
	++read_calls;
	if (source_packets.empty()) return -1;
	*out = source_packets.front(); source_packets.pop_front(); return 0;
}
AVPacket *av_packet_clone(AVPacket *in) { return clone_failure ? nullptr : new AVPacket(*in); }
void av_packet_unref(AVPacket *in) { *in = {}; }
void av_packet_free(AVPacket **in) { delete *in; *in = nullptr; }
void av_packet_move_ref(AVPacket *out, AVPacket *in) { *out = *in; *in = {}; }
bool Submit_Audio_Packet() {
	queued_audio += 3200;
	if (queued_audio >= kAudioStartupSamples) {
		g_audio_thread_running = true;
		if (clock_start < 0) clock_start = now_us;
	}
	return true;
}
bool Submit_Video_Packet() {
	decoded_pts.push_back(g_packet->pts);
	g_pending_video_pts_us = g_packet->pts;
	g_pending_video = true;
	++g_decoded_video_frames;
	return true;
}
bool Upload_Pending_Video() {
	if (!g_uploaded_video_frames) first_upload_audio_samples = queued_audio;
	++g_uploaded_video_frames;
	g_last_video_upload_elapsed_us = Current_Movie_Elapsed_Us();
	g_pending_video = false;
	g_texture_allocated = true;
	if (clock_start < 0) clock_start = now_us;
	return true;
}
void Flush_Decoders() {}
bool Receive_Video_Frame() { return false; }
void Drain_Deferred_Audio_Output() { g_audio_drained.store(queued_audio == 0); }

#include "bink-scheduler-production.inc"

int main(int argc, char **argv) {
	assert(argc == 2);
	const char *test = argv[1];
	if (!std::strcmp(test, "interleaved-playback")) {
		for (int i = 0; i < 20; ++i) {
			source_packets.push_back({0, 1024, i * g_frame_duration_us});
			source_packets.push_back({1, 256, i * g_frame_duration_us});
		}
		for (int frame = 0; frame < 200 && !g_complete; ++frame) {
			BINKMovie::Update();
			if (g_audio_thread_running) queued_audio -= std::min(queued_audio, size_t(1600));
			now_us += 16667;
		}
		assert(g_complete && g_active);
		assert(first_upload_audio_samples >= kAudioStartupSamples);
		assert(decoded_pts.size() == 20);
		for (int i = 0; i < 20; ++i) assert(decoded_pts[i] == i * g_frame_duration_us);
		assert(g_prefetched_video_packets.empty() && g_prefetched_video_bytes == 0);
		std::printf("bink-schedule decoded=%llu uploaded=%llu dropped=%llu startup_audio=%u queue_high_water=%zu\n",
			static_cast<unsigned long long>(g_decoded_video_frames),
			static_cast<unsigned long long>(g_uploaded_video_frames),
			static_cast<unsigned long long>(g_dropped_video_frames),
			first_upload_audio_samples, g_prefetched_video_high_water);
	} else if (!std::strcmp(test, "early-frame")) {
		g_pending_video = g_texture_allocated = g_audio_thread_running = true;
		g_pending_video_pts_us = 100000;
		assert(!Drop_Pending_Video_If_Late(0));
		assert(g_pending_video);
	} else if (!std::strcmp(test, "late-frame-progress")) {
		g_texture_allocated = true;
		g_uploaded_video_frames = 1;
		clock_start = 0;
		for (int i = 1; i <= 120; ++i) {
			now_us = i * 50000LL + 50000;
			g_pending_video = true;
			g_pending_video_pts_us = i * g_frame_duration_us;
			if (!Drop_Pending_Video_If_Late(now_us)) Upload_Pending_Video();
			assert(now_us - g_last_video_upload_elapsed_us < 2 * g_frame_duration_us);
		}
		assert(g_uploaded_video_frames > 1 && g_dropped_video_frames > 0);
	} else if (!std::strcmp(test, "queue-limit")) {
		for (unsigned i = 0; i < kMaxPrefetchedVideoPackets; ++i)
			g_prefetched_video_packets.push_back(new AVPacket{0, 1, 0});
		assert(!Prefetch_Audio_For_Pending_Video() && read_calls == 0);
	} else if (!std::strcmp(test, "byte-limit")) {
		g_prefetched_video_bytes = kMaxPrefetchedVideoBytes - 10;
		source_packets.push_back({0, 11, 0});
		assert(!Prefetch_Audio_For_Pending_Video());
		assert(g_video_prefetch_failed && g_prefetched_video_packets.empty());
	} else if (!std::strcmp(test, "allocation-failure")) {
		clone_failure = true;
		source_packets.push_back({0, 1024, 0});
		g_pending_video = true;
		BINKMovie::Update();
		assert(g_complete && !g_active);
	} else if (!std::strcmp(test, "skip")) {
		skip_requested = true;
		BINKMovie::Update();
		assert(g_complete && read_calls == 0);
	} else return 2;
	for (AVPacket *saved : g_prefetched_video_packets) av_packet_free(&saved);
	std::printf("bink_scheduler=%s PASS\n", test);
}
