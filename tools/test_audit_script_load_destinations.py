import unittest
from tools.audit_script_load_destinations import calls


class LoadDestinationTests(unittest.TestCase):
    def test_nested_size_and_array_destination(self):
        row = calls('Commands->Load_Data(loader, sizeof(obj.Values[index]), &obj.Values[index]);')[0]
        self.assertTrue(row['parse_complete'])
        self.assertEqual(row['size_expression'], 'sizeof(obj.Values[index])')
        self.assertEqual(row['destination_expression'], '&obj.Values[index]')

    def test_disabled_and_comment_calls_ignored(self):
        self.assertEqual(calls('#if 0\nCommands->Load_Data(a,b,c);\n#endif\n/* Commands->Load_Data(a,b,c); */'), [])

    def test_unbalanced_retained_as_unknown(self):
        self.assertFalse(calls('Commands->Load_Data(loader, sizeof(x)')[0]['parse_complete'])


if __name__ == '__main__':
    unittest.main()
