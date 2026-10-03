"""Source-only dazzle lifecycle replay; no compiler or renderer execution."""
from pathlib import Path
import hashlib
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PATCH = ROOT / 'port/patches/ww3d-a35-original-dazzle-lifecycle.patch'


class OriginalDazzleLifecycle(unittest.TestCase):
    def test_anchored_replay_and_native_original_visibility_body(self):
        hashes = {'dazzle.cpp': '2bbcba91d75327b7fa35b4c1f50718ab05d3b252a687a78d0b3c62a90dfefd58',
                  'ww3d.cpp': '32fdca663f7bfffede2b64b1fbafcc1bd0af81b15f46e4dc24aef84e59bd55c6'}
        with tempfile.TemporaryDirectory() as directory:
            for name in hashes:
                Path(directory, name).write_bytes((ROOT / 'staging/ww3d2' / name).read_bytes())
            args = ['patch', '--batch', '--fuzz=0', '--no-backup-if-mismatch', '-p1', '-d', directory]
            if 'Headless host validation has no native dazzle framebuffer' in Path(directory, 'dazzle.cpp').read_text():
                subprocess.run(args + ['--reverse'], input=PATCH.read_bytes(), capture_output=True, check=True)
            for name, digest in hashes.items():
                self.assertEqual(hashlib.sha256(Path(directory, name).read_bytes()).hexdigest(), digest)
            result = subprocess.run(args + ['--forward'], input=PATCH.read_bytes(), capture_output=True, check=True)
            self.assertNotIn(b'offset', result.stdout)
            dazzle = Path(directory, 'dazzle.cpp').read_text()
            ww3d = Path(directory, 'ww3d.cpp').read_text()
        body = dazzle.split('void DazzleRenderObjClass::Render(RenderInfoClass & rinfo)', 1)[1].split(
            'void DazzleRenderObjClass::Render_Dazzle', 1)[0]
        original = (ROOT / 'upstream/CnC_Renegade/Code/ww3d2/dazzle.cpp').read_text()
        reference = original.split('void DazzleRenderObjClass::Render(RenderInfoClass & rinfo)', 1)[1].split(
            'void DazzleRenderObjClass::Render_Dazzle', 1)[0]
        # Native branch is the unchanged original body, not a new effect.
        restored = '{\n' + body.split('#else\n', 1)[1].replace('\n#endif\n}', '\n}', 1)
        self.assertEqual(restored.strip('\n'), reference.strip('\n'))
        self.assertIn('#if defined(RENEGADE_VITA_PORT) && !defined(__vita__)', body)
        init = ww3d.split('WW3DErrorType WW3D::Init(', 1)[1].split('#else', 1)[0]
        self.assertLess(init.index('VertexMaterialClass::Init();'), init.index('DazzleRenderObjClass::Init_From_INI'))
        self.assertLess(init.index('DazzleRenderObjClass::Init_From_INI'), init.index('IsInitted = true;'))
        shutdown = ww3d.split('WW3DErrorType WW3D::Shutdown(', 1)[1].split('#else', 1)[0]
        self.assertLess(shutdown.index('DazzleRenderObjClass::Deinit();'), shutdown.index('Free_Assets();'))

    def test_interactive_full_init_and_original_layer_owners(self):
        runtime = (ROOT / 'port/platform/vita/a31_vita_runtime.cpp').read_text()
        self.assertIn('WW3D::Init(NULL, NULL, false)', runtime)
        combat = (ROOT / 'staging/combat/combat.cpp').read_text()
        self.assertIn('DazzleLayer = new DazzleLayerClass;', combat)
        self.assertIn('dlayer->Render(COMBAT_CAMERA);', combat)
        render = combat.split('void CombatManager::Render()', 1)[1]
        self.assertLess(render.index('WW3D::Render(COMBAT_SCENE'), render.index('dlayer->Render(COMBAT_CAMERA)'))
        self.assertLess(render.index('dlayer->Render(COMBAT_CAMERA)'), render.index('HUDClass::Render()'))
