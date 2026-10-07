"""Read-only direct text/media and computed conversation candidate discovery.

Same-script assignments are conservative leads, not C++ dataflow or execution
proof. Retail-derived receipts stay in build/ without subtitle/audio payloads.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

from tools.audit_campaign_source_surface import COMMAND_CALL
from tools.audit_mission_content_bindings import MAPS, ROOT, TOKEN, audit_map, masked, parameter_fields, source_scripts
from tools.audit_mission_conversations import resource_context
from tools.renegade_cinematic_dependency_scan import parse_command

OWNERS = {'M00_Tutorial.mix': 'Mission00.cpp', 'M13.mix': 'MissionX0.cpp', 'M01.mix': 'Mission01.cpp'}
TEXT_ARGUMENTS = {'Set_HUD_Help_Text': (0,), 'Display_Text': (0,),
                  'Add_Objective': (3, 5), 'Set_Objective_HUD_Info': (3,),
                  'Set_Objective_HUD_Info_Position': (3,)}
MEDIA_ARGUMENTS = {'Add_Objective': (4, 'objective_description_sound_name'),
                   'Set_Objective_HUD_Info': (2, 'objective_texture'),
                   'Set_Objective_HUD_Info_Position': (2, 'objective_texture')}
IDENTIFIER = re.compile(r'^[A-Za-z_]\w*$')


def arguments(source, start):
    """Return exact argument spans after an opening parenthesis, ignoring tokens."""
    code = masked(source, strings=True)
    stack, begin, rows = [')'], start, []
    pairs = {'(': ')', '[': ']', '{': '}'}
    for pos in range(start, len(code)):
        char = code[pos]
        if char in pairs:
            stack.append(pairs[char])
        elif char in ')]}':
            if not stack or stack.pop() != char:
                raise ValueError('mismatched C++ argument delimiters')
            if not stack:
                rows.append((begin, source[begin:pos].strip()))
                return rows, pos + 1
        elif char == ',' and len(stack) == 1:
            rows.append((begin, source[begin:pos].strip()))
            begin = pos + 1
    raise ValueError('unterminated C++ argument list')


def command_calls(source):
    for match in COMMAND_CALL.finditer(masked(source, strings=True)):
        args, end = arguments(source, match.end())
        yield {'command': match[1], 'offset': match.start(), 'arguments': args, 'end': end}


def unwrap(value):
    value = masked(value).strip()
    while value.startswith('('):
        spans, end = arguments(value, 1)
        if end != len(value) or len(spans) != 1:
            break
        value = spans[0][1]
    return value


def literal_string(value):
    """Narrow literals/concatenation only; unsupported encodings stay unresolved."""
    value = unwrap(value)
    tokens = list(TOKEN.finditer(value))
    if not tokens or any(not token[0].startswith('"') for token in tokens):
        return None
    if re.sub(TOKEN, '', value).strip():
        return None
    result = []
    for token in tokens:
        # C++ hexadecimal escapes consume all following hex digits; Python's
        # literal decoder consumes two. Reject wider forms instead of guessing.
        for escape in re.finditer(r'\\(?:.|$)', token[0]):
            suffix = token[0][escape.start():]
            if re.match(r'\\x[0-9a-fA-F]{3,}', suffix):
                return None
            if not re.match(r'''\\(?:[abfnrtv\\?'"\n]|[0-7]{1,3}|x[0-9a-fA-F]{2})''', suffix):
                return None
        try:
            result.append(ast.literal_eval(token[0]))
        except (SyntaxError, ValueError):
            return None
    # Original narrow-string lookup uses C string termination.
    return ''.join(result).split('\0', 1)[0]


def constant_id(expression, definitions, visiting=()):
    """Resolve a deliberately small numeric/alias grammar; never execute source."""
    try:
        node = ast.parse(expression.strip(), mode='eval').body
    except (SyntaxError, ValueError):
        return None

    def evaluate(node):
        if isinstance(node, ast.Constant) and type(node.value) is int:
            return node.value
        if isinstance(node, ast.Name) and node.id in definitions and node.id not in visiting:
            return constant_id(definitions[node.id], definitions, (*visiting, node.id))
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            value = evaluate(node.operand)
            return None if value is None else value * (-1 if isinstance(node.op, ast.USub) else 1)
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub)):
            left, right = evaluate(node.left), evaluate(node.right)
            return None if left is None or right is None else left + right * (-1 if isinstance(node.op, ast.Sub) else 1)
        return None

    return evaluate(node)


def string_id_definitions(root, header=None):
    if header is None:
        header = (root / 'upstream/CnC_Renegade/Code/Scripts/string_ids.h').read_bytes()
    source = masked(header.decode('latin1'))
    result = {}
    for name, expression in re.findall(r'^\s*#\s*define\s+(\w+)[ \t]+([^\n]+)', source, re.MULTILINE):
        if name in result and result[name].strip() != expression.strip():
            raise ValueError('ambiguous original string ID definition')
        result[name] = expression.strip()
    return result


def assignments(source):
    """Collect all same-script scalar/array assignments with source offsets."""
    code = masked(source, strings=True)
    result = {}
    for match in re.finditer(r'\b(\w+)\s*(?:\[[^\]\n]*\]\s*)?=(?!=)', code):
        prefix = code[:match.start()].rstrip()
        if prefix.endswith(('.', '->', ':')):
            continue  # A member/qualified expression is not a local identifier.
        pos, stack = match.end(), []
        pairs = {'(': ')', '[': ']', '{': '}'}
        while pos < len(code):
            char = code[pos]
            if char in pairs:
                stack.append(pairs[char])
            elif char in ')]}':
                if not stack or stack.pop() != char:
                    break
            elif char == ';' and not stack:
                break
            pos += 1
        value = source[match.end():pos].strip()
        values = []
        if value.startswith('{') and value.endswith('}'):
            spans, _ = arguments('(' + value[1:-1] + ')', 1)
            values = [v for _, v in spans]
        else:
            values = [value]
        result.setdefault(match[1], []).extend({'expression': v, 'offset': match.start()} for v in values)
    return result


def computed_names(expression, row, bindings):
    expression = unwrap(expression)
    parameter = re.fullmatch(r'Get_Parameter\s*\(\s*("(?:\\.|[^"\\])*")\s*\)', expression)
    if parameter:
        name = literal_string(parameter[1])
        if name is None:
            return []
        values = []
        for index, binding in enumerate(bindings):
            if binding['name'].lower() != row['name'].lower():
                continue
            for field in binding.get('parameter_fields') or []:
                if field['name'] is not None and field['name'].lower() == name.lower():
                    values.append({'name': field['value'], 'kind': 'authored_parameter_candidate',
                                   'binding_index': index, 'parameter_index': field['index'],
                                   'binding_kind': binding.get('binding_kind'),
                                   'source_owner': binding.get('source_owner'), 'source_line': binding.get('source_line'),
                                   'archive': binding.get('archive'), 'member': binding.get('member'),
                                   'cinematic_line': binding.get('cinematic_line')})
        return values
    variable = re.fullmatch(r'(\w+)(?:\s*\[.*\])?', expression, re.DOTALL)
    if not variable:
        return []
    values, pending, seen = [], [variable[1]], set()
    assigned = assignments(row['body'])
    while pending:
        name = pending.pop()
        if name in seen:
            continue
        seen.add(name)
        for item in assigned.get(name, []):
            value = literal_string(item['expression'])
            if value is not None:
                values.append({'name': value, 'kind': 'same_script_assignment_candidate',
                               'variable': name,
                               'assignment_line': row['body_start_line'] + row['body'].count('\n', 0, item['offset'])})
            else:
                alias = unwrap(item['expression'])
                if IDENTIFIER.fullmatch(alias):
                    pending.append(alias)
    return values


def source_routes(scripts, binding_audit, ids):
    discovered = {row['name'].lower() for row in binding_audit['discovered_scripts']}
    selected = {key: row for key, row in scripts.items()
                if key in discovered or row['owner'] == OWNERS.get(binding_audit['map'])}
    bindings = list(binding_audit['bindings'])
    source_bindings = []
    for row in selected.values():
        for call in command_calls(row['body']):
            if call['command'] != 'Attach_Script':
                continue
            args = call['arguments']
            name, parameters = literal_string(args[1][1]), literal_string(args[2][1])
            target = scripts.get(name.lower()) if name is not None else None
            if target is None or parameters is None:
                continue
            source_bindings.append({'name': name, 'binding_kind': 'literal_source_attachment',
                                    'source_owner': row['owner'], 'source_script': row['name'],
                                    'source_line': row['body_start_line'] + row['body'].count('\n', 0, call['offset']),
                                    'parameter_fields': parameter_fields(target['descriptor'], parameters)})
    bindings.extend(source_bindings)
    text, media, conversations = [], [], []
    for key, row in sorted(selected.items()):
        for call in command_calls(row['body']):
            command, args = call['command'], call['arguments']
            origin = {'script': row['name'], 'owner': row['owner'], 'command': command,
                      'script_in_discovered_closure': key in discovered,
                      'line': row['body_start_line'] + row['body'].count('\n', 0, call['offset'])}
            for index in TEXT_ARGUMENTS.get(command, ()):
                if index >= len(args):
                    continue  # Optional trailing argument (Add_Objective long ID) left at its default.
                expression = args[index][1]
                value = constant_id(expression, ids)
                text.append({**origin, 'argument_index': index, 'expression': expression, 'text_id': value,
                             'state': 'clear_help' if value == 0 and command == 'Set_HUD_Help_Text' else
                             'resolved_source_id' if value is not None and 0 <= value <= 0x7fffffff else
                             'unresolved_or_out_of_range_expression'})
            if command in MEDIA_ARGUMENTS:
                index, kind = MEDIA_ARGUMENTS[command]
                if index >= len(args):
                    continue  # Optional description-sound argument left at its default (NULL).
                expression = args[index][1]
                media.append({**origin, 'kind': kind, 'expression': expression,
                              'name': literal_string(expression), 'null_argument': expression.strip() in ('NULL', '0', 'nullptr')})
            if command == 'Create_Conversation':
                expression = args[0][1]
                literal = literal_string(expression)
                candidates = ([{'name': literal, 'kind': 'literal_argument'}] if literal is not None else
                              computed_names(expression, row, bindings))
                conversations.append({**origin, 'expression': expression, 'computed': literal is None,
                                      'candidates': candidates})
    return {'text_calls': text, 'media_calls': media, 'conversation_calls': conversations,
            'source_attachment_bindings': source_bindings}


def texture_candidates(files, filename, mission):
    """Original DDSFileClass replaces the last three extension characters."""
    result = []
    if len(filename) >= 4 and filename[-4] == '.':
        dds_name = filename[:-3] + 'dds'
        result.extend({**row, 'lookup_role': 'original_dds_attempt'} for row in files.candidates(dds_name, mission))
    if filename.lower().endswith('.tga'):
        result.extend({**row, 'lookup_role': 'original_targa_fallback'} for row in files.candidates(filename, mission))
    return result


def cinematic_bindings(binding, scripts, archives):
    """Retain parameters from reached text variants, with archive/hash provenance."""
    result = []
    by_name = {a.path.name: a for a in archives}
    for member in binding.get('media', {}).get('text_members', []):
        payload = by_name[member['archive']].read_binary(member['member'])
        if hashlib.sha256(payload).hexdigest() != member['sha256']:
            raise ValueError('cinematic candidate changed since binding discovery')
        for line, text in enumerate(payload.decode('latin1').splitlines(), 1):
            command = parse_command(text)
            if command is None or command[1] != 'attach_script' or len(command[2]) < 3:
                continue
            args = command[2]
            target = scripts.get(args[1].lower())
            if target is None:
                continue
            result.append({'name': args[1], 'binding_kind': 'cinematic_attachment',
                           'archive': member['archive'], 'member': member['member'], 'sha256': member['sha256'],
                           'cinematic_line': line, 'time_token': command[0], 'object_slot': args[0],
                           'parameter_fields': parameter_fields(target['descriptor'], args[2])})
    return result


def audit(root, data, map_name, context=None, scripts=None):
    context = resource_context(data) if context is None else context
    scripts = source_scripts(root) if scripts is None else scripts
    binding = audit_map(root, data, map_name, scripts)
    from tools.audit_deep_saved_content import conversations as decode_conversations
    from tools.audit_m13_level_owners import chunks
    from tools.renegade_cinematic_dependency_scan import MixArchive
    mission = MixArchive(data / map_name)
    text_bindings = cinematic_bindings(binding, scripts, [mission, *context.get('archives', [])])
    id_header = (root / 'upstream/CnC_Renegade/Code/Scripts/string_ids.h').read_bytes()
    ids = string_id_definitions(root, id_header)
    routes = source_routes(scripts, {**binding, 'bindings': [*binding['bindings'], *text_bindings]}, ids)
    names = {r['name'].lower() for c in context['globals'] for r in c['rows']}
    for name in mission.entries:
        if name.endswith(('.ldd', '.lsd')):
            names.update(r['name'].lower() for r in decode_conversations(chunks(mission.read_binary(name)), allow_legacy_category=False))
    for call in routes['conversation_calls']:
        for candidate in call['candidates']:
            candidate['located_in_conversation_records'] = candidate['name'].lower() in names
    help_header = (root / 'port/platform/renegade_vita_tutorial_help.h').read_bytes()
    help_source = masked(help_header.decode('utf-8'))
    help_ids = {constant_id(value, ids) for value in re.findall(r'\bcase\s+(\w+)\s*:', help_source)}
    help_ids.discard(None)
    for call in routes['text_calls']:
        call['has_english_vita_help_replacement'] = call['command'] == 'Set_HUD_Help_Text' and call['text_id'] in help_ids
    variants = []
    for candidate in context['strings']:
        finding = []
        for call in routes['text_calls']:
            if call['state'] == 'resolved_source_id' and call['text_id'] not in candidate['rows']:
                finding.append({**call, 'kind': 'direct_text_id_not_located'})
        variants.append({'archive': candidate['archive'], 'member': candidate['member'],
                         'sha256': candidate['sha256'], 'findings': finding})
    for call in routes['media_calls']:
        if call['kind'] == 'objective_texture' and call['name'] is not None:
            call['candidates'] = texture_candidates(context['files'], call['name'], mission)
        elif call['kind'] == 'objective_description_sound_name' and call['name'] is not None:
            call['definition_candidates'] = [{'id': key, 'factory': row['factory']}
                                            for key, row in context['definitions'].items()
                                            if row['name'].lower() == call['name'].lower()]
    candidates = [value for row in routes['conversation_calls'] for value in row['candidates']]
    return {'schema_version': 1, 'map': map_name, 'archive_sha256': binding['archive_sha256'],
            'source_input_sha256': {'string_ids.h': hashlib.sha256(id_header).hexdigest(),
                                    'renegade_vita_tutorial_help.h': hashlib.sha256(help_header).hexdigest()},
            'evidence_class': 'read-only source and authored text/media candidate metadata',
            **routes, 'cinematic_attachment_bindings': text_bindings, 'translation_candidates': variants,
            'summary': {'direct_text_calls': len(routes['text_calls']),
                        'unique_direct_text_ids': len({r['text_id'] for r in routes['text_calls'] if r['state'] == 'resolved_source_id'}),
                        'unresolved_text_expressions': sum(r['state'] == 'unresolved_or_out_of_range_expression' for r in routes['text_calls']),
                        'text_findings_per_candidate': {c['archive']: len(c['findings']) for c in variants},
                        'objective_texture_calls': sum(r['kind'] == 'objective_texture' for r in routes['media_calls']),
                        'unlocated_objective_textures': sorted({r['name'] for r in routes['media_calls'] if r['kind'] == 'objective_texture' and r['name'] is not None and not r['candidates']}),
                        'computed_conversation_calls': sum(r['computed'] for r in routes['conversation_calls']),
                        'computed_calls_without_candidates': sum(r['computed'] and not r['candidates'] for r in routes['conversation_calls']),
                        'conversation_candidate_kinds': dict(sorted(Counter(r['kind'] for r in candidates).items())),
                        'unlocated_conversation_candidate_names': sorted({r['name'] for r in candidates if not r['located_in_conversation_records']})},
            'runtime_or_physical_acceptance': False, 'complete_mission_closure': False,
            'limits': ['Same-script assignments, aliases and array entries are conservative candidates without branch/scope/index-range proof.',
                       'Computed calls remain open, including those with located candidates; function returns, members, dynamic formatting and defaults need tracing.',
                       'Direct HUD text does not automatically play its translation sound; objective description sound names are separate stored fields.',
                       'File/ID presence and English prompt source coverage do not prove display, playback, translation, input or physical correctness.',
                       'No subtitle/audio payload export, retail writes, C++ compilation, launch or device actions.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--map', action='append', dest='maps')
    parser.add_argument('--output-directory', type=Path, required=True)
    args = parser.parse_args()
    output = args.output_directory.resolve()
    if not output.is_relative_to((args.root / 'build').resolve()):
        parser.error('detailed receipts must remain under private build/')
    maps = args.maps or MAPS
    if any('/' in n or '\\' in n or not n.lower().endswith('.mix') for n in maps):
        parser.error('map names must be archive filenames below retail Data')
    context, scripts = resource_context(args.data), source_scripts(args.root)
    output.mkdir(parents=True, exist_ok=True)
    for name in maps:
        result = audit(args.root, args.data, name, context, scripts)
        (output / (Path(name).stem.lower() + '-text-routes.json')).write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps({'map': name, **result['summary']}, sort_keys=True), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
