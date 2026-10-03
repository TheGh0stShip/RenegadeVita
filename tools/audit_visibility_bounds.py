#!/usr/bin/env python3
"""Validate visibility table serialization bounds without decompressing assets."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import ctypes
import ctypes.util
from tools.audit_m13_level_owners import chunks, microchunks
from tools.renegade_cinematic_dependency_scan import MixArchive
from tools.audit_level_spatial_presence import SIGNATURES


def matching_chunks(data, signature):
    """Keep every occurrence under its full original loader ancestry."""
    expected = tuple(int(value, 16) for value in signature)
    found = []
    def visit(nodes, ancestry=()):
        for node in nodes:
            path = ancestry + (node.kind,)
            if path == expected:
                found.append(node)
            visit(node.children, path)
    visit(chunks(data))
    return found


class HostLzoDecoder:
    """Host-only LZO2 safe decoder; lzo_uint follows host size_t, not disk uint32."""
    def __init__(self):
        name = ctypes.util.find_library('lzo2')
        if not name:
            raise RuntimeError('Optional host liblzo2 is unavailable')
        self.library = ctypes.CDLL(name)
        self.function = self.library.lzo1x_decompress_safe
        self.function.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p,
                                  ctypes.POINTER(ctypes.c_size_t), ctypes.c_void_p]
        self.function.restype = ctypes.c_int
        self.library.lzo_version.restype = ctypes.c_uint
        self.version = self.library.lzo_version()

    def __call__(self, payload, expected):
        if expected > 16 * 1024 * 1024:
            raise ValueError('Visibility decode exceeds audit allocation limit')
        source = ctypes.create_string_buffer(payload)
        destination = ctypes.create_string_buffer(max(expected, 1))
        size = ctypes.c_size_t(expected)
        code = self.function(source, len(payload), destination, ctypes.byref(size), None)
        if code != 0:
            raise ValueError('LZO safe decode rejected payload')
        return size.value


def audit_candidate(data, candidate, decoder=None):
    if hashlib.sha256(data).hexdigest() != candidate['member_sha256']:
        raise ValueError('Member identity mismatch')
    nodes = matching_chunks(data, SIGNATURES['visibility_tables'])
    if (len(nodes) != candidate['count'] or not nodes or
            nodes[0].offset != candidate['first_offset'] or
            sum(len(n.data) for n in nodes) != candidate['payload_bytes_sum']):
        raise ValueError('Visibility occurrence inventory mismatch')
    rows = []
    for node in nodes:
        row = {'offset': node.offset}
        try:
            row.update(validate(node.data, decoder))
        except ValueError:
            row['parser_error'] = True
        rows.append(row)
    return rows


def validate(data, decoder=None):
    nodes = chunks(data)
    if not nodes or nodes[0].kind != 0x34500000:
        raise ValueError('Missing first visibility variables chunk')
    entries = list(microchunks(nodes[0].data))
    fields = dict(entries)
    findings = []
    if len(fields) != len(entries):
        findings.append('duplicate_visibility_variable')
    def number(key):
        if len(fields.get(key, b'')) != 4:
            raise ValueError('Missing or wrong-width visibility variable')
        return struct.unpack('<I', fields[key])[0]
    version, objects, sectors = number(0), number(2), number(3)
    ids = set()
    pending = None
    tables = compressed = 0
    decoded = decode_errors = size_mismatches = 0
    expected_bytes = ((objects + 31) // 32) * 4
    for node in nodes[1:]:
        if node.kind == 0x34500001:
            if len(node.data) != 4:
                raise ValueError('Wrong-width table ID')
            if pending is not None:
                findings.append('id_without_data')
            pending = struct.unpack('<I', node.data)[0]
        elif node.kind == 0x34500002:
            if pending is None or pending >= sectors:
                findings.append('table_id_outside_sector_count')
            if pending in ids:
                findings.append('duplicate_table_id')
            ids.add(pending)
            children = chunks(node.data)
            if not children or children[0].kind != 1 or len(children[0].data) != 4:
                raise ValueError('Missing compressed byte count')
            declared = struct.unpack('<I', children[0].data)[0]
            payloads = [n for n in children[1:] if n.kind in (2, 3)]
            if any(n.kind not in (2, 3) for n in children[1:]):
                findings.append('unknown_compressed_table_chunk')
            if len(payloads) != 1 or len(payloads[0].data) != declared:
                findings.append('compressed_size_mismatch')
            if any(n.kind == 2 for n in payloads):
                findings.append('obsolete_lzhl_payload')
            if decoder is not None and len(payloads) == 1 and payloads[0].kind == 3:
                try:
                    actual = decoder(payloads[0].data, expected_bytes)
                    decoded += 1
                    if actual != expected_bytes:
                        size_mismatches += 1
                        findings.append('decoded_size_mismatch')
                except ValueError:
                    decode_errors += 1
                    findings.append('lzo_decode_rejected')
            compressed += declared
            tables += 1
            pending = None
        else:
            findings.append('unknown_manager_chunk')
    if pending is not None:
        findings.append('id_without_data')
    result = {'version': version, 'vis_objects': objects, 'vis_sectors': sectors,
            'tables': tables, 'compressed_bytes': compressed,
            'obsolete_version': version < 0x10001, 'findings': sorted(set(findings))}
    if decoder is not None:
        result.update(expected_decoded_bytes_per_table=expected_bytes,
                      decoded_tables=decoded, decode_errors=decode_errors,
                      decoded_size_mismatches=size_mismatches)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data', type=Path, required=True)
    p.add_argument('--presence', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--decode-lzo', action='store_true', help='Use optional host liblzo2 safe decoder')
    args = p.parse_args()
    receipt = args.presence.read_bytes()
    rows = []
    decoder = HostLzoDecoder() if args.decode_lzo else None
    for owner in json.loads(receipt)['rows']:
        if owner['name'] != 'visibility_tables':
            continue
        archive = MixArchive(args.data / owner['map'])
        for candidate in owner['candidates']:
            member, _, offset, size = archive.entry_records[candidate['index_record']]
            if member != candidate['member']:
                raise ValueError('Archive index identity mismatch')
            with archive.path.open('rb') as stream:
                stream.seek(offset)
                data = stream.read(size)
            if len(data) != size:
                raise ValueError('Truncated member')
            for result in audit_candidate(data, candidate, decoder):
                row = {'map': owner['map'], 'member': member,
                   'index_record': candidate['index_record'],
                   'status': 'unknown', 'evidence_class': 'retail_serialization_bounds',
                   'member_sha256': candidate['member_sha256']}
                row.update(result)
                rows.append(row)
    root = Path(__file__).resolve().parents[1]
    args.output.write_text(json.dumps({'schema': 2, 'complete': False, 'rows': rows,
        'presence_sha256': hashlib.sha256(receipt).hexdigest(),
        'parser_inputs': [{'source': source, 'sha256': hashlib.sha256((root / source).read_bytes()).hexdigest()}
                          for source in ('tools/audit_visibility_bounds.py', 'tools/audit_m13_level_owners.py',
                                         'tools/audit_level_spatial_presence.py', 'tools/renegade_cinematic_dependency_scan.py',
                                         'staging/wwphys/vistable.cpp', 'staging/wwphys/vistablemgr.cpp',
                                         'staging/wwlib/lzo.cpp')],
        'decoder': {'provider': 'host_liblzo2_safe', 'version': decoder.version} if decoder else None,
        'limits': ['Host decode does not prove original ARM decoder or visibility correctness',
                   'Only exact reviewed visibility ancestry; other data families remain open']}, indent=2)+'\n')
    print(json.dumps({'rows': len(rows), 'parser_errors': sum(bool(r.get('parser_error')) for r in rows),
                      'findings': sum(len(r.get('findings', [])) for r in rows)}))


if __name__ == '__main__':
    main()
