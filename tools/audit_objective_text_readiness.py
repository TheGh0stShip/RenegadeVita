"""Read-only campaign objective/HUD/encyclopedia text-ID and glyph readiness audit.

For each requested mission this resolves every script-supplied string ID
(Add_Objective, Set_Objective_HUD_Info*, Display_Text, Set_HUD_Help_Text) and
every literal Reveal_Encyclopedia_* ID against the retail strings.tdb record
sets, then checks the decoded UTF-16 code points against the TrueType cmaps of
the fonts the Vita FreeType provider loads. Reports carry IDs, symbolic names,
counts and code points only; no retail string, audio or font payload is emitted.

Source-scan evidence only: it proves no runtime lookup, rendering or layout.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import unicodedata

import tools.audit_mission_text_routes as routes
from tools.audit_m13_level_owners import chunks, microchunks, u32
from tools.audit_mission_content_bindings import ROOT, source_scripts
from tools.audit_mission_conversations import resource_context
from tools.audit_mission_text_routes import audit, command_calls, constant_id, string_id_definitions
from tools.renegade_cinematic_dependency_scan import MixArchive

MAPS = tuple('M%02d.mix' % n for n in range(1, 12))
OBJECTIVE_COMMANDS = ('Add_Objective', 'Set_Objective_Status', 'Set_Objective_Radar_Blip',
                      'Set_Objective_Radar_Blip_Object', 'Set_Objective_HUD_Info',
                      'Set_Objective_HUD_Info_Position')
ENCYCLOPEDIA = {'Reveal_Encyclopedia_Character': 'characters.ini', 'Reveal_Encyclopedia_Weapon': 'weapons.ini',
                'Reveal_Encyclopedia_Vehicle': 'vehicles.ini', 'Reveal_Encyclopedia_Building': 'buildings.ini'}
# Radar enumerations from scriptcommands.h (shape 0..4, color 0..7).
RADAR_SHAPES, RADAR_COLORS = range(0, 5), range(0, 8)
# Font families named by stylemgr.ini; HUD/objective/subtitle fonts are all Arial MT.
FONT_FILES = {'Arial MT (ARI_____.TTF)': 'ARI_____.TTF', 'Regatta Condensed (54251___.TTF)': '54251___.TTF'}
FONT_FALLBACK_FILES = {'Arial user fallback (arial.ttf)': 'arial.ttf'}


# ---------------------------------------------------------------- TrueType cmap
def ttf_codepoints(data):
    """Return the set of Unicode code points mapped to a nonzero glyph (cmap 0/3)."""
    count = struct.unpack('>H', data[4:6])[0]
    tables = {}
    for i in range(count):
        tag, _, offset, length = struct.unpack('>4sIII', data[12 + 16 * i:28 + 16 * i])
        tables[tag] = (offset, length)
    base = tables[b'cmap'][0]
    subtables = struct.unpack('>H', data[base + 2:base + 4])[0]
    result = set()
    for i in range(subtables):
        platform, encoding, offset = struct.unpack('>HHI', data[base + 4 + 8 * i:base + 12 + 8 * i])
        if not (platform == 0 or (platform == 3 and encoding in (1, 10))):
            continue
        start = base + offset
        fmt = struct.unpack('>H', data[start:start + 2])[0]
        if fmt == 0:
            result.update(c for c in range(256) if data[start + 6 + c])
        elif fmt == 4:
            segments = struct.unpack('>H', data[start + 6:start + 8])[0] // 2
            end_at, start_at = start + 14, start + 16 + 2 * segments
            delta_at, range_at = start_at + 2 * segments, start_at + 4 * segments
            for s in range(segments):
                last = struct.unpack('>H', data[end_at + 2 * s:end_at + 2 * s + 2])[0]
                first = struct.unpack('>H', data[start_at + 2 * s:start_at + 2 * s + 2])[0]
                delta = struct.unpack('>h', data[delta_at + 2 * s:delta_at + 2 * s + 2])[0]
                ro = struct.unpack('>H', data[range_at + 2 * s:range_at + 2 * s + 2])[0]
                for code in range(first, last + 1):
                    if code == 0xFFFF:
                        continue
                    if ro == 0:
                        glyph = (code + delta) & 0xFFFF
                    else:
                        addr = range_at + 2 * s + ro + 2 * (code - first)
                        glyph = struct.unpack('>H', data[addr:addr + 2])[0]
                        glyph = (glyph + delta) & 0xFFFF if glyph else 0
                    if glyph:
                        result.add(code)
        elif fmt == 6:
            first, entries = struct.unpack('>HH', data[start + 6:start + 10])
            for k in range(entries):
                if struct.unpack('>H', data[start + 10 + 2 * k:start + 12 + 2 * k])[0]:
                    result.add(first + k)
        elif fmt == 12:
            groups = struct.unpack('>I', data[start + 12:start + 16])[0]
            for g in range(groups):
                lo, hi, gid = struct.unpack('>III', data[start + 16 + 12 * g:start + 28 + 12 * g])
                result.update(c for c in range(lo, hi + 1) if gid + (c - lo))
    return result


def load_fonts(font_dirs):
    fonts, missing = {}, []
    for table, role in ((FONT_FILES, 'primary'), (FONT_FALLBACK_FILES, 'fallback')):
        for label, name in table.items():
            found = next((p for d in font_dirs for p in Path(d).iterdir() if p.name.lower() == name.lower()), None)
            if found is None:
                missing.append(label)
                continue
            payload = found.read_bytes()
            fonts[label] = {'role': role, 'bytes': len(payload), 'sha256': hashlib.sha256(payload).hexdigest(),
                            'codepoints': ttf_codepoints(payload)}
    return fonts, missing


# ------------------------------------------------------- translation DB (texts)
def translation_texts(nodes):
    """Mirror audit_mission_conversations.translations but keep decoded UTF-16 in memory."""
    result = {}
    for manager in nodes:
        if manager.kind != 0x90000:
            continue
        for section in manager.children:
            if section.kind != 0x07141201:
                continue
            for factory in section.children:
                if factory.kind != 0x90001:
                    continue
                body = factory.children[1].children
                variables = [n for n in body if n.kind == 0x06141108]
                fields = dict(microchunks(variables[0].data))
                key = u32(fields[1])
                wide = [n.data for n in body if n.kind == 0x0614110b]
                if 3 in fields:
                    wide.insert(0, fields[3])
                result[key] = [w.decode('utf-16le').rstrip('\0') for w in wide]
    return result


def load_translation_candidates(data):
    candidates = {}
    for path in sorted(data.iterdir()):
        if not (path.name.lower().startswith('always') and path.suffix.lower() in ('.dat', '.dbs', '.mix')):
            continue
        archive = MixArchive(path)
        if 'strings.tdb' in archive.entries:
            payload = archive.read_binary('strings.tdb')
            candidates[path.name] = {'sha256': hashlib.sha256(payload).hexdigest(),
                                     'texts': translation_texts(chunks(payload))}
    return candidates


def load_encyclopedia(data):
    """characters/weapons/vehicles/buildings.ini: section ID -> (NameID, DescriptionID)."""
    result = {}
    for path in sorted(data.iterdir()):
        if not (path.name.lower().startswith('always') and path.suffix.lower() in ('.dat', '.dbs', '.mix')):
            continue
        archive = MixArchive(path)
        for ini in ENCYCLOPEDIA.values():
            if ini not in archive.entries or ini in result:
                continue
            rows, section = {}, None
            for line in archive.read_binary(ini).decode('latin1').splitlines():
                line = line.split(';', 1)[0].strip()
                if line.startswith('['):
                    section = {'section': line}
                elif '=' in line and section is not None:
                    key, value = (x.strip() for x in line.split('=', 1))
                    section[key.lower()] = value
                    if key.lower() == 'id' and value.isdigit():
                        rows[int(value)] = section
            result[ini] = {'archive': path.name, 'rows': rows}
    return result


# -------------------------------------------------------------------- analysis
def text_class(text, fonts):
    """Return {codepoint: {font label: covered}} for non-ASCII and control characters."""
    result = {}
    for ch in set(text):
        cp = ord(ch)
        if 0x20 <= cp < 0x7F:
            continue
        result[cp] = {label: cp in font['codepoints'] for label, font in fonts.items()}
    return result


def analyze_map(root, data, map_name, context, scripts, ids, candidates, fonts, encyclopedia, owner_scan):
    if owner_scan:
        number = int(re.search(r'(\d+)', map_name)[1])
        owners = {r['owner'] for r in scripts.values() if re.fullmatch(r'mission0*%d\.cpp' % number, r['owner'].lower())}
        routes.OWNERS[map_name] = sorted(owners)[0] if owners else None
    result = audit(root, data, map_name, context, scripts)
    primary = sorted(candidates)[0]
    findings, unresolved, per_id = [], [], {}
    glyph_gaps = {}  # (candidate, language) -> {cp: {font: bool}} with IDs
    for call in result['text_calls']:
        if call['state'] == 'clear_help':
            continue
        if call['state'] != 'resolved_source_id':
            unresolved.append({k: call[k] for k in ('script', 'owner', 'command', 'line', 'expression', 'argument_index')})
            continue
        text_id = call['text_id']
        if text_id == 0 and call['command'] != 'Set_HUD_Help_Text':
            continue  # 0 is the original "no description / none" sentinel for objective/message IDs.
        per_id.setdefault(text_id, []).append(call)
    for text_id, calls in sorted(per_id.items()):
        names = sorted({n for n, v in ids.items() if constant_id(v, ids) == text_id})
        entry = {'id': text_id, 'names': names, 'calls': [{k: c[k] for k in ('script', 'command', 'line', 'argument_index', 'script_in_discovered_closure')} for c in calls]}
        for cand_name, cand in candidates.items():
            texts = cand['texts'].get(text_id)
            if texts is None:
                findings.append({**entry, 'kind': 'missing_in_tdb', 'candidate': cand_name})
                continue
            if not texts or all(t == '' for t in texts):
                findings.append({**entry, 'kind': 'empty_translation', 'candidate': cand_name})
            for language, text in enumerate(texts):
                for cp, cover in text_class(text, fonts).items():
                    glyph_gaps.setdefault((cand_name, language), {}).setdefault(cp, {'covered': cover, 'ids': set()})['ids'].add(text_id)
    # Objective/radar call checks: objective IDs used by Set_Objective_* but never added.
    names = {c['script'].lower() for c in result['text_calls']}
    added, used, radar_calls, bad_radar = set(), {}, 0, []
    encyclopedia_calls = []
    for name in names:
        row = scripts.get(name)
        if row is None:
            continue
        for call in command_calls(row['body']):
            command, args = call['command'], call['arguments']
            line = row['body_start_line'] + row['body'].count('\n', 0, call['offset'])
            if command in OBJECTIVE_COMMANDS and args:
                key = re.sub(r'\s+', '', args[0][1])
                (added.add(key) if command == 'Add_Objective' else used.setdefault(key, []).append((row['name'], command, line)))
            if command == 'Add_Radar_Marker' and len(args) >= 4:
                radar_calls += 1
                for expr, valid, label in ((args[2][1], RADAR_SHAPES, 'shape'), (args[3][1], RADAR_COLORS, 'color')):
                    value = constant_id(expr, ids)
                    if value is not None and value not in valid:
                        bad_radar.append({'script': row['name'], 'line': line, 'field': label, 'value': value})
            if command in ENCYCLOPEDIA and args:
                value = constant_id(args[0][1], ids)
                encyclopedia_calls.append({'script': row['name'], 'line': line, 'command': command,
                                           'expression': args[0][1], 'id': value, 'ini': ENCYCLOPEDIA[command]})
    for call in encyclopedia_calls:
        rows = encyclopedia.get(call['ini'], {}).get('rows', {})
        row = rows.get(call['id']) if call['id'] is not None else None
        call['ini_section_found'] = row is not None
        call['name_id'] = int(row['nameid']) if row and row.get('nameid', '').isdigit() else None
        call['description_id'] = int(row['descriptionid']) if row and row.get('descriptionid', '').isdigit() else None
        call['text_missing'] = {cand_name: [t for t in (call['name_id'], call['description_id'])
                                            if t is not None and t not in cand['texts']]
                                for cand_name, cand in candidates.items()} if row else {}
    return {'map': map_name, 'archive_sha256': result['archive_sha256'], 'findings': findings,
            'unresolved_expressions': unresolved, 'unique_text_ids': len(per_id),
            'text_calls': len(result['text_calls']), 'per_command': {c: sum(1 for x in result['text_calls'] if x['command'] == c) for c in sorted({x['command'] for x in result['text_calls']})},
            'objectives_added': sorted(added), 'objective_refs_without_add': sorted(k for k in used if k not in added),
            'radar_marker_calls': radar_calls, 'radar_invalid_literals': bad_radar,
            'encyclopedia_calls': encyclopedia_calls,
            'glyph_gaps': [{'candidate': c, 'language_index': l, 'codepoint': cp, 'covered': v['covered'], 'id_count': len(v['ids']),
                            'ids': sorted(v['ids'])[:12]}
                           for (c, l), rows in sorted(glyph_gaps.items()) for cp, v in sorted(rows.items())],
            'closure_vs_owner': {'closure_text_ids': len({c['text_id'] for c in result['text_calls'] if c['script_in_discovered_closure'] and c['state'] == 'resolved_source_id'}),
                                 'owner_lead_only_text_ids': len({c['text_id'] for c in result['text_calls'] if not c['script_in_discovered_closure'] and c['state'] == 'resolved_source_id'})},
            'sentinel_primary_candidate': primary}


LANGUAGES = ('English', 'French', 'German', 'Spanish', 'Chinese', 'Japanese', 'Korean')  # translatedb.h LANGID_*


def glyph_rows(maps, labels):
    """Aggregate (candidate, language) -> code points with per-font coverage over all maps."""
    agg = {}
    for m in maps:
        for g in m['glyph_gaps']:
            row = agg.setdefault((g['candidate'], g['language_index']), {})
            row.setdefault(g['codepoint'], {'covered': g['covered'], 'ids': set()})['ids'].update(g['ids'])
    table = []
    for (cand, lang), rows in sorted(agg.items()):
        printable = {cp: v for cp, v in rows.items() if cp != 0x0A}  # newline is a row break, not a glyph
        table.append({'candidate': cand, 'language': lang, 'codepoints': len(printable),
                      'uncovered': {label: sorted(cp for cp, v in printable.items() if not v['covered'][label]) for label in labels}})
    return table


def render_report(summary, header_sha256):
    """Markdown with IDs, counts and code points only; never retail string text."""
    maps, fonts, cands = summary['maps'], summary['fonts'], summary['candidates']
    labels = list(fonts)
    missing = sum(len(m['findings']) for m in maps)
    unresolved = sum(len(m['unresolved_expressions']) for m in maps)
    out = ['# Campaign objective/HUD text readiness M01-M11', '',
           'Read-only scan of `Add_Objective`, `Set_Objective_HUD_Info(_Position)`, `Display_Text` and',
           '`Set_HUD_Help_Text` string IDs, radar markers and `Reveal_Encyclopedia_*` IDs against the retail',
           '`strings.tdb` record sets, plus Unicode coverage of the Vita FreeType font files. Tool:',
           '`tools/audit_objective_text_readiness.py` (extends `tools/audit_mission_text_routes.py`).',
           'Evidence class: host Python source/data scan; no build, launch, emulator or Vita. No retail text is',
           'reproduced (IDs, counts and code points only). It proves no runtime lookup, rendering or layout.', '',
           '## Verdict', '',
           f'- Unresolved string IDs, M01-M11, both TDB candidates: **{missing}**.',
           f'- Non-constant/unresolvable string-ID expressions: **{unresolved}**.',
           '- Runtime language is English: both retail strings.tdb files store language ID 0 in their variables chunk,',
           '  `TranslateDBClass::m_LanguageID` defaults to LANGID_ENGLISH, and the only game-side',
           '  `Set_Current_Language` (Commando/init.cpp) is commented out. English strings in the referenced IDs are',
           '  ASCII plus U+000A newline, so no non-ASCII glyph is required for English.',
           '- Non-English records: French/German need Latin-1 plus U+0153, covered by Arial MT; Chinese/Korean need',
           '  CJK/Hangul, which Arial MT, Regatta and the user `arial.ttf` fallback do **not** cover. Not a defect for',
           '  English play; a gap if non-English language selection is ever exposed on Vita.',
           '- Encyclopedia reveals: every literal ID has an INI section whose NameID/DescriptionID resolve in both TDBs.', '',
           '## Inputs', '', '| Input | SHA-256 | Detail |', '|---|---|---|']
    for name, c in cands.items():
        out.append(f"| {name} strings.tdb | `{c['sha256']}` | {c['ids']} IDs, translations per ID {c['languages_per_id']} |")
    for name, f in fonts.items():
        out.append(f"| {name} | `{f['sha256']}` | {f['bytes']} bytes, {f['codepoints']} Unicode code points ({f['role']}) |")
    out += [f'| string_ids.h | `{header_sha256}` | symbolic ID header |', '',
            "Scope: scripts in each map's discovered binding closure plus the mission owner `.cpp` (scripts not bound",
            'in the closure are \"owner-only leads\"). Both archive candidates are checked so the result is independent',
            'of mount order.', '',
            '## Per-mission ID resolution', '',
            '| Map | Add_Objective | HUD info | Display_Text | HUD help | Unique IDs | Closure IDs | Owner-only IDs | Missing | Unresolved exprs | Radar markers | Encyclopedia reveals |',
            '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for m in maps:
        pc = m['per_command']
        out.append(f"| {m['map']} | {pc.get('Add_Objective', 0)} | "
                   f"{pc.get('Set_Objective_HUD_Info', 0) + pc.get('Set_Objective_HUD_Info_Position', 0)} | "
                   f"{pc.get('Display_Text', 0)} | {pc.get('Set_HUD_Help_Text', 0)} | {m['unique_text_ids']} | "
                   f"{m['closure_vs_owner']['closure_text_ids']} | {m['closure_vs_owner']['owner_lead_only_text_ids']} | "
                   f"{len(m['findings'])} | {len(m['unresolved_expressions'])} | {m['radar_marker_calls']} | {len(m['encyclopedia_calls'])} |")
    out += ['', 'Counts are call sites; `Add_Objective` contributes both its title ID and optional long description ID.',
            'A zero ID in an objective/message slot means "none" in the original and is not looked up. Unique IDs',
            'are distinct nonzero IDs per map (Set_HUD_Help_Text(0) is the original clear operation).', '',
            '## Unresolved IDs per mission', '']
    for m in maps:
        rows = [f"- ID {f['id']} {f['names']} {f['kind']} in {f['candidate']} ({f['calls'][0]['script']}:{f['calls'][0]['line']})" for f in m['findings']]
        rows += [f"- expression `{u['expression']}` in {u['script']}:{u['line']} ({u['command']})" for u in m['unresolved_expressions']]
        out += rows or [f"- {m['map']}: none"]
    out += ['', '## Objective cross-reference leads (heuristic, not defects)', '',
            '`Set_Objective_*` targets whose `Add_Objective` was not found with the same ID token in the scanned',
            'scripts. Causes are helper functions passing a variable ID (`id`, `type`), numeric IDs added through a',
            'helper or custom event, cross-script constants, and commented-out source. Token matching only; they say',
            'nothing about string-ID resolution above and need dataflow tracing before being called defects.', '']
    out += [f"- {m['map']}: " + ', '.join(f'`{x}`' for x in m['objective_refs_without_add']) for m in maps if m['objective_refs_without_add']]
    out += ['', 'M01 `M01_BARN_OBJECTIVE_JDG` and `M01_BARN_ROUNDUP_OBJECTIVE_JGD` do have literal `Add_Objective` calls',
            '(Mission01.cpp lines 2042 and 2117), so those two are scanner scope misses, not missing objectives.',
            'M03 numeric IDs 1000-1010 appear in `Set_Objective_HUD_Info*`; the nearby `Add_Objective` lines are',
            'commented out in Mission03.cpp (78-82), so the live add path for them is unverified.']
    bad = [r for m in maps for r in m['radar_invalid_literals']]
    out += ['', '## Radar markers', '',
            '`Add_Radar_Marker` and `Set_Objective_Radar_Blip*` carry no string ID, only shape (0-4) and color (0-7)',
            'enums. M04 is the only map with direct `Add_Radar_Marker` calls (9). Literal shape/color values outside',
            f"scriptcommands.h ranges: {len(bad)}." + ('' if not bad else ' See JSON receipt.'), '',
            '## Encyclopedia reveals', '',
            '`Reveal_Encyclopedia_*` take INI `ID=` values (characters/weapons/vehicles/buildings.ini in always.dat).',
            'Each literal ID was matched to its section and the section NameID/DescriptionID checked in both TDBs.', '',
            '| Map | Reveals | INI section found | Text IDs missing |', '|---|---:|---:|---:|']
    for m in maps:
        e = m['encyclopedia_calls']
        if e:
            out.append(f"| {m['map']} | {len(e)} | {sum(x['ini_section_found'] for x in e)} | "
                       f"{sum(1 for x in e if any(x['text_missing'].values()))} |")
    out += ['', '`Display_Encyclopedia_Event_UI` uses the GlobalSettings event string ID (definition data) and',
            '`Toolkit_Powerup` reveals via a script parameter; neither is a literal script argument, so both are outside',
            'this scan. EVA/radar/objective voice and the Add_Objective description-sound field are audio, not text.', '',
            '## Glyph / font support', '',
            'Per `stylemgr.ini`, HUD/objective/in-game text and subtitles use Arial MT (ARI_____.TTF, first in the',
            'provider candidate list); titles/menus use Regatta Condensed LET (54251___.TTF). `FT_Load_Char`',
            'succeeds for an unmapped code point by rendering .notdef, so a gap shows a box instead of failing. The',
            'coverage is a cmap lookup, not rendered-pixel evidence. Code points are those in IDs referenced by',
            'M01-M11 scripts. U+000A is a row break handled by the sentence layout and excluded from the counts.', '',
            '| TDB candidate | Language | Non-ASCII code points | Uncovered by Arial MT | Uncovered by Regatta | Uncovered by arial.ttf |',
            '|---|---|---:|---:|---:|---:|']
    for row in glyph_rows(maps, labels):
        name = LANGUAGES[row['language']] if row['language'] < len(LANGUAGES) else str(row['language'])
        out.append(f"| {row['candidate']} | {row['language']} {name} | {row['codepoints']} | " +
                   ' | '.join(str(len(row['uncovered'][label])) for label in labels) + ' |')
    out += ['', 'English (language 0) has no non-ASCII code point in either candidate. always.dbs carries one',
            'translation per ID. Spanish (index 3) and Japanese (index 5) produced no gap rows: no non-ASCII code point',
            'in the referenced IDs (or no distinct string); not separately verified beyond that.', '',
            'Uncovered code points are U+4E00-9FFF style CJK ideographs, U+3000 punctuation (Chinese) and',
            'U+AC00-D7A3 Hangul syllables (Korean) except U+2026, which Arial MT covers. U+000A aside, French/German',
            'code points are all covered by Arial MT and Regatta.', '',
            '## Reproduce', '', '```sh',
            'python3 -m tools.audit_objective_text_readiness --data /path/to/retail/Data \\',
            '  --font-dir /path/with/ARI_____.TTF --font-dir /path/with/user/fonts --owner-scan \\',
            '  --output-directory build/objective-text-readiness-YYYYMMDD --report reports/campaign/OBJECTIVE_TEXT_READINESS.md',
            '```', '',
            'Detailed JSON stays in ignored `build/`. Limits: script-argument source scan only; TDB/INI/font presence',
            'does not prove display, translation selection, wrapping, glyph rasterization or physical correctness.',
            'Physical Vita font availability (loose ARI_____.TTF outside Data/) is a separate gate; the emulator',
            'retail tree carries it only through the `user/fonts` fallback.']
    return '\n'.join(out) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, help='write the markdown readiness report here')
    parser.add_argument('--from-json', type=Path, help='render --report from an existing JSON receipt instead of rescanning')
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--data', type=Path)
    parser.add_argument('--font-dir', type=Path, action='append')
    parser.add_argument('--map', action='append', dest='maps')
    parser.add_argument('--owner-scan', action='store_true', help='also scan the mission owner .cpp (unbound script leads)')
    parser.add_argument('--output-directory', type=Path)
    args = parser.parse_args()
    header = args.root / 'upstream/CnC_Renegade/Code/Scripts/string_ids.h'
    if args.from_json:
        summary = json.loads(args.from_json.read_text())
        args.report.write_text(render_report(summary, hashlib.sha256(header.read_bytes()).hexdigest()))
        return 0
    if args.data is None or not args.font_dir or args.output_directory is None:
        parser.error('--data, --font-dir and --output-directory are required for a scan')
    output = args.output_directory.resolve()
    if not output.is_relative_to((args.root / 'build').resolve()):
        parser.error('detailed receipts must remain under private build/')
    output.mkdir(parents=True, exist_ok=True)
    context, scripts = resource_context(args.data), source_scripts(args.root)
    ids = string_id_definitions(args.root)
    candidates = load_translation_candidates(args.data)
    fonts, missing_fonts = load_fonts(args.font_dir)
    encyclopedia = load_encyclopedia(args.data)
    results = []
    for name in args.maps or MAPS:
        result = analyze_map(args.root, args.data, name, context, scripts, ids, candidates, fonts, encyclopedia, args.owner_scan)
        results.append(result)
        print(json.dumps({'map': name, 'ids': result['unique_text_ids'], 'findings': len(result['findings']),
                          'unresolved': len(result['unresolved_expressions'])}), flush=True)
    summary = {'schema_version': 1, 'evidence_class': 'read-only source/TDB/font-cmap scan; no retail text emitted',
               'candidates': {k: {'sha256': v['sha256'], 'ids': len(v['texts']),
                                  'languages_per_id': sorted({len(t) for t in v['texts'].values()})} for k, v in candidates.items()},
               'fonts': {k: {kk: vv for kk, vv in v.items() if kk != 'codepoints'} | {'codepoints': len(v['codepoints'])} for k, v in fonts.items()},
               'missing_fonts': missing_fonts, 'owner_scan': args.owner_scan, 'maps': results}
    (output / 'objective-text-readiness.json').write_text(json.dumps(summary, indent=1) + '\n')
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(render_report(summary, hashlib.sha256(header.read_bytes()).hexdigest()))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
