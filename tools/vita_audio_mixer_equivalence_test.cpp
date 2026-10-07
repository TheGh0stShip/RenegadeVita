// The specialised mixer must reproduce the original per-frame mixer bit for
// bit (output, cursor doubles, loop state, statistics and MPEG decode request
// order), and the shared decoded-PCM cache must keep ownership and memory
// bounded. The provider is included directly to reach its internal state.
#include "../port/audio/vita/renegade_miles_provider.cpp"

#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <utility>
#include <vector>

#define CHECK(condition) do { if (!(condition)) { \
	std::fprintf(stderr, "check failed at line %d: %s\n", __LINE__, #condition); \
	std::abort(); } } while (0)

namespace {

// ---------------------------------------------------------------------------
// Original mixer, verbatim apart from reading PCM from the shared image.

int16_t Reference_Source_Sample(const RenegadeMilesSample *sample, size_t frame,
	uint16_t output_channel)
{
	const size_t frames = Sample_Frame_Count(sample);
	if (frames == 0) return 0;
	frame = std::min(frame, frames - 1U);
	const uint16_t source_channel = sample->wave.channels == 1
		? 0 : std::min<uint16_t>(output_channel, sample->wave.channels - 1U);
	if (sample->mpeg) return sample->mpeg->Sample(frame, source_channel);
	return sample->pcm->wave.samples[frame * sample->wave.channels + source_channel];
}

void Reference_Mix_Locked(int16_t *output, size_t frames)
{
	if (frames > kOutputFrames) return;
	std::fill(output, output + frames * 2U, 0);
	int32_t accumulator[kOutputFrames * 2U] = {};
	int32_t stream_accumulator[kOutputFrames * 2U] = {};
	bool stream_mix_attempted = false;
	uint32_t stream_mix_peak_abs = 0U;
	for (RenegadeMilesSample *sample : g_samples) {
		if (sample == nullptr || !sample->playing || sample->paused ||
			Sample_Frame_Count(sample) == 0) continue;
		const bool is_stream = sample->streaming;
		if (is_stream) stream_mix_attempted = true;
		const double step = static_cast<double>(
			sample->playback_rate > 0 ? sample->playback_rate :
			static_cast<S32>(sample->wave.sample_rate)) / kOutputRate;
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
			const size_t source_frames = Sample_Frame_Count(sample);
			while (sample->cursor >= source_frames) {
				if (!Advance_Loop(sample)) break;
			}
			if (!sample->playing) break;
			const size_t first = static_cast<size_t>(sample->cursor);
			const size_t second = std::min(first + 1U, source_frames - 1U);
			const float fraction = static_cast<float>(sample->cursor - first);
			for (uint16_t channel = 0; channel < 2; ++channel) {
				const float start = Reference_Source_Sample(sample, first, channel);
				const float end = Reference_Source_Sample(sample, second, channel);
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
	} else {
		g_stats.last_stream_mix_active = 0U;
		g_stats.last_stream_mix_frames = 0U;
		g_stats.last_stream_mix_nonzero = 0U;
		g_stats.last_stream_mix_peak_abs = 0U;
	}
}

// ---------------------------------------------------------------------------

struct Random {
	uint64_t state;
	uint32_t Next()
	{
		state = state * 6364136223846793005ULL + 1442695040888963407ULL;
		return static_cast<uint32_t>(state >> 33U);
	}
	uint32_t Below(uint32_t bound) { return bound == 0U ? 0U : Next() % bound; }
	float Unit() { return static_cast<float>(Next() & 0xffffffU) / 16777216.0F; }
};

std::vector<uint8_t> Pcm_Wave(uint16_t channels, uint32_t rate, uint32_t frames, uint64_t seed)
{
	const uint32_t data_bytes = frames * channels * 2U;
	std::vector<uint8_t> image(44U + data_bytes);
	auto put32 = [&](size_t at, uint32_t value) {
		for (unsigned i = 0; i < 4U; ++i) image[at + i] = static_cast<uint8_t>(value >> (8U * i));
	};
	auto put16 = [&](size_t at, uint16_t value) {
		image[at] = static_cast<uint8_t>(value);
		image[at + 1U] = static_cast<uint8_t>(value >> 8U);
	};
	std::memcpy(&image[0], "RIFF", 4); put32(4, 36U + data_bytes);
	std::memcpy(&image[8], "WAVEfmt ", 8); put32(16, 16U);
	put16(20, 1U); put16(22, channels); put32(24, rate);
	put32(28, rate * channels * 2U); put16(32, static_cast<uint16_t>(channels * 2U));
	put16(34, 16U); std::memcpy(&image[36], "data", 4); put32(40, data_bytes);
	Random random{seed};
	for (uint32_t index = 0; index < frames * channels; ++index) {
		const uint32_t pick = random.Below(16U);
		const int16_t value = pick == 0U ? 32767 : pick == 1U ? -32768 :
			pick == 2U ? 0 : static_cast<int16_t>(random.Next());
		put16(44U + index * 2U, static_cast<uint16_t>(value));
	}
	return image;
}

// Deterministic fake compressed music that records every decode request.
class FakeMpeg final : public RenegadeVitaAudio::MpegPlayback {
public:
	FakeMpeg(size_t frames, uint16_t channels, uint32_t rate, std::vector<uint64_t> *log)
		: frames_(frames), channels_(channels), rate_(rate), log_(log) {}
	size_t Frame_Count() const override { return frames_; }
	uint32_t Sample_Rate() const override { return rate_; }
	uint16_t Channels() const override { return channels_; }
	size_t PCM_Storage_Bytes() const override { return 0U; }
	int16_t Sample(size_t frame, uint16_t channel) override
	{
		log_->push_back(static_cast<uint64_t>(frame) * 4U + channel);
		return static_cast<int16_t>((frame * 7919U + channel * 104729U) & 0xffffU);
	}
private:
	size_t frames_;
	uint16_t channels_;
	uint32_t rate_;
	std::vector<uint64_t> *log_;
};

struct VoiceState {
	double cursor;
	U32 loops_remaining;
	bool playing;
	bool paused;
};

struct RunResult {
	std::vector<int16_t> output;
	std::vector<VoiceState> voices;
	std::vector<uint64_t> mpeg_log;
	RenegadeMilesRuntimeStats stats;
};

// The WAVE parser accepts 8-192 kHz and one or two channels; odd rates are
// reached through playback-rate overrides.
const uint32_t kRates[] = { 8000U, 11025U, 22050U, 44100U, 48000U, 96000U, 47999U, 32000U, 192000U };

RunResult Run_Scenario(uint64_t seed, bool reference)
{
	RunResult result;
	Random random{seed};
	const unsigned voices = 1U + random.Below(12U);
	std::vector<RenegadeMilesSample *> samples;
	for (unsigned voice = 0; voice < voices; ++voice) {
		RenegadeMilesSample *sample = AIL_allocate_sample_handle(nullptr);
		CHECK(sample != nullptr);
		samples.push_back(sample);
		const bool mpeg = random.Below(8U) == 0U;
		const uint16_t channels = static_cast<uint16_t>(1U + random.Below(2U));
		const uint32_t rate = kRates[random.Below(sizeof(kRates) / sizeof(kRates[0]))];
		const uint32_t frames = 1U + (random.Below(4U) == 0U ? random.Below(4U) : random.Below(3000U));
		if (mpeg) {
			const uint16_t mpeg_channels = static_cast<uint16_t>(1U + random.Below(2U));
			sample->mpeg.reset(new FakeMpeg(frames, mpeg_channels, rate, &result.mpeg_log));
			sample->wave = {};
			sample->wave.channels = mpeg_channels;
			sample->wave.sample_rate = rate;
			sample->playback_rate = static_cast<S32>(rate);
		} else {
			// A few voices share one image so the cache path is exercised.
			const uint64_t image_seed = random.Below(3U) == 0U ? 77U : seed * 131U + voice;
			const std::vector<uint8_t> image = image_seed == 77U ?
				Pcm_Wave(2U, 22050U, 1500U, 77U) : Pcm_Wave(channels, rate, frames, image_seed);
			CHECK(AIL_set_named_sample_file(sample, nullptr, image.data(),
				static_cast<U32>(image.size()), 0) == 1);
		}
		const size_t total = Sample_Frame_Count(sample);
		if (random.Below(3U) == 0U) sample->playback_rate = 1 + static_cast<S32>(random.Below(100000U));
		const uint32_t loop_pick = random.Below(6U);
		const U32 loops = loop_pick == 0U ? 0U : loop_pick == 1U ? 7U : loop_pick;
		sample->loop_count = loops;
		sample->loops_remaining = random.Below(4U) == 0U ? random.Below(3U) : loops;
		const uint32_t cursor_pick = random.Below(5U);
		sample->cursor = cursor_pick == 0U ? 0.0 :
			cursor_pick == 1U ? static_cast<double>(total) - random.Unit() * 3.0 :
			cursor_pick == 2U ? static_cast<double>(total + random.Below(5U)) :
			static_cast<double>(random.Unit()) * static_cast<double>(total);
		if (sample->cursor < 0.0) sample->cursor = 0.0;
		const uint32_t volume_pick = random.Below(5U);
		sample->volume = volume_pick == 0U ? 0 : volume_pick == 1U ? 127 :
			static_cast<S32>(random.Below(128U));
		sample->pan = random.Below(4U) == 0U ? 64 : static_cast<S32>(random.Below(128U));
		sample->spatial = random.Below(2U) == 0U;
		sample->maximum_distance = random.Unit() * 60.0F;
		sample->minimum_distance = random.Unit() * 20.0F;
		for (float &axis : sample->position) axis = (random.Unit() - 0.5F) * 80.0F;
		sample->streaming = random.Below(3U) == 0U;
		sample->playing = random.Below(8U) != 0U;
		sample->paused = random.Below(10U) == 0U;
	}
	g_stats = {};
	const unsigned buffers = 1U + random.Below(6U);
	for (unsigned buffer = 0; buffer < buffers; ++buffer) {
		const size_t frames = random.Below(10U) == 0U ? kOutputFrames + 1U :
			1U + random.Below(static_cast<uint32_t>(kOutputFrames));
		std::vector<int16_t> output(kOutputFrames * 2U + 2U, 0x5a5a);
		if (reference) Reference_Mix_Locked(output.data(), frames);
		else Mix_Locked(output.data(), frames);
		result.output.insert(result.output.end(), output.begin(), output.end());
	}
	for (RenegadeMilesSample *sample : samples) {
		result.voices.push_back({sample->cursor, sample->loops_remaining,
			sample->playing, sample->paused});
	}
	result.stats = g_stats;
	for (RenegadeMilesSample *sample : samples) AIL_release_sample_handle(sample);
	return result;
}

bool Same_Mix_Stats(const RenegadeMilesRuntimeStats &a, const RenegadeMilesRuntimeStats &b)
{
	return a.mixed_buffers == b.mixed_buffers && a.mixed_frames == b.mixed_frames &&
		a.mixed_nonzero_buffers == b.mixed_nonzero_buffers &&
		a.mixed_peak_abs == b.mixed_peak_abs &&
		a.stream_mixed_buffers == b.stream_mixed_buffers &&
		a.stream_mixed_frames == b.stream_mixed_frames &&
		a.stream_mixed_nonzero_buffers == b.stream_mixed_nonzero_buffers &&
		a.stream_mixed_peak_abs == b.stream_mixed_peak_abs &&
		a.last_stream_mix_active == b.last_stream_mix_active &&
		a.last_stream_mix_frames == b.last_stream_mix_frames &&
		a.last_stream_mix_nonzero == b.last_stream_mix_nonzero &&
		a.last_stream_mix_peak_abs == b.last_stream_mix_peak_abs;
}

void Check_Mixer_Equivalence(unsigned scenarios)
{
	for (unsigned scenario = 0; scenario < scenarios; ++scenario) {
		const uint64_t seed = 0x51ed2701ULL + scenario * 7919ULL;
		const RunResult fast = Run_Scenario(seed, false);
		const RunResult reference = Run_Scenario(seed, true);
		if (fast.output != reference.output || fast.mpeg_log != reference.mpeg_log ||
			!Same_Mix_Stats(fast.stats, reference.stats) ||
			fast.voices.size() != reference.voices.size()) {
			std::fprintf(stderr, "mixer mismatch in scenario %u\n", scenario);
			std::abort();
		}
		for (size_t voice = 0; voice < fast.voices.size(); ++voice) {
			const VoiceState &a = fast.voices[voice];
			const VoiceState &b = reference.voices[voice];
			if (std::memcmp(&a.cursor, &b.cursor, sizeof(double)) != 0 ||
				a.loops_remaining != b.loops_remaining || a.playing != b.playing ||
				a.paused != b.paused) {
				std::fprintf(stderr, "voice state mismatch in scenario %u voice %zu\n",
					scenario, voice);
				std::abort();
			}
		}
	}
	std::printf("audio mixer equivalence PASS scenarios=%u\n", scenarios);
}

// ---------------------------------------------------------------------------

void Check_Pcm_Cache()
{
	AIL_shutdown();
	AIL_startup();
	Renegade_Miles_Reset_Runtime_Stats();
	RenegadeMilesRuntimeStats stats = {};
	const std::vector<uint8_t> shot = Pcm_Wave(1U, 22050U, 4000U, 9U);
	HSAMPLE a = AIL_allocate_sample_handle(nullptr);
	HSAMPLE b = AIL_allocate_sample_handle(nullptr);
	CHECK(AIL_set_named_sample_file(a, nullptr, shot.data(), static_cast<U32>(shot.size()), 0));
	CHECK(AIL_set_named_sample_file(b, nullptr, shot.data(), static_cast<U32>(shot.size()), 0));
	Renegade_Miles_Get_Runtime_Stats(&stats);
	CHECK(stats.pcm_decodes == 1U && stats.pcm_cache_hits == 1U);
	CHECK(stats.pcm_cache_entries == 1U && stats.pcm_cache_bytes > 8000U);
	CHECK(a->pcm == b->pcm && a->pcm->references == 3U && a->pcm->cached);
	CHECK(a->encoded_data_bytes == 8000U && b->wave.sample_rate == 22050U);
	CHECK(a->wave.samples.empty() && Sample_Frame_Count(b) == 4000U);

	// A copy of the image at another address is the same content.
	std::vector<uint8_t> copy = shot;
	HSAMPLE c = AIL_allocate_sample_handle(nullptr);
	CHECK(AIL_set_named_sample_file(c, nullptr, copy.data(), static_cast<U32>(copy.size()), 0));
	CHECK(c->pcm == a->pcm);
	// One changed byte is a different image.
	copy[44U + 1000U] ^= 0x40U;
	CHECK(AIL_set_named_sample_file(c, nullptr, copy.data(), static_cast<U32>(copy.size()), 0));
	CHECK(c->pcm != a->pcm && c->pcm->wave.samples[500] != a->pcm->wave.samples[500]);
	Renegade_Miles_Get_Runtime_Stats(&stats);
	CHECK(stats.pcm_decodes == 2U && stats.pcm_cache_hits == 2U && stats.pcm_cache_entries == 2U);

	// A failed decode keeps the voice's previous image.
	RenegadeMilesPcm *before = c->pcm;
	std::vector<uint8_t> broken = copy;
	std::memcpy(&broken[36], "junk", 4);
	CHECK(AIL_set_named_sample_file(c, nullptr, broken.data(), static_cast<U32>(broken.size()), 0) == 0);
	CHECK(c->pcm == before && Sample_Frame_Count(c) == 4000U);

	// Reinitialising and releasing voices drops their references only.
	AIL_init_sample(a);
	CHECK(a->pcm == nullptr && b->pcm->references == 2U);
	AIL_release_sample_handle(b);
	CHECK(g_pcm_cache_bytes != 0U);

	// Idle images are evicted least recently used first; playing ones never.
	HSAMPLE keep = AIL_allocate_sample_handle(nullptr);
	const std::vector<uint8_t> big = Pcm_Wave(2U, 44100U, 200000U, 11U);
	CHECK(AIL_set_named_sample_file(keep, nullptr, big.data(), static_cast<U32>(big.size()), 0));
	RenegadeMilesPcm *kept = keep->pcm;
	CHECK(kept->cached);
	for (unsigned image = 0; image < 40U; ++image) {
		const std::vector<uint8_t> other = Pcm_Wave(2U, 44100U, 100000U, 100U + image);
		CHECK(AIL_set_named_sample_file(a, nullptr, other.data(), static_cast<U32>(other.size()), 0));
		CHECK(g_pcm_cache_bytes <= kPcmCacheBudgetBytes);
	}
	Renegade_Miles_Get_Runtime_Stats(&stats);
	CHECK(stats.pcm_cache_evictions != 0U && kept->cached && keep->pcm == kept);
	CHECK(Find_Cached_Pcm(Hash_Image(big.data(), big.size()), big.size()) == kept);
	CHECK(Find_Cached_Pcm(Hash_Image(shot.data(), shot.size()), shot.size()) == nullptr);

	// Images too large to retain are decoded per use and freed with the voice.
	const std::vector<uint8_t> huge = Pcm_Wave(2U, 44100U, 400000U, 12U);
	CHECK(huge.size() > kPcmCacheMaximumSourceBytes);
	const uint32_t decodes_before = stats.pcm_decodes;
	CHECK(AIL_set_named_sample_file(c, nullptr, huge.data(), static_cast<U32>(huge.size()), 0));
	CHECK(AIL_set_named_sample_file(a, nullptr, huge.data(), static_cast<U32>(huge.size()), 0));
	CHECK(!c->pcm->cached && c->pcm != a->pcm && c->pcm->references == 1U);
	Renegade_Miles_Get_Runtime_Stats(&stats);
	CHECK(stats.pcm_decodes == decodes_before + 2U);

	// Mixing a shared image from two voices matches mixing each alone.
	AIL_set_named_sample_file(a, nullptr, shot.data(), static_cast<U32>(shot.size()), 0);
	AIL_set_named_sample_file(c, nullptr, shot.data(), static_cast<U32>(shot.size()), 0);
	CHECK(a->pcm == c->pcm);
	AIL_release_sample_handle(keep);
	AIL_start_sample(a);
	AIL_start_sample(c);
	int16_t mixed[256 * 2];
	CHECK(Renegade_Miles_Mix_For_Test(mixed, 256U));
	CHECK(a->cursor == c->cursor && a->cursor > 0.0);

	AIL_release_sample_handle(a);
	AIL_release_sample_handle(c);
	AIL_shutdown();
	CHECK(g_pcm_cache_bytes == 0U);
	for (RenegadeMilesPcm *pcm : g_pcm_cache) CHECK(pcm == nullptr);
	std::printf("audio pcm cache PASS\n");
}

} // namespace

int main(int argc, char **argv)
{
	AIL_startup();
	const unsigned scenarios = argc > 1 ? static_cast<unsigned>(std::strtoul(argv[1], nullptr, 10)) : 3000U;
	Check_Mixer_Equivalence(scenarios);
	Check_Pcm_Cache();
	return 0;
}
