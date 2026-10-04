#!/usr/bin/env python3
"""Inventory every DDB index record in supplied retail MIX/DAT/DBS archives.

Only bounded chunk metadata is emitted; definition payloads stay private.
"""
import argparse
import hashlib
import json
from pathlib import Path

from tools.audit_level_chunk_inventory import summarize
from tools.audit_sweep_retail import map_names
from tools.renegade_cinematic_dependency_scan import MixArchive


def archive_names(data):
    required = set(map_names(data)) | {'always.dat', 'Always2.dat', 'always3.dat', 'always.dbs'}
    supplied = {p.name for p in data.iterdir()
                if p.is_file() and p.suffix.lower() in ('.mix', '.dat', '.dbs')}
    by_case = {name.lower(): name for name in supplied}
    return sorted(supplied | {name for name in required if name.lower() not in by_case})


def inventory(data):
    rows = []
    for name in archive_names(data):
        path = data / name
        row = {'map': name, 'status': 'unknown', 'evidence_class': 'retail_database_chunk_metadata',
               'members': []}
        if not path.is_file():
            row['input_missing'] = True
            rows.append(row)
            continue
        archive = MixArchive(path)
        with path.open('rb') as stream:
            row['archive_sha256'] = hashlib.file_digest(stream, 'sha256').hexdigest()
            for index, (member, _, offset, size) in enumerate(archive.entry_records):
                if Path(member).suffix.lower() != '.ddb':
                    continue
                stream.seek(offset)
                payload = stream.read(size)
                result = {'member': member, 'index_record': index, 'bytes': size,
                          'sha256': hashlib.sha256(payload).hexdigest(), 'status': 'unknown'}
                if len(payload) != size:
                    raise ValueError('Truncated database member')
                result['chunk_paths'] = summarize(payload)
                row['members'].append(result)
        rows.append(row)
    return {'schema': 1, 'complete': False, 'rows': rows,
            'totals': {'archives': len(rows), 'members': sum(len(r['members']) for r in rows),
                       'missing_archives': sum(bool(r.get('input_missing')) for r in rows)},
            'scope': 'Every DDB index record in supplied MIX/DAT/DBS archives, including duplicate names',
            'limits': ['Database payloads, definition class IDs and runtime precedence remain unreviewed.',
                       'Archive hashes identify supplied edition; they do not establish edition provenance.',
                       'Chunk metadata does not prove native loader support.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    result = inventory(args.data)
    root = Path(__file__).resolve().parents[1]
    sources = ['tools/audit_database_chunk_inventory.py', 'tools/audit_level_chunk_inventory.py',
               'tools/audit_m13_level_owners.py', 'tools/audit_sweep_retail.py',
               'tools/renegade_cinematic_dependency_scan.py']
    result['parser_inputs'] = [{'source': name,
                               'sha256': hashlib.sha256((root / name).read_bytes()).hexdigest()}
                              for name in sources]
    owners = ['staging/wwsaveload/definitionmgr.cpp', 'staging/wwsaveload/saveloadids.h',
              'upstream/CnC_Renegade/Code/Tools/LevelEdit/EditorChunkIDs.h',
              'upstream/CnC_Renegade/Code/Tools/LevelEdit/LevelEdit.dsp']
    result['owner_source_receipts'] = [{'source': name,
                                      'sha256': hashlib.sha256((root / name).read_bytes()).hexdigest()}
                                     for name in owners]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result['totals']))


if __name__ == '__main__':
    main()
