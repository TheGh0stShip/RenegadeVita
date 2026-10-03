#!/usr/bin/env python3
"""Resolve exact member-name leads across supplied archives and loose files.

No payloads are emitted; presence is not runtime mount or execution proof.
"""
import argparse
import hashlib
import json
from pathlib import Path
from tools.renegade_cinematic_dependency_scan import MixArchive


def file_hash(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def resolve(names, records, loose):
    result = {name.lower(): {'name': name.lower(), 'archive_candidates': [],
                             'loose_candidates': [], 'status': 'unknown'} for name in names}
    for archive, index, name, offset, size in records:
        if name.lower() in result:
            result[name.lower()]['archive_candidates'].append(
                {'archive': archive, 'index_record': index, 'member': name,
                 'offset': offset, 'bytes': size})
    for name in loose:
        if Path(name).name.lower() in result:
            result[Path(name).name.lower()]['loose_candidates'].append(name)
    return [result[name] for name in sorted(result)]


def audit(data, names):
    records, archives, errors = [], [], []
    for path in sorted(data.iterdir()):
        if not path.is_file() or path.suffix.lower() not in ('.mix', '.dat', '.dbs'):
            continue
        try:
            archive = MixArchive(path)
            archives.append({'archive': path.name, 'sha256': file_hash(path)})
            records.extend((path.name, index, name, offset, size)
                           for index, (name, _, offset, size) in enumerate(archive.entry_records))
        except (OSError, ValueError) as error:
            errors.append({'archive': path.name, 'error_type': type(error).__name__})
    loose = sorted(path.relative_to(data).as_posix() for path in data.rglob('*') if path.is_file())
    return {'schema': 1, 'complete': False, 'evidence_class': 'archive_index_and_loose_name_metadata',
            'archives': archives, 'archive_errors': errors, 'index_records_scanned': len(records),
            'rows': resolve(names, records, loose),
            'limits': ['Exact names only; computed aliases and other data roots remain open.',
                       'Missing names do not prove unreachable content or justify exclusion.',
                       'Presence does not establish runtime mount order or selected variant.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--retail-inventory', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    source = args.retail_inventory.read_bytes()
    inventory = json.loads(source)
    names = {name for row in inventory['rows'] for name in row['missing_cinematic_control_candidates']}
    result = audit(args.data, names)
    result['retail_inventory_sha256'] = hashlib.sha256(source).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'names': len(result['rows']), 'archives': len(result['archives']),
                      'records': result['index_records_scanned'], 'errors': len(result['archive_errors'])}))


if __name__ == '__main__':
    main()
