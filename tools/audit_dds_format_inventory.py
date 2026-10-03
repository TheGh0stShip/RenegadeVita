"""Read-only DDS header inventory across every supplied MIX1 archive.

Metadata only; format presence does not prove mount order or runtime use.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct
import zlib

from renegade_cinematic_dependency_scan import MixArchive


def file_sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def inspect_header(data):
    if len(data) != 128 or data[:4] != b'DDS ':
        raise ValueError('short or invalid DDS header')
    if struct.unpack_from('<I', data, 4)[0] != 124 or struct.unpack_from('<I', data, 76)[0] != 32:
        raise ValueError('invalid DDS structure sizes')
    height, width = struct.unpack_from('<II', data, 12)
    flags = struct.unpack_from('<I', data, 80)[0]
    fourcc = data[84:88]
    return {'width': width, 'height': height,
            'mip_count_declared': struct.unpack_from('<I', data, 28)[0],
            'format': fourcc.decode('ascii', errors='replace') if flags & 4 else 'uncompressed',
            'pixel_flags': flags, 'header_sha256': hashlib.sha256(data).hexdigest()}


def audit(directory):
    rows, archives, errors = [], [], []
    for path in sorted(directory.iterdir()):
        if not path.is_file() or path.suffix.lower() not in ('.mix', '.dat', '.dbs'):
            continue
        try:
            archive = MixArchive(path)
        except (ValueError, OSError, struct.error, UnicodeError) as error:
            errors.append({'archive': path.name, 'error_type': type(error).__name__})
            continue
        archives.append({'archive': path.name, 'members': len(archive.entry_records),
                         'unique_names': len(archive.entries),
                         'sha256': file_sha256(path),
                         'bytes': path.stat().st_size})
        with path.open('rb') as stream:
            for index, (name, crc, offset, size) in enumerate(archive.entry_records):
                if not name.lower().endswith('.dds'):
                    continue
                row = {'archive': path.name, 'member': name, 'index_record': index,
                       'offset': offset, 'bytes': size}
                stream.seek(offset)
                try:
                    if crc != zlib.crc32(name.upper().encode('ascii')):
                        raise ValueError('CRC/name mismatch')
                    row.update(inspect_header(stream.read(min(size, 128))))
                except ValueError as error:
                    row.update(format='invalid', error=str(error))
                rows.append(row)
    inputs = {name: file_sha256(Path(__file__).parent / name)
              for name in ('audit_dds_format_inventory.py', 'renegade_cinematic_dependency_scan.py')}
    for row in rows:
        row['status'] = 'unknown'
        row['evidence_class'] = 'retail_header_metadata'
        identity = [row['archive'], row['index_record'], row['member'], row['offset'], row['bytes']]
        row['row_id'] = hashlib.sha256(json.dumps(identity).encode()).hexdigest()
    return {'schema_version': 1, 'complete': False, 'archives': archives,
            'inputs_sha256': inputs,
            'archive_errors': errors, 'rows': rows,
            'totals': {'dds_members': len(rows), 'by_format': dict(Counter(r['format'] for r in rows))},
            'limits': ['Named archive index records only; duplicate names retained separately.',
                       'Loose DDS files and nested archives are not enumerated.',
                       'Headers only; payload validity, mount precedence and runtime usage unverified.']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.data)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'totals': result['totals'], 'archives': len(result['archives']),
                      'archive_errors': result['archive_errors']}))
