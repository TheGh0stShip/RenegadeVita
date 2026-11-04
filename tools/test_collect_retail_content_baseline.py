"""Asset-free counterexamples for a retail-first, non-filtering denominator."""
import hashlib
import contextlib
import io
import json
from pathlib import Path
import struct
import tempfile
import unittest
import zlib
from unittest.mock import patch

from tools.collect_retail_content_baseline import ROOT, collect, flow_records, main, member_leads, resolve_retail, summary
from tools.test_m13_level_owners import chunk, definition, integer, micro


def write_mix(path, members):
    # Keep duplicate names; each physical index record is a separate lead.
    body, records = b'', []
    for name, payload in members:
        records.append((zlib.crc32(name.upper().encode('ascii')), 12 + len(body), len(payload)))
        body += payload
    index = struct.pack('<I', len(records)) + b''.join(struct.pack('<III', *row) for row in records)
    names = struct.pack('<I', len(records))
    for name, _ in members:
        encoded = name.encode('ascii') + b'\0'
        names += bytes([len(encoded)]) + encoded
    path.write_bytes(struct.pack('<4sII', b'MIX1', 12 + len(body), 12 + len(body) + len(index)) + body + index + names)


class RetailBaselineTests(unittest.TestCase):
    def test_campaign_and_unknown_authored_behavior_do_not_depend_on_port(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data = root / 'Data'
            data.mkdir()
            # Deliberately no upstream/, staging/, CMakeLists or native binary.
            write_mix(data / 'always.dat', [('campaign.ini',
                      b'[Campaign]\n0=Level M99.mix\n1=Score\n2=NewRetailAction\n')])
            script = chunk(131001135, micro(1, b'NotInReleasedSource\0') +
                           micro(2, b'payload\0') + micro(4, integer(0xffffffff)))
            write_mix(data / 'M99.mix', [('unlisted.ldd', script),
                      ('sequence.txt', b'0 Unknown_Retail_Command,hand_off\n-60 Play_Audio,voice.wav\n')])
            before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in data.iterdir()}
            result = collect(root)
            after = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in data.iterdir()}
            self.assertEqual(before, after, 'read-only discovery changed retail bytes')
            self.assertFalse(result['source_or_port_graph_consulted'])
            self.assertEqual([s['resource'] for s in result['campaign_flow'] if s['kind'] == 'level'], ['M99.mix'])
            mission = next(a for a in result['archives'] if a['name'] == 'M99.mix')
            bindings = mission['entries'][0]['discovery']['level_records']['script_records']
            self.assertEqual(bindings[0]['name'], 'NotInReleasedSource')
            self.assertEqual(bindings[0]['owner_token'], 0xffffffff)
            commands = mission['entries'][1]['discovery']['timed_command_candidates']
            self.assertEqual(commands[0]['command'], 'unknown_retail_command')
            self.assertEqual(commands[1]['time_units'], 'frames_at_30_hz')
            self.assertIn('unclassified_campaign_directive', [i['kind'] for i in result['discovery_issues']])
            public = summary(result)
            self.assertFalse(public['content_inventory_complete'])
            self.assertFalse(public['play_test_ready'])
            self.assertNotIn('payload', json.dumps(public))
            self.assertNotIn('NotInReleasedSource', json.dumps(public))

    def test_duplicate_members_and_competing_campaigns_are_not_silently_collapsed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data = root / 'Data'
            data.mkdir()
            flow = b'[Campaign]\n0=Level Missing.mix\n'
            write_mix(data / 'always.dat', [('campaign.ini', flow), ('campaign.ini', flow),
                                           ('scene.txt', b'0 UnknownA\n'), ('scene.txt', b'0 UnknownB\n')])
            result = collect(root)
            self.assertEqual(len(result['archives'][0]['entries']), 4)
            self.assertEqual(len(result['campaign_candidates']), 2)
            self.assertEqual(result['campaign_flow'], [])
            self.assertIn('campaign_precedence_unresolved', [i['kind'] for i in result['discovery_issues']])
            self.assertEqual(summary(result)['timed_command_candidates'], 2)

    def test_empty_invalid_and_ambiguous_inputs_cannot_look_complete(self):
        for payload in (b'[Campaign]\n', b'[Campaign]\n0=Score\n0=Level X.mix\n'):
            with self.assertRaises(ValueError):
                flow_records(payload)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'Data').mkdir()
            (root / 'Data/broken.mix').write_bytes(b'MIX1')
            result = collect(root)
            self.assertEqual(result['discovery_issues'][0]['kind'], 'archive_parse')
            self.assertFalse(summary(result)['play_test_ready'])
            for name in ('../outside', '/absolute', 'Data/../other', 'ux0:secret'):
                with self.assertRaises(ValueError):
                    resolve_retail(root, name)
            (root / 'Data/NAME').touch()
            (root / 'Data/name').touch()
            with self.assertRaisesRegex(ValueError, 'Ambiguous'):
                resolve_retail(root, 'Data/name')

    def test_crc_mismatch_keeps_unclassified_entry_and_root_override_is_not_ignored(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data = root / 'Data'
            data.mkdir()
            path = data / 'always.dat'
            write_mix(path, [('campaign.ini', b'[Campaign]\n0=Score\n')])
            raw = bytearray(path.read_bytes())
            index = struct.unpack_from('<I', raw, 4)[0]
            raw[index + 4] ^= 1
            path.write_bytes(raw)
            (root / 'campaign.ini').write_text('[Campaign]\n0=NewUnknownAction\n')
            result = collect(root)
            self.assertIn('crc_name_mismatch', [i['kind'] for i in result['discovery_issues']])
            self.assertEqual(len(result['archives'][0]['entries']), 1)
            self.assertEqual(result['campaign_candidates'][0]['entry'], 'loose:campaign.ini')
            self.assertEqual(result['campaign_flow'][0]['kind'], 'newunknownaction')

    def test_unknown_chunks_definitions_and_untimed_text_remain_visible(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data = root / 'Data'
            data.mkdir()
            write_mix(data / 'anything.mix', [
                ('unknown.ldd', chunk(0x789abcde, b'unknown record')),
                ('all.ddb', definition(0x78901234, 0xffffffff, b'')),
                ('unknown.txt', b'NotATimedCommand\n; comment\n-30 Unknown_Verb,a\n'),
                ('campaign.ini', b'[Campaign]\n1=Level anything.mix extra\n[Other]\nKey=Other value\n')])
            result = collect(root)
            entries = {e['name']: e for e in result['archives'][0]['entries']}
            self.assertEqual(entries['unknown.ldd']['discovery']['chunk_path_census'][0]['path'], ['0x789abcde'])
            self.assertIn(0xffffffff, entries['all.ddb']['discovery']['definition_records'])
            text = entries['unknown.txt']['discovery']
            self.assertEqual(text['nonblank_lines'], 3)
            self.assertEqual(len(text['unclassified_text_lines']), 1)
            self.assertEqual(result['campaign_flow'][0]['tokens'][-1], 'extra')
            self.assertEqual(result['campaign_candidates'][0]['section_records'][1]['name'], 'Other')
            self.assertGreater(summary(result)['binary_chunk_nodes_open'], 1)

    def test_chunk_census_hashes_unsampled_nodes_and_separates_ancestor_paths(self):
        children = b''.join(chunk(0x5555, bytes([n])) for n in range(12))
        payload = chunk(0x7777, children, True) + chunk(0x8888, chunk(0x5555, b'other'), True)
        first = member_leads('scene.ldd', payload)
        path = ['0x00007777', '0x00005555']
        group = next(g for g in first['chunk_path_census'] if g['path'] == path)
        self.assertEqual(group['count'], 12)
        self.assertEqual(len(group['sample_offsets']), 8)
        self.assertEqual(first['chunk_node_count'], 15)
        changed_children = children[:-1] + b'Z'
        second = member_leads('scene.ldd', chunk(0x7777, changed_children, True) +
                              chunk(0x8888, chunk(0x5555, b'other'), True))
        changed = next(g for g in second['chunk_path_census'] if g['path'] == path)
        self.assertEqual(group['sample_offsets'], changed['sample_offsets'])
        self.assertNotEqual(group['all_node_records_sha256'], changed['all_node_records_sha256'])

    def test_archive_case_conflicts_cannot_collapse_entry_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data = root / 'Data'
            data.mkdir()
            for name in ('same.mix', 'SAME.mix'):
                write_mix(data / name, [('scene.txt', b'0 Unknown_Command\n')])
            result = collect(root)
            self.assertIn('archive_case_conflict', [i['kind'] for i in result['discovery_issues']])
            ids = [e['id'] for a in result['archives'] for e in a['entries']]
            self.assertEqual(len(set(ids)), 2)

    def test_cli_cannot_write_into_a_retail_tree_even_when_it_is_under_build(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'build') as directory:
            root = Path(directory)
            output = root / 'Data/metadata.json'
            with patch('sys.argv', ['collect', '--retail-root', str(root), '--private-output', str(output)]), \
                    contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                main()
            self.assertEqual(error.exception.code, 2)
            self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
