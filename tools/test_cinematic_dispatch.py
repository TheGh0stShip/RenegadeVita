"""Execute all original cinematic dispatch branches against bounded callback seams."""
from contextlib import nullcontext
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]


class CinematicDispatchTests(unittest.TestCase):
    def test_original_dispatch(self):
        retained=os.environ.get('RENEGADE_CINEMATIC_DISPATCH_DIRECTORY')
        if retained:Path(retained).mkdir(parents=True,exist_ok=True)
        context=nullcontext(retained) if retained else tempfile.TemporaryDirectory()
        with context as directory:
            path=Path(directory);executable=path/'dispatch'
            command=['c++','-std=c++17','-O1','-g','-fpermissive',
                '-fsanitize=address,undefined','-fno-sanitize-recover=all',
                '-include',str(ROOT/'port/compatibility/include/msvc_compat.h'),
                '-include',str(ROOT/'port/compatibility/include/renegade_script_call_defaults.h')]
            for name in ('staging/scripts','staging/wwmath','staging/wwlib','port/compatibility/include'):
                command+=['-I',str(ROOT/name)]
            command+=[str(ROOT/'tools/host_cinematic_dispatch_test.cpp')]
            for name in ('scripts.cpp','ScriptFactory.cpp','ScriptRegistrar.cpp','strtrim.cpp'):
                command+=[str(ROOT/'staging/scripts'/name)]
            command+=['-o',str(executable)]
            compiled=subprocess.run(command,capture_output=True,text=True)
            if retained:(path/'compile.log').write_text(compiled.stdout+compiled.stderr)
            self.assertEqual(compiled.returncode,0,compiled.stderr)
            result=subprocess.run([str(executable)],capture_output=True,text=True)
            if retained:(path/'runtime.log').write_text(result.stdout+result.stderr)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertIn('PASS branches=18 camera_release=1 title_prefix=1 unknown=1',result.stdout)
            if retained:
                digest=lambda file:hashlib.sha256(file.read_bytes()).hexdigest()
                receipt={'schema_version':1,'evidence_class':'host_original_cinematic_dispatch_asan_ubsan',
                    'branches_passed':18,'camera_release_passed':True,'title_prefix_passed':True,
                    'unknown_title_no_callback_passed':True,'binary_sha256':digest(executable),
                    'source_sha256':{name:digest(ROOT/name) for name in
                        ('tools/host_cinematic_dispatch_test.cpp','tools/test_cinematic_dispatch.py',
                         'tools/host_cinematic_save_test.cpp','staging/scripts/Test_Cinematic.cpp')},
                    'limits':['Bounded synthetic callbacks and opaque object identity; no real engine effects.',
                              'One success route per title; alternative, failure and lifetime paths remain open.',
                              'Native-only telemetry/platform branches and ARM/physical dispatch remain untested.']}
                (path/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
