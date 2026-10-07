"""RVTX1 (tutorial-texture-v1.flag) packing proofs and boundary contract.

Pure Python: the C++ re-pack expressions are read from the header text and
evaluated exhaustively over all 65,536 16-bit inputs, so the proof follows the
source the ARM build compiles. No compiler is invoked.
"""
import pathlib
import re
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
HEADER = ROOT / 'port/renderer/vita/texture_upload_packing.h'
BOUNDARY = ROOT / 'port/renderer/vita/ww3d_dx8_boundary.cpp'


def c_return_expression(source, function):
    body = source[source.index(function):]
    match = re.search(r'return static_cast<uint16_t>\((.*?)\);\n', body)
    return match.group(1)


def as_python(expression):
    # Only integer literals with U suffixes, &, |, <<, >> and one identifier.
    python = re.sub(r'\b(0x[0-9a-fA-F]+|\d+)U\b', r'\1', expression)
    if not re.fullmatch(r'[\sa-z_()&|<>0-9xA-Fa-f]+', python):
        raise AssertionError('unexpected token in C++ expression: ' + expression)
    return python


def d3d_a1r5g5b5_fields(pixel):
    # Convert_Surface_Pixel_To_RGBA(D3DFMT_A1R5G5B5) field extraction.
    return ((pixel >> 10) & 0x1f, (pixel >> 5) & 0x1f, pixel & 0x1f, pixel >> 15)


def gl_5551_fields(packed):
    # vitaGL texture_callbacks.c read_rgba5551 (GL_UNSIGNED_SHORT_5_5_5_1).
    return ((packed >> 11) & 0x1f, (packed >> 6) & 0x1f, (packed >> 1) & 0x1f, packed & 1)


class TexturePackingProofs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.header = HEADER.read_text(encoding='utf-8')
        cls.pack = staticmethod(eval('lambda pixel: (' + as_python(c_return_expression(
            cls.header, 'Pack_RGBA5551_From_A1R5G5B5')) + ') & 0xffff'))
        cls.unpack = staticmethod(eval('lambda packed: (' + as_python(c_return_expression(
            cls.header, 'Unpack_A1R5G5B5_From_RGBA5551')) + ') & 0xffff'))

    def test_every_a1r5g5b5_texel_keeps_its_exact_fields(self):
        for pixel in range(0x10000):
            self.assertEqual(d3d_a1r5g5b5_fields(pixel), gl_5551_fields(self.pack(pixel)))

    def test_repack_is_a_bijection(self):
        packed = [self.pack(pixel) for pixel in range(0x10000)]
        self.assertEqual(len(set(packed)), 0x10000)
        for pixel in range(0x10000):
            self.assertEqual(self.unpack(self.pack(pixel)), pixel)

    def test_documented_expansion_bound(self):
        # RGBA8888 path: v*255/31 (integer). Hardware 5-bit expansion is not
        # specified here; bit replication and exact rounding both stay within
        # one 8-bit step, which is why RVTX1 is default off, not "identical".
        for value in range(32):
            cpu = value * 255 // 31
            self.assertLessEqual(abs(cpu - ((value << 3) | (value >> 2))), 1)
            self.assertLessEqual(abs(cpu - round(value * 255 / 31)), 1)

    def test_row_packer_reads_little_endian_and_mixes_packed_words(self):
        body = self.header[self.header.index('inline uint32_t Pack_A1R5G5B5_Row'):]
        body = body[:body.index('\n}\n')]
        self.assertIn('static_cast<uint16_t>(source[x * 2U])', body)
        self.assertIn('static_cast<uint16_t>(source[x * 2U + 1U]) << 8U', body)
        self.assertIn('destination[x] = packed;', body)
        self.assertIn('checksum = (checksum ^ packed) * 16777619U;', body)

    def test_flag_grammar_is_strict_and_default_off(self):
        parse = self.header[self.header.index('inline unsigned Parse_Mode'):]
        parse = parse[:parse.index('\n}\n')]
        self.assertIn("size != 8U", parse)
        for needle in ("data[0] != 'R'", "data[1] != 'V'", "data[2] != 'T'",
                       "data[3] != 'X'", "data[4] != '1'", "data[5] != ' '",
                       "data[7] != '\\n'"):
            self.assertIn(needle, parse)
        self.assertIn('return value & MODE_KNOWN_BITS;', parse)
        self.assertEqual(parse.count('return 0U;'), 2)
        self.assertIn('MODE_PACK_A1R5G5B5 = 1U,', self.header)
        self.assertIn('MODE_KNOWN_BITS = 1U', self.header)

    def test_linear_storage_estimate_pads_rows_to_eight_texels(self):
        self.assertIn('static_cast<uint64_t>((width + 7U) & ~7U) * height * bytes_per_texel',
                      self.header)


class TexturePackingBoundaryContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.boundary = BOUNDARY.read_text(encoding='utf-8')

    def section(self, start, end):
        begin = self.boundary.index(start)
        return self.boundary[begin:self.boundary.index(end, begin)]

    def test_flag_is_read_once_and_absent_means_unchanged(self):
        mode = self.section('unsigned Texture_Packing_Mode()', '\n}\n')
        self.assertIn('static int mode = -1;', mode)
        self.assertIn('unsigned parsed = 0U;', mode)
        self.assertIn('"ux0:data/renegade/user/config/tutorial-texture-v1.flag", "rb"', mode)
        self.assertIn('RenegadeVitaTexturePacking::Parse_Mode(value, size)', mode)
        self.assertEqual(self.boundary.count('tutorial-texture-v1.flag"'), 1)

    def test_only_archive_a1r5g5b5_targas_take_the_packed_path(self):
        create = self.section('IDirect3DTexture8 *Create_Texture_From_Surface(',
                              'IDirect3DTexture8 *Create_Checkerboard_Fallback()\n{')
        gate = create.index('!retain_surface_copy && description.Format == D3DFMT_A1R5G5B5')
        self.assertLess(create.index('#if defined(__vita__)'), gate)
        self.assertIn('(Texture_Packing_Mode() & RenegadeVitaTexturePacking::MODE_PACK_A1R5G5B5) != 0U',
                      create)
        self.assertIn('if (packed != NULL) return packed;', create)
        # The RGBA8888 expansion is skipped only when the packed upload succeeded.
        self.assertLess(gate, create.index('const size_t rgba_bytes = '))
        self.assertEqual(self.boundary.count('Create_Packed_A1R5G5B5_Texture('), 2)

    def test_packed_upload_is_16_bit_level_zero_and_transactional(self):
        packed = self.section('IDirect3DTexture8 *Create_Packed_A1R5G5B5_Texture(',
                              '\n#endif\n')
        self.assertIn('description.Format != D3DFMT_A1R5G5B5', packed)
        self.assertIn('surface->Get_Pitch() < description.Width * 2U', packed)
        self.assertIn('glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, description.Width, description.Height,\n'
                      '\t\t0, GL_RGBA, GL_UNSIGNED_SHORT_5_5_5_1, packed.data());', packed)
        self.assertNotIn('glGenerateMipmap', packed)
        self.assertNotIn('GL_LINEAR_MIPMAP', packed)
        self.assertIn('glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);', packed)
        self.assertLess(packed.index('glBindTexture(GL_TEXTURE_2D, native);'),
                        packed.index('RenegadeVitaRenderer::Invalidate_Texture_State_Cache();'))
        failure = packed[packed.index('if (glGetError() != GL_NO_ERROR) {'):]
        failure = failure[:failure.index('}')]
        self.assertIn('RenegadeVitaRenderer::Release_Texture(native);', failure)
        self.assertIn('return NULL;', failure)
        self.assertIn('texture->SourceFormat = description.Format;', packed)
        self.assertIn('texture->HasAlpha = true;', packed)
        self.assertIn('texture->ResidentBytes = packed.size() * sizeof(uint16_t);', packed)
        self.assertIn('RenegadeVitaRenderer::Record_Texture_Upload(texture->ResidentBytes);', packed)
        self.assertNotIn('Attach_Texture_Surface_Copy', packed)

    def test_archive_targa_totals_are_logged_in_both_modes(self):
        targa = self.section('IDirect3DTexture8 *Load_Targa_Texture',
                             'int Get_Indexed_Material_UV_Source')
        self.assertIn('const uint64_t started_us = sceKernelGetProcessTimeWide();', targa)
        self.assertIn('Record_Archive_Targa_Load(texture, decoded_us - started_us,', targa)
        self.assertLess(targa.index('if (texture != NULL && !texture->DiagnosticFallback)'),
                        targa.index('Record_Archive_Targa_Load('))
        record = self.section('void Record_Archive_Targa_Load(', '\n}\n')
        self.assertIn("if (totals.loads > 16U && (totals.loads & (totals.loads - 1U)) != 0U) return;", record)
        self.assertIn('"archive-tga loads=%u packed16=%u', record)


if __name__ == '__main__':
    unittest.main()
