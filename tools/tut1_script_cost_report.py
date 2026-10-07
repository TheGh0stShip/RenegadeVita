#!/usr/bin/env python3
"""Summarise script-layer cost from a Vita runtime log (TUT-R1-03, RVSC1).

Reads only numeric telemetry lines that the runtime already writes:

* ``A4 mission object summary`` - object census at level load;
* ``A4 combat casts`` - per-window CombatManager::Think average (dev240+);
* ``A4 campaign pacing`` - cumulative stage averages (older logs; window
  values are reconstructed from the deltas and carry up to
  ``frames / window`` microseconds of integer-truncation error);
* ``A3.5 perf`` - per-window sim/render stage averages;
* ``A3.6 script-cost`` - the RVSC1 watch line (script-cost-v1.flag =
  ``RVSC1 1``), named original WWPROFILE scopes whatever their rank;
* ``A3.6 frame-profile: version=2`` - top scopes, used for the rank bound
  when no watch line is present.

Script layer = ``ScriptZone Think`` (inclusive of Star/All Enter and the
Entered/Exited callbacks) + ``Scriptable PostThink`` (observer/custom timer
expiry and the Timer_Expired/Custom callbacks they dispatch) + the RVSC1
scopes ``Conversation Think``, ``Objective Update`` and ``Spawn Update``.
These five do not nest in each other. ``See`` (the original Enemy_Seen
perception scan) is reported separately; it is AI perception, not script
code. Inclusive scope times also contain the profiler's own overhead for
nested scopes.

No log text is copied into the output, only numbers. Never claims a gain.
"""
import argparse
import json
import re
import statistics
import sys

OBJECT_SUMMARY = re.compile(r'A4 mission object summary: phase=(\S+) (.*)$')
COMBAT_CASTS = re.compile(r'A4 combat casts: frames=(\d+) window=(\d+) combat_avg_us=(\d+)')
PACING = re.compile(
    r'A4 campaign pacing: frames=(\d+) avg_us '
    r'time/input/path/control/network/combat/other=(\d+)/(\d+)/(\d+)/(\d+)/(\d+)/(\d+)/(\d+)')
PERF = re.compile(r'A3\.5 perf: frames=(\d+) .*?stage_us sync/sim/render=(\d+)/(\d+)/(\d+)')
SCRIPT_COST = re.compile(r'A3\.6 script-cost: version=1 window=(\d+) frames=(\d+) '
                         r'avg_frame_us=(\d+) inclusive=1 avg_us/calls_per_frame:(.*)$')
FRAME_PROFILE = re.compile(r'A3\.6 frame-profile: version=2 window=(\d+) frames=(\d+) '
                           r'avg_frame_us=(\d+) .*? top avg_us/calls_per_frame:(.*)$')
SCOPE = re.compile(r'(\S+)=(\d+)/(\d+(?:\.\d+)?)')
PACING_FIELDS = ('time', 'input', 'path', 'control', 'network', 'combat', 'other')

ORIGINAL_SCRIPT_SCOPES = ('ScriptZone_Think', 'Scriptable_PostThink')
SCRIPT_LAYER_SCOPES = ORIGINAL_SCRIPT_SCOPES + ('Conversation_Think', 'Objective_Update',
                                                'Spawn_Update')


def _scopes(text):
    return {name: (int(us), float(calls)) for name, us, calls in SCOPE.findall(text)}


def parse_object_summaries(lines):
    result = []
    for line in lines:
        match = OBJECT_SUMMARY.search(line)
        if match:
            fields = dict(re.findall(r'(\w+)=(\d+)', match.group(2)))
            result.append({'phase': match.group(1),
                           **{key: int(value) for key, value in fields.items()}})
    return result


def parse_combat_windows(lines):
    """Window CombatManager::Think averages in microseconds per frame."""
    windows = [int(m.group(3)) for m in map(COMBAT_CASTS.search, lines) if m]
    if windows:
        return windows, 'combat_casts'
    return [w['combat'] for w in parse_pacing_windows(lines)], 'pacing_delta'


def parse_pacing_windows(lines):
    """Reconstruct per-window stage averages from cumulative pacing lines.

    A frame count that does not increase starts a new session (repeated
    flushes of the same line are ignored, a restart resets the baseline).
    """
    windows = []
    previous = None
    for line in lines:
        match = PACING.search(line)
        if not match:
            continue
        frames = int(match.group(1))
        values = [int(match.group(index)) for index in range(2, 9)]
        if previous is not None and frames == previous[0]:
            continue
        if previous is None or frames < previous[0]:
            previous = (frames, values)
            continue
        span = frames - previous[0]
        window = {'start': previous[0], 'end': frames}
        for index, field in enumerate(PACING_FIELDS):
            window[field] = (values[index] * frames - previous[1][index] * previous[0]) / span
        windows.append(window)
        previous = (frames, values)
    return windows


def parse_perf_windows(lines):
    seen = set()
    windows = []
    for match in map(PERF.search, lines):
        if not match:
            continue
        key = tuple(int(match.group(index)) for index in range(1, 5))
        if key in seen:
            continue
        seen.add(key)
        windows.append({'frames': key[0], 'sim_us': key[2], 'render_us': key[3]})
    return windows


def parse_script_cost_windows(lines):
    windows = []
    for match in map(SCRIPT_COST.search, lines):
        if match:
            windows.append({'window': int(match.group(1)),
                            'avg_frame_us': int(match.group(3)),
                            'scopes': _scopes(match.group(4))})
    return windows


def parse_frame_profile_windows(lines):
    windows = []
    for match in map(FRAME_PROFILE.search, lines):
        if match:
            windows.append({'window': int(match.group(1)),
                            'avg_frame_us': int(match.group(3)),
                            'scopes': _scopes(match.group(4))})
    return windows


def _distribution(values):
    values = sorted(values)
    if not values:
        return None
    p95 = values[min(len(values) - 1, int(round(0.95 * (len(values) - 1))))]
    return {'n': len(values), 'median': statistics.median(values), 'p95': p95,
            'max': values[-1]}


def summarize(lines):
    summary = {'object_summaries': parse_object_summaries(lines)}
    combat, combat_source = parse_combat_windows(lines)
    summary['combat_us_per_frame'] = _distribution(combat)
    summary['combat_source'] = combat_source
    perf = parse_perf_windows(lines)
    summary['sim_us_per_frame'] = _distribution([w['sim_us'] for w in perf])
    summary['render_us_per_frame'] = _distribution([w['render_us'] for w in perf])

    watch = parse_script_cost_windows(lines)
    summary['script_cost_windows'] = len(watch)
    if watch:
        per_scope = {}
        layer = []
        layer_share_frame = []
        layer_share_combat = []
        for window in watch:
            scopes = window['scopes']
            for name, (us, calls) in scopes.items():
                per_scope.setdefault(name, {'us': [], 'calls': []})
                per_scope[name]['us'].append(us)
                per_scope[name]['calls'].append(calls)
            script_us = sum(scopes.get(name, (0, 0.0))[0] for name in SCRIPT_LAYER_SCOPES)
            layer.append(script_us)
            if window['avg_frame_us'] > 0:
                layer_share_frame.append(script_us / window['avg_frame_us'])
            combat_us = scopes.get('CombatManager_Think', (0, 0.0))[0]
            if combat_us > 0:
                layer_share_combat.append(script_us / combat_us)
        summary['scopes'] = {
            name: {'us_per_frame': _distribution(values['us']),
                   'calls_per_frame_median': statistics.median(values['calls'])}
            for name, values in sorted(per_scope.items())}
        summary['script_layer_us_per_frame'] = _distribution(layer)
        summary['script_layer_share_of_frame'] = _distribution(layer_share_frame)
        summary['script_layer_share_of_combat'] = _distribution(layer_share_combat)
    else:
        # Without the watch line an original scope absent from the top list
        # is bounded by the smallest listed scope of that window. The RVSC1
        # scopes do not exist then, so conversations, objectives and spawners
        # stay unmeasured (inside CombatManager Think only).
        bounds = []
        for window in parse_frame_profile_windows(lines):
            scopes = window['scopes']
            if not scopes:
                continue
            listed = {name: us for name, (us, _calls) in scopes.items()}
            smallest = min(listed.values())
            bounds.append(sum(listed.get(name, smallest) for name in ORIGINAL_SCRIPT_SCOPES))
        summary['original_script_scopes_upper_bound_us_per_frame'] = _distribution(bounds)
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('logs', nargs='+', help='runtime log files (read only)')
    parser.add_argument('--json', help='write the summary JSON here')
    args = parser.parse_args(argv)
    result = {}
    for path in args.logs:
        with open(path, errors='replace') as handle:
            result[path] = summarize(handle.read().splitlines())
    text = json.dumps(result, indent=2, sort_keys=True)
    if args.json:
        with open(args.json, 'w') as handle:
            handle.write(text + '\n')
    else:
        sys.stdout.write(text + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
