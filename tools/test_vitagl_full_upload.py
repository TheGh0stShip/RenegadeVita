"""Compare pinned texture copy-on-write and RGBA row-copy bodies byte for byte."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class FullUploadTests(unittest.TestCase):
    def test_texture_pixels_and_retirement(self):
        with tempfile.TemporaryDirectory(prefix='renegade-upload-') as folder:
            p = Path(folder)
            subprocess.run(['tar', '-xzf', str(ROOT/'build/deps/vitagl-demo/source.tar.gz'),
                '--strip-components=1', '-C', folder], check=True)
            pristine = (p/'source/textures.c').read_text()
            subprocess.run(['patch', '--batch', '--fuzz=0', '-p1', '-i', str(ROOT/
                'port/renderer/vita/dependency-patches/vitagl-full-rgba-upload.patch')],
                cwd=p, check=True, capture_output=True)
            patched = (p/'source/textures.c').read_text()
            allocation = (p/'source/utils/gpu_utils.c').read_text()
            start = allocation.index('void gpu_alloc_texture(')
            end = allocation.index('void gpu_alloc_paletted_texture(', start)
            (p/'allocation.inc').write_text(allocation[start:end])
            for name, source in [('baseline', pristine), ('patched', patched)]:
                start = source.index('// Copying the texture in a new mem location', source.index('void _glTexSubImage2D('))
                end = source.index('\n#endif\n\t// Calculating start address', start)
                copy = source[start:end]
                start = source.index('\t\tptr += xoffset * bpp + yoffset * mip_stride;', end)
                end = source.index(' else { // Executing texture modification via callbacks', start)
                rows = source[start:end]
                # This optimization is restricted to level zero. Exercise the
                # actual base-level offset/row copy; other mip writes are out
                # of scope and their old-image preservation remains required.
                (p/(name+'.inc')).write_text(copy + '\nuint8_t *ptr=(uint8_t*)tex->data;\n'
                    'unsigned mip_w=orig_w,mip_stride=VGL_ALIGN(orig_w,8)*bpp;\n' + rows)
            subprocess.run(['g++', '-std=c++17', '-O1', '-g', '-Wall', '-Wextra', '-Werror', '-Wno-sign-compare',
                '-fsanitize=address,undefined', '-fno-omit-frame-pointer', '-I'+folder,
                str(ROOT/'tools/vitagl_full_upload_test.cpp'), '-o', str(p/'test')], check=True)
            subprocess.run([str(p/'test')], check=True)


if __name__ == '__main__':
    unittest.main()
