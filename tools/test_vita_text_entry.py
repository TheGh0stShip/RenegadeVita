import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

SOURCE = r'''
#include "renegade_text_entry_session.h"
#include <assert.h>
#include <stdio.h>
using namespace RenegadeTextEntry;
struct Keyboard {
    static inline uint16_t *initial, *output;
    static inline size_t limit;
    static inline Status status = Status::Absent;
    static inline bool open_ok = true, accept = true, close_ok = true;
    static inline int opens = 0, closes = 0, results = 0, aborts = 0;
    static bool Open(uint16_t *i, uint16_t *o, size_t n) {
        ++opens; initial=i; output=o; limit=n;
        if (open_ok) status=Status::Running;
        return open_ok;
    }
    static Status Get_Status() { return status; }
    static bool Accepted() { ++results; return accept; }
    static bool Close() { ++closes; if (close_ok) status=Status::Absent; return close_ok; }
    static void Abort() { ++aborts; status=Status::Finished; }
};
int main() {
    Session<Keyboard> s;
    int owner=0, other=0;
    wchar_t out[MaxLength+1] = {L'X',0};
    assert(!s.Begin(nullptr,L"save",20));
    assert(!s.Begin(&owner,nullptr,20));
    assert(!s.Begin(&owner,L"save",0));
    assert(!s.Begin(&owner,L"save",-1));
    Keyboard::open_ok=false;
    assert(!s.Begin(&owner,L"save",20) && !s.Block_Input(false));
    Keyboard::open_ok=true;
    assert(s.Begin(&owner,L"Manual save",20));
    assert(s.Active() && s.Block_Input(true));
    assert(!s.Begin(&other,L"replace",20));
    assert(!s.Take_Result(&owner,out,MaxLength+1));
    Keyboard::output[0]='N'; Keyboard::output[1]=0;
    Keyboard::status=Status::Finished;
    Keyboard::close_ok=false;
    assert(s.Active() && !s.Take_Result(&owner,out,MaxLength+1));
    assert(out[0]=='X');
    int results=Keyboard::results;
    Keyboard::close_ok=true;
    assert(!s.Active() && Keyboard::results==results);
    assert(!s.Take_Result(&other,out,MaxLength+1));
    assert(s.Take_Result(&owner,out,MaxLength+1) && out[0]=='N' && out[1]==0);
    assert(!s.Take_Result(&owner,out,MaxLength+1));
    assert(s.Block_Input(false) && s.Block_Input(false));
    assert(s.Block_Input(true) && !s.Block_Input(false));
    // Cancel and owner destruction never deliver a result to another control.
    assert(s.Begin(&owner,L"old",20));
    s.Cancel(&other); assert(s.Active());
    s.Cancel(&owner); assert(!s.Active() && Keyboard::aborts==1);
    assert(!s.Take_Result(&owner,out,MaxLength+1) && out[0]=='N');
    assert(s.Block_Input(true) && !s.Block_Input(true));
    assert(s.Begin(&owner,L"cancel",20));
    Keyboard::accept=false; Keyboard::status=Status::Finished;
    assert(!s.Take_Result(&owner,out,MaxLength+1) && out[0]=='N');
    assert(s.Block_Input(true));
    Keyboard::accept=true;
    // Strictly bounded output, including missing terminator and surrogates.
    const uint16_t cases[][5]={{'A','B','C','D','E'},{0xD800,0,0,0,0},
        {0xDC00,0,0,0,0},{0xD800,'A',0,0,0},{'A','B','C',0xD800,0}};
    for (auto &bad:cases) {
        assert(s.Begin(&owner,L"old",4));
        for (int i=0;i<5;++i) Keyboard::output[i]=bad[i];
        Keyboard::status=Status::Finished;
        assert(!s.Take_Result(&owner,out,MaxLength+1) && out[0]=='N');
        assert(s.Block_Input(true));
    }
    assert(s.Begin(&owner,L"\U0001F600xyz",3));
    assert(Keyboard::initial[0]==0xD83D && Keyboard::initial[1]==0xDE00);
    assert(Keyboard::initial[2]=='x' && Keyboard::initial[3]==0);
    Keyboard::output[0]=0xD83D; Keyboard::output[1]=0xDE00; Keyboard::output[2]=0;
    Keyboard::status=Status::Finished;
    assert(s.Take_Result(&owner,out,MaxLength+1));
    assert(static_cast<unsigned>(out[0])==(sizeof(wchar_t)==2 ? 0xD83D : 0x1F600));
    assert(s.Block_Input(true));
    assert(s.Begin(&owner,L"\U0001F600",1) && Keyboard::initial[0]==0);
    s.Cancel_All(); assert(s.Block_Input(true));
    assert(s.Begin(&owner,L"empty",99999) && Keyboard::limit==MaxLength);
    Keyboard::status=Status::Finished;
    assert(s.Take_Result(&owner,out,MaxLength+1) && out[0]==0);
    assert(s.Block_Input(true));
    assert(s.Begin(&owner,L"lost",8));
    Keyboard::status=Status::Absent;
    assert(!s.Take_Result(&owner,out,MaxLength+1));
    assert(s.Block_Input(true) && !s.Block_Input(false));
    puts("Text entry ownership, cancellation, bounds, UTF16 and release checks PASS");
}
'''

class VitaTextEntryTests(unittest.TestCase):
    def run_contract(self, short_wchar):
        with tempfile.TemporaryDirectory(prefix='renegade-text-entry-') as tmp:
            source=Path(tmp)/'test.cpp'; binary=Path(tmp)/'test'
            source.write_text(SOURCE)
            command=['g++','-std=c++17','-Wall','-Wextra','-Werror','-g',
                '-fsanitize=address,undefined','-fno-omit-frame-pointer','-fno-pie','-no-pie',
                '-I',str(ROOT/'port/platform'),str(source),'-o',str(binary)]
            if short_wchar: command.insert(1,'-fshort-wchar')
            subprocess.run(command,check=True)
            subprocess.run([str(binary)],check=True,env={**os.environ,
                'ASAN_OPTIONS':'detect_leaks=1:halt_on_error=1',
                'UBSAN_OPTIONS':'halt_on_error=1:print_stacktrace=1'})
    def test_native_wchar_width(self): self.run_contract(True)
    def test_host_wchar_width(self): self.run_contract(False)

if __name__=='__main__': unittest.main()
