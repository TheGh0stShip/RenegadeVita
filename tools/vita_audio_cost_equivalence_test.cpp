// Host equivalence test for the RVAU1 audio cost switches. The same stream
// and 3D sample sequence is mixed under every mask; each mask must produce
// output identical to mask 0 and the counters must show each switch acted.
#include "mss.h"
#include "renegade_audio_cost.h"
#include "renegade_miles_runtime_stats.h"
#include "renegade_miles_test.h"
#include "renegade_wave_decoder.h"

#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <vector>

namespace {

void Write_U16(std::vector<uint8_t> &data, uint16_t value)
{
	data.push_back(static_cast<uint8_t>(value));
	data.push_back(static_cast<uint8_t>(value >> 8U));
}

void Write_U32(std::vector<uint8_t> &data, uint32_t value)
{
	for (unsigned shift = 0U; shift < 32U; shift += 8U)
		data.push_back(static_cast<uint8_t>(value >> shift));
}

void FourCC(std::vector<uint8_t> &data, const char *text)
{
	data.insert(data.end(), text, text + 4);
}

std::vector<uint8_t> Wave(uint16_t encoding, uint16_t block_align, uint16_t bits,
	const std::vector<uint8_t> &extension, const std::vector<uint8_t> &samples,
	uint32_t fact_frames)
{
	std::vector<uint8_t> result;
	FourCC(result, "RIFF");
	Write_U32(result, 0U);
	FourCC(result, "WAVE");
	FourCC(result, "fmt ");
	Write_U32(result, static_cast<uint32_t>(16U + extension.size()));
	Write_U16(result, encoding);
	Write_U16(result, 1U);
	Write_U32(result, 22050U);
	Write_U32(result, 22050U * block_align);
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
	if ((samples.size() & 1U) != 0U) result.push_back(0U);
	const uint32_t riff_bytes = static_cast<uint32_t>(result.size() - 8U);
	for (unsigned index = 0U; index < 4U; ++index)
		result[4U + index] = static_cast<uint8_t>(riff_bytes >> (8U * index));
	return result;
}

uint32_t g_seed = 0x12345678U;
uint8_t Next_Byte()
{
	g_seed = g_seed * 1664525U + 1013904223U;
	return static_cast<uint8_t>(g_seed >> 24U);
}

// Mono IMA ADPCM: 256-byte blocks of 505 frames, `blocks` full blocks plus a
// two-byte predictor tail, with `fact_extra` frames of fact padding.
std::vector<uint8_t> Ima_Wave(unsigned blocks, uint32_t fact_extra)
{
	std::vector<uint8_t> extension;
	Write_U16(extension, 2U);
	Write_U16(extension, 505U);
	std::vector<uint8_t> data;
	for (unsigned block = 0U; block < blocks; ++block) {
		Write_U16(data, static_cast<uint16_t>(Next_Byte() << 4U));
		data.push_back(static_cast<uint8_t>(Next_Byte() % 89U));
		data.push_back(0U);
		for (unsigned index = 0U; index < 252U; ++index) data.push_back(Next_Byte());
	}
	data.push_back(Next_Byte());
	data.push_back(Next_Byte());
	return Wave(0x11U, 256U, 4U, extension, data, blocks * 505U + fact_extra);
}

std::vector<uint8_t> Pcm_Wave(unsigned frames)
{
	std::vector<uint8_t> data;
	for (unsigned frame = 0U; frame < frames; ++frame) {
		data.push_back(Next_Byte());
		data.push_back(Next_Byte());
	}
	return Wave(1U, 2U, 16U, {}, data, 0U);
}

struct Fixture {
	const char *name;
	std::vector<uint8_t> bytes;
};
std::vector<Fixture> g_files;
struct OpenFile {
	const Fixture *fixture = nullptr;
	size_t position = 0U;
};
OpenFile g_open[4];

U32 AILCALLBACK File_Open(const char *name, AIL_FILE_HANDLE *handle)
{
	if (name == nullptr || handle == nullptr) return 0U;
	for (const Fixture &fixture : g_files) {
		if (std::strcmp(fixture.name, name) != 0) continue;
		for (size_t slot = 0U; slot < 4U; ++slot) {
			if (g_open[slot].fixture != nullptr) continue;
			g_open[slot].fixture = &fixture;
			g_open[slot].position = 0U;
			*handle = static_cast<AIL_FILE_HANDLE>(slot + 1U);
			return 1U;
		}
	}
	return 0U;
}

OpenFile *Find_Open(AIL_FILE_HANDLE handle)
{
	return handle >= 1U && handle <= 4U && g_open[handle - 1U].fixture != nullptr
		? &g_open[handle - 1U] : nullptr;
}

void AILCALLBACK File_Close(AIL_FILE_HANDLE handle)
{
	if (OpenFile *file = Find_Open(handle)) file->fixture = nullptr;
}

S32 AILCALLBACK File_Seek(AIL_FILE_HANDLE handle, S32 offset, U32 type)
{
	OpenFile *file = Find_Open(handle);
	if (file == nullptr || offset < 0) return -1;
	const size_t size = file->fixture->bytes.size();
	const size_t base = type == AIL_FILE_SEEK_END ? size :
		type == AIL_FILE_SEEK_CURRENT ? file->position : 0U;
	if (base + static_cast<size_t>(offset) > size) return -1;
	file->position = base + static_cast<size_t>(offset);
	return static_cast<S32>(file->position);
}

U32 AILCALLBACK File_Read(AIL_FILE_HANDLE handle, void *buffer, U32 bytes)
{
	OpenFile *file = Find_Open(handle);
	if (file == nullptr || buffer == nullptr) return 0U;
	const size_t count = std::min<size_t>(bytes,
		file->fixture->bytes.size() - file->position);
	std::memcpy(buffer, file->fixture->bytes.data() + file->position, count);
	file->position += count;
	return static_cast<U32>(count);
}

void Mix(std::vector<int16_t> *output, unsigned buffers)
{
	int16_t block[1024U * 2U];
	for (unsigned index = 0U; index < buffers; ++index) {
		std::fill(std::begin(block), std::end(block), static_cast<int16_t>(0));
		Renegade_Miles_Mix_For_Test(block, 1024U);
		output->insert(output->end(), std::begin(block), std::end(block));
	}
}

struct RunResult {
	std::vector<int16_t> output;
	RenegadeMilesAudioCostStats before = {};
	RenegadeMilesAudioCostStats after = {};
	RenegadeMilesAudioCostStats shutdown = {};
	unsigned opened = 0U;
	unsigned failed = 0U;
};

RunResult Run(unsigned mode)
{
	RunResult result;
	AIL_startup();
	Renegade_Miles_Set_Audio_Cost_Mode(mode);
	Renegade_Miles_Get_Audio_Cost_Stats(&result.before);
	AIL_set_file_callbacks(File_Open, File_Close, File_Seek, File_Read);
	HSAMPLE first = AIL_allocate_sample_handle(nullptr);
	HSAMPLE second = AIL_allocate_sample_handle(nullptr);
	H3DSAMPLE spatial = AIL_allocate_3D_sample_handle(1U);
	const char *order[] = { "line_ima.wav", "line_pcm.wav", "big_ima.wav",
		"line_ima.wav", "line_pcm.wav" };
	for (unsigned round = 0U; round < 3U; ++round) {
		for (const char *name : order) {
			HSTREAM stream = AIL_open_stream_by_sample(nullptr, first, name, 0);
			// A second stream overlaps the first on another handle.
			HSTREAM other = AIL_open_stream_by_sample(nullptr, second, "line_pcm.wav", 0);
			result.opened += 2U;
			if (stream == nullptr) ++result.failed;
			if (other == nullptr) ++result.failed;
			AIL_set_stream_volume(stream, 100);
			AIL_set_stream_volume(other, 60);
			AIL_set_stream_pan(other, 20);
			AIL_start_stream(stream);
			AIL_start_stream(other);
			Mix(&result.output, 3U);
			AIL_close_stream(other);
			Mix(&result.output, 2U);
			AIL_close_stream(stream);
		}
		const Fixture &line = g_files[0];
		AIL_set_3D_sample_file_bounded(spatial, line.bytes.data(), line.bytes.size());
		AIL_set_3D_position(spatial, 3.0F, 0.0F, 4.0F);
		AIL_start_3D_sample(spatial);
		Mix(&result.output, 4U);
		AIL_end_3D_sample(spatial);
	}
	Renegade_Miles_Get_Audio_Cost_Stats(&result.after);
	AIL_release_3D_sample_handle(spatial);
	AIL_release_sample_handle(second);
	AIL_release_sample_handle(first);
	AIL_shutdown();
	Renegade_Miles_Get_Audio_Cost_Stats(&result.shutdown);
	return result;
}

bool Require(bool condition, const char *message, unsigned mode)
{
	if (!condition) std::fprintf(stderr, "audio cost test (mode %X): %s\n", mode, message);
	return condition;
}

uint32_t Delta(uint32_t after, uint32_t before)
{
	return after - before;
}

} // namespace

int main()
{
	g_files.push_back({ "line_ima.wav", Ima_Wave(6U, 300U) });
	g_files.push_back({ "line_pcm.wav", Pcm_Wave(3000U) });
	g_files.push_back({ "big_ima.wav", Ima_Wave(600U, 0U) });
	bool passed = Require(g_files[2].bytes.size() > 128U * 1024U, "big fixture fits a slab", 0U);

	const RunResult reference = Run(0U);
	passed &= Require(reference.failed == 0U, "mode 0 stream open failed", 0U);
	bool nonzero = false;
	for (int16_t value : reference.output) nonzero = nonzero || value != 0;
	passed &= Require(nonzero, "mode 0 mixed silence", 0U);
	passed &= Require(Delta(reference.after.stream_probe_hits, reference.before.stream_probe_hits) == 0U &&
		Delta(reference.after.image_pool_hits, reference.before.image_pool_hits) == 0U &&
		Delta(reference.after.stream_pcm_deferred, reference.before.stream_pcm_deferred) == 0U &&
		Delta(reference.after.exact_reserve_raises, reference.before.exact_reserve_raises) == 0U,
		"mode 0 used an RVAU1 path", 0U);

	for (unsigned mode = 1U; mode <= RENEGADE_AUDIO_COST_ALL; ++mode) {
		const RunResult run = Run(mode);
		passed &= Require(run.failed == 0U, "stream open failed", mode);
		passed &= Require(run.output == reference.output, "mixed output differs from mode 0", mode);
		const uint32_t probe_hits = Delta(run.after.stream_probe_hits, run.before.stream_probe_hits);
		const uint32_t deferred = Delta(run.after.stream_pcm_deferred, run.before.stream_pcm_deferred);
		const uint32_t admitted = Delta(run.after.stream_pcm_admitted, run.before.stream_pcm_admitted);
		const uint32_t pool_hits = Delta(run.after.image_pool_hits, run.before.image_pool_hits);
		const uint32_t oversize = Delta(run.after.image_pool_oversize, run.before.image_pool_oversize);
		const uint32_t raises = Delta(run.after.exact_reserve_raises, run.before.exact_reserve_raises);
		passed &= Require(((mode & RENEGADE_AUDIO_COST_STREAM_CACHE_PROBE) != 0U) == (probe_hits != 0U),
			"cache probe hits do not follow bit 1", mode);
		passed &= Require(((mode & RENEGADE_AUDIO_COST_STREAM_SECOND_OPEN_ADMISSION) != 0U) ==
			(deferred != 0U && admitted != 0U), "admission does not follow bit 2", mode);
		passed &= Require(((mode & RENEGADE_AUDIO_COST_STREAM_IMAGE_POOL) != 0U) ==
			(pool_hits != 0U && oversize != 0U), "image pool does not follow bit 3", mode);
		passed &= Require(((mode & RENEGADE_AUDIO_COST_EXACT_DECODE_RESERVE) != 0U) == (raises != 0U),
			"exact reserve does not follow bit 0", mode);
		passed &= Require(((mode & RENEGADE_AUDIO_COST_STREAM_IMAGE_POOL) != 0U) ==
			(run.after.image_pool_resident_bytes == 128U * 1024U),
			"image pool keeps one slab while streams open sequentially", mode);
		passed &= Require(run.shutdown.image_pool_resident_bytes == 0U,
			"image pool slabs survive shutdown", mode);
	}
	Renegade_Miles_Set_Audio_Cost_Mode(0U);

	unsigned parsed = 99U;
	passed &= Require(Renegade_Parse_Audio_Cost_Flag("RVAU1 F\n", 8U, &parsed) && parsed == 15U,
		"flag F", 0U);
	passed &= Require(Renegade_Parse_Audio_Cost_Flag("RVAU1 a\n", 8U, &parsed) && parsed == 10U,
		"flag a", 0U);
	passed &= Require(!Renegade_Parse_Audio_Cost_Flag("RVAU1 G\n", 8U, &parsed) &&
		!Renegade_Parse_Audio_Cost_Flag("RVAU1 1", 7U, &parsed) &&
		!Renegade_Parse_Audio_Cost_Flag("RVPL1 1\n", 8U, &parsed), "malformed flags", 0U);

	RenegadeAudioImagePool<64U, 1U> pool;
	RenegadeAudioImageLease first;
	RenegadeAudioImageLease second;
	passed &= Require(pool.Acquire(64U, &first) && first.data != nullptr, "pool acquire", 0U);
	passed &= Require(!pool.Acquire(8U, &second) && second.data == nullptr && pool.Busy() == 1U,
		"pool busy fallback", 0U);
	passed &= Require(!pool.Acquire(65U, &second) && pool.Oversize() == 1U, "pool oversize", 0U);
	pool.Release(&first);
	passed &= Require(pool.Acquire(8U, &second) && pool.Hits() == 2U &&
		pool.Resident_Bytes() == 64U, "pool reuse", 0U);
	pool.Release(&second);
	pool.Free_Idle();
	passed &= Require(pool.Resident_Bytes() == 0U, "pool free", 0U);

	if (!passed) return 1;
	std::printf("vita_audio_cost_equivalence=passed buffers=%zu\n", reference.output.size() / 2048U);
	return 0;
}
