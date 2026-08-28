#pragma once

#include <stddef.h>
#include <stdint.h>

#include <vector>

namespace RenegadeVitaAudio {

enum class WaveEncoding : uint16_t {
	Pcm = 0x0001,
	MicrosoftAdpcm = 0x0002,
	ImaAdpcm = 0x0011
};

struct WaveInfo {
	WaveEncoding encoding = WaveEncoding::Pcm;
	uint16_t channels = 0;
	uint16_t bits_per_sample = 0;
	uint16_t block_align = 0;
	uint16_t samples_per_block = 0;
	uint32_t sample_rate = 0;
	uint32_t data_bytes = 0;
	size_t data_offset = 0;
	std::vector<int16_t> coefficients;
};

struct DecodedWave {
	uint16_t channels = 0;
	uint32_t sample_rate = 0;
	std::vector<int16_t> samples;

	size_t Frame_Count() const
	{
		return channels == 0 ? 0 : samples.size() / channels;
	}
};

bool Inspect_Wave(const uint8_t *data, size_t bytes, WaveInfo *info,
	const char **error = nullptr, bool allow_truncated_data = false);
bool Decode_Wave(const uint8_t *data, size_t bytes, DecodedWave *decoded,
	const char **error = nullptr);

} // namespace RenegadeVitaAudio
