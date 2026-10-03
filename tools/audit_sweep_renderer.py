"""S2 unpreprocessed renderer denominator; never a feature-support verdict."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re

from audit_sweep_port_guards import mask_noncode
from sweep_cpp_functions import parser, walk

ROOT = Path(__file__).resolve().parents[1]
STATE = re.compile(r'\bD3D(?:RS|TSS|SAMP|FVF|FMT|TS)_[A-Za-z0-9_]+\b')
FEATURE_OWNERS = {
    'rigid_mesh': ['MeshClass'], 'skinned_mesh': ['MeshClass', 'MeshModelClass'],
    'hlod': ['HLodClass'], 'aggregate': ['AggregateLoaderClass', 'AggregateDefClass'],
    'collection': ['CollectionClass'], 'rigid_decal': ['RigidDecalMeshClass'],
    'skinned_decal': ['SkinDecalMeshClass'], 'dazzle_halo': ['DazzleRenderObjClass'],
    'lensflare': ['LensflareTypeClass', 'LensflareInitClass'],
    'particle_emitter': ['ParticleEmitterClass'], 'point_group': ['PointGroupClass'],
    'line_group': ['LineGroupClass'], 'segmented_line': ['SegmentedLineClass'],
    'line3d': ['Line3DClass'], 'streak': ['StreakClass'],
    'sphere': ['SphereRenderObjClass'], 'ring': ['RingRenderObjClass'],
    'box': ['AABoxRenderObjClass', 'OBBoxRenderObjClass'], 'shatter': ['ShatterSystem'],
    'texture_projector': ['TexProjectClass'], 'shadow_projector': ['TexProjectClass'],
    'render_to_texture': ['DX8Wrapper'], 'distance_lod': ['DistLODClass'],
    'snapshot': ['SnapshotActivated', 'Is_Snapshot_Activated'],
    'sound_render_object': ['SoundRenderObjClass'], 'bitmap': ['Bitmap2DObjClass'],
    'sentence': ['Render2DSentenceClass'], 'render2d_text': ['Render2DClass', 'Render2DTextClass'],
}


def feature_expectations(classes):
    """Required helper owners remain visible even outside RenderObj ancestry.

    Names are source-discovery seeds, not authoritative ownership or a missing
    feature verdict. Snapshot and absent streak seeds require independent trace.
    """
    return [{'kind': 'required_feature', 'feature': feature, 'owner_seeds': seeds,
             'candidate_definitions': [{'file': row['file'], 'line': row['line'],
                                        'name': row['name']} for row in classes
                                       if row['name'] in seeds],
             'status': 'unknown', 'evidence_class': 'requirement_source_crosscheck'}
            for feature, seeds in FEATURE_OWNERS.items()]


def state_symbols(rows):
    references = defaultdict(list)
    for row in rows:
        if row['kind'] == 'draw_state_reference':
            references[row['symbol']].append({'file': row['file'], 'line': row['line'],
                                              'column': row['column']})
    return [{'kind': 'draw_state_symbol', 'symbol': symbol, 'references': refs,
             'status': 'unknown', 'native_mapping': 'unreviewed',
             'evidence_class': 'source_token_aggregation'}
            for symbol, refs in sorted(references.items())]


def state_reviews(rows, reviews, inputs):
    issues = []
    for review in reviews:
        pins = review.get('inputs_sha256', {})
        matches = [r for r in rows if r['kind'] == 'draw_state_symbol' and
                   r['symbol'] == review['symbol']]
        if not pins or any(inputs.get(f) != checksum for f, checksum in pins.items()) or len(matches) != 1:
            issues.append({'symbol': review['symbol'], 'reason': 'source evidence changed or absent'})
            continue
        if review['status'] not in ('missing', 'boundary_replaced', 'unknown'):
            raise ValueError('Invalid renderer state review status')
        matches[0].update(status=review['status'], native_mapping=review['native_mapping'],
                          review=review, classification_evidence_class='source_review')
    return issues


def syntax(text, cpp_parser):
    data = text.encode()
    tree = cpp_parser.parse(data)
    classes, errors = [], []
    for node in walk(tree.root_node):
        if node.type in ('class_specifier', 'struct_specifier'):
            name = node.child_by_field_name('name')
            body = node.child_by_field_name('body')
            if name is None or body is None:
                continue  # Forward declarations are not definitions.
            bases = next((c for c in node.named_children if c.type == 'base_class_clause'), None)
            scopes = []
            parent = node.parent
            while parent:
                if parent.type in ('namespace_definition', 'class_specifier', 'struct_specifier'):
                    scope = parent.child_by_field_name('name')
                    if scope:
                        scopes.append(data[scope.start_byte:scope.end_byte].decode())
                parent = parent.parent
            base_names = [data[c.start_byte:c.end_byte].decode() for c in bases.named_children
                          if c.type != 'access_specifier'] if bases else []
            classes.append({'name': data[name.start_byte:name.end_byte].decode(),
                            'scope': '::'.join(reversed(scopes)), 'bases': base_names,
                            'line': node.start_point.row + 1,
                            'end_line': node.end_point.row + 1,
                            'start_byte': node.start_byte, 'end_byte': node.end_byte,
                            'definition_sha256': hashlib.sha256(data[node.start_byte:node.end_byte]).hexdigest(),
                            'parse_has_error': node.has_error})
        if node.type == 'ERROR' or node.is_missing:
            errors.append({'line': node.start_point.row + 1, 'start_byte': node.start_byte,
                           'end_byte': node.end_byte, 'node_type': node.type,
                           'missing': node.is_missing})
    return classes, errors


def state_references(text):
    masked = mask_noncode(text)
    return [{'symbol': m[0], 'line': masked.count('\n', 0, m.start()) + 1,
             'column': m.start() - masked.rfind('\n', 0, m.start())}
            for m in STATE.finditer(masked)]


def ancestry(classes):
    """Candidate graph only: namespaces, aliases and active branches unresolved."""
    graph = defaultdict(set)
    for row in classes:
        graph[row['name']].update(row['bases'])
    def reaches(name, target, seen):
        if name == target:
            return True
        if name in seen:
            return False
        return any(reaches(base, target, seen | {name}) for base in graph[name])
    for row in classes:
        row['candidate_roles'] = [role for base, role in
                                  (('RenderObjClass', 'render_object'),
                                   ('PrototypeLoaderClass', 'prototype_loader'),
                                   ('PrototypeClass', 'prototype'))
                                  if reaches(row['name'], base, set())]


def audit(root):
    cpp_parser = parser()
    rows, inputs = [], {}
    for directory in ('staging/ww3d2', 'port/renderer'):
        for path in sorted((root / directory).rglob('*')):
            if not path.is_file() or path.suffix.lower() not in ('.cpp', '.c', '.h', '.hpp', '.inl'):
                continue
            relative = path.relative_to(root).as_posix()
            inputs[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
            text = path.read_text(errors='replace')
            classes, errors = syntax(text, cpp_parser)
            for kind, records in (('class_definition', classes), ('parse_unknown', errors),
                                  ('draw_state_reference', state_references(text))):
                rows.extend(dict(r, kind=kind, file=relative, status='unknown',
                                 evidence_class='unpreprocessed_source_syntax') for r in records)
    classes = [r for r in rows if r['kind'] == 'class_definition']
    ancestry(classes)
    rows.extend(feature_expectations(classes))
    rows.extend(state_symbols(rows))
    review_path = root / 'tools/sweep_reviews/renderer.json'
    review_issues = []
    if review_path.exists():
        inputs['tools/sweep_reviews/renderer.json'] = hashlib.sha256(review_path.read_bytes()).hexdigest()
        review_issues = state_reviews(rows, json.loads(review_path.read_text())['reviews'], inputs)
    for row in rows:
        identity = {key: row[key] for key in ('kind', 'file', 'line', 'column', 'start_byte',
                                             'end_byte', 'symbol', 'node_type', 'feature') if key in row}
        row['row_id'] = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    if len({r['row_id'] for r in rows}) != len(rows):
        raise ValueError('Duplicate renderer inventory locations')
    for name in ('audit_sweep_renderer.py', 'sweep_cpp_functions.py',
                 'audit_sweep_port_guards.py', 'sweep-parser-requirements.txt'):
        path = root / 'tools' / name
        inputs['tools/' + name] = hashlib.sha256(path.read_bytes()).hexdigest()
    upstream = root / 'upstream/CnC_Renegade/Code/ww3d2'
    missing = [p.relative_to(upstream).as_posix() for p in sorted(upstream.rglob('*'))
               if p.is_file() and p.suffix.lower() in ('.cpp', '.h', '.inl')
               and not (root / 'staging/ww3d2' / p.relative_to(upstream)).exists()]
    totals = {'rows': len(rows), 'by_kind': dict(Counter(r['kind'] for r in rows)),
              'by_status': dict(Counter(r['status'] for r in rows)),
              'candidate_roles': dict(Counter(role for r in classes for role in r['candidate_roles'])),
              'unique_draw_state_symbols': len({r['symbol'] for r in rows if 'symbol' in r})}
    aliases = defaultdict(list)
    for file, checksum in inputs.items():
        if file.startswith('staging/'):
            aliases[(file.lower(), checksum)].append(file)
    case_aliases = [names for names in aliases.values() if len(names) > 1]
    return {'schema_version': 1, 'sweep': 'S2', 'complete': False, 'totals': totals,
            'review_identity_issues': review_issues,
            'identical_case_alias_paths': case_aliases,
            'rows': rows, 'inputs_sha256': inputs, 'upstream_files_missing_from_staging': missing,
            'coverage_open': ['Active build branches and macro-generated declarations.',
                              'Scoped/aliased/template inheritance and duplicate class names.',
                              'State references are not proof that a state is set or supported.',
                              'Numeric states, dynamically computed FVF and draw-state combinations.',
                              'Selected/linked loaders, native submission paths and all-map effects.',
                              'Classes outside WW3D/renderer trees and parse uncertainties.',
                              'Render2D/text and non-RenderObj helper owners require explicit feature mapping.']}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root', type=Path, default=ROOT)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    result = audit(args.root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps(result['totals']))


if __name__ == '__main__':
    main()
