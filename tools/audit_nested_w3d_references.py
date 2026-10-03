"""Read-only nested W3D reference census; unresolved names are leads, not bugs."""
import argparse
from collections import Counter
import json
from pathlib import Path
import struct
import hashlib
from tools.renegade_cinematic_dependency_scan import MixArchive
from tools.audit_w3d_loader_coverage import chunk_paths


def chunks(data, start=0, end=None, depth=0):
    end = len(data) if end is None else end
    if depth > 64:
        raise ValueError('excessive nesting')
    while start < end:
        if end-start < 8:
            raise ValueError('truncated header')
        kind, size = struct.unpack_from('<II', data, start)
        stop = start+8+(size & 0x7fffffff)
        if stop > end:
            raise ValueError('chunk exceeds parent')
        yield kind, data[start+8:stop]
        if size & 0x80000000:
            yield from chunks(data, start+8, stop, depth+1)
        start = stop


def references(data):
    result = []
    for kind, body in chunks(data):
        if kind == 0x32:
            value = body.split(b'\0', 1)[0].decode('latin1').lower()
            if value:
                result.append(('texture', value))
        elif kind == 0x704:
            if len(body) != 36:
                raise ValueError('invalid HLOD subobject width')
            value = body[4:36].split(b'\0', 1)[0].decode('latin1').lower()
            if value:
                result.append(('hlod_subobject', value))
    return result


def scan(data):
    archives = []
    archive_errors = []
    archive_receipts = []
    names = set(p.name.lower() for p in data.iterdir() if p.is_file())
    for p in sorted(data.iterdir()):
        if not p.is_file() or p.suffix.lower() not in ('.mix', '.dat', '.dbs'):
            continue
        try:
            archive = MixArchive(p)
        except (ValueError, struct.error) as error:
            archive_errors.append({'archive':p.name,'error_type':type(error).__name__})
            continue
        names.update(archive.entries)
        archives.append(archive)
        with p.open('rb') as stream:
            archive_receipts.append({'archive':p.name,'sha256':hashlib.file_digest(stream,'sha256').hexdigest(),
                                     'index_records':len(archive.entry_records)})
    rows, errors, counts = [], [], Counter()
    members = 0
    member_receipts=[]
    for archive in archives:
        grouped={}
        with archive.path.open('rb') as stream:
            for index, (name, _, offset, size) in enumerate(archive.entry_records):
                if not name.lower().endswith('.w3d'):
                    continue
                stream.seek(offset)
                payload = stream.read(size)
                members += 1
                source_hash=hashlib.sha256(payload).hexdigest()
                member_receipts.append({'archive':archive.path.name,'member':name,'index_record':index,
                                        'sha256':source_hash,'bytes':size})
                try:
                    if len(payload)!=size:
                        raise ValueError('short archive member')
                    refs=[]
                    for path, chunk_offset, body_size in chunk_paths(payload):
                        if path[-1] not in (0x32,0x704):
                            continue
                        body=payload[chunk_offset+8:chunk_offset+8+body_size]
                        # Keep each occurrence's context; names are discovery leads.
                        for kind,value in references(struct.pack('<II',path[-1],len(body))+body):
                            refs.append((kind,value,path,chunk_offset))
                except ValueError as e:
                    errors.append({'archive': archive.path.name, 'member': name,'index_record':index,'error': str(e)})
                    continue
                for kind, value, path, chunk_offset in refs:
                    counts[kind] += 1
                    # DX8 texture loading can select a DDS sibling of a TGA.
                    available = kind == 'texture' and (value in names or str(Path(value).with_suffix('.dds')) in names)
                    row=grouped.setdefault((kind,value),{'archive': archive.path.name, 'member': name,
                                 'index_record':index,'first_offset':chunk_offset,'member_sha256':source_hash,
                                 'kind': kind, 'reference': value,
                                 'occurrence_count':0,'chunk_paths':[], 'status':'unknown',
                                 'evidence_class':'retail_dependency_name_metadata',
                                 'filename_or_dds_available_anywhere': available if kind == 'texture' else None})
                    row['occurrence_count']+=1
                    signature=[f'0x{k:08x}' for k in path]
                    if signature not in row['chunk_paths']:
                        row['chunk_paths'].append(signature)
        rows.extend(grouped[key] for key in sorted(grouped))
    root=Path(__file__).resolve().parents[1]
    return {'schema': 2,'complete':False, 'scope': 'All supplied archive W3D texture/HLOD names; availability is not runtime mounting/precedence',
            'archives':archive_receipts,'archive_errors':archive_errors,'member_receipts':member_receipts,
            'parser_inputs':[{'source':p,'sha256':hashlib.sha256((root/p).read_bytes()).hexdigest()}
                             for p in ('tools/audit_nested_w3d_references.py','tools/audit_w3d_loader_coverage.py',
                                       'tools/renegade_cinematic_dependency_scan.py')],
            'limits':['Rows aggregate archive/kind/name; first origin and all distinct parent paths retained',
                      'HLOD names are internal object names; filename lookup does not establish resolution',
                      'Loose model contents, numeric context semantics, mount precedence and runtime dependency closure remain open'],
            'w3d_members': members, 'reference_counts': dict(counts), 'references': rows,
            'errors': errors, 'runtime_verified': False}


def summary(result):
    rows=[]
    for archive in result['archives']:
        for kind in ('texture','hlod_subobject'):
            refs=[r for r in result['references'] if r['archive']==archive['archive'] and r['kind']==kind]
            unresolved=[r for r in refs if kind=='texture' and not r['filename_or_dds_available_anywhere']]
            rows.append({'archive':archive['archive'],'kind':kind,'status':'unknown',
                'evidence_class':'retail_dependency_name_metadata',
                'reference_occurrences':sum(r['occurrence_count'] for r in refs),
                'distinct_names':len(refs),'unresolved_texture_occurrences':sum(r['occurrence_count'] for r in unresolved),
                'unresolved_texture_names':unresolved})
    return {'schema':1,'complete':False,'rows':rows,'total':len(rows),
            'counts':{'unknown':len(rows)},'archives':result['archives'],
            'w3d_members':result['w3d_members'],'reference_counts':result['reference_counts'],
            'archive_errors':result['archive_errors'],'parser_errors':result['errors'],
            'parser_inputs':result['parser_inputs'],'limits':result['limits']+[
                'Full resolved-reference provenance retained separately; public rows aggregate archive/kind counts']}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--private-output',type=Path,help='Optional full local name/provenance receipt')
    a = p.parse_args()
    result = scan(a.data)
    if a.private_output:
        a.private_output.write_text(json.dumps(result,indent=2)+'\n')
    a.output.write_text(json.dumps(summary(result), indent=2)+'\n')
    print(json.dumps({'members': result['w3d_members'], 'references': result['reference_counts'],
                      'errors': len(result['errors']), 'unresolved_texture_occurrences': sum(
                          r['occurrence_count'] for r in result['references'] if
                          r['kind']=='texture' and not r['filename_or_dds_available_anywhere'])}))
