"""S1 source inventory. Inventory evidence never proves runtime behavior.

Patch history and current source are separate denominators: a later patch may
remove an earlier guard. Unselected patches remain visible, not silently absent.
Function-body classification is deliberately an open coverage gate until its
parser and original-owner review are complete.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
PORT_MACRO = re.compile(r'\b(?:RENEGADE_(?:VITA_\w*|A\w*|HOST_\w*)|_UNIX|VITA|__vita__|__VITA__)\b')
DIRECTIVE = re.compile(r'^\s*#\s*(if|ifdef|ifndef|elif)\b')
STATUSES = {'original_compiled', 'original_patched', 'boundary_replaced',
            'stubbed_or_noop', 'disabled_by_port_guard', 'excluded_with_proof', 'missing', 'unknown'}
LEXICAL_NONCODE = re.compile(
    r'(?:u8|u|U|L)?R"(?P<delimiter>[^\s()\\]{0,16})\([\s\S]*?\)(?P=delimiter)"'
    r'|(?:u8|u|U|L)?"(?:\\[\s\S]|[^"\\])*"'
    r"|(?<![A-Za-z_0-9])(?:u8|u|U|L)?'(?:\\[^\n]|[^'\\\n]){1,8}'"
    r'|//(?:\\\r?\n|[^\n])*|/\*[\s\S]*?\*/')


def mask_noncode(text):
    """Keep physical offsets/lines while hiding comments and literal contents."""
    return LEXICAL_NONCODE.sub(lambda match: re.sub(r'[^\r\n]', ' ', match[0]), text)


def apply_reviews(rows, reviews, expected_inputs=None, current_inputs=None):
    """A reviewed body may be classified only while its syntax identity matches.

    A stale review stays visible as a mismatch and leaves the row unknown.
    Neither a source review nor an unchanged hash establishes runtime acceptance.
    """
    issues = [{'file': file, 'reason': 'review caller/context input absent or changed'}
              for file, checksum in (expected_inputs or {}).items()
              if (current_inputs or {}).get(file) != checksum]
    if issues:
        return issues
    for review in reviews:
        if review['status'] not in STATUSES:
            raise ValueError('Invalid review status: ' + review['status'])
        matches = [row for row in rows if row['kind'] == 'port_function' and
                   row['file'] == review['file'] and row['declarator'] == review['declarator']]
        if len(matches) != 1 or matches[0].get('body_sha256') != review['body_sha256']:
            issues.append({'file': review['file'], 'declarator': review['declarator'],
                           'reason': 'review identity absent, ambiguous or changed'})
            continue
        row = matches[0]
        row['status'] = review['status']
        row['review'] = {key: review[key] for key in
                         ('original_owner', 'behavior', 'callers', 'affected_scope', 'acceptance_open')}
        row['classification_evidence_class'] = 'source_review'
    return issues


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def directives(lines):
    """Read logical preprocessor lines, retaining every physical source line."""
    result = []
    masked_lines = mask_noncode('\n'.join(lines)).split('\n')
    i = 0
    while i < len(lines):
        first = i
        parts = [lines[i]]
        masked_parts = [masked_lines[i]]
        while parts[-1].rstrip().endswith('\\') and i + 1 < len(lines):
            i += 1
            parts.append(lines[i])
            masked_parts.append(masked_lines[i])
        value = '\n'.join(parts)
        masked_value = '\n'.join(masked_parts)
        if DIRECTIVE.match(masked_value) and PORT_MACRO.search(masked_value):
            result.append((first, i, value))
        i += 1
    return result


def patch_guards(text):
    """Reconstruct both hunk sides, including context and continued directives.

    Hunk coordinates describe that patch's input/output, not today's staged
    files. Keep removals too, so restorations cannot look like active omissions.
    """
    rows = []
    target = None
    sides = {'old': [], 'new': []}

    def flush():
        for side, entries in sides.items():
            for first, last, value in directives([e['text'] for e in entries]):
                selected = entries[first:last + 1]
                if any(e['changed'] for e in selected):
                    rows.append({'change': 'added' if side == 'new' else 'removed',
                                 'target': target,
                                 'patch_lines': [e['patch_line'] for e in selected],
                                 'hunk_lines': [e['line'] for e in selected],
                                 'directive': value})
        for side in sides:
            sides[side] = []

    old_line = new_line = 0
    in_hunk = False
    for number, line in enumerate(text.splitlines(), 1):
        if line.startswith('+++ '):
            flush()
            target = line[4:].split('\t')[0]
            in_hunk = False
        elif line.startswith('@@ '):
            flush()
            match = re.match(r'@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@', line)
            if not match:
                raise ValueError(f'Unsupported hunk header at patch line {number}')
            old_line, new_line = (int(x) for x in match.groups())
            in_hunk = True
        elif in_hunk and line[:1] in (' ', '+', '-'):
            prefix = line[0]
            if prefix != '+':
                sides['old'].append({'text': line[1:], 'line': old_line,
                                     'patch_line': number, 'changed': prefix == '-'})
                old_line += 1
            if prefix != '-':
                sides['new'].append({'text': line[1:], 'line': new_line,
                                     'patch_line': number, 'changed': prefix == '+'})
                new_line += 1
    flush()
    return rows


def stage_patch_selection(text):
    """Literal staging references; selection is not proof of application."""
    return re.findall(r'\$rv_root/(port/patches/[^"\s]+\.patch)', text)


def wrapper_references(text):
    return [{'symbol': match[1], 'line': text.count('\n', 0, match.start()) + 1}
            for match in re.finditer(r'--wrap(?:=|,)([A-Za-z_][A-Za-z_0-9]*)', text)]


def audit(root=ROOT, include_functions=False):
    stage = root / 'tools/stage_sources.sh'
    selection = stage_patch_selection(stage.read_text())
    selected = set(selection)
    patches = sorted((root / 'port/patches').glob('*.patch'))
    rows, inputs, patch_inventory, function_files = [], {}, [], []
    cpp_parser = None
    if include_functions:
        from sweep_cpp_functions import function_inventory, parser
        cpp_parser = parser()
    for patch in patches:
        relative = patch.relative_to(root).as_posix()
        inputs[relative] = digest(patch)
        patch_inventory.append({'path': relative, 'sha256': inputs[relative],
                                'stage_reference_count': selection.count(relative)})
        for row in patch_guards(patch.read_text(errors='replace')):
            rows.append({'kind': 'patch_guard', 'file': relative,
                         'selected_by_stage_script': relative in selected,
                         'status': 'unknown', 'evidence_class': 'source_patch', **row})
    for directory in ('port', 'staging'):
        for path in sorted((root / directory).rglob('*')):
            if not path.is_file() or path.suffix.lower() not in ('.c', '.cpp', '.h', '.hpp', '.inl'):
                continue
            relative = path.relative_to(root).as_posix()
            text = path.read_text(errors='replace')
            inputs[relative] = digest(path)
            for first, last, value in directives(text.splitlines()):
                rows.append({'kind': 'current_source_guard', 'file': relative,
                             'line': first + 1, 'end_line': last + 1,
                             'directive': value, 'status': 'unknown',
                             'evidence_class': 'current_source'})
            if directory == 'port' and include_functions:
                inventory = function_inventory(text, cpp_parser)
                function_files.append({'file': relative,
                                       'functions': len(inventory['functions']),
                                       'parse_errors': len(inventory['parse_errors']),
                                       'root_has_error': inventory['root_has_error']})
                for row in inventory['functions']:
                    rows.append({'kind': 'port_function', 'file': relative,
                                 'status': 'unknown', 'evidence_class': 'source_syntax', **row})
                for row in inventory['parse_errors']:
                    rows.append({'kind': 'port_parse_unknown', 'file': relative,
                                 'status': 'unknown', 'evidence_class': 'source_syntax', **row})
    build_files = [root / 'CMakeLists.txt', root / 'tools/host_a30_definitions/CMakeLists.txt']
    build_files += sorted((root / 'cmake').rglob('*.cmake'))
    for path in build_files:
        relative = path.relative_to(root).as_posix()
        inputs[relative] = digest(path)
        for row in wrapper_references(path.read_text()):
            rows.append({'kind': 'link_wrapper_reference', 'file': relative,
                         'status': 'unknown', 'evidence_class': 'build_source', **row})
    inputs['tools/stage_sources.sh'] = digest(stage)
    review_path = root / 'tools/sweep_reviews/port_guards.json'
    review_issues = []
    if include_functions and review_path.exists():
        inputs[review_path.relative_to(root).as_posix()] = digest(review_path)
        review_document = json.loads(review_path.read_text())
        review_issues = apply_reviews(rows, review_document['reviews'],
                                     review_document.get('evidence_inputs_sha256'), inputs)
    kinds = dict(sorted(Counter(row['kind'] for row in rows).items()))
    return {'schema_version': 1, 'sweep': 'S1', 'complete': False,
            'evidence_class': 'source_inventory',
            'totals': {'rows': len(rows), 'by_kind': kinds,
                       'by_status': dict(Counter(row['status'] for row in rows)),
                       'patch_files': len(patches), 'stage_patch_references': len(selection)},
            'patch_inventory': patch_inventory,
            'function_files': function_files,
            'function_inventory_requested': include_functions,
            'review_identity_issues': review_issues,
            'missing_selected_patches': sorted(selected - {p.relative_to(root).as_posix() for p in patches}),
            'inputs_sha256': inputs, 'rows': rows,
            'coverage_open': [
                ('Review function-body signals, including log-only/constant expressions and '
                 'macro-generated definitions.' if include_functions else
                 'Function definitions under port/: constant, early, log-only returns and markers.'),
                'Review each original owner, reachable callers and affected missions/modes.',
                'Classify current guards; conditions have not been evaluated for a build profile.',
                'Match patch history to final staged source; hunk lines are historical coordinates.',
                'Patch hunks can begin inside omitted lexical context; current-source guards are separate evidence.',
                'Macro-generated conditions/functions and non-CMake link flags need denominators.',
                'Literal stage references do not prove selected patches applied successfully.',
                'Source selection does not prove compilation, linkage, behavior or pixels.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--include-functions', action='store_true',
                        help='Require the pinned C++ syntax parser and enumerate all port functions')
    args = parser.parse_args()
    result = audit(args.root, include_functions=args.include_functions)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'complete': result['complete'], **result['totals']}))


if __name__ == '__main__':
    main()
