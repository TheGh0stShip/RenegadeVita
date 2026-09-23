#pragma once

// Opt-in local development input below original DirectInput/game ownership.
// No socket, emulator hook, save-state mutation or background desktop input.
#include <psp2/ctrl.h>
#include <psp2/io/fcntl.h>
#include <psp2/io/stat.h>
#include <psp2/kernel/processmgr.h>
#include <psp2/rtc.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "vita_runtime_log.h"

namespace RenegadeVitaDevInput {

static const char *const kEnable = "ux0:data/renegade/user/config/dev-input-enable.flag";
static const char *const kSession = "ux0:data/renegade/user/config/dev-input-session.txt";
static const char *const kCommand = "ux0:data/renegade/user/config/dev-input-command.txt";
static const char *const kAck = "ux0:data/renegade/user/config/dev-input-ack.txt";
static const uint32_t kButtonMask = 0x0000f3f9U;

struct State {
	bool enabled;
	bool active;
	uint64_t token;
	uint64_t expires;
	uint64_t next_poll;
	uint64_t next_enable_check;
	SceOff command_size;
	SceDateTime command_mtime;
	uint32_t sequence;
	uint32_t buttons;
	uint8_t lx, ly, rx, ry;
	bool command_stat_valid;
};

inline State &Get_State()
{
	static State state = {};
	return state;
}

inline int Read_Text(const char *path, char *text, unsigned capacity)
{
	const SceUID file = sceIoOpen(path, SCE_O_RDONLY, 0);
	if (file < 0) return -1;
	const int bytes = sceIoRead(file, text, capacity - 1U);
	const int closed = sceIoClose(file);
	if (bytes < 0 || closed < 0 || static_cast<unsigned>(bytes) >= capacity - 1U) return -1;
	text[bytes] = 0;
	return bytes;
}

inline bool Write_Text(const char *path, const char *text)
{
	const SceUID file = sceIoOpen(path, SCE_O_WRONLY | SCE_O_CREAT | SCE_O_TRUNC, 0666);
	if (file < 0) return false;
	const unsigned length = static_cast<unsigned>(strlen(text));
	const int written = sceIoWrite(file, text, length);
	const int closed = sceIoClose(file);
	return written == static_cast<int>(length) && closed >= 0;
}

inline bool Write_Ack(const char *status)
{
	const State &state = Get_State();
	char text[96];
	snprintf(text, sizeof(text), "RVDEV1 %016llx %u %s\n",
		static_cast<unsigned long long>(state.token), state.sequence, status);
	return Write_Text(kAck, text);
}

inline bool Marker_Enabled()
{
	char marker[32];
	return Read_Text(kEnable, marker, sizeof(marker)) == 7 && strcmp(marker, "RVDEV1\n") == 0;
}

inline bool Same_Time(const SceDateTime &left, const SceDateTime &right)
{
	return left.year == right.year && left.month == right.month &&
		left.day == right.day && left.hour == right.hour &&
		left.minute == right.minute && left.second == right.second &&
		left.microsecond == right.microsecond;
}

inline bool Command_File_Changed(State &state)
{
	SceIoStat status = {};
	if (sceIoGetstat(kCommand, &status) < 0) {
		state.command_stat_valid = false;
		return false;
	}
	if (state.command_stat_valid && state.command_size == status.st_size &&
		Same_Time(state.command_mtime, status.st_mtime)) {
		return false;
	}
	state.command_size = status.st_size;
	state.command_mtime = status.st_mtime;
	state.command_stat_valid = true;
	return true;
}

inline void Shutdown()
{
	State &state = Get_State();
	if (state.enabled) {
		state.active = false;
		Write_Ack("STOPPED");
		sceIoRemove(kSession);
		Vita_Append_A22_Runtime_Breadcrumb("dev-input", "local input channel stopped; override released");
	}
	state = State{};
}

inline void Initialize(bool route_passthrough)
{
	Shutdown();
	if (!route_passthrough || !Marker_Enabled()) return;
	SceRtcTick tick = {};
	if (sceRtcGetCurrentTick(&tick) < 0 || tick.tick == 0U) return;
	State &state = Get_State();
	state.token = tick.tick;
	char text[128];
	snprintf(text, sizeof(text), "RVDEV1 %016llx 0 0 128 128 128 128 0\n",
		static_cast<unsigned long long>(state.token));
	if (!Write_Text(kCommand, text) || !Write_Ack("IDLE")) return;
	snprintf(text, sizeof(text), "RVDEV1 %016llx\n", static_cast<unsigned long long>(state.token));
	if (!Write_Text(kSession, text)) return;
	state.enabled = true;
	Vita_Append_A22_Runtime_Breadcrumb("dev-input",
		"local channel enabled token=%016llx max_hold_ms=3000 poll_hz=20 original_controller_owner=1 benchmark_eligible=0",
		static_cast<unsigned long long>(state.token));
}

inline void Apply(SceCtrlData &controller)
{
	State &state = Get_State();
	if (!state.enabled) return; // No polling or clock calls in ordinary builds/runs.
	const uint64_t now = sceKernelGetProcessTimeWide();
	if ((controller.buttons & SCE_CTRL_START) != 0U) {
		Shutdown(); // Physical abort always wins; original runtime still sees START.
		return;
	}
	if (now >= state.next_enable_check) {
		state.next_enable_check = now + 1000000U;
		if (!Marker_Enabled()) { Shutdown(); return; }
	}
	if (state.active && now >= state.expires) {
		state.active = false;
		Write_Ack("RELEASED");
	}
	if (now >= state.next_poll) {
		state.next_poll = now + 100000U;
		if (!Command_File_Changed(state)) return;
		char text[192];
		const int length = Read_Text(kCommand, text, sizeof(text));
		unsigned long long token = 0;
		unsigned sequence = 0, buttons = 0, lx = 0, ly = 0, rx = 0, ry = 0, hold = 0;
		int consumed = 0;
		if (length > 0 && sscanf(text, "RVDEV1 %llx %u %u %u %u %u %u %u %n",
			&token, &sequence, &buttons, &lx, &ly, &rx, &ry, &hold, &consumed) == 8) {
			bool tail_valid = true;
			for (int index = consumed; index < length; ++index) {
				const char c = text[index];
				if (c != ' ' && c != '\t' && c != '\r' && c != '\n') tail_valid = false;
			}
			if (tail_valid && token == state.token && sequence > state.sequence &&
				(buttons & ~kButtonMask) == 0U && lx <= 255U && ly <= 255U &&
				rx <= 255U && ry <= 255U && hold <= 3000U) {
				state.sequence = sequence;
				state.buttons = buttons;
				state.lx = static_cast<uint8_t>(lx); state.ly = static_cast<uint8_t>(ly);
				state.rx = static_cast<uint8_t>(rx); state.ry = static_cast<uint8_t>(ry);
				state.expires = now + static_cast<uint64_t>(hold) * 1000U;
				state.active = hold != 0U;
				if (!Write_Ack(state.active ? "ACTIVE" : "RELEASED")) state.active = false;
				Vita_Append_A22_Runtime_Breadcrumb("dev-input",
					"accepted sequence=%u buttons=%08X axes=%u/%u/%u/%u hold_ms=%u active=%d gameplay_effect_unassessed=1",
					sequence, buttons, lx, ly, rx, ry, hold, state.active ? 1 : 0);
			}
		}
	}
	if (!state.active) return;
	controller.buttons |= state.buttons;
	if (state.lx != 128U) controller.lx = state.lx;
	if (state.ly != 128U) controller.ly = state.ly;
	if (state.rx != 128U) controller.rx = state.rx;
	if (state.ry != 128U) controller.ry = state.ry;
}

} // namespace RenegadeVitaDevInput
