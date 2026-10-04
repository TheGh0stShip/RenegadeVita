"""Execute production projective coordinates and validate pinned shader variants."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]


class ProjectiveCoordinatesTest(unittest.TestCase):
    def test_production_transform_and_interpolation(self):
        source=(ROOT/'port/renderer/vita/ww3d_vita_renderer.cpp').read_text()
        begin=source.index('void Apply_DX8_Texture_Transform(')
        end=source.index('bool Emit_Original_Texture_Coordinate(',begin)
        with tempfile.TemporaryDirectory(prefix='renegade-projective-') as folder:
            p=Path(folder)
            (p/'projective-production.inc').write_text(source[begin:end])
            subprocess.run(['g++','-std=c++17','-O1','-g','-Wall','-Wextra','-Werror',
                '-fsanitize=address,undefined','-fno-omit-frame-pointer','-I'+folder,
                '-I'+str(ROOT/'port/renderer/vita'),str(ROOT/'tools/vita_projective_coordinates_test.cpp'),
                '-o',str(p/'test')],check=True)
            subprocess.run([str(p/'test')],check=True)

    def test_pinned_shader_interface_and_cache_identity(self):
        with tempfile.TemporaryDirectory(prefix='renegade-projective-shader-') as folder:
            p=Path(folder)
            subprocess.run(['tar','-xzf',str(ROOT/'build/deps/vitagl-demo/source.tar.gz'),
                '--strip-components=1','-C',folder],check=True)
            for name in ('compact-unlit','indexed-immediate','projective-immediate'):
                subprocess.run(['patch','--batch','--fuzz=0','-p1','-i',str(ROOT/
                    ('port/renderer/vita/dependency-patches/vitagl-'+name+'.patch'))],
                    cwd=p,check=True,capture_output=True)
            ffp=(p/'source/ffp.c').read_text()
            self.assertIn('uint32_t projective : 1;',ffp)
            self.assertEqual(ffp.count('| 0x80000000U'),2)
            self.assertIn('mask.projective = attrs && renegade_projective_immediate;',ffp)
            self.assertIn('mask.fixed_mask = mask.pos_fixed_mask = 0;',ffp)
            variants=0
            for projective in (0,1):
                for textures in (1,2):
                    for lights in (0,1,4):
                        for shading in (0,1):
                            for kind in ('v','f'):
                                template=(p/('source/shaders/ffp_'+kind+'.h')).read_text().split('R"(',1)[1].rsplit(')"',1)[0]
                                if kind=='v':
                                    args=(0,textures,1,lights,shading,1,0,0,1,0,projective)
                                else:
                                    args=('',0,textures,1,3,0,0,lights,shading,0,0,0,projective)
                                shader=template%args
                                self.assertLess(len(shader.encode()),8192)
                                result=subprocess.run(['cpp','-P','-x','c','-'],input=shader,
                                    text=True,check=True,capture_output=True).stdout
                                if projective:
                                    self.assertIn('float3 '+('out vTexcoord' if kind=='v' else 'vTexcoord'),result)
                                    if kind=='v':
                                        self.assertIn('Otexcoord0.xy, 0.f, Otexcoord0.z',result)
                                        self.assertIn('.xyw;',result)
                                    else:
                                        self.assertIn('(vTexcoord).xy / (vTexcoord).z',result)
                                else:
                                    self.assertIn('float2 '+('out vTexcoord' if kind=='v' else 'vTexcoord'),result)
                                variants+=1
            print(f'Pinned projective shader preprocessing/interface PASS variants={variants}; GPU compilation unverified')


if __name__=='__main__':
    unittest.main()
