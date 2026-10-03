"""Read-only shipped-script literal parameter-name audit, not execution proof."""
import ast
import argparse
from collections import Counter
import json
import hashlib
from pathlib import Path
import re
import sys
if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.audit_mission_content_bindings import source_scripts, masked, ROOT, MAPS, audit_map

CALL = re.compile(r'\bGet_(?:Int_|Float_|Vector3_|Bool_)?Parameter\s*\(')
LITERAL = re.compile(r'\s*("(?:\\.|[^"\\])*"\s*)(?=\))')


def parameter_index(descriptor, name):
    if descriptor is None:
        return None
    if any(ord(char) > 127 for char in descriptor + name):
        return None # C locale/non-ASCII stricmp behavior needs separate evidence.
    raw = descriptor.encode('latin1')[:511].decode('latin1')
    parts = raw.split(',') if raw else []
    if raw.endswith(','):
        parts.pop()
    for index, part in enumerate(parts):
        field = re.split(r'[=:\n]', part, maxsplit=1)[0].strip(' \t\r\n\v\f')
        if field.lower() == name.lower():
            return index
    return -1


def audit(scripts):
    rows, unresolved = [], []
    for script in scripts.values():
        body, code = script['body'], masked(script['body'], strings=True)
        for call in CALL.finditer(code):
            literal = LITERAL.match(body, call.end())
            line = script['body_start_line'] + body.count('\n', 0, call.start())
            identity = {'script': script['name'], 'owner': script['owner'], 'line': line}
            if not literal:
                unresolved.append(identity)
                continue
            name = ast.literal_eval(literal[1].strip())
            index = parameter_index(script['descriptor'], name)
            rows.append({**identity, 'parameter_name': name, 'lookup_index': index,
                         'finding': index == -1, 'descriptor_unresolved': index is None})
    return {'literal_calls': rows, 'non_literal_or_numeric_calls': unresolved,
            'finding_calls_by_owner': dict(Counter(r['owner'] for r in rows if r['finding'])),
            'runtime_execution_verified': False,
            'limits': ['Shipped DSP source scope, literal names only; runtime parameter values are separate.',
                       'Existing retail misspellings are preserved; a mismatch is not authorization to rename.',
                       'No compiled parser, native callback or mission progression proof.']}


def scoped_findings(report, binding):
    bound = {row['name'].lower() for row in binding['bindings']}
    closure = {row['name'].lower() for row in binding['discovered_scripts']}
    rows = [{**row, 'authored_binding_present': row['script'].lower() in bound,
             'source_dependency_closure_present': row['script'].lower() in closure,
             'authored_binding_count': sum(r['name'].lower() == row['script'].lower() for r in binding['bindings'])}
            for row in report['literal_calls'] if row['finding'] and row['script'].lower() in bound | closure]
    return {'map': binding['map'], 'archive_sha256': binding['archive_sha256'],
            'objects_ddb_sha256': binding['objects_ddb_sha256'],
            'definition_overlays': binding['definition_overlays'],
            'level_member_sha256': {name: row['sha256'] for name, row in binding['members'].items()},
            'findings': rows, 'runtime_execution_verified': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, help='regenerate scoped authored bindings read-only')
    args = parser.parse_args()
    scripts = source_scripts()
    result = audit(scripts)
    directory = ROOT / 'upstream/CnC_Renegade/Code/Scripts'
    result['source_sha256'] = {name: hashlib.sha256((directory / name).read_bytes()).hexdigest()
                              for name in sorted({r['owner'] for r in scripts.values()} | {'Scripts.dsp', 'scripts.cpp', 'strtrim.cpp'})}
    if args.data:
        result['scoped_maps'] = [scoped_findings(result, audit_map(ROOT, args.data, name, scripts)) for name in MAPS]
    output = ROOT / 'build/dev208-parameter-names-20261003.json'
    output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'literal_calls': len(result['literal_calls']),
                      'unresolved_or_numeric_calls': len(result['non_literal_or_numeric_calls']),
                      'finding_calls_by_owner': result['finding_calls_by_owner']}))
