import unittest

from audit_sweep_port_guards import directives, patch_guards, stage_patch_selection, wrapper_references


class PortGuardInventoryTest(unittest.TestCase):
    def test_multiline_added_macro_with_context_directive(self):
        patch = ('--- a/test.cpp\n+++ b/test.cpp\n@@ -10,2 +10,3 @@\n'
                 ' #if defined(OTHER) || \\\n+                 +    defined(RENEGADE_VITA_PORT) || \\\n+                  defined(FINAL)\n')
        rows = patch_guards(patch)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['change'], 'added')
        self.assertEqual(rows[0]['hunk_lines'], [10, 11, 12])
        self.assertEqual(rows[0]['patch_lines'], [4, 5, 6])

    def test_removed_guard_retained_separately(self):
        patch = ('--- a/test.cpp\n+++ b/test.cpp\n@@ -4,2 +4,1 @@\n'
                 '-#ifdef RENEGADE_VITA_PORT\n body();\n')
        rows = patch_guards(patch)
        self.assertEqual([(r['change'], r['hunk_lines']) for r in rows], [('removed', [4])])

    def test_context_only_is_not_introduced_guard(self):
        patch = ('--- a/test.cpp\n+++ b/test.cpp\n@@ -1,2 +1,2 @@\n'
                 ' #ifdef VITA\n-old();\n+new();\n')
        self.assertEqual(patch_guards(patch), [])

    def test_macro_families_and_token_boundaries(self):
        lines = ['#if RENEGADE_A4_ORIGINAL_FRONTEND', '#ifndef _UNIX',
                 '#elif RENEGADE_HOST_AUDIO', '#if MY_VITA_EXTENSION',
                 '#define VITA 1', '#ifdef OTHER']
        self.assertEqual([r[0] for r in directives(lines)], [0, 1, 2])

    def test_selection_and_both_wrapper_forms(self):
        self.assertEqual(stage_patch_selection('< "$rv_root/port/patches/one.patch"'),
                         ['port/patches/one.patch'])
        self.assertEqual(wrapper_references('-Wl,--wrap=shark_init\n-Wl,--wrap,pthread_create'),
                         [{'symbol': 'shark_init', 'line': 1}, {'symbol': 'pthread_create', 'line': 2}])


if __name__ == '__main__':
    unittest.main()
