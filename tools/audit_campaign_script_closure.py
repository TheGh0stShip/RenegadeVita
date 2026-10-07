#!/usr/bin/env python3
"""Campaign-wide script binding closure (static, read-only, deterministic).

For M13 and M01..M11 (optionally M00) this joins every script attachment found
in retail data against the sources that are actually selected for the Vita
target:

* level data (.ldd/.lsd): persisted, spawner and CombatManager start scripts;
* preset definitions (always.dbs objects.ddb plus the mission .ddb overlays);
* cinematic .txt `Attach_Script` commands (mission archives, always.dat and
  Always2.dat) parsed with the original Test_Cinematic loader rules.

Checks: registration present in a TU selected by CMake, no registration name
collisions (the original ScriptRegistrar matches names with stricmp, so
collisions are case-insensitive), parameter-read indices versus supplied value
counts (original Get_Parameter(int) returns "" outside the supplied range),
literal source-to-source attachments, and sender/receiver consistency of the
script custom-event constants.

Nothing is built, launched or executed.  Retail archives and the optional retail
Scripts2.dll are opened read-only; the generated JSON/Markdown contain script
names, counts, member names and offsets only (no parameter values or payloads).
Severity vocabulary: `blocks completion`, `cosmetic`, `retail-identical`.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re

from tools.audit_cinematic_command_coverage import CAMPAIGN, SHARED, classify, parse_payload
from tools.audit_m13_level_owners import chunks, definitions, level_records, reference_fields
from tools.audit_mission_content_bindings import constant_branch_code, masked
from tools.audit_mission_event_routes import numeric_constants
from tools.audit_mission_text_routes import constant_id
from tools.audit_script_parameter_reads import descriptor_names, reads
from tools.check_m13_script_coverage import DECLARE, selected_owners
from tools.renegade_cinematic_dependency_scan import MixArchive

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA = Path('/mnt/c/Users/steve/AppData/Roaming/Vita3K/Vita3K/ux0/data/renegade/retail/Data')
SCOPE = ['M00_Tutorial.mix'] + CAMPAIGN
SEVERITIES = ('blocks completion', 'cosmetic', 'retail-identical')
MISSION_OWNERS = {'Mission00.cpp': 'M00', 'Mission01.cpp': 'M01', 'Mission02.cpp': 'M02',
                  'Mission03.cpp': 'M03', 'Mission04.cpp': 'M04', 'Mission05.cpp': 'M05',
                  'Mission06.cpp': 'M06', 'Mission07.cpp': 'M07', 'mission08.cpp': 'M08',
                  'Mission09.cpp': 'M09', 'Mission10.cpp': 'M10', 'Mission11.cpp': 'M11',
                  'MissionX0.cpp': 'M13'}
# CUSTOM_EVENT_SYSTEM_FIRST (gameobjobserver.h): engine-originated events.
SYSTEM_EVENT_FIRST = 1000000000
STRING = re.compile(r'"(?:\\.|[^"\\])*"')
INCLUDE = re.compile(r'^\s*#\s*include\s+"([^"]+)"', re.MULTILINE)
CUSTOM_DEF = re.compile(r'\bCustom\s*\(\s*GameObject\s*\*\s*\w+\s*,\s*int\s+(\w+)\s*,\s*int\s+(\w+)\s*,[^)]*\)\s*(?:const\s*)?\{')


# --------------------------------------------------------------------------
# Source scanning
# --------------------------------------------------------------------------

def scan_registrations(directory, selected):
    """Every DECLARE_SCRIPT in directory/*.cpp; `selected` is the compiled TU set."""
    rows = []
    for path in sorted(directory.glob('*.cpp')):
        text = path.read_text(encoding='latin1')
        source = constant_branch_code(masked(text))
        code = masked(source, strings=True)
        declarations = list(DECLARE.finditer(code))
        for index, match in enumerate(declarations):
            end = declarations[index + 1].start() if index + 1 < len(declarations) else len(source)
            desc = re.match(r'\s*((?:"(?:\\.|[^"\\])*"\s*)+)\)', source[match.end():])
            descriptor = ''.join(eval_literal(s) for s in STRING.findall(desc[1])) if desc else None
            rows.append({'name': match[1], 'owner': path.name,
                         'line': source.count('\n', 0, match.start()) + 1,
                         'descriptor': descriptor, 'body': source[match.end():end],
                         'start': match.start(), 'compiled': path.name in selected})
    return rows


def eval_literal(token):
    import ast
    return ast.literal_eval(token)


def registry_findings(rows):
    by_name = defaultdict(list)
    for row in rows:
        by_name[row['name'].lower()].append(row)
    findings = []
    for key, group in sorted(by_name.items()):
        if len(group) < 2:
            continue
        compiled = [row for row in group if row['compiled']]
        spellings = sorted({row['name'] for row in group})
        severity = 'blocks completion' if len(compiled) > 1 else 'retail-identical'
        findings.append({'kind': 'registration_name_collision', 'name': key, 'spellings': spellings,
                         'owners': sorted(f"{row['owner']}:{row['line']}" for row in group),
                         'compiled_count': len(compiled), 'severity': severity})
    return findings, by_name


def include_closure(directory, path, seen=None, depth=3):
    """Texts of local quoted includes (case-insensitive lookup), shallow depth."""
    seen = set() if seen is None else seen
    names = {item.name.lower(): item for item in directory.iterdir()} if directory.is_dir() else {}
    texts = []
    source = path.read_text(encoding='latin1')
    if depth:
        for include in INCLUDE.findall(masked(source)):
            target = names.get(include.replace('\\', '/').split('/')[-1].lower())
            if target and target.suffix.lower() == '.h' and target not in seen:
                seen.add(target)
                texts.extend(include_closure(directory, target, seen, depth - 1))
    texts.append(source)
    return texts


CALL = re.compile(r'\bCommands\s*->\s*(\w+)\s*\(')


def find_calls(source, code, wanted):
    """Linear scan of `Commands->X(...)` calls; `code` is masked(source, strings=True)."""
    pairs = {'(': ')', '[': ']', '{': '}'}
    for match in CALL.finditer(code):
        if match[1] not in wanted:
            continue
        stack, begin, spans = [')'], match.end(), []
        for pos in range(match.end(), len(code)):
            char = code[pos]
            if char in pairs:
                stack.append(pairs[char])
            elif char in ')]}':
                if not stack or stack.pop() != char:
                    break
                if not stack:
                    spans.append(source[begin:pos].strip())
                    break
            elif char == ',' and len(stack) == 1:
                spans.append(source[begin:pos].strip())
                begin = pos + 1
        else:
            continue
        yield {'command': match[1], 'offset': match.start(), 'arguments': spans}


def brace_body(code, open_index):
    depth = 0
    for pos in range(open_index, len(code)):
        depth += (code[pos] == '{') - (code[pos] == '}')
        if depth == 0:
            return pos + 1
    return len(code)


def receiver_values(body, constants, type_name):
    """Values compared against the Custom() type argument inside one body."""
    code = masked(body, strings=True)
    exact, lows, highs, computed = set(), [], [], []

    def resolve(expression):
        expression = expression.strip()
        value = constant_id(expression, constants)
        return value

    for match in re.finditer(r'\b' + re.escape(type_name) + r'\s*(==|>=|<=|>|<)\s*([A-Za-z_]\w*(?:\s*[+-]\s*\w+)?|-?\d+)', code):
        value = resolve(match[2])
        if value is None:
            computed.append(match[2].strip())
        elif match[1] == '==':
            exact.add(value)
        elif match[1] in ('>=', '>'):
            lows.append(value + (match[1] == '>'))
        else:
            highs.append(value - (match[1] == '<'))
    for match in re.finditer(r'([A-Za-z_]\w*|-?\d+)\s*==\s*' + re.escape(type_name) + r'\b', code):
        value = resolve(match[1])
        if value is None:
            computed.append(match[1])
        else:
            exact.add(value)
    for match in re.finditer(r'\bcase\s+([^:;]+?)\s*:', code):
        value = resolve(match[1])
        if value is None:
            computed.append(match[1].strip())
        else:
            exact.add(value)
    span = (min(lows) if lows else None, max(highs) if highs else None) if (lows or highs) else None
    return {'exact': sorted(exact), 'range': span, 'computed': sorted(set(computed))}


def scan_events(directory, registrations):
    """Per TU: custom-event senders/receivers and literal Attach_Script calls (static, narrow)."""
    by_file = defaultdict(list)
    for row in registrations:
        by_file[row['owner']].append(row)
    senders, receivers, attachments = [], [], []
    names_used = defaultdict(lambda: defaultdict(set))
    for path in sorted(directory.glob('*.cpp')):
        text = path.read_text(encoding='latin1')
        constants = numeric_constants('\n'.join(include_closure(directory, path)))
        own = constant_branch_code(masked(text))
        code = masked(own, strings=True)
        scripts = sorted(by_file.get(path.name, []), key=lambda row: row['start'])

        def owner_of(offset):
            current = None
            for row in scripts:
                if row['start'] <= offset:
                    current = row['name']
            return current

        for call in find_calls(own, code, ('Send_Custom_Event', 'Attach_Script')):
            args = call['arguments']
            if call['command'] == 'Attach_Script':
                if len(args) >= 2:
                    attachments.append({'owner': path.name, 'script': owner_of(call['offset']),
                                        'target': literal_text(args[1])})
                continue
            if len(args) < 3:
                continue
            expression = args[2]
            value = constant_id(expression, constants)
            if re.fullmatch(r'[A-Za-z_]\w*', expression.strip()):
                names_used[expression.strip()][path.name].add(value)
            param = args[3].strip() if len(args) > 3 else ''
            param_value = (constant_id(param, constants) if re.fullmatch(r'[A-Za-z_]\w*', param) else None)
            senders.append({'owner': path.name, 'script': owner_of(call['offset']),
                            'expression': ' '.join(expression.split()), 'value': value,
                            'param_value': param_value})
        for match in CUSTOM_DEF.finditer(code):
            end = brace_body(code, match.end() - 1)
            info = receiver_values(own[match.end() - 1:end], constants, match[1])
            info['param_exact'] = receiver_values(own[match.end() - 1:end], constants, match[2])['exact']
            for token in re.findall(r'(?:==|\bcase)\s*([A-Za-z_]\w*)', code[match.end() - 1:end]):
                if token in constants:
                    names_used[token][path.name].add(int(constants[token]))
            receivers.append({'owner': path.name, 'script': owner_of(match.start()), **info})
    return senders, receivers, names_used, attachments


def attachment_findings(registry, attachments, compiled):
    """Literal Commands->Attach_Script(obj, "Name", ...) in compiled script units."""
    findings = []
    for row in attachments:
        if row['owner'] not in compiled or row['target'] is None:
            continue
        group = registry.get(row['target'].lower())
        if not group:
            findings.append({'kind': 'literal_attach_unregistered', 'script': row['script'],
                             'owner': row['owner'], 'target': row['target'], 'severity': 'retail-identical'})
        elif not any(item['compiled'] for item in group):
            findings.append({'kind': 'literal_attach_uncompiled', 'script': row['script'],
                             'owner': row['owner'], 'target': row['target'], 'severity': 'blocks completion'})
    return findings


def event_findings(senders, receivers, names_used, compiled, cinematic_types):
    """Value-level sender/receiver closure plus cross-TU constant-name conflicts."""
    findings = []

    def covered(value, only_compiled, param=False):
        for row in receivers:
            if only_compiled and row['owner'] not in compiled:
                continue
            if value in row['exact'] or (param and value in row.get('param_exact', ())):
                return True
            lo, hi = row['range'] or (None, None)
            if row['range'] and (lo is None or value >= lo) and (hi is None or value <= hi):
                return True
        return False

    sent_values = defaultdict(set)
    for row in senders:
        if row['value'] is None:
            continue
        sent_values[row['value']].add(row['owner'])
        if row.get('param_value'):
            sent_values[row['param_value']].add(row['owner'])
        if row['owner'] not in compiled:
            continue
        identities = [row['value']] + ([row['param_value']] if row.get('param_value') else [])
        if any(covered(v, True, True) for v in identities) or row['value'] >= SYSTEM_EVENT_FIRST:
            continue
        if any(covered(v, False, True) for v in identities):
            findings.append({'kind': 'receiver_only_in_uncompiled_unit', 'value': row['value'],
                             'sender': f"{row['owner']}:{row['script']}", 'severity': 'blocks completion'})
        else:
            findings.append({'kind': 'sender_without_receiver', 'value': row['value'],
                             'sender': f"{row['owner']}:{row['script']}", 'severity': 'retail-identical'})
    summary = defaultdict(lambda: {'senders_literal': 0, 'senders_computed': 0, 'receiver_values': 0,
                                   'receiver_values_without_literal_sender': 0, 'range_receivers': 0})
    for row in senders:
        summary[row['owner']]['senders_literal' if row['value'] is not None else 'senders_computed'] += 1
    for row in receivers:
        if row['owner'] not in compiled:
            continue
        entry = summary[row['owner']]
        entry['range_receivers'] += row['range'] is not None
        for value in sorted(set(row['exact']) | set(row.get('param_exact', ()))):
            entry['receiver_values'] += 1
            if value < SYSTEM_EVENT_FIRST and value not in sent_values and value not in cinematic_types:
                entry['receiver_values_without_literal_sender'] += 1
    for value in sorted(cinematic_types):
        if value < SYSTEM_EVENT_FIRST and not covered(value, True):
            findings.append({'kind': 'cinematic_send_custom_without_receiver', 'value': value,
                             'severity': 'retail-identical'})
    # Same constant name, different value in two units where one side sends it: each unit compiles its
    # own definition exactly as retail did, so this is reported as information, never as a port defect.
    sent_names = defaultdict(lambda: defaultdict(set))
    for row in senders:
        if re.fullmatch(r'[A-Za-z_]\w*', row['expression']) and row['value'] is not None:
            sent_names[row['expression']][row['owner']].add(row['value'])
    reused = []
    for name, per_owner in sorted(sent_names.items()):
        for owner, values in sorted(per_owner.items()):
            others = {o: {v for v in vals if v is not None} for o, vals in names_used.get(name, {}).items() if o != owner}
            if any(vals and not (vals & values) for vals in others.values()):
                reused.append(name)
                break
    return findings, {'per_unit': {k: dict(v) for k, v in sorted(summary.items())},
                      'cross_unit_constant_name_reuse': reused}


def literal_text(expression):
    tokens = STRING.findall(expression.strip())
    if not tokens or STRING.sub('', expression).strip():
        return None
    return ''.join(eval_literal(token) for token in tokens)


# --------------------------------------------------------------------------
# Binding classification
# --------------------------------------------------------------------------

def value_count(parameters):
    return None if parameters is None else (parameters.count(',') + 1 if parameters else 0)


_READS = {}


def cached_reads(row, descriptor):
    key = (row['owner'], row['name'])
    if key not in _READS:
        _READS[key] = reads(row['body'], descriptor)
    return _READS[key]


def classify_binding(binding, group, dll_names, placed):
    """Findings for one authored binding. `group` = registrations sharing the name."""
    findings = []
    name = binding['name']
    in_dll = None if dll_names is None else name.lower() in dll_names
    compiled = [row for row in group if row['compiled']]
    if not group or not compiled:
        # Absent from every supplied retail DLL: the retail game could not run it either.
        severity = ('retail-identical' if in_dll is False else
                    'blocks completion' if placed else 'cosmetic')
        findings.append({'kind': 'unregistered_script' if not group else 'registered_in_uncompiled_unit',
                         'severity': severity, 'in_retail_dll': in_dll, 'placed': placed,
                         'owners': sorted({row['owner'] for row in group})})
        return findings
    row = compiled[0]
    supplied = value_count(binding.get('parameters'))
    descriptor = row['descriptor']
    if descriptor is None:
        findings.append({'kind': 'descriptor_not_literal', 'severity': 'cosmetic'})
        return findings
    names = descriptor_names(descriptor) if descriptor else []
    if supplied is not None and supplied > len(names):
        findings.append({'kind': 'excess_supplied_values', 'severity': 'retail-identical',
                         'supplied': supplied, 'descriptor': len(names)})
    if supplied is not None and supplied < len(names):
        findings.append({'kind': 'fewer_supplied_values', 'severity': 'retail-identical',
                         'supplied': supplied, 'descriptor': len(names)})
    for read in cached_reads(row, descriptor):
        index = read['index']
        if read['category'] == 'literal_name_absent':
            findings.append({'kind': 'read_name_absent_from_descriptor', 'severity': 'retail-identical',
                             'read': read['name']})
        elif read['category'] in ('literal_name_matches', 'literal_index') and index is not None:
            if index >= len(names) and read['category'] == 'literal_index':
                findings.append({'kind': 'read_index_beyond_descriptor', 'severity': 'retail-identical',
                                 'index': index, 'descriptor': len(names)})
            elif supplied is not None and index >= supplied:
                findings.append({'kind': 'read_beyond_supplied_values', 'severity': 'retail-identical',
                                 'index': index, 'supplied': supplied})
    unique = {}
    for item in findings:
        unique[json.dumps(item, sort_keys=True)] = item
    return list(unique.values())


# --------------------------------------------------------------------------
# Retail data
# --------------------------------------------------------------------------

def preset_closure(defs, level):
    """Typed-reference closure from level-placed definitions (no script inference)."""
    pending = {row['definition_id'] for row in level['objects'] + level['spawners'] + level['physics']
               if row.get('definition_id')}
    reached = set()
    while pending:
        key = pending.pop()
        if key in reached or key not in defs:
            continue
        reached.add(key)
        pending.update(set(defs[key]['definition_references']) - reached)
    return reached


def mission_rows(data, name, schema, always_defs, sends):
    mission = MixArchive(data / name)
    defs = dict(always_defs)
    members = sorted(mission.entries)
    overlay_ids = set()
    for member in members:
        if member.endswith('.ddb'):
            overlay = definitions(chunks(mission.read_binary(member)), schema)
            overlay_ids.update(overlay)
            defs.update(overlay)
    level = {'script_records': [], 'objects': [], 'spawners': [], 'physics': []}
    for member in members:
        if member.endswith(('.ldd', '.lsd')):
            record = level_records(chunks(mission.read_binary(member)))
            for row in record['script_records']:
                level['script_records'].append({**row, 'member': member})
            for key in ('objects', 'spawners', 'physics'):
                level[key].extend(record[key])
    placed = preset_closure(defs, level)
    rows = []
    for binding in level['script_records']:
        rows.append({'source': 'level:' + binding['binding_kind'], 'name': binding['name'],
                     'location': f"{binding['member']}@{binding['offset']}",
                     'parameters': binding.get('parameters'), 'placed': True})
    for key in sorted(defs):
        if key not in placed and key not in overlay_ids:
            continue
        for binding in defs[key]['script_bindings']:
            rows.append({'source': 'preset', 'name': binding['name'],
                         'location': f"definition {key} ({defs[key]['name']})",
                         'parameters': binding.get('parameters'), 'placed': key in placed})
    cinematic = []
    for member in members:
        if not member.endswith('.txt'):
            continue
        records, _ = parse_payload(mission.read_binary(member))
        cinematic.extend(cinematic_attachments(member, records, name, sends))
    return {'rows': rows, 'cinematic': cinematic, 'definitions': len(defs), 'placed_definitions': len(placed),
            'placed_ids': placed, 'overlay_definitions': len(overlay_ids),
            'sha256': hashlib.sha256((data / name).read_bytes()).hexdigest()}


def cinematic_attachments(member, records, archive, sends):
    """Attach_Script rows; Send_Custom type arguments are collected into `sends`."""
    result = []
    for record in records:
        info = classify(record)
        if info['command'] == 'Send_Custom' and len(info['args']) > 1:
            try:
                sends.add(int(info['args'][1]))
            except ValueError:
                pass
        if info['command'] != 'Attach_Script':
            continue
        args = info['args']
        result.append({'source': 'cinematic', 'name': args[1] if len(args) > 1 else '',
                       'location': f"{archive}:{member}:{record['line']}",
                       'parameters': args[2] if len(args) > 2 else None, 'placed': True, 'archive': archive})
    return result


def shared_cinematics(data, sends):
    result = []
    for name in SHARED:
        if not (data / name).exists():
            continue
        archive = MixArchive(data / name)
        for member in sorted(archive.entries):
            if member.endswith('.txt'):
                records, _ = parse_payload(archive.read_binary(member))
                result.extend(cinematic_attachments(member, records, name, sends))
    return result


def dll_script_names(paths):
    """Lower-case printable runs in retail DLLs; membership proves presence only."""
    paths = [path for path in paths or [] if path.exists()]
    if not paths:
        return None
    return {run.decode('latin1').lower() for path in paths
            for run in re.findall(rb'[A-Za-z0-9_]{4,}', path.read_bytes())}


# --------------------------------------------------------------------------
# Driver
# --------------------------------------------------------------------------

def build_report(root, data, maps, dll_paths):
    scripts_dir = root / 'staging/scripts'
    selected = selected_owners(root)['vita']
    registrations = scan_registrations(scripts_dir, selected)
    collisions, registry = registry_findings(registrations)
    dll_names = dll_script_names(dll_paths)
    compiled = set(selected)
    report = {'schema_version': 1, 'evidence_class': 'static_authored_metadata_and_cmake_selection',
              'runtime_or_physical_acceptance': False, 'maps': {}, 'findings': [],
              'registrations': {'total': len(registrations),
                                'compiled': sum(row['compiled'] for row in registrations),
                                'uncompiled_units': sorted({row['owner'] for row in registrations if not row['compiled']}),
                                'compiled_units': len(compiled)}}
    report['findings'].extend({**item, 'scope': 'registry'} for item in collisions)
    senders, receivers, names_used, attachments = scan_events(scripts_dir, registrations)
    report['findings'].extend({**item, 'scope': 'source'} for item in attachment_findings(
        registry, attachments, compiled))
    schema = reference_fields(root)
    always_defs = definitions(chunks(MixArchive(data / 'always.dbs').read_binary('objects.ddb')), schema)
    cinematic_values = set()
    shared = shared_cinematics(data, cinematic_values)
    all_rows, placed_anywhere = {}, set()
    for name in maps:
        result = mission_rows(data, name, schema, always_defs, cinematic_values)
        all_rows[name] = result['rows'] + result['cinematic']
        placed_anywhere.update(result['placed_ids'])
        report['maps'][name] = {'archive_sha256': result['sha256'], 'definitions': result['definitions'],
                                'overlay_definitions': result['overlay_definitions'],
                                'placed_definitions': len(result['placed_ids'])}
    all_rows['objects.ddb (all presets)'] = [
        {'source': 'preset', 'name': binding['name'], 'location': f"definition {key} ({always_defs[key]['name']})",
         'parameters': binding.get('parameters'), 'placed': key in placed_anywhere}
        for key in sorted(always_defs) for binding in always_defs[key]['script_bindings']]
    report['maps']['objects.ddb (all presets)'] = {
        'archive_sha256': hashlib.sha256((data / 'always.dbs').read_bytes()).hexdigest(),
        'definitions': len(always_defs), 'placed_definitions': len(placed_anywhere & set(always_defs))}
    all_rows['always.dat+Always2.dat'] = shared
    report['maps']['always.dat+Always2.dat'] = {'archive_sha256': {
        n: hashlib.sha256((data / n).read_bytes()).hexdigest() for n in SHARED if (data / n).exists()}}
    found, report['custom_event_summary'] = event_findings(
        senders, receivers, names_used, compiled, cinematic_values)
    report['findings'].extend({**item, 'scope': 'custom_events'} for item in found)
    up_dir = root / 'upstream/CnC_Renegade/Code/Scripts'
    if up_dir.is_dir():
        up = scan_events(up_dir, scan_registrations(up_dir, set()))
        surface = lambda rows: {(r['owner'], r['script'] or '', r.get('value'), tuple(r.get('exact', ())),
                                 r.get('range')) for r in rows}
        for label, mine, theirs in (('senders', senders, up[0]), ('receivers', receivers, up[1])):
            added, removed = surface(mine) - surface(theirs), surface(theirs) - surface(mine)
            if removed:
                report['findings'].append({'scope': 'custom_events', 'kind': 'patched_event_surface_removed',
                                           'which': label, 'count': len(removed), 'severity': 'blocks completion'})
            if added:
                report['findings'].append({
                    'scope': 'custom_events', 'kind': 'patched_event_surface_added', 'which': label,
                    'count': len(added), 'severity': 'cosmetic',
                    'items': sorted(f'{o}:{sc}:{v if v is not None else sorted(e)}' for o, sc, v, e, _ in added)})
        report['custom_event_summary']['staging_matches_upstream_event_surface'] = not any(
            f['kind'] == 'patched_event_surface_removed' for f in report['findings'])
    for name, rows in all_rows.items():
        counts, per_source = Counter(), Counter()
        unresolved = []
        distinct = set()
        for row in rows:
            per_source[row['source']] += 1
            distinct.add(row['name'].lower())
            group = registry.get(row['name'].lower(), [])
            for finding in classify_binding(row, group, dll_names, row['placed']):
                counts[(finding['kind'], finding['severity'])] += 1
                if finding['kind'] in ('unregistered_script', 'registered_in_uncompiled_unit',
                                       'descriptor_not_literal'):
                    unresolved.append({'name': row['name'], 'source': row['source'],
                                       'location': row['location'], **finding})
        report['maps'][name].update({
            'bindings': len(rows), 'distinct_scripts': len(distinct),
            'by_source': dict(sorted(per_source.items())),
            'finding_counts': {f'{kind} [{severity}]': n for (kind, severity), n in sorted(counts.items())},
            'unresolved': sorted(unresolved, key=lambda r: (r['name'], r['location']))})
    report['findings'].sort(key=lambda r: json.dumps(r, sort_keys=True))
    totals = Counter()
    for row in report['maps'].values():
        for key, count in row.get('finding_counts', {}).items():
            totals[key] += count
    report['binding_finding_totals'] = dict(sorted(totals.items()))
    report['severity_totals'] = dict(sorted(Counter(
        item['severity'] for item in report['findings']).items()))
    for name, row in report['maps'].items():
        for item in row.get('unresolved', []):
            report['severity_totals'][item['severity']] = report['severity_totals'].get(item['severity'], 0) + 1
    report['dll'] = None if dll_names is None else {
        'files': {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in dll_paths if path.exists()},
        'tokens': len(dll_names),
        # Calibration: how many compiled source registrations the DLL token match recognises.
        'compiled_source_names_found': sum(row['name'].lower() in dll_names for row in registrations if row['compiled']),
        'compiled_source_names': sum(row['compiled'] for row in registrations)}
    report['uncompiled_registrations'] = [
        {'name': row['name'], 'owner': row['owner'],
         'in_retail_dll': None if dll_names is None else row['name'].lower() in dll_names}
        for row in registrations if not row['compiled']]
    report['limits'] = [
        'Static joins only: authored bindings do not prove instantiation, zone entry or callback execution.',
        'Parameter reads resolve literal names/indices only; computed reads are not judged.',
        'Custom-event pairing is value-level across scripts (senders target dynamic objects); receiver ranges are approximate.',
        'Preset placement uses typed definition references from level-placed objects; script-created presets are not inferred.',
        'Retail Scripts2.dll membership is a printable-token match, not a registry dump.',
        'Host/static evidence is not Vita3K or physical acceptance.']
    report['tool_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    return report


def headline(report):
    maps = [row for row in report['maps'].values() if 'bindings' in row]
    unresolved = [item for row in maps for item in row['unresolved']]
    by_severity = Counter(item['severity'] for item in unresolved)
    blocking = by_severity.get('blocks completion', 0) + sum(
        item['severity'] == 'blocks completion' for item in report['findings'])
    return (f"{sum(row['bindings'] for row in maps)} authored bindings across {len(maps)} scopes; "
            f"{len(unresolved)} are unresolved ("
            + ', '.join(f'{n} {k}' for k, n in sorted(by_severity.items())) + '). '
            f"Items that block completion: **{blocking}**. "
            'Unresolved names that are absent from the supplied retail Scripts DLLs cannot be created by the retail '
            'game either: ScriptManager::Create_Script returns NULL and the attachment is skipped identically.')


def render_markdown(report):
    lines = ['# Campaign script binding closure', '',
             'Generated by `python3 -m tools.audit_campaign_script_closure` (static, read-only; no build, launch or retail modification).',
             'Scope: M00, M01..M11, M13 level data, objects.ddb presets with mission overlays, and cinematic `Attach_Script` text commands.', '',
             '## Headline', '',
             headline(report), '',
             '## Registry and CMake selection', '',
             f"- Registrations in `staging/scripts`: **{report['registrations']['total']}**; in Vita-selected units: **{report['registrations']['compiled']}**.",
             f"- Vita-selected script units: {report['registrations']['compiled_units']}; units with registrations that are not selected: "
             + (', '.join(f'`{u}`' for u in report['registrations']['uncompiled_units']) or 'none') + '.', '',
             '## Per mission', '',
             '| Map | Bindings | Distinct scripts | Sources | Unresolved | Findings by kind [severity] |', '| --- | --- | --- | --- | --- | --- |']
    for name, row in report['maps'].items():
        if 'bindings' not in row:
            continue
        kinds = '; '.join(f'{k} x{v}' for k, v in row['finding_counts'].items()) or 'none'
        sources = ', '.join(f'{k} {v}' for k, v in row['by_source'].items())
        lines.append(f"| {name} | {row['bindings']} | {row['distinct_scripts']} | {sources} | {len(row['unresolved'])} | {kinds} |")
    lines += ['', '## Unresolved bindings', '']
    unresolved = [(name, item) for name, row in report['maps'].items() for item in row.get('unresolved', [])]
    if not unresolved:
        lines.append('None.')
    else:
        lines += ['| Map | Script | Source | Location | Kind | Severity | In retail Scripts DLLs |', '| --- | --- | --- | --- | --- | --- | --- |']
        for name, item in unresolved:
            lines.append(f"| {name} | `{item['name']}` | {item['source']} | {item['location']} | {item['kind']} | {item['severity']} | {item.get('in_retail_dll')} |")
    lines += ['', '## Registry, source-attachment and custom-event findings', '']
    if not report['findings']:
        lines.append('None.')
    else:
        lines += ['| Scope | Kind | Severity | Detail |', '| --- | --- | --- | --- |']
        for item in report['findings']:
            detail = {k: v for k, v in item.items() if k not in ('scope', 'kind', 'severity')}
            lines.append(f"| {item['scope']} | {item['kind']} | {item['severity']} | `{json.dumps(detail, sort_keys=True)}` |")
    summary = report['custom_event_summary']
    lines += ['', '## Custom-event closure per script unit', '',
              'No (unit, script, event) sender/receiver triple removed by the staging patches relative to upstream: '
              f"**{summary.get('staging_matches_upstream_event_surface')}** (multiplicity may differ: the pointer-exchange patches duplicate sends). "
              'Literal senders are resolved constants; computed senders (parameter/zone driven) are not judged.', '',
              '| Unit | Literal senders | Computed senders | Receiver values | Without literal sender | Range receivers |',
              '| --- | --- | --- | --- | --- | --- |']
    for unit, row in summary['per_unit'].items():
        lines.append(f"| {unit} | {row['senders_literal']} | {row['senders_computed']} | {row['receiver_values']} | "
                     f"{row['receiver_values_without_literal_sender']} | {row['range_receivers']} |")
    lines += ['', 'Constant names reused with different values in different units (each unit compiles its own definition, as retail): '
              + (', '.join(f'`{n}`' for n in summary['cross_unit_constant_name_reuse']) or 'none') + '.', '',
              '## Registrations in units that are not selected for the Vita target', '',
              '| Script | Unit | In retail DLL |', '| --- | --- | --- |']
    for row in report['uncompiled_registrations']:
        lines.append(f"| `{row['name']}` | {row['owner']} | {row['in_retail_dll']} |")
    dll = report['dll']
    if dll:
        lines += ['', f"Retail DLL token calibration: {dll['compiled_source_names_found']} of {dll['compiled_source_names']} "
                  f"Vita-compiled source registrations are recognised in {', '.join(sorted(dll['files']))}."]
    lines += ['', '## Severity totals', '', '```json', json.dumps(report['severity_totals'], indent=2), '```',
              '', 'Per-binding parameter findings (all `retail-identical`: original `Get_Parameter` returns empty text outside the supplied range):', '',
              '```json', json.dumps(report['binding_finding_totals'], indent=2), '```', '',
              '## Limits', ''] + [f'- {text}' for text in report['limits']]
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--data', type=Path, default=DEFAULT_DATA)
    parser.add_argument('--retail-dll', type=Path, action='append', dest='dlls')
    parser.add_argument('--map', action='append', dest='maps')
    parser.add_argument('--json', type=Path)
    parser.add_argument('--render-json', type=Path, help='render --markdown from a saved --json without rescanning')
    parser.add_argument('--markdown', type=Path)
    args = parser.parse_args()
    if args.render_json:
        args.markdown.write_text(render_markdown(json.loads(args.render_json.read_text())))
        return
    report = build_report(args.root, args.data, args.maps or SCOPE, args.dlls)
    if args.json:
        args.json.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    if args.markdown:
        args.markdown.write_text(render_markdown(report))
    print(json.dumps({'maps': len(report['maps']), 'findings': len(report['findings']),
                      'severity_totals': report['severity_totals']}, sort_keys=True))


if __name__ == '__main__':
    main()
