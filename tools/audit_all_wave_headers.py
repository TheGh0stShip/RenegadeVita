#!/usr/bin/env python3
"""Inventory WAV metadata across every supplied archive, preserving index duplicates."""
import argparse
from collections import Counter
import hashlib
import json
import struct
from pathlib import Path
from tools.audit_mission_wave_headers import inspect_wave
from tools.renegade_cinematic_dependency_scan import MixArchive


def physical_chunks(data):
    """Walk actual source bounds independently of the outer RIFF declaration.

    This is forensic metadata, never a compatibility decoder or repaired file.
    """
    result = {'source_bytes': len(data), 'chunks': [], 'errors': []}
    if len(data) < 12 or data[:4] != b'RIFF' or data[8:12] != b'WAVE':
        result['errors'].append('not_complete_riff_wave_header')
        return result
    result['declared_bytes'] = struct.unpack_from('<I', data, 4)[0] + 8
    result['declared_minus_source_bytes'] = result['declared_bytes'] - len(data)
    offset = 12
    while offset + 8 <= len(data):
        kind, size = struct.unpack_from('<4sI', data, offset)
        payload = offset + 8
        available = len(data) - payload
        result['chunks'].append({'kind_hex': kind.hex(), 'offset': offset,
                                 'declared_payload_bytes': size, 'available_payload_bytes': min(size, available)})
        if size > available:
            result['errors'].append('chunk_exceeds_actual_source')
            break
        offset = payload + size
        if size & 1:
            if offset == len(data):
                result['final_odd_padding_absent'] = True
                break
            offset += 1
    result['remaining_source_bytes'] = len(data) - offset
    if not result['errors'] and result['remaining_source_bytes']:
        result['errors'].append('incomplete_chunk_header_trailer')
    counts = Counter(c['kind_hex'] for c in result['chunks'])
    result['single_format_and_data'] = counts[b'fmt '.hex()] == counts[b'data'.hex()] == 1
    data_chunks = [c for c in result['chunks'] if c['kind_hex'] == b'data'.hex()]
    result['data_payloads_within_source'] = bool(data_chunks) and all(
        c['declared_payload_bytes'] == c['available_payload_bytes'] for c in data_chunks)
    if len(data_chunks) == 1 and result['data_payloads_within_source']:
        chunk = data_chunks[0]
        result['bytes_after_data_payload'] = len(data) - chunk['offset'] - 8 - chunk['declared_payload_bytes']
    return result


def summarize(archive, members):
    formats = Counter()
    findings = []
    for member in members:
        metadata = member['metadata']
        fmt = metadata.get('format')
        formats[tuple(fmt[k] for k in ('tag', 'channels', 'sample_rate', 'bits_per_sample')) if fmt else None] += 1
        if metadata['header_findings'] or metadata['block_findings']:
            findings.append({k: member[k] for k in ('member', 'index_record', 'offset', 'bytes', 'sha256')} |
                            {'header_findings': metadata['header_findings'],
                             'block_findings': metadata['block_findings'],
                             'physical_chunk_bounds': member.get('physical_chunk_bounds'), 'status': 'unknown'})
    return {'archive': archive, 'status': 'unknown', 'evidence_class': 'retail_wave_metadata',
            'wave_members': len(members),
            'formats': [{'format': list(key) if key else None, 'members': count}
                        for key, count in sorted(formats.items(), key=lambda item: str(item[0]))],
            'header_finding_members': sum(bool(m['metadata']['header_findings']) for m in members),
            'block_finding_members': sum(bool(m['metadata']['block_findings']) for m in members),
            'findings': findings}


def scan(directory):
    rows, archives, receipts = [], [], []
    for path in sorted(directory.iterdir()):
        if not path.is_file() or path.suffix.lower() not in ('.mix', '.dat', '.dbs'):
            continue
        archive = MixArchive(path)
        members = []
        with path.open('rb') as stream:
            archives.append({'archive': path.name, 'sha256': hashlib.file_digest(stream, 'sha256').hexdigest()})
            for index, (name, _, offset, size) in enumerate(archive.entry_records):
                if not name.lower().endswith('.wav'):
                    continue
                stream.seek(offset)
                data = stream.read(size)
                if len(data) != size:
                    raise ValueError('truncated archive member')
                metadata = inspect_wave(data)
                member = {'member': name, 'index_record': index, 'offset': offset, 'bytes': size,
                          'sha256': hashlib.sha256(data).hexdigest(), 'metadata': metadata}
                if metadata['header_findings'] or metadata['block_findings']:
                    member['physical_chunk_bounds'] = physical_chunks(data)
                members.append(member)
        rows.append(summarize(path.name, members))
        receipts.append({'archive': path.name, 'members': members})
    return rows, archives, receipts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--private-output', type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    if args.private_output and not args.private_output.resolve().is_relative_to(root / 'build'):
        parser.error('detailed receipts must remain under private build/')
    rows, archives, receipts = scan(args.data)
    sources = ('tools/audit_all_wave_headers.py', 'tools/audit_mission_wave_headers.py',
               'tools/renegade_cinematic_dependency_scan.py', 'port/audio/vita/renegade_wave_decoder.cpp')
    result = {'schema': 1, 'complete': False, 'rows': rows, 'total': len(rows),
              'counts': {'unknown': len(rows)}, 'archives': archives,
              'totals': {key: sum(row[key] for row in rows)
                         for key in ('wave_members', 'header_finding_members', 'block_finding_members')},
              'parser_inputs': [{'source': source, 'sha256': hashlib.sha256((root / source).read_bytes()).hexdigest()}
                               for source in sources],
              'limits': ['Every archive index WAV occurrence is counted, including duplicate names.',
                         'Loose WAVs, music and movie streams are separate denominators.',
                         'Strict RIFF failures may prevent format identification; these are not unknown-codec verdicts.',
                         'Metadata checks prove no PCM decode, runtime selection, playback or physical acceptance.']}
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    if args.private_output:
        args.private_output.write_text(json.dumps(receipts, indent=2) + '\n')
    print(json.dumps(result['totals']))


if __name__ == '__main__':
    main()
