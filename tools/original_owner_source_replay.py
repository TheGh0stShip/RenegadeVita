"""Replay an owner's ordered patches from pristine source to a target patch.

Uses a caller-owned temporary directory; never changes active staging.
"""
from pathlib import Path
import re
import subprocess
import hashlib
from tools.renegade_patch_inventory import load_inventory

ROOT = Path(__file__).resolve().parents[1]


def replay_to_patch(directory, component, names, target):
    directory = Path(directory)
    pristine = ROOT / 'upstream/CnC_Renegade/Code'
    folder = next(path for path in pristine.iterdir()
                  if path.is_dir() and path.name.lower() == component.lower())
    for name in names:
        source = next(path for path in folder.iterdir() if path.name.lower() == name.lower())
        directory.joinpath(name).write_bytes(source.read_bytes())
    for entry in load_inventory(ROOT)['patches']:
        if entry['stage_directory'] not in (component, ''):
            continue
        path = ROOT / entry['path']
        selected = []
        for block in re.split(rb'(?=^--- )', path.read_bytes(), flags=re.M):
            match = re.match(rb'--- (?:[ab]/)?([^\s]+)', block)
            if match:
                relative = match.group(1).decode()
                if entry['stage_directory'] == '':
                    prefix = component + '/'
                    if not relative.startswith(prefix):
                        continue
                    relative = relative[len(prefix):]
                if relative in names:
                    block = block.split(b'\ndiff --git ', 1)[0]
                    if not block.endswith(b'\n'):
                        block += b'\n'
                    if entry['stage_directory'] == '':
                        block = re.sub(rb'^(---|\+\+\+) ([ab]/)?' + component.encode() + rb'/',
                                       rb'\1 \2', block, flags=re.M)
                    selected.append(block)
        if not selected:
            continue
        before = {name: directory.joinpath(name).read_text(encoding='latin1') for name in names}
        result = subprocess.run(['patch', '--batch', '--forward', '--fuzz=0',
                                 '--no-backup-if-mismatch', '-p1', '-d', str(directory)],
                                input=b''.join(selected), capture_output=True)
        if result.returncode != 0:
            raise ValueError(f'{path.name}: replay failed: {result.stdout.decode()} {result.stderr.decode()}')
        if path.name == target:
            if target == 'combat-a35-action-observer-miss-telemetry.patch':
                expected = 'a8cc3e7149aeb6dcdf01bb87e7df176b2175aa8b5880888fa2ec25ffd91ce816'
                actual = hashlib.sha256(before['action.cpp'].encode('latin1')).hexdigest()
                if actual != expected:
                    raise ValueError(f'{target}: input identity mismatch: {actual}')
            if b'offset' in result.stdout:
                raise ValueError(f'{target}: target patch required an offset')
            return before, result
    raise ValueError(f'target patch not selected: {target}')
