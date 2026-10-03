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
CHECKS = [('staging/ww3d2/textureloader.cpp', 'staging/ww3d2/texture.cpp')]


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
    args = parser.parse_args()
    build = args.build_dir.resolve()
    report = args.report.resolve()
    output_dir = report.parent / (report.stem + '-objects')
    output_dir.mkdir(parents=True, exist_ok=True)
    commands = subprocess.check_output(
        ['ninja', '-C', str(build), '-t', 'commands', args.target], text=True)
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
                     'runtime_status': 'excluded from current runtime graph; integration remains open'})
    report.write_text(json.dumps({'evidence_class': 'object compilation only',
                                 'denominator': len(rows), 'rows': rows}, indent=2) + '\n')
    return int(any(row['exit'] != 0 for row in rows))


if __name__ == '__main__':
    raise SystemExit(main())
