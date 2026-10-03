#!/usr/bin/env python3
"""Inventory staged translation units against one ARM target's build database.

Map mentions prove neither section retention nor factory registration.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path
import subprocess


def digest(data):
    return hashlib.sha256(data).hexdigest()


def registration_candidates(code):
    # Preserve offsets while masking comments and literals. Candidates inside
    # inactive preprocessor branches remain candidates, never proven registrars.
    pattern = r'//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\''
    masked = re.sub(pattern, lambda m: ''.join('\n' if c == '\n' else ' ' for c in m[0]),
                    code, flags=re.S)
    expressions = {
        'script': r'\bDECLARE_SCRIPT\s*\(\s*(\w+)',
        'definition': r'\bDECLARE_DEFINITION_FACTORY\s*\(\s*(\w+)\s*,\s*(\w+)',
        'network': r'\bDECLARE_NETWORKOBJECT_FACTORY\s*\(\s*(\w+)\s*,\s*(\w+)',
        'persist': r'\bSimplePersistFactoryClass\s*<\s*(\w+)\s*,\s*(\w+)\s*>\s*(\w+)\s*[;(]',
    }
    found = []
    for kind, expression in expressions.items():
        for match in re.finditer(expression, masked):
            found.append({'kind': kind, 'arguments': list(match.groups()),
                          'line': code.count('\n', 0, match.start()) + 1,
                          'status': 'unknown', 'evidence_class': 'source_candidate'})
    return sorted(found, key=lambda r: (r['line'], r['kind']))


def defined_symbols(data):
    result = {}
    for line in data.decode('utf-8', errors='replace').splitlines():
        match = re.fullmatch(r'([0-9a-fA-F]+)\s+([A-Za-z])\s+(\S.*)', line)
        if match and match[2].upper() != 'U':
            result.setdefault(match[3], []).append({'address': match[1].lower(),
                                                    'type': match[2]})
    return result


def inventory(root, database, target, map_bytes, symbol_bytes=b''):
    prefix = f'CMakeFiles/{target}.dir/'
    selected = {}
    for entry in database:
        if not entry.get('output', '').startswith(prefix):
            continue
        source = (Path(entry['directory']) / entry['file']).resolve()
        selected[source] = entry['output']
    map_text = map_bytes.decode('utf-8', errors='replace')
    symbols = defined_symbols(symbol_bytes)
    rows = []
    registrars = []
    for source in sorted((root / 'staging').rglob('*')):
        if source.suffix.lower() not in ('.cpp', '.c', '.cc', '.cxx'):
            continue
        name = source.relative_to(root).as_posix()
        obj = selected.get(source.resolve())
        for candidate in registration_candidates(source.read_text(errors='replace')):
            expected = None
            if candidate['kind'] == 'script':
                expected = '_' + candidate['arguments'][0] + 'Registrant'
            elif candidate['kind'] == 'persist':
                expected = candidate['arguments'][2]
            registrars.append(dict(candidate, source=name,
                                   id=digest(f'{name}:{candidate["line"]}:{candidate["kind"]}'.encode()),
                                   selected_for_target=obj is not None,
                                   expected_symbol=expected,
                                   defined_symbol_matches=symbols.get(expected, []),
                                   registration_verified=False))
        rows.append({'id': digest(name.encode()), 'source': name,
                     'source_sha256': digest(source.read_bytes()),
                     'selected_for_target': obj is not None,
                     'map_mentions_object': bool(obj and obj in map_text),
                     'status': 'unknown', 'evidence_class': 'build_metadata',
                     'registration_verified': False})
    staged_names = {}
    for row in rows:
        staged_names.setdefault(row['source'].removeprefix('staging/').casefold(), []).append(row['source'])
    upstream_rows = []
    upstream = root / 'upstream' / 'CnC_Renegade' / 'Code'
    for source in sorted(upstream.rglob('*')):
        if source.suffix.lower() not in ('.cpp', '.c', '.cc', '.cxx'):
            continue
        relative = source.relative_to(upstream).as_posix()
        name = source.relative_to(root).as_posix()
        upstream_rows.append({'id': digest(name.encode()), 'source': name,
                              'source_sha256': digest(source.read_bytes()),
                              'staged_candidates': staged_names.get(relative.casefold(), []),
                              'status': 'unknown', 'evidence_class': 'source_inventory'})
    return {'schema': 1, 'sweep': 'S3', 'target': target, 'complete': False,
            'scope': 'All staged C/C++ translation units; includes potential non-runtime units',
            'open_risks': ['Runtime versus editor/tool upstream classification',
                           'Manual, templated, alternate and header registrars',
                           'Console/game-mode/prototype registrations',
                           'Inactive preprocessor registration candidates',
                           'Discarded versus retained sections', 'Retail factory IDs',
                           'Selected sources may differ from the retained build inputs'],
            'map_sha256': digest(map_bytes), 'total': len(rows),
            'symbols_sha256': digest(symbol_bytes) if symbol_bytes else None,
            'selected': sum(r['selected_for_target'] for r in rows),
            'map_mentioned': sum(r['map_mentions_object'] for r in rows),
            'counts': {'unknown': len(rows)}, 'rows': rows,
            'upstream_total': len(upstream_rows),
            'upstream_without_staged_candidate': sum(not r['staged_candidates'] for r in upstream_rows),
            'upstream_rows': upstream_rows,
            'registration_candidate_total': len(registrars),
            'registration_candidates_with_defined_symbol': sum(bool(r['defined_symbol_matches']) for r in registrars),
            'registration_candidates': registrars}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--map', type=Path, required=True)
    parser.add_argument('--target', required=True)
    parser.add_argument('--symbols', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    database = json.loads(subprocess.check_output(
        ['ninja', '-C', str(args.build), '-t', 'compdb'], text=True, timeout=30))
    result = inventory(root, database, args.target, args.map.read_bytes(), args.symbols.read_bytes())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ('total', 'selected', 'map_mentioned', 'counts')}))


if __name__ == '__main__':
    main()
