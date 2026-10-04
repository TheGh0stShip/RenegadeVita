#!/usr/bin/env python3
"""Bind missing all-map definition fields to inspected original caller bodies.

Unchanged source proves preserved conditional behavior, not runtime execution.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

from tools.audit_sweep_port_guards import mask_noncode


OWNERS = {
    'muzzle': ('Combat/weapons.cpp', 'WeaponClass::Do_Firing_Effects'),
    'eject': ('Combat/weapons.cpp', 'WeaponClass::Make_Shell_Eject'),
    'twiddle': ('wwsaveload/twiddler.cpp', 'TwiddlerClass::Twiddle'),
    'create': ('wwsaveload/twiddler.cpp', 'TwiddlerClass::Create'),
    'lookup': ('wwsaveload/definitionmgr.cpp', 'DefinitionMgrClass::Find_Definition'),
    'audio': ('WWAudio/WWAudio.cpp', 'WWAudioClass::Create_Sound'),
}
ROUTES = {
    'MICROCHUNKID_WEAPON_DEF_MUZZLE_FLASH_PHYS_DEF_ID': {
        'owners': ['muzzle', 'lookup'], 'source_outcome': 'Missing definition skips optional muzzle effect creation.',
        'condition': 'Nonzero ID; firing effects only outside the first-person star route; time must advance.'},
    'MICROCHUNKID_WEAPON_DEF_EJECT_PHYS_DEF_ID': {
        'owners': ['eject', 'muzzle', 'lookup'], 'source_outcome': 'Missing definition skips casing creation.',
        'condition': 'Caller requires star owner, weapon model and eject bone outside first-person route.'},
    'twiddler_choice': {
        'owners': ['twiddle', 'create', 'lookup', 'audio'],
        'source_outcome': 'Selected missing choice returns null; Create returns null. Audio ID caller guards null.',
        'condition': 'Choice is random; other twiddler callers and actual choice invocation require review.'},
}


def body(source, qualified, parameter_prefix=None):
    masked = mask_noncode(source)
    pattern = re.escape(qualified) + r'\s*\(([^()]*)\)\s*(?:const\s*)?\{'
    matches = [m for m in re.finditer(pattern, masked)
               if parameter_prefix is None or m[1].strip().startswith(parameter_prefix)]
    if len(matches) != 1:
        raise ValueError('Ambiguous or missing original method: ' + qualified)
    match = matches[0]
    start = match.end() - 1
    depth = 1
    end = start + 1
    while depth and end < len(masked):
        depth += (masked[end] == '{') - (masked[end] == '}')
        end += 1
    if depth:
        raise ValueError('Unterminated method')
    return source[start:end], source.count('\n', 0, match.start()) + 1


def references(inventory, owners):
    grouped = {}
    for scope in inventory['rows'][1:]:
        for reference in scope['unresolved_field_provenance']:
            key = reference.get('field_name') or reference['kind']
            row = grouped.setdefault((key, reference['id']), {'field': key, 'target_id': reference['id'],
                'affected_maps': set(), 'owner_definition_ids': set(), 'field_occurrences': 0})
            row['affected_maps'].add(scope['map'])
            row['owner_definition_ids'].add(reference['owner_definition_id'])
            row['field_occurrences'] += 1
    rows = []
    for (field, target), record in sorted(grouped.items()):
        route = ROUTES.get(field)
        rows.append({**record, 'affected_maps': sorted(record['affected_maps']),
                     'owner_definition_ids': sorted(record['owner_definition_ids']),
                     'caller_review': route,
                     'reviewed_bodies_match_upstream': bool(route) and all(owners[k]['matches_upstream'] for k in route['owners']),
                     'status': 'unknown', 'evidence_class': 'retail_reference_and_original_source_review'})
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inventory', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    owners = {}
    for key, (relative, method) in OWNERS.items():
        staged_path = Path('staging') / str(Path(relative).parent).lower() / Path(relative).name
        upstream_path = Path('upstream/CnC_Renegade/Code') / relative
        staged = (root / staged_path).read_text(encoding='latin1')
        original = (root / upstream_path).read_text(encoding='latin1')
        prefix = 'int' if key == 'audio' else None
        current_body, line = body(staged, method, prefix)
        original_body, original_line = body(original, method, prefix)
        owners[key] = {'source': staged_path.as_posix(), 'method': method, 'line': line,
                       'source_sha256': hashlib.sha256((root / staged_path).read_bytes()).hexdigest(),
                       'body_sha256': hashlib.sha256(current_body.encode('latin1')).hexdigest(),
                       'upstream': upstream_path.as_posix(), 'upstream_line': original_line,
                       'upstream_body_sha256': hashlib.sha256(original_body.encode('latin1')).hexdigest(),
                       'matches_upstream': current_body == original_body}
    inventory = json.loads(args.inventory.read_text())
    rows = references(inventory, owners)
    result = {'schema_version': 1, 'complete': False, 'total': len(rows), 'rows': rows,
              'counts': dict(Counter(r['status'] for r in rows)), 'owners': owners,
              'inventory_sha256': hashlib.sha256(args.inventory.read_bytes()).hexdigest(),
              'parser_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'limits': ['Source equality does not prove rendered effects or audio playback.',
                         'Only missing map-rooted parsed edges are covered; database-only and computed edges remain open.',
                         'Optional effect omission remains a fidelity question; retail behavior is preserved.',
                         'Twiddler call-site context, runtime choice and stale-data provenance remain unverified.']}
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'rows': len(rows), 'body_matches': sum(r['matches_upstream'] for r in owners.values()),
                      'bodies': len(owners), 'unreviewed_fields': sum(r['caller_review'] is None for r in rows)}))


if __name__ == '__main__':
    main()
