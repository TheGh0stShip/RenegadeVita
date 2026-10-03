import unittest
from tools.audit_sweep_performance import records


class LedgerRecordsTest(unittest.TestCase):
    def test_sections_tables_and_provenance(self):
        source = '# Ledger\ntext\n## Cost\n| Hypothesis | Evidence |\n| --- | --- |\n| Slow load | unmeasured |\n\n## Next\nunknown\n'
        rows = records(source)
        self.assertEqual([r['kind'] for r in rows],
                         ['ledger_section', 'ledger_section', 'ledger_table_row', 'ledger_section'])
        self.assertEqual(rows[2]['line'], 6)
        self.assertEqual(rows[2]['section'], 'Cost')
        self.assertEqual(rows[1]['end_line'], 7)
        self.assertNotEqual(rows[1]['content_sha256'], rows[2]['content_sha256'])
        self.assertNotIn('measurement', rows[2])

    def test_duplicate_labels_remain_distinct_by_line(self):
        rows = records('## Same\nfirst\n## Same\nsecond\n')
        self.assertEqual(len(rows), 2)
        self.assertNotEqual(rows[0]['line'], rows[1]['line'])
        self.assertNotEqual(rows[0]['content_sha256'], rows[1]['content_sha256'])
