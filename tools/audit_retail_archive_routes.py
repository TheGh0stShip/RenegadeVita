"""Read-only archive-provider gap analysis; never a gameplay completeness gate.

Consumes the independent retail catalogue. Compares archive CRC coverage, not
content use or rendered results. Full details must stay under build/.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GLOBALS = ('always2.dat', 'always.dbs', 'always.dat')


def top_level(name):
    return '/' not in name and '\\' not in name


def analyze(catalogue):
    archives = {}
    for row in catalogue['archives']:
        key = row['name'].casefold()
        if key in archives:
            raise ValueError('Ambiguous archive identity')
        archives[key] = row
    # Original init.cpp enumerates top-level *.mix, not recursive subfolders.
    mounted = [name for name in archives if name in GLOBALS or
               (top_level(name) and name.endswith('.mix'))]
    providers = defaultdict(list)
    for name in mounted:
        for entry in archives[name]['entries']:
            crc = entry['crc32']
            if not isinstance(crc, int) or not 0 <= crc <= 0xffffffff:
                raise ValueError('Archive CRC must retain unsigned 32-bit semantics')
            providers[crc].append({'archive': archives[name]['name'],
                                   'entry': entry['id'], 'name': entry['name'],
                                   'size': entry['size']})
    levels = []
    for flow in catalogue['campaign_flow']:
        if flow['kind'] == 'level' and flow['resource']:
            name = flow['resource'].casefold()
            if name not in levels:
                levels.append(name)
    scenarios = []
    for selected in ['m00_tutorial.mix', *levels]:
        if any(s['selected_archive'].casefold() == selected for s in scenarios):
            continue
        # Current full-port initial SP route, before any dynamic round swap.
        route = [*GLOBALS, 'm00_tutorial.mix', selected]
        if selected in ('m01.mix', 'm04.mix'):
            route.append('m08.mix')
        route = list(dict.fromkeys(route))
        present = set(route) & set(mounted)
        missing = [{'crc32': crc, 'providers': rows} for crc, rows in sorted(providers.items())
                   if not any(row['archive'].casefold() in present for row in rows)]
        scenarios.append({'selected_archive': selected,
                          'modeled_archives': route,
                          'missing_route_archives': [n for n in route if n not in archives],
                          'unreachable_archive_crc_count': len(missing),
                          'unreachable_archive_resources': missing,
                          'semantic_impact': 'OPEN; membership is not a usage trace'})
    collisions = [{'crc32': crc, 'providers': rows,
                   'names_differ': len({r['name'].upper() for r in rows}) > 1,
                   'payload_equivalence': 'UNKNOWN'}
                  for crc, rows in sorted(providers.items()) if len(rows) > 1]
    return {'schema': 1, 'evidence_class': 'STATIC_ARCHIVE_MEMBERSHIP_MODEL',
            'archive_set_sha256': catalogue['archive_set_sha256'],
            'catalogue_issues': catalogue['discovery_issues'],
            'original_top_level_archive_count': len(mounted),
            'original_archive_crc_count': len(providers),
            'excluded_nested_archives': [r['name'] for r in archives.values()
                                         if not top_level(r['name'])],
            'other_unmounted_archives': [r['name'] for name, r in archives.items()
                                         if top_level(r['name']) and name not in mounted],
            'duplicate_crc_provider_groups': collisions,
            'scenarios': scenarios,
            'limits': ['Loose files, temp/provider factories and runtime attachments are not modeled.',
                       'Windows enumeration order is not assumed to be alphabetical.',
                       'M09 SearchStart precedes loose/global fallback; temp factory precedes it.',
                       'Duplicate CRC providers need payload and precedence review.',
                       'Scenarios describe initial single-player routes, not round transitions.',
                       'Unavailable archive resources are leads, not proven missing gameplay.'],
            'content_inventory_complete': False, 'play_test_ready': False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('catalogue', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args(argv)
    output = args.output.resolve()
    if not output.is_relative_to((ROOT / 'build').resolve()):
        parser.error('Private archive details must remain under build/')
    if output == args.catalogue.resolve():
        parser.error('Cannot overwrite the input catalogue')
    raw = args.catalogue.read_bytes()
    result = analyze(json.loads(raw))
    result['catalogue_sha256'] = hashlib.sha256(raw).hexdigest()
    result['analyzer_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    result['source_sha256'] = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                              for name in ('upstream/CnC_Renegade/Code/Commando/init.cpp',
                                           'upstream/CnC_Renegade/Code/Combat/ffactorylist.cpp',
                                           'upstream/CnC_Renegade/Code/Combat/savegame.cpp',
                                           'port/platform/vita/a31_vita_runtime.cpp')}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'archives': result['original_top_level_archive_count'],
                      'crc_keys': result['original_archive_crc_count'],
                      'duplicate_provider_groups': len(result['duplicate_crc_provider_groups']),
                      'scenarios': [{'selected': s['selected_archive'],
                                     'unreachable_crc_keys': s['unreachable_archive_crc_count'],
                                     'missing_archives': s['missing_route_archives']}
                                    for s in result['scenarios']],
                      'play_test_ready': False}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
