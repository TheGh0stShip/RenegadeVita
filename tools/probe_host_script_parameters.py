#!/usr/bin/env python3
"""Exercise original script construction and parameter APIs without callbacks."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess


SCRIPT = '''import gdb, json
rows = []
def create(name):
    value = gdb.parse_and_eval('ScriptRegistrar::CreateScript("%s")' % name)
    if not int(value):
        raise RuntimeError('Expected script creation failed')
    return '((ScriptImpClass*)%d)' % int(value)
def set_params(obj, text):
    gdb.parse_and_eval(obj + '->Set_Parameters_String(' + json.dumps(text) + ')')
def check(label, actual, expected, tolerance=0):
    matches = abs(actual-expected) <= tolerance if tolerance else actual == expected
    rows.append(dict(label=label, actual=actual, expected=expected, matches=matches, status='unknown'))
damage = create('M00_Damage_Modifier_DME')
set_params(damage, '0.15,0,1,1,1')
check('case insensitive declared name', int(gdb.parse_and_eval(damage+'->Get_Parameter_Index("KILLABLE_BY_NOTSTAR")')), 4)
check('original underscore mismatch index', int(gdb.parse_and_eval(damage+'->Get_Parameter_Index("Killable_ByNotStar")')), -1)
check('original underscore mismatch integer', int(gdb.parse_and_eval(damage+'->Get_Int_Parameter("Killable_ByNotStar")')), 0)
check('declared underscore integer', int(gdb.parse_and_eval(damage+'->Get_Int_Parameter("Killable_by_NotStar")')), 1)
check('float conversion', float(gdb.parse_and_eval(damage+'->Get_Float_Parameter("Damage_multiplier")')), 0.15, 0.000001)
killed = create('M03_Killed_Sound')
set_params(killed, '1')
check('missing named value text', gdb.parse_and_eval(killed+'->Get_Parameter("Location")').string(), '')
check('missing named value integer', int(gdb.parse_and_eval(killed+'->Get_Int_Parameter("Location")')), 0)
set_params(killed, '')
check('empty set preserves previous arguments', int(gdb.parse_and_eval(killed+'->Get_Int_Parameter("Officer")')), 1)
set_params(killed, '2,')
check('trailing comma argument count', int(gdb.parse_and_eval(killed).dereference()['mArgC']), 2)
check('trailing comma text', gdb.parse_and_eval(killed+'->Get_Parameter((int)1)').string(), '')
set_params(killed, 'bad,17x')
check('nonnumeric integer text', int(gdb.parse_and_eval(killed+'->Get_Int_Parameter("Officer")')), 0)
check('integer numeric prefix', int(gdb.parse_and_eval(killed+'->Get_Int_Parameter("Location")')), 17)
patrol = create('M06_Hedgemaze_Patrol')
set_params(patrol, '7,1.5 -2.25 3')
vector = gdb.parse_and_eval(patrol+'->Get_Vector3_Parameter("Waypath_Loc")')
check('vector conversion', [float(vector[field]) for field in ('X','Y','Z')], [1.5,-2.25,3.0])
set_params(patrol, '7,broken')
vector = gdb.parse_and_eval(patrol+'->Get_Vector3_Parameter("Waypath_Loc")')
check('nonnumeric vector text', [float(vector[field]) for field in ('X','Y','Z')], [0.0,0.0,0.0])
print('PARAMETER_JSON:' + json.dumps(rows))
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
        '-ex', 'run --sorting-selftest lights', '-ex', 'python exec(' + repr(SCRIPT) + ')', str(binary)],
        capture_output=True, text=True, timeout=120,
        env={**os.environ, 'ASAN_OPTIONS': 'detect_leaks=0'})
    args.log.parent.mkdir(parents=True, exist_ok=True)
    args.log.write_text(result.stdout + result.stderr)
    payload = next((line.removeprefix('PARAMETER_JSON:') for line in result.stdout.splitlines()
                    if line.startswith('PARAMETER_JSON:')), None)
    if result.returncode or payload is None:
        raise SystemExit('Parameter probe failed; inspect retained log')
    rows = json.loads(payload)
    receipt = {
        'schema_version': 1, 'evidence_class': 'host_original_script_creation_and_parameter_execution',
        'binary_sha256': hashlib.sha256(binary.read_bytes()).hexdigest(),
        'parser_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'owner_source_sha256': {name: hashlib.sha256(Path(name).read_bytes()).hexdigest()
            for name in ('staging/scripts/scripts.cpp', 'staging/scripts/scripts.h',
                         'staging/scripts/ScriptRegistrar.cpp', 'staging/scripts/ScriptRegistrant.h',
                         'staging/scripts/Toolkit.cpp', 'staging/scripts/Mission03.cpp',
                         'staging/scripts/Mission06.cpp')},
        'total': len(rows), 'matched': sum(row['matches'] for row in rows), 'rows': rows,
        'scripts_created': 3,
        'limits': ['Synthetic values; no authored parameter payloads, gameplay objects or callbacks executed.',
                   'No mission impact, script state save/load, destruction or ARM/physical acceptance proof.',
                   'Three allocations live until bounded debugger process exit; leak checking disabled.',
                   'Numeric overflow, arbitrary locales, embedded NUL and long descriptions remain open.'],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2) + '\n')
    print(f"Original parameter cases matched {receipt['matched']}/{receipt['total']}")
    return 0 if receipt['matched'] == receipt['total'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
