"""F4: a rejected load must not leave remapped-but-unlinked post-load state.

Runs the real staged SaveLoadSystemClass/PointerRemapClass/ChunkIO and
ReferencerClass code under host ASan/UBSan with an injected rejection after the
pointer remap, and checks the discard hook overrides in the staged sources.
"""
from contextlib import nullcontext
from pathlib import Path
import os
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / 'staging'

SHIM = '''#pragma once
#include "reflist.h"
class ScriptableGameObj : public ReferenceableClass<ScriptableGameObj> {
public:
	ScriptableGameObj() : ReferenceableClass<ScriptableGameObj>(this) {}
};
'''


def body(text, signature):
    start = text.index(signature)
    open_brace = text.index('{', start)
    depth = 0
    for index in range(open_brace, len(text)):
        if text[index] == '{':
            depth += 1
        elif text[index] == '}':
            depth -= 1
            if depth == 0:
                return text[open_brace:index + 1]
    raise AssertionError(signature)


def read(relative):
    return (STAGE / relative).read_text(encoding='latin-1')


class RejectedLoadDiscardContract(unittest.TestCase):
    def test_discard_calls_hook_before_clearing_registration(self):
        discard = body(read('wwsaveload/saveload.cpp'),
                       'void SaveLoadSystemClass::Discard_Post_Load_Callbacks')
        self.assertLess(discard.index('obj->On_Post_Load_Discarded();'),
                        discard.index('obj->Set_Post_Load_Registered(false);'))
        self.assertNotIn('On_Post_Load()', discard)
        self.assertIn('virtual void						On_Post_Load_Discarded (void)				{ }',
                      read('wwsaveload/postloadable.h'))

    def test_referencer_drops_unlinked_target(self):
        hook = body(read('combat/reflist.cpp'), 'void	ReferencerClass::On_Post_Load_Discarded')
        self.assertIn('ReferenceTarget = NULL;', hook)
        self.assertIn('TargetReferencerListNext = NULL;', hook)
        self.assertNotIn('->', hook)  # must not dereference a possibly freed target

    def test_scriptable_purges_null_observers_only(self):
        text = read('combat/scriptablegameobj.cpp')
        hook = body(text, 'void ScriptableGameObj::On_Post_Load_Discarded')
        self.assertIn('BaseGameObj::On_Post_Load_Discarded();', hook)
        self.assertIn('observer_list[ index ] == NULL', hook)
        for forbidden in ('ObserverCreatedPending', 'Start_Observers', 'Attach', 'Detach'):
            self.assertNotIn(forbidden, hook)
        self.assertIn('observer->Detach( this );', body(text, 'void ScriptableGameObj::Remove_Observer'))

    def test_moveable_drops_unlinked_carrier(self):
        text = read('wwphys/movephys.cpp')
        hook = body(text, 'void MoveablePhysClass::On_Post_Load_Discarded')
        self.assertIn('DynamicPhysClass::On_Post_Load_Discarded();', hook)
        self.assertIn('Carrier = NULL;', hook)
        self.assertNotIn('Link_To_Carrier', hook)
        self.assertIn('Link_To_Carrier(NULL);', body(text, 'MoveablePhysClass::~MoveablePhysClass(void)'))

    def test_every_override_is_declared(self):
        for header, pattern in (('combat/reflist.h', r'virtual void\s+On_Post_Load_Discarded\(void\);'),
                                ('combat/scriptablegameobj.h', r'virtual\s+void\s+On_Post_Load_Discarded\( void \);'),
                                ('wwphys/movephys.h', r'virtual void\s+On_Post_Load_Discarded \(void\);')):
            self.assertRegex(read(header), pattern, header)
        overrides = set()
        for path in STAGE.rglob('*.cpp'):
            for match in re.finditer(r'(\w+)::On_Post_Load_Discarded\s*\(', path.read_text(encoding='latin-1')):
                overrides.add(match.group(1))
        self.assertTrue({'ReferencerClass', 'ScriptableGameObj', 'MoveablePhysClass'} <= overrides, overrides)


class RejectedLoadDiscardHost(unittest.TestCase):
    def test_rejected_load_unwinds_under_asan(self):
        retained = os.environ.get('RENEGADE_REJECTED_LOAD_PROBE_DIRECTORY')
        if retained:
            Path(retained).mkdir(parents=True, exist_ok=True)
        with (nullcontext(retained) if retained else tempfile.TemporaryDirectory()) as directory:
            path = Path(directory)
            (path / 'shim').mkdir(exist_ok=True)
            (path / 'shim' / 'scriptablegameobj.h').write_text(SHIM)
            command = ['c++', '-std=c++17', '-O1', '-g', '-fpermissive', '-w', '-DRENEGADE_HOST_ABI_TEST',
                       '-fsanitize=address,undefined', '-fno-sanitize-recover=all', '-pthread',
                       '-include', str(ROOT / 'port/compatibility/include/msvc_compat.h'),
                       '-I', str(path / 'shim')]
            for name in ('staging/combat', 'staging/wwsaveload', 'staging/wwlib', 'staging/wwdebug',
                         'staging/wwmath', 'port/compatibility/include', 'port/platform'):
                command += ['-I', str(ROOT / name)]
            command += [str(ROOT / 'tools/host_rejected_load_discard_test.cpp')]
            # reflist.cpp includes "scriptablegameobj.h" by quotes; compile a verbatim
            # copy beside the shim so the quote search finds the shim first.
            (path / 'shim' / 'reflist.cpp').write_bytes((STAGE / 'combat/reflist.cpp').read_bytes())
            command.append(str(path / 'shim' / 'reflist.cpp'))
            for name in ('wwsaveload/saveload.cpp', 'wwsaveload/pointerremap.cpp',
                         'wwsaveload/saveloadsubsystem.cpp',
                         'wwsaveload/persistfactory.cpp', 'wwlib/chunkio.cpp', 'wwlib/ramfile.cpp',
                         'wwlib/slnode.cpp', 'wwlib/systimer.cpp'):
                command.append(str(STAGE / name))
            command += [str(ROOT / 'tools/host_rejected_load_discard_stubs.cpp'), '-o', str(path / 'probe')]
            compiled = subprocess.run(command, capture_output=True, text=True)
            if retained:
                (path / 'compile.log').write_text(compiled.stdout + compiled.stderr)
            self.assertEqual(compiled.returncode, 0, compiled.stderr[-6000:])
            env = dict(os.environ, ASAN_OPTIONS='detect_leaks=0:handle_segv=1')
            result = subprocess.run([str(path / 'probe')], capture_output=True, text=True, env=env)
            if retained:
                (path / 'runtime.log').write_text(result.stdout + result.stderr)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr[-6000:])
            self.assertIn('negative control: unlinked referencer destruction crashed as expected', result.stdout)
            self.assertIn('PASS rejected_load_discard accepted=2 rejected=2 negative_control=crash', result.stdout)


if __name__ == '__main__':
    unittest.main()
