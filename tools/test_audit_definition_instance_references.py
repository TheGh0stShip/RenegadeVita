import unittest

from tools.audit_definition_instance_references import graph


def definition(factory, targets):
    return {'factory': factory, 'definition_references': targets,
            'definition_reference_provenance': [{'id': target, 'field_id': i, 'offset': i * 4}
                                               for i, target in enumerate(targets)]}


class InstanceGraphTests(unittest.TestCase):
    def test_cycles_missing_and_zero(self):
        defs = {1: definition('0x00040000', [2, 0]),
                2: definition('0x00040001', [1, 99])}
        result = graph(defs, [1])
        self.assertEqual(result['reached_definitions'], 2)
        self.assertEqual(result['missing_ids'], [99])
        self.assertEqual(result['typed_reference_fields'], 3)
        self.assertEqual(result['edge_counts']['absent_target'], 1)

    def test_global_and_rooted_graphs_differ(self):
        defs = {1: definition('0x00040000', []), 2: definition('0x00040001', [99])}
        self.assertEqual(graph(defs, [1])['missing_ids'], [])
        self.assertEqual(graph(defs)['missing_ids'], [99])

    def test_editor_target_is_distinct_from_absent(self):
        defs = {1: definition('0x00040000', [2]), 2: definition('0x00050000', [])}
        self.assertEqual(graph(defs, [1])['edge_counts'], {'editor_target': 1})

    def test_missing_root_retained_without_fabricated_edge(self):
        result = graph({}, [123])
        self.assertEqual(result['missing_ids'], [123])
        self.assertEqual(result['typed_reference_fields'], 0)


if __name__ == '__main__':
    unittest.main()
