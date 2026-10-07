#include "renegade_vita_frame_profile.h"

#include <psp2/kernel/processmgr.h>
#include <psp2/kernel/threadmgr.h>

#include <stdarg.h>
#include <stdio.h>
#include <string.h>

#ifndef RENEGADE_VITA_FRAME_PROFILE_DEFAULT
#define RENEGADE_VITA_FRAME_PROFILE_DEFAULT 1
#endif

// Declared in a30_vita_runtime.h; repeated to avoid its engine headers.
int A30_Vita_Log(const char *format, ...) __attribute__((format(printf, 1, 2)));

bool g_renegade_frame_profile_active = false;

namespace {

constexpr unsigned kSlots = 256U;          // power of two
constexpr unsigned kWindowFrames = 120U;
constexpr unsigned kReportedScopes = 16U;
constexpr unsigned kReportedWorstScopes = 10U;
// The first kExactCallsPerFrame entries of a scope in a frame are timed;
// later entries are timed with probability 1 / 2^kSampleShift.
constexpr uint32_t kExactCallsPerFrame = 2U;
constexpr unsigned kSampleShift = 4U;
constexpr unsigned kCalibrationCalls = 256U;
constexpr uint32_t kTokenIndexMask = 0xFFFFU;
constexpr uint32_t kTokenSampled = 0x10000U;

struct ProfileSlot {
	const char *name;
	uint64_t window_us;        // estimated inclusive time this window
	uint32_t window_calls;
	uint32_t frame_us;         // exact time of the first kExactCallsPerFrame calls
	uint32_t frame_sample_us;  // time of the sampled later calls
	uint32_t frame_calls;
	uint32_t frame_samples;
	uint32_t worst_frame_us;   // this scope's share of the window's worst frame
	bool touched;
};

ProfileSlot g_slots[kSlots];
unsigned g_touched[kSlots];
unsigned g_touched_count = 0U;
unsigned g_used_slots = 0U;
uint32_t g_overflow_scopes = 0U;
SceUID g_profiled_thread = -1;
// Profiled-thread test: the game thread's stack range when known (no kernel
// call per scope), otherwise its thread id.
uintptr_t g_profiled_stack_low = 0U;
uintptr_t g_profiled_stack_size = 0U;
uint32_t g_sample_state = 0x2545F491U;
uint32_t g_clock_read_ns = 0U;
uint32_t g_window_frames = 0U;
uint64_t g_window_frame_us = 0U;
uint32_t g_window_worst_us = 0U;
uint32_t g_window_worst_index = 0U;
uint64_t g_window_scopes = 0U;
uint64_t g_window_timed = 0U;
uint32_t g_frame_scopes = 0U;
uint32_t g_frame_timed = 0U;
uint32_t g_total_windows = 0U;

inline uint32_t Read_Clock_Us()
{
	// Same monotonic microsecond source as the frame and stage timers; the
	// low 32 bits are enough for scope durations (unsigned difference).
	return static_cast<uint32_t>(sceKernelGetProcessTimeWide());
}

inline bool On_Profiled_Thread()
{
	if (g_profiled_stack_size != 0U) {
		const uintptr_t frame = reinterpret_cast<uintptr_t>(__builtin_frame_address(0));
		return frame - g_profiled_stack_low < g_profiled_stack_size;
	}
	return sceKernelGetThreadId() == g_profiled_thread;
}

inline void Touch(ProfileSlot &slot)
{
	if (!slot.touched) {
		slot.touched = true;
		g_touched[g_touched_count++] = static_cast<unsigned>(&slot - g_slots);
	}
}

inline void Clear_Frame(ProfileSlot &slot)
{
	slot.frame_us = 0U;
	slot.frame_sample_us = 0U;
	slot.frame_calls = 0U;
	slot.frame_samples = 0U;
	slot.touched = false;
}

// Exact time of the first calls plus the sampled mean for the rest. With no
// sample among the later calls, the exact calls' mean stands in for them.
// Double (exact for these magnitudes) avoids a software 64-bit divide per
// hot slot per frame; the result is rounded to the nearest microsecond.
uint32_t Frame_Estimate_Us(const ProfileSlot &slot)
{
	if (slot.frame_calls <= kExactCallsPerFrame) return slot.frame_us;
	const double later_calls = static_cast<double>(slot.frame_calls - kExactCallsPerFrame);
	const double later_us = slot.frame_samples != 0U ?
		static_cast<double>(slot.frame_sample_us) * later_calls / slot.frame_samples :
		static_cast<double>(slot.frame_us) * later_calls / kExactCallsPerFrame;
	const double estimate = static_cast<double>(slot.frame_us) + later_us + 0.5;
	return estimate >= 4294967295.0 ? 0xFFFFFFFFU : static_cast<uint32_t>(estimate);
}

ProfileSlot *Find_Slot(const char *name)
{
	unsigned index = static_cast<unsigned>(reinterpret_cast<uintptr_t>(name) >> 2) & (kSlots - 1U);
	for (unsigned probe = 0U; probe < kSlots; ++probe) {
		ProfileSlot &slot = g_slots[index];
		if (slot.name == name) return &slot;
		if (slot.name == NULL) {
			// Keep a few slots free so lookups always terminate quickly.
			if (g_used_slots >= kSlots - 8U) return NULL;
			slot.name = name;
			++g_used_slots;
			return &slot;
		}
		index = (index + 1U) & (kSlots - 1U);
	}
	return NULL;
}

void Append_Name(char *line, size_t size, size_t &length, const char *name)
{
	// Scope names contain spaces; keep each log field one token.
	for (const char *cursor = name; *cursor != 0 && length + 1U < size; ++cursor) {
		const char c = *cursor;
		line[length++] = (c == ' ' || c == '=' || c == '/') ? '_' : c;
	}
	line[length] = 0;
}

void Appendf(char *line, size_t size, size_t &length, const char *format, ...)
	__attribute__((format(printf, 4, 5)));

void Appendf(char *line, size_t size, size_t &length, const char *format, ...)
{
	if (length + 1U >= size) return;
	va_list arguments;
	va_start(arguments, format);
	const int written = vsnprintf(line + length, size - length, format, arguments);
	va_end(arguments);
	if (written > 0) {
		length += static_cast<size_t>(written);
		if (length >= size) length = size - 1U;
	}
}

void Report_Window()
{
	unsigned order[kReportedScopes];
	unsigned order_count = 0U;
	for (unsigned index = 0U; index < kSlots; ++index) {
		if (g_slots[index].name == NULL || g_slots[index].window_calls == 0U) continue;
		unsigned position = order_count < kReportedScopes ? order_count++ : kReportedScopes;
		if (position == kReportedScopes) {
			if (g_slots[index].window_us <= g_slots[order[kReportedScopes - 1U]].window_us) continue;
			position = kReportedScopes - 1U;
		}
		while (position > 0U &&
			g_slots[order[position - 1U]].window_us < g_slots[index].window_us) {
			order[position] = order[position - 1U];
			--position;
		}
		order[position] = index;
	}
	char line[2048];
	size_t length = 0U;
	line[0] = 0;
	// version=2: avg_us of a scope entered more than exact_calls times per
	// frame is an estimate (see renegade_vita_frame_profile.h). Each of the
	// timed_per_frame scopes reads the clock twice; est_clock_us is that cost
	// at the calibrated clock_ns.
	const uint64_t timed_per_frame = g_window_timed / g_window_frames;
	Appendf(line, sizeof(line), length,
		"A3.6 frame-profile: version=2 window=%u frames=%u avg_frame_us=%llu worst_frame_us=%u worst_frame_index=%u scopes_per_frame=%llu timed_per_frame=%llu exact_calls=%u sample=1/%u clock_ns=%u est_clock_us=%llu overflow=%u inclusive=1 top avg_us/calls_per_frame:",
		g_total_windows, g_window_frames,
		static_cast<unsigned long long>(g_window_frame_us / g_window_frames),
		g_window_worst_us, g_window_worst_index,
		static_cast<unsigned long long>(g_window_scopes / g_window_frames),
		static_cast<unsigned long long>(timed_per_frame),
		static_cast<unsigned>(kExactCallsPerFrame), 1U << kSampleShift, g_clock_read_ns,
		static_cast<unsigned long long>(timed_per_frame * 2U * g_clock_read_ns / 1000U),
		g_overflow_scopes);
	for (unsigned i = 0U; i < order_count; ++i) {
		const ProfileSlot &slot = g_slots[order[i]];
		Appendf(line, sizeof(line), length, " ");
		Append_Name(line, sizeof(line), length, slot.name);
		Appendf(line, sizeof(line), length, "=%llu/%.1f",
			static_cast<unsigned long long>(slot.window_us / g_window_frames),
			static_cast<double>(slot.window_calls) / g_window_frames);
	}
	A30_Vita_Log("%s\n", line);

	// Separate line for the window's worst frame, largest scopes first.
	length = 0U;
	line[0] = 0;
	Appendf(line, sizeof(line), length,
		"A3.6 frame-profile-worst: window=%u frame_index=%u frame_us=%u scope_us:",
		g_total_windows, g_window_worst_index, g_window_worst_us);
	bool reported[kSlots] = {};
	for (unsigned rank = 0U; rank < kReportedWorstScopes; ++rank) {
		unsigned best = kSlots;
		for (unsigned index = 0U; index < kSlots; ++index) {
			if (reported[index] || g_slots[index].worst_frame_us == 0U) continue;
			if (best == kSlots || g_slots[index].worst_frame_us > g_slots[best].worst_frame_us) {
				best = index;
			}
		}
		if (best == kSlots) break;
		reported[best] = true;
		Appendf(line, sizeof(line), length, " ");
		Append_Name(line, sizeof(line), length, g_slots[best].name);
		Appendf(line, sizeof(line), length, "=%u", g_slots[best].worst_frame_us);
	}
	A30_Vita_Log("%s\n", line);

	for (unsigned index = 0U; index < kSlots; ++index) {
		g_slots[index].window_us = 0U;
		g_slots[index].window_calls = 0U;
		g_slots[index].worst_frame_us = 0U;
	}
	g_window_frames = 0U;
	g_window_frame_us = 0U;
	g_window_worst_us = 0U;
	g_window_worst_index = 0U;
	g_window_scopes = 0U;
	g_window_timed = 0U;
	++g_total_windows;
}

// Logs the per-call cost of the clock candidates once, so hardware logs can
// size the profiler's own overhead (timed_per_frame * 2 * clock_ns).
void Calibrate_Clock_Cost()
{
	volatile uint32_t sink = 0U;
	const uint64_t start = sceKernelGetProcessTimeWide();
	for (unsigned i = 0U; i < kCalibrationCalls; ++i) {
		sink = sink + static_cast<uint32_t>(sceKernelGetProcessTimeWide());
	}
	const uint64_t after_process_wide = sceKernelGetProcessTimeWide();
	for (unsigned i = 0U; i < kCalibrationCalls; ++i) {
		sink = sink + sceKernelGetProcessTimeLow();
	}
	const uint64_t after_process_low = sceKernelGetProcessTimeWide();
	for (unsigned i = 0U; i < kCalibrationCalls; ++i) {
		sink = sink + static_cast<uint32_t>(sceKernelGetSystemTimeWide());
	}
	const uint64_t after_system_wide = sceKernelGetProcessTimeWide();
	for (unsigned i = 0U; i < kCalibrationCalls; ++i) {
		sink = sink + static_cast<uint32_t>(sceKernelGetThreadId());
	}
	const uint64_t after_thread_id = sceKernelGetProcessTimeWide();
	for (unsigned i = 0U; i < kCalibrationCalls; ++i) {
		sink = sink + (On_Profiled_Thread() ? 1U : 0U);
	}
	const uint64_t after_thread_test = sceKernelGetProcessTimeWide();
	(void)sink;
	const auto per_call_ns = [](uint64_t begin, uint64_t end) {
		return static_cast<unsigned>((end - begin) * 1000U / kCalibrationCalls);
	};
	g_clock_read_ns = per_call_ns(start, after_process_wide);
	A30_Vita_Log("A3.6 frame-profile: clock-cost calls=%u process_time_wide_ns=%u process_time_low_ns=%u system_time_wide_ns=%u thread_id_ns=%u profiled_thread_test_ns=%u\n",
		kCalibrationCalls, g_clock_read_ns,
		per_call_ns(after_process_wide, after_process_low),
		per_call_ns(after_process_low, after_system_wide),
		per_call_ns(after_system_wide, after_thread_id),
		per_call_ns(after_thread_id, after_thread_test));
}

} // namespace

uint64_t Renegade_Frame_Profile_Begin(const char *name)
{
	if (!On_Profiled_Thread()) return 0U;
	++g_frame_scopes;
	ProfileSlot *slot = Find_Slot(name);
	if (slot == NULL) {
		++g_overflow_scopes;
		return 0U;
	}
	Touch(*slot);
	uint32_t flags = 0U;
	if (++slot->frame_calls > kExactCallsPerFrame) {
		// LCG; its top bits decide, so 1 in 2^kSampleShift entries is timed.
		g_sample_state = g_sample_state * 1664525U + 1013904223U;
		if ((g_sample_state >> (32U - kSampleShift)) != 0U) return 0U;
		flags = kTokenSampled;
	}
	++g_frame_timed;
	const uint32_t index = static_cast<uint32_t>(slot - g_slots) + 1U;
	return (static_cast<uint64_t>(Read_Clock_Us()) << 32) | flags | index;
}

void Renegade_Frame_Profile_End(uint64_t token)
{
	const uint32_t now_us = Read_Clock_Us();
	const uint32_t low = static_cast<uint32_t>(token);
	ProfileSlot &slot = g_slots[(low & kTokenIndexMask) - 1U];
	const uint32_t elapsed = now_us - static_cast<uint32_t>(token >> 32);
	// A scope opened before Begin_Frame still closes into the open frame.
	Touch(slot);
	if ((low & kTokenSampled) != 0U) {
		slot.frame_sample_us += elapsed;
		++slot.frame_samples;
	} else {
		slot.frame_us += elapsed;
	}
}

void Renegade_Frame_Profile_Configure(void)
{
	bool enabled = RENEGADE_VITA_FRAME_PROFILE_DEFAULT != 0;
	FILE *file = fopen("ux0:data/renegade/user/config/frame-profile-v1.flag", "rb");
	if (file != NULL) {
		char value[9] = {};
		const size_t size = fread(value, 1U, sizeof(value), file);
		const bool read_ok = !ferror(file);
		fclose(file);
		if (read_ok && size == 8U && memcmp(value, "RVFP1 ", 6U) == 0 &&
			value[7] == '\n' && (value[6] == '0' || value[6] == '1')) {
			enabled = value[6] == '1';
		}
	}
	g_profiled_thread = sceKernelGetThreadId();
	// Use the stack range only if it really contains this thread's frame.
	g_profiled_stack_low = 0U;
	g_profiled_stack_size = 0U;
	SceKernelThreadInfo info;
	memset(&info, 0, sizeof(info));
	info.size = sizeof(info);
	if (sceKernelGetThreadInfo(g_profiled_thread, &info) >= 0 &&
		info.stack != NULL && info.stackSize > 0) {
		const uintptr_t low = reinterpret_cast<uintptr_t>(info.stack);
		const uintptr_t size = static_cast<uintptr_t>(info.stackSize);
		const uintptr_t frame = reinterpret_cast<uintptr_t>(__builtin_frame_address(0));
		if (frame - low < size) {
			g_profiled_stack_low = low;
			g_profiled_stack_size = size;
		}
	}
	Calibrate_Clock_Cost();
	g_renegade_frame_profile_active = enabled;
	A30_Vita_Log("A3.6 frame-profile: configured enabled=%d window_frames=%u slots=%u thread=%08X thread_test=%s exact_calls=%u sample=1/%u\n",
		enabled ? 1 : 0, kWindowFrames, kSlots, static_cast<unsigned>(g_profiled_thread),
		g_profiled_stack_size != 0U ? "stack-range" : "thread-id",
		static_cast<unsigned>(kExactCallsPerFrame), 1U << kSampleShift);
}

void Renegade_Frame_Profile_Begin_Frame(void)
{
	// Discard scopes recorded since the previous frame closed. Calls reach
	// the window only in End_Frame, so nothing needs withdrawing.
	for (unsigned i = 0U; i < g_touched_count; ++i) Clear_Frame(g_slots[g_touched[i]]);
	g_touched_count = 0U;
	g_frame_scopes = 0U;
	g_frame_timed = 0U;
}

void Renegade_Frame_Profile_End_Frame(uint32_t frame_us)
{
	if (!g_renegade_frame_profile_active) return;
	const bool worst = g_window_frames == 0U || frame_us > g_window_worst_us;
	if (worst) {
		for (unsigned index = 0U; index < kSlots; ++index) g_slots[index].worst_frame_us = 0U;
		g_window_worst_us = frame_us;
		g_window_worst_index = g_window_frames;
	}
	for (unsigned i = 0U; i < g_touched_count; ++i) {
		ProfileSlot &slot = g_slots[g_touched[i]];
		const uint32_t estimate_us = Frame_Estimate_Us(slot);
		slot.window_us += estimate_us;
		slot.window_calls += slot.frame_calls;
		if (worst) slot.worst_frame_us = estimate_us;
		Clear_Frame(slot);
	}
	g_touched_count = 0U;
	g_window_scopes += g_frame_scopes;
	g_window_timed += g_frame_timed;
	g_frame_scopes = 0U;
	g_frame_timed = 0U;
	g_window_frame_us += frame_us;
	if (++g_window_frames >= kWindowFrames) Report_Window();
}
