import unittest

from probe_host_persist_registry import expected_factories


class RegistrySymbolTests(unittest.TestCase):
    def test_ids_classes_and_duplicate_symbols(self):
        text = '\n'.join([
            'a W SimplePersistFactoryClass<One, 42>::Chunk_ID() const',
            'b W SimplePersistFactoryClass<One, 42>::Chunk_ID() const',
            'c W SimplePersistFactoryClass<Two, 42>::Chunk_ID() const',
            'd W SimplePersistFactoryClass<Other, 7>::Load(ChunkLoadClass&) const',
            'e W SimplePersistFactoryClass<Last, -1>::Chunk_ID() const'])
        self.assertEqual(expected_factories(text), [
            {'chunk_id': 42, 'classes': ['One', 'Two']},
            {'chunk_id': 4294967295, 'classes': ['Last']}])

    def test_empty_denominator(self):
        self.assertEqual(expected_factories('unrelated symbols'), [])


if __name__ == '__main__':
    unittest.main()
