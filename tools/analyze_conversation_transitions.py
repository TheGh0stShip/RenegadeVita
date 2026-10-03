"""Offline numeric conversation event assessment; never claims gameplay closure."""
import argparse
import json
import math
from pathlib import Path
import re

DETAIL = re.compile(r'instance=(\d+) conversation_id=(-?\d+) action=(-?\d+) remark=(-?\d+) text_id=(-?\d+) next_seconds=(\S+) reason=(-?\d+)')
MONITOR = re.compile(r'instance=(\d+) conversation_id=(-?\d+) action=(-?\d+) object_id=(-?\d+) observer_index=(-?\d+) reason=(-?\d+)')


def analyze(events):
    rows, monitors, findings, identities = [], [], [], set()
    zero, unknown, dropped = 0, 0, 0
    for index, event in enumerate(events):
        if not isinstance(event, dict):
            raise ValueError('event must be an object')
        if event.get('category') != 'conversation':
            continue
        identity = (event.get('candidate'), event.get('archive'), event.get('load_source'))
        if not all(isinstance(value, str) and value for value in identity):
            raise ValueError('missing conversation event identity')
        identities.add(identity)
        name, detail = event.get('name'), event.get('detail')
        if not isinstance(detail, str) or len(detail) > 223:
            raise ValueError('invalid bounded conversation detail')
        if name == 'queue_overflow':
            match = re.fullmatch(r'unretained=(\d+)', detail)
            if not match or not 0 < int(match[1]) <= 0xffffffff:
                raise ValueError('invalid queue overflow count')
            dropped += int(match[1])
            findings.append({'record': index, 'kind': 'queue_loss', 'count': int(match[1])})
            continue
        if name in ('monitor_inserted', 'monitor_present', 'monitor_capacity_rejected', 'observer_call_attempted'):
            match = MONITOR.fullmatch(detail)
            if not match:
                raise ValueError('malformed numeric monitor event')
            values = list(map(int, match.groups()))
            if values[0] > 0xffffffffffffffff or any(not -2**31 <= n < 2**31 for n in values[1:]):
                raise ValueError('monitor numeric width exceeded')
            monitors.append({'record': index, 'event': name, 'instance': values[0],
                             'conversation_id': values[1], 'action_id': values[2],
                             'object_id': values[3], 'observer_index': values[4], 'reason': values[5]})
            if values[0] == 0:
                unknown += 1
            if name == 'monitor_capacity_rejected':
                findings.append({'record': index, 'kind': 'monitor_capacity_rejected'})
            continue
        if name not in ('remark_scheduled', 'owner_finished'):
            findings.append({'record': index, 'kind': 'unrecognized_conversation_event'})
            continue
        match = DETAIL.fullmatch(detail)
        if not match:
            raise ValueError('malformed numeric conversation transition')
        instance, conversation, action, remark, text, seconds, reason = match.groups()
        instance = int(instance)
        numbers = list(map(int, (conversation, action, remark, text, reason)))
        seconds = float(seconds)
        if instance > 0xffffffffffffffff or any(not -2**31 <= n < 2**31 for n in numbers):
            raise ValueError('conversation numeric width exceeded')
        if not math.isfinite(seconds):
            findings.append({'record': index, 'kind': 'nonfinite_timer'})
            seconds = None
        if instance == 0:
            unknown += 1
        if name == 'remark_scheduled' and seconds is not None and seconds <= 0:
            zero += 1
            findings.append({'record': index, 'kind': 'nonpositive_remark_timer'})
        rows.append({'record': index, 'instance': instance, 'conversation_id': numbers[0],
                     'action_id': numbers[1], 'remark': numbers[2], 'text_id': numbers[3],
                     'seconds': seconds, 'reason': numbers[4], 'event': name})
    if len(identities) > 1:
        raise ValueError('mixed conversation capture identities')
    return {'schema': 1, 'identity': list(next(iter(identities))) if identities else None,
            'transitions': rows, 'monitor_events': monitors, 'findings': findings, 'queue_unretained': dropped,
            'nonpositive_remark_timers': zero, 'unknown_instance_records': unknown,
            'callback_delivery_verified': False, 'complete_progression_verified': False,
            'limits': ['One process capture only; tokens are reused across application launches.',
                       'Owner finish is not observer callback delivery or success.',
                       'Missing transitions may reflect opt-out, queue loss or ring eviction.',
                       'No pairing across absent start, reset, load or lifecycle evidence.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('events', type=Path)
    args = parser.parse_args()
    records = [json.loads(line) for line in args.events.read_text().splitlines() if line.strip()]
    print(json.dumps(analyze(records), indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
