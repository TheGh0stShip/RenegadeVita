#!/usr/bin/env python3
"""Compare all-archive HLOD child names with original prototype-header candidates."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
from tools.renegade_cinematic_dependency_scan import MixArchive
from tools.audit_hlod_dependencies import declared_render_names, inspect_hlod
from tools.audit_w3d_loader_coverage import root_types


def reconcile(members):
    providers=defaultdict(list)
    for member in members:
        for declaration in member.get('declarations',[]):
            providers[declaration['name'].casefold()].append(member)
    rows=[]
    for archive in sorted({m['archive'] for m in members}):
        own=[m for m in members if m['archive']==archive]
        missing={}; matched=ambiguous=external=builtin=total=0
        for member in own:
            for model in member.get('hlods',[]):
                for array in model['arrays']:
                    for child in array['objects']:
                        total+=1
                        name=child['name'].casefold()
                        if name=='null':
                            builtin+=1
                            continue
                        candidates=providers.get(name,[])
                        if candidates:
                            matched+=1
                            ambiguous+=len(candidates)>1
                            external+=not any(p['archive']==archive for p in candidates)
                        else:
                            row=missing.setdefault(name,{'name':child['name'],'occurrences':0,
                                'member':member['member'],'index_record':member['index_record'],
                                'member_sha256':member['sha256'],'hlod':model['name'],
                                'array_kind':array['kind'],'bone_index':child['bone_index'],
                                'status':'unknown','evidence_class':'retail_name_and_header_candidates'})
                            row['occurrences']+=1
        rows.append({'archive':archive,'status':'unknown','evidence_class':'retail_name_and_header_candidates',
            'w3d_members':len(own),'parser_errors':sum('parser_error' in m for m in own),
            'declared_prototypes':sum(len(m.get('declarations',[])) for m in own),
            'child_occurrences':total,'header_candidate_matches':matched,'builtin_null_names':builtin,
            'ambiguous_provider_occurrences':ambiguous,'only_other_archive_candidates':external,
            'unresolved_occurrences':sum(r['occurrences'] for r in missing.values()),
            'unresolved_names':[missing[k] for k in sorted(missing)]})
    return rows


def scan(directory):
    members=[];archives=[]
    for path in sorted(directory.iterdir()):
        if not path.is_file() or path.suffix.lower() not in ('.mix','.dat','.dbs'):
            continue
        archive=MixArchive(path)
        with path.open('rb') as stream:
            archives.append({'archive':path.name,'sha256':hashlib.file_digest(stream,'sha256').hexdigest()})
            for index,(name,_,offset,size) in enumerate(archive.entry_records):
                if not name.lower().endswith('.w3d'):
                    continue
                stream.seek(offset);data=stream.read(size)
                member={'archive':path.name,'member':name,'index_record':index,
                        'sha256':hashlib.sha256(data).hexdigest()}
                try:
                    if len(data)!=size:
                        raise ValueError('Truncated member')
                    member['root_types']=[f'0x{k:08x}' for k in root_types(data)]
                    member['declarations']=declared_render_names(data)
                    member['hlods']=inspect_hlod(data)
                except ValueError:
                    member['parser_error']=True
                members.append(member)
    return archives,members


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--private-output',type=Path)
    args=p.parse_args()
    archives,members=scan(args.data)
    rows=reconcile(members)
    # Preserve zero-model archive rows in the denominator.
    for archive in archives:
        if not any(r['archive']==archive['archive'] for r in rows):
            rows.append({'archive':archive['archive'],'status':'unknown','w3d_members':0,
                         'child_occurrences':0,'header_candidate_matches':0,'builtin_null_names':0,
                         'unresolved_occurrences':0,'unresolved_names':[]})
    rows.sort(key=lambda r:r['archive'])
    root=Path(__file__).resolve().parents[1]
    sources=('tools/audit_all_hlod_names.py','tools/audit_hlod_dependencies.py',
             'tools/audit_m13_level_owners.py','tools/audit_w3d_loader_coverage.py',
             'tools/renegade_cinematic_dependency_scan.py','staging/ww3d2/assetmgr.cpp',
             'staging/ww3d2/w3d_file.h','staging/ww3d2/sphereobj.h','staging/ww3d2/ringobj.h',
             'staging/ww3d2/meshmdlio.cpp')
    result={'schema':1,'complete':False,'rows':rows,'total':len(rows),
            'counts':{'unknown':len(rows)},'archives':archives,
            'totals':{'w3d_members':len(members),
                      'child_occurrences':sum(r['child_occurrences'] for r in rows),
                      'unresolved_occurrences':sum(r['unresolved_occurrences'] for r in rows),
                      'parser_errors':sum('parser_error' in m for m in members)},
            'parser_inputs':[{'source':s,'sha256':hashlib.sha256((root/s).read_bytes()).hexdigest()} for s in sources],
            'limits':['Declarations cover reviewed prototype name fields; full schema and content validation remain open',
                      'Global header candidates do not prove mount order, load-on-demand filename choice or registration',
                      'NULL is the original built-in prototype name; runtime initialization remains unverified',
                      'HLOD proxy arrays are application data and excluded from child dependency counts',
                      'Loose model contents and missing-name runtime selection remain open']}
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    if args.private_output:
        args.private_output.write_text(json.dumps(members,indent=2)+'\n')
    print(json.dumps(result['totals']))


if __name__=='__main__':
    main()
