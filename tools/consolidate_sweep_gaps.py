#!/usr/bin/env python3
"""Retain every non-original-compiled status record from the eight sweeps."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

SWEEPS = ('port_guards', 'renderer', 'link', 'retail', 'scripts', 'systems',
          'performance', 'external')
ISSUES = dict(zip(SWEEPS, range(5, 13)))
SUPPLEMENTS = ('level_chunks', 'spatial_presence', 'visibility_bounds',
               'w3d_chunks', 'w3d_consumers', 'dds_formats', 'w3d_references', 'hlod_names', 'wave_headers', 'wave_decode', 'procedural_fvf_layouts',
               'database_chunks', 'level_persist_closure', 'database_persist_closure',
               'host_definition_registry', 'database_definition_closure', 'definition_instances',
               'missing_definition_callers', 'host_script_registry', 'live_script_bindings', 'host_network_registry', 'host_prototype_registry', 'live_script_parameters', 'script_parameter_reads', 'host_script_parameters', 'script_parameter_surface', 'script_load_destinations')
ISSUES.update({name: 8 for name in SUPPLEMENTS})
ISSUES['procedural_fvf_layouts'] = 6
ISSUES.update({name: 7 for name in ('level_persist_closure', 'database_persist_closure',
                                  'host_definition_registry', 'database_definition_closure', 'host_script_registry')})
ISSUES['live_script_bindings'] = 9
ISSUES['host_network_registry'] = 7
ISSUES['host_prototype_registry'] = 7
ISSUES['live_script_parameters'] = 9
ISSUES['script_parameter_reads'] = 9
ISSUES['host_script_parameters'] = 9
ISSUES['script_parameter_surface'] = 9
ISSUES['script_load_destinations'] = 9
SCRIPT_SUPPLEMENTS = ('script_command_bodies', 'script_command_port_dependencies',
                     'host_script_command_table', 'cinematic_dispatch_dependencies', 'script_portability',
                     'script_compiler_diagnostics', 'm09_camera_bindings')
SUPPLEMENTS += SCRIPT_SUPPLEMENTS
ISSUES.update({name: 9 for name in SCRIPT_SUPPLEMENTS})
STATUSES = {'original_compiled', 'original_patched', 'boundary_replaced',
            'stubbed_or_noop', 'disabled_by_port_guard', 'excluded_with_proof',
            'missing', 'unknown'}


def status_records(value, pointer='', inherited_map=None):
    if isinstance(value, dict):
        archive=value.get('archive','')
        mission = value.get('map', archive if archive.lower().endswith('.mix') else inherited_map)
        if 'status' in value:
            if value['status'] not in STATUSES:
                raise ValueError(f'Unexpected status at {pointer}')
            yield pointer, value, mission
        for key, child in value.items():
            if key == 'review' and isinstance(child, dict) and 'status' in value and 'status' in child:
                if value['status'] != child['status']:
                    raise ValueError(f'Review status disagrees with parent at {pointer}')
                # This is provenance for the same finding, not a second gap.
                continue
            escaped = key.replace('~', '~0').replace('/', '~1')
            yield from status_records(child, pointer + '/' + escaped, mission)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from status_records(child, pointer + '/' + str(index), inherited_map)


def root_records(name, value):
    """Reconcile heterogeneous denominators without rewriting JSON pointers."""
    if name not in SUPPLEMENTS:
        rows=value['rows']
        expected=value.get('total', value.get('totals', {}).get('rows'))
        if expected != len(rows):
            raise ValueError(f'{name}: root denominator mismatch')
        if dict(Counter(r['status'] for r in rows)) != value.get('counts', value.get('totals', {}).get('by_status')):
            raise ValueError(f'{name}: status reconciliation failed')
        return rows
    rows=value['archives'] if name=='w3d_chunks' else value['rows']
    totals=value.get('totals',{})
    if name in SCRIPT_SUPPLEMENTS:
        if value['total'] != len(rows):
            raise ValueError(f'{name}: denominator mismatch')
        if name == 'host_script_command_table':
            for field, row_field in (('nonnull', 'nonnull'),
                                     ('assigned_name_matches', 'assigned_name_match'),
                                     ('arm_function_signatures_retained', 'arm_function_signature_retained')):
                if value[field] != sum(bool(r[row_field]) for r in rows):
                    raise ValueError(f'{name}: execution partition mismatch')
        elif value['counts'] != dict(Counter(r['status'] for r in rows)):
            raise ValueError(f'{name}: status partition mismatch')
        if name == 'script_command_port_dependencies':
            if value['commands_with_port_candidates'] != sum(bool(r['matched_calls']) for r in rows) or value['matched_call_names'] != sum(len(r['matched_calls']) for r in rows):
                raise ValueError(f'{name}: candidate partition mismatch')
        if name == 'cinematic_dispatch_dependencies':
            calls = sorted({call['name'] for row in rows for call in row['command_calls']})
            if value['unique_engine_commands'] != calls:
                raise ValueError(f'{name}: command partition mismatch')
        if name == 'script_portability':
            if value['dsp_units'] + value['directory_headers'] != len(rows) or value['dsp_units'] != sum(r['surface']=='dsp_unit' for r in rows) or value['directory_headers'] != sum(r['surface']=='directory_header' for r in rows) or value['staged_present'] != sum(r['staged_present'] for r in rows):
                raise ValueError(f'{name}: source partition mismatch')
            for key in ('original', 'staged'):
                categories = dict(Counter(f['category'] for r in rows for f in r[key+'_findings']))
                if categories != value[key+'_categories']:
                    raise ValueError(f'{name}: category partition mismatch')
        if name == 'script_compiler_diagnostics':
            counts = Counter()
            for row in rows:
                counts.update(row['diagnostic_counts'])
            if dict(counts) != value['diagnostic_counts']:
                raise ValueError(f'{name}: diagnostic partition mismatch')
        if name == 'm09_camera_bindings':
            if value['binding_count'] != sum(row['binding_count'] for row in rows):
                raise ValueError(f'{name}: binding partition mismatch')
    elif name=='script_load_destinations':
        if value['total']!=len(rows) or value['counts']!=dict(Counter(r['status'] for r in rows)) or value['parse_complete']!=sum(r['parse_complete'] for r in rows):
            raise ValueError('Script load destination partition mismatch')
    elif name=='script_parameter_surface':
        if value['total']!=len(rows) or value['counts']!=dict(Counter(r['status'] for r in rows)) or value['categories']!=dict(Counter(r['coverage'] for r in rows)) or value['syntax_kinds']!=dict(Counter(r['syntax_kind'] for r in rows)):
            raise ValueError('Script parameter surface partition mismatch')
    elif name=='host_script_parameters':
        if value['total']!=len(rows) or value['matched']!=sum(r['matches'] for r in rows):
            raise ValueError('Host script parameter partition mismatch')
    elif name=='script_parameter_reads':
        if value['total']!=len(rows) or value['counts']!=dict(Counter(r['status'] for r in rows)) or value['categories']!=dict(Counter(r['category'] for r in rows)):
            raise ValueError('Script parameter read partition mismatch')
    elif name=='host_script_registry':
        if value['total']!=len(rows) or value['counts']!=dict(Counter(r['status'] for r in rows)) or value['registry_count']!=len(value['registry_entries']):
            raise ValueError('Live script registry denominator mismatch')
        if value['matched_candidates']!=sum(r['name_matches'] for r in rows) or value['unmatched_candidates']!=sum(not r['found'] for r in rows):
            raise ValueError('Live script registry candidate partition mismatch')
    elif name=='live_script_parameters':
        if value['total']!=len(rows) or value['counts']!=dict(Counter(r['status'] for r in rows)):
            raise ValueError('Script parameter denominator mismatch')
        categories=Counter()
        for row in rows:
            if row['bindings']!=sum(row['categories'].values()) or len(row['leads'])!=row['bindings']-row['categories'].get('equal_count',0):
                raise ValueError('Script parameter partition mismatch')
            categories.update(row['categories'])
        if dict(categories)!=value['categories'] or value['bindings']!=sum(categories.values()):
            raise ValueError('Script parameter totals mismatch')
    elif name=='live_script_bindings':
        if value['total']!=len(rows) or value['counts']!=dict(Counter(r['status'] for r in rows)):
            raise ValueError('Live script binding denominator mismatch')
        for row in rows:
            if row['bindings']!=row['registered_bindings']+row['unregistered_bindings'] or row['unregistered_bindings']!=len(row['missing']):
                raise ValueError('Live script binding partition mismatch')
        if totals!={key:sum(r[key] for r in rows) for key in ('bindings','registered_bindings','unregistered_bindings')}:
            raise ValueError('Live script binding totals mismatch')
    elif name=='missing_definition_callers':
        if value['total']!=len(rows) or value['counts']!=dict(Counter(r['status'] for r in rows)):
            raise ValueError('Missing-definition caller denominator mismatch')
    elif name=='definition_instances':
        if value['total']!=len(rows) or value['counts']!=dict(Counter(r['status'] for r in rows)):
            raise ValueError('Definition instance scope denominator mismatch')
        for row in rows:
            if not row.get('input_missing') and row['typed_reference_fields']!=sum(row['edge_counts'].values()):
                raise ValueError('Definition reference edge partition mismatch')
    elif name=='database_chunks':
        if totals['archives']!=len(rows) or totals['members']!=sum(len(r['members']) for r in rows):
            raise ValueError('Database member denominator mismatch')
    elif name in {'level_persist_closure', 'database_persist_closure'}:
        if totals['factory_ids']!=len(rows) or totals['candidate_instances']!=sum(r['candidate_instances'] for r in rows):
            raise ValueError('Persistence denominator mismatch')
        if totals['without_arm_symbol']!=sum(not r['arm_load_symbol_present'] for r in rows) or totals['without_host_lookup']!=sum(not r['host_lookup_matches'] for r in rows):
            raise ValueError('Persistence evidence partition mismatch')
    elif name=='host_prototype_registry':
        if value['total']!=len(rows) or value['matched']!=sum(r['lookup_matches'] for r in rows) or len({r['chunk_id'] for r in rows})!=len(rows):
            raise ValueError('Prototype registry partition mismatch')
    elif name in {'host_definition_registry', 'host_network_registry'}:
        if value['total']!=len(rows) or value['matched']!=sum(r['matches'] for r in rows):
            raise ValueError('Definition lookup denominator mismatch')
        if name=='host_network_registry':
            ids=value['live_ids']
            expected={r['class_id'] for r in rows}
            if value['live_factory_count']!=len(ids) or len(set(ids))!=len(ids) or value['live_non_template_ids']!=sorted(set(ids)-expected):
                raise ValueError('Network live registry partition mismatch')
    elif name=='database_definition_closure':
        if totals['persistence_ids']!=len(rows) or totals['mapped']!=sum(bool(r['definition_class_ids']) for r in rows) or totals['unmapped']!=len(rows)-totals['mapped'] or totals['ambiguous']!=sum(r['class_id_mapping_ambiguous'] for r in rows):
            raise ValueError('Definition closure partition mismatch')
    elif name=='procedural_fvf_layouts':
        if value['total']!=len(rows) or value['counts']!=dict(Counter(r['status'] for r in rows)):
            raise ValueError('Procedural FVF denominator/status mismatch')
        admitted=sum(r['native_layout_admitted'] for r in rows)
        if value['admitted_layouts']!=admitted or value['unsupported_layouts']!=len(rows)-admitted:
            raise ValueError('Procedural FVF admission partition mismatch')
    elif name=='level_chunks':
        if totals.get('maps')!=len(rows) or totals.get('members')!=sum(len(r['members']) for r in rows):
            raise ValueError('Level member denominator mismatch')
    elif name=='w3d_chunks':
        measured={'archives':len(rows),'w3d_members':sum(len(r['members']) for r in rows),
                  'chunk_occurrences':sum(sum(c['count'] for c in r['chunk_paths']) for r in rows),
                  'archive_chunk_paths':sum(len(r['chunk_paths']) for r in rows),
                  'distinct_chunk_ids':len({k for r in rows for c in r['chunk_paths'] for k in c['chunk_path']}),
                  'parser_errors':sum(len(r['errors']) for r in rows)}
        if measured!=totals or any(r['w3d_files']!=len(r['members']) for r in rows):
            raise ValueError('W3D denominator mismatch')
    elif name=='w3d_consumers' and value['total']!=len(rows):
        raise ValueError('W3D consumer denominator mismatch')
    elif name=='dds_formats':
        if totals.get('dds_members')!=len(rows) or totals.get('by_format')!=dict(Counter(r['format'] for r in rows)):
            raise ValueError('DDS denominator mismatch')
    elif name=='w3d_references':
        measured=dict(Counter())
        for row in rows:
            measured[row['kind']]=measured.get(row['kind'],0)+row['reference_occurrences']
        if value['total']!=len(rows) or measured!=value['reference_counts']:
            raise ValueError('W3D reference denominator mismatch')
    elif name=='wave_decode':
        fields=('wave_members','decoded_members','rejected_members')
        if value['total']!=len(rows) or totals!={k:sum(r[k] for r in rows) for k in fields}:
            raise ValueError('WAV decode denominator mismatch')
        for row in rows:
            if row['wave_members']!=row['decoded_members']+row['rejected_members'] or row['rejected_members']!=len(row['failures']):
                raise ValueError('WAV decode result partition mismatch')
        if value['counts']!=dict(Counter(r['status'] for r in rows)):
            raise ValueError('WAV decode status reconciliation failed')
    elif name=='wave_headers':
        fields=('wave_members','header_finding_members','block_finding_members')
        if value['total']!=len(rows) or totals!={k:sum(r[k] for r in rows) for k in fields}:
            raise ValueError('WAV denominator mismatch')
        if value['counts']!=dict(Counter(r['status'] for r in rows)):
            raise ValueError('WAV status reconciliation failed')
        for row in rows:
            if row['wave_members']!=sum(f['members'] for f in row['formats']):
                raise ValueError('WAV format partition mismatch')
            for field, findings in (('header_finding_members','header_findings'),
                                    ('block_finding_members','block_findings')):
                if row[field]!=sum(bool(f[findings]) for f in row['findings']):
                    raise ValueError('WAV finding partition mismatch')
    elif name=='hlod_names':
        if value['total']!=len(rows) or totals['child_occurrences']!=sum(r['child_occurrences'] for r in rows):
            raise ValueError('HLOD name denominator mismatch')
        for row in rows:
            if row['child_occurrences']!=sum(row[k] for k in ('header_candidate_matches','builtin_null_names','unresolved_occurrences')):
                raise ValueError('HLOD resolution partition mismatch')
    return rows


def consolidate(inputs):
    inputs=list(inputs)
    identities={name:hashlib.sha256(data).hexdigest() for name,data in inputs}
    dependencies={'spatial_presence':('chunk_inventory_sha256','level_chunks'),
                  'visibility_bounds':('presence_sha256','spatial_presence'),
                  'w3d_consumers':('inventory_sha256','w3d_chunks'),
                  'wave_decode':('wave_inventory_sha256','wave_headers'),
                  'missing_definition_callers':('inventory_sha256','definition_instances'),
                  'host_script_registry':('inventory_sha256','link'),
                  'live_script_bindings':('registry_sha256','host_script_registry'),
                  'live_script_parameters':('registry_sha256','host_script_registry'),
                  'script_parameter_reads':('registry_sha256','host_script_registry'),
                  'script_parameter_surface':('reads_sha256','script_parameter_reads')}
    rows = []
    receipts = []
    for name, data in inputs:
        value = json.loads(data)
        if name == 'script_command_port_dependencies':
            for key, parent in (('command_bodies', 'script_command_bodies'), ('port_guards', 'port_guards')):
                if parent in identities and value['parent_sha256'].get(key) != identities[parent]:
                    raise ValueError(f'{name}: stale parent inventory identity')
        if name in {'level_persist_closure', 'database_persist_closure', 'database_definition_closure'}:
            for parent in value.get('inputs', []):
                parent_name=Path(parent['source']).stem
                if parent_name in identities and parent['sha256']!=identities[parent_name]:
                    raise ValueError(f'{name}: stale registry parent inventory identity')
        if name in dependencies:
            field,parent=dependencies[name]
            if parent in identities and value.get(field)!=identities[parent]:
                raise ValueError(f'{name}: stale parent inventory identity')
        if name=='w3d_consumers' and 'link' in identities and value.get('link_inventory_sha256')!=identities['link']:
            raise ValueError('W3D consumers: stale link inventory identity')
        if name in {'live_script_bindings','live_script_parameters','script_parameter_reads'} and 'retail' in identities and value.get('retail_sha256')!=identities['retail']:
            raise ValueError('Live script bindings: stale retail inventory identity')
        root_rows = root_records(name, value)
        count = 0
        for pointer, record, mission in status_records(value):
            if record['status'] == 'original_compiled':
                continue
            status = record['status']
            severity = ('visual' if name in {'renderer', 'procedural_fvf_layouts'} and status == 'missing' else
                        'missing_behavior' if status in {'missing', 'stubbed_or_noop', 'disabled_by_port_guard'}
                        else 'unclassified')
            label = next((record[k] for k in ('name', 'title', 'label', 'symbol', 'source', 'file', 'map', 'chunk_id', 'member', 'chunk_path')
                          if k in record), pointer)
            review = record.get('review', {})
            rows.append({'id': hashlib.sha256((name + pointer).encode()).hexdigest(),
                         'sweep': name, 'inventory_pointer': pointer,
                         'label': str(label), 'status': status, 'severity': severity,
                         'severity_basis': 'scoped inventory finding' if severity != 'unclassified' else 'requires impact review',
                         'affected_missions_modes': [mission] if mission else record.get('affected_maps', review.get('affected_scope', ['unknown; callers and retail usage require reconciliation'])),
                         'original_owner': review.get('original_owner', 'requires original-owner review'),
                         'acceptance_open': review.get('acceptance_open', record.get('acceptance_open', 'requires caller, behavior and evidence-class review')),
                         'review_evidence_pointer': pointer + '/review' if review else None,
                         'evidence_class': record.get('evidence_class', 'parent_inventory_metadata'),
                         'evidence_source': f'reports/generated/sweeps/{name}.json',
                         'cluster': ('renderer' if name=='procedural_fvf_layouts' else
                                     'link' if name in {'host_definition_registry', 'host_script_registry', 'host_network_registry', 'host_prototype_registry', 'level_persist_closure', 'database_persist_closure', 'database_definition_closure'} else
                                     'scripts' if name in SCRIPT_SUPPLEMENTS or name in {'live_script_bindings','live_script_parameters','script_parameter_reads','host_script_parameters','script_parameter_surface','script_load_destinations'} else
                                     'retail' if name in SUPPLEMENTS else name)})
            count += 1
        receipts.append({'sweep': name, 'sha256': hashlib.sha256(data).hexdigest(),
                         'issue_url': f'https://github.com/TheGh0stShip/RenegadeVita/issues/{ISSUES[name]}' if name in ISSUES else None,
                         'root_rows': len(root_rows), 'retained_status_records': count,
                         'complete': value.get('complete', False),
                         'coverage_risks': value.get('open_risks', value.get('coverage_open', value.get('limits', [])))})
    priority = {'crash_freeze': 0, 'progression_blocker': 1, 'missing_behavior': 2,
                'wrong_behavior': 3, 'visual': 4, 'audio': 5, 'performance': 6, 'unclassified': 7}
    rows.sort(key=lambda r: (priority[r['severity']], r['sweep'], r['inventory_pointer']))
    return {'schema': 1, 'complete': False, 'total': len(rows),
            'counts': dict(sorted(Counter(r['status'] for r in rows).items())),
            'severity_counts': dict(sorted(Counter(r['severity'] for r in rows).items())),
            'inputs': receipts, 'rows': rows,
            'limitations': ['Counts are evidence records, not unique defects',
                            'Supplementary inventories overlap; records are not deduplicated across evidence layers',
                            'Nested status records retained separately; matching review statuses merged with parent findings',
                            'Unclassified rows have no established impact severity',
                            'Excluded and replaced records remain for proof/acceptance review',
                            'Sweep incompleteness and unclassified caller/mode impact prevent Phase 1 exit']}


def markdown(result):
    def cell(value):
        return str(value).replace('|', '\\|').replace('\n', ' ')
    lines = ['# Full port gap register', '',
             'Initial consolidation; Phase 1 remains incomplete. Every non-`original_compiled`',
             f'status record in the eight sweeps and {len(SUPPLEMENTS)} supplements is retained, including nested records.',
             'Supplementary inventories overlap; their counts are not unique missing features.',
             'Rows count evidence records, not unique defects. Unknown impact is unclassified;',
             'it is not silently ranked as a confirmed crash or progression blocker.', '',
             'Reproduce with `python3 -m tools.consolidate_sweep_gaps`.', '',
             '## Sweep reconciliation', '', '| Sweep | Root rows | Retained records | Complete |',
             '| --- | ---: | ---: | --- |']
    for item in result['inputs']:
        lines.append(f"| {item['sweep']} | {item['root_rows']} | {item['retained_status_records']} | {item['complete']} |")
    lines += ['', 'Original owners and detailed evidence remain at the inventory JSON pointers.',
              'Clusters require caller/mode review and required evidence classes before fixes.',
              'Sweep clusters are tracked in issues [5–12](https://github.com/TheGh0stShip/RenegadeVita/issues).',
              'Matching embedded reviews are provenance for their parent findings; their status',
              'is not counted twice. Severity escalation and per-gap dependencies remain open.', '',
              '## Retained records', '', '| Sweep / JSON pointer | Label | Status | Severity | Affected missions/modes |',
              '| --- | --- | --- | --- | --- |']
    for row in result['rows']:
        lines.append('| ' + ' | '.join(cell(v) for v in (
            row['sweep'] + ' ' + row['inventory_pointer'], row['label'], row['status'],
            row['severity'], ', '.join(row['affected_missions_modes']))) + ' |')
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('reports/generated/sweeps/gaps.json'))
    parser.add_argument('--markdown', type=Path, default=Path('reports/FULL_PORT_GAP_REGISTER.md'))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    result = consolidate([(name, (root / f'reports/generated/sweeps/{name}.json').read_bytes()) for name in SWEEPS + SUPPLEMENTS])
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    args.markdown.write_text(markdown(result))
    print(json.dumps({'total': result['total'], 'counts': result['counts']}))


if __name__ == '__main__':
    main()
