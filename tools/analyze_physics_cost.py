#!/usr/bin/env python3
"""Summarise Combat/physics cost windows from a Vita runtime log.

TUT-R1 PHYSICS_COLLISION_COST.  Turns the existing checkpoint telemetry into
per-window figures for a fixed route (the tutorial: Logan, Sydney, Gunner
range, Mobius, HMVV, base buildings) and compares two runs for hardware A/B:

* ``A4 campaign pacing`` (cumulative stage averages) -> windowed Combat,
  network and control cost.  Cumulative averages are integer-truncated, so a
  derived window carries up to ``frames/window`` microseconds of error; the
  exact windowed ``combat_avg_us`` of ``A4 combat casts`` (dev240+) replaces
  it whenever both lines share a checkpoint.
* ``A4 combat casts`` -> scene casts per frame (culled vs collision region)
  and awake/hibernating soldiers per frame.
* ``A3.5 perf`` -> rolling frame-time percentiles and sim/render split.
* ``A3.6 vis-census`` -> PVS sector status and the census's own cost.
* ``A3.6 frame-profile`` -> physics/collision scopes among the top scopes.

Reads logs only; prints nothing from the log except these numeric fields.
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from pathlib import Path

PACING_RE = re.compile(
    r'A4 campaign pacing: frames=(\d+) avg_us '
    r'time/input/path/control/network/combat/other='
    r'(\d+)/(\d+)/(\d+)/(\d+)/(\d+)/(\d+)/(\d+)')
CASTS_RE = re.compile(
    r'A4 combat casts: frames=(\d+) window=(\d+) combat_avg_us=(\d+) '
    r'soldiers_awake/hibernating_per_frame=([\d.]+)/([\d.]+) per_frame '
    r'ray_cull/ray_region/aabox_cull/aabox_region/obbox_cull/obbox_region='
    r'([\d.]+)/([\d.]+)/([\d.]+)/([\d.]+)/([\d.]+)/([\d.]+)')
PERF_RE = re.compile(
    r'A3\.5 perf: frames=(\d+) rolling_samples=(\d+) avg_fps=([\d.]+) '
    r'frame_us min/p50/p95/p99/max=(\d+)/(\d+)/(\d+)/(\d+)/(\d+) '
    r'.*?stage_us sync/sim/render=(\d+)/(\d+)/(\d+)')
CENSUS_RE = re.compile(
    r'A3\.6 vis-census: frame=(\d+) vis_enabled=(-?\d+) inverted=(-?\d+) '
    r'sector=(-?\d+) missing=(-?\d+) fallback=(-?\d+) pvs_true=(-?\d+)/(-?\d+) '
    r'static total/ws/in_frustum/pvs_hidden/vis_saved/collected='
    r'(\d+)/(\d+)/(\d+)/(\d+)/(\d+)/(\d+) '
    r'dynamic total/in_frustum/pvs_hidden/vis_saved/collected='
    r'(\d+)/(\d+)/(\d+)/(\d+)/(\d+) census_us=(\d+)')
PROFILE_RE = re.compile(
    r'A3\.6 frame-profile: version=(\d+) window=(\d+) frames=(\d+) avg_frame_us=(\d+) '
    r'.*?top avg_us/calls_per_frame:(.*)$')
PROFILE_TOKEN_RE = re.compile(r'(\S+)=(\d+)/([\d.]+)')

CAST_KINDS = ('ray_cull', 'ray_region', 'aabox_cull', 'aabox_region',
              'obbox_cull', 'obbox_region')
STAGES = ('time', 'input', 'path', 'control', 'network', 'combat', 'other')
# Engine WWPROFILE names after the profiler's space/'='/'/' -> '_' mapping.
PHYSICS_SCOPE_RE = re.compile(
    r'Phys|Timestep|Cast|Collide|Collision|^Scene$|Dazzle|Ground|Spring|Sweep|'
    r'Target|Bullet|^Camera|Collect|Vehicle|Wheel|RigidBody|Rbody|Human|See$|Raycast')


def _percentile(values, fraction):
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round(fraction * (len(ordered) - 1)))))
    return ordered[index]


def _median(values):
    return statistics.median(values) if values else None


def parse_log(text: str) -> dict:
    """Collect the checkpoint records of one log, in order of appearance."""
    pacing, casts, perf, census, profile = [], [], [], [], []
    for raw in text.splitlines():
        match = PACING_RE.search(raw)
        if match:
            values = [int(v) for v in match.groups()]
            pacing.append({'frames': values[0], **dict(zip(STAGES, values[1:]))})
            continue
        match = CASTS_RE.search(raw)
        if match:
            values = match.groups()
            casts.append({'frames': int(values[0]), 'window': int(values[1]),
                          'combat_avg_us': int(values[2]),
                          'awake': float(values[3]), 'hibernating': float(values[4]),
                          **{kind: float(v) for kind, v in zip(CAST_KINDS, values[5:])}})
            continue
        match = PERF_RE.search(raw)
        if match:
            values = match.groups()
            record = {'frames': int(values[0]), 'samples': int(values[1]),
                      'avg_fps': float(values[2]),
                      'min': int(values[3]), 'p50': int(values[4]), 'p95': int(values[5]),
                      'p99': int(values[6]), 'max': int(values[7]),
                      'sync_us': int(values[8]), 'sim_us': int(values[9]),
                      'render_us': int(values[10])}
            # The runtime prints the same checkpoint perf line twice.
            if not perf or perf[-1] != record:
                perf.append(record)
            continue
        match = CENSUS_RE.search(raw)
        if match:
            v = [int(x) for x in match.groups()]
            census.append({'frame': v[0], 'vis_enabled': v[1], 'sector': v[3],
                           'missing': v[4], 'pvs_true': v[6], 'pvs_bits': v[7],
                           'static_total': v[8], 'static_in_frustum': v[10],
                           'static_pvs_hidden': v[11],
                           'dynamic_total': v[14], 'dynamic_in_frustum': v[15],
                           'dynamic_pvs_hidden': v[16], 'census_us': v[19]})
            continue
        match = PROFILE_RE.search(raw)
        if match:
            scopes = {name: {'avg_us': int(us), 'calls': float(calls)}
                      for name, us, calls in PROFILE_TOKEN_RE.findall(match.group(5))}
            profile.append({'window': int(match.group(2)), 'frames': int(match.group(3)),
                            'avg_frame_us': int(match.group(4)), 'scopes': scopes})
    return {'pacing': pacing, 'casts': casts, 'perf': perf, 'census': census,
            'profile': profile}


def pacing_windows(pacing: list[dict]) -> list[dict]:
    """Difference consecutive cumulative pacing lines into windows.

    A drop in ``frames`` starts a new session (new process or reset totals);
    its first line is then a window from zero.
    """
    windows = []
    previous = None
    session = 0
    for record in pacing:
        if previous is not None and record['frames'] <= previous['frames']:
            session += 1
            previous = None
        base_frames = previous['frames'] if previous else 0
        span = record['frames'] - base_frames
        if span <= 0:
            previous = record
            continue
        window = {'session': session, 'start': base_frames, 'end': record['frames'],
                  'frames': span, 'exact': False}
        for stage in STAGES:
            total = record[stage] * record['frames']
            prior = previous[stage] * previous['frames'] if previous else 0
            window[stage + '_us'] = max(0, round((total - prior) / span))
        windows.append(window)
        previous = record
    return windows


def merge_windows(parsed: dict) -> list[dict]:
    """Attach exact casts/perf figures to pacing windows by checkpoint frame."""
    windows = pacing_windows(parsed['pacing'])
    casts = {}
    for record in parsed['casts']:
        casts.setdefault(record['frames'], record)
    perf = {}
    for record in parsed['perf']:
        perf.setdefault(record['frames'], record)
    for window in windows:
        cast = casts.get(window['end'])
        if cast is not None and cast['window'] == window['frames']:
            window['combat_us'] = cast['combat_avg_us']
            window['exact'] = True
        if cast is not None:
            window['awake'] = cast['awake']
            window['hibernating'] = cast['hibernating']
            window['casts'] = {kind: cast[kind] for kind in CAST_KINDS}
            window['casts_per_frame'] = round(sum(cast[kind] for kind in CAST_KINDS), 1)
        record = perf.get(window['end'])
        if record is not None:
            window.update({'p50': record['p50'], 'p95': record['p95'], 'p99': record['p99'],
                           'avg_fps': record['avg_fps'], 'render_us': record['render_us'],
                           'sim_us': record['sim_us']})
    return windows


def find_bursts(windows: list[dict], threshold_us: int) -> list[dict]:
    """Merge consecutive windows whose Combat cost reaches the threshold."""
    bursts = []
    current = None
    for window in windows:
        hot = window['combat_us'] >= threshold_us
        if hot and current is not None and current['session'] == window['session'] \
                and current['end'] == window['start']:
            current['end'] = window['end']
            current['windows'] += 1
            current['peak_combat_us'] = max(current['peak_combat_us'], window['combat_us'])
            continue
        if hot:
            current = {'session': window['session'], 'start': window['start'],
                       'end': window['end'], 'windows': 1,
                       'peak_combat_us': window['combat_us']}
            bursts.append(current)
        else:
            current = None
    return bursts


def summarise(parsed: dict, burst_us: int = 8000) -> dict:
    windows = merge_windows(parsed)
    combat = [w['combat_us'] for w in windows]
    network = [w['network_us'] for w in windows]
    frame_us = [1e6 / w['avg_fps'] for w in windows if w.get('avg_fps')]
    summary = {
        'windows': len(windows),
        'exact_combat_windows': sum(1 for w in windows if w['exact']),
        'combat_us': {'median': _median(combat), 'p90': _percentile(combat, 0.9),
                      'max': max(combat) if combat else None},
        'network_us': {'median': _median(network), 'max': max(network) if network else None},
        'frame_us_median': round(_median(frame_us)) if frame_us else None,
        'bursts': find_bursts(windows, burst_us),
        'burst_threshold_us': burst_us,
    }
    if summary['frame_us_median'] and summary['combat_us']['median'] is not None:
        summary['combat_share_of_frame'] = round(
            summary['combat_us']['median'] / summary['frame_us_median'], 3)
    cast_windows = [w for w in windows if 'casts' in w]
    if cast_windows:
        summary['casts_per_frame'] = {
            kind: _median([w['casts'][kind] for w in cast_windows]) for kind in CAST_KINDS}
        summary['casts_per_frame']['total_max'] = max(w['casts_per_frame'] for w in cast_windows)
        summary['soldiers_per_frame'] = {
            'awake_median': _median([w['awake'] for w in cast_windows]),
            'hibernating_median': _median([w['hibernating'] for w in cast_windows])}
    if parsed['census']:
        census = parsed['census']
        summary['vis_census'] = {
            'samples': len(census),
            'sector_missing_fraction': round(sum(c['missing'] for c in census) / len(census), 3),
            'dynamic_pvs_hidden_median': _median([c['dynamic_pvs_hidden'] for c in census]),
            'dynamic_total_median': _median([c['dynamic_total'] for c in census]),
            'census_us_median': _median([c['census_us'] for c in census]),
            'census_us_max': max(c['census_us'] for c in census)}
    scopes: dict[str, list[dict]] = {}
    for record in parsed['profile']:
        for name, value in record['scopes'].items():
            if PHYSICS_SCOPE_RE.search(name):
                scopes.setdefault(name, []).append(value)
    if scopes:
        summary['profile_scopes'] = {
            name: {'windows': len(values),
                   'avg_us_median': _median([v['avg_us'] for v in values]),
                   'avg_us_max': max(v['avg_us'] for v in values),
                   'calls_median': _median([v['calls'] for v in values])}
            for name, values in sorted(scopes.items())}
    summary['window_rows'] = windows
    return summary


def compare(a: dict, b: dict) -> dict:
    """Median deltas (B - A) for the headline metrics of two summaries."""
    def pick(summary, *path):
        value = summary
        for key in path:
            if not isinstance(value, dict) or key not in value:
                return None
            value = value[key]
        return value

    rows = {}
    for label, path in (('combat_us_median', ('combat_us', 'median')),
                        ('combat_us_p90', ('combat_us', 'p90')),
                        ('combat_us_max', ('combat_us', 'max')),
                        ('network_us_median', ('network_us', 'median')),
                        ('frame_us_median', ('frame_us_median',)),
                        ('awake_median', ('soldiers_per_frame', 'awake_median')),
                        ('ray_cull_median', ('casts_per_frame', 'ray_cull')),
                        ('aabox_cull_median', ('casts_per_frame', 'aabox_cull')),
                        ('obbox_cull_median', ('casts_per_frame', 'obbox_cull'))):
        left, right = pick(a, *path), pick(b, *path)
        delta = right - left if left is not None and right is not None else None
        rows[label] = {'a': left, 'b': right, 'delta': delta}
    rows['bursts'] = {'a': len(a['bursts']), 'b': len(b['bursts']),
                      'delta': len(b['bursts']) - len(a['bursts'])}
    return rows


def format_summary(summary: dict, label: str) -> str:
    lines = [f'== {label}: windows={summary["windows"]} '
             f'exact_combat={summary["exact_combat_windows"]} '
             f'frame_us_median={summary["frame_us_median"]}']
    combat = summary['combat_us']
    lines.append(f'combat_us median/p90/max={combat["median"]}/{combat["p90"]}/{combat["max"]} '
                 f'share_of_frame={summary.get("combat_share_of_frame")} '
                 f'network_us median={summary["network_us"]["median"]}')
    if 'casts_per_frame' in summary:
        casts = summary['casts_per_frame']
        lines.append('casts/frame median ' + ' '.join(
            f'{kind}={casts[kind]}' for kind in CAST_KINDS) + f' total_max={casts["total_max"]}')
        soldiers = summary['soldiers_per_frame']
        lines.append(f'soldiers/frame awake={soldiers["awake_median"]} '
                     f'hibernating={soldiers["hibernating_median"]}')
    if 'vis_census' in summary:
        census = summary['vis_census']
        lines.append('vis-census ' + ' '.join(f'{k}={v}' for k, v in census.items()))
    for name, value in summary.get('profile_scopes', {}).items():
        lines.append(f'scope {name} avg_us median/max={value["avg_us_median"]}/'
                     f'{value["avg_us_max"]} calls={value["calls_median"]} '
                     f'windows={value["windows"]}')
    lines.append(f'bursts (combat_us >= {summary["burst_threshold_us"]}): {len(summary["bursts"])}')
    for burst in summary['bursts']:
        lines.append(f'  session={burst["session"]} frames={burst["start"]}..{burst["end"]} '
                     f'windows={burst["windows"]} peak_combat_us={burst["peak_combat_us"]}')
    return '\n'.join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('log', type=Path)
    parser.add_argument('--compare', type=Path, help='second log (B) for an A/B delta')
    parser.add_argument('--burst-us', type=int, default=8000,
                        help='windowed Combat cost that counts as a burst (default 8000)')
    parser.add_argument('--windows', action='store_true', help='include per-window rows')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args(argv)

    def load(path):
        summary = summarise(parse_log(path.read_text(encoding='utf-8', errors='replace')),
                            args.burst_us)
        if not args.windows:
            summary.pop('window_rows')
        return summary

    a = load(args.log)
    result = {'a': a}
    if args.compare:
        result['b'] = load(args.compare)
        result['delta'] = compare(a, result['b'])
    if args.json:
        print(json.dumps(result, indent=2))
        return 0
    print(format_summary(a, 'A ' + args.log.name))
    if args.compare:
        print(format_summary(result['b'], 'B ' + args.compare.name))
        print('== delta (B - A)')
        for label, row in result['delta'].items():
            print(f'{label}: {row["a"]} -> {row["b"]} delta={row["delta"]}')
    if args.windows:
        for row in a['window_rows']:
            print(json.dumps(row, sort_keys=True))
    return 0


if __name__ == '__main__':
    sys.exit(main())
