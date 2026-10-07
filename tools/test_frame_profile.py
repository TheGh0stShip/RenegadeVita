"""Host checks for the Vita game-thread frame profiler.

Compiles port/platform/vita/renegade_vita_frame_profile.cpp against a fake
psp2 clock/thread API (ASan/UBSan) and checks: disabled scopes never read the
clock, once-per-frame scopes stay exact, hot scopes read the clock for a
bounded share of entries while their reported time stays an unbiased
estimate, other threads are ignored, and the report line keeps its fields.
"""
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PROFILE_CPP = ROOT / "port/platform/vita/renegade_vita_frame_profile.cpp"
PROFILE_INCLUDE = ROOT / "port/compatibility/include"

PROCESSMGR_H = r'''
#pragma once
#include <stdint.h>
typedef uint64_t SceUInt64;
typedef uint32_t SceUInt32;
SceUInt64 sceKernelGetProcessTimeWide(void);
SceUInt32 sceKernelGetProcessTimeLow(void);
'''

THREADMGR_H = r'''
#pragma once
#include <stddef.h>
#include <stdint.h>
typedef int SceUID;
typedef int SceInt32;
typedef int64_t SceInt64;
typedef struct SceKernelThreadInfo {
    size_t size;
    void *stack;
    SceInt32 stackSize;
} SceKernelThreadInfo;
SceUID sceKernelGetThreadId(void);
int sceKernelGetThreadInfo(SceUID thid, SceKernelThreadInfo *info);
SceInt64 sceKernelGetSystemTimeWide(void);
'''

HARNESS = r'''
#include "renegade_vita_frame_profile.h"
#include <psp2/kernel/processmgr.h>
#include <psp2/kernel/threadmgr.h>
#include <pthread.h>
#include <cassert>
#include <cmath>
#include <cstdarg>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <thread>
#include <vector>

static uint64_t g_now = 1000000000ULL;   // starts past 2^32 to cover truncation
static unsigned g_clock_reads = 0U;
static int g_thread_id = 0x40010003;
static bool g_thread_info_ok = true;
static std::vector<std::string> g_lines;

SceUInt64 sceKernelGetProcessTimeWide(void) { ++g_clock_reads; return g_now; }
SceUInt32 sceKernelGetProcessTimeLow(void) { ++g_clock_reads; return static_cast<SceUInt32>(g_now); }
SceInt64 sceKernelGetSystemTimeWide(void) { ++g_clock_reads; return static_cast<SceInt64>(g_now); }
SceUID sceKernelGetThreadId(void) { return g_thread_id; }
int sceKernelGetThreadInfo(SceUID, SceKernelThreadInfo *info)
{
    if (!g_thread_info_ok) return -1;
    pthread_attr_t attr;
    void *stack = nullptr;
    size_t size = 0U;
    pthread_getattr_np(pthread_self(), &attr);
    pthread_attr_getstack(&attr, &stack, &size);
    pthread_attr_destroy(&attr);
    info->stack = stack;
    info->stackSize = static_cast<SceInt32>(size);
    return 0;
}
int A30_Vita_Log(const char *format, ...)
{
    char buffer[4096];
    va_list arguments;
    va_start(arguments, format);
    vsnprintf(buffer, sizeof(buffer), format, arguments);
    va_end(arguments);
    g_lines.push_back(buffer);
    return 0;
}

static const char kFrameName[] = "Once Per Frame";
static const char kHotName[] = "Hot Per Object";
static const char kChildName[] = "Hot Child";

static void Work(uint64_t us) { g_now += us; }

static std::string Last_Line(const char *prefix)
{
    for (auto it = g_lines.rbegin(); it != g_lines.rend(); ++it) {
        if (it->compare(0, strlen(prefix), prefix) == 0) return *it;
    }
    return std::string();
}

static unsigned long long Field(const std::string &line, const char *key)
{
    const std::string needle = std::string(" ") + key + "=";
    const size_t at = line.find(needle);
    assert(at != std::string::npos);
    return strtoull(line.c_str() + at + needle.size(), nullptr, 10);
}

static double Scope_Avg(const std::string &line, const char *mangled)
{
    const std::string needle = std::string(" ") + mangled + "=";
    const size_t at = line.find(needle);
    assert(at != std::string::npos);
    return strtod(line.c_str() + at + needle.size(), nullptr);
}

int main(int argc, char **argv)
{
    const bool use_thread_id = argc > 1 && strcmp(argv[1], "thread-id") == 0;
    g_thread_info_ok = !use_thread_id;

    // Disabled before Configure: no clock read, no state.
    {
        RENEGADE_FRAME_PROFILE(kHotName);
        Work(5);
    }
    assert(g_clock_reads == 0U);

    Renegade_Frame_Profile_Configure();
    const std::string configured = Last_Line("A3.6 frame-profile: configured");
    assert(configured.find("enabled=1") != std::string::npos);
    assert(configured.find(use_thread_id ? "thread_test=thread-id" : "thread_test=stack-range") !=
        std::string::npos);
    assert(!Last_Line("A3.6 frame-profile: clock-cost").empty());

    // Another thread never touches profiler state.
    const int main_thread_id = g_thread_id;
    std::thread other([&]() {
        if (use_thread_id) g_thread_id = main_thread_id + 1;
        RENEGADE_FRAME_PROFILE(kFrameName);
    });
    other.join();
    g_thread_id = main_thread_id;

    // One window of 120 frames: one exact scope (variable duration) plus a
    // hot scope entered 1000 times per frame with a nested child.
    srand(12345);
    uint64_t true_frame_total = 0U;
    uint64_t true_hot_total = 0U;
    uint64_t true_child_total = 0U;
    const unsigned reads_before = g_clock_reads;
    unsigned timed_entries = 0U;
    for (unsigned frame = 0U; frame < 120U; ++frame) {
        Renegade_Frame_Profile_Begin_Frame();
        const uint64_t frame_begin = g_now;
        {
            RENEGADE_FRAME_PROFILE(kFrameName);
            const uint64_t scope_begin = g_now;
            for (unsigned call = 0U; call < 1000U; ++call) {
                RENEGADE_FRAME_PROFILE(kHotName);
                const uint64_t hot_begin = g_now;
                Work(2U + static_cast<uint64_t>(rand() % 7));
                {
                    RENEGADE_FRAME_PROFILE(kChildName);
                    const uint64_t child = 1U + static_cast<uint64_t>(rand() % 3);
                    Work(child);
                    true_child_total += child;
                }
                true_hot_total += g_now - hot_begin;
            }
            Work(100U + frame);
            true_frame_total += g_now - scope_begin;
        }
        Renegade_Frame_Profile_End_Frame(static_cast<uint32_t>(g_now - frame_begin));
    }
    timed_entries = (g_clock_reads - reads_before) / 2U;

    const std::string report = Last_Line("A3.6 frame-profile: version=2");
    assert(!report.empty());
    assert(Field(report, "frames") == 120U);
    assert(Field(report, "scopes_per_frame") == 2001U);
    const unsigned long long timed = Field(report, "timed_per_frame");
    // Expected 1 + 2 * (2 + 998 / 16) = ~130 timed entries of 2001.
    assert(timed >= 100U && timed <= 170U);
    assert(timed_entries / 120U == timed);
    assert(Field(report, "exact_calls") == 2U);
    assert(Field(report, "overflow") == 0U);
    assert(report.find(" sample=1/16 ") != std::string::npos);

    // The once-per-frame scope is exact; hot scopes are unbiased estimates.
    const double frame_avg = Scope_Avg(report, "Once_Per_Frame");
    assert(static_cast<unsigned long long>(frame_avg) == true_frame_total / 120U);
    const double hot_avg = Scope_Avg(report, "Hot_Per_Object");
    const double child_avg = Scope_Avg(report, "Hot_Child");
    const double true_hot = static_cast<double>(true_hot_total) / 120.0;
    const double true_child = static_cast<double>(true_child_total) / 120.0;
    printf("frame=%.0f hot=%.0f/%.0f child=%.0f/%.0f timed=%llu\n",
        frame_avg, hot_avg, true_hot, child_avg, true_child, timed);
    assert(std::fabs(hot_avg - true_hot) / true_hot < 0.03);
    assert(std::fabs(child_avg - true_child) / true_child < 0.03);
    assert(report.find("Hot_Per_Object=") != std::string::npos);
    assert(report.find("/1000.0") != std::string::npos);
    const std::string worst = Last_Line("A3.6 frame-profile-worst:");
    assert(worst.find("Once_Per_Frame=") != std::string::npos);

    // Constant-duration hot scope: the estimate is exact.
    for (unsigned frame = 0U; frame < 120U; ++frame) {
        Renegade_Frame_Profile_Begin_Frame();
        const uint64_t frame_begin = g_now;
        for (unsigned call = 0U; call < 500U; ++call) {
            RENEGADE_FRAME_PROFILE(kHotName);
            Work(3);
        }
        Renegade_Frame_Profile_End_Frame(static_cast<uint32_t>(g_now - frame_begin));
    }
    const std::string constant = Last_Line("A3.6 frame-profile: version=2");
    assert(static_cast<unsigned>(Scope_Avg(constant, "Hot_Per_Object")) == 1500U);

    // Scopes recorded outside a frame (loading, pause) are discarded.
    {
        RENEGADE_FRAME_PROFILE(kChildName);
        Work(1000000);
    }
    for (unsigned frame = 0U; frame < 120U; ++frame) {
        Renegade_Frame_Profile_Begin_Frame();
        const uint64_t frame_begin = g_now;
        {
            RENEGADE_FRAME_PROFILE(kFrameName);
            Work(10);
        }
        Renegade_Frame_Profile_End_Frame(static_cast<uint32_t>(g_now - frame_begin));
    }
    const std::string discarded = Last_Line("A3.6 frame-profile: version=2");
    assert(discarded.find("Hot_Child=") == std::string::npos);
    assert(static_cast<unsigned>(Scope_Avg(discarded, "Once_Per_Frame")) == 10U);

    // Disabled again: no clock read per scope.
    g_renegade_frame_profile_active = false;
    const unsigned disabled_reads = g_clock_reads;
    for (unsigned call = 0U; call < 1000U; ++call) {
        RENEGADE_FRAME_PROFILE(kHotName);
    }
    assert(g_clock_reads == disabled_reads);
    puts("frame profile host checks passed");
    return 0;
}
'''


class FrameProfileHostTests(unittest.TestCase):
    def _run(self, mode):
        compiler = shutil.which("g++")
        if compiler is None:
            self.skipTest("g++ unavailable")
        with tempfile.TemporaryDirectory(prefix="frame-profile-") as folder:
            folder = Path(folder)
            kernel = folder / "psp2/kernel"
            kernel.mkdir(parents=True)
            (kernel / "processmgr.h").write_text(PROCESSMGR_H)
            (kernel / "threadmgr.h").write_text(THREADMGR_H)
            harness = folder / "harness.cpp"
            harness.write_text(HARNESS)
            binary = folder / "frame_profile"
            subprocess.run([
                compiler, "-std=c++17", "-O1", "-g", "-Wall", "-Wextra", "-Werror",
                "-fsanitize=address,undefined", "-fno-sanitize-recover=all",
                "-DRENEGADE_VITA_FRAME_PROFILE=1",
                "-DRENEGADE_VITA_FRAME_PROFILE_DEFAULT=1",
                "-I", str(folder), "-I", str(PROFILE_INCLUDE),
                str(PROFILE_CPP), str(harness), "-o", str(binary), "-pthread",
            ], check=True)
            result = subprocess.run([str(binary), mode], check=True,
                capture_output=True, text=True)
            self.assertIn("frame profile host checks passed", result.stdout)
            return result.stdout

    def test_stack_range_thread_test(self):
        self._run("stack-range")

    def test_thread_id_fallback(self):
        self._run("thread-id")

    def test_vita_performance_counter_matches_newlib_monotonic(self):
        # VitaSDK newlib clock_gettime(CLOCK_MONOTONIC): t = process time us,
        # tv_sec = t / 10^6 (32-bit time_t), tv_nsec = (t % 10^6) * 1000. The
        # former QueryPerformanceCounter combined them; the Vita path is t*1000.
        import random
        generator = random.Random(7)
        samples = [0, 1, 999999, 1000000, 2**32 - 1, 2**32, 2**40 + 12345]
        samples += [generator.randrange(0, 2**45) for _ in range(10000)]
        for t in samples:
            tv_sec = (t // 1000000) & 0xFFFFFFFF
            tv_nsec = (t % 1000000) * 1000
            self.assertEqual(tv_sec * 1000000000 + tv_nsec, t * 1000)
        compat = (PROFILE_INCLUDE / "win32_compat.h").read_text()
        self.assertIn(
            "*counter = (LARGE_INTEGER)sceKernelGetProcessTimeWide() * INT64_C(1000);",
            compat)
        self.assertIn("*frequency = INT64_C(1000000000);", compat)

    def test_report_documents_estimates(self):
        source = PROFILE_CPP.read_text()
        self.assertIn("version=2", source)
        self.assertRegex(source, r"timed_per_frame=%llu")
        header = (PROFILE_INCLUDE / "renegade_vita_frame_profile.h").read_text()
        self.assertIn("probability 1/16", header)
        self.assertTrue(re.search(r"kExactCallsPerFrame = 2U", source))
        self.assertTrue(re.search(r"kSampleShift = 4U", source))


if __name__ == "__main__":
    unittest.main()
