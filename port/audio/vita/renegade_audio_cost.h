#pragma once

// RVAU1 audio cost switches. A user config file
// ux0:data/renegade/user/config/audio-cost-v1.flag containing exactly
// "RVAU1 <hex digit>\n" selects a mask; anything else keeps the build default
// (all off). Every bit changes only where decoded PCM and transient file
// images live and whether a decode is repeated; the PCM the mixer reads, its
// cursor, loop and gain arithmetic are unchanged.
//   bit 0  ADPCM decodes reserve their final sample count once (no regrowth)
//   bit 1  a stream open reuses a cached decode of identical bytes before
//          decoding them again
//   bit 2  a stream's decoded PCM enters the PCM cache on its second open
//   bit 3  stream file images up to one slab are read into a reusable slab

#include <atomic>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <new>

#if !defined(RENEGADE_VITA_AUDIO_COST_DEFAULT)
#define RENEGADE_VITA_AUDIO_COST_DEFAULT 0U
#endif

enum {
	RENEGADE_AUDIO_COST_EXACT_DECODE_RESERVE = 1U,
	RENEGADE_AUDIO_COST_STREAM_CACHE_PROBE = 2U,
	RENEGADE_AUDIO_COST_STREAM_SECOND_OPEN_ADMISSION = 4U,
	RENEGADE_AUDIO_COST_STREAM_IMAGE_POOL = 8U,
	RENEGADE_AUDIO_COST_ALL = 15U
};

// Exactly "RVAU1 <hex digit>\n" (8 bytes). Returns false otherwise.
inline bool Renegade_Parse_Audio_Cost_Flag(const char *value, size_t size, unsigned *mode)
{
	if (value == nullptr || mode == nullptr || size != 8U ||
		std::memcmp(value, "RVAU1 ", 6U) != 0 || value[7] != '\n') return false;
	const char digit = value[6];
	if (digit >= '0' && digit <= '9') {
		*mode = static_cast<unsigned>(digit - '0');
	} else if (digit >= 'A' && digit <= 'F') {
		*mode = 10U + static_cast<unsigned>(digit - 'A');
	} else if (digit >= 'a' && digit <= 'f') {
		*mode = 10U + static_cast<unsigned>(digit - 'a');
	} else {
		return false;
	}
	return true;
}

struct RenegadeAudioImageLease {
	uint8_t *data = nullptr;
	size_t slot = 0U;
};

// A bounded set of identically sized reusable byte slabs for transient stream
// file images. A slab is claimed for one open and returned before that open
// publishes. A request larger than a slab, finding every slab claimed, or
// failing to allocate a slab gets no lease; the caller then uses its existing
// heap allocation. Slabs are allocated on first claim and kept until
// Free_Idle. Claims are atomic, so no provider lock is needed.
template <size_t SlabBytes, size_t Slabs>
class RenegadeAudioImagePool {
	static_assert(SlabBytes > 0U && Slabs > 0U, "empty image pool");
	std::atomic<bool> claimed[Slabs] = {};
	uint8_t *slabs[Slabs] = {};   // touched only by the claim holder
	std::atomic<uint32_t> resident{0U};
	std::atomic<uint32_t> hits{0U};
	std::atomic<uint32_t> oversize{0U};
	std::atomic<uint32_t> busy{0U};
	std::atomic<uint32_t> allocation_failures{0U};

public:
	static constexpr size_t kSlabBytes = SlabBytes;
	static constexpr size_t kSlabs = Slabs;

	bool Acquire(size_t bytes, RenegadeAudioImageLease *lease)
	{
		if (lease == nullptr) return false;
		lease->data = nullptr;
		if (bytes == 0U || bytes > SlabBytes) {
			oversize.fetch_add(1U, std::memory_order_relaxed);
			return false;
		}
		for (size_t slot = 0U; slot < Slabs; ++slot) {
			bool expected = false;
			if (!claimed[slot].compare_exchange_strong(expected, true,
				std::memory_order_acquire, std::memory_order_relaxed)) continue;
			if (slabs[slot] == nullptr) {
				slabs[slot] = new (std::nothrow) uint8_t[SlabBytes];
				if (slabs[slot] == nullptr) {
					claimed[slot].store(false, std::memory_order_release);
					allocation_failures.fetch_add(1U, std::memory_order_relaxed);
					return false;
				}
				resident.fetch_add(1U, std::memory_order_relaxed);
			}
			lease->data = slabs[slot];
			lease->slot = slot;
			hits.fetch_add(1U, std::memory_order_relaxed);
			return true;
		}
		busy.fetch_add(1U, std::memory_order_relaxed);
		return false;
	}

	void Release(RenegadeAudioImageLease *lease)
	{
		if (lease == nullptr || lease->data == nullptr || lease->slot >= Slabs) return;
		lease->data = nullptr;
		claimed[lease->slot].store(false, std::memory_order_release);
	}

	// Frees every slab not currently claimed (shutdown).
	void Free_Idle()
	{
		for (size_t slot = 0U; slot < Slabs; ++slot) {
			bool expected = false;
			if (!claimed[slot].compare_exchange_strong(expected, true,
				std::memory_order_acquire, std::memory_order_relaxed)) continue;
			if (slabs[slot] != nullptr) {
				delete[] slabs[slot];
				slabs[slot] = nullptr;
				resident.fetch_sub(1U, std::memory_order_relaxed);
			}
			claimed[slot].store(false, std::memory_order_release);
		}
	}

	uint32_t Resident_Bytes() const
	{
		return resident.load(std::memory_order_relaxed) * static_cast<uint32_t>(SlabBytes);
	}
	uint32_t Hits() const { return hits.load(std::memory_order_relaxed); }
	uint32_t Oversize() const { return oversize.load(std::memory_order_relaxed); }
	uint32_t Busy() const { return busy.load(std::memory_order_relaxed); }
	uint32_t Allocation_Failures() const
	{
		return allocation_failures.load(std::memory_order_relaxed);
	}
};
