"""Read-only campaign text/conversation closure over existing conversation receipts.

Consumes the per-map JSON receipts written by tools/audit_mission_conversations.py
(--output-directory below private build/) and the retail Data directory, then
answers, per mission: which script-referenced conversation names resolve, whether
every remark text ID resolves in each strings.tdb candidate, which remarks carry
no voice or a voice definition that is absent, and which script string-ID
arguments are zero or defaulted (the TRANSLATE(0) == NULL hazard). It also scans
mission scripts for Add_Objective calls that omit the long-description ID.

Only IDs, names and counts are emitted; no retail text or audio. It proves no
runtime behavior.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re

from tools.audit_mission_content_bindings import ROOT
from tools.audit_mission_conversations import resource_context

MAPS = ['M13'] + ['M%02d' % n for n in range(1, 12)]
# Parameter index of each script string-ID argument.
STRING_ARGUMENTS = {'Add_Objective': (3, 5), 'Set_Objective_HUD_Info': (3,),
                    'Set_Objective_HUD_Info_Position': (3,), 'Set_HUD_Help_Text': (0,),
                    'Display_Text': (0,)}
CALL = re.compile(r'(?<![\w])(Add_Objective|Set_Objective_HUD_Info_Position|Set_Objective_HUD_Info|'
                  r'Set_HUD_Help_Text|Display_Text)\s*\(')
ADD_OBJECTIVE_ARITY = 6  # id, type, status, short ID, sound filename, long ID (default 0)


def blank_comments(source):
    source = re.sub(r'/\*.*?\*/', lambda m: re.sub(r'[^\n]', ' ', m[0]), source, flags=re.S)
    return re.sub(r'//[^\n]*', lambda m: ' ' * len(m[0]), source)


def split_arguments(source, start):
    """Top-level comma split of a call whose '(' precedes `start`; strings stay intact."""
    depth, args, current, in_string, i = 1, [], [], False, start
    while i < len(source):
        char = source[i]
        if in_string:
            current.append(char)
            if char == '\\' and i + 1 < len(source):
                current.append(source[i + 1])
                i += 1
            elif char == '"':
                in_string = False
        elif char == '"':
            in_string = True
            current.append(char)
        elif char in '([{':
            depth += 1
            current.append(char)
        elif char in ')]}':
            depth -= 1
            if depth == 0:
                args.append(''.join(current).strip())
                return args
            current.append(char)
        elif char == ',' and depth == 1:
            args.append(''.join(current).strip())
            current = []
        else:
            current.append(char)
        i += 1
    raise ValueError('unterminated call')


def scan_script_arguments(source, filename):
    """Zero/NULL string-ID arguments and Add_Objective calls that default the long ID."""
    code = blank_comments(source)
    zero, defaulted, total = [], [], 0
    for match in CALL.finditer(code):
        total += 1
        command = match[1]
        args = split_arguments(code, match.end())
        line = code.count('\n', 0, match.start()) + 1
        if command == 'Add_Objective' and len(args) < ADD_OBJECTIVE_ARITY:
            defaulted.append({'file': filename, 'line': line, 'arguments': len(args),
                              'short_id': args[3] if len(args) > 3 else None})
        for index in STRING_ARGUMENTS[command]:
            if index < len(args) and args[index] in ('0', 'NULL', '0L', '(0)'):
                zero.append({'file': filename, 'line': line, 'command': command, 'index': index})
    return {'calls': total, 'zero_arguments': zero, 'defaulted_long_id': defaulted}


def candidate_rows(context):
    return {c['archive']: c['rows'] for c in context['strings']}


def voice_state(row):
    sound_id = row['sound_id']
    if sound_id is None or sound_id == 0 or sound_id >= 0x80000000:
        return 'no_voice'
    return 'positive'


def analyze_map(receipt, global_rows, strings):
    level = defaultdict(list)
    for row in receipt['level_conversations']:
        level[row['name'].lower()].append(row)
    leads = defaultdict(list)
    for lead in receipt['source_name_leads']:
        leads[lead['name'].lower()].append(lead)
    missing, text_ids, remarks, orator_errors = [], set(), 0, 0
    found = Counter()
    for name, rows in sorted(leads.items()):
        located = level.get(name, []) + global_rows.get(name, [])
        if not located:
            missing.append({'name': name, 'sites': [{'script': r.get('script'), 'line': r.get('line'),
                            'in_closure': r.get('script_in_discovered_closure')} for r in rows]})
            continue
        found['level' if name in level else 'global'] += 1
        for row in located:
            for remark in row['remarks']:
                remarks += 1
                text_ids.add(remark['text_id'])
                if not 0 <= remark['orator_index'] < len(row['orators']):
                    orator_errors += 1
    per_candidate = {}
    for archive, rows in strings.items():
        absent = sorted(t for t in text_ids if t not in rows)
        present = [rows[t] for t in text_ids if t in rows]
        empty = sum(1 for r in present if r['translations'] and r['translations'][0]['code_units'] == 0)
        no_translation = sum(1 for r in present if not r['translations'])
        voices = Counter(voice_state(r) for r in present)
        per_candidate[archive] = {'text_ids_absent': absent, 'empty_first_translation': empty,
                                  'rows_without_translation': no_translation, 'voice': dict(voices)}
    sound_gaps = {}
    for candidate in receipt['string_database_candidates']:
        kinds = defaultdict(set)
        for finding in candidate['findings']:
            if finding.get('text_id') in text_ids:
                kinds[finding['kind']].add(finding['text_id'])
        sound_gaps[candidate['archive']] = {k: sorted(v) for k, v in sorted(kinds.items())}
    return {'conversation_names': len(leads), 'found_level': found['level'], 'found_global': found['global'],
            'missing_names': missing, 'remarks': remarks, 'text_ids': len(text_ids),
            'orator_index_errors': orator_errors, 'candidates': per_candidate, 'sound_gaps': sound_gaps}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--receipts', type=Path, required=True,
                        help='directory of <map>-conversations.json from audit_mission_conversations')
    parser.add_argument('--output', type=Path, required=True, help='JSON result path below private build/')
    args = parser.parse_args()
    if not args.output.resolve().is_relative_to((args.root / 'build').resolve()):
        parser.error('detailed receipts must remain under private build/')
    context = resource_context(args.data)
    globals_by_name = defaultdict(list)
    for candidate in context['globals']:
        for row in candidate['rows']:
            globals_by_name[row['name'].lower()].append(row)
    strings = candidate_rows(context)
    result = {'schema_version': 1, 'maps': {}, 'scripts': {}}
    for name in MAPS:
        path = args.receipts / (name.lower() + '-conversations.json')
        result['maps'][name] = analyze_map(json.loads(path.read_text()), globals_by_name, strings)
        print(json.dumps({'map': name, **{k: v for k, v in result['maps'][name].items()
                                          if k in ('conversation_names', 'found_level', 'found_global', 'text_ids')},
                          'missing': [m['name'] for m in result['maps'][name]['missing_names']]}), flush=True)
    scripts = args.root / 'upstream/CnC_Renegade/Code/Scripts'
    for path in sorted(scripts.glob('*.cpp')):
        result['scripts'][path.name] = scan_script_arguments(path.read_text(encoding='latin1'), path.name)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=1) + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
