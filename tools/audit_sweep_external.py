#!/usr/bin/env python3
"""Compare pinned OpenW3D tree metadata with the pristine EA source tree."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess


def compare(original, reference):
    if reference.get('truncated'):
        raise ValueError('Truncated reference tree cannot establish a denominator')
    remote = {r['path']: r['sha'] for r in reference['tree'] if r['type'] == 'blob'}
    if len(remote) != sum(r['type'] == 'blob' for r in reference['tree']):
        raise ValueError('Duplicate reference paths')
    rows = []
    for path in sorted(set(original) | set(remote)):
        relation = ('same_blob' if original.get(path) == remote.get(path) else
                    'reference_only' if path not in original else
                    'ea_only' if path not in remote else 'different_blob')
        rows.append({'id': hashlib.sha256(path.encode()).hexdigest(), 'source': path,
                     'ea_blob': original.get(path), 'reference_blob': remote.get(path),
                     'relation': relation, 'status': 'unknown',
                     'evidence_class': 'git_tree_metadata'})
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference-tree', type=Path, required=True)
    parser.add_argument('--reference-commit', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    upstream = root / 'upstream/CnC_Renegade'
    def git(*arguments):
        return subprocess.check_output(['git', '-C', str(upstream), *arguments])
    commit = git('rev-parse', 'HEAD').decode().strip()
    original = {}
    for item in git('ls-tree', '-rz', '--full-tree', commit).split(b'\0'):
        if not item:
            continue
        metadata, path = item.split(b'\t', 1)
        _, kind, sha = metadata.decode().split()
        if kind == 'blob':
            original[path.decode()] = sha
    data = args.reference_tree.read_bytes()
    tree = json.loads(data)
    if tree['sha'] != args.reference_commit:
        raise ValueError('Reference tree identity differs from requested commit')
    rows = compare(original, tree)
    result = {'schema': 1, 'sweep': 'S8', 'complete': False, 'total': len(rows),
              'counts': {'unknown': len(rows)},
              'relation_counts': dict(sorted(Counter(r['relation'] for r in rows).items())),
              'rows': rows, 'ea_commit': commit, 'reference_commit': args.reference_commit,
              'reference_url': 'https://github.com/w3dhub/OpenW3D',
              'reference_tree_sha256': hashlib.sha256(data).hexdigest(),
              'scope': 'All blob paths in the union of pinned EA and OpenW3D trees',
              'open_risks': ['Blob differences are not fixes or portability verdicts',
                             'Compiler/ABI/threading/renderer/audio behavioral comparison remains open',
                             'Reference changes still need comparison with current port patches',
                             'Retail 1.037 disagreements require private binary identity and addresses',
                             'TT/W3DHub changelog and mod failure-class denominators remain open',
                             'License/notices must be checked per proposed adoption; none adopted']}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result['relation_counts']))


if __name__ == '__main__':
    main()
