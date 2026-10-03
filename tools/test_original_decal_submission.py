"""Source-only temporary patch replay; does not compile or execute renderer."""
from pathlib import Path
import tempfile
import unittest
from tools.original_effect_source_replay import replay

ROOT = Path(__file__).resolve().parents[1]


class OriginalDecalSubmission(unittest.TestCase):
    def test_anchored_connected_replay(self):
        with tempfile.TemporaryDirectory() as directory:
            replay(directory)
            mesh = Path(directory, 'mesh.cpp').read_text()
            native = mesh.split('RenegadeVitaRenderer::Submit_Mesh(*this, rinfo);', 1)[1].split('#else', 1)[0]
            self.assertIn('RINFO_OVERRIDE_ADDITIONAL_PASSES_ONLY', native)
            self.assertIn('Get_Decal_Rejection_Distance()', native)
            self.assertIn('TheDX8MeshRenderer.Add_To_Render_List(DecalMesh)', native)
            ww3d = Path(directory, 'ww3d.cpp').read_text().split('void WW3D::Flush(RenderInfoClass & rinfo)', 1)[1]
            self.assertLess(ww3d.index('TheDX8MeshRenderer.Flush();'), ww3d.index('Render_And_Clear_Static_Sort_Lists'))
            decal = Path(directory, 'decalmsh.cpp').read_text()
            original = (ROOT / 'upstream/CnC_Renegade/Code/ww3d2/decalmsh.cpp').read_text()
            for kind in ('Rigid', 'Skin'):
                signature = f'void {kind}DecalMeshClass::Render(void)'
                body = decal.split(signature, 1)[1].split('/***********************************************************************************************', 1)[0]
                reference = original.split(signature, 1)[1].split('/***********************************************************************************************', 1)[0]
                restored = '{\n' + body.split('#else\n', 1)[1].replace('#endif\n}', '}', 1)
                self.assertEqual(restored.strip(), reference.strip())
                self.assertIn('&& !defined(__vita__)', body)

    def test_original_list_owner_and_reset(self):
        boundary = (ROOT / 'port/renderer/vita/ww3d_dx8_boundary.cpp').read_text()
        queue = boundary.split('void DX8MeshRendererClass::Add_To_Render_List', 1)[1].split('void DX8MeshRendererClass::Flush', 1)[0]
        for statement in ('Set_Next_Visible(visible_decal_meshes)', 'visible_decal_meshes = decalmesh',
                          'decal_mesh->Render()', 'Peek_Next_Visible()', 'visible_decal_meshes = NULL',
                          'D3DRS_ZBIAS, 8', 'D3DRS_ZBIAS, 0'):
            self.assertIn(statement, queue)
