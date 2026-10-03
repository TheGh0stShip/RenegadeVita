import re
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def posix(text):
    """Select only simple platform branches present in the original thread unit."""
    stack, result, active = [], [], True
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(('#ifdef ', '#ifndef ')):
            directive, symbol = stripped.split(maxsplit=1)
            value = symbol == '_UNIX'
            if directive == '#ifndef':
                value = not value
            stack.append((active, value))
            active = active and value
        elif stripped.startswith('#if '):
            # Include guards in the original header are enabled in a fresh TU.
            stack.append((active, True))
        elif stripped.startswith('#else'):
            parent, value = stack[-1]
            active = parent and not value
        elif stripped.startswith('#endif'):
            parent, _ = stack.pop()
            active = parent
        elif active:
            result.append(line)
    return '\n'.join(result)


def staged_fixture():
    temp = tempfile.TemporaryDirectory()
    directory = Path(temp.name)
    for module, names, patch_name in (
            ('wwlib', ('thread.cpp', 'thread.h'), 'wwlib-a35-thread-completion-acquire.patch'),
            ('ww3d2', ('textureloader.cpp',), 'ww3d-a35-texture-worker-cancellation.patch')):
        target = directory / module
        target.mkdir()
        texts = []
        for name in names:
            text = (ROOT / 'staging' / module / name).read_text()
            (target / name).write_text(text)
            texts.append(text)
        patch = (ROOT / 'port/patches' / patch_name).read_bytes()
        already = '__atomic_load_n(&handle, __ATOMIC_ACQUIRE) != 0UL' in texts[0] if module == 'wwlib' else (
            'while (Should_Run())' in texts[0])
        if already:
            reverse = subprocess.run(['patch', '--batch', '--reverse', '--fuzz=0',
                                      '--no-backup-if-mismatch', '-d', str(target), '-p1'],
                                     input=patch, capture_output=True)
            if reverse.returncode:
                raise AssertionError(reverse.stdout + reverse.stderr)
        result = subprocess.run(['patch', '--batch', '--forward', '--fuzz=0',
                                 '--no-backup-if-mismatch', '-d', str(target), '-p1'],
                                input=patch, capture_output=True)
        if result.returncode:
            raise AssertionError(result.stdout + result.stderr)
    return temp, directory


class ThreadPublicationContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not (ROOT / 'staging/wwlib/thread.cpp').exists():
            raise unittest.SkipTest('existing staged source unavailable; no stage/build run')
        cls.temp, cls.fixture = staged_fixture()
        cls.cpp = posix((cls.fixture / 'wwlib/thread.cpp').read_text())
        cls.header = (cls.fixture / 'wwlib/thread.h').read_text()

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_completion_release_is_last_object_access(self):
        internal = self.cpp.split('void __cdecl ThreadClass::Internal_Thread_Function', 1)[1].split(
            'void ThreadClass::Execute()', 1)[0]
        terminal = internal.index('__atomic_store_n(&tc->handle, 0UL, __ATOMIC_RELEASE)')
        self.assertNotIn('tc->', internal[terminal:].split(';', 1)[1])
        self.assertLess(internal.index('tc->ThreadID = 0'), terminal)
        self.assertLess(internal.index('__atomic_store_n(&tc->running, false'), terminal)

    def test_poll_and_stop_acquire_completion(self):
        poll = self.cpp.split('bool ThreadClass::Is_Running()', 1)[1]
        self.assertIn('__atomic_load_n(&handle, __ATOMIC_ACQUIRE)', poll)
        self.assertNotIn('!!handle', poll)
        stop = self.cpp.split('void ThreadClass::Stop(', 1)[1].split('void ThreadClass::Sleep_Ms', 1)[0]
        self.assertIn('__atomic_load_n(&handle, __ATOMIC_ACQUIRE)', stop)

    def test_parent_initializes_run_flag_and_worker_cannot_override_stop(self):
        execute = self.cpp.split('void ThreadClass::Execute()', 1)[1].split('void ThreadClass::Set_Priority', 1)[0]
        self.assertLess(execute.index('__atomic_store_n(&handle, 1UL'), execute.index('pthread_create('))
        self.assertLess(execute.index('__atomic_store_n(&running, true'), execute.index('pthread_create('))
        internal = self.cpp.split('void __cdecl ThreadClass::Internal_Thread_Function', 1)[1].split(
            'void ThreadClass::Execute()', 1)[0]
        self.assertNotIn('running=true', internal)
        failure = execute.split('} else {', 1)[1]
        self.assertLess(failure.index('running, false'), failure.index('handle, 0UL'))

    def test_cancellation_uses_atomic_selected_texture_loop(self):
        header = posix(self.header)
        self.assertIn('__atomic_load_n(&running, __ATOMIC_ACQUIRE)', header)
        texture = (self.fixture / 'ww3d2/textureloader.cpp').read_text()
        self.assertIn('while (Should_Run())', texture)
        self.assertNotIn('while (running)', texture)
        # Other selected original worker bodies do not poll the base flag.
        for source in ('Combat/combat.cpp', 'Commando/init.cpp', 'Commando/shutdown.cpp',
                       'Commando/bandwidthcheck.cpp', 'Commando/bandwidthcheck.h'):
            text = (ROOT / 'upstream/CnC_Renegade/Code' / source).read_text(encoding='latin1')
            self.assertIsNone(re.search(r'\b(?:while|if)\s*\(\s*running\s*\)', text), source)

    def test_runtime_fields_and_windows_fallback_preserved(self):
        for field in ('volatile bool running;', 'unsigned ThreadID;', 'volatile unsigned long handle;'):
            self.assertIn(field, self.header)
        self.assertIn('#else\n\t\treturn running;', self.header)
        self.assertIn('#else\n\treturn !!handle;', (self.fixture / 'wwlib/thread.cpp').read_text())
        self.assertNotIn('pthread_t handle', self.header)
        self.assertIn('ThreadID(0)', self.cpp)

    def test_patch_registry_and_prepared_original_owner_probe(self):
        from tools.renegade_patch_inventory import load_inventory
        inventory = str(load_inventory(ROOT))
        for patch in ('wwlib-a35-thread-completion-acquire.patch', 'ww3d-a35-texture-worker-cancellation.patch'):
            self.assertIn(patch, inventory)
        cmake = (ROOT / 'tools/host_a30_definitions/CMakeLists.txt').read_text()
        probe = cmake.split('add_executable(a35_thread_publication_selftest', 1)[1].split(
            'add_executable(a35_wwmath_validity_selftest', 1)[0]
        self.assertIn('${RV_STAGE}/wwlib/thread.cpp', probe)
        self.assertIn('--wrap=pthread_create', probe)
        source = (ROOT / 'tools/host_a35_thread_publication_test.cpp').read_text()
        for marker in ('public ThreadClass', 'probe.work == 0U', 'fail_create.store(true)',
                       'probe.payload == UINT32_C', 'Completed_ID() == 0U'):
            self.assertIn(marker, source)

    def test_source_replay_leaves_no_patch_debris(self):
        self.assertFalse(list(self.fixture.rglob('*.orig')))
        self.assertFalse(list(self.fixture.rglob('*.rej')))


if __name__ == '__main__':
    unittest.main()
