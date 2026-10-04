#!/usr/bin/env python3
"""Compare all-map authored script bindings with a retained live host registry."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


def compare(binding, registry, expected):
    if (binding['archive_sha256'] != expected['archive_sha256'] or
            binding['objects_ddb_sha256'] != expected['objects_ddb_sha256']):
        raise ValueError('Binding receipt data identity mismatch')
    names = {entry['name'].lower() for entry in registry['registry_entries']}
    missing = []
    kinds = Counter()
    for row in binding['bindings']:
        kinds[row['binding_kind']] += 1
        if row['name'].lower() not in names:
            provenance = {key: row[key] for key in ('name', 'binding_kind', 'member', 'offset',
                                                  'definition_id', 'spawner_id') if key in row}
            missing.append(provenance)
    return {'map': binding['map'], 'archive_sha256': binding['archive_sha256'],
            'objects_ddb_sha256': binding['objects_ddb_sha256'],
            'bindings': len(binding['bindings']), 'binding_kinds': dict(sorted(kinds.items())),
            'registered_bindings': len(binding['bindings']) - len(missing),
            'unregistered_bindings': len(missing), 'missing': missing,
            'status': 'unknown', 'evidence_class': 'authored_metadata_and_host_live_script_registry'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bindings-directory', required=True, type=Path)
    parser.add_argument('--retail', required=True, type=Path)
    parser.add_argument('--registry', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    registry = json.loads(args.registry.read_text())
    retail = json.loads(args.retail.read_text())
    expected = {row['map']: row for row in retail['rows']}
    seen = set()
    rows = []
    for path in sorted(args.bindings_directory.glob('*bindings.json')):
        binding = json.loads(path.read_text())
        name = binding['map']
        if name in seen or name not in expected:
            raise ValueError('Unexpected or duplicate map binding receipt')
        seen.add(name)
        row = compare(binding, registry, expected[name])
        row['binding_receipt_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
        rows.append(row)
    if seen != set(expected):
        raise ValueError('Incomplete all-map binding denominator')
    receipt = {'schema_version': 1, 'complete': False, 'total': len(rows), 'rows': rows,
               'counts': dict(Counter(row['status'] for row in rows)),
               'totals': {key: sum(row[key] for row in rows)
                          for key in ('bindings', 'registered_bindings', 'unregistered_bindings')},
               'registry_sha256': hashlib.sha256(args.registry.read_bytes()).hexdigest(),
               'retail_sha256': hashlib.sha256(args.retail.read_bytes()).hexdigest(),
               'parser_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               'limits': ['Authored binding membership does not prove script creation or callbacks.',
                          'Runtime-created/computed names and retail DLL equivalence remain open.',
                          'Data hashes match retained receipts; this does not prove mounted runtime precedence.',
                          'Host registration is separate from ARM/physical mission acceptance.']}
    args.output.write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({'maps': len(rows), **receipt['totals']}))


if __name__ == '__main__':
    main()
