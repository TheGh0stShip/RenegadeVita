#pragma once

// Internal rendering resolution for the Vita presentation boundary.
//
// The Vita display controller scans out a smaller framebuffer (720x408,
// 640x368 or 480x272) and scales it to the 960x544 panel at no GPU cost.
// The original engine keeps its 960x544 logical device: only the final
// logical-display -> physical-display-buffer viewport mapping, the full-target
// viewport and diagnostic readback know about the smaller buffer.
//
// This header is platform-free so the flag grammar, coordinate mapping,
// capture expansion and dynamic controller are host-testable.

#include <stddef.h>
#include <stdint.h>
#include <string.h>

namespace RenegadeVitaInternalResolution {

enum : uint32_t {
	LOGICAL_WIDTH = 960U,
	LOGICAL_HEIGHT = 544U
};

// Levels index the sizes sceDisplaySetFrameBuf accepts on the handheld.
enum : uint32_t {
	LEVEL_100 = 0U,
	LEVEL_75 = 1U,
	LEVEL_67 = 2U,
	LEVEL_50 = 3U,
	LEVEL_COUNT = 4U
};

struct LevelSize {
	uint32_t width;
	uint32_t height;
	uint32_t percent;
};

inline const LevelSize &Level_Size(uint32_t level)
{
	static const LevelSize sizes[LEVEL_COUNT] = {
		{960U, 544U, 100U}, {720U, 408U, 75U}, {640U, 368U, 67U}, {480U, 272U, 50U}
	};
	return sizes[level < LEVEL_COUNT ? level : LEVEL_100];
}

struct Mode {
	bool automatic;
	uint32_t level;
};

// Accepts exactly "RVIR1 100\n", "RVIR1 75\n", "RVIR1 67\n", "RVIR1 50\n" or
// "RVIR1 auto\n" (same strict style as msaa-v1.flag). Anything else leaves
// mode untouched and returns false.
inline bool Parse_Flag(const char *data, size_t size, Mode &mode)
{
	if (data == NULL || size < 8U || memcmp(data, "RVIR1 ", 6U) != 0 ||
		data[size - 1U] != '\n') {
		return false;
	}
	const char *value = data + 6U;
	const size_t length = size - 7U;
	struct Entry { const char *text; bool automatic; uint32_t level; };
	static const Entry entries[] = {
		{"100", false, LEVEL_100}, {"75", false, LEVEL_75},
		{"67", false, LEVEL_67}, {"50", false, LEVEL_50},
		{"auto", true, LEVEL_100}
	};
	for (size_t i = 0U; i < sizeof(entries) / sizeof(entries[0]); ++i) {
		if (strlen(entries[i].text) == length &&
			memcmp(entries[i].text, value, length) == 0) {
			mode.automatic = entries[i].automatic;
			mode.level = entries[i].level;
			return true;
		}
	}
	return false;
}

// Leading edges floor and trailing edges ceil, matching the existing
// logical->presentation mapping. When physical == logical the result is the
// input edge exactly, so 100% is bit-identical to the unscaled path.
inline uint32_t Scale_Edge(uint64_t logical_edge, uint32_t logical_dimension,
	uint32_t physical_dimension, bool trailing)
{
	if (logical_dimension == 0U) return 0U;
	const uint64_t scaled = logical_edge * physical_dimension;
	return static_cast<uint32_t>(trailing ?
		(scaled + logical_dimension - 1U) / logical_dimension :
		scaled / logical_dimension);
}

// Expands a packed physical RGBA8888 image at the start of pixels, in place,
// to logical_width x logical_height by nearest neighbour. Row order (GL
// bottom-up) is preserved. Safe in place: every destination pixel d reads
// source s(d) <= d, and destinations are written in decreasing order, so no
// source still needed is overwritten (s(d') <= d' < d for every later d').
inline void Expand_Capture_In_Place(uint8_t *pixels, uint32_t physical_width,
	uint32_t physical_height, uint32_t logical_width, uint32_t logical_height)
{
	if (pixels == NULL || physical_width == 0U || physical_height == 0U ||
		physical_width > logical_width || physical_height > logical_height ||
		(physical_width == logical_width && physical_height == logical_height)) {
		return;
	}
	for (uint32_t y = logical_height; y-- > 0U;) {
		const uint32_t source_y = static_cast<uint32_t>(
			static_cast<uint64_t>(y) * physical_height / logical_height);
		for (uint32_t x = logical_width; x-- > 0U;) {
			const uint32_t source_x = static_cast<uint32_t>(
				static_cast<uint64_t>(x) * physical_width / logical_width);
			memmove(pixels + (static_cast<size_t>(y) * logical_width + x) * 4U,
				pixels + (static_cast<size_t>(source_y) * physical_width + source_x) * 4U,
				4U);
		}
	}
}

enum DecisionKind {
	DECISION_NONE = 0,       // window not yet full
	DECISION_HOLD,
	DECISION_HOLD_STALL,     // loading/stall window: no judgement
	DECISION_DOWN,           // lower resolution
	DECISION_UP,             // higher resolution
	DECISION_REVERT_DOWN,    // lower step bought < 5% p50: undo and lock
	DECISION_REVERT_UP       // higher step regressed: undo and lock
};

inline const char *Decision_Name(DecisionKind kind)
{
	switch (kind) {
	case DECISION_HOLD: return "hold";
	case DECISION_HOLD_STALL: return "hold-stall";
	case DECISION_DOWN: return "down";
	case DECISION_UP: return "up";
	case DECISION_REVERT_DOWN: return "revert-ineffective-down";
	case DECISION_REVERT_UP: return "revert-regressed-up";
	default: return "none";
	}
}

struct Decision {
	DecisionKind kind;
	uint32_t previous_level;
	uint32_t level;
	uint32_t p50_us;
	uint32_t p95_us;
	uint32_t down_lock;
	uint32_t up_lock;
};

// Frame-time driven level controller, evaluated once per 120-frame
// checkpoint over a complete window of 120 present-to-present intervals. Policy (all on the 120-frame p50/p95 of present-to-present time):
//   down  when p50 > 34.0 ms (missing the 33.3 ms / 30 fps budget);
//   up    when p50 <= 25.0 ms and p95 <= 33.4 ms (comfortably inside it);
//   hold  between the two bands (hysteresis), and for stall windows
//         (p50 > 200 ms: loading screens, level transitions).
// At most one step per evaluation; an up step additionally needs the level to
// have held for UP_DWELL evaluations. A down step that does not improve p50 by
// at least 5% (CPU-bound frame: fill is not the cost) is reverted and further
// down steps are locked out; an up step that falls back into the down band is
// reverted and further up steps are locked out. Lockouts start at 4
// evaluations and double per revert up to 256 (30720 frames), so the number of
// changes over any period is logarithmically bounded.
class Controller {
public:
	enum : uint32_t {
		WINDOW = 120U,
		DOWN_P50_US = 34000U,
		UP_P50_US = 25000U,
		UP_P95_US = 33400U,
		STALL_P50_US = 200000U,
		MIN_IMPROVEMENT_PERCENT = 5U,
		BACKOFF_INITIAL = 4U,
		BACKOFF_MAX = 256U,
		UP_DWELL = 3U
	};

	Controller() { Reset(LEVEL_100, LEVEL_50); }

	void Reset(uint32_t level, uint32_t lowest_level)
	{
		lowest_level_ = lowest_level < LEVEL_COUNT ? lowest_level : LEVEL_50;
		level_ = level <= lowest_level_ ? level : lowest_level_;
		count_ = 0U;
		probation_ = PROBATION_NONE;
		since_change_ = 0U;
		p50_before_ = 0U;
		down_lock_ = 0U;
		up_lock_ = 0U;
		backoff_ = BACKOFF_INITIAL;
	}

	uint32_t Level() const { return level_; }
	uint32_t Samples() const { return count_; }

	// Returns true when the window is full and Evaluate() should run.
	bool Record_Frame(uint32_t frame_us)
	{
		if (count_ < WINDOW) samples_[count_++] = frame_us;
		return count_ >= WINDOW;
	}

	Decision Evaluate()
	{
		Decision decision = {};
		decision.previous_level = level_;
		decision.level = level_;
		if (count_ < WINDOW) {
			// Incomplete window (missed presents): discard rather than judge.
			count_ = 0U;
			decision.kind = DECISION_NONE;
			return decision;
		}
		uint32_t sorted[WINDOW];
		memcpy(sorted, samples_, sizeof(sorted));
		// Insertion sort: 120 values once per 120 frames; avoids <algorithm>
		// next to the original headers' min/max definitions.
		for (uint32_t i = 1U; i < WINDOW; ++i) {
			const uint32_t value = sorted[i];
			uint32_t j = i;
			for (; j > 0U && sorted[j - 1U] > value; --j) sorted[j] = sorted[j - 1U];
			sorted[j] = value;
		}
		count_ = 0U;
		const uint32_t p50 = sorted[WINDOW / 2U];
		const uint32_t p95 = sorted[(WINDOW * 95U) / 100U];
		decision.p50_us = p50;
		decision.p95_us = p95;
		decision.kind = Decide(p50, p95);
		decision.level = level_;
		decision.down_lock = down_lock_;
		decision.up_lock = up_lock_;
		return decision;
	}

private:
	enum Probation { PROBATION_NONE, PROBATION_AFTER_DOWN, PROBATION_AFTER_UP };

	void Lock(uint32_t &lock)
	{
		lock = backoff_;
		backoff_ = backoff_ * 2U > BACKOFF_MAX ? BACKOFF_MAX : backoff_ * 2U;
	}

	DecisionKind Decide(uint32_t p50, uint32_t p95)
	{
		if (p50 > STALL_P50_US) return DECISION_HOLD_STALL;
		if (down_lock_ > 0U) --down_lock_;
		if (up_lock_ > 0U) --up_lock_;
		if (since_change_ < UP_DWELL) ++since_change_;
		if (probation_ == PROBATION_AFTER_DOWN) {
			probation_ = PROBATION_NONE;
			if (static_cast<uint64_t>(p50) * 100U >
				static_cast<uint64_t>(p50_before_) * (100U - MIN_IMPROVEMENT_PERCENT)) {
				--level_;
				since_change_ = 0U;
				Lock(down_lock_);
				return DECISION_REVERT_DOWN;
			}
		} else if (probation_ == PROBATION_AFTER_UP) {
			probation_ = PROBATION_NONE;
			if (p50 > DOWN_P50_US) {
				++level_;
				since_change_ = 0U;
				Lock(up_lock_);
				return DECISION_REVERT_UP;
			}
		}
		if (p50 > DOWN_P50_US && level_ < lowest_level_ && down_lock_ == 0U) {
			++level_;
			since_change_ = 0U;
			probation_ = PROBATION_AFTER_DOWN;
			p50_before_ = p50;
			return DECISION_DOWN;
		}
		if (p50 <= UP_P50_US && p95 <= UP_P95_US && level_ > LEVEL_100 &&
			up_lock_ == 0U && since_change_ >= UP_DWELL) {
			--level_;
			since_change_ = 0U;
			probation_ = PROBATION_AFTER_UP;
			return DECISION_UP;
		}
		return DECISION_HOLD;
	}

	uint32_t samples_[WINDOW];
	uint32_t count_;
	uint32_t level_;
	uint32_t lowest_level_;
	Probation probation_;
	uint32_t since_change_;
	uint32_t p50_before_;
	uint32_t down_lock_;
	uint32_t up_lock_;
	uint32_t backoff_;
};

} // namespace RenegadeVitaInternalResolution
