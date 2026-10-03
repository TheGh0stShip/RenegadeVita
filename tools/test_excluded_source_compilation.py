import shlex
import subprocess
import tempfile
import unittest
from pathlib import Path

from tools.check_excluded_original_sources import compile_command


class ExcludedCompilationTests(unittest.TestCase):
    def test_real_compile_preserves_flags_and_quoted_paths(self):
        with tempfile.TemporaryDirectory(prefix='compile closure ') as temporary:
            root = Path(temporary)
            template = root / 'template.cpp'
            source = root / 'original.cpp'
            output = root / 'original.o'
            template.write_text('invalid template must never be compiled')
            source.write_text('#ifndef REQUIRED_OWNER_FLAG\n#error missing flag\n#endif\n'
                              'static_assert(sizeof(int) == 4);\nint value = REQUIRED_OWNER_FLAG;\n')
            command = shlex.join(['c++', '-DREQUIRED_OWNER_FLAG=7', '-c', str(template),
                                  '-MD', '-MT', 'old.o', '-MF', 'old.d', '-o', 'old.o'])
            derived = compile_command(command, root, template, source, output)
            subprocess.run(derived, cwd=root, check=True, capture_output=True)
            self.assertGreater(output.stat().st_size, 0)
            self.assertTrue(Path(str(output) + '.d').is_file())
            self.assertFalse((root / 'old.o').exists())
            self.assertIn('-DREQUIRED_OWNER_FLAG=7', derived)

    def test_missing_or_ambiguous_owner_is_rejected(self):
        root = Path('/tmp')
        line = 'c++ -c /tmp/template.cpp -o old.o'
        for commands in ['', line + '\n' + line]:
            with self.assertRaises(ValueError):
                compile_command(commands, root, root/'template.cpp', root/'original.cpp', root/'out.o')


if __name__ == '__main__':
    unittest.main()
