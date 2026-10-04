#!/usr/bin/env python3
"""Reconcile level SimplePersistFactory envelopes with ARM and host evidence.

Only sibling OBJPOINTER/OBJDATA envelopes identify candidates. Arbitrary leaf
IDs are not factory requests. Metadata cannot prove exact sibling instances.
"""
import argparse
import hashlib
import json
from pathlib import Path


def reconcile(levels, arm, host):
    linked = {}
    for row in arm['persist_load_methods']:
        linked.setdefault(row['chunk_id'], []).append(row)
    live = {row['chunk_id']: row for row in host['rows']}
    observations = {}
    risks = []
    for level in levels['rows']:
        if level.get('input_missing'):
            risks.append({'map': level['map'], 'reason': 'missing_archive'})
        for member in level['members']:
            if 'chunk_paths' not in member:
                risks.append({'map': level['map'], 'member': member['member'],
                              'reason': 'missing_chunk_metadata'})
                continue
            paths = {}
            for row in member['chunk_paths']:
                path = tuple(row['chunk_path'])
                if path in paths:
                    raise ValueError('Duplicate chunk ancestry')
                paths[path] = row
            for path, pointer in paths.items():
                if len(path) < 2 or int(path[-1], 16) != 0x00100100:
                    continue
                data_path = path[:-1] + ('0x00100101',)
                data = paths.get(data_path)
                if (not data or pointer['count'] <= 0 or
                        data['count'] != pointer['count'] or
                        pointer['payload_bytes_sum'] != pointer['count'] * 4):
                    risks.append({'map': level['map'], 'member': member['member'],
                                  'chunk_path': list(path), 'reason': 'incomplete_factory_envelope'})
                    continue
                chunk = int(path[-2], 16)
                observations.setdefault(chunk, []).append({
                    'map': level['map'], 'archive_sha256': level.get('archive_sha256'),
                    'member': member['member'], 'member_sha256': member['sha256'],
                    'index_record': member['index_record'], 'chunk_path': list(path[:-1]),
                    'first_pointer_offset': pointer['first_offset'],
                    'candidate_instances': pointer['count']})
    rows = []
    for chunk, occurrences in sorted(observations.items()):
        candidates = linked.get(chunk, [])
        host_row = live.get(chunk)
        rows.append({'chunk_id': chunk, 'chunk_id_hex': f'0x{chunk:08X}',
                     'candidate_instances': sum(o['candidate_instances'] for o in occurrences),
                     'occurrences': occurrences,
                     'arm_load_symbol_present': bool(candidates),
                     'arm_classes': sorted({r['class'] for r in candidates}),
                     'host_lookup_matches': bool(host_row and host_row['matches']),
                     'status': 'unknown',
                     'evidence_class': 'retail_metadata_arm_symbols_and_host_lookup'})
    return {'schema_version': 1, 'complete': False, 'rows': rows, 'risks': risks,
            'totals': {'maps': len(levels['rows']), 'factory_ids': len(rows),
                       'candidate_instances': sum(r['candidate_instances'] for r in rows),
                       'without_arm_symbol': sum(not r['arm_load_symbol_present'] for r in rows),
                       'without_host_lookup': sum(not r['host_lookup_matches'] for r in rows),
                       'metadata_risks': len(risks)},
            'inventory_scope': levels.get('scope', 'Input chunk metadata only'),
            'limits': ['Only supplied chunk metadata is covered; other data and saves remain open.',
                       'Aggregated paths identify candidate envelopes, not exact sibling ordering.',
                       'Manual/non-template factories and opaque subsystem payloads remain open.',
                       'Symbols and host lookup do not prove ARM registration or Load/Save behavior.',
                       'Definition class IDs are distinct from persistence chunk IDs.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--levels', required=True, type=Path)
    parser.add_argument('--arm', required=True, type=Path)
    parser.add_argument('--host', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    paths = [args.levels, args.arm, args.host]
    result = reconcile(*(json.loads(p.read_text()) for p in paths))
    result['inputs'] = [{'source': p.as_posix(), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
                        for p in paths]
    result['parser_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result['totals']))


if __name__ == '__main__':
    main()
