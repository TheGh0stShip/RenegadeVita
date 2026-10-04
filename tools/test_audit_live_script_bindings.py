import unittest

from tools.audit_live_script_bindings import compare


class LiveBindingTests(unittest.TestCase):
    def setUp(self):
        self.binding={'map':'M11.mix','archive_sha256':'a','objects_ddb_sha256':'b',
                      'bindings':[{'name':'Script_A','binding_kind':'persisted_script'},
                                  {'name':'Missing','binding_kind':'spawner_script','spawner_id':42}]}
        self.registry={'registry_entries':[{'name':'script_a'}]}
        self.expected={'archive_sha256':'a','objects_ddb_sha256':'b'}

    def test_case_insensitive_membership_and_missing_provenance(self):
        row=compare(self.binding,self.registry,self.expected)
        self.assertEqual(row['registered_bindings'],1)
        self.assertEqual(row['missing'][0]['spawner_id'],42)
        self.assertEqual(row['status'],'unknown')

    def test_stale_data_identity_rejected(self):
        for key in self.expected:
            expected={**self.expected,key:'stale'}
            with self.assertRaises(ValueError):
                compare(self.binding,self.registry,expected)


if __name__ == '__main__':
    unittest.main()
