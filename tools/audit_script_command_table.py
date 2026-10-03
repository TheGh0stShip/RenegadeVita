"""Source-only declared-script command/table comparison; no engine execution.

Only direct Commands->Name(...) calls and EngineCommands.Name = identifier
assignments are resolved. No preprocessor, function-pointer or behavior proof.
"""
from collections import defaultdict
import json
import hashlib

from tools.audit_mission_content_bindings import ROOT, masked, source_scripts
from tools.audit_mission_text_routes import command_calls
import re


def table_assignments(source):
    code = masked(source, strings=True)
    assignments = defaultdict(set)
    for match in re.finditer(r'\bEngineCommands\.(\w+)\s*=\s*([^;]+);', code):
        value = match[2].strip()
        owner = re.fullmatch(r'&?\s*([A-Za-z_]\w*)', value)
        assignments[match[1]].add(owner[1] if owner else '<unresolved expression>')
    return {name: sorted(values) for name, values in sorted(assignments.items())}


def compare(scripts, table):
    uses = defaultdict(set)
    for script in scripts:
        for call in command_calls(script['body']):
            uses[call['command']].add(script['owner'])
    missing = sorted(name for name in uses if name not in table)
    unresolved = sorted(name for name in uses if name in table and (
        len(table[name]) != 1 or table[name][0] in ('NULL', 'nullptr', '<unresolved expression>')))
    return {'used_commands': len(uses), 'table_fields': len(table),
            'missing_assignments': missing, 'unresolved_assignments': unresolved,
            'commands': {name: {'owners': sorted(owners), 'table_candidates': table.get(name, [])}
                         for name, owners in sorted(uses.items())},
            'compiled_registration_or_behavior_proven': False}


def main():
    scripts = source_scripts(ROOT)
    original = (ROOT / 'upstream/CnC_Renegade/Code/Combat/scriptcommands.cpp').read_text(encoding='latin1')
    table = table_assignments(original)
    focus = {'Mission00.cpp', 'MissionX0.cpp', 'Mission01.cpp'}
    result = {'all_dsp_declared_scripts': compare(scripts.values(), table),
              'focus_mission_declared_scripts': compare(
                  [script for script in scripts.values() if script['owner'] in focus], table),
              'limits': ['Direct declared-script bodies only; helper/global calls outside those bodies are not covered.',
                         'Assignments are lexical candidates, not evaluated platform/preprocessor selections.',
                         'A named original function is not proof of a linked, registered or working native command.']}
    directory = ROOT / 'upstream/CnC_Renegade/Code'
    paths = {directory / 'Scripts' / script['owner'] for script in scripts.values()}
    paths.update((directory / 'Scripts/Scripts.dsp', directory / 'Combat/scriptcommands.cpp'))
    result['original_source_sha256'] = {path.relative_to(directory).as_posix():
                                       hashlib.sha256(path.read_bytes()).hexdigest()
                                       for path in sorted(paths)}
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
