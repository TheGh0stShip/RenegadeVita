"""Enumerate all released C/C++ units; lexical mentions are not link evidence."""
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def inventory(root):
    code = root / 'upstream/CnC_Renegade/Code'
    manifests = [root / 'CMakeLists.txt', *sorted((root / 'cmake').glob('*.cmake'))]
    texts = {str(p.relative_to(root)): p.read_text() for p in manifests}
    rows = []
    for source in sorted(code.rglob('*')):
        if not source.is_file() or source.suffix.lower() not in ('.c', '.cpp', '.cxx', '.cc'):
            continue
        relative = source.relative_to(code).as_posix()
        staged = root / 'staging' / relative
        # Preserve original spelling; case collisions need explicit review.
        mentions = [name for name, text in texts.items()
                    if relative.lower() in text.lower()]
        rows.append({'original': relative,
                     'original_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
                     'staged_exact_path_exists': staged.is_file(),
                     'manifest_literal_mentions': mentions,
                     'status': 'requires selected-target and owner classification',
                     'linked': None})
    return {'scope': 'All released C/C++ files, including tools and obsolete units. '
                     'Literal mentions do not prove selection; absence does not prove omission. '
                     'No compile, link or runtime acceptance is inferred.',
            'manifest_sha256': {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                                for p in manifests},
            'total': len(rows),
            'by_top_directory': dict(sorted(Counter(r['original'].split('/')[0]
                                                    for r in rows).items())),
            'rows': rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    result = inventory(ROOT)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, indent=2) + '\n')
    print(f"Enumerated {result['total']} original units; classification remains open.")


if __name__ == '__main__':
    main()
