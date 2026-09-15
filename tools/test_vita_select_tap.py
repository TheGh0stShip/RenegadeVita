"""Production Select gesture: original objective action vs modifiers/focus loss."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SelectTapTests(unittest.TestCase):
    def test_tap_chords_and_focus_release(self):
        source = r'''
        #include "renegade_vita_input_contract.h"
        #include "renegade_vita_button_state_contract.h"
        #include <assert.h>
        using namespace RenegadeVitaInput;
        int main() {
            SelectTap tap;
            // Holding Select across initialization must never emit an action.
            assert(!tap.Sample(true,false,true));
            assert(!tap.Sample(false,false,true));
            // One original hit on release, no repeats while held or neutral.
            for(int i=0;i<100;++i) assert(!tap.Sample(true,false,true));
            assert(tap.Sample(false,false,true));
            assert(!tap.Sample(false,false,true));
            // Select+Square, either press order and either release order.
            for(int order=0;order<4;++order) {
                assert(!tap.Sample(true,order&1,true));
                assert(!tap.Sample(true,true,true));
                assert(!tap.Sample(order&2,!(order&2),true));
                assert(!tap.Sample(false,false,true));
            }
            // A modifier first appearing on the release sample consumes it.
            assert(!tap.Sample(true,false,true));
            assert(!tap.Sample(false,true,true));
            // Menu/IME/diagnostic mode must not carry a tap into gameplay.
            assert(!tap.Sample(true,false,true));
            assert(!tap.Sample(true,false,false));
            assert(!tap.Sample(true,false,true));
            assert(!tap.Sample(false,false,true));
            assert(!tap.Sample(true,false,true));
            tap.Reset();
            assert(!tap.Sample(false,false,true));
            assert(!tap.Sample(true,false,true));
            assert(tap.Sample(false,false,true));
            // Actual logical key conversion: hit, then release, never stuck.
            uint8_t state=Advance_Button_State(0,true);
            assert((state & BUTTON_HIT)!=0);
            state=Advance_Button_State(state,false);
            assert((state & BUTTON_HELD)==0 && (state & BUTTON_RELEASED)!=0);
        }
        '''
        with tempfile.TemporaryDirectory(prefix='vita-select-') as d:
            cpp = Path(d)/'select.cpp'; binary=Path(d)/'select'
            cpp.write_text(source)
            subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror',
                '-fsanitize=address,undefined','-fno-omit-frame-pointer','-no-pie',
                '-I',str(ROOT/'port/platform'),str(cpp),'-o',str(binary)], check=True)
            subprocess.run([str(binary)],check=True)


if __name__ == '__main__':
    unittest.main()
