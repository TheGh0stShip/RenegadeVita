import unittest
from tools.audit_script_parameter_reads import reads


class ParameterReadTests(unittest.TestCase):
    def test_comments_strings_and_case(self):
        body = '// Get_Int_Parameter("Absent")\nconst char* s="Get_Parameter(0)";\nGet_Int_Parameter("a");'
        result = reads(body, 'A:int')
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['category'], 'literal_name_matches')

    def test_underscores_are_significant(self):
        result = reads('Get_Int_Parameter("Killable_ByNotStar");', 'Killable_by_NotStar:int')
        self.assertEqual(result[0]['category'], 'literal_name_absent')

    def test_computed_nested_and_indices_retained(self):
        result = reads('Get_Parameter(make_name(1)); Get_Float_Parameter(-1);', '')
        self.assertEqual([r['category'] for r in result], ['computed_argument', 'literal_index'])
        self.assertEqual(result[1]['index'], -1)

    def test_adjacent_literals_and_trailing_description_comma(self):
        result = reads('Get_Parameter("A" /* join */ "B");', 'AB:int,')
        self.assertEqual(result[0]['index'], 0)


if __name__ == '__main__':
    unittest.main()
