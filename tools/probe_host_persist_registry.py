#!/usr/bin/env python3
"""Run original persistence lookup after static initialization in a host ELF.

No retail assets or factory Load/Save calls are used. Symbol presence defines
the expected denominator; runtime lookup is separate evidence. Not Vita proof.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess


def expected_factories(symbols):
    rows = {}
    for match in re.finditer(
            r'SimplePersistFactoryClass<([^\n]+), (-?\d+)>::Chunk_ID\(\) const', symbols):
        name, value = match.groups()
        chunk = int(value) & 0xffffffff
        rows.setdefault(chunk, set()).add(name)
    return [{'chunk_id': chunk, 'classes': sorted(names)}
            for chunk, names in sorted(rows.items())]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--log', required=True, type=Path)
    parser.add_argument('--timeout', type=int, default=120)
    args = parser.parse_args()
    binary = args.binary.resolve()
    symbols = subprocess.check_output(['nm', '-C', '--defined-only', str(binary)], text=True)
    expected = expected_factories(symbols)
    if not expected:
        raise SystemExit('No template factory Chunk_ID symbols; denominator unavailable')
    # This script is generated solely from numeric IDs and fixed expressions.
    # Never feed external issue text or retail parameters into debugger commands.
    script = '''import gdb, json
expected = EXPECTED
rows = []
absent = next(value for value in range(1024) if value not in {item['chunk_id'] for item in expected})
if int(gdb.parse_and_eval('SaveLoadSystemClass::Find_Persist_Factory((unsigned int)%d)' % absent)) != 0:
    raise RuntimeError('Expected-absent lookup returned a factory')
for item in expected:
    chunk = item['chunk_id']
    factory = gdb.parse_and_eval('SaveLoadSystemClass::Find_Persist_Factory((unsigned int)%d)' % chunk)
    actual = None
    if int(factory) != 0:
        actual = int(gdb.parse_and_eval('((PersistFactoryClass*)%d)->Chunk_ID()' % int(factory)))
    rows.append(dict(item, found=int(factory) != 0, returned_chunk_id=actual, matches=actual == chunk))
print('REGISTRY_JSON:' + json.dumps(rows))
'''.replace('EXPECTED', repr(expected))
    result = subprocess.run([
        'gdb', '-q', '-batch', '-ex', 'set debuginfod enabled off',
        '-ex', 'set pagination off', '-ex', 'break main',
        '-ex', 'run --sorting-selftest lights',
        '-ex', 'python exec(' + repr(script) + ')', str(binary)],
        capture_output=True, text=True, timeout=args.timeout,
        env={**os.environ, 'ASAN_OPTIONS': 'detect_leaks=0'})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.log.parent.mkdir(parents=True, exist_ok=True)
    args.log.write_text(result.stdout + result.stderr)
    payload = next((line.removeprefix('REGISTRY_JSON:') for line in result.stdout.splitlines()
                    if line.startswith('REGISTRY_JSON:')), None)
    if result.returncode or payload is None:
        raise SystemExit('Debugger probe failed; inspect retained log')
    rows = json.loads(payload)
    receipt = {
        'schema_version': 1, 'evidence_class': 'host_original_factory_runtime_lookup',
        'binary_sha256': hashlib.sha256(binary.read_bytes()).hexdigest(),
        'symbol_listing_sha256': hashlib.sha256(symbols.encode()).hexdigest(),
        'total': len(rows), 'matched': sum(row['matches'] for row in rows), 'rows': rows,
        'negative_control': 'An ID absent from the symbol denominator returned null.',
        'limits': ['Host graph only; no ARM or physical acceptance.',
                   'Template Chunk_ID symbol denominator only; other factory forms remain open.',
                   'Lookup verifies IDs, not Load/Save, retail closure or class identity.',
                   'Breakpoint at main verifies static initialization only.',
                   'Debugger run disables leak checking; prior sanitizer runs are separate.'],
    }
    args.output.write_text(json.dumps(receipt, indent=2) + '\n')
    print(f"Runtime lookup matched {receipt['matched']}/{receipt['total']} IDs")
    return 0 if receipt['matched'] == receipt['total'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
