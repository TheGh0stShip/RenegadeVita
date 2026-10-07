#pragma once

// Presentation pacing for the Vita present boundary (frame-pacing-v1.flag,
// prefix RVFR1).
//
// With vsync on and the game running between 30 and 60 fps, frames are shown
// for one or two vblanks in an irregular pattern (16.7/33.3 ms judder). The
// controller below chooses only the vitaGL swap interval (eglSwapInterval:
// 1 = flip on every vblank, 2 = hold each frame for two vblanks, read by the
// display queue callback, gxm.c:236-263). It never touches simulation time:
// the original TimeManager keeps measuring real elapsed time (TIMEGETTIME)
// every frame and still caps the step at 1/SLOWEST_FPS (combat/timemgr.cpp).
//
// Platform-free and host-checkable without a compiler:
// tools/frame_pacing_model.py is a line-for-line Python mirror of this header
// and tools/test_vita_frame_pacing.py drives synthetic frame-time traces
// through it, then cross-checks the constants, flag table and decision names
// parsed from this file. Change both files together.

#include <stddef.h>
#include <stdint.h>
#include <string.h>

namespace RenegadeVitaFramePacing {

enum : uint32_t {
	MODE_OFF = 0U,       // swap interval never touched (current behaviour)
	MODE_LOCK30 = 1U,    // swap interval 2 whenever armed
	MODE_ADAPTIVE = 2U,  // swap interval 1 or 2 per window, with hysteresis
	MODE_COUNT = 3U
};

inline const char *Mode_Name(uint32_t mode)
{
	switch (mode) {
	case MODE_LOCK30: return "lock30";
	case MODE_ADAPTIVE: return "adaptive";
	default: return "off";
	}
}

// Accepts exactly "RVFR1 off\n", "RVFR1 30\n" or "RVFR1 auto\n" (same strict
// style as internal-resolution-v1.flag). Anything else leaves mode untouched
// and returns false. No file at all is handled by the caller (pacing code
// does not run); "off" keeps the current presentation but logs cadence.
inline bool Parse_Flag(const char *data, size_t size, uint32_t &mode)
{
	if (data == NULL || size < 8U || memcmp(data, "RVFR1 ", 6U) != 0 ||
		data[size - 1U] != '\n') {
		return false;
	}
	const char *value = data + 6U;
	const size_t length = size - 7U;
	struct Entry { const char *text; uint32_t mode; };
	static const Entry entries[] = {
		{"off", MODE_OFF}, {"30", MODE_LOCK30}, {"auto", MODE_ADAPTIVE}
	};
	for (size_t i = 0U; i < sizeof(entries) / sizeof(entries[0]); ++i) {
		if (strlen(entries[i].text) == length &&
			memcmp(entries[i].text, value, length) == 0) {
			mode = entries[i].mode;
			return true;
		}
	}
	return false;
}

// Display cadence proxy: vblanks elapsed between consecutive present returns
// on the game thread (sceDisplayGetVcount deltas). A 60 Hz lock is all ones,
// a 30 Hz lock all twos; judder shows up as changes between consecutive
// deltas. Break() drops the predecessor across stalls and dialog frames.
class Cadence {
public:
	Cadence() { Reset(); last_ = 0U; have_last_ = false; }

	void Reset()
	{
		frames = 0U;
		zero = 0U;
		one = 0U;
		two = 0U;
		three_plus = 0U;
		changes = 0U;
	}

	void Break() { have_last_ = false; }

	void Record(uint32_t delta)
	{
		++frames;
		if (delta == 0U) ++zero;
		else if (delta == 1U) ++one;
		else if (delta == 2U) ++two;
		else ++three_plus;
		if (have_last_ && delta != last_) ++changes;
		last_ = delta;
		have_last_ = true;
	}

	uint32_t frames;
	uint32_t zero;
	uint32_t one;
	uint32_t two;
	uint32_t three_plus;
	uint32_t changes;

private:
	uint32_t last_;
	bool have_last_;
};

enum DecisionKind {
	DECISION_NONE = 0,   // no window evaluated and no arm/suspend this frame
	DECISION_HOLD,       // window evaluated, target unchanged
	DECISION_SUSPEND,    // stall or dialog: back to every vblank, window dropped
	DECISION_ARM,        // ARM_FRAMES steady presents: target applies again
	DECISION_DOWN,       // 60 -> 30: window p95 present interval > DOWN_P95_US
	DECISION_UP,         // 30 -> 60 probe: UP_DWELL windows of CPU headroom
	DECISION_REVERT_UP   // probe window missed 60: back to 30, up locked out
};

inline const char *Decision_Name(DecisionKind kind)
{
	switch (kind) {
	case DECISION_HOLD: return "hold";
	case DECISION_SUSPEND: return "suspend";
	case DECISION_ARM: return "arm";
	case DECISION_DOWN: return "down";
	case DECISION_UP: return "up";
	case DECISION_REVERT_UP: return "revert-up";
	default: return "none";
	}
}

struct Decision {
	DecisionKind kind;
	uint32_t previous_interval;
	uint32_t interval;
	uint32_t p95_interval_us;
	uint32_t p95_busy_us;
	uint32_t up_lock;
	uint32_t headroom_windows;
};

// Swap-interval controller, one Record_Frame per presented frame.
//   lock30:   interval 2 while armed.
//   adaptive: start at 60 (interval 1). Over each full WINDOW of presents:
//     at 60, p95 present interval > DOWN_P95_US (missing 60 often enough to
//            judder) drops to 30;
//     at 30, present intervals are vsync-bound and say nothing about
//            headroom, so the game-thread busy time (interval minus the time
//            blocked in the present call) is judged instead: UP_DWELL
//            consecutive windows with p95 busy <= UP_BUSY_P95_US probe 60.
//     The first PROBATION_WINDOWS full windows after a probe are probation:
//     missing 60 there (GPU cost is invisible to busy time, or the content is
//     only briefly lighter) reverts the probe and locks up steps out for 4,
//     8, ... up to 256 windows, so the number of failed probes over any
//     period is logarithmically bounded.
//   Both: a present gap > STALL_US (loading, level transitions) or a dialog
//   frame suspends pacing (interval 1, window dropped, headroom cleared);
//   ARM_FRAMES consecutive steady presents re-arm it with the target kept.
class Controller {
public:
	enum : uint32_t {
		WINDOW = 60U,
		DOWN_P95_US = 17500U,
		UP_BUSY_P95_US = 13000U,
		UP_DWELL = 3U,
		PROBATION_WINDOWS = 3U,
		STALL_US = 200000U,
		ARM_FRAMES = 60U,
		BACKOFF_INITIAL = 4U,
		BACKOFF_MAX = 256U
	};

	Controller() { Reset(MODE_OFF); }

	void Reset(uint32_t mode)
	{
		mode_ = mode < MODE_COUNT ? mode : static_cast<uint32_t>(MODE_OFF);
		target_ = mode_ == MODE_LOCK30 ? 2U : 1U;
		armed_ = false;
		steady_ = 0U;
		count_ = 0U;
		probation_ = 0U;
		headroom_ = 0U;
		up_lock_ = 0U;
		backoff_ = BACKOFF_INITIAL;
	}

	uint32_t Mode() const { return mode_; }
	bool Armed() const { return armed_; }
	uint32_t Target() const { return target_; }
	// Swap interval to apply now: the target while armed, every vblank otherwise.
	uint32_t Interval() const { return armed_ ? target_ : 1U; }

	// interval_us: present-to-present time; busy_us: the part of it spent
	// outside the present call; suspend: frame must not be judged (IME).
	Decision Record_Frame(uint32_t interval_us, uint32_t busy_us, bool suspend)
	{
		Decision decision = {};
		decision.kind = DECISION_NONE;
		decision.previous_interval = Interval();
		if (mode_ != MODE_OFF) {
			if (suspend || interval_us > STALL_US) {
				count_ = 0U;
				steady_ = 0U;
				headroom_ = 0U;
				if (armed_) {
					armed_ = false;
					decision.kind = DECISION_SUSPEND;
				}
			} else if (!armed_) {
				++steady_;
				if (steady_ >= ARM_FRAMES) {
					armed_ = true;
					count_ = 0U;
					decision.kind = DECISION_ARM;
				}
			} else {
				interval_samples_[count_] = interval_us;
				busy_samples_[count_] = busy_us;
				++count_;
				if (count_ >= WINDOW) {
					count_ = 0U;
					decision.p95_interval_us = P95(interval_samples_);
					decision.p95_busy_us = P95(busy_samples_);
					decision.kind = Decide(decision.p95_interval_us, decision.p95_busy_us);
				}
			}
		}
		decision.interval = Interval();
		decision.up_lock = up_lock_;
		decision.headroom_windows = headroom_;
		return decision;
	}

private:
	// Insertion sort of one window copy: 60 values once per 60 frames; avoids
	// <algorithm> next to the original headers' min/max definitions.
	static uint32_t P95(const uint32_t *samples)
	{
		uint32_t sorted[WINDOW];
		memcpy(sorted, samples, sizeof(sorted));
		for (uint32_t i = 1U; i < WINDOW; ++i) {
			const uint32_t value = sorted[i];
			uint32_t j = i;
			for (; j > 0U && sorted[j - 1U] > value; --j) sorted[j] = sorted[j - 1U];
			sorted[j] = value;
		}
		return sorted[(WINDOW * 95U) / 100U];
	}

	void Lock_Up()
	{
		up_lock_ = backoff_;
		backoff_ = backoff_ * 2U > BACKOFF_MAX ? static_cast<uint32_t>(BACKOFF_MAX) : backoff_ * 2U;
	}

	DecisionKind Decide(uint32_t p95_interval, uint32_t p95_busy)
	{
		if (mode_ != MODE_ADAPTIVE) return DECISION_HOLD;
		if (up_lock_ > 0U) --up_lock_;
		if (target_ == 1U) {
			if (p95_interval <= DOWN_P95_US) {
				if (probation_ > 0U) --probation_;
				return DECISION_HOLD;
			}
			target_ = 2U;
			headroom_ = 0U;
			if (probation_ > 0U) {
				probation_ = 0U;
				Lock_Up();
				return DECISION_REVERT_UP;
			}
			return DECISION_DOWN;
		}
		if (p95_busy <= UP_BUSY_P95_US) {
			if (headroom_ < UP_DWELL) ++headroom_;
		} else {
			headroom_ = 0U;
		}
		if (headroom_ >= UP_DWELL && up_lock_ == 0U) {
			target_ = 1U;
			headroom_ = 0U;
			probation_ = PROBATION_WINDOWS;
			return DECISION_UP;
		}
		return DECISION_HOLD;
	}

	uint32_t interval_samples_[WINDOW];
	uint32_t busy_samples_[WINDOW];
	uint32_t mode_;
	uint32_t target_;
	bool armed_;
	uint32_t steady_;
	uint32_t count_;
	uint32_t probation_;
	uint32_t headroom_;
	uint32_t up_lock_;
	uint32_t backoff_;
};

} // namespace RenegadeVitaFramePacing
