import importlib.util
import unittest

from audit_sweep_renderer import ancestry, state_references, syntax
from sweep_cpp_functions import parser

PARSER_AVAILABLE = bool(importlib.util.find_spec('tree_sitter') and
                        importlib.util.find_spec('tree_sitter_cpp'))


class RendererInventoryTest(unittest.TestCase):
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
