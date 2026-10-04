"""Enumerate original/staged bodies for every declared ScriptCommands slot.

Lexical signals are review leads, never runtime or stub verdicts.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

from tools.audit_sweep_scripts import command_slots
from tools.audit_script_command_table import table_assignments
from tools.audit_missing_definition_callers import body
from tools.audit_sweep_port_guards import mask_noncode


def digest(value):
    return hashlib.sha256(value.encode('latin1')).hexdigest()


def inspect(source, name):
    try:
        text, line = body(source, name)
    except ValueError as error:
        return {'resolved': False, 'reason': str(error)}
    clean = mask_noncode(text)
    return {'resolved': True, 'line': line, 'body_sha256': digest(text),
            'preprocessor_directives': [s.strip() for s in clean.splitlines()
                                       if s.lstrip().startswith('#')],
            'return_statements': len(re.findall(r'\breturn\b', clean)),
            'call_name_candidates': sorted(set(re.findall(r'\b([A-Za-z_]\w*)\s*\(', clean))
                                           - {'if', 'while', 'for', 'switch', 'sizeof'}),
            'constant_return_candidates': re.findall(r'\breturn\s+(true|false|NULL|nullptr|0|1)\s*;', clean)}


def inventory(header, original, staged):
    old, new = table_assignments(original), table_assignments(staged)
    rows = []
    for slot in command_slots(header):
        owners = []
        for name in sorted(set(old.get(slot['name'], []) + new.get(slot['name'], []))):
            before, after = inspect(original, name), inspect(staged, name)
            owners.append({'function': name, 'original': before, 'staged': after,
                           'body_matches_original': before.get('resolved') and after.get('resolved')
                           and before['body_sha256'] == after['body_sha256']})
        rows.append({**slot, 'owners': owners, 'status': 'unknown',
                     'evidence_class': 'source_body_metadata'})
    counts = Counter('unresolved' if not r['owners'] or any(not o['staged']['resolved'] or
                     not o['original']['resolved'] for o in r['owners']) else
                     'body_equal' if all(o['body_matches_original'] for o in r['owners']) else
                     'body_changed' for r in rows)
    return {'schema': 1, 'complete': False, 'total': len(rows),
            'counts': {'unknown': len(rows)}, 'body_comparison_counts': dict(sorted(counts.items())),
            'rows': rows, 'open_risks': ['Preprocessor branches are not evaluated.',
             'Equal bodies can call replaced downstream owners or macros.',
             'Return and call syntax do not prove stub behavior or execution.',
             'Ambiguous overloads remain unresolved; ARM ABI and initialization need runtime evidence.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    files = ['upstream/CnC_Renegade/Code/Scripts/scriptcommands.h',
             'upstream/CnC_Renegade/Code/Combat/scriptcommands.cpp', 'staging/combat/scriptcommands.cpp']
    sources = [(root / f).read_text(encoding='latin1') for f in files]
    result = inventory(*sources)
    result['inputs'] = [{'source': f, 'sha256': digest(s)} for f, s in zip(files, sources)]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result['body_comparison_counts']))


if __name__ == '__main__':
    main()
