"""Read-only original HLOD names; no runtime asset-resolution proof."""
import struct

from tools.audit_m13_level_owners import chunks


def fixed_name(payload):
    if b'\0' not in payload:
        raise ValueError('unterminated HLOD name')
    return payload.split(b'\0', 1)[0].decode('latin1')


def inspect_hlod(data):
    rows = []
    for root in chunks(data):
        if root.kind != 0x700:
            continue
        children = chunks(root.data)
        headers = [n for n in children if n.kind == 0x701]
        if len(headers) != 1 or len(headers[0].data) != 40:
            raise ValueError('missing or invalid HLOD header')
        header = headers[0].data
        lod_count = struct.unpack_from('<I', header, 4)[0]
        arrays = []
        for node in children:
            # Proxy names are application data, not Create_Render_Obj dependencies.
            if node.kind not in (0x702, 0x705):
                continue
            fields = chunks(node.data)
            if not fields or fields[0].kind != 0x703 or len(fields[0].data) != 8:
                raise ValueError('invalid HLOD array header')
            count = struct.unpack_from('<I', fields[0].data)[0]
            objects = fields[1:]
            if len(objects) != count:
                raise ValueError('HLOD array count mismatch')
            names = []
            for obj in objects:
                if obj.kind != 0x704 or len(obj.data) != 36:
                    raise ValueError('invalid HLOD child record')
                names.append({'name': fixed_name(obj.data[4:36]),
                              'bone_index': struct.unpack_from('<I', obj.data)[0]})
            arrays.append({'kind': 'lod' if node.kind == 0x702 else 'aggregate',
                           'objects': names})
        if sum(a['kind'] == 'lod' for a in arrays) != lod_count:
            raise ValueError('HLOD LOD count mismatch')
        rows.append({'name': fixed_name(header[8:24]),
                     'hierarchy_name': fixed_name(header[24:40]),
                     'arrays': arrays, 'runtime_resolution_proven': False})
    return rows


def declared_render_names(data):
    """Selected original prototype header names, not a live registration claim."""
    names = []
    for node in chunks(data):
        if node.kind == 0:
            headers = [n for n in node.children if n.kind == 0x1f]
            if len(headers) != 1 or len(headers[0].data) < 40:
                raise ValueError('invalid mesh name header')
            header = headers[0].data
            mesh = fixed_name(header[8:24])
            container = fixed_name(header[24:40])
            names.append({'name': container + '.' + mesh if container else mesh,
                          'kind': 'mesh'})
        elif node.kind == 0x740:
            if len(node.data) < 40:
                raise ValueError('short box name header')
            names.append({'name': fixed_name(node.data[8:40]), 'kind': 'box'})
    names.extend({'name': row['name'], 'kind': 'hlod'} for row in inspect_hlod(data))
    return names
