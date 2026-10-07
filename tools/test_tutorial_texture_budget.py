"""Synthetic-fixture tests for tools/tutorial_texture_budget.py (pure Python).

Fixtures are tiny generated MIX/DDS/TGA/W3D files; no retail data is read.
"""
import io
import json
import struct
import tempfile
import unittest
import zlib
from contextlib import redirect_stdout
from pathlib import Path

from tools import tutorial_texture_budget as budget


def chunk(kind, payload, nested=False):
    return struct.pack('<II', kind, len(payload) | (0x80000000 if nested else 0)) + payload


def texture(name, attributes=None):
    body = chunk(0x32, name.encode('ascii') + b'\0')
    if attributes is not None:
        body += chunk(0x33, struct.pack('<HHIf', attributes, 0, 1, 0.0))
    return chunk(0x31, body, True)


def textures(*items):
    return chunk(0x30, b''.join(items), True)


def mesh(*children):
    return chunk(0x0, b''.join(children), True)


def dds(width, height, fourcc, mip_count, data_bytes, fill):
    header = bytearray(128)
    header[:4] = b'DDS '
    struct.pack_into('<IIIIIII', header, 4, 124, 0x1007, height, width, 0, 0, mip_count)
    struct.pack_into('<II4s', header, 76, 32, 4, fourcc)
    return bytes(header) + bytes([fill]) * data_bytes


def tga16(width, height, fill):
    header = struct.pack('<BBBHHBHHHHBB', 0, 0, 2, 0, 0, 0, 0, 0, width, height, 16, 1)
    return header + bytes([fill]) * (width * height * 2)


def write_mix(path, members):
    names = list(members)
    data = bytearray(b'MIX1' + b'\0' * 8)
    records = []
    for name in names:
        payload = members[name]
        records.append((zlib.crc32(name.upper().encode('ascii')), len(data), len(payload)))
        data += payload
    index_offset = len(data)
    data += struct.pack('<I', len(names))
    for record in records:
        data += struct.pack('<III', *record)
    names_offset = len(data)
    data += struct.pack('<I', len(names))
    for name in names:
        raw = name.encode('ascii') + b'\0'
        data += bytes([len(raw)]) + raw
    struct.pack_into('<II', data, 4, index_offset, names_offset)
    path.write_bytes(bytes(data))


def dep(names):
    body = b''.join(bytes([1, len(n) + 1]) + n.encode('ascii') + b'\0' for n in names)
    return struct.pack('<II', 0x04020527, len(body)) + body


def emitter(texture_name):
    info = texture_name.encode('ascii').ljust(260, b'\0') + b'\0' * 64
    return chunk(0x500, chunk(0x501, b'\0' * 40) + chunk(0x503, info), True)


def hlod(sub_object):
    sub = struct.pack('<I', 0) + sub_object.encode('ascii').ljust(32, b'\0')
    return chunk(0x700, chunk(0x701, b'\0' * 48) +
                 chunk(0x702, chunk(0x703, b'\0' * 8) + chunk(0x704, sub), True), True)


def build_fixture(root):
    data = root / 'Data'
    data.mkdir()
    lvl = mesh(textures(texture('TEX_NATIVE.TGA', 0), texture('tex_tail.tga'))) + hlod('OTHER.MESH')
    other = mesh(textures(texture('tex_dxt3.tga'), texture('tex_16.tga'),
                          texture('nolod.tga', budget.W3DTEXTURE_NO_LOD),
                          texture('ghost.tga'))) + emitter('emit.tga')
    dep_model = mesh(
        chunk(0x25, textures(texture('lm_selected.tga')), True),
        chunk(0x26, textures(texture('lm_skipped.tga')), True),
        textures(texture('dup_a.tga'), texture('dup_b.tga'), texture('variant.tga'),
                 texture('variant.dds'), texture('truncated.tga')))
    write_mix(data / 'M00_Tutorial.mix', {
        'lvl.w3d': lvl,
        'm00_tutorial.dep': dep(['dep_model.w3d', 'missing_model.w3d', '.w3d']),
    })
    write_mix(data / 'always.dat', {
        'other.w3d': other,
        'dep_model.w3d': dep_model,
        'tex_native.dds': dds(64, 64, b'DXT1', 7, 2744, 0x11),
        'tex_tail.dds': dds(64, 16, b'DXT5', 7, 1424, 0x12),
        'tex_dxt3.dds': dds(32, 32, b'DXT3', 1, 1024, 0x13),
        'tex_16.tga': tga16(16, 8, 0xAB),
        'nolod.dds': dds(32, 32, b'DXT1', 6, 680, 0x14),
        'emit.dds': dds(4, 4, b'DXT1', 1, 8, 0x15),
        'lm_selected.dds': dds(4, 4, b'DXT1', 1, 8, 0x16),
        'lm_skipped.dds': dds(4, 4, b'DXT1', 1, 8, 0x17),
        'dup_a.dds': dds(8, 8, b'DXT1', 1, 32, 0x18),
        'dup_b.dds': dds(8, 8, b'DXT1', 1, 32, 0x18),
        'variant.dds': dds(8, 8, b'DXT1', 1, 32, 0x19),
        'truncated.dds': dds(64, 64, b'DXT1', 1, 100, 0x1A),
    })
    # Always2.dat is searched before always.dat; loose Data files before both.
    write_mix(data / 'Always2.dat', {'nolod.dds': dds(16, 16, b'DXT1', 5, 168, 0x1B)})
    (data / 'emit.dds').write_bytes(dds(8, 8, b'DXT1', 1, 32, 0x1C))
    return data


class TutorialTextureBudgetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.data = build_fixture(Path(cls.temporary.name))
        cls.receipt = budget.build_receipt(cls.data)
        cls.rows = {row['name']: row for row in cls.receipt['textures']}

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def test_closure_follows_level_members_dep_and_render_object_references(self):
        closure = self.receipt['closure']
        self.assertEqual(closure['seed_sources'], {'level_mix_member': 1, 'level_dep': 2})
        self.assertEqual(closure['models_resolved'], 3)  # lvl, dep_model, other via HLOD
        self.assertEqual(closure['unresolved_model_names'], ['missing_model.w3d'])
        self.assertEqual(self.receipt['missing_archives'], ['always.dbs'])
        self.assertEqual([m['source'] for m in self.receipt['mount_order']],
                         ['Data/', 'Always2.dat', 'always.dat', 'M00_Tutorial.mix'])

    def test_only_the_selected_prelit_wrapper_is_followed(self):
        self.assertIn('lm_selected.tga', self.rows)
        self.assertNotIn('lm_skipped.tga', self.rows)
        self.assertEqual(self.rows['lm_selected.tga']['origins'], {'prelit_lightmap_multi_pass': 1})
        vertex = budget.build_receipt(self.data, prelit_mode='vertex')
        names = {row['name'] for row in vertex['textures']}
        self.assertNotIn('lm_selected.tga', names)
        self.assertNotIn('lm_skipped.tga', names)

    def test_native_compressed_chain_after_ddsfile_drops_two_levels(self):
        row = self.rows['tex_native.tga']  # names are lower-cased like the asset manager
        self.assertEqual(row['path'], 'native_compressed')
        self.assertEqual(row['upload_levels'], 5)  # 7 file levels - 2
        self.assertEqual(row['gpu_bytes'], 2048 + 512 + 128 + 32 + 8)
        self.assertEqual(row['cpu_decode_texels'], 0)

    def test_sub_block_tail_forces_full_decode_and_vitagl_generated_chain(self):
        row = self.rows['tex_tail.tga']
        self.assertEqual(row['path'], 'cpu_decode_rgba8888')
        self.assertEqual(row['decode_reasons'], ['sub_block_tail_levels'])
        self.assertEqual(row['full_block_levels'], 3)
        self.assertEqual(row['cpu_decode_texels'], 64 * 16 + 32 * 8 + 16 * 4 + 8 * 4 + 4 * 4)
        self.assertEqual(row['retained_cpu_bytes'], row['cpu_decode_texels'] * 4)
        self.assertEqual(row['gpu_bytes'], 4096 + 1024 + 256 + 64 + 32)
        self.assertEqual(row['compressed_chain_bytes'], 1024 + 256 + 64 + 32 + 16)
        self.assertEqual(row['authored_levels_discarded_by_gl'], 4)

    def test_dxt3_is_decoded_per_pixel(self):
        row = self.rows['tex_dxt3.tga']
        self.assertEqual(row['decode_reasons'], ['format_dxt3'])
        self.assertTrue(row['per_pixel_decode'])
        self.assertEqual(row['gpu_bytes'], 32 * 32 * 4)
        self.assertEqual(row['compressed_chain_bytes'], 8 * 8 * 16)

    def test_tga16_level_zero_rgba8888_and_rvtx1_estimate(self):
        row = self.rows['tex_16.tga']
        self.assertEqual(row['path'], 'cpu_convert_rgba8888_level0')
        self.assertEqual((row['format'], row['width'], row['height']), ('A1R5G5B5', 16, 8))
        self.assertEqual(row['gpu_bytes'], 16 * 8 * 4)
        self.assertEqual(row['gpu_bytes_rvtx1_pack16'], 16 * 8 * 2)
        totals = self.receipt['totals']
        self.assertEqual(totals['gpu_bytes_estimate'] - totals['gpu_bytes_estimate_rvtx1_pack16'], 256)

    def test_mount_precedence_and_mip_request(self):
        self.assertEqual(self.rows['emit.tga']['source'], 'Data/')
        self.assertEqual(self.rows['emit.tga']['width'], 8)
        self.assertEqual(self.rows['emit.tga']['origins'], {'emitter': 1})
        nolod = self.rows['nolod.tga']
        self.assertEqual((nolod['source'], nolod['width']), ('Always2.dat', 16))
        self.assertEqual(nolod['requests'], {'1': 1})
        self.assertEqual((nolod['upload_levels'], nolod['gpu_bytes']), (1, 128))

    def test_fallbacks(self):
        self.assertEqual(self.rows['ghost.tga']['path'], 'fallback_missing')
        self.assertEqual(self.rows['truncated.tga']['path'], 'fallback_truncated_dds')

    def test_duplicates_are_reported_by_name_only(self):
        self.assertEqual(self.receipt['byte_identical_source_groups'],
                         [['always.dat:dup_a.dds', 'always.dat:dup_b.dds']])
        self.assertEqual(self.rows['variant.tga']['source_member'], 'variant.dds')
        self.assertEqual(self.rows['variant.dds']['source_member'], 'variant.dds')

    def test_ranked_savings(self):
        ranked = {c['id']: c for c in self.receipt['savings_ranked']}
        self.assertEqual(ranked['dxt_sub_block_tail_keep_compressed']['gpu_bytes_saved_estimate'],
                         5472 - 1392)
        self.assertEqual(ranked['dxt3_native_ubc2']['gpu_bytes_saved_estimate'], 4096 - 1024)
        self.assertEqual(ranked['tga16_keep_16bit']['gpu_bytes_saved_estimate'], 256)
        self.assertEqual(ranked['duplicate_name_variants']['gpu_bytes_saved_estimate'], 32)
        order = [c['id'] for c in self.receipt['savings_ranked']]
        self.assertEqual(order[:4], ['dxt_sub_block_tail_keep_compressed', 'dxt3_native_ubc2',
                                     'tga16_keep_16bit', 'duplicate_name_variants'])
        self.assertEqual([c['rank'] for c in self.receipt['savings_ranked']],
                         list(range(1, len(order) + 1)))

    def test_receipt_carries_no_asset_bytes(self):
        text = json.dumps(self.receipt)
        self.assertNotIn('abababab', text.lower())
        self.assertNotIn('1111111111', text)
        self.assertFalse(self.receipt['runtime_verified'])

    def test_cli_writes_receipt(self):
        output = Path(self.temporary.name) / 'out' / 'receipt.json'
        stream = io.StringIO()
        with redirect_stdout(stream):
            self.assertEqual(budget.main(['--data', str(self.data), '--output', str(output),
                                          '--top', '3']), 0)
        self.assertEqual(json.loads(output.read_text())['totals']['texture_keys'],
                         len(self.receipt['textures']))
        self.assertIn('ranked savings:', stream.getvalue())

    def test_model_helpers_match_vitagl_allocation_rules(self):
        self.assertEqual(budget.vitagl_linear_bytes(223, 256), 224 * 256 * 4)
        self.assertEqual(budget.vitagl_generated_chain_bytes(4, 4), 8 * 4 * 4 + 8 * 2 * 4 + 8 * 1 * 4)
        self.assertEqual(budget.ddsfile_mip_levels(0), 1)
        self.assertEqual(budget.ddsfile_mip_levels(2), 1)
        self.assertEqual(budget.ddsfile_mip_levels(9), 7)
        self.assertEqual(budget.mip_request(None), 0)
        self.assertEqual(budget.mip_request(0x0004 | 0x00c0), 1)
        self.assertEqual(budget.mip_request(0x0080), 3)
        # DDSFileClass stops dividing at one block, unlike block-rounded files.
        self.assertEqual(budget.ddsfile_chain_bytes(64, 16, 'DXT5', 5), 1024 + 256 + 64 + 16 + 16)


if __name__ == '__main__':
    unittest.main()
