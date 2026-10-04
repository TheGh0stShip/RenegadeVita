#!/usr/bin/env python3
"""Inventory original script Load_Data destinations before a shared bounds fix."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

from tools.audit_campaign_source_surface import dsp_sources
from tools.audit_mission_content_bindings import constant_branch_code, masked


def calls(source):
    source = constant_branch_code(masked(source))
    code = masked(source, strings=True)
    rows = []
    for match in re.finditer(r'\bCommands\s*->\s*Load_Data\s*\(', code):
        depth, end, start, parts = 1, match.end(), match.end(), []
        while end < len(code) and depth:
            char = code[end]
            if char == ',' and depth == 1:
                parts.append(source[start:end].strip())
                start = end + 1
            depth += (char == '(') - (char == ')')
            if not depth:
                parts.append(source[start:end].strip())
            end += 1
        rows.append({'line': code.count('\n', 0, match.start()) + 1,
                     'arguments': parts, 'parse_complete': depth == 0 and len(parts) == 3,
                     'size_expression': parts[1] if len(parts) == 3 else None,
                     'destination_expression': parts[2] if len(parts) == 3 else None,
                     'status': 'unknown'})
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    directory = Path('upstream/CnC_Renegade/Code/Scripts')
    units = dsp_sources(directory / 'Scripts.dsp')
    rows = []
    for unit in units:
        for row in calls((directory / unit).read_text(encoding='latin1')):
            row['source'] = unit
            rows.append(row)
    receipt = {
        'schema_version': 1, 'complete': False, 'total': len(rows), 'rows': rows,
        'counts': dict(Counter(row['status'] for row in rows)), 'shipped_units': len(units),
        'parse_complete': sum(row['parse_complete'] for row in rows),
        'source_sha256': {unit: hashlib.sha256((directory / unit).read_bytes()).hexdigest() for unit in units},
        'parser_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'shared_owner_sha256': hashlib.sha256(Path('staging/combat/scriptcommands.cpp').read_bytes()).hexdigest(),
        'shared_owner': 'Combat/scriptcommands.cpp::Load_Data',
        'review': ['Shared owner reads Cur_Micro_Chunk_Length bytes; destination capacity is assertion-only.',
                   'Cinematic saved-command caller uses len < 200 without a positive-length check.',
                   'Shared runtime bounds plus destination initialization/termination require a tested fix cluster.'],
        'limits': ['Lexical explicit Commands->Load_Data calls in shipped units only.',
                   'Computed pointers, arrays, helper indirection and actual destination capacities require review.',
                   'No malformed save executed; valid runtime loads and native behavior remain unverified.'],
    }
    args.output.write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({key: receipt[key] for key in ('total', 'parse_complete', 'shipped_units')}))


if __name__ == '__main__':
    main()
