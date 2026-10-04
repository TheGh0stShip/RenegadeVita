"""Compare explicit D3D enum values without executing either header.

The reference is a supplied source header, not proof of SDK or device behavior.
Expressions, implicit values and absent names remain unresolved.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

from audit_sweep_port_guards import mask_noncode


def assignments(source):
    result = {}
    for match in re.finditer(r'\b(D3D[A-Z][A-Z0-9_]*)\s*=\s*([^,;}\n]+)', mask_noncode(source)):
        expression = match[2].strip()
        literal = re.fullmatch(r'(0[xX][0-9a-fA-F]+|[0-9]+)[uUlL]*', expression)
        value = int(literal[1], 16 if literal[1].lower().startswith('0x') else 10) if literal else None
        result.setdefault(match[1], []).append({'value': value, 'expression': expression,
            'line': source.count('\n', 0, match.start()) + 1})
    return result


def compare(native, reference):
    left, right = assignments(native), assignments(reference)
    rows = []
    for name in sorted(left):
        a, b = left[name], right.get(name, [])
        status = 'unresolved'
        if len(a) == len(b) == 1 and a[0]['value'] is not None and b[0]['value'] is not None:
            status = 'equal' if a[0]['value'] == b[0]['value'] else 'different'
        rows.append({'symbol': name, 'native': a, 'reference': b, 'comparison': status})
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native', type=Path, required=True)
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    native, reference = args.native.read_bytes(), args.reference.read_bytes()
    rows = compare(native.decode(), reference.decode())
    document = {'schema_version': 1, 'evidence_class': 'supplied_header_literal_comparison',
        'native_sha256': hashlib.sha256(native).hexdigest(),
        'reference_sha256': hashlib.sha256(reference).hexdigest(),
        'scope': 'Explicit assignments in native header; not a complete SDK enum or ABI inventory.',
        'rows': rows, 'totals': {key: sum(r['comparison'] == key for r in rows)
            for key in ('equal', 'different', 'unresolved')}}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(document, indent=2, sort_keys=True) + '\n')
    print(json.dumps(document['totals'], sort_keys=True))


if __name__ == '__main__':
    main()
