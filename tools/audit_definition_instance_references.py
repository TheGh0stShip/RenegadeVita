#!/usr/bin/env python3
"""Inventory typed definition edges globally and from all-map serialized roots.

Graph reachability is metadata evidence, not proof a runtime branch executes.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from tools.audit_m13_level_owners import chunks, definitions, level_records, reference_fields
from tools.audit_sweep_retail import map_names
from tools.renegade_cinematic_dependency_scan import MixArchive


def graph(defs, roots=None):
    reached, missing = set(), set()
    pending = set(defs) if roots is None else set(roots) - {0}
    while pending:
        key = pending.pop()
        if key in reached or key in missing:
            continue
        if key not in defs:
            missing.add(key)
            continue
        reached.add(key)
        pending.update(set(defs[key]['definition_references']) - reached - missing - {0})
    edges = []
    for owner in sorted(reached):
        for reference in defs[owner]['definition_reference_provenance']:
            target = reference['id']
            if not target:
                continue
            candidate = defs.get(target)
            disposition = ('absent_target' if candidate is None else
                           'editor_target' if 0x50000 <= int(candidate['factory'], 16) < 0x60000 else
                           'present_target')
            edges.append({'owner_definition_id': owner, 'owner_factory': defs[owner]['factory'],
                          **reference, 'disposition': disposition,
                          'target_factory': candidate['factory'] if candidate else None})
    return {'reached_definitions': len(reached), 'missing_ids': sorted(missing),
            'typed_reference_fields': len(edges),
            'edge_counts': dict(sorted(Counter(e['disposition'] for e in edges).items())),
            'edges': edges}


def public_row(scope, result, **identity):
    return {'map': scope, **identity, 'status': 'unknown', 'evidence_class': 'retail_typed_reference_metadata',
            'reached_definitions': result['reached_definitions'],
            'typed_reference_fields': result['typed_reference_fields'],
            'edge_counts': result['edge_counts'], 'missing_ids': result['missing_ids'],
            'unresolved_field_provenance': [e for e in result['edges'] if e['disposition'] != 'present_target']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--private-output', required=True, type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    schema = reference_fields(root)
    database = MixArchive(args.data / 'always.dbs').read_binary('objects.ddb')
    baseline = definitions(chunks(database), schema)
    database_hash = hashlib.sha256(database).hexdigest()
    complete_graph = graph(baseline)
    rows = [public_row('objects.ddb (all parsed definitions)', complete_graph,
                       objects_ddb_sha256=database_hash)]
    private = {'database_graph': complete_graph, 'maps': []}
    for name in map_names(args.data):
        path = args.data / name
        if not path.is_file():
            rows.append({'map': name, 'status': 'unknown', 'input_missing': True,
                         'evidence_class': 'missing_input', 'missing_ids': []})
            continue
        archive = MixArchive(path)
        defs = dict(baseline)
        overlays = []
        roots = set()
        members = []
        # Match the existing source audit's sorted named-overlay precedence.
        # Duplicate DDB names and actual runtime mount order remain open.
        for member in sorted(archive.entries):
            if member.endswith('.ddb'):
                payload = archive.read_binary(member)
                additions = definitions(chunks(payload), schema)
                overlays.append({'member': member, 'sha256': hashlib.sha256(payload).hexdigest(),
                                 'definition_count': len(additions),
                                 'overridden_ids': sorted(defs.keys() & additions.keys())})
                defs.update(additions)
            elif member.endswith(('.ldd', '.lsd')):
                payload = archive.read_binary(member)
                record = level_records(chunks(payload))
                roots.update(r['definition_id'] for r in record['objects'] + record['spawners'] + record['physics']
                             if r['definition_id'])
                members.append({'member': member, 'sha256': hashlib.sha256(payload).hexdigest()})
        roots.update(key for key, row in defs.items()
                     if row['factory'] in ('0x00040602', '0x00040603') or
                     (row['factory'] == '0x00040601' and row['name'].lower() == 'loiter'))
        result = graph(defs, roots)
        with path.open('rb') as stream:
            archive_hash = hashlib.file_digest(stream, 'sha256').hexdigest()
        rows.append(public_row(name, result, archive_sha256=archive_hash,
                               serialized_and_global_root_count=len(roots),
                               members=members, definition_overlays=overlays))
        private['maps'].append({'map': name, 'roots': sorted(roots), 'graph': result})
    receipt = {'schema_version': 1, 'complete': False, 'total': len(rows), 'rows': rows,
               'counts': dict(Counter(r['status'] for r in rows)),
               'scope': 'Whole objects.ddb graph plus serialized/global-setting roots for all supplied maps',
               'limits': ['Only typed fields covered by the existing source schema are inspected.',
                          'Script-created presets, computed IDs and unparsed fields can add roots/edges.',
                          'Graph reachability is not execution; absent IDs are leads, not confirmed port defects.',
                          'Named overlay precedence and duplicate database names require runtime verification.',
                          'Editor-target absence in parsed edges does not prove complete editor irrelevance.']}
    sources = ['tools/audit_definition_instance_references.py', 'tools/audit_m13_level_owners.py',
               'tools/audit_sweep_retail.py', 'tools/renegade_cinematic_dependency_scan.py']
    receipt['parser_inputs'] = [{'source': name, 'sha256': hashlib.sha256((root / name).read_bytes()).hexdigest()}
                               for name in sources]
    owners = ['vehicle.cpp', 'cinematicgameobj.cpp', 'doors.cpp', 'elevator.cpp',
              'soldier.cpp', 'powerup.cpp', 'beacongameobj.cpp', 'physicalgameobj.cpp',
              'armedgameobj.cpp', 'weaponmanager.cpp', 'explosion.cpp', 'globalsettings.cpp',
              'combatchunkid.h', 'spawn.cpp', 'basegameobj.cpp']
    owner_sources = ['staging/combat/' + name for name in owners] + [
        'staging/wwsaveload/saveloadids.h', 'staging/wwsaveload/definition.cpp',
        'staging/wwsaveload/twiddler.cpp', 'staging/wwphys/phys.cpp']
    receipt['owner_source_receipts'] = [
        {'source': name, 'sha256': hashlib.sha256((root / name).read_bytes()).hexdigest()}
        for name in owner_sources]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.private_output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2) + '\n')
    args.private_output.write_text(json.dumps(private, indent=2) + '\n')
    print(json.dumps({'scopes': len(rows), 'database_missing_ids': len(complete_graph['missing_ids']),
                      'database_edges': complete_graph['typed_reference_fields'],
                      'database_edge_counts': complete_graph['edge_counts']}))


if __name__ == '__main__':
    main()
