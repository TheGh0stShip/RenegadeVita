#!/usr/bin/env python3
"""Check declared script candidates against the original live host registrar.

No script is instantiated and no retail/gameplay/device session is started.
"""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess


def script_candidates(inventory):
    rows = [row for row in inventory['registration_candidates'] if row['kind'] == 'script']
    for row in rows:
        if not re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*', row['arguments'][0]):
            raise ValueError('Script candidate is not a safe identifier')
    if not rows:
        raise ValueError('Script candidate denominator unavailable')
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', required=True, type=Path)
    parser.add_argument('--inventory', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--log', required=True, type=Path)
    parser.add_argument('--timeout', type=int, default=300)
    args = parser.parse_args()
    candidates = script_candidates(json.loads(args.inventory.read_text()))
    names = sorted({row['arguments'][0] for row in candidates})
    script = '''import gdb, hashlib, json
names = NAMES
negative = '__Renegade_Registry_Absent_Probe__'
if int(gdb.parse_and_eval('ScriptRegistrar::CreateScript("%s")' % negative)) != 0:
    raise RuntimeError('Expected-absent script resolved')
count = int(gdb.parse_and_eval('ScriptRegistrar::Count()'))
entries = []
pointer = gdb.parse_and_eval('ScriptRegistrar::mScriptFactories')
seen = set()
while int(pointer) != 0:
    address = int(pointer)
    if address in seen or len(seen) >= 4096:
        raise RuntimeError('Registry cycle or bound exceeded')
    seen.add(address)
    factory = pointer.dereference()
    index = len(entries)
    indexed = gdb.parse_and_eval('ScriptRegistrar::GetScriptFactory((int)%d)' % index)
    if int(indexed) != address:
        raise RuntimeError('Original indexed lookup disagrees with live registry')
    name = factory['ScriptName'].string()
    description = factory['ParamDescription'].string()
    entries.append({'name':name, 'parameter_description_sha256':hashlib.sha256(description.encode()).hexdigest()})
    pointer = factory['mNext']
if count != len(entries):
    raise RuntimeError('Original Count disagrees with traversed registry')
if int(gdb.parse_and_eval('ScriptRegistrar::GetScriptFactory((int)%d)' % count)) != 0:
    raise RuntimeError('Out-of-range indexed lookup did not return null')
lookups = {}
for name in names:
    actual = next((item['name'] for item in entries if item['name'].lower() == name.lower()), None)
    found = actual is not None
    lookups[name] = {'found':found, 'returned_name':actual, 'name_matches':bool(actual and actual.lower() == name.lower())}
print('SCRIPT_JSON:' + json.dumps({'count':count, 'entries':entries, 'lookups':lookups}))
'''.replace('NAMES', repr(names))
    binary = args.binary.resolve()
    result = subprocess.run([
        'gdb', '-q', '-batch', '-ex', 'set debuginfod enabled off',
        '-ex', 'set pagination off', '-ex', 'break main',
        '-ex', 'run --sorting-selftest lights',
        '-ex', 'python exec(' + repr(script) + ')', str(binary)],
        capture_output=True, text=True, timeout=args.timeout,
        env={**os.environ, 'ASAN_OPTIONS': 'detect_leaks=0'})
    args.log.parent.mkdir(parents=True, exist_ok=True)
    args.log.write_text(result.stdout + result.stderr)
    payload = next((line.removeprefix('SCRIPT_JSON:') for line in result.stdout.splitlines()
                    if line.startswith('SCRIPT_JSON:')), None)
    if result.returncode or payload is None:
        raise SystemExit('Debugger script lookup failed; inspect retained log')
    live = json.loads(payload)
    rows = [{'candidate_id': row['id'], 'name': row['arguments'][0],
             'source': row['source'], 'line': row['line'],
             'arm_selected_source': row['selected_for_target'],
             'arm_defined_symbol_match': bool(row['defined_symbol_matches']),
             **live['lookups'][row['arguments'][0]],
             'status': 'unknown', 'evidence_class': 'host_original_script_index_lookup_and_arm_metadata'}
            for row in candidates]
    grouped = Counter(entry['name'].lower() for entry in live['entries'])
    receipt = {'schema_version': 1, 'complete': False, 'total': len(rows), 'rows': rows,
               'counts': dict(Counter(row['status'] for row in rows)),
               'registry_count': live['count'], 'registry_entries': live['entries'],
               'candidate_names': len(names),
               'matched_candidates': sum(row['name_matches'] for row in rows),
               'unmatched_candidates': sum(not row['found'] for row in rows),
               'duplicate_registry_names': sorted(name for name, count in grouped.items() if count > 1),
               'registry_names_without_candidate': sorted(entry['name'] for entry in live['entries']
                    if entry['name'].lower() not in {name.lower() for name in names}),
               'binary_sha256': hashlib.sha256(binary.read_bytes()).hexdigest(),
               'inventory_sha256': hashlib.sha256(args.inventory.read_bytes()).hexdigest(),
               'parser_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               'negative_control': 'CreateScript for an absent name and indexed lookup beyond Count returned null.',
               'candidate_match_method': 'Case-insensitive comparison against the live index-verified registry.',
               'limits': ['Inactive, excluded and header macro declarations remain source candidates.',
                          'Host lookup does not prove ARM initialization or mission script execution.',
                          'Parameter descriptor hashes do not prove retail parameter compatibility.',
                          'Name-only lookup method was not retained in this ELF; candidate names matched from indexed entries.',
                          'Valid script creation, callbacks, timers and save/load remain untested.',
                          'Debugger leak checking disabled; prior sanitizer evidence is separate.']}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({key: receipt[key] for key in ('total', 'candidate_names', 'registry_count',
                                                  'matched_candidates', 'unmatched_candidates')}))


if __name__ == '__main__':
    main()
