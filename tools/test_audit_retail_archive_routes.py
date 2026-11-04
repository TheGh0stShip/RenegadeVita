import unittest

from tools.audit_retail_archive_routes import analyze


def archive(name, entries):
    return {'name': name, 'entries': [dict(id=f'{name}:{i}', name=label, crc32=crc, size=4)
                                      for i, (label, crc) in enumerate(entries)]}


def catalogue(*rows):
    return {'archives': list(rows), 'campaign_flow': [{'kind': 'level', 'resource': 'M01.mix'}],
            'archive_set_sha256': 'fixture', 'discovery_issues': []}


class ArchiveRouteTests(unittest.TestCase):
    def test_cross_mission_resources_and_existing_supplement(self):
        result = analyze(catalogue(archive('Always.dat', [('shared', 1)]),
                         archive('M01.mix', [('local', 2)]),
                         archive('M08.mix', [('bag', 3)]),
                         archive('M02.mix', [('unknown_script.txt', 0xffffffff)])),
                         'restricted-before-fix')
        route = result['scenarios'][1]
        self.assertEqual(route['unreachable_archive_crc_count'], 1)
        self.assertEqual(route['unreachable_archive_resources'][0]['crc32'], 0xffffffff)
        self.assertFalse(result['play_test_ready'])

    def test_general_mount_policy_exposes_other_mission_without_content_pass(self):
        result = analyze(catalogue(archive('M01.mix', [('local', 2)]),
                                   archive('M02.mix', [('cross', 3)])))
        self.assertTrue(all(s['unreachable_archive_crc_count'] == 0 for s in result['scenarios']))
        self.assertFalse(result['content_inventory_complete'])
        self.assertFalse(result['play_test_ready'])

    def test_duplicate_provider_is_not_a_missing_resource_or_equivalence_claim(self):
        result = analyze(catalogue(archive('Always.dat', [('shared', 1)]),
                         archive('M02.mix', [('SHARED', 1), ('different_name', 1)])))
        self.assertEqual(result['scenarios'][0]['unreachable_archive_crc_count'], 0)
        group = result['duplicate_crc_provider_groups'][0]
        self.assertEqual(len(group['providers']), 3)
        self.assertTrue(group['names_differ'])
        self.assertEqual(group['payload_equivalence'], 'UNKNOWN')

    def test_top_level_enumeration_does_not_invent_nested_mounts(self):
        result = analyze(catalogue(archive('mods/extra.mix', [('nested', 4)])))
        self.assertEqual(result['original_archive_crc_count'], 0)
        self.assertEqual(result['excluded_nested_archives'], ['mods/extra.mix'])
        self.assertIn('m01.mix', result['scenarios'][1]['missing_route_archives'])

    def test_ambiguous_case_and_non32bit_keys_rejected(self):
        with self.assertRaises(ValueError):
            analyze(catalogue(archive('M01.mix', []), archive('m01.mix', [])))
        with self.assertRaises(ValueError):
            analyze(catalogue(archive('M01.mix', [('bad', 0x100000000)])))


if __name__ == '__main__':
    unittest.main()
