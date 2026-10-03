"""Read-only authored bindings and object-ID leads; never a mission pass.

Detailed receipts contain user-owned retail metadata and belong under build/.
Only sanitized findings, source code and synthetic fixtures may be published.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import re

from tools.audit_campaign_source_surface import dsp_sources
from tools.audit_m13_level_owners import MixArchive, chunks, definitions, level_records, reference_fields
from tools.check_m13_script_coverage import ROOT, DECLARE, TOKEN, ATTACH
from tools.deep_content_dependencies import DeepContentDependencies, literal_presets

MAPS = ("M00_Tutorial.mix", "M13.mix", "M01.mix")
FIND_LITERAL = re.compile(r'\bCommands\s*->\s*Find_Object\s*\(\s*(\d+)\s*\)')
STRING = re.compile(r'"(?:\\.|[^"\\])*"')


def masked(source, strings=False):
    def replace(match):
        if strings or match[0].startswith(("//", "/*")):
            return re.sub(r'[^\n]', ' ', match[0])
        return match[0]
    return TOKEN.sub(replace, source)


def constant_branch_code(source):
    """Mask provably disabled #if 0/1 branches; retain unknown alternatives."""
    result, stack, active = [], [], True
    for line in source.splitlines(keepends=True):
        directive = re.match(r'\s*#\s*(if|ifdef|ifndef|elif|else|endif)\b(.*)', line)
        if directive:
            kind, expression = directive.groups()
            if kind in ('if', 'ifdef', 'ifndef'):
                stack.append({'parent': active, 'remaining': True})
            if kind in ('if', 'ifdef', 'ifndef', 'elif'):
                if not stack:
                    raise ValueError('unmatched conditional directive')
                constant = expression.strip().strip('()').strip() if kind in ('if', 'elif') else ''
                active = stack[-1]['parent'] and stack[-1]['remaining'] and constant != '0'
                if constant == '1':
                    stack[-1]['remaining'] = False
            elif kind == 'else':
                if not stack:
                    raise ValueError('unmatched else')
                active = stack[-1]['parent'] and stack[-1]['remaining']
                stack[-1]['remaining'] = False
            else:
                if not stack:
                    raise ValueError('unmatched endif')
                active = stack.pop()['parent']
            result.append(re.sub(r'[^\n]', ' ', line))
        else:
            result.append(line if active else re.sub(r'[^\n]', ' ', line))
    if stack:
        raise ValueError('unclosed conditional directive')
    return ''.join(result)


def source_scripts(root=ROOT):
    directory = root / "upstream/CnC_Renegade/Code/Scripts"
    result = {}
    for filename in dsp_sources(directory / "Scripts.dsp"):
        if filename == "DLLmain.cpp":
            continue
        source = constant_branch_code(masked((directory / filename).read_text(encoding="latin1")))
        code = masked(source, strings=True)
        declarations = list(DECLARE.finditer(code))
        for i, match in enumerate(declarations):
            end = declarations[i + 1].start() if i + 1 < len(declarations) else len(source)
            # Supported descriptors are literal strings, including adjacent literals.
            desc = re.match(r'\s*((?:"(?:\\.|[^"\\])*"\s*)+)\)', source[match.end():])
            descriptor = ''.join(ast.literal_eval(s) for s in STRING.findall(desc[1])) if desc else None
            body = source[match.end():end]
            lookups = [{"id": int(call[1]), "line": source.count('\n', 0, call.start()) + 1}
                       for call in FIND_LITERAL.finditer(code, match.end(), end)]
            key = match[1].lower()
            if key in result:
                raise ValueError(f"duplicate shipped script registration: {match[1]}")
            result[key] = {"name": match[1], "owner": filename, "descriptor": descriptor,
                           "body": body, "lookups": lookups,
                           "attachments": sorted({m.lower() for m in ATTACH.findall(body)})}
    return result


def parameter_fields(descriptor, parameters):
    """Describe serialized values without inventing absent defaults or CSV rules."""
    if descriptor is None or parameters is None:
        return None
    # Get_Parameter_Index copies at most 511 bytes, then splits on commas.
    names = [re.split(r'[=:\n]', part, maxsplit=1)[0].strip()
             for part in descriptor[:511].split(',')] if descriptor else []
    values = parameters.split(',') if parameters else []
    return [{"index": i, "name": names[i] if i < len(names) else None,
             "value": value} for i, value in enumerate(values)]


def lookup_rows(scripts, discovered, objects, spawners, owner_files):
    object_ids = {row["instance_id"] for row in objects if row["instance_id"] != 0}
    spawner_ids = {row["instance_id"] for row in spawners if row["instance_id"] is not None}
    rows = []
    for key, script in sorted(scripts.items()):
        if script["owner"] not in owner_files and key not in discovered:
            continue
        for call in script["lookups"]:
            classification = ("serialized_game_object" if call["id"] in object_ids else
                              "spawner_id_only_not_a_game_object" if call["id"] in spawner_ids else
                              "not_located_in_serialized_ids")
            rows.append({**call, "script": script["name"], "owner": script["owner"],
                         "script_in_discovered_closure": key in discovered,
                         "classification": classification})
    return rows


def structural_findings(members, reached, defs, unknown, missing_definitions):
    result = [issue for member in members.values() for issue in member['script_binding_issues']]
    result.extend({**issue, "definition_id": key} for key in sorted(reached)
                  for issue in defs[key]['script_binding_issues'])
    result.extend({"kind": "unknown_shipped_script", "name": name} for name in sorted(unknown))
    result.extend({"kind": "definition_id_not_located", "id": key} for key in sorted(missing_definitions))
    return result


def audit_map(root, data_root, map_name, scripts=None):
    scripts = source_scripts(root) if scripts is None else scripts
    mission = MixArchive(data_root / map_name)
    database = MixArchive(data_root / "always.dbs")
    payload = database.read_binary("objects.ddb")
    defs = definitions(chunks(payload), reference_fields(root))
    database_hash = hashlib.sha256(payload).hexdigest()
    overlays = []
    for member in sorted(mission.entries):
        if member.endswith('.ddb'):
            data = mission.read_binary(member)
            rows = definitions(chunks(data), reference_fields(root))
            overlays.append({"member": member, "sha256": hashlib.sha256(data).hexdigest(),
                             "definitions": len(rows), "overridden_ids": sorted(defs.keys() & rows.keys())})
            defs.update(rows)
    members = {}
    bindings = []
    objects = []
    spawners = []
    pending_defs = set()
    for member in sorted(mission.entries):
        if member.endswith(('.ldd', '.lsd')):
            data = mission.read_binary(member)
            record = level_records(chunks(data))
            record['sha256'] = hashlib.sha256(data).hexdigest()
            members[member] = record
            bindings.extend({**row, "member": member} for row in record['script_records'])
            objects.extend(record['objects'])
            spawners.extend(record['spawners'])
            pending_defs.update(row['definition_id'] for row in record['objects'] + record['spawners'] + record['physics']
                                if row['definition_id'])
    if not members:
        raise ValueError("no level members")
    names = {}
    for key, row in defs.items():
        names.setdefault(row['name'].lower(), set()).add(key)
    scanner = DeepContentDependencies(data_root, mission)
    reached_defs, reached_scripts, unknown, missing_defs, missing_presets = set(), set(), set(), set(), set()
    pending_scripts = {row['name'].lower() for row in bindings}
    pending_presets = set()
    scanned_bindings = 0
    while pending_defs or pending_scripts or pending_presets or scanned_bindings < len(bindings):
        for key in sorted(pending_defs):
            if key in reached_defs:
                continue
            if key not in defs:
                missing_defs.add(key)
                continue
            reached_defs.add(key)
            row = defs[key]
            bindings.extend({**binding, "binding_kind": "definition_script", "definition_id": key}
                            for binding in row['script_bindings'])
            # More typed definition edges may be discovered on subsequent passes.
        pending_defs = set().union(*(set(defs[key]['definition_references']) for key in reached_defs)) - reached_defs - missing_defs
        for binding in bindings[scanned_bindings:]:
            pending_scripts.add(binding['name'].lower())
            if binding['parameters'] is not None:
                # Exact parameter tokens may supply dynamically chosen names.
                # Keep these as leads; their use by a specific command is unproved.
                leads = []
                for i, value in enumerate(binding['parameters'].split(',')):
                    if value.lower() in names:
                        pending_presets.add(value)
                        leads.append({'index': i, 'kind': 'exact_preset_token', 'name': value})
                    if value.lower() in scripts:
                        pending_scripts.add(value.lower())
                        leads.append({'index': i, 'kind': 'exact_script_token', 'name': value})
                binding['parameter_reference_leads'] = leads
                created, attached = scanner.from_parameters(binding['parameters'], binding['name'])
                pending_presets.update(created)
                pending_scripts.update(name.lower() for name in attached)
        scanned_bindings = len(bindings)
        current_scripts, pending_scripts = pending_scripts, set()
        for key in sorted(current_scripts - reached_scripts - unknown):
            if key not in scripts:
                unknown.add(key)
                continue
            reached_scripts.add(key)
            row = scripts[key]
            pending_scripts.update(row['attachments'])
            created, attached = scanner.from_source(row['body'], row['name'])
            pending_presets.update(created | literal_presets(row['body']))
            pending_scripts.update(name.lower() for name in attached)
        pending_scripts -= reached_scripts | unknown
        for name in pending_presets:
            candidates = names.get(name.lower(), set())
            if not candidates:
                missing_presets.add(name)
            pending_defs.update(candidates - reached_defs)
        pending_presets = set()
    for binding in bindings:
        row = scripts.get(binding['name'].lower())
        binding['source_owner'] = row['owner'] if row else None
        binding['parameter_fields'] = parameter_fields(row['descriptor'] if row else None, binding['parameters'])
    own_file = {'M00_Tutorial.mix': 'Mission00.cpp', 'M13.mix': 'MissionX0.cpp', 'M01.mix': 'Mission01.cpp'}.get(map_name)
    lookups = lookup_rows(scripts, reached_scripts, objects, spawners, {own_file} if own_file else set())
    findings = structural_findings(members, reached_defs, defs, unknown, missing_defs)
    media = scanner.receipt()
    return {"schema_version": 1, "evidence_class": "read-only authored metadata and literal source dependency leads",
            "map": map_name, "archive_sha256": hashlib.sha256(mission.path.read_bytes()).hexdigest(),
            "objects_ddb_sha256": database_hash, "definition_overlays": overlays,
            "members": members, "bindings": bindings, "discovered_definition_count": len(reached_defs),
            "discovered_scripts": [{"name": scripts[k]['name'], "owner": scripts[k]['owner']} for k in sorted(reached_scripts)],
            "structural_findings": findings, "structural_metadata_gate_passed": not findings,
            "missing_literal_presets": sorted(missing_presets), "media": media, "literal_object_lookups": lookups,
            "summary": {"serialized_game_objects": len(objects), "serialized_spawners": len(spawners),
                        "level_bindings": sum(len(row['script_records']) for row in members.values()),
                        "all_discovered_bindings": len(bindings), "discovered_scripts": len(reached_scripts),
                        "structural_findings": len(findings), "text_candidates": len(media['text_members']),
                        "binding_decode_findings": sum(f['kind'] not in ('definition_id_not_located', 'unknown_shipped_script') for f in findings),
                        "unknown_shipped_scripts": sorted(unknown), "not_located_definition_ids": sorted(missing_defs),
                        "missing_texts": media['missing_text_names'], "missing_literal_presets": sorted(missing_presets),
                        "not_located_ids_in_discovered_scripts": sorted({r['id'] for r in lookups if r['script_in_discovered_closure']
                            and r['classification'] != 'serialized_game_object'}),
                        "not_located_ids_outside_discovered_scripts": sorted({r['id'] for r in lookups if not r['script_in_discovered_closure']
                            and r['classification'] != 'serialized_game_object'})},
            "runtime_or_physical_acceptance": False,
            "limits": ["Literal/typed dependency closure is incomplete for computed names, dynamic IDs and all branch/route lifetimes.",
                       "Not located IDs remain review leads even outside this discovered binding closure; scripts are not proved unreachable.",
                       "Serialized ID presence does not establish live ScriptableGameObj membership or successful lookup at a particular time.",
                       "Text collision alternatives are retained; runtime mount order and executed variants are not inferred.",
                       "Parameter fields describe supplied values only; no absent default values or modified misspelled names are invented.",
                       "No engine build/launch, asset migration, retail modification or runtime registration verification."]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--map', action='append', dest='maps')
    parser.add_argument('--output-directory', type=Path, required=True)
    args = parser.parse_args()
    for name in args.maps or MAPS:
        if '/' in name or '\\' in name or not name.lower().endswith('.mix'):
            parser.error('map names must be archive filenames below the retail data root')
    # Prevent accidental publication of detailed proprietary level metadata.
    output = args.output_directory.resolve()
    if not output.is_relative_to((args.root / 'build').resolve()):
        parser.error('detailed receipts must remain under the private build directory')
    output.mkdir(parents=True, exist_ok=True)
    scripts = source_scripts(args.root)
    for name in args.maps or MAPS:
        result = audit_map(args.root, args.data, name, scripts)
        destination = output / (Path(name).stem.lower() + '-bindings.json')
        destination.write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps({"map": name, "structural_metadata_gate_passed": result['structural_metadata_gate_passed'],
                          **result['summary']}, sort_keys=True), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
