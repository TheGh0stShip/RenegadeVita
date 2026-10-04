import unittest

from probe_host_script_registry import script_candidates


class ScriptCandidateTests(unittest.TestCase):
    def test_inactive_and_duplicate_candidates_retained(self):
        rows=[{'kind':'script','arguments':['M00_Test'],'selected_for_target':False},
              {'kind':'script','arguments':['M00_Test'],'selected_for_target':None},
              {'kind':'persist','arguments':['Other']}]
        self.assertEqual(script_candidates({'registration_candidates':rows}),rows[:2])

    def test_debugger_expression_injection_rejected(self):
        for value in ['bad\"name', 'A);quit', 'name with space', '']:
            with self.assertRaises(ValueError):
                script_candidates({'registration_candidates':[{'kind':'script','arguments':[value]}]})

    def test_empty_denominator_rejected(self):
        with self.assertRaises(ValueError):
            script_candidates({'registration_candidates':[]})


if __name__ == '__main__':
    unittest.main()
