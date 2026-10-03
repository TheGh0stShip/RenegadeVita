"""Read-only conversation -> translation -> sound -> retail-file discovery.

Detailed metadata stays under build/. No dialogue text, audio payloads, game
execution, save migration or device action. Archive alternatives are separate
evidence, not an inferred runtime mount order.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

from tools.audit_deep_saved_content import conversations, signed32
from tools.audit_m13_level_owners import chunks, definitions, flatten, microchunks, string, u32
from tools.audit_mission_content_bindings import MAPS, ROOT, TOKEN, audit_map, constant_branch_code, masked, source_scripts
from tools.renegade_cinematic_dependency_scan import MixArchive

CONVERSATION_CALL = re.compile(r'\bCommands\s*->\s*Create_Conversation\s*\(')
LITERAL_NAME = re.compile(r'\s*"((?:\\.|[^"\\])*)"\s*(?=[,)])')


def startup_source_findings(root=ROOT):
    """Check bootstrap source hooks, not compilation or executed control flow."""
    paths = {'native': 'port/platform/vita/a31_vita_runtime.cpp',
             'host': 'tools/host_a30_definitions/a31_interactive_main.cpp',
             'helper': 'port/platform/a31_gameplay_boundary.cpp'}
    finding = []
    for route, path in paths.items():
        source = constant_branch_code(masked((root / path).read_text()))
        code = masked(source, strings=True)
        if route == 'helper':
            # All checks refer to the helper's body, excluding unrelated code.
            start = re.search(r'\bbool\s+A31_Interactive_Load_Global_Conversations\s*\([^)]*\)\s*\{', code)
            if not start:
                finding.append({'kind': 'global_conversation_helper_missing'})
                continue
            depth, end = 1, start.end()
            while depth and end < len(code):
                depth += (code[end] == '{') - (code[end] == '}')
                end += 1
            body, raw = code[start.end():end], source[start.end():end]
            required = ('factory.Get_File(', 'SaveLoadSystemClass::Load(cload)',
                        'factory.Return_File(file)', 'file->Close()',
                        'ConversationMgrClass::CATEGORY_GLOBAL', 'if (!loaded)')
            if depth or any(token not in body for token in required) or '"CONV10.CDB"' not in raw:
                finding.append({'kind': 'global_conversation_helper_contract_missing'})
        else:
            call = code.find('A31_Interactive_Load_Global_Conversations(')
            combat = code.find('CombatManager::Init(')
            if call < 0 or combat < 0 or call >= combat:
                finding.append({'kind': 'global_conversation_bootstrap_hook_missing_or_late', 'route': route})
            if 'global_conversations_initialized && !combat_initialized' not in code or 'ConversationMgrClass::Shutdown()' not in code:
                finding.append({'kind': 'global_conversation_early_failure_cleanup_missing', 'route': route})
    return finding


def digest(data):
    return hashlib.sha256(data).hexdigest()


def file_digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def scalar_fields(data):
    rows = microchunks(data)
    if len({k for k, _ in rows}) != len(rows):
        raise ValueError('duplicate scalar field')
    return dict(rows)


def utf16_metadata(data):
    if len(data) % 2 or not data.endswith(b'\0\0'):
        raise ValueError('invalid original UTF-16LE string width/terminator')
    value = data.decode('utf-16le')
    if '\0' in value[:-1]:
        raise ValueError('embedded UTF-16LE string terminator')
    return {'bytes': len(data), 'code_units': len(data) // 2 - 1, 'sha256': digest(data)}


def translations(nodes):
    result, issues = {}, []
    for manager in nodes:
        if manager.kind != 0x90000:
            continue
        for section in manager.children:
            if section.kind != 0x07141201:
                continue
            for factory in section.children:
                if factory.kind != 0x90001:
                    issues.append({'kind': 'unsupported_translation_factory', 'id': factory.kind})
                    continue
                if [c.kind for c in factory.children] != [0x100100, 0x100101]:
                    raise ValueError('invalid original translation factory wrapper')
                token = u32(factory.children[0].data)
                body = factory.children[1].children
                variables = [n for n in body if n.kind == 0x06141108]
                if len(variables) != 1:
                    raise ValueError('missing/ambiguous translation variables')
                fields = scalar_fields(variables[0].data)
                key = u32(fields[1])
                if key in result:
                    raise ValueError('duplicate translation ID within candidate')
                wide = [utf16_metadata(n.data) for n in body if n.kind == 0x0614110b]
                if 3 in fields:  # Legacy inline translation, original VARID_STRING.
                    wide.insert(0, utf16_metadata(fields[3]))
                result[key] = {'id': key, 'description': string(fields[2], 'latin1'),
                               'sound_id': u32(fields[5]) if 5 in fields else None,
                               'old_pointer_token': token, 'translations': wide,
                               'animation': string(fields[6], 'latin1') if 6 in fields else ''}
    if not result:
        raise ValueError('no translation objects located')
    return result, issues


def sound_definitions(nodes):
    result = definitions(nodes)
    by_offset = {row['offset']: key for key, row in result.items()}
    for manager in nodes:
        if manager.kind != 0x101:
            continue
        for group in manager.children:
            if group.kind != 0x101:
                continue
            for factory in group.children:
                if factory.kind not in (0x30000, 0x102):
                    continue
                key = by_offset[factory.offset]
                bodies = [n for n in factory.children if n.kind == 0x100101]
                if len(bodies) != 1:
                    raise ValueError('ambiguous sound/twiddler factory body')
                variables = [n for n in bodies[0].children if n.kind == 0x100]
                if len(variables) != 1:
                    raise ValueError('ambiguous sound/twiddler variables')
                if factory.kind == 0x102:
                    # Preserve ordinals and duplicates; these affect random weights.
                    result[key]['alternatives'] = [u32(v) for k, v in microchunks(variables[0].data) if k == 1]
                else:
                    fields = scalar_fields(variables[0].data)
                    result[key]['filename'] = string(fields[11], 'latin1') if 11 in fields else None
    return result


class RetailFiles:
    def __init__(self, root, archives):
        self.root = root
        self.archives = archives
        self.loose = {}
        for path in sorted(root.iterdir()):
            if path.is_file() and path.resolve().is_relative_to(root.resolve()):
                self.loose.setdefault(path.name.lower(), []).append(path)
        self.cache = {}

    def candidates(self, filename, mission):
        # Original WWAudio uses Strip_Path_From_Filename, not authoring paths.
        basename = filename.replace('\\', '/').rsplit('/', 1)[-1].lower()
        result = []
        for archive in [mission, *self.archives]:
            if basename in archive.entries:
                key = (str(archive.path), basename)
                if key not in self.cache:
                    data = archive.read_binary(basename)
                    self.cache[key] = {'archive': archive.path.name, 'member': basename,
                                       'bytes': len(data), 'sha256': digest(data)}
                result.append(self.cache[key])
        for path in self.loose.get(basename, []):
            key = ('loose', str(path))
            if key not in self.cache:
                self.cache[key] = {'archive': None, 'member': path.name,
                                   'bytes': path.stat().st_size, 'sha256': file_digest(path)}
            result.append(self.cache[key])
        return result


def sound_chain(sound_id, defs, files, mission):
    leaves, findings = [], []
    pending = [(sound_id, [])]
    while pending:
        key, path = pending.pop()
        if key in [edge['id'] for edge in path]:
            findings.append({'kind': 'sound_twiddler_cycle', 'id': key, 'path': path})
            continue
        row = defs.get(key)
        if row is None:
            findings.append({'kind': 'sound_definition_id_not_located', 'id': key, 'path': path})
        elif row['factory'] == '0x00000102':
            alternatives = row['alternatives']
            if not alternatives:
                findings.append({'kind': 'empty_sound_twiddler', 'id': key, 'path': path})
            for ordinal, alternative in reversed(list(enumerate(alternatives))):
                pending.append((alternative, path + [{'id': key, 'alternative_ordinal': ordinal}]))
        elif row['factory'] != '0x00030000':
            findings.append({'kind': 'translation_target_is_not_sound_definition', 'id': key,
                             'factory': row['factory'], 'path': path})
        elif not row.get('filename'):
            findings.append({'kind': 'sound_filename_empty_or_absent', 'id': key, 'path': path})
        else:
            candidates = files.candidates(row['filename'], mission)
            leaves.append({'id': key, 'name': row['name'], 'filename': row['filename'],
                           'path': path, 'candidates': candidates})
            if not candidates:
                findings.append({'kind': 'sound_file_not_located', 'id': key,
                                 'filename': row['filename'], 'path': path})
    return leaves, findings


def conversation_leads(scripts, binding_audit, known_names=()):
    discovered = {s['name'].lower() for s in binding_audit['discovered_scripts']}
    own = {'M00_Tutorial.mix': 'Mission00.cpp', 'M13.mix': 'MissionX0.cpp', 'M01.mix': 'Mission01.cpp'}
    literals, computed = [], []
    for key, row in sorted(scripts.items()):
        if key not in discovered and row['owner'] != own.get(binding_audit['map']):
            continue
        code = masked(row['body'], strings=True)
        for match in CONVERSATION_CALL.finditer(code):
            name = LITERAL_NAME.match(row['body'][match.end():])
            lead = {'script': row['name'], 'owner': row['owner'],
                    'script_in_discovered_closure': key in discovered,
                    'line': row['body_start_line'] + row['body'].count('\n', 0, match.start())}
            if name:
                literals.append({**lead, 'name': name[1], 'kind': 'literal_source_call'})
            else:
                computed.append(lead)
        # Array tables and helper arguments supply names beyond direct calls.
        # An exact known name is a source lead, not execution proof.
        known = {name.lower() for name in known_names}
        located = {(lead['script'], lead['line'], lead['name'].lower()) for lead in literals}
        for token in TOKEN.finditer(row['body']):
            if not token[0].startswith('"'):
                continue
            value = ast.literal_eval(token[0])
            line = row['body_start_line'] + row['body'].count('\n', 0, token.start())
            if value.lower() in known and (row['name'], line, value.lower()) not in located:
                literals.append({'script': row['name'], 'owner': row['owner'], 'line': line,
                                 'script_in_discovered_closure': key in discovered,
                                 'name': value, 'kind': 'known_name_string_lead'})
    return literals, computed


def resource_context(data):
    archives = [MixArchive(p) for p in sorted(data.iterdir()) if p.name.lower().startswith('always')
                and p.suffix.lower() in ('.dat', '.dbs', '.mix')]
    string_candidates, global_candidates, defs = [], [], {}
    for archive in archives:
        if 'strings.tdb' in archive.entries:
            payload = archive.read_binary('strings.tdb')
            rows, issues = translations(chunks(payload))
            string_candidates.append({'archive': archive.path.name, 'member': 'strings.tdb',
                                      'sha256': digest(payload), 'rows': rows, 'issues': issues})
        if 'conv10.cdb' in archive.entries:
            payload = archive.read_binary('conv10.cdb')
            rows = conversations(chunks(payload), allow_legacy_category=False)
            global_candidates.append({'archive': archive.path.name, 'member': 'conv10.cdb',
                                      'sha256': digest(payload), 'rows': rows})
        if 'objects.ddb' in archive.entries:
            defs.update(sound_definitions(chunks(archive.read_binary('objects.ddb'))))
    if not string_candidates or not global_candidates or not defs:
        raise ValueError('missing strings, global conversation or definition database')
    return {'archives': archives, 'strings': string_candidates, 'globals': global_candidates,
            'definitions': defs, 'files': RetailFiles(data, archives)}


def audit(root, data, map_name, context=None, scripts=None):
    context = resource_context(data) if context is None else context
    scripts = source_scripts(root) if scripts is None else scripts
    bindings = audit_map(root, data, map_name, scripts)
    mission = MixArchive(data / map_name)
    level, members, defs = [], [], dict(context['definitions'])
    for name in sorted(mission.entries):
        if name.endswith(('.ldd', '.lsd')):
            payload = mission.read_binary(name)
            rows = conversations(chunks(payload), allow_legacy_category=False)
            level.extend({**row, 'archive': map_name, 'member': name} for row in rows)
            members.append({'archive': map_name, 'member': name, 'sha256': digest(payload), 'records': len(rows)})
        elif name.endswith('.ddb'):
            defs.update(sound_definitions(chunks(mission.read_binary(name))))
    global_rows = [{**row, 'archive': candidate['archive'], 'member': candidate['member']}
                   for candidate in context['globals'] for row in candidate['rows']]
    all_rows = global_rows + level
    names = {row['name'].lower() for row in all_rows}
    leads, computed = conversation_leads(scripts, bindings, names)
    for binding in bindings['bindings']:
        for field in binding.get('parameter_fields') or []:
            value = field['value']
            if value.lower() in names:
                leads.append({'kind': 'exact_parameter_token_lead', 'name': value,
                              'script': binding['name'], 'parameter_index': field['index']})
    missing_names = [lead for lead in leads if lead['name'].lower() not in names]
    text_ids = {remark['text_id'] for row in all_rows for remark in row['remarks']}
    level_text_ids = {remark['text_id'] for row in level for remark in row['remarks']}
    variants = []
    for candidate in context['strings']:
        chains, issues = [], list(candidate['issues'])
        for key in sorted(text_ids):
            row = candidate['rows'].get(key)
            if row is None:
                issues.append({'kind': 'conversation_text_id_not_located', 'id': key, 'text_id': key})
                continue
            sound_id = row['sound_id']
            signed_sound = signed32(sound_id.to_bytes(4, 'little')) if sound_id is not None else None
            chain = {'text_id': key, 'description': row['description'], 'translations': row['translations'],
                     'sound_id': sound_id, 'signed_sound_id': signed_sound, 'animation': row['animation']}
            if sound_id is None:
                issues.append({'kind': 'translation_sound_field_absent', 'id': key, 'text_id': key})
                chain['voice_state'] = 'absent_serialized_field_original_default_minus_one'
            elif sound_id == 0:
                chain['voice_state'] = 'explicit_zero_no_voice'
            elif signed_sound <= 0:
                chain['voice_state'] = 'nonpositive_signed_sound_id_no_speech'
            else:
                chain['voice_state'] = 'positive_sound_reference'
                chain['sound_leaves'], findings = sound_chain(sound_id, defs, context['files'], mission)
                issues.extend({**finding, 'text_id': key} for finding in findings)
            chains.append(chain)
        issues = [{**i, 'referenced_by_authored_level': i.get('text_id') in level_text_ids}
                  for i in issues]
        variants.append({'archive': candidate['archive'], 'member': candidate['member'],
                         'sha256': candidate['sha256'], 'database_objects': len(candidate['rows']),
                         'chains': chains, 'findings': issues,
                         'authored_level_finding_counts': dict(sorted(Counter(i['kind'] for i in issues
                                                               if i['referenced_by_authored_level']).items())),
                         'finding_counts': dict(sorted(Counter(i['kind'] for i in issues).items()))})
    invalid_orators = [{'conversation': row['name'], 'archive': row['archive'], 'member': row['member'],
                        'remark': i, 'orator_index': r['orator_index'], 'orator_count': len(row['orators'])}
                       for row in all_rows for i, r in enumerate(row['remarks'])
                       if not 0 <= r['orator_index'] < len(row['orators'])]
    return {'schema_version': 1, 'evidence_class': 'read-only authored conversation and media metadata',
            'map': map_name, 'archive_sha256': bindings['archive_sha256'], 'level_members': members,
            'global_databases': [{k: v for k, v in c.items() if k != 'rows'} | {'records': len(c['rows'])}
                                 for c in context['globals']],
            'level_conversations': level, 'source_name_leads': leads, 'computed_source_calls': computed,
            'unlocated_literal_name_leads': missing_names, 'invalid_orator_indices': invalid_orators,
            'startup_source_findings': startup_source_findings(root),
            'string_database_candidates': variants,
            'summary': {'global_conversations': len(global_rows), 'level_conversations': len(level),
                        'level_remarks': sum(r['remark_count'] for r in level),
                        'unique_text_ids': len(text_ids), 'literal_or_parameter_name_leads': len(leads),
                        'source_lead_kinds': dict(sorted(Counter(lead['kind'] for lead in leads).items())),
                        'unlocated_literal_name_leads': len(missing_names), 'computed_source_calls': len(computed),
                        'invalid_orator_indices': len(invalid_orators),
                        'database_candidates': [{k: c[k] for k in ('archive', 'database_objects', 'finding_counts',
                                                                   'authored_level_finding_counts')}
                                                for c in variants]},
            'runtime_or_physical_acceptance': False, 'complete_mission_closure': False,
            'limits': ['All authored level and global records are conservative roots, including unused/test records.',
                       'Computed conversation names, direct HUD/text calls and active save-state conversations need separate tracing.',
                       'Archive/database alternatives are separate; runtime resolution and mount order are not claimed.',
                       'File existence/hashes do not establish audio decoding, timing, playback, animation, visemes or visible subtitles.',
                       'No subtitle text/audio payload published, retail writes, C++ build, game launch or device action.']}


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
    context = resource_context(args.data)
    scripts = source_scripts(args.root)
    output.mkdir(parents=True, exist_ok=True)
    for name in args.maps or MAPS:
        result = audit(args.root, args.data, name, context, scripts)
        (output / (Path(name).stem.lower() + '-conversations.json')).write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps({'map': name, **result['summary']}, sort_keys=True), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
