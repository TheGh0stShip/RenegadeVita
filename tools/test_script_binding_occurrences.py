import json
from pathlib import Path
import tempfile
import unittest
from tools.audit_script_binding_occurrences import inventory, summarize


class BindingOccurrenceTests(unittest.TestCase):
    def test_counts_without_publishing_parameters(self):
        value = {'map': 'm09.mix', 'archive_sha256': 'a', 'objects_ddb_sha256': 'b',
                 'bindings': [{'name': 'M09_Camera_Activate', 'binding_kind': 'persisted_script',
                               'parameters': 'private', 'parameter_fields': [{}] * 5}]}
        result = summarize(value, {'map': 'm09.mix', 'archive_sha256': 'a'}, 'm09_camera_activate')
        self.assertEqual(result['binding_count'], 1)
        self.assertEqual(result['parameter_field_counts'], {'5': 1})
        self.assertNotIn('private', json.dumps(result))
        value['archive_sha256'] = 'wrong'
        with self.assertRaises(ValueError):
            summarize(value, {'map': 'm09.mix', 'archive_sha256': 'a'}, 'm09_camera_activate')

    def test_rejects_incomplete_denominator(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, 'Incomplete'):
                inventory(Path(directory), {'rows': [{'map': 'm09.mix'}]}, 'camera')

    def test_retains_zero_match_map(self):
        with tempfile.TemporaryDirectory() as directory:
            value = {'map': 'm01.mix', 'archive_sha256': 'a', 'objects_ddb_sha256': 'b', 'bindings': []}
            Path(directory, 'm01-bindings.json').write_text(json.dumps(value))
            result = inventory(Path(directory), {'rows': [{'map': 'm01.mix', 'archive_sha256': 'a'}]}, 'camera')
            self.assertEqual(result['total'], 1)
            self.assertEqual(result['binding_count'], 0)
            self.assertEqual(result['counts'], {'unknown': 1})
