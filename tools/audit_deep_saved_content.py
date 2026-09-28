"""Decode previously skipped conversation records and inspect local save metadata.

Read-only: retains hashes, names/IDs and factory requirements, never save bytes,
descriptions, player names or retail payloads. Original pointer tokens stay u32.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from tools.audit_m13_level_owners import chunks, flatten, microchunks, string, u32, level_records
from tools.check_m13_script_coverage import ROOT, script_dependencies, selected_owners, check_symbols
from tools.renegade_cinematic_dependency_scan import MixArchive
import subprocess


def raw_chunks(data, base=0):
    pos=0
    while pos<len(data):
        if len(data)-pos<8:
            raise ValueError('truncated record header')
        kind,size=struct.unpack_from('<II',data,pos)
        end=pos+8+(size&0x7fffffff)
        if end>len(data):
            raise ValueError('record extends outside parent')
        yield kind,base+pos,data[pos+8:end]
        pos=end


def conversations(nodes):
    records=[]
    for node in flatten(nodes):
        if node.kind != 0x40700:
            continue
        for kind,offset,data in raw_chunks(node.data,node.offset+8):
            if kind != 0x08090318:  # ConversationMgr::CHUNKID_CONVERSATION_CATEGORY
                continue
            if not data or data[0] >= 2:
                raise ValueError('invalid conversation category')
            # Match the already-staged original loader's bounded compatibility
            # for early Vita saves, whose enum occupied one byte.
            width=4
            if len(data)==1:
                width=1
            elif len(data)>=9:
                next_id,next_size=struct.unpack_from('<II',data,1)
                if next_id==0x08090319 and (next_size&0x7fffffff)<=len(data)-9:
                    width=1
            if width==4 and (len(data)<4 or data[1:4]!=b'\0\0\0'):
                raise ValueError('invalid original uint32 conversation category')
            category=data[0]
            for child,at,payload in raw_chunks(data[width:],offset+8+width):
                if child != 0x08090319:
                    raise ValueError('unexpected conversation category child')
                parsed=chunks(payload,at+8)
                identity=[n for n in parsed if n.kind==0x08090316]
                if len(identity)!=1:
                    raise ValueError('missing/ambiguous conversation identity')
                fields=dict(microchunks(identity[0].data))
                remarks=[dict(microchunks(n.data)) for n in flatten(parsed) if n.kind==0x01250307]
                records.append({'category':category,'category_bytes':width,'offset':at,'name':string(fields[0]),'id':u32(fields[1]),
                                'remark_count':len(remarks),'text_ids':[u32(r[1]) for r in remarks]})
    return records


def run(data_root,save_root,build):
    members=[]
    for name in ['always.dbs','M00_Tutorial.mix','Skirmish00.mix','M13.mix','M01.mix']:
        archive=MixArchive(data_root/name)
        for member in sorted(archive.entries):
            if member.endswith(('.ldd','.lsd','.ddb')):
                payload=archive.read_binary(member)
                rows=conversations(chunks(payload))
                members.append({'archive':name,'member':member,'sha256':hashlib.sha256(payload).hexdigest(),
                                'conversation_count':len(rows),'conversations':rows})
    symbols=subprocess.check_output(['/usr/local/vitasdk/bin/arm-vita-eabi-nm','-C',str(build/'RenegadeVitaA31')],text=True)
    selected=selected_owners(ROOT)
    saves=[]
    for p in sorted(save_root.rglob('*.sav')):
        payload=p.read_bytes()
        row={'sha256':hashlib.sha256(payload).hexdigest(),'bytes':len(payload)}
        try:
            nodes=chunks(payload)
            records=level_records(nodes)
            closure=script_dependencies(ROOT/'upstream/CnC_Renegade/Code/Scripts',
                                        {s['name'] for s in records['script_records']},prefixes=())
            check_symbols(closure,symbols)
            row.update({'saved_script_records':len(records['script_records']),
                        'required_script_count':len(closure['required_scripts']),
                        'missing_source_owners':{t:sorted(set(closure['required_owners'])-s) for t,s in selected.items()},
                        'unresolved_scripts':closure['unresolved_literal_scripts'],
                        'missing_linked_scripts':closure['missing_linked_factories']})
            try:
                conv=conversations(nodes)
                row['conversation_count']=len(conv)
                row['legacy_one_byte_category']=any(c['category_bytes']==1 for c in conv)
            except (ValueError,KeyError,UnicodeError) as e:
                row['conversation_decode_error']=str(e)
        except (ValueError,KeyError,UnicodeError) as e:
            row['decode_error']=str(e)
        saves.append(row)
    return {'schema':1,'evidence':'read-only binary metadata, not load/replay or registration',
            'members':members,'saves':saves,
            'limits':['No game execution, save migration or write-success test.',
                      'Active conversation monitors/orator state not semantically validated.',
                      'Save requirements reflect already persisted objects, not every future branch.']}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data',type=Path,required=True);p.add_argument('--saves',type=Path,required=True)
    p.add_argument('--build',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();r=run(a.data,a.saves,a.build)
    a.output.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({'conversations':{x['archive']+':'+x['member']:x['conversation_count'] for x in r['members']},
                      'saves':len(r['saves']),'save_decode_errors':sum('decode_error' in s for s in r['saves']),
                      'conversation_decode_errors':sum('conversation_decode_error' in s for s in r['saves'])},indent=2))
