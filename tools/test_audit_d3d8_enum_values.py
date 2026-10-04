import unittest

from audit_d3d8_enum_values import assignments, compare


class D3DEnumComparison(unittest.TestCase):
    def test_literals_comments_and_expressions(self):
        rows = assignments('// D3DRS_FAKE=7,\nenum { D3DRS_A=0x8U, D3DRS_B=(1<<2), D3DRS_C=12 };')
        self.assertNotIn('D3DRS_FAKE', rows)
        self.assertEqual(rows['D3DRS_A'][0]['value'], 8)
        self.assertIsNone(rows['D3DRS_B'][0]['value'])
        self.assertEqual(rows['D3DRS_C'][0]['value'], 12)

    def test_difference_absence_and_duplicate_are_distinct(self):
        rows = compare('enum {D3DRS_A=26,D3DRS_B=141,D3DRS_C=2,D3DRS_D=1};',
                       'enum {D3DRS_A=139,D3DRS_B=141,D3DRS_D=1}; enum {D3DRS_D=2};')
        self.assertEqual({r['symbol']: r['comparison'] for r in rows},
            {'D3DRS_A': 'different', 'D3DRS_B': 'equal', 'D3DRS_C': 'unresolved', 'D3DRS_D': 'unresolved'})


if __name__ == '__main__':
    unittest.main()
