"""Read shared retail control texts through original host FileFactory/MIX commands.

Outputs hashes/counts only. Retail bytes remain inside the local debugger.
"""
import argparse
import hashlib
import json
import os
import shlex
from pathlib import Path
import subprocess
from tools.renegade_cinematic_dependency_scan import MixArchive


def expected(payload):
    lines = []
    offset = 0
    while offset < len(payload):
        end = payload.find(b'\n', offset)
        end = len(payload) if end < 0 else end + 1
        line = payload[offset:end][:199].split(b'\0', 1)[0]
        offset = end
        if not line: break
        lines.append(line)
    return hashlib.sha256(b'\0'.join(lines)).hexdigest(), len(lines)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('binary','retail-root','work','output'):
        p.add_argument('--'+name,type=Path,required=True)
    args = p.parse_args()
    archives = {x.name.lower():x for x in (args.retail_root/'Data').iterdir()}
    candidates = {}
    identities = {}
    for name in ('always2.dat','always.dbs','always.dat'):
        path = archives[name]; archive = MixArchive(path)
        identities[name] = hashlib.sha256(path.read_bytes()).hexdigest()
        for member in archive.entries:
            if member.endswith('.txt'):
                candidates.setdefault(member,[]).append(expected(archive.read_binary(member)))
    script = '''import gdb,json,hashlib
buffer=gdb.parse_and_eval('(char*)malloc(200)')
address=int(buffer)
rows=[]
for name in '''+repr(sorted(candidates))+''':
 handle=int(gdb.parse_and_eval('Text_File_Open('+json.dumps(name)+')'))
 lines=[]
 if handle:
  while int(gdb.parse_and_eval('Text_File_Get_String(%d,(char*)%d,199)'%(handle,address))):
   line=bytes(gdb.selected_inferior().read_memory(address,200)).split(b'\\0',1)[0]
   lines.append(line)
  gdb.parse_and_eval('Text_File_Close(%d)'%handle)
 rows.append(dict(member=name,opened=bool(handle),lines=len(lines),sha256=hashlib.sha256(b'\\0'.join(lines)).hexdigest(),status='unknown'))
gdb.parse_and_eval('(void)free((void*)%d)'%address)
print('MIX_TEXT_JSON:'+json.dumps(rows))
'''
    args.work.mkdir(parents=True,exist_ok=True)
    roots=[args.retail_root.resolve()]+[(args.work/name).resolve() for name in ('user','cache','mods')]
    for root in roots[1:]: root.mkdir(parents=True,exist_ok=True)
    result=subprocess.run(['gdb','-q','-batch','-ex','set debuginfod enabled off',
       '-ex','set pagination off','-ex','break a31_interactive_main.cpp:1182',
       '-ex','run '+' '.join(shlex.quote(str(root)) for root in roots),'-ex','python exec('+repr(script)+')',
       str(args.binary.resolve())],capture_output=True,text=True,timeout=180,
       env={**os.environ,'ASAN_OPTIONS':'detect_leaks=0'})
    (args.work/'debugger.log').write_text(result.stdout+result.stderr)
    payload=next((x.removeprefix('MIX_TEXT_JSON:') for x in result.stdout.splitlines() if x.startswith('MIX_TEXT_JSON:')),None)
    if result.returncode or payload is None: raise SystemExit('MIX text probe failed; inspect private debugger log')
    rows=json.loads(payload)
    for row in rows: row['matches_archive_candidate']=row['opened'] and (row['sha256'],row['lines']) in candidates[row['member']]
    receipt={'schema_version':1,'evidence_class':'host_original_mix_text_command_execution',
       'binary_sha256':hashlib.sha256(args.binary.read_bytes()).hexdigest(),
       'probe_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
       'archive_sha256':identities,'total':len(rows),'matched':sum(x['matches_archive_candidate'] for x in rows),
       'rows':rows,'limits':['Shared archives only; per-map controls and always3.dat remain outside this denominator.',
          'Debugger stops after original factory setup; no world, script dispatch or playback.',
          'Leak checking disabled for debugger; host I/O does not prove physical I/O.']}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(receipt,indent=2)+'\n')
    print('Shared MIX text transport matched %d/%d'%(receipt['matched'],receipt['total']))
    return 0 if receipt['matched']==receipt['total'] else 1


if __name__=='__main__': raise SystemExit(main())
