#!/usr/bin/env python3
"""Match spatial-data chunk paths to reviewed original owner contexts."""
import argparse
import hashlib
import json
from pathlib import Path

SIGNATURES = {
    'visibility_tables': ('0x00020000', '0x04433220', '0x00004700'),
    'static_object_culling': ('0x00020000', '0x04433220', '0x00004500'),
    'pathfind_database': ('0x00020000', '0x04433221', '0x01060635'),
}
SOURCES = ('staging/wwsaveload/saveloadids.h', 'staging/wwphys/wwphysids.h',
           'staging/wwphys/physstaticsavesystem.h', 'staging/wwphys/physstaticsavesystem.cpp',
           'staging/wwphys/pscene_saveload.cpp', 'staging/wwphys/Pathfind.cpp')


def reconcile(inventory):
    rows = []
    for level in inventory['rows']:
        for name, signature in SIGNATURES.items():
            candidates = []
            for member in level['members']:
                for chunk in member.get('chunk_paths', []):
                    if tuple(chunk['chunk_path']) == signature:
                        candidates.append({'member': member['member'], 'member_sha256': member['sha256'],
                                           'index_record': member['index_record'], 'chunk_path': chunk['chunk_path'],
                                           'first_offset': chunk['first_offset'], 'count': chunk['count'],
                                           'payload_bytes_sum': chunk['payload_bytes_sum']})
            rows.append({'map': level['map'], 'name': name, 'expected_chunk_path': signature,
                         'candidates': candidates, 'located': bool(candidates),
                         'status': 'unknown', 'evidence_class': 'retail_chunk_and_source_review',
                         'acceptance_open': 'Loader execution, leaf bounds/semantics, post-load linkage and runtime navigation/culling'})
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--chunks', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    data = args.chunks.read_bytes()
    root = Path(__file__).resolve().parents[1]
    result = {'schema': 1, 'complete': False, 'rows': reconcile(json.loads(data)),
              'chunk_inventory_sha256': hashlib.sha256(data).hexdigest(),
              'reviewed_owner_sources': [{'source': p, 'sha256': hashlib.sha256((root / p).read_bytes()).hexdigest()} for p in SOURCES],
              'limits': ['Reviewed numeric paths require re-review if source definitions change',
                         'Presence does not prove semantic validity or runtime loader support',
                         'Only three spatial data families; other geometry/visibility/pathfind content remains open']}
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'rows': len(result['rows']), 'located': sum(r['located'] for r in result['rows'])}))


if __name__ == '__main__':
    main()
