#!/usr/bin/env python3
"""Inventory original network factory owners against one configured Ninja target.

Compilation membership is not proof of runtime registration or wire compatibility.
Pair this with the original factory/runtime tests, not a directory-wide grep.
"""
import argparse
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def inventory(build, target):
    database = json.loads(subprocess.check_output(
        ['ninja', '-C', str(build), '-t', 'compdb'], text=True, timeout=30))
    prefix = 'CMakeFiles/' + target + '.dir/'
    compiled = {(Path(row['directory']) / row['file']).resolve()
                for row in database if row['output'].startswith(prefix)}
    records = []
    for module in ('commando', 'combat'):
        for source in sorted((ROOT / 'staging' / module).glob('*.cpp')):
            code = source.read_text(errors='replace')
            code = re.sub(r'/\*.*?\*/|//[^\n]*', '', code, flags=re.S)
            for name, class_id in re.findall(
                    r'DECLARE_NETWORKOBJECT_FACTORY\s*\(\s*(\w+)\s*,\s*(\w+)\s*\)', code):
                records.append({'source': str(source.relative_to(ROOT)),
                                'class': name, 'class_id': class_id,
                                'source_compiled': source.resolve() in compiled})
    return {'schema': 1, 'target': target,
            'scope': 'original DECLARE_NETWORKOBJECT_FACTORY owners; excludes manual factories',
            'runtime_registration_verified': False,
            'missing_count': sum(not row['source_compiled'] for row in records),
            'factories': records}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--target', required=True)
    args = parser.parse_args()
    print(json.dumps(inventory(args.build, args.target), indent=2))
