"""Read-only authored zone metadata. Detailed output stays under private build/."""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import struct

from tools.audit_mission_content_bindings import ROOT, MAPS
from tools.audit_m13_level_owners import chunks, flatten, microchunks, level_records, u32
from tools.renegade_cinematic_dependency_scan import MixArchive


def unique_fields(data):
    fields = {}
    for key, value in microchunks(data):
        if key in fields:
            raise ValueError('duplicate zone field')
        fields[key] = value
    return fields


def decode_definition(data):
    fields = unique_fields(data)
    result = {}
    for key, name in ((3, 'check_stars_only'), (5, 'environment_zone')):
        value = fields.get(key)
        if value is not None and value not in (b'\0', b'\1'):
            raise ValueError('invalid serialized zone boolean')
        result[name] = bool(value[0]) if value is not None else None
    result['zone_type'] = struct.unpack('<i', fields[4])[0] if 4 in fields and len(fields[4]) == 4 else None
    if 4 in fields and result['zone_type'] is None:
        raise ValueError('zone type is not signed32')
    return result


def decode_bounds(data):
    fields = unique_fields(data)
    if 1 not in fields or len(fields[1]) != 60:
        raise ValueError('zone OBBox is not original 15 float32 fields')
    values = struct.unpack('<15f', fields[1])
    findings = []
    if not all(math.isfinite(value) for value in values):
        raise ValueError('nonfinite zone bounds')
    if any(value < 0 for value in values[12:15]):
        findings.append('negative_extent')
    return {'basis': list(values[:9]), 'center': list(values[9:12]),
            'extent': list(values[12:15]), 'findings': findings}


def scan(payload, definitions=False):
    result = []
    for factory in flatten(chunks(payload)):
        if len(factory.children) != 2 or [c.kind for c in factory.children] != [0x100100, 0x100101]:
            continue
        variables = [node for node in flatten(factory.children[1].children)
                     if node.kind == (1111991133 if definitions else 922991807)]
        if not variables:
            continue
        if len(variables) != 1:
            raise ValueError('ambiguous zone variable chunk')
        if definitions:
            ids = [u32(unique_fields(node.data)[1]) for node in flatten(factory.children)
                   if node.kind == 0x100 and not node.children and 1 in unique_fields(node.data)
                   and 3 in unique_fields(node.data)]
            if len(ids) != 1:
                raise ValueError('ambiguous zone definition identity')
            result.append({'definition_id': ids[0], **decode_definition(variables[0].data)})
        else:
            objects = level_records([factory])['objects']
            if len(objects) != 1:
                raise ValueError('ambiguous zone object identity')
            result.append({**objects[0], **decode_bounds(variables[0].data)})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not args.output.resolve().is_relative_to((ROOT / 'build').resolve()):
        parser.error('detailed receipts must remain in private build/')
    global_payload = MixArchive(args.data / 'always.dbs').read_binary('objects.ddb')
    base = {row['definition_id']: row for row in scan(global_payload, definitions=True)}
    result = {'maps': [], 'objects_ddb_sha256': hashlib.sha256(global_payload).hexdigest(),
              'runtime_verified': False, 'limits': ['Serialized metadata only; no overlap or callback execution.',
              'Missing definition fields remain unknown; no constructor defaults inferred.']}
    source = ROOT / 'upstream/CnC_Renegade/Code'
    result['original_source_sha256'] = {name: hashlib.sha256((source / name).read_bytes()).hexdigest()
                                       for name in ('Combat/scriptzone.cpp', 'WWMath/obbox.h')}
    for name in MAPS:
        archive = MixArchive(args.data / name)
        defs, members = dict(base), []
        for member in sorted(archive.entries):
            if member.endswith('.ddb'):
                payload = archive.read_binary(member)
                defs.update({row['definition_id']: row for row in scan(payload, definitions=True)})
                members.append({'member': member, 'sha256': hashlib.sha256(payload).hexdigest()})
        zones = []
        for member in sorted(archive.entries):
            if member.endswith(('.ldd', '.lsd')):
                payload = archive.read_binary(member)
                members.append({'member': member, 'sha256': hashlib.sha256(payload).hexdigest()})
                for row in scan(payload):
                    zones.append({**row, 'member': member, 'definition': defs.get(row['definition_id'])})
        counts = Counter('unknown' if row['definition'] is None or row['definition']['check_stars_only'] is None
                         else 'stars_only' if row['definition']['check_stars_only'] else 'all_smart' for row in zones)
        result['maps'].append({'map': name, 'archive_sha256': hashlib.sha256((args.data / name).read_bytes()).hexdigest(),
                              'members': members, 'zones': zones, 'summary': {'zone_records': len(zones),
                              'filter_counts': dict(counts), 'bounds_findings': sum(bool(row['findings']) for row in zones)}})
        print(name, result['maps'][-1]['summary'])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')


if __name__ == '__main__':
    main()
