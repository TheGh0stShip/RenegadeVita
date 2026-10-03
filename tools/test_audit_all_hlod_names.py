import unittest
from tools.audit_all_hlod_names import reconcile


class HlodNameResolutionTest(unittest.TestCase):
    def test_internal_names_casefold_duplicates_and_builtin(self):
        members=[{'archive':'always.dat','member':'different_filename.w3d','index_record':0,'sha256':'a',
                  'declarations':[{'name':'RIG.BODY'}]},
                 {'archive':'always.dat','member':'other.w3d','index_record':1,'sha256':'b',
                  'declarations':[{'name':'rig.body'}]},
                 {'archive':'M11.mix','member':'rig.w3d','index_record':0,'sha256':'c',
                  'hlods':[{'name':'RIG','arrays':[{'kind':'lod','objects':[
                      {'name':'Rig.Body','bone_index':1},{'name':'NULL','bone_index':0},
                      {'name':'missing.child','bone_index':2}]}]}]}]
        row=next(r for r in reconcile(members) if r['archive']=='M11.mix')
        self.assertEqual(row['header_candidate_matches'],1)
        self.assertEqual(row['ambiguous_provider_occurrences'],1)
        self.assertEqual(row['only_other_archive_candidates'],1)
        self.assertEqual(row['builtin_null_names'],1)
        self.assertEqual(row['unresolved_occurrences'],1)
        self.assertEqual(row['child_occurrences'],sum(row[k] for k in
            ('header_candidate_matches','builtin_null_names','unresolved_occurrences')))
