"""Read-only nested W3D reference census; unresolved names are leads, not bugs."""
import argparse
from collections import Counter
import json
from pathlib import Path
import struct
from tools.renegade_cinematic_dependency_scan import MixArchive


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
    names = set(p.name.lower() for p in data.iterdir() if p.is_file())
    for p in sorted(data.iterdir()):
        if p.suffix.lower() not in ('.mix', '.dat', '.dbs'):
            continue
        try:
            archive = MixArchive(p)
        except (ValueError, struct.error):
            continue
        names.update(archive.entries)
        if p.name.lower().startswith(('always', 'c&c_')) or p.name.lower() in (
                'm00_tutorial.mix', 'skirmish00.mix', 'm13.mix', 'm01.mix'):
            archives.append(archive)
    rows, errors, counts = [], [], Counter()
    members = 0
    for archive in archives:
        with archive.path.open('rb') as stream:
            for name, (_, offset, size) in sorted(archive.entries.items()):
                if not name.endswith('.w3d'):
                    continue
                stream.seek(offset)
                payload = stream.read(size)
                members += 1
                try:
                    refs = references(payload)
                except ValueError as e:
                    errors.append({'archive': archive.path.name, 'member': name, 'error': str(e)})
                    continue
                for kind, value in refs:
                    counts[kind] += 1
                    # DX8 texture loading can select a DDS sibling of a TGA.
                    available = kind == 'texture' and (value in names or str(Path(value).with_suffix('.dds')) in names)
                    rows.append({'archive': archive.path.name, 'member': name,
                                 'kind': kind, 'reference': value,
                                 'filename_or_dds_available_anywhere': available if kind == 'texture' else None})
    return {'schema': 1, 'scope': 'nested texture and HLOD names; availability is not runtime mounting/precedence',
            'w3d_members': members, 'reference_counts': dict(counts), 'references': rows,
            'errors': errors, 'runtime_verified': False}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    result = scan(a.data)
    a.output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({'members': result['w3d_members'], 'references': result['reference_counts'],
                      'errors': len(result['errors']), 'unresolved_texture_occurrences': sum(
                          r['kind']=='texture' and not r['filename_or_dds_available_anywhere'] for r in result['references'])}))
