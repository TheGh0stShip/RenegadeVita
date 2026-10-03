#!/usr/bin/env python3
"""Validate bounded lookup observations; counts never prove mission correctness.

Also accepts a load-only flight summary. It does not validate frame timing,
establish physical provenance, or replace the strict flight-bundle validator.
Detailed names stay in private build/ output; stdout contains counts only.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

KINDS = ('script_factory', 'object', 'conversation_name', 'text_file_available')
PHASES = ('level_load', 'gameplay')
ROOT = Path(__file__).resolve().parents[1]
MAX_UINT32 = (1 << 32) - 1


def uint32(value, field):
    if type(value) is not int or not 0 <= value <= MAX_UINT32:
        raise ValueError(f'{field}: expected uint32')
    return value


def boolean(value, field):
    if type(value) is not bool:
        raise ValueError(f'{field}: expected boolean')
    return value


def context(phase, frame):
    uint32(frame, 'frame')
    if phase not in PHASES or (phase == 'level_load' and frame != 0) or (
            phase == 'gameplay' and frame == 0):
        raise ValueError('invalid lookup phase/frame context')
    return PHASES.index(phase), frame


def analyze_lookups(summary: dict, *, expected_candidate: str, archive: str) -> dict:
    if not isinstance(summary, dict) or summary.get('candidate') != expected_candidate:
        raise ValueError('lookup summary candidate mismatch')
    if not isinstance(summary.get('archive'), str) or summary['archive'].lower() != archive.lower():
        raise ValueError('lookup summary archive mismatch')
    report = {'schema_version': 1, 'candidate': expected_candidate, 'archive': archive,
              'evidence_class': 'lookup metadata; physical provenance unverified',
              'status': 'not_recorded', 'kinds': [],
              'limits': ['Absent lookups are observations, not confirmed port defects.',
                         'Returned values do not prove the intended object, script, file or dialogue behavior.',
                         'First samples are bounded; names can be lossy and counters can saturate.',
                         'Load context includes preload, loader work and post-load callbacks.',
                         'Gameplay frame denotes an attempted frame, not proof that it completed.',
                         'Lookup summaries do not establish route completion, visual correctness or physical acceptance.']}
    data = summary.get('lookup_diagnostics')
    if data is None:
        return report
    if not isinstance(data, dict) or type(data.get('schema')) is not int or data['schema'] != 1:
        raise ValueError('unsupported lookup diagnostics schema')
    available = boolean(data.get('snapshot_available'), 'snapshot_available')
    if not available:
        if data.get('snapshot_status') not in ('busy', 'error'):
            raise ValueError('unavailable snapshot needs busy/error status')
        if 'kinds' in data:
            raise ValueError('unavailable snapshot must not expose stale counters')
        report['status'] = 'snapshot_' + data['snapshot_status']
        return report
    enabled = boolean(data.get('enabled'), 'enabled')
    active = boolean(data.get('collection_active'), 'collection_active')
    if active and not enabled:
        raise ValueError('disabled session cannot be collecting')
    current = context(data.get('phase'), data.get('frame'))
    if type(data.get('capacity_per_kind')) is not int or data['capacity_per_kind'] != 16 or (
            type(data.get('name_capacity')) is not int or data['name_capacity'] != 96) or (
            data.get('retention') != 'first_samples'):
        raise ValueError('unsupported lookup storage contract')
    rows = data.get('kinds')
    if not isinstance(rows, list) or len(rows) != len(KINDS):
        raise ValueError('lookup kinds must contain all four channels')
    seen = set()
    for row in rows:
        if not isinstance(row, dict) or row.get('kind') not in KINDS or row['kind'] in seen:
            raise ValueError('unknown or duplicate lookup kind')
        kind = row['kind']
        seen.add(kind)
        counters = {name: uint32(row.get(name), name) for name in (
            'attempts', 'returned', 'absent', 'sentinel_absent', 'unretained_absent', 'lossy_absent')}
        saturated = boolean(row.get('saturated'), 'saturated')
        samples = row.get('samples')
        if not isinstance(samples, list) or len(samples) > 16:
            raise ValueError('lookup sample capacity exceeded')
        retained = 0
        lossy_retained = 0
        keys = set()
        for sample in samples:
            if not isinstance(sample, dict):
                raise ValueError('lookup sample must be an object')
            name, object_id = sample.get('name'), sample.get('object_id')
            if not isinstance(name, str) or len(name) >= 96 or any(not 32 <= ord(ch) < 127 for ch in name):
                raise ValueError('sample name exceeds bounded printable ASCII contract')
            if type(object_id) is not int or not -(1 << 31) <= object_id < (1 << 31):
                raise ValueError('sample object ID must remain int32')
            if kind == 'object' and (object_id == 0 or name) or kind != 'object' and (object_id != 0 or not name):
                raise ValueError('sample key roles or sentinel classification invalid')
            count = uint32(sample.get('count'), 'sample count')
            if count == 0:
                raise ValueError('retained sample must have a positive count')
            first = context(sample.get('first_phase'), sample.get('first_frame'))
            last = context(sample.get('last_phase'), sample.get('last_frame'))
            if not first <= last <= current:
                raise ValueError('sample lifetime falls outside capture context')
            lossy = boolean(sample.get('key_lossy'), 'key_lossy')
            if lossy:
                if kind == 'object' or count != 1:
                    raise ValueError('lossy names cannot be deduplicated or used as object IDs')
                lossy_retained += count
            else:
                key = object_id, name
                if key in keys:
                    raise ValueError('duplicate exact retained key')
                keys.add(key)
            retained += count
        if saturated and MAX_UINT32 not in (*counters.values(), *(s['count'] for s in samples)):
            raise ValueError('saturation flag requires a saturated counter')
        if not saturated:
            if counters['attempts'] != counters['returned'] + counters['absent'] or (
                    counters['absent'] != counters['sentinel_absent'] + counters['unretained_absent'] + retained):
                raise ValueError('lookup counters do not reconcile with retained observations')
            if not lossy_retained <= counters['lossy_absent'] <= counters['absent'] - counters['sentinel_absent']:
                raise ValueError('lossy lookup counter mismatch')
            if counters['unretained_absent'] and len(samples) != 16:
                raise ValueError('unretained observations require full first-sample capacity')
        if not enabled and (any(counters.values()) or samples or saturated):
            raise ValueError('disabled capture cannot contain lookup observations')
        report['kinds'].append({'kind': kind, **counters, 'counters_are_lower_bounds': saturated,
                                'retained_samples': len(samples), 'samples': samples})
    report.update(status='captured' if enabled else 'disabled', collection_active=active,
                  phase=data['phase'], attempted_frame=data['frame'])
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('summary', type=Path)
    parser.add_argument('--candidate', required=True)
    parser.add_argument('--archive', required=True)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.output and not args.output.resolve().is_relative_to((ROOT / 'build').resolve()):
        parser.error('detailed receipts must remain under private build/')
    try:
        if args.summary.stat().st_size > 262144:
            raise ValueError('lookup summary exceeds bounded file size')
        report = analyze_lookups(json.loads(args.summary.read_text(encoding='utf-8')),
                                 expected_candidate=args.candidate, archive=args.archive)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps({'status': report['status'], 'channels': [
        {name: row[name] for name in ('kind', 'attempts', 'returned', 'absent', 'retained_samples',
                                     'unretained_absent', 'counters_are_lower_bounds')}
        for row in report['kinds']]}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
