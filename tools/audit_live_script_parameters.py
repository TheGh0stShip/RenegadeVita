#!/usr/bin/env python3
"""Join all-map positional parameters to hash-verified live script descriptors."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

from tools.audit_live_script_bindings import compare
from tools.audit_mission_content_bindings import source_scripts


def parameter_shape(descriptor, parameters):
    # Original Get_Parameter_Index truncates the description to 511 bytes.
    parts = descriptor.encode('latin1')[:511].decode('latin1').split(',')
    # The original while (*param_ptr) never visits a final empty field.
    if parts[-1] == '':
        parts.pop()
    names = [re.split(r'[=:\n]', part, maxsplit=1)[0].strip() for part in parts]
    count = None if parameters is None else (parameters.count(',') + 1 if parameters else 0)
    category = ('parameters_unrecorded' if count is None else
                'excess_values' if count > len(names) else
                'fewer_values' if count < len(names) else 'equal_count')
    return {'category': category, 'value_count': count, 'descriptor_count': len(names),
            'descriptor_truncated': len(descriptor.encode('latin1')) > 511}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ('bindings-directory', 'retail', 'registry', 'output'):
        parser.add_argument('--' + option, required=True, type=Path)
    args = parser.parse_args()
    scripts = source_scripts()
    registry = json.loads(args.registry.read_text())
    live = {entry['name'].lower(): entry for entry in registry['registry_entries']}
    verified = {}
    for name, entry in live.items():
        source = scripts.get(name)
        if source is None or source['descriptor'] is None:
            raise ValueError('Live descriptor source unavailable: ' + name)
        digest = hashlib.sha256(source['descriptor'].encode()).hexdigest()
        if digest != entry['parameter_description_sha256']:
            raise ValueError('Live/source descriptor mismatch: ' + name)
        verified[name] = source
    retail = json.loads(args.retail.read_text())
    expected = {row['map']: row for row in retail['rows']}
    rows, seen = [], set()
    for path in sorted(args.bindings_directory.glob('*bindings.json')):
        binding = json.loads(path.read_text())
        name = binding['map']
        if name in seen or name not in expected:
            raise ValueError('Unexpected or duplicate map')
        seen.add(name)
        compare(binding, registry, expected[name])
        categories, leads = Counter(), []
        for item in binding['bindings']:
            source = verified.get(item['name'].lower())
            shape = (parameter_shape(source['descriptor'], item.get('parameters')) if source else
                     {'category': 'unregistered', 'value_count': None, 'descriptor_count': None})
            categories[shape['category']] += 1
            if shape['category'] not in ('equal_count',):
                leads.append({**{key: item[key] for key in ('name', 'binding_kind', 'member', 'offset',
                                                          'definition_id', 'spawner_id') if key in item}, **shape})
        rows.append({'map': name, 'status': 'unknown', 'bindings': len(binding['bindings']),
                     'categories': dict(sorted(categories.items())), 'leads': leads,
                     'binding_receipt_sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    if seen != set(expected):
        raise ValueError('Incomplete all-map denominator')
    totals = Counter()
    for row in rows:
        totals.update(row['categories'])
    receipt = {
        'schema_version': 1, 'complete': False, 'total': len(rows), 'rows': rows,
        'counts': dict(Counter(row['status'] for row in rows)),
        'bindings': sum(row['bindings'] for row in rows), 'categories': dict(sorted(totals.items())),
        'live_descriptors_verified': len(verified),
        'registry_sha256': hashlib.sha256(args.registry.read_bytes()).hexdigest(),
        'retail_sha256': hashlib.sha256(args.retail.read_bytes()).hexdigest(),
        'parser_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'helper_sha256': {name: hashlib.sha256(Path(name).read_bytes()).hexdigest()
                          for name in ('tools/audit_live_script_bindings.py',
                                       'tools/audit_mission_content_bindings.py')},
        'original_parameter_owner_sha256': hashlib.sha256(Path('staging/scripts/scripts.cpp').read_bytes()).hexdigest(),
        'descriptor_sources_sha256': {
            owner: hashlib.sha256((Path('upstream/CnC_Renegade/Code/Scripts') / owner).read_bytes()).hexdigest()
            for owner in sorted({row['owner'] for row in verified.values()})},
        'limits': ['Positional shape only; type conversion, lookup names and callbacks remain open.',
                   'Fewer/excess values are leads, not proof of bugs or progression failure.',
                   'Original Get_Parameter returns empty text outside supplied positions; defaults are not invented.',
                   'Unrecorded parameters are distinct from authored empty strings.',
                   'Embedded NUL, newline handling and numeric/vector coercions require original runtime probes.',
                   'Host descriptor identity does not prove ARM initialization or physical behavior.'],
    }
    args.output.write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({key: receipt[key] for key in ('total', 'bindings', 'categories', 'live_descriptors_verified')}))


if __name__ == '__main__':
    main()
