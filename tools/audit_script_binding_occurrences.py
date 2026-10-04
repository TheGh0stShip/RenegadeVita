#!/usr/bin/env python3
"""Count one script's authored bindings across a hash-verified all-map surface."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


def summarize(bindings, expected, script):
    if bindings['map'] != expected['map'] or bindings['archive_sha256'] != expected['archive_sha256']:
        raise ValueError('Map/archive identity mismatch')
    matches = [row for row in bindings['bindings'] if row['name'].lower() == script.lower()]
    return {'map': bindings['map'], 'status': 'unknown',
            'evidence_class': 'authored_script_binding_metadata',
            'archive_sha256': bindings['archive_sha256'],
            'objects_ddb_sha256': bindings['objects_ddb_sha256'],
            'binding_count': len(matches),
            'binding_kinds': dict(sorted(Counter(row['binding_kind'] for row in matches).items())),
            'parameter_field_counts': dict(sorted(Counter(str(len(row.get('parameter_fields', [])))
                                                         for row in matches).items()))}


def inventory(directory, retail, script):
    expected = {row['map']: row for row in retail['rows']}
    if len(expected) != len(retail['rows']):
        raise ValueError('Duplicate retail map')
    rows = []
    seen = set()
    for path in sorted(directory.glob('*bindings.json')):
        value = json.loads(path.read_text())
        name = value['map']
        if name not in expected or name in seen:
            raise ValueError('Unexpected or duplicate map')
        seen.add(name)
        row = summarize(value, expected[name], script)
        row['binding_receipt_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
        rows.append(row)
    if seen != set(expected):
        raise ValueError('Incomplete all-map denominator')
    return {'schema_version': 1, 'complete': False, 'script': script,
            'total': len(rows), 'rows': rows, 'counts': {'unknown': len(rows)},
            'binding_count': sum(row['binding_count'] for row in rows),
            'limits': ['Authored bindings do not establish instantiation, zone entry or callback execution.',
                       'Zero matches apply only to this retained binding surface; computed/runtime attachments remain open.',
                       'Camera object resolution, archive mounting precedence and native presentation remain unverified.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bindings-directory', type=Path, required=True)
    parser.add_argument('--retail', type=Path, required=True)
    parser.add_argument('--script', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = inventory(args.bindings_directory, json.loads(args.retail.read_text()), args.script)
    result['retail_inventory_sha256'] = hashlib.sha256(args.retail.read_bytes()).hexdigest()
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'maps': result['total'], 'bindings': result['binding_count']}))


if __name__ == '__main__':
    main()
