import json
import hashlib
import unittest
from tools.consolidate_sweep_gaps import consolidate


class ConsolidationTest(unittest.TestCase):
    def test_wave_partitions_and_nested_findings(self):
        row={'archive':'M03.mix','status':'unknown','wave_members':2,
             'formats':[{'format':None,'members':2}], 'header_finding_members':1,
             'block_finding_members':0,'findings':[{'member':'voice.wav','status':'unknown',
             'header_findings':['riff_length_outside_source'],'block_findings':[]}]}
        value={'total':1,'counts':{'unknown':1},'rows':[row],
               'totals':{k:row[k] for k in ('wave_members','header_finding_members','block_finding_members')}}
        result=consolidate([('wave_headers',json.dumps(value).encode())])
        self.assertEqual(result['total'],2)
        self.assertTrue(all(r['affected_missions_modes']==['M03.mix'] for r in result['rows']))
        row['formats'][0]['members']=1
        with self.assertRaisesRegex(ValueError,'format partition'):
            consolidate([('wave_headers',json.dumps(value).encode())])

    def test_supplement_nested_records_and_parent_identity(self):
        parent={'rows':[{'map':'M11.mix','status':'unknown','members':[
            {'status':'unknown','chunk_paths':[{'status':'unknown','chunk_path':['0x1']}]}]}],
            'totals':{'maps':1,'members':1}}
        data=json.dumps(parent).encode()
        child={'rows':[{'map':'M11.mix','status':'unknown','acceptance_open':'runtime culling'}],
               'chunk_inventory_sha256':hashlib.sha256(data).hexdigest(),'limits':['partial']}
        result=consolidate([('level_chunks',data),('spatial_presence',json.dumps(child).encode())])
        self.assertEqual(result['total'],4)
        self.assertTrue(all(r['cluster']=='retail' for r in result['rows']))
        self.assertEqual(result['inputs'][1]['coverage_risks'],['partial'])
        self.assertEqual(result['rows'][-1]['acceptance_open'],'runtime culling')
        child['chunk_inventory_sha256']='stale'
        with self.assertRaises(ValueError):
            consolidate([('level_chunks',data),('spatial_presence',json.dumps(child).encode())])

    def test_supplement_denominator_mismatch(self):
        value={'rows':[],'totals':{'maps':1,'members':0}}
        with self.assertRaises(ValueError):
            consolidate([('level_chunks',json.dumps(value).encode())])
    def test_review_is_provenance_and_conflicts_fail(self):
        data = {'total': 1, 'counts': {'missing': 1}, 'rows': [
            {'status': 'missing', 'symbol': 'D3DRS_ZBIAS', 'review': {
                'status': 'missing', 'original_owner': 'DX8Wrapper',
                'affected_scope': ['decals'], 'acceptance_open': 'native depth check'}}]}
        result = consolidate([('renderer', json.dumps(data).encode())])
        self.assertEqual(result['total'], 1)
        self.assertEqual(result['rows'][0]['original_owner'], 'DX8Wrapper')
        self.assertEqual(result['rows'][0]['review_evidence_pointer'], '/rows/0/review')
        data['rows'][0]['review']['status'] = 'unknown'
        with self.assertRaises(ValueError):
            consolidate([('renderer', json.dumps(data).encode())])

    def test_nested_unknown_and_original_filter(self):
        data = {'total': 2, 'counts': {'unknown': 1, 'original_compiled': 1},
                'rows': [{'status': 'unknown', 'map': 'M09',
                          'nested': [{'status': 'missing', 'name': 'factory'}]},
                         {'status': 'original_compiled'}]}
        result = consolidate([('retail', json.dumps(data).encode())])
        self.assertEqual(result['total'], 2)
        self.assertEqual(result['rows'][0]['inventory_pointer'], '/rows/0/nested/0')
        self.assertEqual(result['rows'][0]['affected_missions_modes'], ['M09'])
        self.assertEqual(result['rows'][1]['severity'], 'unclassified')

    def test_denominator_and_status_mismatch_fail(self):
        for data in ({'total': 2, 'rows': [], 'counts': {}},
                     {'total': 1, 'rows': [{'status': 'unknown'}], 'counts': {'missing': 1}}):
            with self.assertRaises(ValueError):
                consolidate([('scripts', json.dumps(data).encode())])
