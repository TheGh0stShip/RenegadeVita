"""Discover private retail content leads without consulting the port/source graph.

This is a discovery seed, never a gameplay/readiness pass. Detailed metadata
stays under build/; stdout contains sanitized counts and archive names only.
Disk readers use explicit little-endian 32-bit fields, not host pointer widths.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import struct
import sys
import zlib

ROOT = Path(__file__).resolve().parents[1]
if __package__ in (None, ''):
    sys.path.insert(0, str(ROOT))

from tools.audit_m13_level_owners import chunks, definitions, level_records
from tools.check_campaign_chain import parse_ini
from tools.renegade_cinematic_dependency_scan import MixArchive, parse_command, timing_metadata


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def resolve_retail(root, logical):
    parts = logical.replace('\\', '/').split('/')
    if logical.startswith(('/', '\\')) or ':' in logical or any(p in ('.', '..') for p in parts):
        raise ValueError('Unsafe retail-relative resource path')
    path = root
    for part in filter(None, parts):
        if not path.is_dir():
            return None
        matches = [p for p in path.iterdir() if p.name.casefold() == part.casefold()]
        if len(matches) > 1:
            raise ValueError('Ambiguous retail name case')
        if not matches:
            return None
        path = matches[0]
        if not path.resolve().is_relative_to(root.resolve()):
            raise ValueError('Retail resource leaves the selected baseline root')
    return path


def flow_records(payload):
    sections = parse_ini(payload.decode('latin1'))
    campaign = [v for k, v in sections.items() if k.casefold() == 'campaign']
    if len(campaign) != 1:
        raise ValueError('Expected one unambiguous Campaign section')
    result, keys = [], set()
    for index, (key, value) in enumerate(campaign[0]):
        if key.casefold() in keys:
            raise ValueError('Duplicate campaign key requires original INI semantics review')
        keys.add(key.casefold())
        tokens = value.split()
        kind = tokens[0].casefold() if tokens else 'unknown'
        result.append({'id': f'campaign-flow:{index}', 'entry_key': key,
                       'kind': kind, 'resource': tokens[1] if kind in ('level', 'movie') and len(tokens) > 1 else None,
                       'tokens': tokens,
                       'directive_sha256': hashlib.sha256(value.encode('latin1')).hexdigest(),
                       'content_review': 'OPEN'})
    if not result:
        raise ValueError('Empty campaign flow is not a content denominator')
    return result


def member_leads(name, payload):
    suffix = Path(name).suffix.lower()
    result = {'sha256': hashlib.sha256(payload).hexdigest(), 'semantic_review': 'OPEN'}
    if suffix in ('.ldd', '.lsd', '.ddb'):
        nodes = chunks(payload)
        # Preserve every structural node, even when the typed decoder has no
        # interpretation for it. "Parsed" never means semantically consumed.
        groups = {}
        def census(children, parents=()):
            for node in children:
                path = parents + (node.kind,)
                state = groups.setdefault(path, {'count': 0, 'payload_bytes': 0,
                                                'sample_offsets': [], 'digest': hashlib.sha256()})
                state['count'] += 1
                state['payload_bytes'] += len(node.data)
                if len(state['sample_offsets']) < 8:
                    state['sample_offsets'].append(node.offset)
                state['digest'].update(struct.pack('<IIII', node.kind, node.offset,
                                                   len(node.data), len(node.children)))
                state['digest'].update(hashlib.sha256(node.data).digest())
                census(node.children, path)
        census(nodes)
        result['chunk_node_count'] = sum(g['count'] for g in groups.values())
        result['chunk_path_census'] = [{'path': [f'0x{x:08x}' for x in path],
                                       'count': group['count'], 'payload_bytes': group['payload_bytes'],
                                       'sample_offsets': group['sample_offsets'],
                                       'all_node_records_sha256': group['digest'].hexdigest(),
                                       'semantic_review': 'OPEN'} for path, group in sorted(groups.items())]
        result['chunk_census_scope'] = 'Every node counted and hashed by ancestor path; at most eight example offsets per path. Not semantic consumption.'
    if suffix in ('.ldd', '.lsd'):
        result['level_records'] = level_records(nodes)
    elif suffix == '.ddb':
        # Basic persisted identity and authored script records only. No source
        # project list, provider registration list or native class whitelist.
        result['definition_records'] = definitions(nodes, {})
        result['reference_schema_complete'] = False
    elif suffix == '.txt':
        commands, malformed, unclassified, nonblank, comments = [], [], [], 0, 0
        for line_number, line in enumerate(payload.decode('latin1').splitlines(), 1):
            if line.strip():
                nonblank += 1
            if line.lstrip().startswith(';'):
                comments += 1
            parsed = parse_command(line)
            if parsed is not None:
                token, command, arguments = parsed
                # Keep unknown verbs too: implementation is not the denominator.
                commands.append({'line': line_number, 'command': command, 'arguments': arguments,
                                 **timing_metadata(token), 'semantic_review': 'OPEN'})
            elif line.strip() and not line.lstrip().startswith(';'):
                lead = {'line': line_number, 'line_sha256': hashlib.sha256(line.encode('latin1')).hexdigest()}
                unclassified.append(lead)
                if re.match(r'^\s*[+\-\d.]', line):
                    malformed.append(lead)
        result.update(timed_command_candidates=commands, unparsed_numeric_lines=malformed,
                      unclassified_text_lines=unclassified, nonblank_lines=nonblank, comment_lines=comments,
                      text_format_verified=False)
    return result


def collect(retail_root):
    data = resolve_retail(retail_root, 'Data')
    if data is None:
        raise ValueError('Missing retail Data directory')
    archive_paths = sorted(p for p in data.rglob('*') if p.is_file() and
                           p.suffix.lower() in ('.mix', '.dat', '.dbs'))
    if not archive_paths:
        raise ValueError('No retail archives; refusing an empty baseline')
    archives, issues, campaign_candidates = [], [], []
    archive_names = Counter(p.relative_to(data).as_posix().casefold() for p in archive_paths)
    for name, count in archive_names.items():
        if count > 1:
            issues.append({'archive': name, 'kind': 'archive_case_conflict'})
    for path in archive_paths:
        logical = path.relative_to(data).as_posix()
        if not path.resolve().is_relative_to(retail_root.resolve()):
            issues.append({'archive': logical, 'kind': 'archive_leaves_baseline_root'})
            continue
        stamp = (path.stat().st_size, path.stat().st_mtime_ns)
        row = {'name': logical, 'sha256': sha256_file(path), 'size': stamp[0], 'mtime_ns': stamp[1],
               'entries': [], 'content_review': 'OPEN'}
        archives.append(row)
        try:
            archive = MixArchive(path)
        except (ValueError, OSError, UnicodeError, struct.error) as error:
            issues.append({'archive': logical, 'kind': 'archive_parse', 'detail': str(error)})
            continue
        names = Counter(name.casefold() for name, *_ in archive.entry_records)
        crc_keys = [crc for _, crc, _, _ in archive.entry_records]
        row['crc_index_sorted'] = crc_keys == sorted(crc_keys)
        if not row['crc_index_sorted']:
            issues.append({'archive': logical, 'kind': 'unsorted_archive_crc_index'})
        if len(set(crc_keys)) != len(crc_keys):
            issues.append({'archive': logical, 'kind': 'duplicate_archive_crc_keys'})
        row['duplicate_names'] = sorted(name for name, count in names.items() if count > 1)
        if row['duplicate_names']:
            issues.append({'archive': logical, 'kind': 'duplicate_member_names'})
        # Do not use the name->entry dict: it collapses duplicate name records.
        with path.open('rb') as stream:
            for ordinal, (name, crc, offset, size) in enumerate(archive.entry_records):
                entry = {'id': f'archive-entry:{logical}:{ordinal}',
                         'name': name, 'crc32': crc, 'offset': offset, 'size': size,
                         'decode_status': 'unreviewed_format'}
                row['entries'].append(entry)
                if crc != zlib.crc32(name.upper().encode('ascii')) & 0xffffffff:
                    entry['decode_status'] = 'blocked_crc_name_mismatch'
                    issues.append({'entry': entry['id'], 'kind': 'crc_name_mismatch'})
                    continue
                if Path(name).suffix.lower() not in ('.ldd', '.lsd', '.ddb', '.txt') and name.casefold() != 'campaign.ini':
                    continue
                stream.seek(offset)
                payload = stream.read(size)
                if len(payload) != size:
                    entry['decode_status'] = 'blocked_short_read'
                    issues.append({'entry': entry['id'], 'kind': 'short_read'})
                    continue
                if name.casefold() == 'campaign.ini':
                    campaign_candidates.append({'archive': logical, 'entry': entry['id'],
                                                'sha256': hashlib.sha256(payload).hexdigest(), 'payload': payload})
                try:
                    entry['discovery'] = member_leads(name, payload)
                    entry['decode_status'] = 'parsed_metadata_only'
                except (ValueError, KeyError, IndexError, UnicodeError, struct.error) as error:
                    entry['decode_status'] = 'parse_error'
                    issues.append({'entry': entry['id'], 'kind': 'member_parse', 'detail': str(error)})
        if stamp != (path.stat().st_size, path.stat().st_mtime_ns):
            issues.append({'archive': logical, 'kind': 'archive_changed_during_collection'})
    # Retail loose files may override packed members. Keep that surface visible;
    # this first seed does not invent a complete filesystem precedence model.
    loose = [{'name': p.relative_to(data).as_posix(), 'size': p.stat().st_size, 'content_review': 'OPEN'}
             for p in sorted(data.rglob('*')) if p.is_file() and p not in archive_paths]
    for name in ('campaign.ini', 'Data/campaign.ini'):
        loose_campaign = resolve_retail(retail_root, name)
        if loose_campaign is not None:
            payload = loose_campaign.read_bytes()
            campaign_candidates.append({'archive': None, 'entry': 'loose:' + name,
                                        'sha256': hashlib.sha256(payload).hexdigest(), 'payload': payload})
    # Multiple copies require actual original factory-precedence reconciliation.
    flow = []
    if len(campaign_candidates) != 1:
        issues.append({'kind': 'campaign_precedence_unresolved', 'candidates': len(campaign_candidates)})
    else:
        try:
            flow = flow_records(campaign_candidates[0]['payload'])
        except ValueError as error:
            issues.append({'kind': 'campaign_parse', 'detail': str(error)})
    for candidate in campaign_candidates:
        candidate['section_records'] = [{'name': name, 'semantic_review': 'OPEN',
                                        'entries': [{'key': key, 'tokens': value.split()} for key, value in rows]}
                                       for name, rows in parse_ini(candidate['payload'].decode('latin1')).items()]
        candidate.pop('payload')
    for step in flow:
        if step['kind'] not in ('level', 'movie', 'score', 'message'):
            issues.append({'step': step['id'], 'kind': 'unclassified_campaign_directive'})
        if step['kind'] in ('level', 'movie'):
            resource = step['resource']
            try:
                found = resolve_retail(retail_root, 'Data/' + resource) if step['kind'] == 'level' and resource else \
                        resolve_retail(retail_root, resource) if resource else None
            except ValueError as error:
                issues.append({'step': step['id'], 'kind': 'resource_path', 'detail': str(error)})
                found = None
            step['resource_present'] = found is not None and found.is_file()
            step['lookup_assumption'] = 'Data-relative loose level; root-relative movie; original factory precedence OPEN'
            archive_row = next((a for a in archives if step['kind'] == 'level' and
                                resource and a['name'].casefold() == resource.casefold()), None)
            step['resource_decode_state'] = 'absent' if not step['resource_present'] else 'present_unparsed'
            if archive_row and any('level_records' in e.get('discovery', {}) for e in archive_row['entries']):
                step['resource_decode_state'] = 'present_metadata_decoded'
            if not step['resource_present']:
                issues.append({'step': step['id'], 'kind': 'missing_flow_resource'})
    binaries = []
    for name in ('game.exe', 'game2.exe', 'scripts.dll', 'scripts2.dll'):
        path = resolve_retail(retail_root, name)
        if path is not None and path.is_file():
            binaries.append({'name': path.name, 'sha256': sha256_file(path), 'size': path.stat().st_size})
    documents = []
    manual = resolve_retail(retail_root, 'Manuals/CC_RENEGADE_MANUAL - ENGLISH.PDF')
    if manual is not None and manual.is_file():
        documents.append({'name': manual.name, 'sha256': sha256_file(manual),
                          'scope': 'Publisher expectations; version-specific retail behavior unverified'})
    archive_set_sha256 = hashlib.sha256(json.dumps(sorted(
        (a['name'].casefold(), a['sha256']) for a in archives), separators=(',', ':')).encode()).hexdigest()
    return {'schema': 1, 'evidence_class': 'retail-only discovery seed; no gameplay acceptance',
            'retail_root': str(retail_root.resolve()),
            'archive_set_sha256': archive_set_sha256,
            'decoder_sha256': {name: sha256_file(ROOT / name) for name in (
                'tools/collect_retail_content_baseline.py', 'tools/audit_m13_level_owners.py',
                'tools/check_campaign_chain.py', 'tools/renegade_cinematic_dependency_scan.py')},
            'retail_version_verified': False, 'source_or_port_graph_consulted': False,
            'content_inventory_complete': False, 'play_test_ready': False,
            'binaries': binaries, 'reference_documents': documents,
            'campaign_candidates': campaign_candidates, 'campaign_flow': flow,
            'archives': archives, 'unreviewed_loose_files': loose, 'discovery_issues': issues,
            'required_unfinished_work': ['retail reference sequence catalogue and version reconciliation',
                'all authored entries mapped to visible/audible gameplay and prerequisites',
                'complete definition/conversation/resource decoding and loose-file precedence',
                'original owner, linked factory, reachable behavior and stub audit per feature',
                'shared gameplay, presentation, persistence, Practice and networking feature catalogue',
                'all-mission content admission and regression checks; runtime evidence remains held']}


def summary(catalogue):
    entries = [entry for archive in catalogue['archives'] for entry in archive['entries']]
    levels = [entry for entry in entries if 'level_records' in entry.get('discovery', {})]
    definitions_ = [entry for entry in entries if 'definition_records' in entry.get('discovery', {})]
    return {'evidence_class': catalogue['evidence_class'], 'content_inventory_complete': False,
            'archive_set_sha256': catalogue['archive_set_sha256'],
            'retail_version_verified': catalogue['retail_version_verified'],
            'play_test_ready': False, 'archive_count': len(catalogue['archives']), 'entry_count': len(entries),
            'campaign_flow_steps': len(catalogue['campaign_flow']),
            'campaign_level_listing': [s['resource'] for s in catalogue['campaign_flow'] if s['kind'] == 'level'],
            'sequence_semantics_review': 'OPEN',
            'entries_by_decode_status': dict(sorted(Counter(e['decode_status'] for e in entries).items())),
            'issues_by_kind': dict(sorted(Counter(i['kind'] for i in catalogue['discovery_issues']).items())),
            'binary_chunk_nodes_open': sum(e.get('discovery', {}).get('chunk_node_count', 0) for e in entries),
            'text_lines_unclassified': sum(len(e.get('discovery', {}).get('unclassified_text_lines', [])) for e in entries),
            'decoded_level_members': len(levels),
            'level_script_bindings': sum(len(e['discovery']['level_records']['script_records']) for e in levels),
            'decoded_definition_members': len(definitions_),
            'definition_records': sum(len(e['discovery']['definition_records']) for e in definitions_),
            'timed_command_candidates': sum(len(e.get('discovery', {}).get('timed_command_candidates', [])) for e in entries),
            'discovery_issues': len(catalogue['discovery_issues']),
            'unreviewed_loose_files': len(catalogue['unreviewed_loose_files'])}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--retail-root', type=Path, required=True)
    parser.add_argument('--private-output', type=Path, required=True)
    args = parser.parse_args()
    if not args.private_output.resolve().is_relative_to((ROOT / 'build').resolve()):
        parser.error('detailed retail metadata must stay under the private build directory')
    if args.private_output.resolve().is_relative_to(args.retail_root.resolve()):
        parser.error('discovery output must not modify the selected retail tree')
    catalogue = collect(args.retail_root)
    args.private_output.parent.mkdir(parents=True, exist_ok=True)
    args.private_output.write_text(json.dumps(catalogue, indent=2) + '\n')
    print(json.dumps(summary(catalogue), indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
