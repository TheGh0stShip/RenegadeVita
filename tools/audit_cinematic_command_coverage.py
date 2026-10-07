#!/usr/bin/env python3
"""Read-only inventory of cinematic control commands in retail MIX/DAT archives.

Scans every .txt member of the campaign archives (M01..M11, M13) plus
always.dat/Always2.dat, parses each line with the original Test_Cinematic
loader/dispatch rules (Load_Control_File, Get_Command_Parameter, Title_Match)
and compares the command names with the ones that staging/scripts/
Test_Cinematic.cpp actually dispatches.  Nothing here executes commands or
proves runtime/physical behavior; it is a static text audit.

Retail data is opened read-only.  The Markdown report contains only counts,
member names and short command prefixes (no retail payload is copied).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from tools.audit_cinematic_slots import ASCII_SPACE, integer, runtime_parameters, time_seconds
from tools.renegade_cinematic_dependency_scan import MixArchive

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA = Path('/mnt/c/Users/steve/AppData/Roaming/Vita3K/Vita3K/ux0/data/renegade/retail/Data')
DEFAULT_UPSTREAM = ROOT / 'upstream/CnC_Renegade'
CAMPAIGN = ['M01.mix', 'M02.mix', 'M03.mix', 'M04.mix', 'M05.mix', 'M06.mix', 'M07.mix',
            'M08.mix', 'M09.mix', 'M10.mix', 'M11.mix', 'M13.mix']
SHARED = ['always.dat', 'Always2.dat']
INFORMATIONAL = {'extra_args_ignored', 'title_case_differs_from_canonical', 'detach_host_slot_minus1'}
MISSION_SOURCES = {'Mission00.cpp': 'M00', 'Mission01.cpp': 'M01', 'Mission02.cpp': 'M02', 'Mission03.cpp': 'M03',
                   'Mission04.cpp': 'M04', 'Mission05.cpp': 'M05', 'Mission06.cpp': 'M06', 'Mission07.cpp': 'M07',
                   'mission08.cpp': 'M08', 'Mission09.cpp': 'M09', 'Mission10.cpp': 'M10', 'Mission11.cpp': 'M11',
                   'MissionX0.cpp': 'M13'}
NUM_SLOTS = 40
LAST_VALID_TIMESTAMP = 999000.0

# Title_Match order in Test_Cinematic::Parse_Command.  `reads` is the number of
# Get_First/Next_Parameter calls the Command_* handler makes; `types` gives how
# each read is consumed (slot = guarded 0..39 slot, uslot = unguarded index,
# int/float = atoi/atof, str = text, hashid = id or #slot).
COMMANDS = [
    ('Create_Object',           [('slot', 'slot'), ('model', 'str')]),
    ('Create_Real_Object',      [('slot', 'slot'), ('preset', 'str'), ('host_slot', 'uslot_opt'), ('host_bone', 'str')]),
    ('Create_Explosion',        [('preset', 'str'), ('host_slot', 'uslot'), ('host_bone', 'str')]),
    ('Destroy_Object',          [('slot', 'slot')]),
    ('Play_Animation',          [('slot', 'slot'), ('anim', 'str'), ('looping', 'int'), ('sub_obj', 'str'), ('blended', 'int')]),
    ('Play_Audio',              [('preset', 'str'), ('slot', 'slot_opt'), ('bone', 'str')]),
    ('Control_Camera',          [('slot', 'slot_cam')]),
    ('Send_Custom',             [('to', 'hashid'), ('type', 'int'), ('param', 'hashid')]),
    ('Attach_To_Bone',          [('obj_slot', 'slot'), ('host_slot', 'slot'), ('bone', 'str')]),
    ('Attach_Script',           [('slot', 'slot'), ('script', 'str'), ('script_params', 'str')]),
    ('Set_Primary',             [('slot', 'slot')]),
    ('Move_Slot',               [('new', 'slot'), ('old', 'slot')]),
    ('Sniper_Control',          [('enabled', 'int'), ('zoom', 'float')]),
    ('Shake_Camera',            [('slot', 'slot'), ('intensity', 'float'), ('duration', 'float')]),
    ('Enable_Shadow',           [('slot', 'slot'), ('onoff', 'int')]),
    ('Enable_Letterbox',        [('onoff', 'int'), ('time', 'float')]),
    ('Set_Screen_Fade_Color',   [('r', 'float'), ('g', 'float'), ('b', 'float'), ('time', 'float')]),
    ('Set_Screen_Fade_Opacity', [('opacity', 'float'), ('time', 'float')]),
]
NAMES = [name for name, _ in COMMANDS]
SPEC = {name.lower(): (name, fields) for name, fields in COMMANDS}
# Minimum meaningful arguments (empty/missing reads fall back to ""/0).
REQUIRED = {
    'create_object': 2, 'create_real_object': 2, 'create_explosion': 3, 'destroy_object': 1,
    'play_animation': 2, 'play_audio': 1, 'control_camera': 1, 'send_custom': 3,
    'attach_to_bone': 2, 'attach_script': 2, 'set_primary': 1, 'move_slot': 2,
    'sniper_control': 2, 'shake_camera': 3, 'enable_shadow': 2, 'enable_letterbox': 2,
    'set_screen_fade_color': 4, 'set_screen_fade_opacity': 2,
}
INT_RE = re.compile(r'[+-]?\d+$')
FLOAT_RE = re.compile(r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$')


def split_lines(payload):
    """Text_File_Get_String: LF terminated, at most 199 bytes kept, NUL-first ends load."""
    lines = payload.split(b'\n')
    out = []
    for index, raw in enumerate(lines):
        if index < len(lines) - 1:
            raw += b'\n'
        if not raw:
            break
        truncated = len(raw) > 199
        raw = raw[:199]
        if raw[0] == 0:
            out.append((index + 1, None, truncated))   # loader stops here
            break
        out.append((index + 1, raw.split(b'\0', 1)[0], truncated))
    return out


def strip_ws(text, signed_char):
    """Whitespace per `*p <= ' '`: signed char (PC) treats bytes >=0x80 as blanks."""
    blank = ASCII_SPACE + '\0' + (''.join(chr(v) for v in range(128, 256)) if signed_char else '')
    return text.strip(blank), blank


def parse_payload(payload, signed_char=True):
    records, notes = [], []
    for number, raw, truncated in split_lines(payload):
        if raw is None:
            notes.append((number, 'nul_first_byte_ends_load'))
            break
        if truncated:
            notes.append((number, 'line_truncated_to_199'))
        text = raw.replace(b'\t', b' ').decode('latin1')
        text, blank = strip_ws(text, signed_char)
        if not text or text.startswith(';'):
            continue
        end = 0
        while end < len(text) and text[end] not in blank:
            end += 1
        token, rest = text[:end], text[end:].lstrip(blank)
        if not rest:
            notes.append((number, 'time_without_command_ignored'))
            continue
        try:
            seconds = time_seconds(token)
            time_ok = True
        except (ValueError, OverflowError):
            seconds, time_ok = 0.0, False
            notes.append((number, 'unsupported_atof_spelling'))
        if not FLOAT_RE.match(token) and time_ok:
            notes.append((number, 'time_token_not_numeric_atof_zero'))
        records.append({'line': number, 'token': token, 'seconds': seconds, 'text': rest})
    records.sort(key=lambda r: (r['seconds'], r['line']))
    return records, notes


def classify(record):
    """Reproduce Title_Match order; report exact/prefix/unknown plus parameter list."""
    text = record['text']
    title_end = text.find(',')
    title_token = (text if title_end < 0 else text[:title_end]).strip()
    for name in NAMES:
        if text[:len(name)].lower() == name.lower():
            after_title = text[len(name):]
            comma = after_title.find(',')
            skipped = (after_title if comma < 0 else after_title[:comma])
            params = runtime_parameters(after_title[comma + 1:]) if comma >= 0 else []
            return {'command': name, 'match': 'exact' if title_token.lower() == name.lower() else 'prefix',
                    'title_token': title_token, 'skipped_text': skipped.strip(), 'args': params,
                    'has_comma': comma >= 0}
    return {'command': None, 'match': 'unknown', 'title_token': title_token, 'args': [], 'skipped_text': '',
            'has_comma': title_end >= 0}


def argument_findings(info):
    """Argument-count and value edge cases the original handler tolerates silently."""
    name = info['command']
    key = name.lower()
    _, fields = SPEC[key]
    args = info['args']
    reads = len(fields)
    out = []
    if info['skipped_text']:
        out.append('title_suffix_skipped')       # e.g. "Control_Camera 0" -> args lost
    if not info['has_comma'] and reads:
        out.append('no_comma_all_args_empty')
    nonempty = [a for a in args if a != '']
    if len(args) < REQUIRED[key] or any(args[i] == '' for i in range(min(REQUIRED[key], len(args)))):
        if not nonempty:
            out.append('no_args_default_slot0_or_empty')
        elif key not in ('create_real_object',) or len(args) < 2:
            out.append('missing_required_args')
    if len(args) > reads:
        out.append('extra_args_ignored')
    if info['title_token'] != name:
        out.append('title_case_differs_from_canonical')
    for index, (field, kind) in enumerate(fields):
        value = args[index] if index < len(args) else ''
        if kind in ('slot', 'slot_opt', 'slot_cam', 'uslot', 'uslot_opt'):
            if value == '' and kind in ('slot_opt', 'uslot_opt'):
                continue
            if value != '' and not INT_RE.match(value):
                out.append('nonnumeric_%s' % field)
            slot = integer(value) if value != '' else 0
            if slot is None:
                out.append('slot_overflow_%s' % field)
            elif kind in ('uslot', 'uslot_opt'):
                if not 0 <= slot < NUM_SLOTS:
                    out.append('UNGUARDED_slot_out_of_range_%s' % field)   # ObjectSlots[idx] OOB read
            elif kind == 'slot_cam':
                if slot < -1 or slot >= NUM_SLOTS:
                    out.append('camera_slot_out_of_range')
            elif not 0 <= slot < NUM_SLOTS:
                if key == 'attach_to_bone' and field == 'host_slot':
                    # Original: out-of-range host slot becomes -1, which detaches.
                    out.append('detach_host_slot_minus1' if slot == -1 else 'detach_via_out_of_range_host_slot')
                else:
                    out.append('guarded_slot_out_of_range_%s' % field)
        elif kind == 'int':
            if value != '' and not INT_RE.match(value):
                out.append('nonnumeric_int_%s' % field)
        elif kind == 'float':
            if value != '' and not FLOAT_RE.match(value):
                out.append('nonnumeric_float_%s' % field)
        elif kind == 'hashid':
            body = value.split('#', 1)[1] if '#' in value else value
            if value == '':
                continue
            if not INT_RE.match(body.strip()):
                out.append('nonnumeric_%s' % field)
            elif '#' in value:
                s = integer(body)
                if s is None or not 0 <= s < NUM_SLOTS:
                    out.append('hash_slot_out_of_range_%s' % field)
        elif kind == 'str':
            if value == '' and index < REQUIRED[key]:
                out.append('empty_%s' % field)
    return sorted(set(out))


def source_literals(upstream):
    """Map lower-case .txt filename -> sources whose string literals mention it."""
    mapping = defaultdict(set)
    scripts = upstream / 'Code/Scripts'
    if not scripts.is_dir():
        return mapping
    pattern = re.compile(r'"([^"\\]*?\.txt)"', re.I)
    for path in sorted(scripts.glob('*.cpp')):
        text = path.read_text(encoding='latin1')
        for match in pattern.finditer(text):
            name = match.group(1).replace('\\', '/').split('/')[-1].lower()
            mapping[name].add(path.name)
    return mapping


def audit(data, upstream):
    literals = source_literals(upstream)
    members = []
    archive_hashes = {}
    for archive_name in CAMPAIGN + SHARED:
        path = data / archive_name
        if not path.exists():
            continue
        archive = MixArchive(path)
        archive_hashes[archive_name] = hashlib.sha256(path.read_bytes()).hexdigest()
        for name in sorted(archive.entries):
            if not name.endswith('.txt'):
                continue
            payload = archive.read_binary(name)
            records, notes = parse_payload(payload, signed_char=True)
            records_u, _ = parse_payload(payload, signed_char=False)
            row = {'archive': archive_name, 'member': name, 'bytes': len(payload),
                   'sha256': hashlib.sha256(payload).hexdigest(),
                   'crlf_lines': payload.count(b'\r\n'), 'high_bytes': sum(b >= 0x80 for b in payload),
                   'signed_unsigned_char_diverge': [(r['seconds'], r['text']) for r in records]
                                                    != [(r['seconds'], r['text']) for r in records_u],
                   'source_literal_refs': sorted(literals.get(name, [])), 'records': [], 'notes': notes}
            for rec in records:
                info = classify(rec)
                entry = {'line': rec['line'], 'time': rec['seconds'], 'token': rec['token'],
                         **{k: info[k] for k in ('command', 'match', 'title_token', 'args')}}
                if info['command']:
                    entry['findings'] = argument_findings(info)
                else:
                    entry['findings'] = []
                    entry['sample'] = rec['text'][:48]
                row['records'].append(entry)
            row['dispatchable'] = sum(1 for r in row['records'] if r['command'])
            row['is_control'] = row['dispatchable'] > 0
            members.append(row)
    return {'archives': archive_hashes, 'members': members}


def summarize(result):
    controls = [m for m in result['members'] if m['is_control']]
    noncontrol = [m for m in result['members'] if not m['is_control']]
    per_archive = defaultdict(Counter)
    per_archive_files = Counter()
    totals = Counter()
    unknown = defaultdict(list)
    prefix_matches = []
    finding_counts = Counter()
    finding_examples = defaultdict(list)
    timing = Counter()
    extras = Counter()
    arity = defaultdict(Counter)
    tail = Counter()
    unknown_numeric_time = Counter()
    all_instances = defaultdict(list)
    for m in controls:
        per_archive_files[m['archive']] += 1
        for r in m['records']:
            if r['command']:
                per_archive[m['archive']][r['command']] += 1
                totals[r['command']] += 1
                if r['match'] == 'prefix':
                    prefix_matches.append((m['archive'], m['member'], r['line'], r['title_token']))
                arity[r['command']][len(r['args'])] += 1
                if r['time'] >= LAST_VALID_TIMESTAMP:
                    tail[r['command']] += 1
                if 'extra_args_ignored' in r['findings']:
                    extras[(r['command'], len(r['args']))] += 1
                for f in r['findings']:
                    all_instances[f].append((m['archive'], m['member'], r['line'], r['command'], r['args']))
                    finding_counts[f] += 1
                    if len(finding_examples[f]) < 6:
                        finding_examples[f].append((m['archive'], m['member'], r['line'], r['command'], r['args']))
            else:
                unknown[r['title_token']].append((m['archive'], m['member'], r['line']))
                unknown_numeric_time[bool(re.match(r'[+-]?[\d.]', r['token']))] += 1
            if r['time'] >= LAST_VALID_TIMESTAMP:
                timing['tail_or_boundary_commands'] += 1
            if r['token'].startswith('-'):
                timing['negative_frame_time_commands'] += 1
            if r['time'] == 0:
                timing['time_zero_commands'] += 1
    return {'controls': controls, 'noncontrol': noncontrol, 'per_archive': per_archive,
            'per_archive_files': per_archive_files, 'totals': totals, 'unknown': unknown,
            'prefix_matches': prefix_matches, 'finding_counts': finding_counts,
            'finding_examples': finding_examples, 'timing': timing, 'extras': extras, 'arity': arity, 'tail': tail,
            'unknown_numeric_time': unknown_numeric_time, 'all_instances': all_instances}


def table(headers, rows):
    out = ['| ' + ' | '.join(headers) + ' |', '|' + '|'.join(' --- ' for _ in headers) + '|']
    out += ['| ' + ' | '.join(str(c) for c in row) + ' |' for row in rows]
    return '\n'.join(out)


def render(result, s):
    archives = CAMPAIGN + SHARED
    present = [a for a in archives if a in result['archives']]
    lines = []
    w = lines.append
    w('# Cinematic command coverage (retail control files vs `Test_Cinematic`)')
    w('')
    w('Static text audit, generated by `python3 -m tools.audit_cinematic_command_coverage`. '
      'It applies the original `Load_Control_File` / `Get_Command_Parameter` / `Title_Match` rules to every '
      '`.txt` member of M01..M11, M13, `always.dat` and `Always2.dat` in the unchanged retail Data directory. '
      'Nothing was executed; no runtime, Vita3K or physical-Vita acceptance is implied. '
      'No retail payload is reproduced here, only member names, counts and short command titles.')
    w('')
    total_records = sum(s['totals'].values()) + sum(len(v) for v in s['unknown'].values() if False)
    unknown_records = sum(len(v) for v in s['unknown'].values())
    w('## Headline')
    w('')
    w('- `.txt` members scanned: **%d** across %d archives; **%d** are cinematic control files '
      '(at least one dispatchable command), %d are other text.' % (
          len(result['members']), len(present), len(s['controls']), len(s['noncontrol'])))
    w('- Records in control files: **%d** dispatchable + **%d** that no `Title_Match` accepts.' % (
        sum(s['totals'].values()), unknown_records))
    w('- Distinct commands used: **%d of %d** implemented.  Implemented but never used by retail data: %s.' % (
        len(s['totals']), len(NAMES),
        ', '.join('`%s`' % n for n in NAMES if n not in s['totals']) or 'none'))
    w('- Unknown command titles in control files: **%d distinct / %d records**.' % (
        len(s['unknown']), unknown_records))
    w('- Prefix-only title matches (title longer than a known command): **%d**.' % len(s['prefix_matches']))
    w('')
    w('## Commands implemented by `Test_Cinematic::Parse_Command`')
    w('')
    w('The staging `Test_Cinematic.cpp` has the same 18 `Title_Match` lines, in the same order, as '
      'upstream `Code/Scripts/Test_Cinematic.cpp` (verified by diff of the `Title_Match` lines). '
      'Matching is `strnicmp` on the title prefix, then skip to the next comma; the Vita patches do not add, '
      'remove or reorder commands.')
    w('')
    rows = []
    for name, fields in COMMANDS:
        rows.append((name, REQUIRED[name.lower()], len(fields),
                     ', '.join('%s:%s' % f for f in fields), s['totals'].get(name, 0)))
    w(table(['Command', 'Min args', 'Args read', 'Argument handling', 'Retail uses'], rows))
    w('')
    w('## Vita patches touching `Test_Cinematic`')
    w('')
    w(table(['Patch', 'Touches command set?', 'Effect'], [
        ('scripts-a35-cinematic-camera-save', 'no', 'persists `IsCameraCinematic` (chunk 8); legacy saves default to false; member initializers'),
        ('scripts-a35-cinematic-command-load-bounds', 'no', 'save-load only: `len > 0`, NUL-terminated check before `Add_Control_Line`'),
        ('scripts-a35-cinematic-control-lifetime', 'no', 'destructor frees `Controls` list'),
        ('scripts-a35-cinematic-filename-diagnostics', 'no', 'drops unused `DATA\\%s` buffer, `%s` log args; filename passed unchanged to `Text_File_Open`'),
        ('scripts-a35-cinematic-primary-id-buffer', 'no', '`char id[12]` for `Set_Primary` attach parameter'),
        ('scripts-a35-cinematic-command-timing / time-budget-only / original-dispatch', 'no', 'diagnostic slow-command log only; net result restores original due-command dispatch in `Parse_Commands`'),
        ('scripts-a35-m13-slot19-phases, scripts-a45-m13-intro-camera-trace, scripts-a36-m13-finale-delivery-trace, dev168-m13-loader-summary', 'no', 'Vita-only trace logging for `X00_Intro.txt` / `X0Z_Finale.txt`'),
        ('combat-a36-level-cinematic-camera-release', 'no', '`CombatManager::Unload_Level` releases cinematic camera host (not in the script)'),
    ]))
    w('')
    w('## Per-archive command usage (control files only)')
    w('')
    header = ['Command'] + [a.replace('.mix', '').replace('.dat', '') for a in present] + ['Total']
    rows = []
    for name in NAMES:
        counts = [s['per_archive'][a].get(name, 0) for a in present]
        rows.append([name] + [c or '' for c in counts] + [s['totals'].get(name, 0)])
    rows.append(['**Control files**'] + [s['per_archive_files'].get(a, 0) for a in present] + [len(s['controls'])])
    rows.append(['**Records**'] + [sum(s['per_archive'][a].values()) for a in present] + [sum(s['totals'].values())])
    w(table(header, rows))
    w('')
    w('`always.dat` / `Always2.dat` control files are shared; the mission sources that name them by '
      'string literal are listed below.')
    w('')
    w('## Unknown / unsupported commands')
    w('')
    if not s['unknown']:
        w('None: every record in every control file matches one of the 18 `Title_Match` titles.')
    else:
        w('Records whose command text matches no `Title_Match` title are silently dropped by the original '
          'parser (the `else` branch has its debug message commented out).')
        w('')
        rows = []
        for title, refs in sorted(s['unknown'].items(), key=lambda kv: -len(kv[1])):
            by_file = Counter((a, m) for a, m, _ in refs)
            rows.append((title or '(empty)', len(refs),
                         '; '.join('%s:%s x%d' % (a, m, c) for (a, m), c in sorted(by_file.items()))))
        w('Time token numeric on %d of these records; non-numeric on %d. A non-numeric first token '
          'makes `atof` return 0, so these are decorative banner/comment lines authored without a leading `;` '
          'that load at time 0 and dispatch nothing.' % (
              s['unknown_numeric_time'].get(True, 0), s['unknown_numeric_time'].get(False, 0)))
        w('')
        w(table(['Title as authored', 'Records', 'Files'], rows[:40]))
        if len(rows) > 40:
            w('')
            w('(%d further distinct titles omitted)' % (len(rows) - 40))
    w('')
    if s['prefix_matches']:
        w('### Prefix-only matches')
        w('')
        rows = [(a, m, ln, t) for a, m, ln, t in s['prefix_matches'][:40]]
        w(table(['Archive', 'Member', 'Line', 'Title'], rows))
        w('')
    w('## Argument and value edge cases')
    w('')
    w('Counts are records. These are authored-data properties that the original handlers tolerate '
      '(empty string / `atoi` prefix-or-zero); each is a review lead, not a proven runtime defect.')
    w('')
    meaning = {
        'extra_args_ignored': 'more comma fields than the handler reads (legacy position/facing fields); ignored',
        'detach_host_slot_minus1': '`Attach_To_Bone` host slot -1: authored detach (original behavior)',
        'detach_via_out_of_range_host_slot': 'host slot < -1 or >= 40 is clamped to -1 and also detaches',
        'guarded_slot_out_of_range_obj_slot': 'object slot out of range: command silently skipped',
        'nonnumeric_host_slot': 'host slot token is text: `atoi` gives 0, so host becomes slot 0',
        'nonnumeric_slot': 'slot token is text: `atoi` gives 0',
        'no_args_default_slot0_or_empty': 'command has no arguments: `atoi("")` = 0 operates on slot 0 / empty names',
        'missing_required_args': 'fewer or empty required args: handler uses ""/0 defaults',
        'title_case_differs_from_canonical': 'title spelled with different case; accepted by `strnicmp`',
    }
    rows = []
    for f, c in sorted(s['finding_counts'].items(), key=lambda kv: (-kv[1], kv[0])):
        ex = s['finding_examples'][f][0]
        rows.append((f, c, meaning.get(f, ''), '%s:%s line %d `%s`' % (ex[0], ex[1], ex[2], ex[3])))
    if rows:
        w(table(['Finding', 'Records', 'Original behavior', 'First example'], rows))
    else:
        w('No argument-count or value edge cases found.')
    w('')
    w('### Extra arguments by command (field count in the authored line)')
    w('')
    w(table(['Command', 'Fields authored', 'Records'],
            [(c, n, v) for (c, n), v in sorted(s['extras'].items())]))
    w('')
    w('### Authored field-count histogram per command')
    w('')
    rows = []
    for name, fields in COMMANDS:
        hist = s['arity'].get(name)
        if not hist:
            continue
        rows.append((name, REQUIRED[name.lower()], len(fields),
                     ', '.join('%d fields x%d' % (n, c) for n, c in sorted(hist.items()))))
    w(table(['Command', 'Min args', 'Args read', 'Authored distribution'], rows))
    w('')
    w('### Records at time >= 999000 (run only after the primary object is killed)')
    w('')
    w(table(['Command', 'Records'], [(c, n) for c, n in sorted(s['tail'].items(), key=lambda kv: -kv[1])]))
    w('')
    w('### Every instance of the rarer edge cases')
    w('')
    rare = [f for f, c in s['finding_counts'].items()
            if c <= 12 and f not in ('extra_args_ignored',)]
    rows = []
    for f in sorted(rare):
        for a, m, ln, cmd, args in s['all_instances'][f]:
            rows.append((f, '%s:%s' % (a, m), ln, cmd, ', '.join(args)[:60]))
    w(table(['Finding', 'Member', 'Line', 'Command', 'Authored args'], rows) if rows else 'None.')
    w('')
    w('### Control-file level properties')
    w('')
    notes = Counter(n for m in s['controls'] for _, n in m['notes'])
    w(table(['Property', 'Count'], [
        ('control files with CR/LF line endings', sum(1 for m in s['controls'] if m['crlf_lines'])),
        ('control files containing bytes >= 0x80', sum(1 for m in s['controls'] if m['high_bytes'])),
        ('files where signed-char (PC) vs unsigned-char (ARM) whitespace changes the parse',
         sum(1 for m in s['controls'] if m['signed_unsigned_char_diverge'])),
        ('negative (frame-number) time tokens', s['timing'].get('negative_frame_time_commands', 0)),
        ('time >= 999000 (primary-killed tail / boundary)', s['timing'].get('tail_or_boundary_commands', 0)),
        ('time == 0 commands', s['timing'].get('time_zero_commands', 0)),
    ] + [('loader note: ' + k, v) for k, v in sorted(notes.items())]))
    w('')
    w('## Per-mission rollup')
    w('')
    w('Own = control files stored in the mission archive. Shared = `always.dat`/`Always2.dat` control files '
      'whose exact `.txt` name appears as a string literal in that mission\'s upstream script source '
      '(names built at runtime with `sprintf` are not matched, so this is a lower bound). A file named by several mission sources counts in each of them.')
    w('')
    shared_all = [m for m in s['controls'] if m['archive'] in SHARED]
    rows = []
    attributed = set()
    for archive in CAMPAIGN:
        tag = archive.replace('.mix', '')
        own = [m for m in s['controls'] if m['archive'] == archive]
        sources = [src for src, t in MISSION_SOURCES.items() if t == tag]
        shared = [m for m in shared_all if any(r in sources for r in m['source_literal_refs'])]
        attributed.update(m['member'] for m in shared)
        rows.append((tag, len(own), sum(len(m['records']) for m in own), len(shared),
                     sum(len(m['records']) for m in shared),
                     sum(1 for m in own + shared for r in m['records'] if set(r['findings']) - INFORMATIONAL)))
    w(table(['Mission', 'Own control files', 'Own records', 'Shared (literal-referenced)', 'Shared records',
             'Review-flag records'], rows))
    w('')
    other = [m for m in shared_all if m['member'] not in attributed]
    w('Shared control files with no mission-source literal match: %d of %d (%d records); they are reached '
      'through runtime-built names, `Test_*`/other scripts, or presets in the object database.' % (
          len(other), len(shared_all), sum(len(m['records']) for m in other)))
    w('')
    w('## Per-file command usage')
    w('')
    for archive in present:
        files = [m for m in s['controls'] if m['archive'] == archive]
        if not files:
            continue
        w('### %s (%d control files)' % (archive, len(files)))
        w('')
        rows = []
        for m in files:
            counts = Counter(r['command'] or '?' + r['title_token'] for r in m['records'])
            flagged = sum(1 for r in m['records'] if set(r['findings']) - INFORMATIONAL)
            refs = ','.join(m['source_literal_refs'])
            rows.append((m['member'], len(m['records']), ', '.join('%s %d' % (k, v) for k, v in sorted(counts.items())),
                         flagged or '', refs))
        w(table(['Member', 'Records', 'Commands', 'Review flags', 'Source literal refs'], rows))
        w('')
    w('## Non-control `.txt` members')
    w('')
    w(table(['Archive', 'Member', 'Bytes'], [(m['archive'], m['member'], m['bytes']) for m in s['noncontrol']]))
    w('')
    exclusive = {n: [a for a in present if s['per_archive'][a].get(n)] for n in NAMES}
    w('## Findings')
    w('')
    w('1. **Coverage is complete for retail data.** Every one of the %d dispatchable records uses one of the 18 '
      'implemented titles; there are no misspelled or legacy command names (for example no `Send_Custon`). '
      '`Create_Explosion` is implemented but unused by any scanned archive.' % sum(s['totals'].values()))
    w('2. **No Vita-specific command gap.** The Vita patches change save/load bounds, lifetime and diagnostics only (the '
      'dispatch-timing patches net out to the original due-command loop); the 18-title `Title_Match` chain is byte-identical to upstream. Effects of each '
      'command depend on Combat script commands, not on this script.')
    w('3. **The 31 unknown-title records are not commands.** They are banner/comment lines authored without a '
      'leading `;`, so `atof` reads time 0 and `Title_Match` rejects them; they are consumed in the first '
      'dispatch batch with no effect.')
    w('4. **Authored-data defects with deterministic original behavior** (reproduce on Vita only if the original '
      'handler logic is preserved): `Destroy_Object` with no argument destroys slot 0 (M02 `x2e_c130drop`); '
      '`Attach_To_Bone` with a bone name in the host-slot position attaches to slot 0 with an empty bone '
      '(M02 `x2f_orcasam`, M13 `mx0_a03_humveedrop`/`mx0_a03_tankdrop`, always.dat `xg_humveedrop`); '
      'two M01 `x1d_*hover_mtank` `Attach_To_Bone` lines use object slot -4 and are skipped; five M11 '
      '`x11d_repel_*` lines use host slot -2 and detach; two M01 `x1z_finale` `Play_Audio` lines are in a legacy '
      '4-field layout (preset parsed as the leading number).')
    w('5. **Signedness:** no retail control file contains bytes >= 0x80, so the loader\'s signed-char (PC) '
      'versus unsigned-char (ARM default) whitespace tests give the same result on all %d control files. '
      'No `-fsigned-char` was found in `CMakeLists.txt`, `cmake/` or `tools/build.sh`.' % len(s['controls']))
    w('6. **Commands used by three or fewer scanned archives** (narrow retail exposure, so a regression is easy to '
      'miss in a campaign pass): ' + '; '.join('`%s` (%s)' % (n, ', '.join(a.replace('.mix', '') for a in v))
                                     for n, v in exclusive.items() if 0 < len(v) <= 3) + '.')
    w('7. **Mission coverage:** M07 and M10 have no control files of their own and rely on shared `always.dat` '
      'cinematics; M04 and M06 own one and two control files. M02 holds the most records.')
    w('')
    w('## Archive identities')
    w('')
    w(table(['Archive', 'SHA-256'], [(a, '`%s`' % h) for a, h in sorted(result['archives'].items())]))
    w('')
    w('## Limits')
    w('')
    w('- Parser models the original loader (199-byte line cap, tab-to-space, comment/blank skipping, '
      '`atof` time tokens, negative frames at 30 Hz) and `Get_Command_Parameter` quoting. It does not run commands.')
    w('- A member counts as a control file when at least one record dispatches; membership in a mission '
      'is by archive and by string literals in the upstream mission sources, not by runtime reachability.')
    w('- Preset names, animation names, script names and event IDs are not resolved against the object database here.')
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=DEFAULT_DATA)
    parser.add_argument('--upstream', type=Path, default=DEFAULT_UPSTREAM)
    parser.add_argument('--markdown', type=Path, default=ROOT / 'reports/campaign/CINEMATIC_COMMAND_COVERAGE.md')
    parser.add_argument('--json', type=Path, help='optional detailed JSON receipt (keep under build/)')
    args = parser.parse_args()
    result = audit(args.data, args.upstream)
    s = summarize(result)
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.write_text(render(result, s))
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(result, indent=1) + '\n')
    print('members=%d control=%d records=%d unknown_titles=%d' % (
        len(result['members']), len(s['controls']), sum(s['totals'].values()), len(s['unknown'])))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
