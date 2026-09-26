#!/usr/bin/env python3
"""Read-only raw-animation ownership audit. Outputs metadata, never asset payloads."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from renegade_cinematic_dependency_scan import MixArchive


def chunks(data, start, end):
    offset = start
    while offset < end:
        if end - offset < 8:
            raise ValueError('truncated chunk header')
        kind, size = struct.unpack_from('<II', data, offset)
        stop = offset + 8 + (size & 0x7fffffff)
        if stop > end:
            raise ValueError('chunk outside parent')
        yield kind, offset + 8, stop
        offset = stop


def audit_w3d(data):
    result = []
    for kind, start, end in chunks(data, 0, len(data)):
        if kind != 0x200:
            continue
        seen = set()
        for child, begin, stop in chunks(data, start, end):
            if child not in (0x202, 0x203):
                continue
            header = 12 if child == 0x202 else 9
            if stop - begin < header:
                raise ValueError('truncated animation channel header')
            if child == 0x202:
                first, last, width, channel, pivot, _ = struct.unpack_from('<6H', data, begin)
                data_bytes = (last - first + 1) * width * 4
                valid_type = channel <= 6
            else:
                first, last, channel, pivot = struct.unpack_from('<4H', data, begin)
                data_bytes = (last - first + 8) // 8
                valid_type = channel == 0
            key = (child, pivot, channel)
            reasons = []
            if key in seen:
                reasons.append('replaces_owned_channel')
            if not valid_type:
                reasons.append('unsupported_raw_channel_type')
            if last < first or data_bytes > stop - begin - header:
                reasons.append('invalid_frame_range_or_payload')
            if reasons:
                result.append(dict(offset=begin, chunk=child, pivot=pivot, channel=channel,
                                   data_bytes=data_bytes, reasons=reasons))
            seen.add(key)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    args = parser.parse_args()
    archive = MixArchive(args.archive)
    findings = []
    scanned = 0
    for name in sorted(archive.entries):
        if not name.endswith('.w3d'):
            continue
        data = archive.read_binary(name)
        scanned += 1
        issues = audit_w3d(data)
        if issues:
            findings.append(dict(member=name, sha256=hashlib.sha256(data).hexdigest(), issues=issues))
    print(json.dumps(dict(schema=1, archive=args.archive.name, w3d_members_scanned=scanned,
                          findings=findings), indent=2))
