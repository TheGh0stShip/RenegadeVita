import unittest

from probe_host_definition_registry import expected_definitions


class DefinitionSymbolsTests(unittest.TestCase):
    def test_deduplicates_and_keeps_distinct_class_ids(self):
        symbols = '\n'.join([
            'a W SimpleDefinitionFactoryClass<A, 123, &AName>::Get_Class_ID() const',
            'b W SimpleDefinitionFactoryClass<A, 123, &AName>::Get_Class_ID() const',
            'c W SimpleDefinitionFactoryClass<B, 123, &BName>::Get_Class_ID() const',
            'd W SimpleDefinitionFactoryClass<C, -1, &CName>::Get_Class_ID() const',
            'e W SimplePersistFactoryClass<Other, 4>::Chunk_ID() const'])
        self.assertEqual(expected_definitions(symbols), [
            {'class_id': 123, 'classes': ['A', 'B']},
            {'class_id': 4294967295, 'classes': ['C']}])

    def test_other_methods_do_not_define_denominator(self):
        self.assertEqual(expected_definitions(
            'SimpleDefinitionFactoryClass<A, 1, &Name>::Create() const'), [])


if __name__ == '__main__':
    unittest.main()
