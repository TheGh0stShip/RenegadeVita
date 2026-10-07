"""Read-only render-state census of the tutorial's W3D meshes (render-sort-v1).

Parses M00_Tutorial.mix with the existing MIX/chunk helpers, selects each
mesh's material passes the way MeshModelClass does in the default
PRELIT_MODE_LIGHTMAP_MULTI_PASS, rebuilds the static mesh cache batch runs
(triangle order, split on texture/material/shader/detail change) and
classifies every batch with the render-sort-v1 rule. Then it estimates, for
windows of N consecutive meshes, how many batch state changes and shader
changes the per-mesh replay order costs versus the pass-major plans.

Aggregate numbers only; nothing from the archive is written. This is not a
measurement of the running game: which meshes are visible together, and in
what order, comes from the original culling system at run time.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import random
import struct
import sys

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.audit_m13_level_owners import chunks
from tools.audit_prelit_material_candidates import select_prelit
from tools.renegade_cinematic_dependency_scan import MixArchive
from tools import vita_opaque_sort_model as model

DEFAULT_ARCHIVE = Path(__file__).resolve().parents[1] / 'retail-pc/Data/M00_Tutorial.mix'
PRELIT_MODE_LIGHTMAP_MULTI_PASS = 1


def children(node, kind):
    nodes = node.children or chunks(node.data)
    return [child for child in nodes if child.kind == kind]


def u32s(data):
    return list(struct.unpack_from('<%dI' % (len(data) // 4), data))


def shader_state(raw):
    """W3dShaderStruct -> the ShaderClass fields Convert_Shader keeps."""
    (depth_compare, depth_mask, _color_mask, dest_blend, _fog, pri_gradient, sec_gradient,
     src_blend, texturing, detail_color, detail_alpha, _preset, alpha_test, _pdc, _pda,
     _pad) = raw
    return {'depth_compare': depth_compare, 'depth_write': depth_mask == 1,
            'blend': not (src_blend == 1 and dest_blend == 0), 'alpha_test': alpha_test == 1,
            'detail': texturing == 1 and (detail_color != 0 or detail_alpha != 0),
            'bits': (depth_compare, depth_mask, dest_blend, pri_gradient, sec_gradient,
                     src_blend, texturing, detail_color, detail_alpha, alpha_test)}


def mesh_batches(mesh):
    """Static-cache batch runs of one mesh, in build order."""
    header = children(mesh, 0x1f)[0].data
    attributes = struct.unpack_from('<I', header, 4)[0]
    name = header[8:24].split(b'\0')[0].decode('latin1')
    container = header[24:40].split(b'\0')[0].decode('latin1')
    triangle_count = struct.unpack_from('<I', header, 40)[0]
    selected = select_prelit(attributes, PRELIT_MODE_LIGHTMAP_MULTI_PASS)
    scope = mesh
    if selected is not None:
        wrapper = children(mesh, selected)
        if len(wrapper) == 1:
            scope = wrapper[0]
    shaders = [shader_state(struct.unpack_from('<16B', node.data, offset))
               for node in children(scope, 0x29) for offset in range(0, len(node.data), 16)]
    textures = []
    for group in children(scope, 0x30):
        for texture in children(group, 0x31):
            names = children(texture, 0x32)
            textures.append(names[0].data.split(b'\0')[0].decode('latin1').lower() if names else None)
    first_vertex = []
    for node in children(mesh, 0x20):
        first_vertex = [struct.unpack_from('<I', node.data, offset)[0]
                        for offset in range(0, len(node.data), 32)]
    batches = []
    for pass_index, material_pass in enumerate(children(scope, 0x38)):
        vmat = children(material_pass, 0x39)
        vmat_ids = u32s(vmat[0].data) if vmat else [0]
        shader_ids = children(material_pass, 0x3a)
        shader_ids = u32s(shader_ids[0].data) if shader_ids else [0]
        stages = []
        for stage in children(material_pass, 0x48):
            ids = children(stage, 0x49)
            stages.append(u32s(ids[0].data) if ids else None)
        previous = None
        for triangle in range(triangle_count):
            shader = shaders[shader_ids[triangle] if len(shader_ids) > 1 else shader_ids[0]] \
                if shaders else shader_state((3, 1, 0, 0, 0, 1, 0, 1, 0) + (0,) * 7)
            texture = []
            for ids in stages[:2]:
                tid = None if ids is None else (ids[triangle] if len(ids) > 1 else ids[0])
                texture.append(textures[tid] if tid is not None and tid < len(textures) else None)
            texture += [None] * (2 - len(texture))
            detail = shader['detail'] and texture[1] is not None
            vertex = first_vertex[triangle] if triangle < len(first_vertex) else 0
            material = vmat_ids[vertex] if len(vmat_ids) > 1 and vertex < len(vmat_ids) else vmat_ids[0]
            key = (texture[0], texture[1] if detail else None, (container, name, material),
                   shader['bits'], detail)
            if key != previous:
                batches.append({'pass': pass_index, 'tex0': key[0], 'tex1': key[1],
                                'mat': key[2], 'shader': key[3], 'detail': detail,
                                'cls': model.classify(shader['blend'], shader['depth_write'], True,
                                                      shader['alpha_test'],
                                                      shader['depth_compare'])})
                previous = key
    return container + '.' + name, batches


def changes(slots, order):
    """Consecutive-batch changes: replay state, shader bits, textures, mesh binds."""
    state = shader = texture = binds = 0
    for position, slot in enumerate(order):
        if position == 0:
            state = shader = texture = binds = 1
            continue
        a, b = slots[order[position - 1]], slots[slot]
        state += model.state_key(a) != model.state_key(b)
        shader += a['shader'] != b['shader']
        texture += (a['tex0'], a['tex1']) != (b['tex0'], b['tex1'])
        binds += a['item'] != b['item']
    return state, shader, texture, binds


def census(archive_path, window, samples, seed):
    archive = MixArchive(archive_path)
    meshes = []
    for name, *_ in archive.entry_records:
        if not name.lower().endswith('.w3d'):
            continue
        for node in chunks(archive.read_binary(name)):
            if node.kind == 0:
                meshes.append(mesh_batches(node))
    totals = Counter()
    for _, batches in meshes:
        totals['meshes'] += 1
        passes = max((b['pass'] for b in batches), default=-1) + 1
        totals['multipass_meshes'] += passes > 1
        eligible = model.entry_eligible(batches)
        totals['eligible_meshes'] += eligible
        totals['eligible_multipass_meshes'] += eligible and passes > 1
        for current in range(passes):
            runs = [b for b in batches if b['pass'] == current]
            label = 'pass0' if current == 0 else 'pass1plus'
            totals[label + '_batches'] += len(runs)
            totals[label + '_distinct_states'] += len({model.state_key(b) for b in runs})
    eligible_meshes = [batches for _, batches in meshes if model.entry_eligible(batches)]
    rng = random.Random(seed)
    estimates = {}
    for label, ordered in (('archive_order', True), ('random_order', False)):
        sums = Counter()
        for _ in range(samples):
            if ordered:
                start = rng.randrange(max(1, len(eligible_meshes) - window))
                chosen = eligible_meshes[start:start + window]
            else:
                chosen = rng.sample(eligible_meshes, min(window, len(eligible_meshes)))
            slots = [dict(b, item=i) for i, batches in enumerate(chosen) for b in batches]
            for mode in model.MODES:
                state, shader, texture, binds = changes(slots, model.plan(mode, slots))
                sums['mode%d_state' % mode] += state
                sums['mode%d_shader' % mode] += shader
                sums['mode%d_texture' % mode] += texture
                sums['mode%d_binds' % mode] += binds
        estimates[label] = {key: round(value / samples, 1) for key, value in sorted(sums.items())}
    return {'archive': archive_path.name, 'prelit_mode': 'LIGHTMAP_MULTI_PASS',
            'totals': dict(sorted(totals.items())), 'window_meshes': window,
            'samples': samples, 'per_window_mean': estimates,
            'measured_on_hardware': False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--archive', type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument('--window', type=int, default=40)
    parser.add_argument('--samples', type=int, default=400)
    parser.add_argument('--seed', type=int, default=1)
    args = parser.parse_args(argv)
    print(json.dumps(census(args.archive, args.window, args.samples, args.seed), indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
