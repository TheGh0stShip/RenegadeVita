"""Static audit: script zones that gate progression and are thin enough for a
fast player to cross between two Think samples (Vita frame-rate tunnelling).

Read-only. Joins the original level zone records (`tools.audit_script_zones`)
with their persisted script bindings (`level_records`) and classifies the
Entered() body of each bound script in `staging/scripts`. Thickness is the
smallest full width (2 x extent) of the oriented box along its horizontal
local axes; it is a geometric bound, not a measured travel path.
"""
import argparse
from collections import defaultdict
import json
import math
from pathlib import Path
import re

from tools.audit_campaign_script_closure import ROOT, DEFAULT_DATA, scan_registrations
from tools.audit_cinematic_command_coverage import CAMPAIGN
from tools.audit_m13_level_owners import chunks, level_records
from tools.audit_mission_content_bindings import masked
from tools.audit_script_zones import scan
from tools.renegade_cinematic_dependency_scan import MixArchive

SCOPE = ['M00_Tutorial.mix'] + CAMPAIGN
# reports/campaign/CAMPAIGN_VEHICLES.md section 1 (drivable, not stationary).
PLAYER_VEHICLE_MAPS = {'M01.mix', 'M02.mix', 'M07.mix', 'M08.mix', 'M10.mix'}
THIN_LIMIT_M = 6.0          # 30 m/s x 0.2 s (TimeManager SLOWEST_FPS = 5)
ENTERED = re.compile(r'\bvoid\s+Entered\s*\(\s*GameObject\s*\*\s*\w+\s*,\s*GameObject\s*\*\s*\w+\s*\)\s*\{')
CLASSES = (
    ('mission_complete', re.compile(r'\bMission_Complete\s*\(')),
    ('objective', re.compile(r'\b(?:Add_Objective|Set_Objective_Status|Change_Objective_Type|'
                             r'Set_Objective_HUD_Info\w*|Set_Objective_Radar_Blip\w*)\s*\(')),
    ('cinematic', re.compile(r'Test_Cinematic|"[^"]*\.txt"|Cinematic', re.IGNORECASE)),
    ('custom_event', re.compile(r'\bSend_Custom_Event\s*\(')),
)
GATING = ('mission_complete', 'objective', 'cinematic', 'custom_event')


def entered_body(body):
    code = masked(body, strings=False)
    match = ENTERED.search(code)
    if not match:
        return None
    depth = 0
    for pos in range(match.end() - 1, len(code)):
        depth += (code[pos] == '{') - (code[pos] == '}')
        if depth == 0:
            return body[match.end():pos]
    return body[match.end():]


def classify(text):
    if text is None:
        return ['no_entered']
    found = [name for name, pattern in CLASSES if pattern.search(text)]
    return found or ['other']


def dimensions(row):
    basis = row['basis']
    extent = row['extent']
    horizontal, vertical = [], []
    for axis in range(3):
        column = (basis[axis], basis[3 + axis], basis[6 + axis])
        (vertical if abs(column[2]) >= 0.7 else horizontal).append(2.0 * extent[axis])
    thin = min(horizontal) if horizontal else min(2.0 * e for e in extent)
    return {'thin_horizontal_m': thin, 'long_horizontal_m': max(horizontal) if horizontal else thin,
            'height_m': max(vertical) if vertical else None,
            'thinnest_any_m': min(2.0 * e for e in extent)}


def audit(root, data, maps):
    registrations = scan_registrations(root / 'staging/scripts', set())
    by_name = defaultdict(list)
    for item in registrations:
        by_name[item['name'].lower()].append(item)
    report = {'maps': {}, 'thin_limit_m': THIN_LIMIT_M, 'evidence_class': 'static_authored_metadata'}
    for name in maps:
        archive = MixArchive(data / name)
        zones, scripts = [], defaultdict(list)
        for member in sorted(archive.entries):
            if not member.endswith(('.ldd', '.lsd')):
                continue
            payload = archive.read_binary(member)
            for record in level_records(chunks(payload))['script_records']:
                owner = record.get('owner')
                if owner:
                    scripts[owner['instance_id']].append(record)
            zones.extend({**row, 'member': member} for row in scan(payload))
        rows = []
        for zone in zones:
            bound = []
            for record in scripts.get(zone['instance_id'], []):
                sources = by_name.get(record['name'].lower(), [])
                text = entered_body(sources[0]['body']) if sources else None
                kinds = classify(text) if sources else ['unregistered']
                bound.append({'script': record['name'], 'parameters': record['parameters'],
                              'owner_file': sources[0]['owner'] if sources else None,
                              'classes': kinds,
                              'star_filter': bool(text and re.search(r'Is_A_Star|STAR', text))})
            classes = sorted({k for item in bound for k in item['classes']})
            gating = [k for k in GATING if k in classes]
            dims = dimensions(zone)
            rows.append({'instance_id': zone['instance_id'], 'definition_id': zone['definition_id'],
                         'center': [round(v, 2) for v in zone['center']], **{k: (round(v, 2) if v is not None else None)
                         for k, v in dims.items()}, 'scripts': bound, 'gating': gating,
                         'thin': dims['thin_horizontal_m'] < THIN_LIMIT_M,
                         'vehicle_mission': name in PLAYER_VEHICLE_MAPS})
        rows.sort(key=lambda row: row['thin_horizontal_m'])
        report['maps'][name] = {
            'zones': len(rows), 'with_scripts': sum(bool(r['scripts']) for r in rows),
            'gating': sum(bool(r['gating']) for r in rows),
            'gating_thin': sum(bool(r['gating']) and r['thin'] for r in rows),
            'gating_hard_thin': sum(bool(set(r['gating']) - {'custom_event'}) and r['thin'] for r in rows),
            'rows': rows}
    return report


def markdown(report):
    lines = ['| Map | Zones | Scripted | Gating (any) | Gating & thin < 6 m | Hard-gating & thin |',
             '| --- | ---: | ---: | ---: | ---: | ---: |']
    for name, item in report['maps'].items():
        lines.append(f"| {name} | {item['zones']} | {item['with_scripts']} | {item['gating']} | "
                     f"{item['gating_thin']} | {item['gating_hard_thin']} |")
    lines += ['', '| Map | Zone ID | Thin (m) | Long (m) | Height (m) | Player vehicles in map | Gating | Script(s) |',
              '| --- | ---: | ---: | ---: | ---: | --- | --- | --- |']
    for name, item in report['maps'].items():
        for row in item['rows']:
            if row['thin'] and row['gating']:
                scripts = ', '.join(f"`{s['script']}`" for s in row['scripts'])
                lines.append(f"| {name} | {row['instance_id']} | {row['thin_horizontal_m']:.2f} | "
                             f"{row['long_horizontal_m']:.2f} | {row['height_m'] if row['height_m'] is not None else '-'} | "
                             f"{'yes' if row['vehicle_mission'] else 'no'} | {'/'.join(row['gating'])} | {scripts} |")
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=DEFAULT_DATA)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--markdown', action='store_true')
    args = parser.parse_args()
    report = audit(ROOT, args.data, SCOPE)
    if args.output:
        if not args.output.resolve().is_relative_to((ROOT / 'build').resolve()):
            parser.error('detailed receipts must remain in private build/')
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    if args.markdown:
        print(markdown(report))
    else:
        for name, item in report['maps'].items():
            print(name, {k: v for k, v in item.items() if k != 'rows'})


if __name__ == '__main__':
    main()
