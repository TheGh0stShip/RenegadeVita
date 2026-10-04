import unittest

from tools.audit_missing_definition_callers import body, references


class CallerReviewTests(unittest.TestCase):
    def test_body_ignores_literal_and_comment_braces(self):
        source = 'void A::Call() { const char *s = "}"; /* { */ if (x) { y(); } }'
        extracted, line = body(source, 'A::Call')
        self.assertEqual(extracted, source[source.index('{'):])
        self.assertEqual(line, 1)

    def test_overload_needs_explicit_selector(self):
        source = 'void A::Call(int x) {} void A::Call(const char *x) {}'
        with self.assertRaises(ValueError):
            body(source, 'A::Call')
        self.assertEqual(body(source, 'A::Call', 'int')[0], '{}')

    def test_unknown_fields_and_map_denominator_retained(self):
        inventory = {'rows': [{}, {'map': 'M01.mix', 'unresolved_field_provenance': [
            {'kind': 'unknown_field', 'id': 12, 'owner_definition_id': 8}]},
            {'map': 'M02.mix', 'unresolved_field_provenance': [
            {'kind': 'unknown_field', 'id': 12, 'owner_definition_id': 9}]}]}
        row = references(inventory, {})[0]
        self.assertEqual(row['affected_maps'], ['M01.mix', 'M02.mix'])
        self.assertIsNone(row['caller_review'])
        self.assertFalse(row['reviewed_bodies_match_upstream'])
        self.assertEqual(row['status'], 'unknown')

    def test_changed_owner_cannot_claim_original_body(self):
        inventory={'rows':[{}, {'map':'M01.mix','unresolved_field_provenance': [{
            'kind':'typed_field','field_name':'MICROCHUNKID_WEAPON_DEF_EJECT_PHYS_DEF_ID',
            'id':12,'owner_definition_id':8}]}]}
        owners={key:{'matches_upstream':True} for key in ('eject','muzzle','lookup')}
        self.assertTrue(references(inventory,owners)[0]['reviewed_bodies_match_upstream'])
        owners['eject']['matches_upstream']=False
        self.assertFalse(references(inventory,owners)[0]['reviewed_bodies_match_upstream'])


if __name__ == '__main__':
    unittest.main()
