"""Enumerate the original category selector's structural FVF outputs.

Runs the verbatim-source policy contract first. Native admission is restricted
to the current bridge's two explicit layouts; this is not pixel acceptance.
"""
import argparse
import hashlib
import itertools
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    subprocess.run([sys.executable, '-m', 'unittest',
                    'tools.test_original_renderer_fvf_selection'], cwd=ROOT, check=True)
    bridge = ROOT / 'port/renderer/vita/ww3d_vita_renderer.cpp'
    text = bridge.read_text()
    # Bind this admission comparison to the actual current production guard.
    required = ['const uint32_t mesh_fvf = 0x00000152U;',
                'const uint32_t render2d_fvf = 0x00000252U;',
                'submission.vertex_stride == 36U;', 'submission.vertex_stride == 44U;',
                'if (!mesh_layout && !dynamic_two_uv_layout)']
    if any(fragment not in text for fragment in required):
        raise ValueError('Native FVF admission changed; review and update this comparison')
    rows = []
    for uv, normal, diffuse, specular in itertools.product(range(9), range(2), range(2), range(2)):
        fvf = 2 | (16 if normal else 0) | (64 if diffuse else 0) | (128 if specular else 0) | (uv << 8)
        rows.append({'fvf': f'{fvf:08x}', 'texture_coordinates': uv,
                     'name': f'Original category FVF {fvf:08x}',
                     'status': 'unknown' if fvf in (0x152, 0x252) else 'missing',
                     'evidence_class': 'original selector contract and native admission source',
                     'normal': bool(normal), 'diffuse': bool(diffuse), 'specular': bool(specular),
                     'stride': 12 + normal * 12 + diffuse * 4 + specular * 4 + uv * 8,
                     'native_layout_admitted': fvf in (0x152, 0x252),
                     'review': {
                         'original_owner': 'DX8FVFCategoryContainer::Define_FVF and original rigid category buffers',
                         'affected_scope': ['Original category mesh draws across native modes; actual retail/layout incidence remains unknown'],
                         'acceptance_open': 'Preserve original offsets, optional colors/normals and UV sources; validate lighting and materials on host, ARM and hardware'},
                     'retail_incidence': 'unknown', 'native_pixels': 'unverified'})
    assert len(rows) == len({r['fvf'] for r in rows}) == 72
    inputs = ['staging/ww3d2/dx8renderer.cpp', 'port/renderer/vita/ww3d_vita_renderer.cpp',
              'tools/test_original_renderer_fvf_selection.py']
    result = {'schema': 1, 'evidence_class': 'verbatim selector host sanitizer and ARM object contract',
              'inputs_sha256': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in inputs},
              'total': 72, 'counts': {'missing': 70, 'unknown': 2},
              'potential_layouts': 72, 'admitted_layouts': 2, 'unsupported_layouts': 70,
              'rows': rows, 'complete': False, 'physical_acceptance': False,
              'scope': 'Structural producer inputs; no claim that all occur in retail data. Mesh inputs are test doubles. Sorted meshes select dynamic FVF when sorting is enabled.'}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    main()
