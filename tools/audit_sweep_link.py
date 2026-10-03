#!/usr/bin/env python3
"""Inventory staged translation units against one ARM target's build database.

Map mentions prove neither section retention nor factory registration.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def digest(data):
    return hashlib.sha256(data).hexdigest()


def inventory(root, database, target, map_bytes):
    prefix = f'CMakeFiles/{target}.dir/'
    selected = {}
    for entry in database:
        if not entry.get('output', '').startswith(prefix):
            continue
        source = (Path(entry['directory']) / entry['file']).resolve()
        selected[source] = entry['output']
    map_text = map_bytes.decode('utf-8', errors='replace')
    rows = []
    for source in sorted((root / 'staging').rglob('*')):
        if source.suffix.lower() not in ('.cpp', '.c', '.cc', '.cxx'):
            continue
        name = source.relative_to(root).as_posix()
        obj = selected.get(source.resolve())
        rows.append({'id': digest(name.encode()), 'source': name,
                     'source_sha256': digest(source.read_bytes()),
                     'selected_for_target': obj is not None,
                     'map_mentions_object': bool(obj and obj in map_text),
                     'status': 'unknown', 'evidence_class': 'build_metadata',
                     'registration_verified': False})
    return {'schema': 1, 'sweep': 'S3', 'target': target, 'complete': False,
            'scope': 'All staged C/C++ translation units; includes potential non-runtime units',
            'open_risks': ['Upstream units absent from staging', 'Static and manual registrars',
                           'Discarded versus retained sections', 'Retail factory IDs',
                           'Selected sources may differ from the retained build inputs'],
            'map_sha256': digest(map_bytes), 'total': len(rows),
            'selected': sum(r['selected_for_target'] for r in rows),
            'map_mentioned': sum(r['map_mentions_object'] for r in rows),
            'counts': {'unknown': len(rows)}, 'rows': rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--map', type=Path, required=True)
    parser.add_argument('--target', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    database = json.loads(subprocess.check_output(
        ['ninja', '-C', str(args.build), '-t', 'compdb'], text=True, timeout=30))
    result = inventory(root, database, args.target, args.map.read_bytes())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ('total', 'selected', 'map_mentioned', 'counts')}))


if __name__ == '__main__':
    main()
