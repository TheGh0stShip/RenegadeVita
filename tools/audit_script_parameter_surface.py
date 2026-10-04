#!/usr/bin/env python3
"""Enumerate parameter-related call syntax across shipped script units and headers."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re

from tools.audit_campaign_source_surface import dsp_sources
from tools.audit_mission_content_bindings import constant_branch_code, masked

METHOD = re.compile(r'\b(Get_[A-Za-z_0-9]*Parameters?[A-Za-z_0-9]*)\s*\(')


def surface(source):
    source = constant_branch_code(masked(source))
    code = masked(source, strings=True)
    rows = []
    for match in METHOD.finditer(code):
        depth, end = 1, match.end()
        while end < len(code) and depth:
            depth += (code[end] == '(') - (code[end] == ')')
            end += 1
        tail = code[end:].lstrip()
        if tail.startswith('const'):
            tail = tail[5:].lstrip()
        kind = 'definition_candidate' if not depth and tail.startswith('{') else 'call_or_declaration_candidate'
        rows.append({'method': match[1], 'line': code.count('\n', 0, match.start()) + 1,
                     'column': match.start() - code.rfind('\n', 0, match.start()),
                     'syntax_kind': kind, 'balanced_arguments': depth == 0,
                     'status': 'unknown'})
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reads', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    directory = Path('upstream/CnC_Renegade/Code/Scripts')
    sources = [directory / name for name in dsp_sources(directory / 'Scripts.dsp')]
    headers = sorted(path for path in directory.iterdir() if path.suffix.lower() == '.h')
    known = defaultdict(set)
    for row in json.loads(args.reads.read_text())['rows']:
        known[(row['original_owner'], row['line'], row['method'])].add(row['script'])
    rows, hashes = [], {}
    for path in sources + headers:
        hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
        for row in surface(path.read_text(encoding='latin1')):
            owners = sorted(known.get((path.name, row['line'], row['method']), set()))
            row.update(source=path.name, source_kind='header' if path in headers else 'shipped_translation_unit',
                       live_body_owner_candidates=owners,
                       coverage='live_body_read' if owners else 'outside_live_body_read_inventory')
            rows.append(row)
    receipt = {
        'schema_version': 1, 'complete': False, 'total': len(rows), 'rows': rows,
        'counts': dict(Counter(row['status'] for row in rows)),
        'categories': dict(Counter(row['coverage'] for row in rows)),
        'syntax_kinds': dict(Counter(row['syntax_kind'] for row in rows)),
        'methods': dict(Counter(row['method'] for row in rows)),
        'shipped_units': len(sources), 'headers': len(headers),
        'reads_sha256': hashlib.sha256(args.reads.read_bytes()).hexdigest(),
        'parser_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'helper_sha256': {name: hashlib.sha256(Path(name).read_bytes()).hexdigest()
                          for name in ('tools/audit_campaign_source_surface.py',
                                       'tools/audit_mission_content_bindings.py')},
        'source_sha256': hashes,
        'dsp_sha256': hashlib.sha256((directory / 'Scripts.dsp').read_bytes()).hexdigest(),
        'limits': ['Lexical syntax denominator includes method definitions and declarations; not all rows are calls.',
                   'Headers are scanned independently; include/branch/macro expansion and overload resolution remain open.',
                   'Known script attribution uses source line and method; repeated expressions need AST review.',
                   'Cinematic Get_Command/First/Next_Parameter APIs are distinct from ScriptImpClass descriptor lookup.',
                   'No callback execution, retail cinematic parsing or ARM/physical acceptance established.'],
    }
    args.output.write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({key: receipt[key] for key in ('total','categories','syntax_kinds','shipped_units','headers')}))


if __name__ == '__main__':
    main()
