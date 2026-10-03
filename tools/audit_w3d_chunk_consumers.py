#!/usr/bin/env python3
"""Reconcile observed retail W3D IDs with staged symbolic consumer candidates."""
import argparse
import hashlib
import json
import re
from pathlib import Path


def mask(code):
    pattern = r'//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\''
    return re.sub(pattern, lambda m: ''.join('\n' if c == '\n' else ' ' for c in m[0]), code, flags=re.S)


def chunk_enum(code):
    masked = mask(code)
    blocks = [m[1] for m in re.finditer(r'\benum\s*\{([^{}]*)\}', masked, re.S)
              if re.search(r'\bW3D_CHUNK_MESH\b', m[1])]
    if len(blocks) != 1:
        raise ValueError('Ambiguous W3D chunk enum')
    names = {}
    value = -1
    for entry in blocks[0].split(','):
        if not entry.strip():
            continue
        match = re.fullmatch(r'\s*((?:OBSOLETE_)?W3D_CHUNK_\w+)\s*(?:=\s*(0x[0-9a-fA-F]+|[0-9]+))?\s*', entry)
        if not match:
            raise ValueError('Unsupported W3D enum expression')
        value = int(match[2], 0) if match[2] else value + 1
        if match[1] in names or not 0 <= value <= 0xffffffff:
            raise ValueError('Duplicate name or invalid chunk ID')
        names[match[1]] = value
    return names


def references(code, names):
    masked = mask(code)
    found = []
    for match in re.finditer(r'\b(?:OBSOLETE_)?W3D_CHUNK_\w+\b', masked):
        if match[0] not in names:
            continue
        prefix = masked[max(0, match.start()-80):match.start()]
        kind = 'case_label' if re.search(r'\bcase\s*$', prefix) else 'symbol_reference'
        found.append({'name': match[0], 'line': code.count('\n', 0, match.start())+1,
                      'reference_kind': kind})
    return found


def reconcile(inventory, names, candidates):
    observed = {}
    for archive in inventory['archives']:
        for path in archive['chunk_paths']:
            key = path['chunk_path'][-1]
            observed.setdefault(key, []).append({'archive':archive['archive'],
                'chunk_path':path['chunk_path'], 'count':path['count'],
                'member':path['first_member'],'index_record':path['first_index_record'],
                'offset':path['first_offset']})
    rows = []
    for key, occurrences in sorted(observed.items()):
        aliases = sorted(name for name, value in names.items() if value == int(key,16))
        matches = [r for r in candidates if r['name'] in aliases]
        rows.append({'chunk_id':key,'names':aliases,'occurrences':sum(o['count'] for o in occurrences),
                     'retail_paths':occurrences,'source_candidates':matches,
                     'has_case_candidate':any(r['reference_kind']=='case_label' for r in matches),
                     'status':'unknown','evidence_class':'retail_metadata_and_source_candidates'})
    return rows


def local_owner(path):
    """Reviewed primitive-local IDs must never match an unrelated parent."""
    values=tuple(int(value,16) for value in path)
    if len(values)==2 and values[0] in (0x741,0x742) and 1<=values[1]<=5:
        sphere=('CHUNKID_SPHERE_DEF','CHUNKID_COLOR_CHANNEL','CHUNKID_ALPHA_CHANNEL',
                'CHUNKID_SCALE_CHANNEL','CHUNKID_VECTOR_CHANNEL')
        ring=('CHUNKID_RING_DEF','CHUNKID_COLOR_CHANNEL','CHUNKID_ALPHA_CHANNEL',
              'CHUNKID_INNER_SCALE_CHANNEL','CHUNKID_OUTER_SCALE_CHANNEL')
        owner='sphereobj.cpp' if values[0]==0x741 else 'ringobj.cpp'
        return ('staging/ww3d2/'+owner,(sphere if values[0]==0x741 else ring)[values[1]-1])
    if len(values)==3 and values[0] in (0x741,0x742) and 2<=values[1]<=5 and values[2]==0x03150809:
        return ('staging/ww3d2/prim_anim.h','CHUNKID_VARIABLES')
    return None


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--inventory',type=Path,required=True)
    p.add_argument('--link-inventory',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    root=Path(__file__).resolve().parents[1]
    enum_path=root/'staging/ww3d2/w3d_file.h'
    names=chunk_enum(enum_path.read_text(encoding='latin1'))
    receipt=args.inventory.read_bytes(); link=args.link_inventory.read_bytes()
    selection={r['source'].casefold():r for r in json.loads(link)['rows']}
    candidates=[];sources=[]
    for path in sorted((root/'staging').rglob('*')):
        if not path.is_file() or path.suffix.lower() not in ('.cpp','.h','.hpp','.cc','.cxx') or path==enum_path:
            continue
        code=path.read_text(encoding='latin1')
        refs=references(code,names)
        if not refs:
            continue
        source=path.relative_to(root).as_posix()
        sources.append({'source':source,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
        selected=selection.get(source.casefold())
        for reference in refs:
            reference.update(source=source,selected_translation_unit=bool(selected and selected['selected_for_target']),
                             map_mentions_object=bool(selected and selected['map_mentions_object']))
            candidates.append(reference)
    rows=reconcile(json.loads(receipt),names,candidates)
    for row in rows:
        row['reviewed_local_consumer_candidates']=[]
        for occurrence in row['retail_paths']:
            owner=local_owner(occurrence['chunk_path'])
            if owner is None:
                continue
            source,name=owner
            content=(root/source).read_bytes()
            code=content.decode('latin1')
            masked=mask(code)
            matches=list(re.finditer(r'\bcase\s+'+re.escape(name)+r'\s*:',masked))
            if len(matches)!=1:
                raise ValueError('Reviewed local consumer changed; re-review required')
            row['reviewed_local_consumer_candidates'].append({'chunk_path':occurrence['chunk_path'],
                'source':source,'name':name,'line':code.count('\n',0,matches[0].start())+1,
                'source_sha256':hashlib.sha256(content).hexdigest(),
                'selected_translation_unit':bool(selection.get(source.casefold(),{}).get('selected_for_target'))})
    result={'schema':1,'complete':False,'rows':rows,'total':len(rows),
            'inventory_sha256':hashlib.sha256(receipt).hexdigest(),
            'link_inventory_sha256':hashlib.sha256(link).hexdigest(),
            'enum_sha256':hashlib.sha256(enum_path.read_bytes()).hexdigest(),
            'generator_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'source_inputs':sources,
            'counts':{'with_case_candidate':sum(r['has_case_candidate'] for r in rows),
                      'without_symbol_candidate':sum(not r['source_candidates'] for r in rows),
                      'unnamed_in_staged_enum':sum(not r['names'] for r in rows)},
            'limits':['Symbolic source candidates may be save paths, inactive branches or unrelated parent contexts',
                      'Numeric dispatch, macros, header inclusion, port-owned consumers and loader registration remain unreviewed',
                      'Primitive-local numeric paths are reviewed constants; owner changes require numeric re-review',
                      'No source candidate is not proof of missing support; all statuses remain unknown']}
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'total':result['total'],'counts':result['counts']}))


if __name__=='__main__':
    main()
