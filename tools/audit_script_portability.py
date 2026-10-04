#!/usr/bin/env python3
"""Inventory compiler-assumption syntax across the original Scripts build surface.

Findings are review candidates, never proof of undefined behavior or type flow.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

from tools.audit_campaign_source_surface import dsp_sources
from tools.audit_mission_content_bindings import masked

PATTERNS = {
    'case_insensitive_lookup': r'\b(?:_?stricmp|_?strnicmp|strcasecmp|strncasecmp)\s*\(',
    'plain_char_declaration': r'\bchar\s+(?:\*\s*)*[A-Za-z_]\w*',
    'dereference_order_comparison': r'\*\s*[A-Za-z_]\w*\s+(?:<=|>=|<|>)(?!=)',
    'integer_cast': r'\(\s*(?:(?:unsigned|signed)\s+)?(?:int|long|size_t|intptr_t|uintptr_t)\s*\)(?=\s*[\w(&*+\-])',
    'address_to_integer_cast': r'\(\s*(?:(?:unsigned|signed)\s+)?(?:int|long|intptr_t|uintptr_t)\s*\)\s*&\s*[A-Za-z_]\w*',
    'scalar_pointer_cast': r'\(\s*(?:const\s+)?(?:int|long|char|float|double|void)\s*\*\s*\)(?=\s*[\w(&*+\-])',
    'size_expression': r'\bsizeof\s*(?:\([^;\n]*?\)|[A-Za-z_]\w*)',
    'loop_local_declaration': r'\bfor\s*\(\s*(?:int|unsigned|long|char|float|double|size_t)\s+(?:\*\s*)?[A-Za-z_]\w*',
    'bare_scalar_declaration': r'(?m)^[^\S\n]*(?:int|unsigned int|long|float|double|bool|char)\s+(?:\*\s*)?[A-Za-z_]\w*\s*;',
}


def findings(source):
    code = masked(source, strings=True)
    declarations = list(re.finditer(r'\bDECLARE_SCRIPT\s*\(\s*(\w+)', code))
    result = []
    for category, pattern in PATTERNS.items():
        for match in re.finditer(pattern, code):
            if category == 'plain_char_declaration' and re.search(r'\b(?:unsigned|signed)\s*$', code[:match.start()]):
                continue
            owners = [m[1] for m in declarations if m.start() <= match.start()]
            result.append({'category': category,
                           'line': code.count('\n', 0, match.start()) + 1,
                           'offset': match.start(),
                           'syntax_sha256': hashlib.sha256(match[0].encode()).hexdigest(),
                           'preceding_script_declaration_candidate': owners[-1] if owners else None,
                           'status': 'unknown', 'evidence_class': 'lexical_compiler_assumption_candidate'})
    return sorted(result, key=lambda r: (r['offset'], r['category']))


def inventory(root):
    original = root / 'upstream/CnC_Renegade/Code/Scripts'
    staged = root / 'staging/scripts'
    units = dsp_sources(original / 'Scripts.dsp')
    if len(units) != len(set(units)):
        raise ValueError('Duplicate Scripts.dsp unit')
    headers = sorted(p.name for p in original.glob('*.h'))
    rows = []
    for name in units + headers:
        source = original / name
        native = staged / name
        data = source.read_bytes()
        original_findings = findings(data.decode('latin1'))
        staged_data = native.read_bytes() if native.is_file() else None
        staged_findings = findings(staged_data.decode('latin1')) if staged_data is not None else []
        rows.append({'name': name, 'surface': 'dsp_unit' if name in units else 'directory_header',
                     'original_source': source.relative_to(root).as_posix(),
                     'original_sha256': hashlib.sha256(data).hexdigest(),
                     'staged_source': native.relative_to(root).as_posix(),
                     'staged_present': staged_data is not None,
                     'staged_sha256': hashlib.sha256(staged_data).hexdigest() if staged_data is not None else None,
                     'original_findings': original_findings, 'staged_findings': staged_findings,
                     'status': 'unknown', 'evidence_class': 'original_and_staged_source_metadata'})
    counts = lambda key: dict(sorted(Counter(f['category'] for r in rows for f in r[key]).items()))
    return {'schema_version': 1, 'complete': False, 'total': len(rows),
            'counts': {'unknown': len(rows)}, 'rows': rows,
            'dsp_units': len(units), 'directory_headers': len(headers),
            'staged_present': sum(r['staged_present'] for r in rows),
            'original_categories': counts('original_findings'), 'staged_categories': counts('staged_findings'),
            'dsp_sha256': hashlib.sha256((original/'Scripts.dsp').read_bytes()).hexdigest(),
            'limits': ['Lexical syntax candidates; no type resolution, dataflow or defect verdict.',
                       'Plain-char declarations and dereference comparisons are separate candidates, not a proven signed-char dependency.',
                       'Bare declarations may be class members or assigned before use; uninitialized reads need compiler/dataflow evidence.',
                       'Loop declarations do not prove post-loop scope use.',
                       'Integer casts do not prove pointer truncation; sizeof operands do not prove serialized-width errors.',
                       'Preprocessor alternatives are retained without evaluating platform selection.',
                       'All original directory headers are inventoried, including headers outside the DSP include closure.',
                       'Macros, templates, transitive includes and compiler ABI flags require separate analysis.',
                       'Dereference comparisons require separated operators to avoid template-name matches; compact comparisons can be missed.',
                       'Preceding DECLARE_SCRIPT is an ownership candidate; helpers can follow declarations.',
                       'Native ARMv7 ILP32 and host LP64 execution remain distinct evidence classes.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('reports/generated/sweeps/script_portability.json'))
    args = parser.parse_args()
    result = inventory(Path(__file__).resolve().parents[1])
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({key: result[key] for key in ('total','dsp_units','directory_headers','staged_present','original_categories','staged_categories')}))


if __name__ == '__main__':
    main()
