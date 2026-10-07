#!/usr/bin/env python3
"""Read-only dump of the persisted WeatherMgr (chunk 0x40800) in every map LSD.

Level files persist _TheWeatherMgr: a static micro chunk (0x03020113, empty in the
original loader) and a dynamic micro-chunk block (0x11020245) holding the
authored wind/rain/snow/ash/fog parameters. Values are little-endian floats.
Does not run the game, build, or export asset bytes.
"""
from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path

if __package__:
    from .audit_m13_level_owners import chunks, microchunks
    from .audit_sweep_retail import map_names
    from .renegade_cinematic_dependency_scan import MixArchive
else:
    from audit_m13_level_owners import chunks, microchunks
    from audit_sweep_retail import map_names
    from renegade_cinematic_dependency_scan import MixArchive

WEATHER_MGR = 0x40800
DYNAMIC = 0x11020245
STATIC = 0x03020113
FIELDS = ('current', 'normal_value', 'normal_target', 'normal_duration',
          'override_target', 'override_duration')
# Micro-chunk ids follow the VARID_ enum in Combat/WeatherMgr.h (VARID_DUMMY = 9).
PARAMS = ('wind_heading', 'wind_speed', 'wind_variability',
          'rain_density', 'snow_density', 'ash_density')
FOG_PARAMS = ('fog_start', 'fog_end')


def decode(micro):
    ids = {}
    base = 0x0A
    for name in PARAMS:
        ids[name] = base
        base += len(FIELDS)
    wind_override, precip_override, fog_enabled = base, base + 1, base + 2
    base += 3
    for name in FOG_PARAMS:
        ids[name] = base
        base += len(FIELDS)
    by_id = dict(micro)
    out = {}
    for name, first in ids.items():
        row = {}
        for index, field in enumerate(FIELDS):
            payload = by_id.get(first + index)
            if payload is not None and len(payload) == 4:
                row[field] = round(struct.unpack('<f', payload)[0], 6)
        out[name] = row
    for name, mid, fmt in (('wind_override_count', wind_override, '<I'),
                           ('precipitation_override_count', precip_override, '<I'),
                           ('fog_enabled', fog_enabled, '<B')):
        payload = by_id.get(mid)
        ok = payload is not None and len(payload) == struct.calcsize(fmt)
        out[name] = struct.unpack(fmt, payload)[0] if ok else None
    known = {first + k for first in ids.values() for k in range(len(FIELDS))}
    known |= {wind_override, precip_override, fog_enabled}
    out['unknown_micro_ids'] = sorted(set(by_id) - known)
    return out


def find(nodes):
    for node in nodes:
        if node.kind == WEATHER_MGR:
            yield node
        yield from find(node.children)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    rows = []
    for name in map_names(args.data):
        path = args.data / name
        row = {'map': name, 'members': []}
        if not path.is_file():
            row['input_missing'] = True
            rows.append(row)
            continue
        archive = MixArchive(path)
        with path.open('rb') as stream:
            for member, _, offset, size in archive.entry_records:
                if Path(member).suffix.lower() != '.lsd':
                    continue
                stream.seek(offset)
                data = stream.read(size)
                result = {'member': member, 'bytes': size}
                try:
                    nodes = list(find(chunks(data)))
                    result['weather_chunks'] = len(nodes)
                    for node in nodes:
                        kids = node.children or chunks(node.data)
                        result['static_chunk_bytes'] = [len(k.data) for k in kids if k.kind == STATIC]
                        for kid in kids:
                            if kid.kind == DYNAMIC:
                                result['weather'] = decode(microchunks(kid.data))
                except ValueError as error:
                    result['error'] = str(error)
                row['members'].append(result)
        rows.append(row)
    text = json.dumps({'schema': 1, 'rows': rows}, indent=2, sort_keys=True)
    if args.output:
        args.output.write_text(text + '\n')
    else:
        print(text)


if __name__ == '__main__':
    main()
