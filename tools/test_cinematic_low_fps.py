"""Original Test_Cinematic scheduling at Vita frame rates (host, ASan/UBSan).

Compiles tools/host_cinematic_low_fps_test.cpp against the staged script and
runs synthetic schedules; when the unchanged retail Data directory is present
it also streams every .txt member of the campaign archives through the same
profiles (15/20/30 fps, 200 ms clamp, 200-600 ms spikes, pause and suspend).
Retail bytes are only piped to the local binary; nothing is copied or kept.
"""
from contextlib import nullcontext
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get('RENEGADE_RETAIL_DATA',
    '/mnt/c/Users/steve/AppData/Roaming/Vita3K/Vita3K/ux0/data/renegade/retail/Data'))
ARCHIVES = ['M01.mix', 'M02.mix', 'M03.mix', 'M04.mix', 'M05.mix', 'M06.mix', 'M07.mix', 'M08.mix',
            'M09.mix', 'M10.mix', 'M11.mix', 'M13.mix', 'always.dat', 'Always2.dat']
KEY_MEMBERS = ['M13.mix:x0z_finale.txt', 'M08.mix:x8a_midtro.txt', 'M11.mix:x11n_midtro.txt',
               'M06.mix:x6b_midtro.txt', 'M06.mix:x6c_midtro.txt', 'M13.mix:x00_intro.txt']


def compile_harness(directory):
    executable = Path(directory) / 'cinematic-low-fps'
    command = ['c++', '-std=c++17', '-O1', '-g', '-fpermissive',
               '-fsanitize=address,undefined', '-fno-sanitize-recover=all',
               '-include', str(ROOT / 'port/compatibility/include/msvc_compat.h'),
               '-include', str(ROOT / 'port/compatibility/include/renegade_script_call_defaults.h')]
    for name in ('staging/scripts', 'staging/wwmath', 'staging/wwlib', 'port/compatibility/include'):
        command += ['-I', str(ROOT / name)]
    command.append(str(ROOT / 'tools/host_cinematic_low_fps_test.cpp'))
    for name in ('scripts.cpp', 'ScriptFactory.cpp', 'ScriptRegistrar.cpp', 'strtrim.cpp'):
        command.append(str(ROOT / 'staging/scripts' / name))
    command += ['-o', str(executable)]
    compiled = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    return executable, compiled


def retail_streams(parts=8):
    from tools.renegade_cinematic_dependency_scan import MixArchive
    streams = [bytearray() for _ in range(parts)]
    members = 0
    for archive_name in ARCHIVES:
        archive = MixArchive(DATA / archive_name)
        for member in sorted(archive.entries):
            if not member.endswith('.txt'):
                continue
            name = f'{archive_name}:{member}'.encode()
            payload = archive.read_binary(member)
            streams[members % parts] += (struct.pack('<I', len(name)) + name +
                                         struct.pack('<I', len(payload)) + payload)
            members += 1
    return [bytes(stream) for stream in streams], members


class CinematicLowFpsTests(unittest.TestCase):
    def test_low_fps_scheduling(self):
        retained = os.environ.get('RENEGADE_CINEMATIC_LOW_FPS_DIRECTORY')
        if retained:
            Path(retained).mkdir(parents=True, exist_ok=True)
        context = nullcontext(retained) if retained else tempfile.TemporaryDirectory(prefix='renegade-cinematic-low-fps-')
        with context as directory:
            executable, compiled = compile_harness(directory)
            self.assertEqual(compiled.returncode, 0, compiled.stdout + compiled.stderr)
            result = subprocess.run([str(executable)], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            for marker in ('PASS synthetic_dense_every_frame', 'PASS synthetic_final_batch',
                           'PASS synthetic_time_zero_only', 'PASS synthetic re-entrant primary kill',
                           'Original cinematic low-fps scheduling PASS'):
                self.assertIn(marker, result.stdout)
            if not all((DATA / name).exists() for name in ARCHIVES):
                self.skipTest(f'retail Data not present at {DATA}')
            streams, members = retail_streams()
            run = lambda stream: subprocess.run([str(executable), '--retail'], cwd=ROOT, input=stream,
                                                capture_output=True)
            with ThreadPoolExecutor(max_workers=len(streams)) as pool:
                results = list(pool.map(run, streams))
            text = ''.join(r.stdout.decode('latin1') + r.stderr.decode('latin1') for r in results)
            if retained:
                (Path(directory) / 'retail.log').write_text(text)
            for r in results:
                self.assertEqual(r.returncode, 0, text[-4000:])
            passed = sum(int(line.split()[3].split('/')[0]) for line in text.splitlines()
                         if line.startswith('Retail low-fps scheduling:'))
            self.assertEqual(passed, members, text[-4000:])
            for member in KEY_MEMBERS:
                self.assertIn(f'PASS {member} ', text)


if __name__ == '__main__':
    unittest.main()
