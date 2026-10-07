"""Synthetic-fixture tests for tools/audit_campaign_asset_closure.py (no retail data)."""
import struct
import sys
import tempfile
import unittest
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import audit_campaign_asset_closure as closure_audit  # noqa: E402


def chunk(kind, payload=b'', nested=False):
    size = len(payload) | (0x80000000 if nested else 0)
    return struct.pack('<II', kind, size) + payload


def fixed(text, width):
    return text.encode('latin1').ljust(width, b'\0')


def write_mix(path, members):
    """Write a MIX1 archive as read by MixArchive (sorted CRC index, name table)."""
    entries = sorted(((zlib.crc32(name.upper().encode('latin1')) & 0xFFFFFFFF, name, data)
                      for name, data in members.items()), key=lambda row: row[0])
    body, offset, index = b'', 12, []
    for crc, _name, data in entries:
        index.append((crc, offset + len(body), len(data)))
        body += data
    index_offset = 12 + len(body)
    table = struct.pack('<I', len(entries)) + b''.join(struct.pack('<III', *row) for row in index)
    names_offset = index_offset + len(table)
    names = struct.pack('<I', len(entries)) + b''.join(
        bytes([len(name) + 1]) + name.encode('latin1') + b'\0' for _crc, name, _data in entries)
    path.write_bytes(struct.pack('<4sII', b'MIX1', index_offset, names_offset) + body + table + names)


def hlod(name, hierarchy, children):
    header = struct.pack('<II', 0x00010000, len(children)) + fixed(name, 16) + fixed(hierarchy, 16)
    array_header = struct.pack('<II', len(children), 0)
    subs = b''.join(chunk(0x704, struct.pack('<I', 0) + fixed(child, 32)) for child in children)
    lod = chunk(0x702, chunk(0x703, array_header) + subs, nested=True)
    return chunk(0x700, chunk(0x701, header) + lod, nested=True)


def mesh(name, container, textures):
    header = struct.pack('<II', 0, 0) + fixed(name, 16) + fixed(container, 16) + b'\0' * 8
    body = chunk(0x1F, header)
    names = b''.join(chunk(0x31 + 1 - 1, b'') for _ in ())  # keep layout simple
    tex = b''.join(chunk(0x30, chunk(0x32, tex.encode('latin1') + b'\0'), nested=True) for tex in textures)
    body += chunk(0x31, tex, nested=True) + names
    return chunk(0x0, body, nested=True)


def dep(names):
    body = b''.join(bytes([1, len(name) + 1]) + name.encode('latin1') + b'\0' for name in names)
    return chunk(0x04020527, body)


class PathEmulation(unittest.TestCase):
    def test_normalize_rejects_what_the_port_rejects(self):
        for bad in ('', '/x', '\\x', 'C:foo', 'a/../b', './a', 'a:b'):
            self.assertIsNone(closure_audit.normalize_logical(bad)[0], bad)
        self.assertEqual(closure_audit.normalize_logical('Data\\\\Movies//R_L01.bik')[0], 'Data/Movies/R_L01.bik')

    def test_case_insensitive_component_resolution_and_namespace_diversion(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'Data' / 'Movies').mkdir(parents=True)
            (root / 'Data' / 'Movies' / 'R_L01.BIK').write_bytes(b'x')
            tree = closure_audit.LooseTree(root)
            found = tree.resolve('data\\movies\\r_l01.bik')
            self.assertEqual(found['status'], 'found')
            self.assertTrue(found['case_only'])
            self.assertEqual(tree.resolve('Data/Movies/R_L01.BIK')['case_only'], False)
            self.assertEqual(tree.resolve('save\\a.sav')['status'], 'diverted')
            self.assertEqual(tree.resolve('Data/../x')['status'], 'rejected')
            self.assertEqual(tree.resolve('Data/Movies/none.bik')['status'], 'missing')


class ParsersAndModel(unittest.TestCase):
    def test_dep_records_and_placeholders(self):
        names, issues = closure_audit.read_dep(dep(['A.w3d', '.w3d', 'COM^SAT.w3d']))
        self.assertEqual(names, ['A.w3d', '.w3d', 'COM^SAT.w3d'])
        self.assertEqual(issues, [])
        self.assertEqual(closure_audit.read_dep(b'\0' * 8)[1], ['unexpected dependency root chunk 0x00000000'])

    def test_w3d_hlod_children_and_textures(self):
        data = hlod('TANK', 'S_TANK', ['TANK.BODY', 'NULL']) + mesh('BODY', 'TANK', ['body.tga'])
        info = closure_audit.parse_w3d(data)
        self.assertEqual(info['hlods'][0]['children'], [('TANK.BODY', 'lod'), ('NULL', 'lod')])
        self.assertEqual(info['hlods'][0]['hierarchy'], 'S_TANK')
        self.assertIn(('body.tga', 'TANK.BODY'), info['textures'])
        self.assertIn('TANK.BODY', info['declared'])

    def test_texture_candidates_follow_ddsfile_rule(self):
        self.assertEqual(closure_audit.texture_candidates('Foo.TGA'), ['foo.dds', 'foo.tga'])
        self.assertEqual(closure_audit.texture_candidates('x.dds'), ['x.dds', 'x.dds'])
        self.assertIn('shorter', closure_audit.texture_candidates('ab')[0])


class MountAndClosure(unittest.TestCase):
    def build(self, tmp, mission_members, shared=None):
        data = Path(tmp) / 'retail' / 'Data'
        data.mkdir(parents=True)
        write_mix(data / 'always.dat', shared or {'tank.w3d': hlod('TANK', 'S_TANK', ['TANK.BODY', 'GHOST']) +
                                                   mesh('BODY', 'TANK', ['body.tga'])})
        write_mix(data / 'M01.mix', mission_members)
        write_mix(data / 'M09.mix', {'only9.w3d': b''})
        return closure_audit.Context(data)

    def test_mount_orders(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self.build(tmp, {'a.w3d': b''})
            self.assertEqual(closure_audit.Mount(ctx, 'M01.mix', 'vita').archive_names[-1], 'M01.mix')
            self.assertEqual(closure_audit.Mount(ctx, 'M09.mix', 'vita').archive_names[0], 'M09.mix')
            self.assertEqual(closure_audit.Mount(ctx, 'M01.mix', 'pc').archive_names[3:],
                             ['M01.mix', 'M09.mix'])
            self.assertEqual(closure_audit.Mount(ctx, 'M09.mix', 'pc').archive_names[0], 'M09.mix')
            self.assertEqual(closure_audit.Mount(ctx, 'M09.mix', 'pc').search_start, 'M09.mix')
            self.assertIsNone(closure_audit.Mount(ctx, 'M01.mix', 'pc').search_start)

    def test_lookup_is_case_insensitive_and_first_provider_wins(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self.build(tmp, {'TANK.W3D': b'mission copy'})
            mount = closure_audit.Mount(ctx, 'M01.mix', 'vita')
            hit = mount.lookup('Tank.w3d')
            self.assertEqual(hit['provider'], 'always.dat')
            self.assertEqual(len(mount.lookup_all('tank.w3d')), 2)
            self.assertIsNone(mount.lookup('absent.w3d'))

    def test_pc_order_finds_other_mission_mix_but_vita_does_not(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self.build(tmp, {'a.w3d': b''})
            self.assertIsNone(closure_audit.Mount(ctx, 'M01.mix', 'vita').lookup('only9.w3d'))
            self.assertEqual(closure_audit.Mount(ctx, 'M01.mix', 'pc').lookup('only9.w3d')['provider'], 'M09.mix')

    def test_resolve_robj_verdicts(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self.build(tmp, {'a.w3d': b''})
            closure = closure_audit.Closure(ctx, 'M01.mix')
            self.assertIsNotNone(closure.load('tank.w3d', 'always.dep'))
            self.assertEqual(closure.resolve_robj('TANK.BODY'), 'declared')
            self.assertEqual(closure.resolve_robj('NULL'), 'builtin')
            self.assertEqual(closure.resolve_robj('GHOST'), 'missing')
            self.assertEqual(closure.on_demand_filename('TANK.BODY'), 'TANK.w3d')
            self.assertEqual(closure.resolve_robj('TANK.GHOSTMESH'), 'file-lacks-prototype')

    def test_audit_mission_end_to_end_reports_missing_child_and_texture(self):
        with tempfile.TemporaryDirectory() as tmp:
            members = {'m01.dep': dep(['tank.w3d', 'missing.w3d', '.w3d']),
                       'always.dep': b''}
            ctx = self.build(tmp, members)
            ctx.sound_presets_for = lambda closure, mission: {
                'sound_files': [], 'conversation_text': [], 'conversation_sounds': [], 'summary': {}}
            ctx.sound_preset_names = lambda: {}

            def no_audio(ctx_, closure_, mission_, report_, unresolved_, count_):
                return None

            report = closure_audit.audit_mission(ctx, 'M01', no_audio)
            by_category = {}
            for row in report['unresolved']:
                by_category.setdefault(row['category'], []).append(row['name'])
            self.assertEqual(by_category['dep_w3d'], ['missing.w3d'])
            self.assertEqual(by_category['hlod_child'], ['GHOST'])
            self.assertEqual(by_category['texture'], ['body.tga'])
            self.assertEqual(report['dep_placeholder_records'], 1)
            texture_row = [r for r in report['unresolved'] if r['category'] == 'texture'][0]
            self.assertEqual(texture_row['candidates_probed'], ['body.dds', 'body.tga'])
            self.assertFalse(texture_row['pc_order_resolves'])

    def test_archive_name_hazards_flag_diverted_and_rejected_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp) / 'retail' / 'Data'
            data.mkdir(parents=True)
            write_mix(data / 'always.dat', {'save\\x.w3d': b'', 'a:b.dds': b'', 'ok.w3d': b'', 'sp ace.wav': b''})
            ctx = closure_audit.Context(data)
            result = closure_audit.archive_name_hazards(ctx, [])
            self.assertEqual(result['members_scanned'], 4)
            self.assertEqual(result['rejected_by_loose_translation'], {'contains-colon': 1})
            self.assertEqual(result['diverted_to_writable_namespace'], {'save': 1})
            self.assertEqual(result['names_with_whitespace'], 1)

    def test_pc_only_means_pc_finds_a_provider_the_vita_order_never_mounts(self):
        with tempfile.TemporaryDirectory() as tmp:
            members = {'m01.dep': dep(['tank.w3d']), 'always.dep': b''}
            ctx = self.build(tmp, members)
            write_mix(Path(tmp) / 'retail' / 'Data' / 'M08.mix', {'body.dds': b'DDS '})
            ctx = closure_audit.Context(Path(tmp) / 'retail' / 'Data')
            ctx.sound_presets_for = lambda closure, mission: {
                'sound_files': [], 'conversation_text': [], 'conversation_sounds': [], 'summary': {}}
            ctx.sound_preset_names = lambda: {}
            report = closure_audit.audit_mission(ctx, 'M01', lambda *a: None)
            texture = [r for r in report['unresolved'] if r['category'] == 'texture'][0]
            self.assertTrue(texture['pc_order_resolves'])
            self.assertEqual(texture['pc_providers'], ['M08.mix'])
            child = [r for r in report['unresolved'] if r['category'] == 'hlod_child'][0]
            self.assertFalse(child['pc_order_resolves'])

    def test_markdown_renders_minimal_summary(self):
        summary = {'order_vita': ['a'], 'order_pc': ['b'], 'unmounted_by_original_game_init': [],
                   'missions': [{'mission': 'M01', 'archive': 'M01.mix', 'categories': {
                       'texture': {'checked': 1, 'resolved': 0, 'unresolved': 1}},
                       'unresolved': [{'mission': 'M01', 'category': 'texture', 'name': 'x.tga',
                                       'referenced_by': 'a.w3d:A', 'pc_order_resolves': True,
                                       'pc_providers': ['M08.mix']}],
                       'w3d_files_loaded': 1, 'dep_name_flags': [], 'texture_name_flags': [],
                       'texture_tga_only': [], 'mission_members_shadowed_by_earlier_provider': [],
                       'always_dep_providers': ['Always2.dat'],
                       'preload_dependent_prototypes': {'count': 0, 'only_always_dep': 0}}],
                   'movies': [], 'retail_case_collisions': []}
        text = closure_audit.render_markdown(summary)
        self.assertIn('Port-side gaps', text)
        self.assertIn('`x.tga`', text)
        self.assertIn('M08.mix', text)


if __name__ == '__main__':
    unittest.main()
