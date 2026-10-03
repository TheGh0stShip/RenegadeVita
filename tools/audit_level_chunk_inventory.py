#!/usr/bin/env python3
"""Inventory bounded LSD/LDD chunk metadata across every supplied map."""
import argparse
import hashlib
import json
from pathlib import Path
from tools.audit_m13_level_owners import chunks
from tools.audit_sweep_retail import map_names
from tools.renegade_cinematic_dependency_scan import MixArchive


def summarize(data):
    grouped = {}
    def visit(nodes, ancestry=()):
        for node in nodes:
            key = ancestry + (node.kind,)
            row = grouped.setdefault(key, {'chunk_path': [f'0x{k:08X}' for k in key],
                                           'count': 0, 'first_offset': node.offset,
                                           'payload_bytes_sum': 0, 'status': 'unknown'})
            row['count'] += 1
            row['payload_bytes_sum'] += len(node.data)
            visit(node.children, key)
    visit(chunks(data))
    return sorted(grouped.values(), key=lambda r: r['chunk_path'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    rows = []
    for name in map_names(args.data):
        path = args.data / name
        row = {'map': name, 'status': 'unknown', 'evidence_class': 'retail_chunk_metadata', 'members': []}
        if not path.is_file():
            row['input_missing'] = True
        else:
            archive = MixArchive(path)
            with path.open('rb') as stream:
                row['archive_sha256'] = hashlib.file_digest(stream, 'sha256').hexdigest()
                for index, (member, _, offset, size) in enumerate(archive.entry_records):
                    if Path(member).suffix.lower() not in ('.lsd', '.ldd'):
                        continue
                    stream.seek(offset)
                    data = stream.read(size)
                    result = {'member': member, 'index_record': index, 'bytes': size,
                              'sha256': hashlib.sha256(data).hexdigest(), 'status': 'unknown'}
                    try:
                        if len(data) != size:
                            raise ValueError('Truncated member')
                        result['chunk_paths'] = summarize(data)
                    except ValueError as error:
                        result['error_type'] = type(error).__name__
                    row['members'].append(result)
        rows.append(row)
    result = {'schema': 1, 'complete': False, 'rows': rows,
              'totals': {'maps': len(rows), 'members': sum(len(r['members']) for r in rows)},
              'scope': 'All LSD/LDD index records in supplied MIX maps; chunk ancestry retained',
              'limits': ['Conversation subsystem 0x40700 deliberately opaque',
                         'Chunk presence does not prove loader support or valid visibility/pathfinding data',
                         'Leaf payload semantics and runtime mounts remain unreviewed']}
    root = Path(__file__).resolve().parents[1]
    result['parser_inputs'] = [
        {'source': source, 'sha256': hashlib.sha256((root / source).read_bytes()).hexdigest()}
        for source in ('tools/audit_level_chunk_inventory.py', 'tools/audit_m13_level_owners.py',
                       'tools/audit_sweep_retail.py', 'tools/renegade_cinematic_dependency_scan.py')]
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result['totals']))


if __name__ == '__main__':
    main()
