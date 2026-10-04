#!/usr/bin/env python3
"""Check original host network factory lookup without creating objects or packets."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess


def expected_factories(symbols):
    factories = {}
    for name, value in re.findall(
            r'SimpleNetworkObjectFactoryClass<([^\n]+?), (-?\d+)>::Get_Class_ID\(\) const',
            symbols):
        factories.setdefault(int(value) & 0xffffffff, set()).add(name)
    return [{'class_id': value, 'classes': sorted(names)}
            for value, names in sorted(factories.items())]


def debugger_script(expected):
    # Only numeric IDs become debugger expressions; class names remain data.
    return '''import gdb, json
expected = EXPECTED
seen = set()
live = []
factory = gdb.parse_and_eval('NetworkObjectFactoryMgrClass::_FactoryListHead')
previous = 0
while int(factory):
    address = int(factory)
    if address in seen or len(seen) >= 4096:
        raise RuntimeError('Registry cycle or traversal bound exceeded')
    seen.add(address)
    obj = factory.dereference()
    if int(obj['PrevFactory']) != previous:
        raise RuntimeError('Broken reverse factory link')
    value = int(gdb.parse_and_eval('((NetworkObjectFactoryClass*)%d)->Get_Class_ID()' % address))
    lookup = gdb.parse_and_eval('NetworkObjectFactoryMgrClass::Find_Factory((unsigned int)%d)' % value)
    if int(lookup) != address:
        raise RuntimeError('Duplicate ID or lookup/list mismatch')
    live.append(value)
    previous = address
    factory = obj['NextFactory']
absent = next(value for value in range(1024) if value not in set(live))
if int(gdb.parse_and_eval('NetworkObjectFactoryMgrClass::Find_Factory((unsigned int)%d)' % absent)):
    raise RuntimeError('Absent ID returned a factory')
rows = []
for item in expected:
    value = item['class_id']
    found = int(gdb.parse_and_eval('NetworkObjectFactoryMgrClass::Find_Factory((unsigned int)%d)' % value)) != 0
    rows.append(dict(item, found=found, matches=found and value in live))
print('NETWORK_JSON:' + json.dumps(dict(rows=rows, live_ids=sorted(live))))
'''.replace('EXPECTED', repr(expected))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ('binary', 'arm-symbols', 'output', 'log'):
        parser.add_argument('--' + option, required=True, type=Path)
    parser.add_argument('--timeout', type=int, default=120)
    args = parser.parse_args()
    binary = args.binary.resolve()
    symbols = subprocess.check_output(['nm', '-C', '--defined-only', str(binary)], text=True)
    expected = expected_factories(symbols)
    arm = {row['class_id']: row['classes'] for row in expected_factories(args.arm_symbols.read_text())}
    if not expected or not arm:
        raise SystemExit('Network template symbol denominator unavailable')
    result = subprocess.run([
        'gdb', '-q', '-batch', '-ex', 'set debuginfod enabled off',
        '-ex', 'set pagination off', '-ex', 'break main',
        '-ex', 'run --sorting-selftest lights',
        '-ex', 'python exec(' + repr(debugger_script(expected)) + ')', str(binary)],
        capture_output=True, text=True, timeout=args.timeout,
        env={**os.environ, 'ASAN_OPTIONS': 'detect_leaks=0'})
    args.log.parent.mkdir(parents=True, exist_ok=True)
    args.log.write_text(result.stdout + result.stderr)
    payload = next((line.removeprefix('NETWORK_JSON:') for line in result.stdout.splitlines()
                    if line.startswith('NETWORK_JSON:')), None)
    if result.returncode or payload is None:
        raise SystemExit('Debugger probe failed; inspect retained log')
    data = json.loads(payload)
    rows = data['rows']
    for row in rows:
        row.update(arm_classes=arm.get(row['class_id'], []),
                   arm_symbol_present=row['class_id'] in arm, status='unknown')
    expected_ids = {row['class_id'] for row in rows}
    receipt = {
        'schema_version': 1,
        'evidence_class': 'host_original_network_lookup_and_arm_symbols',
        'binary_sha256': hashlib.sha256(binary.read_bytes()).hexdigest(),
        'symbol_listing_sha256': hashlib.sha256(symbols.encode()).hexdigest(),
        'arm_symbols_sha256': hashlib.sha256(args.arm_symbols.read_bytes()).hexdigest(),
        'parser_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'owner_source_sha256': {
            name: hashlib.sha256(Path(name).read_bytes()).hexdigest()
            for name in ('staging/wwnet/networkobjectfactory.h',
                         'staging/wwnet/networkobjectfactory.cpp',
                         'staging/wwnet/networkobjectfactorymgr.cpp',
                         'staging/combat/basegameobj.cpp',
                         'port/platform/renegade_tt_purchase_network.cpp')},
        'total': len(rows), 'matched': sum(row['matches'] for row in rows),
        'live_factory_count': len(data['live_ids']),
        'live_ids': data['live_ids'],
        'live_non_template_ids': sorted(set(data['live_ids']) - expected_ids),
        'arm_template_ids': len(arm), 'arm_only_ids': sorted(set(arm) - expected_ids),
        'rows': rows,
        'negative_control': 'An absent ID returned null.',
        'limits': ['Host static initialization and lookup only; ARM initialization remains open.',
                   'No object creation, packet handling, network traffic or device interaction.',
                   'Template symbols do not enumerate custom factory subclasses.',
                   'Debugger leak checking disabled; sanitizer evidence remains separate.'],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2) + '\n')
    print(f"Network lookup matched {receipt['matched']}/{len(rows)}; live {len(data['live_ids'])}; ARM {len(arm)}")
    return 0 if receipt['matched'] == len(rows) else 1


if __name__ == '__main__':
    raise SystemExit(main())
