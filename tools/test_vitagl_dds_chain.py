"""Compile the actual native chain upload against pinned swizzle and GXM records."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class DDSChainTests(unittest.TestCase):
    def test_native_chain_pixels_layout_and_failure(self):
        with tempfile.TemporaryDirectory(prefix='renegade-dds-chain-') as folder:
            p = Path(folder)
            subprocess.run(['tar', '-xzf', str(ROOT/'build/deps/vitagl-demo/source.tar.gz'),
                '--strip-components=1', '-C', folder], check=True)
            subprocess.run(['patch', '--batch', '--fuzz=0', '-p1', '-i', str(ROOT/
                'port/renderer/vita/dependency-patches/vitagl-dds-chain.patch')],
                cwd=p, check=True, capture_output=True)
            source = (p/'source/textures.c').read_text()
            (p/'dxt-chain-production.inc').write_text(source[source.index(
                'GLboolean vglRenegadeUploadDXTChain('):])
            swizzle = (p/'source/utils/texture_swizzler.cpp').read_text()
            a = swizzle.index('static inline uint32_t Part1By1(')
            b = swizzle.index('// Inverse of Part1By1', a)
            c = swizzle.index('template <uint32_t pixelSize, CopyPixel copyPixel>')
            d = swizzle.index('#pragma GCC diagnostic push', c)
            (p/'dxt-swizzle-reference.inc').write_text(swizzle[a:b]+swizzle[c:d])
            boundary = (ROOT/'port/renderer/vita/ww3d_dx8_boundary.cpp').read_text()
            start = boundary.index('bool Upload_Retained_DDS_Chain(')
            end = boundary.index('\n#endif', start)
            (p/'dds-surface-production.inc').write_text(boundary[start:end])
            subprocess.run(['g++', '-std=c++17', '-O1', '-g', '-Wall', '-Wextra', '-Werror',
                '-fsanitize=address,undefined', '-fno-omit-frame-pointer', '-I'+folder,
                str(ROOT/'tools/vitagl_dds_chain_test.cpp'), '-o', str(p/'test')], check=True)
            subprocess.run([str(p/'test')], check=True)


if __name__ == '__main__':
    unittest.main()
