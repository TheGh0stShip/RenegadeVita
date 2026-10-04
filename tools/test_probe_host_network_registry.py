import unittest

from probe_host_network_registry import debugger_script, expected_factories


class NetworkRegistryTests(unittest.TestCase):
    def test_template_ids_deduplicated_with_full_unsigned_width(self):
        text = '\n'.join([
            'W SimpleNetworkObjectFactoryClass<A, 1001>::Get_Class_ID() const',
            'W SimpleNetworkObjectFactoryClass<A, 1001>::Get_Class_ID() const',
            't SimpleNetworkObjectFactoryClass<(anonymous namespace)::B, -1>::Get_Class_ID() const'])
        self.assertEqual(expected_factories(text), [
            {'class_id': 1001, 'classes': ['A']},
            {'class_id': 4294967295, 'classes': ['(anonymous namespace)::B']}])

    def test_creation_and_other_factory_types_excluded(self):
        self.assertEqual(expected_factories(
            'SimpleNetworkObjectFactoryClass<A, 2>::Create() const\n'
            'SimpleDefinitionFactoryClass<A, 2, &Name>::Get_Class_ID() const'), [])

    def test_class_names_are_data_not_debugger_expressions(self):
        script = debugger_script([{'class_id': 1, 'classes': ['"malicious; text"']}])
        compile(script, '<registry-probe>', 'exec')
        self.assertNotIn('Create(', script)
        self.assertIn('>= 4096', script)


if __name__ == '__main__':
    unittest.main()
