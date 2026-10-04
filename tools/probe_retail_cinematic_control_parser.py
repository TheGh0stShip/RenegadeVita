"""Compare original compiled cinematic scheduling against all archive text members."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
from tools.audit_cinematic_slots import time_seconds, ASCII_SPACE
from tools.renegade_cinematic_dependency_scan import MixArchive


def reference(payload):
    records=[]
    lines=payload.split(b'\n')
    signed_char_space=ASCII_SPACE+''.join(chr(value) for value in range(128,256))
    for index,raw in enumerate(lines):
        if index<len(lines)-1: raw+=b'\n'
        raw=raw[:199].split(b'\0',1)[0]
        if not raw: break
        text=raw.replace(b'\t',b' ').decode('latin1').strip(signed_char_space)
        if not text or text.startswith(';'): continue
        parts=re.match(r'^([^\x00-\x20\x80-\xff]+)[\x00-\x20\x80-\xff]+(.+)$',text)
        if not parts: continue
        seconds=time_seconds(parts[1]);command=parts[2].encode('latin1')
        value=14695981039346656037
        for byte in command: value=((value^byte)*1099511628211)&0xffffffffffffffff
        bits=struct.unpack('<I',struct.pack('<f',seconds))[0]
        records.append((seconds,index,f'{bits:08x}:{value:016x}'))
    return [row[2] for row in sorted(records,key=lambda row:(row[0],row[1]))]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('binary','data','work','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();args.work.mkdir(parents=True,exist_ok=True)
    stream=bytearray();rows=[];expected=[];archives={}
    for path in sorted(p for p in args.data.iterdir() if p.suffix.lower() in ('.mix','.dat','.dbs')):
        archive=MixArchive(path);archives[path.name]=hashlib.sha256(path.read_bytes()).hexdigest()
        for name in sorted(archive.entries):
            if not name.endswith('.txt'):continue
            payload=archive.read_binary(name)
            stream.extend(struct.pack('<I',len(payload)));stream.extend(payload)
            expected.append(reference(payload))
            rows.append({'archive':path.name,'member':name,'payload_sha256':hashlib.sha256(payload).hexdigest(),
                         'status':'unknown'})
    result=subprocess.run([str(args.binary.resolve())],input=bytes(stream),capture_output=True)
    (args.work/'runtime.log').write_bytes(result.stdout+result.stderr)
    if result.returncode:raise SystemExit('Original parser failed; inspect retained log')
    actual=result.stdout.decode().splitlines()
    if len(actual)!=len(rows):raise SystemExit('Parser receipt count mismatch')
    for row,line,wanted in zip(rows,actual,expected):
        fields=line.split();count=int(fields[0]);records=fields[1:]
        row.update(command_records=count,records_match=count==len(records) and records==wanted,
                   records_sha256=hashlib.sha256(' '.join(records).encode()).hexdigest())
    receipt={'schema_version':1,'evidence_class':'all_archive_original_cinematic_load_parser_asan_ubsan',
        'total_archives':len(archives),'total_members':len(rows),
        'matched':sum(r['records_match'] for r in rows),'command_records':sum(r['command_records'] for r in rows),
        'binary_sha256':hashlib.sha256(args.binary.read_bytes()).hexdigest(),
        'archive_sha256':archives,'rows':rows,
        'source_sha256':{name:hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in
           ['tools/host_cinematic_control_parse_test.cpp','tools/host_cinematic_save_test.cpp',
            'tools/probe_retail_cinematic_control_parser.py','staging/scripts/Test_Cinematic.cpp']},
        'limits':['All .txt members are tested; not every member is a cinematic control.',
                  'Synthetic line transport; real MIX transport has separate host receipts.',
                  'Scheduling parse only; no command dispatch, effects, mission completion or physical evidence.',
                  'FNV hashes compare exact command bytes alongside float bits/order; hashes do not validate effects.']}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(receipt,indent=2)+'\n')
    print('Original parser matched %d/%d members, %d records'%(receipt['matched'],len(rows),receipt['command_records']))
    return 0 if receipt['matched']==len(rows) else 1


if __name__=='__main__':raise SystemExit(main())
