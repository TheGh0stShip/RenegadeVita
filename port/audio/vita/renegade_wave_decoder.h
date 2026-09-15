#pragma once

#include <stddef.h>
#include <stdint.h>

#include <vector>
#include <memory>

namespace RenegadeVitaAudio {

// Compressed music remains encoded; callers retain cursor, mixing and looping.
class MpegPlayback {
public:
	virtual ~MpegPlayback() = default;
	virtual size_t Frame_Count() const = 0;
	virtual uint32_t Sample_Rate() const = 0;
	virtual uint16_t Channels() const = 0;
	virtual int16_t Sample(size_t frame, uint16_t channel) = 0;
	virtual size_t PCM_Storage_Bytes() const = 0;
};
bool Is_Mpeg_Media(const uint8_t *data, size_t bytes);
std::unique_ptr<MpegPlayback> Open_Mpeg_Playback(const uint8_t *data,
	size_t bytes, const char **error = nullptr);

enum class WaveEncoding : uint16_t {
	Pcm = 0x0001,
	MicrosoftAdpcm = 0x0002,
	ImaAdpcm = 0x0011,
	MpegLayer3 = 0x0055
};

struct WaveInfo {
	WaveEncoding encoding = WaveEncoding::Pcm;
	uint16_t channels = 0;
	uint16_t bits_per_sample = 0;
	uint16_t block_align = 0;
	uint16_t samples_per_block = 0;
	uint32_t sample_rate = 0;
	uint32_t data_bytes = 0;
	uint32_t fact_sample_frames = 0;
	uint32_t estimated_sample_frames = 0;
	uint32_t sample_frames = 0;
	size_t data_offset = 0;
	std::vector<int16_t> coefficients;
};

struct DecodedWave {
	uint16_t channels = 0;
	uint32_t sample_rate = 0;
	uint32_t fact_sample_frames = 0;
	uint32_t estimated_sample_frames = 0;
	uint32_t untrimmed_sample_frames = 0;
	uint32_t trimmed_sample_frames = 0;
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
// Return metadata from the same validated parse used for decoding. Callers
// cannot supply stale or unvalidated metadata to bypass RIFF bounds checks.
bool Decode_Wave_With_Info(const uint8_t *data, size_t bytes,
	DecodedWave *decoded, WaveInfo *info, const char **error = nullptr);

} // namespace RenegadeVitaAudio
