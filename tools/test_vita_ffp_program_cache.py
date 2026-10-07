"""vitaGL FFP program cache: patch application, wiring and key-record logic."""
from pathlib import Path
import os
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PATCHES = ROOT / 'port/renderer/vita/dependency-patches'
ORDER = ['compact-unlit', 'indexed-immediate', 'full-rgba-upload', 'dds-chain',
         'projective-immediate', 'attribute-invalidation', 'ffp-program-cache']
TARBALL = Path(os.environ.get('RENEGADE_VITAGL_TARBALL',
                              ROOT / 'build/deps/vitagl-demo/source.tar.gz'))
PATCH = PATCHES / 'vitagl-ffp-program-cache.patch'
WARM_H = ROOT / 'port/renderer/vita/ww3d_vita_ffp_program_warm.h'


def stat_names(text, prefix):
    body = text[text.index(prefix + 'VERSION'):]
    body = body[:body.index(prefix + 'COUNT')]
    return [name[len(prefix):] for name in re.findall(prefix + r'[A-Z_]+', body)]


class FfpProgramCacheTests(unittest.TestCase):
    @unittest.skipUnless(TARBALL.exists(), 'pinned vitaGL tarball unavailable')
    def test_patch_applies_in_build_order_and_redirects_every_ffp_path(self):
        with tempfile.TemporaryDirectory(prefix='renegade-ffp-cache-') as folder:
            subprocess.run(['tar', '-xzf', str(TARBALL), '--strip-components=1', '-C', folder],
                           check=True)
            for name in ORDER:
                subprocess.run(['patch', '--batch', '--fuzz=0', '-p1', '-i',
                                str(PATCHES / ('vitagl-' + name + '.patch'))],
                               cwd=folder, check=True, capture_output=True)
            ffp = (Path(folder) / 'source/ffp.c').read_text()
            vgl = (Path(folder) / 'source/vgl.c').read_text()
        # Active (two-stage, combiner) lazy paths and the pre-warm use the
        # application-owned directory; only the #error'd HIGH branches keep
        # upstream's literal.
        active = re.sub(r'#ifdef HAVE_HIGH_FFP_TEXUNITS\n\t\tsprintf\(fname, "ux0:data/shader_cache[^\n]*\n#else\n', '', ffp)
        self.assertEqual(ffp.count('"%s/v/%08X-%d.gxp", vgl_renegade_ffp_cache_path'), 2)
        self.assertEqual(ffp.count('"%s/f/%08X-%016llX.gxp", vgl_renegade_ffp_cache_path'), 2)
        reload = active[active.index('uint8_t reload_ffp_shaders('):
                        active.index('void _glDrawArrays_FixedFunctionIMPL(')]
        self.assertNotIn('sprintf(fname, "ux0:data/shader_cache/v%d/v/%08X', reload)
        self.assertNotIn('sprintf(fname, "ux0:data/shader_cache/v%d/f/%08X-%016llX', reload)
        # Both first-use reads go through the validating loader; compiles and
        # writes are unchanged and counted.
        self.assertEqual(reload.count('renegade_load_cached_ffp_program(fname)'), 2)
        self.assertEqual(reload.count('shark_compile_shader_extended('), 2)
        self.assertIn('sceGxmProgramCheck(prog) != 0', ffp)
        self.assertIn('renegade_ffp_count_build(RENEGADE_FFP_STAT_VERT_COMPILES', reload)
        self.assertIn('renegade_ffp_count_build(RENEGADE_FFP_STAT_FRAG_COMPILES', reload)
        # Pre-warm never evicts and restores the active program globals.
        prewarm = ffp[ffp.index('void vglRenegadePrewarmFfpPrograms('):]
        self.assertIn('vert_shader_cache_size < SHADER_CACHE_SIZE', prewarm)
        self.assertIn('frag_shader_cache_size < SHADER_CACHE_SIZE', prewarm)
        self.assertNotIn('ForceUnregister', prewarm)
        self.assertNotIn('shark_compile', prewarm)
        for name in ['ffp_vertex_program', 'ffp_vertex_params', 'ffp_vertex_attribs',
                     'ffp_fragment_program', 'ffp_fragment_params']:
            self.assertIn('%s = saved_%s;' % (name, name.replace('ffp_', '')), prewarm)
        # vglInit derives the FFP directory from the application root and
        # creates it (and v/, f/) at runtime; the default stays upstream's.
        init = vgl[vgl.index('if (shader_cache_root[0]) {'):]
        init = init[:init.index('#ifdef HAVE_SHADER_CACHE')]
        self.assertIn('"%s/ffp-%s", shader_cache_root, vglRenegadeGetFfpCacheTag()', init)
        self.assertIn('sceIoMkdir(vgl_renegade_ffp_cache_path, 0777);', init)
        self.assertIn('"ux0:data/shader_cache/v%d", FFP_SHADER_CACHE_MAGIC', init)
        # The tag carries revision, FFP magic, WVP mode and patch digest.
        self.assertIn('return VGL_GIT_HASH "-m" RENEGADE_FFP_STR(FFP_SHADER_CACHE_MAGIC) '
                      '"-w" RENEGADE_FFP_STR(WVP_ON_GPU) "-p" RENEGADE_VGL_FFP_CACHE_DIGEST;', ffp)

    @unittest.skipUnless(TARBALL.exists(), 'pinned vitaGL tarball unavailable')
    def test_prewarm_and_loader_against_mocks(self):
        """Compile the patched cache types, loader, key export and pre-warm
        with GXM/IO mocks: exact file bytes inserted, invalid files rejected,
        resident and out-of-mask keys skipped, no wrap, globals restored."""
        with tempfile.TemporaryDirectory(prefix='renegade-ffp-prewarm-') as folder:
            subprocess.run(['tar', '-xzf', str(TARBALL), '--strip-components=1', '-C', folder],
                           check=True)
            for name in ORDER:
                subprocess.run(['patch', '--batch', '--fuzz=0', '-p1', '-i',
                                str(PATCHES / ('vitagl-' + name + '.patch'))],
                               cwd=folder, check=True, capture_output=True)
            ffp = (Path(folder) / 'source/ffp.c').read_text()
            start = ffp.index('typedef union {\n\tstruct {\n\t\tuint32_t alpha_test_mode')
            types = ffp[start:ffp.index('uint8_t ffp_vertex_num_params', start)]
            mask_end = types.index('#define FRAGMENT_SHADER_MASK')
            types = types[:mask_end] + types[mask_end:].replace('#endif\n', '', 1)
            start = ffp.index('// Renegade platform extension: application-owned FFP GXP cache')
            loader = ffp[start:ffp.index('uint8_t reload_ffp_shaders(', start)]
            tail = ffp[ffp.index('// Renegade platform extension: export the FFP program keys'):]
            (Path(folder) / 'ffp_extract.inc').write_text(types + loader + tail)
            binary = Path(folder) / 'prewarm'
            subprocess.run(['gcc', '-std=gnu11', '-O1', '-g', '-Wall', '-Wextra', '-Werror',
                            '-Wno-format', '-Wno-unused-function',
                            '-fsanitize=address,undefined', '-fno-sanitize-recover=all',
                            '-fno-omit-frame-pointer', '-I' + folder,
                            str(ROOT / 'tools/vitagl_ffp_prewarm_test.c'), '-o', str(binary)],
                           check=True)
            result = subprocess.run([str(binary)], check=True, capture_output=True, text=True)
            self.assertIn('OK', result.stdout)

    def test_stat_indices_match_between_patch_and_port(self):
        patch_names = stat_names(PATCH.read_text(), 'RENEGADE_FFP_STAT_')
        port_names = stat_names(WARM_H.read_text(), 'STAT_')
        self.assertEqual(patch_names, port_names)
        self.assertGreater(len(port_names), 10)

    def test_build_script_applies_versions_and_reextracts(self):
        script = (ROOT / 'tools/build_vitagl_demo.sh').read_text()
        self.assertIn('vitagl-ffp-program-cache.patch', script)
        self.assertLess(script.index('-p1 < "$attribute_patch"'),
                        script.index('-p1 < "$program_cache_patch"'))
        self.assertLess(script.index('-p1 < "$program_cache_patch"'), script.index('make -C'))
        identity = script[script.index('identity=$('):]
        self.assertIn('"$program_cache_patch"', identity[:identity.index('\n')])
        extract = script[script.index('tar -xzf "$work/source.tar.gz" --strip-components=1 -C "$work/source" \\'):]
        extract = extract[:extract.index('patch --batch')]
        self.assertIn('source/vgl.c', extract)
        self.assertIn('source/ffp.c', extract)
        self.assertIn('-DRENEGADE_VGL_FFP_CACHE_DIGEST=', script)
        digest = script[script.index('ffp_cache_digest=$('):script.index('make -C')]
        for name in ['ffp.c', 'shaders/ffp_v.h', 'shaders/ffp_f.h', 'texture_combiners/']:
            self.assertIn(name, digest)

    def test_renderer_and_runtime_wiring(self):
        renderer = (ROOT / 'port/renderer/vita/ww3d_vita_renderer.cpp').read_text()
        self.assertIn('vglSetShaderCachePath(shader_cache_path);', renderer)
        self.assertIn('"ux0:data/renegade/cache/vitagl-shader-cache"', renderer)
        init = renderer[renderer.index('const GLboolean resolution_fallback = vglInitExtended('):]
        self.assertIn('RenegadeVitaFfpProgramWarm::Prewarm_From_Record("renderer-init");',
                      init[:init.index('Log_VitaGL_Memory();')])
        self.assertLess(renderer.index('vglSetShaderCachePath(shader_cache_path);'),
                        renderer.index('Prewarm_From_Record("renderer-init")'))
        self.assertEqual(renderer.count('RenegadeVitaFfpProgramWarm::Sample_Window('), 1)
        self.assertEqual(renderer.count('RenegadeVitaFfpProgramWarm::Record_Resident_Keys('), 1)
        runtime = (ROOT / 'port/platform/vita/a31_vita_runtime.cpp').read_text()
        prepare = runtime[runtime.index('void Prepare_Original_Level_Loading_Resources('):]
        self.assertIn('RenegadeVitaFfpProgramWarm::Record_Resident_Keys("level-prepare");',
                      prepare[:prepare.index('Warm_Level_Cinematic_Preset_Models(')])
        cmake = (ROOT / 'CMakeLists.txt').read_text()
        self.assertIn('port/renderer/vita/ww3d_vita_ffp_program_warm.cpp', cmake)

    def test_key_record_harness(self):
        with tempfile.TemporaryDirectory(prefix='renegade-ffp-keys-') as folder:
            binary = Path(folder) / 'test'
            subprocess.run(['g++', '-std=c++17', '-O1', '-g', '-Wall', '-Wextra', '-Werror',
                            '-fsanitize=address,undefined', '-fno-sanitize-recover=all',
                            '-fno-omit-frame-pointer',
                            '-I' + str(ROOT / 'port/renderer/vita'),
                            str(ROOT / 'tools/vita_ffp_program_keys_test.cpp'),
                            '-o', str(binary)], check=True)
            result = subprocess.run([str(binary)], check=True, capture_output=True, text=True)
            self.assertIn('OK', result.stdout)


if __name__ == '__main__':
    unittest.main()
