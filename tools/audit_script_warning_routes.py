#!/usr/bin/env python3
"""Retain the remaining compiler-warning denominator and its authored owners."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

from tools.audit_mission_content_bindings import masked
from tools.audit_script_binding_occurrences import inventory as binding_inventory

OWNERS = {
    'Mission10.cpp': ('M10_Apache_Controller', 'M10_Apache'),
    'mission08.cpp': ('M08_Apache_Controller', 'M08_Apache'),
    'Test_PDS.cpp': ('PDS_Test_Inventory',),
    'Test_RMV_Toolkit.cpp': ('RMV_Engineer_Wander',),
}


def script_section(source, name):
    declarations = list(re.finditer(r'\bDECLARE_SCRIPT\s*\(\s*(\w+)', masked(source, strings=True)))
    matches = [item for item in declarations if item[1] == name]
    if len(matches) != 1:
        raise ValueError('Missing or ambiguous script owner: ' + name)
    match = matches[0]
    end = next((item.start() for item in declarations if item.start() > match.start()), len(source))
    return source[match.start():end]


def inventory(root, directory):
    path = root / 'reports/generated/sweeps/script_compiler_diagnostics.json'
    diagnostics = json.loads(path.read_text())
    retail = json.loads((root / 'reports/generated/sweeps/retail.json').read_text())
    rows = []
    for unit in diagnostics['rows']:
        for candidate in unit['review_candidates']:
            if unit['name'] not in OWNERS:
                raise ValueError('Unreviewed diagnostic owner: ' + unit['name'])
            source = root / 'staging/scripts' / unit['name']
            data = source.read_bytes()
            if hashlib.sha256(data).hexdigest() != unit['source_sha256']:
                raise ValueError('Stale compiler source identity')
            owner = OWNERS[unit['name']][0]
            section = script_section(data.decode('latin1'), owner)
            rows.append({'unit': unit['name'], 'script': owner, 'status': 'unknown',
                         'evidence_class': 'compiler_diagnostic_and_source_owner_review',
                         'diagnostic': candidate, 'source_sha256': unit['source_sha256'],
                         'script_section_sha256': hashlib.sha256(section.encode('latin1')).hexdigest()})
    surfaces = []
    for unit, names in OWNERS.items():
        for name in names:
            binding = binding_inventory(directory, retail, name)
            surfaces.append({'unit': unit, 'script': name, 'status': 'unknown',
                             'maps_scanned': binding['total'], 'bindings': binding['binding_count'],
                             'map_rows': binding['rows']})
    return {'schema_version': 1, 'complete': False, 'total': len(rows),
            'rows': rows, 'counts': dict(Counter(row['status'] for row in rows)),
            'compiler_inventory_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'binding_surfaces': surfaces,
            'limits': ['Source owners and authored bindings do not establish live event/timer delivery.',
                       'Apache valid indices are 0..2; area -1 is a distinct no-active-area sentinel.',
                       'The sprintf warnings cover full int range; array/index provenance must be assessed first.',
                       'The technician reconstructs a pointer then replaces it with a literal before animation use.',
                       'No medkit pointer sender was established; a receiver cast alone does not authorize token substitution.',
                       'Uninitialized omitted Apache slots and save/reload values require further evidence.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bindings-directory', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = inventory(Path(__file__).resolve().parents[1], args.bindings_directory)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'warnings': result['total'], 'binding_scripts': len(result['binding_surfaces'])}))


if __name__ == '__main__':
    main()
