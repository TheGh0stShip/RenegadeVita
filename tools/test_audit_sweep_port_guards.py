import unittest

from audit_sweep_port_guards import apply_reviews, directives, mask_noncode, patch_guards, stage_patch_selection, wrapper_references


class PortGuardInventoryTest(unittest.TestCase):
    def test_changed_initializer_invalidates_definition_review(self):
        rows = [{'kind': 'port_function', 'file': 'port/a.cpp', 'declarator': 'X()',
                 'body_sha256': 'same', 'definition_sha256': 'new', 'status': 'unknown'}]
        review = {'file': 'port/a.cpp', 'declarator': 'X()', 'body_sha256': 'same',
                  'definition_sha256': 'old', 'status': 'boundary_replaced'}
        self.assertEqual(len(apply_reviews(rows, [review])), 1)
        self.assertEqual(rows[0]['status'], 'unknown')

    def test_literal_comment_and_raw_string_directives_are_not_guards(self):
        lines = ['/*', '#ifdef VITA', '*/', 'const char *s=R"tag(',
                 '#if __vita__', ')tag";', '#if OTHER // RENEGADE_VITA_PORT',
                 '#ifdef RENEGADE_HOST_AUDIO']
        self.assertEqual([r[0] for r in directives(lines)], [7])

    def test_continued_line_comment_hides_next_physical_line(self):
        lines = ['// continued \\', '#ifdef VITA', '#ifdef __vita__']
        self.assertEqual([r[0] for r in directives(lines)], [2])

    def test_mask_preserves_offsets_and_numeric_separators(self):
        text = 'int n=1\'000 + 2\'000; /* comment */\nconst char *s="\\\" VITA";'
        masked = mask_noncode(text)
        self.assertEqual(len(masked), len(text))
        self.assertEqual(masked.count('\n'), text.count('\n'))
        self.assertIn("1'000 + 2'000", masked)
        self.assertNotIn('VITA', masked)

    def test_changed_caller_context_invalidates_review(self):
        rows = [{'kind': 'port_function', 'file': 'port/a.cpp', 'declarator': 'f()',
                 'body_sha256': 'same', 'status': 'unknown'}]
        review = {'file': 'port/a.cpp', 'declarator': 'f()', 'body_sha256': 'same',
                  'status': 'stubbed_or_noop'}
        issues = apply_reviews(rows, [review], {'staging/caller.cpp': 'old'},
                               {'staging/caller.cpp': 'new'})
        self.assertEqual(len(issues), 1)
        self.assertEqual(rows[0]['status'], 'unknown')

    def test_stale_review_cannot_classify_changed_body(self):
        rows = [{'kind': 'port_function', 'file': 'port/a.cpp', 'declarator': 'f()',
                 'body_sha256': 'new', 'status': 'unknown'}]
        review = {'file': 'port/a.cpp', 'declarator': 'f()', 'body_sha256': 'old',
                  'status': 'stubbed_or_noop'}
        self.assertEqual(len(apply_reviews(rows, [review])), 1)
        self.assertEqual(rows[0]['status'], 'unknown')

    def test_review_requires_unique_identity(self):
        row = {'kind': 'port_function', 'file': 'port/a.cpp', 'declarator': 'f()',
               'body_sha256': 'same', 'status': 'unknown'}
        review = {key: row[key] for key in ('file', 'declarator', 'body_sha256')}
        review['status'] = 'stubbed_or_noop'
        self.assertEqual(len(apply_reviews([row.copy(), row.copy()], [review])), 1)

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
                 '#define VITA 1', '#ifdef OTHER', '#if defined(__vita__)',
                 '#ifndef __VITA__']
        self.assertEqual([r[0] for r in directives(lines)], [0, 1, 2, 6, 7])

    def test_selection_and_both_wrapper_forms(self):
        self.assertEqual(stage_patch_selection('< "$rv_root/port/patches/one.patch"'),
                         ['port/patches/one.patch'])
        self.assertEqual(wrapper_references('-Wl,--wrap=shark_init\n-Wl,--wrap,pthread_create'),
                         [{'symbol': 'shark_init', 'line': 1}, {'symbol': 'pthread_create', 'line': 2}])


if __name__ == '__main__':
    unittest.main()
