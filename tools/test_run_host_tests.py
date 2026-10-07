"""Unit tests for tools/run_host_tests.py on throwaway fixture repositories.

Fixture sources are multi-line strings; nothing here compiles. The end-to-end
cases only start Python unittest children inside the temporary fixture tree.
"""
import argparse
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import textwrap
import unittest

from tools import run_host_tests as runner

PURE = '''
    import unittest
    from pathlib import Path
    ROOT = Path(__file__).resolve().parents[1]

    class T(unittest.TestCase):
        def test_text(self):
            text = (ROOT / 'port/renderer/r.cpp').read_text()
            self.assertIn("g++", text + "g++")
'''
COMPILES = '''
    import subprocess, unittest
    from pathlib import Path
    ROOT = Path(__file__).resolve().parents[1]

    class T(unittest.TestCase):
        def test_build(self):
            command = ["g++", "-O2", str(ROOT / "tools/h_test.cpp"), "-o", "x"]
            subprocess.run(command, check=True)
'''
SANITIZER = '''
    import subprocess, unittest

    def build(extra):
        subprocess.run(["c++", "-fsanitize=address,undefined", *extra], check=True)

    class T(unittest.TestCase):
        def test_build(self):
            build([])
'''
SANITIZER_OPTIONAL = '''
    import os, subprocess, unittest

    def build(sanitize):
        command = ["g++", "x.cpp"]
        if sanitize:
            command += ["-fsanitize=thread"]
        subprocess.run(command, check=True)

    class T(unittest.TestCase):
        def test_build(self):
            build(os.environ.get("SANITIZE") == "1")
'''
HELPER = '''
    import subprocess

    def parse(text):
        return text.split()

    def main():
        return subprocess.check_output(["ninja", "-C", "build/x", "-t", "compdb"])

    if __name__ == "__main__":
        main()
'''
USES_HELPER_PARSE = '''
    import unittest
    from tools.helper import parse

    class T(unittest.TestCase):
        def test_parse(self):
            self.assertEqual(parse("a b"), ["a", "b"])
'''
USES_HELPER_MAIN = '''
    import unittest
    from tools.helper import main

    class T(unittest.TestCase):
        def test_main(self):
            main()
'''
BUILD_SCRIPT = '''
    import subprocess
    subprocess.run(["gcc", "probe.c"], check=True)
'''
RUNS_SCRIPT = '''
    import subprocess, sys, unittest
    from pathlib import Path
    TOOL = Path(__file__).resolve().parents[1] / "tools" / "build_thing.py"

    class T(unittest.TestCase):
        def test_run(self):
            subprocess.run([sys.executable, str(TOOL)], check=True)
'''
READS_SCRIPT = '''
    import subprocess, unittest
    from pathlib import Path
    TOOL = Path(__file__).resolve().parents[1] / "tools" / "build_thing.py"

    class T(unittest.TestCase):
        def test_read(self):
            self.assertIn("probe.c", TOOL.read_text())
            subprocess.run(["patch", "--dry-run"], input=b"")
'''
RETAIL = '''
    import os, unittest
    from pathlib import Path
    DATA = Path(os.environ.get("RENEGADE_RETAIL_ROOT", "/nonexistent")) / "Data"

    class T(unittest.TestCase):
        def test_read(self):
            if not DATA.exists():
                self.skipTest("no retail")
'''
ARTIFACT = '''
    import subprocess, unittest
    from pathlib import Path
    ROOT = Path(__file__).resolve().parents[1]

    class T(unittest.TestCase):
        def test_selftest(self):
            subprocess.run([str(ROOT / "build/host/runtime"), "--selftest"], check=True)
'''
DEVICE = '''
    import ftplib, unittest

    class T(unittest.TestCase):
        def test_upload(self):
            ftplib.FTP("192.0.2.1").quit()
'''
FUNCTIONS = '''
    def test_one():
        assert 1 + 1 == 2

    def test_two():
        assert "a" == "b"
'''
SCRIPT = '''
    def main():
        return 0

    if __name__ == "__main__":
        raise SystemExit(main())
'''
CLI_DRIVER = '''
    import argparse

    if __name__ == "__main__":
        parser = argparse.ArgumentParser()
        parser.add_argument("--binary", required=True)
        parser.parse_args()
'''
BARE_IMPORT = '''
    import unittest
    from helper import parse

    class T(unittest.TestCase):
        def test_parse(self):
            self.assertEqual(parse("x"), ["x"])
'''
STAGE = '''
    patch --batch --forward --fuzz=0 --no-backup-if-mismatch \\
    \t-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/combat-fix.patch"
    echo "Applied: port/patches/combat-fix.patch"
'''
PATCH = '''
    --- a/a.cpp
    +++ b/a.cpp
    @@ -1 +1 @@
    -old
    +new
'''
READS_STAGED = '''
    import unittest
    from pathlib import Path
    ROOT = Path(__file__).resolve().parents[1]

    class T(unittest.TestCase):
        def test_staged(self):
            self.assertTrue((ROOT / "staging/combat/a.cpp").read_text())
'''
HARNESS = '''
    #include "../port/inc/a.h"
    int main() { return 0; }
'''
PASSING = '''
    import unittest

    class T(unittest.TestCase):
        def test_ok(self):
            self.assertTrue(True)
'''
FAILING = '''
    import unittest

    class T(unittest.TestCase):
        def test_bad(self):
            self.assertEqual(1, 2)

        def test_ok(self):
            self.assertTrue(True)
'''
SLOW = '''
    import time, unittest

    class T(unittest.TestCase):
        def test_slow(self):
            time.sleep(60)
'''


class FixtureCase(unittest.TestCase):
    def setUp(self):
        self.original_root = runner.ROOT
        self.temporary = tempfile.TemporaryDirectory(prefix='run-host-tests-')
        self.root = Path(self.temporary.name)
        runner.set_root(self.root)
        self.addCleanup(self.restore)

    def restore(self):
        runner.set_root(self.original_root)
        self.temporary.cleanup()

    def write(self, files):
        for name, text in files.items():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(textwrap.dedent(text).lstrip('\n'))
        runner.set_root(self.root)  # drop caches built from the previous files

    def classify(self, name):
        return runner.classify(name)


class ClassificationTests(FixtureCase):
    def test_lanes_follow_compiler_sanitizer_retail_artifact_and_device_use(self):
        self.write({'tools/test_pure.py': PURE, 'tools/test_compiles.py': COMPILES,
                    'tools/test_sanitizer.py': SANITIZER,
                    'tools/test_optional.py': SANITIZER_OPTIONAL,
                    'tools/test_retail.py': RETAIL, 'tools/test_artifact.py': ARTIFACT,
                    'tools/test_device.py': DEVICE})
        lanes = {name: self.classify(f'tools/test_{name}.py')['lane']
                 for name in ('pure', 'compiles', 'sanitizer', 'optional', 'retail',
                              'artifact', 'device')}
        self.assertEqual(lanes, {'pure': 'pure', 'compiles': 'compiled', 'sanitizer': 'sanitizer',
                                 'optional': 'compiled', 'retail': 'retail',
                                 'artifact': 'artifact', 'device': 'device'})
        optional = self.classify('tools/test_optional.py')['tags']
        self.assertIn('sanitizer-optional', optional)
        self.assertIn('tsan', optional)
        self.assertIn('skips-without-retail', self.classify('tools/test_retail.py')['tags'])
        self.assertIn('pure-python', self.classify('tools/test_pure.py')['tags'])

    def test_helper_main_block_is_not_reached_by_importing_a_parser(self):
        self.write({'tools/helper.py': HELPER, 'tools/test_parse.py': USES_HELPER_PARSE,
                    'tools/test_main.py': USES_HELPER_MAIN})
        self.assertEqual(self.classify('tools/test_parse.py')['lane'], 'pure')
        main = self.classify('tools/test_main.py')
        self.assertEqual(main['lane'], 'artifact')
        self.assertIn('needs-build-artifact', main['tags'])

    def test_executed_script_signals_propagate_but_reading_a_script_does_not(self):
        self.write({'tools/build_thing.py': BUILD_SCRIPT, 'tools/test_runs.py': RUNS_SCRIPT,
                    'tools/test_reads.py': READS_SCRIPT})
        runs = self.classify('tools/test_runs.py')
        self.assertEqual(runs['lane'], 'compiled')
        self.assertTrue(any('via tools/build_thing.py' in r for r in runs['reasons']), runs)
        self.assertEqual(self.classify('tools/test_reads.py')['lane'], 'pure')

    def test_kinds_and_run_modes(self):
        self.write({'tools/helper.py': HELPER, 'tools/test_functions.py': FUNCTIONS,
                    'tools/test_script.py': SCRIPT, 'tools/test_cli.py': CLI_DRIVER,
                    'tools/test_bare.py': BARE_IMPORT, 'tools/test_pure.py': PURE})
        modes = {name: (self.classify(f'tools/test_{name}.py')['kind'],
                        self.classify(f'tools/test_{name}.py')['run'])
                 for name in ('functions', 'script', 'cli', 'bare', 'pure')}
        self.assertEqual(modes, {'functions': ('functions', 'functions'),
                                 'script': ('script', 'script'), 'cli': ('cli-driver', 'none'),
                                 'bare': ('unittest', 'discover'),
                                 'pure': ('unittest', 'module')})

    def test_manifest_is_deterministic_and_counts_lanes(self):
        self.write({'tools/test_pure.py': PURE, 'tools/test_compiles.py': COMPILES})
        first = runner.manifest_text(runner.build_manifest())
        runner.set_root(self.root)
        self.assertEqual(first, runner.manifest_text(runner.build_manifest()))
        counts = json.loads(first)['counts']
        self.assertEqual(counts['modules'], 2)
        self.assertEqual(counts['lanes']['pure'], 1)
        self.assertEqual(counts['lanes']['compiled'], 1)


class ChangeMappingTests(FixtureCase):
    FILES = {
        'tools/stage_sources.sh': STAGE, 'port/patches/combat-fix.patch': PATCH,
        'staging/combat/a.cpp': 'new\n', 'port/renderer/r.cpp': 'int r;\n',
        'port/inc/a.h': '#pragma once\n', 'port/other/unknown.cpp': 'int u;\n',
        'tools/h_test.cpp': HARNESS, 'tools/helper.py': HELPER, 'docs/readme.md': 'text\n',
        'tools/test_staged.py': READS_STAGED, 'tools/test_pure.py': PURE,
        'tools/test_compiles.py': COMPILES, 'tools/test_parse.py': USES_HELPER_PARSE,
    }

    def setUp(self):
        super().setUp()
        self.write(self.FILES)
        self.tests = runner.build_manifest()['tests']

    def impacted(self, *changed, fallback='compiled'):
        selected, notes = runner.impacted_tests(set(changed), self.tests, None, fallback,
                                                files=self.FILES)
        return selected, notes

    def test_patch_maps_through_staged_file(self):
        selected, _ = self.impacted('port/patches/combat-fix.patch')
        self.assertEqual(set(selected), {'tools/test_staged.py'})
        self.assertIn('<- port/patches/combat-fix.patch', selected['tools/test_staged.py'][0])

    def test_direct_path_helper_and_harness_include(self):
        self.assertEqual(set(self.impacted('port/renderer/r.cpp')[0]), {'tools/test_pure.py'})
        self.assertEqual(set(self.impacted('tools/helper.py')[0]), {'tools/test_parse.py'})
        self.assertEqual(set(self.impacted('port/inc/a.h')[0]), {'tools/test_compiles.py'})
        self.assertEqual(set(self.impacted('tools/test_pure.py')[0]), {'tools/test_pure.py'})

    def test_build_system_change_selects_everything(self):
        selected, notes = self.impacted('CMakeLists.txt')
        self.assertEqual(set(selected), set(self.tests))
        self.assertTrue(any('every test' in note for note in notes))

    def test_unmapped_files_and_fallbacks(self):
        selected, notes = self.impacted('docs/readme.md')
        self.assertEqual(selected, {})
        self.assertTrue(any('unmapped' in note for note in notes))
        compiled, _ = self.impacted('port/other/unknown.cpp')
        self.assertEqual(set(compiled), {'tools/test_compiles.py'})
        self.assertEqual(self.impacted('port/other/unknown.cpp', fallback='none')[0], {})
        everything, _ = self.impacted('docs/readme.md', fallback='all')
        self.assertEqual(set(everything), set(self.tests))

    def test_stage_registration_lines(self):
        for line in ('patch --batch --forward --fuzz=0 --no-backup-if-mismatch \\',
                     '\t-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/x-y.patch"',
                     'echo "Applied: port/patches/x-y.patch"', '# comment', ''):
            self.assertTrue(runner.STAGE_PATCH_LINE.match(line), line)
        for line in ('sed -i "s/a/b/" "$rv_stage/combat/a.cpp"', 'rm -rf -- "$rv_stage"'):
            self.assertFalse(runner.STAGE_PATCH_LINE.match(line), line)


class ShardingTests(FixtureCase):
    THREE = '''
        import unittest

        class T(unittest.TestCase):
            def test_a(self): pass
            def test_b(self): pass
            def test_c(self): pass
    '''
    MIXIN = '''
        import unittest

        class Shared:
            def test_shared(self): pass

        class T(Shared, unittest.TestCase):
            def test_own(self): pass
    '''

    def plan(self, record, jobs=2, split_over=6.0):
        tests = runner.build_manifest()['tests']
        args = argparse.Namespace(split_over=split_over, jobs=jobs)
        return runner.plan_jobs(['tools/test_three.py'], tests, args,
                                {'tools/test_three.py': record})

    def test_slow_module_is_bin_packed_by_recorded_case_time(self):
        self.write({'tools/test_three.py': self.THREE})
        ids = [f'tools.test_three.T.test_{name}' for name in 'abc']
        record = {'seconds': 20.0, 'cases': dict(zip(ids, (9.0, 8.0, 3.0)))}
        jobs = self.plan(record)
        self.assertEqual([(j['ids'], j['expected']) for j in jobs],
                         [([ids[0]], 9.0), ([ids[1], ids[2]], 11.0)])
        self.assertEqual(len(self.plan(record, jobs=8)), 3)
        self.assertEqual(self.plan(record, split_over=0)[0]['ids'], None)
        stale = {'seconds': 20.0, 'cases': {ids[0]: 20.0}}
        self.assertEqual(len(self.plan(stale)), 1)

    def test_inherited_tests_are_never_split(self):
        self.write({'tools/test_mixin.py': self.MIXIN, 'tools/test_three.py': self.THREE})
        self.assertIsNone(runner.static_test_ids('tools/test_mixin.py'))
        self.assertEqual(len(runner.static_test_ids('tools/test_three.py')), 3)


class OutputParsingTests(unittest.TestCase):
    def test_unittest_summary_and_subtest_deduplication(self):
        text = textwrap.dedent('''
            ======================================================================
            FAIL: test_a (tools.test_x.Case.test_a) (mode='0')
            ----------------------------------------------------------------------
            FAIL: test_a (tools.test_x.Case.test_a) (mode='1')
            ERROR: setUpClass (tools.test_x.Other)
            ----------------------------------------------------------------------
            Ran 7 tests in 0.250s

            FAILED (failures=2, errors=1, skipped=3)
        ''')
        verdict, counts, failing = runner.parse_unittest_output(text)
        self.assertEqual(verdict, 'FAILED')
        self.assertEqual((counts['tests'], counts['failures'], counts['errors'], counts['skipped']),
                         (7, 2, 1, 3))
        self.assertEqual(failing, [{'kind': 'FAIL', 'id': 'tools.test_x.Case.test_a'},
                                   {'kind': 'ERROR', 'id': 'tools.test_x.Other.setUpClass'}])
        verdict, counts, _ = runner.parse_unittest_output('Ran 1 test in 0.1s\n\nOK (skipped=1)\n')
        self.assertEqual((verdict, counts['tests'], counts['skipped']), ('OK', 1, 1))

    def test_manifest_reasons_never_carry_absolute_host_paths(self):
        self.assertEqual(runner._public('abs:/srv/user/tree/build/deps/x.tar.gz'),
                         '<absolute>/build/deps/x.tar.gz')
        self.assertEqual(runner._public('/srv/user/Games/Renegade/Data'), '<absolute>/Data')
        self.assertEqual(runner._public('/opt/elsewhere'), '<absolute path>')
        self.assertEqual(runner._public('build/host/runtime'), 'build/host/runtime')

    def test_known_failure_matching_accepts_short_ids(self):
        known = {'test_vita_x.test_method': 'r', 'tools.test_whole': 'r'}
        self.assertTrue(runner.is_known_failure('tools.test_vita_x.Case.test_method',
                                                'tools.test_vita_x', known))
        self.assertFalse(runner.is_known_failure('tools.test_vita_x.Case.test_other',
                                                 'tools.test_vita_x', known))
        self.assertTrue(runner.is_known_failure('anything', 'tools.test_whole', known))


class ExecutionTests(FixtureCase):
    def run_main(self, *arguments):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            code = runner.main(list(arguments))
        return code, output.getvalue()

    def test_function_style_modules_run_without_pytest(self):
        self.write({'tools/test_functions.py': FUNCTIONS})
        output = io.StringIO()
        saved_path = list(sys.path)
        try:
            with contextlib.redirect_stdout(output):
                code = runner.run_function_tests('tools/test_functions.py')
        finally:
            sys.path[:] = saved_path
            sys.modules.pop('tools.test_functions', None)
        self.assertEqual(code, 1)
        verdict, counts, failing = runner.parse_unittest_output(output.getvalue())
        self.assertEqual((verdict, counts['tests'], counts['failures']), ('FAILED', 2, 1))
        self.assertEqual(failing[0]['id'], 'tools.test_functions.test_two')

    def test_parallel_run_summary_exit_codes_and_known_failures(self):
        self.write({'tools/test_passing.py': PASSING, 'tools/test_failing.py': FAILING})
        summary = self.root / 'summary.json'
        code, output = self.run_main('--jobs', '2', '--summary', str(summary))
        self.assertEqual(code, 1, output)
        data = json.loads(summary.read_text())
        statuses = {r['module']: r['status'] for r in data['results']}
        self.assertEqual(statuses, {'tools.test_passing': 'pass', 'tools.test_failing': 'fail'})
        self.assertEqual(data['tests_run'], 3)
        failing = next(r for r in data['results'] if r['module'] == 'tools.test_failing')
        self.assertEqual(failing['failing'], [{'kind': 'FAIL', 'id': 'tools.test_failing.T.test_bad'}])
        self.assertIn('Slowest', output)
        (self.root / 'tools/host_test_known_failures.json').write_text(json.dumps(
            {'known_failures': [{'id': 'tools.test_failing.T.test_bad', 'reason': 'fixture'}]}))
        code, output = self.run_main('--jobs', '2', '--summary', str(summary),
                                     '--allow-known-failures')
        self.assertEqual(code, 0, output)
        self.assertIn('KNOWN FAIL tools.test_failing', output)

    def test_timeout_usage_errors_and_manifest_check(self):
        self.write({'tools/test_slow.py': SLOW, 'tools/test_passing.py': PASSING})
        summary = self.root / 'summary.json'
        code, output = self.run_main('test_slow', '--timeout', '1', '--summary', str(summary))
        self.assertEqual(code, 1, output)
        self.assertEqual(json.loads(summary.read_text())['results'][0]['status'], 'timeout')
        self.assertEqual(self.run_main('--lanes', 'nonsense')[0], 2)
        self.assertEqual(self.run_main('no_such_test_module')[0], 2)
        self.assertEqual(self.run_main('--check-manifest')[0], 3)
        self.assertEqual(self.run_main('--write-manifest')[0], 0)
        self.assertEqual(self.run_main('--check-manifest')[0], 0)
        code, output = self.run_main('--pure-only', '--list')
        self.assertEqual(code, 0)
        self.assertIn('2 module(s) selected', output)


if __name__ == '__main__':
    unittest.main()
