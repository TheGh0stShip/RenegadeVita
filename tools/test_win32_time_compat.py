#!/usr/bin/env python3
import subprocess
import tempfile
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    source = r'''
#include "port/compatibility/include/win32_compat.h"
#include <stdio.h>

static FILETIME make_filetime(unsigned long long value)
{
	FILETIME result = {};
	result.dwLowDateTime = (DWORD)(value & 0xffffffffULL);
	result.dwHighDateTime = (DWORD)(value >> 32U);
	return result;
}

static int expect_time(unsigned long long value, int year, int month, int day,
	int day_of_week, int hour, int minute, int second, int millisecond)
{
	FILETIME file_time = make_filetime(value);
	FILETIME local_time = {};
	SYSTEMTIME system_time = {};
	if (!FileTimeToLocalFileTime(&file_time, &local_time)) return 10;
	if (Renegade_FileTime_Value(&local_time) != value) return 11;
	if (!FileTimeToSystemTime(&local_time, &system_time)) return 12;
	if (system_time.wYear != year || system_time.wMonth != month ||
		system_time.wDay != day || system_time.wDayOfWeek != day_of_week ||
		system_time.wHour != hour || system_time.wMinute != minute ||
		system_time.wSecond != second ||
		system_time.wMilliseconds != millisecond) {
		printf("%u-%u-%u dow=%u %u:%u:%u.%u\n",
			system_time.wYear, system_time.wMonth, system_time.wDay,
			system_time.wDayOfWeek, system_time.wHour, system_time.wMinute,
			system_time.wSecond, system_time.wMilliseconds);
		return 13;
	}
	return 0;
}

int main()
{
	SYSTEMTIME invalid = {};
	if (FileTimeToSystemTime(NULL, &invalid) != 0) return 1;
	FILETIME too_old = make_filetime(1ULL);
	if (FileTimeToSystemTime(&too_old, &invalid) != 0) return 2;
	if (invalid.wMonth != 0 || invalid.wDay != 0) return 3;

	int rc = expect_time(116444736000000000ULL, 1970, 1, 1, 4, 0, 0, 0, 0);
	if (rc != 0) return rc;
	rc = expect_time(133802084967890000ULL, 2025, 1, 1, 3, 12, 34, 56, 789);
	if (rc != 0) return rc;
	return expect_time(134021952000000000ULL, 2025, 9, 13, 6, 0, 0, 0, 0);
}
'''
    with tempfile.TemporaryDirectory(prefix="rv-time-compat-") as tmp:
        src = Path(tmp) / "time_compat.cpp"
        exe = Path(tmp) / "time_compat"
        src.write_text(source)
        compile_cmd = [
            "g++",
            "-std=c++17",
            "-DRENEGADE_HOST_ABI_TEST",
            "-I",
            str(root),
            str(src),
            "-o",
            str(exe),
        ]
        subprocess.run(compile_cmd, check=True)
        subprocess.run([str(exe)], check=True)

    header = (root / "port/compatibility/include/win32_compat.h").read_text()
    body = header[header.index("static inline BOOL FileTimeToLocalFileTime") :
                  header.index("static inline LONG CompareFileTime")]
    assert "sceRtcSetWin32FileTime" not in body
    assert "sceRtcGetDayOfWeek" not in body
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
