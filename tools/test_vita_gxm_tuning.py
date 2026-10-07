"""Execute the vitaGL sizing flag parser and transient-pool accounting, and pin
their wiring into the Vita renderer init/present path."""
from pathlib import Path
import os
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
RENDERER = ROOT / 'port/renderer/vita/ww3d_vita_renderer.cpp'
HEADER = ROOT / 'port/renderer/vita/ww3d_vita_gxm_tuning.h'
MAIN_TREE = Path('/home/steve/projects/RenegadeVitaBuilder/workspace/active')
SDK_GXM = Path('/usr/local/vitasdk/arm-vita-eabi/include/psp2/gxm.h')

HARNESS = r'''
#include "ww3d_vita_gxm_tuning.h"
#include <cassert>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>

static bool parse(const std::string &text, VitaGLSizing *out) {
    return Parse_VitaGL_Sizing_Flag(text.data(), text.size(), out);
}

static bool same(const VitaGLSizing &a, const VitaGLSizing &b) {
    return std::memcmp(&a, &b, sizeof(a)) == 0;
}

static void accepted_invariants(const VitaGLSizing &s) {
    assert(s.immediate_pool_bytes >= (1U << 20) && s.immediate_pool_bytes <= (16U << 20));
    assert(s.circular_pool_bytes >= (16U << 20) && s.circular_pool_bytes <= (64U << 20));
    assert(s.display_buffers == 2U || s.display_buffers == 3U);
    assert(s.vdm_ring_bytes >= (128U << 10) && s.vdm_ring_bytes <= (1024U << 10));
    assert(s.vertex_ring_bytes >= (2048U << 10) && s.vertex_ring_bytes <= (8192U << 10));
    assert(s.fragment_ring_bytes >= (512U << 10) && s.fragment_ring_bytes <= (4096U << 10));
    assert(s.fragment_usse_ring_bytes >= (16U << 10) && s.fragment_usse_ring_bytes <= (64U << 10));
    assert(s.parameter_buffer_bytes >= (8U << 20) && s.parameter_buffer_bytes <= (64U << 20));
    assert(s.ram_reserve_bytes >= (16U << 20) && s.ram_reserve_bytes <= (64U << 20));
    assert(s.vdm_ring_bytes % 4096U == 0U && s.vertex_ring_bytes % 4096U == 0U);
    assert(s.fragment_ring_bytes % 4096U == 0U && s.fragment_usse_ring_bytes % 4096U == 0U);
    assert(s.circular_pool_bytes / s.display_buffers >= s.immediate_pool_bytes + (1U << 20));
    assert((s.overridden & ~0x1FFU) == 0U);
}

int main() {
    const VitaGLSizing d = Default_VitaGL_Sizing();
    assert(d.immediate_pool_bytes == 4U * 1024U * 1024U);
    assert(d.ram_reserve_bytes == 0x1000000U);
    assert(d.circular_pool_bytes == 32U * 1024U * 1024U && d.display_buffers == 3U);
    assert(d.vdm_ring_bytes == 131072U && d.vertex_ring_bytes == 2097152U);
    assert(d.fragment_ring_bytes == 524288U && d.fragment_usse_ring_bytes == 16384U);
    assert(d.parameter_buffer_bytes == 16777216U && d.overridden == 0U);
    accepted_invariants(d);

    VitaGLSizing s = d;
    assert(parse("RVGX1 bufs=2\n", &s));
    assert(s.display_buffers == 2U && s.overridden == VitaGLSizing::BUFFERS);
    VitaGLSizing expect = d; expect.display_buffers = 2U; expect.overridden = VitaGLSizing::BUFFERS;
    assert(same(s, expect));

    s = d;
    assert(parse("RVGX1 imm=8 circ=48 bufs=3 vdm=512 vtx=4096 frag=1024 usse=32 pb=32 ramres=24\n", &s));
    assert(s.immediate_pool_bytes == (8U << 20) && s.circular_pool_bytes == (48U << 20));
    assert(s.vdm_ring_bytes == (512U << 10) && s.vertex_ring_bytes == (4096U << 10));
    assert(s.fragment_ring_bytes == (1024U << 10) && s.fragment_usse_ring_bytes == (32U << 10));
    assert(s.parameter_buffer_bytes == (32U << 20) && s.ram_reserve_bytes == (24U << 20));
    assert(s.overridden == 0x1FFU);
    accepted_invariants(s);

    // Boundary values on both sides of every range.
    const char *good[] = {
        "RVGX1 imm=1\n", "RVGX1 imm=9\n", "RVGX1 circ=16\n", "RVGX1 circ=64\n",
        "RVGX1 vdm=128\n", "RVGX1 vdm=1024\n", "RVGX1 vtx=2048\n", "RVGX1 vtx=8192\n",
        "RVGX1 frag=512\n", "RVGX1 frag=4096\n", "RVGX1 usse=16\n", "RVGX1 usse=64\n",
        "RVGX1 pb=8\n", "RVGX1 pb=64\n", "RVGX1 ramres=16\n", "RVGX1 ramres=64\n",
        "RVGX1 imm=16 circ=51\n", "RVGX1 imm=15 circ=48 bufs=3\n",
    };
    for (const char *line : good) {
        s = d;
        if (!parse(line, &s)) { std::fprintf(stderr, "rejected %s", line); return 1; }
        accepted_invariants(s);
    }
    const char *bad[] = {
        "", "\n", "RVGX1\n", "RVGX1 \n", "RVGX1 bufs=2", "RVGX1 bufs=2 \n", "RVGX1  bufs=2\n",
        "RVGX0 bufs=2\n", "rvgx1 bufs=2\n", "RVGX1 BUFS=2\n", "RVGX1 bufs=1\n", "RVGX1 bufs=4\n",
        "RVGX1 bufs=02\n", "RVGX1 bufs=\n", "RVGX1 =2\n", "RVGX1 bufs=2 bufs=3\n",
        "RVGX1 imm=0\n", "RVGX1 imm=17\n", "RVGX1 imm=10\n", "RVGX1 imm=16\n",
        "RVGX1 circ=15\n", "RVGX1 circ=65\n", "RVGX1 vdm=127\n", "RVGX1 vdm=130\n",
        "RVGX1 vdm=1028\n", "RVGX1 vtx=2047\n", "RVGX1 vtx=8196\n", "RVGX1 frag=510\n",
        "RVGX1 usse=12\n", "RVGX1 usse=18\n", "RVGX1 pb=7\n", "RVGX1 pb=65\n",
        "RVGX1 ramres=8\n", "RVGX1 ramres=65\n", "RVGX1 msaa=2\n", "RVGX1 bufs=2\n\n",
        "RVGX1 bufs=2\r\n", "RVGX1 bufs=+2\n", "RVGX1 bufs=-2\n", "RVGX1 vdm=000128\n",
        "RVGX1 vdm=4294967424\n", "RVGX1 bufs=2;\n", "RVGX1bufs=2\n", "RVGX1 imm=8 circ=16\n",
        "RVGX1 imm=5 bufs=3 circ=16\n",
        "RVGX1 bufs=23", "RVGX1 vdm=1288",
    };
    for (const char *line : bad) {
        VitaGLSizing before = d; before.vdm_ring_bytes = 0xABCDU; s = before;
        if (parse(line, &s)) { std::fprintf(stderr, "accepted bad line '%s'\n", line); return 1; }
        assert(same(s, before));
    }
    std::string long_line = "RVGX1";
    while (long_line.size() < 170U) long_line += " bufs=2";
    long_line += "\n";
    s = d; assert(!parse(long_line, &s)); assert(same(s, d));
    assert(!Parse_VitaGL_Sizing_Flag(NULL, 5U, &s));
    assert(!Parse_VitaGL_Sizing_Flag("RVGX1 bufs=2\n", 13U, NULL));
    // Embedded NUL inside the declared length is rejected, not truncated.
    const char nul_line[] = "RVGX1 bufs=2\0 x\n";
    s = d; assert(!Parse_VitaGL_Sizing_Flag(nul_line, sizeof(nul_line) - 1U, &s));

    // Random mutations: never crash; every accepted result is in range.
    unsigned seed = 12345U, accepted = 0U;
    const char alphabet[] = "RVGX1 =\n0123456789abcdefghimnoprstuvx";
    for (unsigned round = 0U; round < 200000U; ++round) {
        seed = seed * 1103515245U + 12345U;
        std::string text = (seed & 1U) ? "RVGX1 " : "RVGX1 imm=4 bufs=2 ";
        const unsigned extra = (seed >> 8) % 24U;
        for (unsigned i = 0U; i < extra; ++i) {
            seed = seed * 1103515245U + 12345U;
            text += alphabet[(seed >> 16) % (sizeof(alphabet) - 1U)];
        }
        if ((seed >> 4) & 1U) text += "\n";
        s = d;
        if (parse(text, &s)) { accepted_invariants(s); ++accepted; }
        else assert(same(s, d));
    }

    // Spans.
    unsigned char block[64];
    assert(VitaGL_Span_Bytes(block, block + 40) == 40U);
    assert(VitaGL_Span_Bytes(block + 40, block) == 0U);
    assert(VitaGL_Span_Bytes(NULL, block) == 0U && VitaGL_Span_Bytes(block, NULL) == 0U);

    // Window accounting.
    VitaGLPoolWindow window = {};
    window.Record(1000U, 4096U, 5000U, 10000U);
    window.Record(3000U, 4096U, 9000U, 10000U);
    window.Record(5000U, 4096U, 12000U, 10000U);
    assert(window.frames == 3U && window.immediate_peak_bytes == 5000U);
    assert(window.immediate_overrun_frames == 1U && window.circular_overrun_frames == 1U);
    assert(window.circular_peak_bytes == 12000U && window.Immediate_Average_Bytes() == 3000U);
    assert(window.immediate_capacity_bytes == 4096U && window.circular_slice_bytes == 10000U);
    window.Record(10U, 0U, 10U, 0U);  // unknown capacities never count as overruns
    window.Record(4096U, 4096U, 10000U, 10000U);  // exactly full is not an overrun
    assert(window.immediate_overrun_frames == 1U && window.circular_overrun_frames == 1U);
    window.Reset();
    assert(window.frames == 0U && window.immediate_peak_bytes == 0U &&
           window.Immediate_Average_Bytes() == 0U && window.circular_overrun_frames == 0U);
    std::printf("vitaGL sizing parser PASS accepted_mutations=%u\n", accepted);
    return 0;
}
'''


class VitaGxmTuningTests(unittest.TestCase):
    def test_parser_and_pool_window(self):
        flags = ['-O2']
        if os.environ.get('RENEGADE_GXM_SANITIZE', '1') == '1':
            flags = ['-O1', '-g', '-fsanitize=address,undefined',
                     '-fno-sanitize-recover=all', '-fno-omit-frame-pointer']
        with tempfile.TemporaryDirectory(prefix='renegade-gxm-tuning-') as folder:
            source = Path(folder) / 'test.cpp'
            binary = Path(folder) / 'test'
            source.write_text(HARNESS)
            subprocess.run(['g++', '-std=c++17', *flags, '-Wall', '-Wextra', '-Werror',
                            '-I' + str(HEADER.parent), str(source), '-o', str(binary)],
                           check=True)
            result = subprocess.run([str(binary)], check=True, capture_output=True, text=True)
            self.assertIn('PASS', result.stdout)

    def test_defaults_match_sdk_constants(self):
        if not SDK_GXM.exists():
            self.skipTest('VitaSDK gxm.h not installed')
        gxm = SDK_GXM.read_text()
        header = HEADER.read_text()
        for name, value in (('PARAMETER_BUFFER_SIZE', '16U << 20'),
                            ('VDM_RING_BUFFER_SIZE', '128U << 10'),
                            ('VERTEX_RING_BUFFER_SIZE', '2U << 20'),
                            ('FRAGMENT_RING_BUFFER_SIZE', '512U << 10'),
                            ('FRAGMENT_USSE_RING_BUFFER_SIZE', '16U << 10')):
            match = re.search(r'#define SCE_GXM_DEFAULT_%s\s+\(([^)]*)\)' % name, gxm)
            self.assertIsNotNone(match, name)
            sdk_bytes = 1
            for factor in match.group(1).split('*'):  # e.g. 16 * 1024 * 1024
                sdk_bytes *= int(factor)
            base, shift = value.replace('U', '').split('<<')
            self.assertEqual(sdk_bytes, int(base) << int(shift), name)
            self.assertIn('= %s;' % value, header)

    def test_renderer_wiring(self):
        source = RENDERER.read_text()
        init = source[source.index('bool Initialize()'):]
        init = init[:init.index('\n}\n')]
        # Sizes are requested before vglInitExtended and reported after it.
        self.assertLess(init.index('Apply_VitaGL_Sizing(vitagl_sizing);'),
                        init.index('vglInitExtended('))
        # The display size comes from the internal-resolution scan-out level
        # (960x544 unless internal-resolution-v1.flag selects a smaller one).
        call = init[init.index('vglInitExtended('):]
        call = call[:call.index(';')]
        self.assertIn('static_cast<int>(vitagl_sizing.immediate_pool_bytes),', call)
        self.assertIn('static_cast<int>(g_physical_display_width),', call)
        self.assertIn('static_cast<int>(g_physical_display_height),', call)
        self.assertIn('static_cast<int>(vitagl_sizing.ram_reserve_bytes), campaign_msaa);', init)
        self.assertLess(init.index('vglInitExtended('),
                        init.index('Log_VitaGL_Effective_Sizing(vitagl_sizing);'))
        # The garbage collector placement stays ahead of vglInit.
        self.assertLess(init.index('vglSetupGarbageCollector(0x10000100, SCE_KERNEL_CPU_MASK_USER_2);'),
                        init.index('vglInitExtended('))
        apply = source[source.index('void Apply_VitaGL_Sizing('):]
        apply = apply[:apply.index('\n}\n')]
        # Every setter is conditional on its overridden bit: no flag, no change.
        setters = re.findall(r'\tif \(sizing\.overridden & VitaGLSizing::(\w+)\) (vglSet\w+)\(', apply)
        self.assertEqual(len(setters), 7)
        self.assertEqual(apply.count('vglSet'), 7)
        end_frame = source[source.index('void End_Frame(bool present)'):]
        self.assertLess(end_frame.index('Sample_VitaGL_Transient_Pools(g_statistics.frames);'),
                        end_frame.index('vglSwapBuffers('))

    def test_extern_types_match_pinned_vitagl(self):
        vitagl = MAIN_TREE / 'build/deps/vitagl-demo/source/source'
        if not (vitagl / 'gxm.c').exists():
            self.skipTest('pinned vitaGL source not present')
        definitions = '\n'.join((vitagl / name).read_text(errors='replace') for name in
                                ('gxm.c', 'vgl.c', 'ffp.c', 'utils/mem_utils.c'))
        expected = {
            'legacy_pool_size': r'^int legacy_pool_size\b',
            'legacy_pool_ptr': r'^float \*legacy_pool_ptr\b',
            'legacy_pool_end': r'^float \*legacy_pool_end\b',
            'circular_data_pool_size': r'^uint32_t circular_data_pool_size\b',
            'circular_data_pool': r'^uint8_t \*circular_data_pool\[DISPLAY_MAX_BUFFER_COUNT\]',
            'circular_data_pool_ptr': r'^uint8_t \*circular_data_pool_ptr\[DISPLAY_MAX_BUFFER_COUNT\]',
            'circular_data_pool_limit': r'^uint8_t \*circular_data_pool_limit\[DISPLAY_MAX_BUFFER_COUNT\]',
            'vgl_circular_idx': r'^int vgl_circular_idx\b',
            'gxm_display_buffer_count': r'^uint8_t gxm_display_buffer_count\b',
            'gxm_param_buf_size': r'^uint32_t gxm_param_buf_size\b',
            'vsync_interval': r'^uint32_t vsync_interval\b',
            'has_cached_mem': r'^GLboolean has_cached_mem\b',
        }
        for name, pattern in expected.items():
            self.assertRegex(definitions, re.compile(pattern, re.M), name)
        # The default circular pool and immediate-pool reservation semantics the
        # header documents.
        self.assertIn('#define CIRCULAR_POOL_SIZE_DEF (32 * 1024 * 1024)', definitions)
        self.assertIn('uint8_t gxm_display_buffer_count = 3;', definitions)
        self.assertIn('legacy_pool = (float *)gpu_alloc_mapped_temp(legacy_pool_size);', definitions)


if __name__ == '__main__':
    unittest.main()
