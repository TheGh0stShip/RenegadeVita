#pragma once

#include <stddef.h>
#include <stdint.h>
#include <string.h>

namespace RenegadeVitaInputRoute {

enum Mode : uint32_t {
	MODE_PASSTHROUGH = 0U,
	MODE_RECORD = 1U,
	MODE_REPLAY = 2U,
	MODE_REJECTED = 3U,
};

enum : uint32_t {
	LEGACY_VERSION = 1U,
	VERSION = 2U,
	FLAG_COMPLETE = 1U,
	FLAG_TRUNCATED = 2U,
	MAX_SAMPLES = 18000U,
};

struct Sample {
	uint32_t buttons;
	uint8_t lx;
	uint8_t ly;
	uint8_t rx;
	uint8_t ry;
};

struct TimedSample {
	uint32_t buttons;
	uint8_t lx;
	uint8_t ly;
	uint8_t rx;
	uint8_t ry;
	uint32_t delta_us;
};

struct Header {
	char magic[8];
	uint32_t version;
	uint32_t sample_size;
	uint32_t sample_count;
	uint32_t flags;
	uint32_t checksum;
	uint32_t reserved;
};

static_assert(sizeof(Sample) == 8U, "input route sample ABI changed");
static_assert(sizeof(TimedSample) == 12U, "timed input route sample ABI changed");
static_assert(sizeof(Header) == 32U, "input route header ABI changed");

inline uint32_t Checksum_Bytes(const void *payload, size_t byte_count)
{
	const uint8_t *bytes = reinterpret_cast<const uint8_t *>(payload);
	uint32_t checksum = 2166136261U;
	for (size_t index = 0; index < byte_count; ++index) {
		checksum ^= bytes[index];
		checksum *= 16777619U;
	}
	return checksum;
}

inline uint32_t Checksum(const Sample *samples, uint32_t sample_count)
{
	return Checksum_Bytes(samples, static_cast<size_t>(sample_count) * sizeof(Sample));
}

inline uint32_t Checksum(const TimedSample *samples, uint32_t sample_count)
{
	return Checksum_Bytes(samples, static_cast<size_t>(sample_count) * sizeof(TimedSample));
}

inline Header Build_Legacy_Header(const Sample *samples, uint32_t sample_count, bool truncated)
{
	Header header = {};
	memcpy(header.magic, "RVINPUT1", sizeof(header.magic));
	header.version = LEGACY_VERSION;
	header.sample_size = sizeof(Sample);
	header.sample_count = sample_count;
	header.flags = FLAG_COMPLETE | (truncated ? FLAG_TRUNCATED : 0U);
	header.checksum = Checksum(samples, sample_count);
	return header;
}

inline Header Build_Header(const Sample *samples, uint32_t sample_count, bool truncated)
{
	return Build_Legacy_Header(samples, sample_count, truncated);
}

inline Header Build_Header(const TimedSample *samples, uint32_t sample_count, bool truncated)
{
	Header header = {};
	memcpy(header.magic, "RVINPUT1", sizeof(header.magic));
	header.version = VERSION;
	header.sample_size = sizeof(TimedSample);
	header.sample_count = sample_count;
	header.flags = FLAG_COMPLETE | (truncated ? FLAG_TRUNCATED : 0U);
	header.checksum = Checksum(samples, sample_count);
	return header;
}

inline bool Is_Supported_Format(uint32_t version, uint32_t sample_size)
{
	return (version == LEGACY_VERSION && sample_size == sizeof(Sample)) ||
		(version == VERSION && sample_size == sizeof(TimedSample));
}

inline bool Validate_Header(const Header &header, size_t file_size)
{
	const uint32_t known_flags = FLAG_COMPLETE | FLAG_TRUNCATED;
	return memcmp(header.magic, "RVINPUT1", sizeof(header.magic)) == 0 &&
		Is_Supported_Format(header.version, header.sample_size) &&
		header.sample_count > 0U && header.sample_count <= MAX_SAMPLES &&
		(header.flags & FLAG_COMPLETE) != 0U &&
		(header.flags & ~known_flags) == 0U && header.reserved == 0U &&
		file_size == sizeof(Header) +
			static_cast<size_t>(header.sample_count) * header.sample_size;
}

} // namespace RenegadeVitaInputRoute
