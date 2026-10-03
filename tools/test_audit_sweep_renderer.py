import importlib.util
import unittest

from audit_sweep_renderer import ancestry, feature_expectations, state_references, state_reviews, state_symbols, syntax
from sweep_cpp_functions import parser

PARSER_AVAILABLE = bool(importlib.util.find_spec('tree_sitter') and
                        importlib.util.find_spec('tree_sitter_cpp'))


class RendererInventoryTest(unittest.TestCase):
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
