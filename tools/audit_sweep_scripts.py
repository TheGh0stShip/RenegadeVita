#!/usr/bin/env python3
"""S5 complete declared command slots and original Scripts.dsp units."""
import argparse
import hashlib
import json
from pathlib import Path
import re
from tools.audit_campaign_source_surface import dsp_sources
from tools.audit_mission_content_bindings import masked, source_scripts
from tools.audit_script_command_table import table_assignments, compare


def command_slots(source):
    clean = masked(source, strings=True)
    struct = re.search(r'typedef\s+struct\s*\{([^}]+)\}\s*ScriptCommands\s*;', clean, re.S)
    if not struct:
        raise ValueError('ScriptCommands structure not located')
    return [{'name': m[1], 'line': clean.count('\n', 0, struct.start(1) + m.start()) + 1}
            for m in re.finditer(r'\(\s*\*\s*(\w+)\s*\)\s*\(', struct[1])]


def inventory(root, link):
    directory = root / 'upstream/CnC_Renegade/Code'
    header = directory / 'Scripts/scriptcommands.h'
    original = directory / 'Combat/scriptcommands.cpp'
    native = root / 'staging/combat/scriptcommands.cpp'
    original_table = table_assignments(original.read_text(encoding='latin1'))
    native_table = table_assignments(native.read_text(encoding='latin1'))
    scripts = source_scripts(root)
    uses = compare(scripts.values(), original_table)['commands']
    rows = []
    for slot in command_slots(header.read_text(encoding='latin1')):
        rows.append(dict(slot, id=hashlib.sha256(slot['name'].encode()).hexdigest(),
                         original_assignment_candidates=original_table.get(slot['name'], []),
                         staged_assignment_candidates=native_table.get(slot['name'], []),
                         original_script_owner_candidates=uses.get(slot['name'], {}).get('owners', []),
                         status='unknown', evidence_class='source_metadata'))
    selected = {row['source'] for row in link['rows'] if row['selected_for_target']}
    units = [{'source': 'staging/scripts/' + name, 'selected_for_arm_target': 'staging/scripts/' + name in selected,
              'status': 'unknown', 'evidence_class': 'source_and_build_metadata'}
             for name in dsp_sources(directory / 'Scripts/Scripts.dsp')]
    paths = [header, original, native, directory / 'Scripts/Scripts.dsp']
    return {'schema': 1, 'sweep': 'S5', 'complete': False, 'total': len(rows),
            'counts': {'unknown': len(rows)}, 'rows': rows, 'script_units': units,
            'script_unit_total': len(units),
            'selected_script_units': sum(row['selected_for_arm_target'] for row in units),
            'inputs': [{'source': path.relative_to(root).as_posix(),
                        'sha256': hashlib.sha256(path.read_bytes()).hexdigest()} for path in paths],
            'open_risks': ['Lexical assignments do not evaluate platform branches or function bodies',
                           'Indirect commands and helper/global calls', 'Slot ABI layout and initialization',
                           'Retail parameter matching and MSVC semantic differences',
                           'Behavior/stub classification and runtime registration'],
            'scope': 'Every function-pointer slot in original ScriptCommands and every Scripts.dsp C++ unit'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--link-inventory', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    data = args.link_inventory.read_bytes()
    result = inventory(Path(__file__).resolve().parents[1], json.loads(data))
    result['link_inventory_sha256'] = hashlib.sha256(data).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ('total', 'script_unit_total', 'selected_script_units')}))


if __name__ == '__main__':
    main()
