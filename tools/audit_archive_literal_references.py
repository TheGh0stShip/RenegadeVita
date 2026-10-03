"""Read-only literal-name evidence; no reference is never exclusion proof."""
import argparse
import json
from pathlib import Path
from renegade_cinematic_dependency_scan import MixArchive
from audit_dds_format_inventory import file_sha256


def matches(stream, offset, size, needles, block_size=1024 * 1024):
    stream.seek(offset)
    overlap = max(map(len, needles), default=1) - 1
    tail, consumed = b'', 0
    while consumed < size:
        block = stream.read(min(block_size, size - consumed))
        if not block:
            raise ValueError('truncated member')
        data = (tail + block).lower()
        base = consumed - len(tail)
        for needle in needles:
            start = 0
            while True:
                found = data.find(needle, start)
                if found < 0:
                    break
                if base + found + len(needle) > consumed:
                    yield needle.decode('ascii'), base + found
                start = found + 1
        consumed += len(block)
        tail = data[-overlap:] if overlap else b''


def audit(directory, names):
    needles = sorted({name.lower().encode('ascii') for name in names})
    if not needles or any(not needle for needle in needles):
        raise ValueError('nonempty literal names required')
    hits, archives, count = [], [], 0
    for path in sorted(directory.iterdir()):
        if path.suffix.lower() not in ('.mix', '.dat', '.dbs') or not path.is_file():
            continue
        archive = MixArchive(path)
        archives.append({'archive': path.name, 'sha256': file_sha256(path)})
        with path.open('rb') as stream:
            for index, (name, _, offset, size) in enumerate(archive.entry_records):
                count += 1
                hits.extend({'archive': path.name, 'member': name, 'index_record': index,
                             'name': literal, 'byte_offset': position}
                            for literal, position in matches(stream, offset, size, needles))
    return {'complete': False, 'names': sorted(set(names)), 'archives': archives,
            'members_scanned': count, 'hits': hits,
            'limit': 'Literal byte references only; absence does not prove exclusion. Computed names, loose files, mount order and execution remain open.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--name', action='append', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.data, args.name)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'members_scanned': result['members_scanned'], 'hits': len(result['hits'])}))
