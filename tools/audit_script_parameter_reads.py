#!/usr/bin/env python3
"""Inventory literal, indexed and computed reads in live original script bodies."""
import argparse
import ast
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re

from tools.audit_live_script_bindings import compare
from tools.audit_mission_content_bindings import masked, source_scripts

READ = re.compile(r'\b(Get_(?:(?:Int|Float|Vector3)_)?Parameter(?:_Index)?)\s*\(')
LITERAL = re.compile(r'\s*(?:"(?:\\.|[^"\\])*"\s*)+\Z')
STRING = re.compile(r'"(?:\\.|[^"\\])*"')


def descriptor_names(descriptor):
    parts = descriptor.encode('latin1')[:511].decode('latin1').split(',')
    if parts[-1] == '':
        parts.pop()
    return [re.split(r'[=:\n]', part, maxsplit=1)[0].strip() for part in parts]


def reads(body, descriptor):
    code = masked(body, strings=True)
    names = descriptor_names(descriptor)
    rows = []
    for match in READ.finditer(code):
        depth, end = 1, match.end()
        while end < len(code) and depth:
            depth += (code[end] == '(') - (code[end] == ')')
            end += 1
        argument = masked(body[match.end():end - 1]).strip() if depth == 0 else ''
        name, index = None, None
        if depth:
            category = 'unresolved_parse'
        elif LITERAL.fullmatch(argument):
            name = ''.join(ast.literal_eval(s) for s in STRING.findall(argument))
            index = next((i for i, candidate in enumerate(names) if candidate.lower() == name.lower()), -1)
            category = 'literal_name_matches' if index >= 0 else 'literal_name_absent'
        elif re.fullmatch(r'[+-]?\d+', argument) and match[1] != 'Get_Parameter_Index':
            index = int(argument)
            category = 'literal_index'
        else:
            category = 'computed_argument'
        rows.append({'method': match[1], 'name': name, 'index': index, 'category': category,
                     'relative_line': body.count('\n', 0, match.start()), 'status': 'unknown'})
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ('registry', 'retail', 'bindings-directory', 'output'):
        parser.add_argument('--' + option, required=True, type=Path)
    args = parser.parse_args()
    registry = json.loads(args.registry.read_text())
    expected = {row['map']: row for row in json.loads(args.retail.read_text())['rows']}
    maps, seen = defaultdict(set), set()
    for path in args.bindings_directory.glob('*bindings.json'):
        binding = json.loads(path.read_text())
        if binding['map'] in seen or binding['map'] not in expected:
            raise ValueError('Unexpected or duplicate map')
        seen.add(binding['map'])
        compare(binding, registry, expected[binding['map']])
        for item in binding['bindings']:
            maps[item['name'].lower()].add(binding['map'])
    if seen != set(expected):
        raise ValueError('Incomplete all-map denominator')
    scripts, rows = source_scripts(), []
    for entry in registry['registry_entries']:
        key = entry['name'].lower()
        source = scripts[key]
        if hashlib.sha256(source['descriptor'].encode()).hexdigest() != entry['parameter_description_sha256']:
            raise ValueError('Live descriptor source mismatch')
        for row in reads(source['body'], source['descriptor']):
            row.update(script=source['name'], original_owner=source['owner'],
                       line=source['body_start_line'] + row.pop('relative_line'),
                       affected_maps=sorted(maps[key]))
            rows.append(row)
    receipt = {
        'schema_version': 1, 'complete': False, 'total': len(rows), 'rows': rows,
        'counts': dict(Counter(row['status'] for row in rows)),
        'categories': dict(Counter(row['category'] for row in rows)),
        'live_script_bodies': len(registry['registry_entries']), 'maps': len(seen),
        'registry_sha256': hashlib.sha256(args.registry.read_bytes()).hexdigest(),
        'retail_sha256': hashlib.sha256(args.retail.read_bytes()).hexdigest(),
        'parser_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'helper_sha256': hashlib.sha256(Path('tools/audit_mission_content_bindings.py').read_bytes()).hexdigest(),
        'owner_source_sha256': {owner: hashlib.sha256((Path('upstream/CnC_Renegade/Code/Scripts') / owner).read_bytes()).hexdigest()
                                for owner in sorted({scripts[e['name'].lower()]['owner'] for e in registry['registry_entries']})},
        'limits': ['Lexical script-body call inventory; overloads, helpers, macros and inherited methods require review.',
                   'Computed arguments retained unresolved; literal indices do not establish supplied argument bounds.',
                   'Affected maps are authored direct binding occurrences, not complete runtime attachment reachability.',
                   'Original typos are retained; missing names do not authorize changes in retail behavior.',
                   'Callback execution, numeric conversion and ARM/physical acceptance remain open.'],
    }
    args.output.write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({key: receipt[key] for key in ('total', 'categories', 'live_script_bodies', 'maps')}))


if __name__ == '__main__':
    main()
