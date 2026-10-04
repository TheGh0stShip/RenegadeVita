import json
import hashlib
import unittest
from tools.consolidate_sweep_gaps import consolidate


class ConsolidationTest(unittest.TestCase):
    def test_script_parameter_categories_partition(self):
        receipt={'total':1,'counts':{'unknown':1},'bindings':2,
                 'categories':{'equal_count':1,'excess_values':1},
                 'rows':[{'status':'unknown','bindings':2,
                          'categories':{'equal_count':1,'excess_values':1},'leads':[{}]}]}
        result=consolidate([('live_script_parameters',json.dumps(receipt).encode())])
        self.assertEqual(result['rows'][0]['cluster'],'scripts')
        receipt['rows'][0]['leads']=[]
        with self.assertRaisesRegex(ValueError,'partition'):
            consolidate([('live_script_parameters',json.dumps(receipt).encode())])

    def test_prototype_registry_duplicate_chunks_rejected(self):
        receipt={'total':1,'matched':1,'rows':[{'chunk_id':0,'lookup_matches':True,'status':'unknown'}]}
        result=consolidate([('host_prototype_registry',json.dumps(receipt).encode())])
        self.assertEqual(result['rows'][0]['cluster'],'link')
        receipt['rows'].append(receipt['rows'][0].copy())
        receipt.update(total=2,matched=2)
        with self.assertRaisesRegex(ValueError,'partition'):
            consolidate([('host_prototype_registry',json.dumps(receipt).encode())])

    def test_network_custom_factory_partition_and_cluster(self):
        receipt={'total':1,'matched':1,'rows':[{'class_id':1,'matches':True,'status':'unknown'}],
                 'live_ids':[1,2],'live_factory_count':2,'live_non_template_ids':[2]}
        result=consolidate([('host_network_registry',json.dumps(receipt).encode())])
        self.assertEqual(result['rows'][0]['cluster'],'link')
        receipt['live_non_template_ids']=[]
        with self.assertRaisesRegex(ValueError,'partition'):
            consolidate([('host_network_registry',json.dumps(receipt).encode())])

    def test_live_script_registry_and_binding_partitions(self):
        registry={'total':1,'counts':{'unknown':1},'registry_count':1,
                  'registry_entries':[{'name':'A'}], 'matched_candidates':1,
                  'unmatched_candidates':0,'rows':[{'status':'unknown','name_matches':True,'found':True}]}
        data=json.dumps(registry).encode()
        bindings={'total':1,'counts':{'unknown':1},'registry_sha256':hashlib.sha256(data).hexdigest(),
                  'totals':{'bindings':2,'registered_bindings':1,'unregistered_bindings':1},
                  'rows':[{'map':'M11.mix','status':'unknown','bindings':2,
                           'registered_bindings':1,'unregistered_bindings':1,'missing':[{'name':'B'}]}]}
        result=consolidate([('host_script_registry',data),('live_script_bindings',json.dumps(bindings).encode())])
        self.assertEqual(result['total'],2)
        self.assertEqual({r['cluster'] for r in result['rows']},{'link','scripts'})
        bindings['rows'][0]['unregistered_bindings']=0
        with self.assertRaisesRegex(ValueError,'partition'):
            consolidate([('live_script_bindings',json.dumps(bindings).encode())])

    def test_missing_caller_maps_and_parent_identity(self):
        parent={'total':0,'counts':{},'rows':[]}
        data=json.dumps(parent).encode()
        child={'total':1,'counts':{'unknown':1},'rows':[{
            'status':'unknown','affected_maps':['M01.mix','M02.mix']}],
            'inventory_sha256':hashlib.sha256(data).hexdigest()}
        result=consolidate([('definition_instances',data),
                            ('missing_definition_callers',json.dumps(child).encode())])
        self.assertEqual(result['rows'][0]['affected_missions_modes'],['M01.mix','M02.mix'])
        child['inventory_sha256']='stale'
        with self.assertRaisesRegex(ValueError,'stale parent'):
            consolidate([('definition_instances',data),
                         ('missing_definition_callers',json.dumps(child).encode())])

    def test_definition_reference_edge_partition(self):
        value={'total':1,'counts':{'unknown':1},'rows':[{
            'map':'M01.mix','status':'unknown','typed_reference_fields':2,
            'edge_counts':{'absent_target':1,'present_target':1}}]}
        result=consolidate([('definition_instances',json.dumps(value).encode())])
        self.assertEqual(result['total'],1)
        value['rows'][0]['typed_reference_fields']=3
        with self.assertRaisesRegex(ValueError,'edge partition'):
            consolidate([('definition_instances',json.dumps(value).encode())])

    def test_definition_closure_partition_and_registry_parent(self):
        host={'total':1,'matched':1,'rows':[{'status':'unknown','matches':True}]}
        data=json.dumps(host).encode()
        child={'rows':[{'status':'unknown','definition_class_ids':[99],
                        'class_id_mapping_ambiguous':False}],
               'totals':{'persistence_ids':1,'mapped':1,'unmapped':0,'ambiguous':0},
               'inputs':[{'source':'reports/generated/sweeps/host_definition_registry.json',
                          'sha256':hashlib.sha256(data).hexdigest()}]}
        result=consolidate([('host_definition_registry',data),
                            ('database_definition_closure',json.dumps(child).encode())])
        self.assertEqual(result['total'],2)
        self.assertTrue(all(r['cluster']=='link' for r in result['rows']))
        child['inputs'][0]['sha256']='stale'
        with self.assertRaisesRegex(ValueError,'stale registry'):
            consolidate([('host_definition_registry',data),
                         ('database_definition_closure',json.dumps(child).encode())])

    def test_fvf_renderer_cluster_and_partition(self):
        value={'total':2,'counts':{'missing':1,'unknown':1},'admitted_layouts':1,
               'unsupported_layouts':1,'rows':[
               {'status':'missing','native_layout_admitted':False,'name':'FVF 002'},
               {'status':'unknown','native_layout_admitted':True,'name':'FVF 152'}]}
        result=consolidate([('procedural_fvf_layouts',json.dumps(value).encode())])
        self.assertTrue(all(r['cluster']=='renderer' for r in result['rows']))
        self.assertEqual(result['rows'][0]['severity'],'visual')
        value['admitted_layouts']=2
        with self.assertRaisesRegex(ValueError,'partition'):
            consolidate([('procedural_fvf_layouts',json.dumps(value).encode())])

    def test_decode_results_reconcile_and_reject_bad_partition(self):
        row={'archive':'M01.mix','status':'unknown','wave_members':2,
             'decoded_members':1,'rejected_members':1,'failures':[{'member':'bad.wav'}]}
        value={'total':1,'counts':{'unknown':1},'rows':[row],
               'totals':{k:row[k] for k in ('wave_members','decoded_members','rejected_members')}}
        result=consolidate([('wave_decode',json.dumps(value).encode())])
        self.assertEqual(result['total'],1)
        row['decoded_members']=0
        value['totals']['decoded_members']=0
        with self.assertRaisesRegex(ValueError,'partition'):
            consolidate([('wave_decode',json.dumps(value).encode())])

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
