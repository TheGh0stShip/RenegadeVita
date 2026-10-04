#!/usr/bin/env python3
"""Inventory WAV metadata across every supplied archive, preserving index duplicates."""
import argparse
from collections import Counter
import hashlib
import json
import struct
from pathlib import Path
from tools.audit_mission_wave_headers import inspect_wave
from tools.audit_mission_conversations import sound_definitions, translations
from tools.audit_deep_saved_content import conversations
from tools.audit_m13_level_owners import chunks
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


def match_definitions(definitions, members):
    """Retain exact/basename candidates separately; do not infer mount precedence."""
    candidates = {}
    for identifier, definition in definitions.items():
        filename = definition.get('filename')
        if filename:
            basename = filename.replace('\\', '/').rsplit('/', 1)[-1]
            candidates.setdefault(basename.casefold(), []).append(
                {'definition_id': identifier, 'definition_name': definition['name'],
                 'definition_offset': definition['offset'],
                 'filename_match': 'exact_casefold' if filename == basename else 'basename_casefold',
                 'authored_filename_sha256': hashlib.sha256(filename.encode('utf-8')).hexdigest()})
    return {name: candidates.get(name.casefold(), []) for name in members}


def definition_references(directory, rows):
    names = {f['member'] for row in rows for f in row['findings']}
    databases = []
    for path in sorted(directory.iterdir()):
        if not path.is_file() or path.suffix.lower() not in ('.mix', '.dat', '.dbs'):
            continue
        archive = MixArchive(path)
        with path.open('rb') as stream:
            for index, (name, _, offset, size) in enumerate(archive.entry_records):
                if name.casefold() != 'objects.ddb':
                    continue
                stream.seek(offset)
                data = stream.read(size)
                if len(data) != size:
                    raise ValueError('truncated definition database')
                definitions = sound_definitions(chunks(data))
                matches = match_definitions(definitions, names)
                identity = {'archive': path.name, 'member': name, 'index_record': index,
                            'offset': offset, 'sha256': hashlib.sha256(data).hexdigest()}
                databases.append(identity | {'definitions': len(definitions),
                    'sound_filename_definitions': sum(bool(d.get('filename')) for d in definitions.values()),
                    'matched_flagged_filenames': sum(bool(v) for v in matches.values())})
                for row in rows:
                    for finding in row['findings']:
                        finding.setdefault('definition_candidates', []).extend(
                            identity | candidate for candidate in matches[finding['member']])
    return databases


def translation_links(records, sound_ids):
    return [{'text_id': key, 'sound_id': row['sound_id']}
            for key, row in sorted(records.items()) if row.get('sound_id') in sound_ids]


def conversation_references(directory, rows):
    findings = [f for row in rows for f in row['findings']]
    sound_ids = {d['definition_id'] for f in findings for d in f.get('definition_candidates', [])}
    databases, translation_rows, conversation_rows = [], [], []
    for path in sorted(directory.iterdir()):
        if not path.is_file() or path.suffix.lower() not in ('.mix', '.dat', '.dbs'):
            continue
        archive = MixArchive(path)
        with path.open('rb') as stream:
            for index, (name, _, offset, size) in enumerate(archive.entry_records):
                is_translation = name.casefold() == 'strings.tdb'
                if not is_translation and not name.lower().endswith(('.ldd', '.lsd', '.cdb')):
                    continue
                stream.seek(offset)
                data = stream.read(size)
                if len(data) != size:
                    raise ValueError('truncated conversation/translation member')
                identity = {'archive': path.name, 'member': name, 'index_record': index,
                            'sha256': hashlib.sha256(data).hexdigest()}
                nodes = chunks(data)
                if is_translation:
                    records, issues = translations(nodes)
                    if issues:
                        raise ValueError('unsupported translation schema')
                    links = translation_links(records, sound_ids)
                    translation_rows.extend(identity | link for link in links)
                    databases.append(identity | {'kind': 'translation', 'records': len(records), 'matched_records': len(links)})
                else:
                    records = conversations(nodes, allow_legacy_category=False)
                    conversation_rows.extend((identity, record) for record in records)
                    databases.append(identity | {'kind': 'conversation', 'records': len(records)})
    by_sound, by_text = {}, {}
    for link in translation_rows:
        by_sound.setdefault(link['sound_id'], []).append(link)
    for identity, record in conversation_rows:
        for ordinal, remark in enumerate(record['remarks']):
            by_text.setdefault(remark['text_id'], []).append(identity | {
                'conversation_id': record['id'], 'conversation_name': record['name'],
                'conversation_offset': record['offset'], 'remark_ordinal': ordinal,
                'remark_offset': remark['offset'], 'text_id': remark['text_id']})
    for finding in findings:
        ids = {d['definition_id'] for d in finding.get('definition_candidates', [])}
        finding['translation_candidates'] = [link for identifier in sorted(ids) for link in by_sound.get(identifier, [])]
        text_ids = {link['text_id'] for link in finding['translation_candidates']}
        finding['conversation_candidates'] = [link for identifier in sorted(text_ids) for link in by_text.get(identifier, [])]
    return databases


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
    databases = definition_references(args.data, rows)
    reference_databases = conversation_references(args.data, rows)
    sources = ('tools/audit_all_wave_headers.py', 'tools/audit_mission_wave_headers.py',
               'tools/renegade_cinematic_dependency_scan.py', 'tools/audit_mission_conversations.py',
               'tools/audit_m13_level_owners.py', 'tools/audit_deep_saved_content.py',
               'port/audio/vita/renegade_wave_decoder.cpp')
    result = {'schema': 1, 'complete': False, 'rows': rows, 'total': len(rows),
              'counts': {'unknown': len(rows)}, 'archives': archives,
              'definition_databases': databases,
              'reference_databases': reference_databases,
              'totals': {key: sum(row[key] for row in rows)
                         for key in ('wave_members', 'header_finding_members', 'block_finding_members')},
              'parser_inputs': [{'source': source, 'sha256': hashlib.sha256((root / source).read_bytes()).hexdigest()}
                               for source in sources],
              'limits': ['Every archive index WAV occurrence is counted, including duplicate names.',
                         'Loose WAVs, music and movie streams are separate denominators.',
                         'Strict RIFF failures may prevent format identification; these are not unknown-codec verdicts.',
                         'Sound-definition matches retain every database alternative; active callers and mount precedence remain open.',
                         'Translation links use direct sound IDs; indirect twiddler chains and direct audio callers remain separate.',
                         'Metadata checks prove no PCM decode, runtime selection, playback or physical acceptance.']}
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    if args.private_output:
        args.private_output.write_text(json.dumps(receipts, indent=2) + '\n')
    print(json.dumps(result['totals']))


if __name__ == '__main__':
    main()
