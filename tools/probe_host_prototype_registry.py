#!/usr/bin/env python3
"""Inspect original prototype loaders after retail-free host WW3D initialization."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess


def probe_script():
    return '''import gdb, json
result = int(gdb.parse_and_eval('WW3D::Init((void*)0, (char*)0, true)'))
if result != 0:
    raise RuntimeError('WW3D initialization failed')
manager = gdb.parse_and_eval('WW3DAssetManager::TheInstance')
if int(manager):
    raise RuntimeError('Unexpected preexisting asset manager')
storage = int(gdb.parse_and_eval('(void*)malloc(sizeof(WW3DAssetManager))'))
if not storage:
    raise RuntimeError('Asset manager allocation failed')
gdb.parse_and_eval("((void (*)(void*)) &'_ZN16WW3DAssetManagerC1Ev')((void*)%d)" % storage)
manager = gdb.parse_and_eval('WW3DAssetManager::TheInstance')
if int(manager) != storage:
    raise RuntimeError('Constructor did not publish the manager')
loaders = manager.dereference()['PrototypeLoaders']
count = int(loaders['ActiveCount'])
if not 0 < count <= 256:
    raise RuntimeError('Prototype loader count outside bound')
rows = []
seen = set()
for index in range(count):
    loader = loaders['Vector'][index]
    if not int(loader):
        raise RuntimeError('Null loader')
    address = int(loader)
    chunk = int(gdb.parse_and_eval('((PrototypeLoaderClass*)%d)->Chunk_Type()' % address))
    found = gdb.parse_and_eval('((WW3DAssetManager*)%d)->Find_Prototype_Loader((int)%d)' % (int(manager), chunk))
    if int(found) != address or chunk in seen:
        raise RuntimeError('Duplicate chunk or lookup/list mismatch')
    seen.add(chunk)
    rows.append(dict(index=index, loader_class=str(loader.dereference().dynamic_type), chunk_id=chunk, lookup_matches=True, status='unknown'))
absent = next(value for value in range(1024) if value not in seen)
if int(gdb.parse_and_eval('((WW3DAssetManager*)%d)->Find_Prototype_Loader((int)%d)' % (int(manager), absent))):
    raise RuntimeError('Absent chunk returned a loader')
print('PROTOTYPE_JSON:' + json.dumps(rows))
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ('binary', 'output', 'log'):
        parser.add_argument('--' + option, required=True, type=Path)
    args = parser.parse_args()
    binary = args.binary.resolve()
    result = subprocess.run([
        'gdb', '-q', '-batch', '-ex', 'set debuginfod enabled off',
        '-ex', 'set pagination off', '-ex', 'break main',
        '-ex', 'run --sorting-selftest lights',
        '-ex', 'python exec(' + repr(probe_script()) + ')', str(binary)],
        capture_output=True, text=True, timeout=120,
        env={**os.environ, 'ASAN_OPTIONS': 'detect_leaks=0'})
    args.log.parent.mkdir(parents=True, exist_ok=True)
    args.log.write_text(result.stdout + result.stderr)
    payload = next((line.removeprefix('PROTOTYPE_JSON:') for line in result.stdout.splitlines()
                    if line.startswith('PROTOTYPE_JSON:')), None)
    if result.returncode or payload is None:
        raise SystemExit('Debugger probe failed; inspect retained log')
    rows = json.loads(payload)
    receipt = {
        'schema_version': 1, 'evidence_class': 'host_original_ww3d_initialization_and_prototype_lookup',
        'binary_sha256': hashlib.sha256(binary.read_bytes()).hexdigest(),
        'parser_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'owner_source_sha256': {name: hashlib.sha256(Path(name).read_bytes()).hexdigest()
                                for name in ('staging/ww3d2/assetmgr.cpp', 'staging/ww3d2/assetmgr.h',
                                             'staging/ww3d2/ww3d.cpp')},
        'total': len(rows), 'matched': sum(row['lookup_matches'] for row in rows),
        'rows': rows, 'negative_control': 'An absent chunk ID returned null.',
        'limits': ['Host original asset-manager constructor only; Vita startup adds further loaders.',
                   'No retail data, prototype loading or rendering exercised.',
                   'ARM activation and physical correctness remain unverified.',
                   'Allocation lives until debugger process exit; destructor/shutdown untested.',
                   'Debugger leak checking disabled; sanitizer evidence is separate.'],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2) + '\n')
    print(f"Prototype lookup matched {receipt['matched']}/{receipt['total']}")


if __name__ == '__main__':
    main()
