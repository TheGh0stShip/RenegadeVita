#!/usr/bin/env python3
"""Inventory performance ledger records and required unmeasured budget gates."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

LEDGER = 'reports/PERFORMANCE_HYPOTHESIS_LEDGER.md'
OWNERS = {
    'synchronous_asset_loads': ['ww3d2/assetmgr.cpp', 'ww3d2/textureloader.cpp'],
    'per_frame_allocation': ['ww3d2/mesh.cpp', 'Combat/gameobjmanager.cpp'],
    'pathfind_solves': ['wwphys/Pathfind.cpp'],
    'visibility_culling': ['wwphys/pscene_vis.cpp', 'wwphys/pscene.cpp'],
    'sorting': ['ww3d2/sortingrenderer.cpp'],
    'particles': ['ww3d2/part_emt.cpp'],
    'audio_decode': ['WWAudio/SoundBuffer.cpp', 'WWAudio/WWAudio.cpp'],
    'lock_contention': ['WWAudio/Threads.cpp', 'wwlib/thread.cpp'],
    'first_frame_long_load': ['Commando/gamemode.cpp', 'ww3d2/assetmgr.cpp'],
}
BUDGETS = ('available_app_cores_and_actual_clock', 'user_ram_free_and_high_water',
           'cdram_free_and_high_water', 'draw_calls_at_960x544',
           'frame_time_median_p95_p99_worst')


def records(text):
    """Retain every section and table data row; do not infer measurement class."""
    lines = text.splitlines()
    result = []
    heading = None
    for index, line in enumerate(lines):
        if re.match(r'^#{1,6}\s+', line):
            heading = line.lstrip('#').strip()
            end = next((j for j in range(index + 1, len(lines))
                        if re.match(r'^#{1,6}\s+', lines[j])), len(lines))
            block = '\n'.join(lines[index:end])
            result.append({'kind': 'ledger_section', 'label': heading,
                           'line': index + 1, 'end_line': end,
                           'content_sha256': hashlib.sha256(block.encode()).hexdigest()})
        elif line.startswith('|') and index and lines[index - 1].startswith('|'):
            cells = line.strip('|').split('|')
            if all(re.fullmatch(r'\s*:?-+:?\s*', c) for c in cells):
                continue
            # A table header is followed by a separator; never count it as data.
            if index + 1 < len(lines) and re.match(r'^\|\s*:?-+', lines[index + 1]):
                continue
            result.append({'kind': 'ledger_table_row', 'label': cells[0].strip(),
                           'section': heading, 'line': index + 1,
                           'content_sha256': hashlib.sha256(line.encode()).hexdigest()})
    return result


def inventory(root):
    ledger = root / LEDGER
    rows = records(ledger.read_text())
    for row in rows:
        row['source'] = LEDGER
        row['evidence_class'] = 'historical_report_metadata'
        row['measurement_verification'] = 'matching raw artifacts not reconciled by this inventory'
    for name, owners in OWNERS.items():
        candidates = []
        for owner in owners:
            path = root / 'upstream/CnC_Renegade/Code' / owner
            candidates.append({'source': path.relative_to(root).as_posix(),
                               'exists': path.is_file(),
                               'sha256': hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None})
        rows.append({'kind': 'required_cost_family', 'label': name,
                     'original_owner_candidates': candidates,
                     'evidence_class': 'source_metadata', 'measurement': None})
    probes = []
    for source in ('port/platform/vita/a30_main.cpp', 'port/renderer/vita/ww3d_vita_renderer.cpp'):
        path = root / source
        data = path.read_bytes()
        for line, text in enumerate(data.decode().splitlines(), 1):
            for token in ('scePowerSetArmClockFrequency', 'sceKernelGetFreeMemorySize', 'vglMemFree'):
                if token in text:
                    probes.append({'source': source, 'line': line, 'token': token,
                                   'sha256': hashlib.sha256(data).hexdigest()})
    for budget in BUDGETS:
        rows.append({'kind': 'required_budget_gate', 'label': budget,
                     'evidence_class': 'required_physical_measurement', 'measurement': None})
    for row in rows:
        key = f"{row['kind']}:{row.get('source', '')}:{row.get('line', '')}:{row['label']}"
        row['id'] = hashlib.sha256(key.encode()).hexdigest()
        row['status'] = 'unknown'
    return {'schema': 1, 'sweep': 'S7', 'complete': False, 'total': len(rows),
            'counts': {'unknown': len(rows)}, 'kind_counts': dict(sorted(Counter(r['kind'] for r in rows).items())),
            'rows': rows, 'ledger_sha256': hashlib.sha256(ledger.read_bytes()).hexdigest(),
            'budget_instrumentation_candidates': probes,
            'profiling_priorities': [
                {'rank': 1, 'map': 'M05', 'scenario': 'town square'},
                {'rank': 2, 'map': 'M10', 'scenario': 'open base'},
                {'rank': 3, 'map': 'M06', 'scenario': 'collapse'},
                {'rank': 4, 'map': 'M08', 'scenario': 'canyon'}],
            'priority_basis': 'provisional workload coverage; not measured cost ranking',
            'scope': 'Every ledger heading and table data row plus required cost families and physical budget gates',
            'open_risks': ['Historical reports require matching raw artifact verification',
                           'Costs documented outside this ledger and undocumented costs',
                           'Owner candidates are not causal attribution or caller closure',
                           'No current fixed-route physical memory or frame-time measurements',
                           'Ledger records can overlap and do not count unique defects']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = inventory(Path(__file__).resolve().parents[1])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result['kind_counts']))


if __name__ == '__main__':
    main()
