"""Run original text-file commands with real host pointer tokens and a file seam."""
from contextlib import nullcontext
from pathlib import Path
import hashlib
import json
import os
import subprocess
import tempfile
import unittest
from tools.audit_script_command_bodies import inspect
from tools.audit_missing_definition_callers import body

ROOT = Path(__file__).resolve().parents[1]


class TextFileBoundaryTests(unittest.TestCase):
    def test_original_line_and_handle_contract(self):
        owner = ROOT/'staging/combat/scriptcommands.cpp'
        source = owner.read_text(encoding='latin1')
        signatures = [('Text_File_Open','int Text_File_Open(const char *filename)'),
                      ('Text_File_Get_String','bool Text_File_Get_String(int handle,char *buffer,int size)'),
                      ('Text_File_Close','void Text_File_Close(int handle)')]
        prefix = r'''
#include <cassert>
#include <cstring>
#include <string>
#include "renegade_ui_pointer_tokens.h"
struct FileClass {
 std::string content; size_t cursor=0; bool available=true; unsigned closes=0;
 void Open() { cursor=0; }
 bool Is_Available() { return available; }
 int Read(void *destination,int count) {
  assert(count==1); if(cursor==content.size()) return 0;
  *static_cast<char*>(destination)=content[cursor++]; return 1;
 }
 void Close() { ++closes; }
};
struct Factory {
 FileClass file; bool null_file=false; unsigned returned=0;
 FileClass *Get_File(const char *) { return null_file ? nullptr : &file; }
 void Return_File(FileClass *value) { assert(value==&file); ++returned; }
} factory;
Factory *_TheFileFactory=&factory;
enum { A35_LOOKUP_TEXT_FILE=1 };
void A35_Script_Lookup_Record(int,const char *,int,bool) {}
'''
        suffix = r'''
int main() {
 static_assert(sizeof(int)==4 && sizeof(uint32_t)==4,"handle ABI");
 char out[8];
 factory.null_file=true; assert(Text_File_Open("missing")==0);
 factory.null_file=false; factory.file.available=false;
 assert(Text_File_Open("unavailable")==0 && factory.returned==1);
 factory.file.available=true; factory.file.content="a\r\nb\nlast";
 int handle=Text_File_Open("fixture"); assert(handle!=0);
 assert(Text_File_Get_String(handle,out,7) && std::strcmp(out,"a\r\n")==0);
 assert(Text_File_Get_String(handle,out,7) && std::strcmp(out,"b\n")==0);
 assert(Text_File_Get_String(handle,out,7) && std::strcmp(out,"last")==0);
 assert(!Text_File_Get_String(handle,out,7) && out[0]==0);
 Text_File_Close(handle); Text_File_Close(handle);
 assert(factory.file.closes==1 && factory.returned==2);
 assert(!Text_File_Get_String(handle,out,7));
 factory.file.content="abcdefghijk\nnext\n"; handle=Text_File_Open("long");
 assert(Text_File_Get_String(handle,out,3) && std::strcmp(out,"abc")==0);
 assert(Text_File_Get_String(handle,out,7) && std::strcmp(out,"next\n")==0);
 Text_File_Close(handle);
 factory.file.content="discard\nkeep\n"; handle=Text_File_Open("zero");
 assert(!Text_File_Get_String(handle,out,0) && out[0]==0);
 assert(Text_File_Get_String(handle,out,7) && std::strcmp(out,"keep\n")==0);
 Text_File_Close(handle);
 assert(!Text_File_Get_String(0,out,7)); Text_File_Close(0);
 puts("Original text-file command contract PASS");
}
'''
        retained = os.environ.get('RENEGADE_TEXT_FILE_PROBE_DIRECTORY')
        if retained:
            Path(retained).mkdir(parents=True,exist_ok=True)
        context = nullcontext(retained) if retained else tempfile.TemporaryDirectory()
        with context as directory:
            path = Path(directory)
            code = prefix+'\n'.join(signature+body(source,name)[0] for name,signature in signatures)+suffix
            (path/'text.cpp').write_text(code)
            command = ['c++','-std=c++17','-O1','-g','-fsanitize=address,undefined',
                       '-fno-sanitize-recover=all','-DRENEGADE_HOST_ABI_TEST',
                       '-I'+str(ROOT/'port/platform'),'-I'+str(ROOT/'port/compatibility/include'),
                       str(path/'text.cpp'),str(ROOT/'port/platform/renegade_ui_pointer_tokens.cpp'),
                       '-pthread','-o',str(path/'text')]
            compile_result = subprocess.run(command,capture_output=True,text=True)
            if retained: (path/'compile.log').write_text(compile_result.stdout+compile_result.stderr)
            self.assertEqual(compile_result.returncode,0,compile_result.stderr)
            run = subprocess.run([str(path/'text')],capture_output=True,text=True)
            if retained: (path/'runtime.log').write_text(run.stdout+run.stderr)
            self.assertEqual(run.returncode,0,run.stdout+run.stderr)
            if retained:
                digest=lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
                receipt={'schema_version':1,'evidence_class':'host_original_text_file_commands_asan_ubsan',
                         'binary_sha256':digest(path/'text'),'owner_sha256':digest(owner),
                         'probe_sha256':digest(Path(__file__)),'token_owner_sha256':digest(ROOT/'port/platform/renegade_ui_pointer_tokens.cpp'),
                         'commands':{name:inspect(source,name)['body_sha256'] for name,_ in signatures},
                         'passed':True,'limits':['Synthetic file seam; no retail archive or physical I/O.',
                           'size is original maximum characters; caller must allocate size+1 bytes.',
                           'Zero capacity consumes a line and returns false; invalid native pointer handles remain untested.',
                           'Host LP64 token map evidence does not prove Vita ILP32 behavior.']}
                (path/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
