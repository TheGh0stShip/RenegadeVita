"""Read-only cinematic callers and possible custom-event slot writers.

This is deliberately incomplete C++ dataflow analysis. Same-script assignments
are possible values, never proof that a particular callback assigns or sends
them. Detailed authored metadata stays in ignored build/.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

from tools.audit_cinematic_slots import NUM_SLOTS, audit as cinematic_audit, integer
from tools.audit_mission_content_bindings import MAPS, ROOT, constant_branch_code, masked, parameter_fields, source_scripts
from tools.audit_mission_text_routes import arguments, assignments, command_calls, constant_id, literal_string, unwrap
from tools.renegade_cinematic_dependency_scan import MixArchive

MISSION_OWNERS = {'M00_Tutorial.mix': 'Mission00.cpp', 'M13.mix': 'MissionX0.cpp', 'M01.mix': 'Mission01.cpp'}


def enum_constants(source, inherited=None):
    """Narrow unscoped enum grammar; unknown increments/conflicts stay unknown.

    Comments never supply values. No preprocessor, namespace, include or C++
    evaluator is claimed. Scoped enums and unsupported expressions are omitted.
    """
    values = dict(inherited or {})
    ambiguous = set()
    code = constant_branch_code(masked(source, strings=True))
    for match in re.finditer(r'\benum\s+(?:[A-Za-z_]\w*\s*)?\{([^{}]*)\}', code):
        previous = -1
        for item in match[1].split(','):
            entry = re.fullmatch(r'\s*([A-Za-z_]\w*)\s*(?:=\s*(.*?))?\s*', item)
            if not entry:
                continue
            name, expression = entry.groups()
            value = constant_id(expression, values) if expression is not None else (
                previous + 1 if previous is not None else None)
            if value is not None and not -0x80000000 <= value <= 0x7fffffff:
                value = None
            previous = value
            if name in ambiguous or name in values and values[name] != str(value):
                ambiguous.add(name)
                values.pop(name, None)
            elif value is not None:
                values[name] = str(value)
    return values


def numeric_constants(source, inherited=None):
    """Single object-like numeric/alias defines plus the narrow enum grammar."""
    values = dict(inherited or {})
    definitions, ambiguous = {}, set()
    code = constant_branch_code(masked(source, strings=True))
    for name, expression in re.findall(r'^\s*#\s*define\s+(\w+)[ \t]+([^\n]+)', code, re.MULTILINE):
        expression = expression.strip()
        if name in definitions and definitions[name] != expression:
            ambiguous.add(name)
        definitions[name] = expression
    ambiguous.update(re.findall(r'^\s*#\s*undef\s+(\w+)', code, re.MULTILINE))
    for name in ambiguous:
        definitions.pop(name, None)
        values.pop(name, None)
    possible = {**values, **definitions}
    for name in definitions:
        value = constant_id(name, possible)
        if value is not None and -0x80000000 <= value <= 0x7fffffff:
            if name in values and values[name] != str(value):
                ambiguous.add(name)
                values.pop(name, None)
            else:
                values[name] = str(value)
    result = enum_constants(source, values)
    for name in ambiguous:
        result.pop(name, None)
    return result


def callbacks(source):
    """Locate void method bodies for provenance, without executing callbacks."""
    code = masked(source, strings=True)
    rows = []
    for match in re.finditer(r'\bvoid\s+(\w+)\s*\(', code):
        _, end = arguments(source, match.end())
        start = end
        while start < len(code) and code[start].isspace():
            start += 1
        if start >= len(code) or code[start] != '{':
            continue
        depth = 1
        for end in range(start + 1, len(code)):
            depth += (code[end] == '{') - (code[end] == '}')
            if depth == 0:
                rows.append({'name': match[1], 'start': start, 'end': end})
                break
        else:
            raise ValueError('unclosed source callback')
    return rows


def possible_integers(expression, constants, assigned, fields, visiting=()):
    """Return candidate int32 values plus unresolved flag, not reaching defs."""
    expression = unwrap(expression)
    value = constant_id(expression, constants)
    if value is not None:
        return ({value}, False) if -0x80000000 <= value <= 0x7fffffff else (set(), True)
    parameter = re.fullmatch(r'Get_Int_Parameter\s*\((.*)\)', expression, re.DOTALL)
    if parameter and fields is not None:
        token = parameter[1].strip()
        name = literal_string(token)
        if name is not None:
            field = next((row for row in fields if row.get('name') is not None
                          and row['name'].lower() == name.lower()), None)
        else:
            index = constant_id(token, constants)
            if index is None:
                return set(), True
            field = next((row for row in fields if row['index'] == index), None)
        # Original Get_Parameter returns empty for an absent index; atoi is 0.
        # Descriptor defaults are not inserted by Set_Parameters_String.
        value = integer(field['value'] if field is not None else '')
        return ({value}, False) if value is not None else (set(), True)
    if re.fullmatch(r'[A-Za-z_]\w*', expression) and expression not in visiting:
        values = set()
        for candidate in assigned.get(expression, []):
            part, _ = possible_integers(candidate['expression'], constants, assigned, fields,
                                        (*visiting, expression))
            values.update(part)
        # Assignments from other callbacks, parameters, shadowing and writes
        # outside this narrow grammar can supply values absent from this set.
        return values, True
    return set(), True


def context_bindings(binding, files, scripts):
    rows = list(binding['bindings'])
    for file in files:
        for branch, commands in file['branches'].items():
            for command in commands:
                args = command.get('arguments', [])
                if command['command'] == 'attach_script' and len(args) >= 2:
                    script = scripts.get(args[1].lower())
                    parameters = args[2] if len(args) > 2 else ''
                    rows.append({'name': args[1], 'parameters': parameters,
                                 'parameter_fields': parameter_fields(script['descriptor'], parameters) if script else None,
                                 'binding_kind': 'cinematic_attachment_candidate', 'cinematic_member': file['member'],
                                 'cinematic_line': command['line'], 'cinematic_branch': branch,
                                 'cinematic_seconds_float32': command['seconds_float32']})
    return rows


def source_routes(binding, files, scripts, constants_by_owner):
    contexts = context_bindings(binding, files, scripts)
    reached = {row['name'].lower() for row in binding['discovered_scripts']}
    reached.update(row['name'].lower() for row in contexts)
    reached.update(name for name, row in scripts.items() if row['owner'] == MISSION_OWNERS[binding['map']])
    target_members = {file['member'].lower() for file in files}
    routes, callers = [], []
    for name in sorted(reached):
        script = scripts.get(name)
        if script is None:
            continue
        body = script['body']
        assigned = assignments(body)
        method_ranges = callbacks(body)
        constants = constants_by_owner.get(script['owner'], {})
        script_contexts = [dict(row, context_index=i) for i, row in enumerate(contexts)
                           if row['name'].lower() == name]
        if not script_contexts:
            script_contexts = [{'binding_kind': 'unbound_source_context', 'context_index': None,
                                'parameter_fields': None}]
        for call in command_calls(body):
            args = [text for _, text in call['arguments']]
            callback = next((row['name'] for row in method_ranges
                             if row['start'] < call['offset'] < row['end']), None)
            provenance = {'script': script['name'], 'owner': script['owner'], 'callback': callback,
                          'line': script['body_start_line'] + body[:call['offset']].count('\n'),
                          'arguments': args, 'callback_execution_proven': False}
            if call['command'] == 'Attach_Script' and len(args) >= 3 and literal_string(args[1]) == 'Test_Cinematic':
                member = literal_string(args[2])
                if member is None or member.lower() in target_members:
                    callers.append({**provenance, 'control_file_literal': member,
                                    'target_expression': args[0],
                                    'possible_target_assignments': assigned.get(unwrap(args[0]), []),
                                    'target_identity_and_lifetime_proven': False})
            if call['command'] != 'Send_Custom_Event' or len(args) < 4:
                continue
            for context in script_contexts:
                values, unresolved = possible_integers(args[2], constants, assigned, context['parameter_fields'])
                base = constant_id('M00_CUSTOM_CINEMATIC_SET_SLOT', constants)
                if base is None:
                    raise ValueError('original cinematic slot enum was not resolved')
                routes.append({**provenance, 'binding_kind': context['binding_kind'],
                               'context_index': context['context_index'], 'event_type_expression': args[2],
                               'possible_event_types': sorted(values), 'unresolved_event_type_possible': unresolved,
                               'possible_cinematic_slots': sorted(value - base for value in values
                                                                  if base <= value < base + NUM_SLOTS),
                               'destination_expression': args[1], 'custom_parameter_expression': args[3],
                               'delay_expression': args[4] if len(args) > 4 else '0 (original default)',
                               'destination_identity_delivery_and_slot_write_proven': False})
    return routes, callers


def included_constants(directory, source, inherited, seen=None):
    """Discover quoted headers within Scripts, preserving canonical paths.

    This follows a source include graph, not a platform preprocessor. External
    headers and path expressions stay outside the narrow numeric grammar.
    """
    seen = set() if seen is None else seen
    values = dict(inherited)
    code = constant_branch_code(masked(source))
    for name in re.findall(r'^\s*#\s*include\s+"([^"\n]+)"', code, re.MULTILINE):
        if Path(name).name != name or '\\' in name:
            continue
        candidates = [path for path in directory.glob('*.h') if path.name.lower() == name.lower()]
        if len(candidates) > 1:
            raise ValueError('ambiguous source header case alias')
        if not candidates or candidates[0] in seen:
            continue
        header = candidates[0]
        seen.add(header)
        # String-ID definitions are outside this event-type grammar; leaving
        # them unresolved cannot establish absence of a sender.
        if header.name.lower() == 'string_ids.h':
            continue
        text = header.read_text(encoding='latin1')
        values = included_constants(directory, text, values, seen)
        values = numeric_constants(text, values)
    return values


def owner_constants(root, scripts):
    directory = root / 'upstream/CnC_Renegade/Code/Scripts'
    toolkit = numeric_constants((directory / 'Toolkit.h').read_text(encoding='latin1'))
    if toolkit.get('M00_CUSTOM_CINEMATIC_SET_SLOT') != '10000':
        raise ValueError('original cinematic slot range changed; review source contract')
    result = {}
    for owner in {row['owner'] for row in scripts.values()}:
        text = (directory / owner).read_text(encoding='latin1')
        constants = included_constants(directory, text, toolkit)
        result[owner] = numeric_constants(text, constants)
    return result, toolkit


def analyze(binding, cinematic, scripts, constants):
    if binding['map'] != cinematic['map'] or binding['archive_sha256'] != cinematic['archive_sha256']:
        raise ValueError('binding/cinematic identity mismatch')
    routes, callers = source_routes(binding, cinematic['files'], scripts, constants)
    control_events = []
    for file in cinematic['files']:
        for branch, commands in file['branches'].items():
            for command in commands:
                args = command.get('arguments', [])
                if command['command'] != 'send_custom' or len(args) < 3:
                    continue
                event_type = command['custom_event_type']
                control_events.append({'member': file['member'], 'line': command['line'], 'branch': branch,
                                       'seconds_float32': command['seconds_float32'], 'event_type': event_type,
                                       'destination_token': args[0], 'custom_parameter_token': args[2],
                                       'possible_cinematic_slot': event_type - 10000 if event_type is not None
                                           and 10000 <= event_type < 10000 + NUM_SLOTS else None,
                                       'destination_identity_delivery_and_slot_write_proven': False})
    return {'schema_version': 1, 'map': binding['map'], 'archive_sha256': binding['archive_sha256'],
            'evidence_class': 'read-only possible source event values and cinematic caller provenance',
            'custom_routes': routes, 'cinematic_callers': callers, 'control_custom_events': control_events,
            'summary': {'source_event_calls': len({(row['owner'], row['line']) for row in routes}),
                        'event_binding_contexts': len(routes), 'possible_slot_writer_contexts': sum(bool(row['possible_cinematic_slots']) for row in routes),
                        'unresolved_event_type_contexts': sum(row['unresolved_event_type_possible'] for row in routes),
                        'cinematic_callers': len(callers),
                        'control_custom_events': len(control_events),
                        'control_slot_fill_candidates': sum(row['possible_cinematic_slot'] is not None for row in control_events),
                        'callback_contexts': dict(sorted(Counter(row['callback'] or 'unclassified' for row in routes).items()))},
            'runtime_or_physical_acceptance': False, 'complete_mission_closure': False,
            'limits': ['Candidate numeric values do not prove sending, delivery, destination identity, slot mutation or successful registration.',
                       'Same-script assignments are unscoped possible values; unknown/shadowed/callback inputs remain unresolved even when some candidates resolve.',
                       'Only quoted Scripts headers and a narrow enum/numeric-macro/parameter/integer grammar are evaluated; other includes, macros, operators and C++ dataflow are unproved.',
                       'Source counts include all scripts in the mission unit as well as discovered helpers, not only presently attached scripts.',
                       'Synchronous Created/custom recursion, delayed timers, damage/death/corpse behavior and primary-killed snapshots require runtime evidence.',
                       'No retail mutation, C++ compilation, game launch or device action.']}


def verify_definition_receipt(data, binding, archives):
    """Definition-script parameters depend on the matching objects.ddb member."""
    expected = binding.get('objects_ddb_sha256')
    if not isinstance(expected, str) or re.fullmatch(r'[0-9a-f]{64}', expected) is None:
        raise ValueError('binding receipt lacks valid objects.ddb identity')
    if 'always.dbs' not in archives:
        archives['always.dbs'] = MixArchive(data / 'always.dbs')
    payload = archives['always.dbs'].read_binary('objects.ddb')
    if hashlib.sha256(payload).hexdigest() != expected:
        raise ValueError('objects.ddb differs from authored binding receipt')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--bindings-directory', type=Path, required=True)
    parser.add_argument('--output-directory', type=Path, required=True)
    args = parser.parse_args()
    output = args.output_directory.resolve()
    if not output.is_relative_to((args.root / 'build').resolve()):
        parser.error('detailed event receipts must remain under private build/')
    scripts = source_scripts(args.root)
    constants, toolkit = owner_constants(args.root, scripts)
    output.mkdir(parents=True, exist_ok=True)
    archives = {}
    for map_name in MAPS:
        payload = (args.bindings_directory / (Path(map_name).stem.lower() + '-bindings.json')).read_bytes()
        binding = json.loads(payload)
        if binding['map'] != map_name:
            parser.error('binding receipt map mismatch')
        verify_definition_receipt(args.data, binding, archives)
        cinematic = cinematic_audit(args.data, binding, scripts, archives)
        result = analyze(binding, cinematic, scripts, constants)
        result['objects_ddb_sha256'] = binding['objects_ddb_sha256']
        result['binding_receipt_sha256'] = hashlib.sha256(payload).hexdigest()
        result['derived_toolkit_values'] = {name: int(toolkit[name]) for name in (
            'M00_SEND_OBJECT_ID', 'M00_CUSTOM_CINEMATIC_PRIMARY_KILLED', 'M00_CUSTOM_CINEMATIC_SET_SLOT')}
        owners = {row['owner'] for row in result['custom_routes'] + result['cinematic_callers']}
        source = args.root / 'upstream/CnC_Renegade/Code'
        inputs = {source / 'Scripts' / owner for owner in owners}
        inputs.update((source / 'Scripts').glob('*.h'))
        inputs.update(source / path for path in (
            'Combat/scriptcommands.cpp', 'Combat/scriptablegameobj.cpp', 'Combat/gameobjmanager.cpp',
            'Combat/soldier.cpp', 'Combat/activeconversation.cpp', 'Scripts/Test_Cinematic.cpp'))
        result['original_source_hashes'] = {path.relative_to(source).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                                           for path in sorted(inputs)}
        result['verified_text_members'] = [{key: file[key] for key in ('archive', 'member', 'sha256')}
                                           for file in cinematic['files']]
        (output / (Path(map_name).stem.lower() + '-event-routes.json')).write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps({'map': map_name, **result['summary'], 'runtime_verified': False}), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
