#!/usr/bin/env python3
"""Validate visibility table serialization bounds without decompressing assets."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from tools.audit_m13_level_owners import chunks, microchunks
from tools.renegade_cinematic_dependency_scan import MixArchive


def validate(data):
    nodes = chunks(data)
    if not nodes or nodes[0].kind != 0x34500000:
        raise ValueError('Missing first visibility variables chunk')
    fields = dict(microchunks(nodes[0].data))
    def number(key):
        if len(fields.get(key, b'')) != 4:
            raise ValueError('Missing or wrong-width visibility variable')
        return struct.unpack('<I', fields[key])[0]
    version, objects, sectors = number(0), number(2), number(3)
    findings, ids = [], set()
    pending = None
    tables = compressed = 0
    for node in nodes[1:]:
        if node.kind == 0x34500001:
            if len(node.data) != 4:
                raise ValueError('Wrong-width table ID')
            if pending is not None:
                findings.append('id_without_data')
            pending = struct.unpack('<I', node.data)[0]
        elif node.kind == 0x34500002:
            if pending is None or pending >= sectors:
                findings.append('table_id_outside_sector_count')
            if pending in ids:
                findings.append('duplicate_table_id')
            ids.add(pending)
            children = chunks(node.data)
            if not children or children[0].kind != 1 or len(children[0].data) != 4:
                raise ValueError('Missing compressed byte count')
            declared = struct.unpack('<I', children[0].data)[0]
            payloads = [n for n in children[1:] if n.kind in (2, 3)]
            if len(payloads) != 1 or len(payloads[0].data) != declared:
                findings.append('compressed_size_mismatch')
            if any(n.kind == 2 for n in payloads):
                findings.append('obsolete_lzhl_payload')
            compressed += declared
            tables += 1
            pending = None
        else:
            findings.append('unknown_manager_chunk')
    if pending is not None:
        findings.append('id_without_data')
    return {'version': version, 'vis_objects': objects, 'vis_sectors': sectors,
            'tables': tables, 'compressed_bytes': compressed,
            'obsolete_version': version < 0x10001, 'findings': sorted(set(findings))}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data', type=Path, required=True)
    p.add_argument('--presence', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    receipt = args.presence.read_bytes()
    rows = []
    for owner in json.loads(receipt)['rows']:
        if owner['name'] != 'visibility_tables':
            continue
        archive = MixArchive(args.data / owner['map'])
        for candidate in owner['candidates']:
            data = archive.read_binary(candidate['member'])
            if hashlib.sha256(data).hexdigest() != candidate['member_sha256']:
                raise ValueError('Member identity mismatch')
            offset = candidate['first_offset']
            kind, size = struct.unpack_from('<II', data, offset)
            end = offset + 8 + (size & 0x7fffffff)
            if kind != 0x4700 or end > len(data):
                raise ValueError('Visibility chunk boundary mismatch')
            row = {'map': owner['map'], 'member': candidate['member'], 'offset': offset,
                   'status': 'unknown', 'evidence_class': 'retail_serialization_bounds',
                   'member_sha256': candidate['member_sha256']}
            try:
                row.update(validate(data[offset+8:end]))
            except ValueError:
                row['parser_error'] = True
            rows.append(row)
    args.output.write_text(json.dumps({'schema': 1, 'complete': False, 'rows': rows,
        'presence_sha256': hashlib.sha256(receipt).hexdigest(),
        'limits': ['No LZO decompression or visibility correctness proof',
                   'First matching chunk occurrence only; repeated chunks require separate review']}, indent=2)+'\n')
    print(json.dumps({'rows': len(rows), 'parser_errors': sum(bool(r.get('parser_error')) for r in rows),
                      'findings': sum(len(r.get('findings', [])) for r in rows)}))


if __name__ == '__main__':
    main()
