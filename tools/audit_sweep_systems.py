#!/usr/bin/env python3
"""S6 frontend denominator: every original Commando RC dialog declaration.

Resource and reference presence do not prove factory routing or display.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
from tools.audit_mission_content_bindings import masked
from tools.generate_wwui_dialog_templates import macros, CAMPAIGN_IDS, MULTIPLAYER_IDS

SYSTEM_OWNERS = {
    'innate_ai': ('combat/soldierobserver.cpp',),
    'actions': ('combat/action.cpp', 'combat/pathaction.cpp'),
    'pathfinding': ('wwphys/pathfind*.cpp', 'wwphys/path.cpp', 'wwphys/pathobject.cpp'),
    'vehicle_drivers': ('combat/vehicledriver.cpp',),
    'harvesters': ('combat/harvester*.cpp',),
    'base_defenses': ('scripts/toolkit.cpp', 'scripts/mission10.cpp'),
    'hibernation': ('combat/gameobjmanager.cpp', 'combat/smartgameobj.cpp'),
    'bosses': ('combat/*bossgameobj.cpp',),
    'petrova_scripts': ('scripts/mission11.cpp',),
    'vehicle_physics': ('wwphys/*vehicle*.cpp',),
    'elevators_doors_ladders': ('combat/elevator.cpp', 'combat/doors.cpp', 'combat/transition*.cpp'),
    'weapons_damage': ('combat/weapon*.cpp', 'combat/bullet.cpp', 'combat/damage.cpp', 'combat/explosion.cpp'),
    'c4_beacons': ('combat/c4.cpp', 'combat/beacon*.cpp'),
    'buildings_power_mct': ('combat/building*.cpp', 'combat/*factorygameobj.cpp', 'combat/airstripgameobj.cpp'),
    'cinematics': ('scripts/test_cinematic.cpp', 'combat/cinematicgameobj.cpp', 'combat/ccamera.cpp'),
    'conversations_visemes': ('combat/*conversation*.cpp', 'combat/viseme.cpp'),
    'hud_radar_objectives': ('combat/hud*.cpp', 'combat/radar.cpp', 'combat/objectives.cpp'),
    'audio': ('wwaudio/*.cpp',),
    'input': ('combat/directinput.cpp', 'combat/input.cpp'),
    'networking': ('wwnet/*.cpp', 'commando/cnetwork.cpp'),
    'filesystem': ('wwlib/*file*.cpp', 'wwlib/*mix*.cpp'),
    'threads_timers_memory': ('wwlib/*thread*.cpp', 'wwlib/*timer*.cpp', 'wwlib/*alloc*.cpp'),
    'game_modes': ('commando/*gamemode*.cpp', 'commando/gamemode.cpp'),
    'frontend': ('commando/dlg*.cpp', 'wwui/*.cpp'),
    'saves_campaign': ('commando/*save*.cpp', 'commando/campaign.cpp'),
    'encyclopedia_score_credits': ('combat/encyclopedia*.cpp', 'commando/*score*.cpp', 'commando/*credit*.cpp'),
    'movies': ('commando/movie.cpp', 'binkmovie/*.cpp'),
}


def system_owners(root, link):
    from fnmatch import fnmatchcase
    indexed = {r['source']: r for r in link.get('upstream_rows', [])}
    staged = {r['source']: r for r in link.get('rows', [])}
    rows = []
    directory = root / 'upstream/CnC_Renegade/Code'
    files = sorted(p for p in directory.rglob('*') if p.is_file() and p.suffix.lower() == '.cpp')
    for name, patterns in SYSTEM_OWNERS.items():
        matches = []
        missing = []
        for pattern in patterns:
            found = [p for p in files if fnmatchcase(p.relative_to(directory).as_posix().lower(), pattern)]
            if not found:
                missing.append(pattern)
            for path in found:
                source = path.relative_to(root).as_posix()
                candidates = indexed.get(source, {}).get('staged_candidates', [])
                matches.append({'source': source, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                                'link_inventory_source_key': source if source in indexed else None,
                                'staged_candidates': [
                                    {'source': candidate,
                                     'selected_for_arm_target': staged.get(candidate, {}).get('selected_for_target'),
                                     'map_mentions_object': staged.get(candidate, {}).get('map_mentions_object')}
                                    for candidate in candidates],
                                'matched_pattern': pattern})
        rows.append({'id': hashlib.sha256(name.encode()).hexdigest(), 'name': name,
                     'status': 'unknown', 'evidence_class': 'source_and_build_metadata',
                     'owner_candidates': matches, 'unmatched_owner_patterns': missing,
                     'acceptance_open': 'Caller/mode completeness, retained symbols, boundary behavior and runtime evidence'})
    return rows


def dialogs(code):
    clean = masked(code, strings=True)
    rows = []
    for match in re.finditer(r'^[ \t]*(\w+)[ \t]+DIALOG(?:EX)?\b[^\n]*', clean, re.M):
        rows.append({'name': match[1], 'line': clean.count('\n', 0, match.start()) + 1})
    return rows


def control_lock_references(code):
    clean = masked(code, strings=True)
    return [{'line': clean.count('\n', 0, match.start()) + 1,
             'column': match.start() - clean.rfind('\n', 0, match.start()),
             'commands_member_candidate': bool(re.search(r'Commands\s*->\s*$', clean[max(0, match.start()-80):match.start()]))}
            for match in re.finditer(r'\bControl_Enable\s*\(', clean)]


def control_locks(root, link):
    selected = {r['source'] for r in link.get('rows', []) if r['selected_for_target']}
    rows = []
    paths = list((root / 'staging').rglob('*')) + list((root / 'port').rglob('*'))
    for path in sorted(paths):
        if not path.is_file() or path.suffix.lower() not in ('.cpp', '.h', '.hpp', '.cc', '.cxx'):
            continue
        data = path.read_bytes()
        refs = control_lock_references(data.decode('latin1'))
        source = path.relative_to(root).as_posix()
        digest = hashlib.sha256(data).hexdigest()
        for ref in refs:
            rows.append(dict(ref, source=source, source_sha256=digest,
                             id=hashlib.sha256(f'{source}:{ref["line"]}:{ref["column"]}'.encode()).hexdigest(),
                             directly_selected_translation_unit=source in selected,
                             status='unknown', evidence_class='unpreprocessed_source_syntax',
                             acceptance_open='Resolve branch/caller, lock lifetime, restoration and controller/touch enforcement'))
    return rows


def inventory(root, template_path, link=None):
    link = link or {'rows': []}
    selected = {row['source'] for row in link['rows'] if row['selected_for_target']}
    original = root / 'upstream/CnC_Renegade/Code/Commando'
    ids = macros((original / 'resource.h', original / 'dialogresource.h'))
    template_bytes = template_path.read_bytes()
    present = {int(n) for n in re.findall(rb'static const unsigned char kDialog(\d+)\[\]', template_bytes)}
    references = {}
    for source in sorted((root / 'staging/commando').iterdir()):
        if source.suffix.lower() not in ('.cpp', '.h', '.hpp'):
            continue
        code = masked(source.read_text(encoding='latin1'), strings=True)
        for match in re.finditer(r'\bIDD_\w+\b', code):
            line_start = code.rfind('\n', 0, match.start()) + 1
            declaration = bool(re.match(r'[ \t]*#[ \t]*define[ \t]+$', code[line_start:match.start()]))
            references.setdefault(match[0], []).append(
                {'source': source.relative_to(root).as_posix(),
                 'line': code.count('\n', 0, match.start()) + 1,
                 'reference_kind': 'resource_definition' if declaration else 'source_use',
                 'source_selected_for_arm_target': source.relative_to(root).as_posix() in selected,
                 'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest()})
    rows, inputs = [], []
    for resource in sorted(original.glob('*.rc')):
        source = resource.relative_to(root).as_posix()
        inputs.append({'source': source, 'sha256': hashlib.sha256(resource.read_bytes()).hexdigest()})
        for declaration in dialogs(resource.read_text(encoding='latin1')):
            numeric = ids.get(declaration['name'])
            rows.append(dict(declaration, id=hashlib.sha256(
                f'{source}:{declaration["line"]}:{declaration["name"]}'.encode()).hexdigest(),
                source=source, resource_id=numeric,
                selected_by_full_port_generator=numeric in CAMPAIGN_IDS | MULTIPLAYER_IDS,
                present_in_retained_templates=numeric in present,
                source_reference_candidates=references.get(declaration['name'], []),
                selected_source_use_candidates=[ref for ref in references.get(declaration['name'], [])
                    if ref['reference_kind'] == 'source_use' and ref['source_selected_for_arm_target']],
                status='unknown', evidence_class='source_and_generated_resource_metadata'))
    return {'schema': 1, 'sweep': 'S6', 'complete': False,
            'scope': 'All original Commando/*.rc dialog declarations; staged Commando token references',
            'inputs': inputs, 'template_sha256': hashlib.sha256(template_bytes).hexdigest(),
            'total': len(rows), 'counts': {'unknown': len(rows)},
            'present_in_retained_templates': sum(r['present_in_retained_templates'] for r in rows),
            'absent_from_retained_templates': sum(not r['present_in_retained_templates'] for r in rows),
            'open_risks': ['Conditional resource branches and duplicate declarations',
                           'Dynamic/numeric resource routing and other source directories',
                           'Alternate resource providers', 'Controls/styles and factory callback behavior',
                           'Owner patterns are candidate coverage, not complete caller or class closure',
                           'Platform replacement/provider paths and all Control_Enable locks'],
            'system_rows': system_owners(root, link),
            'control_lock_rows': control_locks(root, link),
            'control_lock_scope': 'Every Control_Enable(...) token occurrence in staged and port C++/headers, including declarations and inactive branches; header inclusion and runtime execution not inferred',
            'rows': rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--templates', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--link-inventory', type=Path, required=True)
    args = parser.parse_args()
    link_bytes = args.link_inventory.read_bytes()
    result = inventory(Path(__file__).resolve().parents[1], args.templates, json.loads(link_bytes))
    result['link_inventory_sha256'] = hashlib.sha256(link_bytes).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({key: result[key] for key in ('total', 'present_in_retained_templates', 'absent_from_retained_templates')}))


if __name__ == '__main__':
    main()
