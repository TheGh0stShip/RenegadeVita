"""Host model of the Vita suspend/resume real frame-step cap.

Compiles the staged TimeManager::Update_Frame_Time delta lines (including the
port hook call) together with the real Renegade_Vita_Resume_Frame_Clock_Rebase
body from a31_vita_runtime.cpp, then drives a fake process clock through
suspend/resume orderings. Host evidence only.
"""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

HARNESS = r'''
#include <atomic>
#include <cstdarg>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

#define MIN(a, b) ((a) < (b) ? (a) : (b))
#define TICKS_PER_SECOND 1000
#define SLOWEST_FPS 5

static std::atomic<uint32_t> g_power_resume_events(0U);
static std::atomic<uint32_t> g_power_app_resume_events(0U);
static std::vector<std::string> g_log;

static void A30_Vita_Log(const char *format, ...)
{
	char buffer[512];
	va_list args;
	va_start(args, format);
	vsnprintf(buffer, sizeof(buffer), format, args);
	va_end(args);
	g_log.push_back(buffer);
}

#include "hook.inc"

static int g_now = 0;

class TimeManager {
public:
	static int FrameTicks;
	static int RealFrameTicks;
	static int LastTicks;
	static int SystemTicks() { return g_now; }
	static void Update_Frame_Time()
	{
#include "update.inc"
	}
};
int TimeManager::FrameTicks = 0;
int TimeManager::RealFrameTicks = 0;
int TimeManager::LastTicks = 0;

static int g_failures = 0;
#define CHECK(cond) do { if (!(cond)) { std::fprintf(stderr, "FAIL %s:%d %s\n", __FILE__, __LINE__, #cond); ++g_failures; } } while (0)

static void Frame(int real_ms)
{
	g_now += real_ms;
	TimeManager::Update_Frame_Time();
}

static bool Last_Log_Has(const char *text)
{
	return !g_log.empty() && std::strstr(g_log.back().c_str(), text) != nullptr;
}

int main()
{
	g_now = 1000;
	TimeManager::Update_Frame_Time();
	for (int i = 0; i < 10; ++i) Frame(33);
	CHECK(TimeManager::RealFrameTicks == 33 && TimeManager::FrameTicks == 33);
	CHECK(g_log.empty());

	// Original semantics: an ordinary long frame without a resume keeps its
	// real step; only the simulated step is capped.
	Frame(2500);
	CHECK(TimeManager::RealFrameTicks == 2500 && TimeManager::FrameTicks == 200);
	CHECK(g_log.empty());

	// Process clock advances 30 s across suspend; the notification is seen
	// before the next update: one capped real step, then normal frames.
	g_now += 30000;
	g_power_resume_events.fetch_add(1U);
	Frame(33);
	CHECK(TimeManager::RealFrameTicks == 200 && TimeManager::FrameTicks == 200);
	CHECK(Last_Log_Has("pending_real_ms=30033") && Last_Log_Has("action=capped"));
	Frame(33);
	CHECK(TimeManager::RealFrameTicks == 33 && TimeManager::FrameTicks == 33);
	CHECK(g_log.size() == 1U);

	// Process clock frozen across suspend: nothing to cap.
	g_power_app_resume_events.fetch_add(1U);
	Frame(33);
	CHECK(TimeManager::RealFrameTicks == 33);
	CHECK(Last_Log_Has("pending_real_ms=33") && Last_Log_Has("action=unchanged"));

	// System and application resume coalesced into one update: one cap.
	g_now += 5000;
	g_power_resume_events.fetch_add(1U);
	g_power_app_resume_events.fetch_add(1U);
	Frame(20);
	CHECK(TimeManager::RealFrameTicks == 200);
	Frame(20);
	CHECK(TimeManager::RealFrameTicks == 20);
	const size_t before_late = g_log.size();

	// Late notification: the gap was consumed before the event arrived. The
	// record says so through recent_max_real_ms and leaves the step alone.
	Frame(12000);
	CHECK(TimeManager::RealFrameTicks == 12000);
	g_power_resume_events.fetch_add(1U);
	Frame(33);
	CHECK(TimeManager::RealFrameTicks == 33);
	CHECK(g_log.size() == before_late + 1U);
	CHECK(Last_Log_Has("action=unchanged") && Last_Log_Has("recent_max_real_ms=12000"));

	// Bounded record: at most 32 lines, the cap keeps working past the bound.
	for (int i = 0; i < 40; ++i) {
		g_now += 1000;
		g_power_resume_events.fetch_add(1U);
		Frame(33);
		CHECK(TimeManager::RealFrameTicks == 200);
	}
	CHECK(g_log.size() == 32U);

	if (g_failures != 0) return 1;
	std::printf("suspend/resume frame clock model PASS log_lines=%zu\n", g_log.size());
	return 0;
}
'''


def extract_hook(text):
    begin = text.index('int Renegade_Vita_Resume_Frame_Clock_Rebase(int ticks, int last_ticks,')
    end = text.index('\n}\n', begin) + 3
    return text[begin:end]


def extract_update(text):
    body = text.split('void\tTimeManager::Update_Frame_Time()', 1)[1]
    begin = body.index('\tint\tticks = SystemTicks();')
    end = body.index('\tFrameTicks = MIN( FrameTicks, (TICKS_PER_SECOND / SLOWEST_FPS) );')
    return body[begin:end] + '\tFrameTicks = MIN( FrameTicks, (TICKS_PER_SECOND / SLOWEST_FPS) );\n'


class SuspendResumeFrameClock(unittest.TestCase):
    def test_staged_hook_precedes_original_deltas(self):
        update = extract_update((ROOT / 'staging/combat/timemgr.cpp').read_text())
        hook = update.index('LastTicks = Renegade_Vita_Resume_Frame_Clock_Rebase( ticks, LastTicks,')
        self.assertLess(update.index('// sync first time'), hook)
        self.assertLess(hook, update.index('FrameTicks = ticks - LastTicks;'))
        self.assertIn('RealFrameTicks, TICKS_PER_SECOND / SLOWEST_FPS );', update)

    def test_power_callback_counts_application_resume(self):
        text = (ROOT / 'port/platform/vita/a31_vita_runtime.cpp').read_text()
        callback = text.split('int Power_Event_Callback(int, int, int power_info, void *)', 1)[1]
        callback = callback.split('\n}\n', 1)[0]
        self.assertIn('SCE_POWER_CB_APP_RESUME', callback)
        self.assertIn('g_power_app_resume_events.fetch_add', callback)
        self.assertNotIn('A30_Vita_Log', callback)

    def test_cinematic_slow_record_copies_text_before_dispatch(self):
        text = (ROOT / 'staging/scripts/Test_Cinematic.cpp').read_text()
        parse = text.split('void\tParse_Command( char *command )', 1)[1].split('void\tParse_Commands(', 1)[0]
        copy = parse.index('char vita_original_command[161];')
        self.assertLess(copy, parse.index('strncpy(vita_original_command, command,'))
        self.assertLess(copy, parse.index('Title_Match( &command, "Create_Object" )'))
        self.assertNotIn('const char *vita_original_command = command;', parse)
        self.assertIn('command=%.160s', parse)

    def test_frame_clock_model(self):
        runtime = (ROOT / 'port/platform/vita/a31_vita_runtime.cpp').read_text()
        timemgr = (ROOT / 'staging/combat/timemgr.cpp').read_text()
        with tempfile.TemporaryDirectory(prefix='renegade-resume-clock-') as folder:
            path = Path(folder)
            (path / 'hook.inc').write_text(extract_hook(runtime))
            (path / 'update.inc').write_text(extract_update(timemgr))
            (path / 'harness.cpp').write_text(HARNESS)
            subprocess.run(['g++', '-std=c++17', '-O1', '-g', '-Wall', '-Wextra', '-Werror',
                            '-D__vita__=1', '-DRENEGADE_VITA_PORT=1',
                            '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
                            '-I' + folder, str(path / 'harness.cpp'), '-o', str(path / 'test')],
                           check=True)
            result = subprocess.run([str(path / 'test')], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            self.assertIn('PASS log_lines=32', result.stdout)


if __name__ == '__main__':
    unittest.main()
