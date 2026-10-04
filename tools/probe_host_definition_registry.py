#!/usr/bin/env python3
"""Verify original definition factory ID lookups after host initialization.

Definition class IDs are not persistence chunk IDs. No Create/Load calls occur.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess


def expected_definitions(symbols):
    rows = {}
    pattern = (r'SimpleDefinitionFactoryClass<([^\n]+?), (-?\d+), '
               r'[^\n]+>::Get_Class_ID\(\) const')
    for match in re.finditer(pattern, symbols):
        name, value = match.groups()
        rows.setdefault(int(value) & 0xffffffff, set()).add(name)
    return [{'class_id': value, 'classes': sorted(names)}
            for value, names in sorted(rows.items())]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', required=True, type=Path)
    parser.add_argument('--arm-symbols', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--log', required=True, type=Path)
    parser.add_argument('--timeout', type=int, default=120)
    args = parser.parse_args()
    binary = args.binary.resolve()
    symbols = subprocess.check_output(['nm', '-C', '--defined-only', str(binary)], text=True)
    expected = expected_definitions(symbols)
    arm = {row['class_id']: row['classes']
           for row in expected_definitions(args.arm_symbols.read_text())}
    if not expected or not arm:
        raise SystemExit('Template definition symbol denominator unavailable')
    script = '''import gdb, json
expected = EXPECTED
rows = []
absent = next(value for value in range(1024) if value not in {item['class_id'] for item in expected})
if int(gdb.parse_and_eval('DefinitionFactoryMgrClass::Find_Factory((unsigned int)%d)' % absent)) != 0:
    raise RuntimeError('Expected-absent class lookup returned a factory')
for item in expected:
    value = item['class_id']
    factory = gdb.parse_and_eval('DefinitionFactoryMgrClass::Find_Factory((unsigned int)%d)' % value)
    actual = None
    if int(factory) != 0:
        actual = int(gdb.parse_and_eval('((DefinitionFactoryClass*)%d)->Get_Class_ID()' % int(factory)))
    rows.append(dict(item, found=int(factory) != 0, returned_class_id=actual, matches=actual == value))
print('DEFINITION_JSON:' + json.dumps(rows))
'''.replace('EXPECTED', repr(expected))
    result = subprocess.run([
        'gdb', '-q', '-batch', '-ex', 'set debuginfod enabled off',
        '-ex', 'set pagination off', '-ex', 'break main',
        '-ex', 'run --sorting-selftest lights',
        '-ex', 'python exec(' + repr(script) + ')', str(binary)],
        capture_output=True, text=True, timeout=args.timeout,
        env={**os.environ, 'ASAN_OPTIONS': 'detect_leaks=0'})
    args.log.parent.mkdir(parents=True, exist_ok=True)
    args.log.write_text(result.stdout + result.stderr)
    payload = next((line.removeprefix('DEFINITION_JSON:') for line in result.stdout.splitlines()
                    if line.startswith('DEFINITION_JSON:')), None)
    if result.returncode or payload is None:
        raise SystemExit('Debugger probe failed; inspect retained log')
    rows = json.loads(payload)
    for row in rows:
        row['arm_classes'] = arm.get(row['class_id'], [])
        row['arm_symbol_present'] = bool(row['arm_classes'])
        row['status'] = 'unknown'
    receipt = {
        'schema_version': 1, 'evidence_class': 'host_original_definition_lookup_and_arm_symbols',
        'binary_sha256': hashlib.sha256(binary.read_bytes()).hexdigest(),
        'symbol_listing_sha256': hashlib.sha256(symbols.encode()).hexdigest(),
        'arm_symbols_sha256': hashlib.sha256(args.arm_symbols.read_bytes()).hexdigest(),
        'parser_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'total': len(rows), 'matched': sum(row['matches'] for row in rows),
        'arm_template_ids': len(arm),
        'arm_only_ids': sorted(set(arm) - {r['class_id'] for r in rows}), 'rows': rows,
        'negative_control': 'An absent class ID returned null.',
        'limits': ['Template Get_Class_ID symbol denominator only; manual forms remain open.',
                   'Host lookup does not prove ARM initialization or physical correctness.',
                   'Create, Load/Save, retail references and name lookup remain untested.',
                   'Debugger leak checking disabled; prior sanitizer evidence is separate.'],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2) + '\n')
    print(f"Definition lookup matched {receipt['matched']}/{receipt['total']} IDs; ARM has {len(arm)}")
    return 0 if receipt['matched'] == receipt['total'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
