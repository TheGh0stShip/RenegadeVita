import importlib.util
from pathlib import Path
import tempfile
import unittest

from audit_sweep_renderer import audit, ancestry, feature_expectations, state_references, state_reviews, state_symbols, syntax
from sweep_cpp_functions import parser

PARSER_AVAILABLE = bool(importlib.util.find_spec('tree_sitter') and
                        importlib.util.find_spec('tree_sitter_cpp'))


class RendererInventoryTest(unittest.TestCase):
    def test_light_types_and_material_color_sources_are_value_domains(self):
        rows = state_symbols([dict(r, kind='draw_state_reference', file='light.inc')
                              for r in state_references(
                                  'D3DLIGHT_DIRECTIONAL; D3DLIGHT_POINT; D3DLIGHT_SPOT; '
                                  'D3DMCS_MATERIAL; D3DMCS_COLOR1; D3DMCS_COLOR2; '
                                  '"D3DLIGHT_POINT"; // D3DMCS_COLOR1')])
        self.assertEqual(len(rows), 6)
        self.assertTrue(all(r['symbol_role'] == 'value_or_layout_token' for r in rows))

    @unittest.skipUnless(PARSER_AVAILABLE, 'Pinned sweep parser not installed')
    def test_include_fragments_and_cpp_variants_are_inventory_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ('audit_sweep_renderer.py', 'sweep_cpp_functions.py',
                         'audit_sweep_port_guards.py', 'sweep-parser-requirements.txt'):
                path = root / 'tools' / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('fixture')
            source = root / 'port/renderer'
            source.mkdir(parents=True)
            for suffix in ('.inc', '.ipp', '.cc', '.cxx', '.hh', '.hxx', '.CC'):
                (source / ('fragment' + suffix)).write_text(
                    'class Fragment: public RenderObjClass {}; D3DRS_AMBIENT;')
            (source / 'notes.txt').write_text('D3DRS_ZBIAS;')
            upstream = root / 'upstream/CnC_Renegade/Code/ww3d2'
            upstream.mkdir(parents=True)
            (upstream / 'missing.inc').write_text('D3DRS_LIGHTING;')
            result = audit(root)
            fragments = [r for r in result['rows'] if r['kind'] == 'class_definition']
            self.assertEqual(len(fragments), 7)
            self.assertTrue(all('render_object' in r['candidate_roles'] for r in fragments))
            ambient = next(r for r in result['rows'] if r.get('symbol') == 'D3DRS_AMBIENT'
                           and r['kind'] == 'draw_state_symbol')
            self.assertEqual(len(ambient['references']), 7)
            self.assertFalse(any(r.get('symbol') == 'D3DRS_ZBIAS' for r in result['rows']))
            self.assertEqual(result['upstream_files_missing_from_staging'], ['missing.inc'])
            self.assertEqual(sum(k.startswith('port/renderer/') for k in result['inputs_sha256']), 7)

    def test_original_compound_vertex_layout_names_are_discovered(self):
        self.assertEqual([r['symbol'] for r in state_references(
            'DX8_FVF_XYZNDUV1; DX8_FVF_XYZUV2; "DX8_FVF_XYZ";')],
            ['DX8_FVF_XYZNDUV1', 'DX8_FVF_XYZUV2'])

    def test_engine_format_names_are_retained_with_directx_names(self):
        refs = state_references('WW3D_FORMAT_U8V8; D3DFMT_U8V8; '
                                '"WW3D_FORMAT_DXT1"; // WW3D_FORMAT_COUNT')
        self.assertEqual([r['symbol'] for r in refs],
                         ['WW3D_FORMAT_U8V8', 'D3DFMT_U8V8'])

    def test_coordinate_generation_values_are_not_state_selectors(self):
        rows = state_symbols([dict(r, kind='draw_state_reference', file='a.cpp')
                              for r in state_references(
                                  'D3DTSS_TEXCOORDINDEX; D3DTSS_TCI_PASSTHRU;')])
        roles = {r['symbol']: r['symbol_role'] for r in rows}
        self.assertEqual(roles['D3DTSS_TEXCOORDINDEX'], 'state_selector')
        self.assertEqual(roles['D3DTSS_TCI_PASSTHRU'], 'value_or_layout_token')

    def test_value_domains_and_modifiers_are_retained(self):
        text = ('D3DTOP_BUMPENVMAP; D3DTA_COMPLEMENT | D3DTA_TEXTURE; '
                'D3DTTFF_PROJECTED; D3DTADDRESS_MIRROR; D3DTEXF_ANISOTROPIC; '
                'D3DBLEND_SRCALPHA; D3DCMP_LESS; D3DSTENCILOP_KEEP; '
                '"D3DTOP_ADD"; /* D3DTA_DIFFUSE */')
        symbols = [r['symbol'] for r in state_references(text)]
        self.assertEqual(symbols, ['D3DTOP_BUMPENVMAP', 'D3DTA_COMPLEMENT',
                                  'D3DTA_TEXTURE', 'D3DTTFF_PROJECTED',
                                  'D3DTADDRESS_MIRROR', 'D3DTEXF_ANISOTROPIC',
                                  'D3DBLEND_SRCALPHA', 'D3DCMP_LESS',
                                  'D3DSTENCILOP_KEEP'])

    def test_duplicate_reviews_cannot_overwrite_classification(self):
        rows = state_symbols([dict(r, kind='draw_state_reference', file='a.cpp')
                              for r in state_references('D3DTSS_ADDRESSW;')])
        review = {'symbol': 'D3DTSS_ADDRESSW', 'status': 'missing',
                  'native_mapping': 'missing', 'inputs_sha256': {'a.cpp': 'hash'}}
        conflicting = dict(review, status='boundary_replaced')
        issues = state_reviews(rows, [review, conflicting], {'a.cpp': 'hash'})
        self.assertEqual(len(issues), 2)
        self.assertEqual(rows[0]['status'], 'unknown')

    def test_state_aggregation_and_stale_review(self):
        refs = [dict(r, kind='draw_state_reference', file='a.cpp')
                for r in state_references('D3DRS_ZBIAS; D3DRS_ZBIAS;')]
        rows = state_symbols(refs)
        self.assertEqual(len(rows), 1)
        self.assertEqual(len(rows[0]['references']), 2)
        review = {'symbol': 'D3DRS_ZBIAS', 'status': 'missing', 'native_mapping': 'missing',
                  'inputs_sha256': {'a.cpp': 'old'}}
        self.assertEqual(len(state_reviews(rows, [review], {'a.cpp': 'changed'})), 1)
        self.assertEqual(rows[0]['status'], 'unknown')
        self.assertEqual(state_reviews(rows, [review], {'a.cpp': 'old'}), [])
        self.assertEqual(rows[0]['status'], 'missing')

    def test_helper_and_absent_owner_are_never_silently_excluded(self):
        rows = feature_expectations([{'name': 'SkinDecalMeshClass', 'file': 'a.h', 'line': 2}])
        decal = next(r for r in rows if r['feature'] == 'skinned_decal')
        streak = next(r for r in rows if r['feature'] == 'streak')
        self.assertEqual(decal['candidate_definitions'][0]['line'], 2)
        self.assertEqual(streak['candidate_definitions'], [])
        self.assertEqual(streak['status'], 'unknown')
        self.assertEqual(len({r['feature'] for r in rows}), len(rows))

    @unittest.skipUnless(PARSER_AVAILABLE, 'Pinned sweep parser not installed')
    def test_transitive_and_multiple_inheritance_retained(self):
        text = ('class RenderObjClass {}; class Animated: public RenderObjClass {};'
                'class HLOD: public Animated, public Other {}; class Forward;')
        classes, errors = syntax(text, parser())
        self.assertEqual(errors, [])
        ancestry(classes)
        self.assertEqual([r['name'] for r in classes], ['RenderObjClass', 'Animated', 'HLOD'])
        self.assertEqual(classes[-1]['bases'], ['Animated', 'Other'])
        self.assertIn('render_object', classes[-1]['candidate_roles'])

    def test_cycles_do_not_hide_loader(self):
        rows = [{'name': 'A', 'bases': ['B']}, {'name': 'B', 'bases': ['A', 'PrototypeLoaderClass']}]
        ancestry(rows)
        self.assertIn('prototype_loader', rows[0]['candidate_roles'])

    @unittest.skipUnless(PARSER_AVAILABLE, 'Pinned sweep parser not installed')
    def test_scopes_templates_and_parse_uncertainty_retained(self):
        classes, _ = syntax('namespace X { struct A: Base<int> {}; }', parser())
        self.assertEqual(classes[0]['scope'], 'X')
        self.assertEqual(classes[0]['bases'], ['Base<int>'])
        _, errors = syntax('class Broken { int f( }', parser())
        self.assertTrue(errors)

    def test_literals_and_comments_are_not_state_references(self):
        text = '// D3DRS_ZBIAS\n"D3DFMT_A8"; D3DRS_ZBIAS; D3DTSS_COLOROP; D3DFVF_XYZ;'
        refs = state_references(text)
        self.assertEqual([r['symbol'] for r in refs], ['D3DRS_ZBIAS', 'D3DTSS_COLOROP', 'D3DFVF_XYZ'])
        self.assertEqual(refs[0]['line'], 2)
        self.assertGreater(refs[0]['column'], 1)


if __name__ == '__main__':
    unittest.main()
