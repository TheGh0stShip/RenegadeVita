"""Read-only soldier dialogue options and unresolved voice-reference provenance.

An option in a preset or serialized instance is metadata, not an executed bark.
Detailed retail-derived records stay under ignored build/; no subtitle/audio
payload, C++ compilation, engine execution, retail mutation or device action.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
import math
from pathlib import Path
import re
import struct

from tools.audit_deep_saved_content import conversations
from tools.audit_m13_level_owners import chunks, flatten, microchunks, u32
from tools.audit_mission_content_bindings import MAPS, ROOT, audit_map, constant_branch_code, masked, source_scripts
from tools.audit_mission_conversations import digest, resource_context, sound_chain, sound_definitions
from tools.audit_mission_event_routes import enum_constants
from tools.renegade_cinematic_dependency_scan import MixArchive


def source_schema(root=ROOT):
    specs = {'save_ids': 'staging/wwsaveload/saveloadids.h',
             'soldier': 'staging/combat/soldier.cpp',
             'dialogue': 'staging/combat/dialogue.cpp',
             'events': 'staging/combat/dialogue.h',
             'factories': 'staging/combat/combatchunkid.h'}
    constants, provenance = {}, []
    for scope, path in specs.items():
        source = (root / path).read_bytes()
        inherited = {k: str(v) for k, v in constants['save_ids'].items()} if scope == 'factories' else None
        constants[scope] = {k: int(v) for k, v in enum_constants(source.decode('latin1'), inherited).items()}
        provenance.append({'path': path, 'sha256': digest(source)})
    event_source = masked((root / specs['dialogue']).read_text(encoding='latin1'))
    array = re.search(r'\bDIALOG_EVENT_NAMES\s*\[DIALOG_MAX\]\s*=\s*\{(.*?)\}', event_source, re.DOTALL)
    names = re.findall(r'"([A-Z0-9_]+)"', array[1]) if array else []
    schema = {'definition_entry': constants['soldier']['CHUNKID_DEF_DIALOG_ENTRY'],
              'instance_entry': constants['soldier']['CHUNKID_DIALOG_ENTRY'],
              'dialogue_variables': constants['dialogue']['CHUNKID_DIALOGUE_VARIABLES'],
              'option': constants['dialogue']['CHUNKID_DIALOGUE_OPTION'],
              'option_variables': constants['dialogue']['CHUNKID_OPTION_VARIABLES'],
              'silence_field': constants['dialogue']['VARID_DIALOGUE_SILENCE'],
              'weight_field': constants['dialogue']['VARID_WEIGHT'],
              'conversation_field': constants['dialogue']['VARID_CONVERSATION_ID'],
              'definition_factory': constants['factories']['CHUNKID_GAME_OBJECT_DEF_SOLDIER'],
              'instance_factory': constants['factories']['CHUNKID_GAME_OBJECT_SOLDIER'],
              'event_count': constants['events']['DIALOG_MAX'], 'event_names': names,
              'event_symbols': {k: v for k, v in constants['events'].items() if k.startswith('DIALOG_') and k != 'DIALOG_MAX'}}
    if len(names) != schema['event_count']:
        raise ValueError('original dialogue event ordinal/name mismatch')
    # The identity chunk/fields belong to the existing original BaseGameObj decoder.
    for path in ('staging/combat/dialogue.cpp', 'staging/combat/soldier.cpp',
                 'staging/combat/activeconversation.cpp', 'staging/wwaudio/WWAudio.cpp',
                 'staging/wwsaveload/definitionmgr.cpp', 'staging/wwtranslatedb/translateobj.cpp'):
        if not any(row['path'] == path for row in provenance):
            provenance.append({'path': path, 'sha256': digest((root / path).read_bytes())})
    return schema, provenance


def event_callers(source, schema, owner):
    code = constant_branch_code(masked(source, strings=True))
    result = []
    for match in re.finditer(r'(?<![:\w])\bSay_Dialogue\s*\(([^()]*)\)', code):
        expression = match[1].strip()
        event = schema['event_symbols'].get(expression)
        result.append({'owner': owner, 'line': source.count('\n', 0, match.start()) + 1,
                       'expression': expression, 'event_ordinal': event,
                       'event_name': schema['event_names'][event] if event is not None else None})
    return result


def signed(value):
    return value if value < 0x80000000 else value - 0x100000000


def float_metadata(data, serialized):
    if len(data) != 4:
        raise ValueError('expected original float32 field')
    value = struct.unpack('<f', data)[0]
    kind = 'nonfinite' if not math.isfinite(value) else 'positive' if value > 0 else 'zero' if value == 0 else 'negative'
    return {'bits': u32(data), 'value': value if math.isfinite(value) else None,
            'class': kind, 'serialized': serialized}


def dialogue_tables(entries, schema):
    tables = []
    for event, entry in enumerate(entries[:schema['event_count']]):
        silence, silence_writes = struct.pack('<f', 1.0), 0
        options = []
        for node in entry.children:
            if node.kind == schema['dialogue_variables']:
                for key, value in microchunks(node.data):
                    if key == schema['silence_field']:
                        silence, silence_writes = value, silence_writes + 1
            elif node.kind == schema['option']:
                weight, conversation, weight_writes, conversation_writes = struct.pack('<f', 1.0), 0, 0, 0
                for variables in node.children:
                    if variables.kind != schema['option_variables']:
                        continue
                    for key, value in microchunks(variables.data):
                        if key == schema['weight_field']:
                            weight, weight_writes = value, weight_writes + 1
                        elif key == schema['conversation_field']:
                            conversation, conversation_writes = u32(value), conversation_writes + 1
                options.append({'ordinal': len(options), 'weight': float_metadata(weight, weight_writes > 0),
                                'raw_conversation_id': conversation, 'conversation_id': signed(conversation),
                                'conversation_serialized': conversation_writes > 0,
                                'weight_writes': weight_writes, 'conversation_writes': conversation_writes})
        tables.append({'event_ordinal': event, 'event_name': schema['event_names'][event],
                       'silence_weight': float_metadata(silence, silence_writes > 0),
                       'silence_writes': silence_writes, 'options': options})
    return tables, max(0, len(entries) - schema['event_count'])


def factory_body(factory):
    if [child.kind for child in factory.children] != [0x100100, 0x100101]:
        raise ValueError('invalid original soldier persist factory wrapper')
    return factory.children[1].children


def definition_dialogues(nodes, defs, schema):
    by_offset = {row['offset']: key for key, row in defs.items()}
    result = {}
    for manager in nodes:
        if manager.kind != 0x101:
            continue
        for group in manager.children:
            if group.kind != 0x101:
                continue
            for factory in group.children:
                if factory.kind != schema['definition_factory']:
                    continue
                entries = [node for node in factory_body(factory) if node.kind == schema['definition_entry']]
                tables, ignored = dialogue_tables(entries, schema)
                key = by_offset[factory.offset]
                result[key] = {'definition_id': key, 'offset': factory.offset, 'tables': tables,
                               'ignored_excess_event_entries': ignored}
    return result


def instance_dialogues(nodes, schema):
    result = []
    for factory in flatten(nodes):
        if factory.kind != schema['instance_factory']:
            continue
        body = factory_body(factory)
        identities = []
        for node in flatten(body):
            if node.kind == 910991407:  # Existing BaseGameObj named identity layout.
                fields = dict(microchunks(node.data))
                identities.append({'definition_id': u32(fields[2]), 'instance_id': u32(fields[3])})
        if len(identities) != 1:
            raise ValueError('missing/ambiguous serialized soldier identity')
        entries = [node for node in body if node.kind == schema['instance_entry']]
        tables, ignored = dialogue_tables(entries, schema)
        result.append({**identities[0], 'offset': factory.offset,
                       'serialized_id_state': 'zero_assignment_lifetime_unverified' if identities[0]['instance_id'] == 0 else 'nonzero_serialized_id',
                       'old_pointer_token': u32(factory.children[0].data), 'tables': tables,
                       'ignored_excess_event_entries': ignored})
    return result


def sound_reference(raw):
    effective = 0xffffffff if raw is None else raw
    return {'serialized_sound_id': raw, 'effective_sound_id': effective,
            'signed_sound_id': signed(effective),
            'state': 'absent_original_default_minus_one' if raw is None else 'zero' if raw == 0 else
                     'positive_int32' if signed(raw) > 0 else 'negative_int32',
            'soldier_speech_lookup_attempt': signed(effective) > 0,
            'conversation_duration_lookup_attempt': effective != 0}


def remark_voice(remark, strings, defs, files, mission):
    key = remark['text_id']
    row = strings.get(key)
    if row is None:
        return {'text_id': key, 'findings': [{'kind': 'conversation_text_id_not_located', 'id': key}]}
    reference = sound_reference(row['sound_id'])
    leaves, findings = [], []
    if reference['soldier_speech_lookup_attempt']:
        leaves, findings = sound_chain(reference['effective_sound_id'], defs, files, mission)
    return {'text_id': key, **reference, 'sound_leaves': leaves, 'findings': findings}


def link_options(owners, conversation_rows, strings, defs, files, mission):
    by_id = defaultdict(list)
    for row in conversation_rows:
        by_id[row['id']].append(row)
    resolved = {}
    links = []
    for owner in owners:
        for table in owner['tables']:
            for option in table['options']:
                key = option['conversation_id']
                if key not in resolved:
                    matches = by_id.get(key, []) if key > 0 else []
                    candidates = []
                    for row in matches:
                        chains = [remark_voice(r, strings, defs, files, mission) for r in row['remarks']]
                        candidates.append({'archive': row['archive'], 'member': row['member'], 'name': row['name'],
                                           'id': row['id'], 'category': row.get('category'), 'chains': chains,
                                           'has_voice_finding': any(c['findings'] for c in chains)})
                    resolved[key] = {'conversation_id': key,
                                     'state': 'nonpositive_id_no_start' if key <= 0 else
                                              'not_located' if not matches else
                                              'ambiguous_candidates' if len(matches) > 1 else 'located_candidate',
                                     'candidates': candidates}
                links.append({**{k: v for k, v in owner.items() if k != 'tables'},
                              'event_ordinal': table['event_ordinal'], 'event_name': table['event_name'],
                              'silence_weight': table['silence_weight'], **option,
                              'has_voice_finding_candidate': any(c['has_voice_finding'] for c in resolved[key]['candidates']),
                              'conversation_resolution': resolved[key]['state']})
    return links, [resolved[key] for key in sorted(resolved)]


def link_summary(links):
    gaps = [r for r in links if r['has_voice_finding_candidate']]
    return {'option_records': len(links), 'positive_conversation_ids': len({r['conversation_id'] for r in links if r['conversation_id'] > 0}),
            'voice_finding_option_records': len(gaps), 'voice_finding_conversation_ids': len({r['conversation_id'] for r in gaps}),
            'voice_finding_definition_ids': len({r['definition_id'] for r in gaps}),
            'voice_finding_weight_classes': dict(sorted(Counter(r['weight']['class'] for r in gaps).items())),
            'voice_finding_events': dict(sorted(Counter(r['event_name'] for r in gaps).items())),
            'voice_finding_zero_id_option_records': sum(r['scope'] == 'serialized_instance' and r['instance_id'] == 0 for r in gaps),
            'unlocated_conversation_option_records': sum(r['conversation_resolution'] == 'not_located' for r in links),
            'ambiguous_conversation_option_records': sum(r['conversation_resolution'] == 'ambiguous_candidates' for r in links)}


def audit(root, data, map_name, context=None, scripts=None):
    schema, sources = source_schema(root)
    callers = []
    for path in sorted((root / 'staging/combat').glob('*.cpp')):
        rows = event_callers(path.read_text(encoding='latin1'), schema, str(path.relative_to(root)))
        callers.extend(rows)
        if rows and not any(row['path'] == str(path.relative_to(root)) for row in sources):
            sources.append({'path': str(path.relative_to(root)), 'sha256': digest(path.read_bytes())})
    context = resource_context(data) if context is None else context
    bindings = audit_map(root, data, map_name, scripts)
    mission, database = MixArchive(data / map_name), MixArchive(data / 'always.dbs')
    payload = database.read_binary('objects.ddb')
    if digest(payload) != bindings['objects_ddb_sha256']:
        raise ValueError('authored binding definition database identity changed')
    nodes = chunks(payload)
    defs = sound_definitions(nodes)
    owners = definition_dialogues(nodes, defs, schema)
    base = {'archive': database.path.name, 'member': 'objects.ddb', 'sha256': digest(payload)}
    owners = {key: {**row, **base} for key, row in owners.items()}
    overlays, instances, level = [], [], []
    for name in sorted(mission.entries):
        if name.endswith('.ddb'):
            payload = mission.read_binary(name)
            identity = {'archive': map_name, 'member': name, 'sha256': digest(payload)}
            expected = next((row for row in bindings['definition_overlays'] if row['member'] == name), None)
            if expected is None or identity['sha256'] != expected['sha256']:
                raise ValueError('authored binding definition overlay identity changed')
            nodes = chunks(payload)
            additions = sound_definitions(nodes)
            overlays.append({**identity, 'overridden_ids': sorted(defs.keys() & additions.keys())})
            for key in additions:
                owners.pop(key, None)
            owners.update({key: {**row, **identity} for key, row in definition_dialogues(nodes, additions, schema).items()})
            defs.update(additions)
        elif name.endswith(('.ldd', '.lsd')):
            payload = mission.read_binary(name)
            if digest(payload) != bindings['members'][name]['sha256']:
                raise ValueError('authored binding level identity changed')
            nodes = chunks(payload)
            identity = {'archive': map_name, 'member': name, 'sha256': digest(payload)}
            instances.extend({**row, **identity, 'scope': 'serialized_instance'} for row in instance_dialogues(nodes, schema))
            level.extend({**row, **identity} for row in conversations(nodes, allow_legacy_category=False))
    discovered = set(bindings['discovered_definition_ids'])
    definitions = [{**row, 'scope': 'definition', 'in_partial_binding_closure': key in discovered}
                   for key, row in sorted(owners.items())]
    variants = []
    for global_database in context['globals']:
        global_rows = [{**row, 'archive': global_database['archive'], 'member': global_database['member']}
                       for row in global_database['rows']]
        for strings in context['strings']:
            links, resolutions = link_options(definitions + instances, global_rows + level, strings['rows'],
                                              defs, context['files'], mission)
            definition_links = [r for r in links if r['scope'] == 'definition']
            variants.append({'global_database': {k: v for k, v in global_database.items() if k != 'rows'},
                             'string_database': {k: v for k, v in strings.items() if k not in ('rows', 'issues')},
                             'option_links': links, 'conversation_candidates': resolutions,
                             'summary': {'all_definitions': link_summary(definition_links),
                                         'partial_binding_definitions': link_summary([r for r in definition_links if r['in_partial_binding_closure']]),
                                         'serialized_instances': link_summary([r for r in links if r['scope'] == 'serialized_instance'])}})
    alternatives = []
    for archive in context['archives']:
        if 'objects.ddb' in archive.entries:
            alternatives.append({'archive': archive.path.name, 'member': 'objects.ddb',
                                 'sha256': digest(archive.read_binary('objects.ddb'))})
    return {'schema_version': 1, 'evidence_class': 'read-only original soldier dialogue and voice metadata',
            'map': map_name, 'archive_sha256': bindings['archive_sha256'], 'source_schema': schema,
            'source_provenance': sources, 'source_event_callers': callers,
            'source_event_call_scope': 'staged_combat_cpp_simple_expressions_unknown_dynamic_arguments_retained',
            'definition_database': base, 'other_definition_database_candidates': alternatives,
            'definition_overlays': overlays, 'definition_scope': 'explicit_always_dbs_and_sorted_map_overlays_matches_binding_audit',
            'definition_owners': definitions, 'serialized_instances': instances, 'database_variants': variants,
            'summary': {'soldier_definitions': len(definitions), 'partial_binding_soldier_definitions': sum(r['in_partial_binding_closure'] for r in definitions),
                        'serialized_soldier_instances': len(instances),
                        'serialized_zero_id_soldier_records': sum(r['instance_id'] == 0 for r in instances),
                        'database_variants': [r['summary'] for r in variants]},
            'runtime_or_physical_acceptance': False, 'complete_mission_closure': False,
            'limits': ['Options are metadata candidates; weights and partial dependency closure prove no branch, spawn or playback.',
                       'Serialized instance dialogue is separate from preset defaults; missing tables do not prove runtime inheritance.',
                       'Zero serialized object IDs remain separate records identified by member/offset; assignment and live membership are unverified.',
                       'Global/string variants and conversation-ID collisions remain separate; runtime mount/list precedence is unverified.',
                       'Only the explicit audited definition scope is used, never a merge of always-archive alternatives.',
                       'Negative sound IDs suppress soldier speech but remain duration-query attempts; default missing lookup is not a speech gap.',
                       'Original float32 bit patterns are retained without simulating random-selection or ARM floating-point behavior.',
                       'No retail data rewrite, name/ID alias, subtitle/audio export, C++ build, game launch or device action.']}


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
    for name in args.maps or MAPS:
        if '/' in name or '\\' in name or not name.lower().endswith('.mix'):
            parser.error('map names must be archive filenames below retail Data')
    context, scripts = resource_context(args.data), source_scripts(args.root)
    output.mkdir(parents=True, exist_ok=True)
    for name in args.maps or MAPS:
        result = audit(args.root, args.data, name, context, scripts)
        (output / (Path(name).stem.lower() + '-voice-routes.json')).write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
        print(json.dumps({'map': name, **result['summary']}, sort_keys=True), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
