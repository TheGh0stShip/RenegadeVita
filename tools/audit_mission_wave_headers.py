"""Read-only authored-remark WAV metadata, not a decoder or playback test.

Revalidate private conversation receipts, retain every archive/database
alternative, inspect headers and ADPCM block structure without producing PCM.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import struct
import sys

# Support the documented tools/path.py invocation from any working directory.
if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.audit_mission_content_bindings import MAPS, ROOT
from tools.audit_mission_conversations import digest, file_digest
from tools.renegade_cinematic_dependency_scan import MixArchive


def inspect_wave(data, statistics_header_only=False):
    result = {'header_findings': [], 'block_findings': [], 'chunk_counts': {},
              'runtime_decode_or_playback_verified': False}
    findings = result['header_findings']
    if len(data) < 12 or data[:4] != b'RIFF' or data[8:12] != b'WAVE':
        findings.append('not_complete_riff_wave_header')
        return result
    declared = struct.unpack_from('<I', data, 4)[0] + 8
    result.update(source_bytes=len(data), declared_bytes=declared, trailing_source_bytes=max(0, len(data) - declared))
    if declared < 12 or (declared > len(data) and not statistics_header_only):
        findings.append('riff_length_outside_source')
        return result
    scan_bytes = min(declared, len(data))
    offset, fmt, data_range, fact, counts = 12, None, None, 0, Counter()
    while offset + 8 <= scan_bytes:
        kind, size = struct.unpack_from('<4sI', data, offset)
        start = offset + 8
        counts[kind.hex()] += 1
        if size > scan_bytes - start:
            if statistics_header_only and kind == b'data':
                data_range = start, size
                result['truncated_data_header_admitted'] = True
                break
            findings.append('chunk_outside_riff')
            break
        if kind == b'fmt ':
            if fmt is not None:
                findings.append('duplicate_format_chunk')
            elif size < 16:
                findings.append('truncated_format_chunk')
            else:
                tag, channels, rate, byte_rate, align, bits = struct.unpack_from('<HHIIHH', data, start)
                fmt = {'tag': tag, 'channels': channels, 'sample_rate': rate, 'byte_rate': byte_rate,
                       'block_align': align, 'bits_per_sample': bits, 'samples_per_block': 0,
                       'coefficient_count': 0}
                if tag not in (1, 2, 17):
                    findings.append('unsupported_wave_tag_in_current_provider')
                if channels not in (1, 2) or not 8000 <= rate <= 192000 or align == 0:
                    findings.append('invalid_format_values')
                if tag == 1 and (bits not in (8, 16) or align != channels * (bits // 8)):
                    findings.append('invalid_pcm_layout')
                if tag in (2, 17):
                    if bits != 4:
                        findings.append('invalid_adpcm_bit_depth')
                    if size < 20:
                        findings.append('truncated_adpcm_extension')
                    else:
                        fmt['samples_per_block'] = struct.unpack_from('<H', data, start + 18)[0]
                if tag == 2:
                    if size < 22:
                        findings.append('truncated_ms_adpcm_coefficients')
                    else:
                        count = struct.unpack_from('<H', data, start + 20)[0]
                        fmt['coefficient_count'] = count
                        if not 1 <= count <= 32 or 22 + count * 4 > size:
                            findings.append('invalid_ms_adpcm_coefficient_layout')
        elif kind == b'data':
            if data_range is not None:
                findings.append('duplicate_data_chunk')
            else:
                data_range = start, size
        elif kind == b'fact' and size >= 4:
            fact = struct.unpack_from('<I', data, start)[0]
        padded = size + (size & 1)
        # Current Inspect_Wave stops here if a final odd chunk lacks padding.
        # Retain that condition without inventing a stricter decoder verdict.
        if padded > scan_bytes - start:
            result['final_odd_chunk_padding_absent'] = True
            offset = start + size
            break
        offset = start + padded
    result.update(chunk_counts=dict(sorted(counts.items())), unparsed_riff_bytes=scan_bytes - offset,
                  format=fmt, fact_frames=fact)
    if fmt is None:
        findings.append('format_absent')
    if data_range is None:
        findings.append('data_absent')
    if findings:
        return result
    if statistics_header_only:
        result.update(header_conditions_satisfied=True, data_bytes=data_range[1],
                      statistics_header_only=True)
        return result
    start, size = data_range
    result.update(data_bytes=size, complete_block_count=size // fmt['block_align'],
                  remainder_bytes=size % fmt['block_align'])
    channels, align, tag, spb = fmt['channels'], fmt['block_align'], fmt['tag'], fmt['samples_per_block']
    remainder = size % align
    if tag == 1:
        estimate = size // align
    else:
        header = channels * (7 if tag == 2 else 4)
        partial = 0
        if spb and remainder > header:
            partial = min(spb, (2 if tag == 2 else 1) +
                          ((remainder - header) * (2 if channels == 1 else 1) if tag == 2 else
                           ((remainder - header) * 2) // channels))
        estimate = (size // align) * spb + partial if spb else 0
        failures, reserved_nonzero, inspected = Counter(), 0, 0
        for offset in range(start, start + size, align):
            block = min(align, start + size - offset)
            inspected += 1
            if block < header:
                failures['adpcm_block_header_truncated'] += 1
            elif tag == 17:
                for channel in range(channels):
                    if data[offset + channel * 4 + 2] > 88:
                        failures['ima_step_index_outside_table'] += 1
                    reserved_nonzero += data[offset + channel * 4 + 3] != 0
            elif any(data[offset + channel] >= fmt['coefficient_count'] for channel in range(channels)):
                failures['ms_adpcm_predictor_outside_coefficients'] += 1
        result.update(adpcm_blocks_inspected=inspected, ima_reserved_nonzero=reserved_nonzero,
                      block_findings=[{'kind': k, 'count': v} for k, v in sorted(failures.items())])
    estimate = min(0xffffffff, estimate)
    result.update(estimated_frames=estimate, metadata_frames=fact or estimate,
                  fact_minus_estimated_frames=(fact - estimate) if fact else None,
                  estimated_pcm_bytes=estimate * channels * 2,
                  estimated_samples_exceed_provider_ceiling=estimate * channels > 16 * 1024 * 1024,
                  header_conditions_satisfied=True)
    return result


def basename(name):
    if not isinstance(name, str) or not name or '/' in name or '\\' in name or name in ('.', '..'):
        raise ValueError('receipt file/member must remain a basename')
    return name


def candidate_bytes(root, candidate, archives):
    member = basename(candidate['member'])
    if candidate['archive'] is None:
        path = root / member
        if not path.resolve().is_relative_to(root.resolve()):
            raise ValueError('loose voice candidate escapes retail root')
        payload = path.read_bytes()
    else:
        name = basename(candidate['archive'])
        if name not in archives:
            archives[name] = MixArchive(root / name)
        payload = archives[name].read_binary(member)
    if digest(payload) != candidate['sha256'] or ('bytes' in candidate and len(payload) != candidate['bytes']):
        raise ValueError('voice candidate no longer matches conversation receipt')
    return payload


def audit(root, data, receipt, cache=None, archives=None):
    cache, archives = ({} if cache is None else cache), ({} if archives is None else archives)
    name = basename(receipt['map'])
    if file_digest(data / name) != receipt['archive_sha256']:
        raise ValueError('mission archive no longer matches conversation receipt')
    if name not in archives:
        archives[name] = MixArchive(data / name)
    definitions = receipt.get('definition_databases')
    if not definitions:
        raise ValueError('conversation receipt lacks definition database provenance; regenerate it')
    for identity in receipt['level_members'] + receipt['global_databases'] + receipt['string_database_candidates'] + definitions:
        candidate_bytes(data, identity, archives)
    text_ids = {remark['text_id'] for row in receipt['level_conversations'] for remark in row['remarks']}
    variants = []
    for variant in receipt['string_database_candidates']:
        references, unlocated, unique = [], [], set()
        for chain in variant['chains']:
            if chain['text_id'] not in text_ids:
                continue
            for leaf in chain.get('sound_leaves', []):
                if not leaf['candidates']:
                    unlocated.append({'text_id': chain['text_id'], 'sound_id': leaf['id']})
                for candidate in leaf['candidates']:
                    key = candidate['archive'], candidate['member']
                    if key not in cache:
                        payload = candidate_bytes(data, candidate, archives)
                        cache[key] = {'identity': candidate, 'metadata': inspect_wave(payload),
                                      'statistics_header_metadata': inspect_wave(payload, statistics_header_only=True)}
                    elif cache[key]['identity'] != candidate:
                        raise ValueError('conflicting identity for shared voice candidate')
                    unique.add(key)
                    references.append({'text_id': chain['text_id'], 'sound_id': leaf['id'],
                                       'archive': candidate['archive'], 'member': candidate['member']})
        files = [cache[key] for key in sorted(unique, key=lambda k: (k[0] or '', k[1]))]
        formats = Counter((row['metadata']['format']['tag'], row['metadata']['format']['channels'],
                           row['metadata']['format']['sample_rate'], row['metadata']['format']['bits_per_sample'])
                          for row in files if row['metadata'].get('format'))
        variants.append({'string_database': {k: variant[k] for k in ('archive', 'member', 'sha256')},
                         'references': references, 'files': files, 'unlocated_voice_leaves': unlocated,
                         'authored_reference_findings': [r for r in variant['findings'] if r.get('text_id') in text_ids],
                         'summary': {'candidate_references': len(references), 'unique_candidates': len(files),
                                     'authored_reference_findings': sum(r.get('text_id') in text_ids for r in variant['findings']),
                                     'header_finding_files': sum(bool(row['metadata']['header_findings']) for row in files),
                                     'statistics_header_finding_files': sum(bool(row['statistics_header_metadata']['header_findings']) for row in files),
                                     'block_finding_files': sum(bool(row['metadata']['block_findings']) for row in files),
                                     'formats': [{'tag': k[0], 'channels': k[1], 'sample_rate': k[2], 'bits': k[3], 'files': v}
                                                 for k, v in sorted(formats.items())]}})
    source_paths = ['port/audio/vita/renegade_wave_decoder.cpp', 'port/audio/vita/renegade_wave_decoder.h',
                    'port/audio/vita/renegade_miles_provider.cpp']
    return {'schema_version': 1, 'evidence_class': 'read-only authored-remark WAV header/block metadata',
            'map': name, 'archive_sha256': receipt['archive_sha256'], 'definition_databases': definitions,
            'database_variants': variants,
            'source_provenance': [{'path': p, 'sha256': file_digest(root / p)} for p in source_paths],
            'runtime_or_physical_acceptance': False, 'complete_mission_closure': False,
            'limits': ['Authored level remark voice candidates only; global barks, cinematic/direct sounds and music are separate.',
                       'Database/archive alternatives do not prove runtime precedence or executed branches.',
                       'Header and block checks produce no PCM and prove no C++ decoder, Miles, mixing, voice duration or device playback.',
                       'Fact/estimate differences are metadata; trimming and actual decoded frames require compiled reference tests.',
                       'No retail/audio/text export, conversion, build, game/emulator/device action or native gate.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--conversations-directory', type=Path, required=True)
    parser.add_argument('--output-directory', type=Path, required=True)
    args = parser.parse_args()
    output = args.output_directory.resolve()
    if not output.is_relative_to((args.root / 'build').resolve()):
        parser.error('detailed receipts must remain under private build/')
    cache, archives = {}, {}
    output.mkdir(parents=True, exist_ok=True)
    for name in MAPS:
        receipt = json.loads((args.conversations_directory / (Path(name).stem.lower() + '-conversations.json')).read_text())
        result = audit(args.root, args.data, receipt, cache, archives)
        (output / (Path(name).stem.lower() + '-wave-headers.json')).write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps({'map': name, 'variants': [v['summary'] for v in result['database_variants']]}, sort_keys=True), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
