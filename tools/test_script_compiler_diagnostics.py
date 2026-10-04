import unittest
from pathlib import Path
import subprocess
import tempfile
from tools.audit_script_compiler_diagnostics import isolated_command, parse_diagnostics, public_summary


class CompilerDiagnosticsTests(unittest.TestCase):
    def test_isolates_outputs_and_preserves_per_unit_flags(self):
        args = isolated_command('/usr/bin/cmake -E env X=1 /usr/bin/ccache /usr/bin/c++ '
                                '-DHOST=1 -include defaults.h -fpermissive -MD '
                                '-MT old -MFold.d -o old.o -c source.cpp', '/tmp/new.o')
        self.assertEqual(args[0], '/usr/bin/c++')
        self.assertIn('-fpermissive', args)
        self.assertIn('defaults.h', args)
        self.assertNotIn('old.o', args)
        self.assertNotIn('-MFold.d', args)
        self.assertEqual(args[-2:], ['-o', '/tmp/new.o'])

    def test_rejects_unknown_compiler(self):
        with self.assertRaises(ValueError):
            isolated_command('ar source.cpp', '/tmp/new.o')

    def test_preserves_nested_notes_and_locations(self):
        result = parse_diagnostics('[{"kind":"warning","message":"read",'
                                   '"option":"-Wuninitialized","locations":[], '
                                   '"children":[{"kind":"note","message":"declared"}]}]')
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['option'], '-Wuninitialized')

    def test_empty_diagnostics(self):
        self.assertEqual(parse_diagnostics('[]'), [])

    def test_malformed_is_not_silent_success(self):
        for value in ('noise', '{}', '[{}]'):
            with self.assertRaises(ValueError):
                parse_diagnostics(value)

    def test_actual_gcc_detects_uninitialized_read(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'probe.cpp'
            source.write_text('int probe() { int value; return value; }\n')
            command = isolated_command('/usr/bin/c++ -c ' + str(source),
                                       Path(directory) / 'probe.o')
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            diagnostics = parse_diagnostics(result.stderr)
            self.assertTrue(any(item.get('option') == '-Wuninitialized'
                                for item in diagnostics), diagnostics)

    def test_summary_keeps_unknown_and_unselected_rows(self):
        receipt = {'rows': [{'name': 'DLLmain.cpp', 'status': 'unknown',
                            'compile_command_matches': 0, 'source_sha256': 'abc'},
                           {'name': 'Mission01.cpp', 'status': 'unknown',
                            'compile_command_matches': 1, 'returncode': 0,
                            'diagnostics': [{'kind': 'warning', 'message': 'read',
                                             'option': '-Wuninitialized'}]}],
                   'dsp_sha256': 'def', 'diagnostic_counts': {'-Wuninitialized': 1},
                   'limits': ['host only']}
        summary = public_summary(receipt)
        self.assertEqual(summary['counts'], {'unknown': 2})
        self.assertFalse(summary['complete'])
        self.assertEqual(summary['rows'][1]['dataflow_warning_count'], 1)
        self.assertNotIn('diagnostics', summary['rows'][1])


if __name__ == '__main__':
    unittest.main()
