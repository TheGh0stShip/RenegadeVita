import unittest
from tools.audit_live_script_parameters import parameter_shape


class ParameterShapeTests(unittest.TestCase):
    def test_empty_and_unrecorded_are_distinct(self):
        self.assertEqual(parameter_shape('', None)['category'], 'parameters_unrecorded')
        self.assertEqual(parameter_shape('', '')['category'], 'equal_count')

    def test_commas_are_positional_not_csv(self):
        shape = parameter_shape('Name:string,Position:Vector3', '"a,b",1 2 3')
        self.assertEqual(shape['category'], 'excess_values')
        self.assertEqual(shape['value_count'], 3)
        self.assertEqual(parameter_shape('A:int,B:int', '1,')['category'], 'equal_count')

    def test_original_descriptor_byte_bound(self):
        shape = parameter_shape('A' * 511 + ',B:int', '1,2')
        self.assertTrue(shape['descriptor_truncated'])
        self.assertEqual(shape['descriptor_count'], 1)

    def test_trailing_descriptor_comma_is_not_a_named_parameter(self):
        self.assertEqual(parameter_shape('A:int,B:int,', '1,2')['category'], 'equal_count')
        self.assertEqual(parameter_shape('A:int,,B:int', '1,2,3')['descriptor_count'], 3)


if __name__ == '__main__':
    unittest.main()
