"""Production rank storage: process restarts, atomic replacement and malformed input.

This suite compiles an asset-free C++ probe and is run only during authorized
host validation. The source-only audit does not execute it.
"""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PROBE = r'''
#include "renegade_mission_ranks.h"
#include <assert.h>
#include <sys/stat.h>
#include <string>
using namespace RenegadeMissionRanks;
int main(int argc, char **argv) {
    assert(argc == 3);
    const char *path = argv[2];
    const char *key = "Software\\Westwood\\Renegade\\Ranks";
    if (strcmp(argv[1], "reject") == 0) {
        assert(!Configure(path, key));
        assert(!Get_Status().ready && Get("m13", 99) == 99);
        assert(!Set("M13", 5));
        return 0;
    }
    assert(Configure(path, key));
    assert(Matches_Key("software\\westwood\\renegade\\RANKS"));
    assert(!Matches_Key("Software\\Westwood\\Renegade\\Options"));
    if (strcmp(argv[1], "seed") == 0) {
        assert(Set("M13", 3)); assert(Set("M01", 5));
        assert(Set("M02", INT32_MIN)); assert(Set("M03", INT32_MAX));
    } else if (strcmp(argv[1], "reload") == 0) {
        assert(Get("m13") == 3 && Get("m01") == 5);
        assert(Get("M02") == INT32_MIN && Get("m03") == INT32_MAX);
        assert(Set("m13", 4)); // Replace an existing destination, preserving spelling.
        char stored_name[NameBytes];
        assert(Get_Name(0, stored_name, sizeof(stored_name)) && strcmp(stored_name, "M13") == 0);
        assert(Delete("m01") && Get("M01", 77) == 77);
        assert(!Set("../outside", 5) && !Set("M13\nM01", 5));
    } else if (strcmp(argv[1], "write-failure") == 0) {
        assert(Get("M13") == 4);
        const std::string temporary = std::string(path) + ".tmp";
        assert(mkdir(temporary.c_str(), 0700) == 0); // Deterministic fopen failure.
        assert(!Set("M13", 1) && Get("M13") == 4);
        assert(!Get_Status().last_write_ok && Get_Status().error != 0);
        assert(rmdir(temporary.c_str()) == 0);
    } else if (strcmp(argv[1], "verify") == 0) {
        assert(Get("m13") == 4 && Get("m01", 99) == 99);
        assert(Clear() && Get("M13", 99) == 99);
    } else if (strcmp(argv[1], "capacity") == 0) {
        assert(Get_Status().count == 0);
        char name[96];
        for (int i = 0; i < MaxEntries; ++i) {
            snprintf(name, sizeof(name), "m%03d", i);
            assert(Set(name, i));
        }
        assert(!Set("extra", 5) && Get_Status().count == MaxEntries);
        memset(name, 'M', sizeof(name)); name[sizeof(name) - 1] = 0;
        assert(!Set(name, 1)); // Full record; must not truncate into another key.
        assert(Clear());
        assert(Set(name, 1)); // 95 characters is allowed.
        std::string too_long(96, 'M'); assert(!Set(too_long.c_str(), 1));
    } else {
        return 2;
    }
    return 0;
}
'''


class MissionRanksTests(unittest.TestCase):
    def compile_probe(self, folder):
        source, binary = folder / "probe.cpp", folder / "probe"
        source.write_text(PROBE)
        subprocess.run(["g++", "-std=c++17", "-Wall", "-Wextra", "-Werror",
                        "-fsanitize=address,undefined", "-fno-omit-frame-pointer", "-fno-pie", "-no-pie",
                        "-pthread", "-I" + str(ROOT / "port/filesystem"), str(source), "-o", str(binary)],
                       check=True, timeout=45)
        return binary

    def run_probe(self, binary, mode, path):
        subprocess.run([str(binary), mode, str(path)], check=True, timeout=30,
                       env={**os.environ, "ASAN_OPTIONS": "detect_leaks=1:halt_on_error=1",
                            "UBSAN_OPTIONS": "halt_on_error=1"})

    def test_separate_process_reload_replacement_delete_and_failed_write(self):
        with tempfile.TemporaryDirectory(prefix="vita-mission-ranks-") as temporary:
            folder = Path(temporary)
            binary = self.compile_probe(folder)
            path = folder / "ranks.cfg"
            for phase in ("seed", "reload", "write-failure", "verify", "capacity"):
                self.run_probe(binary, phase, path)
            self.assertFalse(Path(str(path) + ".tmp").exists())

    def test_corrupt_existing_file_is_rejected_without_overwrite(self):
        with tempfile.TemporaryDirectory(prefix="vita-mission-ranks-corrupt-") as temporary:
            folder = Path(temporary)
            binary = self.compile_probe(folder)
            path = folder / "ranks.cfg"
            header = b"RVRANK1\nCOUNT 1\n"
            invalid = [b"", b"RVRANK2\nCOUNT 0\nEND\n", b"RVRANK1\n",
                       b"RVRANK1\nCOUNT 0\n", header, header + b"m13 5\n",
                       header + b"m13 5", b"RVRANK1\nCOUNT 2\nm13 5\nM13 4\nEND\n",
                       header + b"m13 5\0ignored\nEND\n",
                       header + b"m13 2147483648\nEND\n", header + b"m13 -2147483649\nEND\n",
                       header + b"../outside 5\nEND\n", header + b"m13 +5\nEND\n",
                       header + b"m13  5\nEND\n", header + b"m" * 96 + b" 1\nEND\n",
                       b"RVRANK1\nCOUNT 129\n" + b"".join(f"m{i:03d} 1\n".encode() for i in range(129)) + b"END\n",
                       b"RVRANK1\nCOUNT -1\nEND\n", b"RVRANK1\nCOUNT +1\nm13 5\nEND\n",
                       b"RVRANK1\nCOUNT 99999999999999999999\nEND\n",
                       header + b"m13 5\nEND\ntrailing", b"RVRANK1\nCOUNT 0\nEND\n\0"]
            for payload in invalid:
                with self.subTest(payload=payload[:40]):
                    path.write_bytes(payload)
                    self.run_probe(binary, "reject", path)
                    self.assertEqual(path.read_bytes(), payload)
                    self.assertFalse(Path(str(path) + ".tmp").exists())


if __name__ == "__main__":
    unittest.main()
