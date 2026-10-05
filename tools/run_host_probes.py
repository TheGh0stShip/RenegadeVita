"""Build host targets and run bounded retail-free probes with retained logs."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import time
import sys
import zlib
import platform

ROOT = Path(__file__).resolve().parents[1]
RETAIL_OUTPUTS = {'a30_definition_runtime', 'a36_m01_mix_probe', 'a36_mix_index',
                  'a30_m00_world_runtime', 'a31_m00_gameplay_seed_runtime',
                  'a35_loading_backdrop_contract'}
THREAD_TARGETS = ('a35_campaign_flight_recorder_selftest', 'a35_script_lookup_selftest',
                  'a35_thread_publication_selftest', 'a35_wwmath_validity_selftest',
                  'a35_level_load_status_selftest')


def run(command, log, timeout, environment):
    begin = time.monotonic()
    try:
        with log.open('wb') as stream:
            process = subprocess.Popen(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT,
                                       env=environment, start_new_session=True)
            try:
                code = process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
                code = 'timeout'
    except subprocess.TimeoutExpired:
        code = 'timeout'
    print(f'{log.name}: {code}', flush=True)
    return {'command': command, 'exit': code, 'seconds': round(time.monotonic() - begin, 3),
            'log': str(log), 'log_sha256': hashlib.sha256(log.read_bytes()).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build-dir', type=Path, required=True)
    parser.add_argument('--sanitizer', choices=('none', 'asan-ubsan', 'tsan'), default='asan-ubsan')
    parser.add_argument('--jobs', type=int, default=8)
    parser.add_argument('--timeout', type=int, default=120)
    parser.add_argument('--skip-build', action='store_true')
    parser.add_argument('--disable-aslr', action='store_true',
                        help='use Linux setarch -R for each probe; retain the wrapper in evidence')
    args = parser.parse_args()
    directory = args.build_dir.resolve()
    directory.mkdir(parents=True, exist_ok=True)
    logs = directory / 'probe-logs'
    logs.mkdir(exist_ok=True)
    environment = os.environ.copy()
    environment['ASAN_OPTIONS'] = 'detect_leaks=1:halt_on_error=1'
    environment['UBSAN_OPTIONS'] = 'halt_on_error=1:print_stacktrace=1'
    environment['TSAN_OPTIONS'] = 'halt_on_error=1'
    environment['TTFS_SANITIZE'] = '1' if args.sanitizer == 'asan-ubsan' else '0'
    environment['TTFS_ENGINE_PROBE'] = str(directory / 'a31_m00_interactive_runtime')
    flags = {'none': '', 'asan-ubsan': '-fsanitize=address,undefined -fno-omit-frame-pointer',
             'tsan': '-fsanitize=thread -fno-omit-frame-pointer'}[args.sanitizer]
    summary = {'sanitizer': args.sanitizer, 'evidence_class': 'host', 'build': [], 'probes': [],
               'retail_targets_compile_only': sorted(RETAIL_OUTPUTS)}
    output = directory / 'host-probe-summary.json'
    def save_summary():
        temporary = output.with_suffix('.json.tmp')
        temporary.write_text(json.dumps(summary, indent=2) + '\n')
        temporary.replace(output)
    if args.skip_build:
        cache = (directory / 'CMakeCache.txt').read_text()
        actual = re.search(r'^CMAKE_CXX_FLAGS:STRING=(.*)$', cache, re.M)
        if actual is None or actual.group(1).strip() != flags:
            parser.error('--skip-build requires matching cached sanitizer flags')
    if not args.skip_build:
        config = ['cmake', '-S', str(ROOT / 'tools/host_a30_definitions'), '-B', str(directory),
                  '-G', 'Ninja', '-DRENEGADE_HOST_ORIGINAL_AUDIO=ON', '-DCMAKE_BUILD_TYPE=RelWithDebInfo',
                  '-DCMAKE_CXX_FLAGS=' + flags, '-DCMAKE_C_FLAGS=' + flags,
                  '-DCMAKE_EXE_LINKER_FLAGS=' + flags]
        summary['build'].append(run(config, logs / 'configure.log', 120, environment))
        if summary['build'][-1]['exit'] == 0:
            build = ['cmake', '--build', str(directory), '--parallel', str(args.jobs)]
            if args.sanitizer == 'tsan': build.extend(['--target', *THREAD_TARGETS])
            summary['build'].append(run(build, logs / 'build.log', 3600, environment))
        if any(row['exit'] != 0 for row in summary['build']):
            save_summary()
            return 1
    targets = subprocess.check_output(['ninja', '-C', str(directory), '-t', 'targets', 'all'], text=True)
    binaries = re.findall(r'^([^ :]+): CXX_EXECUTABLE_LINKER', targets, re.M)
    cases = []
    for binary in binaries:
        if binary in RETAIL_OUTPUTS or binary == 'a31_m00_interactive_runtime': continue
        if args.sanitizer == 'tsan' and binary not in THREAD_TARGETS: continue
        cases.append([str(directory / binary)])
    if args.sanitizer != 'tsan':
        source = (ROOT / 'tools/host_a30_definitions/a31_interactive_main.cpp').read_text()
        switches = re.findall(r'argc == 2 && strcmp\(argv\[1\], "([^"]+-selftest)"\) == 0', source)
        cases.extend([str(directory / 'a31_m00_interactive_runtime'), switch] for switch in switches)
        cases.extend([str(directory / 'a31_m00_interactive_runtime'), '--sorting-selftest', case]
                     for case in ('basic', 'nodes', 'vertices', 'indices', 'zero', 'index-limit', 'vertex-limit', 'interleaved', 'strip', 'statistics', 'lights', 'merge'))
        # Exact asset-free package oracle retained by the TTFS contracts.
        sys.path.insert(0, str(ROOT))
        from tools.make_ttfs_fixture import FIXTURE_FILES
        from tools.test_ttfs import ORACLE
        fixture = directory / 'ttfs-probe-fixture'
        fixture.mkdir(exist_ok=True)
        (fixture / 'manifest.tpi').write_bytes(ORACLE)
        for name, content in FIXTURE_FILES.items():
            (fixture / f'{zlib.crc32(content):08X}.{name}').write_bytes(content)
        cases.append([str(directory / 'a31_m00_interactive_runtime'), '--ttfs-cache-selftest', str(fixture)])
        cases.append([sys.executable, '-m', 'unittest', 'tools.test_ttfs'])
    summary['denominator'] = len(cases)
    summary['binary_inventory'] = [
        {'name': name, 'sha256': hashlib.sha256((directory / name).read_bytes()).hexdigest()}
        for name in binaries if (directory / name).is_file()
    ]
    summary['cmake_cache_sha256'] = hashlib.sha256((directory / 'CMakeCache.txt').read_bytes()).hexdigest()
    summary['disable_aslr'] = args.disable_aslr
    if args.disable_aslr:
        if platform.system() != 'Linux':
            parser.error('--disable-aslr requires Linux setarch')
        cases = [['setarch', platform.machine(), '-R', *command] for command in cases]
    for index, command in enumerate(cases):
        summary['probes'].append(run(command, logs / f'probe-{index:03d}.log', args.timeout, environment))
        save_summary()
    return int(any(row['exit'] != 0 for row in summary['probes']))


if __name__ == '__main__':
    raise SystemExit(main())
