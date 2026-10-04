import unittest

from audit_sweep_port_guards import apply_reviews, branch_contexts, directives, macro_definitions, mask_noncode, patch_guards, reconcile_patch_guards, row_identity, stage_patch_destinations, stage_patch_selection, validate_inventory, wrapper_references


class PortGuardInventoryTest(unittest.TestCase):
    def test_unchanged_body_in_changed_preprocessor_branch_invalidates_review(self):
        row = {'kind': 'port_function', 'file': 'port/a.cpp', 'declarator': 'f()',
               'body_sha256': 'same', 'status': 'unknown',
               'entry_preprocessor_context': [{'condition': '#if NEW', 'branch': '#else'}]}
        review = {'file': 'port/a.cpp', 'declarator': 'f()', 'body_sha256': 'same',
                  'status': 'stubbed_or_noop',
                  'entry_preprocessor_context': [{'condition': '#if OLD', 'branch': '#else'}]}
        self.assertEqual(len(apply_reviews([row], [review])), 1)
        self.assertEqual(row['status'], 'unknown')

    def test_guard_review_requires_source_pin_and_exact_directive(self):
        row = {'kind': 'current_source_guard', 'file': 'staging/a.cpp', 'line': 4,
               'directive': '#if __vita__', 'status': 'unknown'}
        review = dict(row, row_id=row_identity(row), status='disabled_by_port_guard',
                      original_owner='render', behavior='skip', callers=[],
                      affected_scope=['host'], acceptance_open='pixels')
        self.assertEqual(len(apply_reviews([row], [review])), 1)
        self.assertEqual(apply_reviews([row], [review], {'staging/a.cpp': 'hash'},
                                      {'staging/a.cpp': 'hash'}), [])
        row['directive'] = '#if OTHER'
        row['status'] = 'unknown'
        self.assertEqual(len(apply_reviews([row], [review], {'staging/a.cpp': 'hash'},
                                          {'staging/a.cpp': 'hash'})), 1)

    def test_non_function_review_requires_exact_row_and_source_pin(self):
        row = {'kind': 'link_wrapper_reference', 'file': 'CMakeLists.txt', 'line': 9,
               'column': 4, 'symbol': 'wrapped', 'status': 'unknown'}
        review = dict(row, row_id=row_identity(row), status='boundary_replaced',
                      original_owner='platform library entry', behavior='observe call',
                      callers=['native target'], affected_scope=['Vita'],
                      acceptance_open='runtime evidence')
        expected = {'CMakeLists.txt': 'same'}
        self.assertEqual(apply_reviews([row], [review], expected, expected), [])
        self.assertEqual(row['status'], 'boundary_replaced')
        moved = dict(row, line=10, status='unknown')
        self.assertEqual(len(apply_reviews([moved], [review], expected, expected)), 1)
        self.assertEqual(moved['status'], 'unknown')
        unchanged = dict(row, status='unknown')
        self.assertEqual(len(apply_reviews([unchanged], [review], expected,
                                           {'CMakeLists.txt': 'changed'})), 1)
        self.assertEqual(unchanged['status'], 'unknown')

    def test_review_distinguishes_same_signature_in_alternative_branches(self):
        rows = [{'kind': 'port_function', 'file': 'port/a.cpp', 'declarator': 'f()',
                 'body_sha256': body, 'status': 'unknown'} for body in ('native', 'fallback')]
        review = {'file': 'port/a.cpp', 'declarator': 'f()', 'body_sha256': 'fallback',
                  'status': 'stubbed_or_noop', 'original_owner': 'movie',
                  'behavior': 'skip', 'callers': [], 'affected_scope': [],
                  'acceptance_open': 'runtime'}
        self.assertEqual(apply_reviews(rows, [review]), [])
        self.assertEqual([row['status'] for row in rows], ['unknown', 'stubbed_or_noop'])

    def test_reconciliation_rejects_missing_and_duplicate_rows(self):
        row = {'kind': 'port_function', 'file': 'a.cpp', 'line': 1,
               'status': 'unknown', 'evidence_class': 'source_syntax'}
        result = {'rows': [row], 'complete': False,
                  'totals': {'rows': 1, 'by_kind': {'port_function': 1}, 'by_status': {'unknown': 1}}}
        validate_inventory(result)
        self.assertEqual(len(row['row_id']), 64)
        self.assertFalse(result['complete'])
        result['rows'].append(row.copy())
        with self.assertRaisesRegex(ValueError, 'total'):
            validate_inventory(result)
        result['totals'] = {'rows': 2, 'by_kind': {'port_function': 2}, 'by_status': {'unknown': 2}}
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            validate_inventory(result)

    def test_nested_else_and_elif_contexts_remain_uninterpreted(self):
        text = ('#if FEATURE\n#if defined(__vita__)\nvoid real() {}\n'
                '#else\nvoid fallback() {}\n#endif\n#elif OTHER\nvoid other() {}\n'
                '#endif\nvoid always() {}')
        contexts = branch_contexts(text, [3, 5, 8, 10])
        self.assertEqual(len(contexts[3]), 2)
        self.assertEqual(contexts[5][-1]['branch'], '#else')
        self.assertEqual(contexts[5][-1]['condition'], '#if defined(__vita__)')
        self.assertEqual(contexts[8][0]['branch'], '#elif OTHER')
        self.assertEqual(contexts[10], [])

    def test_macro_function_body_is_not_lost_from_denominator(self):
        text = '#define STUB(name) \\\n+          int name() { return 0; }\n#define CONSTANT (0)\n/* #define HIDDEN() {} */'
        rows = macro_definitions(text)
        self.assertEqual([r['name'] for r in rows], ['STUB', 'CONSTANT'])
        self.assertTrue(rows[0]['function_like'])
        self.assertTrue(rows[0]['contains_return_token'])
        self.assertTrue(rows[0]['contains_brace'])
        self.assertEqual(rows[0]['end_line'], 2)
        self.assertFalse(rows[1]['function_like'])

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

    def test_patch_guard_reconciliation_is_exact_and_nonclassifying(self):
        rows = [
            {'kind': 'patch_guard', 'file': 'port/patches/x.patch',
             'target': 'b/combat/x.cpp', 'directive': '#if FEATURE',
             'stage_destination': 'staging', 'status': 'unknown'},
            {'kind': 'current_source_guard', 'file': 'staging/combat/x.cpp',
             'line': 9, 'directive': '#if FEATURE', 'status': 'unknown'},
            {'kind': 'current_source_guard', 'file': 'staging/combat/x.cpp',
             'line': 20, 'directive': '#if OTHER', 'status': 'unknown'},
        ]
        reconcile_patch_guards(rows)
        self.assertEqual(rows[0]['current_target'], 'staging/combat/x.cpp')
        self.assertEqual(rows[0]['exact_current_guard_count'], 1)
        self.assertEqual(rows[0]['exact_current_guard_lines'], [9])
        self.assertEqual(rows[0]['status'], 'unknown')

    def test_stage_patch_destinations_preserve_module_working_directory(self):
        text = ('patch --batch \\\n  -d "$rv_stage/combat" -p1 < '
                '"$rv_root/port/patches/combat-x.patch"\n'
                'patch -d "$rv_stage" -p1 < "$rv_root/port/patches/root.patch"\n')
        self.assertEqual(stage_patch_destinations(text), {
            'port/patches/combat-x.patch': 'staging/combat',
            'port/patches/root.patch': 'staging',
        })

    def test_context_only_is_not_introduced_guard(self):
        patch = ('--- a/test.cpp\n+++ b/test.cpp\n@@ -1,2 +1,2 @@\n'
                 ' #ifdef VITA\n-old();\n+new();\n')
        self.assertEqual(patch_guards(patch), [])

    def test_macro_families_and_token_boundaries(self):
        lines = ['#if RENEGADE_A4_ORIGINAL_FRONTEND', '#ifndef _UNIX',
                 '#elif RENEGADE_HOST_AUDIO', '#if MY_VITA_EXTENSION',
                 '#define VITA 1', '#ifdef OTHER', '#if defined(__vita__)',
                 '#ifndef __VITA__', '#if RENEGADE_ORIGINAL_SORTING',
                 '#ifdef RENEGADE_SHORT_WCHAR_ABI', '#if RENEGADE_MILES_MANUAL_MIX',
                 '#if NOT_RENEGADE_ORIGINAL_SORTING']
        self.assertEqual([r[0] for r in directives(lines)], [0, 1, 2, 6, 7, 8, 9, 10])

    def test_selection_and_both_wrapper_forms(self):
        self.assertEqual(stage_patch_selection('< "$rv_root/port/patches/one.patch"'),
                         ['port/patches/one.patch'])
        self.assertEqual(wrapper_references('-Wl,--wrap=shark_init\n-Wl,--wrap,pthread_create'),
                         [{'symbol': 'shark_init', 'line': 1, 'column': 5},
                          {'symbol': 'pthread_create', 'line': 2, 'column': 5}])


if __name__ == '__main__':
    unittest.main()
