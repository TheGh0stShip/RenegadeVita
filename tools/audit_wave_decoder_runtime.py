"""Run the host-only C++ WAV decoder over all archive entries; emit metadata only."""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import select
import struct
import subprocess
from tools.renegade_cinematic_dependency_scan import MixArchive


def exchange(process, data):
    if len(data) > 64 * 1024 * 1024:
        raise ValueError('probe source ceiling exceeded')
    process.stdin.write(struct.pack('<I', len(data)) + data)
    process.stdin.flush()
    if not select.select([process.stdout], [], [], 60)[0]:
        raise TimeoutError('decoder probe response timeout')
    line = process.stdout.readline().decode('ascii').rstrip('\n')
    fields = line.split('\t', 2)
    if len(fields) != 3 or fields[0] not in ('0', '1'):
        raise ValueError('invalid decoder probe response')
    return {'decoded': fields[0] == '1', 'frames': int(fields[1]), 'error': fields[2]}


def run(directory, executable, stderr_path):
    rows, archives = [], []
    environment = dict(os.environ, ASAN_OPTIONS='detect_leaks=1:halt_on_error=1',
                       UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
    with stderr_path.open('wb') as log:
        process = subprocess.Popen([str(executable.resolve())], stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=log, env=environment)
        try:
            for path in sorted(directory.iterdir()):
                if not path.is_file() or path.suffix.lower() not in ('.mix', '.dat', '.dbs'):
                    continue
                archive = MixArchive(path)
                total = decoded = frames = 0
                failures = []
                with path.open('rb') as stream:
                    archives.append({'archive': path.name, 'sha256': hashlib.file_digest(stream, 'sha256').hexdigest()})
                    for index, (name, _, offset, size) in enumerate(archive.entry_records):
                        if not name.lower().endswith('.wav'):
                            continue
                        stream.seek(offset)
                        data = stream.read(size)
                        if len(data) != size:
                            raise ValueError('truncated WAV member')
                        result = exchange(process, data)
                        total += 1
                        decoded += result['decoded']
                        frames += result['frames']
                        if not result['decoded']:
                            failures.append({'member': name, 'index_record': index, 'offset': offset,
                                             'sha256': hashlib.sha256(data).hexdigest(), 'error': result['error']})
                rows.append({'archive': path.name, 'status': 'unknown', 'evidence_class': 'host_cpp_decode',
                             'wave_members': total, 'decoded_members': decoded, 'decoded_frames': frames,
                             'rejected_members': len(failures), 'failures': failures})
            process.stdin.close()
            if process.wait(timeout=60) != 0:
                raise RuntimeError('decoder probe failed; inspect private sanitizer log')
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
            process.stdout.close()
            if not process.stdin.closed:
                process.stdin.close()
    if stderr_path.stat().st_size:
        raise RuntimeError('decoder stderr is nonempty; inspect private log')
    return rows, archives


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--probe', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--stderr', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    if not args.stderr.resolve().is_relative_to(root / 'build'):
        parser.error('probe stderr must remain under private build/')
    rows, archives = run(args.data, args.probe, args.stderr)
    inventory_path = root / 'reports/generated/sweeps/wave_headers.json'
    inventory_bytes = inventory_path.read_bytes()
    inventory = json.loads(inventory_bytes)
    if inventory['archives'] != archives or inventory['totals']['wave_members'] != sum(r['wave_members'] for r in rows):
        raise ValueError('decoder inputs differ from WAV inventory')
    sources = ('tools/audit_wave_decoder_runtime.py', 'tools/host_wave_archive_probe.cpp',
               'tools/renegade_cinematic_dependency_scan.py',
               'port/audio/vita/renegade_wave_decoder.cpp', 'port/audio/vita/renegade_wave_decoder.h')
    result = {'schema': 1, 'complete': False, 'rows': rows, 'total': len(rows),
              'counts': dict(Counter(row['status'] for row in rows)), 'archives': archives,
              'totals': {k: sum(row[k] for row in rows) for k in ('wave_members','decoded_members','rejected_members')},
              'probe_sha256': hashlib.sha256(args.probe.read_bytes()).hexdigest(),
              'wave_inventory_sha256': hashlib.sha256(inventory_bytes).hexdigest(),
              'sanitizer_stderr_bytes': args.stderr.stat().st_size,
              'parser_inputs': [{'source': s, 'sha256': hashlib.sha256((root/s).read_bytes()).hexdigest()} for s in sources],
              'limits': ['Host decoder invocation only; no mixer, audio device, duration API or Vita acceptance.',
                         'No PCM or retail payload exported; rejected metadata is retained.',
                         'Probe hash identifies the executable; compiler/sanitizer flags require a matching build receipt.']}
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result['totals']))


if __name__ == '__main__':
    main()
