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
STATUSES = {'original_compiled', 'original_patched', 'boundary_replaced',
            'stubbed_or_noop', 'disabled_by_port_guard', 'excluded_with_proof',
            'missing', 'unknown'}


def status_records(value, pointer='', inherited_map=None):
    if isinstance(value, dict):
        mission = value.get('map', inherited_map)
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


def consolidate(inputs):
    rows = []
    receipts = []
    for name, data in inputs:
        value = json.loads(data)
        root_rows = value['rows']
        expected = value.get('total', value.get('totals', {}).get('rows'))
        if expected != len(root_rows):
            raise ValueError(f'{name}: root denominator mismatch')
        actual = dict(Counter(r['status'] for r in root_rows))
        declared = value.get('counts', value.get('totals', {}).get('by_status'))
        if actual != declared:
            raise ValueError(f'{name}: status reconciliation failed')
        count = 0
        for pointer, record, mission in status_records(value):
            if record['status'] == 'original_compiled':
                continue
            status = record['status']
            severity = ('visual' if name == 'renderer' and status == 'missing' else
                        'missing_behavior' if status in {'missing', 'stubbed_or_noop', 'disabled_by_port_guard'}
                        else 'unclassified')
            label = next((record[k] for k in ('name', 'label', 'symbol', 'source', 'file', 'map', 'chunk_id')
                          if k in record), pointer)
            review = record.get('review', {})
            rows.append({'id': hashlib.sha256((name + pointer).encode()).hexdigest(),
                         'sweep': name, 'inventory_pointer': pointer,
                         'label': str(label), 'status': status, 'severity': severity,
                         'severity_basis': 'scoped inventory finding' if severity != 'unclassified' else 'requires impact review',
                         'affected_missions_modes': [mission] if mission else review.get('affected_scope', ['unknown; callers and retail usage require reconciliation']),
                         'original_owner': review.get('original_owner', 'requires original-owner review'),
                         'acceptance_open': review.get('acceptance_open', 'requires caller, behavior and evidence-class review'),
                         'review_evidence_pointer': pointer + '/review' if review else None,
                         'evidence_class': record.get('evidence_class', 'parent_inventory_metadata'),
                         'evidence_source': f'reports/generated/sweeps/{name}.json',
                         'cluster': name})
            count += 1
        receipts.append({'sweep': name, 'sha256': hashlib.sha256(data).hexdigest(),
                         'issue_url': f'https://github.com/TheGh0stShip/RenegadeVita/issues/{ISSUES[name]}' if name in ISSUES else None,
                         'root_rows': len(root_rows), 'retained_status_records': count,
                         'complete': value.get('complete', False),
                         'coverage_risks': value.get('open_risks', value.get('coverage_open', []))})
    priority = {'crash_freeze': 0, 'progression_blocker': 1, 'missing_behavior': 2,
                'wrong_behavior': 3, 'visual': 4, 'audio': 5, 'performance': 6, 'unclassified': 7}
    rows.sort(key=lambda r: (priority[r['severity']], r['sweep'], r['inventory_pointer']))
    return {'schema': 1, 'complete': False, 'total': len(rows),
            'counts': dict(sorted(Counter(r['status'] for r in rows).items())),
            'severity_counts': dict(sorted(Counter(r['severity'] for r in rows).items())),
            'inputs': receipts, 'rows': rows,
            'limitations': ['Counts are evidence records, not unique defects',
                            'Nested status records retained separately; matching review statuses merged with parent findings',
                            'Unclassified rows have no established impact severity',
                            'Excluded and replaced records remain for proof/acceptance review',
                            'Sweep incompleteness and unclassified caller/mode impact prevent Phase 1 exit']}


def markdown(result):
    def cell(value):
        return str(value).replace('|', '\\|').replace('\n', ' ')
    lines = ['# Full port gap register', '',
             'Initial consolidation; Phase 1 remains incomplete. Every non-`original_compiled`',
             'status record in the eight inventories is retained, including nested records.',
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
    result = consolidate([(name, (root / f'reports/generated/sweeps/{name}.json').read_bytes()) for name in SWEEPS])
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    args.markdown.write_text(markdown(result))
    print(json.dumps({'total': result['total'], 'counts': result['counts']}))


if __name__ == '__main__':
    main()
