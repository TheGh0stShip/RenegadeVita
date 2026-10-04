"""Inspect original initialized ScriptCommands pointers in a bounded host process."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
from tools.audit_script_command_table import table_assignments
from tools.audit_sweep_scripts import command_slots
from tools.audit_sweep_link import defined_symbols


def script(names):
    return '''import gdb,json
table=gdb.parse_and_eval('Get_Script_Commands()').dereference()
rows=[]
for name in ''' + repr(names) + ''':
 value=table[name]
 address=int(value)
 symbol=gdb.execute('info symbol %d' % address,to_string=True).strip() if address else ''
 symbol=symbol.split(' in section ')[0]
 rows.append(dict(name=name,nonnull=bool(address),symbol=symbol,status='unknown'))
print('COMMAND_TABLE_JSON:'+json.dumps(rows))
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('binary', 'output', 'log'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--arm-symbols', type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    header = root/'upstream/CnC_Renegade/Code/Scripts/scriptcommands.h'
    owner = root/'staging/combat/scriptcommands.cpp'
    names = [row['name'] for row in command_slots(header.read_text(encoding='latin1'))]
    assignments = table_assignments(owner.read_text(encoding='latin1'))
    result = subprocess.run(['gdb','-q','-batch','-ex','set debuginfod enabled off',
        '-ex','set pagination off','-ex','break main','-ex','run --sorting-selftest lights',
        '-ex','python exec('+repr(script(names))+')',str(args.binary.resolve())],
        capture_output=True,text=True,timeout=120,env={**os.environ,'ASAN_OPTIONS':'detect_leaks=0'})
    args.log.parent.mkdir(parents=True,exist_ok=True)
    args.log.write_text(result.stdout+result.stderr)
    payload = next((line.removeprefix('COMMAND_TABLE_JSON:') for line in result.stdout.splitlines()
                    if line.startswith('COMMAND_TABLE_JSON:')),None)
    if result.returncode or payload is None:
        raise SystemExit('Command table probe failed; inspect private log')
    rows = json.loads(payload)
    for row in rows:
        row['assigned_name_match'] = any(row['symbol'].startswith(name+'(')
                                        for name in assignments.get(row['name'],[]))
    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    receipt = {'schema_version':1,'evidence_class':'host_original_command_table_initialization',
        'binary_sha256':digest(args.binary),'probe_sha256':digest(Path(__file__)),
        'source_sha256':{'staging/combat/scriptcommands.cpp':digest(owner),
                        'upstream/CnC_Renegade/Code/Scripts/scriptcommands.h':digest(header)},
        'total':len(rows),'nonnull':sum(r['nonnull'] for r in rows),
        'assigned_name_matches':sum(r['assigned_name_match'] for r in rows),'rows':rows,
        'limits':['Debugger calls original Get_Script_Commands at main; normal startup ordering is unproven.',
                  'No command callbacks, gameplay, retail data or ARM/physical execution tested.',
                  'Leak checking disabled for debugger operation; this is not a sanitizer or leak result.']}
    if args.arm_symbols:
        symbols = defined_symbols(args.arm_symbols.read_bytes())
        for row in rows:
            row['arm_function_signature_retained'] = any(entry['type'] in 'TtWw'
                for entry in symbols.get(row['symbol'], []))
        receipt['arm_symbols_sha256'] = digest(args.arm_symbols)
        receipt['arm_function_signatures_retained'] = sum(r['arm_function_signature_retained'] for r in rows)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(receipt,indent=2)+'\n')
    print('Command table matched %d/%d' % (receipt['assigned_name_matches'],receipt['total']))
    return 0 if receipt['assigned_name_matches']==receipt['total'] else 1


if __name__=='__main__':
    raise SystemExit(main())
