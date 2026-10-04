"""Run the actual Mission03 sender/receiver scripts under host sanitizers."""
from contextlib import nullcontext
from pathlib import Path
import hashlib
import json
import os
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]


class Mission03PointerTests(unittest.TestCase):
    def test_original_script_exchange_and_scoped_tokens(self):
        retained=os.environ.get('RENEGADE_M03_POINTER_PROBE_DIRECTORY')
        if retained:Path(retained).mkdir(parents=True,exist_ok=True)
        with (nullcontext(retained) if retained else tempfile.TemporaryDirectory()) as directory:
            path=Path(directory)
            command=['c++','-std=c++17','-O1','-g','-fpermissive','-DRENEGADE_HOST_ABI_TEST',
                     '-fsanitize=address,undefined','-fno-sanitize-recover=all','-pthread',
                     '-include',str(ROOT/'port/compatibility/include/msvc_compat.h'),
                     '-include',str(ROOT/'port/compatibility/include/renegade_script_call_defaults.h'),
                     '-include',str(ROOT/'port/compatibility/include/renegade_campaign_script_defaults.h')]
            for name in ('staging/scripts','staging/wwmath','staging/wwlib','port/compatibility/include','port/platform'):
                command+=['-I',str(ROOT/name)]
            command+=[str(ROOT/'tools/host_m03_pointer_exchange_test.cpp')]
            for name in ('scripts.cpp','ScriptFactory.cpp','ScriptRegistrar.cpp','strtrim.cpp'):
                command+=[str(ROOT/'staging/scripts'/name)]
            command+=[str(ROOT/'port/platform/renegade_ui_pointer_tokens.cpp'),'-o',str(path/'exchange')]
            compiled=subprocess.run(command,capture_output=True,text=True)
            if retained:(path/'compile.log').write_text(compiled.stdout+compiled.stderr)
            self.assertEqual(compiled.returncode,0,compiled.stderr)
            result=subprocess.run([str(path/'exchange')],capture_output=True,text=True)
            if retained:(path/'runtime.log').write_text(result.stdout+result.stderr)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertIn('PASS escort_states=3 area_queries=2 real_senders=3 scoped_release nested_tokens',result.stdout)
            if retained:
                digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
                receipt={'schema_version':1,'evidence_class':'host_original_m03_pointer_exchange_asan_ubsan',
                         'escort_states_passed':3,'area_queries_passed':2,'actual_sender_exchanges_passed':3,
                         'scoped_release_passed':True,'nested_tokens_passed':True,'exact_callback_types':True,
                         'binary_sha256':digest(path/'exchange'),
                         'source_sha256':{name:digest(ROOT/name) for name in
                           ('tools/test_m03_pointer_exchange.py','tools/host_m03_pointer_exchange_test.cpp',
                            'tools/host_cinematic_save_test.cpp','staging/scripts/Mission03.cpp',
                            'port/compatibility/include/renegade_script_pointer_exchange.h',
                            'port/platform/renegade_ui_pointer_tokens.cpp')},
                         'limits':['Actual script registration/classes and selected callbacks; synthetic command transport and opaque objects.',
                                   'No complete M03 gameplay, observer lifetime, delayed pointer events or native execution.']}
                (path/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')


if __name__=='__main__':
    unittest.main()
