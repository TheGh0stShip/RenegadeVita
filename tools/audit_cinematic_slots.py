"""Read-only cinematic command ordering and slot producer/lifetime leads.

This traces authored text, not the game. Creates may fail, scripts/custom
events may change objects, and primary death can occur at an unknown time.
Detailed receipts belong in ignored build/ and never establish a mission pass.
"""
from __future__ import annotations

import argparse
from collections import Counter
import copy
import hashlib
import json
import math
from pathlib import Path
import re
import struct

from tools.audit_mission_content_bindings import MAPS, ROOT, masked, source_scripts
from tools.audit_mission_text_routes import arguments, command_calls
from tools.renegade_cinematic_dependency_scan import MixArchive

NUM_SLOTS = 40
LAST_VALID_TIMESTAMP = 999000.0
KNOWN_COMMANDS = (
    'create_object', 'create_real_object', 'create_explosion', 'destroy_object',
    'play_animation', 'play_audio', 'control_camera', 'send_custom',
    'attach_to_bone', 'attach_script', 'set_primary', 'move_slot',
    'sniper_control', 'shake_camera', 'enable_shadow', 'enable_letterbox',
    'set_screen_fade_color', 'set_screen_fade_opacity',
)
DECIMAL_PREFIX = re.compile(r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?')
ASCII_SPACE = ''.join(chr(value) for value in range(1, 33))
EFFECT_COMMANDS = {'Apply_Damage', 'Destroy_Object', 'Send_Custom_Event',
                   'Attach_Script', 'Create_Object', 'Create_Object_At_Bone'}


def float32(value):
    result = struct.unpack('<f', struct.pack('<f', value))[0]
    if not math.isfinite(result):
        raise ValueError('nonfinite original float timestamp')
    return result


def time_seconds(token):
    prefix = DECIMAL_PREFIX.match(token)
    if token.lower().lstrip('+-').startswith(('inf', 'nan', '0x')):
        raise ValueError('unsupported original atof spelling')
    # Original atof returns zero when there is no initial number.
    value = float32(float(prefix[0]) if prefix else 0.0)
    return float32(-value / 30.0) if value < 0 else value


def integer(token):
    # Original atoi consumes an initial decimal integer, or returns zero.
    # Overflow stays open; never reinterpret IDs as pointers.
    prefix = re.match(r'\s*([+-]?\d+)', token)
    value = int(prefix[1]) if prefix else 0
    return value if -0x80000000 <= value <= 0x7fffffff else None


def runtime_parameters(text):
    """Original Get_Command_Parameter quote/comma behavior, not CSV escaping."""
    values, pos = [], 0
    while pos < len(text):
        begin = pos
        while begin < len(text) and text[begin] <= ' ':
            begin += 1
        if begin < len(text) and text[begin] == '"':
            begin += 1
            pos = begin
            while pos < len(text) and text[pos] != '"':
                pos += 1
        while pos < len(text) and text[pos] != ',':
            pos += 1
        value = text[begin:pos].rstrip(ASCII_SPACE)
        values.append(value[:-1] if value.endswith('"') else value)
        if pos == len(text):
            break
        pos += 1
        if pos == len(text):
            values.append('')
    return values


def control_records(payload):
    records, findings = [], []
    # Text_File_Get_String consumes to LF, retains at most 199 bytes including
    # any CR/LF in that window, and discards the remainder of a long line.
    lines = payload.split(b'\n')
    for line_number, raw in enumerate(lines, 1):
        if line_number < len(lines):
            raw += b'\n'
        text = raw[:199].split(b'\0', 1)[0].decode('latin1').strip(ASCII_SPACE)
        if not text or text.startswith(';'):
            continue
        if len(raw) > 199:
            findings.append({'line': line_number, 'kind': 'runtime_line_truncated', 'bytes': len(raw)})
        parts = re.match(r'^([^\x00-\x20]+)[\x00-\x20]+(.+)$', text)
        if parts is None:
            findings.append({'line': line_number, 'kind': 'original_loader_ignores_line_without_command'})
            continue
        token, command_text = parts.groups()
        try:
            seconds = time_seconds(token)
        except (ValueError, OverflowError):
            findings.append({'line': line_number, 'kind': 'unsupported_float32_time'})
            continue
        # Original Title_Match accepts a matching title prefix, then skips to
        # the comma. Unknown command text remains a no-dispatch review lead.
        command = next((name for name in KNOWN_COMMANDS if command_text.lower().startswith(name)), None)
        if command is None:
            command = command_text.split(',', 1)[0].strip().lower()
            args = []
            findings.append({'line': line_number, 'kind': 'original_parser_unknown_command', 'command': command})
        else:
            args = runtime_parameters(command_text.split(',', 1)[1]) if ',' in command_text else []
        branch = ('normal' if seconds < LAST_VALID_TIMESTAMP else
                  'primary_killed_tail' if seconds > LAST_VALID_TIMESTAMP else 'boundary')
        records.append({'line': line_number, 'time_token': token, 'seconds_float32': seconds,
                        'branch': branch, 'command': command,
                        'source_command_title': command_text.split(',', 1)[0], 'arguments': args})
    # Original Add_Control_Line inserts after existing equal timestamps.
    return sorted(records, key=lambda row: (row['seconds_float32'], row['line'])), findings


def created_body(source):
    code = masked(source, strings=True)
    match = re.search(r'\bvoid\s+Created\s*\(', code)
    if match is None:
        return ''
    _, end = arguments(source, match.end())
    start = end
    while start < len(code) and code[start].isspace():
        start += 1
    if start == len(code) or code[start] != '{':
        return ''
    depth = 1
    for end in range(start + 1, len(code)):
        depth += (code[end] == '{') - (code[end] == '}')
        if depth == 0:
            return source[start + 1:end]
    raise ValueError('unclosed Created callback')


def script_effects(name, scripts):
    row = scripts.get(name.lower())
    if row is None:
        return {'name': name, 'source_owner': None, 'source_not_located': True}
    return {'name': name, 'source_owner': row['owner'], 'source_start_line': row['body_start_line'],
            'possible_effect_commands': sorted({c['command'] for c in command_calls(row['body'])
                                                 if c['command'] in EFFECT_COMMANDS}),
            'created_possible_effect_commands': sorted({c['command'] for c in command_calls(created_body(row['body']))
                                                         if c['command'] in EFFECT_COMMANDS}),
            'callback_execution_proven': False}


def slot_uses(command, args):
    """Typed lookup roles; event types and literal parameters are not IDs."""
    if command in ('destroy_object', 'play_animation', 'attach_script', 'set_primary',
                   'shake_camera', 'enable_shadow'):
        return [(0, 'object', 'guarded')]
    if command == 'create_real_object' and len(args) > 2 and args[2]:
        return [(2, 'creation_host', 'unchecked')]
    if command == 'create_explosion':
        return [(1, 'explosion_host', 'unchecked')]
    if command == 'play_audio' and len(args) > 1 and args[1]:
        return [(1, 'audio_host', 'audio_2d_fallback')]
    if command == 'control_camera':
        return [(0, 'camera_host', 'camera_restore_fallback')]
    if command == 'attach_to_bone':
        return [(0, 'object', 'guarded'), (1, 'bone_host', 'detach_fallback')]
    if command == 'move_slot':
        return [(1, 'move_source', 'guarded')]
    if command == 'send_custom':
        return [(i, role, 'guarded') for i, role in ((0, 'custom_destination'), (2, 'custom_parameter'))
                if len(args) > i and '#' in args[i]]
    return []


def trace_branch(records, branch, scripts, object_ids, spawner_ids):
    slots = [[None] for _ in range(NUM_SLOTS)]
    producers, output, findings = {}, [], []
    for original in records:
        row = copy.deepcopy(original)
        args, command = row['arguments'], row['command']
        uses = []
        for index, role, guard in slot_uses(command, args):
            if index >= len(args):
                findings.append({'line': row['line'], 'kind': 'missing_slot_argument', 'argument': index})
                continue
            token = args[index].split('#', 1)[-1] if command == 'send_custom' else args[index]
            slot = integer(token)
            use = {'role': role, 'argument_index': index, 'slot': slot, 'source_token': token,
                   'original_atoi_uses_prefix_or_zero': not bool(re.fullmatch(r'[+-]?\d+', token))}
            if slot is None:
                use['state'] = 'unsupported_integer_token'
            elif not 0 <= slot < NUM_SLOTS:
                use['state'] = {'audio_2d_fallback': 'original_2d_audio',
                                'camera_restore_fallback': 'original_camera_restore',
                                'detach_fallback': 'original_bone_detach'}.get(guard,
                                  'unchecked_out_of_range' if guard == 'unchecked' else 'original_guard_skips_lookup')
            else:
                candidates = [copy.deepcopy(producers[key]) for key in slots[slot] if key is not None]
                use.update({'state': 'text_producer_candidates' if candidates else 'no_prior_text_producer',
                            'producer_candidates': candidates,
                            'prior_empty_or_unknown_snapshot_possible': None in slots[slot],
                            'external_slot_fill_and_runtime_lifetime_unverified': True})
            uses.append(use)
        row['slot_uses'] = uses
        if command == 'play_audio':
            row['audio_preset_name'] = args[0] if args else ''
            row['trailing_arguments_ignored_by_original_command'] = args[3:]
        if command == 'send_custom':
            if len(args) < 3:
                findings.append({'line': row['line'], 'kind': 'missing_custom_argument'})
            else:
                row['custom_event_type'] = integer(args[1])
                if '#' not in args[0]:
                    value = integer(args[0])
                    row['literal_custom_destination'] = {
                        'id': value,
                        'classification': 'zero_or_unsupported_integer' if value in (None, 0) else
                        'serialized_game_object' if value in object_ids else
                        'spawner_namespace_only' if value in spawner_ids else 'not_located_in_serialized_ids',
                        'live_lookup_proven': False}
                if '#' not in args[2]:
                    row['literal_custom_parameter'] = integer(args[2])
        if command in ('create_object', 'create_real_object'):
            slot = integer(args[0]) if args else None
            if len(args) < 2:
                findings.append({'line': row['line'], 'kind': 'missing_creation_argument'})
            elif slot is not None and 0 <= slot < NUM_SLOTS:
                key = row['line']
                producers[key] = {'creation_line': key, 'command': command, 'name': args[1],
                                  'seconds_float32': row['seconds_float32'], 'possible_effects': [],
                                  'creation_success_proven': False}
                # A failed create retains the previous numeric slot value.
                slots[slot] = [*slots[slot], key]
                row['creation_slot'] = slot
        elif command == 'move_slot' and len(args) >= 2:
            new, old = integer(args[0]), integer(args[1])
            if new is not None and old is not None and 0 <= new < NUM_SLOTS and 0 <= old < NUM_SLOTS and new != old:
                slots[new], slots[old] = list(slots[old]), [None]
        elif command in ('destroy_object', 'attach_script') and args:
            slot = integer(args[0])
            if slot is not None and 0 <= slot < NUM_SLOTS:
                effect = {'line': row['line'], 'kind': 'destroy_requested_raw_slot_retained'}
                if command == 'attach_script':
                    if len(args) < 2:
                        findings.append({'line': row['line'], 'kind': 'missing_script_argument'})
                        effect = None
                    else:
                        effect = {'line': row['line'], 'kind': 'script_attachment_candidate',
                                  **script_effects(args[1], scripts)}
                        row['script_source'] = copy.deepcopy(effect)
                if effect is not None:
                    for key in slots[slot]:
                        if key is not None:
                            producers[key]['possible_effects'].append(copy.deepcopy(effect))
        row['initial_slot_snapshot'] = 'zero_at_created_before_external_events' if branch == 'normal' else 'unknown_at_primary_death'
        output.append(row)
    return output, findings


def trace(payload, scripts, object_ids=(), spawner_ids=()):
    records, findings = control_records(payload)
    branches = {}
    for branch in ('normal', 'primary_killed_tail'):
        rows, issues = trace_branch([r for r in records if r['branch'] == branch], branch,
                                    scripts, set(object_ids), set(spawner_ids))
        branches[branch] = rows
        findings.extend(issues)
    branches['boundary'] = [r for r in records if r['branch'] == 'boundary']
    return {'branches': branches, 'findings': findings,
            'command_count': len(records), 'command_counts': dict(sorted(Counter(r['command'] for r in records).items()))}


def audit(data, binding, scripts, archives=None):
    if binding['map'] not in MAPS:
        raise ValueError('unsupported mission binding map')
    mission = MixArchive(data / binding['map'])
    if hashlib.sha256(mission.path.read_bytes()).hexdigest() != binding['archive_sha256']:
        raise ValueError('mission archive differs from authored binding receipt')
    by_name = archives if archives is not None else {}
    by_name[mission.path.name] = mission
    object_ids = {r['instance_id'] for member in binding['members'].values() for r in member['objects'] if r['instance_id']}
    spawner_ids = {r['instance_id'] for member in binding['members'].values() for r in member['spawners'] if r['instance_id']}
    files = []
    for member in binding['media']['text_members']:
        if Path(member['archive']).name != member['archive'] or '\\' in member['archive']:
            raise ValueError('cinematic archive must be a filename below retail Data')
        if member['archive'] not in by_name:
            by_name[member['archive']] = MixArchive(data / member['archive'])
        payload = by_name[member['archive']].read_binary(member['member'])
        if hashlib.sha256(payload).hexdigest() != member['sha256']:
            raise ValueError('cinematic candidate differs from authored binding receipt')
        files.append({**member, **trace(payload, scripts, object_ids, spawner_ids)})
    rows = [row for file in files for branch in file['branches'].values() for row in branch]
    uses = [use for row in rows for use in row.get('slot_uses', [])]
    return {'schema_version': 1, 'map': binding['map'], 'archive_sha256': binding['archive_sha256'],
            'evidence_class': 'read-only authored cinematic order and possible slot producers', 'files': files,
            'summary': {'text_candidates': len(files), 'commands': len(rows),
                        'branch_commands': dict(sorted(Counter(row['branch'] for row in rows).items())),
                        'typed_slot_uses': len(uses),
                        'slot_use_states': dict(sorted(Counter(use['state'] for use in uses).items())),
                        'parser_findings': sum(len(file['findings']) for file in files)},
            'runtime_or_physical_acceptance': False, 'complete_mission_closure': False,
            'limits': ['Only text candidates reached by the supplied authored binding receipt are traced.',
                       'Original narrow parameter parsing, atoi prefix/zero behavior and float32 ordering model source rules, not runtime timer delivery.',
                       'Creates are attempts, not successful writes; failed creation may retain an earlier ID. External slot fills remain open.',
                       'Destroy requests retain raw IDs. Attached-script effect calls across callbacks are leads, not executed damage/death or proven deletion.',
                       'Primary-killed tail begins from an unknown death-time snapshot; end-of-normal slot state is not reused.',
                       'No retail writes, game builds/launches, device actions, runtime slot closure, rendering or audio acceptance.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--bindings-directory', type=Path, required=True)
    parser.add_argument('--output-directory', type=Path, required=True)
    args = parser.parse_args()
    output = args.output_directory.resolve()
    if not output.is_relative_to((args.root / 'build').resolve()):
        parser.error('detailed receipts must remain under private build/')
    scripts = source_scripts(args.root)
    output.mkdir(parents=True, exist_ok=True)
    archives = {}
    for map_name in MAPS:
        path = args.bindings_directory / (Path(map_name).stem.lower() + '-bindings.json')
        payload = path.read_bytes()
        binding = json.loads(payload)
        if binding['map'] != map_name:
            parser.error('binding receipt map mismatch')
        result = audit(args.data, binding, scripts, archives)
        result['binding_receipt_sha256'] = hashlib.sha256(payload).hexdigest()
        source = args.root / 'upstream/CnC_Renegade/Code/Scripts/Test_Cinematic.cpp'
        result['original_cinematic_source_sha256'] = hashlib.sha256(source.read_bytes()).hexdigest()
        (output / (Path(map_name).stem.lower() + '-cinematic-slots.json')).write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps({'map': map_name, **result['summary']}, sort_keys=True), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
