"""Replay only original effect source hunks in a caller-owned temporary tree.

Never executes staging scripts, compilers, builds or game code.
"""
from pathlib import Path
import hashlib
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
NAMES = ('dazzle.cpp', 'decalmsh.cpp', 'mesh.cpp', 'ww3d.cpp')
ANCHORS = {
    'ww3d-a35-original-dazzle-lifecycle.patch': {
        'dazzle.cpp': '2bbcba91d75327b7fa35b4c1f50718ab05d3b252a687a78d0b3c62a90dfefd58',
        'ww3d.cpp': '32fdca663f7bfffede2b64b1fbafcc1bd0af81b15f46e4dc24aef84e59bd55c6'},
    'ww3d-a35-original-decal-submission.patch': {
        'ww3d.cpp': 'a6880363b1bcf43e65d69ace09b3f29248da5483c9d80258ddbad630066ebeb3',
        'decalmsh.cpp': 'a235a5a53c279f59d92099b1efb7ccaa039ba83cec176b9162ede5c7e1d64d4b',
        'mesh.cpp': '628232c017e9ffe25ec68d4732e133b31f13094c2653322c95a5e06319d137ca'}}


def replay(directory):
    directory = Path(directory)
    for name in NAMES:
        directory.joinpath(name).write_bytes((ROOT / 'upstream/CnC_Renegade/Code/ww3d2' / name).read_bytes())
    stage = (ROOT / 'tools/stage_sources.sh').read_text()
    paths = re.findall(r'-d "\$rv_stage/ww3d2" -p1 < "\$rv_root/port/patches/([^"]+)"', stage)
    seen = set()
    receipt = []
    for name in paths:
        path = ROOT / 'port/patches' / name
        selected = []
        for block in re.split(r'(?=^--- )', path.read_text(), flags=re.M):
            match = re.match(r'--- (?:a/)?([^\s]+)', block)
            if match and match.group(1) in NAMES:
                selected.append(block)
        if not selected:
            continue
        for file, expected in ANCHORS.get(name, {}).items():
            actual = hashlib.sha256(directory.joinpath(file).read_bytes()).hexdigest()
            if actual != expected:
                raise ValueError(f'{name}: input identity mismatch for {file}: {actual}')
        result = subprocess.run(['patch', '--batch', '--forward', '--fuzz=0',
                                 '--no-backup-if-mismatch', '-p1', '-d', str(directory)],
                                input=''.join(selected).encode(), capture_output=True, check=True)
        offset = b'offset' in result.stdout
        if name in ANCHORS:
            seen.add(name)
            if offset:
                raise ValueError(f'{name}: restoration requires an offset')
        receipt.append({'patch': name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                        'historical_offset': offset})
    if seen != set(ANCHORS):
        raise ValueError('staging script omitted a required effect restoration')
    return receipt
