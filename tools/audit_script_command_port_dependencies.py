"""Join lexical command calls to port-function and macro review candidates.

Name matches are candidates, not overload resolution or runtime reachability.
"""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re


def join(commands, guards):
    names = defaultdict(list)
    for row in guards['rows']:
        if row['kind'] == 'port_function':
            found = re.findall(r'([A-Za-z_]\w*)\s*\(', row['declarator'])
            if not found:
                continue
            name = found[0]
        elif row['kind'] == 'port_macro_definition' and row.get('function_like'):
            name = row['name']
        else:
            continue
        names[name].append({'row_id': row['row_id'], 'kind': row['kind'],
                           'file': row['file'], 'line': row['line'],
                           'status': row['status'], 'scope': row.get('scope'),
                           'body_sha256': row.get('body_sha256')})
    rows = []
    for command in commands['rows']:
        calls = set()
        for owner in command['owners']:
            staged = owner['staged']
            candidates = [staged] if staged['resolved'] else staged.get('definition_candidates', [])
            for candidate in candidates:
                calls.update(candidate['call_name_candidates'])
        rows.append({'name': command['name'], 'status': 'unknown',
                     'evidence_class': 'lexical_cross_inventory_candidates',
                     'call_total': len(calls),
                     'matched_calls': [{'name': name, 'candidates': names[name]} for name in sorted(calls)
                                       if name in names],
                     'unmatched_calls': sorted(calls - names.keys())})
    return {'schema_version': 1, 'total': len(rows), 'counts': {'unknown': len(rows)},
            'commands_with_port_candidates': sum(bool(r['matched_calls']) for r in rows),
            'matched_call_names': sum(len(r['matched_calls']) for r in rows),
            'rows': rows, 'complete': False,
            'limits': ['Name-only matches can collide across classes and overloads.',
                       'Original staged downstream methods, virtual dispatch and transitive calls are not joined.',
                       'Guard inventory is a hash-pinned snapshot; current body identity must be verified before a fix.',
                       'Macro expansion, preprocessor selection and runtime reachability remain open.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--commands', type=Path, required=True)
    parser.add_argument('--guards', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    inputs = [p.read_bytes() for p in (args.commands, args.guards)]
    result = join(*(json.loads(data) for data in inputs))
    result['parent_sha256'] = dict(zip(('command_bodies', 'port_guards'),
                                     (hashlib.sha256(data).hexdigest() for data in inputs)))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({key: result[key] for key in ('total','commands_with_port_candidates','matched_call_names')}))


if __name__ == '__main__':
    main()
