#ifndef RENEGADE_VITA_CLOCKS_H
#define RENEGADE_VITA_CLOCKS_H

// RVCK1: SoC clock residency, helper-thread placement and keep-awake policy
// at the Vita platform boundary.
//
// The boot request (a30_main.cpp) and the gameplay-loop re-assertion
// (a31_vita_runtime.cpp: Consume_Power_Resume and the 120-frame checkpoint)
// are not gated by this flag. They cover gameplay only. A resume during the
// loading screen, the frontend or a movie leaves clocks unchecked until
// gameplay runs again.
//
// ux0:data/renegade/user/config/clocks-v1.flag holds exactly "RVCK1 <m>\n",
// where m is '0'..'7', a bit mask:
//   1  clock watchdog on the power-callback thread. After a system or
//      application resume callback, the thread re-reads the clocks on each
//      1 s wake for kResumeSettleWakes wakes. Otherwise it re-reads them
//      every kWatchdogIdleWakes wakes, in every phase. Whenever a clock reads
//      below the documented application maximum it requests 444/222/222/166
//      MHz (cpu/bus/gpu/xbar) again and logs the before/after readback.
//   2  helper-thread placement. The power-callback and startup-status threads
//      are created on user core 2, and the BINK audio worker pins itself to
//      user core 1. Without the bit they pass affinity 0
//      (SCE_KERNEL_THREAD_CPU_AFFINITY_MASK_DEFAULT). The SDK header
//      psp2common/kernel/threadmgr.h documents that as inheriting the calling
//      thread's mask, and the caller is the game thread pinned to user core 0.
//   4  keep-awake. While an original cinematic camera or conversation is
//      active, gameplay ticks the auto-suspend and OLED-dimming timers once
//      per kKeepAwakeFrameInterval frames. The BINK boundary already does
//      this for movies. The original game blocked the Windows screen saver
//      for its whole session (Commando/WINMAIN.CPP, SC_SCREENSAVE).
// No file, a malformed file or "RVCK1 0\n" leaves behaviour unchanged.

#include <stddef.h>
#include <stdint.h>
#include <string.h>

namespace RenegadeVitaClocks {

enum : unsigned {
	MODE_CLOCK_WATCHDOG = 1U,
	MODE_THREAD_PLACEMENT = 2U,
	MODE_KEEP_AWAKE = 4U,
	MODE_DEFAULT = 0U
};

// Documented maxima for a normal application (MHz).
enum : int {
	kArmMhz = 444,
	kBusMhz = 222,
	kGpuMhz = 222,
	kXbarMhz = 166
};

enum : unsigned {
	kResumeSettleWakes = 8U,
	kWatchdogIdleWakes = 10U,
	kKeepAwakeFrameInterval = 30U
};

// Strict: exactly "RVCK1 <0-7>\n". Anything else selects MODE_DEFAULT.
inline unsigned Parse_Mode(const char *data, size_t bytes)
{
	if (data == NULL || bytes != 8U || memcmp(data, "RVCK1 ", 6U) != 0 ||
		data[7] != '\n' || data[6] < '0' || data[6] > '7') return MODE_DEFAULT;
	return static_cast<unsigned>(data[6] - '0');
}

inline bool Below_Target(int arm, int bus, int gpu, int xbar)
{
	return arm < kArmMhz || bus < kBusMhz || gpu < kGpuMhz || xbar < kXbarMhz;
}

struct WatchdogState {
	uint32_t seen_events;
	unsigned settle_wakes;
	unsigned idle_wakes;
	unsigned reapplies;
};

// A device that never reaches the target would otherwise log every check.
enum : unsigned { kMaxLoggedReapplies = 32U };

// One decision per power-thread wake: true when the clocks should be read.
// A new resume event opens (or restarts) the settle window.
inline bool Watchdog_Should_Check(WatchdogState &state, uint32_t resume_events)
{
	if (resume_events != state.seen_events) {
		state.seen_events = resume_events;
		state.settle_wakes = kResumeSettleWakes;
		state.idle_wakes = 0U;
	}
	if (state.settle_wakes != 0U) {
		--state.settle_wakes;
		return true;
	}
	if (++state.idle_wakes >= kWatchdogIdleWakes) {
		state.idle_wakes = 0U;
		return true;
	}
	return false;
}

// True on every kKeepAwakeFrameInterval-th frame, once per frame value:
// loop iterations that do not advance the frame counter never tick again.
inline bool Keep_Awake_Due(uint32_t frame, uint32_t &last_frame)
{
	if ((frame % kKeepAwakeFrameInterval) != 0U || frame == last_frame) return false;
	last_frame = frame;
	return true;
}

} // namespace RenegadeVitaClocks

#if defined(__vita__)

#include <stdio.h>
#include <psp2/kernel/processmgr.h>
#include <psp2/kernel/threadmgr.h>
#include <psp2/power.h>

#include "a30_vita_runtime.h"

namespace RenegadeVitaClocks {

// Callback bits that precede a possible clock reset. Only these resume bits
// fall inside SCE_POWER_CB_VALID_MASK_NON_SYSTEM; the suspend bits do not.
const int kResumeEventMask = SCE_POWER_CB_AFTER_SYSTEM_RESUME |
	SCE_POWER_CB_SYSTEM_RESUME | SCE_POWER_CB_APP_RESUME;

inline unsigned Read_Mode()
{
	unsigned mode = MODE_DEFAULT;
	FILE *file = fopen("ux0:data/renegade/user/config/clocks-v1.flag", "rb");
	if (file != NULL) {
		char value[9] = {};
		const size_t size = fread(value, 1U, sizeof(value), file);
		const bool read_ok = !ferror(file);
		fclose(file);
		if (read_ok) mode = Parse_Mode(value, size);
	}
	return mode;
}

// Read once, on first use. The first use is Ensure_Power_Callback_Registered
// on the game thread, before any helper thread exists.
inline unsigned Mode()
{
	static const unsigned mode = Read_Mode();
	return mode;
}

inline bool Enabled(unsigned bit)
{
	return (Mode() & bit) != 0U;
}

// 0 is SCE_KERNEL_THREAD_CPU_AFFINITY_MASK_DEFAULT, the unchanged behaviour.
inline int Helper_Thread_Affinity()
{
	return Enabled(MODE_THREAD_PLACEMENT) ? SCE_KERNEL_CPU_MASK_USER_2 : 0;
}

// With any RVCK1 bit set the callback thread logs through A30_Vita_Log
// (2 KiB line buffer plus vsnprintf), which does not fit the original 4 KiB
// stack. 16 KiB matches the startup-status thread, which also logs.
inline SceSize Power_Thread_Stack_Size()
{
	return Mode() != MODE_DEFAULT ? 0x4000U : 0x1000U;
}

inline void Place_Audio_Worker_Thread()
{
	if (Enabled(MODE_THREAD_PLACEMENT)) {
		(void)sceKernelChangeThreadCpuAffinityMask(SCE_KERNEL_THREAD_ID_SELF,
			SCE_KERNEL_CPU_MASK_USER_1);
	}
}

struct Readback {
	int arm;
	int bus;
	int gpu;
	int xbar;
};

inline Readback Read_Clocks()
{
	Readback clocks;
	clocks.arm = scePowerGetArmClockFrequency();
	clocks.bus = scePowerGetBusClockFrequency();
	clocks.gpu = scePowerGetGpuClockFrequency();
	clocks.xbar = scePowerGetGpuXbarClockFrequency();
	return clocks;
}

// Same request order and values as the boot request in a30_main.cpp.
inline void Request_Targets()
{
	scePowerSetArmClockFrequency(kArmMhz);
	scePowerSetBusClockFrequency(kBusMhz);
	scePowerSetGpuClockFrequency(kGpuMhz);
	scePowerSetGpuXbarClockFrequency(kXbarMhz);
}

// Power-callback thread, once at start: one readback line.
inline void Power_Thread_Armed()
{
	const unsigned mode = Mode();
	if (mode == MODE_DEFAULT) return;
	const Readback clocks = Read_Clocks();
	A30_Vita_Log("RVCK1 clocks: armed mode=%u readback arm/bus/gpu/xbar=%d/%d/%d/%d target=%d/%d/%d/%d affinity=%08X\n",
		mode, clocks.arm, clocks.bus, clocks.gpu, clocks.xbar,
		static_cast<int>(kArmMhz), static_cast<int>(kBusMhz),
		static_cast<int>(kGpuMhz), static_cast<int>(kXbarMhz),
		static_cast<unsigned>(sceKernelGetThreadCpuAffinityMask(sceKernelGetThreadId())));
}

// Power-callback thread, after every sceKernelDelayThreadCB wake.
inline void Power_Thread_Wake(WatchdogState &state, uint32_t resume_events)
{
	if (!Enabled(MODE_CLOCK_WATCHDOG)) return;
	const bool settling = resume_events != state.seen_events ||
		state.settle_wakes != 0U;
	if (!Watchdog_Should_Check(state, resume_events)) return;
	const Readback before = Read_Clocks();
	if (!Below_Target(before.arm, before.bus, before.gpu, before.xbar)) return;
	Request_Targets();
	const Readback after = Read_Clocks();
	if (++state.reapplies > kMaxLoggedReapplies) return;
	A30_Vita_Log("RVCK1 clocks: reapplied trigger=%s resume_events=%u count=%u before arm/bus/gpu/xbar=%d/%d/%d/%d after=%d/%d/%d/%d%s\n",
		settling ? "resume" : "watchdog", static_cast<unsigned>(resume_events),
		state.reapplies, before.arm, before.bus, before.gpu, before.xbar,
		after.arm, after.bus, after.gpu, after.xbar,
		state.reapplies == kMaxLoggedReapplies ? " (further lines suppressed)" : "");
}

} // namespace RenegadeVitaClocks

#endif // __vita__

#endif // RENEGADE_VITA_CLOCKS_H
