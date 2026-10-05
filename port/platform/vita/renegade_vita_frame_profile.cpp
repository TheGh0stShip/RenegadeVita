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

struct ProfileSlot {
	const char *name;
	uint64_t window_us;
	uint32_t window_calls;
	uint32_t frame_us;
	uint32_t frame_calls;
	uint32_t worst_frame_us;   // this scope's share of the window's worst frame
	bool touched;
};

ProfileSlot g_slots[kSlots];
unsigned g_touched[kSlots];
unsigned g_touched_count = 0U;
unsigned g_used_slots = 0U;
uint32_t g_overflow_scopes = 0U;
SceUID g_profiled_thread = -1;
uint32_t g_window_frames = 0U;
uint64_t g_window_frame_us = 0U;
uint32_t g_window_worst_us = 0U;
uint32_t g_window_worst_index = 0U;
uint64_t g_window_scopes = 0U;
uint32_t g_frame_scopes = 0U;
uint32_t g_total_windows = 0U;

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
	Appendf(line, sizeof(line), length,
		"A3.6 frame-profile: version=1 window=%u frames=%u avg_frame_us=%llu worst_frame_us=%u worst_frame_index=%u scopes_per_frame=%llu overflow=%u inclusive=1 top avg_us/calls_per_frame:",
		g_total_windows, g_window_frames,
		static_cast<unsigned long long>(g_window_frame_us / g_window_frames),
		g_window_worst_us, g_window_worst_index,
		static_cast<unsigned long long>(g_window_scopes / g_window_frames),
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
	++g_total_windows;
}

} // namespace

uint64_t Renegade_Frame_Profile_Begin(void)
{
	if (sceKernelGetThreadId() != g_profiled_thread) return 0U;
	return sceKernelGetProcessTimeWide();
}

void Renegade_Frame_Profile_End(const char *name, uint64_t start_us)
{
	const uint64_t now_us = sceKernelGetProcessTimeWide();
	ProfileSlot *slot = Find_Slot(name);
	++g_frame_scopes;
	if (slot == NULL) {
		++g_overflow_scopes;
		return;
	}
	const uint64_t elapsed = now_us > start_us ? now_us - start_us : 0U;
	slot->frame_us += static_cast<uint32_t>(elapsed > 0xFFFFFFFFULL ? 0xFFFFFFFFULL : elapsed);
	++slot->window_calls;
	++slot->frame_calls;
	if (!slot->touched) {
		slot->touched = true;
		g_touched[g_touched_count++] = static_cast<unsigned>(slot - g_slots);
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
	g_renegade_frame_profile_active = enabled;
	A30_Vita_Log("A3.6 frame-profile: configured enabled=%d window_frames=%u slots=%u thread=%08X\n",
		enabled ? 1 : 0, kWindowFrames, kSlots, static_cast<unsigned>(g_profiled_thread));
}

void Renegade_Frame_Profile_Begin_Frame(void)
{
	for (unsigned i = 0U; i < g_touched_count; ++i) {
		ProfileSlot &slot = g_slots[g_touched[i]];
		// Calls were counted as they closed; withdraw the discarded ones.
		slot.window_calls -= slot.frame_calls;
		slot.frame_calls = 0U;
		slot.frame_us = 0U;
		slot.touched = false;
	}
	g_touched_count = 0U;
	g_frame_scopes = 0U;
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
		slot.window_us += slot.frame_us;
		if (worst) slot.worst_frame_us = slot.frame_us;
		slot.frame_us = 0U;
		slot.frame_calls = 0U;
		slot.touched = false;
	}
	g_touched_count = 0U;
	g_window_scopes += g_frame_scopes;
	g_frame_scopes = 0U;
	g_window_frame_us += frame_us;
	if (++g_window_frames >= kWindowFrames) Report_Window();
}
