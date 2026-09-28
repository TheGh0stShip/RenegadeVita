"""Inventory W3D root chunks needing loaders registered by original Commando/init.cpp.

Archive-wide presence is a dependency lead, not proof every asset is displayed.
No model bytes are exported. Original little-endian u32 headers are bounded.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct
import re
import subprocess
from tools.renegade_cinematic_dependency_scan import MixArchive
from tools.check_m13_script_coverage import ROOT, without_comments

LOADERS={0x500:('ParticleEmitterLoaderClass','part_ldr.cpp'),
         0x741:('SphereLoaderClass','sphereobj.cpp'),
         0x742:('RingLoaderClass','ringobj.cpp'),
         0xa00:('SoundRenderObjLoaderClass','soundrobj.cpp')}


def registrations(build):
    db=json.loads(subprocess.check_output(['ninja','-C',str(build),'-t','compdb'],text=True))
    files={(Path(x['directory'])/x['file']).resolve() for x in db if x['output'].startswith('CMakeFiles/RenegadeVitaA31.dir/')}
    calls=[]
    for p in sorted(files):
        if p.suffix=='.cpp' and p.exists():
            source=without_comments(p.read_text(encoding='latin1'))
            calls.extend({'source':str(p.relative_to(ROOT)),'loader':m}
                         for m in re.findall(r'Register_Prototype_Loader\s*\(\s*&\s*(\w+)\s*\)',source))
    symbols=subprocess.check_output(['/usr/local/vitasdk/bin/arm-vita-eabi-nm','-C',str(build/'RenegadeVitaA31')],text=True)
    rows=[]
    for symbol,file in [('_ParticleEmitterLoader','part_ldr.cpp'),('_SphereLoader','sphereobj.cpp'),
                        ('_RingLoader','ringobj.cpp'),('_SoundRenderObjLoader','soundrobj.cpp')]:
        rows.append({'symbol':symbol,'owner':file,'configured':(ROOT/'staging/ww3d2'/file).resolve() in files,
                     'defined_global_in_existing_elf':bool(re.search(r'^\s*[0-9a-fA-F]+\s+[BDRVbd]\s+'+symbol+'$',symbols,re.M)),
                     'direct_registration_in_configured_sources':any(x['loader']==symbol for x in calls)})
    return {'direct_registration_calls':calls,'original_bootstrap_loaders':rows}


def root_types(data):
    pos=0;result=[]
    while pos<len(data):
        if len(data)-pos<8:
            raise ValueError('truncated W3D header')
        kind,size=struct.unpack_from('<II',data,pos)
        end=pos+8+(size&0x7fffffff)
        if end>len(data):
            raise ValueError('W3D chunk exceeds member')
        result.append(kind);pos=end
    return result


def scan(directory):
    rows=[]
    for p in sorted(directory.iterdir()):
        if not (p.name.lower().startswith(('always','c&c_')) or p.name.lower() in
                ('m00_tutorial.mix','skirmish00.mix','m13.mix','m01.mix')) or p.suffix.lower() not in ('.mix','.dat','.dbs'):
            continue
        archive=MixArchive(p);hits=[];counts=Counter();errors=[];files=0
        with p.open('rb') as stream:
            for name,(_,offset,size) in sorted(archive.entries.items()):
                if not name.endswith('.w3d'):
                    continue
                stream.seek(offset);data=stream.read(size);files+=1
                if len(data)!=size:
                    raise ValueError('short archive member')
                try: kinds=root_types(data)
                except ValueError as e:
                    errors.append({'member':name,'error':str(e)});continue
                counts.update(f'0x{k:08x}' for k in kinds)
                required=sorted(set(kinds)&LOADERS.keys())
                if required:
                    hits.append({'member':name,'sha256':hashlib.sha256(data).hexdigest(),
                                 'loader_types':[LOADERS[k][0] for k in required]})
        rows.append({'archive':p.name,'w3d_files':files,'root_chunks':dict(counts),'bootstrap_loader_assets':hits,'errors':errors})
    return {'schema':1,'scope':'selected map and global archive W3D root chunks; not runtime reachability',
            'loader_owners':{f'0x{k:08x}':{'class':v[0],'owner':v[1]} for k,v in LOADERS.items()},'archives':rows}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--data',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--build',type=Path,required=True)
    a=p.parse_args();r=scan(a.data);r['registration_census']=registrations(a.build)
    a.output.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({'w3d_files':sum(x['w3d_files'] for x in r['archives']),
                      'bootstrap_loader_assets':{x['archive']:len(x['bootstrap_loader_assets']) for x in r['archives']},
                      'errors':sum(len(x['errors']) for x in r['archives'])},indent=2))
