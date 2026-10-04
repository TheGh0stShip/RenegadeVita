"""Execute the background runtime-log ring and pin its game-thread contract."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class AsyncRuntimeLogTests(unittest.TestCase):
    def test_ring_under_sanitizers(self):
        for sanitizer in ('address,undefined', 'thread'):
            with self.subTest(sanitizer=sanitizer), \
                    tempfile.TemporaryDirectory(prefix='renegade-async-log-') as folder:
                binary = Path(folder) / 'test'
                subprocess.run(['g++', '-std=c++17', '-O1', '-g', '-fsanitize=' + sanitizer,
                                '-fno-omit-frame-pointer', '-Wall', '-Wextra', '-Werror',
                                '-pthread', '-I' + str(ROOT / 'port/platform'),
                                str(ROOT / 'tools/renegade_async_log_test.cpp'),
                                '-o', str(binary)], check=True)
                subprocess.run([str(binary)], check=True, timeout=120)

    def test_game_thread_paths_enqueue_instead_of_syncing(self):
        platform = (ROOT / 'port/platform/vita/vita_platform.cpp').read_text()
        breadcrumb = platform[platform.index('int Vita_Append_A22_Runtime_Breadcrumb('):]
        enqueue = breadcrumb.index('if (Renegade_Runtime_Log_Enqueue(queued, length)) return 0;')
        self.assertLess(enqueue, breadcrumb.index('Write_Durable_Log_Line(file, line, length)'))
        self.assertIn('SCE_KERNEL_CPU_MASK_USER_2', platform)
        runtime = (ROOT / 'port/platform/vita/a30_vita_runtime.cpp').read_text()
        write = runtime[runtime.index('int Write_Runtime_Log_Line('):
                        runtime.index('int Sync_Runtime_Log_File()')]
        self.assertLess(write.index('Renegade_Runtime_Log_Enqueue(line, length)'),
                        write.index('sceIoWrite'))
        interactive = (ROOT / 'port/platform/vita/a31_vita_runtime.cpp').read_text()
        checkpoint = interactive[interactive.index('Log_Audio_Runtime_Statistics("checkpoint"'):]
        checkpoint = checkpoint[:checkpoint.index('\n\t\t\t\t}')]
        self.assertNotIn('A30_Vita_Log_Flush();', checkpoint)
        main = (ROOT / 'port/platform/vita/a30_main.cpp').read_text()
        self.assertEqual(main.count('A30_Vita_Log_Flush();\n\tsceKernelExitProcess(exit_code);'), 1)


if __name__ == '__main__':
    unittest.main()
