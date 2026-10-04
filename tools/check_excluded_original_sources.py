"""Compile changed original sources omitted from the current runtime graph.

Object compilation does not establish runtime integration or behavior.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import subprocess

ROOT = Path(__file__).resolve().parents[1]
CHECKS = [('staging/ww3d2/textureloader.cpp', 'staging/ww3d2/texture.cpp'),
          ('staging/ww3d2/dx8renderer.cpp', 'staging/ww3d2/texture.cpp'),
          ('staging/ww3d2/dx8polygonrenderer.cpp', 'staging/ww3d2/texture.cpp'),
          ('staging/ww3d2/statistics.cpp', 'staging/ww3d2/texture.cpp')]


def symbol_inventory(output):
    """Retain raw linker identities; aliases and weak definitions stay distinct."""
    symbols = {}
    for line in output.splitlines():
        fields = line.split()
        if len(fields) >= 2 and len(fields[-2]) == 1:
            symbols[fields[-1]] = fields[-2]
    return symbols


def compare_symbols(undefined, defined, linked):
    absent = sorted(set(undefined) - set(linked))
    overlap = sorted(name for name, kind in defined.items()
                     if kind in 'TDBR' and linked.get(name, '') and linked[name] in 'TDBR')
    return {'undefined_symbols': len(undefined),
            'absent_symbol_candidates': absent,
            'strong_definition_overlap_candidates': overlap,
            'scope': 'Symbol presence only; not selected-unit, behavior or runtime proof.'}


def selected_compile_objects(commands, build):
    objects = {}
    for line in commands.splitlines():
        args = shlex.split(line)
        if '-c' in args and '-o' in args:
            output = Path(args[args.index('-o') + 1])
            source = Path(args[args.index('-c') + 1])
            objects[(build / output).resolve()] = (build / source).resolve()
    return objects


def target_object_definitions(nm, objects):
    """Only inspect objects selected by current target commands, never a glob."""
    result = {}
    output = subprocess.check_output(
        [nm, '-A', '--extern-only', '--defined-only', *map(str, objects)], text=True)
    for line in output.splitlines():
        fields = line.rsplit(None, 2)
        if len(fields) != 3 or ':' not in fields[0]:
            continue
        path = Path(fields[0].rsplit(':', 1)[0])
        if path not in objects:
            continue
        result.setdefault(fields[-1], []).append(
            {'object': str(path), 'source': str(objects[path]), 'kind': fields[-2]})
    return result


def link_closure(nm, obj, elf, object_definitions=None):
    def read(path, option):
        return symbol_inventory(subprocess.check_output(
            [nm, '--extern-only', option, str(path)], text=True))
    result = compare_symbols(read(obj, '--undefined-only'),
                             read(obj, '--defined-only'), read(elf, '--defined-only'))
    if object_definitions is not None:
        result['definitions_in_selected_objects'] = {
            symbol: object_definitions[symbol] for symbol in result['absent_symbol_candidates']
            if symbol in object_definitions}
        result['scope'] += ' Selected object definitions distinguish ELF omission from missing providers.'
    return result


def compile_command(commands, build_dir, template, source, output):
    matches = []
    for line in commands.splitlines():
        args = shlex.split(line)
        if '-c' not in args or '-o' not in args:
            continue
        original = Path(args[args.index('-c') + 1])
        if not original.is_absolute():
            original = build_dir / original
        if original.resolve() == template.resolve():
            matches.append(args)
    if len(matches) != 1:
        raise ValueError(f'expected one template compile command, found {len(matches)}')
    args = matches[0]
    args[args.index('-c') + 1] = str(source)
    args[args.index('-o') + 1] = str(output)
    for flag, value in [('-MT', str(output)), ('-MF', str(output) + '.d')]:
        if flag in args:
            args[args.index(flag) + 1] = value
    return args


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build-dir', type=Path, required=True)
    parser.add_argument('--target', required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--link-elf', type=Path,
                        help='Compare each compiled object with this matching target ELF')
    parser.add_argument('--nm', default='nm', help='Target-compatible nm executable')
    args = parser.parse_args()
    build = args.build_dir.resolve()
    report = args.report.resolve()
    output_dir = report.parent / (report.stem + '-objects')
    output_dir.mkdir(parents=True, exist_ok=True)
    commands = subprocess.check_output(
        ['ninja', '-C', str(build), '-t', 'commands', args.target], text=True)
    selected_objects = selected_compile_objects(commands, build)
    selected_sources = set(selected_objects.values())
    object_definitions = target_object_definitions(args.nm, selected_objects) \
        if args.link_elf is not None else None
    rows = []
    for relative, template in CHECKS:
        source = ROOT / relative
        output = output_dir / (source.stem + '.o')
        command = compile_command(commands, build, ROOT / template, source, output)
        log = output.with_suffix('.log')
        with log.open('wb') as stream:
            result = subprocess.run(command, cwd=build, stdout=stream,
                                    stderr=subprocess.STDOUT, timeout=120)
        rows.append({'source': relative, 'command': command,
                     'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
                     'exit': result.returncode, 'object': str(output),
                     'object_sha256': hashlib.sha256(output.read_bytes()).hexdigest()
                         if result.returncode == 0 else None,
                     'log': str(log),
                     'log_sha256': hashlib.sha256(log.read_bytes()).hexdigest(),
                     'selected_by_current_target': source.resolve() in selected_sources,
                     'runtime_status': ('selected by current target; behavior remains unverified'
                         if source.resolve() in selected_sources else
                         'excluded from current runtime graph; integration remains open')})
        if result.returncode == 0 and args.link_elf is not None:
            rows[-1]['link_closure'] = link_closure(args.nm, output, args.link_elf, object_definitions)
    report.write_text(json.dumps({'evidence_class': 'object compilation only',
                                 'link_elf_sha256': hashlib.sha256(args.link_elf.read_bytes()).hexdigest()
                                     if args.link_elf is not None else None,
                                 'selected_object_denominator': len(selected_objects),
                                 'target_commands_sha256': hashlib.sha256(commands.encode()).hexdigest(),
                                 'denominator': len(rows), 'rows': rows}, indent=2) + '\n')
    return int(any(row['exit'] != 0 for row in rows))


if __name__ == '__main__':
    raise SystemExit(main())
