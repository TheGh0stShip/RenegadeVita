"""Read-only W3D prelit candidates; never loader or native visual proof."""
from collections import Counter
import struct

from tools.audit_m13_level_owners import chunks


def select_prelit(attributes, mode):
    """Original mesh header fallthrough, with missing fallback kept unresolved."""
    if mode not in (0, 1, 2):
        raise ValueError('unsupported prelit mode')
    if not attributes & 0x0f000000:
        return None
    order = {2: (0x26, 0x25, 0x24, 0x23),
             1: (0x25, 0x24, 0x23), 0: (0x24, 0x23)}[mode]
    flags = {0x23: 0x01000000, 0x24: 0x02000000,
             0x25: 0x04000000, 0x26: 0x08000000}
    return next((kind for kind in order if attributes & flags[kind]), None)


def inspect_prelit(data, mode):
    rows = []
    for mesh in chunks(data):
        if mesh.kind != 0:
            continue
        headers = [node for node in mesh.children if node.kind == 0x1f]
        if len(headers) != 1 or len(headers[0].data) < 40:
            raise ValueError('missing, short or ambiguous mesh header')
        header = headers[0].data
        attributes = struct.unpack_from('<I', header, 4)[0]
        selected = select_prelit(attributes, mode)
        wrappers = [node for node in mesh.children if node.kind == selected]
        findings = []
        if attributes & 0x0f000000 and selected is None:
            findings.append('selected_fallback_not_advertised')
        if selected is not None and len(wrappers) != 1:
            findings.append('selected_wrapper_missing_or_ambiguous')
        passes = []
        loaded_dig = False
        if len(wrappers) == 1:
            # Known container ownership, not an assumption about its high bit.
            for node in chunks(wrappers[0].data):
                if node.kind != 0x38:
                    continue
                fields = chunks(node.data)
                counts = Counter(field.kind for field in fields)
                candidates = []
                for kind, label in ((0x39, 'vertex_material'), (0x3a, 'shader'),
                                    (0x3b, 'diffuse_color')):
                    if counts[kind] > 1:
                        candidates.append(label)
                if counts[0x3c] and (loaded_dig or counts[0x3c] > 1):
                    candidates.append('diffuse_illumination')
                loaded_dig = loaded_dig or bool(counts[0x3c])
                stages = []
                for field in fields:
                    if field.kind != 0x48:
                        continue
                    stage_counts = Counter(child.kind for child in chunks(field.data))
                    stage_candidates = []
                    if stage_counts[0x49] > 1:
                        stage_candidates.append('texture')
                    if stage_counts[0x4a] + stage_counts[0x05] > 1:
                        stage_candidates.append('uv')
                    stages.append({'alternate_field_candidates': stage_candidates})
                passes.append({'field_counts': {hex(k): v for k, v in sorted(counts.items())},
                               'alternate_material_candidate': counts[0x39] > 1,
                               'alternate_field_candidates': candidates,
                               'texture_stages': stages})
        rows.append({'attributes': attributes, 'requested_mode': mode,
                     'selected_wrapper': selected, 'passes': passes,
                     'findings': findings, 'loader_execution_proven': False,
                     'native_visual_correctness_proven': False})
    return rows
