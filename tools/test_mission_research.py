import unittest

from tools.audit_mission_research import ASSETS, CAVEATS, PERFORMANCE, RECOMMENDATIONS, SYSTEMS, owners, review


class MissionResearchReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = review()

    def test_all_research_sections_are_accounted_for_without_runtime_claim(self):
        self.assertEqual(len(self.result['systems']), 16)
        self.assertEqual(len(self.result['mission_sections']), 13)
        self.assertEqual({section['section'] for section in self.result['overview_sections']}, {
            'overview_architecture', 'campaign_asset_inventory', 'port_checklist', 'profile_priorities', 'gaps_caveats'})
        for section in self.result['overview_sections']:
            for item in section['review_items']:
                self.assertTrue(item['accounted_for_in_review_scope'])
                self.assertFalse(item['runtime_or_complete_content_verified'])
        self.assertFalse(self.result['runtime_or_physical_acceptance'])
        self.assertFalse(self.result['complete_mission_closure'])

    def test_supplied_checklist_asset_profile_caveat_items_remain_explicit(self):
        self.assertEqual((len(RECOMMENDATIONS), len(ASSETS), len(PERFORMANCE), len(CAVEATS)), (11, 10, 4, 9))
        self.assertEqual(set(SYSTEMS), {row['id'] for row in self.result['systems']})

    def test_case_aliases_and_wildcards_record_canonical_paths(self):
        result = owners(['wwphys/pathfind.cpp', 'ww3d2/*vertexbuffer*.cpp'],
                        {'WWPhys/Pathfind.cpp': None, 'ww3d2/dx8vertexbuffer.cpp': None})
        self.assertEqual(result[0]['canonical_source_paths'], ['WWPhys/Pathfind.cpp'])
        self.assertEqual(result[1]['canonical_source_paths'], ['ww3d2/dx8vertexbuffer.cpp'])

    def test_unlocated_owner_stays_open_instead_of_becoming_implemented(self):
        row = owners(['Combat/absent.cpp'], {})[0]
        self.assertEqual(row['status'], 'source_not_located')
        self.assertFalse(row['runtime_verified'])

    def test_all_nominated_original_system_owners_are_located(self):
        for row in self.result['systems']:
            for owner in row['owners']:
                self.assertEqual(owner['status'], 'source_located', owner['reference'])
                self.assertFalse(owner['runtime_verified'])

    def test_count_discrepancies_and_uncertified_media_are_retained(self):
        discrepancies = {row['command']: row for row in self.result['source_call_counts'] if row['status'] != 'matches'}
        self.assertEqual(discrepancies['Find_Object']['current_parser_count'], 3480)
        self.assertEqual(discrepancies['Send_Custom_Event']['current_parser_count'], 2994)
        self.assertEqual(self.result['uncertified_inventory_counts']['conversations'], 436)
        self.assertEqual(self.result['source_inventory']['static_original_dsp_source_count'], 44)
        self.assertNotIn('complete_asset_gate_passed', self.result)


if __name__ == '__main__':
    unittest.main()
