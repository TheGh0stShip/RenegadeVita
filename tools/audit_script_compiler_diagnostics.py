#!/usr/bin/env python3
"""Collect optimized host compiler diagnostics without modifying build outputs."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import shlex
import subprocess

from tools.audit_campaign_source_surface import dsp_sources

DATAFLOW_OPTIONS = {'-Wuninitialized', '-Wmaybe-uninitialized', '-Wreturn-type'}
REVIEW_OPTIONS = DATAFLOW_OPTIONS | {'-Waggressive-loop-optimizations',
                                   '-Wformat-overflow=', '-Wint-to-pointer-cast'}


def public_summary(receipt):
    rows = []
    for row in receipt['rows']:
        diagnostics = row.get('diagnostics', [])
        rows.append({key: row[key] for key in
                     ('name', 'status', 'compile_command_matches', 'evidence_class',
                      'source_sha256', 'returncode', 'object_sha256', 'parse_error')
                     if key in row})
        rows[-1]['diagnostic_counts'] = dict(sorted(Counter(
            item.get('option', item['kind']) for item in diagnostics).items()))
        rows[-1]['dataflow_warning_count'] = sum(
            item.get('option') in DATAFLOW_OPTIONS for item in diagnostics)
        rows[-1]['review_candidates'] = [
            {'status': 'unknown', 'option': item['option'], 'message': item['message'],
             'locations': [{'source': Path(location['caret']['file']).relative_to(
                 Path(__file__).resolve().parents[1]).as_posix(),
                 'line': location['caret']['line']}
                 for location in item.get('locations', []) if 'caret' in location]}
            for item in diagnostics if item.get('option') in REVIEW_OPTIONS]
    return {'schema_version': 1, 'complete': False, 'total': len(rows),
            'counts': {'unknown': len(rows)}, 'rows': rows,
            'dsp_sha256': receipt['dsp_sha256'],
            'diagnostic_counts': receipt['diagnostic_counts'],
            'limits': receipt['limits'],
            'compiler_version_observed_at_summary': subprocess.check_output(
                ['/usr/bin/c++', '--version'], text=True).splitlines()[0]}


def isolated_command(command, output):
    args = shlex.split(command)
    # The CMake environment/cache prefix is build infrastructure, not C++ flags.
    compiler = next((i for i, arg in enumerate(args)
                     if Path(arg).name in ('c++', 'g++')), None)
    if compiler is None:
        raise ValueError('Expected an explicit GCC C++ compiler')
    args = args[compiler:]
    result = []
    index = 0
    while index < len(args):
        arg = args[index]
        if arg in ('-o', '-MF', '-MT', '-MQ'):
            if index + 1 == len(args):
                raise ValueError('Missing compiler option operand')
            index += 2
            continue
        if arg in ('-MD', '-MMD', '-MP', '-MG'):
            index += 1
            continue
        if arg.startswith(('-MF', '-MT', '-MQ')):
            index += 1
            continue
        result.append(arg)
        index += 1
    return result + ['-O2', '-Wuninitialized', '-Wmaybe-uninitialized',
                     '-Wreturn-type', '-fdiagnostics-format=json', '-o', str(output)]


def parse_diagnostics(stderr):
    diagnostics = json.loads(stderr)
    if not isinstance(diagnostics, list):
        raise ValueError('Expected GCC diagnostic array')
    result = []
    def visit(item):
        if not isinstance(item, dict) or 'kind' not in item or 'message' not in item:
            raise ValueError('Malformed GCC diagnostic')
        result.append(item)
        for child in item.get('children', []):
            visit(child)
    for item in diagnostics:
        visit(item)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--compdb', type=Path, required=True)
    parser.add_argument('--work-directory', type=Path, required=True)
    parser.add_argument('--summarize-receipt', action='store_true',
                        help='Summarize the existing retained receipt without recompilation')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    work = args.work_directory.resolve()
    work.mkdir(parents=True, exist_ok=True)
    if args.summarize_receipt:
        if args.output is None:
            parser.error('--summarize-receipt requires --output')
        receipt = json.loads((work / 'receipt.json').read_text())
        args.output.write_text(json.dumps(public_summary(receipt), indent=2)+'\n')
        return
    entries = json.loads(args.compdb.read_text())
    dsp = root / 'upstream/CnC_Renegade/Code/Scripts/Scripts.dsp'
    rows = []
    for name in dsp_sources(dsp):
        source = root / 'staging/scripts' / name
        matches = [entry for entry in entries
                   if Path(entry['file']).resolve() == source.resolve()]
        row = {'name': name, 'status': 'unknown', 'compile_command_matches': len(matches),
               'evidence_class': 'optimized_host_compiler_diagnostics',
               'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest()}
        if len(matches) == 1:
            obj = work / (name + '.o')
            obj.unlink(missing_ok=True)
            command = isolated_command(matches[0]['command'], obj)
            result = subprocess.run(command, cwd=matches[0]['directory'],
                                    capture_output=True, text=True)
            (work / (name + '.stderr.json')).write_text(result.stderr)
            (work / (name + '.stdout.txt')).write_text(result.stdout)
            (work / (name + '.command.json')).write_text(json.dumps(command, indent=2)+'\n')
            row['returncode'] = result.returncode
            row['command_sha256'] = hashlib.sha256(json.dumps(command).encode()).hexdigest()
            try:
                row['diagnostics'] = parse_diagnostics(result.stderr)
            except (ValueError, json.JSONDecodeError) as error:
                row['parse_error'] = str(error)
            row['object_sha256'] = hashlib.sha256(obj.read_bytes()).hexdigest() if obj.exists() else None
        rows.append(row)
        print(name, row.get('returncode', 'unselected'),
              len(row.get('diagnostics', [])), flush=True)
    counts = Counter(item.get('option', item['kind']) for row in rows
                     for item in row.get('diagnostics', []))
    receipt = {'schema_version': 1, 'total': len(rows), 'rows': rows,
               'dsp_sha256': hashlib.sha256(dsp.read_bytes()).hexdigest(),
               'diagnostic_counts': dict(sorted(counts.items())),
               'limits': ['Host LP64 diagnostics do not establish Vita behavior.',
                          'Compiler silence does not establish initialization correctness.',
                          'Unselected DSP units require separate ownership evidence.',
                          'Warnings include transitive headers; source locations retain provenance.']}
    (work / 'receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
    if args.output:
        args.output.write_text(json.dumps(public_summary(receipt), indent=2)+'\n')


if __name__ == '__main__':
    main()
