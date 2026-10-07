"""Static contract for Vita SoC clocks, resume re-application and RVCK1.

Pure Python: reads sources only, runs no compiler. It checks:
- the unconditional boot request stays at the documented application maxima
  (444/222/222/166 MHz cpu/bus/gpu/xbar);
- the gameplay resume path re-applies those clocks;
- the RVCK1 clock watchdog runs after every power-thread wake, counts every
  resume-type callback, and re-requests the same maxima;
- with no clocks-v1.flag every RVCK1 path keeps the previous behaviour
  (thread affinity 0, 4 KiB callback stack, no ticks, no extra requests);
- no port code requests a clock above the documented maxima.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / 'port/platform/vita/a30_main.cpp'
RUNTIME = ROOT / 'port/platform/vita/a31_vita_runtime.cpp'
CLOCKS = ROOT / 'port/platform/vita/renegade_vita_clocks.h'
BINK = ROOT / 'port/platform/a4_binkmovie_boundary.cpp'

MAXIMA = {'Arm': 444, 'Bus': 222, 'Gpu': 222, 'GpuXbar': 166}


def body(source, signature):
    """Return the brace-balanced body that follows signature."""
    start = source.index(signature)
    open_brace = source.index('{', start)
    depth = 0
    for index in range(open_brace, len(source)):
        if source[index] == '{':
            depth += 1
        elif source[index] == '}':
            depth -= 1
            if depth == 0:
                return source[open_brace + 1:index]
    raise AssertionError('unbalanced body for ' + signature)


def strip_comments(source):
    source = re.sub(r'/\*.*?\*/', '', source, flags=re.S)
    return re.sub(r'//[^\n]*', '', source)


class VitaClockContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.main = MAIN.read_text()
        cls.runtime = RUNTIME.read_text()
        cls.clocks = CLOCKS.read_text()
        cls.bink = BINK.read_text()

    def assert_requests_maxima(self, text, literal=True):
        for name, mhz in MAXIMA.items():
            value = str(mhz) if literal else None
            pattern = r'scePowerSet%sClockFrequency\(\s*%s\s*\)' % (
                name, value if literal else r'k\w+Mhz')
            self.assertRegex(text, pattern, name)

    def test_boot_request_is_unconditional_and_at_maxima(self):
        main = strip_comments(self.main)
        entry = main[main.index('Write_Boot_Trace("main-entry"'):
                     main.index('sceKernelChangeThreadCpuAffinityMask(')]
        self.assert_requests_maxima(entry)
        # The boot request is never behind the RVCK1 flag.
        self.assertNotIn('RenegadeVitaClocks', entry)
        self.assertNotIn('clocks-v1.flag', main)

    def test_gameplay_resume_reapplies_clocks(self):
        runtime = strip_comments(self.runtime)
        reassert = body(runtime, 'void Reassert_Performance_Clocks(uint32_t frame)')
        self.assertIn('arm >= 444 && bus >= 222 && gpu >= 222 && xbar >= 166',
                      reassert)
        self.assert_requests_maxima(reassert)
        resume = body(runtime, 'bool Consume_Power_Resume(uint32_t frame)')
        self.assertIn('g_power_resume_events.load(std::memory_order_acquire)', resume)
        self.assertIn('Reassert_Performance_Clocks(frame);', resume)
        self.assertLess(resume.index('if (now == seen) return false;'),
                        resume.index('Reassert_Performance_Clocks(frame);'))
        loop = runtime[runtime.index('A31VitaInteractiveResult A31_Vita_Run_Interactive_Runtime('):]
        self.assertIn('if (Consume_Power_Resume(result.frames))', loop)
        self.assertIn('Reassert_Performance_Clocks(result.frames);', loop)

    def test_power_callback_counts_every_resume_type(self):
        runtime = strip_comments(self.runtime)
        callback = body(runtime, 'int Power_Event_Callback(int, int, int power_info, void *)')
        self.assertIn('(power_info & SCE_POWER_CB_SYSTEM_RESUME) != 0', callback)
        self.assertIn('(power_info & RenegadeVitaClocks::kResumeEventMask) != 0', callback)
        self.assertIn('g_power_clock_events.fetch_add(1U', callback)
        # Callback context: counters only, never a log line or a clock call.
        self.assertNotIn('A30_Vita_Log', callback)
        self.assertNotIn('scePowerSet', callback)
        mask = self.clocks[self.clocks.index('const int kResumeEventMask'):]
        mask = mask[:mask.index(';')]
        for bit in ('SCE_POWER_CB_SYSTEM_RESUME', 'SCE_POWER_CB_AFTER_SYSTEM_RESUME',
                    'SCE_POWER_CB_APP_RESUME'):
            self.assertIn(bit, mask)

    def test_power_thread_runs_watchdog_after_every_wake(self):
        runtime = strip_comments(self.runtime)
        thread = body(runtime, 'int Power_Callback_Thread(SceSize, void *)')
        self.assertLess(thread.index('scePowerRegisterCallback(callback)'),
                        thread.index('RenegadeVitaClocks::Power_Thread_Armed();'))
        loop = body(thread, 'for (;;)')
        self.assertLess(loop.index('sceKernelDelayThreadCB(1000000U);'),
                        loop.index('RenegadeVitaClocks::Power_Thread_Wake(clocks,'))
        self.assertIn('g_power_clock_events.load(std::memory_order_acquire)', loop)

    def test_watchdog_reapplies_documented_maxima(self):
        clocks = strip_comments(self.clocks)
        for name, value in (('kArmMhz', 444), ('kBusMhz', 222),
                            ('kGpuMhz', 222), ('kXbarMhz', 166)):
            self.assertRegex(clocks, r'\b%s = %d\b' % (name, value))
        targets = body(clocks, 'inline void Request_Targets()')
        self.assert_requests_maxima(targets, literal=False)
        below = body(clocks, 'inline bool Below_Target(int arm, int bus, int gpu, int xbar)')
        self.assertEqual(
            ' '.join(below.split()),
            'return arm < kArmMhz || bus < kBusMhz || gpu < kGpuMhz || xbar < kXbarMhz;')
        wake = body(clocks, 'inline void Power_Thread_Wake(WatchdogState &state, uint32_t resume_events)')
        order = ['Enabled(MODE_CLOCK_WATCHDOG)', 'Watchdog_Should_Check(state, resume_events)',
                 'Read_Clocks()', 'Below_Target(before.arm, before.bus, before.gpu, before.xbar)',
                 'Request_Targets();', 'const Readback after = Read_Clocks();']
        positions = [wake.index(token) for token in order]
        self.assertEqual(positions, sorted(positions))
        window = body(clocks, 'inline bool Watchdog_Should_Check(WatchdogState &state, uint32_t resume_events)')
        self.assertIn('if (resume_events != state.seen_events)', window)
        self.assertIn('state.settle_wakes = kResumeSettleWakes;', window)

    def test_flag_is_strict_and_default_off(self):
        clocks = strip_comments(self.clocks)
        self.assertIn('"ux0:data/renegade/user/config/clocks-v1.flag"', clocks)
        parse = body(clocks, 'inline unsigned Parse_Mode(const char *data, size_t bytes)')
        for token in ('bytes != 8U', 'memcmp(data, "RVCK1 ", 6U) != 0',
                      "data[7] != '\\n'", "data[6] < '0'", "data[6] > '7'",
                      'return MODE_DEFAULT;'):
            self.assertIn(token, parse)
        self.assertRegex(clocks, r'MODE_DEFAULT = 0U')
        read = body(clocks, 'inline unsigned Read_Mode()')
        self.assertIn('unsigned mode = MODE_DEFAULT;', read)
        affinity = body(clocks, 'inline int Helper_Thread_Affinity()')
        self.assertIn('Enabled(MODE_THREAD_PLACEMENT) ? SCE_KERNEL_CPU_MASK_USER_2 : 0', affinity)
        stack = body(clocks, 'inline SceSize Power_Thread_Stack_Size()')
        # 0x1000 is the original callback stack; any RVCK1 bit enables logging.
        self.assertIn('Mode() != MODE_DEFAULT ? 0x4000U : 0x1000U', stack)
        armed = body(clocks, 'inline void Power_Thread_Armed()')
        self.assertLess(armed.index('if (mode == MODE_DEFAULT) return;'),
                        armed.index('A30_Vita_Log('))

    def test_helper_threads_use_rvck1_placement(self):
        runtime = strip_comments(self.runtime)
        for name in ('"RenegadePowerCbThread"', '"RenegadeStartupStatus"'):
            call = runtime[runtime.index('sceKernelCreateThread(' + name):]
            call = call[:call.index(';')]
            self.assertIn('RenegadeVitaClocks::Helper_Thread_Affinity()', call, name)
        power = runtime[runtime.index('sceKernelCreateThread("RenegadePowerCbThread"'):]
        self.assertIn('RenegadeVitaClocks::Power_Thread_Stack_Size()',
                      power[:power.index(';')])
        audio = body(strip_comments(self.bink), 'void *Audio_Output_Thread(void *)')
        self.assertTrue(audio.lstrip().startswith(
            'RenegadeVitaClocks::Place_Audio_Worker_Thread();'))

    def test_keep_awake_only_during_original_presentation(self):
        runtime = strip_comments(self.runtime)
        tick = body(runtime, 'void Tick_Presentation_Keep_Awake(uint32_t frame)')
        self.assertIn('RenegadeVitaClocks::Enabled(RenegadeVitaClocks::MODE_KEEP_AWAKE)', tick)
        self.assertIn('RenegadeVitaClocks::Keep_Awake_Due(frame, last_frame)', tick)
        self.assertIn('COMBAT_CAMERA->Is_In_Cinematic()', tick)
        self.assertIn('ConversationMgrClass::Get_Active_Conversation_Count()', tick)
        self.assertLess(tick.index('if (!cinematic && conversations <= 0) return;'),
                        tick.index('sceKernelPowerTick('))
        self.assertIn('SCE_KERNEL_POWER_TICK_DISABLE_AUTO_SUSPEND', tick)
        self.assertIn('SCE_KERNEL_POWER_TICK_DISABLE_OLED_DIMMING', tick)
        loop = runtime[runtime.index('A31VitaInteractiveResult A31_Vita_Run_Interactive_Runtime('):]
        self.assertLess(loop.index('Tick_Presentation_Keep_Awake(result.frames);'),
                        loop.index('if (Consume_Power_Resume(result.frames))'))

    def test_no_port_clock_request_exceeds_documented_maxima(self):
        offenders = []
        for path in (ROOT / 'port').rglob('*'):
            if path.suffix not in ('.c', '.cpp', '.h', '.hpp'):
                continue
            text = strip_comments(path.read_text(errors='ignore'))
            for name, argument in re.findall(
                    r'scePowerSet(Arm|Bus|Gpu|GpuXbar)ClockFrequency\(\s*([^)]*?)\s*\)', text):
                if argument.isdigit() and int(argument) > MAXIMA[name]:
                    offenders.append('%s: %s=%s' % (path.relative_to(ROOT), name, argument))
                elif not argument.isdigit() and not re.fullmatch(r'k\w+Mhz', argument):
                    offenders.append('%s: %s=%s (unchecked)' % (
                        path.relative_to(ROOT), name, argument))
        self.assertEqual(offenders, [])


if __name__ == '__main__':
    unittest.main()
