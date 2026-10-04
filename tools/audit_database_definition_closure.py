#!/usr/bin/env python3
"""Join retail persistence envelopes to definition class IDs by symbol class.

The mapping is symbol evidence, not execution of factory Create or Load.
"""
import argparse
import hashlib
import json
from pathlib import Path


def reconcile(persist, definitions):
    classes = {}
    for row in definitions['rows']:
        for name in row['classes']:
            classes.setdefault(name, []).append(row)
    rows = []
    for record in persist['rows']:
        matches = [row for name in record['arm_classes'] for row in classes.get(name, [])]
        ids = sorted({row['class_id'] for row in matches})
        ambiguous = len(ids) > 1
        rows.append({'persistence_chunk_id': record['chunk_id'],
                     'persistence_chunk_id_hex': record['chunk_id_hex'],
                     'candidate_instances': record['candidate_instances'],
                     'arm_persistence_classes': record['arm_classes'],
                     'definition_class_ids': ids,
                     'class_id_mapping_ambiguous': ambiguous,
                     'all_host_definition_lookups_match': bool(matches) and all(r['matches'] for r in matches),
                     'all_arm_definition_symbols_present': bool(matches) and all(r['arm_symbol_present'] for r in matches),
                     'status': 'unknown', 'evidence_class': 'retail_metadata_symbols_and_host_lookup'})
    return {'schema_version': 1, 'complete': False, 'rows': rows,
            'totals': {'persistence_ids': len(rows),
                       'mapped': sum(bool(r['definition_class_ids']) for r in rows),
                       'unmapped': sum(not r['definition_class_ids'] for r in rows),
                       'ambiguous': sum(r['class_id_mapping_ambiguous'] for r in rows)},
            'limits': ['Class names join demangled template symbols; no actual Create/Load is executed.',
                       'Unmapped editor persistence IDs are open leads, not proven gameplay omissions.',
                       'Definition instance IDs and reference validity require separate reconciliation.',
                       'Host ID lookup and ARM symbols do not prove physical registration or gameplay.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--persist', required=True, type=Path)
    parser.add_argument('--definitions', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    paths = [args.persist, args.definitions]
    result = reconcile(*(json.loads(p.read_text()) for p in paths))
    result['inputs'] = [{'source': p.as_posix(), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
                        for p in paths]
    result['parser_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result['totals']))


if __name__ == '__main__':
    main()
