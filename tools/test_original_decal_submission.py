"""Source-only temporary patch replay; does not compile or execute renderer."""
from pathlib import Path
import hashlib
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class OriginalDecalSubmission(unittest.TestCase):
    def test_anchored_connected_replay(self):
        anchors = {'ww3d.cpp': 'a6880363b1bcf43e65d69ace09b3f29248da5483c9d80258ddbad630066ebeb3',
                   'decalmsh.cpp': 'a235a5a53c279f59d92099b1efb7ccaa039ba83cec176b9162ede5c7e1d64d4b',
                   'mesh.cpp': '628232c017e9ffe25ec68d4732e133b31f13094c2653322c95a5e06319d137ca'}
        with tempfile.TemporaryDirectory() as directory:
            for name in (*anchors, 'dazzle.cpp'):
                Path(directory, name).write_bytes((ROOT / 'staging/ww3d2' / name).read_bytes())
            args = ['patch', '--batch', '--forward', '--fuzz=0', '--no-backup-if-mismatch', '-p1', '-d', directory]
            for patch in ('ww3d-a35-original-dazzle-lifecycle.patch', 'ww3d-a35-original-decal-submission.patch'):
                if 'decal-submission' in patch:
                    for name, digest in anchors.items():
                        self.assertEqual(hashlib.sha256(Path(directory, name).read_bytes()).hexdigest(), digest)
                result = subprocess.run(args, input=(ROOT / 'port/patches' / patch).read_bytes(), capture_output=True, check=True)
                self.assertNotIn(b'offset', result.stdout)
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
