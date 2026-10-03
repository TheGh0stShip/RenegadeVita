#!/usr/bin/env python3
"""Run existing authored-binding discovery across every supplied MIX map.

Detailed level metadata stays private; public output contains counts and hashes.
This is the binding/registration portion of S4, not complete asset closure.
"""
import argparse
import hashlib
import json
from pathlib import Path

from tools.audit_mission_content_bindings import audit_map, source_scripts


def map_names(data):
    expected = {'M00_Tutorial.mix', 'M13.mix'} | {f'M{i:02}.mix' for i in range(1, 12)}
    supplied = {p.name for p in data.iterdir() if p.is_file() and p.suffix.lower() == '.mix'}
    by_case = {name.lower(): name for name in supplied}
    return sorted(supplied | {name for name in expected if name.lower() not in by_case})


def summarize(receipt, link):
    candidates = {}
    for row in link['registration_candidates']:
        if row['kind'] == 'script':
            candidates.setdefault(row['arguments'][0].lower(), []).append(row)
    names = {row['name'].lower() for row in receipt['discovered_scripts']}
    names.update(name.lower() for name in receipt['summary']['unknown_shipped_scripts'])
    unmatched = sorted(name for name in names if not any(
        row['defined_symbol_matches'] for row in candidates.get(name, [])))
    return {'map': receipt['map'], 'archive_sha256': receipt['archive_sha256'],
            'objects_ddb_sha256': receipt['objects_ddb_sha256'],
            'status': 'unknown', 'evidence_class': 'retail_metadata_and_arm_symbols',
            'level_bindings': receipt['summary']['level_bindings'],
            'discovered_bindings': receipt['summary']['all_discovered_bindings'],
            'discovered_script_names': len(names),
            'script_names_without_defined_registrar': unmatched,
            'structural_findings': receipt['summary']['structural_findings'],
            'not_located_definition_count': len(receipt['summary']['not_located_definition_ids']),
            'runtime_registration_verified': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--link-inventory', type=Path, required=True)
    parser.add_argument('--private-output', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    if not args.private_output.resolve().is_relative_to((root / 'build').resolve()):
        parser.error('detailed receipts must remain under build/')
    args.private_output.mkdir(parents=True, exist_ok=True)
    link_bytes = args.link_inventory.read_bytes()
    link = json.loads(link_bytes)
    scripts = source_scripts(root)
    rows = []
    for name in map_names(args.data):
        if not (args.data / name).is_file():
            row = {'map': name, 'status': 'unknown', 'evidence_class': 'input_inventory',
                   'input_missing': True}
        else:
            try:
                receipt = audit_map(root, args.data, name, scripts)
                (args.private_output / (Path(name).stem.lower() + '-bindings.json')).write_text(
                    json.dumps(receipt, indent=2) + '\n')
                row = summarize(receipt, link)
            except (OSError, ValueError) as error:
                row = {'map': name, 'status': 'unknown', 'evidence_class': 'parser_failure',
                       'error_type': type(error).__name__}
        rows.append(row)
        print(json.dumps(row), flush=True)
    result = {'schema': 1, 'sweep': 'S4', 'complete': False,
              'link_inventory_sha256': hashlib.sha256(link_bytes).hexdigest(),
              'scope': 'All supplied MIX filenames plus expected campaign maps; authored binding closure only',
              'open_risks': ['Missing inputs', 'Computed dependency names and IDs',
                             'Remaining S4 asset/loader classes', 'Frontend and global-only content',
                             'Parser failures are not exclusions', 'Runtime mount order and registration'],
              'total': len(rows), 'counts': {'unknown': len(rows)}, 'rows': rows}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    main()
