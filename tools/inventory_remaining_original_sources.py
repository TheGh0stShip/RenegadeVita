"""Enumerate all released C/C++ units; lexical mentions are not link evidence."""
import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def inventory(root, compile_commands=None, target=None):
    code = root / 'upstream/CnC_Renegade/Code'
    sources = sorted(p for p in code.rglob('*') if p.is_file() and
                     p.suffix.lower() in ('.c', '.cpp', '.cxx', '.cc'))
    originals = {}
    for source in sources:
        relative = source.relative_to(code).as_posix()
        originals.setdefault(relative.casefold(), []).append(relative)
    selection = None
    selected = {}
    if compile_commands is not None:
        if not target:
            raise ValueError('compile_commands requires an explicit target')
        commands = json.loads(compile_commands.read_text())
        matched = 0
        for command in commands:
            # CMake emits output separately. Never execute compiler command text.
            output = Path(command.get('output', ''))
            if f'{target}.dir' not in output.parts:
                continue
            matched += 1
            source = Path(command['file'])
            if not source.is_absolute():
                source = Path(command['directory']) / source
            try:
                relative = source.resolve().relative_to((root / 'staging').resolve())
            except ValueError:
                continue  # Port boundaries are not original translation units.
            selected.setdefault(relative.as_posix().casefold(), []).append({
                'source': relative.as_posix(), 'output': str(output),
                'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest()
                                 if source.is_file() else None})
        if not matched:
            raise ValueError(f'No output entries for target {target!r}')
        selection = {'compile_commands': str(compile_commands.resolve()),
                     'sha256': hashlib.sha256(compile_commands.read_bytes()).hexdigest(),
                     'target': target, 'entries': matched,
                     'unmapped_staged_inputs': [entry for key, entries in selected.items()
                                               if key not in originals for entry in entries],
                     'meaning': 'Configured build selection only; compilation and final '
                                'linked retention are not established.'}
    manifests = [root / 'CMakeLists.txt', *sorted((root / 'cmake').glob('*.cmake'))]
    texts = {str(p.relative_to(root)): p.read_text() for p in manifests}
    review_path = root / 'tools/original_source_review.json'
    review_data = json.loads(review_path.read_text()) if review_path.is_file() else {}
    reviews = review_data.get('reviews', {})
    if selection is not None:
        derived = review_data.get('derived_sources', {})
        classified = []
        unmapped = []
        for entry in selection['unmapped_staged_inputs']:
            decision = derived.get(entry['source'])
            if decision is None:
                unmapped.append(entry)
                continue
            if decision['original_owner'] not in originals.get(decision['original_owner'].casefold(), []):
                raise ValueError('Derived source must name an exact released original owner')
            classified.append({**entry, 'source_review': decision})
        selection['derived_staged_inputs'] = classified
        selection['unmapped_staged_inputs'] = unmapped
    # Resolve only known path prefixes, without pretending to evaluate CMake
    # conditions or list membership. Script lists use a separate root variable.
    normalized = {name: text.replace('${RENEGADE_SCRIPT_SOURCE}/', 'scripts/')
                           .replace('${RENEGADE_STAGE}/', '').casefold()
                  for name, text in texts.items()}
    projects = {}
    for project in sorted(code.rglob('*')):
        if not project.is_file() or project.suffix.lower() != '.dsp':
            continue
        for entry in re.findall(r'^SOURCE=(.*)$', project.read_text(errors='replace'), re.M):
            path = (project.parent / entry.strip().strip('"').replace('\\', '/')).resolve()
            projects.setdefault(str(path).casefold(), []).append(str(project.relative_to(code)))
    rows = []
    for source in sources:
        relative = source.relative_to(code).as_posix()
        staged = root / 'staging' / relative
        # Preserve original spelling; case collisions need explicit review.
        mentions = [name for name, text in normalized.items()
                    if relative.casefold() in text]
        rows.append({'original': relative,
                     'original_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
                     'staged_exact_path_exists': staged.is_file(),
                     'manifest_literal_mentions': mentions,
                     'released_project_membership': sorted(set(projects.get(str(source.resolve()).casefold(), []))),
                     'status': 'requires selected-target and owner classification',
                     'linked': None})
        if relative in reviews:
            rows[-1]['source_review'] = reviews[relative]
        if selection is not None:
            entries = selected.get(relative.casefold(), [])
            ambiguous = len(originals[relative.casefold()]) > 1 or \
                        len({entry['source'] for entry in entries}) > 1
            rows[-1]['configured_mapping_ambiguous'] = ambiguous
            rows[-1]['casefold_original_candidates'] = originals[relative.casefold()]
            # Name normalization is useful only when it identifies one owner.
            # Preserve candidate data, but never promote collisions to matches.
            rows[-1]['configured_target_outputs'] = [] if ambiguous else [
                entry['output'] for entry in entries]
            rows[-1]['configured_target_inputs'] = entries
    return {'scope': 'All released C/C++ files, including tools and obsolete units. '
                     'Literal mentions do not prove selection; absence does not prove omission. '
                     'No compile, link or runtime acceptance is inferred.',
            'manifest_sha256': {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                                for p in manifests},
            'configured_selection': selection,
            'source_review_sha256': hashlib.sha256(review_path.read_bytes()).hexdigest()
                                    if review_path.is_file() else None,
            'total': len(rows),
            'by_top_directory': dict(sorted(Counter(r['original'].split('/')[0]
                                                    for r in rows).items())),
            'rows': rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--compile-commands', type=Path)
    parser.add_argument('--target', help='Exact CMake target for configured selection')
    args = parser.parse_args()
    if bool(args.compile_commands) != bool(args.target):
        parser.error('--compile-commands and --target must be supplied together')
    result = inventory(ROOT, args.compile_commands, args.target)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, indent=2) + '\n')
    print(f"Enumerated {result['total']} original units; classification remains open.")


if __name__ == '__main__':
    main()
