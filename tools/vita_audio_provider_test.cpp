#include "mss.h"
#include "renegade_miles_runtime_stats.h"
#include "renegade_miles_test.h"
#include "renegade_wave_decoder.h"

#include <algorithm>
#include <cstring>
#include <cstdint>
#include <cstdio>
#include <vector>

namespace {

void Write_U16(std::vector<uint8_t> &data, uint16_t value)
{
	data.push_back(static_cast<uint8_t>(value));
	data.push_back(static_cast<uint8_t>(value >> 8U));
}

void Write_U32(std::vector<uint8_t> &data, uint32_t value)
{
	data.push_back(static_cast<uint8_t>(value));
	data.push_back(static_cast<uint8_t>(value >> 8U));
	data.push_back(static_cast<uint8_t>(value >> 16U));
	data.push_back(static_cast<uint8_t>(value >> 24U));
}

void FourCC(std::vector<uint8_t> &data, const char text[5])
{
	for (int index = 0; index < 4; ++index) data.push_back(text[index]);
}

std::vector<uint8_t> Wave(uint16_t encoding, uint16_t channels,
	uint32_t rate, uint16_t block_align, uint16_t bits,
	const std::vector<uint8_t> &extension, const std::vector<uint8_t> &samples,
	uint32_t fact_frames = 0U)
{
	std::vector<uint8_t> result;
	FourCC(result, "RIFF");
	Write_U32(result, 0);
	FourCC(result, "WAVE");
	FourCC(result, "fmt ");
	Write_U32(result, static_cast<uint32_t>(16U + extension.size()));
	Write_U16(result, encoding);
	Write_U16(result, channels);
	Write_U32(result, rate);
	Write_U32(result, rate * block_align);
	Write_U16(result, block_align);
	Write_U16(result, bits);
	result.insert(result.end(), extension.begin(), extension.end());
	if (fact_frames != 0U) {
		FourCC(result, "fact");
		Write_U32(result, 4U);
		Write_U32(result, fact_frames);
	}
	FourCC(result, "data");
	Write_U32(result, static_cast<uint32_t>(samples.size()));
	result.insert(result.end(), samples.begin(), samples.end());
	if ((samples.size() & 1U) != 0U) result.push_back(0);
	const uint32_t riff_bytes = static_cast<uint32_t>(result.size() - 8U);
	result[4] = static_cast<uint8_t>(riff_bytes);
	result[5] = static_cast<uint8_t>(riff_bytes >> 8U);
	result[6] = static_cast<uint8_t>(riff_bytes >> 16U);
	result[7] = static_cast<uint8_t>(riff_bytes >> 24U);
	return result;
}

bool Require(bool condition, const char *message)
{
	if (!condition) std::fprintf(stderr, "audio provider test: %s\n", message);
	return condition;
}

std::vector<uint8_t> g_stream_fixture;
size_t g_stream_position = 0;
bool g_stream_open = false;

U32 AILCALLBACK Stream_Open(const char *name, U32 *handle)
{
	if (handle == nullptr || name == nullptr ||
		std::strcmp(name, "logan_test.wav") != 0) return 0U;
	g_stream_position = 0;
	g_stream_open = true;
	*handle = 1U;
	return 1U;
}

void AILCALLBACK Stream_Close(U32 handle)
{
	if (handle == 1U) g_stream_open = false;
}

S32 AILCALLBACK Stream_Seek(U32 handle, S32 offset, U32 type)
{
	if (handle != 1U || !g_stream_open) return -1;
	size_t next = g_stream_position;
	if (type == AIL_FILE_SEEK_BEGIN) {
		if (offset < 0) return -1;
		next = static_cast<size_t>(offset);
	} else if (type == AIL_FILE_SEEK_CURRENT) {
		const S32 current = static_cast<S32>(g_stream_position);
		if (offset < 0 && current < -offset) return -1;
		next = static_cast<size_t>(current + offset);
	} else if (type == AIL_FILE_SEEK_END) {
		const S32 end = static_cast<S32>(g_stream_fixture.size());
		if (offset < 0 && end < -offset) return -1;
		next = static_cast<size_t>(end + offset);
	} else {
		return -1;
	}
	if (next > g_stream_fixture.size()) return -1;
	g_stream_position = next;
	return static_cast<S32>(g_stream_position);
}

U32 AILCALLBACK Stream_Read(U32 handle, void *buffer, U32 bytes)
{
	if (handle != 1U || !g_stream_open || buffer == nullptr) return 0U;
	const size_t available = g_stream_fixture.size() - g_stream_position;
	const size_t count = std::min<size_t>(available, bytes);
	std::memcpy(buffer, g_stream_fixture.data() + g_stream_position, count);
	g_stream_position += count;
	return static_cast<U32>(count);
}

} // namespace

int main()
{
	using RenegadeVitaAudio::DecodedWave;
	bool passed = true;

	std::vector<uint8_t> pcm_samples;
	for (int16_t sample : { int16_t(1000), int16_t(-1000), int16_t(2000), int16_t(-2000) }) {
		Write_U16(pcm_samples, static_cast<uint16_t>(sample));
	}
	const std::vector<uint8_t> pcm = Wave(1, 1, 48000, 2, 16, {}, pcm_samples);
	DecodedWave decoded;
	passed &= Require(RenegadeVitaAudio::Decode_Wave(
		pcm.data(), pcm.size(), &decoded), "PCM decode failed");
	passed &= Require(decoded.channels == 1 && decoded.sample_rate == 48000 &&
		decoded.samples == std::vector<int16_t>({ 1000, -1000, 2000, -2000 }),
		"PCM decode values differ");
	AILSOUNDINFO pcm_info = {};
	passed &= Require(AIL_WAV_info_bounded(pcm.data(), pcm.size(), &pcm_info) != 0 &&
		pcm_info.samples == 4 && pcm_info.rate == 48000,
		"PCM WAVE frame count differs");
	const std::vector<uint8_t> pcm_fact = Wave(1, 1, 48000, 2, 16, {},
		pcm_samples, 3);
	passed &= Require(RenegadeVitaAudio::Decode_Wave(
		pcm_fact.data(), pcm_fact.size(), &decoded),
		"PCM fact-count decode failed");
	passed &= Require(decoded.Frame_Count() == 3 &&
		decoded.fact_sample_frames == 3 &&
		decoded.estimated_sample_frames == 4 &&
		decoded.untrimmed_sample_frames == 4 &&
		decoded.trimmed_sample_frames == 1,
		"PCM fact-count metadata differs");

	const std::vector<uint8_t> pcm8 = Wave(1, 2, 22050, 2, 8, {},
		{ 128, 255, 0, 128 });
	passed &= Require(RenegadeVitaAudio::Decode_Wave(
		pcm8.data(), pcm8.size(), &decoded), "8-bit stereo PCM decode failed");
	passed &= Require(decoded.samples ==
		std::vector<int16_t>({ 0, 32512, -32768, 0 }),
		"8-bit stereo PCM values differ");

	std::vector<uint8_t> ima_extension;
	Write_U16(ima_extension, 2);
	Write_U16(ima_extension, 9);
	const std::vector<uint8_t> ima = Wave(0x11, 1, 8000, 8, 4,
		ima_extension, { 0, 0, 0, 0, 0, 0, 0, 0 });
	passed &= Require(RenegadeVitaAudio::Decode_Wave(
		ima.data(), ima.size(), &decoded), "IMA ADPCM decode failed");
	passed &= Require(decoded.Frame_Count() == 9 && decoded.samples.front() == 0 &&
		decoded.samples.back() == 0, "IMA ADPCM frame contract differs");
	AILSOUNDINFO ima_info = {};
	passed &= Require(AIL_WAV_info_bounded(ima.data(), ima.size(), &ima_info) != 0 &&
		ima_info.samples == 9 && ima_info.rate == 8000,
		"IMA ADPCM WAVE frame count differs");
	const std::vector<uint8_t> ima_fact = Wave(0x11, 1, 8000, 8, 4,
		ima_extension, { 0, 0, 0, 0, 0, 0, 0, 0 }, 5);
	passed &= Require(RenegadeVitaAudio::Decode_Wave(
		ima_fact.data(), ima_fact.size(), &decoded),
		"IMA ADPCM fact-count decode failed");
	passed &= Require(decoded.Frame_Count() == 5,
		"IMA ADPCM fact-count trim differs");
	AILSOUNDINFO ima_fact_info = {};
	passed &= Require(AIL_WAV_info_bounded(
		ima_fact.data(), ima_fact.size(), &ima_fact_info) != 0 &&
		ima_fact_info.samples == 5 && ima_fact_info.rate == 8000,
		"IMA ADPCM fact-count WAVE metadata differs");

	const std::vector<uint8_t> ima_stereo = Wave(0x11, 2, 8000, 16, 4,
		ima_extension, {
			0, 0, 0, 0, 0, 0, 0, 0,
			0, 0, 0, 0, 0, 0, 0, 0
		});
	passed &= Require(RenegadeVitaAudio::Decode_Wave(
		ima_stereo.data(), ima_stereo.size(), &decoded),
		"stereo IMA ADPCM decode failed");
	passed &= Require(decoded.channels == 2 && decoded.Frame_Count() == 9 &&
		decoded.samples == std::vector<int16_t>(18, 0),
		"stereo IMA ADPCM frame contract differs");

	std::vector<uint8_t> ms_extension;
	Write_U16(ms_extension, 8);
	Write_U16(ms_extension, 4);
	Write_U16(ms_extension, 1);
	Write_U16(ms_extension, 256);
	Write_U16(ms_extension, 0);
	const std::vector<uint8_t> ms = Wave(2, 1, 8000, 8, 4, ms_extension,
		{ 0, 16, 0, 0xe8, 3, 0xf4, 1, 0 });
	passed &= Require(RenegadeVitaAudio::Decode_Wave(
		ms.data(), ms.size(), &decoded), "Microsoft ADPCM decode failed");
	passed &= Require(decoded.samples == std::vector<int16_t>({ 500, 1000, 1000, 1000 }),
		"Microsoft ADPCM values differ");
	AILSOUNDINFO ms_info = {};
	passed &= Require(AIL_WAV_info_bounded(ms.data(), ms.size(), &ms_info) != 0 &&
		ms_info.samples == 4 && ms_info.rate == 8000,
		"Microsoft ADPCM WAVE frame count differs");
	const std::vector<uint8_t> ms_fact = Wave(2, 1, 8000, 8, 4, ms_extension,
		{ 0, 16, 0, 0xe8, 3, 0xf4, 1, 0 }, 3);
	passed &= Require(RenegadeVitaAudio::Decode_Wave(
		ms_fact.data(), ms_fact.size(), &decoded),
		"Microsoft ADPCM fact-count decode failed");
	passed &= Require(decoded.Frame_Count() == 3,
		"Microsoft ADPCM fact-count trim differs");
	AILSOUNDINFO ms_fact_info = {};
	passed &= Require(AIL_WAV_info_bounded(
		ms_fact.data(), ms_fact.size(), &ms_fact_info) != 0 &&
		ms_fact_info.samples == 3 && ms_fact_info.rate == 8000,
		"Microsoft ADPCM fact-count WAVE metadata differs");

	std::vector<uint8_t> ms_stereo_extension;
	Write_U16(ms_stereo_extension, 8);
	Write_U16(ms_stereo_extension, 4);
	Write_U16(ms_stereo_extension, 1);
	Write_U16(ms_stereo_extension, 256);
	Write_U16(ms_stereo_extension, 0);
	const std::vector<uint8_t> ms_stereo = Wave(2, 2, 8000, 16, 4,
		ms_stereo_extension, {
			0, 0, 16, 0, 16, 0,
			0xe8, 3, 0x18, 0xfc, 0xf4, 1, 0x0c, 0xfe,
			0, 0
		});
	passed &= Require(RenegadeVitaAudio::Decode_Wave(
		ms_stereo.data(), ms_stereo.size(), &decoded),
		"stereo Microsoft ADPCM decode failed");
	passed &= Require(decoded.channels == 2 && decoded.Frame_Count() == 4,
		"stereo Microsoft ADPCM frame contract differs");

	std::vector<uint8_t> large_pcm_samples(10000, 128);
	const std::vector<uint8_t> large_pcm = Wave(1, 1, 8000, 1, 8, {},
		large_pcm_samples);
	AILSOUNDINFO bounded_info = {};
	passed &= Require(AIL_WAV_info_bounded(large_pcm.data(), 64, &bounded_info) != 0 &&
		bounded_info.data_len == large_pcm_samples.size() &&
		bounded_info.samples == large_pcm_samples.size(),
		"bounded WAVE header inspection failed");
	passed &= Require(!RenegadeVitaAudio::Decode_Wave(
		large_pcm.data(), 64, &decoded),
		"strict WAVE decode accepted a truncated payload");

	AIL_startup();
	Renegade_Miles_Reset_Runtime_Stats();
	WAVEFORMAT format = { WAVE_FORMAT_PCM, 2, 48000, 192000, 4 };
	HDIGDRIVER driver = nullptr;
	passed &= Require(AIL_waveOutOpen(&driver, nullptr, 0, &format) == AIL_NO_ERROR,
		"manual output driver open failed");
	HSAMPLE sample = AIL_allocate_sample_handle(driver);
	passed &= Require(sample != nullptr, "sample allocation failed");
	AIL_init_sample(sample);
	passed &= Require(AIL_set_named_sample_file(sample, nullptr, pcm.data(),
		static_cast<uint32_t>(pcm.size()), 0) != 0, "provider PCM load failed");
	AIL_set_sample_pan(sample, 0);
	AIL_set_sample_volume(sample, 127);
	AIL_set_sample_loop_count(sample, 1);
	AIL_start_sample(sample);
	int16_t mixed[8] = {};
	passed &= Require(Renegade_Miles_Mix_For_Test(mixed, 4), "manual mix failed");
	passed &= Require(mixed[0] == 1000 && mixed[1] == 0 && mixed[2] == -1000 &&
		mixed[3] == 0 && mixed[4] == 2000 && mixed[5] == 0 &&
		mixed[6] == -2000 && mixed[7] == 0,
		"provider volume/pan mix differs");
	AIL_release_sample_handle(sample);
	H3DSAMPLE sample3d = AIL_allocate_3D_sample_handle(1);
	passed &= Require(sample3d != nullptr &&
		AIL_set_3D_sample_file(sample3d, ima.data()) != 0,
		"provider 3D ADPCM load failed");
	passed &= Require(AIL_3D_sample_length(sample3d) == 8,
		"3D provider exposed decoded rather than encoded byte length");
	AIL_set_3D_sample_offset(sample3d, 4);
	passed &= Require(AIL_3D_sample_offset(sample3d) == 4,
		"3D provider encoded-byte seek contract differs");
	AIL_release_3D_sample_handle(sample3d);
	sample3d = AIL_allocate_3D_sample_handle(1);
	passed &= Require(sample3d != nullptr &&
		AIL_set_3D_sample_file(sample3d, pcm.data()) != 0,
		"provider 3D PCM load failed");
	AIL_set_3D_sample_volume(sample3d, 127);
	AIL_set_3D_sample_distances(sample3d, 10.0F, 2.0F);
	AIL_set_3D_position(sample3d, 0.0F, 6.0F, 0.0F);
	AIL_start_3D_sample(sample3d);
	int16_t spatial[2] = {};
	passed &= Require(Renegade_Miles_Mix_For_Test(spatial, 1) &&
		spatial[0] == 500 && spatial[1] == 500,
		"3D provider distance interpolation differs");
	AIL_end_3D_sample(sample3d);
	AIL_set_3D_position(sample3d, 0.0F, 10.0F, 0.0F);
	AIL_start_3D_sample(sample3d);
	spatial[0] = spatial[1] = 1;
	passed &= Require(Renegade_Miles_Mix_For_Test(spatial, 1) &&
		spatial[0] == 0 && spatial[1] == 0,
		"3D provider maximum-distance cutoff differs");
	AIL_release_3D_sample_handle(sample3d);
	g_stream_fixture = pcm_fact;
	AIL_set_file_callbacks(Stream_Open, Stream_Close, Stream_Seek, Stream_Read);
	HSTREAM stream = AIL_open_stream(driver, "logan_test.wav", 0);
	passed &= Require(stream != nullptr, "provider stream open failed");
	AIL_set_stream_loop_count(stream, 2);
	passed &= Require(AIL_stream_loop_count(stream) == 2,
		"provider stream loop-count query differs");
	AIL_set_stream_loop_count(stream, 1);
	AIL_set_stream_volume(stream, 127);
	AIL_set_stream_pan(stream, 64);
	AIL_start_stream(stream);
	int16_t streamed[8] = {};
	passed &= Require(Renegade_Miles_Mix_For_Test(streamed, 4),
		"manual stream mix failed");
	passed &= Require(streamed[0] == 1000 && streamed[1] == 1000 &&
		streamed[2] == -1000 && streamed[3] == -1000 &&
		streamed[4] == 2000 && streamed[5] == 2000 && streamed[6] == 0 &&
		streamed[7] == 0,
		"provider stream mix differs");
	AIL_close_stream(stream);
	RenegadeMilesRuntimeStats stats = {};
	Renegade_Miles_Get_Runtime_Stats(&stats);
	passed &= Require(stats.output_start_attempts == 1 &&
		stats.output_start_successes == 1 && stats.output_start_failures == 0,
		"provider output stats differ");
	passed &= Require(stats.sample_file_load_attempts == 1 &&
		stats.sample_file_load_successes == 1 &&
		stats.sample_3d_file_load_attempts == 2 &&
		stats.sample_3d_file_load_successes == 2,
		"provider decode stats differ");
	passed &= Require(stats.stream_open_attempts == 1 &&
		stats.stream_open_successes == 1 &&
		stats.stream_start_attempts == 1 &&
		stats.stream_start_successes == 1 &&
		stats.stream_bytes_read == pcm_fact.size() &&
		stats.stream_decoded_frames == 3 &&
		stats.stream_mixed_buffers == 1 &&
		stats.stream_mixed_frames == 4 &&
		stats.stream_mixed_nonzero_buffers == 1 &&
		stats.stream_mixed_peak_abs >= 1000 &&
		stats.last_stream_frames == 3 &&
		stats.last_stream_fact_frames == 3 &&
		stats.last_stream_estimated_frames == 4 &&
		stats.last_stream_untrimmed_frames == 4 &&
		stats.last_stream_trimmed_frames == 1 &&
		std::strcmp(stats.last_stream_name, "logan_test.wav") == 0,
		"provider stream stats differ");
	passed &= Require(stats.sample_start_attempts == 4 &&
		stats.sample_start_successes == 4 &&
		stats.mixed_buffers == 4 &&
		stats.mixed_nonzero_buffers == 3 &&
		stats.mixed_peak_abs >= 1000 &&
		stats.active_streams == 0,
		"provider start stats differ");
	AIL_waveOutClose(driver);
	AIL_shutdown();

	if (!passed) return 1;
	std::puts("vita_audio_provider=passed pcm=3 ima_adpcm=2 ms_adpcm=2 bounds=2 mixer=1 spatial=2 stream=1");
	return 0;
}
