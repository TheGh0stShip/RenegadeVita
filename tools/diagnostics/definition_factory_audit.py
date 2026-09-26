#!/usr/bin/env python3
"""Compare unchanged DDB definition chunks with an executable's original factories.

Outputs class counts and registration evidence, never asset contents. This does
not prove that a registered factory implements a server's full behavior.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from renegade_cinematic_dependency_scan import MixArchive


def chunks(data, start, end):
    while start < end:
        if end - start < 8:
            raise ValueError('truncated chunk header')
        kind, size = struct.unpack_from('<II', data, start)
        stop = start + 8 + (size & 0x7fffffff)
        if stop > end:
            raise ValueError('chunk outside parent')
        yield kind, start + 8, stop
        start = stop


def definition_classes(data):
    counts = Counter()
    # SaveLoad DEFMGR -> DefinitionMgr::CHUNKID_OBJECTS -> PersistFactory ID.
    for kind, start, end in chunks(data, 0, len(data)):
        if kind == 0x101:
            for child, begin, stop in chunks(data, start, end):
                if child == 0x101:
                    counts.update(kind for kind, _, _ in chunks(data, begin, stop))
    return counts


def registered(binary, classes):
    ids = sorted(classes)
    result = {}
    for offset in range(0, len(ids), 256):
        selected = ids[offset:offset + 256]
        run = subprocess.run([str(binary), '--persist-factories', *map(str, selected)],
                             check=True, text=True, capture_output=True, timeout=30)
        found = {int(key): value == '1' for key, value in
                 re.findall(r'^persist_factory\.(\d+)=([01])$', run.stdout, re.M)}
        if set(found) != set(selected):
            raise ValueError('incomplete executable registration response')
        result.update(found)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', type=Path, required=True)
    parser.add_argument('archives', type=Path, nargs='+')
    args = parser.parse_args()
    records = []
    all_classes = set()
    for path in args.archives:
        archive = MixArchive(path)
        for name in sorted(archive.entries):
            if not name.endswith('.ddb'):
                continue
            data = archive.read_binary(name)
            counts = definition_classes(data)
            all_classes.update(counts)
            records.append(dict(archive=path.name, member=name,
                                sha256=hashlib.sha256(data).hexdigest(), classes=dict(counts)))
    factories = registered(args.binary.resolve(), all_classes)
    for row in records:
        row['missing'] = {key: count for key, count in row['classes'].items() if not factories[key]}
    print(json.dumps(dict(schema=1, evidence_class='host',
        binary_sha256=hashlib.sha256(args.binary.read_bytes()).hexdigest(),
        records=records, registered=factories), indent=2))
    return 1 if any(row['missing'] for row in records) else 0


if __name__ == '__main__':
    raise SystemExit(main())
