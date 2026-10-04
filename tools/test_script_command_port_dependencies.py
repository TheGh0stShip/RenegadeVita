import unittest
from tools.audit_script_command_port_dependencies import join


class DependencyJoinTests(unittest.TestCase):
    def test_overloads_macros_and_unmatched_calls_are_preserved(self):
        commands = {'rows':[{'name':'Command','owners':[{'staged':{'resolved':False,
            'definition_candidates':[{'call_name_candidates':['Helper','Macro']},
                                     {'call_name_candidates':['Other','Helper']}]}}]}]}
        base = {'file':'port/test.cpp','line':1,'status':'unknown'}
        guards = {'rows':[{**base,'kind':'port_function','declarator':'Helper(int)', 'row_id':'a'},
                         {**base,'kind':'port_function','declarator':'Helper(float)', 'row_id':'b'},
                         {**base,'kind':'port_macro_definition','name':'Macro','function_like':True,'row_id':'c'}]}
        result = join(commands,guards)
        row = result['rows'][0]
        self.assertEqual(row['unmatched_calls'],['Other'])
        self.assertEqual(len(row['matched_calls'][0]['candidates']),2)
        self.assertEqual(result['matched_call_names'],2)
        self.assertEqual(row['status'],'unknown')

    def test_absent_candidate_does_not_mean_original_behavior(self):
        commands = {'rows':[{'name':'Command','owners':[{'staged':{'resolved':True,
                            'call_name_candidates':['OriginalOwner']}}]}]}
        result = join(commands,{'rows':[]})
        self.assertEqual(result['commands_with_port_candidates'],0)
        self.assertFalse(result['complete'])
        self.assertEqual(result['rows'][0]['unmatched_calls'],['OriginalOwner'])
