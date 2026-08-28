#include "renegade_wave_decoder.h"

#include <algorithm>
#include <limits>
#include <utility>

namespace RenegadeVitaAudio {
namespace {

constexpr size_t kMaximumDecodedSamples = 16U * 1024U * 1024U;

uint16_t Read_U16(const uint8_t *data)
{
	return static_cast<uint16_t>(data[0]) |
		(static_cast<uint16_t>(data[1]) << 8U);
}

int16_t Read_S16(const uint8_t *data)
{
	return static_cast<int16_t>(Read_U16(data));
}

uint32_t Read_U32(const uint8_t *data)
{
	return static_cast<uint32_t>(data[0]) |
		(static_cast<uint32_t>(data[1]) << 8U) |
		(static_cast<uint32_t>(data[2]) << 16U) |
		(static_cast<uint32_t>(data[3]) << 24U);
}

bool Fail(const char *message, const char **error)
{
	if (error != nullptr) *error = message;
	return false;
}

int16_t Clamp_Sample(int64_t value)
{
	return static_cast<int16_t>(std::max<int64_t>(-32768,
		std::min<int64_t>(32767, value)));
}

bool Append_Frame(DecodedWave *decoded, const int16_t *frame)
{
	if (decoded->samples.size() > kMaximumDecodedSamples - decoded->channels) {
		return false;
	}
	for (uint16_t channel = 0; channel < decoded->channels; ++channel) {
		decoded->samples.push_back(frame[channel]);
	}
	return true;
}

bool Decode_Pcm(const uint8_t *data, const WaveInfo &info,
	DecodedWave *decoded, const char **error)
{
	const uint8_t *source = data + info.data_offset;
	if (info.bits_per_sample == 8) {
		if (info.data_bytes > kMaximumDecodedSamples) {
			return Fail("PCM sample ceiling exceeded", error);
		}
		decoded->samples.reserve(info.data_bytes);
		for (uint32_t index = 0; index < info.data_bytes; ++index) {
			decoded->samples.push_back(
				static_cast<int16_t>((static_cast<int>(source[index]) - 128) * 256));
		}
		return true;
	}
	if (info.bits_per_sample == 16) {
		const size_t sample_count = info.data_bytes / 2U;
		if (sample_count > kMaximumDecodedSamples) {
			return Fail("PCM sample ceiling exceeded", error);
		}
		decoded->samples.reserve(sample_count);
		for (size_t index = 0; index < sample_count; ++index) {
			decoded->samples.push_back(Read_S16(source + index * 2U));
		}
		return true;
	}
	return Fail("unsupported PCM bit depth", error);
}

constexpr int kImaIndexAdjust[16] = {
	-1, -1, -1, -1, 2, 4, 6, 8,
	-1, -1, -1, -1, 2, 4, 6, 8
};

constexpr int kImaStep[89] = {
	7, 8, 9, 10, 11, 12, 13, 14, 16, 17, 19, 21, 23, 25, 28, 31,
	34, 37, 41, 45, 50, 55, 60, 66, 73, 80, 88, 97, 107, 118, 130,
	143, 157, 173, 190, 209, 230, 253, 279, 307, 337, 371, 408, 449,
	494, 544, 598, 658, 724, 796, 876, 963, 1060, 1166, 1282, 1411,
	1552, 1707, 1878, 2066, 2272, 2499, 2749, 3024, 3327, 3660, 4026,
	4428, 4871, 5358, 5894, 6484, 7132, 7845, 8630, 9493, 10442,
	11487, 12635, 13899, 15289, 16818, 18500, 20350, 22385, 24623,
	27086, 29794, 32767
};

int16_t Decode_Ima_Nibble(uint8_t nibble, int *predictor, int *step_index)
{
	const int step = kImaStep[*step_index];
	int difference = step >> 3;
	if ((nibble & 1U) != 0U) difference += step >> 2;
	if ((nibble & 2U) != 0U) difference += step >> 1;
	if ((nibble & 4U) != 0U) difference += step;
	if ((nibble & 8U) != 0U) difference = -difference;
	*predictor = std::max(-32768, std::min(32767, *predictor + difference));
	*step_index = std::max(0, std::min(88,
		*step_index + kImaIndexAdjust[nibble & 0x0fU]));
	return static_cast<int16_t>(*predictor);
}

bool Decode_Ima_Block(const uint8_t *block, size_t bytes,
	const WaveInfo &info, DecodedWave *decoded, const char **error)
{
	const size_t header_bytes = static_cast<size_t>(info.channels) * 4U;
	if (bytes < header_bytes) return Fail("truncated IMA ADPCM block", error);
	int predictor[2] = {};
	int step_index[2] = {};
	int16_t frame[2] = {};
	for (uint16_t channel = 0; channel < info.channels; ++channel) {
		const uint8_t *header = block + channel * 4U;
		predictor[channel] = Read_S16(header);
		step_index[channel] = header[2];
		if (step_index[channel] > 88) {
			return Fail("invalid IMA ADPCM step index", error);
		}
		frame[channel] = static_cast<int16_t>(predictor[channel]);
	}
	if (!Append_Frame(decoded, frame)) return Fail("decoded sample ceiling exceeded", error);
	const size_t frame_limit = info.samples_per_block != 0
		? info.samples_per_block : std::numeric_limits<size_t>::max();
	size_t frames = 1;
	const uint8_t *payload = block + header_bytes;
	const size_t payload_bytes = bytes - header_bytes;
	if (info.channels == 1) {
		for (size_t index = 0; index < payload_bytes && frames < frame_limit; ++index) {
			const uint8_t packed = payload[index];
			frame[0] = Decode_Ima_Nibble(packed & 0x0fU, predictor, step_index);
			if (!Append_Frame(decoded, frame)) return Fail("decoded sample ceiling exceeded", error);
			++frames;
			if (frames >= frame_limit) break;
			frame[0] = Decode_Ima_Nibble(packed >> 4U, predictor, step_index);
			if (!Append_Frame(decoded, frame)) return Fail("decoded sample ceiling exceeded", error);
			++frames;
		}
		return true;
	}
	for (size_t group = 0; group < payload_bytes && frames < frame_limit;) {
		int16_t channel_samples[2][8] = {};
		size_t counts[2] = {};
		for (uint16_t channel = 0; channel < 2; ++channel) {
			const size_t available = std::min<size_t>(4U, payload_bytes - group);
			for (size_t index = 0; index < available; ++index) {
				const uint8_t packed = payload[group + index];
				channel_samples[channel][counts[channel]++] = Decode_Ima_Nibble(
					packed & 0x0fU, &predictor[channel], &step_index[channel]);
				channel_samples[channel][counts[channel]++] = Decode_Ima_Nibble(
					packed >> 4U, &predictor[channel], &step_index[channel]);
			}
			group += available;
			if (group >= payload_bytes && channel == 0) break;
		}
		const size_t group_frames = std::min(counts[0], counts[1]);
		for (size_t sample = 0; sample < group_frames && frames < frame_limit; ++sample) {
			frame[0] = channel_samples[0][sample];
			frame[1] = channel_samples[1][sample];
			if (!Append_Frame(decoded, frame)) return Fail("decoded sample ceiling exceeded", error);
			++frames;
		}
	}
	return true;
}

bool Decode_Ima(const uint8_t *data, const WaveInfo &info,
	DecodedWave *decoded, const char **error)
{
	const uint8_t *source = data + info.data_offset;
	for (size_t offset = 0; offset < info.data_bytes;) {
		const size_t block_bytes = std::min<size_t>(
			info.block_align, info.data_bytes - offset);
		if (!Decode_Ima_Block(source + offset, block_bytes, info, decoded, error)) {
			return false;
		}
		offset += block_bytes;
	}
	return true;
}

constexpr int kMsAdaptation[16] = {
	230, 230, 230, 230, 307, 409, 512, 614,
	768, 614, 512, 409, 307, 230, 230, 230
};

int16_t Decode_Ms_Nibble(uint8_t nibble, int coefficient1, int coefficient2,
	int *delta, int *sample1, int *sample2)
{
	const int signed_nibble = (nibble & 0x08U) != 0U
		? static_cast<int>(nibble) - 16 : nibble;
	const int64_t prediction = (static_cast<int64_t>(*sample1) * coefficient1 +
		static_cast<int64_t>(*sample2) * coefficient2) / 256 +
		static_cast<int64_t>(signed_nibble) * *delta;
	const int16_t decoded = Clamp_Sample(prediction);
	*sample2 = *sample1;
	*sample1 = decoded;
	*delta = std::max(16, (kMsAdaptation[nibble & 0x0fU] * *delta) / 256);
	return decoded;
}

bool Decode_Ms_Block(const uint8_t *block, size_t bytes,
	const WaveInfo &info, DecodedWave *decoded, const char **error)
{
	const size_t header_bytes = static_cast<size_t>(info.channels) * 7U;
	if (bytes < header_bytes) return Fail("truncated Microsoft ADPCM block", error);
	int coefficient1[2] = {};
	int coefficient2[2] = {};
	int delta[2] = {};
	int sample1[2] = {};
	int sample2[2] = {};
	int16_t frame[2] = {};
	for (uint16_t channel = 0; channel < info.channels; ++channel) {
		const uint8_t predictor = block[channel];
		const size_t pair = static_cast<size_t>(predictor) * 2U;
		if (pair + 1U >= info.coefficients.size()) {
			return Fail("invalid Microsoft ADPCM predictor", error);
		}
		coefficient1[channel] = info.coefficients[pair];
		coefficient2[channel] = info.coefficients[pair + 1U];
			delta[channel] = std::max<int>(16,
				Read_U16(block + info.channels + channel * 2U));
		sample1[channel] = Read_S16(block + info.channels * 3U + channel * 2U);
		sample2[channel] = Read_S16(block + info.channels * 5U + channel * 2U);
		frame[channel] = static_cast<int16_t>(sample2[channel]);
	}
	if (!Append_Frame(decoded, frame)) return Fail("decoded sample ceiling exceeded", error);
	for (uint16_t channel = 0; channel < info.channels; ++channel) {
		frame[channel] = static_cast<int16_t>(sample1[channel]);
	}
	if (!Append_Frame(decoded, frame)) return Fail("decoded sample ceiling exceeded", error);
	const size_t frame_limit = info.samples_per_block != 0
		? info.samples_per_block : std::numeric_limits<size_t>::max();
	size_t frames = 2;
	const uint8_t *payload = block + header_bytes;
	const size_t payload_bytes = bytes - header_bytes;
	for (size_t index = 0; index < payload_bytes && frames < frame_limit; ++index) {
		const uint8_t packed = payload[index];
		if (info.channels == 1) {
			frame[0] = Decode_Ms_Nibble(packed >> 4U, coefficient1[0],
				coefficient2[0], &delta[0], &sample1[0], &sample2[0]);
			if (!Append_Frame(decoded, frame)) return Fail("decoded sample ceiling exceeded", error);
			++frames;
			if (frames >= frame_limit) break;
			frame[0] = Decode_Ms_Nibble(packed & 0x0fU, coefficient1[0],
				coefficient2[0], &delta[0], &sample1[0], &sample2[0]);
		} else {
			frame[0] = Decode_Ms_Nibble(packed >> 4U, coefficient1[0],
				coefficient2[0], &delta[0], &sample1[0], &sample2[0]);
			frame[1] = Decode_Ms_Nibble(packed & 0x0fU, coefficient1[1],
				coefficient2[1], &delta[1], &sample1[1], &sample2[1]);
		}
		if (!Append_Frame(decoded, frame)) return Fail("decoded sample ceiling exceeded", error);
		++frames;
	}
	return true;
}

bool Decode_Microsoft_Adpcm(const uint8_t *data, const WaveInfo &info,
	DecodedWave *decoded, const char **error)
{
	const uint8_t *source = data + info.data_offset;
	for (size_t offset = 0; offset < info.data_bytes;) {
		const size_t block_bytes = std::min<size_t>(
			info.block_align, info.data_bytes - offset);
		if (!Decode_Ms_Block(source + offset, block_bytes, info, decoded, error)) {
			return false;
		}
		offset += block_bytes;
	}
	return true;
}

uint32_t Saturating_U64_To_U32(uint64_t value)
{
	return value > std::numeric_limits<uint32_t>::max()
		? std::numeric_limits<uint32_t>::max()
		: static_cast<uint32_t>(value);
}

uint32_t Estimate_Partial_Adpcm_Frames(const WaveInfo &info, uint32_t bytes)
{
	const uint32_t header = info.encoding == WaveEncoding::MicrosoftAdpcm
		? static_cast<uint32_t>(info.channels) * 7U
		: static_cast<uint32_t>(info.channels) * 4U;
	if (info.samples_per_block == 0U || bytes <= header) return 0U;
	const uint32_t payload = bytes - header;
	uint32_t frames = info.encoding == WaveEncoding::MicrosoftAdpcm ? 2U : 1U;
	if (info.encoding == WaveEncoding::MicrosoftAdpcm) {
		frames += payload * (info.channels == 1U ? 2U : 1U);
	} else {
		frames += (payload * 2U) / info.channels;
	}
	return std::min<uint32_t>(frames, info.samples_per_block);
}

uint32_t Estimate_Frame_Count(const WaveInfo &info)
{
	if (info.block_align == 0U) return 0U;
	if (info.encoding == WaveEncoding::Pcm) {
		return info.data_bytes / info.block_align;
	}
	if (info.samples_per_block == 0U) return 0U;
	const uint32_t full_blocks = info.data_bytes / info.block_align;
	const uint32_t remainder = info.data_bytes % info.block_align;
	const uint64_t frames = static_cast<uint64_t>(full_blocks) *
		info.samples_per_block + Estimate_Partial_Adpcm_Frames(info, remainder);
	return Saturating_U64_To_U32(frames);
}

} // namespace

bool Inspect_Wave(const uint8_t *data, size_t bytes, WaveInfo *info,
	const char **error, bool allow_truncated_data)
{
	if (error != nullptr) *error = nullptr;
	if (data == nullptr || info == nullptr || bytes < 12U) {
		return Fail("truncated RIFF header", error);
	}
	if (Read_U32(data) != UINT32_C(0x46464952) ||
		Read_U32(data + 8U) != UINT32_C(0x45564157)) {
		return Fail("not a RIFF/WAVE image", error);
	}
	const uint64_t declared_bytes = static_cast<uint64_t>(Read_U32(data + 4U)) + 8U;
	if (declared_bytes < 12U) return Fail("invalid RIFF length", error);
	if (!allow_truncated_data && declared_bytes > bytes) {
		return Fail("RIFF image exceeds source buffer", error);
	}
	const size_t scan_bytes = static_cast<size_t>(
		std::min<uint64_t>(declared_bytes, bytes));
	WaveInfo parsed;
	bool format_found = false;
	bool data_found = false;
	for (size_t offset = 12U; offset + 8U <= scan_bytes;) {
		const uint32_t identifier = Read_U32(data + offset);
		const uint32_t chunk_bytes = Read_U32(data + offset + 4U);
		const size_t payload = offset + 8U;
		if (chunk_bytes > scan_bytes - payload) {
			if (allow_truncated_data && identifier == UINT32_C(0x61746164)) {
				parsed.data_offset = payload;
				parsed.data_bytes = chunk_bytes;
				data_found = true;
				break;
			}
			return Fail("RIFF chunk exceeds source image", error);
		}
		if (identifier == UINT32_C(0x20746d66)) {
			if (format_found) return Fail("duplicate WAVE format chunk", error);
			if (chunk_bytes < 16U) return Fail("truncated WAVE format", error);
			const uint16_t encoding = Read_U16(data + payload);
			if (encoding != static_cast<uint16_t>(WaveEncoding::Pcm) &&
				encoding != static_cast<uint16_t>(WaveEncoding::ImaAdpcm) &&
				encoding != static_cast<uint16_t>(WaveEncoding::MicrosoftAdpcm)) {
				return Fail("unsupported WAVE encoding", error);
			}
			parsed.encoding = static_cast<WaveEncoding>(encoding);
			parsed.channels = Read_U16(data + payload + 2U);
			parsed.sample_rate = Read_U32(data + payload + 4U);
			parsed.block_align = Read_U16(data + payload + 12U);
			parsed.bits_per_sample = Read_U16(data + payload + 14U);
			if (parsed.channels == 0 || parsed.channels > 2 ||
				parsed.sample_rate < 8000U || parsed.sample_rate > 192000U ||
				parsed.block_align == 0) {
				return Fail("invalid WAVE format values", error);
			}
			if (encoding == static_cast<uint16_t>(WaveEncoding::Pcm)) {
				if ((parsed.bits_per_sample != 8U && parsed.bits_per_sample != 16U) ||
					parsed.block_align != parsed.channels * (parsed.bits_per_sample / 8U)) {
					return Fail("invalid PCM layout", error);
				}
			} else if (parsed.bits_per_sample != 4U) {
				return Fail("invalid ADPCM bit depth", error);
			}
			if (encoding != static_cast<uint16_t>(WaveEncoding::Pcm)) {
				if (chunk_bytes < 20U) return Fail("truncated ADPCM extension", error);
				parsed.samples_per_block = Read_U16(data + payload + 18U);
			}
			if (encoding == static_cast<uint16_t>(WaveEncoding::MicrosoftAdpcm)) {
				if (chunk_bytes < 22U) return Fail("truncated Microsoft ADPCM coefficients", error);
				const uint16_t coefficient_count = Read_U16(data + payload + 20U);
				if (coefficient_count == 0 || coefficient_count > 32U ||
					22U + static_cast<size_t>(coefficient_count) * 4U > chunk_bytes) {
					return Fail("invalid Microsoft ADPCM coefficients", error);
				}
				parsed.coefficients.reserve(static_cast<size_t>(coefficient_count) * 2U);
				for (uint16_t index = 0; index < coefficient_count; ++index) {
					parsed.coefficients.push_back(Read_S16(
						data + payload + 22U + static_cast<size_t>(index) * 4U));
					parsed.coefficients.push_back(Read_S16(
						data + payload + 24U + static_cast<size_t>(index) * 4U));
				}
			}
			format_found = true;
		} else if (identifier == UINT32_C(0x61746164)) {
			if (data_found) return Fail("duplicate WAVE data chunk", error);
			parsed.data_offset = payload;
			parsed.data_bytes = chunk_bytes;
			data_found = true;
		}
		const size_t padded = static_cast<size_t>(chunk_bytes) + (chunk_bytes & 1U);
		if (padded > scan_bytes - payload) break;
		offset = payload + padded;
	}
	if (!format_found || !data_found) return Fail("WAVE format or data chunk absent", error);
	parsed.sample_frames = Estimate_Frame_Count(parsed);
	*info = std::move(parsed);
	return true;
}

bool Decode_Wave(const uint8_t *data, size_t bytes, DecodedWave *decoded,
	const char **error)
{
	if (decoded == nullptr) return Fail("decoded output is null", error);
	WaveInfo info;
	if (!Inspect_Wave(data, bytes, &info, error)) return false;
	DecodedWave output;
	output.channels = info.channels;
	output.sample_rate = info.sample_rate;
	bool success = false;
	switch (info.encoding) {
		case WaveEncoding::Pcm:
			success = Decode_Pcm(data, info, &output, error);
			break;
		case WaveEncoding::ImaAdpcm:
			success = Decode_Ima(data, info, &output, error);
			break;
		case WaveEncoding::MicrosoftAdpcm:
			success = Decode_Microsoft_Adpcm(data, info, &output, error);
			break;
	}
	if (!success || output.samples.empty()) {
		return success ? Fail("decoded WAVE is empty", error) : false;
	}
	*decoded = std::move(output);
	return true;
}

} // namespace RenegadeVitaAudio
