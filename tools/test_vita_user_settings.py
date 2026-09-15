"""Production user-settings persistence with independent malformed fixtures."""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

class UserSettingsTests(unittest.TestCase):
    def test_atomic_round_trip_validation_and_failed_write(self):
        source = r'''
#include "renegade_vita_user_settings.h"
#include <assert.h>
#include <string>
using namespace RenegadeVitaUserSettings;
int main(int argc, char **argv) {
 assert(argc == 2);
 const std::string path = std::string(argv[1]) + "/options.cfg";
 assert(Configure(path.c_str()));
 assert(State().record.value[0] == 0);
 Record r;
 assert(Parse("RVOPT1 3 37 22 50 100 1 0 1 1 12345 6789 0 2\n",r));
 assert(Save(r));
 r.value[3] = 65;
 assert(Save(r)); // Existing destination must be replaced atomically.
 State().record = Record{};
 assert(Configure(path.c_str()));
 assert(State().record.value[1] == 37 && State().record.value[3] == 65);
 assert(State().record.value[9] == 12345 && State().record.value[10] == 6789);
 const char *invalid[] = {
  "RVOPT2 3 37 22 50 100 1 0 1 1 12345 6789 0 2\n",
  "RVOPT1 4 37 22 50 100 1 0 1 1 12345 6789 0 2\n",
  "RVOPT1 3 101 22 50 100 1 0 1 1 12345 6789 0 2\n",
  "RVOPT1 3 -1 22 50 100 1 0 1 1 12345 6789 0 2\n",
  "RVOPT1 3 37 22 50 100 1 2 1 1 12345 6789 0 2\n",
  "RVOPT1 3 37 22 50 100 1 0 1 1 4294967296 6789 0 2\n",
  "RVOPT1 3 37 22 50 100 1 0 1 1 12345 6789 3 2\n",
  "RVOPT1 3 37 22 50 100 1 0 1 1 12345 6789 0 3\n",
  "RVOPT1 3 37 22 50 100 1 0 1 1 12345 6789 0 2\nextra",
  "RVOPT1 3 37 22 50 100 1 0 1 1 12345 6789 0 2",
  "RVOPT1 3", "RVOPT1 ", ""
 };
 for (const char *bad : invalid) {
  Record unchanged = r;
  assert(!Parse(bad, unchanged));
  assert(memcmp(&r, &unchanged, sizeof(r)) == 0);
 }
 Record invalid_write = r; invalid_write.value[11] = 3;
 assert(!Save(invalid_write));
 assert(Configure(path.c_str()) && State().record.value[3] == 65);
 strcpy(State().path, (std::string(argv[1])+"/missing/options.cfg").c_str());
 assert(!Save(r));
 assert(Configure(path.c_str()) && State().record.value[9] == 12345);
 FILE *file = fopen(path.c_str(), "wb"); assert(file);
 assert(fwrite("RVOPT1 3\0ignored", 1, 16, file) == 16); fclose(file);
 assert(!Configure(path.c_str()) && State().record.value[0] == 0);
 puts("Vita user preferences: replacement, malformed/corrupt data, failed writes and exact budgets PASS");
}
'''
        with tempfile.TemporaryDirectory(prefix='vita-options-contract-') as folder:
            directory = Path(folder)
            (directory/'main.cpp').write_text(source)
            subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror',
                            '-fsanitize=address,undefined','-fno-omit-frame-pointer','-fno-pie','-no-pie',
                            '-I'+str(ROOT/'port/platform'),str(directory/'main.cpp'),
                            '-o',str(directory/'test')],check=True)
            subprocess.run([str(directory/'test'),str(directory)],check=True,
                           env={**os.environ,'ASAN_OPTIONS':'detect_leaks=1:halt_on_error=1',
                                'UBSAN_OPTIONS':'halt_on_error=1'})

if __name__ == '__main__': unittest.main()
