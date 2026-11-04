"""Bind the local FFmpeg installation to its build inputs and installed bytes."""
import argparse
import hashlib
import json
from pathlib import Path
import re

RECEIPT = '.renegade-bink-identity.json'
LIBRARIES = ('avformat', 'avcodec', 'avutil', 'swscale', 'swresample')


def contents(prefix):
    files = {}
    for directory in ('include', 'lib', 'share'):
        base = prefix / directory
        if base.is_symlink():
            raise ValueError(f'Unexpected installed directory symlink: {base}')
        for path in sorted(base.rglob('*')):
            # FFmpeg's static installation contains ordinary files. Do not
            # follow a link out of the installation and bless unrelated bytes.
            if path.is_symlink():
                raise ValueError(f'Unexpected installed symlink: {path}')
            if path.is_file():
                files[path.relative_to(prefix).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    for name in LIBRARIES:
        if f'lib/lib{name}.a' not in files:
            raise ValueError(f'Missing installed library: {name}')
    if not any(name.startswith('include/') for name in files):
        raise ValueError('Missing installed FFmpeg headers')
    return files


def receipt(prefix, identity):
    if not re.fullmatch(r'[0-9a-f]{64}', identity):
        raise ValueError('Invalid FFmpeg input identity')
    return {'schema': 1, 'input_identity': identity, 'files': contents(prefix)}


def verify(prefix, identity):
    try:
        return json.loads((prefix / RECEIPT).read_text()) == receipt(prefix, identity)
    except (OSError, ValueError):
        return False


def record(prefix, identity):
    data = receipt(prefix, identity)
    temporary = prefix / (RECEIPT + '.pending')
    temporary.write_text(json.dumps(data, indent=2) + '\n')
    temporary.replace(prefix / RECEIPT)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('verify', 'record'))
    parser.add_argument('--prefix', type=Path, required=True)
    parser.add_argument('--identity', required=True)
    args = parser.parse_args()
    if args.operation == 'verify':
        return 0 if verify(args.prefix, args.identity) else 1
    record(args.prefix, args.identity)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
